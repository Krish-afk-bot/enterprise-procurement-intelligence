"""Regression tests for entity-name resolution in query understanding (Phase 2).

The LLM understanding pass returns entity mentions in whatever spelling it
likes. Those mentions must be resolved against what the corpus records and
de-duplicated by entity id, otherwise the plan carries two constraints for one
supplier/product and the answerability check refuses a question the evidence
answers (the dominant v2 failure bucket).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.retrieval.query_understanding import (
    LLMUnderstanding,
    TenantVocabulary,
    _resolve_product,
    _resolve_supplier,
    understand_query,
)

SUPPLIER_ID = "sup-1"
SUPPLIER_NAME = "Northwind Industrial Supplies Ltd"
PRODUCT_ID = "prd-1"
PRODUCT_NAME = 'Enterprise Monitor 27"'


def vocabulary() -> TenantVocabulary:
    vocab = TenantVocabulary()
    vocab.suppliers = [(SUPPLIER_ID, SUPPLIER_NAME)]
    vocab.supplier_aliases = {"supplier a": (SUPPLIER_ID, SUPPLIER_NAME)}
    vocab.products = [(PRODUCT_ID, PRODUCT_NAME, "MON-27")]
    return vocab


class TestResolveSupplier:
    def test_short_form_resolves_to_recorded_supplier(self) -> None:
        assert _resolve_supplier("Northwind", vocabulary()) == (SUPPLIER_ID, SUPPLIER_NAME)

    def test_recorded_alias_resolves(self) -> None:
        assert _resolve_supplier("Supplier A", vocabulary()) == (SUPPLIER_ID, SUPPLIER_NAME)

    def test_unknown_supplier_does_not_resolve(self) -> None:
        assert _resolve_supplier("Supplier C", vocabulary()) is None


class TestResolveProduct:
    def test_size_spelling_variant_resolves(self) -> None:
        assert _resolve_product("Enterprise Monitor 27 inch", vocabulary()) == (PRODUCT_ID, PRODUCT_NAME)

    def test_sku_resolves(self) -> None:
        assert _resolve_product("MON-27 bulk order", vocabulary()) == (PRODUCT_ID, PRODUCT_NAME)

    def test_unknown_product_does_not_resolve(self) -> None:
        assert _resolve_product("Unobtainium Widget", vocabulary()) is None


class _StubRouter:
    """Minimal stand-in for ModelRouter.generate_structured."""

    def __init__(self, understanding: LLMUnderstanding) -> None:
        self._understanding = understanding

    async def generate_structured(self, messages, schema, *, task=None):  # noqa: ANN001, ANN002
        return self._understanding


@pytest.mark.asyncio
async def test_llm_name_variants_are_deduplicated_by_entity() -> None:
    understanding = LLMUnderstanding(
        intent="price_lookup",
        suppliers=["Northwind"],
        products=["Enterprise Monitor 27 inch"],
    )
    with patch(
        "app.retrieval.query_understanding.load_vocabulary",
        return_value=vocabulary(),
    ):
        plan = await understand_query(
            'What is the unit price of the Enterprise Monitor 27" from Northwind?',
            session=object(),  # truthy; load_vocabulary is patched
            tenant_id="tenant-1",
            router=_StubRouter(understanding),
        )

    assert plan.supplier_ids == [SUPPLIER_ID]
    assert plan.product_ids == [PRODUCT_ID]
    # One constraint per entity: no duplicate spelling variant is left behind.
    assert plan.suppliers == [SUPPLIER_NAME]
    assert plan.products == [PRODUCT_NAME]


@pytest.mark.asyncio
async def test_unknown_llm_entity_is_kept_as_a_constraint() -> None:
    """A mention the corpus does not record stays visible, so absence is detectable."""
    understanding = LLMUnderstanding(intent="compliance_check", suppliers=["Supplier C"])
    with patch(
        "app.retrieval.query_understanding.load_vocabulary",
        return_value=vocabulary(),
    ):
        plan = await understand_query(
            "Is Supplier C compliant?",
            session=object(),
            tenant_id="tenant-1",
            router=_StubRouter(understanding),
        )

    assert "Supplier C" in plan.suppliers
    assert plan.supplier_ids == []
