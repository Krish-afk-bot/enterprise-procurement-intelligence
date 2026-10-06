"""Unit tests for provider infrastructure adapters.

Tests verify:
  - LocalVectorStore: basic upsert/search/count/delete operations
  - LocalGraphStore: node/edge upsert, traversal, counts
  - MemoryCache: get/set/ttl/expiry/incr
  - LocalStorage: put/get/exists/delete
  - EmbeddingProvider: hashing provider dimension and output shape
  - Provider status methods: available/unavailable reporting

These tests use only local/in-memory implementations so no external
services are required.
"""

from __future__ import annotations

import pytest

from app.providers.types import GraphEdge, GraphNode, VectorPoint

# ================================================================== LocalVectorStore


class TestLocalVectorStore:
    @pytest.fixture()
    def store(self, tmp_path):
        from app.providers.vector.local import LocalVectorStore

        s = LocalVectorStore(tmp_path / "vectors")
        return s

    async def test_ensure_collection_creates_namespace(self, store) -> None:
        await store.ensure_collection("test_col", 4)
        count = await store.count("test_col")
        assert count == 0

    async def test_upsert_and_search(self, store) -> None:
        await store.ensure_collection("test_col", 4)
        points = [
            VectorPoint(id="v1", vector=[1.0, 0.0, 0.0, 0.0], payload={"chunk_id": "chk_1"}),
            VectorPoint(id="v2", vector=[0.0, 1.0, 0.0, 0.0], payload={"chunk_id": "chk_2"}),
        ]
        count = await store.upsert("test_col", points)
        assert count == 2
        hits = await store.search("test_col", [1.0, 0.0, 0.0, 0.0], limit=2)
        assert len(hits) >= 1
        # The closest vector to [1,0,0,0] should be v1
        assert hits[0].id == "v1"

    async def test_count_after_upsert(self, store) -> None:
        await store.ensure_collection("test_col", 4)
        points = [VectorPoint(id=f"v{i}", vector=[float(i), 0.0, 0.0, 0.0], payload={}) for i in range(5)]
        await store.upsert("test_col", points)
        count = await store.count("test_col")
        assert count == 5

    async def test_delete_point(self, store) -> None:
        await store.ensure_collection("test_col", 4)
        await store.upsert("test_col", [VectorPoint(id="v1", vector=[1.0, 0.0, 0.0, 0.0], payload={})])
        deleted = await store.delete("test_col", ["v1"])
        assert deleted == 1
        assert await store.count("test_col") == 0

    async def test_delete_by_document(self, store) -> None:
        await store.ensure_collection("test_col", 4)
        await store.upsert(
            "test_col",
            [
                VectorPoint(id="v1", vector=[1.0, 0.0, 0.0, 0.0], payload={"document_id": "doc_A"}),
                VectorPoint(id="v2", vector=[0.0, 1.0, 0.0, 0.0], payload={"document_id": "doc_B"}),
            ],
        )
        removed = await store.delete_by_document("test_col", "doc_A")
        assert removed >= 1
        assert await store.count("test_col") == 1

    async def test_metadata_filter(self, store) -> None:
        await store.ensure_collection("test_col", 4)
        await store.upsert(
            "test_col",
            [
                VectorPoint(id="v1", vector=[1.0, 0.0, 0.0, 0.0], payload={"doc_type": "contract"}),
                VectorPoint(id="v2", vector=[1.0, 0.0, 0.0, 0.0], payload={"doc_type": "invoice"}),
            ],
        )
        hits = await store.search(
            "test_col", [1.0, 0.0, 0.0, 0.0], limit=10, filters={"doc_type": "contract"}
        )
        assert all(hit.payload.get("doc_type") == "contract" for hit in hits)

    async def test_status_reports_available(self, store) -> None:
        status = await store.status()
        assert status.available is True


# ================================================================== LocalGraphStore


class TestLocalGraphStore:
    @pytest.fixture()
    def store(self, tmp_path):
        from app.providers.graph.local import LocalGraphStore

        return LocalGraphStore(tmp_path / "graph.db")

    async def test_upsert_nodes(self, store) -> None:
        nodes = [
            GraphNode(label="Supplier", key="sup_1", properties={"name": "Acme Corp"}),
            GraphNode(label="Contract", key="con_1", properties={"number": "MSA-001"}),
        ]
        count = await store.upsert_nodes(nodes)
        assert count == 2

    async def test_upsert_edges(self, store) -> None:
        await store.upsert_nodes(
            [
                GraphNode(label="Supplier", key="sup_1", properties={}),
                GraphNode(label="Contract", key="con_1", properties={}),
            ]
        )
        edges = [
            GraphEdge(
                type="HAS_CONTRACT",
                start_label="Supplier",
                start_key="sup_1",
                end_label="Contract",
                end_key="con_1",
                properties={},
            )
        ]
        count = await store.upsert_edges(edges)
        assert count == 1

    async def test_neighbors_returns_connected_nodes(self, store) -> None:
        await store.upsert_nodes(
            [
                GraphNode(label="Supplier", key="sup_1", properties={}),
                GraphNode(label="Product", key="prod_1", properties={}),
            ]
        )
        await store.upsert_edges(
            [
                GraphEdge(
                    type="SUPPLIES",
                    start_label="Supplier",
                    start_key="sup_1",
                    end_label="Product",
                    end_key="prod_1",
                    properties={},
                )
            ]
        )
        edges = await store.neighbors("Supplier", "sup_1")
        assert len(edges) >= 1
        assert any(e.end_key == "prod_1" for e in edges)

    async def test_counts_returns_dict(self, store) -> None:
        counts = await store.counts()
        assert isinstance(counts, dict)

    async def test_status_reports_available(self, store) -> None:
        status = await store.status()
        assert status.available is True


