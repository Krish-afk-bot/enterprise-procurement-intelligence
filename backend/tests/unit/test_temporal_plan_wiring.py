"""Query plans carry one temporal interpretation.

These tests run the rule-based planner only (no model, no database), which is the
path that always executes. They assert that the as-of date and the supporting
notes reach the plan, because the graph, SQL and vector retrievers all read it
from there.
"""

from __future__ import annotations

from datetime import date

from app.retrieval.query_understanding import understand_query_rule_based


def plan_for(question: str):
    return understand_query_rule_based(question)


def test_explicit_as_of_date() -> None:
    plan = plan_for("What was the contract status as of 31 March 2025?")
    assert plan.as_of == date(2025, 3, 31)
    assert plan.temporal_intent == "as_of"


def test_amendment_month_is_resolved_to_month_end() -> None:
    plan = plan_for("Which amendment was effective in June 2025?")
    assert plan.as_of == date(2025, 6, 30)


def test_original_terms_have_no_as_of() -> None:
    plan = plan_for("What were the original payment terms?")
    assert plan.as_of is None
    assert plan.temporal_intent == "original"


def test_terms_after_amendment_stay_unresolved() -> None:
    plan = plan_for("What terms changed after the second amendment?")
    assert plan.as_of is None
    assert plan.temporal_intent == "change"


def test_active_during_a_year_uses_year_end() -> None:
    plan = plan_for("Which supplier agreement was active during 2024?")
    assert plan.as_of == date(2024, 12, 31)
    assert plan.temporal_intent == "range"


def test_relative_reference_is_recorded() -> None:
    plan = plan_for("What changed last year?")
    assert plan.as_of is not None
    assert plan.temporal_intent == "as_of"


def test_non_temporal_question_is_not_filtered() -> None:
    plan = plan_for("Which supplier supplies laptops?")
    assert plan.as_of is None
    assert plan.temporal_intent == "none"
