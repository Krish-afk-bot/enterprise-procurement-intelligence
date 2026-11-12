"""Abandoned candidate-version cleanup.

A crash or lost lease leaves a document with a candidate version that nothing
will activate. The sweep must remove only that version's rows, never the active
version's, and must never touch a document with a live job.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config.settings import Settings
from app.db.base import Base
from app.db.models import (
    Chunk,
    ComplianceCertificate,
    Document,
    IngestionJob,
    Price,
    Tenant,
)
from app.ingestion.cleanup import sweep_abandoned_candidates


class _RecordingVector:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int, str | None]] = []

    async def delete_by_version(
        self, collection: str, document_id: str, indexing_version: int, *, tenant_id: str | None = None
    ) -> int:
        self.calls.append((collection, document_id, indexing_version, tenant_id))
        return 2


@pytest.fixture
def settings() -> Settings:
    return Settings(app_env="test", jwt_secret="test-secret-not-for-production")


@pytest.fixture
async def factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def _seed(factory, *, age_seconds: int = 7200, with_job: bool = False) -> str:
    moment = datetime.now(UTC)
    async with factory() as session:
        tenant = Tenant(name="Sweep tenant", slug="sweep-tenant")
        session.add(tenant)
        await session.flush()
        document = Document(
            tenant_id=tenant.id,
            title="Supply agreement",
            filename="supply.pdf",
            checksum="sweep-checksum",
            active_indexing_version=1,
            candidate_indexing_version=2,
            updated_at=moment - timedelta(seconds=age_seconds),
        )
        session.add(document)
        await session.flush()
        session.add_all(
            [
                Chunk(
                    tenant_id=tenant.id,
                    document_id=document.id,
                    content="active passage",
                    indexing_version=1,
                    is_active=True,
                ),
                Chunk(
                    tenant_id=tenant.id,
                    document_id=document.id,
                    content="candidate passage",
                    indexing_version=2,
                    is_active=False,
                ),
                Price(
                    tenant_id=tenant.id,
                    source_document_id=document.id,
                    unit_price=12.5,
                    indexing_version=2,
                    is_active=False,
                ),
                ComplianceCertificate(
                    tenant_id=tenant.id,
                    source_document_id=document.id,
                    certificate_type="iso_9001",
                    indexing_version=2,
                    is_active=False,
                ),
            ]
        )
        if with_job:
            session.add(
                IngestionJob(
                    tenant_id=tenant.id,
                    document_id=document.id,
                    status="queued",
                    stage="queued",
                    queued_at=moment,
                    indexing_version=2,
                )
            )
        await session.commit()
        return document.id


async def _count(factory, model) -> int:
    async with factory() as session:
        return int((await session.execute(select(func.count()).select_from(model))).scalar_one())


@pytest.mark.asyncio
async def test_stale_candidate_rows_and_vectors_are_removed(factory, settings):
    document_id = await _seed(factory)
    vector = _RecordingVector()

    async with factory() as session:
        counts = await sweep_abandoned_candidates(
            session, settings=settings, vector=vector, stale_after_seconds=3600
        )
        await session.commit()

    assert counts["documents_swept"] == 1
    assert counts["chunks_deleted"] == 1
    assert counts["prices_deleted"] == 1
    assert counts["certificates_deleted"] == 1

    # Only the candidate version went; the active version is untouched.
    assert await _count(factory, Chunk) == 1
    assert await _count(factory, Price) == 0
    assert await _count(factory, ComplianceCertificate) == 0

    async with factory() as session:
        document = await session.get(Document, document_id)
        assert document.candidate_indexing_version is None
        assert document.active_indexing_version == 1

    assert len(vector.calls) == 3, "one delete per configured collection"
    assert all(call[2] == 2 for call in vector.calls)


@pytest.mark.asyncio
async def test_recent_candidate_is_left_alone(factory, settings):
    await _seed(factory, age_seconds=60)

    async with factory() as session:
        counts = await sweep_abandoned_candidates(
            session, settings=settings, stale_after_seconds=3600
        )
        await session.commit()

    assert counts["documents_swept"] == 0
    assert await _count(factory, Chunk) == 2


@pytest.mark.asyncio
async def test_document_with_a_live_job_is_skipped(factory, settings):
    document_id = await _seed(factory, with_job=True)

    async with factory() as session:
        counts = await sweep_abandoned_candidates(
            session, settings=settings, vector=_RecordingVector(), stale_after_seconds=3600
        )
        await session.commit()

    assert counts["skipped_active_job"] == 1
    assert counts["documents_swept"] == 0
    async with factory() as session:
        document = await session.get(Document, document_id)
        assert document.candidate_indexing_version == 2


@pytest.mark.asyncio
async def test_sweep_works_without_a_vector_provider(factory, settings):
    await _seed(factory)

    async with factory() as session:
        counts = await sweep_abandoned_candidates(
            session, settings=settings, vector=None, stale_after_seconds=3600
        )
        await session.commit()

    assert counts["documents_swept"] == 1
    assert counts["vectors_deleted"] == 0
