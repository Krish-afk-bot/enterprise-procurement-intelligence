"""Temporal reasoning and conflict detection (PRD s.35-37).

Conflicts are detected from the *structured* price rows (which carry effective
dates, amendment references, source documents and pages) rather than by asking a
model to spot them in prose. That keeps the explanation and its citations exact:

    Contract NS-2024-001 original: USD 920.00 (effective 2024-01-01)
    Amendment 2: USD 874.00 (effective 2026-01-01, page 1)
    → the later effective value governs from 2026-01-01; both are cited.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Contract, Document, Price, Product, Supplier
from app.observability.logging import get_logger
from app.security.rbac import Principal

logger = get_logger(__name__)


@dataclass(slots=True)
class PriceFact:
    price_id: str
    supplier_id: str | None
    supplier_name: str | None
    contract_id: str | None
    contract_number: str | None
    product_id: str | None
    product_name: str | None
    unit_price: float
    currency: str
    minimum_quantity: int | None
    discount_percent: float | None
    payment_terms: str | None
    delivery_terms: str | None
    effective_date: date | None
    expiry_date: date | None
    amendment_ref: str | None
    document_id: str | None
    document_name: str | None
    page: int | None
    is_synthetic: bool
    quantity: int | None = None
    line_total: float | None = None
    #: Other documents that record the same agreed value (provenance kept).
    also_in: list[dict[str, Any]] = field(default_factory=list)

    @property
    def is_expired(self) -> bool:
        return bool(self.expiry_date and self.expiry_date < date.today())

    def as_dict(self) -> dict[str, Any]:
        return {
            "price_id": self.price_id,
            "supplier_id": self.supplier_id,
            "supplier_name": self.supplier_name,
            "contract_id": self.contract_id,
            "contract_number": self.contract_number,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "unit_price": self.unit_price,
            "currency": self.currency,
            "minimum_quantity": self.minimum_quantity,
            "discount_percent": self.discount_percent,
            "payment_terms": self.payment_terms,
            "delivery_terms": self.delivery_terms,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "amendment_ref": self.amendment_ref,
            "document_id": self.document_id,
            "document_name": self.document_name,
            "page": self.page,
            "is_synthetic": self.is_synthetic,
            "expired": self.is_expired,
            "also_in": self.also_in,
        }


@dataclass(slots=True)
class Conflict:
    kind: str
    description: str
    values: list[dict[str, Any]] = field(default_factory=list)
    resolution: str = ""
    preferred: dict[str, Any] | None = None
    citations: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "description": self.description,
            "values": self.values,
            "resolution": self.resolution,
            "preferred": self.preferred,
            "citations": self.citations,
        }


async def fetch_price_facts(
    session: AsyncSession,
    principal: Principal,
    *,
    supplier_ids: list[str] | None = None,
    product_ids: list[str] | None = None,
    contract_ids: list[str] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 500,
) -> list[PriceFact]:
    statement = (
        select(Price, Supplier.name, Contract.contract_number, Product.name, Document.title, Document.filename)
        .outerjoin(Supplier, Price.supplier_id == Supplier.id)
        .outerjoin(Contract, Price.contract_id == Contract.id)
        .outerjoin(Product, Price.product_id == Product.id)
        .outerjoin(Document, Price.source_document_id == Document.id)
        .where(Price.tenant_id == principal.tenant_id)
        .limit(limit)
    )
    if supplier_ids:
        statement = statement.where(Price.supplier_id.in_(supplier_ids))
    if product_ids:
        statement = statement.where(Price.product_id.in_(product_ids))
    if contract_ids:
        statement = statement.where(Price.contract_id.in_(contract_ids))
    if date_from is not None:
        statement = statement.where((Price.effective_date.is_(None)) | (Price.effective_date >= date_from))
    if date_to is not None:
        statement = statement.where((Price.effective_date.is_(None)) | (Price.effective_date <= date_to))

    facts: list[PriceFact] = []
    for price, supplier_name, contract_number, product_name, doc_title, doc_filename in (
        await session.execute(statement)
    ).all():
        facts.append(
            PriceFact(
                price_id=price.id,
                supplier_id=price.supplier_id,
                supplier_name=supplier_name,
                contract_id=price.contract_id,
                contract_number=contract_number,
                product_id=price.product_id,
                product_name=product_name,
                unit_price=price.unit_price,
                currency=price.currency,
                minimum_quantity=price.minimum_quantity,
                discount_percent=price.discount_percent,
                payment_terms=price.payment_terms,
                delivery_terms=price.delivery_terms,
                effective_date=price.effective_date,
                expiry_date=price.expiry_date,
                amendment_ref=price.amendment_ref,
                document_id=price.source_document_id,
                document_name=doc_title or doc_filename,
                page=price.source_page,
                is_synthetic=price.is_synthetic,
                quantity=price.quantity,
                line_total=price.line_total,
            )
        )
    return facts


def dedupe_price_facts(facts: list[PriceFact]) -> list[PriceFact]:
    """Collapse the same price recorded in several sources into one fact.

    A price repeated in the master agreement and in a price list is *one* agreed
    value with two sources, not two values. The surviving fact keeps the first
    citation; the duplicate sources are appended to ``as_dict()['also_in']`` so
    provenance is not lost.
    """
    unique: dict[tuple, PriceFact] = {}
    for fact in facts:
        key = (
            fact.supplier_id,
            fact.product_id,
            round(fact.unit_price, 4),
            fact.currency,
            fact.effective_date,
            fact.expiry_date,
            fact.amendment_ref or "",
        )
        existing = unique.get(key)
        if existing is None:
            unique[key] = fact
            continue
        source = {"document_id": fact.document_id, "document_name": fact.document_name, "page": fact.page}
        if source not in existing.also_in and fact.document_id != existing.document_id:
            existing.also_in.append(source)
    return list(unique.values())


def detect_price_conflicts(facts: list[PriceFact], *, as_of: date | None = None) -> list[Conflict]:
    """Group price facts per (supplier, product) and explain disagreements.

    Rows that could not be attributed to a supplier are excluded: they cannot be
    shown to disagree with anything until attribution is resolved, and reporting
    them as a conflict would be misleading.
    """
    as_of = as_of or date.today()
    grouped: dict[tuple[str | None, str | None], list[PriceFact]] = {}
    for fact in dedupe_price_facts(facts):
        if fact.supplier_id is None:
            continue
        grouped.setdefault((fact.supplier_id, fact.product_id), []).append(fact)

    conflicts: list[Conflict] = []
    for (supplier_id, product_id), group in grouped.items():
        distinct_prices = {round(fact.unit_price, 4) for fact in group}
        if len(distinct_prices) < 2:
            continue
        dated = sorted(
            group,
            key=lambda fact: (fact.effective_date or date.min, fact.amendment_ref or ""),
        )
        product_name = next((fact.product_name for fact in dated if fact.product_name), "the product")
        supplier_name = next((fact.supplier_name for fact in dated if fact.supplier_name), "the supplier")
        applicable = [fact for fact in dated if (fact.effective_date or date.min) <= as_of]
        preferred = applicable[-1] if applicable else dated[0]
        later = [fact for fact in dated if fact.amendment_ref]
        # Report each distinct agreed value once, naming the amendment that set
        # it when there is one: the same value recorded in a price list and in
        # the amendment that introduced it is one agreed value, not two.
        by_value: dict[float, list[PriceFact]] = {}
        for fact in dated:
            by_value.setdefault(round(fact.unit_price, 4), []).append(fact)
        ordered_values = sorted(by_value.items(), key=lambda item: item[1][0].effective_date or date.min)
        if later:
            description = (
                f"{supplier_name} has {len(ordered_values)} different agreed unit prices for "
                f"{product_name}: "
                + "; ".join(
                    f"{named.currency} {named.unit_price:,.2f}"
                    + (f" from {named.effective_date.isoformat()}" if named.effective_date else " (undated)")
                    + (f" per {named.amendment_ref}" if named.amendment_ref else "")
                    for _, facts_for_value in ordered_values
                    for named in [next((f for f in facts_for_value if f.amendment_ref), facts_for_value[0])]
                )
                + "."
            )
            original = next((fact for fact in dated if not fact.amendment_ref), dated[0])
            resolution = (
                f"The original terms ({original.currency} {original.unit_price:,.2f}"
                + (f" from {original.effective_date.isoformat()}" if original.effective_date else "")
                + f") are changed to {preferred.currency} {preferred.unit_price:,.2f}"
                + (f" effective {preferred.effective_date.isoformat()}" if preferred.effective_date else "")
                + (f" by {preferred.amendment_ref}" if preferred.amendment_ref else "")
                + "; the later terms govern from that date."
            )
        else:
            description = (
                f"{supplier_name} has conflicting unit prices for {product_name} across documents: "
                + "; ".join(f"{fact.currency} {fact.unit_price:,.2f}" for fact in dated)
                + " with no effective dates to order them."
            )
            resolution = (
                "Neither price carries an effective date, so the current price cannot be determined "
                "from the data alone; both sources are shown."
            )
        conflicts.append(
            Conflict(
                kind="price_conflict",
                description=description,
                values=[fact.as_dict() for fact in dated],
                resolution=resolution,
                preferred=preferred.as_dict(),
                citations=[
                    {
                        "document_id": fact.document_id,
                        "document_name": fact.document_name,
                        "page": fact.page,
                        "label": f"{fact.document_name or 'document'}"
                        + (f" — p.{fact.page}" if fact.page else ""),
                        "evidence_type": "structured_price",
                    }
                    for fact in dated
                ],
            )
        )
    return conflicts


def fact_valid_in_period(fact: PriceFact, date_from: date | None, date_to: date | None) -> bool:
    """Whether a price row's validity window intersects the asked period.

    A row with no effective date is treated as open at the start and a row with
    no expiry date as open at the end, so an undated row is never silently
    excluded from a period question.
    """
    if date_from is not None and fact.expiry_date is not None and fact.expiry_date < date_from:
        return False
    if date_to is not None and fact.effective_date is not None and fact.effective_date > date_to:
        return False
    return True


def describe_validity_window(fact: PriceFact) -> str:
    start = fact.effective_date.isoformat() if fact.effective_date else "unknown start"
    end = fact.expiry_date.isoformat() if fact.expiry_date else "open-ended"
    return f"{start} → {end}"


def current_price(
    facts: list[PriceFact], *, as_of: date | None = None, supplier_id: str | None = None
) -> PriceFact | None:
    """The price in force for a supplier/product on a date, chosen by effective date."""
    as_of = as_of or date.today()
    candidates = [fact for fact in facts if supplier_id is None or fact.supplier_id == supplier_id]
    if not candidates:
        return None
    applicable = [
        fact
        for fact in candidates
        if (fact.effective_date is None or fact.effective_date <= as_of)
        and (fact.expiry_date is None or fact.expiry_date >= as_of)
    ]
    pool = applicable or candidates
    return max(pool, key=lambda fact: (fact.effective_date or date.min, fact.amendment_ref or ""))


def temporal_summary(facts: list[PriceFact], *, as_of: date | None = None) -> dict[str, Any]:
    as_of = as_of or date.today()
    return {
        "as_of": as_of.isoformat(),
        "total_price_rows": len(facts),
        "rows_in_force": sum(
            1
            for fact in facts
            if (fact.effective_date is None or fact.effective_date <= as_of)
            and (fact.expiry_date is None or fact.expiry_date >= as_of)
        ),
        "rows_expired": sum(1 for fact in facts if fact.is_expired),
        "rows_without_effective_date": sum(1 for fact in facts if fact.effective_date is None),
        "amendments_referenced": sorted({fact.amendment_ref for fact in facts if fact.amendment_ref}),
    }
