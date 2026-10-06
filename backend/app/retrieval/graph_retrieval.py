"""GraphRAG retrieval (PRD s.34-35).

Answers relationship questions by traversing the knowledge graph:

    Supplier → HAS_CONTRACT → Contract → AMENDS/CONTAINS → Price/Amendment
             → APPLIES_TO → Product
             → COMPLIES_WITH → ComplianceCertificate

Each returned path carries the source documents/pages of the structured rows it
was built from, so a graph answer is as citable as a document answer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.container import Container
from app.db.models import ComplianceCertificate, Document, Price, Product, Supplier
from app.graph.builder import (
    LABEL_PRICE,
    LABEL_SUPPLIER,
)
from app.observability.logging import get_logger
from app.providers.types import GraphEdge
from app.retrieval.context import CitationDraft
from app.retrieval.query_understanding import QueryPlan
from app.security.rbac import Principal

logger = get_logger(__name__)


@dataclass(slots=True)
class GraphPath:
    hops: int
    description: str
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "hops": self.hops,
            "description": self.description,
            "nodes": self.nodes,
            "edges": self.edges,
            "citations": self.citations,
        }


@dataclass(slots=True)
class GraphResult:
    traversal: bool = False
    paths: list[GraphPath] = field(default_factory=list)
    entities: list[dict[str, Any]] = field(default_factory=list)
    citations: list[CitationDraft] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    limits: dict[str, Any] = field(default_factory=dict)

    @property
    def has_data(self) -> bool:
        return bool(self.paths)

    def as_dict(self) -> dict[str, Any]:
        return {
            "traversal": self.traversal,
            "paths": [path.as_dict() for path in self.paths],
            "entities": self.entities,
            "notes": self.notes,
            "limits": self.limits,
        }


async def graph_lookup(
    container: Container,
    session: AsyncSession,
    principal: Principal,
    plan: QueryPlan,
    *,
    max_hops: int = 3,
    max_paths: int = 12,
) -> GraphResult:
    result = GraphResult()
    if not plan.requires_graph and not plan.supplier_ids:
        return result
    result.traversal = True

    supplier_ids = list(plan.supplier_ids)
    if not supplier_ids and plan.suppliers:
        # Resolve by name through the graph itself when the vocabulary missed it.
        for name in plan.suppliers:
            nodes = await container.graph.find_nodes(
                LABEL_SUPPLIER, name_contains=name, tenant_id=principal.tenant_id, limit=5
            )
            supplier_ids.extend(node.key for node in nodes)

    if not supplier_ids:
        result.notes.append(
            "The graph traversal was requested but no supplier could be identified in the knowledge graph."
        )
        return result

    price_pages = await _price_sources(session, principal, supplier_ids)
    for supplier_id in supplier_ids[:4]:
        edges = await container.graph.traverse(LABEL_SUPPLIER, supplier_id, max_hops=max_hops)
        tenant_edges = [
            edge for edge in edges if edge.properties.get("tenant_id") in {None, principal.tenant_id}
        ]
        chain = _summarise_chain(tenant_edges)
        if not chain:
            continue
        citations = _citations_for_chain(chain, price_pages)
        result.paths.append(
            GraphPath(
                hops=len(chain),
                description=_describe_chain(chain, supplier_id),
                nodes=[{"id": edge["to"], "label": edge["to_label"]} for edge in chain],
                edges=chain,
                citations=citations,
            )
        )
        for edge in chain:
            citation = _citation_from_edge(edge, price_pages)
            if citation is not None:
                result.citations.append(citation)
        if len(result.paths) >= max_paths:
            break

    if plan.intent.value == "compliance_check":
        certificates = await _compliance_paths(session, principal, supplier_ids)
        for certificate in certificates:
            result.paths.append(
                GraphPath(hops=2, description=certificate["description"], citations=certificate["citations"])
            )
            result.citations.extend(
                CitationDraft(
                    chunk_id=None,
                    document_id=citation.get("document_id"),
                    document_name=citation.get("document_name") or "compliance certificate",
                    document_type="compliance_certificate",
                    page=citation.get("page"),
                    section="Compliance",
                    snippet=certificate["description"],
                    evidence_type="graph_compliance",
                    verified=True,
                )
                for citation in certificate["citations"]
            )

    result.limits = {"max_hops": max_hops, "paths": len(result.paths)}
    if not result.paths:
        result.notes.append(
            "No graph path linked the requested entities; the answer relies on document and structured evidence."
        )
    return result


def _summarise_chain(edges: list[GraphEdge]) -> list[dict[str, Any]]:
    """Reduce a traversed edge set into a directional chain, deepest first."""
    adjacency: dict[tuple[str, str], list[GraphEdge]] = {}
    for edge in edges:
        adjacency.setdefault((edge.start_label, edge.start_key), []).append(edge)
        adjacency.setdefault((edge.end_label, edge.end_key), []).append(edge)

    chain: list[dict[str, Any]] = []
    for edge in edges:
        chain.append(
            {
                "type": edge.type,
                "from": f"{edge.start_label}:{edge.start_key}",
                "from_label": edge.start_label,
                "to": f"{edge.end_label}:{edge.end_key}",
                "to_label": edge.end_label,
                "properties": edge.properties,
            }
        )
    return chain


def _describe_chain(chain: list[dict[str, Any]], supplier_id: str) -> str:
    labels = [entry["from_label"] for entry in chain]
    return f"{LABEL_SUPPLIER}:{supplier_id} traversal across {len(chain)} relationship(s): " + " → ".join(
        dict.fromkeys([*labels, chain[-1]["to_label"]])
    )


async def _price_sources(
    session: AsyncSession, principal: Principal, supplier_ids: list[str]
) -> dict[str, dict[str, Any]]:
    """Map price_id → source document/page so graph hops can be cited."""
    rows = (
        await session.execute(
            select(
                Price.id,
                Price.source_document_id,
                Price.source_page,
                Document.title,
                Document.filename,
                Price.currency,
                Price.unit_price,
                Price.effective_date,
                Price.amendment_ref,
                Price.product_id,
            )
            .outerjoin(Document, Price.source_document_id == Document.id)
            .where(Price.tenant_id == principal.tenant_id)
        )
    ).all()
    product_names: dict[str, str] = {}
    for product_id, name in (
        await session.execute(
            select(Product.id, Product.name).where(Product.tenant_id == principal.tenant_id)
        )
    ).all():
        product_names[product_id] = name
    return {
        row[0]: {
            "document_id": row[1],
            "page": row[2],
            "document_name": row[3] or row[4],
            "currency": row[5],
            "unit_price": row[6],
            "effective_date": row[7].isoformat() if row[7] else None,
            "amendment_ref": row[8],
            "product_name": product_names.get(row[9] or "", None),
        }
        for row in rows
    }


def _citations_for_chain(
    chain: list[dict[str, Any]], price_sources: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    for entry in chain:
        citation = _edge_citation_payload(entry, price_sources)
        if citation:
            citations.append(citation)
    return citations


def _citation_from_edge(
    edge: dict[str, Any], price_sources: dict[str, dict[str, Any]]
) -> CitationDraft | None:
    payload = _edge_citation_payload(edge, price_sources)
    if not payload:
        return None
    return CitationDraft(
        chunk_id=None,
        document_id=payload.get("document_id"),
        document_name=payload.get("document_name") or "graph evidence",
        document_type="graph",
        page=payload.get("page"),
        section=payload.get("edge_type"),
        snippet=payload.get("snippet", ""),
        evidence_type="graph",
        verified=True,
    )


def _edge_citation_payload(
    edge: dict[str, Any], price_sources: dict[str, dict[str, Any]]
) -> dict[str, Any] | None:
    if edge["to_label"] == LABEL_PRICE:
        price_id = edge["to"].split(":", 1)[-1]
        source = price_sources.get(price_id)
        if source and source.get("document_id"):
            return {
                "document_id": source["document_id"],
                "document_name": source["document_name"],
                "page": source["page"],
                "edge_type": edge["type"],
                "snippet": (
                    f"{source.get('product_name') or 'item'}: {source['currency']} {source['unit_price']:,.2f}"
                    + (f" effective {source['effective_date']}" if source.get("effective_date") else "")
                    + (f" ({source['amendment_ref']})" if source.get("amendment_ref") else "")
                ),
            }
    document_id = edge["properties"].get("document_id")
    if document_id:
        return {
            "document_id": document_id,
            "document_name": None,
            "page": edge["properties"].get("source_page"),
            "edge_type": edge["type"],
            "snippet": f"{edge['type']}: {edge['from']} → {edge['to']}",
        }
    return None


async def _compliance_paths(
    session: AsyncSession, principal: Principal, supplier_ids: list[str]
) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            select(ComplianceCertificate, Supplier.name, Document.title, Document.filename)
            .outerjoin(Supplier, ComplianceCertificate.supplier_id == Supplier.id)
            .outerjoin(Document, ComplianceCertificate.source_document_id == Document.id)
            .where(
                ComplianceCertificate.tenant_id == principal.tenant_id,
                ComplianceCertificate.supplier_id.in_(supplier_ids),
            )
        )
    ).all()
    today = date.today()
    paths: list[dict[str, Any]] = []
    for certificate, supplier_name, title, filename in rows:
        in_force = certificate.status == "active" and not (
            certificate.expiry_date and certificate.expiry_date < today
        )
        paths.append(
            {
                "description": (
                    f"{supplier_name or 'Supplier'} COMPLIES_WITH {certificate.certificate_type}"
                    + (f" ({certificate.certificate_number})" if certificate.certificate_number else "")
                    + (" — currently in force" if in_force else " — not in force")
                ),
                "citations": [
                    {
                        "document_id": certificate.source_document_id,
                        "document_name": title or filename or "compliance certificate",
                        "page": certificate.source_page,
                    }
                ],
            }
        )
    return paths


async def entity_summary(
    container: Container, *, tenant_id: str, label: str, limit: int = 50
) -> list[dict[str, Any]]:
    nodes = await container.graph.find_nodes(label, tenant_id=tenant_id, limit=limit)
    return [{"label": node.label, "key": node.key, "properties": node.properties} for node in nodes]


__all__ = ["GraphPath", "GraphResult", "entity_summary", "graph_lookup"]
