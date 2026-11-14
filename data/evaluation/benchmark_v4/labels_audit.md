# Benchmark v4 label audit

- Questions: 150 (v3: 120, new: 30)
- SHA-256 of questions.json: `0f6fa03db3b652db31961f364dcaf651fec29dcb1c4943c4c9e49c05f53606d3`
- New labels verified against page text: 30/30
- v3 answerable labels whose facts appear verbatim on the cited page: 66/70
- v3 labels with at least one fact not found verbatim: 0

## v3 labels not found verbatim

| id | missing facts |
| --- | --- |

## Method

- Answerable new labels: each expected fact is normalised (case, punctuation, spacing, currency glyphs)
  and required to appear in the raw text of the cited page. The evidence quote is copied from that page.
- Unanswerable new labels: probe terms are searched across every page's text; a hit would fail the label.
- v3 labels are reported above, not silently edited. `needs_review` items stay flagged.
- No question was written from the benchmark results, and no label was changed after the run.
