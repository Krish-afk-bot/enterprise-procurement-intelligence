"""v2 evaluation runner.

Runs the hand-labelled v2 questions through the real agent graph and reports
each family of metrics **separately**, because a single blended "pass rate"
cannot tell you whether the retrieval failed, the generation failed, or the
verifier waved it through:

    retrieval   recall@k, MRR, nDCG@10, hit rate, page coverage
    answer      expected-fact coverage and correctness
    refusal     precision *and* recall (a refusal rate alone is meaningless)
    citation    precision of the displayed citations
    latency     p50 / p95 / max, outliers kept
    tokens      prompt and completion usage

Every pass rate carries a Wilson 95% interval. Every failure is given one label
from a fixed taxonomy so the same table can be compared across pipeline changes.

Two execution modes:

``current``  the full agent graph exactly as the API runs it (``answer_state``);
``oracle``   the labelled documents are injected as the retrieved evidence, so
             only generation + verification are measured. The gap between the
             two is the retrieval's contribution.

Nothing here invents a number: a metric that cannot be computed for a question
is ``None`` and excluded from its aggregate, never counted as a zero.
"""

from __future__ import annotations

import time
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.pipeline import AnswerPipeline
from app.agents.verification import REFUSAL_TEXT
from app.config.container import Container
from app.config.settings import Settings
from app.core.errors import NotFoundError
from app.db.models import Chunk, Document
from app.db.session import session_scope
from app.evaluation.metrics import (
    citation_precision,
    latency_percentiles,
    ndcg_at_k,
    page_coverage,
    recall_at_k,
    reciprocal_rank,
    refusal_confusion,
    refusal_precision_recall,
    wilson_interval,
)
from app.evaluation.v2_dataset import V2Dataset, V2Question, load_v2_dataset
from app.observability.logging import get_logger
from app.security.rbac import Principal

logger = get_logger(__name__)

#: One label per failure, in priority order. The set is fixed so the counts are
#: comparable between runs.
FAILURE_LABELS = (
    "retrieval_miss",
    "wrong_context_selected",
    "generation_error",
    "verification_miss",
    "refusal_failure",
    "error",
)


def _unique(values: list[Any]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value))


def _doc_hit(name: str, pool: list[str]) -> bool:
    needle = name.lower()
    return any(needle == candidate.lower() or needle in candidate.lower() for candidate in pool)


def _mean(values: list[float | None]) -> float | None:
    numbers = [float(value) for value in values if value is not None]
    return round(sum(numbers) / len(numbers), 4) if numbers else None


def _wilson(values: list[bool | None]) -> dict[str, Any] | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return wilson_interval(sum(1 for value in present if value), len(present))


