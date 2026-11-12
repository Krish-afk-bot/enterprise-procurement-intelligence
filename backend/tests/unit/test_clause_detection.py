"""Clause detection in prose.

Contract bodies usually write "3.2 The Supplier shall…" inside a paragraph rather
than putting the number on its own line. Detection used to require a short line,
so prose documents produced no clauses at all — and the graph clause layer had
nothing to build from. These tests pin the prose case and the guard against
mistaking a year or a list number for a clause.
"""

from __future__ import annotations

from app.config.settings import Settings
from app.ingestion.chunking import CONTENT_CLAUSE, chunk_document
from app.ingestion.layout import detect_structure
from app.ingestion.types import ParsedDocument, ParsedPage

LONG = (
    "3.2 The Supplier shall deliver the goods within thirty (30) days of acceptance, "
    "and shall replace any item that fails inspection at no additional cost to the Buyer."
)


def document(*paragraphs: str) -> ParsedDocument:
    text = "\n\n".join(paragraphs)
    return ParsedDocument(pages=[ParsedPage(page_number=1, text=text)])


def test_inline_clause_in_a_long_paragraph_is_detected() -> None:
    structure = detect_structure(document(LONG))
    clause_lines = [line for line in structure.lines if line.clause]
    assert clause_lines, "no clause detected in a numbered prose paragraph"
    assert clause_lines[0].clause == "3.2"
    assert clause_lines[0].kind == "clause"


def test_keyword_clause_is_detected() -> None:
    text = (
        "Clause 7.1 The Buyer must pay each undisputed invoice within forty-five days "
        "of receipt, and may withhold payment for any invoice it disputes in writing."
    )
    structure = detect_structure(document(text))
    assert any(line.clause and line.clause.lower().startswith("clause 7.1") for line in structure.lines)


def test_a_year_at_the_start_is_not_a_clause() -> None:
    text = (
        "2025 was the second year of the framework and the volumes recorded in the "
        "schedule reflect the awards made during that period across all lots."
    )
    structure = detect_structure(document(text))
    assert not any(line.clause for line in structure.lines)


def test_section_heading_in_prose_is_not_a_clause() -> None:
    text = (
        "Section 5 This section explains how the buyer will evaluate tenders, including the "
        "weighting applied to price, quality and social value responses."
    )
    structure = detect_structure(document(text))
    assert not any(line.clause for line in structure.lines)


def test_list_number_is_not_treated_as_a_clause() -> None:
    structure = detect_structure(document("1. The Buyer may request samples before award."))
    # A single number is a list item, not a dotted clause reference.
    assert not any(line.clause for line in structure.lines)


def test_multi_clause_prose_is_chunked_per_clause(settings: Settings) -> None:
    small = settings.model_copy(
        update={"chunk_target_tokens": 20, "chunk_max_tokens": 60, "chunk_overlap_tokens": 5}
    )
    text = "\n\n".join(
        [
            "3.2 The Supplier shall deliver the goods within thirty days of acceptance and shall "
            "replace any item that fails inspection at no additional cost to the Buyer.",
            "4.1 The Buyer must pay each undisputed invoice within forty-five days of receipt of a "
            "valid invoice, and may withhold payment for any invoice it disputes in writing.",
        ]
    )
    doc = document(text)
    structure = detect_structure(doc)
    drafts = chunk_document(doc, structure, small)

    clauses = {draft.clause for draft in drafts if draft.clause}
    assert {"3.2", "4.1"} <= clauses, f"expected both clauses, got {clauses}"
    labelled = [draft for draft in drafts if draft.clause]
    assert all(draft.content_type == CONTENT_CLAUSE for draft in labelled)
