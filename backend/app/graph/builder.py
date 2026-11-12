"""Knowledge graph construction (PRD s.34/s.35).

Entities: Supplier, Contract, Amendment, Product, Price, ComplianceCertificate,
Document, Category. Relationships: HAS_CONTRACT, AMENDS, SUPERSEDES, CONTAINS,
SUPPLIES, HAS_PRICE, APPLIES_TO, COMPLIES_WITH, BELONGS_TO, EVIDENCED_BY.

Temporal edges carry ``effective_date`` / ``expiry_date`` / ``version`` so the
graph can answer version-aware and multi-hop questions
(Supplier → Contract → Amendment → Product → Price).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from app.db.models import ComplianceCertificate, Contract, Price, Product, Supplier
from app.observability.logging import get_logger
from app.providers.base import GraphProvider
from app.providers.types import GraphEdge, GraphNode

logger = get_logger(__name__)

LABEL_SUPPLIER = "Supplier"
LABEL_CONTRACT = "Contract"
LABEL_AMENDMENT = "Amendment"
LABEL_PRODUCT = "Product"
LABEL_PRICE = "Price"
LABEL_COMPLIANCE = "ComplianceCertificate"
LABEL_DOCUMENT = "Document"
LABEL_CATEGORY = "Category"
LABEL_CLAUSE = "Clause"
LABEL_OBLIGATION = "Obligation"

#: Modal verbs and undertakings that mark a contractual duty. This is a lexical
#: signal, not legal interpretation: the node records the sentence so a reader
#: can judge it, and the property says how it was found.
OBLIGATION_RE = re.compile(
    r"\b(?:shall|must|will|is required to|are required to|agrees? to|undertakes? to|is obliged to)\b",
    re.IGNORECASE,
)
_SENTENCE_RE = re.compile(r"(?<=[.;:])\s+")

#: Clause text kept on the node. Enough to recognise the clause in a citation,
#: bounded so a whole section cannot be duplicated into the graph.
CLAUSE_TEXT_LIMIT = 800
OBLIGATION_TEXT_LIMIT = 600


def _props(tenant_id: str, **values: Any) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None} | {"tenant_id": tenant_id}


def supplier_node(supplier: Supplier) -> GraphNode:
    return GraphNode(
        label=LABEL_SUPPLIER,
        key=supplier.id,
        properties=_props(
            supplier.tenant_id,
            name=supplier.name,
            category=supplier.category,
            region=supplier.region,
            country=supplier.country,
            status=supplier.status,
            is_synthetic=supplier.is_synthetic,
        ),
    )


def contract_node(contract: Contract) -> GraphNode:
    return GraphNode(
        label=LABEL_CONTRACT,
        key=contract.id,
        properties=_props(
            contract.tenant_id,
            number=contract.contract_number,
            title=contract.title,
            status=contract.status,
            version=contract.version,
            effective_date=contract.effective_date.isoformat() if contract.effective_date else None,
            expiry_date=contract.expiry_date.isoformat() if contract.expiry_date else None,
            currency=contract.currency,
            total_value=contract.total_value,
        ),
    )


def product_node(product: Product) -> GraphNode:
    return GraphNode(
        label=LABEL_PRODUCT,
        key=product.id,
        properties=_props(
            product.tenant_id,
            name=product.name,
            sku=product.sku,
            category=product.category,
            unit=product.unit,
        ),
    )


def price_node(price: Price) -> GraphNode:
    return GraphNode(
        label=LABEL_PRICE,
        key=price.id,
        properties=_props(
            price.tenant_id,
            unit_price=price.unit_price,
            currency=price.currency,
            minimum_quantity=price.minimum_quantity,
            discount_percent=price.discount_percent,
            effective_date=price.effective_date.isoformat() if price.effective_date else None,
            expiry_date=price.expiry_date.isoformat() if price.expiry_date else None,
            is_current=price.is_current,
            amendment_ref=price.amendment_ref,
            source_document_id=price.source_document_id,
            document_id=price.source_document_id,
            source_page=price.source_page,
        ),
    )


def compliance_node(certificate: ComplianceCertificate) -> GraphNode:
    return GraphNode(
        label=LABEL_COMPLIANCE,
        key=certificate.id,
        properties=_props(
            certificate.tenant_id,
            certificate_type=certificate.certificate_type,
            certificate_number=certificate.certificate_number,
            status=certificate.status,
            issued_date=certificate.issued_date.isoformat() if certificate.issued_date else None,
            expiry_date=certificate.expiry_date.isoformat() if certificate.expiry_date else None,
            source_document_id=certificate.source_document_id,
            document_id=certificate.source_document_id,
        ),
    )


def document_node(
    *, document_id: str, tenant_id: str, title: str, document_type: str, version: int
) -> GraphNode:
    return GraphNode(
        label=LABEL_DOCUMENT,
        key=document_id,
        properties=_props(
            tenant_id, name=title, document_type=document_type, version=version, document_id=document_id
        ),
    )


def clause_node(
    *,
    tenant_id: str,
    document_id: str,
    clause: str,
    text: str,
    page: int | None,
    section: str | None = None,
    effective_date: Any = None,
    expiry_date: Any = None,
) -> GraphNode:
    return GraphNode(
        label=LABEL_CLAUSE,
        key=f"{document_id}:{clause}",
        properties=_props(
            tenant_id,
            name=clause,
            clause=clause,
            section=section,
            text=text[:CLAUSE_TEXT_LIMIT],
            source_page=page,
            document_id=document_id,
            effective_date=effective_date,
            expiry_date=expiry_date,
        ),
    )


def obligation_node(
    *,
    tenant_id: str,
    document_id: str,
    clause: str,
    text: str,
    page: int | None,
) -> GraphNode:
    return GraphNode(
        label=LABEL_OBLIGATION,
        key=f"{document_id}:{clause}:obligation",
        properties=_props(
            tenant_id,
            name=f"Obligation in {clause}",
            clause=clause,
            text=text[:OBLIGATION_TEXT_LIMIT],
            source_page=page,
            document_id=document_id,
            # How the node was found, so a reader is never told a lawyer decided it.
            detection="modal_verb",
        ),
    )


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else None


def _obligation_text(text: str) -> str | None:
    """The sentences of a clause that impose a duty, or None if none do."""
    sentences = [part.strip() for part in _SENTENCE_RE.split(text) if part.strip()]
    duties = [sentence for sentence in sentences if OBLIGATION_RE.search(sentence)]
    if not duties:
        return None
    return " ".join(duties)


def edge(
    edge_type: str,
    start: GraphNode,
    end: GraphNode,
    *,
    tenant_id: str,
    document_id: str | None = None,
    **properties: Any,
) -> GraphEdge:
    return GraphEdge(
        type=edge_type,
        start_label=start.label,
        start_key=start.key,
        end_label=end.label,
        end_key=end.key,
        properties=_props(tenant_id, document_id=document_id, **properties),
    )


class GraphBuilder:
    """Writes the procurement graph through the GraphProvider interface."""

    def __init__(self, graph: GraphProvider) -> None:
        self.graph = graph

    async def upsert_supplier(self, supplier: Supplier) -> None:
        await self.graph.upsert_nodes([supplier_node(supplier)])
        if supplier.category:
            category = GraphNode(
                label=LABEL_CATEGORY,
                key=f"{supplier.tenant_id}:{supplier.category}",
                properties=_props(supplier.tenant_id, name=supplier.category),
            )
            await self.graph.upsert_nodes([category])
            await self.graph.upsert_edges(
                [
                    edge(
                        "BELONGS_TO",
                        supplier_node(supplier),
                        category,
                        tenant_id=supplier.tenant_id,
                    )
                ]
            )

    async def upsert_contract(self, contract: Contract, supplier: Supplier | None) -> None:
        nodes = [contract_node(contract)]
        if supplier is not None:
            nodes.append(supplier_node(supplier))
        await self.graph.upsert_nodes(nodes)
        edges: list[GraphEdge] = []
        contract_n = contract_node(contract)
        if supplier is not None:
            edges.append(
                edge(
                    "HAS_CONTRACT",
                    supplier_node(supplier),
                    contract_n,
                    tenant_id=contract.tenant_id,
                    effective_date=contract.effective_date.isoformat() if contract.effective_date else None,
                )
            )
        if contract.parent_contract_id:
            parent = GraphNode(
                label=LABEL_CONTRACT,
                key=contract.parent_contract_id,
                properties=_props(contract.tenant_id),
            )
            edges.append(
                edge(
                    "AMENDS",
                    contract_n,
                    parent,
                    tenant_id=contract.tenant_id,
                    amendment_date=contract.effective_date.isoformat() if contract.effective_date else None,
                    version=contract.version,
                )
            )
        if contract.superseded_by_id:
            replacement = GraphNode(
                label=LABEL_CONTRACT,
                key=contract.superseded_by_id,
                properties=_props(contract.tenant_id),
            )
            edges.append(edge("SUPERSEDED_BY", contract_n, replacement, tenant_id=contract.tenant_id))
        if edges:
            await self.graph.upsert_edges(edges)

    async def upsert_product(self, product: Product) -> None:
        await self.graph.upsert_nodes([product_node(product)])
        if product.category:
            category = GraphNode(
                label=LABEL_CATEGORY,
                key=f"{product.tenant_id}:{product.category}",
                properties=_props(product.tenant_id, name=product.category),
            )
            await self.graph.upsert_nodes([category])
            await self.graph.upsert_edges(
                [
                    edge(
                        "BELONGS_TO",
                        product_node(product),
                        category,
                        tenant_id=product.tenant_id,
                    )
                ]
            )

    async def upsert_price(
        self, price: Price, *, supplier: Supplier | None, product: Product | None, contract: Contract | None
    ) -> None:
        nodes = [price_node(price)]
        edges: list[GraphEdge] = []
        if supplier is not None:
            nodes.append(supplier_node(supplier))
            edges.append(
                edge(
                    "HAS_PRICE",
                    supplier_node(supplier),
                    price_node(price),
                    tenant_id=price.tenant_id,
                    document_id=price.source_document_id,
                    effective_date=price.effective_date.isoformat() if price.effective_date else None,
                    expiry_date=price.expiry_date.isoformat() if price.expiry_date else None,
                    is_current=price.is_current,
                )
            )
        if product is not None:
            nodes.append(product_node(product))
            edges.append(
                edge(
                    "APPLIES_TO",
                    price_node(price),
                    product_node(product),
                    tenant_id=price.tenant_id,
                    document_id=price.source_document_id,
                )
            )
        if contract is not None:
            nodes.append(contract_node(contract))
            edges.append(
                edge(
                    "CONTAINS",
                    contract_node(contract),
                    price_node(price),
                    tenant_id=price.tenant_id,
                    document_id=price.source_document_id,
                )
            )
        await self.graph.upsert_nodes(nodes)
        if edges:
            await self.graph.upsert_edges(edges)

    async def upsert_compliance(self, certificate: ComplianceCertificate, supplier: Supplier | None) -> None:
        nodes = [compliance_node(certificate)]
        if supplier is not None:
            nodes.append(supplier_node(supplier))
        await self.graph.upsert_nodes(nodes)
        if supplier is not None:
            await self.graph.upsert_edges(
                [
                    edge(
                        "COMPLIES_WITH",
                        supplier_node(supplier),
                        compliance_node(certificate),
                        tenant_id=certificate.tenant_id,
                        document_id=certificate.source_document_id,
                        expiry_date=certificate.expiry_date.isoformat() if certificate.expiry_date else None,
                    )
                ]
            )

    async def link_document(
        self,
        *,
        document_id: str,
        tenant_id: str,
        title: str,
        document_type: str,
        version: int,
        supplier: Supplier | None,
        contract: Contract | None,
    ) -> None:
        document = document_node(
            document_id=document_id,
            tenant_id=tenant_id,
            title=title,
            document_type=document_type,
            version=version,
        )
        nodes = [document]
        edges: list[GraphEdge] = []
        if supplier is not None:
            nodes.append(supplier_node(supplier))
            edges.append(
                edge(
                    "EVIDENCED_BY",
                    supplier_node(supplier),
                    document,
                    tenant_id=tenant_id,
                    document_id=document_id,
                )
            )
        if contract is not None:
            nodes.append(contract_node(contract))
            edges.append(
                edge(
                    "HAS_DOCUMENT",
                    contract_node(contract),
                    document,
                    tenant_id=tenant_id,
                    document_id=document_id,
                    document_type=document_type,
                )
            )
        await self.graph.upsert_nodes(nodes)
        if edges:
            await self.graph.upsert_edges(edges)

    async def link_clauses(
        self,
        *,
        tenant_id: str,
        document_id: str,
        title: str,
        document_type: str,
        version: int,
        chunks: Iterable[Any],
    ) -> int:
        """Write Clause and Obligation nodes for a document's clause chunks.

        Chunks are grouped by their clause number, so a clause split across a page
        boundary becomes one node rather than two. A clause with no modal verb
        produces no Obligation node: the absence of a duty is meaningful, and
        inventing one would be worse than leaving it out.
        """
        grouped: dict[str, dict[str, Any]] = {}
        for chunk in chunks:
            clause = (getattr(chunk, "clause", None) or "").strip()
            if not clause:
                continue
            entry = grouped.setdefault(
                clause,
                {"texts": [], "page": None, "section": None, "effective": None, "expiry": None},
            )
            content = (getattr(chunk, "content", "") or "").strip()
            if content:
                entry["texts"].append(content)
            if entry["page"] is None:
                entry["page"] = getattr(chunk, "page_number", None)
            entry["section"] = entry["section"] or getattr(chunk, "section", None)
            entry["effective"] = entry["effective"] or _iso(getattr(chunk, "effective_date", None))
            entry["expiry"] = entry["expiry"] or _iso(getattr(chunk, "expiry_date", None))

        if not grouped:
            return 0

        document = document_node(
            document_id=document_id,
            tenant_id=tenant_id,
            title=title,
            document_type=document_type,
            version=version,
        )
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        for clause, entry in grouped.items():
            text = " ".join(entry["texts"])
            clause_n = clause_node(
                tenant_id=tenant_id,
                document_id=document_id,
                clause=clause,
                text=text,
                page=entry["page"],
                section=entry["section"],
                effective_date=entry["effective"],
                expiry_date=entry["expiry"],
            )
            nodes.append(clause_n)
            edges.append(
                edge(
                    "CONTAINS",
                    document,
                    clause_n,
                    tenant_id=tenant_id,
                    document_id=document_id,
                    source_page=entry["page"],
                    effective_date=entry["effective"],
                    expiry_date=entry["expiry"],
                )
            )
            duty = _obligation_text(text)
            if duty:
                obligation_n = obligation_node(
                    tenant_id=tenant_id,
                    document_id=document_id,
                    clause=clause,
                    text=duty,
                    page=entry["page"],
                )
                nodes.append(obligation_n)
                edges.append(
                    edge(
                        "IMPOSES",
                        clause_n,
                        obligation_n,
                        tenant_id=tenant_id,
                        document_id=document_id,
                        source_page=entry["page"],
                    )
                )
                # Provenance in the same direction as other evidence edges.
                edges.append(
                    edge(
                        "EVIDENCED_BY",
                        obligation_n,
                        document,
                        tenant_id=tenant_id,
                        document_id=document_id,
                        source_page=entry["page"],
                    )
                )

        await self.graph.upsert_nodes(nodes)
        await self.graph.upsert_edges(edges)
        return len(grouped)

    async def remove_document_entities(self, document_id: str) -> int:
        return await self.graph.delete_subgraph(document_id)


async def multi_hop_supplier_price_chain(
    graph: GraphProvider, *, supplier_id: str, max_hops: int = 3
) -> list[GraphEdge]:
    """Supplier → Contract → Amendment/Price → Product traversal."""
    return await graph.traverse(
        LABEL_SUPPLIER,
        supplier_id,
        max_hops=max_hops,
        edge_types=("HAS_CONTRACT", "AMENDS", "CONTAINS", "HAS_PRICE", "APPLIES_TO"),
    )


__all__ = [
    "GraphBuilder",
    "LABEL_AMENDMENT",
    "LABEL_CATEGORY",
    "LABEL_CLAUSE",
    "LABEL_COMPLIANCE",
    "LABEL_OBLIGATION",
    "LABEL_CONTRACT",
    "LABEL_DOCUMENT",
    "LABEL_PRICE",
    "LABEL_PRODUCT",
    "LABEL_SUPPLIER",
    "compliance_node",
    "contract_node",
    "document_node",
    "edge",
    "multi_hop_supplier_price_chain",
    "price_node",
    "product_node",
    "supplier_node",
]
