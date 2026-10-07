"""Phase 3: Re-index corpus into a new Qdrant collection using BAAI/bge-m3 (1024d).

Creates collection 'procurement_chunks_1024d' — never overwrites the 384d collection.
"""

from __future__ import annotations

import asyncio
import os
import sys

os.environ["EMBEDDING_MODEL"] = "BAAI/bge-m3"
os.environ["EMBEDDING_ALLOW_DOWNLOAD"] = "false"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://epi:epi@localhost:5432/epi"
os.environ["VECTOR_PROVIDER"] = "qdrant"
os.environ["QDRANT_URL"] = "http://localhost:6333"
os.environ["GRAPH_PROVIDER"] = "neo4j"
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "neo4jdev"
os.environ["CACHE_PROVIDER"] = "redis"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["STORAGE_PROVIDER"] = "s3"
os.environ["S3_ENDPOINT"] = "http://localhost:9000"
os.environ["S3_ACCESS_KEY"] = "minioadmin"
os.environ["S3_SECRET_KEY"] = "minioadmin"
os.environ["S3_BUCKET"] = "epi-documents"
os.environ["ALLOW_PROVIDER_FALLBACK"] = "false"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config.settings import reset_settings_cache

reset_settings_cache()

NEW_COLLECTION = "procurement_chunks_1024d"
DIM = 1024


async def main() -> None:
    import asyncpg

    from app.config.container import get_container
    from app.config.settings import get_settings
    from app.providers.types import VectorPoint

    settings = get_settings()
    print(f"Embedding model: {settings.embedding_model}")

    container = get_container()
    await container.startup()

    # Verify dimension
    v = await container.embeddings.embed_query("test")
    actual_dim = len(v)
    print(f"Actual embedding dimension: {actual_dim}")
    assert actual_dim == DIM, f"Expected {DIM}, got {actual_dim}"

    # Ensure the 1024d collection exists
    await container.vector.ensure_collection(NEW_COLLECTION, DIM)
    print(f"Collection '{NEW_COLLECTION}' ready at dim={DIM}")

    # Load all chunks from PostgreSQL
    pg = await asyncpg.connect("postgresql://epi:epi@localhost:5432/epi")
    rows = await pg.fetch(
        "SELECT id, document_id, content, content_type, page_number, section, "
        "       clause, is_synthetic, tenant_id "
        "FROM chunks ORDER BY created_at"
    )
    await pg.close()
    print(f"Loaded {len(rows)} chunks from PostgreSQL")

    # Embed in batches and upsert
    BATCH = 16
    total_upserted = 0
    for i in range(0, len(rows), BATCH):
        batch = rows[i : i + BATCH]
        texts = [r["content"] for r in batch]
        vectors = await container.embeddings.embed_documents(texts)
        points = [
            VectorPoint(
                id=r["id"],
                vector=vec,
                payload={
                    "document_id": r["document_id"],
                    "content_type": r["content_type"],
                    "page_number": r["page_number"],
                    "section": r["section"],
                    "clause": r["clause"],
                    "is_synthetic": r["is_synthetic"],
                    "tenant_id": r["tenant_id"],
                    "chunk_id": r["id"],
                },
            )
            for r, vec in zip(batch, vectors, strict=False)
        ]
        upserted = await container.vector.upsert(NEW_COLLECTION, points)
        total_upserted += upserted
        pct = int((i + len(batch)) / len(rows) * 100)
        print(f"  {pct:3d}%  upserted {total_upserted}/{len(rows)}")

    final_count = await container.vector.count(NEW_COLLECTION)
    print(f"\nTotal vectors in '{NEW_COLLECTION}': {final_count}")
    assert final_count == len(rows), f"Count mismatch: {final_count} != {len(rows)}"

    await container.shutdown()
    print("PASS: BGE-M3 re-index COMPLETE")


if __name__ == "__main__":
    asyncio.run(main())
