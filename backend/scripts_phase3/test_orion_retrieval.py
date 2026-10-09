"""Test Orion contract retrieval with the exact golden question."""

import asyncio
import os
import sys

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
    import asyncpg

    from app.config.container import get_container
    from app.config.settings import get_settings
    from app.db.session import get_session_factory
    from app.retrieval.query_understanding import (
        TenantVocabulary,
        understand_query_rule_based,
    )
    from app.retrieval.retriever import HybridRetriever
    from app.security.rbac import Principal

    settings = get_settings()
    container = get_container()
    await container.startup()

    pg = await asyncpg.connect("postgresql://epi:epi@localhost:5432/epi")
    tenant_row = await pg.fetchrow("SELECT id FROM tenants LIMIT 1")
    user_row = await pg.fetchrow("SELECT id, role FROM users LIMIT 1")

    # Load actual supplier vocabulary
    suppliers = await pg.fetch("SELECT id, name FROM suppliers WHERE tenant_id = $1", tenant_row["id"])
    contracts = await pg.fetch(
        "SELECT id, contract_number FROM contracts WHERE tenant_id = $1", tenant_row["id"]
    )
    vocab = TenantVocabulary(
        suppliers=[(r["id"], r["name"]) for r in suppliers],
        contracts=[(r["id"], r["contract_number"]) for r in contracts],
    )
    await pg.close()

    print(f"Vocab: {len(vocab.suppliers)} suppliers, {len(vocab.contracts)} contracts")
    for s in vocab.suppliers:
        print(f"  supplier: {s}")
    for c in vocab.contracts:
        print(f"  contract: {c}")

    principal = Principal(
        user_id=user_row["id"],
        tenant_id=tenant_row["id"],
        email="admin@epi.local",
        role=user_row["role"],
    )

    # Try both question variants
    questions = [
        "Which contract does Orion Components Co supply under and is it still active?",
        "What is the contract number for Orion Components Co?",
    ]

    session_factory = get_session_factory(settings)
    retriever = HybridRetriever(container, settings)

    async with session_factory() as session:
        for question in questions:
            plan = understand_query_rule_based(question, vocab)
            print(f"\nQ: {question}")
            print(
                f"  intent={plan.intent} suppliers={plan.suppliers} "
                f"contracts={plan.contract_numbers} supplier_ids={plan.supplier_ids}"
            )
            result = await retriever.retrieve(
                session,
                principal,
                plan,
                mode="hybrid",
                limit=5,
                rerank=False,
            )
            for h in result.hits[:5]:
                print(f"  [{h.rank}] {h.document_name} fused={h.fused_score:.4f}")

    await container.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
