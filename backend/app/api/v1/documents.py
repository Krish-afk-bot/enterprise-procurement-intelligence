"""Document management endpoints."""

from __future__ import annotations

from collections.abc import Sequence

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    container_dep,
    get_client_ip,
    get_principal,
    rate_limit,
)
from app.config.container import Container
from app.config.settings import Settings, get_settings
from app.core.errors import FileValidationError, NotFoundError, ValidationError
from app.db.models import DOCUMENT_TYPES, Document
from app.db.session import get_db
from app.ingestion.validation import SUPPORTED_MIME_TYPES, validate_upload
from app.schemas.common import Page as PageSchema
from app.schemas.documents import (
    ChunkOut,
    DocumentDetailOut,
    DocumentOut,
    DocumentUpdate,
    DocumentVersionOut,
    IngestionJobOut,
    PageOut,
    UploadLimits,
    UploadResponse,
    UploadSettings,
)
from app.security import audit
from app.security.rbac import PERM_DOCUMENTS_DELETE, PERM_DOCUMENTS_WRITE, Principal
from app.services import documents as document_service

router = APIRouter(prefix="/documents", tags=["documents"])


async def _with_references(
    session: AsyncSession, principal: Principal, documents: Sequence[Document]
) -> list[DocumentOut]:
    """Document rows with the supplier name and contract number resolved."""
    references = await document_service.display_references(session, principal.tenant_id, documents)
    items: list[DocumentOut] = []
    for document in documents:
        model = DocumentOut.model_validate(document)
        items.append(model.model_copy(update=references.get(document.id) or {}))
    return items


@router.get("/limits", response_model=UploadLimits, summary="Accepted file types and size limit")
async def upload_limits(settings: Settings = Depends(get_settings)) -> UploadLimits:
    return UploadLimits(
        max_upload_mb=settings.max_upload_mb,
        allowed_extensions=settings.allowed_extensions,
        supported_mime_types=SUPPORTED_MIME_TYPES,
    )


@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload a document and queue ingestion",
    dependencies=[Depends(rate_limit("upload", "rate_limit_upload"))],
)
async def upload_document(
    request: Request,
    file: UploadFile = File(..., description="PDF, DOCX, XLSX, CSV, TXT or image"),
    document_type: str | None = Form(default=None),
    supplier_name: str | None = Form(default=None),
    contract_number: str | None = Form(default=None),
    title: str | None = Form(default=None),
    version: int | None = Form(default=None),
    revision_label: str | None = Form(default=None),
    access_level: str | None = Form(default=None),
    effective_date: str | None = Form(default=None),
    expiry_date: str | None = Form(default=None),
    is_synthetic: bool = Form(default=False),
    source: str | None = Form(default=None),
    source_url: str | None = Form(default=None),
    license: str | None = Form(default=None),
    original_id: str | None = Form(default=None),
    replaces_document_id: str | None = Form(
        default=None, description="Upload this file as the next version of an existing document"
    ),
    session: AsyncSession = Depends(get_db),
    container: Container = Depends(container_dep),
    principal: Principal = Depends(get_principal),
    settings: Settings = Depends(get_settings),
) -> UploadResponse:
    principal.require(PERM_DOCUMENTS_WRITE)
    if document_type and document_type.strip().lower().replace(" ", "_") not in DOCUMENT_TYPES:
        raise ValidationError(
            f"'{document_type}' is not a document type this workspace records.",
            details={"allowed_document_types": list(DOCUMENT_TYPES)},
        )
    content = await file.read()
    upload = validate_upload(
        filename=file.filename or "upload",
        content=content,
        declared_mime=file.content_type,
        settings=settings,
    )

    from datetime import date

    def _date(value: str | None) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValidationError(f"'{value}' is not a valid ISO date (YYYY-MM-DD).") from exc

    payload = UploadSettings(
        document_type=document_type,
        supplier_name=supplier_name,
        contract_number=contract_number,
        title=title,
        version=version,
        revision_label=revision_label,
        access_level=access_level,
        effective_date=_date(effective_date),
        expiry_date=_date(expiry_date),
        is_synthetic=is_synthetic,
        source=source,
        source_url=source_url,
        license=license,
        original_id=original_id,
        replaces_document_id=replaces_document_id,
    )
    document, job, duplicate_of = await document_service.store_upload(
        session, container, principal, upload, payload
    )
    await audit.record_principal_action(
        session,
        principal,
        action=audit.ACTION_DOCUMENT_UPLOAD,
        resource_type="document",
        resource_id=document.id,
        ip_address=get_client_ip(request),
        detail={
            "filename": upload.filename,
            "checksum": upload.sha256,
            "size_bytes": upload.size_bytes,
            "duplicate_of": duplicate_of,
            "replaces_document_id": replaces_document_id,
        },
    )
    message = (
        "This file is already indexed for your tenant; the existing document was returned."
        if duplicate_of
        else "Upload accepted. Ingestion has been queued."
    )
    return UploadResponse(
        document=DocumentOut.model_validate(document),
        job=IngestionJobOut.model_validate(job) if job else None,
        duplicate_of=duplicate_of,
        message=message,
    )


