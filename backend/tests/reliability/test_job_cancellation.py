"""Cooperative cancellation of ingestion jobs.

A queued job stops immediately. A running job is cancelled by clearing its
lease, so the worker's next heartbeat fails and it abandons the run. Either way
the reserved candidate version must be released.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.errors import NotFoundError
from app.db.base import Base
from app.db.models import Document, IngestionJob, Tenant
from app.services.documents import cancel_document_job


class _Principal:
    """Minimal stand-in for the authenticated principal the service needs."""

    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id

    def require(self, permission: str) -> None:  # noqa: D401 - permission check
        return None

    def can_read_level(self, level: str) -> bool:
        return True


@pytest.fixture
async def factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def _seed(factory, *, with_job: bool = True) -> tuple[str, str, str]:
    moment = datetime.now(UTC)
    async with factory() as session:
        tenant = Tenant(name="Cancel tenant", slug="cancel-tenant")
        session.add(tenant)
        await session.flush()
        document = Document(
            tenant_id=tenant.id,
            title="Supply agreement",
            filename="supply.pdf",
            checksum="cancel-checksum",
            status="queued",
            stage="queued",
            active_indexing_version=1,
            candidate_indexing_version=2,
        )
        session.add(document)
        await session.flush()
        job_id = ""
        if with_job:
            job = IngestionJob(
                tenant_id=tenant.id,
                document_id=document.id,
                status="running",
                stage="extracting",
                queued_at=moment,
                started_at=moment,
                attempts=1,
                indexing_version=2,
                lease_token="lease-to-clear",
                lease_expires_at=moment,
            )
            session.add(job)
            await session.flush()
            job_id = job.id
        await session.commit()
        return tenant.id, document.id, job_id


@pytest.mark.asyncio
async def test_cancel_marks_the_job_and_releases_the_candidate(factory):
    tenant_id, document_id, job_id = await _seed(factory)

    async with factory() as session:
        job = await cancel_document_job(session, _Principal(tenant_id), document_id)
        await session.commit()
        assert job.id == job_id
        assert job.status == "cancelled"
        assert job.stage == "cancelled"

    async with factory() as session:
        document = await session.get(Document, document_id)
        refreshed_job = await session.get(IngestionJob, job_id)
        assert refreshed_job.lease_token is None
        assert refreshed_job.lease_expires_at is None
        assert refreshed_job.finished_at is not None
        assert document.candidate_indexing_version is None
        assert document.stage == "cancelled"
        assert document.status == "uploaded"


@pytest.mark.asyncio
async def test_cancel_without_an_active_job_is_a_not_found(factory):
    tenant_id, document_id, _ = await _seed(factory, with_job=False)

    async with factory() as session:
        with pytest.raises(NotFoundError):
            await cancel_document_job(session, _Principal(tenant_id), document_id)


@pytest.mark.asyncio
async def test_cancel_from_another_tenant_is_refused(factory):
    _, document_id, _ = await _seed(factory)

    async with factory() as session:
        with pytest.raises(NotFoundError):
            await cancel_document_job(session, _Principal("ten_other"), document_id)
