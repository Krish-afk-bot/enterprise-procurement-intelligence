"""Ingest scanned signature page with OCR enabled into eval DB.

Usage:
    python backend/scripts_phase3/ocr_ingest_scanned.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
SCANNED_PDF = PROJECT_ROOT / "data" / "synthetic" / "supplier_a_scanned_signature_page.pdf"

# Set eval DB environment
EVAL_VAR_ROOT = Path(os.environ.get("EVAL_VAR_DIR", str(BACKEND_DIR / "var" / "eval-v2")))
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{(EVAL_VAR_ROOT / 'eval.db').as_posix()}")
os.environ.setdefault("VAR_DIR", (EVAL_VAR_ROOT / "var").as_posix())
os.environ.setdefault("LOCAL_STORAGE_DIR", (EVAL_VAR_ROOT / "storage").as_posix())
os.environ.setdefault("DB_TYPE", "sqlite")
os.environ.setdefault("SQLITE_DB_PATH", str(EVAL_VAR_ROOT / "eval.db"))
os.environ.setdefault("OCR_ENABLED", "true")  # KEY: enable OCR
os.environ.setdefault("VLM_ENABLED", "false")
os.environ.setdefault("EMBEDDING_PROVIDER", "sentence_transformers")
os.environ.setdefault("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
os.environ.setdefault("RERANKER_ENABLED", "true")
os.environ.setdefault("RERANKER_PROVIDER", "cross_encoder")
os.environ.setdefault("ALLOW_PROVIDER_FALLBACK", "false")
os.environ.setdefault("VECTOR_PROVIDER", "local")
os.environ.setdefault("GRAPH_PROVIDER", "local")
os.environ.setdefault("CACHE_PROVIDER", "memory")
os.environ.setdefault("STORAGE_PROVIDER", "local")

sys.path.insert(0, str(BACKEND_DIR))
from app.config.settings import reset_settings_cache  # noqa: E402

reset_settings_cache()


async def main() -> None:
    from sqlalchemy import select, delete

    from app.config.container import get_container
    from app.config.settings import get_settings
    from app.db.models import Tenant, User, Document, Chunk, DocumentPage
    from app.db.session import session_scope
    from app.ingestion.pipeline import IngestionPipeline
    from app.ingestion.validation import validate_upload
    from app.schemas.documents import UploadSettings
    from app.security.rbac import Principal
    from app.services.documents import store_upload

    settings = get_settings()
    print(f"OCR enabled: {settings.ocr_enabled}")
    print(f"Database: {settings.database_url[:80]}")
    assert settings.ocr_enabled, "OCR_ENABLED must be true"

    container = get_container()
    await container.startup()

    # Get principal
    async with session_scope() as session:
        tenant = (await session.execute(select(Tenant).limit(1))).scalar_one()
        user = (await session.execute(select(User).where(User.tenant_id == tenant.id).limit(1))).scalar_one()

    principal = Principal(
        user_id=user.id,
        tenant_id=tenant.id,
        email=user.email,
        role=user.role,
    )

    # Check if scanned doc already exists and delete it
    async with session_scope() as session:
        existing = (
            await session.execute(
                select(Document).where(Document.filename.ilike("%scanned%"))
            )
        ).scalars().all()
        
        for doc in existing:
            print(f"Deleting existing scanned doc: {doc.id[:20]}...")
            await session.execute(delete(Chunk).where(Chunk.document_id == doc.id))
            await session.execute(delete(DocumentPage).where(DocumentPage.document_id == doc.id))
            await session.delete(doc)
        await session.commit()

    # Ingest with OCR
    raw_bytes = SCANNED_PDF.read_bytes()
    upload = validate_upload(
        filename=SCANNED_PDF.name,
        content=raw_bytes,
        declared_mime="application/pdf",
        settings=settings,
    )

    async with session_scope() as session:
        doc, _job, _existing = await store_upload(
            session=session,
            container=container,
            principal=principal,
            upload=upload,
            settings_payload=UploadSettings(is_synthetic=True),
        )
        await session.commit()
        print(f"Document registered: {doc.id}")

    # Run ingestion pipeline
    pipeline = IngestionPipeline(container, settings)
    print("Running ingestion with OCR=True...")
    outcome = await pipeline.process_document(
        doc.id,
        run_ocr=True,
        run_vision=False,
        rebuild_graph=True,
    )

    print(f"\nStatus: {outcome.status}")
    if outcome.error:
        print(f"ERROR: {outcome.error}")

    # Verify chunks
    async with session_scope() as session:
        chunks = (
            await session.execute(
                select(Chunk).where(Chunk.document_id == doc.id)
            )
        ).scalars().all()

    print(f"\nChunk count: {len(chunks)}")
    if len(chunks) > 0:
        first_chunk = chunks[0]
        preview = first_chunk.content[:200] if first_chunk.content else ""
        print(f"First 200 characters:\n{preview}")
    
    await container.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
