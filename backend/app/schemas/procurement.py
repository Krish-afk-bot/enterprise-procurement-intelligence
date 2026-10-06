"""Structured procurement schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import Field

from app.schemas.common import APIModel
from app.schemas.query import CitationOut


class SupplierOut(APIModel):
    id: str
    name: str
    normalized_name: str = ""
    category: str | None = None
    country: str | None = None
    region: str | None = None
    status: str = "active"
    contact_email: str | None = None
    is_synthetic: bool = False
    source: str | None = None
    source_url: str | None = None
    license: str | None = None
    original_id: str | None = None
    retrieved_at: datetime | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    contract_count: int = 0
    document_count: int = 0
    price_count: int = 0


class ProductOut(APIModel):
    id: str
    sku: str
    name: str
    category: str | None = None
    unit: str = "unit"
    is_synthetic: bool = False
    attributes: dict[str, Any] = Field(default_factory=dict)


class PriceOut(APIModel):
    id: str
    # A price row can be stored before its supplier or contract is reconciled
    # (a pricing schedule that names no party), so both are optional here. The
    # value is null when the row genuinely carries no supplier yet.
    supplier_id: str | None = None
    contract_id: str | None = None
    product_id: str | None = None
    product_name: str | None = None
    supplier_name: str | None = None
    unit_price: float
    currency: str = "USD"
    minimum_quantity: int | None = None
    discount_percent: float | None = None
    payment_terms: str | None = None
    delivery_terms: str | None = None
    quantity: int | None = None
    line_total: float | None = None
    effective_date: date | None = None
    expiry_date: date | None = None
    is_current: bool = True
    amendment_ref: str | None = None
    source_document_id: str | None = None
    source_page: int | None = None
    is_synthetic: bool = False


class ComplianceOut(APIModel):
    id: str
    supplier_id: str
    certificate_type: str
    certificate_number: str | None = None
    issued_date: date | None = None
    expiry_date: date | None = None
    status: str = "unknown"
    scope: str | None = None
    source_document_id: str | None = None
    source_page: int | None = None
    is_synthetic: bool = False


class ContractOut(APIModel):
    id: str
    supplier_id: str | None = None
    supplier_name: str | None = None
    contract_number: str
    title: str = ""
    contract_type: str | None = None
    category: str | None = None
    currency: str = "USD"
    total_value: float | None = None
    effective_date: date | None = None
    expiry_date: date | None = None
    status: str = "unknown"
    version: int = 1
    superseded_by_id: str | None = None
    parent_contract_id: str | None = None
    is_synthetic: bool = False
    source: str | None = None
    source_url: str | None = None
    license: str | None = None
    original_id: str | None = None
    retrieved_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    document_ids: list[str] = Field(default_factory=list)
    price_count: int = 0
    amendment_count: int = 0


class ContractVersionOut(APIModel):
    id: str
    contract_number: str
    version: int
    title: str = ""
    effective_date: date | None = None
    expiry_date: date | None = None
    status: str = "unknown"
    superseded_by_id: str | None = None
    parent_contract_id: str | None = None
    relation: str = "version"


class ContractDetailOut(ContractOut):
    prices: list[PriceOut] = Field(default_factory=list)
    documents: list[dict[str, Any]] = Field(default_factory=list)
    versions: list[ContractVersionOut] = Field(default_factory=list)
    clauses: list[dict[str, Any]] = Field(default_factory=list)
    compliance: list[ComplianceOut] = Field(default_factory=list)


class SupplierDetailOut(SupplierOut):
    contracts: list[ContractOut] = Field(default_factory=list)
    products: list[dict[str, Any]] = Field(default_factory=list)
    prices: list[PriceOut] = Field(default_factory=list)
    compliance: list[ComplianceOut] = Field(default_factory=list)
    documents: list[dict[str, Any]] = Field(default_factory=list)
    timeline: list[dict[str, Any]] = Field(default_factory=list)


class ComparisonRequest(APIModel):
    supplier_ids: list[str] = Field(default_factory=list, max_length=6)
    supplier_names: list[str] = Field(default_factory=list, max_length=6)
    product_ids: list[str] = Field(default_factory=list)
    product_query: str | None = None
    dimensions: list[str] = Field(
        default_factory=lambda: [
            "unit_price",
            "minimum_quantity",
            "payment_terms",
            "delivery_terms",
            "contract_duration",
            "compliance",
            "renewal",
            "discount_percent",
        ]
    )
    as_of: date | None = None


class ComparisonCellOut(APIModel):
    key: str
    value: Any = None
    formatted: str = ""
    source: str = "structured"
    citations: list[CitationOut] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ComparisonColumnOut(APIModel):
    supplier_id: str | None = None
    supplier_name: str
    cells: dict[str, ComparisonCellOut] = Field(default_factory=dict)


class ComparisonOut(APIModel):
    dimensions: list[str] = Field(default_factory=list)
    columns: list[ComparisonColumnOut] = Field(default_factory=list)
    product: dict[str, Any] | None = None
    generated_at: datetime | None = None
    notes: list[str] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)
