"""Concurrent evidence gathering must merge, not overwrite, branch state."""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace

from app.agents.nodes import AgentRuntime


def _runtime() -> AgentRuntime:
    settings = SimpleNamespace(context_max_chunks=12, context_max_tokens=6000)
    return AgentRuntime(container=SimpleNamespace(router=None), settings=settings)


def _state() -> dict:
    return {
        "events": [{"node": "plan", "event": "planned"}],
        "notes": ["base note"],
        "timings": {"plan_ms": 1},
        "tenant_id": "ten",
        "user_id": "usr",
        "role": "admin",
        "question": "q",
        "plan": {},
    }


async def test_branches_run_concurrently_and_merge(monkeypatch) -> None:
    class DummySession:
        async def __aenter__(self):
            return None

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr("app.db.session.session_scope", lambda: DummySession())
    runtime = _runtime()

    async def structured(state, session):
        await asyncio.sleep(0.15)
        return {
            **state,
            "structured": {"facts": [1]},
            "conflicts": [{"kind": "price_supersession"}],
            "events": [*state["events"], {"node": "structured"}],
            "timings": {**state["timings"], "structured_ms": 150},
        }

    async def graph(state, session):
        await asyncio.sleep(0.15)
        return {
            **state,
            "graph": {"paths": [1, 2]},
            "events": [*state["events"], {"node": "graph"}],
            "timings": {**state["timings"], "graph_ms": 150},
        }

    async def retrieve(state, session):
        await asyncio.sleep(0.15)
        return {
            **state,
            "retrieval": {"hits": [1, 2, 3]},
            "events": [*state["events"], {"node": "retrieve"}],
            "timings": {**state["timings"], "retrieval_ms": 150},
        }

    runtime.structured = structured  # type: ignore[method-assign]
    runtime.graph = graph  # type: ignore[method-assign]
    runtime.retrieve = retrieve  # type: ignore[method-assign]

    started = time.perf_counter()
    merged = await runtime.evidence_parallel(_state())
    elapsed = time.perf_counter() - started

    assert elapsed < 0.35, "branches did not overlap"
    assert merged["structured"] == {"facts": [1]}
    assert merged["graph"] == {"paths": [1, 2]}
    assert merged["retrieval"] == {"hits": [1, 2, 3]}
    assert [event["node"] for event in merged["events"]] == ["plan", "structured", "graph", "retrieve"]
    assert merged["timings"]["structured_ms"] == 150
    assert merged["timings"]["graph_ms"] == 150
    assert merged["timings"]["retrieval_ms"] == 150
    assert "parallel_ms" in merged["timings"]
    assert merged["notes"] == ["base note"]
