"""Authentication endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_principal, rate_limit
from app.config.container import get_container
from app.config.settings import Settings, get_settings
from app.core.errors import AuthenticationError, AuthorizationError, ValidationError
from app.db.models import Tenant, User
from app.db.session import get_db
from app.observability.logging import get_logger
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RoleOut,
    TokenResponse,
    UserOut,
)
from app.security import audit
from app.security.rbac import ROLE_ACCESS_CEILING, ROLE_PERMISSIONS, Principal, role_exists
from app.security.revocation import RefreshTokenStore
from app.security.tokens import (
    REFRESH_TOKEN_TYPE,
    decode_token,
    token_remaining_seconds,
)
from app.services import auth as auth_service

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def user_out(user: User) -> UserOut:
    principal = auth_service.principal_from_user(user)
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        tenant_id=user.tenant_id,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        permissions=sorted(principal.permissions),
        access_ceiling=principal.access_ceiling,
    )


# ------------------------------------------------------------------ auth cookies


def _set_refresh_cookie(response: Response, settings: Settings, token: str, expires_at: datetime) -> None:
    """Attach the refresh token as an httpOnly, SameSite cookie."""
    max_age = max(0, int((expires_at - datetime.now(UTC)).total_seconds()))
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        max_age=max_age,
        path=settings.refresh_cookie_path,
        domain=settings.refresh_cookie_domain,
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.refresh_cookie_samesite,
    )


def _clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path=settings.refresh_cookie_path,
        domain=settings.refresh_cookie_domain,
    )


def _token_response(
    response: Response, settings: Settings, tokens: auth_service.TokenPayload, user: User
) -> TokenResponse:
    """Build the response body (access token only) and set the refresh cookie."""
    _set_refresh_cookie(response, settings, tokens["refresh_token"], tokens["refresh_expires_at"])
    return TokenResponse(
        access_token=tokens["access_token"],
        token_type="bearer",
        expires_at=tokens["expires_at"],
        refresh_expires_at=tokens["refresh_expires_at"],
        user=user_out(user),
    )


def _read_refresh_token(request: Request, settings: Settings, payload: RefreshRequest | None) -> str:
    """Prefer the httpOnly cookie; fall back to a body token for API clients."""
    raw = request.cookies.get(settings.refresh_cookie_name)
    if raw:
        return raw
    if payload is not None and payload.refresh_token:
        return payload.refresh_token
    raise AuthenticationError("No refresh token was provided.")


async def _create_workspace(session: AsyncSession) -> Tenant:
    """A self-registered account gets its own workspace.

    Joining an existing tenant implicitly would give anyone who can reach the
    registration endpoint read access to that tenant's documents. Without an
    explicit ``tenant_slug`` (an invitation to a known workspace), a new
    account starts in a workspace it owns.
    """
    import secrets

    tenant = Tenant(name="Personal workspace", slug=f"workspace-{secrets.token_hex(8)}")
    session.add(tenant)
    await session.flush()
    return tenant


async def _resolve_login_tenant(
    session: AsyncSession, settings: Settings, slug: str | None, email: str
) -> Tenant:
    """Resolve which workspace a login belongs to.

    An explicit slug scopes the login to that workspace. Without one, a unique
    email identifies its workspace, so someone who registered into their own
    workspace can still sign in. An email that exists in more than one
    workspace is ambiguous and must name the workspace.
    """
    from sqlalchemy import select

    from app.db.models import User

    if slug:
        return await _resolve_tenant(session, settings, slug)

    users = list(
        (
            await session.execute(
                select(User).where(User.email == email, User.is_active.is_(True))
            )
        ).scalars()
    )
    tenant_ids = {user.tenant_id for user in users}
    if len(tenant_ids) > 1:
        raise AuthenticationError(
            "This email belongs to more than one workspace; provide tenant_slug."
        )
    if len(tenant_ids) == 1:
        tenant = await session.get(Tenant, next(iter(tenant_ids)))
        if tenant is not None:
            return tenant
    return await _resolve_tenant(session, settings, None)


async def _resolve_tenant(session: AsyncSession, settings: Settings, slug: str | None) -> Tenant:
    from sqlalchemy import select

    wanted = slug or settings.default_tenant_slug
    tenant = (await session.execute(select(Tenant).where(Tenant.slug == wanted))).scalar_one_or_none()
    if tenant is None:
        raise AuthenticationError("Unknown tenant.")
    return tenant


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Exchange credentials for access and refresh tokens",
    dependencies=[Depends(rate_limit("login", "rate_limit_login"))],
)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    tenant = await _resolve_login_tenant(session, settings, payload.tenant_slug, payload.email)
    try:
        user = await auth_service.authenticate(
            session, tenant_id=tenant.id, email=payload.email, password=payload.password
        )
    except AuthenticationError:
        await audit.record_audit(
            session,
            action=audit.ACTION_LOGIN_FAILED,
            tenant_id=tenant.id,
            outcome="denied",
            ip_address=get_client_ip(request),
            detail={"email": payload.email},
        )
        await session.commit()
        raise
    await audit.record_audit(
        session,
        action=audit.ACTION_LOGIN,
        tenant_id=tenant.id,
        user_id=user.id,
        ip_address=get_client_ip(request),
    )
    tokens = auth_service.issue_tokens(settings, user)
    return _token_response(response, settings, tokens, user)


@router.post(
    "/register",
    response_model=TokenResponse,
    summary="Self-registration (disabled when ALLOW_SELF_REGISTRATION=false)",
    dependencies=[Depends(rate_limit("login", "rate_limit_login"))],
)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    if not settings.allow_self_registration:
        raise AuthorizationError("Self-registration is disabled. Ask an administrator for an account.")
    if payload.tenant_slug:
        tenant = await _resolve_tenant(session, settings, payload.tenant_slug)
        role = "buyer"
    else:
        tenant = await _create_workspace(session)
        role = "admin"
    user = await auth_service.create_user(
        session,
        tenant_id=tenant.id,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        role=role,
    )
    await audit.record_audit(
        session,
        action=audit.ACTION_REGISTER,
        tenant_id=tenant.id,
        user_id=user.id,
        ip_address=get_client_ip(request),
        detail={"role": user.role},
    )
    tokens = auth_service.issue_tokens(settings, user)
    return _token_response(response, settings, tokens, user)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate the refresh cookie and mint a new access token",
)
async def refresh(
    request: Request,
    response: Response,
    payload: RefreshRequest | None = None,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    raw = _read_refresh_token(request, settings, payload)
    claims = decode_token(settings, raw, expected_type=REFRESH_TOKEN_TYPE)
    store = RefreshTokenStore(get_container().cache)
    jti = str(claims.get("jti", ""))
    if await store.is_revoked(jti):
        # A rotated token was presented again: treat it as theft and fail closed.
        raise AuthenticationError("This refresh token has already been used.")
    user = await session.get(User, claims["sub"])
    if user is None or not user.is_active:
        raise AuthenticationError("The account for this token no longer exists or is disabled.")
    if user.tenant_id != claims.get("tid"):
        raise AuthenticationError("The token tenant does not match the account tenant.")
    # Rotate: the presented token can never be used again.
    await store.revoke(jti, ttl_seconds=token_remaining_seconds(claims))
    tokens = auth_service.issue_tokens(settings, user)
    return _token_response(response, settings, tokens, user)


@router.get("/me", response_model=UserOut, summary="Current user, role and effective permissions")
async def me(
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_db),
) -> UserOut:
    user = await session.get(User, principal.user_id)
    if user is None:
        raise AuthenticationError("The account no longer exists.")
    return user_out(user)


@router.get("/roles", response_model=list[RoleOut], summary="Role catalogue and permissions")
async def roles(principal: Principal = Depends(get_principal)) -> list[RoleOut]:
    principal.require("admin:read")
    return [
        RoleOut(role=role, permissions=sorted(perms), access_ceiling=ROLE_ACCESS_CEILING[role])
        for role, perms in ROLE_PERMISSIONS.items()
    ]


@router.post("/logout", summary="Clear the refresh cookie (server records the audit event)")
async def logout(
    request: Request,
    response: Response,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    raw = request.cookies.get(settings.refresh_cookie_name)
    if raw:
        try:
            claims = decode_token(settings, raw, expected_type=REFRESH_TOKEN_TYPE)
            await RefreshTokenStore(get_container().cache).revoke(
                str(claims.get("jti", "")), ttl_seconds=token_remaining_seconds(claims)
            )
        except AuthenticationError:
            # An unreadable/expired cookie still gets cleared below.
            pass
    _clear_refresh_cookie(response, settings)
    await audit.record_principal_action(
        session, principal, action=audit.ACTION_LOGOUT, ip_address=get_client_ip(request)
    )
    return {"status": "logged_out"}


__all__ = ["router", "user_out", "role_exists", "ValidationError"]
