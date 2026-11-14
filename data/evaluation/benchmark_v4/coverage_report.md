# Chunk coverage audit

Generated 2026-11-14T10:02:36.683484+00:00 in 37.6 s.

| Metric | Value |
| --- | --- |
| Documents rebuilt | 20 |
| Pages | 42 |
| Pages with text / with ≥1 chunk | 41 / 41 |
| Chunks | 655 |
| Character coverage (5-gram, overlap excluded) | 98.09% |
| Documents below 100% page coverage | 1 |
| Documents below 99% char coverage | 2 |

## Per document

| Document | Status | Pages | Pages w/ chunk | Chars | Char cov. | Chunks | Table chunks | Empty | Dup | No page |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 04f6f2_tender_10.html | indexed | 1 | 1/1 | 5722 | 99.56% | 36 | 1 | 0 | 0 | 0 |
| 0508f7_tender_5.html | indexed | 1 | 1/1 | 6278 | 99.76% | 37 | 1 | 0 | 1 | 0 |
| 0523fd_tender_11.html | indexed | 1 | 1/1 | 13129 | 99.87% | 49 | 1 | 0 | 3 | 0 |
| 05a7e4_tender_18.html | indexed | 1 | 1/1 | 9554 | 99.76% | 46 | 1 | 0 | 2 | 0 |
| 060827_tender_19.docx | indexed | 2 | 2/2 | 7360 | 100.00% | 11 | 0 | 0 | 1 | 0 |
| 06093e_tender_20.html | indexed | 1 | 1/1 | 11344 | 99.37% | 49 | 1 | 0 | 2 | 0 |
| 064670_tender_1.html | indexed | 1 | 1/1 | 1051 | 97.24% | 4 | 1 | 0 | 0 | 0 |
| 065308_tender_2.html | indexed | 1 | 1/1 | 4660 | 99.64% | 33 | 1 | 0 | 0 | 0 |
| 065b20_tender_6.pdf | indexed | 22 | 22/22 | 45489 | 93.93% | 60 | 29 | 0 | 3 | 0 |
| 066066_tender_12.html | indexed | 1 | 1/1 | 4971 | 99.60% | 36 | 1 | 0 | 0 | 0 |
| 0664eb_tender_13.html | needs_review | 1 | 0/0 | 0 | 0.00% | 0 | 0 | 0 | 0 | 0 |
| 0679c4_tender_7.html | indexed | 1 | 1/1 | 6875 | 99.62% | 38 | 1 | 0 | 1 | 0 |
| 0683f4_tender_14.html | indexed | 1 | 1/1 | 5273 | 100.00% | 31 | 0 | 0 | 1 | 0 |
| 0685ae_tender_3.html | indexed | 1 | 1/1 | 6125 | 99.71% | 36 | 1 | 0 | 0 | 0 |
| 069a8c_tender_15.html | indexed | 1 | 1/1 | 15453 | 99.83% | 50 | 1 | 0 | 1 | 0 |
| 069b28_tender_16.docx | indexed | 1 | 1/1 | 409 | 100.00% | 1 | 0 | 0 | 0 | 0 |
| 06d0c8_tender_17.html | indexed | 1 | 1/1 | 3871 | 100.00% | 31 | 0 | 0 | 0 | 0 |
| 06d2dd_tender_8.html | indexed | 1 | 1/1 | 5185 | 100.00% | 39 | 0 | 0 | 1 | 0 |
| 06da37_tender_9.html | indexed | 1 | 1/1 | 3706 | 100.00% | 28 | 0 | 0 | 0 | 0 |
| 06e110_tender_4.html | indexed | 1 | 1/1 | 4281 | 99.56% | 40 | 1 | 0 | 0 | 0 |

## Documents with loss

- **064670_tender_1.html** — pages without chunks: none; character coverage 97.24%; warnings: HTML has no physical pages: page 1 is the whole notice (logical numbering).
- **065b20_tender_6.pdf** — pages without chunks: none; character coverage 93.93%; warnings: Vision escalation failed for page 7 (HTTPStatusError); the page kept its text/OCR extraction.; Vision escalation failed for page 8 (HTTPStatusError); the page kept its text/OCR extraction.; Vision escalation failed for page 12 (HTTPStatusError); the page kept its text/OCR extraction.; Vision escalation failed for page 19 (HTTPStatusError); the page kept its text/OCR extraction.; Vision escalation failed for page 20 (HTTPStatusError); the page kept its text/OCR extraction.
- **0664eb_tender_13.html** — pages without chunks: none; character coverage 0.00%; warnings: The HTML page contained no readable text after cleanup.; No text could be extracted from this file, so there is nothing to index. Parser=html, OCR=not_needed, vision=not_needed. Enable OCR or configure a VLM, then re-run indexing.

## Idempotency

Re-ingesting `064670_tender_1.html` produced 4 chunks (was 4); same ids: **True**.

## Known provenance gaps

- Chunk rows carry document id, page number and page id, but the schema has no character offsets,
  bounding boxes or per-page table coordinates populated for text chunks. Table chunks keep their
  headers and markdown but not coordinates.
- Page numbers are the parser's physical page numbering; HTML notices are one logical page.

