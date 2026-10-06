"""Local property-graph provider (SQLite).

Stores labelled nodes and typed relationships and performs genuine multi-hop
breadth-first traversal, including the documented Cypher subset. Used when
``GRAPH_PROVIDER=local`` so GraphRAG works in development and CI without a
Neo4j server; ``GRAPH_PROVIDER=neo4j`` runs the same queries on Neo4j.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections import deque
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import aiosqlite

from app.core.errors import UnsupportedQueryError
from app.observability.logging import get_logger
from app.providers.graph.cypher_subset import ReadQueryPlan, parse_read_query
from app.providers.types import GraphEdge, GraphNode, ProviderStatus

logger = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS graph_nodes (
    node_id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    key TEXT NOT NULL,
    tenant_id TEXT,
    document_id TEXT,
    properties TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS ix_graph_nodes_label_key ON graph_nodes(label, key);
CREATE INDEX IF NOT EXISTS ix_graph_nodes_doc ON graph_nodes(document_id);
CREATE TABLE IF NOT EXISTS graph_edges (
    edge_id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    start_label TEXT NOT NULL,
    start_key TEXT NOT NULL,
    end_label TEXT NOT NULL,
    end_key TEXT NOT NULL,
    tenant_id TEXT,
    document_id TEXT,
    properties TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS ix_graph_edges_start ON graph_edges(start_label, start_key);
CREATE INDEX IF NOT EXISTS ix_graph_edges_end ON graph_edges(end_label, end_key);
CREATE INDEX IF NOT EXISTS ix_graph_edges_type ON graph_edges(type);
CREATE INDEX IF NOT EXISTS ix_graph_edges_doc ON graph_edges(document_id);
"""


def _node_id(label: str, key: str, tenant_id: str | None) -> str:
    return f"{tenant_id or '*'}|{label}|{key}"


def _edge_id(edge: GraphEdge, tenant_id: str | None) -> str:
    raw = (
        f"{tenant_id or '*'}|{edge.type}|{edge.start_label}|{edge.start_key}|{edge.end_label}|{edge.end_key}"
    )
    return hashlib.blake2b(raw.encode("utf-8"), digest_size=16).hexdigest()


