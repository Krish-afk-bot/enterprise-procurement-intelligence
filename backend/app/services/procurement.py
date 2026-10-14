"""Structured procurement read services.

Every endpoint that returns procurement data goes through here, so tenant
scoping and access-level filtering are applied once, in the same place, and can
be audited. Nothing is computed speculatively: a field with no matching row is
returned as null with a note rather than being estimated.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.models import (
    Chunk,
    ComplianceCertificate,
    Contract,
    Document,
    DocumentPage,
    Price,
    ProcurementRecord,
    Product,
    Supplier,
    TableRecord,
)
from app.observability.logging import get_logger
from app.retrieval.analysis import current_price, dedupe_price_facts, fetch_price_facts
from app.retrieval.structured import comparison_matrix
from app.security.rbac import Principal

logger = get_logger(__name__)


def _readable_levels(principal: Principal) -> list[str]:
    return principal.readable_access_levels


async def _document_visibility(session: AsyncSession, principal: Principal) -> dict[str, str]:
    """document_id → access level, limited to what the caller may read."""
    rows = (
        await session.execute(
            select(Document.id, Document.access_level).where(
                Document.tenant_id == principal.tenant_id,
                Document.access_level.in_(_readable_levels(principal)),
            )
        )
    ).all()
    return {row[0]: row[1] for row in rows}


# --------------------------------------------------------------------- suppliers
async def list_suppliers(
    session: AsyncSession,
    principal: Principal,
    *,
    search: str | None = None,
    status: str | None = None,
    category: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    statement = select(Supplier).where(Supplier.tenant_id == principal.tenant_id)
    if search:
        pattern = f"%{search.lower()}%"
        statement = statement.where(
            or_(func.lower(Supplier.name).like(pattern), func.lower(Supplier.normalized_name).like(pattern))
        )
    if status:
        statement = statement.where(Supplier.status == status)
    if category:
        statement = statement.where(Supplier.category == category)
    total = await session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = list(
        (await session.execute(statement.order_by(Supplier.name).offset(offset).limit(limit))).scalars()
    )
    counts = await _supplier_counts(session, principal, [supplier.id for supplier in rows])
    items: list[dict[str, Any]] = []
    for supplier in rows:
        counters = counts.get(supplier.id, {})
        items.append(
            {
                **_supplier_payload(supplier),
                "contract_count": counters.get("contracts", 0),
                "document_count": counters.get("documents", 0),
                "price_count": counters.get("prices", 0),
            }
        )
    return items, int(total)


async def _supplier_counts(
    session: AsyncSession, principal: Principal, supplier_ids: list[str]
) -> dict[str, dict[str, int]]:
    if not supplier_ids:
        return {}
    counts: dict[str, dict[str, int]] = {supplier_id: {} for supplier_id in supplier_ids}
    contracts = (
        await session.execute(
            select(Contract.supplier_id, func.count(Contract.id))
            .where(Contract.tenant_id == principal.tenant_id, Contract.supplier_id.in_(supplier_ids))
            .group_by(Contract.supplier_id)
        )
    ).all()
    for supplier_id, count in contracts:
        counts.setdefault(supplier_id, {})["contracts"] = int(count)
    prices = (
        await session.execute(
            select(Price.supplier_id, func.count(Price.id))
            .where(Price.tenant_id == principal.tenant_id, Price.supplier_id.in_(supplier_ids))
            .group_by(Price.supplier_id)
        )
    ).all()
    for supplier_id, count in prices:
        counts.setdefault(supplier_id, {})["prices"] = int(count)
    documents = (
        await session.execute(
            select(Document.supplier_id, func.count(Document.id))
            .where(
                Document.tenant_id == principal.tenant_id,
                Document.supplier_id.in_(supplier_ids),
                Document.access_level.in_(_readable_levels(principal)),
            )
            .group_by(Document.supplier_id)
        )
    ).all()
    for supplier_id, count in documents:
        counts.setdefault(supplier_id, {})["documents"] = int(count)
    return counts


def _supplier_payload(supplier: Supplier) -> dict[str, Any]:
    return {
        "id": supplier.id,
        "name": supplier.name,
        "normalized_name": supplier.normalized_name or "",
        "category": supplier.category,
        "country": getattr(supplier, "country", None),
        "region": supplier.region,
        "status": supplier.status,
        "contact_email": getattr(supplier, "contact_email", None),
        "is_synthetic": supplier.is_synthetic,
        "source": supplier.source,
        "source_url": supplier.source_url,
        "license": supplier.license,
        "original_id": supplier.original_id,
        "retrieved_at": supplier.retrieved_at,
        "attributes": supplier.attributes or {},
    }


async def supplier_detail(session: AsyncSession, principal: Principal, supplier_id: str) -> dict[str, Any]:
    supplier = await session.get(Supplier, supplier_id)
    if supplier is None or supplier.tenant_id != principal.tenant_id:
        raise NotFoundError("Supplier not found.", details={"supplier_id": supplier_id})

    visible = await _document_visibility(session, principal)
    contracts = list(
        (
            await session.execute(
                select(Contract).where(
                    Contract.tenant_id == principal.tenant_id, Contract.supplier_id == supplier_id
                )
            )
        ).scalars()
    )
    prices = list(
        (
            await session.execute(
                select(Price).where(Price.tenant_id == principal.tenant_id, Price.supplier_id == supplier_id)
            )
        ).scalars()
    )
    certificates = list(
        (
            await session.execute(
                select(ComplianceCertificate).where(
                    ComplianceCertificate.tenant_id == principal.tenant_id,
                    ComplianceCertificate.supplier_id == supplier_id,
                )
            )
        ).scalars()
    )
    documents = list(
        (
            await session.execute(
                select(Document).where(
                    Document.tenant_id == principal.tenant_id,
                    Document.supplier_id == supplier_id,
                    Document.access_level.in_(_readable_levels(principal)),
                )
            )
        ).scalars()
    )
    product_ids = {price.product_id for price in prices if price.product_id}
    products: list[dict[str, Any]] = []
    if product_ids:
        for product in (await session.execute(select(Product).where(Product.id.in_(product_ids)))).scalars():
            products.append(
                {
                    "id": product.id,
                    "sku": product.sku,
                    "name": product.name,
                    "category": product.category,
                    "unit": product.unit,
                }
            )

    facts = dedupe_price_facts(
        await fetch_price_facts(session, principal, supplier_ids=[supplier_id], limit=500)
    )
    best = current_price(facts, supplier_id=supplier_id)
    timeline = sorted(
        (
            {
                "date": (fact.effective_date or fact.expiry_date).isoformat()
                if (fact.effective_date or fact.expiry_date) is not None
                else None,
                "kind": "price",
                "label": (
                    f"{fact.product_name or 'item'} at {fact.currency} {fact.unit_price:,.2f}"
                    + (f" ({fact.amendment_ref})" if fact.amendment_ref else "")
                ),
                "document_id": fact.document_id,
                "document_name": fact.document_name,
                "page": fact.page,
            }
            for fact in facts
            if fact.effective_date or fact.expiry_date
        ),
        key=lambda item: item["date"] or "",
    )

    return {
        **_supplier_payload(supplier),
        "contract_count": len(contracts),
        "document_count": len(documents),
        "price_count": len(prices),
        "contracts": [_contract_payload(contract, visible.get(contract.id)) for contract in contracts],
        "products": products,
        "prices": [_price_payload(price, supplier_name=supplier.name) for price in prices],
        "compliance": [compliance_payload(certificate) for certificate in certificates],
        "documents": [
            {
                "id": document.id,
                "title": document.title,
                "filename": document.filename,
                "document_type": document.document_type,
                "status": document.status,
                "access_level": document.access_level,
                "effective_date": document.effective_date.isoformat() if document.effective_date else None,
                "expiry_date": document.expiry_date.isoformat() if document.expiry_date else None,
            }
            for document in documents
        ],
        "timeline": timeline,
        "current_price": (
            {
                "unit_price": best.unit_price,
                "currency": best.currency,
                "product_name": best.product_name,
                "effective_date": best.effective_date.isoformat() if best.effective_date else None,
                "amendment_ref": best.amendment_ref,
                "document_id": best.document_id,
                "document_name": best.document_name,
                "page": best.page,
            }
            if best
            else None
        ),
    }


# --------------------------------------------------------------------- contracts
async def list_contracts(
    session: AsyncSession,
    principal: Principal,
    *,
    search: str | None = None,
    supplier_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    statement = (
        select(Contract, Supplier.name)
        .outerjoin(Supplier, Contract.supplier_id == Supplier.id)
        .where(Contract.tenant_id == principal.tenant_id)
    )
    if search:
        pattern = f"%{search.lower()}%"
        statement = statement.where(
            or_(
                func.lower(Contract.contract_number).like(pattern),
                func.lower(Contract.title).like(pattern),
            )
        )
    if supplier_id:
        statement = statement.where(Contract.supplier_id == supplier_id)
    if status:
        statement = statement.where(Contract.status == status)
    total = await session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = (
        await session.execute(statement.order_by(Contract.contract_number).offset(offset).limit(limit))
    ).all()
    visible = await _document_visibility(session, principal)
    items = [
        _contract_payload(contract, visible.get(contract.id), supplier_name=supplier_name)
        for contract, supplier_name in rows
    ]
    return items, int(total)


async def contract_detail(session: AsyncSession, principal: Principal, contract_id: str) -> dict[str, Any]:
    contract = await session.get(Contract, contract_id)
    if contract is None or contract.tenant_id != principal.tenant_id:
        raise NotFoundError("Contract not found.", details={"contract_id": contract_id})
    supplier = await session.get(Supplier, contract.supplier_id) if contract.supplier_id else None
    visible = await _document_visibility(session, principal)
    prices = list(
        (
            await session.execute(
                select(Price).where(Price.tenant_id == principal.tenant_id, Price.contract_id == contract_id)
            )
        ).scalars()
    )
    documents = list(
        (
            await session.execute(
                select(Document).where(
                    Document.tenant_id == principal.tenant_id,
                    Document.contract_id == contract_id,
                    Document.access_level.in_(_readable_levels(principal)),
                )
            )
        ).scalars()
    )
    versions = list(
        (
            await session.execute(
                select(Contract).where(
                    Contract.tenant_id == principal.tenant_id,
                    Contract.contract_number == contract.contract_number,
                )
            )
        ).scalars()
    )
    clauses = (
        await session.execute(
            select(Chunk)
            .where(
                Chunk.tenant_id == principal.tenant_id,
                Chunk.contract_id == contract_id,
                Chunk.clause.is_not(None),
            )
            .order_by(Chunk.page_number, Chunk.chunk_index)
            .limit(200)
        )
    ).scalars()
    clause_rows = [
        {
            "chunk_id": chunk.id,
            "page": chunk.page_number,
            "section": chunk.section,
            "subsection": chunk.subsection,
            "clause": chunk.clause,
            "content": chunk.content[:1200],
            "content_type": chunk.content_type,
            "document_id": chunk.document_id,
        }
        for chunk in clauses
    ]
    certificates = list(
        (
            await session.execute(
                select(ComplianceCertificate).where(
                    ComplianceCertificate.tenant_id == principal.tenant_id,
                    ComplianceCertificate.supplier_id == contract.supplier_id,
                )
            )
        ).scalars()
    )
    return {
        **_contract_payload(contract, supplier_name=supplier.name if supplier else None),
        "prices": [
            _price_payload(price, supplier_name=supplier.name if supplier else None) for price in prices
        ],
        "documents": [
            {
                "id": document.id,
                "title": document.title,
                "filename": document.filename,
                "document_type": document.document_type,
                "version": document.version,
                "revision_label": document.revision_label,
                "status": document.status,
                "access_level": document.access_level,
                "effective_date": document.effective_date.isoformat() if document.effective_date else None,
                "expiry_date": document.expiry_date.isoformat() if document.expiry_date else None,
            }
            for document in documents
        ],
        "versions": [
            {
                "id": version.id,
                "contract_number": version.contract_number,
                "version": version.version,
                "title": version.title,
                "effective_date": version.effective_date,
                "expiry_date": version.expiry_date,
                "status": version.status,
                "superseded_by_id": version.superseded_by_id,
                "parent_contract_id": version.parent_contract_id,
                "relation": "current" if version.id == contract.id else "version",
            }
            for version in versions
        ],
        "clauses": clause_rows,
        "compliance": [compliance_payload(certificate) for certificate in certificates],
        "visible_document_ids": sorted(visible),
    }


def _contract_payload(
    contract: Contract, access_level: str | None = None, *, supplier_name: str | None = None
) -> dict[str, Any]:
    today = date.today()
    return {
        "id": contract.id,
        "supplier_id": contract.supplier_id,
        "supplier_name": supplier_name,
        "contract_number": contract.contract_number,
        "title": contract.title or "",
        "contract_type": contract.contract_type,
        "category": contract.category,
        "currency": contract.currency,
        "total_value": contract.total_value,
        "effective_date": contract.effective_date,
        "expiry_date": contract.expiry_date,
        "status": contract.status,
        "version": contract.version,
        "superseded_by_id": contract.superseded_by_id,
        "parent_contract_id": contract.parent_contract_id,
        "is_synthetic": contract.is_synthetic,
        "source": contract.source,
        "source_url": contract.source_url,
        "license": contract.license,
        "original_id": contract.original_id,
        "retrieved_at": contract.retrieved_at,
        "metadata_json": contract.metadata_json or {},
        "is_expired": bool(contract.expiry_date and contract.expiry_date < today),
        "access_level": access_level,
    }


# ------------------------------------------------------------------------ prices
async def list_prices(
    session: AsyncSession,
    principal: Principal,
    *,
    supplier_id: str | None = None,
    product_id: str | None = None,
    contract_id: str | None = None,
    as_of: date | None = None,
    current_only: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    statement = (
        select(Price, Supplier.name, Product.name)
        .outerjoin(Supplier, Price.supplier_id == Supplier.id)
        .outerjoin(Product, Price.product_id == Product.id)
        .where(Price.tenant_id == principal.tenant_id)
    )
    if supplier_id:
        statement = statement.where(Price.supplier_id == supplier_id)
    if product_id:
        statement = statement.where(Price.product_id == product_id)
    if contract_id:
        statement = statement.where(Price.contract_id == contract_id)
    if as_of is not None:
        statement = statement.where(
            (Price.effective_date.is_(None)) | (Price.effective_date <= as_of),
            (Price.expiry_date.is_(None)) | (Price.expiry_date >= as_of),
        )
    if current_only:
        statement = statement.where(Price.is_current.is_(True))
    total = await session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = (
        await session.execute(
            statement.order_by(Price.effective_date.desc().nullslast()).offset(offset).limit(limit)
        )
    ).all()
    items = [
        {
            **_price_payload(price, supplier_name=supplier_name, product_name=product_name),
            "price_type": price.price_type if hasattr(price, "price_type") else None,
        }
        for price, supplier_name, product_name in rows
    ]
    return items, int(total)


def _price_payload(
    price: Price, *, supplier_name: str | None = None, product_name: str | None = None
) -> dict[str, Any]:
    return {
        "id": price.id,
        "supplier_id": price.supplier_id,
        "supplier_name": supplier_name,
        "contract_id": price.contract_id,
        "product_id": price.product_id,
        "product_name": product_name,
        "unit_price": price.unit_price,
        "currency": price.currency,
        "minimum_quantity": price.minimum_quantity,
        "discount_percent": price.discount_percent,
        "payment_terms": price.payment_terms,
        "delivery_terms": price.delivery_terms,
        "quantity": price.quantity,
        "line_total": price.line_total,
        "effective_date": price.effective_date,
        "expiry_date": price.expiry_date,
        "is_current": price.is_current,
        "amendment_ref": price.amendment_ref,
        "source_document_id": price.source_document_id,
        "source_page": price.source_page,
        "is_synthetic": price.is_synthetic,
    }


def compliance_payload(certificate: ComplianceCertificate) -> dict[str, Any]:
    return {
        "id": certificate.id,
        "supplier_id": certificate.supplier_id,
        "certificate_type": certificate.certificate_type,
        "certificate_number": certificate.certificate_number,
        "issued_date": certificate.issued_date,
        "expiry_date": certificate.expiry_date,
        "status": certificate.status,
        "scope": certificate.scope,
        "source_document_id": certificate.source_document_id,
        "source_page": certificate.source_page,
        "is_synthetic": certificate.is_synthetic,
    }


# -------------------------------------------------------------------- products
async def list_products(
    session: AsyncSession,
    principal: Principal,
    *,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    statement = select(Product).where(Product.tenant_id == principal.tenant_id)
    if search:
        pattern = f"%{search.lower()}%"
        statement = statement.where(
            or_(func.lower(Product.name).like(pattern), func.lower(Product.sku).like(pattern))
        )
    total = await session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    products = list(
        (await session.execute(statement.order_by(Product.name).offset(offset).limit(limit))).scalars()
    )
    price_counts: dict[str | None, int] = dict(
        (
            await session.execute(
                select(Price.product_id, func.count(Price.id))
                .where(Price.tenant_id == principal.tenant_id)
                .group_by(Price.product_id)
            )
        ).all()
    )
    items = [
        {
            "id": product.id,
            "sku": product.sku,
            "name": product.name,
            "category": product.category,
            "unit": product.unit,
            "is_synthetic": product.is_synthetic,
            "attributes": product.attributes or {},
            "price_count": int(price_counts.get(product.id, 0)),
        }
        for product in products
    ]
    return items, int(total)


# ------------------------------------------------------------------ comparison
async def compare(
    session: AsyncSession,
    principal: Principal,
    *,
    supplier_ids: list[str],
    supplier_names: list[str] | None = None,
    product_ids: list[str] | None = None,
    product_query: str | None = None,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Supplier comparison built from stored rows; unresolved names are reported."""
    resolved = list(supplier_ids)
    unresolved: list[str] = []
    for name in supplier_names or []:
        match = (
            await session.execute(
                select(Supplier).where(
                    Supplier.tenant_id == principal.tenant_id,
                    func.lower(Supplier.name) == name.lower(),
                )
            )
        ).scalar_one_or_none()
        if match is None:
            match = (
                (
                    await session.execute(
                        select(Supplier).where(
                            Supplier.tenant_id == principal.tenant_id,
                            func.lower(Supplier.name).like(f"%{name.lower()}%"),
                        )
                    )
                )
                .scalars()
                .first()
            )
        if match is None:
            unresolved.append(f"No supplier record matches '{name}'.")
            continue
        if match.id not in resolved:
            resolved.append(match.id)

    products = list(product_ids or [])
    if product_query:
        for product in (
            await session.execute(
                select(Product).where(
                    Product.tenant_id == principal.tenant_id,
                    func.lower(Product.name).like(f"%{product_query.lower()}%"),
                )
            )
        ).scalars():
            if product.id not in products:
                products.append(product.id)

    matrix = await comparison_matrix(
        session, principal, supplier_ids=resolved, product_ids=products or None, as_of=as_of
    )
    matrix["unresolved"] = [*unresolved, *(matrix.get("unresolved") or [])]
    matrix["product"] = {"id": products[0], "name": product_query} if products and product_query else None
    matrix["generated_at"] = datetime.now(UTC)
    return matrix


