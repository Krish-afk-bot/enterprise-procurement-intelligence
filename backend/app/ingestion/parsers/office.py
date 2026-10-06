"""Office/spreadsheet parsing: DOCX, XLSX/XLSM and CSV.

These formats have no physical pages, so logical pages are used and the document
metadata records that fact (``page_numbering``) rather than inventing page
numbers. Spreadsheet sheets map one-to-one onto "pages" so citations stay
traceable.
"""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path

from app.ingestion.types import (
    EXTRACTION_NATIVE,
    ParsedDocument,
    ParsedPage,
    ParsedTable,
    TextBlock,
)

_PAGE_BREAK_RE = re.compile(r"<w:br[^>]*w:type=\"page\"", re.IGNORECASE)


def parse_docx(content: bytes, *, filename: str = "") -> ParsedDocument:
    import docx  # python-docx

    document = docx.Document(io.BytesIO(content))
    pages: list[ParsedPage] = []
    current: list[TextBlock] = []
    page_number = 1
    warning = ""
    try:
        raw_xml = document.element.body.xml
        has_explicit_breaks = bool(_PAGE_BREAK_RE.search(raw_xml))
    except Exception:  # noqa: BLE001
        has_explicit_breaks = False

    order = 0
    for paragraph in document.paragraphs:
        text = (paragraph.text or "").strip()
        style = (paragraph.style.name if paragraph.style is not None else "") or ""
        is_heading = style.lower().startswith("heading") or style.lower() in {"title", "subtitle"}
        has_break = False
        try:
            has_break = bool(_PAGE_BREAK_RE.search(paragraph._p.xml))  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            has_break = False
        if has_break and current:
            pages.append(_page(page_number, current))
            page_number += 1
            current = []
        if text:
            current.append(
                TextBlock(text=text, order=order, kind="heading" if is_heading else "paragraph", bold=is_heading)
            )
            order += 1
    if current or not pages:
        pages.append(_page(page_number, current))

    tables: list[ParsedTable] = []
    for table in document.tables:
        rows = [[(cell.text or "").strip() for cell in row.cells] for row in table.rows]
        rows = [row for row in rows if any(row)]
        if not rows:
            continue
        tables.append(
            ParsedTable(
                headers=rows[0],
                rows=rows[1:],
                extraction_method="docx_table",
                complexity_score=min(4, len(rows[0]) // 2 + (1 if len(rows) >= 8 else 0)),
            )
        )
    if not has_explicit_breaks and len(pages) == 1:
        warning = "DOCX has no explicit page breaks: page numbering is logical (single section)."

    doc = ParsedDocument(
        pages=pages,
        title=(document.core_properties.title or Path(filename).stem).strip(),
        metadata={
            "page_numbering": "physical" if has_explicit_breaks else "logical",
            "parser": "python-docx",
            "core_properties": {
                "author": document.core_properties.author,
                "created": str(document.core_properties.created) if document.core_properties.created else None,
                "modified": str(document.core_properties.modified) if document.core_properties.modified else None,
                "title": document.core_properties.title,
            },
        },
        extraction_method=EXTRACTION_NATIVE,
        tables=tables,
    )
    if warning:
        doc.warnings.append(warning)
    return doc


def parse_xlsx(content: bytes, *, filename: str = "") -> ParsedDocument:
    import openpyxl

    workbook = openpyxl.load_workbook(io.BytesIO(content), data_only=True, read_only=True)
    pages: list[ParsedPage] = []
    tables: list[ParsedTable] = []
    sheets: list[str] = []
    try:
        for index, sheet in enumerate(workbook.worksheets):
            sheets.append(sheet.title)
            rows: list[list[str]] = []
            for row in sheet.iter_rows(values_only=True):
                cells = ["" if value is None else str(value).strip() for value in row]
                if any(cells):
                    rows.append(cells)
                if len(rows) >= 5000:
                    break
            if not rows:
                continue
            header = rows[0]
            body = rows[1:]
            table = ParsedTable(
                headers=header,
                rows=body,
                caption=f"Sheet: {sheet.title}",
                extraction_method="xlsx_sheet",
                complexity_score=min(
                    6, (2 if len(header) >= 4 else 1) + (2 if len(body) >= 12 else 1 if len(body) >= 6 else 0)
                ),
            )
            tables.append(table)
            blocks = [TextBlock(text=f"Sheet: {sheet.title}", order=0, kind="heading", bold=True)]
            for row_index, row in enumerate(rows):
                # Row text is captured by the sheet's table object; marking the
                # blocks as table cells prevents duplicate paragraph chunks.
                blocks.append(
                    TextBlock(text=" | ".join(row), order=row_index + 1, kind="table_cell")
                )
            pages.append(
                ParsedPage(
                    page_number=index + 1,
                    text="\n".join(block.text for block in blocks),
                    blocks=blocks,
                    tables=[table],
                    has_text_layer=True,
                    is_scanned=False,
                    needs_vision=False,
                    extraction_method=EXTRACTION_NATIVE,
                )
            )
    finally:
        workbook.close()

    return ParsedDocument(
        pages=pages,
        title=(Path(filename).stem if filename else "Workbook"),
        document_type_hint="pricing_schedule",
        metadata={"page_numbering": "sheet", "parser": "openpyxl", "sheets": sheets},
        extraction_method=EXTRACTION_NATIVE,
        tables=tables,
        sheets=sheets,
    )


def parse_csv(content: bytes, *, filename: str = "") -> ParsedDocument:
    text = _decode(content)
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    rows = [["" if cell is None else str(cell).strip() for cell in row] for row in reader]
    rows = [row for row in rows if any(row)]
    tables: list[ParsedTable] = []
    if rows:
        tables.append(
            ParsedTable(
                headers=rows[0],
                rows=rows[1:],
                extraction_method="csv_table",
                complexity_score=min(6, (2 if len(rows[0]) >= 4 else 1) + (2 if len(rows) >= 12 else 0)),
            )
        )
    blocks = [TextBlock(text=" | ".join(row), order=i, kind="table_cell") for i, row in enumerate(rows)]
    page = ParsedPage(
        page_number=1,
        text="\n".join(block.text for block in blocks),
        blocks=blocks,
        tables=tables,
        extraction_method=EXTRACTION_NATIVE,
    )
    return ParsedDocument(
        pages=[page],
        title=(Path(filename).stem if filename else "Table"),
        document_type_hint="pricing_schedule",
        metadata={"page_numbering": "single", "parser": "csv", "rows": len(rows)},
        extraction_method=EXTRACTION_NATIVE,
        tables=tables,
    )


def parse_text(content: bytes, *, filename: str = "") -> ParsedDocument:
    text = _decode(content)
    pages: list[ParsedPage] = []
    chunks = text.split("\f") if "\f" in text else [text]
    for index, chunk in enumerate(chunks):
        blocks = [
            TextBlock(
                text=line.strip(),
                order=line_index,
                kind="heading" if line.strip().isupper() and 3 < len(line.strip()) < 80 else "paragraph",
            )
            for line_index, line in enumerate(chunk.splitlines())
            if line.strip()
        ]
        pages.append(
            ParsedPage(
                page_number=index + 1,
                text="\n".join(block.text for block in blocks),
                blocks=blocks,
                extraction_method=EXTRACTION_NATIVE,
            )
        )
    return ParsedDocument(
        pages=pages,
        title=(Path(filename).stem if filename else "Text document"),
        metadata={"page_numbering": "formfeed" if len(pages) > 1 else "single", "parser": "text"},
        extraction_method=EXTRACTION_NATIVE,
    )


def _page(page_number: int, blocks: list[TextBlock]) -> ParsedPage:
    return ParsedPage(
        page_number=page_number,
        text="\n".join(block.text for block in blocks),
        blocks=blocks,
        extraction_method=EXTRACTION_NATIVE,
    )


def _decode(content: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")
