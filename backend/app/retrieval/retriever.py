"""Hybrid retrieval (PRD s.27-30).

    query → dense (Qdrant/local) + BM25 → fuse (RRF) → rerank → authorized hits

Authorization is enforced twice: as a metadata filter pushed into the vector and
keyword indexes, and again when chunk rows are loaded from PostgreSQL (which is
the authoritative record). A chunk the caller may not read can therefore never
enter a context window, a citation or an answer.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.container import Container
from app.config.settings import Settings
from app.db.models import Chunk, Document, TableRecord
from app.observability.logging import get_logger
from app.providers.types import VectorHit
from app.retrieval.fusion import FusedHit, describe_fusion, reciprocal_rank_fusion
from app.retrieval.query_understanding import QueryPlan
from app.security.rbac import Principal
from app.security.scope import build_retrieval_filters

logger = get_logger(__name__)

CHUNK_COLLECTION = "procurement_chunks"


@dataclass(slots=True)
class RetrievalStep:
    name: str
    status: str = "ok"
    detail: str = ""
    candidates: int = 0
    latency_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "candidates": self.candidates,
            "latency_ms": self.latency_ms,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    document_name: str
    document_type: str | None
    page: int | None
    section: str | None
    clause: str | None
    content: str
    contextual_content: str | None
    content_type: str
    access_level: str
    is_synthetic: bool
    version: int = 1
    effective_date: date | None = None
    expiry_date: date | None = None
    supplier_id: str | None = None
    contract_id: str | None = None
    parent_chunk_id: str | None = None
    table_id: str | None = None
    rank: int | None = None
    fused_score: float | None = None
    dense_score: float | None = None
    sparse_score: float | None = None
    rerank_score: float | None = None
    matched_by: list[str] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)

    @property
    def citation_label(self) -> str:
        parts = [self.document_name]
        if self.page:
            parts.append(f"p.{self.page}")
        return " — ".join(parts)

    def as_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "document_name": self.document_name,
            "document_type": self.document_type,
            "page": self.page,
            "section": self.section,
            "clause": self.clause,
            "content": self.content,
            "content_type": self.content_type,
            "access_level": self.access_level,
            "is_synthetic": self.is_synthetic,
            "version": self.version,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "rank": self.rank,
            "fused_score": self.fused_score,
            "dense_score": self.dense_score,
            "sparse_score": self.sparse_score,
            "rerank_score": self.rerank_score,
            "matched_by": self.matched_by,
        }


@dataclass(slots=True)
class RetrievalResult:
    query: str
    mode: str
    hits: list[RetrievedChunk] = field(default_factory=list)
    steps: list[RetrievalStep] = field(default_factory=list)
    reranker: str | None = None
    embedding_model: str | None = None
    candidate_count: int = 0
    notes: list[str] = field(default_factory=list)
    filters: dict[str, Any] = field(default_factory=dict)

    def step_summary(self) -> list[dict[str, Any]]:
        return [step.as_dict() for step in self.steps]


class HybridRetriever:
    def __init__(self, container: Container, settings: Settings) -> None:
        self.container = container
        self.settings = settings

    # ------------------------------------------------------------------ public
    async def retrieve(
        self,
        session: AsyncSession,
        principal: Principal,
        plan: QueryPlan,
        *,
        mode: str = "hybrid",
        limit: int | None = None,
        filters: dict[str, Any] | None = None,
        rerank: bool = True,
        query_text: str | None = None,
    ) -> RetrievalResult:
        query = query_text or plan.query
        top_n = limit or self.settings.rerank_top_n
        # If the query plan identifies specific supplier(s) OR contract(s),
        # add them as pre-filters so single-chunk documents for those entities
        # are not overwhelmed by corpus-wide RRF scores.
        plan_extras: dict[str, Any] = {}
        if len(plan.supplier_ids) == 1:
            # Single identified supplier: scope vector search to that supplier's
            # documents so a small supplier corpus is not crowded out.
            plan_extras["supplier_id"] = plan.supplier_ids[0]
        scoped_filters = build_retrieval_filters(principal, **(filters or {}), **plan_extras)
        result = RetrievalResult(query=query, mode=mode, filters=scoped_filters)

        dense_hits: list[VectorHit] = []
        sparse_hits: list[VectorHit] = []

        if mode in {"hybrid", "dense", "hybrid_rerank"}:
            dense_hits, step = await self._dense_search(query, scoped_filters)
            result.steps.append(step)
        if mode in {"hybrid", "sparse", "hybrid_rerank"}:
            sparse_hits, step = await self._sparse_search(query, principal, scoped_filters)
            result.steps.append(step)

        # If scoped by plan_extras (e.g. single supplier) but zero candidates matched
        # (e.g. tender notices lack supplier tags or supplier was not in document chunks),
        # fall back to tenant-scoped search without plan_extras so evidence is not lost.
        if plan_extras and not dense_hits and not sparse_hits:
            fallback_filters = build_retrieval_filters(principal, **(filters or {}))
            if mode in {"hybrid", "dense", "hybrid_rerank"}:
                dense_hits, fallback_step = await self._dense_search(query, fallback_filters)
                result.steps.append(fallback_step)
            if mode in {"hybrid", "sparse", "hybrid_rerank"}:
                sparse_hits, fallback_step = await self._sparse_search(query, principal, fallback_filters)
                result.steps.append(fallback_step)

        if mode == "dense":
            fused = [
                FusedHit(
                    id=hit.id,
                    fused_score=hit.score,
                    payload=dict(hit.payload),
                    dense_score=hit.score,
                    dense_rank=rank,
                    matched_by=["dense"],
                )
                for rank, hit in enumerate(dense_hits, start=1)
            ]
        elif mode == "sparse":
            fused = [
                FusedHit(
                    id=hit.id,
                    fused_score=hit.score,
                    payload=dict(hit.payload),
                    sparse_score=hit.score,
                    sparse_rank=rank,
                    matched_by=["sparse"],
                )
                for rank, hit in enumerate(sparse_hits, start=1)
            ]
        else:
            fused = reciprocal_rank_fusion(dense_hits, sparse_hits, k=self.settings.rrf_k)
            result.steps.append(
                RetrievalStep(
                    name="fusion",
                    detail="Reciprocal Rank Fusion over dense and BM25 rankings",
                    candidates=len(fused),
                    metadata=describe_fusion(
                        len(dense_hits), len(sparse_hits), len(fused), self.settings.rrf_k
                    ),
                )
            )

        result.candidate_count = len(fused)
        candidates = fused[: self.settings.fusion_top_k]
        chunks = await self._load_chunks(session, principal, candidates)
        result.steps.append(
            RetrievalStep(
                name="authorization_filter",
                detail="Candidates verified against the workspace database with tenant and access-level checks",
                candidates=len(chunks),
                metadata={
                    "dropped": len(candidates) - len(chunks),
                    "readable_access_levels": principal.readable_access_levels,
                    "note": "Documents the caller may not read never reach the model context.",
                },
            )
        )
        if not chunks:
            result.notes.append("No authorised evidence matched this query.")
            return result

        # ------------------------------------------------------------- rerank
        if rerank and self.settings.reranker_enabled:
            if self.settings.rerank_gate_enabled and self._rerank_confident(chunks):
                result.steps.append(
                    RetrievalStep(
                        name="rerank",
                        status="gated",
                        detail=(
                            "skipped: the dense ranking is confident (the top result is both "
                            "high-scoring and clearly ahead), so the cross-encoder would only "
                            "add latency"
                        ),
                        candidates=len(chunks),
                    )
                )
                result.reranker = f"{self.container.reranker.name} (gated)" if self.container.reranker else "gated"
            else:
                chunks, step = await self._rerank(query, chunks)
                result.steps.append(step)
                result.reranker = self.container.reranker.name if self.container.reranker else "none"
        else:
            result.reranker = "disabled"

        chunks = self._apply_temporal_preference(chunks, plan)
        chunks = chunks[:top_n]
        for rank, chunk in enumerate(chunks, start=1):
            chunk.rank = rank
        result.hits = chunks
        if self.container.embeddings is not None:
            result.embedding_model = self.container.embeddings.model_name
        return result

    # ------------------------------------------------------------------ stages
    async def _dense_search(
        self, query: str, filters: dict[str, Any]
    ) -> tuple[list[VectorHit], RetrievalStep]:
        started = time.perf_counter()
        if self.container.router is None or self.container.embeddings is None:
            return [], RetrievalStep(
                name="dense_search", status="skipped", detail="embedding provider unavailable"
            )
        try:
            vector = await self.container.router.embed_query(query)
        except Exception as exc:  # noqa: BLE001
            return [], RetrievalStep(
                name="dense_search", status="unavailable", detail=f"embedding failed: {type(exc).__name__}"
            )
        try:
            hits = await self.container.vector.search(
                CHUNK_COLLECTION, vector, limit=self.settings.dense_top_k, filters=filters
            )
        except Exception as exc:  # noqa: BLE001
            return [], RetrievalStep(
                name="dense_search",
                status="unavailable",
                detail=f"vector search failed: {type(exc).__name__}",
            )
        return hits, RetrievalStep(
            name="dense_search",
            detail=f"vector similarity over {self.container.vector.name}",
            candidates=len(hits),
            latency_ms=int((time.perf_counter() - started) * 1000),
            metadata={"model": self.container.embeddings.model_name, "top_k": self.settings.dense_top_k},
        )

    async def _sparse_search(
        self, query: str, principal: Principal, filters: dict[str, Any]
    ) -> tuple[list[VectorHit], RetrievalStep]:
        started = time.perf_counter()
        if self.container.sparse is None:
            return [], RetrievalStep(
                name="sparse_search", status="skipped", detail="no BM25 index configured"
            )
        try:
            hits = await self.container.sparse.search(
                query, tenant_id=principal.tenant_id, limit=self.settings.sparse_top_k, filters=filters
            )
        except Exception as exc:  # noqa: BLE001
            return [], RetrievalStep(
                name="sparse_search", status="unavailable", detail=f"BM25 failed: {type(exc).__name__}"
            )
        return hits, RetrievalStep(
            name="sparse_search",
            detail="BM25 (Okapi) lexical search over indexed chunks",
            candidates=len(hits),
            latency_ms=int((time.perf_counter() - started) * 1000),
            metadata={"top_k": self.settings.sparse_top_k, "index": self.container.sparse.name},
        )

    def _rerank_confident(self, chunks: list[RetrievedChunk]) -> bool:
        """Whether the fused ranking is already clear enough to skip the model.

        Only dense scores are comparable across queries; RRF scores are rank
        reciprocals and carry no confidence. A high top score with a clear gap
        to the fifth candidate means the cross-encoder is unlikely to reorder
        the head, so its CPU time buys nothing.
        """
        scores = sorted(
            (chunk.dense_score for chunk in chunks if chunk.dense_score is not None), reverse=True
        )
        if len(scores) < 2:
            return False
        fifth = scores[min(4, len(scores) - 1)]
        return (
            scores[0] >= self.settings.rerank_gate_min_score
            and (scores[0] - fifth) >= self.settings.rerank_gate_min_margin
        )

    async def _rerank(
        self, query: str, chunks: list[RetrievedChunk]
    ) -> tuple[list[RetrievedChunk], RetrievalStep]:
        started = time.perf_counter()
        # Rerank only the head. Candidates behind the cut keep their fused order
        # and are still available to the context builder if the head is short.
        limit = max(1, self.settings.rerank_candidate_limit)
        head, tail = chunks[:limit], chunks[limit:]
        documents = [chunk.content for chunk in head]
        try:
            scores = await self.container.router.rerank(query, documents, top_n=len(documents))  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001
            logger.warning("rerank_failed", error=str(exc))
            return chunks, RetrievalStep(
                name="rerank",
                status="unavailable",
                detail=(
                    f"reranker failed ({type(exc).__name__}); fused order retained. "
                    f"The {len(chunks)} candidate(s) below are the fused ranking, not a cross-encoder ranking."
                ),
                # The candidates were retrieved; only the ranking step failed.
                # Reporting zero here would read as "nothing was found".
                candidates=len(chunks),
            )
        by_index = {score.index: score.score for score in scores}
        for index, chunk in enumerate(head):
            chunk.rerank_score = by_index.get(index)
        ordered = sorted(
            head,
            key=lambda chunk: chunk.rerank_score if chunk.rerank_score is not None else -1e9,
            reverse=True,
        )
        return [*ordered, *tail], RetrievalStep(
            name="rerank",
            detail=f"cross-encoder reranking with {self.container.reranker.name}",  # type: ignore[union-attr]
            candidates=len(ordered),
            latency_ms=int((time.perf_counter() - started) * 1000),
            metadata={
                "top_n": self.settings.rerank_top_n,
                "reranked": len(head),
                "unranked_tail": len(tail),
                "candidate_limit": limit,
            },
        )

    @staticmethod
    def _apply_temporal_preference(chunks: list[RetrievedChunk], plan: QueryPlan) -> list[RetrievedChunk]:
        """Prefer evidence that is in force, without hiding the older version.

        The ordering changes; nothing is deleted, so a conflict between the
        original agreement and a later amendment can still be reported.
        
        Changes from baseline:
        - Expired chunks get 0.5x score penalty, not moved to separate tier
        - No penalty if document type matches question or question asks about expiry/validity
        - For temporal queries, use effective date only for supersession within same contract
        """
        from app.core.clock import today
        as_of_date = today()
        
        # Check if question is about expiry/validity/expired status
        question_lower = plan.query.lower() if hasattr(plan, 'query') else ""
        is_expiry_question = any(
            term in question_lower 
            for term in ["expir", "valid", "expired", "in force", "active", "certificate", "compliance", "certification"]
        )

        def sort_key(chunk: RetrievedChunk) -> tuple[int, float]:
            base = chunk.rerank_score if chunk.rerank_score is not None else (chunk.fused_score or 0.0)
            
            # Check if document type matches question context
            doc_type_matches = False
            if chunk.document_type:
                doc_type_lower = chunk.document_type.lower()
                if ("certificate" in question_lower or "compliance" in question_lower) and "certificate" in doc_type_lower:
                    doc_type_matches = True
                elif "amendment" in question_lower and "amendment" in doc_type_lower:
                    doc_type_matches = True
            
            # No penalty if asking about expiry/validity or if doc type matches
            if is_expiry_question or doc_type_matches:
                if plan.requires_temporal and chunk.effective_date:
                    # For temporal queries, use effective date for ordering within same contract
                    # But don't penalize unrelated documents
                    return (0, -chunk.effective_date.toordinal(), -base)
                return (0, -base)
            
            # Apply soft penalty for expired chunks
            expired = chunk.expiry_date is not None and chunk.expiry_date < as_of_date
            if expired:
                # 0.5x penalty instead of moving to separate tier
                adjusted_score = base * 0.5
                return (0, -adjusted_score)
            
            # For temporal queries on non-expired chunks, use effective date for supersession
            if plan.requires_temporal and chunk.effective_date:
                # Use effective date to prefer newer versions of same contract
                return (0, -chunk.effective_date.toordinal(), -base)
            
            return (0, -base)

        return sorted(chunks, key=sort_key)

    async def _load_chunks(
        self, session: AsyncSession, principal: Principal, fused: Sequence[FusedHit]
    ) -> list[RetrievedChunk]:
        if not fused:
            return []
        ids = [hit.id for hit in fused]
        rows = (
            await session.execute(
                select(Chunk, Document.title, Document.filename, Document.access_level)
                .join(Document, Chunk.document_id == Document.id)
                .where(
                    Chunk.id.in_(ids),
                    Chunk.tenant_id == principal.tenant_id,
                    Document.tenant_id == principal.tenant_id,
                    Chunk.is_active == True,  # noqa: E712 - PostgreSQL is authoritative
                    Chunk.indexing_version == Document.active_indexing_version,
                    Chunk.access_level.in_(principal.readable_access_levels),
                    Document.access_level.in_(principal.readable_access_levels),
                )
            )
        ).all()
        by_id = {row[0].id: row for row in rows}
        table_ids = [row[0].table_id for row in rows if row[0].table_id]
        tables: dict[str, list[dict[str, Any]]] = {}
        if table_ids:
            table_rows = (
                await session.execute(select(TableRecord).where(TableRecord.id.in_(table_ids)))
            ).scalars()
            for table in table_rows:
                if table.chunk_id:
                    tables.setdefault(table.chunk_id, []).append(
                        {
                            "table_id": table.id,
                            "page": table.page_number,
                            "caption": table.caption,
                            "headers": table.headers,
                            "rows": table.rows,
                            "markdown": table.markdown,
                        }
                    )
        chunks: list[RetrievedChunk] = []
        for hit in fused:
            row = by_id.get(hit.id)
            if row is None:
                continue
            chunk, title, filename, access_level = row
            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    document_name=title or filename,
                    document_type=chunk.document_type,
                    page=chunk.page_number,
                    section=chunk.section,
                    clause=chunk.clause,
                    content=chunk.content,
                    contextual_content=chunk.contextual_content,
                    content_type=chunk.content_type,
                    access_level=access_level or chunk.access_level,
                    is_synthetic=chunk.is_synthetic,
                    version=chunk.version,
                    effective_date=chunk.effective_date,
                    expiry_date=chunk.expiry_date,
                    supplier_id=chunk.supplier_id,
                    contract_id=chunk.contract_id,
                    parent_chunk_id=chunk.parent_chunk_id,
                    table_id=chunk.table_id,
                    fused_score=hit.fused_score,
                    dense_score=hit.dense_score,
                    sparse_score=hit.sparse_score,
                    matched_by=list(dict.fromkeys(hit.matched_by)),
                    tables=tables.get(chunk.id, []),
                )
            )
        return chunks


async def expand_parents(
    session: AsyncSession, principal: Principal, chunks: list[RetrievedChunk], *, limit: int = 3
) -> dict[str, tuple[str, str | None]]:
    """Fetch parent section text for parent-child retrieval (PRD s.25 level 4)."""
    parent_ids = [chunk.parent_chunk_id for chunk in chunks if chunk.parent_chunk_id][:limit]
    if not parent_ids:
        return {}
    rows = (
        await session.execute(
            select(Chunk.id, Chunk.content, Chunk.section)
            .join(Document, Chunk.document_id == Document.id)
            .where(
                Chunk.id.in_(parent_ids),
                Chunk.tenant_id == principal.tenant_id,
                Chunk.access_level.in_(principal.readable_access_levels),
                Chunk.is_active == True,  # noqa: E712
                Chunk.indexing_version == Document.active_indexing_version,
            )
        )
    ).all()
    return {row[0]: (row[1], row[2]) for row in rows}


async def count_indexed_chunks(container: Container, *, collection: str = CHUNK_COLLECTION) -> int:
    try:
        return await container.vector.count(collection)
    except Exception:  # noqa: BLE001
        return 0


async def retrieval_health(container: Container) -> dict[str, Any]:
    """Small helper for the Admin/system page."""
    results: dict[str, Any] = {}
    try:
        results["vector_count"] = await container.vector.count(CHUNK_COLLECTION)
    except Exception as exc:  # noqa: BLE001
        results["vector_count"] = f"unavailable ({type(exc).__name__})"
    if container.sparse is not None:
        results["sparse"] = (await container.sparse.status()).model_dump()
    results["reranker"] = await asyncio.sleep(0) or (
        (await container.reranker.status()).model_dump() if container.reranker else None
    )
    return results
