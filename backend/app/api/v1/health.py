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
    # GAP-1: Bound health checks to prevent hangs on slow providers
    import asyncio

    database_ok = True
    try:
        await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=5.0)
    except (TimeoutError, Exception):  # noqa: BLE001
        database_ok = False

    try:
        statuses = await asyncio.wait_for(container.provider_statuses(), timeout=5.0)
    except TimeoutError:
        # If provider checks timeout, return minimal degraded response
        return HealthResponse(
            status="degraded",
            app_env=settings.app_env,
            version=__version__,
            degraded=True,
            providers={},
            fallbacks={},
            capabilities={
                "database": database_ok,
                "vector_search": False,
                "keyword_search": False,
                "graph_traversal": False,
                "embeddings": False,
                "reranking": False,
                "llm_generation": False,
                "vision_generation": False,
                "ocr": False,
                "structured_sql": database_ok,
                "evaluation": False,
            },
            details={"error": "provider status checks timed out after 5 seconds"},
        )

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
    # GAP-1: Bound readiness checks with stricter timeout (3s)
    import asyncio

    blocking: list[str] = []
    try:
        await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=3.0)
        database = True
    except (TimeoutError, Exception):  # noqa: BLE001
        database = False
        blocking.append("database")

    try:
        statuses = await asyncio.wait_for(container.provider_statuses(), timeout=3.0)
    except TimeoutError:
        # If provider checks timeout, assume all critical providers down
        return ReadyResponse(ready=False, database=database, blocking=["vector", "embedding", "timeout"])

    for kind in ("vector", "embedding"):
        status = statuses.get(kind)
        if status is None or not status.available:
            blocking.append(kind)
    return ReadyResponse(ready=not blocking, database=database, blocking=blocking)
