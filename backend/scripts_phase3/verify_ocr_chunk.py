"""Verify OCR chunk content in PostgreSQL."""

import asyncio

import asyncpg


async def main() -> None:
    c = await asyncpg.connect("postgresql://epi:epi@localhost:5432/epi")
    rows = await c.fetch(
        "SELECT c.id, c.content, d.filename "
        "FROM chunks c JOIN documents d ON d.id = c.document_id "
        "WHERE d.filename ILIKE $1",
        "%scanned%",
    )
    print(f"Scanned chunks: {len(rows)}")
    for r in rows:
        print(f"\nFilename: {r['filename']}")
        print(f"Content:\n{r['content']}")
        for kw in ["Alvarez", "2024-01-08", "APPROVED"]:
            found = kw.lower() in r["content"].lower()
            print(f"  keyword '{kw}': {'FOUND' if found else 'NOT FOUND'}")
    await c.close()


if __name__ == "__main__":
    asyncio.run(main())
