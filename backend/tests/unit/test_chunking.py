"""Unit tests for app.ingestion.chunking — structural document chunking.

Pure logic tests: no I/O, no database, no model dependencies.
Tests cover chunk_document behaviour against synthetic ParsedDocument /
DocumentStructure fixtures.
"""

from __future__ import annotations

import pytest

from app.config.settings import Settings
from app.ingestion.chunking import (
    CONTENT_CLAUSE,
    CONTENT_PARAGRAPH,
    CONTENT_SECTION,
    CONTENT_TABLE,
    ChunkDraft,
    chunk_document,
)
from app.ingestion.layout import DocumentStructure, StructureLine, detect_structure
from app.ingestion.tokens import count_tokens
from app.ingestion.types import ParsedDocument, ParsedPage, ParsedTable, TextBlock


# ------------------------------------------------------------------ fixtures


@pytest.fixture()
def minimal_settings(settings: Settings) -> Settings:
    """Settings with small token limits to make tests predictable."""
    return settings.model_copy(
        update={
            "chunk_target_tokens": 50,
            "chunk_max_tokens": 120,
            "chunk_overlap_tokens": 10,
        }
    )


def make_simple_document(pages_text: list[str]) -> ParsedDocument:
    """Build a ParsedDocument with plain text pages (no block-level metadata)."""
    pages = [
        ParsedPage(page_number=i + 1, text=text)
        for i, text in enumerate(pages_text)
    ]
    return ParsedDocument(pages=pages)


def make_structure(*lines: tuple[str, int, str | None, str | None]) -> DocumentStructure:
    """Build a DocumentStructure from (text, page, section, subsection) tuples."""
    structure = DocumentStructure()
    for order, (text, page, section, subsection) in enumerate(lines):
        structure.lines.append(
            StructureLine(
                text=text,
                page_number=page,
                section=section,
                subsection=subsection,
                kind="paragraph",
                order=order,
            )
        )
    return structure


# ------------------------------------------------------------------ ChunkDraft.with_counts


class TestChunkDraftWithCounts:
    def test_token_count_populated(self) -> None:
        draft = ChunkDraft(content="Hello world this is a test sentence.").with_counts()
        assert draft.token_count > 0

    def test_empty_content_token_count(self) -> None:
        draft = ChunkDraft(content="").with_counts()
        assert draft.token_count == 0

    def test_longer_content_higher_count(self) -> None:
        short = ChunkDraft(content="Hello.").with_counts()
        long = ChunkDraft(content="Hello world. " * 30).with_counts()
        assert long.token_count > short.token_count


# ------------------------------------------------------------------ chunk_document


class TestChunkDocumentBasic:
    def test_empty_document_returns_no_content_chunks(
        self, minimal_settings: Settings
    ) -> None:
        doc = make_simple_document([""])
        structure = detect_structure(doc)
        drafts = chunk_document(doc, structure, minimal_settings)
        # No meaningful text → only possibly table drafts (none here)
        assert all(d.content_type == CONTENT_TABLE for d in drafts) or len(drafts) == 0

    def test_single_short_page_one_chunk(self, minimal_settings: Settings) -> None:
        doc = make_simple_document(["The unit price is $92 per item."])
        structure = detect_structure(doc)
        drafts = chunk_document(doc, structure, minimal_settings)
        assert len(drafts) >= 1

    def test_all_chunks_have_content(self, minimal_settings: Settings) -> None:
        doc = make_simple_document(
            ["Pricing section. The price is $92 per unit. Effective from January 2026."]
        )
        structure = detect_structure(doc)
        drafts = chunk_document(doc, structure, minimal_settings)
        for draft in drafts:
            assert draft.content.strip()

    def test_token_counts_populated(self, minimal_settings: Settings) -> None:
        doc = make_simple_document(["The price is $92. This is a contract clause."])
        structure = detect_structure(doc)
        drafts = chunk_document(doc, structure, minimal_settings)
        for draft in drafts:
            assert draft.token_count > 0

    def test_page_number_assigned(self, minimal_settings: Settings) -> None:
        doc = make_simple_document(["Page one text.", "Page two text."])
        structure = detect_structure(doc)
        drafts = chunk_document(doc, structure, minimal_settings)
        page_numbers = {d.page_number for d in drafts if d.content_type != CONTENT_TABLE}
        assert page_numbers  # at least one chunk has a page number


