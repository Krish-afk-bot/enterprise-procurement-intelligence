"""Ingestion data types.

Parsers return these structures so the pipeline never touches a parser SDK type.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

EXTRACTION_TEXT = "text"
EXTRACTION_OCR = "ocr"
EXTRACTION_VLM = "vlm"
EXTRACTION_NATIVE = "native"  # native document structure (docx/xlsx/csv)


@dataclass(slots=True)
class TextBlock:
    """A layout-aware text block used for structure detection."""

    text: str
    font_size: float | None = None
    bold: bool | None = None
    bbox: tuple[float, float, float, float] | None = None
    order: int = 0
    kind: str = "paragraph"


@dataclass(slots=True)
class ParsedTable:
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    bbox: tuple[float, float, float, float] | None = None
    caption: str | None = None
    extraction_method: str = EXTRACTION_TEXT
    complexity_score: int = 0

    def to_markdown(self) -> str:
        if not self.headers and not self.rows:
            return ""
        header = self.headers or [
            f"col{i + 1}" for i in range(max(len(r) for r in self.rows) if self.rows else 0)
        ]
        lines = ["| " + " | ".join(_clean(c) for c in header) + " |"]
        lines.append("| " + " | ".join("---" for _ in header) + " |")
        for row in self.rows:
            padded = list(row) + [""] * (len(header) - len(row))
            lines.append("| " + " | ".join(_clean(c) for c in padded[: len(header)]) + " |")
        return "\n".join(lines)


def _clean(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ").strip()


@dataclass(slots=True)
class ParsedPage:
    page_number: int
    text: str = ""
    blocks: list[TextBlock] = field(default_factory=list)
    tables: list[ParsedTable] = field(default_factory=list)
    image_bytes: bytes | None = None
    image_mime: str = "image/png"
    width: float | None = None
    height: float | None = None
    has_text_layer: bool = True
    is_scanned: bool = False
    needs_vision: bool = False
    extraction_method: str = EXTRACTION_TEXT
    ocr_text: str | None = None

    @property
    def char_count(self) -> int:
        return len((self.text or "").strip())

    @property
    def best_text(self) -> str:
        return (self.text or "").strip() or (self.ocr_text or "").strip()


@dataclass(slots=True)
class ParsedDocument:
    pages: list[ParsedPage] = field(default_factory=list)
    title: str = ""
    document_type_hint: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    extraction_method: str = EXTRACTION_TEXT
    warnings: list[str] = field(default_factory=list)
    plain_text: str = ""
    tables: list[ParsedTable] = field(default_factory=list)
    sheets: list[str] = field(default_factory=list)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def scanned_page_count(self) -> int:
        return sum(1 for page in self.pages if page.is_scanned)

    @property
    def full_text(self) -> str:
        if self.plain_text:
            return self.plain_text
        return "\n\n".join(page.best_text for page in self.pages if page.best_text)
