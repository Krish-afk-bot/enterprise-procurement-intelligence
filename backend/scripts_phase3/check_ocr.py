"""Phase 5 Stage 2: Check OCR availability and test on the scanned page."""

import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCANNED_PDF = PROJECT_ROOT / "data" / "synthetic" / "supplier_a_scanned_signature_page.pdf"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://epi:epi@localhost:5432/epi")
os.environ.setdefault("VECTOR_PROVIDER", "qdrant")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("ALLOW_PROVIDER_FALLBACK", "false")


async def main() -> None:
    from app.ingestion.ocr import OcrEngine
    from app.ingestion.parsers.pdf import parse_pdf

    print(f"Scanned PDF exists: {SCANNED_PDF.exists()}")
    print(f"Scanned PDF size: {SCANNED_PDF.stat().st_size:,} bytes")

    # 1. Check OCR engine loads
    engine = OcrEngine(enabled=True, language="en", use_onednn=False)
    loaded = await engine.ensure_loaded()
    print(f"OCR engine loaded: {loaded}")
    if not loaded:
        print("OCR UNAVAILABLE — check PaddleOCR installation")
        return

    # 2. Parse the PDF to get pages
    content = SCANNED_PDF.read_bytes()
    parsed = parse_pdf(content, filename=SCANNED_PDF.name, render_images=True)
    print(f"Pages: {parsed.page_count}  scanned: {parsed.scanned_page_count}")

    for page in parsed.pages:
        print(
            f"  page {page.page_number}: text_len={len(page.text or '')} has_image={page.image_bytes is not None}"
        )

    # 3. Run OCR on the scanned page
    for page in parsed.pages:
        if not page.text or len(page.text.strip()) < 40:
            if page.image_bytes:
                print(f"\nRunning OCR on page {page.page_number}...")
                result = await engine.ocr_image(page.image_bytes)
                print(f"  OCR available: {result.available}")
                print(f"  OCR text (first 400 chars): {result.text[:400] if result.text else '(empty)'}")
                if result.text:
                    for kw in ["Alvarez", "2024-01-08", "APPROVED", "signature", "signed"]:
                        found = kw.lower() in result.text.lower()
                        print(f"  keyword '{kw}': {'FOUND' if found else 'not found'}")
            else:
                print(f"  page {page.page_number}: no image bytes available")


if __name__ == "__main__":
    asyncio.run(main())
