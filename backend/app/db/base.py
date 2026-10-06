"""Declarative base plus shared column mixins."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base.

    JSON documents are mapped to the portable ``JSON`` type so the same schema
    works on PostgreSQL (JSONB-compatible via the JSON type) and SQLite.
    """

    type_annotation_map = {
        dict[str, Any]: JSON,
        dict: JSON,
        list[Any]: JSON,
        list[str]: JSON,
        list[int]: JSON,
        list[float]: JSON,
    }


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class TenantScopedMixin:
    """Every tenant-owned row carries tenant_id and is filtered on it."""

    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )


class ProvenanceMixin:
    """External data provenance is mandatory (PRD s.66)."""

    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    license: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
