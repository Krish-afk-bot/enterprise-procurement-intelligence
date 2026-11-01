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
from app.ingestion.jobs import activate_candidate_version, claim_next_job, mark_job, requeue_stuck_jobs, ActivationError
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

            # Reconcile pending outbox tasks from previous worker crashes
            await self._recover_pending_outbox()
        except Exception as exc:  # noqa: BLE001
            logger.warning("worker_recovery_failed", error=str(exc))

    async def _recover_pending_outbox(self, *, max_total: int = 1000) -> None:
        """Find all jobs with pending graph sync or sparse invalidation and retry them.

        Uses stable keyset pagination on (created_at, id) to avoid OFFSET drift when
        pending jobs are cleared during execution. Maintains a failed_job_ids set within
        the recovery pass so a permanently failing job cannot cause an infinite loop.
        """
        from sqlalchemy import and_, or_, select
        last_created_at = None
        last_id = None
        batch_size = 50
        processed_count = 0
        failed_job_ids: set[str] = set()

        while processed_count < max_total:
            conditions = [IngestionJob.checkpoint == "activated"]
            if last_created_at is not None and last_id is not None:
                conditions.append(
                    or_(
                        IngestionJob.created_at > last_created_at,
                        and_(
                            IngestionJob.created_at == last_created_at,
                            IngestionJob.id > last_id,
                        ),
                    )
                )

            async with session_scope() as session:
                jobs = list(
                    (
                        await session.execute(
                            select(IngestionJob)
                            .where(*conditions)
                            .order_by(IngestionJob.created_at.asc(), IngestionJob.id.asc())
                            .limit(batch_size)
                        )
                    ).scalars()
                )

            if not jobs:
                break

            for job in jobs:
                last_created_at = job.created_at
                last_id = job.id
                processed_count += 1

                if job.id in failed_job_ids:
                    continue

                meta = job.checkpoint_metadata or {}
                if meta.get("graph_sync_pending") or meta.get("sparse_invalidation_pending"):
                    try:
                        await self._process_external_outbox(
                            job_id=job.id,
                            document_id=job.document_id,
                            tenant_id=job.tenant_id,
                            version=job.indexing_version or 1,
                        )
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(
                            "outbox_recovery_job_failed_pass",
                            job_id=job.id,
                            error=str(exc),
                        )
                        failed_job_ids.add(job.id)

            if len(jobs) < batch_size:
                break

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

        async def progress(
            stage: str,
            fraction: float,
            checkpoint: str | None = None,
            checkpoint_metadata: dict | None = None,
        ) -> None:
            async with session_scope() as session:
                job = await session.get(IngestionJob, job_id)
                if job is None:
                    return
                await mark_job(
                    session,
                    job,
                    stage=stage,
                    progress=fraction,
                    checkpoint=checkpoint,
                    checkpoint_metadata=checkpoint_metadata,
                )
                document = await session.get(Document, document_id)
                if document is not None and document.status not in {"failed", "indexed"}:
                    document.stage = stage
                    document.progress = fraction

        outcome = await self._pipeline.process_document(
            document_id, progress=progress, rebuild_graph=True, job_id=job_id
        )
        _is_candidate_ready: bool = False
        _indexing_version: int | None = None
        _tenant_id_for_activation: str | None = None

        async with session_scope() as session:
            job = await session.get(IngestionJob, job_id)
            if job is not None:
                status = "succeeded" if outcome.status in {"indexed", "needs_review"} else "failed"
                is_candidate = job.indexing_version is not None
                final_checkpoint = "candidate_ready" if (is_candidate and status == "succeeded") else None
                await mark_job(
                    session,
                    job,
                    status=status,
                    stage=outcome.status,
                    progress=1.0,
                    error=outcome.error,
                    metrics=outcome.metrics | {"warnings": outcome.warnings},
                    checkpoint=final_checkpoint,
                )
                # Capture fields needed for activation (before session closes)
                _is_candidate_ready = is_candidate and status == "succeeded"
                _indexing_version = job.indexing_version
                _tenant_id_for_activation = job.tenant_id

        # Checkpoint 3: Atomically activate the candidate if it is ready.
        # This runs in its own session so the finalization commit above is
        # durable before activation begins.
        if _is_candidate_ready and _indexing_version is not None and _tenant_id_for_activation is not None:
            try:
                async with session_scope() as session:
                    await activate_candidate_version(
                        session,
                        tenant_id=_tenant_id_for_activation,
                        document_id=document_id,
                        expected_candidate_version=_indexing_version,
                        job_id=job_id,
                    )

                # Durable outbox: Reconcile external store tasks (cache eviction and graph sync)
                await self._process_external_outbox(
                    job_id=job_id,
                    document_id=document_id,
                    tenant_id=_tenant_id_for_activation,
                    version=_indexing_version,
                )

                logger.info(
                    "candidate_activated_by_worker",
                    job_id=job_id,
                    document_id=document_id,
                    activated_version=_indexing_version,
                )
            except ActivationError as exc:
                logger.error(
                    "activation_failed",
                    job_id=job_id,
                    document_id=document_id,
                    error=str(exc),
                )
                async with session_scope() as session:
                    job = await session.get(IngestionJob, job_id)
                    if job is not None:
                        await mark_job(
                            session,
                            job,
                            status="failed",
                            stage="activation_failed",
                            error=f"ActivationError: {exc}",
                        )

        if outcome.status in {"indexed", "needs_review"}:
            self.processed += 1
            logger.info(
                "ingestion_job_succeeded", job_id=job_id, document_id=document_id, status=outcome.status
            )
        else:
            self.failed += 1
            logger.error("ingestion_job_failed", job_id=job_id, document_id=document_id, error=outcome.error)

    async def _process_external_outbox(
        self,
        *,
        job_id: str,
        document_id: str,
        tenant_id: str,
        version: int,
    ) -> None:
        """Durable outbox processor: reconciles sparse-cache eviction and Neo4j graph synchronization.

        Stale Worker Protection:
        Validates against Document.active_indexing_version. If a newer version is already active,
        graph and cache tasks for this older version are superseded and marked as skipped.
        """
        async with session_scope() as session:
            doc = await session.get(Document, document_id)
            if doc is None or doc.active_indexing_version != version:
                logger.warning(
                    "outbox_skipped_stale_version",
                    job_id=job_id,
                    document_id=document_id,
                    job_version=version,
                    active_version=doc.active_indexing_version if doc else None,
                )
                return

        # 1. Sparse / BM25 Cache Invalidation
        if self.container.sparse is not None:
            try:
                await self.container.sparse.invalidate(tenant_id)
                async with session_scope() as session:
                    job = await session.get(IngestionJob, job_id)
                    if job is not None and job.checkpoint_metadata:
                        job.checkpoint_metadata = {
                            **job.checkpoint_metadata,
                            "sparse_invalidation_pending": False,
                            "sparse_invalidated_at": datetime.now(UTC).isoformat(),
                        }
                logger.info("outbox_sparse_cache_invalidated", job_id=job_id, tenant_id=tenant_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "outbox_sparse_invalidation_failed_will_retry",
                    job_id=job_id,
                    tenant_id=tenant_id,
                    error=str(exc),
                )

        # 2. Neo4j Graph Synchronization
        if self._pipeline.rebuild_graph if hasattr(self._pipeline, "rebuild_graph") else True:
            try:
                # Load supplier, contract, extraction counts from document
                async with session_scope() as session:
                    doc = await session.get(Document, document_id)
                    supplier = None
                    contract = None
                    if doc and doc.supplier_id:
                        from app.db.models import Supplier
                        supplier = await session.get(Supplier, doc.supplier_id)
                    if doc and doc.contract_id:
                        from app.db.models import Contract
                        contract = await session.get(Contract, doc.contract_id)

                graph_ok = await self._pipeline._update_graph(
                    tenant_id=tenant_id,
                    document_id=document_id,
                    supplier=supplier,
                    contract=contract,
                    counts={},
                    is_candidate=False,
                )
                async with session_scope() as session:
                    job = await session.get(IngestionJob, job_id)
                    if job is not None and job.checkpoint_metadata:
                        job.checkpoint_metadata = {
                            **job.checkpoint_metadata,
                            "graph_sync_pending": not graph_ok,
                            "graph_synced_at": datetime.now(UTC).isoformat() if graph_ok else None,
                            "graph_status": "synced" if graph_ok else "pending_retry",
                        }
                if graph_ok:
                    logger.info("outbox_graph_synced", job_id=job_id, document_id=document_id)
                else:
                    logger.warning("outbox_graph_sync_pending_retry", job_id=job_id, document_id=document_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "outbox_graph_sync_failed_will_retry",
                    job_id=job_id,
                    document_id=document_id,
                    error=str(exc),
                )

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
