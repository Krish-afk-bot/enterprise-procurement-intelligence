"""Parser dispatch.

The pipeline calls :func:`parse_document` with a validated upload; the concrete
parser is chosen from the *sniffed* MIME type, never from the file extension
alone.
"""

from __future__ import annotations

from app.core.errors import FileValidationError
from app.ingestion.parsers.image import parse_image
from app.ingestion.parsers.office import parse_csv, parse_docx, parse_text, parse_xlsx
from app.ingestion.parsers.pdf import parse_pdf
from app.ingestion.types import ParsedDocument

try:  # optional dependency guard for pypdf fallback
    import pypdf  # noqa: F401

    _HAS_PYPDF = True
except ImportError:  # pragma: no cover
    _HAS_PYPDF = False


def parse_document(
    content: bytes,
    *,
    mime_type: str,
    filename: str = "",
    render_images: bool = True,
) -> ParsedDocument:
    if mime_type == "application/pdf":
        try:
            return parse_pdf(content, filename=filename, render_images=render_images)
        except Exception as exc:  # noqa: BLE001
            fallback = _pypdf_fallback(content, filename)
            if fallback is not None:
                fallback.warnings.append(
                    f"PyMuPDF failed ({type(exc).__name__}); used pypdf text-only extraction. "
                    "Layout, tables and page images are unavailable for this document."
                )
                return fallback
            raise FileValidationError(
                f"The PDF could not be parsed: {type(exc).__name__}.", details={"filename": filename}
            ) from exc

    if mime_type.startswith("image/"):
        return parse_image(content, filename=filename, mime_type=mime_type)

    if mime_type in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }:
        return parse_docx(content, filename=filename)

    if mime_type in {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel.sheet.macroEnabled.12",
        "application/vnd.ms-excel",
    }:
        return parse_xlsx(content, filename=filename)

    if mime_type in {"text/csv", "application/csv"}:
        return parse_csv(content, filename=filename)

    if mime_type in {"text/plain", "text/markdown"}:
        return parse_text(content, filename=filename)

    raise FileValidationError(
        f"No parser is available for content type '{mime_type}'.", details={"filename": filename}
    )


def _pypdf_fallback(content: bytes, filename: str) -> ParsedDocument | None:
    if not _HAS_PYPDF:
        return None
    try:
        import io

        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        pages = []
        from app.ingestion.types import ParsedPage

        for index, page in enumerate(reader.pages):
            text = (page.extract_text() or "").strip()
            pages.append(
                ParsedPage(
                    page_number=index + 1,
                    text=text,
                    has_text_layer=len(text) >= 40,
                    is_scanned=len(text) < 40,
                    extraction_method="text",
                )
            )
        return ParsedDocument(
            pages=pages,
            title=filename or "PDF document",
            metadata={"parser": "pypdf_fallback", "page_numbering": "physical"},
        )
    except Exception:  # noqa: BLE001
        return None


__all__ = [
    "parse_csv",
    "parse_docx",
    "parse_document",
    "parse_image",
    "parse_pdf",
    "parse_text",
    "parse_xlsx",
]
