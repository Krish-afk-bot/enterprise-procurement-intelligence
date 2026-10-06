"""Chunking (PRD s.25).

Four levels, applied in order:

1. **Structural** — sections/subsections/clauses come from the detected layout, so
   a chunk boundary lands where the document changes topic.
2. **Contract-aware** — clause groups (pricing, payment, delivery, definitions)
   are kept intact where they fit, because splitting a price table from its
   currency/term sentence destroys meaning.
3. **Token-aware** — oversized units are split on sentence boundaries with
   overlap, so nothing silently overflows the context window.
4. **Parent-child** — every leaf chunk records a parent unit id; retrieval uses
   the precise leaf but context building can expand to the parent section.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.config.settings import Settings
from app.ingestion.layout import DocumentStructure, StructureLine
from app.ingestion.tokens import count_tokens, split_sentences, truncate_to_tokens
from app.ingestion.types import ParsedDocument, ParsedTable
from app.observability.logging import get_logger

logger = get_logger(__name__)

CONTENT_PARAGRAPH = "paragraph"
CONTENT_CLAUSE = "clause"
CONTENT_TABLE = "table"
CONTENT_SECTION = "section"
CONTENT_HEADING = "heading"
CONTENT_PAGE_VISION = "page_vision"
CONTENT_LIST = "list"

_KEEP_TOGETHER_HINTS = (
    "pricing",
    "price",
    "payment",
    "delivery",
    "definitions",
    "minimum order",
    "discount",
    "renewal",
    "termination",
    "compliance",
    "confidentiality",
)


@dataclass(slots=True)
class ChunkDraft:
    """A chunk ready to be persisted (ids are assigned by the pipeline)."""

    content: str
    content_type: str = CONTENT_PARAGRAPH
    page_number: int | None = None
    section: str | None = None
    subsection: str | None = None
    clause: str | None = None
    token_count: int = 0
    parent_ref: str | None = None
    parent_content: str | None = None
    table_index: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_counts(self) -> ChunkDraft:
        self.token_count = count_tokens(self.content)
        return self


@dataclass(slots=True)
class _Unit:
    """A structural group of consecutive lines sharing a heading context."""

    section: str | None
    subsection: str | None
    lines: list[StructureLine]
    page_numbers: list[int]
    key: str

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines if line.text.strip())

    @property
    def first_page(self) -> int | None:
        return self.page_numbers[0] if self.page_numbers else None

    @property
    def keep_together(self) -> bool:
        lowered = f"{self.section or ''} {self.subsection or ''}".lower()
        return any(hint in lowered for hint in _KEEP_TOGETHER_HINTS)


def chunk_document(
    document: ParsedDocument,
    structure: DocumentStructure,
    settings: Settings,
) -> list[ChunkDraft]:
    drafts: list[ChunkDraft] = []
    units = _build_units(structure)

    for unit in units:
        parent_ref = f"unit:{unit.key}"
        parent_text = unit.text.strip()
        if not parent_text:
            continue
        unit_tokens = count_tokens(parent_text)

        if unit_tokens <= settings.chunk_target_tokens:
            drafts.append(
                ChunkDraft(
                    content=parent_text,
                    content_type=_content_type_for(unit),
                    page_number=unit.first_page,
                    section=unit.section,
                    subsection=unit.subsection,
                    clause=unit.lines[0].clause if unit.lines else None,
                    parent_ref=parent_ref,
                ).with_counts()
            )
            continue

        # Keep short, meaning-critical clause groups intact when possible.
        groups = _clause_groups(unit) if unit.keep_together else [unit.lines]
        if unit.keep_together:
            drafts.append(
                ChunkDraft(
                    content=truncate_to_tokens(parent_text, settings.chunk_max_tokens),
                    content_type=CONTENT_SECTION,
                    page_number=unit.first_page,
                    section=unit.section,
                    subsection=unit.subsection,
                    parent_ref=None,
                    metadata={"role": "parent_section", "unit_key": unit.key},
                ).with_counts()
            )

        for group in groups:
            group_text = "\n".join(line.text for line in group if line.text.strip()).strip()
            if not group_text:
                continue
            clause_label = next((line.clause for line in group if line.clause), None)
            for piece in _split_token_aware(
                group_text,
                settings.chunk_target_tokens,
                settings.chunk_max_tokens,
                settings.chunk_overlap_tokens,
            ):
                drafts.append(
                    ChunkDraft(
                        content=piece,
                        content_type=CONTENT_CLAUSE if clause_label else CONTENT_PARAGRAPH,
                        page_number=group[0].page_number if group else unit.first_page,
                        section=unit.section,
                        subsection=unit.subsection,
                        clause=clause_label,
                        parent_ref=parent_ref,
                        parent_content=truncate_to_tokens(parent_text, settings.chunk_max_tokens),
                    ).with_counts()
                )

    drafts.extend(_table_drafts(document, settings))
    return drafts


def _build_units(structure: DocumentStructure) -> list[_Unit]:
    units: list[_Unit] = []
    current: list[StructureLine] = []
    section: str | None = None
    subsection: str | None = None
    counter = 0

    def flush() -> None:
        nonlocal current, counter
        if not current:
            return
        units.append(
            _Unit(
                section=section,
                subsection=subsection,
                lines=list(current),
                page_numbers=[line.page_number for line in current],
                key=f"{counter:04d}",
            )
        )
        counter += 1
        current = []

    for line in structure.lines:
        if line.kind == "section":
            flush()
            section = line.text
            subsection = None
            current.append(line)
            continue
        if line.kind == "subsection":
            flush()
            subsection = line.text
            current.append(line)
            continue
        current.append(line)
    flush()
    return units


def _clause_groups(unit: _Unit) -> list[list[StructureLine]]:
    groups: list[list[StructureLine]] = []
    current: list[StructureLine] = []
    for line in unit.lines:
        starts_clause = line.clause is not None and line.kind in {"clause", "paragraph"}
        if starts_clause and current:
            groups.append(current)
            current = []
        current.append(line)
    if current:
        groups.append(current)
    return groups


def _split_token_aware(text: str, target_tokens: int, max_tokens: int, overlap_tokens: int) -> list[str]:
    if count_tokens(text) <= max_tokens:
        return [text]
    sentences = split_sentences(text) or [text]
    pieces: list[str] = []
    buffer: list[str] = []
    buffer_tokens = 0

    def flush() -> None:
        nonlocal buffer, buffer_tokens
        if buffer:
            pieces.append(" ".join(buffer).strip())
            # Overlap: keep the tail sentences to preserve cross-boundary context.
            overlap: list[str] = []
            overlap_count = 0
            for sentence in reversed(buffer):
                overlap.insert(0, sentence)
                overlap_count += count_tokens(sentence)
                if overlap_count >= overlap_tokens:
                    break
            buffer = overlap if overlap_count < buffer_tokens else []
            buffer_tokens = sum(count_tokens(s) for s in buffer)

    for sentence in sentences:
        tokens = count_tokens(sentence)
        if tokens > max_tokens:
            flush()
            pieces.append(truncate_to_tokens(sentence, max_tokens))
            buffer, buffer_tokens = [], 0
            continue
        if buffer_tokens + tokens > target_tokens and buffer:
            flush()
        buffer.append(sentence)
        buffer_tokens += tokens
    if buffer:
        pieces.append(" ".join(buffer).strip())
    return [piece for piece in pieces if piece.strip()]


def _table_drafts(document: ParsedDocument, settings: Settings) -> list[ChunkDraft]:
    drafts: list[ChunkDraft] = []
    for page in document.pages:
        for index, table in enumerate(page.tables):
            markdown = table.to_markdown()
            if not markdown.strip():
                continue
            caption = table.caption or f"Table {index + 1} on page {page.page_number}"
            content = f"{caption}\n{markdown}"
            drafts.append(
                ChunkDraft(
                    content=truncate_to_tokens(content, settings.chunk_max_tokens),
                    content_type=CONTENT_TABLE,
                    page_number=page.page_number,
                    section=None,
                    subsection=None,
                    clause=None,
                    table_index=index,
                    metadata={
                        "headers": table.headers,
                        "row_count": len(table.rows),
                        "column_count": len(table.headers),
                        "complexity_score": table.complexity_score,
                        "caption": caption,
                        "extraction_method": table.extraction_method,
                    },
                ).with_counts()
            )
    return drafts


def _content_type_for(unit: _Unit) -> str:
    if unit.lines and all(line.kind in {"heading", "section"} for line in unit.lines):
        return CONTENT_HEADING
    if any(line.clause for line in unit.lines):
        return CONTENT_CLAUSE
    if _looks_like_list(unit.text):
        return CONTENT_LIST
    return CONTENT_PARAGRAPH


def _looks_like_list(text: str) -> bool:
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 3:
        return False
    bullets = sum(
        1
        for line in lines
        if line.strip()[:2] in {"- ", "* ", "• "} or line.strip()[:3].rstrip(".").isdigit()
    )
    return bullets >= len(lines) * 0.6


__all__ = [
    "CONTENT_CLAUSE",
    "CONTENT_HEADING",
    "CONTENT_LIST",
    "CONTENT_PARAGRAPH",
    "CONTENT_PAGE_VISION",
    "CONTENT_SECTION",
    "CONTENT_TABLE",
    "ChunkDraft",
    "chunk_document",
    "ParsedTable",
]
