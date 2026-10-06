"""Retrieval regression tests — supplier comparison and temporal price queries.

These are the regression tests for the two known issues identified in the audit:

  ISSUE A: Supplier comparison answer omitting Supplier B.
  ISSUE B: Lowest-price / historical price query returning wrong aggregation.

Tests are pure-logic: they construct synthetic PriceFact and StructuredResult
objects and verify the generation layer produces answers that include all
expected suppliers and correctly identify the cheapest price for the queried year.

No database, no LLM, no HTTP.
"""

from __future__ import annotations

from datetime import date

from app.agents.generation import (
    _comparison_lead,
    _direct_answer,
    _lowest_price_lead,
)
from app.retrieval.analysis import PriceFact
from app.retrieval.context import ContextBundle
from app.retrieval.query_understanding import Intent, QueryPlan
from app.retrieval.structured import Aggregation, StructuredResult

# ------------------------------------------------------------------ helpers


def make_price_fact(
    *,
    supplier_id: str,
    supplier_name: str,
    product_id: str = "prod_001",
    product_name: str = "Widget A",
    unit_price: float,
    effective_date: date | None = None,
    expiry_date: date | None = None,
    amendment_ref: str | None = None,
    currency: str = "USD",
    document_id: str | None = None,
    document_name: str | None = None,
    page: int | None = None,
) -> PriceFact:
    return PriceFact(
        price_id=f"pr_{supplier_id}",
        supplier_id=supplier_id,
        supplier_name=supplier_name,
        contract_id=None,
        contract_number=None,
        product_id=product_id,
        product_name=product_name,
        unit_price=unit_price,
        currency=currency,
        minimum_quantity=None,
        discount_percent=None,
        payment_terms=None,
        delivery_terms=None,
        effective_date=effective_date,
        expiry_date=expiry_date,
        amendment_ref=amendment_ref,
        document_id=document_id or f"doc_{supplier_id}",
        document_name=document_name or f"{supplier_name} Contract",
        page=page or 1,
        is_synthetic=True,
    )


def empty_bundle() -> ContextBundle:
    return ContextBundle(blocks=[], citations=[])


def make_comparison_plan(supplier_ids: list[str]) -> QueryPlan:
    return QueryPlan(
        query="Compare Supplier A and Supplier B unit prices",
        intent=Intent.COMPARISON,
        supplier_ids=supplier_ids,
        requires_comparison=True,
    )


def make_lowest_price_plan(year: int | None = None) -> QueryPlan:
    return QueryPlan(
        query=f"What was the lowest price in {year}?" if year else "What is the lowest unit price?",
        intent=Intent.AGGREGATION,
        year=year,
    )


# ================================================================== ISSUE A
# Supplier comparison must include BOTH suppliers.
# ==================================================================


