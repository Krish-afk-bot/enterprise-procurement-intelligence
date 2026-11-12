"""Atomic claim semantics for the ingestion queue.

The previous implementation selected a queued row and mutated it in Python, so
two workers could read the same row and both process it. These tests pin the
replacement contract: one conditional UPDATE, one winner.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Document, IngestionJob, Tenant
from app.ingestion.jobs import claim_next_job


@pytest.fixture
async def factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def _seed(factory, count: int = 2) -> list[str]:
    async with factory() as session:
        tenant = Tenant(name="Test tenant", slug="test-tenant")
        session.add(tenant)
        await session.flush()
        document = Document(
            tenant_id=tenant.id,
            title="Supplier agreement",
            filename="agreement.pdf",
            checksum="abc123",
        )
        session.add(document)
        await session.flush()
        base = datetime(2026, 1, 1, tzinfo=UTC)
        jobs = [
            IngestionJob(
                tenant_id=tenant.id,
                document_id=document.id,
                status="queued",
                stage="queued",
                queued_at=base + timedelta(seconds=index),
                created_at=base + timedelta(seconds=index),
            )
            for index in range(count)
        ]
        session.add_all(jobs)
        await session.commit()
        return [job.id for job in jobs]


@pytest.mark.asyncio
async def test_each_queued_job_is_claimed_exactly_once(factory):
    job_ids = await _seed(factory, count=3)

    claimed: list[str] = []
    async with factory() as session:
        while True:
            job = await claim_next_job(session)
            if job is None:
                break
            claimed.append(job.id)
            await session.commit()

    assert claimed == job_ids, "Jobs must be claimed oldest-first, without repeats"
    assert len(set(claimed)) == len(claimed)


@pytest.mark.asyncio
async def test_claim_marks_running_and_counts_the_attempt(factory):
    await _seed(factory, count=1)

    async with factory() as session:
        job = await claim_next_job(session)
        assert job is not None
        await session.commit()
        assert job.status == "running"
        assert job.stage == "starting"
        assert job.attempts == 1
        assert job.started_at is not None


@pytest.mark.asyncio
async def test_second_claim_returns_none_for_a_claimed_job(factory):
    # A worker that loses the race must see no work, not the same job again.
    await _seed(factory, count=1)
    async with factory() as session:
        first = await claim_next_job(session)
        await session.commit()
    async with factory() as session:
        second = await claim_next_job(session)
        await session.commit()

    assert first is not None
    assert second is None


@pytest.mark.asyncio
async def test_non_queued_jobs_are_never_claimed(factory):
    job_ids = await _seed(factory, count=2)
    async with factory() as session:
        finished = await session.get(IngestionJob, job_ids[0])
        finished.status = "succeeded"
        await session.commit()

    async with factory() as session:
        job = await claim_next_job(session)
        await session.commit()

    assert job is not None
    assert job.id == job_ids[1]
