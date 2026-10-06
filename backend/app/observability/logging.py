"""Structured JSON logging with request/query correlation ids."""

from __future__ import annotations

import contextvars
import logging
import sys
from typing import Any

import structlog

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
query_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("query_id", default=None)
tenant_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("tenant_id", default=None)
user_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("user_id", default=None)

_SENSITIVE_KEYS = {
    "password",
    "hashed_password",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "authorization",
    "jwt_secret",
    "secret",
    "neo4j_password",
    "s3_secret_key",
    "llm_api_key",
}


def _inject_context(_logger: Any, _method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    for key, var in (
        ("request_id", request_id_var),
        ("query_id", query_id_var),
        ("tenant_id", tenant_id_var),
        ("user_id", user_id_var),
    ):
        value = var.get()
        if value and key not in event_dict:
            event_dict[key] = value
    return event_dict


def redact_secrets(_logger: Any, _method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Never log credentials, even if a caller passes them by mistake."""
    for key in list(event_dict.keys()):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = "***redacted***"
    return event_dict


def configure_logging(level: str = "INFO", json_output: bool = True) -> None:
    renderer: Any = (
        structlog.processors.JSONRenderer() if json_output else structlog.dev.ConsoleRenderer(colors=False)
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _inject_context,
            redact_secrets,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level.upper())),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "epi") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
