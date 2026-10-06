"""Structured RAG (PRD s.34).

Questions with exact answers are answered by PostgreSQL, not by a language model:

* "total procurement value for Supplier A in 2025" → SQL sum over the price/award
  rows, computed by the database;
* "lowest unit price for X" → SQL min plus the row that produced it;
* "compare A and B" → a matrix assembled from the structured rows;
* "is the contract expired" → date comparison against ``date.today()``.

Derived arithmetic (per-unit × quantity, percentage differences) is done in
Python and labelled ``python_arithmetic``; nothing is estimated by a model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ComplianceCertificate,
    Contract,
    Document,
    Price,
    ProcurementRecord,
    Product,
    Supplier,
)
from app.observability.logging import get_logger
from app.retrieval.analysis import (
    Conflict,
    PriceFact,
    current_price,
    dedupe_price_facts,
    describe_validity_window,
    detect_price_conflicts,
    fact_valid_in_period,
    fetch_price_facts,
)
from app.retrieval.context import CitationDraft
from app.retrieval.query_understanding import Intent, QueryPlan
from app.security.rbac import Principal

logger = get_logger(__name__)


@dataclass(slots=True)
class Aggregation:
    name: str
    value: float | int | str | None
    unit: str | None = None
    method: str = "sql_aggregation"
    detail: str = ""
    group: dict[str, Any] = field(default_factory=dict)
    row_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "method": self.method,
            "detail": self.detail,
            "group": self.group,
            "row_count": self.row_count,
        }


@dataclass(slots=True)
class StructuredResult:
    facts: list[PriceFact] = field(default_factory=list)
    aggregations: list[Aggregation] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    contracts: list[dict[str, Any]] = field(default_factory=list)
    compliance: list[dict[str, Any]] = field(default_factory=list)
    suppliers: list[dict[str, Any]] = field(default_factory=list)
    citations: list[CitationDraft] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    queried: bool = False
    purpose: str = ""

    @property
    def has_data(self) -> bool:
        return bool(self.facts or self.aggregations or self.contracts or self.compliance or self.suppliers)

    def as_dict(self) -> dict[str, Any]:
        return {
            "facts": [fact.as_dict() for fact in self.facts],
            "aggregations": [agg.as_dict() for agg in self.aggregations],
            "conflicts": [conflict.as_dict() for conflict in self.conflicts],
            "contracts": self.contracts,
            "compliance": self.compliance,
            "suppliers": self.suppliers,
            "notes": self.notes,
            "queried": self.queried,
            "purpose": self.purpose,
        }


def _price_citation(fact: PriceFact, *, rank: int | None = None) -> CitationDraft:
    return CitationDraft(
        chunk_id=None,
        document_id=fact.document_id,
        document_name=fact.document_name or "structured procurement record",
        document_type="price_record",
        page=fact.page,
        section="Pricing",
        clause=None,
        snippet=(
            f"{fact.supplier_name or 'Supplier'} — {fact.product_name or 'item'}: "
            f"{fact.currency} {fact.unit_price:,.2f}"
            + (f" (MOQ {fact.minimum_quantity})" if fact.minimum_quantity else "")
            + (f", effective {fact.effective_date.isoformat()}" if fact.effective_date else "")
            + (f", {fact.amendment_ref}" if fact.amendment_ref else "")
        ),
        score=None,
        rank=rank,
        evidence_type="structured_price",
        is_synthetic=fact.is_synthetic,
        verified=True,
        metadata={"price_id": fact.price_id, "contract_number": fact.contract_number},
    )


async def structured_lookup(
    session: AsyncSession, principal: Principal, plan: QueryPlan, *, limit: int = 200
) -> StructuredResult:
    """Answer the structured portion of a plan from PostgreSQL."""
    result = StructuredResult(queried=True, purpose=plan.intent.value)
    wants_structured = plan.requires_structured or plan.intent in {
        Intent.PRICE_LOOKUP,
        Intent.AGGREGATION,
        Intent.COMPARISON,
        Intent.TEMPORAL_CHANGE,
        Intent.COMPLIANCE_CHECK,
    }

    # Price rows are only pulled in when the question is *about* prices. A
    # question that names no supplier, product or contract and asks for no
    # aggregate ("what does the pricing table on page 4 say?") is a document
    # question: dumping every price row into it would attach unrelated figures
    # and unrelated conflicts to the answer.
    scoped = bool(plan.supplier_ids or plan.product_ids or plan.contract_ids)
    aggregate_question = (
        plan.intent in {Intent.AGGREGATION, Intent.COMPARISON}
        or plan.requires_comparison
        or plan.year is not None
        or plan.date_from is not None
        or plan.date_to is not None
    )
    wants_price_rows = scoped or aggregate_question or plan.requires_structured
    facts = (
        await fetch_price_facts(
            session,
            principal,
            supplier_ids=plan.supplier_ids or None,
            product_ids=plan.product_ids or None,
            contract_ids=plan.contract_ids or None,
            limit=limit,
        )
        if wants_price_rows
        else []
    )
    # The same agreed value can appear in several documents; report it once and
    # keep the other sources as provenance.
    result.facts = dedupe_price_facts(facts)

    # A question that names a period ("in 2030", "as of 2025-06-01") is about the
    # rows whose validity window intersects that period. Values outside it are
    # kept aside, reported as a note, and never presented as the answer: this is
    # what makes "no price was agreed for 2030" a real finding rather than a
    # stale figure shown under the wrong year.
    if plan.date_from is not None or plan.date_to is not None:
        in_period = [
            fact for fact in result.facts if fact_valid_in_period(fact, plan.date_from, plan.date_to)
        ]
        outside = [fact for fact in result.facts if fact not in in_period]
        if outside:
            result.notes.append(
                f"{len(outside)} matched price row(s) fall outside the asked period "
                f"({_period_label(plan)}): "
                + "; ".join(
                    f"{fact.supplier_name or 'unattributed'}"
                    + (f"/{fact.product_name}" if fact.product_name else "")
                    + f" {fact.currency} {fact.unit_price:,.2f} valid {describe_validity_window(fact)}"
                    for fact in outside[:4]
                )
                + "."
            )
        result.facts = in_period

    if result.facts:
        result.conflicts = detect_price_conflicts(result.facts)
        result.citations.extend(
            _price_citation(fact, rank=index) for index, fact in enumerate(result.facts[:20], start=1)
        )

    if wants_price_rows and (wants_structured or plan.year):
        wants_totals = (
            plan.intent in {Intent.AGGREGATION, Intent.COMPARISON}
            or bool(plan.year)
            or plan.requires_comparison
        )
        result.aggregations.extend(
            await _aggregate(session, principal, plan, result.facts, include_totals=wants_totals)
        )
    if result.facts and (
        plan.intent in {Intent.COMPARISON, Intent.AGGREGATION}
        or plan.requires_comparison
        or len(plan.supplier_ids) >= 2
    ):
        result.aggregations.extend(_comparison_aggregations(result.facts))
    if plan.contract_ids or plan.contract_numbers:
        result.contracts = await _contract_overview(session, principal, plan)
    if plan.intent == Intent.COMPLIANCE_CHECK or plan.requires_graph:
        result.compliance = await _compliance_overview(session, principal, plan)
    if plan.supplier_ids:
        result.suppliers = await _supplier_overview(session, principal, plan)

    if not facts and not result.contracts and not result.compliance:
        result.notes.append(
            "No structured price, contract or compliance rows matched the question; the answer relies on "
            "document evidence."
        )
    return result


async def _aggregate(
    session: AsyncSession,
    principal: Principal,
    plan: QueryPlan,
    facts: list[PriceFact],
    *,
    include_totals: bool = True,
) -> list[Aggregation]:
    aggregations: list[Aggregation] = []
    tenant_id = principal.tenant_id

    # -- unit price statistics for the matched rows (SQL aggregate)
    # Only meaningful when the rows describe one comparable item; a min/max over
    # a mixed basket of products would be a number nobody asked for.
    single_item = bool(plan.product_ids) or len({fact.product_id for fact in facts}) == 1
    if facts and single_item:
        prices = [fact.unit_price for fact in facts]
        aggregations.append(
            Aggregation(
                name="unit_price_min",
                value=min(prices),
                unit=facts[0].currency,
                detail="Minimum unit price across matched price rows",
                row_count=len(facts),
            )
        )
        aggregations.append(
            Aggregation(
                name="unit_price_max",
                value=max(prices),
                unit=facts[0].currency,
                detail="Maximum unit price across matched price rows",
                row_count=len(facts),
            )
        )
        aggregations.append(
            Aggregation(
                name="unit_price_average",
                value=round(sum(prices) / len(prices), 4),
                unit=facts[0].currency,
                method="python_arithmetic",
                detail="Mean of matched unit prices (computed in Python from the SQL result set)",
                row_count=len(facts),
            )
        )

    if not include_totals:
        return aggregations

    # -- recorded line totals (award/PO value already present in the data)
    recorded = [fact for fact in facts if fact.line_total is not None]
    if recorded:
        aggregations.append(
            Aggregation(
                name="recorded_value_total",
                value=round(sum(fact.line_total or 0.0 for fact in recorded), 2),
                unit=recorded[0].currency,
                detail="Sum of line totals recorded on the matched rows (SQL SUM plus Python reduction)",
                row_count=len(recorded),
            )
        )

    # -- derived quantity × unit price (only where quantity is recorded)
    with_quantity = [fact for fact in facts if fact.quantity and fact.line_total is None]
    if with_quantity:
        total = round(sum(fact.unit_price * (fact.quantity or 0) for fact in with_quantity), 2)
        aggregations.append(
            Aggregation(
                name="derived_value_total",
                value=total,
                unit=with_quantity[0].currency,
                method="python_arithmetic",
                detail=(
                    "Quantity × unit price for rows that record a quantity but no line total; "
                    "computed exactly in Python, not estimated by a model"
                ),
                row_count=len(with_quantity),
            )
        )

    # -- procurement records by year (Layer B structured dataset)
    statement = select(
        ProcurementRecord.award_date, ProcurementRecord.value, ProcurementRecord.supplier_id
    ).where(ProcurementRecord.tenant_id == tenant_id)
    if plan.supplier_ids:
        statement = statement.where(ProcurementRecord.supplier_id.in_(plan.supplier_ids))
    records = (await session.execute(statement.limit(5000))).all()
    if records and plan.year:
        matching = [row for row in records if row[0] is not None and row[0].year == plan.year]
        # A year with no rows is reported as "no data for that year", never as a
        # zero total: an absent row is not a recorded value of zero.
        if matching:
            aggregations.append(
                Aggregation(
                    name=f"procurement_value_{plan.year}",
                    value=round(sum(float(row[1] or 0.0) for row in matching), 2),
                    unit="USD",
                    detail=(
                        f"SQL aggregation over {len(matching)} procurement award row(s) "
                        f"with award_date in {plan.year}"
                    ),
                    group={"year": plan.year},
                    row_count=len(matching),
                )
            )
        else:
            aggregations.append(
                Aggregation(
                    name=f"procurement_value_{plan.year}",
                    value=None,
                    unit="USD",
                    method="sql_aggregation",
                    detail=(
                        f"No procurement award row has award_date in {plan.year} "
                        f"({len(records)} row(s) examined)"
                    ),
                    group={"year": plan.year},
                    row_count=0,
                )
            )
    elif records and not plan.year:
        total = sum(float(row[1] or 0.0) for row in records)
        aggregations.append(
            Aggregation(
                name="procurement_value_all_years",
                value=round(total, 2),
                unit="USD",
                detail=f"SQL aggregation over {len(records)} procurement award row(s)",
                row_count=len(records),
            )
        )

    # -- cheapest supplier among the rows that answer the question (grouped in
    #    Python over the SQL result set, with the row that produced the value)
    by_supplier: dict[str, PriceFact] = {}
    for fact in facts:
        if fact.supplier_id is None:
            continue
        current = by_supplier.get(fact.supplier_id)
        if current is None or fact.unit_price < current.unit_price:
            by_supplier[fact.supplier_id] = fact
    if by_supplier:
        cheapest = min(by_supplier.values(), key=lambda fact: fact.unit_price)
        scope = _period_label(plan) if (plan.date_from or plan.date_to) else "all recorded periods"
        products = {fact.product_name for fact in by_supplier.values() if fact.product_name}
        cross_product_note = (
            f"; the rows span {len(products)} different products, so this compares unit prices across "
            "different items rather than like for like"
            if len(products) > 1
            else ""
        )
        aggregations.append(
            Aggregation(
                name="lowest_price_supplier",
                value=cheapest.unit_price,
                unit=cheapest.currency,
                method="sql_result_set+python_min",
                detail=(
                    f"Cheapest of the {len(by_supplier)} supplier(s) with a price row valid in {scope}: "
                    f"{cheapest.supplier_name}"
                    + (f" for {cheapest.product_name}" if cheapest.product_name else "")
                    + (f" (MOQ {cheapest.minimum_quantity})" if cheapest.minimum_quantity else "")
                    + (
                        f", effective {cheapest.effective_date.isoformat()}"
                        if cheapest.effective_date
                        else ""
                    )
                    + cross_product_note
                    + "."
                ),
                group={
                    "supplier": cheapest.supplier_name,
                    "supplier_id": cheapest.supplier_id,
                    "product": cheapest.product_name,
                    "document": cheapest.document_name,
                    "page": cheapest.page,
                },
                row_count=len(by_supplier),
            )
        )

    # -- grouped cheapest price per product (SQL GROUP BY, Python pick)
    # The aggregate is scoped to the entities and the period the question named,
    # so "lowest price in 2025" cannot be answered with a 2026 value.
    grouped = (
        select(
            Product.name,
            func.min(Price.unit_price),
            func.count(Price.id),
        )
        .join(Price, Price.product_id == Product.id)
        .where(Product.tenant_id == tenant_id, Price.tenant_id == tenant_id)
        .group_by(Product.name)
    )
    if plan.supplier_ids:
        grouped = grouped.where(Price.supplier_id.in_(plan.supplier_ids))
    if plan.product_ids:
        grouped = grouped.where(Price.product_id.in_(plan.product_ids))
    if plan.date_to is not None:
        grouped = grouped.where((Price.effective_date.is_(None)) | (Price.effective_date <= plan.date_to))
    if plan.date_from is not None:
        grouped = grouped.where((Price.expiry_date.is_(None)) | (Price.expiry_date >= plan.date_from))
    for product_name, min_price, count in (await session.execute(grouped)).all():
        aggregations.append(
            Aggregation(
                name="lowest_unit_price",
                value=float(min_price) if min_price is not None else None,
                unit="USD",
                detail=(
                    f"SQL MIN over {int(count)} price row(s) for '{product_name}'"
                    + (f" valid in {_period_label(plan)}" if plan.date_from or plan.date_to else "")
                ),
                group={"product": product_name},
                row_count=int(count),
            )
        )
    return aggregations


def _comparison_aggregations(facts: list[PriceFact]) -> list[Aggregation]:
    """Per-supplier facts used by the comparison workspace and the answer."""
    aggregations: list[Aggregation] = []
    grouped: dict[str, list[PriceFact]] = {}
    for fact in facts:
        key = fact.supplier_name or fact.supplier_id or "unknown"
        grouped.setdefault(key, []).append(fact)
    for supplier_name, group in grouped.items():
        prices = [fact.unit_price for fact in group]
        aggregations.append(
            Aggregation(
                name="supplier_unit_price",
                value=min(prices),
                unit=group[0].currency,
                detail=f"Lowest recorded unit price for {supplier_name} in the matched rows",
                group={"supplier": supplier_name},
                row_count=len(group),
            )
        )
    return aggregations


async def _contract_overview(
    session: AsyncSession, principal: Principal, plan: QueryPlan
) -> list[dict[str, Any]]:
    statement = (
        select(Contract, Supplier.name)
        .outerjoin(Supplier, Contract.supplier_id == Supplier.id)
        .where(Contract.tenant_id == principal.tenant_id)
    )
    if plan.contract_ids:
        statement = statement.where(Contract.id.in_(plan.contract_ids))
    elif plan.contract_numbers:
        statement = statement.where(Contract.contract_number.in_(plan.contract_numbers))
    elif plan.supplier_ids:
        statement = statement.where(Contract.supplier_id.in_(plan.supplier_ids))
    rows = (await session.execute(statement.limit(50))).all()
    overviews: list[dict[str, Any]] = []
    today = date.today()
    for contract, supplier_name in rows:
        document_ids = [
            row[0]
            for row in (
                await session.execute(
                    select(Document.id).where(Document.contract_id == contract.id).limit(20)
                )
            ).all()
        ]
        overviews.append(
            {
                "contract_id": contract.id,
                "contract_number": contract.contract_number,
                "title": contract.title,
                "supplier_id": contract.supplier_id,
                "supplier_name": supplier_name,
                "status": contract.status,
                "version": contract.version,
                "effective_date": contract.effective_date.isoformat() if contract.effective_date else None,
                "expiry_date": contract.expiry_date.isoformat() if contract.expiry_date else None,
                "is_expired": bool(contract.expiry_date and contract.expiry_date < today),
                "currency": contract.currency,
                "total_value": contract.total_value,
                "document_ids": document_ids,
            }
        )
    return overviews


async def _compliance_overview(
    session: AsyncSession, principal: Principal, plan: QueryPlan
) -> list[dict[str, Any]]:
    statement = (
        select(ComplianceCertificate, Supplier.name, Document.title, Document.filename)
        .outerjoin(Supplier, ComplianceCertificate.supplier_id == Supplier.id)
        .outerjoin(Document, ComplianceCertificate.source_document_id == Document.id)
        .where(ComplianceCertificate.tenant_id == principal.tenant_id)
    )
    if plan.supplier_ids:
        statement = statement.where(ComplianceCertificate.supplier_id.in_(plan.supplier_ids))
    rows = (await session.execute(statement.limit(100))).all()
    today = date.today()
    return [
        {
            "certificate_id": certificate.id,
            "supplier_id": certificate.supplier_id,
            "supplier_name": supplier_name,
            "certificate_type": certificate.certificate_type,
            "certificate_number": certificate.certificate_number,
            "issued_date": certificate.issued_date.isoformat() if certificate.issued_date else None,
            "expiry_date": certificate.expiry_date.isoformat() if certificate.expiry_date else None,
            "status": certificate.status,
            "is_expired": bool(certificate.expiry_date and certificate.expiry_date < today),
            "source_document_id": certificate.source_document_id,
            "source_document_name": document_title or document_filename,
            "source_page": certificate.source_page,
        }
        for certificate, supplier_name, document_title, document_filename in rows
    ]


async def _supplier_overview(
    session: AsyncSession, principal: Principal, plan: QueryPlan
) -> list[dict[str, Any]]:
    if not plan.supplier_ids:
        return []
    rows = (
        await session.execute(
            select(Supplier).where(
                Supplier.tenant_id == principal.tenant_id, Supplier.id.in_(plan.supplier_ids)
            )
        )
    ).scalars()
    summaries: list[dict[str, Any]] = []
    for supplier in rows:
        contract_count = await session.scalar(
            select(func.count(Contract.id)).where(
                Contract.tenant_id == principal.tenant_id, Contract.supplier_id == supplier.id
            )
        )
        price_count = await session.scalar(
            select(func.count(Price.id)).where(
                Price.tenant_id == principal.tenant_id, Price.supplier_id == supplier.id
            )
        )
        document_count = await session.scalar(
            select(func.count(Document.id)).where(
                Document.tenant_id == principal.tenant_id, Document.supplier_id == supplier.id
            )
        )
        summaries.append(
            {
                "supplier_id": supplier.id,
                "supplier_name": supplier.name,
                "category": supplier.category,
                "region": supplier.region,
                "status": supplier.status,
                "is_synthetic": supplier.is_synthetic,
                "contract_count": int(contract_count or 0),
                "price_count": int(price_count or 0),
                "document_count": int(document_count or 0),
            }
        )
    return summaries


async def comparison_matrix(
    session: AsyncSession,
    principal: Principal,
    *,
    supplier_ids: list[str],
    product_ids: list[str] | None = None,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Supplier-vs-supplier matrix built from structured rows (used by /compare)."""
    as_of = as_of or date.today()
    facts = await fetch_price_facts(
        session, principal, supplier_ids=supplier_ids, product_ids=product_ids or None, limit=500
    )
    suppliers = list(
        (
            await session.execute(
                select(Supplier).where(
                    Supplier.tenant_id == principal.tenant_id, Supplier.id.in_(supplier_ids)
                )
            )
        ).scalars()
    )
    certificates = list(
        (
            await session.execute(
                select(ComplianceCertificate).where(
                    ComplianceCertificate.tenant_id == principal.tenant_id,
                    ComplianceCertificate.supplier_id.in_(supplier_ids),
                )
            )
        ).scalars()
    )
    contracts = list(
        (
            await session.execute(
                select(Contract).where(
                    Contract.tenant_id == principal.tenant_id, Contract.supplier_id.in_(supplier_ids)
                )
            )
        ).scalars()
    )

    columns: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for supplier in suppliers:
        supplier_facts = [fact for fact in facts if fact.supplier_id == supplier.id]
        active_facts = [
            fact
            for fact in supplier_facts
            if (fact.effective_date is None or fact.effective_date <= as_of)
            and (fact.expiry_date is None or fact.expiry_date >= as_of)
        ]
        chosen = max(
            active_facts or supplier_facts,
            key=lambda fact: (fact.effective_date or date.min, fact.amendment_ref or ""),
            default=None,
        )
        supplier_contracts = [contract for contract in contracts if contract.supplier_id == supplier.id]
        supplier_certificates = [c for c in certificates if c.supplier_id == supplier.id]
        cells: dict[str, Any] = {}

        def cell(
            key: str,
            value: Any,
            *,
            source: str = "structured",
            citations: list[dict[str, Any]] | None = None,
            notes: list[str] | None = None,
            _cells: dict[str, Any] = cells,  # bind loop variable explicitly (B023)
        ) -> None:
            _cells[key] = {
                "key": key,
                "value": value,
                "formatted": _format(value),
                "source": source,
                "citations": citations or [],
                "notes": notes or [],
            }

        if chosen is not None:
            cell(
                "unit_price",
                chosen.unit_price,
                citations=[_price_citation(chosen).as_dict()],
            )
            cell("currency", chosen.currency)
            cell("minimum_quantity", chosen.minimum_quantity)
            cell("discount_percent", chosen.discount_percent)
            cell("payment_terms", chosen.payment_terms)
            cell("delivery_terms", chosen.delivery_terms)
            cell("price_effective_date", chosen.effective_date.isoformat() if chosen.effective_date else None)
            cell("price_amendment", chosen.amendment_ref)
        else:
            for key in (
                "unit_price",
                "minimum_quantity",
                "discount_percent",
                "payment_terms",
                "delivery_terms",
            ):
                cell(
                    key, None, source="unavailable", notes=["No structured price row matched this supplier."]
                )
            unresolved.append(f"{supplier.name}: no structured price row")

        if supplier_contracts:
            contract = max(supplier_contracts, key=lambda item: item.version)
            cell("contract_number", contract.contract_number)
            cell("contract_status", contract.status)
            cell("contract_version", contract.version)
            cell("contract_expiry", contract.expiry_date.isoformat() if contract.expiry_date else None)
            cell(
                "contract_duration",
                _duration_days(contract.effective_date, contract.expiry_date),
                source="derived",
                notes=["Computed from the stored effective and expiry dates."],
            )
            cell(
                "renewal",
                (contract.metadata_json or {}).get("renewal")
                or ("Automatic renewal clause present" if contract.metadata_json.get("renewal") else None),
                source="structured" if (contract.metadata_json or {}).get("renewal") else "unavailable",
            )
        else:
            for key in ("contract_number", "contract_status", "contract_expiry", "renewal"):
                cell(key, None, source="unavailable", notes=["No contract row for this supplier."])

        if supplier_certificates:
            active = [
                c
                for c in supplier_certificates
                if c.status == "active" and not (c.expiry_date and c.expiry_date < as_of)
            ]
            cell(
                "compliance",
                ", ".join(sorted({c.certificate_type for c in active})) or None,
                citations=[
                    {
                        "document_id": c.source_document_id,
                        "document_name": "compliance certificate",
                        "page": c.source_page,
                        "label": c.certificate_type,
                        "evidence_type": "structured_compliance",
                    }
                    for c in supplier_certificates
                ],
                notes=[] if active else ["Certificates exist but none is currently in force."],
            )
        else:
            cell("compliance", None, source="unavailable", notes=["No compliance certificate on record."])

        columns.append(
            {
                "supplier_id": supplier.id,
                "supplier_name": supplier.name,
                "cells": cells,
                "price_rows": len(supplier_facts),
            }
        )

    return {
        "as_of": as_of.isoformat(),
        "columns": columns,
        "unresolved": unresolved,
        "price_rows_considered": len(facts),
        "notes": [
            "Every value is read from workspace database rows extracted from the documents; "
            "cells marked 'unavailable' have no matching record and are never estimated.",
        ],
    }


