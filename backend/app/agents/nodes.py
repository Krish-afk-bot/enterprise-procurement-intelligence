"""Agent graph nodes (PRD s.30-31).

    understand → plan → retrieve → evaluate ─┬─(insufficient)→ rewrite → retrieve
                                             └─(sufficient)──→ generate → verify → finalize

Every node records a status event that the UI can stream. Events describe *what
the system did* (which engines ran, how many candidates came back, whether the
answer was verified) and never expose internal reasoning.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.generation import AnswerGenerator
from app.agents.state import AgentState, add_event
from app.agents.verification import (
    REFUSAL_TEXT,
    assess_evidence_strength,
    assess_query_coverage,
    decide_status,
    extract_claims,
    judge_grounding_lexical,
    judge_grounding_llm,
    refusal_reason,
    relevant_conflicts,
    validate_citations,
)
from app.config.container import Container
from app.config.settings import Settings
from app.core.errors import AuthorizationError, NotFoundError
from app.db.models import Chunk, Document, DocumentPage
from app.observability.logging import get_logger
from app.retrieval.analysis import Conflict, detect_price_conflicts, fetch_price_facts
from app.retrieval.context import ContextBuilder
from app.retrieval.graph_retrieval import GraphResult, graph_lookup
from app.retrieval.query_understanding import (
    Intent,
    QueryPlan,
    understand_query,
    understand_query_rule_based,
)
from app.retrieval.retriever import HybridRetriever, RetrievalResult, expand_parents
from app.retrieval.structured import StructuredResult, structured_lookup
from app.security.rbac import Principal  # noqa: F401  (typing import)

logger = get_logger(__name__)

REWRITE_SUFFIXES = (
    "price list unit price per unit",
    "amendment revised price effective date",
    "clause terms conditions",
)


@dataclass(slots=True)
class NodeReport:
    """Returned by a node so the pipeline can persist timings."""

    events: list[dict[str, Any]]
    latency_ms: int


class AgentRuntime:
    """Holds the service objects the nodes need and implements each node."""

    def __init__(self, container: Container, settings: Settings) -> None:
        self.container = container
        self.settings = settings
        self.retriever = HybridRetriever(container, settings)
        self.generator = AnswerGenerator(container.router, settings)
        self.context_builder = ContextBuilder(
            max_chunks=settings.context_max_chunks, max_tokens=settings.context_max_tokens
        )

    # ------------------------------------------------------------------ setup
    def principal_from_state(self, state: AgentState) -> Principal:
        return Principal(
            user_id=state["user_id"],
            tenant_id=state["tenant_id"],
            email="",
            role=state["role"],
        )

    # ------------------------------------------------------------- understand
    async def understand(self, state: AgentState, session: AsyncSession) -> AgentState:
        import time

        started = time.perf_counter()
        principal = self.principal_from_state(state)
        plan = await understand_query(
            state["question"],
            session=session,
            tenant_id=principal.tenant_id,
            router=self.container.router,
            use_llm=self.settings.llm_configured,
        )
        question = state["question"]
        state["plan"] = plan.as_dict()
        events = add_event(
            state,
            "understand",
            "Query understood",
            f"intent={plan.intent.value}, method={plan.method}, suppliers={len(plan.suppliers)}, "
            f"products={len(plan.products)}",
            intent=plan.intent.value,
            method=plan.method,
            entities={
                "suppliers": plan.suppliers,
                "products": plan.products,
                "contracts": plan.contract_numbers,
                "year": plan.year,
            },
        )
        state["events"] = events
        state.setdefault("notes", [])
        state["notes"] = [*state.get("notes", []), *plan.notes]
        state["timings"] = {
            **(state.get("timings") or {}),
            "understand_ms": int((time.perf_counter() - started) * 1000),
        }
        state["iteration"] = state.get("iteration", 0)
        state["rewrites"] = state.get("rewrites", [])
        state["question"] = question
        return state

    # ------------------------------------------------------------------ plan
    async def plan(self, state: AgentState) -> AgentState:
        plan = QueryPlan.model_validate(state["plan"])
        strategy = state.get("strategy") or _select_strategy(plan)
        tools = ["search_documents"]
        if plan.requires_structured or plan.intent in {
            Intent.PRICE_LOOKUP,
            Intent.AGGREGATION,
            Intent.COMPARISON,
            Intent.TEMPORAL_CHANGE,
        }:
            tools.append("query_database")
        if plan.requires_graph:
            tools.append("query_graph")
        if plan.requires_vision:
            tools.append("retrieve_page")
        if plan.requires_comparison:
            tools.append("compare_suppliers")
        if plan.intent == Intent.COMPLIANCE_CHECK:
            tools.append("search_compliance")
        state["strategy_selected"] = strategy
        state["tool_plan"] = tools
        state["events"] = add_event(
            state,
            "plan",
            "Retrieval plan ready",
            f"strategy={strategy}, tools={', '.join(tools)}",
            strategy=strategy,
            tools=tools,
        )
        state["context"] = {"strategy": strategy, "tools": tools}
        return state

    # -------------------------------------------------------------- retrieval
    async def retrieve(self, state: AgentState, session: AsyncSession) -> AgentState:
        import time

        started = time.perf_counter()
        principal = self.principal_from_state(state)
        plan = QueryPlan.model_validate(state["plan"])
        strategy = state.get("strategy_selected") or "hybrid_rerank"
        mode = _mode_for_strategy(strategy)
        limit = state.get("top_k") or self.settings.rerank_top_n
        result: RetrievalResult = await self.retriever.retrieve(
            session,
            principal,
            plan,
            mode=mode,
            limit=limit,
            filters=state.get("filters") or None,
            rerank=strategy != "dense",
        )
        state["retrieval"] = {
            "mode": result.mode,
            "hits": [hit.as_dict() for hit in result.hits],
            "steps": result.step_summary(),
            "candidates": result.candidate_count,
            "notes": result.notes,
            "reranker": result.reranker,
            "embedding_model": result.embedding_model,
        }
        dense = next((step for step in result.steps if step.name == "dense_search"), None)
        sparse = next((step for step in result.steps if step.name == "sparse_search"), None)
        state["events"] = add_event(
            state,
            "retrieve",
            "Retrieved candidate evidence",
            (
                f"dense={dense.candidates if dense else 0} candidates, "
                f"BM25={sparse.candidates if sparse else 0} candidates, "
                f"{len(result.hits)} authorised after filtering"
            ),
            strategy=result.mode,
            hits=len(result.hits),
        )
        state["timings"] = {
            **(state.get("timings") or {}),
            "retrieval_ms": int((time.perf_counter() - started) * 1000),
        }
        return state

    # ------------------------------------------------------------- structured
    async def structured(self, state: AgentState, session: AsyncSession) -> AgentState:
        import time

        started = time.perf_counter()
        principal = self.principal_from_state(state)
        plan = QueryPlan.model_validate(state["plan"])
        if "query_database" not in (state.get("tool_plan") or []):
            state["structured"] = StructuredResult(queried=False, purpose=plan.intent.value).as_dict()
            return state
        result = await structured_lookup(session, principal, plan)
        state["structured"] = result.as_dict()
        conflicts = [conflict.as_dict() for conflict in result.conflicts]
        state["conflicts"] = conflicts
        detail = f"{len(result.facts)} price row(s), {len(result.aggregations)} aggregation(s)" + (
            f", {len(conflicts)} conflict(s) detected" if conflicts else ""
        )
        state["events"] = add_event(
            state, "structured", "Queried structured procurement data", detail, rows=len(result.facts)
        )
        state["timings"] = {
            **(state.get("timings") or {}),
            "structured_ms": int((time.perf_counter() - started) * 1000),
        }
        return state

    # ------------------------------------------------------------------ graph
    async def graph(self, state: AgentState, session: AsyncSession) -> AgentState:
        import time

        started = time.perf_counter()
        principal = self.principal_from_state(state)
        plan = QueryPlan.model_validate(state["plan"])
        if "query_graph" not in (state.get("tool_plan") or []):
            state["graph"] = GraphResult(traversal=False).as_dict()
            return state
        result = await graph_lookup(self.container, session, principal, plan)
        state["graph"] = result.as_dict()
        state["events"] = add_event(
            state,
            "graph",
            "Traversed the procurement knowledge graph",
            f"{len(result.paths)} path(s), up to {result.limits.get('max_hops')} hops",
            paths=len(result.paths),
        )
        state["timings"] = {
            **(state.get("timings") or {}),
            "graph_ms": int((time.perf_counter() - started) * 1000),
        }
        return state

    # ----------------------------------------------------------------- vision
    async def vision(self, state: AgentState, session: AsyncSession) -> AgentState:
        """Escalate to the VLM only for pages the retrieval step selected."""
        import time

        started = time.perf_counter()
        plan = QueryPlan.model_validate(state["plan"])
        hits = state.get("retrieval", {}).get("hits") or []
        if not state.get("plan") or not plan.requires_vision or not hits:
            state["vision"] = {"used": False, "reason": "not required"}
            return state
        if not self.settings.vlm_configured:
            state["vision"] = {
                "used": False,
                "reason": "no VLM configured; page text and tables were used instead",
            }
            state["events"] = add_event(
                state, "vision", "Visual analysis unavailable", "No VLM endpoint is configured"
            )
            return state

        page_keys = {(hit["document_id"], hit["page"]) for hit in hits[:4] if hit.get("page")}
        analyses: list[dict[str, Any]] = []
        for document_id, page_number in page_keys:
            page = (
                await session.execute(
                    select(DocumentPage).where(
                        DocumentPage.document_id == document_id, DocumentPage.page_number == page_number
                    )
                )
            ).scalar_one_or_none()
            if page is None or not page.image_key:
                continue
            try:
                image = await self.container.storage.get(page.image_key)
                response = await self.container.router.vision(  # type: ignore[union-attr]
                    image,
                    f"Extract every price, quantity, discount, date and clause number visible on page {page_number}. "
                    "Reply as short 'label: value' lines. Mark anything unreadable as 'unreadable'.",
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("vision_failed", document_id=document_id, page=page_number, error=str(exc))
                continue
            if response.mode != "vlm" or not response.text:
                continue
            analyses.append(
                {
                    "document_id": document_id,
                    "page": page_number,
                    "model": response.model,
                    "text": response.text,
                }
            )
        state["vision"] = {"used": bool(analyses), "analyses": analyses}
        if analyses:
            state["events"] = add_event(
                state, "vision", "Analysed page imagery with the vision model", f"{len(analyses)} page(s)"
            )
        state["timings"] = {
            **(state.get("timings") or {}),
            "vision_ms": int((time.perf_counter() - started) * 1000),
        }
        return state

    # ------------------------------------------------------------- evaluation
    async def evaluate_evidence(self, state: AgentState) -> AgentState:

        hits = state.get("retrieval", {}).get("hits") or []
        structured = state.get("structured") or {}
        graph = state.get("graph") or {}
        rerank_scores = [hit.get("rerank_score") for hit in hits if hit.get("rerank_score") is not None]
        dense_scores = [hit.get("dense_score") for hit in hits if hit.get("dense_score") is not None]

        structured_rows = len(structured.get("facts") or []) + len(structured.get("aggregations") or [])
        criteria = {
            "documents": len({hit.get("document_id") for hit in hits}),
            "chunks": len(hits),
            "structured_rows": structured_rows,
            "graph_paths": len(graph.get("paths") or []),
            "best_rerank_score": round(max(rerank_scores), 4) if rerank_scores else None,
            "best_vector_score": round(max(dense_scores), 4) if dense_scores else None,
        }
        threshold = self.settings.evidence_sufficiency_threshold
        score = 0.0
        if criteria["documents"]:
            score += 0.4
        if int(criteria["chunks"] or 0) >= 2:
            score += 0.15
        if structured_rows:
            score += 0.3
        if graph.get("paths"):
            score += 0.15
        if rerank_scores and max(rerank_scores) > 0:
            score += 0.1
        sufficient = score >= threshold and (int(criteria["chunks"] or 0) > 0 or structured_rows > 0)
        state["evidence_sufficient"] = sufficient
        state["sufficiency"] = {
            "score": round(min(score, 1.0), 3),
            "threshold": threshold,
            "criteria": criteria,
            "method": "weighted evidence criteria (documents, structured rows, graph paths, rerank score)",
        }
        state["events"] = add_event(
            state,
            "evaluate",
            "Evaluated evidence sufficiency",
            f"score={round(min(score, 1.0), 3)} threshold={threshold} → {'sufficient' if sufficient else 'insufficient'}",
            sufficient=sufficient,
        )
        return state

    async def rewrite_query(self, state: AgentState) -> AgentState:
        iteration = int(state.get("iteration") or 0) + 1
        plan = QueryPlan.model_validate(state["plan"])
        suffix = REWRITE_SUFFIXES[(iteration - 1) % len(REWRITE_SUFFIXES)]
        rewritten = f"{plan.query} {suffix}"
        state["iteration"] = iteration
        state["question"] = state["question"]
        state["rewrites"] = [*state.get("rewrites", []), rewritten]
        state["strategy_selected"] = "hybrid_rerank"
        state["plan"] = plan.model_copy(update={"query": rewritten}).model_dump(mode="json")
        state["events"] = add_event(
            state,
            "rewrite",
            "Corrective retrieval: query rewritten",
            f"attempt {iteration} with additional terms",
            attempt=iteration,
        )
        return state

    # -------------------------------------------------------------- generate
    async def generate(self, state: AgentState, session: AsyncSession) -> AgentState:
        import time

        started = time.perf_counter()
        principal = self.principal_from_state(state)
        plan = QueryPlan.model_validate(state["plan"])

        hits = state.get("retrieval", {}).get("hits") or []
        chunks = [_chunk_from_payload(hit) for hit in hits]
        parents = await expand_parents(session, principal, chunks) if chunks else {}

        structured = _structured_from_payload(state["structured"])
        conflicts = [
            Conflict(
                kind=item.get("kind", "price_conflict"),
                description=item.get("description", ""),
                values=item.get("values", []),
                resolution=item.get("resolution", ""),
                preferred=item.get("preferred"),
                citations=item.get("citations", []),
            )
            for item in (state.get("conflicts") or [])
        ]

        extra_blocks = _extra_context_blocks(state)
        # Conflict-driven evidence completion: if two documents state different
        # prices, the page that holds the older value must be in the context, or
        # the answer cannot explain the difference it is reporting.
        conflict_blocks = await _conflict_evidence_blocks(session, principal, state, chunks)
        bundle = self.context_builder.build(
            chunks, parents=parents, extra_blocks=[*extra_blocks, *conflict_blocks]
        )
        strength = assess_evidence_strength(bundle, structured, conflicts=conflicts)

        answer = await self.generator.generate(
            question=state["question"],
            plan=plan,
            bundle=bundle,
            structured=structured,
            graph=state.get("graph"),
            conflicts=conflicts,
            evidence_strength=strength.level,
        )
        state["answer_text"] = answer.text
        state["generation_mode"] = answer.mode
        state["model"] = answer.model
        state["prompt_version"] = answer.prompt_version
        state["token_usage"] = answer.token_usage
        state["evidence_strength"] = strength.as_dict()
        state["citations"] = [citation.as_dict() for citation in bundle.citations]
        state["context"] = {**(state.get("context") or {}), **bundle.as_dict()}
        # Declared channel: LangGraph only propagates keys present in the state
        # schema, so the rendered evidence must live in one of them.
        state["context_blocks"] = [
            {
                "marker": block.marker,
                "text": block.text,
                "content_type": block.content_type,
                "is_synthetic": block.is_synthetic,
                "injection": block.injection,
                "citation": block.citation.as_dict(),
            }
            for block in bundle.blocks
        ]
        if answer.degraded:
            state["notes"] = [*state.get("notes", []), *answer.degradation_reasons]
        state["events"] = add_event(
            state,
            "generate",
            "Composed an answer from evidence",
            f"mode={answer.mode}" + (f", model={answer.model}" if answer.model else ""),
            mode=answer.mode,
        )
        state["timings"] = {
            **(state.get("timings") or {}),
            "generation_ms": int((time.perf_counter() - started) * 1000),
        }
        return state

    # ---------------------------------------------------------------- verify
    async def verify(self, state: AgentState) -> AgentState:
        import time

        started = time.perf_counter()
        blocks = state.get("context_blocks") or []
        evidence_texts = [block["citation"].get("snippet") or block["text"] for block in blocks]
        structured = _structured_from_payload(state["structured"])
        # Every structured row and aggregation is evidence for grounding: the
        # figures in the answer come from these rows, so the judge must see them.
        for fact in structured.facts:
            evidence_texts.append(
                f"{fact.supplier_name} {fact.product_name} {fact.unit_price} {fact.currency} "
                f"{fact.effective_date} {fact.expiry_date} {fact.amendment_ref} {fact.document_name} "
                f"MOQ {fact.minimum_quantity} discount {fact.discount_percent}"
            )
        for aggregation in structured.aggregations:
            evidence_texts.append(
                f"{aggregation.name} {aggregation.group} {aggregation.value} {aggregation.unit} {aggregation.method}"
            )
        for conflict in state.get("conflicts") or []:
            evidence_texts.append(f"{conflict.get('description')} {conflict.get('resolution')}")

        answer_text = state.get("answer_text", "")
        claims = extract_claims(answer_text)
        grounding = None
        if self.settings.llm_configured and self.container.router is not None and claims:
            grounding = await judge_grounding_llm(claims, evidence_texts, self.container.router)
        if grounding is None:
            grounding = judge_grounding_lexical(claims, evidence_texts)

        from app.retrieval.context import CitationDraft, ContextBlock, ContextBundle

        # Rebuild the bundle that generation actually saw, rather than an empty
        # stand-in, so criterion counts describe the real context.
        rendered_blocks = [
            ContextBlock(
                marker=block["marker"],
                text=block["text"],
                content_type=block.get("content_type", "text"),
                is_synthetic=bool(block.get("is_synthetic")),
                injection=block.get("injection") or {},
                citation=CitationDraft(
                    chunk_id=block["citation"].get("chunk_id"),
                    document_id=block["citation"].get("document_id"),
                    document_name=block["citation"].get("document_name", ""),
                    document_type=block["citation"].get("document_type"),
                    page=block["citation"].get("page"),
                    section=block["citation"].get("section"),
                    clause=block["citation"].get("clause"),
                    snippet=block["citation"].get("snippet", ""),
                    source_uri=block["citation"].get("source_uri"),
                    score=block["citation"].get("score"),
                    rank=block["citation"].get("rank"),
                    evidence_type=block["citation"].get("evidence_type", "document"),
                    is_synthetic=block["citation"].get("is_synthetic", False),
                    verified=block["citation"].get("verified", False),
                    metadata=block["citation"].get("metadata") or {},
                ),
            )
            for block in blocks
        ]
        bundle = ContextBundle(blocks=rendered_blocks)
        # The context builder renders one citable block per citation, so the
        # rendered blocks are the citation set generation worked from.
        bundle.citations = [block.citation for block in rendered_blocks]
        citation_check = validate_citations(answer_text, bundle)

        all_conflicts = state.get("conflicts") or []
        # Only a disagreement about an entity the question named can make this
        # answer ambiguous; unrelated conflicts stay in the corpus report.
        conflicts = relevant_conflicts(all_conflicts, state.get("plan"))
        coverage = assess_query_coverage(state.get("plan"), bundle, structured)
        status = decide_status(
            grounding=grounding,
            conflicts=conflicts,
            bundle=bundle,
            structured=structured,
            generation_mode=state.get("generation_mode", "llm"),
            coverage=coverage,
        )
        # Evidence strength was measured on the real context bundle during
        # generation; verification adds the grounding outcome to those criteria
        # rather than recomputing them from a reduced bundle and disagreeing.
        existing_strength = dict(state.get("evidence_strength") or {})
        # Recomputing on the restored bundle reproduces generation's assessment
        # (same context, same criteria) and adds the answer-support outcome, so
        # the reported strength is the one the returned answer is judged against.
        evidence_strength = assess_evidence_strength(
            bundle, structured, conflicts=conflicts, groundings=grounding
        )
        evidence_strength = type(evidence_strength)(
            level=evidence_strength.level,
            method="criteria_v1",
            criteria={
                **(existing_strength.get("criteria") or {}),
                **(evidence_strength.criteria or {}),
                "generation_level": existing_strength.get("level"),
                "grounding_score": grounding.score,
                "claims_supported": f"{grounding.supported}/{grounding.total}",
            },
        )

        refusal = False
        if status == "insufficient_evidence" and not conflicts:
            # The refusal body carries the refusal and its readable reason only;
            # the sufficiency criteria are structured data that already travel in
            # ``state['sufficiency']`` and are rendered by the interface.
            answer_text = f"{REFUSAL_TEXT}\n\nWhy: {refusal_reason(bundle, structured, coverage)}"
            refusal = True
            # The draft answer is discarded, so the citation audit must describe
            # the text that is actually returned, not the text that was dropped.
            citation_check = validate_citations(answer_text, bundle)

        state["answer_text"] = answer_text
        state["grounding"] = grounding.as_dict()
        state["citation_check"] = citation_check.as_dict()
        state["evidence_strength"] = evidence_strength.as_dict()
        state["status"] = status
        state["coverage"] = coverage.as_dict()
        state["validation"] = {
            **citation_check.as_dict(),
            "refusal_triggered": refusal,
            "claim_check_method": grounding.method,
            "coverage": coverage.as_dict(),
        }
        if len(conflicts) != len(all_conflicts):
            state["notes"] = [
                *state.get("notes", []),
                (
                    f"{len(all_conflicts) - len(conflicts)} price conflict(s) elsewhere in the corpus were "
                    "not applied to this answer because they do not concern the entities asked about."
                ),
            ]
        state["events"] = add_event(
            state,
            "verify",
            "Verified the answer against evidence",
            (
                f"{grounding.supported}/{grounding.total} claims supported "
                f"({grounding.method}); {len(citation_check.valid)} citation(s) verified"
            ),
            supported=grounding.supported,
            total=grounding.total,
            status=status,
        )
        state["timings"] = {
            **(state.get("timings") or {}),
            "verification_ms": int((time.perf_counter() - started) * 1000),
        }
        return state

    # -------------------------------------------------------------- finalize
    async def finalize(self, state: AgentState) -> AgentState:
        state["events"] = add_event(
            state,
            "finalize",
            "Answer ready",
            f"status={state.get('status')}, evidence strength={state.get('evidence_strength', {}).get('level')}",
            status=state.get("status"),
        )
        return state


def _select_strategy(plan: QueryPlan) -> str:
    if plan.complexity == "high" or plan.requires_graph:
        return "agentic"
    if plan.requires_structured and plan.intent == Intent.AGGREGATION:
        return "hybrid_rerank"
    return "hybrid_rerank"


def _mode_for_strategy(strategy: str) -> str:
    return {
        "dense": "dense",
        "sparse": "sparse",
        "hybrid": "hybrid",
        "hybrid_rerank": "hybrid",
        "hybrid_rerank_contextual": "hybrid",
        "agentic": "hybrid",
    }.get(strategy, "hybrid")


async def _conflict_evidence_blocks(
    session: AsyncSession, principal: Principal, state: AgentState, chunks: list[Any]
) -> list[tuple[Any, str, str]]:
    """Pull in the source pages of conflicting values."""
    from sqlalchemy import select as _select

    from app.retrieval.context import CitationDraft

    conflicts = state.get("conflicts") or []
    if not conflicts:
        return []
    already = {(chunk.document_id, chunk.page) for chunk in chunks}
    wanted: list[tuple[str, int | None]] = []
    for conflict in conflicts:
        for value in conflict.get("values") or []:
            document_id = value.get("document_id")
            page = value.get("page")
            if document_id and (document_id, page) not in already and (document_id, page) not in wanted:
                wanted.append((document_id, page))

    blocks: list[tuple[Any, str, str]] = []
    for document_id, page in wanted[:4]:
        statement = (
            _select(Chunk)
            .where(Chunk.document_id == document_id)
            .where(Chunk.tenant_id == principal.tenant_id)
            .where(Chunk.access_level.in_(principal.readable_access_levels))
        )
        if page is not None:
            statement = statement.where(Chunk.page_number == page)
        statement = statement.order_by(Chunk.embedding_indexed.desc(), Chunk.chunk_index).limit(2)
        rows = list((await session.execute(statement)).scalars())
        document = await session.get(Document, document_id)
        if document is None or document.tenant_id != principal.tenant_id:
            raise NotFoundError("Document not found.", details={"document_id": document_id})
        if not principal.can_read_level(document.access_level):
            raise AuthorizationError(
                f"Access denied to document with access level '{document.access_level}'.",
                details={"document_id": document_id, "access_level": document.access_level},
            )
        for chunk in rows:
            citation = CitationDraft(
                chunk_id=chunk.id,
                document_id=document_id,
                document_name=(document.title or document.filename) if document else "document",
                document_type=chunk.document_type,
                page=chunk.page_number,
                section=chunk.section or "Pricing",
                clause=chunk.clause,
                snippet=chunk.content[:700],
                evidence_type="document",
                is_synthetic=chunk.is_synthetic,
                verified=True,
                metadata={
                    "source": "conflict_evidence_completion",
                    "version": chunk.version,
                    "effective_date": chunk.effective_date.isoformat() if chunk.effective_date else None,
                },
            )
            blocks.append(
                (
                    citation,
                    f"CONFLICTING SOURCE | {citation.document_name} page {chunk.page_number}: "
                    f"{chunk.content[:900]}",
                    chunk.content_type,
                )
            )
    if blocks:
        state["events"] = add_event(
            state,
            "generate",
            "Added the source pages behind conflicting values to the context",
            f"{len(blocks)} block(s) added",
            added=len(blocks),
        )
        state["timings"] = {**(state.get("timings") or {})}
    return blocks


def _extra_context_blocks(state: AgentState) -> list[tuple[Any, str, str]]:
    """Structured and visual evidence rendered as citable context blocks."""
    from app.retrieval.context import CitationDraft

    blocks: list[tuple[Any, str, str]] = []
    structured = state.get("structured") or {}
    for aggregation in (structured.get("aggregations") or [])[:8]:
        citation = CitationDraft(
            chunk_id=None,
            document_id=None,
            document_name="Structured procurement data",
            document_type="structured",
            page=None,
            section=aggregation.get("name"),
            snippet=f"{aggregation.get('name')}={aggregation.get('value')} ({aggregation.get('method')})",
            evidence_type="structured_aggregation",
            verified=True,
            metadata=aggregation,
        )
        blocks.append(
            (
                citation,
                f"STRUCTURED RESULT | {aggregation.get('name')} {aggregation.get('group') or ''} = "
                f"{aggregation.get('value')} ({aggregation.get('method')}; {aggregation.get('detail')})",
                "structured",
            )
        )
    vision = state.get("vision") or {}
    for analysis in (vision.get("analyses") or [])[:3]:
        citation = CitationDraft(
            chunk_id=None,
            document_id=analysis.get("document_id"),
            document_name=f"Page {analysis.get('page')} visual analysis",
            document_type="vision",
            page=analysis.get("page"),
            section="Visual analysis",
            snippet=analysis.get("text", "")[:400],
            evidence_type="vision",
            verified=True,
            metadata={"model": analysis.get("model")},
        )
        blocks.append(
            (citation, f"VISION ANALYSIS (page {analysis.get('page')}): {analysis.get('text')}", "vision")
        )
    return blocks


def _chunk_from_payload(payload: dict[str, Any]):
    from datetime import date

    from app.retrieval.retriever import RetrievedChunk

    def _date(value: Any):
        if not value:
            return None
        try:
            return date.fromisoformat(str(value))
        except ValueError:
            return None

    return RetrievedChunk(
        chunk_id=payload.get("chunk_id", ""),
        document_id=payload.get("document_id", ""),
        document_name=payload.get("document_name", ""),
        document_type=payload.get("document_type"),
        page=payload.get("page"),
        section=payload.get("section"),
        clause=payload.get("clause"),
        content=payload.get("content", ""),
        contextual_content=payload.get("contextual_content"),
        content_type=payload.get("content_type", "paragraph"),
        access_level=payload.get("access_level", "internal"),
        is_synthetic=payload.get("is_synthetic", False),
        version=payload.get("version", 1),
        effective_date=_date(payload.get("effective_date")),
        expiry_date=_date(payload.get("expiry_date")),
        supplier_id=payload.get("supplier_id"),
        contract_id=payload.get("contract_id"),
        parent_chunk_id=payload.get("parent_chunk_id"),
        table_id=payload.get("table_id"),
        rank=payload.get("rank"),
        fused_score=payload.get("fused_score"),
        dense_score=payload.get("dense_score"),
        sparse_score=payload.get("sparse_score"),
        rerank_score=payload.get("rerank_score"),
        matched_by=payload.get("matched_by") or [],
        tables=payload.get("tables") or [],
    )


def _structured_from_payload(payload: dict[str, Any] | None) -> StructuredResult:
    from app.retrieval.analysis import PriceFact

    payload = payload or {}
    result = StructuredResult(
        queried=payload.get("queried", False),
        purpose=payload.get("purpose", ""),
        aggregations=[_aggregation_from_payload(item) for item in (payload.get("aggregations") or [])],
        contracts=payload.get("contracts") or [],
        compliance=payload.get("compliance") or [],
        suppliers=payload.get("suppliers") or [],
        notes=payload.get("notes") or [],
    )
    for item in payload.get("facts") or []:
        result.facts.append(
            PriceFact(
                price_id=item.get("price_id", ""),
                supplier_id=item.get("supplier_id"),
                supplier_name=item.get("supplier_name"),
                contract_id=item.get("contract_id"),
                contract_number=item.get("contract_number"),
                product_id=item.get("product_id"),
                product_name=item.get("product_name"),
                unit_price=float(item.get("unit_price") or 0.0),
                currency=item.get("currency", "USD"),
                minimum_quantity=item.get("minimum_quantity"),
                discount_percent=item.get("discount_percent"),
                payment_terms=item.get("payment_terms"),
                delivery_terms=item.get("delivery_terms"),
                effective_date=_parse_date(item.get("effective_date")),
                expiry_date=_parse_date(item.get("expiry_date")),
                amendment_ref=item.get("amendment_ref"),
                document_id=item.get("document_id"),
                document_name=item.get("document_name"),
                page=item.get("page"),
                is_synthetic=item.get("is_synthetic", False),
                quantity=item.get("quantity"),
                line_total=item.get("line_total"),
            )
        )
    for item in payload.get("conflicts") or []:
        result.conflicts.append(
            Conflict(
                kind=item.get("kind", "price_conflict"),
                description=item.get("description", ""),
                values=item.get("values", []),
                resolution=item.get("resolution", ""),
                preferred=item.get("preferred"),
                citations=item.get("citations", []),
            )
        )
    return result


def _aggregation_from_payload(item: dict[str, Any]):
    from app.retrieval.structured import Aggregation

    return Aggregation(
        name=item.get("name", ""),
        value=item.get("value"),
        unit=item.get("unit"),
        method=item.get("method", "sql_aggregation"),
        detail=item.get("detail", ""),
        group=item.get("group") or {},
        row_count=item.get("row_count", 0),
    )


def _parse_date(value: Any):
    from datetime import date

    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


__all__ = [
    "AgentRuntime",
    "NodeReport",
    "detect_price_conflicts",
    "fetch_price_facts",
    "understand_query_rule_based",
]
