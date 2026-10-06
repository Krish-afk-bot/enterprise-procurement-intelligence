"""Knowledge graph explorer.

The graph is a derived index (supplier → contract → amendment → product → price →
document), rebuilt from the ingested documents. Traversals are executed by the
active graph provider; when no graph store is reachable the endpoints report that
rather than returning an empty picture.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import ContainerDep, PrincipalDep
from app.schemas.common import Page
from app.security.rbac import PERM_GRAPH_READ, Principal

router = APIRouter(tags=["graph"], prefix="/graph")

NODE_LABELS = ("Supplier", "Contract", "Product", "Price", "Document", "ComplianceCertificate", "Amendment")


@router.get("/overview", summary="Node and edge counts by label and type")
async def overview(
    principal: Principal = PrincipalDep,
    container=ContainerDep,
) -> dict:
    principal.require(PERM_GRAPH_READ)
    status = await container.graph.status()
    attributes = status.attributes or {}
    nodes = {key.split(":", 1)[1]: value for key, value in attributes.items() if key.startswith("nodes:")}
    edges = {key.split(":", 1)[1]: value for key, value in attributes.items() if key.startswith("edges:")}
    labels: dict[str, int] = {}
    for label in NODE_LABELS:
        count = 0
        try:
            found = await container.graph.find_nodes(label, limit=1, tenant_id=principal.tenant_id)
            count = len(found)
        except Exception:  # noqa: BLE001 - a label the store does not carry is simply absent
            count = 0
        labels[label] = nodes.get(label, count)
    return {
        "provider": status.name,
        "available": status.available,
        "detail": status.detail,
        "nodes_total": int(attributes.get("nodes") or 0),
        "edges_total": int(attributes.get("edges") or 0),
        "nodes_by_label": labels,
        "edges_by_type": edges,
        "notes": [
            "Counts are reported by the active graph provider.",
            "The graph is derived from ingested documents and rebuilt on re-indexing.",
        ],
    }


@router.get("/nodes", summary="Find graph nodes by label and name")
async def find_nodes(
    label: str = Query(..., description="Node label, e.g. Supplier"),
    name_contains: str | None = None,
    limit: int = 25,
    principal: Principal = PrincipalDep,
    container=ContainerDep,
) -> dict:
    principal.require(PERM_GRAPH_READ)
    nodes = await container.graph.find_nodes(
        label, name_contains=name_contains, limit=limit, tenant_id=principal.tenant_id
    )
    return {
        "label": label,
        "items": [
            {"label": node.label, "key": node.key, "properties": node.properties} for node in nodes
        ],
        "total": len(nodes),
    }


@router.get("/nodes/{label}/{key}/neighbors", summary="Direct neighbours of a node")
async def neighbors(
    label: str,
    key: str,
    direction: str = "both",
    max_hops: int = 1,
    principal: Principal = PrincipalDep,
    container=ContainerDep,
) -> dict:
    principal.require(PERM_GRAPH_READ)
    if max_hops <= 1:
        edges = await container.graph.neighbors(label, key, direction=direction)
    else:
        edges = await container.graph.traverse(
            label, key, max_hops=min(max_hops, 4), tenant_id=principal.tenant_id
        )
    return {
        "node": {"label": label, "key": key},
        "edges": [
            {
                "type": edge.type,
                "start": {"label": edge.start_label, "key": edge.start_key},
                "end": {"label": edge.end_label, "key": edge.end_key},
                "properties": edge.properties,
            }
            for edge in edges
        ],
        "total": len(edges),
    }


@router.get("/paths", summary="Multi-hop traversal from a node")
async def paths(
    label: str,
    key: str,
    max_hops: int = 2,
    principal: Principal = PrincipalDep,
    container=ContainerDep,
) -> dict:
    principal.require(PERM_GRAPH_READ)
    edges = await container.graph.traverse(
        label, key, max_hops=min(max(max_hops, 1), 4), tenant_id=principal.tenant_id
    )
    nodes = sorted({(edge.start_label, edge.start_key) for edge in edges} | {(edge.end_label, edge.end_key) for edge in edges})
    return {
        "root": {"label": label, "key": key},
        "hops": min(max(max_hops, 1), 4),
        "nodes": [{"label": node_label, "key": node_key} for node_label, node_key in nodes],
        "edges": [
            {
                "type": edge.type,
                "start": {"label": edge.start_label, "key": edge.start_key},
                "end": {"label": edge.end_label, "key": edge.end_key},
            }
            for edge in edges
        ],
        "total_edges": len(edges),
    }