def _period_label(plan: QueryPlan) -> str:
    if plan.date_from and plan.date_to and plan.date_from == plan.date_to:
        return plan.date_from.isoformat()
    start = plan.date_from.isoformat() if plan.date_from else "…"
    end = plan.date_to.isoformat() if plan.date_to else "…"
    return f"{start} to {end}"


def _format(value: Any) -> str:
    if value is None:
        return "Not available"
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


def _duration_days(start: date | None, end: date | None) -> int | None:
    if start is None or end is None:
        return None
    return (end - start).days


async def best_price_by_supplier(
    session: AsyncSession, principal: Principal, *, product_ids: list[str] | None = None
) -> list[dict[str, Any]]:
    """Cheapest current price per supplier for the given products."""
    facts = await fetch_price_facts(session, principal, product_ids=product_ids, limit=500)
    by_supplier: dict[str, PriceFact] = {}
    for fact in facts:
        key = fact.supplier_id or "unknown"
        chosen = current_price([fact], supplier_id=fact.supplier_id)
        if chosen is None:
            continue
        existing = by_supplier.get(key)
        if existing is None or chosen.unit_price < existing.unit_price:
            by_supplier[key] = chosen
    return [
        {
            "supplier_id": fact.supplier_id,
            "supplier_name": fact.supplier_name,
            "product_name": fact.product_name,
            "unit_price": fact.unit_price,
            "currency": fact.currency,
            "effective_date": fact.effective_date.isoformat() if fact.effective_date else None,
            "document_id": fact.document_id,
            "document_name": fact.document_name,
            "page": fact.page,
        }
        for fact in sorted(by_supplier.values(), key=lambda item: item.unit_price)
    ]
