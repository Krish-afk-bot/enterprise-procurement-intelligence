"""Phase 3: Ingest the synthetic corpus into the live infrastructure stack.

Connects to PostgreSQL + Qdrant + Neo4j + Redis + MinIO.
Creates a tenant + admin user, registers each document, and runs
the full ingestion pipeline: parse → chunk → embed → Qdrant + Neo4j + PostgreSQL.

Run from backend/ directory.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC_DIR = PROJECT_ROOT / "data" / "synthetic"

# Set production provider env vars before importing Settings
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
os.environ.setdefault("AUTO_CREATE_SCHEMA", "false")
os.environ.setdefault("ALLOW_PROVIDER_FALLBACK", "false")
os.environ.setdefault("OCR_ENABLED", "false")  # skip OCR; scanned page tested separately
os.environ.setdefault("RERANKER_ENABLED", "false")  # not required for ingestion
os.environ.setdefault("EMBEDDING_PROVIDER", "sentence_transformers")
os.environ.setdefault("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

# Re-initialise settings so the env vars above take effect
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config.settings import reset_settings_cache  # noqa: E402

reset_settings_cache()


def _mime(path: Path) -> str:
    return {
        ".pdf": "application/pdf",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".csv": "text/csv",
    }.get(path.suffix, "application/octet-stream")


async def main() -> None:
    from app.config.container import get_container
    from app.config.settings import get_settings
    from app.db.session import get_session_factory
    from app.ingestion.pipeline import IngestionPipeline
    from app.ingestion.validation import validate_upload
    from app.schemas.documents import UploadSettings
    from app.security.rbac import Principal
    from app.services.auth import create_user, get_or_create_default_tenant, get_user_by_email
    from app.services.documents import store_upload

    settings = get_settings()
    print(f"DB:      {settings.database_url[:55]}...")
    print(f"Vector:  {settings.vector_provider} @ {settings.qdrant_url}")
    print(f"Graph:   {settings.graph_provider} @ {settings.neo4j_uri}")
    print(f"Cache:   {settings.cache_provider}")
    print(f"Storage: {settings.storage_provider} @ {settings.s3_endpoint}")
    print(f"Embed:   {settings.embedding_model}")
    print()

    # Start provider container and verify no fallback
    container = get_container()
    await container.startup()
    if container.fallbacks:
        print(f"ERROR: provider fallback occurred: {[f.as_dict() for f in container.fallbacks]}")
        print("Check that all infrastructure services are running.")
        sys.exit(1)
    print(f"All providers live. Startup errors: {container.startup_errors or 'none'}")

    session_factory = get_session_factory(settings)

    # Bootstrap tenant + user
    async with session_factory() as session:
        tenant = await get_or_create_default_tenant(session, settings)
        print(f"Tenant: {tenant.id} ({tenant.slug})")
        user = await get_user_by_email(session, tenant.id, "admin@epi.local")
        if user is None:
            user = await create_user(
                session,
                tenant_id=tenant.id,
                email="admin@epi.local",
                password="EpiAdmin2026!",
                role="admin",
            )
        print(f"User:   {user.id} ({user.email})")
        await session.commit()

    principal = Principal(
        user_id=user.id,
        tenant_id=tenant.id,
        email=user.email,
        role=user.role,
    )

    # Collect documents to ingest (skip the 6 MB scanned page; OCR is off)
    files_to_ingest = sorted(
        p
        for p in SYNTHETIC_DIR.iterdir()
        if p.suffix in {".pdf", ".xlsx", ".csv"} and "scanned" not in p.name
    )
    print(f"\nIngesting {len(files_to_ingest)} documents...")

    totals: dict[str, int] = {"documents": 0, "chunks": 0, "pages": 0, "errors": 0}

    for path in files_to_ingest:
        raw_bytes = path.read_bytes()
        try:
            upload = validate_upload(
                filename=path.name,
                content=raw_bytes,
                declared_mime=_mime(path),
                settings=settings,
            )
            async with session_factory() as session:
                doc, _job, _existing_id = await store_upload(
                    session=session,
                    container=container,
                    principal=principal,
                    upload=upload,
                    settings_payload=UploadSettings(is_synthetic=True),
                )
                await session.commit()

            # Run the full ingestion pipeline (parse → chunk → embed → upsert)
            pipeline = IngestionPipeline(container, settings)
            outcome = await pipeline.process_document(
                doc.id,
                run_ocr=False,
                run_vision=False,
                rebuild_graph=True,
            )

            totals["documents"] += 1
            chunks = outcome.metrics.get("chunk_count", 0)
            pages = outcome.metrics.get("page_count", 0)
            vecs = outcome.metrics.get("vector_points", 0)
            totals["chunks"] += int(chunks)
            totals["pages"] += int(pages)
            icon = "OK" if outcome.status == "complete" else "WRN"
            print(
                f"  {icon} {path.name:55s}  "
                f"{chunks:3} chunks  "
                f"{pages:2} pages  "
                f"{vecs:3} vecs  "
                f"status={outcome.status}"
            )
            if outcome.warnings:
                for w in outcome.warnings[:2]:
                    print(f"    warn: {w}")
            if outcome.error:
                print(f"    error: {outcome.error}")

        except Exception as exc:  # noqa: BLE001
            totals["errors"] += 1
            print(f"  ERR {path.name}: {type(exc).__name__}: {exc}")

    # Summary
    print("\n--- Ingestion summary ---")
    print(f"Documents ingested : {totals['documents']}")
    print(f"Pages stored       : {totals['pages']}")
    print(f"Chunks indexed     : {totals['chunks']}")
    print(f"Errors             : {totals['errors']}")

    # Qdrant vector count
    try:
        qdrant_count = await container.vector.count("procurement_chunks")
        print(f"Qdrant vectors     : {qdrant_count}")
    except Exception as exc:
        print(f"Qdrant count failed: {exc}")

    await container.shutdown()
    if totals["errors"] == 0:
        print("\nPASS: Corpus ingestion COMPLETE")
    else:
        print(f"\nWARN: Ingestion finished with {totals['errors']} error(s)")


if __name__ == "__main__":
    asyncio.run(main())
