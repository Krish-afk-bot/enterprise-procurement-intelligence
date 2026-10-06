"""Asynchronous ingestion worker.

Documents are processed out of band: upload returns immediately with a ``job_id``
and the worker picks jobs off the queue (PRD s.58). The worker is an asyncio task
here; the same loop runs as a separate process via ``python -m app.workers.ingestion_worker``
or the ``worker`` service in docker-compose.
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime

from app.config.container import Container, get_container
from app.config.settings import Settings, get_settings
from app.db.models import Document, IngestionJob
from app.db.session import dispose_engine, init_db, session_scope
from app.ingestion.jobs import claim_next_job, mark_job, requeue_stuck_jobs
from app.ingestion.pipeline import IngestionPipeline
from app.observability.logging import configure_logging, get_logger

logger = get_logger(__name__)


class IngestionWorker:
    def __init__(self, settings: Settings, container: Container, *, concurrency: int | None = None) -> None:
        self.settings = settings
        self.container = container
        self.concurrency = max(1, concurrency or settings.worker_concurrency)
        self._tasks: list[asyncio.Task] = []
        self._stopping = asyncio.Event()
        self._pipeline = IngestionPipeline(container, settings)
        self.processed = 0
        self.failed = 0

    # ------------------------------------------------------------------ lifecycle
    async def start(self) -> None:
        if self._tasks:
            return
        self._stopping.clear()
        self._tasks = [
            asyncio.create_task(self._loop(index), name=f"ingestion-worker-{index}")
            for index in range(self.concurrency)
        ]
        logger.info("ingestion_worker_started", concurrency=self.concurrency)

    async def stop(self) -> None:
        self._stopping.set()
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._tasks = []
        logger.info("ingestion_worker_stopped", processed=self.processed, failed=self.failed)

    @property
    def active(self) -> bool:
        return bool(self._tasks)

    # ---------------------------------------------------------------------- loop
    async def _loop(self, index: int) -> None:
        await self._recover()
        while not self._stopping.is_set():
            try:
                job = await self._claim()
            except Exception as exc:  # noqa: BLE001
                logger.error("worker_claim_failed", worker=index, error=str(exc))
                await asyncio.sleep(self.settings.worker_poll_interval_seconds * 5)
                continue
            if job is None:
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(
                        self._stopping.wait(), timeout=self.settings.worker_poll_interval_seconds
                    )
                continue
            await self._run_job(job)

    async def _recover(self) -> None:
        try:
            async with session_scope() as session:
                requeued = await requeue_stuck_jobs(session)
            if requeued:
                logger.warning("ingestion_jobs_requeued", count=requeued)
        except Exception as exc:  # noqa: BLE001
            logger.warning("worker_recovery_failed", error=str(exc))

    async def _claim(self) -> str | None:
        async with session_scope() as session:
            job = await claim_next_job(session)
            return job.id if job else None

    async def _run_job(self, job_id: str) -> None:
        async with session_scope() as session:
            job = await session.get(IngestionJob, job_id)
            if job is None:
                return
            document_id = job.document_id
            _tenant_id = job.tenant_id  # noqa: F841 — retained for future structured logging
        logger.info("ingestion_job_started", job_id=job_id, document_id=document_id)

        async def progress(stage: str, fraction: float) -> None:
            async with session_scope() as session:
                job = await session.get(IngestionJob, job_id)
                if job is None:
                    return
                await mark_job(session, job, stage=stage, progress=fraction)
                document = await session.get(Document, document_id)
                if document is not None and document.status not in {"failed", "indexed"}:
                    document.stage = stage
                    document.progress = fraction

        outcome = await self._pipeline.process_document(document_id, progress=progress, rebuild_graph=True)
        async with session_scope() as session:
            job = await session.get(IngestionJob, job_id)
            if job is not None:
                status = "succeeded" if outcome.status in {"indexed", "needs_review"} else "failed"
                await mark_job(
                    session,
                    job,
                    status=status,
                    stage=outcome.status,
                    progress=1.0,
                    error=outcome.error,
                    metrics=outcome.metrics | {"warnings": outcome.warnings},
                )
        if outcome.status in {"indexed", "needs_review"}:
            self.processed += 1
            logger.info(
                "ingestion_job_succeeded", job_id=job_id, document_id=document_id, status=outcome.status
            )
        else:
            self.failed += 1
            logger.error("ingestion_job_failed", job_id=job_id, document_id=document_id, error=outcome.error)

    # ------------------------------------------------------- in-process helpers
    async def process_now(self, document_id: str, **kwargs) -> dict:
        """Synchronously process a document (used by scripts and integration tests)."""
        outcome = await self._pipeline.process_document(document_id, **kwargs)
        return outcome.as_dict()

    async def status(self) -> dict[str, object]:
        async with session_scope() as session:
            from sqlalchemy import func, select

            rows = (
                await session.execute(
                    select(IngestionJob.status, func.count(IngestionJob.id)).group_by(IngestionJob.status)
                )
            ).all()
        counts = {status: int(count) for status, count in rows}
        return {
            "active": self.active,
            "concurrency": self.concurrency,
            "processed": self.processed,
            "failed": self.failed,
            "queued_by_status": counts,
            "checked_at": datetime.now(UTC).isoformat(),
        }


async def run_worker_forever() -> None:  # pragma: no cover - process entrypoint
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    if settings.auto_create_schema:
        await init_db()
    container = get_container()
    await container.startup()
    worker = IngestionWorker(settings, container)
    await worker.start()
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await worker.stop()
        await container.shutdown()
        await dispose_engine()


if __name__ == "__main__":  # pragma: no cover
    try:
        asyncio.run(run_worker_forever())
    except KeyboardInterrupt:
        pass
