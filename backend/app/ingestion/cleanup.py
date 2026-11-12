"""Cleanup of abandoned candidate versions.

A staged re-index reserves a candidate version, writes chunks, prices and
certificates against it, and activates it only once indexing succeeded. If the
worker dies after reservation (or loses its lease mid-run), the document keeps a
``candidate_indexing_version`` that nothing will ever activate: new reservations
are refused and the partial rows stay in the database and the vector index.

This sweep finds candidates that are stale *and* have no queued or running job,
removes their derived rows and vectors, and clears the reservation so the
document can be re-indexed.

Safety rules:

* A document with an active job is never touched, regardless of age.
* Only rows for the candidate version are deleted; the active version's chunks,
  prices and certificates are left exactly as they are.
* A vector-store failure is logged and counted, but the SQL cleanup still runs;
  the stale vectors carry a version that no active query selects, so they cannot
  surface in results.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.db.models import (
    Chunk,
    ComplianceCertificate,
    Document,
    DocumentPage,
    IngestionJob,
    Price,
    TableRecord,
)
from app.observability.logging import get_logger

logger = get_logger(__name__)

#: Collections that store per-version points. Names come from settings so a
#: deployment that renames a collection stays consistent with ingestion.
_VECTOR_COLLECTION_SETTINGS = (
    "qdrant_collection_chunks",
    "qdrant_collection_pages",
    "qdrant_collection_tables",
)


async def purge_orphaned_derived_rows(session: AsyncSession) -> dict[str, int]:
    """Delete derived rows whose document no longer exists.

    Documents deleted on a SQLite deployment before explicit derived-row
    deletion was added left their chunks and facts behind, because SQLite does
    not enforce ``ON DELETE CASCADE`` unless foreign keys are enabled per
    connection. This sweep is idempotent and safe to run on every recovery.
    """
    document_ids = select(Document.id)
    targets: tuple[tuple[Any, Any, str], ...] = (
        (Chunk, Chunk.document_id, "chunks"),
        (DocumentPage, DocumentPage.document_id, "pages"),
        (TableRecord, TableRecord.document_id, "tables"),
        (Price, Price.source_document_id, "prices"),
        (ComplianceCertificate, ComplianceCertificate.source_document_id, "certificates"),
        (IngestionJob, IngestionJob.document_id, "jobs"),
    )
    counts: dict[str, int] = {}
    for model, column, key in targets:
        result = await session.execute(delete(model).where(column.not_in(document_ids)))
        counts[key] = result.rowcount or 0
    await session.flush()
    if any(counts.values()):
        logger.warning("orphaned_derived_rows_purged", **counts)
    return counts


async def sweep_abandoned_candidates(
    session: AsyncSession,
    *,
    settings: Settings,
    vector: Any | None = None,
    stale_after_seconds: int = 3600,
    now: datetime | None = None,
    tenant_id: str | None = None,
) -> dict[str, int]:
    """Remove candidate versions that no job will ever activate."""
    moment = now or datetime.now(UTC)
    cutoff = moment - timedelta(seconds=stale_after_seconds)

    statement = select(Document).where(
        Document.candidate_indexing_version.is_not(None),
        Document.updated_at < cutoff,
    )
    if tenant_id is not None:
        statement = statement.where(Document.tenant_id == tenant_id)
    documents = list((await session.execute(statement)).scalars())

    counts: dict[str, int] = {
        "documents_swept": 0,
        "chunks_deleted": 0,
        "prices_deleted": 0,
        "certificates_deleted": 0,
        "vectors_deleted": 0,
        "skipped_active_job": 0,
        "vector_errors": 0,
    }

    for document in documents:
        version = document.candidate_indexing_version
        if version is None:  # defensive: the query filters these out
            continue

        active_job = (
            await session.execute(
                select(IngestionJob.id)
                .where(
                    IngestionJob.document_id == document.id,
                    IngestionJob.status.in_(["queued", "running"]),
                )
                .limit(1)
            )
        ).first()
        if active_job is not None:
            counts["skipped_active_job"] += 1
            continue

        deletions: tuple[tuple[Any, Any, str], ...] = (
            (Chunk, Chunk.document_id, "chunks_deleted"),
            (Price, Price.source_document_id, "prices_deleted"),
            (ComplianceCertificate, ComplianceCertificate.source_document_id, "certificates_deleted"),
        )
        for model, document_column, counter in deletions:
            result = await session.execute(
                delete(model).where(
                    document_column == document.id,
                    model.tenant_id == document.tenant_id,
                    model.indexing_version == version,
                )
            )
            counts[counter] += result.rowcount or 0

        if vector is not None:
            for setting_name in _VECTOR_COLLECTION_SETTINGS:
                collection = getattr(settings, setting_name, None)
                if not collection:
                    continue
                try:
                    counts["vectors_deleted"] += await vector.delete_by_version(
                        collection,
                        document.id,
                        version,
                        tenant_id=document.tenant_id,
                    )
                except Exception as exc:  # noqa: BLE001 — stale points are inert
                    counts["vector_errors"] += 1
                    logger.warning(
                        "candidate_vector_cleanup_failed",
                        document_id=document.id,
                        version=version,
                        collection=collection,
                        error=str(exc),
                    )

        document.candidate_indexing_version = None
        counts["documents_swept"] += 1

    await session.flush()

    if counts["documents_swept"]:
        logger.warning("abandoned_candidates_swept", **counts)
    return counts
