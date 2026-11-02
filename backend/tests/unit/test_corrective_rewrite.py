"""The corrective loop must rewrite from the named coverage gap."""

from __future__ import annotations

from app.agents.nodes import _missing_constraint_terms
from app.retrieval.query_understanding import Intent, QueryPlan


def _plan(query: str = "What is the price?") -> QueryPlan:
    return QueryPlan(query=query, intent=Intent.PRICE_LOOKUP)


def test_rewrite_uses_the_unsatisfied_supplier_and_product() -> None:
    state = {
        "answerability": {
            "constraints": [
                {"kind": "supplier", "constraint": "supplier=Helios Technology Partners Inc", "satisfied": False},
                {"kind": "product", "constraint": "product=Enterprise Monitor 27 inch", "satisfied": False},
            ]
        }
    }
    terms = _missing_constraint_terms(state, _plan(), 1)
    assert "Helios Technology Partners Inc" in terms
    assert "Enterprise Monitor 27 inch" in terms


def test_rewrite_ignores_constraints_that_are_already_satisfied() -> None:
    state = {
        "answerability": {
            "constraints": [
                {"kind": "supplier", "constraint": "supplier=Northwind", "satisfied": True},
                {"kind": "period", "constraint": "period=2025-01-01 to 2025-12-31", "satisfied": False},
            ]
        }
    }
    terms = _missing_constraint_terms(state, _plan("What was the 2025 total?"), 1)
    assert "Northwind" not in terms
    # The year is already in the query; the fallback keeps the rewrite moving.
    assert terms


def test_rewrite_falls_back_to_intent_terms_when_no_constraint_is_recorded() -> None:
    plan = QueryPlan(query="When did the amendment take effect?", intent=Intent.TEMPORAL_CHANGE)
    terms = _missing_constraint_terms({"answerability": {"constraints": []}}, plan, 1)
    assert "amendment" in terms
    assert "superseded" in terms
