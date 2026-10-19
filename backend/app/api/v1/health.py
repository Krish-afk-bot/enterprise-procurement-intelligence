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
    # Phase 7.3B: Improved timeout handling with proper cancellation and resource cleanup
    import asyncio

    from app.observability.logging import get_logger

    logger = get_logger(__name__)

    database_ok = True
    db_error = None
    try:
        await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=5.0)
    except TimeoutError:
        database_ok = False
        db_error = "timeout"
        logger.warning("health_check_database_timeout", timeout_seconds=5.0)
        # Rollback to clean up timed-out transaction
        try:
            await session.rollback()
        except Exception as rollback_exc:  # noqa: BLE001
            logger.warning("health_check_rollback_failed", error=str(rollback_exc))
    except Exception as exc:  # noqa: BLE001
        database_ok = False
        db_error = type(exc).__name__
        logger.warning("health_check_database_error", error=type(exc).__name__)

    # Check providers independently with per-provider timeout to prevent one hanging provider
    # from blocking all checks
    statuses = {}
    provider_timeout = False
    try:
        # Get all providers to check
        provider_tasks = {}
        for kind, provider in container._providers.items():
            async def check_provider(p=provider, k=kind):
                try:
                    return k, await asyncio.wait_for(p.status(), timeout=3.0)
                except TimeoutError:
                    logger.warning("health_check_provider_timeout", provider=k, timeout_seconds=3.0)
                    from app.providers.types import ProviderStatus
                    return k, ProviderStatus.of(k, getattr(p, "name", "unknown"), False, detail="timeout")
                except Exception as exc:  # noqa: BLE001
                    logger.warning("health_check_provider_error", provider=k, error=type(exc).__name__)
                    from app.providers.types import ProviderStatus
                    return k, ProviderStatus.of(k, getattr(p, "name", "unknown"), False, detail=str(exc))
            
            provider_tasks[kind] = asyncio.create_task(check_provider())
        
        # Wait for all with overall timeout
        done, pending = await asyncio.wait(provider_tasks.values(), timeout=5.0)
        
        # Collect results from completed tasks
        for task in done:
            try:
                kind, status = await task
                statuses[kind] = status
            except Exception as exc:  # noqa: BLE001
                logger.warning("health_check_provider_task_failed", error=str(exc))
        
        # Cancel any still-pending tasks
        for task in pending:
            task.cancel()
            provider_timeout = True
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:  # noqa: BLE001
                pass
                
    except Exception as exc:  # noqa: BLE001
        logger.error("health_check_provider_check_failed", error=str(exc))
        provider_timeout = True

    if provider_timeout and not statuses:
        # All provider checks timed out
        return HealthResponse(
            status="degraded",
            app_env=settings.app_env,
            version=__version__,
            degraded=True,
            providers={},
            fallbacks=[],  # Phase 7.3C FIX: Must be list, not dict
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
            details={"error": "provider status checks timed out", "database_error": db_error},
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
            "database_error": db_error,  # Phase 7.3C FIX: Include database error info
        },
    )


@router.get("/ready", response_model=ReadyResponse, summary="Whether the service can serve traffic")
async def ready(
    container: Container = Depends(container_dep),
    session: AsyncSession = Depends(get_db),
) -> ReadyResponse:
    # Phase 7.3B: Improved timeout handling with proper cancellation
    import asyncio

    from app.observability.logging import get_logger

    logger = get_logger(__name__)

    blocking: list[str] = []
    try:
        await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=3.0)
        database = True
    except TimeoutError:
        database = False
        blocking.append("database")
        logger.warning("readiness_check_database_timeout", timeout_seconds=3.0)
        try:
            await session.rollback()
        except Exception:  # noqa: BLE001
            pass
    except Exception as exc:  # noqa: BLE001
        database = False
        blocking.append("database")
        logger.warning("readiness_check_database_error", error=type(exc).__name__)

    # Check critical providers independently
    critical_providers = {"vector", "embedding"}
    try:
        provider_tasks = {}
        for kind in critical_providers:
            provider = container._providers.get(kind)
            if provider is None:
                blocking.append(kind)
                continue
                
            async def check_critical(p=provider, k=kind):
                try:
                    status = await asyncio.wait_for(p.status(), timeout=2.0)
                    return k, status
                except TimeoutError:
                    logger.warning("readiness_check_provider_timeout", provider=k, timeout_seconds=2.0)
                    from app.providers.types import ProviderStatus
                    return k, ProviderStatus.of(k, getattr(p, "name", "unknown"), False, detail="timeout")
                except Exception as exc:  # noqa: BLE001
                    logger.warning("readiness_check_provider_error", provider=k, error=type(exc).__name__)
                    from app.providers.types import ProviderStatus
                    return k, ProviderStatus.of(k, getattr(p, "name", "unknown"), False, detail=str(exc))
            
            provider_tasks[kind] = asyncio.create_task(check_critical())
        
        # Wait with overall timeout
        done, pending = await asyncio.wait(provider_tasks.values(), timeout=3.0)
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:  # noqa: BLE001
                pass
        
        # Check results
        for task in done:
            try:
                kind, status = await task
                if not status.available:
                    blocking.append(kind)
            except Exception:  # noqa: BLE001
                blocking.append("unknown")
                
        # Add timeout indicator if any tasks were cancelled
        if pending:
            blocking.append("timeout")
            
    except Exception as exc:  # noqa: BLE001
        logger.error("readiness_check_failed", error=str(exc))
        blocking.extend(["vector", "embedding", "error"])

    return ReadyResponse(ready=not blocking, database=database, blocking=blocking)
