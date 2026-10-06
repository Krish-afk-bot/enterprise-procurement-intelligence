"""Shared API schemas."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class Page(APIModel, Generic[T]):
    items: list[T] = Field(default_factory=list)
    total: int = 0
    limit: int = 50
    offset: int = 0
    has_more: bool = False


class ErrorDetail(APIModel):
    code: str
    message: str
    request_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(APIModel):
    error: ErrorDetail


class ProviderStatusOut(APIModel):
    kind: str
    name: str
    available: bool
    detail: str = ""
    model: str | None = None
    is_model: bool = True
    attributes: dict[str, Any] = Field(default_factory=dict)


class FallbackNoteOut(APIModel):
    kind: str
    configured: str
    active: str
    reason: str


class HealthResponse(APIModel):
    status: str
    app_env: str
    version: str
    degraded: bool = False
    providers: dict[str, ProviderStatusOut] = Field(default_factory=dict)
    fallbacks: list[FallbackNoteOut] = Field(default_factory=list)
    capabilities: dict[str, bool] = Field(default_factory=dict)
    details: dict[str, Any] = Field(default_factory=dict)


class ReadyResponse(APIModel):
    ready: bool
    database: bool
    blocking: list[str] = Field(default_factory=list)


class CountItem(APIModel):
    label: str
    value: int
    detail: str | None = None


class DashboardStats(APIModel):
    documents_indexed: int = 0
    documents_pending: int = 0
    documents_failed: int = 0
    pages: int = 0
    chunks: int = 0
    chunks_embedded: int = 0
    tables: int = 0
    scanned_pages: int = 0
    suppliers: int = 0
    contracts: int = 0
    products: int = 0
    prices: int = 0
    compliance_certificates: int = 0
    queries_total: int = 0
    queries_insufficient_evidence: int = 0
    evaluation_runs: int = 0
    graph_nodes: int = 0
    graph_edges: int = 0
    synthetic_documents: int = 0
    breakdown: list[CountItem] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