@router.get("", response_model=PageSchema[DocumentOut], summary="List documents")
async def list_documents(
    status: str | None = Query(default=None),
    document_type: str | None = Query(default=None),
    supplier_id: str | None = Query(default=None),
    contract_id: str | None = Query(default=None),
    search: str | None = Query(default=None),
    include_synthetic: bool = Query(default=True),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> PageSchema[DocumentOut]:
    documents, total = await document_service.list_documents(
        session,
        principal,
        status=status,
        document_type=document_type,
        supplier_id=supplier_id,
        contract_id=contract_id,
        search=search,
        include_synthetic=include_synthetic,
        limit=limit,
        offset=offset,
    )
    return PageSchema[DocumentOut](
        items=await _with_references(session, principal, documents),
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(documents) < total,
    )


@router.get("/{document_id}", response_model=DocumentDetailOut, summary="Document detail with pages and tables")
async def get_document(
    document_id: str,
    session: AsyncSession = Depends(get_db),
    container: Container = Depends(container_dep),
    principal: Principal = Depends(get_principal),
) -> DocumentDetailOut:
    detail = await document_service.document_detail(session, container, principal, document_id)
    await audit.record_principal_action(
        session, principal, action=audit.ACTION_DOCUMENT_READ, resource_type="document", resource_id=document_id
    )
    return detail


@router.patch(
    "/{document_id}",
    response_model=DocumentOut,
    summary="Update document metadata",
)
async def update_document(
    document_id: str,
    payload: DocumentUpdate,
    request: Request,
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> DocumentOut:
    """Edit the recorded information about a document.

    Values that describe the document (title, type, supplier, contract, dates,
    access level, revision label) are stored on the document row. Processing
    state is not editable.
    """
    document, changed = await document_service.update_document(session, principal, document_id, payload)
    if changed:
        await audit.record_principal_action(
            session,
            principal,
            action=audit.ACTION_DOCUMENT_UPDATE,
            resource_type="document",
            resource_id=document.id,
            ip_address=get_client_ip(request),
            detail={"changed": changed},
        )
    models = await _with_references(session, principal, [document])
    return models[0]


@router.get(
    "/{document_id}/versions",
    response_model=list[DocumentVersionOut],
    summary="Version history for a document",
)
async def document_versions(
    document_id: str,
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> list[DocumentVersionOut]:
    """Every version of this document that is stored, oldest first.

    The chain is read from the stored replacement links; a version that was
    replaced keeps its own pages, text and citations.
    """
    versions = await document_service.document_versions(session, principal, document_id)
    models = await _with_references(session, principal, [row for row, _ in versions])
    return [
        DocumentVersionOut(**models[index].model_dump(), is_current=is_current)
        for index, (_, is_current) in enumerate(versions)
    ]


@router.get("/{document_id}/pages/{page_number}", response_model=PageOut, summary="Single page content and tables")
async def get_page(
    document_id: str,
    page_number: int,
    session: AsyncSession = Depends(get_db),
    container: Container = Depends(container_dep),
    principal: Principal = Depends(get_principal),
) -> PageOut:
    return await document_service.page_content(session, container, principal, document_id, page_number)


@router.get(
    "/{document_id}/chunks",
    response_model=PageSchema[ChunkOut],
    summary="Chunks for a document (page-level evidence view)",
)
async def get_chunks(
    document_id: str,
    page: int | None = Query(default=None),
    content_type: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> PageSchema[ChunkOut]:
    chunks, total = await document_service.document_chunks(
        session, principal, document_id, page=page, content_type=content_type, limit=limit, offset=offset
    )
    return PageSchema[ChunkOut](
        items=chunks, total=total, limit=limit, offset=offset, has_more=offset + len(chunks) < total
    )


@router.post(
    "/{document_id}/index",
    response_model=IngestionJobOut,
    summary="Re-queue ingestion for a document",
)
async def reindex_document(
    document_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> IngestionJobOut:
    job = await document_service.requeue_document(session, principal, document_id)
    await audit.record_principal_action(
        session,
        principal,
        action=audit.ACTION_DOCUMENT_REINDEX,
        resource_type="document",
        resource_id=document_id,
        ip_address=get_client_ip(request),
    )
    return IngestionJobOut.model_validate(job)


@router.delete("/{document_id}", status_code=204, summary="Delete a document and everything derived from it")
async def delete_document(
    document_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
    container: Container = Depends(container_dep),
    principal: Principal = Depends(get_principal),
) -> Response:
    principal.require(PERM_DOCUMENTS_DELETE)
    await document_service.delete_document(session, container, principal, document_id)
    await audit.record_principal_action(
        session,
        principal,
        action=audit.ACTION_DOCUMENT_DELETE,
        resource_type="document",
        resource_id=document_id,
        ip_address=get_client_ip(request),
    )
    return Response(status_code=204)


@router.get(
    "/{document_id}/pages/{page_number}/image",
    summary="Rendered page image (PNG)",
    response_class=Response,
)
async def page_image(
    document_id: str,
    page_number: int,
    session: AsyncSession = Depends(get_db),
    container: Container = Depends(container_dep),
    principal: Principal = Depends(get_principal),
) -> Response:
    """Serve the stored page image.

    Authorization is enforced here (the storage key is never exposed to the
    client), so a page image can only be fetched for a document the caller may
    read.
    """
    from app.db.models import DocumentPage
    from sqlalchemy import select

    document = await document_service.get_document(session, principal, document_id)
    page = (
        await session.execute(
            select(DocumentPage).where(
                DocumentPage.document_id == document.id, DocumentPage.page_number == page_number
            )
        )
    ).scalar_one_or_none()
    if page is None or not page.image_key:
        raise NotFoundError("No rendered image is stored for this page.")
    data = await container.storage.get(page.image_key)
    return Response(content=data, media_type="image/png", headers={"Cache-Control": "private, max-age=300"})


__all__ = ["FileValidationError", "FileResponse", "router"]
