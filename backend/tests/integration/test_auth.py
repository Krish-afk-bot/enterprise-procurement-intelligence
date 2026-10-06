"""Integration tests for authentication service.

These tests use an in-memory SQLite database (auto-created) and exercise the
full authentication stack: tenant creation, user registration, password
verification, token issuance, and error cases.

No real HTTP requests are made here — that is the job of FastAPI TestClient
tests. This layer tests the service functions directly.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config.settings import Settings
from app.core.errors import AuthenticationError, ValidationError
from app.db import models as _models  # noqa: F401 — registers all ORM metadata
from app.db.base import Base
from app.services.auth import (
    authenticate,
    create_user,
    get_or_create_default_tenant,
    get_user_by_email,
    issue_tokens,
    principal_from_user,
)

# ------------------------------------------------------------------ fixtures


@pytest.fixture()
def auth_settings() -> Settings:
    return Settings(
        app_env="development",
        jwt_secret="test-secret-not-for-production",
        jwt_algorithm="HS256",
        # Use in-memory SQLite; StaticPool keeps it alive across sessions.
        database_url="sqlite+aiosqlite:///:memory:",
        auto_create_schema=True,
        vector_provider="local",
        graph_provider="local",
        cache_provider="memory",
        storage_provider="local",
    )


@pytest.fixture()
async def db_session(auth_settings: Settings) -> AsyncSession:
    """Create all tables in an in-memory database and yield a session."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


# ------------------------------------------------------------------ tenant creation


class TestTenantCreation:
    async def test_get_or_create_creates_tenant(
        self, db_session: AsyncSession, auth_settings: Settings
    ) -> None:
        tenant = await get_or_create_default_tenant(db_session, auth_settings)
        assert tenant.id is not None
        assert tenant.slug == auth_settings.default_tenant_slug

    async def test_get_or_create_is_idempotent(
        self, db_session: AsyncSession, auth_settings: Settings
    ) -> None:
        t1 = await get_or_create_default_tenant(db_session, auth_settings)
        t2 = await get_or_create_default_tenant(db_session, auth_settings)
        assert t1.id == t2.id


# ------------------------------------------------------------------ user creation


class TestUserCreation:
    async def test_create_user_succeeds(self, db_session: AsyncSession, auth_settings: Settings) -> None:
        tenant = await get_or_create_default_tenant(db_session, auth_settings)
        user = await create_user(
            db_session,
            tenant_id=tenant.id,
            email="alice@test.local",
            password="SecurePass123!",
            role="viewer",
        )
        assert user.id is not None
        assert user.email == "alice@test.local"
        assert user.role == "viewer"
        # Password must be hashed, never stored as plaintext
        assert user.hashed_password != "SecurePass123!"

    async def test_duplicate_email_raises_validation_error(
        self, db_session: AsyncSession, auth_settings: Settings
    ) -> None:
        tenant = await get_or_create_default_tenant(db_session, auth_settings)
        await create_user(db_session, tenant_id=tenant.id, email="bob@test.local", password="SecurePass123!")
        with pytest.raises(ValidationError, match="already exists"):
            await create_user(
                db_session, tenant_id=tenant.id, email="bob@test.local", password="AnotherPass!"
            )

    async def test_short_password_raises_validation_error(
        self, db_session: AsyncSession, auth_settings: Settings
    ) -> None:
        tenant = await get_or_create_default_tenant(db_session, auth_settings)
        with pytest.raises(ValidationError, match="8 characters"):
            await create_user(db_session, tenant_id=tenant.id, email="short@test.local", password="short")

    async def test_invalid_role_raises_validation_error(
        self, db_session: AsyncSession, auth_settings: Settings
    ) -> None:
        tenant = await get_or_create_default_tenant(db_session, auth_settings)
        with pytest.raises(ValidationError, match="role"):
            await create_user(
                db_session,
                tenant_id=tenant.id,
                email="badrole@test.local",
                password="SecurePass123!",
                role="superuser",
            )


# ------------------------------------------------------------------ authentication


