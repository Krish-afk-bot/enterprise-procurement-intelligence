# EPI benchmark v4 — full re-ingestion and 150-question run

- Git commit at freeze: `3d15fbf` (the deterministic-chunk-id bug fix was committed after the runs).
- Code commit: `57b4bfe62d836f1f9ab890f198235b117825ff33`.
- Dataset SHA-256: `0f6fa03db3b652db31961f364dcaf651fec29dcb1c4943c4c9e49c05f53606d3` (frozen before Run A).
- Dataset: 150 questions — 94 answerable, 41 unanswerable, 15 needs_review.
- Corpus: 20 source documents, 19 indexed, 1 empty portal page; 42 pages; 655 active chunks.

## 1. Ingestion and coverage

| Metric | Value |
| --- | --- |
| Documents rebuilt | 20 |
| Indexed / needs_review | 19 / 1 (`0664eb_tender_13.html` is an empty page) |
| Pages with text / with ≥1 chunk | 41 / 41 |
| Chunks | 655 |
| Character coverage (5-gram, overlap excluded) | 98.1% |
| Documents below 99% char coverage | 2 |
| Idempotent chunk ids | True (count 4 → 4) |

Below target: `065b20_tender_6.pdf` at 93.9% (page headers/footers such as `PROC/TD/04 v1.2 … Page N of 22` are removed by the parser and are not tagged as boilerplate); `064670_tender_1.html` at 97.2% (portal chrome). `069b28_tender_16.docx` yields only 409 characters from a 119 KB file: its tender body is not in the DOCX text layer (embedded object/image), so it is a real extraction gap, not a chunking gap. No text chunk stores character offsets or bounding boxes: a schema gap, reported rather than worked around.

## 2. Retrieval (Run A, 150 questions)

| Metric | Value | n |
| --- | --- | --- |
| Recall@1 | 81.6% | 98 |
| Recall@3 | 92.9% | 98 |
| Recall@5 | 94.9% | 98 |
| Recall@10 | 98.0% | 98 |
| MRR | 0.8778 | 98 |
| nDCG@10 | 0.9028 | 98 |

Recall@15 is not reported: the run retrieved 10 candidates, the same cap as the baseline. Raising it would change the configuration being measured.

## 3. Answer quality

| Metric | Run A (150) | n |
| --- | --- | --- |
| Literal fact containment | 44.0% (35.1–53.4) | 109 |
| Normalized fact match | 44.0% (35.1–53.4) | 109 |
| LLM judge correctness | 32.5% (13/40) | 40 |

The judge is `qwen2.5-coder:7b` — the same model that generated the answers, because it is the only model installed. It is stricter than literal containment and is not independent. Excluding the 15 `needs_review` v3 items, answer accuracy is 50.0% on 94 questions.

## 4. Citations and faithfulness

| Metric | Value | n |
| --- | --- | --- |
| Citation precision | 0.6957 | 85 |
| Citation recall | 0.7551 | 85 |
| Answers with all citations valid | 100.0% (67.6–100.0) | 8 |
| Pipeline faithfulness | 0.6734 | 99 |
| Unsupported-claim rate | 0.3266 | 99 |

No independent faithfulness check was run beyond the judge; citation validity is the verifier's own verdict, not a second reader.

## 5. Refusals (refuse = positive class)

| Metric | Run A |
| --- | --- |
| Correct refusals (TP) | 33 |
| False refusals (FP, answerable refused) | 34 |
| False answers (FN, unanswerable answered) | 8 |
| Correct answers (TN) | 75 |
| Precision | 0.4925 |
| Recall | 0.8049 |
| Accuracy | 72.0% (64.3–78.6) |

## 6. Baseline comparison on the identical 120 questions (Run B)

