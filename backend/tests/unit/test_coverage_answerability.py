"""Regression tests for the answerability check (Phase 2, spec item 2).

Root cause reproduced here: the LLM query-understanding pass appends extra
supplier/product *name variants* to the plan without a matching id, so
``plan.suppliers`` and ``plan.supplier_ids`` stop being index-aligned. The
coverage check then evaluated the variant by literal text match, failed it, and
``decide_status`` turned that into ``insufficient_evidence`` — a refusal for a
question whose evidence was actually present (26 of the 130 v2 rows).

These tests assert the fix at the coverage level only: a name variant of an
entity that *is* covered must not become an unsatisfied constraint, while a
genuinely absent entity must still be reported unsatisfied (so real refusals
like gq-016 are preserved).
"""

from __future__ import annotations

from app.agents.verification import assess_query_coverage, decide_status
from app.retrieval.analysis import PriceFact
from app.retrieval.context import CitationDraft, ContextBlock, ContextBundle
from app.retrieval.structured import Aggregation, StructuredResult

# ------------------------------------------------------------------ helpers


def price_fact(**overrides) -> PriceFact:
    base: dict = {
        "price_id": "prc-1",
        "supplier_id": "sup-1",
        "supplier_name": "Northwind Industrial Supplies Ltd",
        "contract_id": "con-1",
        "contract_number": "NS-2024-001",
        "product_id": "prd-1",
        "product_name": 'Enterprise Monitor 27"',
        "unit_price": 310.0,
        "currency": "USD",
        "minimum_quantity": None,
        "discount_percent": None,
        "payment_terms": None,
        "delivery_terms": None,
        "effective_date": None,
        "expiry_date": None,
        "amendment_ref": None,
        "document_id": "doc-1",
        "document_name": "Contract NS-2024-001",
        "page": 1,
        "is_synthetic": True,
    }
    base.update(overrides)
    return PriceFact(**base)


def make_bundle(snippets: list[str]) -> ContextBundle:
    citations = [
        CitationDraft(
            chunk_id=f"chk_{i}",
            document_id=f"doc_{i}",
            document_name=f"Document {i}",
            page=1,
            snippet=snippet,
            evidence_type="document",
            verified=True,
        )
        for i, snippet in enumerate(snippets)
    ]
    blocks = [
        ContextBlock(
            marker=f"[{i + 1}]",
            text=f"[{i + 1}] {citation.snippet}",
            citation=citation,
            content_type="paragraph",
            is_synthetic=True,
        )
        for i, citation in enumerate(citations)
    ]
    return ContextBundle(blocks=blocks, citations=citations)


def plan(**overrides) -> dict:
    base = {
        "query": "what is the price",
        "intent": "price_lookup",
        "suppliers": [],
        "supplier_ids": [],
        "products": [],
        "product_ids": [],
        "date_from": None,
        "date_to": None,
    }
    base.update(overrides)
    return base


# ============================================================ supplier variants


class TestSupplierNameVariants:
    def test_llm_added_alias_does_not_break_coverage(self) -> None:
        """`Northwind` (LLM variant, no id) must inherit the id-backed sibling."""
        coverage = assess_query_coverage(
            plan(suppliers=["Northwind Industrial Supplies Ltd", "Northwind"], supplier_ids=["sup-1"]),
            make_bundle(['Enterprise Monitor 27" unit price is USD 310.00.']),
            StructuredResult(queried=True, facts=[price_fact()]),
        )
        assert coverage.satisfied, coverage.as_dict()
        assert coverage.unsatisfied == []

    def test_alias_resolved_by_structured_supplier_name(self) -> None:
        """A short form is covered when structured rows carry the full name."""
        coverage = assess_query_coverage(
            plan(suppliers=["Northwind"]),
            make_bundle(["Unit price USD 310.00."]),
            StructuredResult(queried=True, facts=[price_fact()]),
        )
        assert coverage.satisfied, coverage.as_dict()

    def test_supplier_variant_covered_by_aggregation_group(self) -> None:
        """An aggregation computed for the supplier is evidence for the supplier."""
        structured = StructuredResult(
            queried=True,
            aggregations=[
                Aggregation(
                    name="procurement_value_2025",
                    value=2_162_000.0,
                    unit="USD",
                    group={"supplier": "Northwind Industrial Supplies Ltd", "year": "2025"},
                    row_count=12,
                )
            ],
        )
        coverage = assess_query_coverage(
            plan(intent="aggregation", suppliers=["Northwind"], date_from="2025-01-01", date_to="2025-12-31"),
            make_bundle(["A passage with no supplier name."]),
            structured,
        )
        assert coverage.satisfied, coverage.as_dict()