class TestAuthentication:
    async def test_valid_credentials_return_user(
        self, db_session: AsyncSession, auth_settings: Settings
    ) -> None:
        tenant = await get_or_create_default_tenant(db_session, auth_settings)
        await create_user(db_session, tenant_id=tenant.id, email="carol@test.local", password="ValidPass999!")
        user = await authenticate(
            db_session, tenant_id=tenant.id, email="carol@test.local", password="ValidPass999!"
        )
        assert user.email == "carol@test.local"

    async def test_wrong_password_raises_authentication_error(
        self, db_session: AsyncSession, auth_settings: Settings
    ) -> None:
        tenant = await get_or_create_default_tenant(db_session, auth_settings)
        await create_user(db_session, tenant_id=tenant.id, email="dave@test.local", password="CorrectPass1!")
        with pytest.raises(AuthenticationError, match="Invalid"):
            await authenticate(
                db_session, tenant_id=tenant.id, email="dave@test.local", password="WrongPassword"
            )

    async def test_nonexistent_user_raises_authentication_error(
        self, db_session: AsyncSession, auth_settings: Settings
    ) -> None:
        tenant = await get_or_create_default_tenant(db_session, auth_settings)
        with pytest.raises(AuthenticationError, match="Invalid"):
            await authenticate(
                db_session, tenant_id=tenant.id, email="nobody@test.local", password="AnyPassword1!"
            )

    async def test_wrong_password_and_nonexistent_same_error(
        self, db_session: AsyncSession, auth_settings: Settings
    ) -> None:
        """Error message must not distinguish wrong password from unknown user (no enumeration)."""
        tenant = await get_or_create_default_tenant(db_session, auth_settings)
        await create_user(db_session, tenant_id=tenant.id, email="enum@test.local", password="Pass12345!")
        wrong_pass_msg: str | None = None
        unknown_user_msg: str | None = None

        try:
            await authenticate(db_session, tenant_id=tenant.id, email="enum@test.local", password="Wrong")
        except AuthenticationError as exc:
            wrong_pass_msg = str(exc)

        try:
            await authenticate(
                db_session, tenant_id=tenant.id, email="unknown_enum2@test.local", password="Wrong"
            )
        except AuthenticationError as exc:
            unknown_user_msg = str(exc)

        assert wrong_pass_msg is not None, "Expected AuthenticationError for wrong password"
        assert unknown_user_msg is not None, "Expected AuthenticationError for unknown user"
        # Both paths must return the identical message to prevent account enumeration
        assert wrong_pass_msg == unknown_user_msg, (
            f"Error messages differ — account enumeration possible: "
            f"wrong_pass={wrong_pass_msg!r}, unknown={unknown_user_msg!r}"
        )


# ------------------------------------------------------------------ token issuance


class TestTokenIssuance:
    async def test_issue_tokens_returns_access_and_refresh(
        self, db_session: AsyncSession, auth_settings: Settings
    ) -> None:
        tenant = await get_or_create_default_tenant(db_session, auth_settings)
        user = await create_user(
            db_session, tenant_id=tenant.id, email="eve@test.local", password="Tokens1234!"
        )
        tokens = issue_tokens(auth_settings, user)
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
        assert tokens["access_token"] != tokens["refresh_token"]

    async def test_principal_from_user_carries_correct_ids(
        self, db_session: AsyncSession, auth_settings: Settings
    ) -> None:
        tenant = await get_or_create_default_tenant(db_session, auth_settings)
        user = await create_user(
            db_session, tenant_id=tenant.id, email="frank@test.local", password="Principal1!"
        )
        principal = principal_from_user(user)
        assert principal.user_id == user.id
        assert principal.tenant_id == user.tenant_id
        assert principal.role == user.role


# ------------------------------------------------------------------ lookup


class TestUserLookup:
    async def test_get_user_by_email_returns_user(
        self, db_session: AsyncSession, auth_settings: Settings
    ) -> None:
        tenant = await get_or_create_default_tenant(db_session, auth_settings)
        await create_user(db_session, tenant_id=tenant.id, email="grace@test.local", password="Lookup1234!")
        found = await get_user_by_email(db_session, tenant.id, "grace@test.local")
        assert found is not None
        assert found.email == "grace@test.local"

    async def test_get_user_by_email_returns_none_for_unknown(
        self, db_session: AsyncSession, auth_settings: Settings
    ) -> None:
        tenant = await get_or_create_default_tenant(db_session, auth_settings)
        result = await get_user_by_email(db_session, tenant.id, "nothere@test.local")
        assert result is None
