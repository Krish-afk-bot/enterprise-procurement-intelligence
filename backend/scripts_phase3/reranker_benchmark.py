"""Measure whether the cross-encoder earns its latency.

Runs retrieval twice for every answerable v2 question — reranker on and off —
against the same plan and corpus, and reports recall@10, MRR, nDCG@10, hit rate
and latency percentiles for both.

Usage (from ``backend``):

    python scripts_phase3/reranker_benchmark.py
"""

from __future__ import annotations

import asyncio
import json
import os
import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
EVAL_DIR = PROJECT_ROOT / "data" / "evaluation" / "v2"
EVAL_VAR_ROOT = Path(os.environ.get("EVAL_VAR_DIR", str(BACKEND_DIR / "var" / "eval-v2")))

os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{(EVAL_VAR_ROOT / 'eval.db').as_posix()}")
os.environ.setdefault("VAR_DIR", (EVAL_VAR_ROOT / "var").as_posix())
os.environ.setdefault("LOCAL_STORAGE_DIR", (EVAL_VAR_ROOT / "storage").as_posix())
os.environ.setdefault("OCR_ENABLED", "false")
os.environ.setdefault("VLM_ENABLED", "false")
os.environ.setdefault("EMBEDDING_PROVIDER", "sentence_transformers")
os.environ.setdefault("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
os.environ.setdefault("RERANKER_ENABLED", "true")
os.environ.setdefault("RERANKER_PROVIDER", "cross_encoder")
os.environ.setdefault("ALLOW_PROVIDER_FALLBACK", "false")
os.environ.setdefault("LLM_PROVIDER", "openai_compatible")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("LLM_API_KEY", "ollama")
os.environ.setdefault("LLM_MODEL", "qwen2.5-coder:7b")

sys.path.insert(0, str(BACKEND_DIR))
from app.config.settings import reset_settings_cache  # noqa: E402

reset_settings_cache()


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
    return round(ordered[index], 1)


async def main() -> int:
    from sqlalchemy import select

    from app.config.container import get_container
    from app.config.settings import get_settings
    from app.db.models import Tenant, User
    from app.db.session import session_scope
    from app.evaluation.metrics import ndcg_at_k, recall_at_k, reciprocal_rank
    from app.evaluation.v2_dataset import load_v2_dataset
    from app.retrieval.query_understanding import understand_query
    from app.retrieval.retriever import HybridRetriever
    from app.security.rbac import Principal

    settings = get_settings()
    container = get_container()
    await container.startup()
    dataset = load_v2_dataset(EVAL_DIR)
    questions = [question for question in dataset.questions if question.answerable and question.expected_documents]
    print(f"questions with labelled sources: {len(questions)}")

    async with session_scope() as session:
        tenant = (await session.execute(select(Tenant).limit(1))).scalar_one_or_none()
        user = (
            await session.execute(select(User).where(User.tenant_id == tenant.id).limit(1))
        ).scalar_one_or_none()
    principal = Principal(
        user_id=user.id if user else "eval-runner",
        tenant_id=tenant.id,
        email=user.email if user else "eval@local",
        role=user.role if user else "admin",
    )

    retriever = HybridRetriever(container, settings)
    results: dict[str, dict] = {}
    for label, rerank in (("with_reranker", True), ("without_reranker", False)):
        recalls: list[float] = []
        mrrs: list[float] = []
        ndcgs: list[float] = []
        hits: list[float] = []
        latencies: list[float] = []
        per_question: list[dict] = []
        for question in questions:
            started = time.perf_counter()
            async with session_scope() as session:
                plan = await understand_query(
                    question.question,
                    session=session,
                    tenant_id=principal.tenant_id,
                    router=container.router,
                    use_llm=settings.llm_configured,
                )
                result = await retriever.retrieve(
                    session, principal, plan, mode="hybrid", limit=10, rerank=rerank
                )
            latency = (time.perf_counter() - started) * 1000
            documents = list(dict.fromkeys(hit.document_name for hit in result.hits))
            recall = recall_at_k(documents, question.expected_documents, 10)
            mrr = reciprocal_rank(documents, question.expected_documents)
            ndcg = ndcg_at_k(documents, question.expected_documents, 10)
            if recall is not None:
                recalls.append(recall)
            if mrr is not None:
                mrrs.append(mrr)
            if ndcg is not None:
                ndcgs.append(ndcg)
            hits.append(1.0 if (recall or 0) > 0 else 0.0)
            latencies.append(latency)
            per_question.append(
                {
                    "id": question.id,
                    "recall_at_10": recall,
                    "mrr": mrr,
                    "ndcg_at_10": ndcg,
                    "latency_ms": round(latency, 1),
                    "reranker": result.reranker,
                    "steps": result.step_summary(),
                }
            )
        results[label] = {
            "questions": len(questions),
            "recall_at_10": round(statistics.fmean(recalls), 4) if recalls else None,
            "mrr": round(statistics.fmean(mrrs), 4) if mrrs else None,
            "ndcg_at_10": round(statistics.fmean(ndcgs), 4) if ndcgs else None,
            "hit_rate_at_10": round(statistics.fmean(hits), 4) if hits else None,
            "latency_ms": {
                "p50": _percentile(latencies, 0.50),
                "p95": _percentile(latencies, 0.95),
                "max": round(max(latencies), 1) if latencies else None,
                "mean": round(statistics.fmean(latencies), 1) if latencies else None,
            },
            "rows": per_question,
        }
        print(
            f"{label:<18} recall@10={results[label]['recall_at_10']} mrr={results[label]['mrr']} "
            f"ndcg@10={results[label]['ndcg_at_10']} p50={results[label]['latency_ms']['p50']}ms"
        )

    output = {
        "dataset": {"name": dataset.name, "questions": len(questions)},
        "settings": {
            "rerank_candidate_limit": settings.rerank_candidate_limit,
            "rerank_gate_enabled": settings.rerank_gate_enabled,
            "rerank_top_n": settings.rerank_top_n,
        },
        "modes": results,
    }
    path = EVAL_DIR / "reranker_benchmark.json"
    path.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    print(f"saved {path.relative_to(PROJECT_ROOT)}")
    await container.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