| Metric | Old baseline (recomputed) | Run B | Change | Verdict |
| --- | --- | --- | --- | --- |
| Answer correct, literal | 38.3% (28.4–49.2) | 46.9% (36.4–57.7) | +8.6 pp | within noise (CIs overlap) |
| Recall@5 | 86.8% | 94.3% | +7.5 pp | real (deterministic retriever) |
| Recall@10 | 86.8% | 97.1% | +10.4 pp | real |
| MRR | 0.779 | 0.8864 | +0.107 | real |
| Refusal precision | 0.4286 | 0.5345 | +10.6 pp | not separable from noise |
| Refusal recall | 0.7692 | 0.7949 | +2.6 pp | small |
| Latency p50 (ms) | 9151 | 7812 | — | machine-load dependent |

The old report's 86.8% Recall@5 and Recall@10 were identical because no expected document first appeared at rank 6–10: all hits were already in the top five. It was not a cut-off bug.

## 7. Variance (50-question stratified subset)

| Run | Answer (normalized) | Recall@10 | p50 ms |
| --- | --- | --- | --- |
| A, restricted to subset | 38.9% | 100.0% | 9244 |
| C1 | 38.9% | 100.0% | 8970 |
| C2 | 36.1% | 100.0% | 8775 |

Answer accuracy ranges over 2.8 pp across repeats; retrieval is identical. Two full 150-question repeats would have taken another hour; the variance estimate is therefore from a 50-question subset and is a limitation, not a full-set confidence interval.

## 8. Categories (Run A)

| Category | Q | Answer (normalized) | Recall@10 | Citation P | Refusal P/R | p50 ms |
| --- | --- | --- | --- | --- | --- | --- |
| amendments | 8 | 0.0% | 100.0% | 1.0 | 0.875/1.0 | 8177 |
| award_criteria | 7 | 0.0% | 100.0% | 0.7083 | 0.0/None | 11907 |
| clauses | 8 | — | — | None | 1.0/0.875 | 6100 |
| compliance_check | 1 | 100.0% | 100.0% | 1.0 | None/None | 13828 |
| contract_terms | 2 | 0.0% | 100.0% | 1.0 | 0.0/None | 17767 |
| dates_and_duration | 23 | 52.2% | 100.0% | 0.5703 | 0.0/None | 8453 |
| document_metadata | 18 | 77.8% | 100.0% | 0.8115 | 0.0/None | 5566 |
| graph_multi_hop | 6 | 16.7% | 66.7% | 0.0 | 0.0/None | 16810 |
| historical_temporal | 10 | 70.0% | 100.0% | 0.875 | 0.0/None | 10759 |
| obligations | 8 | 0.0% | 100.0% | 0.9286 | 0.0/None | 10180 |
| parties | 11 | 54.5% | 100.0% | 0.606 | 0.0/None | 9267 |
| payment_terms | 8 | 50.0% | 50.0% | 1.0 | 0.6667/0.3333 | 6332 |
| pricing_schedules | 8 | — | — | None | 1.0/1.0 | 5855 |
| procurement_values | 10 | 50.0% | 100.0% | 0.5033 | 0.0/None | 9509 |
| structured_data | 2 | 50.0% | 100.0% | 1.0 | 0.0/None | 13791 |
| supplier_buyer_relationships | 8 | 0.0% | — | None | 0.0/None | 16286 |
| unanswerable | 10 | — | — | None | 1.0/0.7 | 11364 |
| unanswerable_near_miss | 2 | — | — | None | 1.0/1.0 | 8714 |

Worst categories by answer accuracy where at least one answerable question exists: award_criteria, obligations and amendments (0%), payment_terms (50%), procurement_values (50%). These are numeric/dense-table and clause questions where the retriever found the document but the generator or verifier failed on the passage.

## 9. Routing, classification and MCP

- Rule-based intent accuracy on 45 fresh hand-labelled queries: **40.0%**. Weakest: temporal_change 0/5, relationship 1/5, document_lookup 1/5; best: compliance_check 4/5, general 4/5.
- Routing: 148/150 generations used the large model; structured/SQL engine ran on 87 questions and the graph on 17. No small LLM is installed, so its fallback path could not be exercised. The VLM is configured but no vision model exists: 5 PDF pages logged HTTP 404 and kept text.
- MCP: all 9 tools advertised; 9/9 tool calls succeeded; all 4 negative cases rejected; 22 audit rows written. The agent-over-MCP arm was not run (no validated tool-calling model; the tools search titles/structured fields, not chunk text).

