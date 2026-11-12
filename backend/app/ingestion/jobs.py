"""Ingestion job lifecycle helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import VersionConflictError
from app.core.ids import new_id
from app.db.models import Chunk, ComplianceCertificate, Document, IngestionJob, Price
from app.observability.logging import get_logger


logger = get_logger(__name__)


async def reserve_candidate_version(
    session: AsyncSession,
    *,
    tenant_id: str,
    document_id: str,
    max_attempts: int = 2,
) -> tuple[Document, IngestionJob]:
    """Safely reserve the next candidate version for a document with concurrency protection.

    Guarantees:
    - Never modifies or deactivates the existing active_indexing_version.
    - If a candidate version is already reserved or an active job exists, raises VersionConflictError.
    - Calculates candidate_indexing_version = active_indexing_version + 1.
    - Atomically updates document.candidate_indexing_version and creates an IngestionJob
      associated with that version.
    """
    # 1. Fetch document and verify existence
    doc = await session.get(Document, document_id)
    if doc is None or doc.tenant_id != tenant_id:
        raise VersionConflictError(f"Document {document_id} not found in tenant {tenant_id}.")

    # 2. Check if a candidate reservation is already in progress on the document
    if doc.candidate_indexing_version is not None:
        raise VersionConflictError(
            f"Candidate version {doc.candidate_indexing_version} already reserved for document {document_id}."
        )

    # 3. Check if an active (queued/running) job already exists for this document
    active_job = (
        await session.execute(
            select(IngestionJob).where(
                IngestionJob.document_id == document_id,
                IngestionJob.status.in_(["queued", "running"]),
            )
        )
    ).scalar_one_or_none()
    if active_job is not None:
        raise VersionConflictError(
            f"Active ingestion job {active_job.id} (status: {active_job.status}) already exists for document {document_id}."
        )

    candidate_version = (doc.active_indexing_version or 1) + 1

    # Atomic compare-and-swap check using UPDATE statement
    stmt = (
        update(Document)
        .where(
            Document.id == document_id,
            Document.tenant_id == tenant_id,
            Document.candidate_indexing_version.is_(None),
        )
        .values(candidate_indexing_version=candidate_version)
    )
    result = await session.execute(stmt)
    if result.rowcount == 0:
        raise VersionConflictError(
            f"Concurrent candidate reservation detected for document {document_id}."
        )

    # Create the associated IngestionJob with durable indexing_version
    job = IngestionJob(
        tenant_id=tenant_id,
        document_id=document_id,
        status="queued",
        stage="queued",
        queued_at=datetime.now(UTC),
        max_attempts=max_attempts,
        indexing_version=candidate_version,
    )
    session.add(job)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise VersionConflictError(
            f"Active job already exists for document {document_id}."
        ) from exc

    # Refresh doc in session
    await session.refresh(doc)
    logger.info(
        "candidate_version_reserved",
        document_id=document_id,
        candidate_version=candidate_version,
        active_version=doc.active_indexing_version,
        job_id=job.id,
    )
    return doc, job


async def create_job(
    session: AsyncSession,
    *,
    tenant_id: str,
    document_id: str,
    indexing_version: int | None = None,
    max_attempts: int = 2,
) -> IngestionJob:
    """Create a new ingestion job for a document, associating indexing_version if provided."""
    # Check if an active job already exists
    active_job = (
        await session.execute(
            select(IngestionJob).where(
                IngestionJob.document_id == document_id,
                IngestionJob.status.in_(["queued", "running"]),
            )
        )
    ).scalar_one_or_none()
    if active_job is not None:
        raise VersionConflictError(
            f"Active ingestion job {active_job.id} (status: {active_job.status}) already exists for document {document_id}."
        )

    job = IngestionJob(
        tenant_id=tenant_id,
        document_id=document_id,
        status="queued",
        stage="queued",
        queued_at=datetime.now(UTC),
        max_attempts=max_attempts,
        indexing_version=indexing_version,
    )
    session.add(job)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise VersionConflictError(
            f"Active job already exists for document {document_id}."
        ) from exc

    logger.info("ingestion_job_created", job_id=job.id, document_id=document_id, indexing_version=indexing_version)
    return job


#: Number of candidate rows inspected per claim pass. A pass can lose every
#: candidate to another worker, so the claim retries a bounded number of times.
_CLAIM_BATCH = 8
_CLAIM_PASSES = 3


async def claim_next_job(
    session: AsyncSession, *, lease_seconds: int = 120
) -> IngestionJob | None:
    """Atomically claim the oldest queued job.

    The claim is a conditional UPDATE, not a read followed by a Python-side
    mutation: a row moves from ``queued`` to ``running`` only for the worker
    whose ``WHERE id = ? AND status = 'queued'`` guard still matches at write
    time. A worker that loses the race sees ``rowcount == 0`` and moves to the
    next candidate, so two loops (or two processes) can never process the same
    job twice.

    ``attempts`` is incremented in the same statement, so a crash between claim
    and start cannot lose the attempt count.
    """
    claimed_at = datetime.now(UTC)
    lease_token = new_id("lse")
    lease_expires_at = claimed_at + timedelta(seconds=lease_seconds)
    for _ in range(_CLAIM_PASSES):
        candidate_ids = list(
            (
                await session.execute(
                    select(IngestionJob.id)
                    .where(IngestionJob.status == "queued")
                    .order_by(IngestionJob.created_at.asc(), IngestionJob.id.asc())
                    .limit(_CLAIM_BATCH)
                )
            ).scalars()
        )
        if not candidate_ids:
            return None

        for job_id in candidate_ids:
            result = await session.execute(
                update(IngestionJob)
                .where(IngestionJob.id == job_id, IngestionJob.status == "queued")
                .values(
                    status="running",
                    stage="starting",
                    started_at=claimed_at,
                    attempts=IngestionJob.attempts + 1,
                    lease_token=lease_token,
                    lease_expires_at=lease_expires_at,
                )
            )
            if result.rowcount != 1:
                # Another worker claimed this row between our SELECT and UPDATE.
                continue
            job = await session.get(IngestionJob, job_id, populate_existing=True)
            if job is None:  # deleted between claim and re-read
                continue
            logger.info("ingestion_job_claimed", job_id=job.id, attempts=job.attempts)
            return job

    # Every candidate was taken by another worker; the caller polls again.
    return None


async def heartbeat_job(
    session: AsyncSession,
    *,
    job_id: str,
    lease_token: str,
    lease_seconds: int = 120,
) -> bool:
    """Renew the lease for a job this worker still owns.

    Returns ``False`` when the guard no longer matches, which means the lease
    expired and recovery has requeued (or failed) the job. The worker must then
    abandon its run instead of writing results for a job it no longer owns.
    """
    now = datetime.now(UTC)
    result = await session.execute(
        update(IngestionJob)
        .where(
            IngestionJob.id == job_id,
            IngestionJob.status == "running",
            IngestionJob.lease_token == lease_token,
        )
        .values(lease_expires_at=now + timedelta(seconds=lease_seconds))
    )
    return result.rowcount == 1


async def mark_job(
    session: AsyncSession,
    job: IngestionJob,
    *,
    status: str | None = None,
    stage: str | None = None,
    progress: float | None = None,
    error: str | None = None,
    metrics: dict | None = None,
    checkpoint: str | None = None,
    checkpoint_metadata: dict | None = None,
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
    if checkpoint is not None:
        job.checkpoint = checkpoint
    if checkpoint_metadata is not None:
        job.checkpoint_metadata = {**(job.checkpoint_metadata or {}), **checkpoint_metadata}
    if status in {"succeeded", "failed", "cancelled"}:
        job.finished_at = datetime.now(UTC)
        # A finished job holds no lease; recovery must not requeue it.
        job.lease_token = None
        job.lease_expires_at = None
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
    """Return jobs orphaned by a crash to the queue (bounded by max_attempts).

    Two conditions count as orphaned:

    * the job holds a lease that has expired — the worker stopped renewing it,
      so the process is gone or wedged;
    * the job predates leases (``lease_expires_at IS NULL``) and started longer
      ago than ``older_than_seconds``.

    A running job with a *valid* lease is never touched, no matter how long it
    has been running. That is the difference from the previous behaviour, which
    used the start time alone and could requeue a healthy long ingestion.

    This is a system-level operation that spans all tenants. The background worker
    has system privileges to reset jobs across the entire database.
    """
    now = datetime.now(UTC)
    legacy_cutoff = now - timedelta(seconds=older_than_seconds)
    jobs = list(
        (
            await session.execute(
                select(IngestionJob).where(
                    IngestionJob.status == "running",
                    or_(
                        and_(
                            IngestionJob.lease_expires_at.is_not(None),
                            IngestionJob.lease_expires_at < now,
                        ),
                        and_(
                            IngestionJob.lease_expires_at.is_(None),
                            IngestionJob.started_at < legacy_cutoff,
                        ),
                    ),
                )
            )
        ).scalars()
    )
    requeued = 0
    for job in jobs:
        job.lease_token = None
        job.lease_expires_at = None
        if job.attempts >= job.max_attempts:
            job.status = "failed"
            job.stage = "abandoned"
            job.error_message = "Job exceeded its attempt limit after its worker stopped renewing the lease."
            job.finished_at = now
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


# ---------------------------------------------------------------------------
# Checkpoint 3 — Atomic activation / cutover
# ---------------------------------------------------------------------------


class ActivationError(Exception):
    """Raised when candidate activation cannot proceed safely.

    Not a sub-class of VersionConflictError because activation failures are
    distinct from reservation conflicts and should be handled separately by
    callers.
    """


async def activate_candidate_version(
    session: AsyncSession,
    *,
    tenant_id: str,
    document_id: str,
    expected_candidate_version: int,
    job_id: str | None = None,
) -> Document:
    """Atomically promote a fully-prepared candidate version to active status.

    Guarantees
    ----------
    - Tenant isolation: refuses to operate on a document that does not belong
      to ``tenant_id``.
    - Candidate verification: refuses to activate if
      ``document.candidate_indexing_version != expected_candidate_version``.
    - Stale-worker protection: the CAS UPDATE uses a WHERE clause that
      matches both ``id`` and ``candidate_indexing_version == expected``.
      Only one concurrent transaction can successfully flip the document row.
    - Active version preserved on failure: if any step raises, the caller's
      ``session`` is left uncommitted so a rollback restores the original
      state.
    - Idempotent on repeated calls with the same version: if the document is
      already at ``active_indexing_version == expected_candidate_version``
      (i.e. a previous activation succeeded and the job was retried), the
      function detects the completed state and returns early without error.

    Activation steps (all flushed in a single unit of work)
    -------------------------------------------------------
    1. Load and validate Document — tenant check, candidate version match.
    2. CAS UPDATE Document: flip ``active_indexing_version`` and clear
       ``candidate_indexing_version`` only if the WHERE guard still matches.
    3. Deactivate old active chunks:
       ``UPDATE chunks SET is_active = false WHERE document_id = ? AND
         indexing_version = <old_active_version> AND is_active = true``
    4. Activate candidate chunks:
       ``UPDATE chunks SET is_active = true WHERE document_id = ? AND
         indexing_version = <candidate_version> AND is_active = false``
    5. Update Document status to "indexed" and stage to "indexed".
    6. If ``job_id`` is provided, stamp the job checkpoint to "activated".
    7. Flush all changes (the caller commits or the outer session rolls back).

    Parameters
    ----------
    session:
        An open ``AsyncSession``.  The caller owns commit/rollback.
    tenant_id:
        The tenant that owns the document.
    document_id:
        The document to activate.
    expected_candidate_version:
        The candidate version that should be promoted.  Must match
        ``document.candidate_indexing_version``.
    job_id:
        Optional IngestionJob id to update with the activation checkpoint.

    Returns
    -------
    Document
        The refreshed document after activation.

    Raises
    ------
    ActivationError
        If the document does not exist, belongs to a different tenant, has no
        matching candidate version, or if a concurrent transaction won the CAS
        race.
    """
    # 1. Load and validate the document
    doc = await session.get(Document, document_id)
    if doc is None or doc.tenant_id != tenant_id:
        raise ActivationError(
            f"Document {document_id!r} not found in tenant {tenant_id!r}."
        )

    # Validate job if supplied (or if required)
    job: IngestionJob | None = None
    if job_id is not None:
        job = await session.get(IngestionJob, job_id)
        if job is None:
            # The job row is bookkeeping: it carries the checkpoint and the
            # prepared version. A prepared candidate must still be activatable
            # when that row has been cleaned up, otherwise a finished ingestion
            # is stranded forever. Absence is recorded, not fatal.
            logger.warning("activation_job_row_missing", job_id=job_id, document_id=document_id)
        elif job.tenant_id != tenant_id or job.document_id != document_id:
            raise ActivationError(
                f"Job {job_id!r} tenant/document mismatch: job has "
                f"({job.tenant_id!r}, {job.document_id!r}), expected ({tenant_id!r}, {document_id!r})."
            )
        elif job.indexing_version != expected_candidate_version:
            raise ActivationError(
                f"Job {job_id!r} indexing_version={job.indexing_version!r} does not match "
                f"expected candidate version {expected_candidate_version!r}."
            )

    # Idempotency: if already activated (previous call succeeded, job retried)
    if doc.active_indexing_version == expected_candidate_version and doc.candidate_indexing_version is None:
        if job is not None and job.checkpoint not in {"activated", "candidate_ready"}:
            raise ActivationError(
                f"Job {job_id!r} is in state {job.status!r}/{job.checkpoint!r}; "
                "cannot acknowledge completed activation for a non-ready job."
            )
        logger.info(
            "activation_already_complete",
            document_id=document_id,
            active_version=doc.active_indexing_version,
            job_id=job_id,
        )
        return doc

    # Validate job readiness if job_id is provided
    if job is not None:
        if job.status != "succeeded" or job.checkpoint != "candidate_ready":
            raise ActivationError(
                f"Job {job_id!r} is not in a valid ready state for activation: "
                f"status={job.status!r}, checkpoint={job.checkpoint!r}. Expected succeeded/candidate_ready."
            )

    # Validate candidate slot
    if doc.candidate_indexing_version != expected_candidate_version:
        raise ActivationError(
            f"Document {document_id!r} has candidate_indexing_version="
            f"{doc.candidate_indexing_version!r}, expected {expected_candidate_version!r}. "
            "Activation refused."
        )

    old_active_version = doc.active_indexing_version

    # Safety: the candidate must be strictly newer than the active version.
    if expected_candidate_version <= old_active_version:
        raise ActivationError(
            f"Candidate version {expected_candidate_version} is not strictly newer than the "
            f"active version {old_active_version} for document {document_id!r}."
        )

    # Verify at least one valid candidate chunk exists for this document, tenant, and version
    candidate_chunk_count = (
        await session.execute(
            select(func.count(Chunk.id)).where(
                Chunk.document_id == document_id,
                Chunk.tenant_id == tenant_id,
                Chunk.indexing_version == expected_candidate_version,
            )
        )
    ).scalar_one()
    if (candidate_chunk_count or 0) == 0:
        raise ActivationError(
            f"Cannot activate candidate version {expected_candidate_version} for document "
            f"{document_id!r}: no candidate chunks found for tenant {tenant_id!r}."
        )

    # 2. CAS UPDATE — only wins if the WHERE guard still matches.
    #    A concurrent activation that already flipped the row will cause
    #    rowcount == 0 here, which we detect and raise on.
    cas_result = await session.execute(
        update(Document)
        .where(
            Document.id == document_id,
            Document.tenant_id == tenant_id,
            Document.candidate_indexing_version == expected_candidate_version,
        )
        .values(
            active_indexing_version=expected_candidate_version,
            candidate_indexing_version=None,
            status="indexed",
            stage="indexed",
            progress=1.0,
            error_message=None,
        )
    )
    if cas_result.rowcount == 0:
        raise ActivationError(
            f"CAS guard failed for document {document_id!r}: a concurrent activation may have "
            "already completed, or the candidate version no longer matches. Activation aborted."
        )

    # 3. Deactivate old active chunks and structured records (version == old_active_version)
    if old_active_version is not None:
        await session.execute(
            update(Chunk)
            .where(
                Chunk.document_id == document_id,
                Chunk.tenant_id == tenant_id,
                Chunk.indexing_version == old_active_version,
                Chunk.is_active == True,  # noqa: E712
            )
            .values(is_active=False)
        )
        await session.execute(
            update(Price)
            .where(
                Price.source_document_id == document_id,
                Price.tenant_id == tenant_id,
                Price.indexing_version == old_active_version,
                Price.is_active == True,  # noqa: E712
            )
            .values(is_active=False)
        )
        await session.execute(
            update(ComplianceCertificate)
            .where(
                ComplianceCertificate.source_document_id == document_id,
                ComplianceCertificate.tenant_id == tenant_id,
                ComplianceCertificate.indexing_version == old_active_version,
                ComplianceCertificate.is_active == True,  # noqa: E712
            )
            .values(is_active=False)
        )

    # 4. Activate candidate chunks and structured records
    await session.execute(
        update(Chunk)
        .where(
            Chunk.document_id == document_id,
            Chunk.tenant_id == tenant_id,
            Chunk.indexing_version == expected_candidate_version,
            Chunk.is_active == False,  # noqa: E712
        )
        .values(is_active=True)
    )
    await session.execute(
        update(Price)
        .where(
            Price.source_document_id == document_id,
            Price.tenant_id == tenant_id,
            Price.indexing_version == expected_candidate_version,
            Price.is_active == False,  # noqa: E712
        )
        .values(is_active=True)
    )
    await session.execute(
        update(ComplianceCertificate)
        .where(
            ComplianceCertificate.source_document_id == document_id,
            ComplianceCertificate.tenant_id == tenant_id,
            ComplianceCertificate.indexing_version == expected_candidate_version,
            ComplianceCertificate.is_active == False,  # noqa: E712
        )
        .values(is_active=True)
    )

    # 5. Stamp the job checkpoint and durable outbox if requested
    if job is not None:
        job.checkpoint = "activated"
        job.checkpoint_metadata = {
            **(job.checkpoint_metadata or {}),
            "activated_version": expected_candidate_version,
            "deactivated_version": old_active_version,
            "activated_at": datetime.now(UTC).isoformat(),
            # Durable outbox: external stores must reconcile these tasks
            "graph_sync_pending": True,
            "graph_sync_version": expected_candidate_version,
            "sparse_invalidation_pending": True,
            "sparse_invalidation_version": expected_candidate_version,
        }

    # 6. Flush everything in one shot (caller commits or rolls back)
    await session.flush()

    # Refresh so the returned object reflects the DB state
    await session.refresh(doc)

    logger.info(
        "candidate_version_activated",
        document_id=document_id,
        tenant_id=tenant_id,
        new_active_version=expected_candidate_version,
        old_active_version=old_active_version,
        job_id=job_id,
    )
    return doc
