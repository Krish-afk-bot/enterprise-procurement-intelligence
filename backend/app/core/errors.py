"""Uniform API error envelope.

Every error returned to a client uses the shape::

    {"error": {"code": ..., "message": ..., "request_id": ..., "details": {...}}}

Stack traces are never exposed; they are logged with the request id instead.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for all expected application failures."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None, *, details: dict[str, Any] | None = None) -> None:
        self.message = message or self.message
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"
    message = "The requested resource does not exist."


class DocumentNotFoundError(NotFoundError):
    code = "DOCUMENT_NOT_FOUND"
    message = "The requested document does not exist."


class ValidationError(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"
    message = "The request payload is invalid."


class AuthenticationError(AppError):
    status_code = 401
    code = "UNAUTHENTICATED"
    message = "Valid credentials are required."


class AuthorizationError(AppError):
    status_code = 403
    code = "FORBIDDEN"
    message = "You do not have permission to perform this action."


class TenantIsolationError(AuthorizationError):
    code = "TENANT_ISOLATION_VIOLATION"
    message = "The requested resource belongs to another tenant."


class RateLimitError(AppError):
    status_code = 429
    code = "RATE_LIMITED"
    message = "Too many requests. Please retry later."


class ProviderUnavailableError(AppError):
    status_code = 503
    code = "PROVIDER_UNAVAILABLE"
    message = "A required backend dependency is unavailable."


class NotConfiguredError(AppError):
    status_code = 503
    code = "NOT_CONFIGURED"
    message = "This capability is not configured."


class FileValidationError(AppError):
    status_code = 400
    code = "FILE_REJECTED"
    message = "The uploaded file was rejected."


class ToolExecutionError(AppError):
    status_code = 500
    code = "TOOL_EXECUTION_FAILED"
    message = "A retrieval tool failed to execute."


class UnsupportedQueryError(AppError):
    status_code = 400
    code = "UNSUPPORTED_QUERY"
    message = "The query could not be interpreted."
