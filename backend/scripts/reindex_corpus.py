"""Re-ingest every source document and audit chunk coverage page by page.

Runs the real pipeline (parse → OCR/VLM → metadata → chunk → embed → index →
graph) for each stored document, then measures how much of each page actually
reached a chunk. It never deletes documents, users, tenants, contracts or
suppliers: only the derived rows/vectors that `process_document` replaces for
the document being rebuilt.

    python scripts/reindex_corpus.py --out ../data/evaluation/benchmark_v4
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from app.config.container import get_container  # noqa: E402
from app.config.settings import get_settings  # noqa: E402
from app.db.models import Chunk, Document, DocumentPage, IngestionJob  # noqa: E402
from app.db.session import dispose_engine, session_scope  # noqa: E402
from app.ingestion.pipeline import IngestionPipeline  # noqa: E402

PROJECT_ROOT = ROOT.parent
NGRAM = 5

# Windows consoles default to cp1252 and crash while logging document text.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - non-TTY streams
        pass


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def ngrams(text: str, size: int = NGRAM) -> set[str]:
    text = normalize(text)
    if len(text) < size:
        return {text} if text else set()
    return {text[i : i + size] for i in range(len(text) - size + 1)}


def page_texts(raw: str | None, ocr: str | None) -> str:
    parts = [part for part in (raw, ocr) if part and part.strip()]
    if len(parts) == 2 and normalize(parts[0]) == normalize(parts[1]):
        return parts[0]
    return "\n".join(parts)


async def audit_document(document_id: str) -> dict[str, Any]:
    async with session_scope() as session:
        document = await session.get(Document, document_id)
        pages = (
            await session.execute(
                select(DocumentPage)
                .where(DocumentPage.document_id == document_id)
                .order_by(DocumentPage.page_number)
            )
        ).scalars().all()
        chunks = (
            await session.execute(
                select(Chunk).where(
                    Chunk.document_id == document_id,
                    Chunk.is_active == True,  # noqa: E712
                )
            )
        ).scalars().all()
        job = (
            await session.execute(
                select(IngestionJob)
                .where(IngestionJob.document_id == document_id)
                .order_by(IngestionJob.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    chunk_by_page: dict[int | None, list[Chunk]] = {}
    for chunk in chunks:
        chunk_by_page.setdefault(chunk.page_number, []).append(chunk)

    page_reports = []
    total_page_chars = 0
    covered_page_chars = 0
    pages_with_text = 0
    pages_with_chunk = 0
    pages_without_chunk: list[int] = []

    for page in pages:
        text = page_texts(page.raw_text, page.ocr_text)
        size = len(normalize(text))
        if size:
            pages_with_text += 1
            total_page_chars += size
        page_chunks = chunk_by_page.get(page.page_number, [])
        chunk_text = "\n".join(chunk.content for chunk in page_chunks)
        page_ngrams = ngrams(text)
        chunk_ngrams = ngrams(chunk_text)
        covered = len(page_ngrams & chunk_ngrams)
        coverage = covered / len(page_ngrams) if page_ngrams else None
        if page_chunks and size:
            pages_with_chunk += 1
            covered_page_chars += round((coverage or 0) * size)
        elif size:
            pages_without_chunk.append(page.page_number)

        layout = page.layout or {}
        detected_tables = int(layout.get("table_count") or 0)
        table_chunks = sum(1 for chunk in page_chunks if chunk.content_type == "table")
        page_reports.append(
            {
                "page": page.page_number,
                "chars": size,
                "chunks": len(page_chunks),
                "char_coverage": round(coverage, 4) if coverage is not None else None,
                "tables_detected": detected_tables,
                "table_chunks": table_chunks,
                "extraction_method": page.extraction_method,
                "is_scanned": page.is_scanned,
                "ocr_chars": len(page.ocr_text or ""),
                "has_text_layer": page.has_text_layer,
            }
        )

    contents = [chunk.content for chunk in chunks]
    empty = sum(1 for content in contents if not content.strip())
    duplicates = len(contents) - len(set(contents))
    oversized = sum(
        1 for chunk in chunks if chunk.token_count > get_settings().chunk_max_tokens
    )
    no_page = sum(1 for chunk in chunks if chunk.page_number is None)
    no_page_id = sum(1 for chunk in chunks if chunk.page_id is None)
    no_index = sum(1 for chunk in chunks if not chunk.chunk_index)

    return {
        "document_id": document_id,
        "filename": document.filename if document else None,
        "status": document.status if document else None,
        "page_count": document.page_count if document else None,
        "pages_persisted": len(pages),
        "pages_with_text": pages_with_text,
        "pages_with_chunk": pages_with_chunk,
        "pages_without_chunk": pages_without_chunk,
        "page_chunk_rate": round(pages_with_chunk / pages_with_text, 4) if pages_with_text else None,
        "chars": total_page_chars,
        "char_coverage": round(covered_page_chars / total_page_chars, 4) if total_page_chars else None,
        "chunks": len(chunks),
        "chunk_tokens": sum(chunk.token_count for chunk in chunks),
        "table_chunks": sum(1 for chunk in chunks if chunk.content_type == "table"),
        "empty_chunks": empty,
        "duplicate_chunks": duplicates,
        "oversized_chunks": oversized,
        "chunks_without_page": no_page,
        "chunks_without_page_id": no_page_id,
        "chunks_without_index": no_index,
        "embedding_indexed": sum(1 for chunk in chunks if chunk.embedding_indexed),
        "types": dict(Counter(chunk.content_type for chunk in chunks)),
        "pages": page_reports,
        "job_status": job.status if job else None,
        "job_error": job.error_message if job else None,
        "job_metrics": (job.metrics if job else None),
    }


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(PROJECT_ROOT / "data" / "evaluation" / "benchmark_v4"))
    parser.add_argument("--only", nargs="*", help="filenames to rebuild (default: all)")
    parser.add_argument("--idempotency-doc", default="064670_tender_1.html")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    settings = get_settings()
    container = get_container()
    await container.startup()
    pipeline = IngestionPipeline(container, settings)

    async with session_scope() as session:
        docs = (
            await session.execute(select(Document).order_by(Document.filename))
        ).scalars().all()
        targets = [
            (doc.id, doc.filename)
            for doc in docs
            if not args.only or doc.filename in set(args.only)
        ]

    started = datetime.now(UTC)
    results: list[dict[str, Any]] = []
    for index, (document_id, filename) in enumerate(targets, start=1):
        stage_times: list[dict[str, Any]] = []
        began = time.perf_counter()

        async def progress(
            stage: str,
            fraction: float,
            _times: list[dict[str, Any]] = stage_times,
            _start: float = began,
            **_kwargs: Any,
        ) -> None:
            _times.append(
                {"stage": stage, "fraction": round(fraction, 2), "at_ms": int((time.perf_counter() - _start) * 1000)}
            )

        print(f"[{index}/{len(targets)}] {filename}", flush=True)
        outcome = await pipeline.process_document(
            document_id, progress=progress, job_id=None
        )
        elapsed = time.perf_counter() - began
        audit = await audit_document(document_id)
        audit.update(
            {
                "ingest_status": outcome.status,
                "ingest_error": outcome.error,
                "warnings": outcome.warnings,
                "stage_metrics": outcome.metrics,
                "stage_timings_ms": stage_times,
                "duration_ms": int(elapsed * 1000),
            }
        )
        results.append(audit)
        print(
            f"    status={outcome.status} pages={audit['pages_with_chunk']}/{audit['pages_with_text']} "
            f"chunks={audit['chunks']} coverage={audit['char_coverage']} "
            f"err={outcome.error} in {elapsed:.1f}s",
            flush=True,
        )

    # Idempotency: re-ingest one document and confirm identical ids and counts.
    idempotency: dict[str, Any] = {}
    if not args.only and args.idempotency_doc:
        async with session_scope() as session:
            doc = (
                await session.execute(
                    select(Document).where(Document.filename == args.idempotency_doc)
                )
            ).scalar_one_or_none()
        if doc is not None:
            async with session_scope() as session:
                before = [
                    chunk.id
                    for chunk in (
                        await session.execute(
                            select(Chunk).where(
                                Chunk.document_id == doc.id, Chunk.is_active == True  # noqa: E712
                            )
                        )
                    ).scalars()
                ]
            first = await pipeline.process_document(doc.id, job_id=None)
            async with session_scope() as session:
                after = [
                    chunk.id
                    for chunk in (
                        await session.execute(
                            select(Chunk).where(
                                Chunk.document_id == doc.id, Chunk.is_active == True  # noqa: E712
                            )
                        )
                    ).scalars()
                ]
            idempotency = {
                "document": args.idempotency_doc,
                "status": first.status,
                "chunks_before": len(before),
                "chunks_after": len(after),
                "same_count": len(before) == len(after),
                "same_ids": sorted(before) == sorted(after),
                "ids_sample": sorted(after)[:5],
            }
            print(f"idempotency: {json.dumps(idempotency)}", flush=True)

    await container.shutdown()
    await dispose_engine()

    finished = datetime.now(UTC)
    summary = {
        "generated_at": finished.isoformat(),
        "started_at": started.isoformat(),
        "duration_seconds": round((finished - started).total_seconds(), 1),
        "documents": len(results),
        "chunks": sum(item["chunks"] for item in results),
        "pages": sum(item["pages_persisted"] for item in results),
        "pages_with_text": sum(item["pages_with_text"] for item in results),
        "pages_with_chunk": sum(item["pages_with_chunk"] for item in results),
        "char_coverage": (
            round(
                sum((item["char_coverage"] or 0) * item["chars"] for item in results)
                / max(1, sum(item["chars"] for item in results)),
                4,
            )
            if results
            else None
        ),
        "failed": [item["filename"] for item in results if item["status"] != "indexed"],
        "below_page_target": [
            item["filename"]
            for item in results
            if (item["page_chunk_rate"] or 0) < 1.0
        ],
        "below_char_target": [
            item["filename"]
            for item in results
            if item["chars"] and (item["char_coverage"] or 0) < 0.99
        ],
        "idempotency": idempotency,
        "documents_detail": results,
    }
    (out / "coverage_report.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )

    lines = [
        "# Chunk coverage audit",
        "",
        f"Generated {summary['generated_at']} in {summary['duration_seconds']} s.",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Documents rebuilt | {summary['documents']} |",
        f"| Pages | {summary['pages']} |",
        f"| Pages with text / with ≥1 chunk | {summary['pages_with_text']} / {summary['pages_with_chunk']} |",
        f"| Chunks | {summary['chunks']} |",
        f"| Character coverage (5-gram, overlap excluded) | {summary['char_coverage']:.2%} |",
        f"| Documents below 100% page coverage | {len(summary['below_page_target'])} |",
        f"| Documents below 99% char coverage | {len(summary['below_char_target'])} |",
        "",
        "## Per document",
        "",
        "| Document | Status | Pages | Pages w/ chunk | Chars | Char cov. | Chunks | Table chunks | Empty | Dup | No page |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in results:
        lines.append(
            f"| {item['filename']} | {item['ingest_status']} | {item['pages_persisted']} | "
            f"{item['pages_with_chunk']}/{item['pages_with_text']} | {item['chars']} | "
            f"{(item['char_coverage'] or 0):.2%} | {item['chunks']} | {item['table_chunks']} | "
            f"{item['empty_chunks']} | {item['duplicate_chunks']} | {item['chunks_without_page']} |"
        )

    lines += ["", "## Documents with loss", ""]
    if not summary["below_page_target"] and not summary["below_char_target"]:
        lines.append("None: every page with text produced at least one chunk and every page reached 99% character coverage.")
    else:
        for item in results:
            if (item["page_chunk_rate"] or 0) >= 1.0 and (item["char_coverage"] or 0) >= 0.99:
                continue
            lines.append(
                f"- **{item['filename']}** — pages without chunks: {item['pages_without_chunk'] or 'none'}; "
                f"character coverage {(item['char_coverage'] or 0):.2%}; warnings: "
                f"{'; '.join(item['warnings']) or 'none'}"
            )

    lines += ["", "## Idempotency", ""]
    if idempotency:
        lines.append(
            f"Re-ingesting `{idempotency['document']}` produced "
            f"{idempotency['chunks_after']} chunks (was {idempotency['chunks_before']}); "
            f"same ids: **{idempotency['same_ids']}**."
        )
    else:
        lines.append("Not run.")

    lines += [
        "",
        "## Known provenance gaps",
        "",
        "- Chunk rows carry document id, page number and page id, but the schema has no character offsets,",
        "  bounding boxes or per-page table coordinates populated for text chunks. Table chunks keep their",
        "  headers and markdown but not coordinates.",
        "- Page numbers are the parser's physical page numbering; HTML notices are one logical page.",
        "",
    ]
    (out / "coverage_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({key: summary[key] for key in summary if key != "documents_detail"}, indent=2))
    print(f"wrote {out/'coverage_report.json'}")
    # Keep the manifest checksum in the report for reproducibility.
    print("sha256:", hashlib.sha256((out / "coverage_report.json").read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
