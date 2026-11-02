"""Temporal change handling: supersession is not a conflict.

The v2 failures showed the original 920.00 page being dropped while an amendment
answer still claimed to be a conflict report. These tests pin both halves: the
original value stays in the context, and a clean amendment chain is labelled a
supersession rather than a disagreement.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app.agents.verification import decide_status
from app.retrieval.analysis import PriceFact, detect_price_conflicts
from app.retrieval.context import CitationDraft, ContextBuilder
from app.retrieval.structured import StructuredResult


def fact(**overrides) -> PriceFact:
    base: dict = {
        "price_id": "prc-1",
        "supplier_id": "sup-1",
        "supplier_name": "Northwind Industrial Supplies Ltd",
        "contract_id": "con-1",
        "contract_number": "NS-2024-001",
        "product_id": "prd-1",
        "product_name": "INDUSTRIAL LAPTOP X200",
        "unit_price": 920.0,
        "currency": "USD",
        "minimum_quantity": None,
        "discount_percent": None,
        "payment_terms": None,
        "delivery_terms": None,
        "effective_date": date(2024, 1, 1),
        "expiry_date": date(2026, 12, 31),
        "amendment_ref": None,
        "document_id": "doc-original",
        "document_name": "supplier_a_master_contract.pdf",
        "page": 4,
        "is_synthetic": True,
    }
    base.update(overrides)
    return PriceFact(**base)


def amendment(**overrides) -> PriceFact:
    base = {
        "price_id": "prc-2",
        "unit_price": 874.0,
        "effective_date": date(2026, 1, 1),
        "amendment_ref": "Amendment 2",
        "document_id": "doc-amendment",
        "document_name": "supplier_a_amendment_2.pdf",
        "page": 1,
    }
    base.update(overrides)
    return fact(**base)


def test_amendment_chain_is_a_supersession_not_a_conflict() -> None:
    conflicts = detect_price_conflicts([fact(), amendment()])
    assert len(conflicts) == 1
    assert conflicts[0].kind == "price_supersession"
    assert "920.00" in conflicts[0].description
    assert "874.00" in conflicts[0].description
    assert "superseded" in conflicts[0].description


def test_conflicting_values_at_the_same_time_stay_a_conflict() -> None:
    conflicts = detect_price_conflicts(
        [
            fact(effective_date=date(2025, 1, 1), amendment_ref="Amendment 1"),
            amendment(effective_date=date(2025, 1, 1), unit_price=880.0, amendment_ref="Amendment 1"),
        ]
    )
    assert conflicts[0].kind == "price_conflict"


def test_supersession_does_not_make_the_answer_conflicting() -> None:
    conflicts = detect_price_conflicts([fact(), amendment()])
    status = decide_status(
        grounding=None,
        conflicts=conflicts,
        bundle=SimpleNamespace(blocks=[object()], citations=[]),
        structured=StructuredResult(queried=True),
    )
    assert status != "conflicting"


def chunk(name: str) -> SimpleNamespace:
    return SimpleNamespace(
        chunk_id=f"chk-{name}",
        document_id=f"doc-{name}",
        document_name=name,
        document_type="contract",
        page=1,
        section=None,
        clause=None,
        content=f"content for {name}",
        contextual_content=None,
        content_type="paragraph",
        access_level="internal",
        is_synthetic=True,
        version=1,
        effective_date=None,
        expiry_date=None,
        supplier_id=None,
        contract_id=None,
        parent_chunk_id=None,
        table_id=None,
        rank=1,
        fused_score=0.5,
        dense_score=0.5,
        sparse_score=0.5,
        rerank_score=0.5,
        matched_by=["dense"],
        tables=[],
    )


def test_context_reserves_room_for_structured_and_change_evidence() -> None:
    builder = ContextBuilder(max_chunks=3)
    extras = [
        (
            CitationDraft(chunk_id=None, document_id=None, document_name="structured", snippet=""),
            "STRUCTURED RESULT | total = 1",
            "structured",
        ),
        (
            CitationDraft(
                chunk_id="chk-original",
                document_id="doc-original",
                document_name="supplier_a_master_contract.pdf",
                page=4,
                snippet="unit price 920.00",
            ),
            "CONFLICTING SOURCE | original price 920.00",
            "paragraph",
        ),
    ]
    bundle = builder.build([chunk(f"chunk-{index}") for index in range(5)], extra_blocks=extras)
    texts = " ".join(block.text for block in bundle.blocks)
    assert "STRUCTURED RESULT" in texts
    assert "920.00" in texts
    assert len(bundle.blocks) <= 3
