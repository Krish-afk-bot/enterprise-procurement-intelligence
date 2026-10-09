"""Deeper diagnosis of gq-012, gq-015/017 misses."""

import asyncio
import os
import sys

import asyncpg

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
os.environ.setdefault("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config.settings import reset_settings_cache  # noqa: E402

reset_settings_cache()


async def main() -> None:
    conn = await asyncpg.connect("postgresql://epi:epi@localhost:5432/epi")

    # Check Orion chunk content and embedding
    print("=== All Orion/ORC chunks ===")
    rows = await conn.fetch(
        "SELECT c.id, left(c.content, 200) AS preview, d.filename, "
        "c.chunk_index, c.embedding_indexed "
        "FROM chunks c JOIN documents d ON d.id = c.document_id "
        "WHERE d.filename ILIKE $1 OR c.content ILIKE $2",
        "%ORC%",
        "%ORC-2021%",
    )
    for r in rows:
        print(f"  doc={r['filename']} chunk={r['chunk_index']} embedded={r['embedding_indexed']}")
        print(f"  content: {r['preview']!r}")

    # Check scanned page
    print("\n=== Scanned page document ===")
    rows2 = await conn.fetch(
        "SELECT d.id, d.filename, d.page_count, d.scanned_page_count, d.status, "
        "d.ocr_applied "
        "FROM documents d WHERE d.filename ILIKE $1",
        "%scanned%",
    )
    for r in rows2:
        print(
            f"  {r['filename']}: status={r['status']} pages={r['page_count']} "
            f"scanned={r['scanned_page_count']} ocr_applied={r['ocr_applied']}"
        )

    # Check what gq-012 actually asks and what BM25 finds
    print("\n=== BM25 search for 'Orion ORC-2021-777 expired' ===")
    from app.config.container import get_container
    from app.config.settings import get_settings
    from app.db.session import get_session_factory
    from app.retrieval.query_understanding import understand_query_rule_based
    from app.retrieval.retriever import HybridRetriever
    from app.security.rbac import Principal

    settings = get_settings()
    container = get_container()
    await container.startup()

    tenant_row = await conn.fetchrow("SELECT id FROM tenants LIMIT 1")
    user_row = await conn.fetchrow("SELECT id, role FROM users LIMIT 1")
    principal = Principal(
        user_id=user_row["id"],
        tenant_id=tenant_row["id"],
        email="admin@epi.local",
        role=user_row["role"],
    )

    question = "What is the status of the contract with Orion Components Co? Is ORC-2021-777 still active?"
    plan = understand_query_rule_based(question)
    print(f"  question: {question}")
    print(f"  intent: {plan.intent} suppliers={plan.suppliers} contracts={plan.contract_numbers}")

    session_factory = get_session_factory(settings)
    async with session_factory() as session:
        retriever = HybridRetriever(container, settings)
        result = await retriever.retrieve(session, principal, plan, mode="hybrid", limit=5, rerank=False)
        print(f"  hits: {len(result.hits)}")
        for h in result.hits:
            print(
                f"    [{h.rank}] {h.document_name} p{h.page} "
                f"dense={h.dense_score:.3f} sparse={h.sparse_score:.3f} fused={h.fused_score:.3f}"
            )

    await conn.close()
    await container.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
