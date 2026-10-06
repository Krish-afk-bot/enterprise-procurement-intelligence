"""Admin and observability endpoints.

Model configuration is reported without secrets: model names, provider kinds and
whether an endpoint is configured — never keys or URLs with credentials. Routing
explains which engine handles which task class so the model router is auditable.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ContainerDep, PrincipalDep, get_client_ip
from app.config.settings import Settings, get_settings
from app.core.errors import NotFoundError
from app.db.models import (
    ACCESS_LEVELS,
    ROLES,
    AgentTrace,
    AnswerRecord,
    AuditLog,
    DataSourceRecord,
    Document,
    DocumentPage,
    EvaluationRun,
    IngestionJob,
    QueryRecord,
)
from app.db.session import get_db
from app.schemas.admin import (
    AccessModelOut,
    AuditEntryOut,
    DataSourceCreate,
    DataSourceOut,
    IndexingSummaryOut,
    JobOut,
    ModelConfigOut,
    RoutingRowOut,
    SystemHealthOut,
    TraceOut,
)
from app.schemas.common import DashboardStats, Page
from app.security import audit
from app.security.rbac import (
    ALL_PERMISSIONS,
    PERM_ADMIN_READ,
    PERM_ADMIN_WRITE,
    PERM_AUDIT_READ,
    ROLE_ACCESS_CEILING,
    ROLE_PERMISSIONS,
    Principal,
)
from app.services import procurement as procurement_service

router = APIRouter(tags=["admin"], prefix="/admin")


@router.get("/stats", response_model=DashboardStats, summary="Corpus and usage statistics")
async def stats(
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
    container=ContainerDep,
) -> DashboardStats:
    principal.require(PERM_ADMIN_READ)
    counts = await procurement_service.corpus_stats(session, principal)
    tenant_id = principal.tenant_id

    async def scalar(statement) -> int:
        return int(await session.scalar(statement) or 0)

    documents_indexed = counts["documents"]
    pending = await scalar(
        select(func.count(Document.id)).where(Document.tenant_id == tenant_id, Document.status == "queued")
    )
    failed = await scalar(
        select(func.count(Document.id)).where(Document.tenant_id == tenant_id, Document.status == "failed")
    )
    scanned = await scalar(
        select(func.count(DocumentPage.id)).where(DocumentPage.tenant_id == tenant_id, DocumentPage.is_scanned.is_(True))
    )
    synthetic_documents = await scalar(
        select(func.count(Document.id)).where(Document.tenant_id == tenant_id, Document.is_synthetic.is_(True))
    )
    queries_total = await scalar(
        select(func.count(QueryRecord.id)).where(QueryRecord.tenant_id == tenant_id)
    )
    insufficient = await scalar(
        select(func.count(AnswerRecord.id)).where(
            AnswerRecord.tenant_id == tenant_id, AnswerRecord.status == "insufficient_evidence"
        )
    )
    evaluation_runs = await scalar(
        select(func.count(EvaluationRun.id)).where(EvaluationRun.tenant_id == tenant_id)
    )
    status = await container.graph.status()
    graph_stats = status.attributes or {}

    return DashboardStats(
        documents_indexed=documents_indexed,
        documents_pending=pending,
        documents_failed=failed,
        pages=counts["pages"],
        chunks=counts["chunks"],
        chunks_embedded=counts["chunks_embedded"],
        tables=counts["tables"],
        scanned_pages=scanned,
        suppliers=counts["suppliers"],
        contracts=counts["contracts"],
        products=counts["products"],
        prices=counts["prices"],
        compliance_certificates=counts["compliance_certificates"],
        queries_total=queries_total,
        queries_insufficient_evidence=insufficient,
        evaluation_runs=evaluation_runs,
        graph_nodes=int(graph_stats.get("nodes") or 0),
        graph_edges=int(graph_stats.get("edges") or 0),
        synthetic_documents=synthetic_documents,
        breakdown=[
            {"label": "Documents", "value": counts["documents"], "detail": f"{counts['pages']} page record(s)"},
            {"label": "Chunks", "value": counts["chunks"], "detail": f"{counts['chunks_embedded']} embedded"},
            {"label": "Tables", "value": counts["tables"], "detail": "extracted table records"},
            {"label": "Prices", "value": counts["prices"], "detail": "negotiated price rows"},
            {
                "label": "Procurement records",
                "value": counts["procurement_records"],
                "detail": "structured award/PO rows",
            },
        ],
        notes=[
            "Counts are read from the database for this tenant only.",
            "Graph node/edge counts come from the active graph provider.",
        ],
    )


@router.get(
    "/access-model",
    response_model=AccessModelOut,
    summary="Roles, permissions and document access ceilings",
)
async def access_model(principal: Principal = PrincipalDep) -> AccessModelOut:
    """What each role in this deployment may do, read from the enforced policy."""
    principal.require(PERM_ADMIN_READ)
    return AccessModelOut(
        roles=list(ROLES),
        permissions=sorted(ALL_PERMISSIONS),
        role_permissions={role: sorted(permissions) for role, permissions in ROLE_PERMISSIONS.items()},
        role_access_ceiling=dict(ROLE_ACCESS_CEILING),
        access_levels=list(ACCESS_LEVELS),
        note=(
            "Permissions are enforced by the API on every request. Hiding a control in the interface "
            "never grants or denies access; the document access ceiling limits which documents a role "
            "can read, and per-document ACL grants can widen that for one account."
        ),
    )


@router.get("/config", response_model=ModelConfigOut, summary="Model and engine configuration (no secrets)")
async def model_config(
    settings: Settings = Depends(get_settings),
    principal: Principal = PrincipalDep,
    container=ContainerDep,
) -> ModelConfigOut:
    principal.require(PERM_ADMIN_READ)
    from urllib.parse import urlparse

    host = None
    if settings.llm_base_url:
        try:
            host = urlparse(settings.llm_base_url).netloc or None
        except ValueError:
            host = None
    notes: list[str] = []
    if not settings.llm_configured:
        notes.append(
            "No language model endpoint is configured (LLM_BASE_URL/LLM_API_KEY). Answers are composed "
            "extractively from evidence and every answer is labelled as degraded."
        )
    if not settings.vlm_configured:
        notes.append(
            "No vision model endpoint is configured (VLM_BASE_URL/VLM_MODEL). Layout-sensitive pages are "
            "handled by OCR and table extraction only."
        )
    statuses = await container.provider_statuses()
    for name, status in statuses.items():
        if not status.available:
            notes.append(f"Provider '{name}' is unavailable: {status.detail}")
    return ModelConfigOut(
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
        llm_configured=settings.llm_configured,
        llm_base_url_host=host,
        small_llm_model=settings.llm_small_model,
        vlm_model=settings.vlm_model,
        vlm_configured=settings.vlm_configured,
        embedding_provider=settings.embedding_provider,
        embedding_model=settings.embedding_model,
        embedding_device=None if settings.embedding_device == "auto" else settings.embedding_device,
        reranker_provider=settings.reranker_provider,
        reranker_model=settings.reranker_model,
        reranker_enabled=settings.reranker_enabled,
        ocr_enabled=settings.ocr_enabled,
        vision_escalation_enabled=settings.vision_escalation_enabled,
        max_agent_iterations=settings.max_agent_iterations,
        notes=notes,
    )


@router.get("/routing", response_model=list[RoutingRowOut], summary="Which engine handles which task")
async def routing(
    settings: Settings = Depends(get_settings),
    principal: Principal = PrincipalDep,
    container=ContainerDep,
) -> list[RoutingRowOut]:
    principal.require(PERM_ADMIN_READ)
    if container.router is None:
        return []
    return [RoutingRowOut(**row) for row in await container.router.routing_table()]


@router.get("/health", response_model=SystemHealthOut, summary="System health for operators")
async def system_health(
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
    container=ContainerDep,
    settings: Settings = Depends(get_settings),
) -> SystemHealthOut:
    principal.require(PERM_ADMIN_READ)
    from sqlalchemy import text

    try:
        await session.execute(text("SELECT 1"))
        database = True
    except Exception:  # noqa: BLE001
        database = False
    statuses = await container.provider_statuses()
    return SystemHealthOut(
        status="ok" if database else "degraded",
        database=database,
        providers={name: status.model_dump() for name, status in statuses.items()},
        fallbacks=container.fallbacks,
        capabilities={
            "llm_configured": settings.llm_configured,
            "vlm_configured": settings.vlm_configured,
            "ocr_enabled": settings.ocr_enabled,
            "reranker_enabled": settings.reranker_enabled,
        },
        metrics={},
        logs_note="Structured logs are written to stdout with a request id; query ids are attached to answer records.",
    )


@router.get("/datasources", response_model=Page[DataSourceOut], summary="Registered data source adapters")
async def list_datasources(
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
) -> Page[DataSourceOut]:
    principal.require(PERM_ADMIN_READ)
    statement = select(DataSourceRecord).where(DataSourceRecord.tenant_id == principal.tenant_id)
    total = int(await session.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = list(
        (await session.execute(statement.order_by(DataSourceRecord.name).offset(offset).limit(limit))).scalars()
    )
    items = [
        DataSourceOut(
            id=row.id,
            name=row.name,
            kind=row.kind,
            adapter=row.adapter,
            enabled=row.enabled,
            license=row.license,
            source_url=row.source_url,
            last_sync_at=row.last_sync_at,
            last_sync_status=row.last_sync_status,
            records_imported=row.records_imported or 0,
            config=row.config or {},
        )
        for row in rows
    ]
    return Page[DataSourceOut](
        items=items, total=total, limit=limit, offset=offset, has_more=offset + len(items) < total
    )


@router.post("/datasources", response_model=DataSourceOut, summary="Register a data source adapter")
async def create_datasource(
    payload: DataSourceCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
) -> DataSourceOut:
    principal.require(PERM_ADMIN_WRITE)
    record = DataSourceRecord(
        tenant_id=principal.tenant_id,
        name=payload.name,
        kind=payload.kind,
        adapter=payload.adapter,
        enabled=payload.enabled,
        license=payload.license,
        source_url=payload.source_url,
        config=payload.config,
    )
    session.add(record)
    await session.flush()
    await audit.record_principal_action(
        session,
        principal,
        action=audit.ACTION_ADMIN_CONFIG,
        resource_type="data_source",
        resource_id=record.id,
        ip_address=get_client_ip(request),
        detail={"name": payload.name, "adapter": payload.adapter},
    )
    return DataSourceOut(
        id=record.id,
        name=record.name,
        kind=record.kind,
        adapter=record.adapter,
        enabled=record.enabled,
        license=record.license,
        source_url=record.source_url,
        last_sync_at=None,
        last_sync_status=None,
        records_imported=0,
        config=record.config or {},
    )


@router.get("/audit", response_model=Page[AuditEntryOut], summary="Audit log")
async def audit_log(
    action: str | None = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
) -> Page[AuditEntryOut]:
    principal.require(PERM_AUDIT_READ)
    statement = select(AuditLog).where(AuditLog.tenant_id == principal.tenant_id)
    if action:
        statement = statement.where(AuditLog.action == action)
    total = int(await session.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = list(
        (await session.execute(statement.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit))).scalars()
    )
    items = [
        AuditEntryOut(
            id=row.id,
            action=row.action,
            user_id=row.user_id,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            outcome=row.outcome,
            request_id=row.request_id,
            ip_address=row.ip_address,
            detail=row.detail or {},
            created_at=row.created_at,
        )
        for row in rows
    ]
    return Page[AuditEntryOut](
        items=items, total=total, limit=limit, offset=offset, has_more=offset + len(items) < total
    )


@router.get("/traces", response_model=Page[TraceOut], summary="Agent traces")
async def traces(
    query_id: str | None = None,
    limit: int = 25,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
) -> Page[TraceOut]:
    principal.require(PERM_ADMIN_READ)
    statement = select(AgentTrace).where(AgentTrace.tenant_id == principal.tenant_id)
    if query_id:
        statement = statement.where(AgentTrace.query_id == query_id)
    total = int(await session.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = list(
        (await session.execute(statement.order_by(AgentTrace.created_at.desc()).offset(offset).limit(limit))).scalars()
    )
    items = [
        TraceOut(
            id=row.id,
            query_id=row.query_id,
            user_id=row.user_id,
            duration_ms=row.duration_ms,
            iterations=row.iterations or 0,
            events=row.events or [],
            metrics=row.metrics or {},
            errors=row.errors or [],
            created_at=row.created_at,
        )
        for row in rows
    ]
    return Page[TraceOut](
        items=items, total=total, limit=limit, offset=offset, has_more=offset + len(items) < total
    )


@router.get("/indexing", response_model=IndexingSummaryOut, summary="Ingestion queue summary")
async def indexing(
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
) -> IndexingSummaryOut:
    principal.require(PERM_ADMIN_READ)
    rows = list(
        (
            await session.execute(
                select(IngestionJob.status, func.count(IngestionJob.id))
                .where(IngestionJob.tenant_id == principal.tenant_id)
                .group_by(IngestionJob.status)
            )
        ).all()
    )
    counts = {status: int(count) for status, count in rows}
    recent = list(
        (
            await session.execute(
                select(IngestionJob)
                .where(IngestionJob.tenant_id == principal.tenant_id)
                .order_by(IngestionJob.created_at.desc())
                .limit(15)
            )
        ).scalars()
    )
    from app.config.settings import get_settings as _get_settings

    runtime = _get_settings()
    return IndexingSummaryOut(
        queued=counts.get("queued", 0),
        running=counts.get("running", 0),
        succeeded=counts.get("succeeded", 0),
        failed=counts.get("failed", 0),
        worker_active=True,
        notes=[
            "Ingestion runs in a background worker; uploads are queued and processed outside the request.",
            f"Worker poll interval: {runtime.worker_poll_interval_seconds}s.",
        ],
        recent_jobs=[
            JobOut(
                id=row.id,
                document_id=row.document_id,
                status=row.status,
                stage=row.stage,
                progress=row.progress or 0.0,
                attempts=row.attempts or 0,
                error_message=row.error_message,
                metrics=row.metrics or {},
            )
            for row in recent
        ],
    )


@router.get("/queries/{query_id}", summary="Query record with its answer and citations")
async def query_detail(
    query_id: str,
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
) -> dict:
    query = await session.get(QueryRecord, query_id)
    if query is None or query.tenant_id != principal.tenant_id:
        raise NotFoundError("Query not found.", details={"query_id": query_id})
    answer = (
        await session.execute(select(AnswerRecord).where(AnswerRecord.query_id == query_id))
    ).scalar_one_or_none()
    return {
        "query_id": query.id,
        "query_text": query.query_text,
        "intent": query.intent,
        "strategy": query.strategy,
        "tool_calls": query.tool_calls or [],
        "classification": query.classification or {},
        "rewritten_queries": query.rewritten_queries or [],
        "latency_ms": query.latency_ms,
        "degraded": query.degraded,
        "created_at": query.created_at,
        "answer": (
            {
                "id": answer.id,
                "status": answer.status,
                "generation_mode": answer.generation_mode,
                "model": answer.model,
                "evidence_strength": answer.evidence_strength,
                "grounding": answer.grounding or {},
                "verification": answer.verification or {},
                "retrieval_plan": answer.retrieval_plan or {},
                "answer_text": answer.answer_text,
            }
            if answer
            else None
        ),
    }
