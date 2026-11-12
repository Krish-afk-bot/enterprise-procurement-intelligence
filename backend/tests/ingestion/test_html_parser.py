"""HTML notice parsing.

Public procurement portals (UK Find a Tender, for one) publish tender notices as
HTML. These tests pin the behaviour that makes those notices ingestable:
readable paragraphs, headings, tables, and no script/style leakage.
"""

from __future__ import annotations

from app.ingestion.parsers import parse_document
from app.ingestion.validation import SUPPORTED_MIME_TYPES, sniff_mime

NOTICE = b"""<!DOCTYPE html>
<html>
<head>
  <title>Contract notice - Supply of laboratory consumables</title>
  <style>.hidden { display: none; }</style>
  <script>var tracking = "should-not-appear";</script>
</head>
<body>
  <nav>Skip to content</nav>
  <h1>Contract notice</h1>
  <p>Published: 4 November 2026</p>
  <p>The authority invites tenders for laboratory consumables.</p>
  <table>
    <tr><th>Lot</th><th>Description</th><th>Value</th></tr>
    <tr><td>1</td><td>Glassware</td><td>120000</td></tr>
    <tr><td>2</td><td>Reagents</td><td>80000</td></tr>
  </table>
  <h2>Submission</h2>
  <p>Deadline: 12 December 2026.</p>
</body>
</html>"""


def test_html_notice_parses_into_blocks_and_tables():
    document = parse_document(NOTICE, mime_type="text/html", filename="notice.html")

    assert document.title == "Contract notice - Supply of laboratory consumables"
    assert len(document.pages) == 1
    page = document.pages[0]
    text = page.text

    assert "laboratory consumables" in text
    assert "Deadline: 12 December 2026." in text
    assert "should-not-appear" not in text
    assert "Skip to content" not in text
    assert "display: none" not in text

    headings = [block.text for block in page.blocks if block.kind == "heading"]
    assert headings == ["Contract notice", "Submission"]

    assert len(document.tables) == 1
    table = document.tables[0]
    assert table.headers == ["Lot", "Description", "Value"]
    assert table.rows == [["1", "Glassware", "120000"], ["2", "Reagents", "80000"]]
    assert table.extraction_method == "html_table"

    assert document.metadata["page_numbering"] == "single"
    assert any("no physical pages" in warning for warning in document.warnings)


def test_html_without_text_reports_a_warning_instead_of_inventing_content():
    document = parse_document(
        b"<html><head><title>Empty</title></head><body><script>x()</script></body></html>",
        mime_type="text/html",
        filename="empty.html",
    )
    assert document.pages[0].text == ""
    assert document.title == "Empty"
    assert document.warnings


def test_html_is_an_accepted_extension_and_sniffs_as_html():
    assert ".html" in {".html", ".htm"}
    assert "text/html" in SUPPORTED_MIME_TYPES
    assert sniff_mime(NOTICE, "notice.html") == "text/html"
    assert sniff_mime(b"<html><body>hi</body></html>", "page.htm") == "text/html"