class LocalGraphStore:
    name = "local"

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialised = False
        self._lock = asyncio.Lock()

    async def _connect(self) -> aiosqlite.Connection:
        connection = await aiosqlite.connect(self.path)
        connection.row_factory = aiosqlite.Row
        if not self._initialised:
            await connection.executescript(_SCHEMA)
            await connection.commit()
            self._initialised = True
        return connection

    @staticmethod
    def _row_to_node(row: aiosqlite.Row) -> GraphNode:
        return GraphNode(
            label=row["label"],
            key=row["key"],
            properties=json.loads(row["properties"] or "{}"),
        )

    @staticmethod
    def _row_to_edge(row: aiosqlite.Row) -> GraphEdge:
        return GraphEdge(
            type=row["type"],
            start_label=row["start_label"],
            start_key=row["start_key"],
            end_label=row["end_label"],
            end_key=row["end_key"],
            properties=json.loads(row["properties"] or "{}"),
        )

    # ------------------------------------------------------------------ writes
    async def upsert_nodes(self, nodes: Sequence[GraphNode]) -> int:
        if not nodes:
            return 0
        async with self._lock:
            connection = await self._connect()
            try:
                rows = []
                for node in nodes:
                    props = dict(node.properties)
                    tenant = props.get("tenant_id")
                    rows.append(
                        (
                            _node_id(node.label, node.key, tenant),
                            node.label,
                            node.key,
                            tenant,
                            props.get("document_id"),
                            json.dumps(props, default=str),
                        )
                    )
                await connection.executemany(
                    "INSERT INTO graph_nodes (node_id, label, key, tenant_id, document_id, properties) "
                    "VALUES (?,?,?,?,?,?) ON CONFLICT(node_id) DO UPDATE SET properties=excluded.properties, "
                    "document_id=excluded.document_id",
                    rows,
                )
                await connection.commit()
                return len(rows)
            finally:
                await connection.close()

    async def upsert_edges(self, edges: Sequence[GraphEdge]) -> int:
        if not edges:
            return 0
        async with self._lock:
            connection = await self._connect()
            try:
                rows = []
                for edge in edges:
                    props = dict(edge.properties)
                    tenant = props.get("tenant_id")
                    rows.append(
                        (
                            _edge_id(edge, tenant),
                            edge.type,
                            edge.start_label,
                            edge.start_key,
                            edge.end_label,
                            edge.end_key,
                            tenant,
                            props.get("document_id"),
                            json.dumps(props, default=str),
                        )
                    )
                await connection.executemany(
                    "INSERT INTO graph_edges (edge_id, type, start_label, start_key, end_label, end_key, "
                    "tenant_id, document_id, properties) VALUES (?,?,?,?,?,?,?,?,?) "
                    "ON CONFLICT(edge_id) DO UPDATE SET properties=excluded.properties",
                    rows,
                )
                await connection.commit()
                return len(rows)
            finally:
                await connection.close()

    async def delete_subgraph(self, document_id: str) -> int:
        async with self._lock:
            connection = await self._connect()
            try:
                cursor = await connection.execute(
                    "DELETE FROM graph_edges WHERE document_id = ?", (document_id,)
                )
                removed = cursor.rowcount or 0
                await connection.execute("DELETE FROM graph_nodes WHERE document_id = ?", (document_id,))
                await connection.commit()
                return removed
            finally:
                await connection.close()

    # ------------------------------------------------------------------ reads
    async def neighbors(
        self, label: str, key: str, *, edge_types: Sequence[str] | None = None, direction: str = "both"
    ) -> list[GraphEdge]:
        clauses = []
        params: list[Any] = []
        sides = {
            "out": "start_label = ? AND start_key = ?",
            "in": "end_label = ? AND end_key = ?",
            "both": "((start_label = ? AND start_key = ?) OR (end_label = ? AND end_key = ?))",
        }
        clauses.append(sides.get(direction, sides["both"]))
        params.extend([label, key] if direction != "both" else [label, key, label, key])
        if edge_types:
            placeholders = ",".join("?" for _ in edge_types)
            clauses.append(f"type IN ({placeholders})")
            params.extend(edge_types)
        connection = await self._connect()
        try:
            cursor = await connection.execute(
                f"SELECT * FROM graph_edges WHERE {' AND '.join(clauses)}", params
            )
            rows = await cursor.fetchall()
            return [self._row_to_edge(row) for row in rows]
        finally:
            await connection.close()

    async def traverse(
        self,
        start_label: str,
        start_key: str,
        *,
        max_hops: int = 2,
        edge_types: Sequence[str] | None = None,
        tenant_id: str | None = None,
    ) -> list[GraphEdge]:
        seen: set[str] = set()
        collected: list[GraphEdge] = []
        frontier: deque[tuple[str, str, int]] = deque([(start_label, start_key, 0)])
        visited_nodes: set[tuple[str, str]] = {(start_label, start_key)}
        while frontier:
            label, key, depth = frontier.popleft()
            if depth >= max_hops:
                continue
            for edge in await self.neighbors(label, key, edge_types=edge_types, direction="both"):
                if tenant_id and edge.properties.get("tenant_id") not in {None, tenant_id}:
                    continue
                edge_key = f"{edge.type}|{edge.start_label}|{edge.start_key}|{edge.end_label}|{edge.end_key}"
                if edge_key not in seen:
                    seen.add(edge_key)
                    collected.append(edge)
                other = (
                    (edge.end_label, edge.end_key)
                    if (edge.start_label, edge.start_key) == (label, key)
                    else (edge.start_label, edge.start_key)
                )
                if other not in visited_nodes:
                    visited_nodes.add(other)
                    frontier.append((other[0], other[1], depth + 1))
        return collected

    async def find_nodes(
        self, label: str, *, name_contains: str | None = None, limit: int = 25, tenant_id: str | None = None
    ) -> list[GraphNode]:
        clauses = ["label = ?"]
        params: list[Any] = [label]
        if tenant_id:
            clauses.append("(tenant_id = ? OR tenant_id IS NULL)")
            params.append(tenant_id)
        connection = await self._connect()
        try:
            cursor = await connection.execute(
                f"SELECT * FROM graph_nodes WHERE {' AND '.join(clauses)}", params
            )
            rows = await cursor.fetchall()
        finally:
            await connection.close()
        nodes = [self._row_to_node(row) for row in rows]
        if name_contains:
            needle = name_contains.lower()
            nodes = [
                n
                for n in nodes
                if needle in str(n.properties.get("name", "")).lower() or needle in n.key.lower()
            ]
        return nodes[:limit]

    async def run_read_query(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        plan = parse_read_query(query)
        params = parameters or {}
        rows = await self._execute_plan(plan, params)
        return rows

    async def _execute_plan(self, plan: ReadQueryPlan, params: dict[str, Any]) -> list[dict[str, Any]]:
        start_props = {_strip_param(key): _resolve(value, params) for key, value in plan.start.props.items()}
        starts = await self.find_nodes(
            plan.start.label or "",
            name_contains=str(start_props.get("name_contains") or "") or None,
            limit=50,
        )
        starts = [n for n in starts if all(_node_has(n, k, v) for k, v in start_props.items())]
        if not starts:
            return []

        results: list[dict[str, Any]] = []
        for start in starts:
            self._walk(plan, start, 0, {}, [], results, params)
            if len(results) >= plan.limit:
                break
        return results[: plan.limit]

    def _walk(
        self,
        plan: ReadQueryPlan,
        node: GraphNode,
        hop_index: int,
        bound: dict[str, GraphNode],
        path: list[GraphEdge],
        results: list[dict[str, Any]],
        params: dict[str, Any],
    ) -> None:
        """Depth-first expansion over the hop pattern (synchronous, in-memory)."""
        import sqlite3

        if hop_index >= len(plan.hops):
            row = {var: _serialize(nd) for var, nd in bound.items()}
            row["_path"] = [
                {
                    "type": e.type,
                    "from": f"{e.start_label}:{e.start_key}",
                    "to": f"{e.end_label}:{e.end_key}",
                    "properties": e.properties,
                }
                for e in path
            ]
            if _passes_where(plan, bound, params):
                results.append(row)
            return

        hop = plan.hops[hop_index]
        types = hop.types or None
        connection = sqlite3.connect(self.path)
        try:
            connection.row_factory = sqlite3.Row

            def load_edges(label: str, key: str) -> list[GraphEdge]:
                clauses = ["((start_label = ? AND start_key = ?) OR (end_label = ? AND end_key = ?))"]
                args: list[Any] = [label, key, label, key]
                if types:
                    clauses.append(f"type IN ({','.join('?' for _ in types)})")
                    args.extend(types)
                cursor = connection.execute(f"SELECT * FROM graph_edges WHERE {' AND '.join(clauses)}", args)
                return [
                    GraphEdge(
                        type=r["type"],
                        start_label=r["start_label"],
                        start_key=r["start_key"],
                        end_label=r["end_label"],
                        end_key=r["end_key"],
                        properties=json.loads(r["properties"] or "{}"),
                    )
                    for r in cursor.fetchall()
                ]

            def load_node(label: str, key: str) -> GraphNode | None:
                cursor = connection.execute(
                    "SELECT * FROM graph_nodes WHERE label = ? AND key = ? LIMIT 1", (label, key)
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                return GraphNode(
                    label=row["label"], key=row["key"], properties=json.loads(row["properties"] or "{}")
                )

            max_hops = max(1, hop.max_hops)
            frontier: list[tuple[GraphNode, list[GraphEdge]]] = [(node, [])]
            for depth in range(max_hops):
                next_frontier: list[tuple[GraphNode, list[GraphEdge]]] = []
                for current, trail in frontier:
                    for edge in load_edges(current.label, current.key):
                        other_ref = (
                            (edge.end_label, edge.end_key)
                            if (edge.start_label, edge.start_key) == (current.label, current.key)
                            else (edge.start_label, edge.start_key)
                        )
                        other = load_node(*other_ref)
                        if other is None:
                            continue
                        new_trail = [*trail, edge]
                        if hop.label and other.label != hop.label:
                            continue
                        if depth + 1 >= hop.min_hops:
                            updated = {**bound, hop.var: other}
                            self._walk(
                                plan, other, hop_index + 1, updated, [*path, *new_trail], results, params
                            )
                            if len(results) >= plan.limit:
                                return
                        if depth + 1 < max_hops:
                            next_frontier.append((other, new_trail))
                frontier = next_frontier
                if not frontier:
                    break
        finally:
            connection.close()

    async def counts(self) -> dict[str, int]:
        connection = await self._connect()
        try:
            nodes = await (await connection.execute("SELECT COUNT(*) FROM graph_nodes")).fetchone()
            edges = await (await connection.execute("SELECT COUNT(*) FROM graph_edges")).fetchone()
            labels = await (
                await connection.execute("SELECT label, COUNT(*) AS c FROM graph_nodes GROUP BY label")
            ).fetchall()
        finally:
            await connection.close()
        result = {"nodes": int(nodes[0]) if nodes else 0, "edges": int(edges[0]) if edges else 0}
        for row in labels:
            result[f"nodes:{row['label']}"] = int(row["c"])
        return result

    async def status(self) -> ProviderStatus:
        try:
            counts = await self.counts()
            return ProviderStatus.of(
                "graph", self.name, True, detail=f"sqlite property graph at {self.path}", **counts
            )
        except Exception as exc:  # noqa: BLE001
            return ProviderStatus.of("graph", self.name, False, detail=f"{type(exc).__name__}: {exc}")


def _strip_param(value: str) -> str:
    return value.strip().lstrip("$").strip()


def _resolve(value: str, params: dict[str, Any]) -> Any:
    if value.startswith("$"):
        return params.get(value[1:])
    if value.startswith("name_contains:"):
        return value.split(":", 1)[1]
    return value


def _node_has(node: GraphNode, key: str, expected: Any) -> bool:
    if expected is None:
        return True
    if key == "key":
        return node.key == expected
    if key == "name_contains":
        return str(expected).lower() in str(node.properties.get("name", "")).lower()
    actual = node.properties.get(key)
    if isinstance(expected, str) and isinstance(actual, str):
        return actual.lower() == expected.lower()
    return actual == expected


def _serialize(node: GraphNode) -> dict[str, Any]:
    return {"label": node.label, "key": node.key, "properties": node.properties}


def _passes_where(plan: ReadQueryPlan, bound: dict[str, GraphNode], params: dict[str, Any]) -> bool:
    for clause in plan.where:
        node = bound.get(clause.var)
        if node is None:
            return False
        actual = node.properties.get(clause.prop)
        expected = _resolve(clause.value, params)
        if actual is None:
            return False
        left, right = str(actual).lower(), str(expected).lower()
        if clause.op == "CONTAINS" and right not in left:
            return False
        if clause.op == "=" and left != right:
            return False
        if clause.op == "<>" and left == right:
            return False
        if clause.op in {">", "<", ">=", "<="}:
            try:
                lhs, rhs = float(actual), float(expected)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                return False
            if clause.op == ">" and not lhs > rhs:
                return False
            if clause.op == "<" and not lhs < rhs:
                return False
            if clause.op == ">=" and not lhs >= rhs:
                return False
            if clause.op == "<=" and not lhs <= rhs:
                return False
    return True


__all__ = ["LocalGraphStore", "UnsupportedQueryError"]
