"""Ingestion job lifecycle helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, IngestionJob
from app.observability.logging import get_logger

logger = get_logger(__name__)


async def create_job(
    session: AsyncSession,
    *,
    tenant_id: str,
    document_id: str,
    max_attempts: int = 2,
) -> IngestionJob:
    job = IngestionJob(
        tenant_id=tenant_id,
        document_id=document_id,
        status="queued",
        stage="queued",
        queued_at=datetime.now(timezone.utc),
        max_attempts=max_attempts,
    )
    session.add(job)
    await session.flush()
    logger.info("ingestion_job_created", job_id=job.id, document_id=document_id)
    return job


async def claim_next_job(session: AsyncSession) -> IngestionJob | None:
    """Atomically claim the oldest queued job."""
    statement = (
        select(IngestionJob)
        .where(IngestionJob.status == "queued")
        .order_by(IngestionJob.created_at.asc())
        .limit(1)
    )
    job = (await session.execute(statement)).scalar_one_or_none()
    if job is None:
        return None
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    job.attempts += 1
    job.stage = "starting"
    await session.flush()
    return job


async def mark_job(
    session: AsyncSession,
    job: IngestionJob,
    *,
    status: str | None = None,
    stage: str | None = None,
    progress: float | None = None,
    error: str | None = None,
    metrics: dict | None = None,
) -> None:
    if status:
        job.status = status
    if stage:
        job.stage = stage
    if progress is not None:
        job.progress = progress
    if error is not None:
        job.error_message = error[:2000]
    if metrics:
        job.metrics = {**(job.metrics or {}), **metrics}
    if status in {"succeeded", "failed", "cancelled"}:
        job.finished_at = datetime.now(timezone.utc)
    await session.flush()


async def latest_job_for_document(session: AsyncSession, document_id: str) -> IngestionJob | None:
    statement = (
        select(IngestionJob)
        .where(IngestionJob.document_id == document_id)
        .order_by(IngestionJob.created_at.desc())
        .limit(1)
    )
    return (await session.execute(statement)).scalar_one_or_none()


async def requeue_stuck_jobs(session: AsyncSession, *, older_than_seconds: int = 1800) -> int:
    """Return jobs orphaned by a crash to the queue (bounded by max_attempts)."""
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=older_than_seconds)
    jobs = list(
        (
            await session.execute(
                select(IngestionJob).where(IngestionJob.status == "running", IngestionJob.started_at < cutoff)
            )
        ).scalars()
    )
    requeued = 0
    for job in jobs:
        if job.attempts >= job.max_attempts:
            job.status = "failed"
            job.stage = "abandoned"
            job.error_message = "Job exceeded its attempt limit after a worker restart."
            job.finished_at = datetime.now(timezone.utc)
            document = await session.get(Document, job.document_id)
            if document is not None:
                document.status = "failed"
                document.error_message = job.error_message
        else:
            job.status = "queued"
            job.stage = "queued"
            requeued += 1
    await session.flush()
    return requeued
