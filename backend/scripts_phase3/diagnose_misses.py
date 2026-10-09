"""Diagnose the 4 persistent retrieval misses: gq-012, gq-015, gq-017, gq-020."""

import asyncio
import os
import sys

import asyncpg

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main() -> None:
    conn = await asyncpg.connect("postgresql://epi:epi@localhost:5432/epi")

    print("=== gq-012: Orion expired contract ORC-2021-777 ===")
    rows = await conn.fetch(
        "SELECT c.id, left(c.content, 120) AS preview, d.filename, c.chunk_index, "
        "c.embedding_indexed "
        "FROM chunks c JOIN documents d ON d.id = c.document_id "
        "WHERE d.filename ILIKE $1",
        "%orion%",
    )
    print(f"  Chunks for Orion: {len(rows)}")
    for r in rows:
        print(f"  [{r['chunk_index']}] embedded={r['embedding_indexed']} {r['filename']}: {r['preview']!r}")

    print("\n=== gq-015/017: Scanned signature page ===")
    rows2 = await conn.fetch(
        "SELECT c.id, left(c.content, 120) AS preview, d.filename, c.chunk_index, "
        "c.embedding_indexed "
        "FROM chunks c JOIN documents d ON d.id = c.document_id "
        "WHERE d.filename ILIKE $1",
        "%scanned%",
    )
    print(f"  Chunks for scanned page: {len(rows2)}")
    for r in rows2:
        print(f"  [{r['chunk_index']}] embedded={r['embedding_indexed']}: {r['preview']!r}")
    print("  (OCR was disabled during ingestion — scanned page has no text layer)")

    print("\n=== gq-020: Pricing table ===")
    rows3 = await conn.fetch(
        "SELECT c.id, left(c.content, 120) AS preview, d.filename, c.chunk_index, "
        "c.content_type, c.embedding_indexed "
        "FROM chunks c JOIN documents d ON d.id = c.document_id "
        "WHERE d.filename ILIKE $1",
        "%pricing%",
    )
    print(f"  Chunks for pricing schedule: {len(rows3)}")
    for r in rows3:
        print(
            f"  [{r['chunk_index']}] type={r['content_type']} embedded={r['embedding_indexed']}: "
            f"{r['preview']!r}"
        )

    print("\n=== Qdrant vector count per document ===")
    # Get all unique document names and their chunk counts
    rows4 = await conn.fetch(
        "SELECT d.filename, count(c.id) AS chunk_count, "
        "sum(CASE WHEN c.embedding_indexed THEN 1 ELSE 0 END) AS indexed_count "
        "FROM documents d LEFT JOIN chunks c ON c.document_id = d.id "
        "GROUP BY d.filename ORDER BY d.filename"
    )
    for r in rows4:
        print(f"  {r['filename']}: {r['chunk_count']} chunks, {r['indexed_count']} indexed in Qdrant")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
