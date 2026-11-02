"""HTTP-level tests for the refresh-cookie authentication flow.

These exercise the real FastAPI auth router through an ASGI transport:

  * login sets the refresh token as an httpOnly cookie and never returns it in
    the JSON body, so JavaScript can never read it;
  * refresh rotates the token and revokes the presented one;
  * replaying a rotated (or logged-out) token is rejected;
  * an access token cannot be used as a refresh token.

A throwaway in-memory SQLite database and a MemoryCache-backed container keep
the tests hermetic — no external services are touched.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.errors import register_exception_handlers
from app.api.v1 import auth as auth_api
from app.config.container import Container, set_container
from app.config.settings import Settings, get_settings
from app.db import models as _models  # noqa: F401 — registers all ORM metadata
from app.db.base import Base
from app.db.session import get_db
from app.providers.cache import MemoryCache
from app.services.auth import create_user, get_or_create_default_tenant

REFRESH_COOKIE = "epi_refresh"
EMAIL = "admin@test.local"
PASSWORD = "RefreshPass123!"
STRONG_SECRET = "test-secret-that-is-definitely-long-enough-32"


def build_settings(*, app_env: str = "development") -> Settings:
    return Settings(
        app_env=app_env,
        jwt_secret=STRONG_SECRET,
        jwt_algorithm="HS256",
        access_token_ttl_minutes=15,
        refresh_token_ttl_minutes=1440,
        database_url="sqlite+aiosqlite:///:memory:",
        auto_create_schema=False,
        vector_provider="local",
        graph_provider="local",
        cache_provider="memory",
        storage_provider="local",
        allow_self_registration=False,
    )


def refresh_token_from(response: httpx.Response) -> str:
    """Pull the refresh token out of the Set-Cookie header."""
    for header in response.headers.get_list("set-cookie"):
        if header.startswith(f"{REFRESH_COOKIE}="):
            return header.split(";")[0].split("=", 1)[1]
    raise AssertionError(f"no {REFRESH_COOKIE} cookie in: {response.headers.get_list('set-cookie')}")


def refresh_cookie_header(response: httpx.Response) -> str:
    return next(
        header.split(";")[0]
        for header in response.headers.get_list("set-cookie")
        if header.startswith(f"{REFRESH_COOKIE}=")
    )


@pytest.fixture()
async def auth_env(request: pytest.FixtureRequest) -> AsyncIterator[tuple[httpx.AsyncClient, Settings]]:
    """Yield (client, settings) for the auth router with a seeded admin user."""
    app_env = getattr(request, "param", "development")
    settings = build_settings(app_env=app_env)

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_db() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(auth_api.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings

    set_container(Container(settings=settings, cache=MemoryCache()))
    async with factory() as session:
        tenant = await get_or_create_default_tenant(session, settings)
        await create_user(
            session, tenant_id=tenant.id, email=EMAIL, password=PASSWORD, role="admin"
        )
        await session.commit()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, settings

    set_container(None)
    await engine.dispose()


async def login(client: httpx.AsyncClient) -> httpx.Response:
    response = await client.post(
        "/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return response


# ------------------------------------------------------------------ cookie shape


async def test_login_sets_httponly_cookie_and_omits_refresh_token(
    auth_env: tuple[httpx.AsyncClient, Settings],
) -> None:
    client, _ = auth_env
    response = await login(client)
    body = response.json()

    assert body["access_token"]
    assert body.get("refresh_token") is None, "the refresh token must never reach JavaScript"

    cookies = [h for h in response.headers.get_list("set-cookie") if h.startswith(REFRESH_COOKIE)]
    assert len(cookies) == 1, cookies
    lowered = cookies[0].lower()
    assert "httponly" in lowered
    assert "samesite=strict" in lowered
    assert "path=/api/v1/auth" in lowered
    # Development runs over plain http, so the cookie must not be Secure there.
    assert "secure" not in lowered


@pytest.mark.parametrize("auth_env", ["staging"], indirect=True)
async def test_refresh_cookie_is_secure_outside_development(
    auth_env: tuple[httpx.AsyncClient, Settings],
) -> None:
    client, _ = auth_env
    response = await login(client)
    cookie = next(h for h in response.headers.get_list("set-cookie") if h.startswith(REFRESH_COOKIE))
    assert "secure" in cookie.lower()


# ------------------------------------------------------------------ rotation


async def test_refresh_rotates_the_cookie_and_issues_new_access_token(
    auth_env: tuple[httpx.AsyncClient, Settings],
) -> None:
    client, _ = auth_env
    login_response = await login(client)
    original_access = login_response.json()["access_token"]
    original_refresh = refresh_token_from(login_response)

    response = await client.post(
        "/api/v1/auth/refresh", headers={"cookie": f"{REFRESH_COOKIE}={original_refresh}"}
    )
    assert response.status_code == 200, response.text
    rotated = response.json()
    assert rotated["access_token"] != original_access
    new_refresh = refresh_token_from(response)
    assert new_refresh != original_refresh, "the presented refresh token must be rotated"


async def test_replaying_a_rotated_token_is_rejected(
    auth_env: tuple[httpx.AsyncClient, Settings],
) -> None:
    client, _ = auth_env
    login_response = await login(client)
    stolen = refresh_token_from(login_response)

    first = await client.post(
        "/api/v1/auth/refresh", headers={"cookie": f"{REFRESH_COOKIE}={stolen}"}
    )
    assert first.status_code == 200

    replay = await client.post(
        "/api/v1/auth/refresh", headers={"cookie": f"{REFRESH_COOKIE}={stolen}"}
    )
    assert replay.status_code == 401


async def test_refresh_without_any_token_is_rejected(
    auth_env: tuple[httpx.AsyncClient, Settings],
) -> None:
    client, _ = auth_env
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401
    # The error envelope must actually be produced, not an unhandled exception.
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


async def test_access_token_cannot_be_used_as_a_refresh_token(
    auth_env: tuple[httpx.AsyncClient, Settings],
) -> None:
    client, _ = auth_env
    login_response = await login(client)
    access = login_response.json()["access_token"]

    response = await client.post(
        "/api/v1/auth/refresh", headers={"cookie": f"{REFRESH_COOKIE}={access}"}
    )
    assert response.status_code == 401


async def test_logout_revokes_the_refresh_cookie(
    auth_env: tuple[httpx.AsyncClient, Settings],
) -> None:
    client, _ = auth_env
    login_response = await login(client)
    access = login_response.json()["access_token"]
    cookie = refresh_cookie_header(login_response)

    logout = await client.post(
        "/api/v1/auth/logout", headers={"authorization": f"Bearer {access}", "cookie": cookie}
    )
    assert logout.status_code == 200
    # The server clears the cookie rather than leaving a stale value behind.
    cleared = [h for h in logout.headers.get_list("set-cookie") if h.startswith(REFRESH_COOKIE)]
    assert cleared and "max-age=0" in cleared[0].lower()

    replay = await client.post("/api/v1/auth/refresh", headers={"cookie": cookie})
    assert replay.status_code == 401
