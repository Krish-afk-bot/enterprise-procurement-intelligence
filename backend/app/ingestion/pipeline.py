"""Ingestion pipeline (PRD s.21).

    stored file → parse → OCR → selective VLM → pages persisted (with images)
    → structure detection → metadata extraction → structured facts
    → chunking → contextual enrichment → embeddings → vector index
    → keyword index → graph → document marked indexed

Each stage records what it did, what it skipped and why. A stage that cannot run
(no OCR engine, no LLM, no VLM) degrades the document's *reported* capability
instead of silently pretending the work happened.
"""

from __future__ import annotations

import os
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.container import Container
from app.config.settings import Settings
from app.core.errors import NotFoundError
from app.core.ids import normalize_name
from app.db.models import (
    Chunk,
    ComplianceCertificate,
    Contract,
    Document,
    DocumentPage,
    Price,
    Product,
    Supplier,
    TableRecord,
)
from app.db.session import session_scope
from app.graph.builder import GraphBuilder
from app.ingestion.chunking import ChunkDraft, chunk_document
from app.ingestion.contextualizer import contextual_text, enrich_drafts
from app.ingestion.extractors import ExtractionResult, extract_structured
from app.ingestion.layout import detect_structure
from app.ingestion.metadata import ExtractedMetadata, extract_metadata
from app.ingestion.ocr import OcrEngine
from app.ingestion.parsers import parse_document
from app.ingestion.types import EXTRACTION_VLM, ParsedDocument
from app.observability.logging import get_logger
from app.providers.types import GraphNode, VectorPoint
from app.services.reconciliation import reconcile_attribution

logger = get_logger(__name__)

ProgressCallback = Callable[[str, float], Awaitable[None]]

PAGE_VISION_PROMPT = (
    "This is page {page} of a procurement document. Extract, verbatim where possible: any prices, "
    "currencies, quantities, discounts, payment or delivery terms, table contents, stamps, "
    "signatures, dates and clause numbers. Reply as compact lines of 'label: value'. If a value is "
    "unreadable, say 'unreadable' for it. Do not add commentary."
)

CHUNK_COLLECTION = "procurement_chunks"


@dataclass
class IngestionOutcome:
    document_id: str
    status: str
    stages: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "status": self.status,
            "stages": self.stages,
            "metrics": self.metrics,
            "warnings": self.warnings,
            "error": self.error,
        }