class TestChunkDocumentLargeText:
    def test_oversized_text_produces_multiple_chunks(
        self, minimal_settings: Settings
    ) -> None:
        # Each sentence is ~10 tokens; 12 sentences × 10 = ~120 tokens > target (50)
        sentences = " ".join(
            [f"Sentence number {i} contains some contract pricing information." for i in range(12)]
        )
        doc = make_simple_document([sentences])
        structure = detect_structure(doc)
        drafts = chunk_document(doc, structure, minimal_settings)
        assert len(drafts) >= 2

    def test_max_tokens_not_exceeded(self, minimal_settings: Settings) -> None:
        sentences = " ".join(
            [f"The vendor agrees to supply item {i} at the agreed rate." for i in range(20)]
        )
        doc = make_simple_document([sentences])
        structure = detect_structure(doc)
        drafts = chunk_document(doc, structure, minimal_settings)
        for draft in drafts:
            if draft.content_type != CONTENT_TABLE:
                assert draft.token_count <= minimal_settings.chunk_max_tokens * 1.2  # 20% tolerance


class TestChunkDocumentStructure:
    def test_section_label_propagated(self, minimal_settings: Settings) -> None:
        doc = make_simple_document(["Pricing\n\nThe price is $92 per unit."])
        structure = detect_structure(doc)
        drafts = chunk_document(doc, structure, minimal_settings)
        sections = [d.section for d in drafts if d.section]
        assert len(sections) >= 1

    def test_parent_ref_set_on_split_chunks(self, minimal_settings: Settings) -> None:
        long_text = " ".join(
            [f"Clause {i}: The supplier will deliver within 30 days." for i in range(10)]
        )
        doc = make_simple_document([long_text])
        structure = detect_structure(doc)
        drafts = chunk_document(doc, structure, minimal_settings)
        # At least one split chunk should carry a parent_ref
        refs = [d.parent_ref for d in drafts if d.parent_ref]
        assert len(refs) >= 1


class TestChunkDocumentTables:
    def test_table_produces_table_chunk(self, minimal_settings: Settings) -> None:
        # _table_drafts reads from page.tables, not document.tables
        table = ParsedTable(
            headers=["Supplier", "SKU", "Unit Price"],
            rows=[
                ["Acme Corp", "SKU-001", "$92.00"],
                ["Beta Ltd", "SKU-002", "$88.50"],
            ],
            caption="Table 1: Pricing Schedule",
        )
        page = ParsedPage(page_number=1, text="", tables=[table])
        doc = ParsedDocument(pages=[page])
        structure = detect_structure(doc)
        drafts = chunk_document(doc, structure, minimal_settings)
        table_drafts = [d for d in drafts if d.content_type == CONTENT_TABLE]
        assert len(table_drafts) >= 1

    def test_table_chunk_contains_header(self, minimal_settings: Settings) -> None:
        table = ParsedTable(
            headers=["Item", "Price"],
            rows=[["Widget A", "$10"], ["Widget B", "$20"]],
        )
        page = ParsedPage(page_number=1, text="", tables=[table])
        doc = ParsedDocument(pages=[page])
        structure = detect_structure(doc)
        drafts = chunk_document(doc, structure, minimal_settings)
        table_drafts = [d for d in drafts if d.content_type == CONTENT_TABLE]
        assert any("Item" in d.content or "Price" in d.content for d in table_drafts)

    def test_empty_table_not_in_chunks(self, minimal_settings: Settings) -> None:
        table = ParsedTable(headers=[], rows=[])
        page = ParsedPage(page_number=1, text="", tables=[table])
        doc = ParsedDocument(pages=[page])
        structure = detect_structure(doc)
        drafts = chunk_document(doc, structure, minimal_settings)
        for draft in drafts:
            assert draft.content.strip()  # no empty content
