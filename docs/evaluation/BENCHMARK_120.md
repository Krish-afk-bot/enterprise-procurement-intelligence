# 120-Question Evaluation Benchmark

A reproducible benchmark of 120 procurement-intelligence questions over the real
corpus, with a recorded evidence trail, a runner that measures retrieval, answer,
citation, faithfulness, refusal, temporal and cost metrics, and the baseline
results. It exists to catch regressions and to make failures attributable, not to
produce a marketing number.

## 1. Corpus (what the questions can honestly be about)

| Item | Count |
| --- | --- |
| Documents | 20 real UK Find a Tender (OCDS) tender notices |
| Indexed | 19 (one portal page has no text) |
| Pages / chunks | 42 / 655 |
| Parsed for question generation | 15 notices with the Find a Tender field layout |
| Procurement records | 83,724 buyer/supplier award rows |
| Suppliers | 65,406 |
| Contracts | 1 (`POW-FTS-62602`, no value, no effective date) |
| Prices | 0 |
| Chunks with a clause number | 0 |
| Documents with a revision label | 1 |
| Compliance certificates | 10 (no numbers, no expiry dates) |

The corpus is pre-award tender notices, not signed contracts. That decides which
categories can be answered from evidence and which must be labelled unanswerable:
there are no payment terms except in two notices, no price schedules, no clause
numbering and no amendment history.

## 2. Composition

| # | Category | Questions | Answerable | Unanswerable | Needs review |
| --- | --- | --- | --- | --- | --- |
| 1 | Document metadata and identification | 18 | 18 | 0 | 0 |
| 2 | Contract parties and suppliers | 10 | 10 | 0 | 0 |
| 3 | Contract dates and duration | 18 | 18 | 0 | 0 |
| 4 | Payment terms | 8 | 2 | 6 | 0 |
| 5 | Pricing schedules | 8 | 0 | 8 | 0 |
| 6 | Contract clauses | 8 | 0 | 8 | 0 |
| 7 | Obligations and deliverables | 8 | 8 | 0 | 0 |
| 8 | Amendments and version comparisons | 8 | 0 | 7 | 1 |
| 9 | Supplier and buyer relationships | 8 | 0 | 0 | 8 |
| 10 | Knowledge Graph multi-hop | 6 | 0 | 0 | 6 |
| 11 | Historical and temporal | 10 | 10 | 0 | 0 |
| 12 | Unanswerable / insufficient evidence | 10 | 0 | 10 | 0 |
| | **Total** | **120** | **66** | **39** | **15** |

`answerability` is the label; `review_status` records whether a human checked it.
Nothing in this dataset is `human_reviewed`: 66 questions are `auto_verified`
(the evidence quote was matched programmatically) and 54 are `pending_review`
(derived rows, graph joins, or corpus-absence labels that a person should confirm).

## 3. Where ground truth comes from

The builder (`backend/scripts/build_benchmark_v3.py`) reads only stored data and
source files — never the answer pipeline:

| Verification method | Questions | What it means |
| --- | --- | --- |
| `verbatim_page_text+raw_html` | 46 | Quote is an exact substring of the stored page text *and* the expected facts also appear in the original HTML file after tag stripping |
| `verbatim_page_text` | 20 | Quote matched the stored page text (PDF/DOCX extraction, no raw-text check) |
| `database_row` | 9 | Answer is a stored row (procurement record, revision label) with no notice page |
| `graph_store` | 6 | Two-hop label verified by joining stored graph/relational rows |
| `corpus_absence` | 39 | Unanswerable because the corpus demonstrably lacks the data; the establishing count is recorded on the question |

No question is emitted unless its check passed; unparseable fields produce no
question rather than a guessed one.

## 4. Example questions and expected temporal behaviour

| Question | Category | Expected |
| --- | --- | --- |
| What notice identifier is recorded for the tender 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer'? | metadata | `2025/S 000-010515` |
| Which organisation is the contracting authority for 'Supporting Holocaust Survivor Testimony in Teaching'? | parties | the buyer named in the notice |
| When does the estimated contract period for 'NBI Energy Centre - Next Generation Infrastructure Programme' start? | dates | 15 June 2026 |
| What payment term is stated in the '06e110_tender_4' notice? | payment | 30 Days |
| What unit prices are listed in the pricing schedule for 'ACE - Provision of Financial Management System'? | pricing | refusal — no price rows exist |
| Which numbered clause in 'Dockless bike hire concession services Lot 1' sets out the payment obligations? | clauses | refusal — no clause numbering exists |
| What does the 'Loan Management System' notice say the appointed supplier will deliver? | obligations | the notice's description opening |
| Which revision label is recorded for the document '065b20_tender_6.pdf'? | amendments | the stored revision label (needs review) |
| Which supplier is recorded against '…' for buyer '…'? | relationships | the supplier on that award row (needs review) |
| Which compliance certificates are linked to the supplier associated with …? | graph | the certificate types joined via that supplier |
| As of 2026-11-12, what publication date was recorded for 'Loan Management System'? | temporal | the recorded publication date; the derived as-of must equal 2026-11-12 |
| Who was the winning bidder for the '…' tender? | unanswerable | refusal — no award result is recorded |

Temporal questions are scored on two things: the answer must contain the recorded
date, and the query planner's derived `as_of` must equal the labelled date. The
policy behind that derivation is in `docs/architecture/TEMPORAL_SEMANTICS.md`.

## 5. Metrics

