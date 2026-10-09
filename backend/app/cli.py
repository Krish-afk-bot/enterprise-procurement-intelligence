"""Command line interface (``python -m app.cli``).

Commands: initdb, create-user, ingest, stats, worker, ask, evaluate.
Everything runs against the configured providers, so the CLI and the API behave
identically.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import func, select

from app.config.container import Container, get_container, set_container
from app.config.settings import get_settings
from app.db.models import Chunk, Contract, Document, DocumentPage, Price, ProcurementRecord, Supplier
from app.db.session import dispose_engine, init_db, session_scope
from app.ingestion.connectors import import_csv_source
from app.ingestion.pipeline import IngestionPipeline
from app.ingestion.validation import validate_upload
from app.observability.logging import configure_logging, get_logger
from app.services import auth as auth_service
from app.services.documents import store_upload

logger = get_logger(__name__)


async def _bootstrap_container() -> Container:
    settings = get_settings()
    configure_logging(settings.log_level, False)
    container = get_container()
    await container.startup()
    return container


async def cmd_initdb(args: argparse.Namespace) -> int:
    await init_db()
    print("Database schema created (dev/test path; production uses `alembic upgrade head`).")
    return 0


async def cmd_create_user(args: argparse.Namespace) -> int:
    settings = get_settings()
    await init_db()
    async with session_scope() as session:
        tenant = await auth_service.get_or_create_default_tenant(session, settings)
        user = await auth_service.create_user(
            session,
            tenant_id=tenant.id,
            email=args.email,
            password=args.password,
            full_name=args.name or "",
            role=args.role,
        )
        print(f"Created user {user.email} ({user.role}) in tenant '{tenant.slug}' [{tenant.id}]")
        print(f"  user_id: {user.id}")
    return 0


async def cmd_ingest(args: argparse.Namespace) -> int:
    settings = get_settings()
    container = await _bootstrap_container()
    await init_db()

    directory = Path(args.directory)
    if not directory.exists():
        print(f"Directory not found: {directory}", file=sys.stderr)
        return 2
    extensions = (
        {".pdf", ".docx", ".xlsx", ".csv", ".txt", ".md"}
        if not args.images
        else set(settings.allowed_extensions)
    )
    files = sorted(
        path
        for path in directory.rglob("*")
        if path.is_file()
        and path.suffix.lower() in extensions
        and path.name not in {"manifest.json", "corpus_card.json"}
    )
    if not files:
        print(f"No ingestable files found in {directory}", file=sys.stderr)
        return 2

    async with session_scope() as session:
        tenant = await auth_service.get_or_create_default_tenant(session, settings)
        admin = await auth_service.get_user_by_email(session, tenant.id, args.email)
        if admin is None:
            admin = await auth_service.create_user(
                session,
                tenant_id=tenant.id,
                email=args.email,
                password=args.password,
                full_name="Corpus Loader",
                role="admin",
            )
        principal = auth_service.principal_from_user(admin)
        tenant_id = tenant.id

    pipeline = IngestionPipeline(container, settings)
    results: list[dict] = []
    for path in files:
        content = path.read_bytes()

        # CSV files are structured procurement data, not documents: import them as
        # records so aggregation questions are answered by SQL.
        if path.suffix.lower() == ".csv":
            async with session_scope() as session:
                imported = await import_csv_source(
                    session,
                    tenant_id=tenant_id,
                    content=content,
                    source_name=path.name,
                    source_url=f"file://{path.as_posix()}",
                    license="CC0-1.0 (synthetic)" if "synthetic" in str(path).lower() else None,
                    is_synthetic="synthetic" in str(path).lower(),
                )
            print(
                f"[structured] {path.name} -> {imported.records_imported} record(s), "
                f"{imported.suppliers_created} supplier(s) created, {imported.skipped} skipped"
            )
            results.append(imported.as_dict() | {"file": path.name, "status": "structured"})
            continue

        try:
            upload = validate_upload(
                filename=path.name, content=content, declared_mime=None, settings=settings
            )
        except Exception as exc:  # noqa: BLE001
            print(f"SKIP {path.name}: {exc}")
            continue
        from app.schemas.documents import UploadSettings

        async with session_scope() as session:
            document, _job, duplicate_of = await store_upload(
                session,
                container,
                principal,
                upload,
                UploadSettings(
                    is_synthetic="synthetic" in str(path).lower(),
                    source="synthetic_corpus" if "synthetic" in str(path).lower() else "manual_upload",
                    license="CC0-1.0 (synthetic)" if "synthetic" in str(path).lower() else None,
                ),
            )
            document_id = document.id
            title = document.title
        if duplicate_of:
            if not args.reprocess:
                print(f"SKIP {path.name}: already ingested as {duplicate_of}")
                results.append({"file": path.name, "document_id": duplicate_of, "status": "duplicate"})
                continue
            # --reprocess re-runs the pipeline for an unchanged file so parser,
            # chunker or metadata changes take effect without deleting the row.
            print(f"REPROCESS {path.name}: re-running ingestion for {duplicate_of}")
            document_id = duplicate_of
        outcome = await pipeline.process_document(
            document_id, run_ocr=not args.no_ocr, run_vision=not args.no_vision
        )
        results.append(outcome.as_dict() | {"file": path.name, "title": title})
        status = outcome.status
        print(
            f"[{status}] {path.name} -> {document_id} pages={outcome.metrics.get('page_count')} "
            f"chunks={outcome.metrics.get('chunk_count')} prices={outcome.metrics.get('prices')} "
            f"ocr={outcome.metrics.get('ocr')} vision={outcome.metrics.get('vision')}"
        )
        for warning in outcome.warnings:
            print(f"    ! {warning}")

    if args.json:
        print(json.dumps(results, indent=2))

    async with session_scope() as session:
        counts = {
            "documents": await session.scalar(
                select(func.count(Document.id)).where(Document.tenant_id == tenant_id)
            ),
            "pages": await session.scalar(
                select(func.count(DocumentPage.id)).where(DocumentPage.tenant_id == tenant_id)
            ),
            "chunks": await session.scalar(select(func.count(Chunk.id)).where(Chunk.tenant_id == tenant_id)),
            "chunks_embedded": await session.scalar(
                select(func.count(Chunk.id)).where(
                    Chunk.tenant_id == tenant_id, Chunk.embedding_indexed.is_(True)
                )
            ),
            "suppliers": await session.scalar(
                select(func.count(Supplier.id)).where(Supplier.tenant_id == tenant_id)
            ),
            "contracts": await session.scalar(
                select(func.count(Contract.id)).where(Contract.tenant_id == tenant_id)
            ),
            "prices": await session.scalar(select(func.count(Price.id)).where(Price.tenant_id == tenant_id)),
            "procurement_records": await session.scalar(
                select(func.count(ProcurementRecord.id)).where(ProcurementRecord.tenant_id == tenant_id)
            ),
        }
    print("\nCorpus totals:")
    for key, value in counts.items():
        print(f"  {key:>18}: {value}")
    print(f"\nVector index: {await container.vector.status()}")
    print(f"Graph store : {await container.graph.status()}")
    await container.shutdown()
    await dispose_engine()
    return 0


async def cmd_stats(args: argparse.Namespace) -> int:
    container = await _bootstrap_container()
    await init_db()
    async with session_scope() as session:
        total_docs = await session.scalar(select(func.count(Document.id)))
        total_chunks = await session.scalar(select(func.count(Chunk.id)))
        embedded = await session.scalar(select(func.count(Chunk.id)).where(Chunk.embedding_indexed.is_(True)))
    print(f"documents={total_docs} chunks={total_chunks} chunks_embedded={embedded}")
    print(f"vector: {await container.vector.status()}")
    print(f"graph : {await container.graph.status()}")
    print(f"sparse: {await container.sparse.status()}" if container.sparse else "sparse: none")
    print(f"cache : {await container.cache.status()}" if container.cache else "cache: none")
    print("providers:")
    for name, status in (await container.provider_statuses()).items():
        print(f"  {name:<10} available={status.available} model={status.model} detail={status.detail}")
    await container.shutdown()
    await dispose_engine()
    return 0


async def cmd_worker(args: argparse.Namespace) -> int:
    from app.workers.ingestion_worker import run_worker_forever

    await run_worker_forever()
    return 0


async def cmd_ask(args: argparse.Namespace) -> int:
    from app.agents.pipeline import AnswerPipeline

    settings = get_settings()
    container = await _bootstrap_container()
    await init_db()
    async with session_scope() as session:
        tenant = await auth_service.get_or_create_default_tenant(session, settings)
        user = await auth_service.get_user_by_email(session, tenant.id, args.email)
        if user is None:
            print(f"No user {args.email}", file=sys.stderr)
            return 2
        principal = auth_service.principal_from_user(user)
    pipeline = AnswerPipeline(container, settings)
    result = await pipeline.answer(principal, args.question, debug=args.debug)
    print(result.answer_text)
    print()
    print("Evidence:")
    for citation in result.citations:
        print(f"  - {citation.label} [{citation.evidence_type}]")
    if result.conflicts:
        print("\nConflicts:")
        for conflict in result.conflicts:
            print(f"  ! {conflict.description}")
            print(f"    resolution: {conflict.resolution}")
    print(
        f"\nstatus={result.status} generation_mode={result.generation_mode} "
        f"evidence_strength={result.evidence_strength.level} citations={len(result.citations)} "
        f"grounding={result.grounding.supported_claims}/{result.grounding.total_claims} "
        f"({result.grounding.method})"
    )
    for reason in result.degradation_reasons:
        print(f"  ! {reason}")
    await container.shutdown()
    await dispose_engine()
    return 0


async def cmd_evaluate(args: argparse.Namespace) -> int:
    from app.evaluation.runner import EvaluationRunner

    settings = get_settings()
    container = await _bootstrap_container()
    await init_db()
    async with session_scope() as session:
        tenant = await auth_service.get_or_create_default_tenant(session, settings)
        user = await auth_service.get_user_by_email(session, tenant.id, args.email)
        if user is None:
            print(f"No user {args.email}", file=sys.stderr)
            return 2
        principal = auth_service.principal_from_user(user)
    runner = EvaluationRunner(container, settings)
    run = await runner.run(
        principal,
        experiments=args.experiments,
        categories=args.categories or None,
        max_questions=args.max_questions,
    )
    print(json.dumps(run, indent=2, default=str))
    await container.shutdown()
    await dispose_engine()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="epi", description="Enterprise Procurement Intelligence CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("initdb", help="Create the database schema").set_defaults(func=cmd_initdb)

    create = sub.add_parser("create-user", help="Create a user in the default tenant")
    create.add_argument("--email", required=True)
    create.add_argument("--password", required=True)
    create.add_argument("--name", default="")
    create.add_argument("--role", default="buyer")
    create.set_defaults(func=cmd_create_user)

    ingest = sub.add_parser("ingest", help="Ingest a directory of documents")
    ingest.add_argument("directory", help="Directory containing documents")
    ingest.add_argument("--images", action="store_true", help="Include image uploads")
    ingest.add_argument(
        "--reprocess", action="store_true", help="Re-run ingestion for files that are already in the corpus"
    )
    ingest.add_argument("--no-ocr", action="store_true")
    ingest.add_argument("--no-vision", action="store_true")
    ingest.add_argument("--email", default="admin@epi.local")
    ingest.add_argument("--password", default="admin-local-password")
    ingest.add_argument("--json", action="store_true")
    ingest.set_defaults(func=cmd_ingest)

    stats = sub.add_parser("stats", help="Print corpus and provider statistics")
    stats.set_defaults(func=cmd_stats)

    worker = sub.add_parser("worker", help="Run the ingestion worker")
    worker.set_defaults(func=cmd_worker)

    ask = sub.add_parser("ask", help="Ask a question from the command line")
    ask.add_argument("question")
    ask.add_argument("--email", default="admin@epi.local")
    ask.add_argument("--debug", action="store_true")
    ask.set_defaults(func=cmd_ask)

    evaluate = sub.add_parser("evaluate", help="Run the evaluation suite")
    evaluate.add_argument("--experiments", nargs="+", default=["hybrid_rerank"])
    evaluate.add_argument("--categories", nargs="*", default=None)
    evaluate.add_argument("--max-questions", type=int, default=None)
    evaluate.add_argument("--email", default="admin@epi.local")
    evaluate.set_defaults(func=cmd_evaluate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return asyncio.run(args.func(args))
    except KeyboardInterrupt:
        return 130
    finally:
        set_container(None)


if __name__ == "__main__":
    raise SystemExit(main())
