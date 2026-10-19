"""Tests for authorization failure audit logging (GAP-1 remediation).

Verifies that all authorization failures are logged to the audit_logs table
for compliance review, as required by Phase 7.2B security hardening.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config.settings import Settings
from app.db import models as _models  # noqa: F401
from app.db.base import Base
from app.db.models import AuditLog, Document, Tenant, User
from app.security import audit
from app.security.rbac import Principal
from app.security.tokens import hash_password


@pytest.fixture
def audit_settings() -> Settings:
    """Settings for authorization audit tests with in-memory SQLite."""
    return Settings(
        app_env="development",
        jwt_secret="test-secret-not-for-production",
        database_url="sqlite+aiosqlite:///:memory:",
        auto_create_schema=True,
        vector_provider="local",
        graph_provider="local",
        cache_provider="memory",
        storage_provider="local",
    )


@pytest.fixture
async def session(audit_settings: Settings):
    """Database session fixture for audit tests."""
    engine = create_async_engine(
        audit_settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with SessionLocal() as sess:
        yield sess

    await engine.dispose()


@pytest.fixture
async def tenant_a(session: AsyncSession) -> Tenant:
    """Create Tenant A."""
    tenant = Tenant(name="Tenant A Corp", slug="tenant-a")
    session.add(tenant)
    await session.flush()
    return tenant


@pytest.fixture
async def tenant_b(session: AsyncSession) -> Tenant:
    """Create Tenant B."""
    tenant = Tenant(name="Tenant B Inc", slug="tenant-b")
    session.add(tenant)
    await session.flush()
    return tenant


@pytest.fixture
async def user_a(session: AsyncSession, tenant_a: Tenant) -> User:
    """Create a user in Tenant A."""
    user = User(
        tenant_id=tenant_a.id,
        email="user_a@tenant-a.example",
        full_name="User A",
        hashed_password=hash_password("password123"),
        role="procurement_manager",
    )
    session.add(user)
    await session.flush()
    return user


@pytest.fixture
async def user_b(session: AsyncSession, tenant_b: Tenant) -> User:
    """Create a user in Tenant B."""
    user = User(
        tenant_id=tenant_b.id,
        email="user_b@tenant-b.example",
        full_name="User B",
        hashed_password=hash_password("password123"),
        role="procurement_manager",
    )
    session.add(user)
    await session.flush()
    return user


@pytest.fixture
def principal_a(user_a: User) -> Principal:
    """Principal for Tenant A user."""
    return Principal(
        user_id=user_a.id,
        tenant_id=user_a.tenant_id,
        email=user_a.email,
        role=user_a.role,
        full_name=user_a.full_name,
    )


@pytest.fixture
def principal_b(user_b: User) -> Principal:
    """Principal for Tenant B user."""
    return Principal(
        user_id=user_b.id,
        tenant_id=user_b.tenant_id,
        email=user_b.email,
        role=user_b.role,
        full_name=user_b.full_name,
    )


@pytest.mark.asyncio
class TestAuthorizationAuditLogging:
    """Test that authorization failures are logged to audit_logs table."""

    async def test_direct_audit_logging(
        self, session: AsyncSession, tenant_a: Tenant, principal_b: Principal
    ) -> None:
        """Test that authorization denials can be audited directly."""
        # Simulate an authorization denial
        await audit.record_principal_action(
            session,
            principal_b,
            action=audit.ACTION_ACCESS_DENIED,
            resource_type="document",
            resource_id="doc-test-1",
            outcome="denied",
            ip_address="192.0.2.1",
            detail={"reason": "Tenant isolation violation", "code": "TENANT_ISOLATION_VIOLATION"},
        )
        await session.commit()

        # Verify audit log was created
        result = await session.execute(
            select(AuditLog)
            .where(AuditLog.action == audit.ACTION_ACCESS_DENIED)
            .where(AuditLog.resource_id == "doc-test-1")
        )
        audit_entry = result.scalar_one_or_none()

        assert audit_entry is not None, "Authorization failure should create audit log"
        assert audit_entry.outcome == "denied"
        assert audit_entry.tenant_id == principal_b.tenant_id
        assert audit_entry.user_id == principal_b.user_id
        assert audit_entry.detail["code"] == "TENANT_ISOLATION_VIOLATION"

    async def test_audit_log_contains_principal_info(
        self, session: AsyncSession, tenant_a: Tenant, principal_a: Principal, principal_b: Principal
    ) -> None:
        """Test that audit log contains user and tenant information."""
        # Simulate access denial
        await audit.record_principal_action(
            session,
            principal_b,
            action=audit.ACTION_ACCESS_DENIED,
            resource_type="document",
            resource_id="doc-test-2",
            outcome="denied",
            detail={"code": "FORBIDDEN"},
        )
        await session.commit()

        # Verify principal information in audit log
        result = await session.execute(
            select(AuditLog)
            .where(AuditLog.action == audit.ACTION_ACCESS_DENIED)
            .where(AuditLog.resource_id == "doc-test-2")
        )
        audit_entry = result.scalar_one()

        assert audit_entry.tenant_id == principal_b.tenant_id, "Should log requesting user's tenant"
        assert audit_entry.user_id == principal_b.user_id, "Should log requesting user ID"

    async def test_audit_log_includes_ip_address(
        self, session: AsyncSession, tenant_a: Tenant, principal_b: Principal
    ) -> None:
        """Test that audit log captures client IP address."""
        doc = Document(
            id="doc-audit-3",
            tenant_id=tenant_a.id,
            uploaded_by="user-a-123",
            filename="test3.pdf",
            storage_key="test/test3.pdf",
            mime_type="application/pdf",
            size_bytes=1000,
            status="completed",
        )
        session.add(doc)
        await session.commit()

        # Simulate access denial with IP address
        await audit.record_principal_action(
            session,
            principal_b,
            action=audit.ACTION_ACCESS_DENIED,
            resource_type="document",
            resource_id=doc.id,
            outcome="denied",
            ip_address="203.0.113.42",
            detail={"code": "FORBIDDEN"},
        )
        await session.commit()

        # Verify IP address is logged
        result = await session.execute(
            select(AuditLog)
            .where(AuditLog.action == audit.ACTION_ACCESS_DENIED)
            .where(AuditLog.resource_id == doc.id)
        )
        audit_entry = result.scalar_one()

        assert audit_entry.ip_address == "203.0.113.42", "Should log IP address"

    async def test_recent_access_denials_query(
        self, session: AsyncSession, tenant_a: Tenant, principal_b: Principal
    ) -> None:
        """Test querying recent authorization failures for a tenant."""
        # Create multiple documents and simulate denials
        for i in range(3):
            doc = Document(
                id=f"doc-audit-query-{i}",
                tenant_id=tenant_a.id,
                uploaded_by="user-a-123",
                filename=f"test{i}.pdf",
                storage_key=f"test/test{i}.pdf",
                mime_type="application/pdf",
                size_bytes=1000,
                status="completed",
            )
            session.add(doc)
            await session.flush()

            await audit.record_principal_action(
                session,
                principal_b,
                action=audit.ACTION_ACCESS_DENIED,
                resource_type="document",
                resource_id=doc.id,
                outcome="denied",
                detail={"code": "FORBIDDEN"},
            )
        await session.commit()

        # Query recent denials for principal_b's tenant
        denials = await audit.recent_audit_entries(
            session, tenant_id=principal_b.tenant_id, action=audit.ACTION_ACCESS_DENIED, limit=10
        )

        assert len(denials) >= 3, "Should find at least 3 access denial audit logs"
        assert all(entry.action == audit.ACTION_ACCESS_DENIED for entry in denials)
        assert all(entry.outcome == "denied" for entry in denials)
        assert all(entry.tenant_id == principal_b.tenant_id for entry in denials)

    async def test_audit_record_handles_long_resource_id(
        self, session: AsyncSession, tenant_a: Tenant, principal_b: Principal
    ) -> None:
        """Test that audit logging truncates long resource IDs to avoid database errors."""
        # Create a very long resource ID (>64 characters)
        long_id = "x" * 100

        # This should not raise an exception
        await audit.record_principal_action(
            session,
            principal_b,
            action=audit.ACTION_ACCESS_DENIED,
            resource_type="document",
            resource_id=long_id,
            outcome="denied",
            detail={"code": "FORBIDDEN"},
        )
        await session.commit()

        # Verify it was truncated
        result = await session.execute(
            select(AuditLog)
            .where(AuditLog.action == audit.ACTION_ACCESS_DENIED)
            .where(AuditLog.resource_type == "document")
        )
        audit_entry = result.scalar_one()

        assert len(audit_entry.resource_id) <= 64, "Resource ID should be truncated"
        assert audit_entry.resource_id.endswith("…"), "Truncated ID should end with ellipsis"

    async def test_audit_failure_does_not_crash(
        self, session: AsyncSession, tenant_a: Tenant, principal_b: Principal, monkeypatch
    ) -> None:
        """Test that audit logging failures are handled gracefully."""
        # Force session.flush() to fail
        original_flush = session.flush

        async def failing_flush(*args, **kwargs):
            raise RuntimeError("Database connection lost")

        monkeypatch.setattr(session, "flush", failing_flush)

        # This should not raise - audit failure is logged but doesn't break the flow
        await audit.record_principal_action(
            session,
            principal_b,
            action=audit.ACTION_ACCESS_DENIED,
            resource_type="document",
            resource_id="doc-test",
            outcome="denied",
            detail={"code": "FORBIDDEN"},
        )

        # Restore original flush
        monkeypatch.setattr(session, "flush", original_flush)