class IngestionPipeline:
    def __init__(self, container: Container, settings: Settings) -> None:
        self.container = container
        self.settings = settings
        self.ocr = OcrEngine(
            enabled=settings.ocr_enabled,
            language=settings.ocr_language,
            use_onednn=settings.ocr_use_onednn,
        )
        self.graph_builder = GraphBuilder(container.graph)
        #: Set per document so supplier-alias extraction can see the source name.
        self._current_filename: str = ""

    # ------------------------------------------------------------------ entry
    async def process_document(
        self,
        document_id: str,
        *,
        run_ocr: bool | None = None,
        run_vision: bool | None = None,
        rebuild_graph: bool = True,
        progress: ProgressCallback | None = None,
    ) -> IngestionOutcome:
        started = time.perf_counter()
        outcome = IngestionOutcome(document_id=document_id, status="processing")
        ocr_enabled = self.settings.ocr_enabled if run_ocr is None else run_ocr
        vision_enabled = self.settings.vision_escalation_enabled if run_vision is None else run_vision

        async def report(stage: str, fraction: float) -> None:
            outcome.stages.append(stage)
            if progress is not None:
                await progress(stage, fraction)

        try:
            async with session_scope() as session:
                document = await session.get(Document, document_id)
                if document is None:
                    raise NotFoundError(f"Document {document_id} does not exist.")
                document.status = "processing"
                document.stage = "load"
                document.progress = 0.02
                tenant_id = document.tenant_id
                storage_key = document.storage_key or ""
                mime_type = document.mime_type or "application/octet-stream"
                filename = document.filename
                self._current_filename = filename
            await report("load", 0.02)

            content = await self.container.storage.get(storage_key)

            # ------------------------------------------------------------ 1. parse
            parsed = await self._parse(content, mime_type=mime_type, filename=filename)
            outcome.metrics["parser"] = parsed.metadata.get("parser")
            outcome.metrics["page_count"] = parsed.page_count
            outcome.metrics["page_numbering"] = parsed.metadata.get("page_numbering", "physical")
            outcome.warnings.extend(parsed.warnings)
            await report("parse", 0.15)

            # -------------------------------------------------------- 2. OCR/VLM
            await self._apply_ocr(parsed, enabled=ocr_enabled, outcome=outcome)
            await report("ocr", 0.3)
            await self._apply_vision(parsed, enabled=vision_enabled, outcome=outcome)
            await report("vision", 0.4)

            # ---------------------------------------------- 3. metadata + structure
            async with session_scope() as session:
                document = await session.get(Document, document_id)
                assert document is not None
                meta = extract_metadata(
                    parsed,
                    filename=document.filename,
                    declared_type=None if document.document_type in {None, "", "other"} else document.document_type,
                )
                structure = detect_structure(parsed)
                extraction = extract_structured(parsed, meta)
                outcome.metrics["sections"] = len(structure.sections)
                outcome.metrics["detected_type"] = meta.document_type

            # Amendments and price schedules name the contract but not the
            # supplier, so the contract is resolved first and used to attribute
            # the supplier when the text does not name one.
            contract = await self._resolve_contract(tenant_id, meta)
            supplier = await self._resolve_supplier(tenant_id, meta, contract)
            await report("metadata", 0.48)

            # -------------------------------------------------- 4. persist pages
            async with session_scope() as session:
                document = await session.get(Document, document_id)
                assert document is not None
                await self._delete_existing_artifacts(session, document)
                page_ids = await self._persist_pages(session, document, parsed, tenant_id)
                document.title = document.title or meta.title or filename
                document.document_type = meta.document_type
                document.effective_date = meta.effective_date or document.effective_date
                document.expiry_date = meta.expiry_date or document.expiry_date
                document.version = document.version if document.version > 1 else (meta.version or 1)
                document.revision_label = document.revision_label or meta.revision_label
                document.supplier_id = supplier.id if supplier else document.supplier_id
                document.contract_id = contract.id if contract else document.contract_id
                document.page_count = parsed.page_count
                document.scanned_page_count = parsed.scanned_page_count
                document.ocr_applied = outcome.metrics.get("ocr_pages", 0) > 0
                document.vision_applied = outcome.metrics.get("vision_pages", 0) > 0
                document.extraction_metadata = {
                    "metadata": meta.as_dict(),
                    "parser": parsed.metadata,
                    "page_numbering": parsed.metadata.get("page_numbering", "physical"),
                    "warnings": outcome.warnings,
                }
                for page in parsed.pages:
                    page_id = page_ids.get(page.page_number)
                    if page_id is None:
                        continue
                    if (page.ocr_text or "").strip():
                        await session.execute(
                            DocumentPage.__table__.update()
                            .where(DocumentPage.id == page_id)
                            .values(ocr_text=page.ocr_text)
                        )
            await report("persist_pages", 0.58)

            # ------------------------------------------------------- 5. chunking
            drafts = chunk_document(parsed, structure, self.settings)
            enrich_drafts(
                drafts,
                document_title=meta.title or filename,
                document_type=meta.document_type,
                supplier_name=supplier.name if supplier else meta.supplier_name,
                contract_number=contract.contract_number if contract else meta.contract_number,
                version=contract.version if contract else meta.version,
                is_synthetic=meta.is_synthetic,
                settings=self.settings,
            )
            outcome.metrics["chunk_count"] = len(drafts)
            await report("chunking", 0.66)

            # ---------------------------------------------------- 6. embeddings
            embeddings_available = await self._embed_drafts(drafts, outcome)
            await report("embedding", 0.78)

            # ------------------------------------------------- 7. persist chunks
            table_ids = await self._persist_chunks(
                drafts,
                tenant_id=tenant_id,
                document_id=document_id,
                page_ids=page_ids,
                supplier_id=supplier.id if supplier else None,
                contract_id=contract.id if contract else None,
                meta=meta,
            )
            await report("persist_chunks", 0.84)

            # ------------------------------------------------------- 8. indexing
            indexed_points = await self._index_chunks(drafts, tenant_id=tenant_id, document_id=document_id, outcome=outcome)
            outcome.metrics["vector_points"] = indexed_points
            await self.container.sparse.invalidate(tenant_id) if self.container.sparse else None
            await report("vector_index", 0.9)

            # ------------------------------------------- 9. structured facts + graph
            counts = await self._persist_structured(
                tenant_id=tenant_id,
                document_id=document_id,
                supplier=supplier,
                contract=contract,
                extraction=extraction,
                meta=meta,
                table_ids=table_ids,
            )
            outcome.metrics.update(counts)
            if rebuild_graph:
                await self._update_graph(tenant_id, document_id, supplier, contract, counts)
            # Link whatever became knowable now (an amendment indexed before its
            # master agreement, a sheet that names only the contract, ...).
            async with session_scope() as session:
                reconciled = await reconcile_attribution(session, tenant_id, graph=self.container.graph)
            outcome.metrics["attribution"] = {key: value for key, value in (reconciled or {}).items() if value}
            if counts.get("prices_unattributed"):
                outcome.warnings.append(
                    f"{counts['prices_unattributed']} price row(s) have no supplier yet: the document names the "
                    "contract but the supplier is not known. They will be attributed automatically once the "
                    "contract's supplier is indexed."
                )
            await report("structured_and_graph", 0.96)

            # ------------------------------------------------------- 10. finalise
            async with session_scope() as session:
                document = await session.get(Document, document_id)
                assert document is not None
                document.status = "indexed" if embeddings_available else "needs_review"
                document.stage = "indexed" if embeddings_available else "indexed_without_embeddings"
                document.progress = 1.0
                document.chunk_count = len(drafts)
                document.table_count = sum(1 for draft in drafts if draft.content_type == "table")
                document.error_message = None
            outcome.status = "indexed" if embeddings_available else "needs_review"
            if not drafts:
                outcome.status = "needs_review"
                outcome.warnings.append(
                    "No text could be extracted from this file, so there is nothing to index. "
                    f"Parser={outcome.metrics.get('parser')}, OCR={outcome.metrics.get('ocr')}, "
                    f"vision={outcome.metrics.get('vision')}. Enable OCR or configure a VLM, then re-run indexing."
                )
            elif not embeddings_available:
                outcome.warnings.append(
                    "Embeddings were not produced (embedding provider unavailable): the document is "
                    "keyword-searchable only until embeddings can be generated."
                )
            await report("done", 1.0)
        except Exception as exc:  # noqa: BLE001
            logger.error("ingestion_failed", document_id=document_id, error=str(exc), exc_info=True)
            outcome.status = "failed"
            outcome.error = f"{type(exc).__name__}: {exc}"
            async with session_scope() as session:
                document = await session.get(Document, document_id)
                if document is not None:
                    document.status = "failed"
                    document.stage = "failed"
                    document.error_message = outcome.error[:2000]

        outcome.metrics["duration_ms"] = int((time.perf_counter() - started) * 1000)
        return outcome

    # ------------------------------------------------------------- sub-stages
    async def _parse(self, content: bytes, *, mime_type: str, filename: str) -> ParsedDocument:
        import asyncio

        return await asyncio.to_thread(
            parse_document, content, mime_type=mime_type, filename=filename, render_images=True
        )

    async def _apply_ocr(self, parsed: ParsedDocument, *, enabled: bool, outcome: IngestionOutcome) -> None:
        if not enabled:
            outcome.metrics["ocr"] = "disabled"
            return
        targets = [
            page
            for page in parsed.pages
            if page.is_scanned or len((page.text or "").strip()) < self.settings.ocr_min_chars_per_page
        ]
        if not targets:
            outcome.metrics["ocr_pages"] = 0
            outcome.metrics["ocr"] = "not_needed"
            return
        if not await self.ocr.ensure_loaded():
            outcome.metrics["ocr"] = "unavailable"
            outcome.warnings.append(
                "OCR engine unavailable: pages without a text layer were not read. "
                f"({self.ocr._error or 'engine did not load'})"
            )
            return
        processed = 0
        for page in targets:
            if not page.image_bytes:
                continue
            result = await self.ocr.ocr_image(page.image_bytes)
            if not result.available:
                outcome.metrics["ocr"] = "unavailable"
                outcome.warnings.append(f"OCR failed on page {page.page_number}: {result.detail}")
                break
            page.ocr_text = result.text
            page.extraction_method = "ocr"
            processed += 1
            if len(result.text.strip()) < 20:
                # Visually complex or handwritten: escalate to the VLM later.
                page.needs_vision = True
        outcome.metrics["ocr_pages"] = processed
        if outcome.metrics.get("ocr") != "unavailable":
            outcome.metrics["ocr"] = "applied" if processed else "not_needed"

    async def _apply_vision(self, parsed: ParsedDocument, *, enabled: bool, outcome: IngestionOutcome) -> None:
        if not enabled:
            outcome.metrics["vision"] = "disabled"
            return
        targets = [page for page in parsed.pages if page.needs_vision and page.image_bytes]
        if not targets:
            outcome.metrics["vision_pages"] = 0
            outcome.metrics["vision"] = "not_needed"
            return
        if self.container.router is None or not self.settings.vlm_configured:
            outcome.metrics["vision"] = "unavailable"
            outcome.warnings.append(
                f"{len(targets)} page(s) were flagged as visually complex but no VLM is configured; "
                "their content is only available through OCR/text extraction."
            )
            for page in targets:
                page.needs_vision = True
            return
        applied = 0
        for page in targets:
            response = await self.container.router.vision(
                page.image_bytes or b"",
                PAGE_VISION_PROMPT.format(page=page.page_number),
                mime_type=page.image_mime,
            )
            if response.mode == "unavailable" or not response.text:
                outcome.warnings.append(f"VLM returned no usable output for page {page.page_number}.")
                continue
            page.text = (page.text + "\n" + response.text).strip() if page.text.strip() else response.text
            page.extraction_method = EXTRACTION_VLM
            page.needs_vision = False
            page.blocks = []
            applied += 1
        outcome.metrics["vision_pages"] = applied
        outcome.metrics["vision"] = "applied" if applied else "unavailable"

    async def _delete_existing_artifacts(self, session: AsyncSession, document: Document) -> None:
        """Re-indexing replaces derived data; the stored original is never touched."""
        from sqlalchemy import delete

        await session.execute(delete(Chunk).where(Chunk.document_id == document.id))
        await session.execute(delete(DocumentPage).where(DocumentPage.document_id == document.id))
        await session.execute(delete(TableRecord).where(TableRecord.document_id == document.id))
        collection = CHUNK_COLLECTION
        try:
            await self.container.vector.delete_by_document(collection, document.id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("vector_delete_failed", document_id=document.id, error=str(exc))

    async def _persist_pages(
        self, session: AsyncSession, document: Document, parsed: ParsedDocument, tenant_id: str
    ) -> dict[int, str]:
        page_ids: dict[int, str] = {}
        for page in parsed.pages:
            image_key = None
            if page.image_bytes:
                image_key = f"{tenant_id}/{document.id}/pages/page_{page.page_number:04d}.png"
                try:
                    await self.container.storage.put(image_key, page.image_bytes, content_type=page.image_mime)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("page_image_store_failed", page=page.page_number, error=str(exc))
                    image_key = None
            record = DocumentPage(
                tenant_id=tenant_id,
                document_id=document.id,
                page_number=page.page_number,
                width=page.width,
                height=page.height,
                has_text_layer=page.has_text_layer,
                is_scanned=page.is_scanned,
                needs_vision=page.needs_vision,
                extraction_method=page.extraction_method,
                raw_text=page.text,
                ocr_text=page.ocr_text,
                image_key=image_key,
                layout={
                    "blocks": [
                        {"text": block.text[:2000], "kind": block.kind, "order": block.order, "font_size": block.font_size}
                        for block in page.blocks[:400]
                    ],
                    "table_count": len(page.tables),
                },
                char_count=page.char_count,
            )
            session.add(record)
            await session.flush()
            page_ids[page.page_number] = record.id
        return page_ids

    async def _embed_drafts(self, drafts: list[ChunkDraft], outcome: IngestionOutcome) -> bool:
        if not drafts:
            return False
        if self.container.router is None or self.container.embeddings is None:
            outcome.metrics["embeddings"] = "unavailable"
            return False
        try:
            texts = [contextual_text(draft) for draft in drafts]
            vectors = await self.container.router.embed_documents(texts)
        except Exception as exc:  # noqa: BLE001
            outcome.metrics["embeddings"] = "unavailable"
            outcome.metrics["embedding_error"] = f"{type(exc).__name__}: {exc}"
            return False
        if len(vectors) != len(drafts):
            outcome.metrics["embeddings"] = "mismatch"
            return False
        for draft, vector in zip(drafts, vectors, strict=False):
            draft.metadata["embedding"] = vector
        outcome.metrics["embeddings"] = "applied"
        outcome.metrics["embedding_dim"] = len(vectors[0]) if vectors else 0
        return True

    async def _persist_chunks(
        self,
        drafts: list[ChunkDraft],
        *,
        tenant_id: str,
        document_id: str,
        page_ids: dict[int, str],
        supplier_id: str | None,
        contract_id: str | None,
        meta: ExtractedMetadata,
    ) -> dict[int, str]:
        async with session_scope() as session:
            parent_map: dict[str, str] = {}
            table_ids: dict[int, str] = {}
            for draft in drafts:
                is_parent = draft.metadata.get("role") == "parent_section"
                if is_parent:
                    continue
                parent_id = None
                if draft.parent_ref:
                    parent_id = parent_map.get(draft.parent_ref)
                    if parent_id is None and draft.parent_content:
                        parent = Chunk(
                            tenant_id=tenant_id,
                            document_id=document_id,
                            page_id=page_ids.get(draft.page_number or 0),
                            page_number=draft.page_number,
                            section=draft.section,
                            subsection=draft.subsection,
                            clause=draft.clause,
                            content=draft.parent_content,
                            contextual_content=draft.parent_content,
                            content_type="section",
                            token_count=len(draft.parent_content) // 4,
                            supplier_id=supplier_id,
                            contract_id=contract_id,
                            document_type=meta.document_type,
                            version=meta.version or 1,
                            effective_date=meta.effective_date,
                            expiry_date=meta.expiry_date,
                            metadata_json={"role": "parent_section", "unit_key": draft.parent_ref},
                        )
                        session.add(parent)
                        await session.flush()
                        parent_map[draft.parent_ref] = parent.id
                        parent_id = parent.id
                chunk = Chunk(
                    tenant_id=tenant_id,
                    document_id=document_id,
                    page_id=page_ids.get(draft.page_number or 0),
                    page_number=draft.page_number,
                    parent_chunk_id=parent_id,
                    section=draft.section,
                    subsection=draft.subsection,
                    clause=draft.clause,
                    content=draft.content,
                    contextual_content=contextual_text(draft),
                    content_type=draft.content_type,
                    token_count=draft.token_count,
                    supplier_id=supplier_id,
                    contract_id=contract_id,
                    document_type=meta.document_type,
                    version=meta.version or 1,
                    effective_date=meta.effective_date,
                    expiry_date=meta.expiry_date,
                    is_synthetic=meta.is_synthetic,
                    metadata_json={
                        "context_header": draft.metadata.get("context_header"),
                        "contextual": draft.metadata.get("contextual"),
                        "table": {
                            key: draft.metadata.get(key)
                            for key in ("headers", "row_count", "column_count", "complexity_score", "caption")
                            if draft.metadata.get(key) is not None
                        }
                        or None,
                    },
                )
                session.add(chunk)
                await session.flush()
                if draft.content_type == "table" and draft.table_index is not None:
                    table = TableRecord(
                        tenant_id=tenant_id,
                        document_id=document_id,
                        page_number=draft.page_number or 0,
                        table_index=draft.table_index,
                        caption=draft.metadata.get("caption"),
                        headers=draft.metadata.get("headers") or [],
                        rows=[],
                        coordinates=[],
                        extraction_method=draft.metadata.get("extraction_method", "text"),
                        complexity_score=int(draft.metadata.get("complexity_score") or 0),
                        markdown=draft.content,
                        chunk_id=chunk.id,
                    )
                    session.add(table)
                    await session.flush()
                    chunk.table_id = table.id
                    table_ids[draft.table_index] = table.id
            # parent drafts recorded as their own chunks for completeness
            for draft in drafts:
                if draft.metadata.get("role") != "parent_section":
                    continue
                key = draft.metadata.get("unit_key")
                if key and key in parent_map:
                    continue
                chunk = Chunk(
                    tenant_id=tenant_id,
                    document_id=document_id,
                    page_number=draft.page_number,
                    section=draft.section,
                    subsection=draft.subsection,
                    content=draft.content,
                    contextual_content=contextual_text(draft),
                    content_type="section",
                    token_count=draft.token_count,
                    supplier_id=supplier_id,
                    contract_id=contract_id,
                    document_type=meta.document_type,
                    version=meta.version or 1,
                    effective_date=meta.effective_date,
                    expiry_date=meta.expiry_date,
                    metadata_json={"role": "parent_section", "unit_key": key},
                )
                session.add(chunk)
                await session.flush()
                if key:
                    parent_map[key] = chunk.id
        return table_ids

    async def _index_chunks(
        self, drafts: list[ChunkDraft], *, tenant_id: str, document_id: str, outcome: IngestionOutcome
    ) -> int:
        points: list[VectorPoint] = []
        # Chunks are persisted before indexing so the payload can reference ids.
        async with session_scope() as session:
            rows = (
                await session.execute(
                    select(Chunk).where(Chunk.document_id == document_id, Chunk.tenant_id == tenant_id)
                )
            ).scalars()
            chunk_rows = list(rows)
        # Leaf chunks share their exact source text with their draft, so the
        # (page, content) pair identifies the embedding unambiguously.
        vectors_by_key = {
            (draft.page_number, draft.content): draft.metadata.get("embedding")
            for draft in drafts
            if draft.metadata.get("embedding")
        }
        indexed = 0
        indexed_ids: list[str] = []
        for chunk in chunk_rows:
            vector = vectors_by_key.get((chunk.page_number, chunk.content))
            if vector is None:
                continue
            chunk.embedding_id = f"{self.container.vector.name}:{chunk.id}"
            indexed_ids.append(chunk.id)
            points.append(
                VectorPoint(
                    id=chunk.id,
                    vector=vector,
                    payload={
                        "chunk_id": chunk.id,
                        "tenant_id": tenant_id,
                        "document_id": chunk.document_id,
                        "page_number": chunk.page_number,
                        "section": chunk.section,
                        "clause": chunk.clause,
                        "content_type": chunk.content_type,
                        "document_type": chunk.document_type,
                        "supplier_id": chunk.supplier_id,
                        "contract_id": chunk.contract_id,
                        "version": chunk.version,
                        "effective_date": chunk.effective_date.isoformat() if chunk.effective_date else None,
                        "expiry_date": chunk.expiry_date.isoformat() if chunk.expiry_date else None,
                        "access_level": chunk.access_level,
                        "is_synthetic": chunk.is_synthetic,
                        "table_id": chunk.table_id,
                    },
                )
            )
        if not points:
            return 0
        dimension = len(points[0].vector)
        await self.container.vector.ensure_collection(CHUNK_COLLECTION, dimension)
        indexed = await self.container.vector.upsert(CHUNK_COLLECTION, points)
        if indexed_ids:
            async with session_scope() as session:
                await session.execute(
                    Chunk.__table__.update().where(Chunk.id.in_(indexed_ids)).values(embedding_indexed=True)
                )
        outcome.metrics["embeddings_indexed"] = indexed
        return indexed

    # --------------------------------------------------- entity resolution
    async def _resolve_supplier(
        self, tenant_id: str, meta: ExtractedMetadata, contract: Contract | None
    ) -> Supplier | None:
        if not meta.supplier_name:
            # Amend the contract's supplier rather than dropping attribution.
            if contract is not None and contract.supplier_id:
                async with session_scope() as session:
                    return await session.get(Supplier, contract.supplier_id)
            return None
        normalized = normalize_name(meta.supplier_name)
        async with session_scope() as session:
            supplier = (
                await session.execute(
                    select(Supplier).where(
                        Supplier.tenant_id == tenant_id, Supplier.normalized_name == normalized
                    )
                )
            ).scalar_one_or_none()
            if supplier is None:
                supplier = Supplier(
                    tenant_id=tenant_id,
                    name=meta.supplier_name,
                    normalized_name=normalized,
                    region=None,
                    status="active",
                    is_synthetic=meta.is_synthetic,
                    source="document_extraction",
                    attributes={},
                )
                session.add(supplier)
                await session.flush()
                logger.info("supplier_created_from_document", supplier_id=supplier.id, name=supplier.name)
            await self._record_dataset_alias(session, supplier, meta)
            return supplier

    async def _record_dataset_alias(
        self, session: AsyncSession, supplier: Supplier, meta: ExtractedMetadata
    ) -> None:
        """Record dataset-provided supplier labels (e.g. 'supplier_a_contract.pdf').

        Users often refer to suppliers by the label used in the corpus
        (\"Supplier A\"). The label is taken from the source file name, not
        invented, and is stored on the supplier record so query understanding can
        resolve it — with provenance.
        """
        # The label is the single letter after 'supplier'/'vendor' in the file
        # name (e.g. supplier_a_master_contract.pdf → 'A'). The lookahead covers
        # both '-' and '_' separators, which a trailing \b would not.
        filename = os.path.basename(self._current_filename or "").lower()
        match = re.search(r"\b(?:supplier|vendor)[ _-]([a-z])(?![a-z0-9])", filename)
        if not match:
            return
        alias = match.group(1).upper()
        attributes = dict(supplier.attributes or {})
        aliases = sorted({*(attributes.get("aliases") or []), alias})
        if aliases == (attributes.get("aliases") or []):
            return
        attributes["aliases"] = aliases
        attributes.setdefault("alias_provenance", {})[alias] = {
            "method": "filename_label",
            "filename": self._current_filename,
        }
        supplier.attributes = attributes
        await session.flush()

    async def _resolve_contract(
        self, tenant_id: str, meta: ExtractedMetadata
    ) -> Contract | None:
        if not meta.contract_number:
            return None
        async with session_scope() as session:
            contract = (
                await session.execute(
                    select(Contract).where(
                        Contract.tenant_id == tenant_id, Contract.contract_number == meta.contract_number
                    )
                )
            ).scalar_one_or_none()
            if contract is None:
                contract = Contract(
                    tenant_id=tenant_id,
                    supplier_id=None,
                    contract_number=meta.contract_number,
                    title=meta.title,
                    contract_type="amendment" if meta.amendment_label else "agreement",
                    currency=meta.currency or "USD",
                    total_value=meta.total_value,
                    effective_date=meta.effective_date,
                    expiry_date=meta.expiry_date,
                    status="active" if (meta.expiry_date is None or meta.expiry_date >= date.today()) else "expired",
                    version=(meta.amendment_number + 1) if meta.amendment_number else (meta.version or 1),
                    is_synthetic=meta.is_synthetic,
                    source="document_extraction",
                )
                session.add(contract)
                await session.flush()
                logger.info("contract_created_from_document", contract_id=contract.id, number=contract.contract_number)
            else:
                # The contract record may have been created earlier by a document
                # that carried fewer fields (a price sheet citing the contract
                # number, or an amendment). Fill gaps without overwriting.
                if meta.amendment_number:
                    contract.version = max(contract.version, meta.amendment_number + 1)
                elif contract.version < 1:
                    contract.version = meta.version or 1
                if contract.effective_date is None and meta.effective_date:
                    contract.effective_date = meta.effective_date
                if contract.expiry_date is None and meta.expiry_date:
                    contract.expiry_date = meta.expiry_date
                if not contract.title and meta.title:
                    contract.title = meta.title
                if meta.total_value and not contract.total_value:
                    contract.total_value = meta.total_value
                if meta.currency and contract.currency in {None, "USD"}:
                    contract.currency = meta.currency
                if meta.expiry_date is None or meta.expiry_date >= date.today():
                    contract.status = "active"
                else:
                    contract.status = "expired"
            return contract

    async def _persist_structured(
        self,
        *,
        tenant_id: str,
        document_id: str,
        supplier: Supplier | None,
        contract: Contract | None,
        extraction: ExtractionResult,
        meta: ExtractedMetadata,
        table_ids: dict[int, str],
    ) -> dict[str, int]:
        counts = {"prices": 0, "compliance_certificates": 0, "products_resolved": 0, "prices_unattributed": 0}
        resolved_products: set[str] = set()
        async with session_scope() as session:
            for extracted in extraction.prices:
                product = await self._resolve_product(session, tenant_id, extracted.product_name)
                if product is not None:
                    resolved_products.add(product.id)
                price = Price(
                    tenant_id=tenant_id,
                    supplier_id=supplier.id if supplier else None,
                    contract_id=contract.id if contract else None,
                    product_id=product.id if product else None,
                    unit_price=extracted.unit_price,
                    currency=extracted.currency,
                    minimum_quantity=extracted.minimum_quantity,
                    discount_percent=extracted.discount_percent,
                    payment_terms=extracted.payment_terms or extraction.terms.payment_terms,
                    delivery_terms=extracted.delivery_terms or extraction.terms.delivery_terms,
                    quantity=extracted.quantity,
                    line_total=extracted.line_total,
                    effective_date=extracted.effective_date,
                    expiry_date=extracted.expiry_date,
                    amendment_ref=meta.amendment_label,
                    source_document_id=document_id,
                    source_page=extracted.source_page,
                    source_table_id=table_ids.get(extracted.source_table_index or -1),
                    is_synthetic=meta.is_synthetic,
                )
                session.add(price)
                counts["prices"] += 1
                if supplier is None:
                    counts["prices_unattributed"] += 1
            counts["products_resolved"] = len(resolved_products)

            for extracted_cert in extraction.compliance:
                certificate = ComplianceCertificate(
                    tenant_id=tenant_id,
                    supplier_id=supplier.id if supplier else None,
                    certificate_type=extracted_cert.certificate_type,
                    certificate_number=extracted_cert.certificate_number,
                    issued_date=extracted_cert.issued_date,
                    expiry_date=extracted_cert.expiry_date,
                    status="active"
                    if (extracted_cert.expiry_date is None or extracted_cert.expiry_date >= date.today())
                    else "expired",
                    scope=extracted_cert.scope,
                    source_document_id=document_id,
                    source_page=extracted_cert.source_page,
                    is_synthetic=meta.is_synthetic,
                )
                session.add(certificate)
                counts["compliance_certificates"] += 1

            if contract is not None:
                contract_status = "active"
                if contract.expiry_date and contract.expiry_date < date.today():
                    contract_status = "expired"
                contract.status = contract_status
                if supplier is not None:
                    contract.supplier_id = contract.supplier_id or supplier.id
        return counts

    async def _resolve_product(self, session: AsyncSession, tenant_id: str, name: str) -> Product | None:
        """Find or create the product a pricing row refers to."""
        cleaned = name.strip()
        if not cleaned:
            return None
        normalized = normalize_name(cleaned)
        product = (
            await session.execute(
                select(Product).where(Product.tenant_id == tenant_id, func.lower(Product.name) == cleaned.lower())
            )
        ).scalar_one_or_none()
        if product is None:
            sku_match = await session.execute(
                select(Product).where(Product.tenant_id == tenant_id, Product.sku == cleaned.upper())
            )
            product = sku_match.scalar_one_or_none()
        if product is None:
            product = Product(
                tenant_id=tenant_id,
                sku=cleaned.upper()[:60],
                name=cleaned,
                category=None,
                is_synthetic=False,
                attributes={"normalized_name": normalized, "origin": "document_extraction"},
            )
            session.add(product)
            await session.flush()
        return product

    async def _update_graph(
        self,
        tenant_id: str,
        document_id: str,
        supplier: Supplier | None,
        contract: Contract | None,
        counts: dict[str, int],
    ) -> None:
        try:
            async with session_scope() as session:
                await self.graph_builder.remove_document_entities(document_id)
                document = await session.get(Document, document_id)
                if supplier is not None:
                    await self.graph_builder.upsert_supplier(supplier)
                if contract is not None:
                    await self.graph_builder.upsert_contract(contract, supplier)
                prices = list(
                    (
                        await session.execute(select(Price).where(Price.source_document_id == document_id))
                    ).scalars()
                )
                for price in prices:
                    product = await session.get(Product, price.product_id) if price.product_id else None
                    await self.graph_builder.upsert_price(
                        price, supplier=supplier, product=product, contract=contract
                    )
                certificates = list(
                    (
                        await session.execute(
                            select(ComplianceCertificate).where(
                                ComplianceCertificate.source_document_id == document_id
                            )
                        )
                    ).scalars()
                )
                for certificate in certificates:
                    await self.graph_builder.upsert_compliance(certificate, supplier)
                # Every indexed document gets a graph node, even when it could
                # not be attributed to a supplier or contract.
                await self.graph_builder.link_document(
                    document_id=document_id,
                    tenant_id=tenant_id,
                    title=document.title if document else "",
                    document_type=document.document_type if document else "other",
                    version=document.version if document else 1,
                    supplier=supplier,
                    contract=contract,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("graph_update_failed", document_id=document_id, error=str(exc))


__all__ = ["CHUNK_COLLECTION", "IngestionOutcome", "IngestionPipeline", "GraphNode"]
