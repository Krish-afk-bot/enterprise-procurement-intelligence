"""Answer pipeline.

Runs the LangGraph agent, persists the audit trail (query, answer, citations,
trace) and exposes both a one-shot ``answer()`` and an SSE ``stream()``.

Streaming emits *status events only*: which node ran, which engines were used,
how many candidates came back, whether verification passed. Hidden reasoning is
never produced, so it cannot leak.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import build_agent_graph
from app.agents.nodes import AgentRuntime
from app.config.container import Container
from app.config.settings import Settings
from app.db.models import AgentTrace, AnswerRecord, Citation as CitationModel, Conversation, Message, QueryRecord
from app.db.session import session_scope
from app.observability.logging import get_logger, query_id_var
from app.schemas.query import (
    AnswerOut,
    CitationOut,
    ConflictOut,
    EvidenceStrengthOut,
    GroundingOut,
    QueryFilters,
    RetrievalStepOut,
    retrieval_filter_payload,
)
from app.security.rbac import Principal

logger = get_logger(__name__)


class AnswerPipeline:
    def __init__(self, container: Container, settings: Settings) -> None:
        self.container = container
        self.settings = settings
        self.runtime = AgentRuntime(container, settings)

    # ------------------------------------------------------------------ input
    def _initial_state(
        self,
        principal: Principal,
        question: str,
        *,
        filters: QueryFilters | None = None,
        strategy: str | None = None,
        top_k: int | None = None,
        max_iterations: int | None = None,
        conversation_id: str | None = None,
        debug: bool = False,
    ) -> dict[str, Any]:
        filter_payload: dict[str, Any] = retrieval_filter_payload(filters) if filters is not None else {}
        return {
            "tenant_id": principal.tenant_id,
            "user_id": principal.user_id,
            "role": principal.role,
            "question": question,
            "conversation_id": conversation_id,
            "filters": filter_payload,
            "strategy": strategy,
            "top_k": top_k,
            "max_iterations": max_iterations or self.settings.max_agent_iterations,
            "debug": debug,
            "iteration": 0,
            "events": [],
            "notes": [],
            "errors": [],
        }

    # --------------------------------------------------------------- one-shot
    async def answer(
        self,
        principal: Principal,
        question: str,
        *,
        filters: QueryFilters | None = None,
        strategy: str | None = None,
        top_k: int | None = None,
        max_iterations: int | None = None,
        conversation_id: str | None = None,
        debug: bool = False,
    ) -> AnswerOut:
        started = time.perf_counter()
        state = self._initial_state(
            principal,
            question,
            filters=filters,
            strategy=strategy,
            top_k=top_k,
            max_iterations=max_iterations,
            conversation_id=conversation_id,
            debug=debug,
        )
        async with session_scope() as session:
            graph = build_agent_graph(self.runtime, session)
            final_state = await graph.ainvoke(state)
            answer = await self._persist(session, principal, final_state, started)
        return answer

    # ---------------------------------------------------------------- stream
    async def stream(
        self,
        principal: Principal,
        question: str,
        *,
        filters: QueryFilters | None = None,
        strategy: str | None = None,
        top_k: int | None = None,
        max_iterations: int | None = None,
        conversation_id: str | None = None,
        debug: bool = False,
    ) -> AsyncIterator[dict[str, Any]]:
        started = time.perf_counter()
        state = self._initial_state(
            principal,
            question,
            filters=filters,
            strategy=strategy,
            top_k=top_k,
            max_iterations=max_iterations,
            conversation_id=conversation_id,
            debug=debug,
        )
        emitted = 0
        yield {"type": "status", "event": {"node": "start", "event": "Query received", "detail": question[:200]}}
        async with session_scope() as session:
            graph = build_agent_graph(self.runtime, session)
            snapshot: dict[str, Any] = state
            try:
                async for update in graph.astream(state, stream_mode="values"):
                    snapshot = update
                    events = update.get("events") or []
                    for event in events[emitted:]:
                        yield {"type": "status", "event": event}
                    emitted = len(events)
            except Exception as exc:  # noqa: BLE001
                logger.error("agent_stream_failed", error=str(exc), exc_info=True)
                yield {
                    "type": "error",
                    "error": {"code": "AGENT_FAILED", "message": "The agent could not complete this query."},
                }
                return
            answer = await self._persist(session, principal, snapshot, started)
        yield {"type": "answer", "answer": answer.model_dump(mode="json")}

    # -------------------------------------------------------------- persisting
    async def _persist(
        self, session: AsyncSession, principal: Principal, state: dict[str, Any], started: float
    ) -> AnswerOut:
        latency_ms = int((time.perf_counter() - started) * 1000)
        plan = state.get("plan") or {}
        sufficiency = state.get("sufficiency") or {}
        structured = state.get("structured") or {}
        retrieval = state.get("retrieval") or {}

        query_record = QueryRecord(
            tenant_id=principal.tenant_id,
            user_id=principal.user_id,
            conversation_id=state.get("conversation_id"),
            query_text=state.get("question", ""),
            intent=(plan.get("intent") if isinstance(plan, dict) else None),
            classification=plan if isinstance(plan, dict) else {},
            rewritten_queries=state.get("rewrites") or [],
            strategy=state.get("strategy_selected"),
            tool_calls=state.get("tool_plan") or [],
            latency_ms=latency_ms,
            retrieval_latency_ms=(state.get("timings") or {}).get("retrieval_ms"),
            generation_latency_ms=(state.get("timings") or {}).get("generation_ms"),
            token_usage=state.get("token_usage") or {},
            degraded=state.get("generation_mode") != "llm",
            error=(state.get("errors") or [None])[0],
        )
        session.add(query_record)
        await session.flush()
        query_id_var.set(query_record.id)

        grounding = state.get("grounding") or {}
        evidence_strength = state.get("evidence_strength") or {}
        answer_record = AnswerRecord(
            tenant_id=principal.tenant_id,
            query_id=query_record.id,
            answer_text=state.get("answer_text", ""),
            status=state.get("status", "partial"),
            generation_mode=state.get("generation_mode", "extractive"),
            model=state.get("model"),
            prompt_version=state.get("prompt_version"),
            evidence_strength=evidence_strength.get("level"),
            grounding=grounding,
            conflicts=state.get("conflicts") or [],
            verification=state.get("validation") or {},
            retrieval_plan={
                "strategy": state.get("strategy_selected"),
                "tools": state.get("tool_plan") or [],
                "sufficiency": sufficiency,
                "retrieval_steps": retrieval.get("steps") or [],
                "structured": {
                    "facts": len(structured.get("facts") or []),
                    "aggregations": len(structured.get("aggregations") or []),
                },
                "graph_paths": len((state.get("graph") or {}).get("paths") or []),
                "vision_used": bool((state.get("vision") or {}).get("used")),
            },
        )
        session.add(answer_record)
        await session.flush()

        citation_models: list[CitationModel] = []
        for index, citation in enumerate(state.get("citations") or [], start=1):
            model = CitationModel(
                tenant_id=principal.tenant_id,
                answer_id=answer_record.id,
                query_id=query_record.id,
                chunk_id=citation.get("chunk_id"),
                document_id=citation.get("document_id"),
                document_name=citation.get("document_name"),
                page_number=citation.get("page"),
                section=citation.get("section"),
                clause=citation.get("clause"),
                snippet=citation.get("snippet") or "",
                source_uri=citation.get("source_uri"),
                score=citation.get("score"),
                rank=citation.get("rank") or index,
                evidence_type=citation.get("evidence_type", "document"),
                is_synthetic=citation.get("is_synthetic", False),
                verified=citation.get("verified", False),
                metadata_json=citation.get("metadata") or {},
            )
            session.add(model)
            citation_models.append(model)

        session.add(
            AgentTrace(
                tenant_id=principal.tenant_id,
                query_id=query_record.id,
                user_id=principal.user_id,
                duration_ms=latency_ms,
                iterations=int(state.get("iteration") or 0),
                events=state.get("events") or [],
                metrics={
                    "timings": state.get("timings") or {},
                    "sufficiency": sufficiency,
                    "retrieval": {
                        "candidates": retrieval.get("candidates"),
                        "hits": len(retrieval.get("hits") or []),
                        "mode": retrieval.get("mode"),
                    },
                    "generation_mode": state.get("generation_mode"),
                    "token_usage": state.get("token_usage") or {},
                },
                errors=state.get("errors") or [],
            )
        )

        if state.get("conversation_id"):
            conversation = await session.get(Conversation, state["conversation_id"])
            if conversation is not None and conversation.tenant_id == principal.tenant_id:
                session.add(
                    Message(
                        tenant_id=principal.tenant_id,
                        conversation_id=conversation.id,
                        role="user",
                        content=state.get("question", ""),
                        query_id=query_record.id,
                    )
                )
                session.add(
                    Message(
                        tenant_id=principal.tenant_id,
                        conversation_id=conversation.id,
                        role="assistant",
                        content=state.get("answer_text", ""),
                        query_id=query_record.id,
                    )
                )
                conversation.message_count = (conversation.message_count or 0) + 2

        return self._to_answer_out(
            state, query_id=query_record.id, latency_ms=latency_ms, citations=citation_models
        )

    def _to_answer_out(
        self,
        state: dict[str, Any],
        *,
        query_id: str,
        latency_ms: int,
        citations: list[CitationModel],
    ) -> AnswerOut:
        retrieval = state.get("retrieval") or {}
        structured = state.get("structured") or {}
        notes = list(dict.fromkeys(state.get("notes") or []))
        if not (state.get("generation_mode") == "llm"):
            notes.append(
                "Generation mode is 'extractive': the platform composed this answer from retrieved "
                "evidence without a language model. Configure LLM_BASE_URL/LLM_API_KEY for narrative answers."
            )
        return AnswerOut(
            query_id=query_id,
            answer_text=state.get("answer_text", ""),
            status=state.get("status", "partial"),
            generation_mode=state.get("generation_mode", "extractive"),
            model=state.get("model"),
            prompt_version=state.get("prompt_version"),
            evidence_strength=EvidenceStrengthOut(**(state.get("evidence_strength") or {})),
            grounding=GroundingOut(**(state.get("grounding") or {})),
            conflicts=[ConflictOut(**item) for item in (state.get("conflicts") or [])],
            citations=[citation_out(model) for model in citations],
            retrieval_steps=[RetrievalStepOut(**step) for step in (retrieval.get("steps") or [])],
            plan=state.get("plan") or {},
            validation=state.get("validation") or {},
            timings={**(state.get("timings") or {}), "total_ms": latency_ms},
            token_usage=state.get("token_usage") or {},
            degraded=state.get("generation_mode") != "llm",
            degradation_reasons=notes,
            notes=notes,
            trace=[event for event in (state.get("events") or [])] if state.get("debug") else [],
        )


def citation_out(model: CitationModel) -> CitationOut:
    parts = [model.document_name or "unknown source"]
    if model.page_number:
        parts.append(f"p.{model.page_number}")
    if model.section:
        parts.append(model.section[:60])
    return CitationOut(
        chunk_id=model.chunk_id,
        document_id=model.document_id,
        document_name=model.document_name,
        document_type=(model.metadata_json or {}).get("document_type"),
        page=model.page_number,
        section=model.section,
        clause=model.clause,
        snippet=model.snippet,
        source_uri=model.source_uri,
        score=model.score,
        rank=model.rank,
        evidence_type=model.evidence_type,
        is_synthetic=model.is_synthetic,
        verified=model.verified,
        # Present only when the security detector flagged instruction-like text.
        injection=(model.metadata_json or {}).get("injection"),
        label=" — ".join(parts),
    )
