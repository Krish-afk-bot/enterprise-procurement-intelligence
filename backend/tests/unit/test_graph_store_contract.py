"""Contract tests for the graph store the explorer and GraphRAG depend on.

The knowledge-graph layer had no test of its own. These cover the four
properties everything else assumes:

* the overview reports a per-type edge breakdown, so a total can never appear
  next to an empty breakdown;
* traversal never crosses a tenant boundary;
* traversal honours its hop limit;
* edges keep the provenance the answer path cites.

They run against the local SQLite provider, which implements the same interface
as the Neo4j adapter.
"""

from __future__ import annotations

import pytest

from app.providers.graph.local import LocalGraphStore
from app.providers.types import GraphEdge, GraphNode


def node(label: str, key: str, tenant: str, **properties: object) -> GraphNode:
    return GraphNode(label=label, key=key, properties={**properties, "tenant_id": tenant})


def edge(kind: str, start: tuple[str, str], end: tuple[str, str], tenant: str, **properties: object) -> GraphEdge:
    return GraphEdge(
        type=kind,
        start_label=start[0],
        start_key=start[1],
        end_label=end[0],
        end_key=end[1],
        properties={**properties, "tenant_id": tenant},
    )


@pytest.fixture()
def store(tmp_path):
    return LocalGraphStore(tmp_path / "graph.db")


class TestCounts:
    async def test_counts_report_edges_by_type(self, store) -> None:
        await store.upsert_nodes(
            [
                node("Supplier", "sup-1", "tenant-a", name="Acme Industrial Ltd"),
                node("Contract", "con-1", "tenant-a", number="AC-2026-01"),
            ]
        )
        await store.upsert_edges(
            [edge("HAS_CONTRACT", ("Supplier", "sup-1"), ("Contract", "con-1"), "tenant-a")]
        )

        counts = await store.counts()

        assert counts["edges"] == 1
        # The explorer reads ``edges:<type>``; without this key it rendered a
        # non-zero total beside an empty breakdown.
        assert counts["edges:HAS_CONTRACT"] == 1
        assert counts["nodes:Supplier"] == 1
        assert counts["nodes:Contract"] == 1

    async def test_status_attributes_match_the_overview_contract(self, store) -> None:
        await store.upsert_nodes([node("Supplier", "sup-1", "tenant-a", name="Acme Industrial Ltd")])
        await store.upsert_nodes([node("Document", "doc-1", "tenant-a", title="Notice")])
        await store.upsert_edges(
            [edge("EVIDENCED_BY", ("Supplier", "sup-1"), ("Document", "doc-1"), "tenant-a")]
        )

        status = await store.status()
        attributes = status.attributes or {}
        edges = {key.split(":", 1)[1]: value for key, value in attributes.items() if key.startswith("edges:")}

        assert status.available is True
        assert attributes.get("edges") == 1
        assert edges == {"EVIDENCED_BY": 1}


class TestTenantIsolation:
    async def test_traversal_does_not_cross_tenants(self, store) -> None:
        await store.upsert_nodes(
            [
                node("Supplier", "sup-a", "tenant-a", name="Acme Industrial Ltd"),
                node("Contract", "con-a", "tenant-a"),
                node("Supplier", "sup-b", "tenant-b", name="Other Supplier Ltd"),
                node("Contract", "con-b", "tenant-b"),
            ]
        )
        await store.upsert_edges(
            [
                edge("HAS_CONTRACT", ("Supplier", "sup-a"), ("Contract", "con-a"), "tenant-a"),
                edge("HAS_CONTRACT", ("Supplier", "sup-b"), ("Contract", "con-b"), "tenant-b"),
            ]
        )

        edges = await store.traverse("Supplier", "sup-a", max_hops=2, tenant_id="tenant-a")

        assert [item.end_key for item in edges] == ["con-a"]
        assert all(item.properties.get("tenant_id") == "tenant-a" for item in edges)

    async def test_find_nodes_is_tenant_scoped(self, store) -> None:
        await store.upsert_nodes(
            [
                node("Supplier", "sup-a", "tenant-a", name="Acme Industrial Ltd"),
                node("Supplier", "sup-b", "tenant-b", name="Other Supplier Ltd"),
            ]
        )

        found = await store.find_nodes("Supplier", tenant_id="tenant-a")

        assert [item.key for item in found] == ["sup-a"]


class TestTraversalBounds:
    async def test_hop_limit_is_respected(self, store) -> None:
        await store.upsert_nodes(
            [
                node("Supplier", "sup-1", "tenant-a", name="Acme Industrial Ltd"),
                node("Contract", "con-1", "tenant-a"),
                node("Price", "pri-1", "tenant-a", unit_price=10.0),
            ]
        )
        await store.upsert_edges(
            [
                edge("HAS_CONTRACT", ("Supplier", "sup-1"), ("Contract", "con-1"), "tenant-a"),
                edge("CONTAINS", ("Contract", "con-1"), ("Price", "pri-1"), "tenant-a"),
            ]
        )

        one_hop = await store.traverse("Supplier", "sup-1", max_hops=1, tenant_id="tenant-a")
        two_hops = await store.traverse("Supplier", "sup-1", max_hops=2, tenant_id="tenant-a")

        assert [item.type for item in one_hop] == ["HAS_CONTRACT"]
        assert {item.type for item in two_hops} == {"HAS_CONTRACT", "CONTAINS"}


class TestProvenance:
    async def test_edges_keep_document_and_page_provenance(self, store) -> None:
        await store.upsert_nodes(
            [
                node("Supplier", "sup-1", "tenant-a", name="Acme Industrial Ltd"),
                node("Price", "pri-1", "tenant-a", unit_price=42.5),
            ]
        )
        await store.upsert_edges(
            [
                edge(
                    "HAS_PRICE",
                    ("Supplier", "sup-1"),
                    ("Price", "pri-1"),
                    "tenant-a",
                    document_id="doc-1",
                    source_page=4,
                    effective_date="2026-01-01",
                )
            ]
        )

        edges = await store.neighbors("Supplier", "sup-1")

        assert len(edges) == 1
        properties = edges[0].properties
        assert properties["document_id"] == "doc-1"
        assert properties["source_page"] == 4
        assert properties["effective_date"] == "2026-01-01"
