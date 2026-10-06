"""Knowledge graph construction (PRD s.34/s.35).

Entities: Supplier, Contract, Amendment, Product, Price, ComplianceCertificate,
Document, Category. Relationships: HAS_CONTRACT, AMENDS, SUPERSEDES, CONTAINS,
SUPPLIES, HAS_PRICE, APPLIES_TO, COMPLIES_WITH, BELONGS_TO, EVIDENCED_BY.

Temporal edges carry ``effective_date`` / ``expiry_date`` / ``version`` so the
graph can answer version-aware and multi-hop questions
(Supplier → Contract → Amendment → Product → Price).
"""

from __future__ import annotations

from typing import Any, Protocol

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
        ),
    )


def document_node(
    *, document_id: str, tenant_id: str, title: str, document_type: str, version: int
) -> GraphNode:
    return GraphNode(
        label=LABEL_DOCUMENT,
        key=document_id,
        properties=_props(tenant_id, name=title, document_type=document_type, version=version, document_id=document_id),
    )


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
            edges.append(
                edge("SUPERSEDED_BY", contract_n, replacement, tenant_id=contract.tenant_id)
            )
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
            document_id=document_id, tenant_id=tenant_id, title=title, document_type=document_type, version=version
        )
        nodes = [document]
        edges: list[GraphEdge] = []
        if supplier is not None:
            nodes.append(supplier_node(supplier))
            edges.append(
                edge("EVIDENCED_BY", supplier_node(supplier), document, tenant_id=tenant_id, document_id=document_id)
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

    async def remove_document_entities(self, document_id: str) -> int:
        return await self.graph.delete_subgraph(document_id)


async def multi_hop_supplier_price_chain(
    graph: GraphProvider, *, supplier_id: str, max_hops: int = 3
) -> list[GraphEdge]:
    """Supplier → Contract → Amendment/Price → Product traversal."""
    return await graph.traverse(
        LABEL_SUPPLIER, supplier_id, max_hops=max_hops, edge_types=("HAS_CONTRACT", "AMENDS", "CONTAINS", "HAS_PRICE", "APPLIES_TO")
    )


__all__ = [
    "GraphBuilder",
    "LABEL_AMENDMENT",
    "LABEL_CATEGORY",
    "LABEL_CLAUSE",
    "LABEL_COMPLIANCE",
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
