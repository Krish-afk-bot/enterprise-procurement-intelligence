"""FastAPI application entrypoint."""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.errors import register_exception_handlers
from app.api.v1 import api_router
from app.config.container import get_container
from app.config.settings import Settings, get_settings
from app.db.session import assert_schema_current, dispose_engine, init_db, session_scope
from app.observability.logging import configure_logging, get_logger, request_id_var
from app.observability.tracing import configure_tracing
from app.services.auth import bootstrap_admin
from app.workers.ingestion_worker import IngestionWorker

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    configure_tracing(settings)
    logger.info("startup", app_env=settings.app_env, version=__version__)

    # Fail fast if a non-development environment has an insecure JWT secret.
    settings.validate_startup_security()
    if settings.is_development and settings.is_jwt_secret_weak():
        logger.warning(
            "insecure_jwt_secret",
            message=(
                "JWT_SECRET is set to a known-weak default. "
                "This is only acceptable for local development. "
                "Set a strong secret before deploying."
            ),
        )

    if settings.auto_create_schema:
        await init_db()
    elif settings.app_env not in {"development", "test"}:
        # Production/staging never create tables; fail loudly here rather than
        # on the first request if `alembic upgrade head` was not run.
        await assert_schema_current()
    container = get_container()
    await container.startup()

    async with session_scope() as session:
        try:
            admin = await bootstrap_admin(session, settings)
            if admin is not None:
                logger.info("bootstrap_admin_ready", user_id=admin.id, email=admin.email)
        except Exception as exc:  # noqa: BLE001
            logger.error("bootstrap_failed", error=str(exc))

    # Exactly one process owns the ingestion loops. ``embedded`` keeps the
    # developmental single-process setup; ``external`` hands them to
    # ``python -m app.workers.ingestion_worker`` so the API and the worker do
    # not both poll (and starve) the same queue.
    worker: IngestionWorker | None = None
    if settings.worker_mode == "embedded":
        worker = IngestionWorker(settings, container)
        app.state.worker = worker
        await worker.start()
    else:
        app.state.worker = None
        logger.info("ingestion_worker_not_started", worker_mode=settings.worker_mode)

    try:
        yield
    finally:
        if worker is not None:
            await worker.stop()
        await container.shutdown()
        await dispose_engine()
        logger.info("shutdown_complete")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Multimodal, agentic and graph-enhanced RAG platform for enterprise procurement "
            "intelligence. Answers are grounded in enterprise documents and structured data and "
            "carry page-level citations."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-request-id", "x-response-time-ms"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            request_id_var.reset(token)
            raise
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        response.headers["x-request-id"] = request_id
        response.headers["x-response-time-ms"] = str(elapsed_ms)
        request_id_var.reset(token)
        return response

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/", include_in_schema=False)
    async def root() -> JSONResponse:
        return JSONResponse(
            {
                "name": settings.app_name,
                "version": __version__,
                "docs": "/docs",
                "health": f"{settings.api_prefix}/health",
            }
        )

    return app


app = create_app()
