"""Evaluation runner (PRD s.47-49).

Runs the golden dataset through the real answer pipeline, once per experiment,
and stores both the per-question results and the aggregate metrics. The runner
never fabricates a score: metrics that cannot be computed for a question are
stored as ``null`` and the aggregate reports how many questions contributed.

Experiments differ only in *how evidence is retrieved or which engines are
allowed*, so the comparison is an ablation of the pipeline itself:

    dense            vector similarity only, no reranking
    sparse           BM25 only, no reranking
    hybrid           dense + BM25 fused with RRF, no reranking
    hybrid_rerank    hybrid + cross-encoder reranking (the default)
    agentic          the full LangGraph agent (corrective loop, SQL, graph)
    multimodal       agentic with per-page vision escalation required
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.pipeline import AnswerPipeline
from app.config.container import Container
from app.config.settings import Settings
from app.core.errors import NotFoundError
from app.db.models import EvaluationResult, EvaluationRun
from app.db.session import session_scope
from app.evaluation.dataset import GoldenQuestion, load_golden_dataset
from app.evaluation.metrics import (
    aggregate,
    answer_keywords,
    citation_validity,
    ndcg_at_k,
    page_coverage,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
    refusal_correct,
    word_overlap,
    answered_expected,
)
from app.observability.logging import get_logger
from app.security.rbac import Principal

logger = get_logger(__name__)

PER_QUESTION_METRICS = (
    "recall_at_5",
    "recall_at_10",
    "precision_at_5",
    "reciprocal_rank",
    "ndcg_at_10",
    "page_coverage",
    "keyword_coverage",
    "answer_correct",
    "refusal_correct",
    "citation_validity",
    "reference_f1",
    "latency_ms",
)


@dataclass(slots=True)
class Experiment:
    name: str
    description: str
    strategy: str
    requires: tuple[str, ...] = ()
    #: Forced engine switches applied on top of the strategy.
    overrides: dict[str, Any] | None = None

    def availability(self, settings: Settings) -> tuple[bool, str | None]:
        for requirement in self.requires:
            if requirement == "vlm" and not settings.vlm_configured:
                return False, "No vision model endpoint is configured (VLM_BASE_URL / VLM_MODEL)."
        return True, None


EXPERIMENTS: dict[str, Experiment] = {
    "dense": Experiment(
        name="dense",
        description="Dense vector retrieval only; no lexical search and no reranking.",
        strategy="dense",
    ),
    "sparse": Experiment(
        name="sparse",
        description="BM25 lexical retrieval only; no dense search and no reranking.",
        strategy="sparse",
    ),
    "hybrid": Experiment(
        name="hybrid",
        description="Dense + BM25 fused with reciprocal rank fusion; no reranking.",
        strategy="hybrid",
    ),
    "hybrid_rerank": Experiment(
        name="hybrid_rerank",
        description="Hybrid retrieval followed by cross-encoder reranking (default pipeline).",
        strategy="hybrid_rerank",
    ),
    "hybrid_rerank_contextual": Experiment(
        name="hybrid_rerank_contextual",
        description="Hybrid retrieval + reranking with contextual chunk enrichment.",
        strategy="hybrid_rerank_contextual",
    ),
    "agentic": Experiment(
        name="agentic",
        description="Full agent: query understanding, SQL, graph, corrective retrieval loop.",
        strategy="agentic",
    ),
    "multimodal": Experiment(
        name="multimodal",
        description="Agentic pipeline with vision escalation on layout-sensitive pages.",
        strategy="agentic",
        requires=("vlm",),
        overrides={"force_vision": True},
    ),
}


class EvaluationRunner:
    def __init__(self, container: Container, settings: Settings) -> None:
        self.container = container
        self.settings = settings
        self.pipeline = AnswerPipeline(container, settings)

    # ------------------------------------------------------------------ public
    def experiment_infos(self) -> list[dict[str, Any]]:
        infos: list[dict[str, Any]] = []
        for experiment in EXPERIMENTS.values():
            runnable, reason = experiment.availability(self.settings)
            infos.append(
                {
                    "name": experiment.name,
                    "description": experiment.description,
                    "requires": list(experiment.requires),
                    "runnable": runnable,
                    "unavailable_reason": reason,
                }
            )
        return infos

    def dataset_summary(self) -> dict[str, Any]:
        dataset = load_golden_dataset(self.settings.evaluation_dir)
        return {
            "name": dataset.name,
            "version": dataset.version,
            "path": dataset.path,
            "question_count": len(dataset.questions),
            "categories": dataset.categories,
            "unanswerable_count": sum(1 for question in dataset.questions if question.is_unanswerable),
        }

    async def run(
        self,
        principal: Principal,
        *,
        experiments: list[str] | None = None,
        categories: list[str] | None = None,
        max_questions: int | None = None,
        top_k: int = 10,
        name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute one or more experiments and persist their results."""
        dataset = load_golden_dataset(self.settings.evaluation_dir)
        questions = dataset.filtered(categories=categories, limit=max_questions)
        requested = experiments or ["hybrid_rerank"]
        payloads: list[dict[str, Any]] = []
        for experiment_name in requested:
            experiment = EXPERIMENTS.get(experiment_name)
            if experiment is None:
                raise NotFoundError(
                    f"Unknown experiment '{experiment_name}'.",
                    details={"available": sorted(EXPERIMENTS)},
                )
            payloads.append(
                await self.run_experiment(
                    principal,
                    experiment,
                    questions,
                    dataset_name=f"{dataset.name}@{dataset.version}",
                    top_k=top_k,
                    name=name,
                )
            )
        return payloads

    async def run_experiment(
        self,
        principal: Principal,
        experiment: Experiment,
        questions: list[GoldenQuestion],
        *,
        dataset_name: str,
        top_k: int,
        name: str | None = None,
    ) -> dict[str, Any]:
        runnable, reason = experiment.availability(self.settings)
        started = datetime.now(timezone.utc)
        async with session_scope() as session:
            run = EvaluationRun(
                tenant_id=principal.tenant_id,
                name=name or f"{experiment.name} on {dataset_name}",
                experiment=experiment.name,
                dataset_name=dataset_name,
                status="running" if runnable else "unavailable",
                config={
                    "top_k": top_k,
                    "strategy": experiment.strategy,
                    "question_count": len(questions),
                    "requires": list(experiment.requires),
                    "overrides": experiment.overrides or {},
                },
                summary={},
                question_count=len(questions),
                error_message=reason,
                started_by=principal.user_id,
                started_at=started,
            )
            session.add(run)
            await session.flush()
            run_id = run.id
        if not runnable:
            logger.info("evaluation_experiment_unavailable", experiment=experiment.name, reason=reason)
            return await self._payload(run_id, principal)

        rows: list[dict[str, Any]] = []
        for question in questions:
            rows.append(await self._run_question(principal, experiment, question, top_k=top_k))
            await self._store_result(principal, run_id, question, rows[-1])

        summary = aggregate(rows, PER_QUESTION_METRICS)
        summary["questions"] = len(rows)
        summary["experiment"] = experiment.name
        summary["description"] = experiment.description
        summary["by_category"] = _by_category(rows)
        summary["label"] = _label(summary)
        summary["notes"] = [
            "Metrics are computed against the hand-labelled golden dataset (data/evaluation/golden_questions.json).",
            "A metric is null when the dataset question carries no ground truth for it; nulls are excluded "
            "from the aggregate instead of counting as zero.",
        ]
        async with session_scope() as session:
            run = await session.get(EvaluationRun, run_id)
            if run is not None:
                run.status = "completed"
                run.summary = summary
                run.finished_at = datetime.now(timezone.utc)
        return await self._payload(run_id, principal)

    # ----------------------------------------------------------------- internals
    async def _run_question(
        self, principal: Principal, experiment: Experiment, question: GoldenQuestion, *, top_k: int
    ) -> dict[str, Any]:
        row: dict[str, Any] = {
            "question_id": question.id,
            "question": question.question,
            "category": question.category,
            "difficulty": question.difficulty,
            "expected_answer": question.expected_answer,
            "error": None,
        }
        try:
            answer = await self.pipeline.answer(
                principal,
                question.question,
                strategy=experiment.strategy,
                top_k=top_k,
            )
        except Exception as exc:  # noqa: BLE001 - a failed question must not abort the run
            logger.warning("evaluation_question_failed", question=question.id, error=str(exc))
            row["error"] = f"{type(exc).__name__}: {exc}"
            row["metrics"] = {}
            row["answer_text"] = None
            row["answer_status"] = "error"
            row["retrieved_document_ids"] = []
            row["retrieved_pages"] = []
            row["latency_ms"] = None
            return row

        documents = [citation.document_id for citation in answer.citations if citation.document_id]
        document_names: list[str] = []
        for citation in answer.citations:
            name = citation.document_name
            if name and name not in document_names:
                document_names.append(name)
        pages = [citation.page for citation in answer.citations if citation.page]
        chunk_ids = [citation.chunk_id for citation in answer.citations if citation.chunk_id]
        validation = answer.validation or {}
        keywords = answer_keywords(answer.answer_text, question.expected_keywords)
        grounding_details = (answer.grounding.details or {}) if answer.grounding else {}
        metrics = {
            "recall_at_5": recall_at_k(document_names, question.expected_documents, 5),
            "recall_at_10": recall_at_k(document_names, question.expected_documents, 10),
            "precision_at_5": precision_at_k(document_names, question.expected_documents, 5),
            "reciprocal_rank": reciprocal_rank(document_names, question.expected_documents),
            "ndcg_at_10": ndcg_at_k(document_names, question.expected_documents, 10),
            "page_coverage": page_coverage(pages, question.expected_pages),
            "keyword_coverage": keywords["coverage"],
            "keywords_found": keywords["found"],
            "keywords_missing": keywords["missing"],
            "answer_correct": answered_expected(
                answer.answer_text, question.expected_keywords, question.keyword_target
            ),
            "refusal_correct": refusal_correct(
                question.is_unanswerable,
                answer.status,
                bool(validation.get("refusal_triggered")),
            ),
            "citation_validity": citation_validity(validation),
            "reference_f1": word_overlap(answer.answer_text, question.expected_answer),
            "hallucinated_numbers": len(grounding_details.get("missing_numbers") or []),
            "grounding_supported": answer.grounding.supported_claims if answer.grounding else None,
            "grounding_total": answer.grounding.total_claims if answer.grounding else None,
            "latency_ms": answer.timings.get("total_ms"),
            "answer_status": answer.status,
            "evidence_strength": answer.evidence_strength.level,
        }
        row.update(
            {
                "answer_text": answer.answer_text,
                "answer_status": answer.status,
                "retrieved_chunk_ids": chunk_ids,
                "retrieved_document_ids": documents,
                "document_names": document_names,
                "retrieved_pages": sorted(set(pages)),
                "metrics": metrics,
                "latency_ms": answer.timings.get("total_ms"),
            }
        )
        return row

    async def _store_result(
        self, principal: Principal, run_id: str, question: GoldenQuestion, row: dict[str, Any]
    ) -> None:
        async with session_scope() as session:
            session.add(
                EvaluationResult(
                    tenant_id=principal.tenant_id,
                    run_id=run_id,
                    question_id=question.id,
                    question=question.question,
                    category=question.category,
                    difficulty=question.difficulty,
                    expected_answer=question.expected_answer,
                    expected_documents=list(question.expected_documents),
                    expected_pages=list(question.expected_pages),
                    answer_text=row.get("answer_text"),
                    answer_status=row.get("answer_status"),
                    retrieved_chunk_ids=list(row.get("retrieved_chunk_ids") or []),
                    retrieved_document_ids=list(row.get("retrieved_document_ids") or []),
                    retrieved_pages=list(row.get("retrieved_pages") or []),
                    metrics={
                        **(row.get("metrics") or {}),
                        "expected_keywords": question.expected_keywords,
                        "is_unanswerable": question.is_unanswerable,
                        "notes": question.notes,
                    },
                    latency_ms=row.get("latency_ms"),
                    error=row.get("error"),
                )
            )

    async def _payload(self, run_id: str, principal: Principal) -> dict[str, Any]:
        from app.services.evaluation import evaluation_run_payload

        async with session_scope() as session:
            return await evaluation_run_payload(session, principal, run_id, include_results=True)


def _by_category(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row.get("category") or "general", []).append(row.get("metrics") or {})
    return {
        category: {"questions": len(items), **aggregate(items, PER_QUESTION_METRICS)}
        for category, items in sorted(grouped.items())
    }


def _label(summary: dict[str, Any]) -> str:
    answer = summary.get("answer_correct")
    refusal = summary.get("refusal_correct")
    if answer is None and refusal is None:
        return "not evaluated"
    parts = []
    if answer is not None:
        parts.append(f"answer correctness {answer:.0%}")
    if refusal is not None:
        parts.append(f"refusal correctness {refusal:.0%}")
    return ", ".join(parts) + f" over {summary.get('questions', 0)} questions"
