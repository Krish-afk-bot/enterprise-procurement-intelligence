"""Shared FastAPI dependencies: auth, permissions, rate limiting, providers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.container import Container, get_container
from app.config.settings import Settings, get_settings
from app.core.errors import (
    AuthenticationError,
    RateLimitError,
    TenantIsolationError,
)
from app.db.session import get_db
from app.security.rbac import Principal
from app.security.tokens import decode_token

SessionDep = Depends(get_db)
SettingsDep = Depends(get_settings)


def container_dep() -> Container:
    return get_container()


ContainerDep = Depends(container_dep)


def get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


async def get_principal(
    request: Request,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Principal:
    """Resolve the caller from the Authorization header (JWT bearer)."""
    header = request.headers.get("authorization") or ""
    scheme, _, token = header.partition(" ")
    if not token or scheme.lower() != "bearer":
        raise AuthenticationError("An Authorization: Bearer <token> header is required.")

    payload = decode_token(settings, token)
    from app.db.models import User  # local import avoids a cycle at module load

    user = await session.get(User, payload["sub"])
    if user is None or not user.is_active:
        raise AuthenticationError("The account for this token no longer exists or is disabled.")
    if user.tenant_id != payload.get("tid"):
        # Token was minted for a different tenant than the user now belongs to.
        raise TenantIsolationError("The token tenant does not match the account tenant.")
    return Principal(
        user_id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        role=user.role,
        full_name=user.full_name,
    )


PrincipalDep = Depends(get_principal)


def require_permission(permission: str) -> Callable[[Principal], Awaitable[Principal]]:
    """Dependency factory enforcing a permission server-side."""

    async def _dependency(principal: Principal = Depends(get_principal)) -> Principal:
        principal.require(permission)
        return principal

    return _dependency


def rate_limit(bucket: str, limit_attr: str) -> Callable[..., Awaitable[None]]:
    """Dependency factory applying a configurable fixed-window rate limit.

    For authenticated endpoints, scope the rate limit to the user's tenant and user ID.
    For unauthenticated endpoints, scope to client IP (with X-Forwarded-For support).
    X-Forwarded-For should only be trusted when set by a reverse proxy; otherwise
    clients can spoof this header.
    """

    async def _dependency(
        request: Request,
        container: Container = Depends(container_dep),
        settings: Settings = Depends(get_settings),
        principal: Principal | None = None,  # Optional: provided if endpoint is authenticated
    ) -> None:
        if container.rate_limiter is None:
            return
        limit = int(getattr(settings, limit_attr, 0))
        # Scope authenticated requests to tenant:user for proper isolation
        if principal is not None:
            scope = f"{principal.tenant_id}:{principal.user_id}"
        else:
            # Unauthenticated: use client IP (first address in X-Forwarded-For if present)
            scope = request.headers.get("x-forwarded-for", "") or (
                request.client.host if request.client else "anonymous"
            )
            if "," in scope:
                scope = scope.split(",")[0].strip()
        allowed, _remaining, retry_after = await container.rate_limiter.check(bucket, scope, limit)
        if not allowed:
            raise RateLimitError(
                f"Rate limit exceeded for {bucket}.", details={"retry_after": retry_after, "limit": limit}
            )

    return _dependency
