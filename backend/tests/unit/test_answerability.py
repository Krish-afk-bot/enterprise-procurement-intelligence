"""Answerability regressions for Phase 2 item 2.

The corpus can return evidence and still contain nothing for the period,
currency or attribute the question names. These tests pin the three gaps that
produced confidently wrong answers in the v2 baseline:

* "2030 unit price" answered with a 2026 figure;
* "price expressed in euros" answered in USD;
* "annual rebate percentage" answered although no rebate exists.
"""

from __future__ import annotations

from app.agents.verification import assess_query_coverage
from app.retrieval.analysis import PriceFact
from app.retrieval.structured import StructuredResult


def _fact(**overrides) -> PriceFact:
    base: dict = {
        "price_id": "prc-1",
        "supplier_id": "sup-1",
        "supplier_name": "Northwind Industrial Supplies Ltd",
        "contract_id": "con-1",
        "contract_number": "NS-2024-001",
        "product_id": "prd-1",
        "product_name": "INDUSTRIAL LAPTOP X200",
        "unit_price": 874.0,
        "currency": "USD",
        "minimum_quantity": None,
        "discount_percent": None,
        "payment_terms": None,
        "delivery_terms": None,
        "effective_date": "2026-01-01",
        "expiry_date": "2026-12-31",
        "amendment_ref": "Amendment 2",
        "document_id": "doc-1",
        "document_name": "supplier_a_amendment_2.pdf",
        "page": 1,
        "is_synthetic": True,
    }
    base.update(overrides)
    return PriceFact(**base)


def _structured(*facts: PriceFact) -> StructuredResult:
    return StructuredResult(queried=True, facts=list(facts), purpose="price_lookup")


def _plan(question: str, **overrides) -> dict:
    base = {
        "query": question,
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


def test_future_period_in_question_is_unsatisfied_by_in_force_row() -> None:
    question = "What is the 2030 unit price for the Industrial Laptop X200?"
    coverage = assess_query_coverage(
        _plan(question),
        None,
        _structured(_fact()),
        texts=["The unit price for Industrial Laptop X200 is USD 874.00 effective 2026-01-01."],
        question=question,
    )
    period = next(item for item in coverage.constraints if item["kind"] == "period")
    assert period["satisfied"] is False
    assert coverage.satisfied is False


def test_period_that_evidence_covers_is_satisfied() -> None:
    question = "What was the total 2025 award value with Helios?"
    coverage = assess_query_coverage(
        _plan(question, intent="aggregation"),
        None,
        StructuredResult(queried=True),
        texts=["procurement_value_2025 {'year': 2025} = 1790000.0"],
        question=question,
    )
    period = next(item for item in coverage.constraints if item["kind"] == "period")
    assert period["satisfied"] is True


def test_identifier_year_is_not_treated_as_a_requested_period() -> None:
    question = "What value is recorded for award AWD-2025-A02?"
    coverage = assess_query_coverage(
        _plan(question, intent="aggregation"),
        None,
        StructuredResult(queried=True),
        texts=["AWD-2025-A02 450000"],
        question=question,
    )
    assert not [item for item in coverage.constraints if item["kind"] == "period"]


def test_requested_currency_must_exist_in_the_evidence() -> None:
    question = "What is the unit price for the Industrial Laptop X200 expressed in euros?"
    coverage = assess_query_coverage(
        _plan(question),
        None,
        _structured(_fact()),
        texts=["The unit price is USD 874.00."],
        question=question,
    )
    currency = next(item for item in coverage.constraints if item["kind"] == "currency")
    assert currency["satisfied"] is False


def test_requested_currency_present_is_satisfied() -> None:
    question = "What is the unit price in EUR?"
    coverage = assess_query_coverage(
        _plan(question),
        None,
        _structured(_fact(currency="EUR")),
        texts=["The unit price is EUR 810.00."],
        question=question,
    )
    currency = next(item for item in coverage.constraints if item["kind"] == "currency")
    assert currency["satisfied"] is True


def test_absent_attribute_is_unsatisfied() -> None:
    question = "What annual rebate percentage does Northwind offer?"
    coverage = assess_query_coverage(
        _plan(question),
        None,
        _structured(_fact()),
        texts=["Unit price USD 874.00; minimum order quantity 10 units."],
        question=question,
    )
    attribute = next(item for item in coverage.constraints if item["kind"] == "attribute")
    assert attribute["satisfied"] is False


def test_present_attribute_is_satisfied() -> None:
    question = "What warranty does the laptop carry?"
    coverage = assess_query_coverage(
        _plan(question, intent="contract_terms"),
        None,
        _structured(_fact()),
        texts=["The warranty period is 24 months."],
        question=question,
    )
    attribute = next(item for item in coverage.constraints if item["kind"] == "attribute")
    assert attribute["satisfied"] is True
