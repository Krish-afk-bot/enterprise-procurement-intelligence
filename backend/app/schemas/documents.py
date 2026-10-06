"""Document and ingestion schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import Field

from app.schemas.common import APIModel


class DocumentOut(APIModel):
    id: str
    title: str
    filename: str
    document_type: str
    status: str
    stage: str | None = None
    progress: float = 0.0
    mime_type: str | None = None
    size_bytes: int = 0
    checksum: str = ""
    version: int = 1
    revision_label: str | None = None
    supplier_id: str | None = None
    contract_id: str | None = None
    access_level: str = "internal"
    page_count: int = 0
    chunk_count: int = 0
    table_count: int = 0
    scanned_page_count: int = 0
    ocr_applied: bool = False
    vision_applied: bool = False
    effective_date: date | None = None
    expiry_date: date | None = None
    is_synthetic: bool = False
    source: str | None = None
    source_url: str | None = None
    source_uri: str | None = None
    license: str | None = None
    original_id: str | None = None
    retrieved_at: datetime | None = None
    error_message: str | None = None
    extraction_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    #: Set on a document that has been replaced by a newer version.
    superseded_by_id: str | None = None
    #: Resolved from the workspace database so the client never has to guess a name.
    supplier_name: str | None = None
    contract_number: str | None = None


class TableOut(APIModel):
    id: str
    page_number: int
    table_index: int = 0
    caption: str | None = None
    headers: list[Any] = Field(default_factory=list)
    rows: list[Any] = Field(default_factory=list)
    coordinates: list[Any] = Field(default_factory=list)
    extraction_method: str = "text"
    complexity_score: int = 0
    markdown: str = ""
    chunk_id: str | None = None


class PageOut(APIModel):
    id: str
    page_number: int
    width: float | None = None
    height: float | None = None
    has_text_layer: bool = True
    is_scanned: bool = False
    needs_vision: bool = False
    extraction_method: str = "text"
    raw_text: str | None = None
    ocr_text: str | None = None
    vision_summary: str | None = None
    image_url: str | None = None
    char_count: int = 0
    tables: list[TableOut] = Field(default_factory=list)


class ChunkOut(APIModel):
    id: str
    document_id: str
    page_number: int | None = None
    parent_chunk_id: str | None = None
    chunk_index: int = 0
    section: str | None = None
    subsection: str | None = None
    clause: str | None = None
    content: str
    contextual_content: str | None = None
    content_type: str = "paragraph"
    token_count: int = 0
    supplier_id: str | None = None
    contract_id: str | None = None
    document_type: str | None = None
    version: int = 1
    effective_date: date | None = None
    expiry_date: date | None = None
    access_level: str = "internal"
    is_synthetic: bool = False
    table_id: str | None = None
    embedding_indexed: bool = False


class IngestionJobOut(APIModel):
    id: str
    document_id: str
    status: str
    stage: str | None = None
    progress: float = 0.0
    attempts: int = 0
    error_message: str | None = None
    stages_completed: list[Any] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    queued_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class DocumentDetailOut(DocumentOut):
    pages: list[PageOut] = Field(default_factory=list)
    job: IngestionJobOut | None = None
    chunk_type_counts: dict[str, int] = Field(default_factory=dict)
    #: Display name of the account that uploaded the file, when it still exists.
    uploaded_by_name: str | None = None


class DocumentUpdate(APIModel):
    """Editable document metadata.

    Only the fields present in the request body are changed; omitting a field
    leaves it untouched, and sending an explicit ``null`` clears it. Processing
    state (``status``/``stage``/``progress``) is deliberately not editable: it is
    reported by ingestion, not by a person.
    """

    title: str | None = Field(default=None, min_length=1, max_length=512)
    document_type: str | None = Field(default=None, max_length=64)
    supplier_id: str | None = None
    contract_id: str | None = None
    effective_date: date | None = None
    expiry_date: date | None = None
    access_level: str | None = None
    revision_label: str | None = Field(default=None, max_length=128)


class DocumentVersionOut(DocumentOut):
    """One row of a document's version history."""

    is_current: bool = False


class UploadResponse(APIModel):
    document: DocumentOut
    job: IngestionJobOut | None = None
    duplicate_of: str | None = None
    message: str = ""


class UploadSettings(APIModel):
    """Optional metadata supplied with an upload (overrides auto-detection)."""

    document_type: str | None = None
    supplier_name: str | None = None
    contract_number: str | None = None
    title: str | None = None
    version: int | None = None
    revision_label: str | None = None
    access_level: str | None = None
    effective_date: date | None = None
    expiry_date: date | None = None
    is_synthetic: bool = False
    source: str | None = None
    source_url: str | None = None
    license: str | None = None
    original_id: str | None = None
    #: Document this upload replaces. The replacement becomes the next version
    #: and the replaced row keeps pointing at it, so nothing is overwritten.
    replaces_document_id: str | None = None


class IndexRequest(APIModel):
    force: bool = False
    run_ocr: bool | None = None
    run_vision: bool | None = None
    rebuild_graph: bool = True


class UploadLimits(APIModel):
    max_upload_mb: int
    allowed_extensions: list[str]
    supported_mime_types: list[str]
