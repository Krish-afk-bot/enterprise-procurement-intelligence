"""Admin / observability schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import APIModel


class AccessModelOut(APIModel):
    """The access model this deployment enforces.

    Read straight from the authorization policy the API applies on every request,
    so an administrator can see what each role may do without reading code.
    """

    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    role_permissions: dict[str, list[str]] = Field(default_factory=dict)
    role_access_ceiling: dict[str, str] = Field(default_factory=dict)
    access_levels: list[str] = Field(default_factory=list)
    note: str = ""


class ModelConfigOut(APIModel):
    """Model/engine configuration — never contains secrets."""

    llm_provider: str
    llm_model: str | None = None
    llm_configured: bool = False
    llm_base_url_host: str | None = None
    small_llm_model: str | None = None
    vlm_model: str | None = None
    vlm_configured: bool = False
    embedding_provider: str
    embedding_model: str
    embedding_device: str | None = None
    reranker_provider: str
    reranker_model: str | None = None
    reranker_enabled: bool = True
    ocr_enabled: bool = True
    vision_escalation_enabled: bool = True
    max_agent_iterations: int = 2
    notes: list[str] = Field(default_factory=list)


class RoutingRowOut(APIModel):
    task: str
    engine: str
    model: str | None = None
    reason: str = ""


class DataSourceOut(APIModel):
    id: str
    name: str
    kind: str
    adapter: str
    enabled: bool = False
    license: str | None = None
    source_url: str | None = None
    last_sync_at: datetime | None = None
    last_sync_status: str | None = None
    records_imported: int = 0
    config: dict[str, Any] = Field(default_factory=dict)


class DataSourceCreate(APIModel):
    name: str
    kind: str
    adapter: str
    license: str | None = None
    source_url: str | None = None
    enabled: bool = False
    config: dict[str, Any] = Field(default_factory=dict)


class AuditEntryOut(APIModel):
    id: str
    action: str
    user_id: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    outcome: str = "success"
    request_id: str | None = None
    ip_address: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class TraceEventOut(APIModel):
    ts: float | None = None
    node: str
    event: str
    detail: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    latency_ms: int | None = None


class TraceOut(APIModel):
    id: str
    query_id: str | None = None
    user_id: str | None = None
    duration_ms: int | None = None
    iterations: int = 0
    events: list[TraceEventOut] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    errors: list[Any] = Field(default_factory=list)
    created_at: datetime | None = None


class JobOut(APIModel):
    id: str
    document_id: str
    status: str
    stage: str | None = None
    progress: float = 0.0
    attempts: int = 0
    error_message: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class IndexingSummaryOut(APIModel):
    queued: int = 0
    running: int = 0
    succeeded: int = 0
    failed: int = 0
    worker_active: bool = False
    notes: list[str] = Field(default_factory=list)
    recent_jobs: list[JobOut] = Field(default_factory=list)


class SystemHealthOut(APIModel):
    status: str
    database: bool = False
    providers: dict[str, dict[str, Any]] = Field(default_factory=dict)
    fallbacks: list[dict[str, Any]] = Field(default_factory=list)
    capabilities: dict[str, bool] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    logs_note: str = ""
