"""Benchmark v3 runner: retrieval, answer, citation, faithfulness, temporal.

Runs the 120-question set through the real answer pipeline once and reports each
family of metrics separately, so a failure is attributable to retrieval,
generation, verification or refusal rather than to a blended score.

Definitions used here, stated because they are easy to over-claim:

``recall@k``
    share of the labelled documents present in the top-k retrieved documents.
``answer_correct``
    every labelled fact appears in the answer (case/whitespace/punctuation
    normalised) and the answer was not refused. Containment scoring cannot
    recognise a correct paraphrase; a paraphrase counts as a miss.
``citation precision``
    share of displayed citations that point at a labelled document.
``citation recall``
    share of labelled documents that were cited.
``faithfulness``
    supported claims / total verified claims, from the pipeline's own grounding
    pass. ``unsupported_claim_rate`` is its complement.
``correct refusal rate``
    share of questions where refusal/answer matched the label.
``temporal_correct``
    the derived as-of date equals the labelled one and the labelled facts appear
    (or, for an unanswerable temporal question, it was refused).

A metric with no data is ``None`` and excluded from its mean; the count of
contributing questions is reported beside every aggregate.
"""

from __future__ import annotations

import asyncio
import math
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.agents.pipeline import AnswerPipeline
from app.agents.verification import REFUSAL_TEXT
from app.config.container import Container
from app.config.settings import Settings
from app.evaluation.benchmark import BenchmarkDataset, BenchmarkQuestion
from app.evaluation.metrics import (
    latency_percentiles,
    refusal_confusion,
    refusal_precision_recall,
    wilson_interval,
)
from app.observability.logging import get_logger
from app.retrieval.query_understanding import understand_query_rule_based
from app.security.rbac import Principal

logger = get_logger(__name__)

FAILURE_LABELS = (
    "retrieval_miss",
    "wrong_context_selected",
    "generation_error",
    "verification_miss",
    "refusal_failure",
    "temporal_error",
    "error",
)

_QUESTION_TIMEOUT_SECONDS = 240


def _norm(value: str) -> str:
    text = (value or "").lower()
    for source, target in (("\u2019", "'"), ("\u2013", "-"), ("\u2014", "-"), ("\u00a0", " ")):
        text = text.replace(source, target)
    return " ".join(text.split())


def _unique(values: list[Any]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value))


def _stem(name: str) -> str:
    return _norm(Path(str(name)).stem)


def _doc_hit(expected: str, pool: list[str]) -> bool:
    """Compare documents by stem: labels carry the file extension, retrieved hits
    carry the display name without it."""
    needle = _stem(expected)
    return any(
        needle == _stem(candidate) or needle in _stem(candidate) or _stem(candidate) in needle
        for candidate in pool
    )


def _recall_at_k(retrieved: list[str], expected: list[str], k: int | None = None) -> float | None:
    if not expected:
        return None
    pool = _unique(retrieved[:k] if k else retrieved)
    hits = sum(1 for item in expected if _doc_hit(item, pool))
    return round(hits / len(expected), 4)


def _reciprocal_rank(retrieved: list[str], expected: list[str]) -> float | None:
    if not expected:
        return None
    for index, item in enumerate(_unique(retrieved), start=1):
        if _doc_hit(item, expected):
            return round(1.0 / index, 4)
    return 0.0


def _ndcg_at_k(retrieved: list[str], expected: list[str], k: int = 10) -> float | None:
    if not expected:
        return None
    pool = _unique(retrieved[:k])
    dcg = 0.0
    for index, item in enumerate(pool, start=1):
        if _doc_hit(item, expected):
            dcg += 1.0 / math.log2(index + 1)
    ideal = sum(1.0 / math.log2(index + 1) for index in range(1, min(len(expected), k) + 1))
    return round(dcg / ideal, 4) if ideal else None


def _citation_precision(cited: list[str], expected: list[str]) -> float | None:
    pool = _unique(cited)
    if not pool or not expected:
        return None
    hits = sum(1 for item in pool if _doc_hit(item, expected))
    return round(hits / len(pool), 4)


def _mean(values: list[float | None]) -> float | None:
    numbers = [float(value) for value in values if value is not None]
    return round(sum(numbers) / len(numbers), 4) if numbers else None


def _wilson(values: list[bool | None]) -> dict[str, Any] | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return wilson_interval(sum(1 for value in present if value), len(present))


