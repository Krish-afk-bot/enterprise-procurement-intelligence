"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_principal, rate_limit
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
from app.security.tokens import REFRESH_TOKEN_TYPE, create_token, decode_token
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
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    tenant = await _resolve_tenant(session, settings, payload.tenant_slug)
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
    return TokenResponse(**tokens, user=user_out(user))


@router.post(
    "/register",
    response_model=TokenResponse,
    summary="Self-registration (disabled when ALLOW_SELF_REGISTRATION=false)",
    dependencies=[Depends(rate_limit("login", "rate_limit_login"))],
)
async def register(
    payload: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    if not settings.allow_self_registration:
        raise AuthorizationError("Self-registration is disabled. Ask an administrator for an account.")
    tenant = await _resolve_tenant(session, settings, payload.tenant_slug)
    user = await auth_service.create_user(
        session,
        tenant_id=tenant.id,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        role="buyer",
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
    return TokenResponse(**tokens, user=user_out(user))


@router.post("/refresh", response_model=TokenResponse, summary="Refresh an access token")
async def refresh(
    payload: RefreshRequest,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    claims = decode_token(settings, payload.refresh_token, expected_type=REFRESH_TOKEN_TYPE)
    user = await session.get(User, claims["sub"])
    if user is None or not user.is_active:
        raise AuthenticationError("The account for this token no longer exists or is disabled.")
    if user.tenant_id != claims.get("tid"):
        raise AuthenticationError("The token tenant does not match the account tenant.")
    tokens = auth_service.issue_tokens(settings, user)
    return TokenResponse(**tokens, user=user_out(user))


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


@router.post("/logout", summary="Client-side logout (server records the audit event)")
async def logout(
    request: Request,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await audit.record_principal_action(
        session, principal, action=audit.ACTION_LOGOUT, ip_address=get_client_ip(request)
    )
    return {"status": "logged_out"}


__all__ = ["router", "user_out", "role_exists", "ValidationError"]
