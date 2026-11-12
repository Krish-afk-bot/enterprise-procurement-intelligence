"""HTML parsing for procurement notices.

Many public procurement portals publish tender notices as HTML rather than PDF
(UK Find a Tender, for example). Without this parser those notices could not be
ingested at all, so a real corpus stayed out of reach.

The parser uses only the standard library: it strips scripts, styles and
navigation, keeps block structure as paragraphs, records headings, and turns
``<table>`` elements into ``ParsedTable`` objects so price and lot tables remain
queryable. HTML has no physical pages, so the document declares logical
numbering instead of inventing page numbers.
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from app.ingestion.types import (
    EXTRACTION_NATIVE,
    ParsedDocument,
    ParsedPage,
    ParsedTable,
    TextBlock,
)

_SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "iframe", "nav", "footer"}
_BLOCK_TAGS = {
    "p",
    "div",
    "section",
    "article",
    "main",
    "header",
    "li",
    "ul",
    "ol",
    "tr",
    "table",
    "thead",
    "tbody",
    "br",
    "hr",
    "dd",
    "dt",
    "dl",
    "blockquote",
    "pre",
}
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_CELL_TAGS = {"td", "th"}


class _NoticeCollector(HTMLParser):
    """Turn an HTML notice into ordered text blocks and tables."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[TextBlock] = []
        self.tables: list[ParsedTable] = []
        self.title: str = ""
        self._skip_depth = 0
        self._buffer: list[str] = []
        self._current_heading: str | None = None
        self._in_title = False
        self._order = 0

        # table state
        self._table_depth = 0
        self._rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    # ------------------------------------------------------------------ parser
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = True
            return
        if tag == "table":
            self._flush()
            self._table_depth += 1
            if self._table_depth == 1:
                self._rows = []
            return
        if self._table_depth:
            if tag == "tr":
                self._close_row()
                self._row = []
            elif tag in _CELL_TAGS:
                self._close_cell()
                self._cell = []
            return
        if tag in _HEADING_TAGS:
            self._flush()
            self._current_heading = tag
            return
        if tag in _BLOCK_TAGS:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = False
            return
        if tag == "table":
            if self._table_depth:
                self._close_cell()
                self._close_row()
                self._table_depth -= 1
                if self._table_depth == 0:
                    self._emit_table()
            return
        if self._table_depth:
            if tag in _CELL_TAGS:
                self._close_cell()
            elif tag == "tr":
                self._close_row()
            return
        if tag in _HEADING_TAGS:
            self._flush()
            if self._current_heading == tag:
                self._current_heading = None
            return
        if tag in _BLOCK_TAGS:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = " ".join(data.split())
        if not text:
            return
        if self._in_title:
            self.title = f"{self.title} {text}".strip()
            return
        if self._cell is not None:
            self._cell.append(text)
            return
        self._buffer.append(text)

    # ------------------------------------------------------------------ output
    def _flush(self) -> None:
        if not self._buffer:
            return
        text = " ".join(self._buffer).strip()
        self._buffer = []
        if not text:
            return
        heading = self._current_heading is not None
        self.blocks.append(
            TextBlock(
                text=text,
                order=self._order,
                kind="heading" if heading else "paragraph",
                bold=heading,
            )
        )
        self._order += 1

    def _close_cell(self) -> None:
        if self._cell is None:
            return
        value = " ".join(self._cell).strip()
        self._cell = None
        if self._row is None:
            self._row = []
        self._row.append(value)

    def _close_row(self) -> None:
        self._close_cell()
        if self._row is not None:
            if any(cell for cell in self._row):
                self._rows.append(self._row)
            self._row = None

    def _emit_table(self) -> None:
        rows = [row for row in self._rows if any(cell.strip() for cell in row)]
        self._rows = []
        if len(rows) < 2:
            # A single row is a layout table, not tabular data: keep its text.
            for row in rows:
                joined = " | ".join(cell for cell in row if cell)
                if joined:
                    self.blocks.append(
                        TextBlock(text=joined, order=self._order, kind="paragraph")
                    )
                    self._order += 1
            return
        header = rows[0]
        body = rows[1:]
        self.tables.append(
            ParsedTable(
                headers=header,
                rows=body,
                extraction_method="html_table",
                complexity_score=min(
                    6,
                    (2 if len(header) >= 4 else 1)
                    + (2 if len(body) >= 12 else 1 if len(body) >= 6 else 0),
                ),
            )
        )
        for index, row in enumerate(rows):
            self.blocks.append(
                TextBlock(
                    text=" | ".join(cell for cell in row if cell),
                    order=self._order,
                    kind="table_cell",
                )
            )
            self._order += 1


def parse_html(content: bytes, *, filename: str = "") -> ParsedDocument:
    """Parse an HTML notice into one logical page of blocks and tables."""
    collector = _NoticeCollector()
    collector.feed(_decode(content))
    collector.close()
    collector._flush()

    blocks = collector.blocks
    if not blocks:
        title = collector.title or (Path(filename).stem if filename else "HTML document")
        page = ParsedPage(
            page_number=1,
            text="",
            blocks=[],
            extraction_method=EXTRACTION_NATIVE,
        )
        document = ParsedDocument(
            pages=[page],
            title=title,
            metadata={"page_numbering": "single", "parser": "html", "empty": True},
            extraction_method=EXTRACTION_NATIVE,
        )
        document.warnings.append("The HTML page contained no readable text after cleanup.")
        return document

    page = ParsedPage(
        page_number=1,
        text="\n".join(block.text for block in blocks),
        blocks=blocks,
        tables=list(collector.tables),
        extraction_method=EXTRACTION_NATIVE,
    )
    title = collector.title
    if not title:
        first_heading = next((block for block in blocks if block.kind == "heading"), None)
        title = first_heading.text if first_heading else (Path(filename).stem or "HTML document")
    document = ParsedDocument(
        pages=[page],
        title=title,
        metadata={
            "page_numbering": "single",
            "parser": "html",
            "blocks": len(blocks),
            "tables": len(collector.tables),
        },
        extraction_method=EXTRACTION_NATIVE,
        tables=list(collector.tables),
    )
    if len(document.pages) == 1:
        document.warnings.append(
            "HTML has no physical pages: page 1 is the whole notice (logical numbering)."
        )
    return document


def _decode(content: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "windows-1252", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")
