"""Check supplier_id linkage on Orion chunks."""

import asyncio

import asyncpg


async def main() -> None:
    c = await asyncpg.connect("postgresql://epi:epi@localhost:5432/epi")

    chunks = await c.fetch(
        "SELECT ch.id, ch.supplier_id, d.filename, d.supplier_id AS doc_supplier_id "
        "FROM chunks ch JOIN documents d ON d.id = ch.document_id "
        "WHERE d.filename ILIKE $1",
        "%ORC%",
    )
    print(f"Orion chunks: {len(chunks)}")
    for r in chunks:
        print(f"  chunk.supplier_id={r['supplier_id']}  doc.supplier_id={r['doc_supplier_id']}")

    # Check the supplier record
    sup = await c.fetchrow("SELECT id, name FROM suppliers WHERE name ILIKE $1", "%Orion%")
    print(f"Orion supplier in DB: {sup['id'] if sup else 'NOT FOUND'} - {sup['name'] if sup else ''}")

    # Check document<->supplier link
    doc = await c.fetchrow("SELECT id, supplier_id, filename FROM documents WHERE filename ILIKE $1", "%ORC%")
    print(f"Orion document supplier_id: {doc['supplier_id'] if doc else 'NOT FOUND'}")

    # Check if the Qdrant payload has supplier_id
    # We need to look at what metadata is stored on the chunk
    chunk_meta = await c.fetchrow(
        "SELECT ch.id, ch.supplier_id, ch.metadata_json "
        "FROM chunks ch JOIN documents d ON d.id = ch.document_id "
        "WHERE d.filename ILIKE $1",
        "%ORC%",
    )
    if chunk_meta:
        print(f"Chunk metadata: supplier_id={chunk_meta['supplier_id']}")
        print(f"  metadata_json keys: {list((chunk_meta['metadata_json'] or {}).keys())[:10]}")

    await c.close()


if __name__ == "__main__":
    asyncio.run(main())
