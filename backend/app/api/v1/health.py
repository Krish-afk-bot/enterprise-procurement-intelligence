"""Health / readiness / capability endpoints.

These report the *actual* status of every provider. When something is not
configured the response says so; it never invents data.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.api.deps import container_dep
from app.config.container import Container
from app.config.settings import Settings, get_settings
from app.db.session import get_db
from app.schemas.common import HealthResponse, ProviderStatusOut, ReadyResponse

router = APIRouter(tags=["system"])

REQUIRED_KINDS = {"vector", "graph", "cache", "storage", "embedding"}


@router.get("/health", response_model=HealthResponse, summary="Application and provider health")
async def health(
    container: Container = Depends(container_dep),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_db),
) -> HealthResponse:
    statuses = await container.provider_statuses()
    database_ok = True
    try:
        await session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        database_ok = False

    degraded = (not database_ok) or any(
        not status.available for name, status in statuses.items() if name in REQUIRED_KINDS
    )
    capabilities = {
        "database": database_ok,
        "vector_search": statuses.get("vector", None).available if statuses.get("vector") else False,
        "keyword_search": statuses.get("sparse", None).available if statuses.get("sparse") else False,
        "graph_traversal": statuses.get("graph", None).available if statuses.get("graph") else False,
        "embeddings": statuses.get("embedding", None).available if statuses.get("embedding") else False,
        "reranking": statuses.get("reranker", None).available if statuses.get("reranker") else False,
        "llm_generation": settings.llm_configured,
        "vision_generation": settings.vlm_configured,
        "ocr": settings.ocr_enabled,
        "structured_sql": database_ok,
        "evaluation": True,
    }
    return HealthResponse(
        status="degraded" if degraded else "ok",
        app_env=settings.app_env,
        version=__version__,
        degraded=degraded,
        providers={name: ProviderStatusOut(**status.model_dump()) for name, status in statuses.items()},
        fallbacks=container.fallbacks,
        capabilities=capabilities,
        details={
            "database_url_scheme": settings.database_url.split(":", 1)[0],
            "document_count_note": "counts are reported by /api/v1/admin/stats",
        },
    )


@router.get("/ready", response_model=ReadyResponse, summary="Whether the service can serve traffic")
async def ready(
    container: Container = Depends(container_dep),
    session: AsyncSession = Depends(get_db),
) -> ReadyResponse:
    blocking: list[str] = []
    try:
        await session.execute(text("SELECT 1"))
        database = True
    except Exception:  # noqa: BLE001
        database = False
        blocking.append("database")

    statuses = await container.provider_statuses()
    for kind in ("vector", "embedding"):
        status = statuses.get(kind)
        if status is None or not status.available:
            blocking.append(kind)
    return ReadyResponse(ready=not blocking, database=database, blocking=blocking)
