"""Neo4j adapter — the production graph layer (PRD s.47).

Nodes are stored with a real Neo4j label plus ``key``/``tenant_id`` properties and
a ``props_json`` string for arbitrary attributes. Edge types are written as real
relationship types, so graph traversal stays first-class and indexable.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Any

from app.core.errors import UnsupportedQueryError
from app.observability.logging import get_logger
from app.providers.types import GraphEdge, GraphNode, ProviderStatus

logger = get_logger(__name__)

_SAFE_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _ident(value: str, kind: str) -> str:
    """Labels/relationship types are interpolated (Cypher cannot parameterise them)."""
    if not _SAFE_IDENT.match(value):
        raise UnsupportedQueryError(f"Unsafe {kind} '{value}': only [A-Za-z_][A-Za-z0-9_]* is allowed.")
    return value


class Neo4jGraphStore:
    name = "neo4j"

    def __init__(self, uri: str, *, username: str, password: str, database: str = "neo4j") -> None:
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self._driver: Any = None

    def _get_driver(self) -> Any:
        if self._driver is None:
            from neo4j import AsyncGraphDatabase

            self._driver = AsyncGraphDatabase.driver(self.uri, auth=(self.username, self.password))
        return self._driver

    async def aclose(self) -> None:
        if self._driver is not None:
            await self._driver.close()
            self._driver = None

    async def _run(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        driver = self._get_driver()
        async with driver.session(database=self.database) as session:
            result = await session.run(query, parameters or {})
            return [record.data() async for record in result]

    # ------------------------------------------------------------------ writes
    async def upsert_nodes(self, nodes: Sequence[GraphNode]) -> int:
        if not nodes:
            return 0
        grouped: dict[str, list[dict[str, Any]]] = {}
        for node in nodes:
            grouped.setdefault(_ident(node.label, "label"), []).append(
                {
                    "key": node.key,
                    "tenant_id": node.properties.get("tenant_id"),
                    "document_id": node.properties.get("document_id"),
                    "props_json": json.dumps(node.properties, default=str),
                }
            )
        for label, rows in grouped.items():
            await self._run(
                f"UNWIND $rows AS row MERGE (n:{label} {{key: row.key, tenant_id: row.tenant_id}}) "
                "SET n.props_json = row.props_json, n.document_id = row.document_id",
                {"rows": rows},
            )
        return len(nodes)

    async def upsert_edges(self, edges: Sequence[GraphEdge]) -> int:
        if not edges:
            return 0
        grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        for edge in edges:
            grouped.setdefault(
                (_ident(edge.start_label, "label"), _ident(edge.type, "relationship type"), _ident(edge.end_label, "label")),
                [],
            ).append(
                {
                    "start_key": edge.start_key,
                    "end_key": edge.end_key,
                    "tenant_id": edge.properties.get("tenant_id"),
                    "document_id": edge.properties.get("document_id"),
                    "props_json": json.dumps(edge.properties, default=str),
                }
            )
        for (start_label, rel_type, end_label), rows in grouped.items():
            await self._run(
                f"UNWIND $rows AS row "
                f"MATCH (a:{start_label} {{key: row.start_key, tenant_id: row.tenant_id}}) "
                f"MATCH (b:{end_label} {{key: row.end_key, tenant_id: row.tenant_id}}) "
                f"MERGE (a)-[r:{rel_type}]->(b) SET r.props_json = row.props_json, r.document_id = row.document_id",
                {"rows": rows},
            )
        return len(edges)

    async def delete_subgraph(self, document_id: str) -> int:
        result = await self._run(
            "MATCH (n {document_id: $document_id}) DETACH DELETE n RETURN count(n) AS deleted",
            {"document_id": document_id},
        )
        return int(result[0]["deleted"]) if result else 0

    # ------------------------------------------------------------------ reads
    async def neighbors(
        self, label: str, key: str, *, edge_types: Sequence[str] | None = None, direction: str = "both"
    ) -> list[GraphEdge]:
        label = _ident(label, "label")
        type_filter = " AND type(r) IN $types" if edge_types else ""
        pattern = {
            "out": f"(a:{label} {{key: $key}})-[r]->(b)",
            "in": f"(a)-[r]->(b:{label} {{key: $key}})",
            "both": f"(a:{label} {{key: $key}})-[r]-(b)",
        }[direction]
        rows = await self._run(
            f"MATCH {pattern} WHERE true {type_filter} "
            "RETURN type(r) AS type, labels(a)[0] AS start_label, a.key AS start_key, "
            "labels(b)[0] AS end_label, b.key AS end_key, r.props_json AS props_json LIMIT 500",
            {"key": key, "types": list(edge_types or [])},
        )
        return [_row_to_edge(row) for row in rows]

    async def traverse(
        self,
        start_label: str,
        start_key: str,
        *,
        max_hops: int = 2,
        edge_types: Sequence[str] | None = None,
        tenant_id: str | None = None,
    ) -> list[GraphEdge]:
        label = _ident(start_label, "label")
        hops = max(1, min(int(max_hops), 5))
        type_filter = " AND all(r IN relationships(p) WHERE type(r) IN $types)" if edge_types else ""
        rows = await self._run(
            f"MATCH p = (a:{label} {{key: $key}})-[*1..{hops}]-(b) "
            f"WHERE size(relationships(p)) <= {hops} {type_filter} "
            "UNWIND relationships(p) AS r "
            "RETURN DISTINCT type(r) AS type, labels(startNode(r))[0] AS start_label, startNode(r).key AS start_key, "
            "labels(endNode(r))[0] AS end_label, endNode(r).key AS end_key, r.props_json AS props_json LIMIT 500",
            {"key": key, "types": list(edge_types or [])},
        )
        return [_row_to_edge(row) for row in rows]

    async def find_nodes(
        self, label: str, *, name_contains: str | None = None, limit: int = 25, tenant_id: str | None = None
    ) -> list[GraphNode]:
        label = _ident(label, "label")
        params: dict[str, Any] = {"limit": limit, "tenant_id": tenant_id}
        where = "WHERE ($tenant_id IS NULL OR n.tenant_id = $tenant_id)"
        if name_contains:
            where += " AND toLower(n.props_json) CONTAINS toLower($needle)"
            params["needle"] = name_contains
        rows = await self._run(
            f"MATCH (n:{label}) {where} RETURN n.key AS key, n.props_json AS props_json LIMIT $limit", params
        )
        return [
            GraphNode(label=label, key=row["key"], properties=json.loads(row["props_json"] or "{}"))
            for row in rows
        ]

    async def run_read_query(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        lowered = query.lower()
        forbidden = ("create", "merge", "delete", "set ", "remove", "drop", "call apoc")
        if any(word in lowered for word in forbidden):
            raise UnsupportedQueryError("Only read-only MATCH ... RETURN queries are permitted.")
        rows = await self._run(query, parameters)
        # Node values come back as neo4j Node objects; normalise them.
        return [_flatten_row(row) for row in rows]

    async def counts(self) -> dict[str, int]:
        nodes = await self._run("MATCH (n) RETURN count(n) AS c")
        edges = await self._run("MATCH ()-[r]->() RETURN count(r) AS c")
        labels = await self._run("MATCH (n) RETURN labels(n)[0] AS label, count(*) AS c")
        result = {
            "nodes": int(nodes[0]["c"]) if nodes else 0,
            "edges": int(edges[0]["c"]) if edges else 0,
        }
        for row in labels:
            result[f"nodes:{row['label']}"] = int(row["c"])
        return result

    async def status(self) -> ProviderStatus:
        try:
            counts = await self.counts()
            return ProviderStatus.of(
                "graph", self.name, True, detail=f"connected to {self.uri}", **counts
            )
        except Exception as exc:  # noqa: BLE001
            return ProviderStatus.of("graph", self.name, False, detail=f"unreachable: {type(exc).__name__}")


def _row_to_edge(row: dict[str, Any]) -> GraphEdge:
    return GraphEdge(
        type=row.get("type", ""),
        start_label=row.get("start_label") or "",
        start_key=row.get("start_key") or "",
        end_label=row.get("end_label") or "",
        end_key=row.get("end_key") or "",
        properties=json.loads(row.get("props_json") or "{}"),
    )


def _flatten_row(row: dict[str, Any]) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, dict) and "key" in value and "props_json" in value:
            flat[key] = {
                "label": "_".join(value.get("labels", []) or []) or None,
                "key": value["key"],
                "properties": json.loads(value.get("props_json") or "{}"),
            }
        elif isinstance(value, list):
            flat[key] = [_flatten_row(v) if isinstance(v, dict) else v for v in value]
        else:
            flat[key] = value
    return flat
