"""Agent state passed between graph nodes.

Only safe, presentable data is stored here: the plan, retrieval statistics,
evidence, verification results and status events. No chain-of-thought is
recorded or exposed.
"""

from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    # input
    tenant_id: str
    user_id: str
    role: str
    question: str
    conversation_id: str | None
    filters: dict[str, Any]
    strategy: str | None
    top_k: int
    max_iterations: int
    debug: bool

    # plan
    plan: dict[str, Any]
    strategy_selected: str
    tool_plan: list[str]

    # retrieval artifacts
    retrieval: dict[str, Any]
    structured: dict[str, Any]
    graph: dict[str, Any]
    vision: dict[str, Any]
    conflicts: list[dict[str, Any]]

    # control
    iteration: int
    evidence_sufficient: bool
    sufficiency: dict[str, Any]
    rewrites: list[str]

    # outputs
    context: dict[str, Any]
    #: Rendered evidence blocks from the context builder, carried in a declared
    #: channel so verification can re-check citations against the real context.
    context_blocks: list[dict[str, Any]]
    prompt_version: str
    answer_text: str
    generation_mode: str
    model: str | None
    grounding: dict[str, Any]
    citation_check: dict[str, Any]
    #: Whether the evidence covers the entities and period the question named.
    coverage: dict[str, Any]
    evidence_strength: dict[str, Any]
    status: str
    citations: list[dict[str, Any]]
    validation: dict[str, Any]
    token_usage: dict[str, int]
    notes: list[str]
    errors: list[str]
    events: list[dict[str, Any]]
    timings: dict[str, int]


def add_event(
    state: AgentState, node: str, event: str, detail: str = "", **data: Any
) -> list[dict[str, Any]]:
    """Append a presentable status event (never hidden reasoning)."""
    import time

    events = list(state.get("events") or [])
    events.append(
        {
            "ts": time.time(),
            "node": node,
            "event": event,
            "detail": detail,
            "data": data or {},
        }
    )
    return events
