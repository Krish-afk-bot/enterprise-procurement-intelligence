"""Document service — upload, listing, detail, re-index and deletion.

Ownership of stored files lives in object storage; this service owns the
PostgreSQL metadata and the ingestion job that turns a file into evidence.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.container import Container
from app.core.errors import DocumentNotFoundError, ValidationError
from app.db.models import (
    ACCESS_LEVELS,
    DOCUMENT_TYPES,
    Chunk,
    Contract,
    Document,
    DocumentPage,
    IngestionJob,
    Supplier,
    TableRecord,
    User,
)
from app.ingestion.jobs import create_job, latest_job_for_document
from app.ingestion.pipeline import CHUNK_COLLECTION
from app.ingestion.validation import ValidatedUpload
from app.observability.logging import get_logger
from app.schemas.documents import (
    ChunkOut,
    DocumentDetailOut,
    DocumentOut,
    DocumentUpdate,
    IngestionJobOut,
    PageOut,
    TableOut,
    UploadSettings,
)
from app.security.rbac import Principal, PERM_DOCUMENTS_DELETE, PERM_DOCUMENTS_WRITE

logger = get_logger(__name__)


async def store_upload(
    session: AsyncSession,
    container: Container,
    principal: Principal,
    upload: ValidatedUpload,
    settings_payload: UploadSettings | None = None,
) -> tuple[Document, IngestionJob | None, str | None]:
    """Persist the file, create the document row and queue ingestion."""
    payload = settings_payload or UploadSettings()
    if payload.access_level and not principal.can_read_level(payload.access_level):
        raise ValidationError(
            "The requested access level is above what your role can assign.",
            details={"access_level": payload.access_level, "ceiling": principal.access_ceiling},
        )
    access_level = payload.access_level or "internal"

    # A replacement upload is the version workflow: the uploaded file becomes the
    # next version and the row it replaces keeps pointing at it, so the earlier
    # document, its pages and its citations are never overwritten.
    predecessor: Document | None = None
    if payload.replaces_document_id:
        predecessor = await session.get(Document, payload.replaces_document_id)
        if (
            predecessor is None
            or predecessor.tenant_id != principal.tenant_id
            or not principal.can_read_level(predecessor.access_level)
        ):
            raise ValidationError(
                "The document this upload replaces was not found in this workspace.",
                details={"replaces_document_id": payload.replaces_document_id},
            )
        if predecessor.superseded_by_id:
            raise ValidationError(
                "That document has already been replaced by a newer version.",
                details={"superseded_by_id": predecessor.superseded_by_id},
            )

    existing = (
        await session.execute(
            select(Document).where(
                Document.tenant_id == principal.tenant_id, Document.checksum == upload.sha256
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        logger.info("duplicate_upload", document_id=existing.id, checksum=upload.sha256)
        job = await latest_job_for_document(session, existing.id)
        return existing, job, existing.id

    document = Document(
        tenant_id=principal.tenant_id,
        document_type=payload.document_type or "other",
        title=payload.title or upload.filename,
        filename=upload.filename,
        mime_type=upload.detected_mime,
        size_bytes=upload.size_bytes,
        checksum=upload.sha256,
        version=payload.version or ((predecessor.version + 1) if predecessor else 1),
        revision_label=payload.revision_label,
        access_level=access_level,
        status="queued",
        stage="queued",
        effective_date=payload.effective_date,
        expiry_date=payload.expiry_date,
        is_synthetic=payload.is_synthetic or "synthetic" in upload.filename.lower(),
        uploaded_by=principal.user_id,
        source=payload.source,
        source_url=payload.source_url,
        license=payload.license,
        original_id=payload.original_id,
        retrieved_at=datetime.now(timezone.utc) if payload.source_url else None,
    )
    session.add(document)
    await session.flush()

    storage_key = f"{principal.tenant_id}/documents/{document.id}/original{upload.extension}"
    await container.storage.put(storage_key, upload.content, content_type=upload.detected_mime)
    document.storage_key = storage_key
    document.source_uri = payload.source_url or f"upload://{document.id}{upload.extension}"

    job = await create_job(session, tenant_id=principal.tenant_id, document_id=document.id)
    upload_metadata: dict[str, Any] = {
        "upload": {
            "declared_mime": upload.declared_mime,
            "detected_mime": upload.detected_mime,
            "sha256": upload.sha256,
            "size_bytes": upload.size_bytes,
            "uploaded_by": principal.user_id,
        }
    }
    if predecessor is not None:
        predecessor.superseded_by_id = document.id
        upload_metadata["replaces"] = {
            "document_id": predecessor.id,
            "version": predecessor.version,
            "title": predecessor.title or predecessor.filename,
        }
    document.extraction_metadata = upload_metadata
    return document, job, None


async def list_documents(
    session: AsyncSession,
    principal: Principal,
    *,
    status: str | None = None,
    document_type: str | None = None,
    supplier_id: str | None = None,
    contract_id: str | None = None,
    search: str | None = None,
    include_synthetic: bool = True,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Document], int]:
    conditions = [
        Document.tenant_id == principal.tenant_id,
        Document.access_level.in_(principal.readable_access_levels),
    ]
    if status:
        conditions.append(Document.status == status)
    if document_type:
        conditions.append(Document.document_type == document_type)
    if supplier_id:
        conditions.append(Document.supplier_id == supplier_id)
    if contract_id:
        conditions.append(Document.contract_id == contract_id)
    if not include_synthetic:
        conditions.append(Document.is_synthetic.is_(False))
    if search:
        needle = f"%{search.lower()}%"
        conditions.append(func.lower(Document.title).like(needle) | func.lower(Document.filename).like(needle))

    total = (
        await session.execute(select(func.count(Document.id)).where(*conditions))
    ).scalar_one()
    rows = (
        await session.execute(
            select(Document)
            .where(*conditions)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars()
    return list(rows), int(total or 0)


async def get_document(session: AsyncSession, principal: Principal, document_id: str) -> Document:
    document = await session.get(Document, document_id)
    if document is None:
        raise DocumentNotFoundError()
    if document.tenant_id != principal.tenant_id or not principal.can_read_level(document.access_level):
        # Do not reveal that the document exists in another tenant.
        raise DocumentNotFoundError()
    return document


async def document_detail(
    session: AsyncSession,
    container: Container,
    principal: Principal,
    document_id: str,
    *,
    include_page_text: bool = True,
) -> DocumentDetailOut:
    document = await get_document(session, principal, document_id)
    pages = list(
        (
            await session.execute(
                select(DocumentPage)
                .where(DocumentPage.document_id == document.id)
                .order_by(DocumentPage.page_number)
            )
        ).scalars()
    )
    tables = list(
        (
            await session.execute(
                select(TableRecord)
                .where(TableRecord.document_id == document.id)
                .order_by(TableRecord.page_number, TableRecord.table_index)
            )
        ).scalars()
    )
    type_counts = dict(
        (
            await session.execute(
                select(Chunk.content_type, func.count(Chunk.id))
                .where(Chunk.document_id == document.id)
                .group_by(Chunk.content_type)
            )
        ).all()
    )
    job = await latest_job_for_document(session, document.id)

    tables_by_page: dict[int, list[TableOut]] = {}
    for table in tables:
        tables_by_page.setdefault(table.page_number, []).append(
            TableOut(
                id=table.id,
                page_number=table.page_number,
                table_index=table.table_index,
                caption=table.caption,
                headers=table.headers,
                rows=table.rows,
                coordinates=table.coordinates,
                extraction_method=table.extraction_method,
                complexity_score=table.complexity_score,
                markdown=table.markdown,
                chunk_id=table.chunk_id,
            )
        )

    page_models: list[PageOut] = []
    for page in pages:
        image_url = None
        if page.image_key:
            try:
                image_url = await container.storage.url_for(page.image_key)
            except Exception:  # noqa: BLE001 - a missing image must not break the page
                image_url = None
        page_models.append(
            PageOut(
                id=page.id,
                page_number=page.page_number,
                width=page.width,
                height=page.height,
                has_text_layer=page.has_text_layer,
                is_scanned=page.is_scanned,
                needs_vision=page.needs_vision,
                extraction_method=page.extraction_method,
                raw_text=page.raw_text if include_page_text else None,
                ocr_text=page.ocr_text if include_page_text else None,
                vision_summary=page.vision_summary,
                image_url=image_url,
                char_count=page.char_count,
                tables=tables_by_page.get(page.page_number, []),
            )
        )

    base = DocumentOut.model_validate(document)
    references = await display_references(session, principal.tenant_id, [document])
    return DocumentDetailOut(
        **{**base.model_dump(), **(references.get(document.id) or {})},
        pages=page_models,
        job=IngestionJobOut.model_validate(job) if job else None,
        chunk_type_counts={str(key): int(value) for key, value in type_counts.items()},
        uploaded_by_name=await uploader_name(session, document.uploaded_by),
    )


async def document_chunks(
    session: AsyncSession,
    principal: Principal,
    document_id: str,
    *,
    page: int | None = None,
    content_type: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> tuple[list[ChunkOut], int]:
    document = await get_document(session, principal, document_id)
    conditions = [Chunk.document_id == document.id]
    if page is not None:
        conditions.append(Chunk.page_number == page)
    if content_type:
        conditions.append(Chunk.content_type == content_type)
    total = (await session.execute(select(func.count(Chunk.id)).where(*conditions))).scalar_one()
    rows = (
        await session.execute(
            select(Chunk).where(*conditions).order_by(Chunk.chunk_index, Chunk.page_number).limit(limit).offset(offset)
        )
    ).scalars()
    return [ChunkOut.model_validate(row) for row in rows], int(total or 0)


async def page_content(
    session: AsyncSession, container: Container, principal: Principal, document_id: str, page_number: int
) -> PageOut:
    document = await get_document(session, principal, document_id)
    page = (
        await session.execute(
            select(DocumentPage).where(
                DocumentPage.document_id == document.id, DocumentPage.page_number == page_number
            )
        )
    ).scalar_one_or_none()
    if page is None:
        raise DocumentNotFoundError(f"Page {page_number} does not exist in this document.")
    tables = list(
        (
            await session.execute(
                select(TableRecord).where(
                    TableRecord.document_id == document.id, TableRecord.page_number == page_number
                )
            )
        ).scalars()
    )
    image_url = None
    if page.image_key:
        try:
            image_url = await container.storage.url_for(page.image_key)
        except Exception:  # noqa: BLE001
            image_url = None
    return PageOut(
        id=page.id,
        page_number=page.page_number,
        width=page.width,
        height=page.height,
        has_text_layer=page.has_text_layer,
        is_scanned=page.is_scanned,
        needs_vision=page.needs_vision,
        extraction_method=page.extraction_method,
        raw_text=page.raw_text,
        ocr_text=page.ocr_text,
        vision_summary=page.vision_summary,
        image_url=image_url,
        char_count=page.char_count,
        tables=[
            TableOut(
                id=table.id,
                page_number=table.page_number,
                table_index=table.table_index,
                caption=table.caption,
                headers=table.headers,
                rows=table.rows,
                coordinates=table.coordinates,
                extraction_method=table.extraction_method,
                complexity_score=table.complexity_score,
                markdown=table.markdown,
                chunk_id=table.chunk_id,
            )
            for table in tables
        ],
    )


async def delete_document(
    session: AsyncSession, container: Container, principal: Principal, document_id: str
) -> None:
    document = await get_document(session, principal, document_id)
    principal.require(PERM_DOCUMENTS_DELETE)

    try:
        await container.vector.delete_by_document(CHUNK_COLLECTION, document.id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("vector_delete_failed", document_id=document.id, error=str(exc))
    if container.sparse is not None:
        await container.sparse.invalidate(principal.tenant_id)
    try:
        await container.graph.delete_subgraph(document.id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("graph_delete_failed", document_id=document.id, error=str(exc))
    if document.storage_key:
        try:
            await container.storage.delete(document.storage_key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("storage_delete_failed", document_id=document.id, error=str(exc))
    await session.delete(document)


async def requeue_document(
    session: AsyncSession, principal: Principal, document_id: str
) -> IngestionJob:
    document = await get_document(session, principal, document_id)
    principal.require(PERM_DOCUMENTS_WRITE)
    document.status = "queued"
    document.stage = "queued"
    document.progress = 0.0
    document.error_message = None
    job = await create_job(session, tenant_id=principal.tenant_id, document_id=document.id)
    return job


async def display_references(
    session: AsyncSession, tenant_id: str, documents: Sequence[Document]
) -> dict[str, dict[str, str | None]]:
    """Resolve supplier name and contract number for the given document rows.

    Read once per request instead of per row, and never guessed on the client.
    """
    supplier_ids = {document.supplier_id for document in documents if document.supplier_id}
    contract_ids = {document.contract_id for document in documents if document.contract_id}
    supplier_names: dict[str, str] = {}
    contract_numbers: dict[str, str] = {}
    if supplier_ids:
        rows = await session.execute(
            select(Supplier.id, Supplier.name).where(
                Supplier.tenant_id == tenant_id, Supplier.id.in_(supplier_ids)
            )
        )
        supplier_names = {str(row[0]): str(row[1]) for row in rows.all()}
    if contract_ids:
        rows = await session.execute(
            select(Contract.id, Contract.contract_number).where(
                Contract.tenant_id == tenant_id, Contract.id.in_(contract_ids)
            )
        )
        contract_numbers = {str(row[0]): str(row[1]) for row in rows.all()}
    return {
        document.id: {
            "supplier_name": supplier_names.get(document.supplier_id or ""),
            "contract_number": contract_numbers.get(document.contract_id or ""),
        }
        for document in documents
    }


async def uploader_name(session: AsyncSession, user_id: str | None) -> str | None:
    """Display name of the account that uploaded a file, when it still exists."""
    if not user_id:
        return None
    user = await session.get(User, user_id)
    if user is None:
        return None
    return user.full_name or user.email


async def update_document(
    session: AsyncSession,
    principal: Principal,
    document_id: str,
    payload: DocumentUpdate,
) -> tuple[Document, dict[str, Any]]:
    """Apply a metadata edit to a document row.

    Only the fields present in the request are touched, every value is validated
    against the vocabulary this workspace actually records, and the edit is
    appended to the document's own history. Returns the document plus a
    JSON-safe record of what changed for the audit log.
    """
    principal.require(PERM_DOCUMENTS_WRITE)
    document = await get_document(session, principal, document_id)
    provided = payload.model_fields_set
    if not provided:
        raise ValidationError("The request contained no fields to change.")

    prospective: dict[str, Any] = {}

    if "title" in provided:
        title = (payload.title or "").strip()
        if not title:
            raise ValidationError("A document needs a title.")
        prospective["title"] = title

    if "document_type" in provided:
        document_type = (payload.document_type or "").strip().lower().replace(" ", "_")
        if document_type not in DOCUMENT_TYPES:
            raise ValidationError(
                f"'{payload.document_type}' is not a document type this workspace records.",
                details={"allowed_document_types": list(DOCUMENT_TYPES)},
            )
        prospective["document_type"] = document_type

    if "supplier_id" in provided:
        supplier_id = payload.supplier_id
        if supplier_id:
            supplier = await session.get(Supplier, supplier_id)
            if supplier is None or supplier.tenant_id != principal.tenant_id:
                raise ValidationError(
                    "No supplier with that id exists in this workspace.",
                    details={"supplier_id": supplier_id},
                )
        prospective["supplier_id"] = supplier_id

    if "contract_id" in provided:
        contract_id = payload.contract_id
        if contract_id:
            contract = await session.get(Contract, contract_id)
            if contract is None or contract.tenant_id != principal.tenant_id:
                raise ValidationError(
                    "No contract with that id exists in this workspace.",
                    details={"contract_id": contract_id},
                )
        prospective["contract_id"] = contract_id

    if "access_level" in provided:
        level = (payload.access_level or "").strip().lower()
        if level not in ACCESS_LEVELS:
            raise ValidationError(
                f"'{level}' is not an access level this workspace uses.",
                details={"allowed_access_levels": list(ACCESS_LEVELS)},
            )
        if not principal.can_read_level(level):
            raise ValidationError(
                "The requested access level is above what your role can assign.",
                details={"access_level": level, "ceiling": principal.access_ceiling},
            )
        prospective["access_level"] = level

    if "revision_label" in provided:
        prospective["revision_label"] = (payload.revision_label or "").strip() or None

    for field in ("effective_date", "expiry_date"):
        if field in provided:
            prospective[field] = getattr(payload, field)
    effective = prospective.get("effective_date", document.effective_date)
    expiry = prospective.get("expiry_date", document.expiry_date)
    if effective and expiry and expiry < effective:
        raise ValidationError(
            "The expiry date cannot be earlier than the effective date.",
            details={"effective_date": effective.isoformat(), "expiry_date": expiry.isoformat()},
        )

    before = {field: _json_value(getattr(document, field)) for field in prospective}
    for field, value in prospective.items():
        setattr(document, field, value)
    after = {field: _json_value(getattr(document, field)) for field in prospective}
    changed = {
        field: {"from": before[field], "to": after[field]}
        for field in prospective
        if before[field] != after[field]
    }
    if not changed:
        return document, {}

    history = list(document.extraction_metadata.get("metadata_edits") or [])
    history.append(
        {
            "at": datetime.now(timezone.utc).isoformat(),
            "by": principal.user_id,
            "fields": sorted(changed),
        }
    )
    document.extraction_metadata = {**document.extraction_metadata, "metadata_edits": history[-20:]}
    return document, changed


def _json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


async def document_versions(
    session: AsyncSession, principal: Principal, document_id: str, *, max_chain: int = 20
) -> list[tuple[Document, bool]]:
    """Version history for a document, oldest first.

    The lineage is the stored ``superseded_by_id`` chain rather than a guess: a
    replacement records itself on the row it replaces. Returns each version with
    a flag for whether it is the version that currently governs.
    """
    document = await get_document(session, principal, document_id)
    seen = {document.id}

    first = document
    for _ in range(max_chain):
        predecessor = (
            await session.execute(
                select(Document)
                .where(Document.superseded_by_id == first.id)
                .order_by(Document.version.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if predecessor is None or predecessor.id in seen:
            break
        if predecessor.tenant_id != principal.tenant_id or not principal.can_read_level(
            predecessor.access_level
        ):
            break
        seen.add(predecessor.id)
        first = predecessor

    chain = [first]
    latest = first
    for _ in range(max_chain):
        if not latest.superseded_by_id or latest.superseded_by_id in seen:
            break
        successor = await session.get(Document, latest.superseded_by_id)
        if successor is None:
            break
        if successor.tenant_id != principal.tenant_id or not principal.can_read_level(
            successor.access_level
        ):
            break
        seen.add(successor.id)
        chain.append(successor)
        latest = successor

    ordered = sorted(
        chain,
        key=lambda item: (item.version or 1, item.created_at.timestamp() if item.created_at else 0.0),
    )
    return [(item, not item.superseded_by_id) for item in ordered]


async def document_type_counts(session: AsyncSession, tenant_id: str) -> Sequence[tuple[str, int]]:
    rows = await session.execute(
        select(Document.document_type, func.count(Document.id))
        .where(Document.tenant_id == tenant_id)
        .group_by(Document.document_type)
    )
    return [(str(row[0]), int(row[1])) for row in rows.all()]
