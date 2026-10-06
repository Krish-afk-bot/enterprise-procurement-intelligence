"""LangGraph orchestration (PRD s.30-31).

    START → understand → plan → structured → graph → retrieve → vision
          → evaluate ─┬─ insufficient → rewrite → retrieve (bounded)
                      └─ sufficient  → generate → verify → finalize → END

The corrective loop is capped by ``MAX_AGENT_ITERATIONS`` so an unanswerable
question can never spin.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.nodes import AgentRuntime
from app.agents.state import AgentState
from app.observability.logging import get_logger

logger = get_logger(__name__)


def route_after_evaluation(state: AgentState) -> str:
    if state.get("evidence_sufficient"):
        return "generate"
    iterations = int(state.get("iteration") or 0)
    max_iterations = int(state.get("max_iterations") or 2)
    if iterations < max_iterations:
        return "rewrite"
    state["events"] = [
        *(state.get("events") or []),
        {
            "node": "evaluate",
            "event": "Corrective retrieval stopped",
            "detail": f"reached the configured iteration limit ({max_iterations})",
            "data": {"max_iterations": max_iterations},
        },
    ]
    return "generate"


def build_agent_graph(runtime: AgentRuntime, session: AsyncSession) -> Any:
    """Compile the LangGraph state machine bound to a database session."""
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("langgraph is required to run the agent") from exc

    async def understand(state: AgentState) -> AgentState:
        return await runtime.understand(state, session)

    async def plan(state: AgentState) -> AgentState:
        return await runtime.plan(state)

    async def structured(state: AgentState) -> AgentState:
        return await runtime.structured(state, session)

    async def graph_lookup(state: AgentState) -> AgentState:
        return await runtime.graph(state, session)

    async def retrieve(state: AgentState) -> AgentState:
        return await runtime.retrieve(state, session)

    async def vision(state: AgentState) -> AgentState:
        return await runtime.vision(state, session)

    async def evaluate(state: AgentState) -> AgentState:
        return await runtime.evaluate_evidence(state)

    async def rewrite(state: AgentState) -> AgentState:
        return await runtime.rewrite_query(state)

    async def generate(state: AgentState) -> AgentState:
        return await runtime.generate(state, session)

    async def verify(state: AgentState) -> AgentState:
        return await runtime.verify(state)

    async def finalize(state: AgentState) -> AgentState:
        return await runtime.finalize(state)

    builder = StateGraph(AgentState)
    builder.add_node("understand", understand)
    builder.add_node("plan", plan)
    builder.add_node("structured", structured)
    builder.add_node("graph", graph_lookup)
    builder.add_node("retrieve", retrieve)
    builder.add_node("vision", vision)
    builder.add_node("evaluate", evaluate)
    builder.add_node("rewrite", rewrite)
    builder.add_node("generate", generate)
    builder.add_node("verify", verify)
    builder.add_node("finalize", finalize)

    builder.add_edge(START, "understand")
    builder.add_edge("understand", "plan")
    builder.add_edge("plan", "structured")
    builder.add_edge("structured", "graph")
    builder.add_edge("graph", "retrieve")
    builder.add_edge("retrieve", "vision")
    builder.add_edge("vision", "evaluate")
    builder.add_conditional_edges(
        "evaluate", route_after_evaluation, {"rewrite": "rewrite", "generate": "generate"}
    )
    builder.add_edge("rewrite", "retrieve")
    builder.add_edge("generate", "verify")
    builder.add_edge("verify", "finalize")
    builder.add_edge("finalize", END)
    return builder.compile()


def graph_diagram() -> str:
    """Text rendering of the pipeline, used in docs and the Admin UI."""
    return (
        "START → understand → plan → structured → graph → retrieve → vision → evaluate "
        "→ (rewrite → retrieve)* → generate → verify → finalize → END"
    )
