"""Phase 4 Stage 4: Retrieval evaluation WITH reranker enabled.

Identical to eval_retrieval.py but with rerank=True to compare
before/after reranker metrics.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://epi:epi@localhost:5432/epi")
os.environ.setdefault("VECTOR_PROVIDER", "qdrant")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("GRAPH_PROVIDER", "neo4j")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USERNAME", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "neo4jdev")
os.environ.setdefault("CACHE_PROVIDER", "redis")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("STORAGE_PROVIDER", "s3")
os.environ.setdefault("S3_ENDPOINT", "http://localhost:9000")
os.environ.setdefault("S3_ACCESS_KEY", "minioadmin")
os.environ.setdefault("S3_SECRET_KEY", "minioadmin")
os.environ.setdefault("S3_BUCKET", "epi-documents")
os.environ.setdefault("ALLOW_PROVIDER_FALLBACK", "false")
os.environ.setdefault("RERANKER_ENABLED", "true")
os.environ.setdefault("RERANKER_PROVIDER", "cross_encoder")
os.environ.setdefault("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config.settings import reset_settings_cache  # noqa: E402

reset_settings_cache()

K = 5


async def main() -> dict:
    import asyncpg

    from app.config.container import get_container
    from app.config.settings import get_settings
    from app.db.session import get_session_factory
    from app.retrieval.query_understanding import understand_query_rule_based
    from app.retrieval.retriever import HybridRetriever
    from app.security.rbac import Principal

    settings = get_settings()
    print(f"Model  : {settings.embedding_model}")
    print(f"Reranker: {settings.reranker_provider} enabled={settings.reranker_enabled}")

    container = get_container()
    await container.startup()
    print(f"Reranker active: {container.reranker.name if container.reranker else 'none'}")

    session_factory = get_session_factory(settings)

    pg = await asyncpg.connect("postgresql://epi:epi@localhost:5432/epi")
    tenant_row = await pg.fetchrow("SELECT id FROM tenants LIMIT 1")
    user_row = await pg.fetchrow("SELECT id, role FROM users LIMIT 1")
    await pg.close()

    if not tenant_row:
        print("ERROR: No tenant. Run ingest_corpus.py first.")
        sys.exit(1)

    principal = Principal(
        user_id=user_row["id"],
        tenant_id=tenant_row["id"],
        email="admin@epi.local",
        role=user_row["role"],
    )

    retriever = HybridRetriever(container, settings)
    golden_path = PROJECT_ROOT / "data" / "evaluation" / "golden_questions.json"
    golden = json.loads(golden_path.read_text())
    questions = golden["questions"]
    print(f"\nRunning {len(questions)} golden questions (K={K}, rerank=True)...\n")

    results = []
    latencies = []

    async with session_factory() as session:
        for q in questions:
            t0 = time.perf_counter()
            plan = understand_query_rule_based(q["question"])
            result = await retriever.retrieve(
                session,
                principal,
                plan,
                mode="hybrid",
                limit=K,
                rerank=True,
            )
            latency_ms = int((time.perf_counter() - t0) * 1000)
            latencies.append(latency_ms)

            hit_docs = {h.document_name for h in result.hits}
            expected_docs = set(q.get("expected_documents") or [])

            recall = (
                len(hit_docs & expected_docs) / len(expected_docs)
                if expected_docs
                else (1.0 if q.get("is_unanswerable") else 0.0)
            )
            precision = (
                len(hit_docs & expected_docs) / len(result.hits) if (result.hits and expected_docs) else 0.0
            )
            mrr = 0.0
            for rank, hit in enumerate(result.hits, start=1):
                if hit.document_name in expected_docs:
                    mrr = 1.0 / rank
                    break

            hit = recall > 0 or (q.get("is_unanswerable") and len(result.hits) == 0)
            rerank_scores = [h.rerank_score for h in result.hits if h.rerank_score is not None]

            results.append(
                {
                    "id": q["id"],
                    "recall_at_k": round(recall, 3),
                    "precision_at_k": round(precision, 3),
                    "mrr": round(mrr, 3),
                    "hit": hit,
                    "retrieved": len(result.hits),
                    "latency_ms": latency_ms,
                    "best_rerank_score": round(max(rerank_scores), 4) if rerank_scores else None,
                }
            )
            status = "PASS" if recall >= 0.5 or q.get("is_unanswerable") else "MISS"
            print(f"  [{status}] {q['id']} recall={recall:.2f} mrr={mrr:.2f} latency={latency_ms}ms")

    answered_qs = [r for r, q in zip(results, questions, strict=False) if not q.get("is_unanswerable")]
    unanswerable_qs = [r for r, q in zip(results, questions, strict=False) if q.get("is_unanswerable")]

    recall_at_k = sum(r["recall_at_k"] for r in answered_qs) / len(answered_qs) if answered_qs else 0.0
    precision_at_k = sum(r["precision_at_k"] for r in answered_qs) / len(answered_qs) if answered_qs else 0.0
    mrr = sum(r["mrr"] for r in answered_qs) / len(answered_qs) if answered_qs else 0.0
    hit_rate = sum(r["hit"] for r in results) / len(results)
    p50 = sorted(latencies)[len(latencies) // 2]
    p95 = sorted(latencies)[int(len(latencies) * 0.95)]

    print("\n--- Retrieval metrics WITH reranker ---")
    print(f"Model          : {settings.embedding_model}")
    print(f"Reranker       : {settings.reranker_provider}")
    print(
        f"Questions      : {len(results)} ({len(answered_qs)} answerable, {len(unanswerable_qs)} unanswerable)"
    )
    print(f"Recall@{K}       : {recall_at_k:.3f}")
    print(f"Precision@{K}    : {precision_at_k:.3f}")
    print(f"MRR            : {mrr:.3f}")
    print(f"Hit Rate       : {hit_rate:.3f}")
    print(f"Latency p50    : {p50}ms")
    print(f"Latency p95    : {p95}ms")

    summary = {
        "model": settings.embedding_model,
        "reranker": settings.reranker_provider,
        "k": K,
        "recall_at_k": round(recall_at_k, 3),
        "precision_at_k": round(precision_at_k, 3),
        "mrr": round(mrr, 3),
        "hit_rate": round(hit_rate, 3),
        "latency_p50_ms": p50,
        "latency_p95_ms": p95,
        "question_results": results,
    }
    out_path = PROJECT_ROOT / "data" / "evaluation" / "retrieval_with_reranker.json"
    out_path.write_text(json.dumps(summary, indent=2))
    print(f"\nResults saved to {out_path}")

    await container.shutdown()
    return summary


if __name__ == "__main__":
    asyncio.run(main())
