"""Lexical (BM25) retrieval.

BM25 is what makes exact supplier names, contract numbers, SKUs, clause numbers
and literal prices findable — dense vectors alone are bad at those (PRD s.28).

The index is built from the ``chunks`` table (real BM25, Okapi), cached per
tenant, and invalidated whenever the corpus changes. For very large corpora the
same interface is satisfied by OpenSearch or Qdrant sparse vectors.
"""

from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk
from app.observability.logging import get_logger
from app.providers.filters import matches
from app.providers.types import ProviderStatus, VectorHit

logger = get_logger(__name__)

_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._\-/]*")


def tokenize(text: str) -> list[str]:
    """Case-folded tokenizer that keeps contract numbers and SKUs intact."""
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


class _TenantIndex:
    __slots__ = ("bm25", "chunk_ids", "payloads", "signature", "built_at")

    def __init__(self, bm25: Any, chunk_ids: list[str], payloads: list[dict[str, Any]], signature: tuple) -> None:
        self.bm25 = bm25
        self.chunk_ids = chunk_ids
        self.payloads = payloads
        self.signature = signature
        self.built_at = time.time()


class LocalBM25Index:
    name = "bm25_sql"

    def __init__(self, session_factory: Any, *, cache_ttl_seconds: int = 300) -> None:
        self._session_factory = session_factory
        self._indices: dict[str, _TenantIndex] = {}
        self._lock = asyncio.Lock()
        self.cache_ttl_seconds = cache_ttl_seconds

    async def invalidate(self, tenant_id: str | None = None) -> None:
        if tenant_id is None:
            self._indices.clear()
        else:
            self._indices.pop(tenant_id, None)

    async def _signature(self, session: AsyncSession, tenant_id: str) -> tuple:
        row = await session.execute(
            select(func.count(Chunk.id), func.max(Chunk.updated_at)).where(Chunk.tenant_id == tenant_id)
        )
        count, latest = row.one()
        return (int(count or 0), str(latest))

    async def _build(self, tenant_id: str) -> _TenantIndex:
        from rank_bm25 import BM25Okapi

        async with self._session_factory() as session:
            signature = await self._signature(session, tenant_id)
            rows = (
                await session.execute(
                    select(
                        Chunk.id,
                        Chunk.content,
                        Chunk.document_id,
                        Chunk.page_number,
                        Chunk.section,
                        Chunk.clause,
                        Chunk.content_type,
                        Chunk.document_type,
                        Chunk.supplier_id,
                        Chunk.contract_id,
                        Chunk.version,
                        Chunk.effective_date,
                        Chunk.expiry_date,
                        Chunk.access_level,
                        Chunk.category,
                        Chunk.region,
                        Chunk.is_synthetic,
                        Chunk.table_id,
                        Chunk.token_count,
                    ).where(Chunk.tenant_id == tenant_id)
                )
            ).all()
        corpus = [tokenize(row.content) for row in rows]
        corpus = [tokens or ["_empty_"] for tokens in corpus]
        bm25 = BM25Okapi(corpus) if corpus else None
        chunk_ids = [row.id for row in rows]
        payloads = [
            {
                "document_id": row.document_id,
                "page_number": row.page_number,
                "section": row.section,
                "clause": row.clause,
                "content_type": row.content_type,
                "document_type": row.document_type,
                "supplier_id": row.supplier_id,
                "contract_id": row.contract_id,
                "version": row.version,
                "effective_date": row.effective_date.isoformat() if row.effective_date else None,
                "expiry_date": row.expiry_date.isoformat() if row.expiry_date else None,
                "access_level": row.access_level,
                "category": row.category,
                "region": row.region,
                "is_synthetic": row.is_synthetic,
                "table_id": row.table_id,
                "token_count": row.token_count,
                "tenant_id": tenant_id,
                "content": row.content,
            }
            for row in rows
        ]
        index = _TenantIndex(bm25, chunk_ids, payloads, signature)
        logger.info("bm25_index_built", tenant_id=tenant_id, chunks=len(chunk_ids))
        return index

    async def _get_index(self, tenant_id: str) -> _TenantIndex | None:
        cached = self._indices.get(tenant_id)
        if cached and time.time() - cached.built_at < self.cache_ttl_seconds:
            return cached
        async with self._lock:
            if tenant_id in self._indices and time.time() - self._indices[tenant_id].built_at < self.cache_ttl_seconds:
                return self._indices[tenant_id]
            index = await self._build(tenant_id)
            self._indices[tenant_id] = index
            return index

    async def search(
        self,
        query: str,
        *,
        tenant_id: str,
        limit: int = 50,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorHit]:
        tokens = tokenize(query)
        if not tokens:
            return []
        index = await self._get_index(tenant_id)
        if index is None or index.bm25 is None:
            return []
        scores = index.bm25.get_scores(tokens)
        candidates: list[tuple[float, int]] = []
        for position, score in enumerate(scores):
            if score <= 0:
                continue
            payload = index.payloads[position]
            if not matches(payload, {**(filters or {}), "tenant_id": tenant_id}):
                continue
            candidates.append((float(score), position))
        candidates.sort(key=lambda item: item[0], reverse=True)
        return [
            VectorHit(
                id=index.chunk_ids[position],
                score=score,
                payload=index.payloads[position],
                source="sparse",
            )
            for score, position in candidates[:limit]
        ]

    async def status(self) -> ProviderStatus:
        return ProviderStatus.of(
            "sparse",
            self.name,
            True,
            detail="BM25 (Okapi) index built from the chunks table, per-tenant, TTL-cached",
            indexed_tenants=len(self._indices),
            indexed_chunks={tid: len(idx.chunk_ids) for tid, idx in self._indices.items()},
        )


async def token_count(text: str) -> int:
    return len(tokenize(text))


def detect_exact_terms(query: str) -> Sequence[str]:
    """Surface literal identifiers the query contains (used for query planning)."""
    patterns = {
        "contract_number": r"\b(?:CTR|CN|CONTRACT)[-_]?[A-Z0-9]{3,}\b",
        "sku": r"\b(?:SKU|P/N|PART)[-_]?[A-Z0-9]{3,}\b",
        "clause": r"\bclause\s+\d+(?:\.\d+)*\b",
        "amount": r"\$\s?\d[\d,]*(?:\.\d+)?\b",
    }
    found: list[str] = []
    for pattern in patterns.values():
        found.extend(re.findall(pattern, query, flags=re.IGNORECASE))
    return found
