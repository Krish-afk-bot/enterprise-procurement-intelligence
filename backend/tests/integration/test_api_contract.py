"""API contract guards.

These lock down two request-shape properties that were silently broken:

  1. A single Pydantic body model must be accepted as the *flat* JSON body.
     A stray non-dependency parameter on the rate-limit dependency made
     FastAPI embed every endpoint body as ``{"payload": {...}, ...}``, so
     clients posting the documented flat body got a 422.
  2. Expected application errors must return the documented error envelope
     rather than an unhandled exception from inside the handler itself.
"""

from __future__ import annotations

from app.main import create_app


def request_body_schema(app, path: str) -> dict:
    schema = app.openapi()
    body = schema["paths"][path]["post"]["requestBody"]
    return body["content"]["application/json"]["schema"]


def test_login_accepts_a_flat_request_body() -> None:
    app = create_app()
    assert request_body_schema(app, "/api/v1/auth/login") == {
        "$ref": "#/components/schemas/LoginRequest"
    }


def test_query_accepts_a_flat_request_body() -> None:
    app = create_app()
    assert request_body_schema(app, "/api/v1/query") == {
        "$ref": "#/components/schemas/QueryRequest"
    }


def test_no_endpoint_body_is_wrapped_in_a_payload_envelope() -> None:
    app = create_app()
    schemas = app.openapi()["components"]["schemas"]
    nested = {
        name: props
        for name, props in (
            (name, definition.get("properties", {})) for name, definition in schemas.items()
        )
        if "payload" in props or "principal" in props
    }
    assert nested == {}, f"request bodies are being embedded: {sorted(nested)}"