## 10. Failure taxonomy (Run A)

| Label | Count |
| --- | --- |
| none | 81 |
| refusal_failure | 42 |
| verification_miss | 7 |
| wrong_context_selected | 8 |
| generation_error | 11 |
| temporal_error | 1 |

### Top 20 failures

| id | label | question | expected | answer (truncated) |
| --- | --- | --- | --- | --- |
| META-005 | refusal_failure | Which CPV code leads the classification list for 'Gallery 33 - 3D and 2D Exhibit | 79415200 - Design consultancy services | Answer I couldn't verify this from the available procurement documents.  Verification Single source, not corroborated |
| META-010 | refusal_failure | Which CPV code leads the classification list for 'Supporting Holocaust Survivor  | 80000000 - Education and training services | I couldn't verify this from the available procurement documents.  Why: The evidence retrieved did not directly support the generated stateme |
| META-014 | verification_miss | Which main procurement category is recorded for 'Provision of a Human Resource S | Goods | Answer The main procurement category recorded for 'Provision of a Human Resource System & Duties Management System' is Services.  Evidence - |
| META-015 | refusal_failure | Which CPV code leads the classification list for 'Provision of a Human Resource  | 48000000 - Software package and information systems | I couldn't verify this from the available procurement documents.  Why: The evidence retrieved did not directly support the generated stateme |
| PARTY-002 | refusal_failure | Who is the named contact for the 'Gallery 33 - 3D and 2D Exhibition Design/Lead  | Chloe Higgins | Answer I couldn't verify this from the available procurement documents.  Verification Single source, not corroborated |
| PARTY-003 | verification_miss | Which region is recorded for the contracting authority of 'Gallery 33 - 3D and 2 | UKI33 - Kensington & Chelsea and Hammersmith & Fulham | Answer The region recorded for the contracting authority of 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer' is London.  Evidence -  |
| PARTY-006 | refusal_failure | Who is the named contact for the 'Supporting Holocaust Survivor Testimony in Tea | Anne Hardy | Answer I couldn't verify this from the available procurement documents.  Verification Single source, not corroborated |
| PARTY-007 | refusal_failure | Which region is recorded for the contracting authority of 'Supporting Holocaust  | UKI32 - Westminster | Answer I couldn't verify this from the available procurement documents.  Verification Single source, not corroborated |
| PARTY-010 | refusal_failure | Which region is recorded for the contracting authority of 'Provision of a Human  | UKG13 - Warwickshire | Answer I couldn't verify this from the available procurement documents.  Verification Single source, not corroborated |
| DATE-001 | refusal_failure | When does the estimated contract period for 'Gallery 33 - 3D and 2D Exhibition D | 7 July 2025 | Answer I couldn't verify this from the available procurement documents.  Verification Single source, not corroborated |
| DATE-002 | refusal_failure | When does the estimated contract period for 'Gallery 33 - 3D and 2D Exhibition D | 1 August 2027 | I couldn't verify this from the available procurement documents. |
| DATE-003 | wrong_context_selected | What contract duration is estimated for 'Gallery 33 - 3D and 2D Exhibition Desig | 2 years, 26 days | Answer The contract duration for 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer' is estimated to be 4 years, starting from 1 Octobe |
| DATE-006 | wrong_context_selected | When does the estimated contract period for 'Supporting Holocaust Survivor Testi | 1 August 2025 | Answer The estimated contract period for 'Supporting Holocaust Survivor Testimony in Teaching' starts on 1 September 2027.  Evidence - 069a8 |
| DATE-007 | wrong_context_selected | When does the estimated contract period for 'Supporting Holocaust Survivor Testi | 31 March 2026 | Answer The estimated contract period for 'Supporting Holocaust Survivor Testimony in Teaching' ends on 15 September 2031.  Evidence - 0679c4 |
| DATE-012 | generation_error | When does the estimated contract period for 'Provision of a Human Resource Syste | 31 July 2032 | Answer The estimated contract period for 'Provision of a Human Resource System & Duties Management System' ends on 1 August 2035.  Evidence  |
| DATE-016 | generation_error | When does the estimated contract period for 'NBI Energy Centre - Next Generation | 11 January 2028 | Answer The estimated contract period for 'NBI Energy Centre - Next Generation Infrastructure Programme' ends on 15 September 2031, as per th |
| DATE-017 | wrong_context_selected | What award decision date is estimated for 'NBI Energy Centre - Next Generation I | 8 May 2026 | Answer The estimated award decision date for 'NBI Energy Centre - Next Generation Infrastructure Programme' is 15 September 2026.  Evidence  |
| PAY-001 | refusal_failure | What payment term is stated in the '06e110_tender_4' notice? | 30 Days | I couldn't verify this from the available procurement documents.  Why: The evidence retrieved did not directly support the generated stateme |
| PAY-003 | refusal_failure | What payment terms does the 'Gallery 33 - 3D and 2D Exhibition Design/Lead Desig | None | Answer The payment terms specified in the 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer' notice are 30 Days.  Evidence - 06e110_te |
| PAY-004 | refusal_failure | What payment terms does the 'Supporting Holocaust Survivor Testimony in Teaching | None | Answer The 'Supporting Holocaust Survivor Testimony in Teaching' notice specifies payment terms of 30 Days.  Evidence - 06e110_tender_4 — p. |

