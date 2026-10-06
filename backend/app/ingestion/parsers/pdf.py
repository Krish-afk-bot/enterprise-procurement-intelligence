"""PDF parsing with PyMuPDF.

Extracts per-page text *and* layout: font-size aware blocks (for heading/section
detection), vector tables, and a rendered page image used for OCR and for
selective VLM escalation. Pages with almost no extractable text are flagged as
scanned instead of being silently treated as empty.
"""

from __future__ import annotations

from pathlib import Path

from app.ingestion.types import (
    EXTRACTION_OCR,
    EXTRACTION_TEXT,
    ParsedDocument,
    ParsedPage,
    ParsedTable,
    TextBlock,
)
from app.observability.logging import get_logger

logger = get_logger(__name__)

MIN_CHARS_FOR_TEXT_LAYER = 40
RENDER_DPI = 144


def parse_pdf(content: bytes, *, filename: str = "", render_images: bool = True) -> ParsedDocument:
    import fitz  # PyMuPDF

    document = fitz.open(stream=content, filetype="pdf")
    pages: list[ParsedPage] = []
    warnings: list[str] = []
    try:
        metadata = dict(document.metadata or {})
        for index, page in enumerate(document):
            page_number = index + 1
            text_dict = page.get_text("dict")
            tables = _tables_from_page(page)
            blocks = _blocks_from_dict(text_dict, tables)
            plain = "\n".join(block.text for block in blocks if block.text).strip()
            area = max(1.0, page.rect.width * page.rect.height)
            text_density = len(plain) / area
            has_text_layer = len(plain) >= MIN_CHARS_FOR_TEXT_LAYER
            is_scanned = not has_text_layer
            image_bytes = None
            if render_images:
                try:
                    pixmap = page.get_pixmap(dpi=RENDER_DPI, alpha=False)
                    image_bytes = pixmap.tobytes("png")
                except Exception as exc:  # noqa: BLE001
                    warnings.append(f"page {page_number}: render failed ({type(exc).__name__})")
            pages.append(
                ParsedPage(
                    page_number=page_number,
                    text=plain,
                    blocks=blocks,
                    tables=tables,
                    image_bytes=image_bytes,
                    width=float(page.rect.width),
                    height=float(page.rect.height),
                    has_text_layer=has_text_layer,
                    is_scanned=is_scanned,
                    needs_vision=_needs_vision(is_scanned, tables, text_density, page),
                    extraction_method=EXTRACTION_TEXT if has_text_layer else EXTRACTION_OCR,
                )
            )
    finally:
        document.close()

    return ParsedDocument(
        pages=pages,
        title=(metadata.get("title") or Path(filename).stem).strip(),
        metadata={
            "pdf_metadata": {k: v for k, v in metadata.items() if v},
            "page_numbering": "physical",
            "parser": "pymupdf",
        },
        extraction_method=EXTRACTION_TEXT,
        warnings=warnings,
    )


def _blocks_from_dict(text_dict: dict, tables: list[ParsedTable]) -> list[TextBlock]:
    """Extract layout blocks and classify headings against the *dominant* body size.

    Using the median font size mislabels body text as headings on pages that
    contain many small table cells (the median drops to the cell size). The
    dominant size — the size carrying the most characters — is a far more stable
    baseline, and text inside a detected table region is never a heading.
    """
    blocks: list[TextBlock] = []
    raw: list[tuple[str, float, bool, tuple[float, float, float, float]]] = []
    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            text = "".join(span.get("text", "") for span in spans).strip()
            if not text:
                continue
            fonts = [span.get("size", 0.0) for span in spans]
            size = round(max(fonts) if fonts else 0.0, 1)
            bold = any("bold" in (span.get("font", "").lower()) for span in spans)
            bbox = tuple(line.get("bbox", (0, 0, 0, 0)))
            raw.append((text, size, bold, bbox))  # type: ignore[arg-type]

    dominant_size = _dominant_size(raw)
    for order, (text, size, bold, bbox) in enumerate(raw):
        in_table = _inside_any_table(bbox, tables)
        is_heading = (
            not in_table
            and size >= dominant_size + 0.9
            and len(text) <= 140
            and not text.endswith(('.', ';'))
        )
        blocks.append(
            TextBlock(
                text=text,
                font_size=size,
                bold=bold,
                bbox=bbox,
                order=order,
                kind="table_cell" if in_table else ("heading" if is_heading else "paragraph"),
            )
        )
    return blocks


def _dominant_size(raw: list[tuple[str, float, bool, tuple[float, float, float, float]]]) -> float:
    """Font size carrying the most characters (the body text size)."""
    weight: dict[float, int] = {}
    for text, size, _bold, _bbox in raw:
        weight[size] = weight.get(size, 0) + len(text)
    if not weight:
        return 0.0
    # Ignore the tiny running-footer size when other sizes are present.
    candidates = {size: count for size, count in weight.items() if size >= 8.0} or weight
    return max(candidates.items(), key=lambda item: item[1])[0]


def _inside_any_table(bbox: tuple[float, float, float, float], tables: list[ParsedTable]) -> bool:
    if not tables or not bbox:
        return False
    cx = (bbox[0] + bbox[2]) / 2
    cy = (bbox[1] + bbox[3]) / 2
    for table in tables:
        if not table.bbox:
            continue
        x0, y0, x1, y1 = table.bbox
        if x0 - 1 <= cx <= x1 + 1 and y0 - 1 <= cy <= y1 + 1:
            return True
    return False


def _tables_from_page(page) -> list[ParsedTable]:
    tables: list[ParsedTable] = []
    finder = getattr(page, "find_tables", None)
    if finder is None:
        return tables
    try:
        found = finder()
    except Exception as exc:  # noqa: BLE001
        logger.warning("pdf_table_detection_failed", error=str(exc))
        return tables
    for table in getattr(found, "tables", []):
        try:
            rows = table.extract()
        except Exception:  # noqa: BLE001
            continue
        cleaned = [[("" if cell is None else str(cell)).strip() for cell in row] for row in rows if row]
        if not cleaned:
            continue
        header = cleaned[0]
        body = cleaned[1:]
        tables.append(
            ParsedTable(
                headers=[h for h in header],
                rows=body,
                bbox=tuple(table.bbox) if getattr(table, "bbox", None) else None,
                extraction_method="pdf_vector_table",
                complexity_score=_complexity(len(header), len(body)),
            )
        )
    return tables


def _complexity(columns: int, rows: int) -> int:
    if columns <= 0:
        return 0
    score = 0
    if columns >= 4:
        score += 2
    elif columns == 3:
        score += 1
    if rows >= 12:
        score += 2
    elif rows >= 6:
        score += 1
    return score


def _needs_vision(is_scanned: bool, tables: list[ParsedTable], text_density: float, page) -> bool:
    """Escalate only genuinely visual pages (PRD s.13: never every page)."""
    if is_scanned:
        return True
    if any(table.complexity_score >= 3 for table in tables):
        return True
    # Dense drawings/images with little text usually carry visual-only meaning.
    try:
        drawings = page.get_drawings()
    except Exception:  # noqa: BLE001
        drawings = []
    if len(drawings) > 60 and text_density < 0.0008:
        return True
    return False
