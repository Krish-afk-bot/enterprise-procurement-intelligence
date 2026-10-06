"""Documents, pages, tables and chunks — the page-level retrieval substrate."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.ids import new_id
from app.db.base import Base, ProvenanceMixin, TenantScopedMixin, TimestampMixin

DOCUMENT_STATUSES = (
    "uploaded",
    "queued",
    "processing",
    "indexed",
    "failed",
    "needs_review",
    "archived",
)
DOCUMENT_TYPES = (
    "contract",
    "amendment",
    "pricing_agreement",
    "pricing_schedule",
    "compliance_certificate",
    "purchase_order",
    "invoice",
    "specification",
    "tender",
    "supplier_record",
    "other",
)
CONTENT_TYPES = (
    "paragraph",
    "clause",
    "heading",
    "table",
    "table_summary",
    "list",
    "image_caption",
    "page_vision",
)


class Document(Base, TenantScopedMixin, TimestampMixin, ProvenanceMixin):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("doc"))
    supplier_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    contract_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    document_type: Mapped[str] = mapped_column(String(64), default="other", nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    filename: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False, index=True, default="")
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    revision_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    access_level: Mapped[str] = mapped_column(String(64), default="internal", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="uploaded", nullable=False, index=True)
    stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    table_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    scanned_page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ocr_applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    vision_applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    superseded_by_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    uploaded_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extraction_metadata: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)

    pages: Mapped[list[DocumentPage]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="DocumentPage.page_number"
    )
    chunks: Mapped[list[Chunk]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentPage(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "document_pages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("pg"))
    document_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    width: Mapped[float | None] = mapped_column(Float, nullable=True)
    height: Mapped[float | None] = mapped_column(Float, nullable=True)
    has_text_layer: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_scanned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    needs_vision: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    extraction_method: Mapped[str] = mapped_column(String(64), default="text", nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    layout: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    vision_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    vision_metadata: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    document: Mapped[Document] = relationship(back_populates="pages")

    @property
    def text(self) -> str:
        """Best available text for the page (OCR only fills gaps)."""
        return (self.raw_text or "").strip() or (self.ocr_text or "").strip()


class TableRecord(Base, TenantScopedMixin, TimestampMixin):
    """Tables stay structured: headers, rows, cells and coordinates are preserved."""

    __tablename__ = "document_tables"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("tbl"))
    document_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    table_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    headers: Mapped[list[Any]] = mapped_column(default=list, nullable=False)
    rows: Mapped[list[Any]] = mapped_column(default=list, nullable=False)
    coordinates: Mapped[list[Any]] = mapped_column(default=list, nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(64), default="text", nullable=False)
    complexity_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    markdown: Mapped[str] = mapped_column(Text, default="", nullable=False)
    chunk_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)


class Chunk(Base, TenantScopedMixin, TimestampMixin):
    """A retrievable unit. Hierarchy is kept via parent_chunk_id."""

    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("chk"))
    document_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    parent_chunk_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    section: Mapped[str | None] = mapped_column(String(512), nullable=True)
    subsection: Mapped[str | None] = mapped_column(String(512), nullable=True)
    clause: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    contextual_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_type: Mapped[str] = mapped_column(String(64), default="paragraph", nullable=False, index=True)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    supplier_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    contract_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    document_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    access_level: Mapped[str] = mapped_column(String(64), default="internal", nullable=False, index=True)
    region: Mapped[str | None] = mapped_column(String(128), nullable=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    table_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    embedding_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    embedding_indexed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)

    document: Mapped[Document] = relationship(back_populates="chunks")
