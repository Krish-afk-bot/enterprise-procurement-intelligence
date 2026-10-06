"""Attribution reconciliation.

Documents arrive in any order. An amendment or price sheet can be indexed before
the master agreement that names the supplier, and spreadsheets often name only
one of the two. This pass links what is now knowable:

  * a contract with no supplier inherits it from any document that cites the contract
  * documents and prices with no supplier inherit it from their contract
  * prices with no contract inherit it from their source document
  * prices that resolve a supplier/contract afterwards are re-linked in the graph

It runs after each document is indexed and can be re-run at any time; it never
overwrites an existing attribution.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ComplianceCertificate, Contract, Document, Price, Product, Supplier
from app.graph.builder import GraphBuilder
from app.observability.logging import get_logger
from app.providers.base import GraphProvider

logger = get_logger(__name__)


async def reconcile_attribution(
    session: AsyncSession, tenant_id: str, *, graph: GraphProvider | None = None
) -> dict[str, int]:
    counts = {
        "contracts_attributed": 0,
        "documents_attributed": 0,
        "prices_attributed": 0,
        "certificates_attributed": 0,
        "graph_relinked": 0,
    }

    # 1. Contracts that lack a supplier but whose documents know one.
    orphan_contracts = list(
        (
            await session.execute(
                select(Contract).where(Contract.tenant_id == tenant_id, Contract.supplier_id.is_(None))
            )
        ).scalars()
    )
    for contract in orphan_contracts:
        supplier_id = (
            await session.execute(
                select(Document.supplier_id)
                .where(
                    Document.tenant_id == tenant_id,
                    Document.contract_id == contract.id,
                    Document.supplier_id.is_not(None),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if supplier_id:
            contract.supplier_id = supplier_id
            counts["contracts_attributed"] += 1

    # 2. Documents that lack a supplier but whose contract knows one.
    contract_suppliers = dict(
        (
            await session.execute(
                select(Contract.id, Contract.supplier_id).where(
                    Contract.tenant_id == tenant_id, Contract.supplier_id.is_not(None)
                )
            )
        ).all()
    )
    if contract_suppliers:
        unset_documents = list(
            (
                await session.execute(
                    select(Document).where(
                        Document.tenant_id == tenant_id,
                        Document.supplier_id.is_(None),
                        Document.contract_id.is_not(None),
                    )
                )
            ).scalars()
        )
        for document in unset_documents:
            supplier_id = contract_suppliers.get(document.contract_id or "")
            if supplier_id:
                document.supplier_id = supplier_id
                counts["documents_attributed"] += 1

    # 3. Prices: inherit from contract, then from the source document.
    await session.flush()
    unset_prices = list(
        (
            await session.execute(
                select(Price).where(Price.tenant_id == tenant_id, Price.supplier_id.is_(None))
            )
        ).scalars()
    )
    for price in unset_prices:
        if price.contract_id and price.contract_id in contract_suppliers:
            price.supplier_id = contract_suppliers[price.contract_id]
        elif price.source_document_id:
            document = await session.get(Document, price.source_document_id)
            if document is not None and document.supplier_id:
                price.supplier_id = document.supplier_id
        if price.supplier_id:
            counts["prices_attributed"] += 1

    # 4. Compliance certificates follow the same rule.
    unset_certificates = list(
        (
            await session.execute(
                select(ComplianceCertificate).where(
                    ComplianceCertificate.tenant_id == tenant_id,
                    ComplianceCertificate.supplier_id.is_(None),
                )
            )
        ).scalars()
    )
    for certificate in unset_certificates:
        if certificate.source_document_id:
            document = await session.get(Document, certificate.source_document_id)
            if document is not None and document.supplier_id:
                certificate.supplier_id = document.supplier_id
                counts["certificates_attributed"] += 1

    await session.flush()

    if graph is not None and counts["prices_attributed"]:
        counts["graph_relinked"] = await _relink_graph(session, tenant_id, graph)

    if any(counts.values()):
        logger.info("attribution_reconciled", tenant_id=tenant_id, **counts)
    return counts


async def _relink_graph(session: AsyncSession, tenant_id: str, graph: GraphProvider) -> int:
    """Re-emit graph edges for newly attributed prices."""
    builder = GraphBuilder(graph)
    relinked = 0
    prices = list(
        (
            await session.execute(
                select(Price).where(Price.tenant_id == tenant_id, Price.supplier_id.is_not(None))
            )
        ).scalars()
    )
    supplier_cache: dict[str, Supplier] = {}
    product_cache: dict[str, Product] = {}
    contract_cache: dict[str, Contract] = {}
    for price in prices:
        supplier = supplier_cache.get(price.supplier_id or "")
        if supplier is None and price.supplier_id:
            fetched = await session.get(Supplier, price.supplier_id)
            if fetched is not None:
                supplier_cache[price.supplier_id] = fetched
                supplier = fetched
        product = None
        if price.product_id:
            product = product_cache.get(price.product_id)
            if product is None:
                product = await session.get(Product, price.product_id)
                if product is not None:
                    product_cache[price.product_id] = product
        contract = None
        if price.contract_id:
            contract = contract_cache.get(price.contract_id)
            if contract is None:
                contract = await session.get(Contract, price.contract_id)
                if contract is not None:
                    contract_cache[price.contract_id] = contract
        if supplier is None:
            continue
        await builder.upsert_price(price, supplier=supplier, product=product, contract=contract)
        relinked += 1
    return relinked


async def attribution_summary(session: AsyncSession, tenant_id: str) -> dict[str, int]:
    """Counts of unattributed rows, surfaced in the Admin UI as data-quality metrics."""
    return {
        "contracts_without_supplier": int(
            await session.scalar(
                select(func.count(Contract.id)).where(
                    Contract.tenant_id == tenant_id, Contract.supplier_id.is_(None)
                )
            )
            or 0
        ),
        "documents_without_supplier": int(
            await session.scalar(
                select(func.count(Document.id)).where(
                    Document.tenant_id == tenant_id, Document.supplier_id.is_(None)
                )
            )
            or 0
        ),
        "prices_without_supplier": int(
            await session.scalar(
                select(func.count(Price.id)).where(Price.tenant_id == tenant_id, Price.supplier_id.is_(None))
            )
            or 0
        ),
        "prices_without_product": int(
            await session.scalar(
                select(func.count(Price.id)).where(Price.tenant_id == tenant_id, Price.product_id.is_(None))
            )
            or 0
        ),
        "prices_without_effective_date": int(
            await session.scalar(
                select(func.count(Price.id)).where(
                    Price.tenant_id == tenant_id, Price.effective_date.is_(None)
                )
            )
            or 0
        ),
        "documents_needing_review": int(
            await session.scalar(
                select(func.count(Document.id)).where(
                    Document.tenant_id == tenant_id, Document.status == "needs_review"
                )
            )
            or 0
        ),
    }


__all__ = ["attribution_summary", "reconcile_attribution", "update", "Any"]
