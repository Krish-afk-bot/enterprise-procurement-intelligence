"""One span per node must carry the numbers an operator needs."""

from __future__ import annotations

import time

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.observability.tracing import annotate_node_span, node_span


def test_node_span_records_latency_tokens_and_retrieval_counts() -> None:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    started = time.perf_counter()
    with node_span("agent.generate") as span:
        annotate_node_span(
            span,
            started,
            {
                "timings": {"generation_ms": 42},
                "retrieval": {"hits": [1, 2, 3], "candidates": 9},
                "token_usage": {"prompt_tokens": 100, "completion_tokens": 20},
                "model": "qwen2.5-coder:7b",
                "status": "supported",
                "grounding": {"supported_claims": 3, "total_claims": 3},
            },
        )

    finished = exporter.get_finished_spans()
    assert [item.name for item in finished] == ["agent.generate"]
    attributes = finished[0].attributes or {}
    assert attributes["agent.generation_ms"] == 42
    assert attributes["retrieval.hits"] == 3
    assert attributes["retrieval.candidates"] == 9
    assert attributes["llm.prompt_tokens"] == 100
    assert attributes["llm.completion_tokens"] == 20
    assert attributes["llm.model"] == "qwen2.5-coder:7b"
    assert attributes["answer.status"] == "supported"
    assert attributes["grounding.supported"] == 3
    assert attributes["agent.latency_ms"] >= 0
