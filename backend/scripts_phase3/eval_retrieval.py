"""Phase 3: Retrieval evaluation against the golden question set.

Runs the hybrid retrieval pipeline (dense + BM25 + RRF) for each golden
question and measures Recall@5, Precision@5, MRR, and Hit Rate.
Does NOT call the LLM - retrieval metrics only.

Usage:
  python scripts_phase3/eval_retrieval.py [--model bge-small|bge-m3]
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
os.environ.setdefault("RERANKER_ENABLED", "false")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config.settings import reset_settings_cache  # noqa: E402


def _parse_args():
    model = "bge-small"
    for arg in sys.argv[1:]:
        if arg.startswith("--model="):
            model = arg.split("=", 1)[1]
        elif arg in ("bge-m3", "bge-small"):
            model = arg
    return model


async def main() -> dict:
    model_arg = _parse_args()
    if model_arg == "bge-m3":
        os.environ["EMBEDDING_MODEL"] = "BAAI/bge-m3"
        collection = "procurement_chunks_1024d"
    else:
        os.environ["EMBEDDING_MODEL"] = "BAAI/bge-small-en-v1.5"
        collection = "procurement_chunks"

    reset_settings_cache()

    import asyncpg

    from app.config.container import get_container
    from app.config.settings import get_settings
    from app.db.session import get_session_factory
    from app.retrieval.query_understanding import understand_query_rule_based
    from app.retrieval.retriever import HybridRetriever
    from app.security.rbac import Principal

    settings = get_settings()
    print(f"Model  : {settings.embedding_model}")
    print(f"Collect: {collection}")

    container = get_container()
    await container.startup()
    print(f"Providers: vector={container.vector.name} embed={container.embeddings.model_name}")

    session_factory = get_session_factory(settings)

    # Load tenant/user
    pg = await asyncpg.connect("postgresql://epi:epi@localhost:5432/epi")
    tenant_row = await pg.fetchrow("SELECT id FROM tenants LIMIT 1")
    user_row = await pg.fetchrow("SELECT id, role FROM users LIMIT 1")
    await pg.close()

    if not tenant_row:
        print("ERROR: No tenant found. Run ingest_corpus.py first.")
        sys.exit(1)

    principal = Principal(
        user_id=user_row["id"],
        tenant_id=tenant_row["id"],
        email="admin@epi.local",
        role=user_row["role"],
    )

    # Override the collection name on the retriever if using bge-m3
    from app.ingestion.pipeline import CHUNK_COLLECTION

    if collection != CHUNK_COLLECTION:
        import app.ingestion.pipeline as _pipeline_mod

        _pipeline_mod.CHUNK_COLLECTION = collection

    retriever = HybridRetriever(container, settings)

    # Load golden questions
    golden_path = PROJECT_ROOT / "data" / "evaluation" / "golden_questions.json"
    golden = json.loads(golden_path.read_text())
    questions = golden["questions"]
    print(f"\nRunning {len(questions)} golden questions (K=5)...\n")

    K = 5
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
                rerank=False,
            )
            latency_ms = int((time.perf_counter() - t0) * 1000)
            latencies.append(latency_ms)

            hit_docs = {h.document_name for h in result.hits}
            expected_docs = set(q.get("expected_documents") or [])

            # Recall@K: fraction of expected docs retrieved in top K
            if expected_docs:
                recall = len(hit_docs & expected_docs) / len(expected_docs)
            else:
                recall = 1.0 if q.get("is_unanswerable") else 0.0

            # Precision@K: fraction of retrieved docs that are expected
            if result.hits:
                precision = len(hit_docs & expected_docs) / len(result.hits) if expected_docs else 0.0
            else:
                precision = 0.0

            # MRR: 1/rank of first relevant hit
            mrr = 0.0
            for rank, hit in enumerate(result.hits, start=1):
                if hit.document_name in expected_docs:
                    mrr = 1.0 / rank
                    break

            hit = recall > 0 or (q.get("is_unanswerable") and len(result.hits) == 0)

            results.append(
                {
                    "id": q["id"],
                    "question": q["question"][:60],
                    "category": q["category"],
                    "is_unanswerable": q.get("is_unanswerable", False),
                    "recall_at_k": round(recall, 3),
                    "precision_at_k": round(precision, 3),
                    "mrr": round(mrr, 3),
                    "hit": hit,
                    "retrieved": len(result.hits),
                    "hit_docs": list(hit_docs),
                    "expected_docs": list(expected_docs),
                    "latency_ms": latency_ms,
                }
            )

            status = "PASS" if recall >= 0.5 or q.get("is_unanswerable") else "MISS"
            print(
                f"  [{status}] {q['id']} recall={recall:.2f} mrr={mrr:.2f} "
                f"hits={len(result.hits)} latency={latency_ms}ms"
            )
            print(f"         retrieved: {list(hit_docs)[:3]}")
            print(f"         expected:  {list(expected_docs)[:3]}")

    # Aggregate metrics
    answered = [r for r in results if not r["is_unanswerable"]]
    unanswerable = [r for r in results if r["is_unanswerable"]]
    recall_at_k = sum(r["recall_at_k"] for r in answered) / len(answered) if answered else 0.0
    precision_at_k = sum(r["precision_at_k"] for r in answered) / len(answered) if answered else 0.0
    mrr = sum(r["mrr"] for r in answered) / len(answered) if answered else 0.0
    hit_rate = sum(r["hit"] for r in results) / len(results)
    p50 = sorted(latencies)[len(latencies) // 2]
    p95 = sorted(latencies)[int(len(latencies) * 0.95)]

    print(f"\n--- Retrieval metrics ({settings.embedding_model}) ---")
    print(f"Questions      : {len(results)} ({len(answered)} answerable, {len(unanswerable)} unanswerable)")
    print(f"Recall@{K}       : {recall_at_k:.3f}")
    print(f"Precision@{K}    : {precision_at_k:.3f}")
    print(f"MRR            : {mrr:.3f}")
    print(f"Hit Rate       : {hit_rate:.3f}")
    print(f"Latency p50    : {p50}ms")
    print(f"Latency p95    : {p95}ms")

    summary = {
        "model": settings.embedding_model,
        "collection": collection,
        "k": K,
        "recall_at_k": round(recall_at_k, 3),
        "precision_at_k": round(precision_at_k, 3),
        "mrr": round(mrr, 3),
        "hit_rate": round(hit_rate, 3),
        "latency_p50_ms": p50,
        "latency_p95_ms": p95,
        "question_results": results,
    }

    out_path = PROJECT_ROOT / "data" / "evaluation" / f"retrieval_baseline_{model_arg}.json"
    out_path.write_text(json.dumps(summary, indent=2))
    print(f"\nResults saved to {out_path}")

    await container.shutdown()
    return summary


if __name__ == "__main__":
    asyncio.run(main())