class V2Runner:
    """Executes the v2 dataset against the graph and returns a full report."""

    def __init__(self, container: Container, settings: Settings) -> None:
        self.container = container
        self.settings = settings
        self.pipeline = AnswerPipeline(container, settings)
        self.runtime = self.pipeline.runtime
        self.dataset_file = "questions.json"  # Can be overridden

    # ------------------------------------------------------------------ public
    def load_dataset(self, directory: str | None = None) -> V2Dataset:
        return load_v2_dataset(
            self.settings.evaluation_dir / "v2" if directory is None else directory,
            filename=self.dataset_file
        )

    async def run(
        self,
        principal: Principal,
        *,
        mode: str = "current",
        strategy: str | None = None,
        top_k: int = 10,
        categories: list[str] | None = None,
        max_questions: int | None = None,
        on_row: Any = None,
    ) -> dict[str, Any]:
        """Run every question and return the report payload."""
        if mode not in {"current", "oracle"}:
            raise NotFoundError(f"Unknown v2 evaluation mode '{mode}'.", details={"modes": ["current", "oracle"]})
        dataset = self.load_dataset()
        questions = dataset.filtered(categories=categories, limit=max_questions)
        started = time.perf_counter()
        rows: list[dict[str, Any]] = []
        for index, question in enumerate(questions, start=1):
            row = await self._run_question(principal, question, mode=mode, strategy=strategy, top_k=top_k)
            rows.append(row)
            if on_row is not None:
                on_row(index, len(questions), row)
        report = self._report(dataset, rows, mode=mode, strategy=strategy, top_k=top_k)
        report["run"]["duration_seconds"] = round(time.perf_counter() - started, 1)
        return report

    # --------------------------------------------------------------- per-question
    async def _run_question(
        self, principal: Principal, question: V2Question, *, mode: str, strategy: str | None, top_k: int
    ) -> dict[str, Any]:
        started = time.perf_counter()
        row: dict[str, Any] = {
            "id": question.id,
            "question": question.question,
            "category": question.category,
            "difficulty": question.difficulty,
            "adversarial": question.adversarial,
            "expected_refusal": question.expected_refusal,
            "expected_answer": question.expected_answer,
            "expected_facts": question.expected_facts,
            "expected_documents": question.expected_documents,
            "expected_pages": question.expected_pages,
            "notes": question.notes,
            "error": None,
        }
        try:
            if mode == "oracle":
                state, oracle_docs = await self._oracle_state(principal, question, top_k=top_k)
                row["oracle_documents"] = oracle_docs
            else:
                state = await self.pipeline.answer_state(principal, question.question, strategy=strategy, top_k=top_k)
        except Exception as exc:  # noqa: BLE001 - one failed question must not abort the run
            logger.warning("v2_question_failed", question=question.id, error=str(exc))
            row.update(
                {
                    "error": f"{type(exc).__name__}: {exc}",
                    "answer_text": None,
                    "status": "error",
                    "refused": False,
                    "answer_correct": None,
                    "failure_label": "error",
                    "latency_ms": int((time.perf_counter() - started) * 1000),
                }
            )
            return row

        row.update(self._score(question, state))
        row["latency_ms"] = int((time.perf_counter() - started) * 1000)
        row["failure_label"] = _failure_label(row)
        return row

    def _score(self, question: V2Question, state: dict[str, Any]) -> dict[str, Any]:
        answer_text = state.get("answer_text") or ""
        retrieval = state.get("retrieval") or {}
        hits = retrieval.get("hits") or []
        citations = state.get("citations") or []
        validation = state.get("validation") or {}
        grounding = state.get("grounding") or {}
        token_usage = state.get("token_usage") or {}
        status = state.get("status") or "error"

        retrieved_documents = _unique([hit.get("document_name") for hit in hits])
        retrieved_pages = _unique([hit.get("page") for hit in hits if hit.get("page")])
        cited_documents = _unique([citation.get("document_name") for citation in citations])
        cited_pages = _unique([citation.get("page") for citation in citations if citation.get("page")])

        lowered = answer_text.lower()
        found = [fact for fact in question.expected_facts if fact.lower() in lowered]
        missing = [fact for fact in question.expected_facts if fact.lower() not in lowered]
        fact_coverage = round(len(found) / len(question.expected_facts), 4) if question.expected_facts else None

        refused = bool(validation.get("refusal_triggered")) or status == "insufficient_evidence"
        if not refused and REFUSAL_TEXT.lower() in lowered:
            refused = True

        expected_pages = [int(page) for page in question.expected_pages]
        answer_correct: bool | None = None
        if question.answerable and question.expected_facts:
            answer_correct = len(missing) == 0 and not refused

        citation_score = citation_precision(cited_documents, question.expected_documents)
        recall_5 = recall_at_k(retrieved_documents, question.expected_documents, 5)
        recall_10 = recall_at_k(retrieved_documents, question.expected_documents, 10)
        # ``state['grounding']`` is ``GroundingResult.as_dict()``, whose keys are
        # ``total_claims``/``supported_claims`` (not ``total``/``supported``).
        grounding_total = int(grounding.get("total_claims") or 0)
        grounding_supported = int(grounding.get("supported_claims") or 0)

        return {
            "answer_text": answer_text,
            "status": status,
            "generation_mode": state.get("generation_mode"),
            "model": state.get("model"),
            "refused": refused,
            "refusal_correct": refused == question.expected_refusal,
            # answer metrics
            "facts_found": found,
            "facts_missing": missing,
            "fact_coverage": fact_coverage,
            "answer_correct": answer_correct,
            # retrieval metrics
            "retrieved_documents": retrieved_documents,
            "retrieved_pages": retrieved_pages,
            "recall_at_5": recall_5,
            "recall_at_10": recall_10,
            "hit_at_5": (recall_5 > 0) if recall_5 is not None else None,
            "hit_at_10": (recall_10 > 0) if recall_10 is not None else None,
            "reciprocal_rank": reciprocal_rank(retrieved_documents, question.expected_documents),
            "ndcg_at_10": ndcg_at_k(retrieved_documents, question.expected_documents, 10),
            "page_coverage": page_coverage(retrieved_pages, expected_pages),
            # citation metrics
            "cited_documents": cited_documents,
            "cited_pages": cited_pages,
            "citation_precision": citation_score,
            "citations_clean": (citation_score == 1.0) if citation_score is not None else None,
            "citation_validity": (
                round(
                    int(validation.get("valid_citations") or 0)
                    / max(1, int(validation.get("valid_citations") or 0) + int(validation.get("invalid_citations") or 0)),
                    4,
                )
                if (validation.get("valid_citations") or validation.get("invalid_citations"))
                else None
            ),
            # verification
            "grounding_supported": grounding_supported,
            "grounding_total": grounding_total,
            "evidence_strength": (state.get("evidence_strength") or {}).get("level"),
            "answerability": state.get("answerability") or {},
            "citation_selection": state.get("citation_selection") or {},
            "grounding_details": grounding.get("details") or {},
            # latency + cost
            "timings_ms": state.get("timings") or {},
            "prompt_tokens": int(token_usage.get("prompt_tokens") or 0),
            "completion_tokens": int(token_usage.get("completion_tokens") or 0),
        }

    # ------------------------------------------------------------------- oracle
    async def _oracle_state(
        self, principal: Principal, question: V2Question, *, top_k: int
    ) -> tuple[dict[str, Any], list[str]]:
        """Run generation + verification against the labelled evidence only."""
        state: dict[str, Any] = {
            "tenant_id": principal.tenant_id,
            "user_id": principal.user_id,
            "role": principal.role,
            "question": question.question,
            "conversation_id": None,
            "filters": {},
            "strategy": None,
            "top_k": top_k,
            "max_iterations": 1,
            "debug": False,
            "iteration": 0,
            "events": [],
            "notes": [],
            "errors": [],
        }
        async with session_scope() as session:
            state = await self.runtime.understand(state, session)
            state = await self.runtime.plan(state)
            state = await self.runtime.structured(state, session)
            state["graph"] = {"traversal": False, "paths": [], "reason": "oracle run: graph skipped"}
            hits, used = await self._oracle_hits(session, principal, question, top_k=top_k)
            state["retrieval"] = {
                "mode": "oracle",
                "hits": hits,
                "steps": [],
                "candidates": len(hits),
                "notes": ["Oracle context: the labelled documents were supplied directly."],
            }
            state["vision"] = {"used": False, "reason": "oracle run"}
            state = await self.runtime.evaluate_evidence(state)
            state = await self.runtime.generate(state, session)
            state = await self.runtime.verify(state)
            state = await self.runtime.finalize(state)
        return state, used

    async def _oracle_hits(
        self, session: AsyncSession, principal: Principal, question: V2Question, *, top_k: int
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Supply *all* chunks of the labelled documents, labelled pages first.

        A top-``k`` slice is deliberately **not** applied: the oracle is meant to
        measure generation + verification given the right evidence, so starving it
        of the labelled page would masquerade as a generation failure. Only the
        labelled documents are supplied, so the run still tests nothing about
        retrieval.
        """
        if not question.expected_documents:
            return [], []
        document_order = {name: index for index, name in enumerate(question.expected_documents)}
        documents = list(
            (
                await session.execute(
                    select(Document).where(
                        Document.tenant_id == principal.tenant_id,
                        Document.filename.in_(question.expected_documents),
                    )
                )
            ).scalars()
        )
        documents.sort(key=lambda document: document_order.get(document.filename, len(document_order)))
        expected_pages = {int(page) for page in question.expected_pages}
        hits: list[dict[str, Any]] = []
        used: list[str] = []
        for document in documents:
            if not principal.can_read_level(document.access_level):
                continue
            chunks = list(
                (
                    await session.execute(
                        select(Chunk).where(Chunk.document_id == document.id, Chunk.tenant_id == principal.tenant_id)
                    )
                ).scalars()
            )
            if not chunks:
                continue
            chunks.sort(
                key=lambda chunk: (
                    0 if (expected_pages and chunk.page_number in expected_pages) else 1,
                    chunk.chunk_index,
                )
            )
            used.append(document.filename)
            for chunk in chunks:
                hits.append(
                    {
                        "chunk_id": chunk.id,
                        "document_id": document.id,
                        "document_name": document.title or document.filename,
                        "document_type": chunk.document_type,
                        "page": chunk.page_number,
                        "section": chunk.section,
                        "clause": chunk.clause,
                        "content": chunk.content,
                        "contextual_content": chunk.contextual_content,
                        "content_type": chunk.content_type,
                        "access_level": chunk.access_level,
                        "is_synthetic": chunk.is_synthetic,
                        "version": chunk.version,
                        "effective_date": chunk.effective_date.isoformat() if chunk.effective_date else None,
                        "expiry_date": chunk.expiry_date.isoformat() if chunk.expiry_date else None,
                        "supplier_id": chunk.supplier_id,
                        "contract_id": chunk.contract_id,
                        "parent_chunk_id": chunk.parent_chunk_id,
                        "table_id": chunk.table_id,
                        "rank": len(hits) + 1,
                        "fused_score": None,
                        "dense_score": None,
                        "sparse_score": None,
                        "rerank_score": None,
                        "matched_by": ["oracle"],
                        "tables": [],
                    }
                )
        return hits, used

    # ------------------------------------------------------------------ report
    def _report(
        self, dataset: V2Dataset, rows: list[dict[str, Any]], *, mode: str, strategy: str | None, top_k: int
    ) -> dict[str, Any]:
        answerable = [row for row in rows if not row["expected_refusal"]]
        retrieval_rows = [row for row in rows if row["expected_documents"]]

        counts = refusal_confusion(rows)
        refusal = refusal_precision_recall(counts)
        refusal["accuracy"] = _wilson([row.get("refusal_correct") for row in rows])
        refusal["questions"] = len(rows)

        taxonomy = Counter(row.get("failure_label") for row in rows if row.get("failure_label"))
        models = sorted({row.get("model") for row in rows if row.get("model")})

        return {
            "dataset": dataset.summary(),
            "run": {
                "mode": mode,
                "oracle": mode == "oracle",
                "strategy": strategy,
                "top_k": top_k,
                "started_at": datetime.now(UTC).isoformat(),
                "llm_model": (self.settings.llm_model if self.settings.llm_configured else None),
                "llm_endpoint": self.settings.llm_base_url,
                "observed_models": models,
                "embedding_model": self.settings.embedding_model,
                "reranker_enabled": self.settings.reranker_enabled,
                "vlm_configured": self.settings.vlm_configured,
                "generation_modes": dict(Counter(row.get("generation_mode") for row in rows)),
            },
            "retrieval": {
                "questions": len(retrieval_rows),
                "recall_at_5": _mean([row.get("recall_at_5") for row in retrieval_rows]),
                "recall_at_10": _mean([row.get("recall_at_10") for row in retrieval_rows]),
                "mrr": _mean([row.get("reciprocal_rank") for row in retrieval_rows]),
                "ndcg_at_10": _mean([row.get("ndcg_at_10") for row in retrieval_rows]),
                "page_coverage": _mean([row.get("page_coverage") for row in retrieval_rows]),
                "hit_rate_at_5": _wilson([row.get("hit_at_5") for row in retrieval_rows]),
                "hit_rate_at_10": _wilson([row.get("hit_at_10") for row in retrieval_rows]),
            },
            "answer": {
                "questions": len([row for row in answerable if row.get("answer_correct") is not None]),
                "correct": _wilson([row.get("answer_correct") for row in answerable]),
                "mean_fact_coverage": _mean([row.get("fact_coverage") for row in answerable]),
            },
            "refusal": refusal,
            "citation": {
                "questions": len([row for row in answerable if row.get("citation_precision") is not None]),
                "mean_precision": _mean([row.get("citation_precision") for row in answerable]),
                "no_unsupported_citations": _wilson([row.get("citations_clean") for row in answerable]),
                "mean_validity": _mean([row.get("citation_validity") for row in rows]),
            },
            "latency_ms": latency_percentiles([row.get("latency_ms") for row in rows]),
            "tokens": {
                "prompt_total": sum(int(row.get("prompt_tokens") or 0) for row in rows),
                "completion_total": sum(int(row.get("completion_tokens") or 0) for row in rows),
                "prompt_mean": _mean([row.get("prompt_tokens") for row in rows]),
                "completion_mean": _mean([row.get("completion_tokens") for row in rows]),
                "cost_usd": None,
                "cost_note": "not measured: no per-token price is configured for the local model",
            },
            "failure_taxonomy": {label: taxonomy.get(label, 0) for label in FAILURE_LABELS},
            "failures_total": sum(taxonomy.values()),
            "by_category": _by_category(rows),
            "rows": rows,
        }


def _by_category(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row.get("category") or "general", []).append(row)
    report: dict[str, Any] = {}
    for category, items in sorted(grouped.items()):
        answerable = [row for row in items if not row["expected_refusal"]]
        counts = refusal_confusion(items)
        report[category] = {
            "questions": len(items),
            "answer_correct": _wilson([row.get("answer_correct") for row in answerable]),
            "fact_coverage": _mean([row.get("fact_coverage") for row in answerable]),
            "refusal_precision": refusal_precision_recall(counts)["precision"],
            "refusal_recall": refusal_precision_recall(counts)["recall"],
            "failures": {
                label: sum(1 for row in items if row.get("failure_label") == label)
                for label in FAILURE_LABELS
                if any(row.get("failure_label") == label for row in items)
            },
        }
    return report


def _failure_label(row: dict[str, Any]) -> str | None:
    """Assign exactly one taxonomy label to a failed question, else ``None``."""
    if row.get("error"):
        return "error"
    expected_refusal = bool(row.get("expected_refusal"))
    refused = bool(row.get("refused"))
    if expected_refusal != refused:
        return "refusal_failure"
    if expected_refusal:
        return None  # correctly refused
    if row.get("answer_correct") is None:
        return None  # no fact label to judge against
    if row.get("answer_correct"):
        return None

    expected_documents = row.get("expected_documents") or []
    if expected_documents:
        if not any(_doc_hit(name, row.get("retrieved_documents") or []) for name in expected_documents):
            return "retrieval_miss"
        if not any(_doc_hit(name, row.get("cited_documents") or []) for name in expected_documents):
            return "wrong_context_selected"

    total = int(row.get("grounding_total") or 0)
    supported = int(row.get("grounding_supported") or 0)
    reported_verified = row.get("status") == "supported" and (total == 0 or supported == total)
    return "verification_miss" if reported_verified else "generation_error"


__all__ = ["FAILURE_LABELS", "V2Runner"]
