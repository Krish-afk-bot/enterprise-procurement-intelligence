"""Phase 4 Stage 3: Full golden evaluation with LLM-enabled pipeline.

Runs all 22 golden questions through the complete RAG pipeline
(query understanding → structured retrieval → hybrid retrieval →
reranking → context builder → LLM generation → grounding → citation validation)
and records per-question results.

Usage (with Ollama llama3.1:8b):
  python scripts_phase3/golden_eval_llm.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# ------------------------------------------------------------------ env setup
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
os.environ.setdefault("EMBEDDING_PROVIDER", "sentence_transformers")
os.environ.setdefault("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
# LLM — override from env if caller sets them
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "ollama")
LLM_MODEL = os.environ.get("LLM_MODEL", "llama3.1:8b")
os.environ["LLM_BASE_URL"] = LLM_BASE_URL
os.environ["LLM_API_KEY"] = LLM_API_KEY
os.environ["LLM_MODEL"] = LLM_MODEL

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config.settings import reset_settings_cache  # noqa: E402

reset_settings_cache()


def _kw_hit(answer_text: str, keywords: list[str], min_hits: int) -> tuple[bool, list[str]]:
    """Return (passed, found_keywords)."""
    found = [kw for kw in keywords if kw.lower() in answer_text.lower()]
    return len(found) >= min_hits, found


async def main() -> None:
    import asyncpg

    from app.agents.pipeline import AnswerPipeline
    from app.config.container import get_container
    from app.config.settings import get_settings
    from app.db.session import get_session_factory
    from app.security.rbac import Principal

    settings = get_settings()
    print(f"LLM: {settings.llm_model} @ {settings.llm_base_url}")
    print(f"LLM configured: {settings.llm_configured}")
    print(f"Embed: {settings.embedding_model}")

    container = get_container()
    await container.startup()
    if container.fallbacks:
        print(f"WARN: fallbacks active: {[f.as_dict() for f in container.fallbacks]}")

    # Load tenant/user
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

    session_factory = get_session_factory(settings)
    pipeline = AnswerPipeline(container, settings)

    golden_path = PROJECT_ROOT / "data" / "evaluation" / "golden_questions.json"
    golden = json.loads(golden_path.read_text())
    questions = golden["questions"]
    print(f"\nRunning {len(questions)} golden questions...\n")

    results = []
    latencies = []

    async with session_factory() as session:  # noqa: F841
        for q in questions:
            t0 = time.perf_counter()
            try:
                answer = await pipeline.answer(
                    principal,
                    q["question"],
                    debug=False,
                )
            except Exception as exc:
                print(f"  ERROR {q['id']}: {exc}")
                results.append(
                    {
                        "id": q["id"],
                        "question": q["question"][:60],
                        "category": q["category"],
                        "is_unanswerable": q.get("is_unanswerable", False),
                        "generation_mode": "error",
                        "answer": f"ERROR: {exc}",
                        "grounded": False,
                        "citation_valid": False,
                        "kw_pass": False,
                        "pass": False,
                        "fail_reason": f"exception: {type(exc).__name__}",
                        "latency_ms": int((time.perf_counter() - t0) * 1000),
                    }
                )
                continue

            latency_ms = int((time.perf_counter() - t0) * 1000)
            latencies.append(latency_ms)

            # Keyword check
            keywords = q.get("expected_keywords") or []
            min_hits = q.get("minimum_keyword_hits", 1)
            is_unanswerable = q.get("is_unanswerable", False)

            if is_unanswerable:
                # Pass if system refused (status=insufficient_evidence or answer contains refusal)
                refused = (
                    answer.status == "insufficient_evidence"
                    or "couldn't verify" in answer.answer_text.lower()
                    or "no verified evidence" in answer.answer_text.lower()
                    or "not found" in answer.answer_text.lower()
                )
                kw_pass = refused
                found_kw: list[str] = []
            else:
                kw_pass, found_kw = _kw_hit(answer.answer_text, keywords, min_hits)

            # Citation validity
            citation_valid = len(answer.citations) > 0 and any(
                c.document_id or c.chunk_id for c in answer.citations
            )

            # Grounding
            grounded = (
                answer.grounding.score is not None and answer.grounding.score >= 0.5
            ) or answer.generation_mode == "extractive"

            passed = kw_pass and (not keywords or citation_valid or is_unanswerable)
            fail_reason = ""
            if not kw_pass:
                if is_unanswerable:
                    fail_reason = "did not refuse"
                else:
                    missing = [kw for kw in keywords if kw.lower() not in answer.answer_text.lower()]
                    fail_reason = f"missing keywords: {missing}"
            elif not citation_valid and keywords and not is_unanswerable:
                fail_reason = "no valid citation"

            status = "PASS" if passed else "FAIL"
            mode_short = answer.generation_mode[:3].upper()
            print(
                f"  [{status}] {q['id']} mode={mode_short} "
                f"status={answer.status} citations={len(answer.citations)} "
                f"grounded={answer.grounding.score} latency={latency_ms}ms"
            )
            if not passed:
                print(f"         reason: {fail_reason}")
            if answer.degraded:
                for r in answer.degradation_reasons[:1]:
                    print(f"         degraded: {r[:80]}")

            results.append(
                {
                    "id": q["id"],
                    "question": q["question"][:70],
                    "category": q["category"],
                    "is_unanswerable": is_unanswerable,
                    "generation_mode": answer.generation_mode,
                    "answer_preview": answer.answer_text[:200],
                    "status": answer.status,
                    "grounding_score": answer.grounding.score,
                    "grounded": grounded,
                    "citations": len(answer.citations),
                    "citation_valid": citation_valid,
                    "kw_pass": kw_pass,
                    "found_keywords": found_kw,
                    "pass": passed,
                    "fail_reason": fail_reason,
                    "latency_ms": latency_ms,
                    "degraded": answer.degraded,
                }
            )

    # ---------------------------------------------------------------- summary
    passed_count = sum(1 for r in results if r["pass"])
    failed_count = len(results) - passed_count
    llm_count = sum(1 for r in results if r.get("generation_mode") == "llm")
    ext_count = sum(1 for r in results if r.get("generation_mode") == "extractive")
    cit_valid = sum(1 for r in results if r.get("citation_valid"))
    grounded_count = sum(1 for r in results if r.get("grounded"))

    p50 = sorted(latencies)[len(latencies) // 2] if latencies else 0
    p95 = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

    print(f"\n{'=' * 60}")
    print(f"GOLDEN EVALUATION RESULTS ({LLM_MODEL})")
    print(f"{'=' * 60}")
    print(f"Total questions : {len(results)}")
    print(f"Passed          : {passed_count}/{len(results)}")
    print(f"Failed          : {failed_count}")
    print(f"LLM mode        : {llm_count}")
    print(f"Extractive mode : {ext_count}")
    print(f"Citation valid  : {cit_valid}/{len(results)}")
    print(f"Grounded        : {grounded_count}/{len(results)}")
    print(f"Latency p50     : {p50}ms")
    print(f"Latency p95     : {p95}ms")

    print("\nFailed questions:")
    for r in results:
        if not r["pass"]:
            print(f"  {r['id']}: {r['fail_reason']} (mode={r.get('generation_mode', '?')})")

    # Save results
    out = {
        "model": LLM_MODEL,
        "endpoint": LLM_BASE_URL,
        "passed": passed_count,
        "total": len(results),
        "llm_mode_count": llm_count,
        "extractive_mode_count": ext_count,
        "citation_valid_count": cit_valid,
        "grounded_count": grounded_count,
        "latency_p50_ms": p50,
        "latency_p95_ms": p95,
        "results": results,
    }
    out_path = PROJECT_ROOT / "data" / "evaluation" / "golden_eval_llm.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nResults saved to {out_path}")

    await container.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