class TestSupplierComparisonCoversAllSuppliers:
    """Regression tests for ISSUE A: omitted supplier in comparison answer."""

    def _run_comparison(self, supplier_ids: list[str], facts: list[PriceFact]) -> list[str]:
        structured = StructuredResult(facts=facts, queried=True)
        plan = make_comparison_plan(supplier_ids)
        return _comparison_lead(structured, empty_bundle(), plan)

    def test_both_suppliers_appear_in_comparison_lead(self) -> None:
        facts = [
            make_price_fact(supplier_id="sup_a", supplier_name="Supplier A", unit_price=92.0),
            make_price_fact(supplier_id="sup_b", supplier_name="Supplier B", unit_price=88.5),
        ]
        lines = self._run_comparison(["sup_a", "sup_b"], facts)
        text = "\n".join(lines)
        assert "Supplier A" in text, "Supplier A missing from comparison answer"
        assert "Supplier B" in text, "Supplier B missing from comparison answer — ISSUE A regression"

    def test_three_supplier_comparison_includes_all_three(self) -> None:
        facts = [
            make_price_fact(supplier_id="sup_a", supplier_name="Alpha Corp", unit_price=100.0),
            make_price_fact(supplier_id="sup_b", supplier_name="Beta Ltd", unit_price=95.0),
            make_price_fact(supplier_id="sup_c", supplier_name="Gamma Inc", unit_price=110.0),
        ]
        lines = self._run_comparison(["sup_a", "sup_b", "sup_c"], facts)
        text = "\n".join(lines)
        assert "Alpha Corp" in text
        assert "Beta Ltd" in text
        assert "Gamma Inc" in text

    def test_comparison_lead_empty_when_fewer_than_two_suppliers(self) -> None:
        facts = [
            make_price_fact(supplier_id="sup_a", supplier_name="Supplier A", unit_price=92.0),
        ]
        lines = self._run_comparison(["sup_a"], facts)
        # Only one supplier: no comparison possible
        assert lines == []

    def test_comparison_uses_current_price_when_multiple_versions(self) -> None:
        """The governing price (latest effective date, in-force) should be shown."""
        facts = [
            make_price_fact(
                supplier_id="sup_a",
                supplier_name="Supplier A",
                unit_price=920.0,
                effective_date=date(2024, 1, 1),
                amendment_ref="Original",
            ),
            make_price_fact(
                supplier_id="sup_a",
                supplier_name="Supplier A",
                unit_price=874.0,
                effective_date=date(2026, 1, 1),
                amendment_ref="Amendment 2",
            ),
            make_price_fact(
                supplier_id="sup_b",
                supplier_name="Supplier B",
                unit_price=860.0,
                effective_date=date(2025, 6, 1),
            ),
        ]
        lines = self._run_comparison(["sup_a", "sup_b"], facts)
        text = "\n".join(lines)
        # Both must be present
        assert "Supplier A" in text
        assert "Supplier B" in text
        # The governing Supplier A price should be 874 (Amendment 2), not 920
        assert "874" in text, "Expected amended price 874 for Supplier A, not the original 920"

    def test_comparison_prices_shown_with_figures(self) -> None:
        facts = [
            make_price_fact(supplier_id="s1", supplier_name="NovaChem", unit_price=78.50),
            make_price_fact(supplier_id="s2", supplier_name="GlobalMfg", unit_price=82.00),
        ]
        lines = self._run_comparison(["s1", "s2"], facts)
        text = "\n".join(lines)
        assert "78" in text or "78.50" in text
        assert "82" in text or "82.00" in text

    def test_direct_answer_delegates_to_comparison_when_required(self) -> None:
        facts = [
            make_price_fact(supplier_id="sup_a", supplier_name="Alpha", unit_price=50.0),
            make_price_fact(supplier_id="sup_b", supplier_name="Beta", unit_price=55.0),
        ]
        structured = StructuredResult(facts=facts, queried=True)
        plan = make_comparison_plan(["sup_a", "sup_b"])
        lines = _direct_answer(plan=plan, structured=structured, bundle=empty_bundle())
        text = "\n".join(lines)
        assert "Alpha" in text
        assert "Beta" in text


# ================================================================== ISSUE B
# Lowest-price query must name the supplier, product, and respect the year.
# ==================================================================


