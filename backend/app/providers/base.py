"""Provider interfaces (dependency-inversion boundary).

Business logic depends on these protocols only. Concrete adapters live next to
them and are selected by the provider factory from configuration.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from app.providers.types import (
    GraphEdge,
    GraphNode,
    LLMMessage,
    LLMResponse,
    ProviderStatus,
    RerankScore,
    VectorHit,
    VectorPoint,
    VisionResponse,
)


class UnavailableProviderError(RuntimeError):
    """Raised when a provider is selected but cannot serve requests."""

    def __init__(self, kind: str, name: str, detail: str = "") -> None:
        self.kind = kind
        self.name = name
        self.detail = detail
        super().__init__(f"{kind} provider '{name}' unavailable: {detail or 'not configured'}")


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    async def complete(
        self,
        messages: Sequence[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> LLMResponse: ...

    def stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]: ...

    async def complete_structured(
        self,
        messages: Sequence[LLMMessage],
        schema: type[BaseModel],
        *,
        model: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> BaseModel | None: ...

    async def status(self) -> ProviderStatus: ...


@runtime_checkable
class VisionProvider(Protocol):
    name: str

    async def describe(
        self,
        image_bytes: bytes,
        prompt: str,
        *,
        mime_type: str = "image/png",
        model: str | None = None,
    ) -> VisionResponse: ...

    async def status(self) -> ProviderStatus: ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    name: str
    model_name: str

    @property
    def dimension(self) -> int: ...

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...

    async def status(self) -> ProviderStatus: ...


@runtime_checkable
class RerankerProvider(Protocol):
    name: str

    async def rank(self, query: str, documents: Sequence[str], *, top_n: int | None = None) -> list[RerankScore]: ...

    async def status(self) -> ProviderStatus: ...


@runtime_checkable
class VectorStoreProvider(Protocol):
    name: str

    async def ensure_collection(self, name: str, dimension: int) -> None: ...

    async def upsert(self, collection: str, points: Sequence[VectorPoint]) -> int: ...

    async def search(
        self,
        collection: str,
        vector: Sequence[float],
        *,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorHit]: ...

    async def delete(self, collection: str, point_ids: Sequence[str]) -> int: ...

    async def delete_by_document(self, collection: str, document_id: str) -> int: ...

    async def count(self, collection: str) -> int: ...

    async def status(self) -> ProviderStatus: ...


@runtime_checkable
class GraphProvider(Protocol):
    name: str

    async def upsert_nodes(self, nodes: Sequence[GraphNode]) -> int: ...

    async def upsert_edges(self, edges: Sequence[GraphEdge]) -> int: ...

    async def neighbors(
        self, label: str, key: str, *, edge_types: Sequence[str] | None = None, direction: str = "both"
    ) -> list[GraphEdge]: ...

    async def traverse(
        self,
        start_label: str,
        start_key: str,
        *,
        max_hops: int = 2,
        edge_types: Sequence[str] | None = None,
    ) -> list[GraphEdge]: ...

    async def find_nodes(self, label: str, *, name_contains: str | None = None, limit: int = 25) -> list[GraphNode]: ...

    async def run_read_query(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]: ...

    async def delete_subgraph(self, document_id: str) -> int: ...

    async def counts(self) -> dict[str, int]: ...

    async def status(self) -> ProviderStatus: ...


@runtime_checkable
class CacheProvider(Protocol):
    name: str

    async def get(self, key: str) -> Any | None: ...

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None: ...

    async def delete(self, key: str) -> None: ...

    async def incr(self, key: str, ttl_seconds: int | None = None) -> int: ...

    async def ttl(self, key: str) -> int | None: ...

    async def clear_prefix(self, prefix: str) -> int: ...

    async def status(self) -> ProviderStatus: ...


@runtime_checkable
class StorageProvider(Protocol):
    name: str

    async def put(self, key: str, data: bytes, *, content_type: str | None = None) -> str: ...

    async def get(self, key: str) -> bytes: ...

    async def exists(self, key: str) -> bool: ...

    async def delete(self, key: str) -> None: ...

    async def url_for(self, key: str) -> str | None: ...

    async def status(self) -> ProviderStatus: ...


@runtime_checkable
class SparseIndexProvider(Protocol):
    """Lexical (BM25) retrieval over indexed chunks."""

    name: str

    async def search(
        self, query: str, *, tenant_id: str, limit: int = 50, filters: dict[str, Any] | None = None
    ) -> list[VectorHit]: ...

    async def invalidate(self, tenant_id: str | None = None) -> None: ...

    async def status(self) -> ProviderStatus: ...
