"""Document structure detection.

Builds the Document → Page → Section → Subsection → Clause hierarchy that
chunking and citation rely on. Headings come from font-size/style signals;
clauses from numbered-clause patterns and common contract section keywords.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.ingestion.types import ParsedDocument, ParsedPage, TextBlock

CLAUSE_PATTERNS = [
    re.compile(
        r"^(?P<label>(?:section|article|clause)\s+\d+(?:\.\d+)*)\s*[:.\-]?\s*(?P<title>.*)$", re.IGNORECASE
    ),
    re.compile(r"^(?P<label>\d+(?:\.\d+){0,3})\s+(?P<title>[A-Z][^.]{3,90})$"),
    re.compile(r"^(?P<label>[A-Z])\.\s+(?P<title>[A-Z][^.]{3,80})$"),
]

KEYWORD_SECTIONS = (
    "definitions",
    "scope",
    "term",
    "term and termination",
    "pricing",
    "prices",
    "price",
    "payment",
    "payment terms",
    "delivery",
    "delivery terms",
    "minimum order",
    "discount",
    "warranty",
    "liability",
    "indemnity",
    "confidentiality",
    "compliance",
    "audit",
    "renewal",
    "termination",
    "amendment",
    "governing law",
    "service level",
    "orders",
    "acceptance",
    "assignment",
)


@dataclass(slots=True)
class StructureLine:
    """One paragraph with its detected position in the hierarchy."""

    text: str
    page_number: int
    section: str | None = None
    subsection: str | None = None
    clause: str | None = None
    kind: str = "paragraph"
    order: int = 0


@dataclass(slots=True)
class DocumentStructure:
    lines: list[StructureLine] = field(default_factory=list)
    sections: list[dict[str, object]] = field(default_factory=list)
    headings: list[str] = field(default_factory=list)

    def section_text(self, section: str) -> str:
        return "\n".join(line.text for line in self.lines if line.section == section)


def detect_structure(document: ParsedDocument) -> DocumentStructure:
    structure = DocumentStructure()
    current_section: str | None = None
    current_subsection: str | None = None
    current_clause: str | None = None
    section_pages: dict[str, list[int]] = {}
    order = 0

    for page in document.pages:
        for block in _ordered_blocks(page):
            text = block.text.strip()
            if not text:
                continue
            kind, label, title = _classify(block, text)
            if kind == "skip":
                continue
            if kind == "section":
                current_section = title or label or text
                current_subsection = None
                current_clause = None
                structure.headings.append(current_section)
                section_pages.setdefault(current_section, []).append(page.page_number)
            elif kind == "clause":
                current_clause = label or current_clause
                if not current_section:
                    current_section = "General"
                    section_pages.setdefault(current_section, []).append(page.page_number)
            elif kind == "subsection":
                current_subsection = title or label or text

            structure.lines.append(
                StructureLine(
                    text=text,
                    page_number=page.page_number,
                    section=current_section,
                    subsection=current_subsection,
                    clause=current_clause if kind in {"clause", "paragraph"} else None,
                    kind=kind,
                    order=order,
                )
            )
            order += 1

    for name, pages in section_pages.items():
        structure.sections.append(
            {
                "section": name,
                "pages": sorted(set(pages)),
                "line_count": sum(1 for line in structure.lines if line.section == name),
            }
        )
    return structure


def _ordered_blocks(page: ParsedPage) -> list[TextBlock]:
    if page.blocks:
        # Table cells are represented as table chunks, so they are not repeated
        # inside paragraph chunks (which would double-count pricing content).
        return sorted(
            (block for block in page.blocks if block.kind != "table_cell"),
            key=lambda block: block.order,
        )
    return [
        TextBlock(text=line, order=index)
        for index, line in enumerate(page.best_text.splitlines())
        if line.strip()
    ]


def _classify(block: TextBlock, text: str) -> tuple[str, str | None, str | None]:
    stripped = text.strip()
    lowered = stripped.lower().rstrip(":.")
    if block.kind == "table_cell":
        return ("skip", None, None)
    if block.kind == "heading":
        return ("section", None, stripped)
    if len(stripped) <= 90 and lowered in KEYWORD_SECTIONS:
        return ("section", None, stripped.title())
    if len(stripped) <= 90:
        for pattern in CLAUSE_PATTERNS:
            match = pattern.match(stripped)
            if match:
                label = match.group("label").strip()
                title = (match.groupdict().get("title") or "").strip()
                if title and title.lower().rstrip(":.") in KEYWORD_SECTIONS and len(title) < 60:
                    return ("section", label, f"{label} {title}".strip())
                if label.lower().startswith(("section", "article", "clause")) or re.match(
                    r"^\d+\.\d+", label
                ):
                    return ("subsection", label, f"{label} {title}".strip())
                return ("clause", label, f"{label} {title}".strip())
    return ("paragraph", None, None)


def page_heading_map(structure: DocumentStructure) -> dict[int, str | None]:
    """Nearest preceding section per page, used for contextual enrichment."""
    mapping: dict[int, str | None] = {}
    last_section: str | None = None
    for line in sorted(structure.lines, key=lambda item: (item.page_number, item.order)):
        if line.kind == "section" and line.text:
            last_section = line.text
        mapping.setdefault(line.page_number, last_section)
    return mapping