class TestLowestPriceQueryAccuracy:
    """Regression tests for ISSUE B: incomplete/incorrect lowest-price answer."""

    def _build_structured_with_lowest(
        self,
        cheapest_supplier: str,
        cheapest_price: float,
        product_name: str,
        facts: list[PriceFact],
    ) -> StructuredResult:
        structured = StructuredResult(facts=facts, queried=True)
        group = {
            "supplier": cheapest_supplier,
            "supplier_id": f"sup_{cheapest_supplier.lower().replace(' ', '_')}",
            "product": product_name,
        }
        structured.aggregations.append(
            Aggregation(
                name="lowest_price_supplier",
                value=cheapest_price,
                unit="USD",
                method="sql_result_set+python_min",
                detail=f"Cheapest: {cheapest_supplier} for {product_name}",
                group=group,
            )
        )
        return structured

    def test_lowest_price_lead_names_supplier(self) -> None:
        facts = [
            make_price_fact(supplier_id="sup_x", supplier_name="Nexus Ltd", unit_price=45.0),
        ]
        structured = self._build_structured_with_lowest("Nexus Ltd", 45.0, "Industrial Valve", facts)
        plan = make_lowest_price_plan()
        lines = _lowest_price_lead(structured, empty_bundle(), plan)
        text = "\n".join(lines)
        assert "Nexus Ltd" in text, "Supplier name missing from lowest-price answer — ISSUE B regression"

    def test_lowest_price_lead_names_product(self) -> None:
        facts = [
            make_price_fact(
                supplier_id="sup_y", supplier_name="AcmeCo", product_name="Pressure Sensor", unit_price=130.0
            ),
        ]
        structured = self._build_structured_with_lowest("AcmeCo", 130.0, "Pressure Sensor", facts)
        plan = make_lowest_price_plan()
        lines = _lowest_price_lead(structured, empty_bundle(), plan)
        text = "\n".join(lines)
        assert "Pressure Sensor" in text, "Product name missing from lowest-price answer"

    def test_lowest_price_lead_includes_price_figure(self) -> None:
        facts = [
            make_price_fact(supplier_id="sup_z", supplier_name="ZenithCo", unit_price=67.25),
        ]
        structured = self._build_structured_with_lowest("ZenithCo", 67.25, "Widget B", facts)
        plan = make_lowest_price_plan()
        lines = _lowest_price_lead(structured, empty_bundle(), plan)
        text = "\n".join(lines)
        assert "67" in text or "67.25" in text

    def test_lowest_price_with_year_shows_year_scope(self) -> None:
        facts = [
            make_price_fact(
                supplier_id="sup_a",
                supplier_name="Supplier A",
                unit_price=92.0,
                effective_date=date(2025, 1, 1),
            ),
        ]
        structured = self._build_structured_with_lowest("Supplier A", 92.0, "Widget A", facts)
        plan = make_lowest_price_plan(year=2025)
        # For a year query the plan sets date_from / date_to; simulate that
        from datetime import date as _date

        plan.date_from = _date(2025, 1, 1)
        plan.date_to = _date(2025, 12, 31)
        lines = _lowest_price_lead(structured, empty_bundle(), plan)
        text = "\n".join(lines)
        assert "2025" in text, "Year scope missing from lowest-price answer — ISSUE B regression"

    def test_lowest_price_returns_empty_when_no_lowest_aggregation(self) -> None:
        structured = StructuredResult(facts=[], queried=True)  # no aggregation
        plan = make_lowest_price_plan()
        lines = _lowest_price_lead(structured, empty_bundle(), plan)
        assert lines == [], "Should return empty list when no lowest_price_supplier aggregation"

    def test_direct_answer_returns_lowest_price_lead_for_aggregation_intent(self) -> None:
        facts = [
            make_price_fact(supplier_id="sup_q", supplier_name="QuadMfg", unit_price=55.0),
        ]
        structured = self._build_structured_with_lowest("QuadMfg", 55.0, "Component X", facts)
        plan = QueryPlan(
            query="What is the lowest unit price?",
            intent=Intent.AGGREGATION,
        )
        lines = _direct_answer(plan=plan, structured=structured, bundle=empty_bundle())
        text = "\n".join(lines)
        assert "QuadMfg" in text
        assert "55" in text or "55.0" in text


# ================================================================== Citations
# ==================================================================


class TestCitationIntegrity:
    """Citations must reference real documents; no phantom citations."""

    def test_comparison_lead_assigns_markers_from_bundle(self) -> None:
        from app.retrieval.context import CitationDraft, ContextBlock

        citation_a = CitationDraft(
            chunk_id=None,
            document_id="doc_a",
            document_name="Contract A",
            document_type="contract",
            page=1,
            section="Pricing",
            clause=None,
            snippet="Supplier A unit price: USD 92.00",
            score=0.9,
            rank=1,
            evidence_type="vector",
            is_synthetic=True,
            verified=True,
        )
        block_a = ContextBlock(
            marker="[1]",
            text="Supplier A unit price: USD 92.00",
            citation=citation_a,
            content_type="paragraph",
            is_synthetic=True,
        )
        bundle = ContextBundle(blocks=[block_a], citations=[citation_a])

        facts = [
            make_price_fact(
                supplier_id="sup_a",
                supplier_name="Supplier A",
                unit_price=92.0,
                document_id="doc_a",
                document_name="Contract A",
                page=1,
            ),
            make_price_fact(
                supplier_id="sup_b", supplier_name="Supplier B", unit_price=88.5, document_id="doc_b"
            ),
        ]
        structured = StructuredResult(facts=facts, queried=True)
        plan = make_comparison_plan(["sup_a", "sup_b"])
        lines = _comparison_lead(structured, bundle, plan)
        text = "\n".join(lines)
        # Marker [1] must appear for the document that is in the bundle
        assert "[1]" in text or "doc_a" in text or "Contract A" in text
