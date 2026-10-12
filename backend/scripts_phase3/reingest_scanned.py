"""Phase 5 Stage 2: Re-ingest the scanned signature page with OCR enabled.

The document was previously ingested with OCR_ENABLED=false, producing 0 chunks.
This script re-ingests it via the full pipeline with OCR on.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCANNED_PDF = PROJECT_ROOT / "data" / "synthetic" / "supplier_a_scanned_signature_page.pdf"

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
os.environ.setdefault("OCR_ENABLED", "true")  # KEY: OCR on
os.environ.setdefault("RERANKER_ENABLED", "false")
os.environ.setdefault("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
os.environ.setdefault("AUTO_CREATE_SCHEMA", "false")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config.settings import reset_settings_cache  # noqa: E402

reset_settings_cache()


async def main() -> None:
    import asyncpg

    from app.config.container import get_container
    from app.config.settings import get_settings
    from app.db.session import get_session_factory
    from app.ingestion.pipeline import IngestionPipeline
    from app.ingestion.validation import validate_upload
    from app.schemas.documents import UploadSettings
    from app.security.rbac import Principal
    from app.services.documents import store_upload

    settings = get_settings()
    print(f"OCR enabled: {settings.ocr_enabled}")
    assert settings.ocr_enabled, "OCR_ENABLED must be true"

    container = get_container()
    await container.startup()
    print(f"Providers: vector={container.vector.name} fallbacks={[f.kind for f in container.fallbacks]}")

    pg = await asyncpg.connect("postgresql://epi:epi@localhost:5432/epi")
    tenant_row = await pg.fetchrow("SELECT id FROM tenants LIMIT 1")
    user_row = await pg.fetchrow("SELECT id, role FROM users LIMIT 1")

    # Check current state of the scanned document
    existing = await pg.fetch(
        "SELECT d.id, d.status, count(c.id) AS chunk_count "
        "FROM documents d LEFT JOIN chunks c ON c.document_id = d.id "
        "WHERE d.filename ILIKE $1 GROUP BY d.id, d.status",
        "%scanned%",
    )
    print("\nCurrent state of scanned document:")
    for r in existing:
        print(f"  doc={r['id'][:20]}... status={r['status']} chunks={r['chunk_count']}")

    await pg.close()

    principal = Principal(
        user_id=user_row["id"],
        tenant_id=tenant_row["id"],
        email="admin@epi.local",
        role=user_row["role"],
    )

    session_factory = get_session_factory(settings)
    raw_bytes = SCANNED_PDF.read_bytes()

    # Delete the old document record so we can re-ingest cleanly
    if existing:
        pg2 = await asyncpg.connect("postgresql://epi:epi@localhost:5432/epi")
        for r in existing:
            doc_id = r["id"]
            await pg2.execute("DELETE FROM chunks WHERE document_id = $1", doc_id)
            await pg2.execute("DELETE FROM document_pages WHERE document_id = $1", doc_id)
            await pg2.execute("DELETE FROM ingestion_jobs WHERE document_id = $1", doc_id)
            await pg2.execute("DELETE FROM documents WHERE id = $1", doc_id)
            print(f"Removed old document record {doc_id[:20]}...")
        await pg2.close()

    # Re-ingest with OCR enabled
    upload = validate_upload(
        filename=SCANNED_PDF.name,
        content=raw_bytes,
        declared_mime="application/pdf",
        settings=settings,
    )
    async with session_factory() as session:
        doc, _job, _existing = await store_upload(
            session=session,
            container=container,
            principal=principal,
            upload=upload,
            settings_payload=UploadSettings(is_synthetic=True),
        )
        await session.commit()
        print(f"\nDocument registered: {doc.id}")

    # Run full ingestion pipeline with OCR
    pipeline = IngestionPipeline(container, settings)
    print("Running ingestion with OCR=True...")
    outcome = await pipeline.process_document(
        doc.id,
        run_ocr=True,
        run_vision=False,
        rebuild_graph=True,
    )

    print("\nIngestion outcome:")
    print(f"  status: {outcome.status}")
    print(f"  stages: {outcome.stages}")
    print(f"  metrics: {outcome.metrics}")
    if outcome.warnings:
        for w in outcome.warnings[:3]:
            print(f"  warn: {w}")
    if outcome.error:
        print(f"  ERROR: {outcome.error}")

    # Verify results in DB
    pg3 = await asyncpg.connect("postgresql://epi:epi@localhost:5432/epi")
    chunks = await pg3.fetch(
        "SELECT id, left(content, 120) AS preview, page_number, embedding_indexed "
        "FROM chunks WHERE document_id = $1",
        doc.id,
    )
    pages = await pg3.fetch(
        "SELECT page_number, left(coalesce(ocr_text, raw_text, ''), 80) AS preview "
        "FROM document_pages WHERE document_id = $1",
        doc.id,
    )
    await pg3.close()

    print(f"\nChunks created: {len(chunks)}")
    for c in chunks:
        print(f"  p{c['page_number']} embedded={c['embedding_indexed']}: {c['preview']!r}")

    print(f"\nPages stored: {len(pages)}")
    for p in pages:
        print(f"  p{p['page_number']}: {p['preview']!r}")

    qdrant_count = await container.vector.count("procurement_chunks")
    print(f"\nQdrant total vectors (procurement_chunks): {qdrant_count}")

    # Keyword check in chunk content
    all_text = " ".join(c["preview"] for c in chunks)
    for kw in ["Alvarez", "2024-01-08", "APPROVED"]:
        found = kw.lower() in all_text.lower()
        print(f"  keyword '{kw}': {'FOUND in chunks' if found else 'NOT FOUND'}")

    await container.shutdown()

    if outcome.status in ("complete", "indexed") and len(chunks) > 0:
        print("\nPASS: Scanned document re-indexed with OCR content")
    else:
        print(f"\nFAIL: status={outcome.status} chunks={len(chunks)}")


if __name__ == "__main__":
    asyncio.run(main())