| Metric | Definition |
| --- | --- |
| Recall@5 / Recall@10 | Share of labelled documents in the top-k retrieved hits |
| MRR | Reciprocal rank of the first labelled document |
| nDCG@10 | Binary-relevance nDCG over retrieved documents |
| Answer correctness | Every labelled fact appears in the answer (normalised containment) and it was not refused |
| Citation precision / recall | Share of displayed citations pointing at labelled documents / share of labelled documents cited |
| Faithfulness | Supported claims ÷ total claims from the pipeline's grounding pass |
| Unsupported claim rate | 1 − faithfulness |
| Correct refusal rate | Refusal matched the label (with precision and recall reported separately) |
| Temporal correctness | Derived as-of equals the labelled one and the expected facts appear (or a refusal was expected and given) |
| Latency / tokens | p50, p95, max wall time; prompt and completion tokens |

A metric with no applicable questions is `null` and excluded from the mean; the
number of contributing questions is reported beside every aggregate.

## 6. Baseline results

Recorded on 12 November 2026 against the pipeline as it stood when the benchmark
was built, before any tuning. Run: default strategy, `top_k=10`,
`qwen2.5-coder:7b` via a local OpenAI-compatible endpoint, `bge-small-en-v1.5`
embeddings, reranker enabled, 1,169.5 s for 120 questions. Raw outputs:
`results/baseline/{rows.jsonl,summary.json,report.md}`.

| Metric | Value | Contributing questions |
| --- | --- | --- |
| Recall@5 | 0.8676 | 70 |
| Recall@10 | 0.8676 | 70 |
| MRR | 0.8020 | 70 |
| nDCG@10 | 0.8187 | 70 |
| Page coverage | 0.9375 | 70 |
| Answer correctness | 0.3974 (31/78, Wilson 0.30–0.51) | 78 |
| Citation precision | 0.7740 | 43 |
| Citation recall | 0.5588 | 43 |
| Faithfulness | 0.6938 | 65 |
| Unsupported claim rate | 0.3062 | 65 |
| Correct refusal accuracy | 0.5812 (68/117) | 117 |
| Refusal precision / recall | 0.4286 / 0.7692 | 120 |
| Temporal correctness | 0.7000 (7/10) | 10 |
| Latency p50 / p95 / max | 9,151 / 16,279 / 32,180 ms | 120 |
| Prompt / completion tokens | 195,964 / 7,094 | 120 |

### Failed-question analysis

Taxonomy: 49 `refusal_failure`, 3 `generation_error`, 3 `error`, 2
`wrong_context_selected`, 1 `verification_miss`, 1 `temporal_error`, 0
`retrieval_miss`.

1. **Refusal is the dominant failure (49/120).** Of these, 40 were answerable
   questions the pipeline refused — concentrated in supplier/buyer relationships
   (7), obligations (5), payment terms (5), graph multi-hop (6) and dates (9).
   The award-relationship and certificate questions have no notice page in the
   corpus, so the pipeline's evidence gate refuses rather than answering from the
   structured row; that is a genuine product gap, not a metric artefact. The other
   9 were unanswerable questions answered anyway, mostly where the model produced
   a plausible value instead of refusing.
2. **Answer correctness is 31/78.** Metadata is the strongest category (0.72);
   dates (0.39), parties (0.375), obligations (0.0) and relationships (0.0) are
   weak. Part of the gap is the strict containment rule (a paraphrase is a miss),
   but the obligations and relationship failures are substantive: those answers
   do not contain the labelled fact even when the right document was retrieved.
3. **Three questions errored** (`PARTY-002`, `PARTY-006`, `REL-005`) with
   `Invalid isoformat string: ''`: some `procurement_records.award_date` values
   are empty strings, which SQLAlchemy's date processor rejects. This is a
   pre-existing data-handling defect; it was fixed in
   `app/retrieval/structured.py` *after* this baseline was recorded, so the
   baseline above still contains the errors.
4. **Temporal correctness is 7/10.** All ten derived the correct as-of date, but
   three answers failed: two refused a question whose publication date is in the
   document, and one answered without including the date. Temporal filtering is
   working; the generation/refusal gate is the weak link.
5. **Retrieval is not the bottleneck on this set** (recall 0.87, MRR 0.80), with
   two wrong-context selections in dates. The set labels one document per
   question, so recall@5 and recall@10 coincide.
6. **Latency ~9.7 s mean** is too slow for interactive use and is recorded, not
   optimised, in this run.

## 7. Reproducing

```bash
cd backend
python scripts/build_benchmark_v3.py                  # rebuild dataset + manifest
python scripts/run_benchmark_v3.py --top-k 10          # full 120-question run
python scripts/run_benchmark_v3.py --limit 10 --out var/smoke
python -m pytest tests/unit/test_benchmark_v3.py -q
```

The runner writes `rows.jsonl` (one row per question, including failures),
`summary.json` (aggregates, without per-question rows), `dataset_used.json` and a
markdown `report.md` with the failed-question analysis.

## 8. Known limitations

1. **No human adjudication.** Zero questions are human-reviewed. The 54
   `pending_review` labels exist precisely because a person still has to confirm
   them; until then, metrics on those categories are provisional.
2. **Containment scoring.** A correct paraphrase counts as a miss, and a number
   that coincidentally appears in the answer counts as a hit.
3. **The graph store is thin.** It holds 31 nodes and no persisted edge table, so
   the multi-hop labels are verified by SQL joins over the same rows.
4. **Only 15 notices** carry the field layout the builder parses, so metadata,
   party and date questions concentrate on those documents.
5. **No award linkage.** `procurement_records` is a separate award feed; questions
   about the winner of a specific notice are unanswerable by construction.
6. **Faithfulness is self-reported** by the pipeline's grounding pass; it is not
   an independent judge.
7. **Token cost is not priced.** Totals are reported; USD cost is `null` because
   no per-token price is configured.
