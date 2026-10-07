"""Phase 3: Verify PostgreSQL tables after Alembic migration."""

import asyncio

import asyncpg


async def main() -> None:
    conn = await asyncpg.connect("postgresql://epi:epi@localhost:5432/epi")
    rows = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
    tables = [r["tablename"] for r in rows]
    print("Tables:", tables)
    expected = [
        "agent_traces",
        "alembic_version",
        "answer_records",
        "audit_log",
        "citations",
        "chunks",
        "compliance_certificates",
        "contracts",
        "conversations",
        "document_pages",
        "documents",
        "ingestion_jobs",
        "messages",
        "price_records",
        "procurement_records",
        "products",
        "query_records",
        "suppliers",
        "tenants",
        "users",
    ]
    missing = [t for t in expected if t not in tables]
    if missing:
        print("MISSING:", missing)
    else:
        print("All expected tables present.")
    await conn.close()


asyncio.run(main())
