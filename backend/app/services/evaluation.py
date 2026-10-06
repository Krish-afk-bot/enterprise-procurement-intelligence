"""Evaluation read services (runs, results, comparisons)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.models import EvaluationResult, EvaluationRun
from app.security.rbac import Principal


def _run_payload(run: EvaluationRun, *, metric_keys: list[str] | None = None) -> dict[str, Any]:
    summary = run.summary or {}
    metrics: list[dict[str, Any]] = []
    for key in metric_keys or sorted(key for key, value in summary.items() if isinstance(value, (int, float))):
        value = summary.get(key)
        if value is None or key.endswith("_n"):
            continue
        metrics.append(
            {
                "name": key,
                "value": float(value),
                "count": int(summary.get(f"{key}_n") or run.question_count),
                "display": _display(key, value),
                "description": METRIC_DESCRIPTIONS.get(key, ""),
            }
        )
    return {
        "id": run.id,
        "name": run.name,
        "experiment": run.experiment,
        "dataset_name": run.dataset_name,
        "status": run.status,
        "question_count": run.question_count,
        "summary": summary,
        "metrics": metrics,
        "config": run.config or {},
        "error_message": run.error_message,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "created_at": run.created_at,
    }


METRIC_DESCRIPTIONS: dict[str, str] = {
    "recall_at_5": "Share of labelled sources present in the top 5 retrieved documents.",
    "recall_at_10": "Share of labelled sources present in the top 10 retrieved documents.",
    "precision_at_5": "Share of the top 5 retrieved documents that are labelled as relevant.",
    "reciprocal_rank": "1 / rank of the first relevant document (MRR over the dataset).",
    "ndcg_at_10": "Binary-relevance nDCG at 10.",
    "page_coverage": "Share of labelled pages cited by the answer.",
    "keyword_coverage": "Share of the labelled ground-truth strings contained in the answer.",
    "answer_correct": "Share of answerable questions whose answer contains enough labelled facts.",
    "refusal_correct": "Share of questions where refusing (or answering) was the right behaviour.",
    "citation_validity": "Share of displayed citations backed by retrieved evidence.",
    "reference_f1": "Token F1 against the reference answer (diagnostic).",
    "latency_ms": "End-to-end latency per question in milliseconds.",
    "questions": "Number of golden questions evaluated.",
}


def _display(key: str, value: float) -> str:
    if key == "latency_ms":
        return f"{value:,.0f} ms"
    return f"{value:.3f}"


async def list_runs(
    session: AsyncSession, principal: Principal, *, limit: int = 25, offset: int = 0
) -> tuple[list[dict[str, Any]], int]:
    statement = select(EvaluationRun).where(EvaluationRun.tenant_id == principal.tenant_id)
    total = await session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    runs = list(
        (
            await session.execute(
                statement.order_by(EvaluationRun.created_at.desc()).offset(offset).limit(limit)
            )
        ).scalars()
    )
    return [_run_payload(run) for run in runs], int(total)


async def get_run(session: AsyncSession, principal: Principal, run_id: str) -> dict[str, Any]:
    run = await session.get(EvaluationRun, run_id)
    if run is None or run.tenant_id != principal.tenant_id:
        raise NotFoundError("Evaluation run not found.", details={"run_id": run_id})
    return _run_payload(run)


async def evaluation_run_payload(
    session: AsyncSession, principal: Principal, run_id: str, *, include_results: bool = False
) -> dict[str, Any]:
    payload = await get_run(session, principal, run_id)
    if not include_results:
        return payload
    results = list(
        (
            await session.execute(
                select(EvaluationResult)
                .where(EvaluationResult.run_id == run_id, EvaluationResult.tenant_id == principal.tenant_id)
                .order_by(EvaluationResult.question_id)
            )
        ).scalars()
    )
    payload["results"] = [
        {
            "id": row.id,
            "question_id": row.question_id,
            "question": row.question,
            "category": row.category,
            "difficulty": row.difficulty,
            "expected_answer": row.expected_answer,
            "answer_text": row.answer_text,
            "answer_status": row.answer_status,
            "retrieved_document_ids": row.retrieved_document_ids or [],
            "retrieved_pages": row.retrieved_pages or [],
            "metrics": row.metrics or {},
            "latency_ms": row.latency_ms,
            "error": row.error,
        }
        for row in results
    ]
    return payload


async def delete_run(session: AsyncSession, principal: Principal, run_id: str) -> None:
    run = await session.get(EvaluationRun, run_id)
    if run is None or run.tenant_id != principal.tenant_id:
        raise NotFoundError("Evaluation run not found.", details={"run_id": run_id})
    await session.delete(run)


async def compare_runs(
    session: AsyncSession, principal: Principal, run_ids: list[str]
) -> dict[str, Any]:
    """Metric-by-metric comparison across stored runs (no recomputation)."""
    runs = []
    for run_id in run_ids:
        runs.append(await get_run(session, principal, run_id))
    keys: list[str] = []
    for run in runs:
        for key, value in (run.get("summary") or {}).items():
            if isinstance(value, (int, float)) and key not in {"questions"} and not key.endswith("_n"):
                if key not in keys:
                    keys.append(key)
    rows = []
    for key in keys:
        values = {
            f"{run['experiment']}:{run['id'][-6:]}": (run.get("summary") or {}).get(key) for run in runs
        }
        available = {label: value for label, value in values.items() if isinstance(value, (int, float))}
        best_label = None
        if available:
            chooser = min if _lower_is_better(key) else max
            best_label = chooser(available, key=lambda label: available[label])
        rows.append(
            {
                "metric": key,
                "values": values,
                "best": best_label,
                "higher_is_better": not _lower_is_better(key),
                "description": METRIC_DESCRIPTIONS.get(key, ""),
            }
        )
    return {
        "metric": "all",
        "rows": rows,
        "notes": [
            "Values are read from stored runs; nothing is recomputed for the comparison.",
            "A null value means the metric was not available for that run (for example an experiment "
            "that requires a model endpoint which is not configured).",
        ],
        "has_data": bool(rows),
        "runs": [
            {
                "id": run["id"],
                "experiment": run["experiment"],
                "status": run["status"],
                "question_count": run["question_count"],
            }
            for run in runs
        ],
    }


def _lower_is_better(metric: str) -> bool:
    return metric in {"latency_ms", "hallucinated_numbers"}
