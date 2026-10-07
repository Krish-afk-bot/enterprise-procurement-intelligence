"""Phase 3: Neo4j live verification via the application graph abstraction.

Tests: connect, node upsert, edge upsert, neighbors, multi-hop traversal,
Cypher query, counts, cleanup.  All test nodes carry a test_run marker
so cleanup can remove them without touching production data.
"""

from __future__ import annotations

import asyncio
import os
import sys

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "neo4jdev"
TEST_MARKER = "phase3_test_run"


async def main() -> None:
    from app.providers.graph.neo4j import Neo4jGraphStore
    from app.providers.types import GraphEdge, GraphNode

    store = Neo4jGraphStore(NEO4J_URI, username=NEO4J_USER, password=NEO4J_PASS)

    # 1. status
    status = await store.status()
    print(f"status.available={status.available}  detail={status.detail!r}")
    assert status.available, f"Neo4j not available: {status.detail}"

    # 2. upsert procurement nodes (tenant_id required by the MERGE constraint)
    TENANT = "test_tenant_phase3"
    nodes = [
        GraphNode(
            label="Supplier",
            key="test_sup_1",
            properties={"name": "Acme Corp", "tenant_id": TENANT, "test_run": TEST_MARKER},
        ),
        GraphNode(
            label="Supplier",
            key="test_sup_2",
            properties={"name": "Beta Industries", "tenant_id": TENANT, "test_run": TEST_MARKER},
        ),
        GraphNode(
            label="Contract",
            key="test_con_1",
            properties={"number": "MSA-TEST-001", "tenant_id": TENANT, "test_run": TEST_MARKER},
        ),
        GraphNode(
            label="Product",
            key="test_prod_1",
            properties={"name": "Widget A", "tenant_id": TENANT, "test_run": TEST_MARKER},
        ),
        GraphNode(
            label="Price",
            key="test_price_1",
            properties={"unit_price": 92.0, "tenant_id": TENANT, "test_run": TEST_MARKER},
        ),
    ]
    n = await store.upsert_nodes(nodes)
    print(f"upserted {n} nodes")
    assert n == 5

    # 3. upsert edges (procurement relationships) — tenant_id in properties for MATCH
    edges = [
        GraphEdge(
            type="HAS_CONTRACT",
            start_label="Supplier",
            start_key="test_sup_1",
            end_label="Contract",
            end_key="test_con_1",
            properties={"tenant_id": TENANT},
        ),
        GraphEdge(
            type="SUPPLIES",
            start_label="Supplier",
            start_key="test_sup_1",
            end_label="Product",
            end_key="test_prod_1",
            properties={"tenant_id": TENANT},
        ),
        GraphEdge(
            type="APPLIES_TO",
            start_label="Price",
            start_key="test_price_1",
            end_label="Product",
            end_key="test_prod_1",
            properties={"tenant_id": TENANT},
        ),
        GraphEdge(
            type="SUPPLIES",
            start_label="Supplier",
            start_key="test_sup_2",
            end_label="Product",
            end_key="test_prod_1",
            properties={"tenant_id": TENANT},
        ),
    ]
    e = await store.upsert_edges(edges)
    print(f"upserted {e} edges")
    assert e == 4

    # 4. neighbors — test_sup_1 should have 2 neighbors (Contract + Product)
    nbrs = await store.neighbors("Supplier", "test_sup_1")
    print(f"neighbors of test_sup_1: {[(n.type, n.end_key) for n in nbrs]}")
    assert len(nbrs) >= 2, f"expected >=2 neighbors, got {len(nbrs)}"

    # 5. multi-hop traversal: Supplier → Contract AND Product (2 hops max)
    paths = await store.traverse("Supplier", "test_sup_1", max_hops=2)
    endpoint_keys = {e.end_key for e in paths}
    print(f"traverse end keys: {endpoint_keys}")
    assert "test_con_1" in endpoint_keys, "Contract not reachable via traversal"
    assert "test_prod_1" in endpoint_keys, "Product not reachable via traversal"

    # 6. find_nodes — look up by label
    found = await store.find_nodes("Supplier", name_contains="Acme")
    print(f"find_nodes('Supplier', name_contains='Acme'): {[n.key for n in found]}")
    assert any(n.key == "test_sup_1" for n in found), "Acme Corp not found"

    # 7. multi-hop application query: suppliers for the same product
    # Note: node properties are stored in props_json, not as raw Neo4j properties.
    # Use key-based matching which IS stored as a direct property.
    rows = await store.run_read_query(
        "MATCH (s:Supplier)-[:SUPPLIES]->(p:Product {key: $pk}) RETURN s.key AS supplier_key",
        {"pk": "test_prod_1"},
    )
    supplier_keys = {r["supplier_key"] for r in rows}
    print(f"suppliers of test_prod_1: {supplier_keys}")
    assert "test_sup_1" in supplier_keys, "test_sup_1 missing from product suppliers"
    assert "test_sup_2" in supplier_keys, "test_sup_2 missing from product suppliers"

    # 8. counts
    counts = await store.counts()
    print(f"graph counts: {counts}")
    assert "nodes" in counts and counts["nodes"] >= 5

    # 9. cleanup — use driver directly since run_read_query blocks DETACH DELETE
    driver = store._get_driver()
    async with driver.session() as neo_session:
        await neo_session.run(
            "MATCH (n {tenant_id: $t}) DETACH DELETE n",
            {"t": TENANT},
        )
    print("test nodes cleaned up")
    print("✓  Neo4j live verification PASSED")

    await store.aclose()


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    asyncio.run(main())
