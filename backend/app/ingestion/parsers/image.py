"""Image parsing: PNG/JPEG/TIFF uploads are single scanned pages."""

from __future__ import annotations

import io
from pathlib import Path

from app.ingestion.types import EXTRACTION_OCR, ParsedDocument, ParsedPage


def parse_image(content: bytes, *, filename: str = "", mime_type: str = "image/png") -> ParsedDocument:
    from PIL import Image

    with Image.open(io.BytesIO(content)) as image:
        width, height = image.size
        mode = image.mode
        if mode not in {"RGB", "L"}:
            converted = image.convert("RGB")
            buffer = io.BytesIO()
            converted.save(buffer, format="PNG")
            normalized_png = buffer.getvalue()
        else:
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            normalized_png = buffer.getvalue()

    page = ParsedPage(
        page_number=1,
        text="",
        blocks=[],
        tables=[],
        image_bytes=normalized_png,
        image_mime="image/png",
        width=float(width),
        height=float(height),
        has_text_layer=False,
        is_scanned=True,
        needs_vision=False,  # decided after OCR runs
        extraction_method=EXTRACTION_OCR,
    )
    return ParsedDocument(
        pages=[page],
        title=(Path(filename).stem if filename else "Image"),
        metadata={
            "page_numbering": "single",
            "parser": "pillow",
            "original_mime": mime_type,
            "original_mode": mode,
            "width": width,
            "height": height,
        },
        extraction_method=EXTRACTION_OCR,
    )
