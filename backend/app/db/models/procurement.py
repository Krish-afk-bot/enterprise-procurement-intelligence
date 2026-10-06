"""Structured procurement domain: suppliers, contracts, products, prices, compliance."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.ids import new_id
from app.db.base import Base, ProvenanceMixin, TenantScopedMixin, TimestampMixin

CONTRACT_STATUSES = ("draft", "active", "expired", "terminated", "superseded", "unknown")


class Supplier(Base, TenantScopedMixin, TimestampMixin, ProvenanceMixin):
    __tablename__ = "suppliers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("sup"))
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True, default="")
    category: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    country: Mapped[str | None] = mapped_column(String(128), nullable=True)
    region: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(64), default="active", nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attributes: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)

    contracts: Mapped[list[Contract]] = relationship(back_populates="supplier")


class Contract(Base, TenantScopedMixin, TimestampMixin, ProvenanceMixin):
    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("ctr"))
    supplier_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    contract_number: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    contract_type: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    total_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(64), default="unknown", nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    superseded_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("contracts.id", ondelete="SET NULL"), nullable=True
    )
    parent_contract_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("contracts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)

    supplier: Mapped[Supplier | None] = relationship(back_populates="contracts")


class Product(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("prd"))
    sku: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    unit: Mapped[str] = mapped_column(String(32), default="unit", nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attributes: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)


class Price(Base, TenantScopedMixin, TimestampMixin, ProvenanceMixin):
    """A negotiated price. Rows are versioned: never overwrite, supersede."""

    __tablename__ = "prices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("prc"))
    #: Nullable on purpose: an amendment or price sheet often names the contract
    #: but not the supplier. The row is stored immediately and attributed by
    #: ``services.reconciliation`` as soon as the supplier becomes known, so
    #: ingestion is order-independent and nothing is dropped.
    supplier_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    contract_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("contracts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    product_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    minimum_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discount_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivery_terms: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line_total: Mapped[float | None] = mapped_column(Float, nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    superseded_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("prices.id", ondelete="SET NULL"), nullable=True
    )
    amendment_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_document_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_table_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ComplianceCertificate(Base, TenantScopedMixin, TimestampMixin, ProvenanceMixin):
    __tablename__ = "compliance_certificates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("cmp"))
    supplier_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    certificate_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    certificate_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    issued_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(64), default="unknown", nullable=False)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_document_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ProcurementRecord(Base, TenantScopedMixin, TimestampMixin, ProvenanceMixin):
    """Award / purchase line from an external structured procurement dataset."""

    __tablename__ = "procurement_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("rec"))
    buyer: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    supplier_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    contract_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    award_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    region: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    raw: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class DataSourceRecord(Base, TenantScopedMixin, TimestampMixin):
    """Registry of configured external data sources (never holds secrets)."""

    __tablename__ = "data_sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("src"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)  # documents | structured
    adapter: Mapped[str] = mapped_column(String(128), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    license: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    records_imported: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