class BenchmarkRunner:
    def __init__(self, container: Container, settings: Settings) -> None:
        self.container = container
        self.settings = settings
        self.pipeline = AnswerPipeline(container, settings)

    async def run(
        self,
        principal: Principal,
        dataset: BenchmarkDataset,
        *,
        top_k: int = 10,
        strategy: str | None = None,
        categories: list[str] | None = None,
        limit: int | None = None,
        on_row: Any = None,
    ) -> dict[str, Any]:
        questions = dataset.filtered(categories=categories, limit=limit)
        started = time.perf_counter()
        rows: list[dict[str, Any]] = []
        for index, question in enumerate(questions, start=1):
            row = await self._run_question(principal, question, top_k=top_k, strategy=strategy)
            rows.append(row)
            if on_row is not None:
                on_row(index, len(questions), row)
        report = self.report(dataset, rows, top_k=top_k, strategy=strategy)
        report["run"]["duration_seconds"] = round(time.perf_counter() - started, 1)
        return report

    # ------------------------------------------------------------- per question
    async def _run_question(
        self,
        principal: Principal,
        question: BenchmarkQuestion,
        *,
        top_k: int,
        strategy: str | None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        base = {
            "id": question.id,
            "question": question.question,
            "category": question.category,
            "answerability": question.answerability,
            "review_status": question.review_status,
            "expected_answer": question.expected_answer,
            "expected_facts": question.expected_facts,
            "expected_documents": question.expected_documents,
            "expected_refusal": question.expected_refusal,
            "temporal": question.temporal,
        }
        try:
            state = await asyncio.wait_for(
                self.pipeline.answer_state(principal, question.question, strategy=strategy, top_k=top_k),
                timeout=_QUESTION_TIMEOUT_SECONDS,
            )
        except Exception as exc:  # noqa: BLE001 - one question must not abort the run
            logger.warning("benchmark_question_failed", question=question.id, error=str(exc))
            base.update(
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
            return base

        base.update(self._score(question, state))
        base["latency_ms"] = int((time.perf_counter() - started) * 1000)
        base["failure_label"] = _failure_label(base)
        return base

    def _score(self, question: BenchmarkQuestion, state: dict[str, Any]) -> dict[str, Any]:
        answer_text = state.get("answer_text") or ""
        hits = (state.get("retrieval") or {}).get("hits") or []
        citations = state.get("citations") or []
        validation = state.get("validation") or {}
        grounding = state.get("grounding") or {}
        tokens = state.get("token_usage") or {}
        status = state.get("status") or "error"

        retrieved_documents = _unique([hit.get("document_name") for hit in hits])
        retrieved_pages = _unique([hit.get("page") for hit in hits if hit.get("page")])
        cited_documents = _unique([citation.get("document_name") for citation in citations])
        cited_pages = _unique([citation.get("page") for citation in citations if citation.get("page")])

        lowered = _norm(answer_text)
        found = [fact for fact in question.expected_facts if _norm(fact) in lowered]
        missing = [fact for fact in question.expected_facts if _norm(fact) not in lowered]
        coverage = round(len(found) / len(question.expected_facts), 4) if question.expected_facts else None

        refused = bool(validation.get("refusal_triggered")) or status == "insufficient_evidence"
        if not refused and _norm(REFUSAL_TEXT) in lowered:
            refused = True

        answer_correct: bool | None = None
        if question.answerable and question.expected_facts:
            answer_correct = not missing and not refused
        elif question.expected_refusal:
            answer_correct = refused

        citation_score = _citation_precision(cited_documents, question.expected_documents)
        cited_labelled = (
            sum(1 for expected in question.expected_documents if _doc_hit(expected, cited_documents))
            if question.expected_documents
            else None
        )
        citation_recall = (
            round(cited_labelled / len(question.expected_documents), 4)
            if cited_labelled is not None
            else None
        )

        grounding_total = int(grounding.get("total_claims") or 0)
        grounding_supported = int(grounding.get("supported_claims") or 0)
        faithfulness = round(grounding_supported / grounding_total, 4) if grounding_total else None
        unsupported_rate = round(1 - faithfulness, 4) if faithfulness is not None else None

        temporal_correct: bool | None = None
        derived_as_of = None
        if question.temporal:
            plan = understand_query_rule_based(question.question)
            derived_as_of = plan.as_of.isoformat() if plan.as_of else None
            expected_as_of = (question.temporal or {}).get("expected_as_of")
            as_of_ok = derived_as_of == expected_as_of
            temporal_correct = bool(as_of_ok and answer_correct) if question.answerable else bool(as_of_ok and refused)

        return {
            "answer_text": answer_text,
            "status": status,
            "generation_mode": state.get("generation_mode"),
            "model": state.get("model"),
            "refused": refused,
            "refusal_correct": refused == question.expected_refusal,
            "facts_found": found,
            "facts_missing": missing,
            "fact_coverage": coverage,
            "answer_correct": answer_correct,
            "retrieved_documents": retrieved_documents,
            "retrieved_pages": retrieved_pages,
            "recall_at_5": _recall_at_k(retrieved_documents, question.expected_documents, 5),
            "recall_at_10": _recall_at_k(retrieved_documents, question.expected_documents, 10),
            "reciprocal_rank": _reciprocal_rank(retrieved_documents, question.expected_documents),
            "ndcg_at_10": _ndcg_at_k(retrieved_documents, question.expected_documents, 10),
            "page_coverage": (
                round(
                    sum(1 for page in question.expected_pages if str(page) in set(retrieved_pages))
                    / len(question.expected_pages),
                    4,
                )
                if question.expected_pages
                else None
            ),
            "cited_documents": cited_documents,
            "cited_pages": cited_pages,
            "citation_precision": citation_score,
            "citation_recall": citation_recall,
            "citation_validity": (
                round(
                    int(validation.get("valid_citations") or 0)
                    / max(
                        1,
                        int(validation.get("valid_citations") or 0)
                        + int(validation.get("invalid_citations") or 0),
                    ),
                    4,
                )
                if (validation.get("valid_citations") or validation.get("invalid_citations"))
                else None
            ),
            "grounding_supported": grounding_supported,
            "grounding_total": grounding_total,
            "faithfulness": faithfulness,
            "unsupported_claim_rate": unsupported_rate,
            "temporal_correct": temporal_correct,
            "derived_as_of": derived_as_of,
            "evidence_strength": (state.get("evidence_strength") or {}).get("level"),
            "prompt_tokens": int(tokens.get("prompt_tokens") or 0),
            "completion_tokens": int(tokens.get("completion_tokens") or 0),
            "timings_ms": state.get("timings") or {},
        }

    # ------------------------------------------------------------------- report
    def report(
        self,
        dataset: BenchmarkDataset,
        rows: list[dict[str, Any]],
        *,
        top_k: int,
        strategy: str | None,
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
                "mode": "benchmark_v3",
                "strategy": strategy,
                "top_k": top_k,
                "started_at": datetime.now(UTC).isoformat(),
                "question_count": len(rows),
                "llm_model": self.settings.llm_model if self.settings.llm_configured else None,
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
                "hit_rate_at_5": _wilson([
                    (row.get("recall_at_5") or 0) > 0 if row.get("recall_at_5") is not None else None
                    for row in retrieval_rows
                ]),
                "hit_rate_at_10": _wilson([
                    (row.get("recall_at_10") or 0) > 0 if row.get("recall_at_10") is not None else None
                    for row in retrieval_rows
                ]),
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
                "mean_recall": _mean([row.get("citation_recall") for row in answerable]),
                "citations_clean": _wilson([(row.get("citation_precision") == 1.0) if row.get("citation_precision") is not None else None for row in answerable]),
                "mean_validity": _mean([row.get("citation_validity") for row in rows]),
            },
            "faithfulness": {
                "questions": len([row for row in rows if row.get("faithfulness") is not None]),
                "mean": _mean([row.get("faithfulness") for row in rows]),
                "unsupported_claim_rate": _mean([row.get("unsupported_claim_rate") for row in rows]),
                "fully_supported": _wilson([
                    (row.get("faithfulness") == 1.0) if row.get("faithfulness") is not None else None
                    for row in rows
                ]),
            },
            "temporal": {
                "questions": len([row for row in rows if row.get("temporal_correct") is not None]),
                "correct": _wilson([row.get("temporal_correct") for row in rows]),
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
    summary: dict[str, Any] = {}
    for category, items in sorted(grouped.items()):
        answerable = [row for row in items if not row["expected_refusal"]]
        counts = refusal_confusion(items)
        summary[category] = {
            "questions": len(items),
            "answerable": len(answerable),
            "answer_correct": _wilson([row.get("answer_correct") for row in answerable]),
            "fact_coverage": _mean([row.get("fact_coverage") for row in answerable]),
            "recall_at_10": _mean([row.get("recall_at_10") for row in items]),
            "citation_precision": _mean([row.get("citation_precision") for row in answerable]),
            "faithfulness": _mean([row.get("faithfulness") for row in items]),
            "refusal_precision": refusal_precision_recall(counts)["precision"],
            "refusal_recall": refusal_precision_recall(counts)["recall"],
            "temporal_correct": _wilson([row.get("temporal_correct") for row in items]),
            "latency_p50_ms": latency_percentiles([row.get("latency_ms") for row in items]).get("p50"),
            "failures": {
                label: sum(1 for row in items if row.get("failure_label") == label)
                for label in FAILURE_LABELS
                if any(row.get("failure_label") == label for row in items)
            },
        }
    return summary


def _failure_label(row: dict[str, Any]) -> str | None:
    """Assign one taxonomy label to a failed question, else ``None``."""
    if row.get("error"):
        return "error"
    expected_refusal = bool(row.get("expected_refusal"))
    refused = bool(row.get("refused"))
    if expected_refusal != refused:
        return "refusal_failure"
    if expected_refusal:
        return None
    if row.get("temporal") and row.get("temporal_correct") is False:
        return "temporal_error"
    if row.get("answer_correct") is None:
        return None
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
    verified = row.get("status") == "supported" and (total == 0 or supported == total)
    return "verification_miss" if verified else "generation_error"


__all__ = ["BenchmarkRunner", "FAILURE_LABELS"]
