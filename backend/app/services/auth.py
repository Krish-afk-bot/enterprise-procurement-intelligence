"""Authentication service: tenants, users, login and bootstrap."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.core.errors import AuthenticationError, ValidationError
from app.core.ids import normalize_name
from app.db.models import Tenant, User
from app.observability.logging import get_logger
from app.security.rbac import Principal, role_exists
from app.security.tokens import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    create_token,
    hash_password,
    verify_password,
)

logger = get_logger(__name__)


async def get_or_create_default_tenant(session: AsyncSession, settings: Settings) -> Tenant:
    tenant = (
        await session.execute(select(Tenant).where(Tenant.slug == settings.default_tenant_slug))
    ).scalar_one_or_none()
    if tenant is None:
        tenant = Tenant(name=settings.bootstrap_tenant_name, slug=settings.default_tenant_slug)
        session.add(tenant)
        await session.flush()
        logger.info("tenant_created", tenant_id=tenant.id, slug=tenant.slug)
    return tenant


async def get_user_by_email(session: AsyncSession, tenant_id: str, email: str) -> User | None:
    return (
        await session.execute(
            select(User).where(User.tenant_id == tenant_id, func.lower(User.email) == email.strip().lower())
        )
    ).scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    *,
    tenant_id: str,
    email: str,
    password: str,
    full_name: str = "",
    role: str = "viewer",
) -> User:
    if not role_exists(role):
        raise ValidationError(f"Unknown role '{role}'.")
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    if await get_user_by_email(session, tenant_id, email):
        raise ValidationError("A user with that email already exists in this tenant.")
    user = User(
        tenant_id=tenant_id,
        email=email.strip().lower(),
        full_name=full_name.strip() or normalize_name(email.split("@")[0]).title(),
        hashed_password=hash_password(password),
        role=role,
    )
    session.add(user)
    await session.flush()
    logger.info("user_created", user_id=user.id, tenant_id=tenant_id, role=role)
    return user


async def authenticate(session: AsyncSession, *, tenant_id: str, email: str, password: str) -> User:
    user = await get_user_by_email(session, tenant_id, email)
    if user is None or not verify_password(password, user.hashed_password):
        # Same error for unknown user and wrong password: no account enumeration.
        raise AuthenticationError("Invalid email or password.")
    if not user.is_active:
        raise AuthenticationError("This account is disabled.")
    user.last_login_at = datetime.now(UTC)
    return user


def principal_from_user(user: User) -> Principal:
    return Principal(
        user_id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        role=user.role,
        full_name=user.full_name,
    )


def issue_tokens(settings: Settings, user: User) -> dict[str, object]:
    access_token, access_expires = create_token(
        settings,
        subject=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
        token_type=ACCESS_TOKEN_TYPE,
    )
    refresh_token, refresh_expires = create_token(
        settings,
        subject=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
        token_type=REFRESH_TOKEN_TYPE,
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_at": access_expires,
        "refresh_expires_at": refresh_expires,
    }


async def bootstrap_admin(session: AsyncSession, settings: Settings) -> User | None:
    if not (settings.bootstrap_admin_email and settings.bootstrap_admin_password):
        return None
    tenant = await get_or_create_default_tenant(session, settings)
    existing = await get_user_by_email(session, tenant.id, settings.bootstrap_admin_email)
    if existing is not None:
        if existing.role != "admin":
            existing.role = "admin"
            logger.info("bootstrap_admin_role_updated", user_id=existing.id)
        return existing
    logger.warning(
        "bootstrap_admin_created",
        email=settings.bootstrap_admin_email,
        hint="unset BOOTSTRAP_ADMIN_PASSWORD after first login",
    )
    return await create_user(
        session,
        tenant_id=tenant.id,
        email=settings.bootstrap_admin_email,
        password=settings.bootstrap_admin_password,
        full_name="Platform Administrator",
        role="admin",
    )
