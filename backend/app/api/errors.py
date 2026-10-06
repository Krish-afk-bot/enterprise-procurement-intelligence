"""Exception handlers: one error envelope, no stack traces to clients."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import AppError, RateLimitError
from app.observability.logging import get_logger, request_id_var

logger = get_logger(__name__)


def error_body(
    code: str, message: str, *, request_id: str | None = None, details: dict | None = None
) -> dict:
    payload: dict = {"code": code, "message": message, "request_id": request_id}
    if details:
        payload["details"] = details
    return {"error": payload}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_request: Request, exc: AppError) -> JSONResponse:
        headers = {}
        if isinstance(exc, RateLimitError) and exc.details.get("retry_after"):
            headers["Retry-After"] = str(exc.details["retry_after"])
        logger.info("app_error", code=exc.code, message=exc.message, details=exc.details)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.code, exc.message, request_id=request_id_var.get(), details=exc.details),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_body(
                "VALIDATION_ERROR",
                "The request payload is invalid.",
                request_id=request_id_var.get(),
                details={"errors": _safe_errors(exc.errors())},
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {
            401: "UNAUTHENTICATED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            429: "RATE_LIMITED",
        }.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(code, str(exc.detail), request_id=request_id_var.get()),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_exception", error_type=type(exc).__name__, error=str(exc), exc_info=True)
        return JSONResponse(
            status_code=500,
            content=error_body(
                "INTERNAL_ERROR",
                "An unexpected error occurred. The failure has been logged with this request id.",
                request_id=request_id_var.get(),
            ),
        )


def _safe_errors(errors: list[dict]) -> list[dict]:
    """Strip non-serialisable values (e.g. ValueError objects) from pydantic errors."""
    cleaned = []
    for error in errors:
        entry = {k: v for k, v in error.items() if k in {"type", "loc", "msg"}}
        entry["loc"] = [str(part) for part in entry.get("loc", [])]
        cleaned.append(entry)
    return cleaned
