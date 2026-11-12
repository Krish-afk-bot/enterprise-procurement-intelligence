"""Clause and obligation nodes.

These tests use a recording provider rather than a database: the builder's job is
to decide which nodes and edges to emit, and the assertions are about that
decision — grouping, dedupe, provenance and the rule that a clause without a duty
produces no obligation.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app.graph.builder import (
    LABEL_CLAUSE,
    LABEL_OBLIGATION,
    GraphBuilder,
    clause_node,
    obligation_node,
)

TENANT = "ten_test"
DOC = "doc_test"


class RecordingGraph:
    name = "recording"

    def __init__(self) -> None:
        self.nodes: list = []
        self.edges: list = []

    async def upsert_nodes(self, nodes) -> int:
        self.nodes.extend(nodes)
        return len(nodes)

    async def upsert_edges(self, edges) -> int:
        self.edges.extend(edges)
        return len(edges)


def chunk(**overrides):
    base = {
        "clause": "3.2",
        "section": "Payment",
        "page_number": 4,
        "content": "The Supplier shall invoice monthly.",
        "content_type": "paragraph",
        "effective_date": None,
        "expiry_date": None,
    }
    return SimpleNamespace(**{**base, **overrides})


async def build(*chunks, title="Contract") -> tuple[RecordingGraph, int]:
    graph = RecordingGraph()
    written = await GraphBuilder(graph).link_clauses(
        tenant_id=TENANT,
        document_id=DOC,
        title=title,
        document_type="contract",
        version=1,
        chunks=list(chunks),
    )
    return graph, written


class TestClauseNodes:
    async def test_chunks_are_grouped_by_clause(self) -> None:
        graph, written = await build(
            chunk(content="First part."),
            chunk(content="Second part."),
        )
        clauses = [node for node in graph.nodes if node.label == LABEL_CLAUSE]
        assert written == 1
        assert len(clauses) == 1
        assert "First part." in clauses[0].properties["text"]
        assert "Second part." in clauses[0].properties["text"]

    async def test_separate_clauses_become_separate_nodes(self) -> None:
        graph, written = await build(chunk(clause="3.2"), chunk(clause="4.1"))
        clauses = {node.key for node in graph.nodes if node.label == LABEL_CLAUSE}
        assert written == 2
        assert clauses == {f"{DOC}:3.2", f"{DOC}:4.1"}

    async def test_chunks_without_a_clause_are_ignored(self) -> None:
        graph, written = await build(chunk(clause=None), chunk(clause="  "))
        assert written == 0
        assert graph.nodes == []
        assert graph.edges == []

    async def test_clause_carries_provenance(self) -> None:
        graph, _ = await build(chunk(effective_date=date(2024, 1, 1), expiry_date=date(2025, 1, 1)))
        node = next(node for node in graph.nodes if node.label == LABEL_CLAUSE)
        assert node.properties["document_id"] == DOC
        assert node.properties["source_page"] == 4
        assert node.properties["tenant_id"] == TENANT
        assert node.properties["effective_date"] == "2024-01-01"
        assert node.properties["expiry_date"] == "2025-01-01"

    async def test_document_contains_clause_edge(self) -> None:
        graph, _ = await build(chunk())
        contains = [edge for edge in graph.edges if edge.type == "CONTAINS"]
        assert len(contains) == 1
        assert contains[0].start_label == "Document"
        assert contains[0].end_label == LABEL_CLAUSE
        assert contains[0].properties["document_id"] == DOC


class TestObligations:
    async def test_modal_verb_creates_an_obligation(self) -> None:
        graph, _ = await build(chunk(content="The Supplier shall deliver by the 5th. Invoices are monthly."))
        obligations = [node for node in graph.nodes if node.label == LABEL_OBLIGATION]
        assert len(obligations) == 1
        assert "shall deliver" in obligations[0].properties["text"]
        assert "Invoices are monthly" not in obligations[0].properties["text"]
        assert obligations[0].properties["detection"] == "modal_verb"

    async def test_clause_without_a_duty_has_no_obligation(self) -> None:
        graph, _ = await build(chunk(content="This clause is for information only."))
        assert not [node for node in graph.nodes if node.label == LABEL_OBLIGATION]
        assert not [edge for edge in graph.edges if edge.type == "IMPOSES"]

    async def test_obligation_edges_point_at_clause_and_document(self) -> None:
        graph, _ = await build(chunk())
        types = {edge.type for edge in graph.edges}
        assert {"CONTAINS", "IMPOSES", "EVIDENCED_BY"} <= types
        imposes = next(edge for edge in graph.edges if edge.type == "IMPOSES")
        assert imposes.start_label == LABEL_CLAUSE
        assert imposes.end_label == LABEL_OBLIGATION

    async def test_each_clause_gets_at_most_one_obligation(self) -> None:
        graph, _ = await build(
            chunk(content="The Supplier shall invoice. The Buyer must pay. Each party will cooperate.")
        )
        assert len([node for node in graph.nodes if node.label == LABEL_OBLIGATION]) == 1


class TestNodeBuilders:
    def test_clause_key_is_document_scoped(self) -> None:
        node = clause_node(
            tenant_id=TENANT, document_id=DOC, clause="7", text="x", page=1
        )
        assert node.key == f"{DOC}:7"

    def test_obligation_text_is_bounded(self) -> None:
        node = obligation_node(
            tenant_id=TENANT, document_id=DOC, clause="7", text="shall " * 400, page=1
        )
        assert len(node.properties["text"]) <= 600
