"""Tracing for the agent graph.

Two independent transports, both driven by settings:

* **OpenTelemetry** — one span per LangGraph node. Every span carries the node's
  latency, the model and token counts when the node generated text, and the
  retrieval counts when the node retrieved. Spans are exported over OTLP when an
  endpoint is configured; without an exporter they are still created and
  sampled, so adding a collector needs no code change.
* **LangSmith** — when ``LANGSMITH_API_KEY`` is present and tracing is enabled,
  the standard LangChain environment variables are set before LangGraph runs, so
  the graph is traced by the library itself.
"""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from typing import Any, Iterator

from app.observability.logging import get_logger

logger = get_logger(__name__)

_CONFIGURED = False


def configure_tracing(settings: Any) -> None:
    """Install the tracer provider and LangSmith environment exactly once."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    if getattr(settings, "langsmith_tracing", False) and getattr(settings, "langsmith_api_key", None):
        # Both the current LANGSMITH_* and the older LANGCHAIN_* names are read
        # by langsmith/langgraph versions in the wild.
        for key, value in {
            "LANGSMITH_TRACING": "true",
            "LANGSMITH_API_KEY": settings.langsmith_api_key,
            "LANGSMITH_PROJECT": getattr(settings, "langsmith_project", "epi-procurement"),
            "LANGCHAIN_TRACING_V2": "true",
            "LANGCHAIN_API_KEY": settings.langsmith_api_key,
            "LANGCHAIN_PROJECT": getattr(settings, "langsmith_project", "epi-procurement"),
        }.items():
            os.environ.setdefault(key, str(value))
        logger.info("langsmith_tracing_enabled", project=settings.langsmith_project)

    if not getattr(settings, "otel_enabled", True):
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:  # pragma: no cover - observability extra not installed
        logger.warning("otel_unavailable", reason="opentelemetry-sdk is not installed")
        return

    provider = TracerProvider(
        resource=Resource.create({"service.name": getattr(settings, "otel_service_name", "epi-api")})
    )
    endpoint = getattr(settings, "otel_exporter_otlp_endpoint", None)
    if endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
            logger.info("otel_export_enabled", endpoint=endpoint)
        except ImportError:
            logger.warning(
                "otel_exporter_unavailable",
                reason="install opentelemetry-exporter-otlp-proto-http to export spans",
            )
    trace.set_tracer_provider(provider)
    logger.info("otel_tracing_enabled", service=getattr(settings, "otel_service_name", "epi-api"))


@contextmanager
def node_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[Any]:
    """Start a span for one graph node; never let tracing break the request."""
    try:
        from opentelemetry import trace

        tracer = trace.get_tracer("epi.agents")
        with tracer.start_as_current_span(name, attributes=attributes or {}) as span:
            yield span
            return
    except ImportError:  # pragma: no cover
        pass
    yield _NullSpan()


class _NullSpan:
    def set_attribute(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def record_exception(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def set_status(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def annotate_node_span(span: Any, start: float, result: dict[str, Any] | None) -> None:
    """Attach the facts an operator actually needs to the node span."""
    span.set_attribute("agent.latency_ms", round((time.perf_counter() - start) * 1000, 1))
    if not result:
        return
    timings = result.get("timings") or {}
    for key, value in timings.items():
        if isinstance(value, (int, float)):
            span.set_attribute(f"agent.{key}", value)
    retrieval = result.get("retrieval") or {}
    if retrieval.get("hits") is not None:
        span.set_attribute("retrieval.hits", len(retrieval.get("hits") or []))
        span.set_attribute("retrieval.candidates", int(retrieval.get("candidates") or 0))
    tokens = result.get("token_usage") or {}
    if tokens:
        span.set_attribute("llm.prompt_tokens", int(tokens.get("prompt_tokens") or 0))
        span.set_attribute("llm.completion_tokens", int(tokens.get("completion_tokens") or 0))
    if result.get("model"):
        span.set_attribute("llm.model", str(result["model"]))
    if result.get("status"):
        span.set_attribute("answer.status", str(result["status"]))
    if result.get("grounding"):
        grounding = result["grounding"] or {}
        span.set_attribute("grounding.supported", int(grounding.get("supported_claims") or 0))
        span.set_attribute("grounding.total", int(grounding.get("total_claims") or 0))


__all__ = ["annotate_node_span", "configure_tracing", "node_span"]