## 11. Configuration

| Setting | Value |
| --- | --- |
| Database | SQLite `backend/var/epi.db` |
| Vector store | local numpy cosine index (`procurement_chunks`, 384d) |
| Graph | local SQLite property graph |
| Cache | in-memory |
| Object storage | local filesystem |
| Generation | qwen2.5-coder:7b via Ollama, temperature 0.1, max 2048 tokens |
| Small LLM | not configured |
| VLM | configured, no vision model available |
| Embeddings | BAAI/bge-small-en-v1.5, 384 dimensions, CUDA |
| Reranker | BAAI/bge-reranker-v2-m3 (cross-encoder) |
| Retrieval | dense 50 + BM25 50, RRF k=45, rerank 15, context 12 chunks / 6000 tokens, top_k 10 |
| Chunking | target 320, max 700, overlap 60 |
| Hardware | Windows, Python 3.13, CUDA GPU |

## 12. Reproduction

```sh
cd backend
python scripts/reindex_corpus.py                  # rebuild + coverage_report.*
python scripts/build_benchmark_v4.py              # questions.json + SHA-256
python scripts/intent_eval.py
python scripts/verify_mcp_all.py
python scripts/run_benchmark_v3.py --dataset-dir ../data/evaluation/benchmark_v4 \
  --out ../data/evaluation/benchmark_v4/results/run_A --top-k 10 --quiet
python scripts/run_benchmark_v3.py --dataset-dir ../data/evaluation/benchmark_v3 \
  --out ../data/evaluation/benchmark_v4/results/run_B --top-k 10 --quiet
python scripts/run_benchmark_v3.py --dataset-dir ../data/evaluation/benchmark_v4/subset50 \
  --out ../data/evaluation/benchmark_v4/results/run_C_1 --top-k 10 --quiet
python scripts/judge_answers.py --sample 40
python scripts/analyze_benchmark_v4.py
```

## 13. Limitations

- Labels are not human-adjudicated. 15 v3 labels remain `needs_review`; 66 other v3 answerable labels were machine-checked against the cited page, and all 30 new labels passed the same check. No reviewer has signed off, and `review_sample.csv` exists for that review.
- The judge shares the generator's model; its 32.5% is not an independent correctness estimate.
- Generation ran at temperature 0.1, not 0, because that is the configured production value; variance was measured instead.
- Variance is measured on a 50-question subset, not the full 150.
- 069b28_tender_16.docx content is missing from its text layer; the 409 characters extracted are the whole available text.
- The old benchmark's Recall@5 = Recall@10 was verified as real (no rank 6–10 hits), not a metric bug.
- The corpus is 20 UK tender notices of one type; results do not generalise to other document families.