# ----------------------------------------------------------------------- stats
async def corpus_stats(session: AsyncSession, principal: Principal) -> dict[str, Any]:
    tenant_id = principal.tenant_id
    visible_levels = _readable_levels(principal)

    async def count(model: Any, *conditions: Any) -> int:
        return int(
            await session.scalar(
                select(func.count(model.id)).where(model.tenant_id == tenant_id, *conditions)
            )
            or 0
        )

    documents = await count(Document, Document.access_level.in_(visible_levels))
    pages = int(
        await session.scalar(select(func.count(DocumentPage.id)).where(DocumentPage.tenant_id == tenant_id))
        or 0
    )
    tables = int(
        await session.scalar(select(func.count(TableRecord.id)).where(TableRecord.tenant_id == tenant_id))
        or 0
    )
    chunks = await count(Chunk)
    embedded = await count(Chunk, Chunk.embedding_indexed.is_(True))
    contracts = await count(Contract)
    suppliers = await count(Supplier)
    products = await count(Product)
    prices = await count(Price)
    records = await count(ProcurementRecord)
    certificates = await count(ComplianceCertificate)
    return {
        "documents": documents,
        "pages": pages,
        "tables": tables,
        "chunks": chunks,
        "chunks_embedded": embedded,
        "suppliers": suppliers,
        "contracts": contracts,
        "products": products,
        "prices": prices,
        "procurement_records": records,
        "compliance_certificates": certificates,
        "visible_access_levels": visible_levels,
        "notes": [
            "Counts are read from the database for the caller's tenant only.",
            "Document count excludes documents above the caller's access ceiling.",
        ],
    }
