"""Qdrant adapter — the production vector store (PRD s.27).

Dense vectors with mandatory metadata filtering. Sparse/keyword retrieval is
served by the sparse index provider (BM25) so it stays swappable, but the same
payload schema is used for both.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.observability.logging import get_logger
from app.providers.base import UnavailableProviderError
from app.providers.filters import to_qdrant_filter
from app.providers.types import ProviderStatus, VectorHit, VectorPoint

logger = get_logger(__name__)


class QdrantVectorStore:
    name = "qdrant"

    def __init__(self, url: str, *, api_key: str | None = None, timeout: float = 10.0) -> None:
        self.url = url
        self.api_key = api_key
        self.timeout = timeout
        self._client: Any = None
        self._ready: set[str] = set()

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from qdrant_client import AsyncQdrantClient
            except ImportError as exc:  # pragma: no cover
                raise UnavailableProviderError("vector", self.name, "qdrant-client is not installed") from exc
            self._client = AsyncQdrantClient(url=self.url, api_key=self.api_key, timeout=self.timeout)
        return self._client

    async def ensure_collection(self, name: str, dimension: int) -> None:
        from qdrant_client.http import models as qmodels

        if name in self._ready:
            return
        client = self._get_client()
        exists = await client.collection_exists(name)
        if not exists:
            await client.create_collection(
                collection_name=name,
                vectors_config=qmodels.VectorParams(size=dimension, distance=qmodels.Distance.COSINE),
            )
            for field in (
                "tenant_id",
                "supplier_id",
                "contract_id",
                "document_id",
                "document_type",
                "access_level",
            ):
                await client.create_payload_index(
                    collection_name=name,
                    field_name=field,
                    field_schema=qmodels.PayloadSchemaType.KEYWORD,
                )
            await client.create_payload_index(
                collection_name=name,
                field_name="effective_date",
                field_schema=qmodels.PayloadSchemaType.DATETIME,
            )
            logger.info("qdrant_collection_created", collection=name, dimension=dimension)
        self._ready.add(name)

    async def upsert(self, collection: str, points: Sequence[VectorPoint]) -> int:
        from qdrant_client.http import models as qmodels

        if not points:
            return 0
        client = self._get_client()
        batch = [
            qmodels.PointStruct(
                id=_point_uuid(p.id), vector=list(p.vector), payload={**p.payload, "point_id": p.id}
            )
            for p in points
        ]
        await client.upsert(collection_name=collection, points=batch, wait=True)
        return len(batch)

    async def search(
        self,
        collection: str,
        vector: Sequence[float],
        *,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorHit]:
        client = self._get_client()
        results = await client.query_points(
            collection_name=collection,
            query=list(vector),
            query_filter=to_qdrant_filter(filters),
            limit=limit,
            with_payload=True,
        )
        hits: list[VectorHit] = []
        for point in getattr(results, "points", results):
            payload = dict(point.payload or {})
            original = payload.pop("point_id", str(point.id))
            hits.append(VectorHit(id=original, score=float(point.score), payload=payload, source="dense"))
        return hits

    async def delete(self, collection: str, point_ids: Sequence[str]) -> int:
        from qdrant_client.http import models as qmodels

        if not point_ids:
            return 0
        client = self._get_client()
        await client.delete(
            collection_name=collection,
            points_selector=qmodels.PointIdsList(points=[_point_uuid(pid) for pid in point_ids]),
            wait=True,
        )
        return len(point_ids)

    async def delete_by_document(self, collection: str, document_id: str) -> int:
        from qdrant_client.http import models as qmodels

        client = self._get_client()
        before = await self.count(collection)
        await client.delete(
            collection_name=collection,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(key="document_id", match=qmodels.MatchValue(value=document_id))
                    ]
                )
            ),
            wait=True,
        )
        return max(0, before - await self.count(collection))

    async def count(self, collection: str) -> int:
        client = self._get_client()
        try:
            result = await client.count(collection_name=collection, exact=True)
            return int(result.count)
        except Exception as exc:  # noqa: BLE001 - missing collection == 0 points
            logger.warning("qdrant_count_failed", collection=collection, error=str(exc))
            return 0

    async def status(self) -> ProviderStatus:
        try:
            client = self._get_client()
            collections = await client.get_collections()
            names = [c.name for c in getattr(collections, "collections", [])]
            return ProviderStatus.of(
                "vector",
                self.name,
                True,
                detail=f"connected to {self.url}",
                collections={n: None for n in names},
            )
        except Exception as exc:  # noqa: BLE001
            return ProviderStatus.of("vector", self.name, False, detail=f"unreachable: {type(exc).__name__}")

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None


def _point_uuid(point_id: str) -> str:
    """Deterministic UUIDv5 so the point id is stable across re-indexing."""
    import uuid

    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"epi:{point_id}"))
