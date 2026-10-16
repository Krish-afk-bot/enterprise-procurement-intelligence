"""Regression tests for audit log field truncation.

Covers the Phase 6.1 bug: audit_logs.resource_id is VARCHAR(64).
Passing a string longer than 64 characters caused a
StringDataRightTruncationError that put the SQLAlchemy async session into
PendingRollbackError state, poisoning the response and returning HTTP 500.

Fix: record_audit() now truncates resource_id to 64 chars before flush.
If the flush still fails for another reason, a rollback is issued so the
session stays usable.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models as _models  # noqa: F401
from app.db.base import Base
from app.security.audit import record_audit, record_principal_action
from app.security.rbac import Principal

# ------------------------------------------------------------------ fixtures


@pytest.fixture()
async def session() -> AsyncSession:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


def make_principal(tenant_id: str = "ten_test") -> Principal:
    return Principal(
        user_id="usr_test",
        tenant_id=tenant_id,
        email="test@test.local",
        role="admin",
    )


# ================================================================== Truncation tests


class TestAuditResourceIdTruncation:
    async def test_resource_id_over_64_chars_truncated(self, session: AsyncSession) -> None:
        """resource_id longer than 64 chars must be silently truncated, not crash."""
        # Two UUID-like strings joined with comma = 65 chars (the exact compare scenario)
        long_id = "sup_1c4ac6a6436842c48815b6f58288f19e,sup_3e230fab7eda4b34862de2e1466fad92"
        assert len(long_id) > 64, f"Test precondition: {len(long_id)} chars"

        entry = await record_audit(
            session,
            action="compare.run",
            tenant_id="ten_test",
            resource_id=long_id,
        )
        await session.commit()

        # Verify the stored resource_id is at most 64 chars
        assert entry.resource_id is not None
        assert len(entry.resource_id) <= 64

    async def test_resource_id_exactly_64_chars_not_modified(self, session: AsyncSession) -> None:
        """A resource_id of exactly 64 chars must pass through unchanged."""
        exact_id = "a" * 64
        entry = await record_audit(
            session,
            action="query.run",
            tenant_id="ten_test",
            resource_id=exact_id,
        )
        await session.commit()
        assert entry.resource_id == exact_id

    async def test_resource_id_short_not_modified(self, session: AsyncSession) -> None:
        """A short resource_id must not be padded or changed."""
        short_id = "qry_abc123"
        entry = await record_audit(
            session,
            action="query.run",
            tenant_id="ten_test",
            resource_id=short_id,
        )
        await session.commit()
        assert entry.resource_id == short_id

    async def test_none_resource_id_accepted(self, session: AsyncSession) -> None:
        """None resource_id must not crash."""
        entry = await record_audit(
            session,
            action="auth.login",
            tenant_id="ten_test",
            resource_id=None,
        )
        await session.commit()
        assert entry.resource_id is None

    async def test_record_principal_action_with_long_id(self, session: AsyncSession) -> None:
        """record_principal_action must not crash with a long resource_id."""
        principal = make_principal()
        # Should not raise
        await record_principal_action(
            session,
            principal,
            action="compare.run",
            resource_type="comparison",
            resource_id="sup_" + "x" * 100,  # definitely over 64
        )
        await session.commit()

    async def test_session_stays_usable_after_truncation(self, session: AsyncSession) -> None:
        """After record_audit with a long resource_id the session must still work."""
        long_id = "x" * 200
        await record_audit(
            session,
            action="compare.run",
            tenant_id="ten_test",
            resource_id=long_id,
        )
        await session.commit()

        # Session must still be usable — this was the core regression
        entry2 = await record_audit(
            session,
            action="query.run",
            tenant_id="ten_test",
            resource_id="short_id",
        )
        await session.commit()
        assert entry2.resource_id == "short_id"
