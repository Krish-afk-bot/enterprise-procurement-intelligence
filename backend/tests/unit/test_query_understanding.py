"""Unit tests for app.retrieval.query_understanding — rule-based query planner.

Pure logic tests: no database, no LLM, no HTTP.
All vocabulary is constructed in-memory.
"""

from __future__ import annotations

import pytest

from app.retrieval.query_understanding import (
    Intent,
    QueryPlan,
    TenantVocabulary,
    keyword_terms,
    understand_query_rule_based,
)


# ------------------------------------------------------------------ helpers

def make_vocab(
    suppliers: list[tuple[str, str]] | None = None,
    products: list[tuple[str, str, str]] | None = None,
    contracts: list[tuple[str, str]] | None = None,
) -> TenantVocabulary:
    v = TenantVocabulary(
        suppliers=suppliers or [],
        products=products or [],
        contracts=contracts or [],
    )
    return v


# ------------------------------------------------------------------ keyword_terms

class TestKeywordTerms:
    def test_empty_query_returns_empty(self) -> None:
        assert keyword_terms("") == []

    def test_stopwords_excluded(self) -> None:
        terms = keyword_terms("what is the price of this item")
        assert "what" not in terms
        assert "the" not in terms
        assert "is" not in terms

    def test_meaningful_tokens_included(self) -> None:
        terms = keyword_terms("Compare prices for Widget A and Widget B")
        assert "Compare" in terms or "compare" in terms.lower() or any("ompare" in t for t in terms)
        assert "Widget" in terms or any("idget" in t for t in terms)

    def test_short_tokens_excluded(self) -> None:
        # keyword_terms uses regex `[A-Za-z][A-Za-z0-9\-]{2,}` — single/double letter words excluded
        terms = keyword_terms("A is to B")
        assert "A" not in terms
        assert "B" not in terms

    def test_limit_respected(self) -> None:
        long_query = " ".join([f"keyword{i}" for i in range(50)])
        terms = keyword_terms(long_query, limit=5)
        assert len(terms) <= 5

    def test_hyphenated_terms_included(self) -> None:
        terms = keyword_terms("What is the year-to-date spend on procurement?")
        assert any("year" in t.lower() or "date" in t.lower() or "procurement" in t.lower() for t in terms)

    def test_numeric_terms_included(self) -> None:
        terms = keyword_terms("Contract ABC123 pricing terms")
        assert any("ABC123" in t or "abc" in t.lower() for t in terms)


# ------------------------------------------------------------------ understand_query_rule_based

class TestIntentDetection:
    def test_price_lookup_intent(self) -> None:
        plan = understand_query_rule_based("What is the unit price for Widget A?")
        assert plan.intent == Intent.PRICE_LOOKUP

    def test_comparison_intent(self) -> None:
        plan = understand_query_rule_based("Compare Supplier Alpha vs Supplier Beta prices")
        assert plan.intent == Intent.COMPARISON

    def test_temporal_intent_amendment(self) -> None:
        plan = understand_query_rule_based("What is the price after the latest amendment?")
        assert plan.intent in (Intent.TEMPORAL_CHANGE, Intent.PRICE_LOOKUP)
        assert plan.requires_temporal is True

    def test_aggregation_intent_lowest(self) -> None:
        plan = understand_query_rule_based("What is the lowest price in 2025?")
        assert plan.intent in (Intent.AGGREGATION, Intent.PRICE_LOOKUP)

    def test_contract_terms_intent(self) -> None:
        plan = understand_query_rule_based("What are the payment terms in the contract?")
        assert plan.intent == Intent.CONTRACT_TERMS

    def test_general_fallback_intent(self) -> None:
        plan = understand_query_rule_based("Hello world")
        assert plan.intent == Intent.GENERAL

    def test_method_is_rule_based(self) -> None:
        plan = understand_query_rule_based("some query")
        assert plan.method == "rule_based"


class TestEntityLinking:
    def test_supplier_linked_by_name(self) -> None:
        vocab = make_vocab(suppliers=[("sup_001", "Acme Corp")])
        plan = understand_query_rule_based("What is the price from Acme Corp?", vocab)
        assert "sup_001" in plan.supplier_ids
        assert "Acme Corp" in plan.suppliers

    def test_supplier_not_linked_when_absent(self) -> None:
        vocab = make_vocab(suppliers=[("sup_001", "Acme Corp")])
        plan = understand_query_rule_based("What are the standard lead times?", vocab)
        assert plan.supplier_ids == []

    def test_product_linked_by_name(self) -> None:
        vocab = make_vocab(products=[("prod_001", "Industrial Pump", "SKU-IPX")])
        plan = understand_query_rule_based("Show pricing for Industrial Pump", vocab)
        assert "prod_001" in plan.product_ids
        assert "Industrial Pump" in plan.products

    def test_product_linked_by_sku(self) -> None:
        vocab = make_vocab(products=[("prod_001", "Industrial Pump", "SKU-IPX")])
        plan = understand_query_rule_based("What is the price for SKU-IPX?", vocab)
        assert "prod_001" in plan.product_ids

    def test_contract_linked_by_number(self) -> None:
        vocab = make_vocab(contracts=[("con_001", "MSA-2024-001")])
        plan = understand_query_rule_based("What are the terms in MSA-2024-001?", vocab)
        assert "con_001" in plan.contract_ids
        assert "MSA-2024-001" in plan.contract_numbers

    def test_empty_vocabulary_no_entities(self) -> None:
        plan = understand_query_rule_based("What is the price for Widget A?", TenantVocabulary())
        assert plan.entities == []
        assert plan.supplier_ids == []

    def test_multiple_suppliers_linked(self) -> None:
        vocab = make_vocab(
            suppliers=[("sup_001", "Acme Corp"), ("sup_002", "Beta Industries")]
        )
        plan = understand_query_rule_based(
            "Compare prices between Acme Corp and Beta Industries", vocab
        )
        assert "sup_001" in plan.supplier_ids
        assert "sup_002" in plan.supplier_ids


class TestRequiresFlags:
    def test_comparison_query_sets_requires_comparison(self) -> None:
        plan = understand_query_rule_based("Compare Supplier A vs Supplier B")
        assert plan.requires_comparison is True

    def test_temporal_query_sets_requires_temporal(self) -> None:
        plan = understand_query_rule_based("What is the current price after the amendment?")
        assert plan.requires_temporal is True

    def test_simple_price_query_no_comparison_flag(self) -> None:
        plan = understand_query_rule_based("What is the unit price for item X?")
        assert plan.requires_comparison is False


class TestYearExtraction:
    def test_year_extracted(self) -> None:
        plan = understand_query_rule_based("What were the prices in 2024?")
        assert plan.year == 2024

    def test_no_year_when_absent(self) -> None:
        plan = understand_query_rule_based("What is the unit price?")
        assert plan.year is None


class TestQueryPlanContract:
    def test_as_dict_is_serialisable(self) -> None:
        plan = understand_query_rule_based("What is the unit price for Widget?")
        d = plan.as_dict()
        assert isinstance(d, dict)
        assert "intent" in d
        assert "query" in d

    def test_query_preserved(self) -> None:
        q = "How much does the XL Widget cost per unit?"
        plan = understand_query_rule_based(q)
        assert plan.query == q
