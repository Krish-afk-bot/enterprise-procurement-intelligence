"""Worker lease semantics for ingestion jobs.

A job is owned only while its lease is valid. These tests pin the contract that
recovery uses the lease rather than the start time, so a healthy long ingestion
is never requeued, while a job whose worker stopped heartbeating is.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Document, IngestionJob, Tenant
from app.ingestion.jobs import claim_next_job, heartbeat_job, mark_job, requeue_stuck_jobs


@pytest.fixture
async def factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def _document(session) -> Document:
    tenant = Tenant(name="Lease tenant", slug="lease-tenant")
    session.add(tenant)
    await session.flush()
    document = Document(
        tenant_id=tenant.id,
        title="Framework agreement",
        filename="framework.pdf",
        checksum="lease-checksum",
    )
    session.add(document)
    await session.flush()
    return document


@pytest.mark.asyncio
async def test_claim_creates_a_valid_lease(factory):
    async with factory() as session:
        document = await _document(session)
        session.add(
            IngestionJob(
                tenant_id=document.tenant_id,
                document_id=document.id,
                status="queued",
                stage="queued",
                queued_at=datetime.now(UTC),
            )
        )
        await session.commit()

    async with factory() as session:
        job = await claim_next_job(session, lease_seconds=120)
        assert job is not None
        assert job.lease_token
        assert job.lease_expires_at is not None
        # SQLite returns naive datetimes even for timezone-aware columns.
        expiry = job.lease_expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=UTC)
        assert expiry > datetime.now(UTC)
        await session.commit()


@pytest.mark.asyncio
async def test_heartbeat_extends_the_lease(factory):
    async with factory() as session:
        document = await _document(session)
        session.add(
            IngestionJob(
                tenant_id=document.tenant_id,
                document_id=document.id,
                status="queued",
                stage="queued",
                queued_at=datetime.now(UTC),
            )
        )
        await session.commit()

    async with factory() as session:
        job = await claim_next_job(session, lease_seconds=30)
        assert job is not None
        token = job.lease_token
        first_expiry = job.lease_expires_at
        await session.commit()

    async with factory() as session:
        renewed = await heartbeat_job(
            session, job_id=job.id, lease_token=token, lease_seconds=600
        )
        await session.commit()
        assert renewed is True

    async with factory() as session:
        refreshed = await session.get(IngestionJob, job.id)
        assert refreshed.lease_expires_at > first_expiry


@pytest.mark.asyncio
async def test_heartbeat_rejects_a_superseded_token(factory):
    async with factory() as session:
        document = await _document(session)
        session.add(
            IngestionJob(
                tenant_id=document.tenant_id,
                document_id=document.id,
                status="queued",
                stage="queued",
                queued_at=datetime.now(UTC),
            )
        )
        await session.commit()

    async with factory() as session:
        job = await claim_next_job(session)
        assert job is not None
        await session.commit()

    async with factory() as session:
        renewed = await heartbeat_job(session, job_id=job.id, lease_token="not-the-owner")
        await session.commit()
        assert renewed is False


@pytest.mark.asyncio
async def test_valid_lease_is_never_requeued_even_when_started_long_ago(factory):
    async with factory() as session:
        document = await _document(session)
        session.add(
            IngestionJob(
                tenant_id=document.tenant_id,
                document_id=document.id,
                status="running",
                stage="extracting",
                started_at=datetime.now(UTC) - timedelta(hours=6),
                attempts=1,
                max_attempts=3,
                lease_token="live-token",
                lease_expires_at=datetime.now(UTC) + timedelta(minutes=2),
            )
        )
        await session.commit()

    async with factory() as session:
        requeued = await requeue_stuck_jobs(session, older_than_seconds=60)
        await session.commit()

    assert requeued == 0


@pytest.mark.asyncio
async def test_expired_lease_is_requeued(factory):
    async with factory() as session:
        document = await _document(session)
        session.add(
            IngestionJob(
                tenant_id=document.tenant_id,
                document_id=document.id,
                status="running",
                stage="extracting",
                started_at=datetime.now(UTC) - timedelta(minutes=5),
                attempts=1,
                max_attempts=3,
                lease_token="dead-token",
                lease_expires_at=datetime.now(UTC) - timedelta(seconds=1),
            )
        )
        await session.commit()

    async with factory() as session:
        requeued = await requeue_stuck_jobs(session)
        await session.commit()

    async with factory() as session:
        job = (await session.execute(IngestionJob.__table__.select())).first()
        refreshed = await session.get(IngestionJob, job.id)
        assert requeued == 1
        assert refreshed.status == "queued"
        assert refreshed.lease_token is None
        assert refreshed.lease_expires_at is None


@pytest.mark.asyncio
async def test_expired_lease_at_attempt_limit_fails_the_job_and_document(factory):
    async with factory() as session:
        document = await _document(session)
        document.status = "processing"
        session.add(
            IngestionJob(
                tenant_id=document.tenant_id,
                document_id=document.id,
                status="running",
                stage="extracting",
                started_at=datetime.now(UTC) - timedelta(minutes=5),
                attempts=2,
                max_attempts=2,
                lease_token="dead-token",
                lease_expires_at=datetime.now(UTC) - timedelta(seconds=1),
            )
        )
        await session.commit()

    async with factory() as session:
        requeued = await requeue_stuck_jobs(session)
        await session.commit()

    async with factory() as session:
        job = (await session.execute(IngestionJob.__table__.select())).first()
        refreshed_job = await session.get(IngestionJob, job.id)
        refreshed_document = await session.get(Document, document.id)
        assert requeued == 0
        assert refreshed_job.status == "failed"
        assert refreshed_job.stage == "abandoned"
        assert refreshed_job.lease_token is None
        assert refreshed_document.status == "failed"


@pytest.mark.asyncio
async def test_legacy_running_job_without_lease_uses_the_start_time_rule(factory):
    async with factory() as session:
        document = await _document(session)
        session.add(
            IngestionJob(
                tenant_id=document.tenant_id,
                document_id=document.id,
                status="running",
                stage="extracting",
                started_at=datetime.now(UTC) - timedelta(hours=1),
                attempts=1,
                max_attempts=3,
            )
        )
        await session.commit()

    async with factory() as session:
        requeued = await requeue_stuck_jobs(session, older_than_seconds=1800)
        await session.commit()

    assert requeued == 1


@pytest.mark.asyncio
async def test_terminal_status_releases_the_lease(factory):
    async with factory() as session:
        document = await _document(session)
        session.add(
            IngestionJob(
                tenant_id=document.tenant_id,
                document_id=document.id,
                status="queued",
                stage="queued",
                queued_at=datetime.now(UTC),
            )
        )
        await session.commit()

    async with factory() as session:
        job = await claim_next_job(session)
        assert job is not None
        await mark_job(session, job, status="succeeded", stage="indexed", progress=1.0)
        await session.commit()
        assert job.lease_token is None
        assert job.lease_expires_at is None