# ============================================================= product variants


class TestProductNameVariants:
    def test_quoted_size_variant_matches_inch_spelling(self) -> None:
        """`Enterprise Monitor 27 inch` and `Enterprise Monitor 27"` are the same name."""
        coverage = assess_query_coverage(
            plan(products=['Enterprise Monitor 27"', "Enterprise Monitor 27 inch"], product_ids=["prd-1"]),
            make_bundle(["Unit price USD 310.00."]),
            StructuredResult(queried=True, facts=[price_fact()]),
        )
        assert coverage.satisfied, coverage.as_dict()
        assert coverage.unsatisfied == []

    def test_product_variant_covered_by_structured_product_name(self) -> None:
        coverage = assess_query_coverage(
            plan(products=["Enterprise Monitor 27 inch"]),
            make_bundle(["Unit price USD 310.00."]),
            StructuredResult(queried=True, facts=[price_fact()]),
        )
        assert coverage.satisfied, coverage.as_dict()


# =================================================== real refusals must survive


class TestGenuineAbsenceStillUnsatisfied:
    def test_unknown_supplier_is_unsatisfied(self) -> None:
        coverage = assess_query_coverage(
            plan(intent="compliance_check", suppliers=["Supplier C"]),
            make_bundle(["Acme Corp is based in the United States."]),
            StructuredResult(queried=True, facts=[price_fact()]),
        )
        assert not coverage.satisfied
        assert any(item["constraint"] == "supplier=Supplier C" for item in coverage.unsatisfied)

    def test_unknown_product_is_unsatisfied(self) -> None:
        coverage = assess_query_coverage(
            plan(products=["Unobtainium Widget"]),
            make_bundle(["Unit price USD 310.00."]),
            StructuredResult(queried=True, facts=[price_fact()]),
        )
        assert not coverage.satisfied
        assert any(item["constraint"] == "product=Unobtainium Widget" for item in coverage.unsatisfied)

    def test_uncovered_entity_still_refused_by_decide_status(self) -> None:
        """The refusal path must still fire when the entity is genuinely absent."""
        bundle = make_bundle(["Acme Corp is based in the United States."])
        coverage = assess_query_coverage(
            plan(intent="compliance_check", suppliers=["Supplier C"]),
            bundle,
            StructuredResult(queried=True),
        )
        status = decide_status(
            grounding=None,
            conflicts=[],
            bundle=bundle,
            structured=StructuredResult(queried=True),
            generation_mode="llm",
            coverage=coverage,
        )
        assert status == "insufficient_evidence"


# ================================================ wording differences still match


class TestParaphraseMatching:
    """A name the corpus writes differently is still the same entity.

    Real notices write "Master Vendor Contingent Workforce Recruitment and
    Management Services" for the question's "master vendor contingent workforce
    recruitment service". Requiring the literal phrase refused questions whose
    evidence was present; requiring every word keeps genuinely absent entities
    unsatisfied.
    """

    def test_connective_words_and_plural_do_not_break_coverage(self) -> None:
        coverage = assess_query_coverage(
            plan(products=["master vendor contingent workforce recruitment service"]),
            make_bundle(
                ["FSCS569 Master Vendor Contingent Workforce Recruitment and Management Services."]
            ),
            StructuredResult(queried=False),
        )
        assert coverage.satisfied, coverage.as_dict()
        assert coverage.unsatisfied == []

    def test_partial_word_overlap_is_not_coverage(self) -> None:
        coverage = assess_query_coverage(
            plan(products=["Unobtainium Widget"]),
            make_bundle(["Unobtainium appears without the second word."]),
            StructuredResult(queried=False),
        )
        assert not coverage.satisfied
        assert any(item["constraint"] == "product=Unobtainium Widget" for item in coverage.unsatisfied)