# ================================================================== MemoryCache


class TestMemoryCache:
    @pytest.fixture()
    def cache(self):
        from app.providers.cache import MemoryCache

        return MemoryCache()

    async def test_set_and_get(self, cache) -> None:
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"

    async def test_get_missing_returns_none(self, cache) -> None:
        result = await cache.get("nonexistent")
        assert result is None

    async def test_delete(self, cache) -> None:
        await cache.set("key1", "value1")
        await cache.delete("key1")
        assert await cache.get("key1") is None

    async def test_set_with_ttl(self, cache) -> None:
        await cache.set("ttl_key", "ttl_value", ttl_seconds=3600)
        result = await cache.get("ttl_key")
        assert result == "ttl_value"

    async def test_incr_creates_counter(self, cache) -> None:
        count = await cache.incr("counter", ttl_seconds=60)
        assert count == 1
        count2 = await cache.incr("counter", ttl_seconds=60)
        assert count2 == 2

    async def test_serialises_dict(self, cache) -> None:
        data = {"key": "value", "number": 42}
        await cache.set("dict_key", data)
        result = await cache.get("dict_key")
        assert result == data

    async def test_status_reports_available(self, cache) -> None:
        status = await cache.status()
        assert status.available is True


# ================================================================== LocalStorage


class TestLocalStorage:
    @pytest.fixture()
    def storage(self, tmp_path):
        from app.providers.storage import LocalStorage

        return LocalStorage(tmp_path / "storage")

    async def test_put_and_get(self, storage) -> None:
        await storage.put("file/test.txt", b"hello world", content_type="text/plain")
        data = await storage.get("file/test.txt")
        assert data == b"hello world"

    async def test_exists_true_after_put(self, storage) -> None:
        await storage.put("f/doc.pdf", b"pdf content")
        assert await storage.exists("f/doc.pdf") is True

    async def test_exists_false_before_put(self, storage) -> None:
        assert await storage.exists("f/missing.pdf") is False

    async def test_delete(self, storage) -> None:
        await storage.put("f/deletable.txt", b"data")
        await storage.delete("f/deletable.txt")
        assert await storage.exists("f/deletable.txt") is False

    async def test_url_for_returns_string_or_none(self, storage) -> None:
        await storage.put("f/document.pdf", b"pdf")
        url = await storage.url_for("f/document.pdf")
        # local storage may return None or a file:// URL
        assert url is None or isinstance(url, str)

    async def test_status_reports_available(self, storage) -> None:
        status = await storage.status()
        assert status.available is True


# ================================================================== HashingEmbeddingProvider


class TestHashingEmbeddingProvider:
    @pytest.fixture()
    def provider(self):
        from app.providers.embedding import CachedEmbeddingProvider, HashingEmbeddingProvider

        return CachedEmbeddingProvider(HashingEmbeddingProvider())

    async def test_embed_query_returns_list_of_floats(self, provider) -> None:
        vector = await provider.embed_query("What is the price?")
        assert isinstance(vector, list)
        assert all(isinstance(v, float) for v in vector)

    async def test_embed_query_has_nonzero_dimension(self, provider) -> None:
        vector = await provider.embed_query("price")
        assert len(vector) > 0

    async def test_embed_documents_returns_one_vector_per_doc(self, provider) -> None:
        texts = ["Document one.", "Document two.", "Document three."]
        vectors = await provider.embed_documents(texts)
        assert len(vectors) == 3
        assert all(isinstance(v, list) for v in vectors)

    async def test_same_text_produces_same_vector(self, provider) -> None:
        """Hashing is deterministic."""
        v1 = await provider.embed_query("price for Widget A")
        v2 = await provider.embed_query("price for Widget A")
        assert v1 == v2

    async def test_different_texts_produce_different_vectors(self, provider) -> None:
        v1 = await provider.embed_query("Widget A price")
        v2 = await provider.embed_query("completely different text")
        assert v1 != v2

    async def test_status_available(self, provider) -> None:
        status = await provider.status()
        assert status.available is True
