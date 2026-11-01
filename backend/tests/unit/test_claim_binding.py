"""Tests for per-claim evidence binding.

The important regression is the second case: a number that exists in the
evidence, but for a different supplier, must not support the claim that attaches
it to the wrong supplier.
"""

from __future__ import annotations

import pytest

from app.agents.claim_binding import (
    EvidencePassage,
    bind_claims,
    normalise_number,
    passages_from_blocks,
)


def _passages() -> list[EvidencePassage]:
    return [
        EvidencePassage(
            ref=1,
            text=(
                "Northwind Industrial Supplies Ltd. Unit price for the Industrial Laptop X200 "
                "is USD 874.00 per unit, effective 2026-01-01."
            ),
            document_name="supplier_a_amendment_2.pdf",
            supplier="Northwind Industrial Supplies Ltd",
            product="INDUSTRIAL LAPTOP X200",
            effective_date="2026-01-01",
        ),
        EvidencePassage(
            ref=2,
            text=(
                "Helios Technology Partners Inc. Unit price for the Industrial Laptop X200 "
                "is USD 895.00 per unit, effective 2024-01-01."
            ),
            document_name="supplier_b_supply_agreement.pdf",
            supplier="Helios Technology Partners Inc",
            product="INDUSTRIAL LAPTOP X200",
            effective_date="2024-01-01",
        ),
    ]


ENTITIES = [
    "Northwind Industrial Supplies Ltd",
    "Helios Technology Partners Inc",
    "Orion Components Co",
    "INDUSTRIAL LAPTOP X200",
]


def test_correct_entity_number_and_date_bind() -> None:
    checks = bind_claims(
        ["The Industrial Laptop X200 unit price from Northwind is USD 874.00 effective 2026-01-01."],
        _passages(),
        known_entities=ENTITIES,
    )
    assert len(checks) == 1
    assert checks[0].supported is True
    assert checks[0].evidence_refs == [1]


def test_number_for_the_wrong_supplier_must_fail() -> None:
    """895.00 exists in the evidence, but only under Helios — not Northwind."""
    checks = bind_claims(
        ["The Industrial Laptop X200 unit price from Northwind is USD 895.00."],
        _passages(),
        known_entities=ENTITIES,
    )
    assert checks[0].supported is False
    assert checks[0].missing_numbers == ["895"]
    assert "Northwind" in checks[0].reason or "northwind" in checks[0].reason.lower()


def test_number_for_the_wrong_period_must_fail() -> None:
    checks = bind_claims(
        ["Northwind's Industrial Laptop X200 price of USD 874.00 was effective 2020-01-01."],
        _passages(),
        known_entities=ENTITIES,
    )
    assert checks[0].supported is False
    assert "2020" in checks[0].missing_numbers


def test_comparison_with_two_clauses_binds_each_side() -> None:
    checks = bind_claims(
        [
            "Northwind offers the Industrial Laptop X200 at USD 874.00 while "
            "Helios offers it at USD 895.00."
        ],
        _passages(),
        known_entities=ENTITIES,
    )
    assert checks[0].supported is True
    assert checks[0].evidence_refs == [1, 2]


def test_comparison_with_numbers_swapped_between_suppliers_fails() -> None:
    checks = bind_claims(
        [
            "Northwind offers the Industrial Laptop X200 at USD 895.00 while "
            "Helios offers it at USD 874.00."
        ],
        _passages(),
        known_entities=ENTITIES,
    )
    assert checks[0].supported is False


def test_claim_without_numbers_falls_back_to_lexical_overlap() -> None:
    supported = bind_claims(
        ["Northwind Industrial Supplies holds an ISO 9001 certificate."],
        [
            EvidencePassage(
                ref=1,
                text="Northwind Industrial Supplies holds ISO 9001 certification.",
                supplier="Northwind Industrial Supplies Ltd",
            )
        ],
        known_entities=ENTITIES,
    )
    unsupported = bind_claims(
        ["Orion Components holds a valid ISO 9001 certificate."],
        [
            EvidencePassage(
                ref=1,
                text="Northwind Industrial Supplies holds ISO 9001 certification.",
                supplier="Northwind Industrial Supplies Ltd",
            )
        ],
        known_entities=ENTITIES,
    )
    assert supported[0].supported is True
    assert unsupported[0].supported is False


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("874.00", "874"), ("1,790,000", "1790000"), ("0.50", "0.5"), ("2026", "2026")],
)
def test_normalise_number(raw: str, expected: str) -> None:
    assert normalise_number(raw) == expected


def test_passages_from_blocks_includes_structured_rows() -> None:
    class Fact:
        supplier_name = "Northwind Industrial Supplies Ltd"
        product_name = "INDUSTRIAL LAPTOP X200"
        unit_price = 874.0
        currency = "USD"
        effective_date = "2026-01-01"
        expiry_date = "2026-12-31"
        document_name = "supplier_a_amendment_2.pdf"

    passages, entities = passages_from_blocks(
        [{"text": "document block", "citation": {"document_name": "doc.pdf", "metadata": {}}}],
        structured_facts=[Fact()],
    )
    assert [passage.kind for passage in passages] == ["document", "structured_fact"]
    assert passages[1].supplier == "Northwind Industrial Supplies Ltd"
    assert "Northwind Industrial Supplies Ltd" in entities
    assert "INDUSTRIAL LAPTOP X200" in entities
