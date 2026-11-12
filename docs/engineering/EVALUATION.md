# Retrieval Evaluation — recorded results

These are measured numbers from this working tree, not estimates. They were
produced by running the labelled question set through the real answer pipeline via
`POST /api/v1/evaluation/runs` and reading the stored rows back.

## Setup

| Item | Value |
| --- | --- |
| Corpus | 20 real UK Find a Tender (OCDS) tender notices, imported via the API |
| Indexed | 19 `indexed`, 1 `needs_review` (an empty portal page with no text) |
| Pages / chunks | 42 / 640 |
| Question set | `data/evaluation/golden_questions.json`, 12 questions (11 answerable, 1 unanswerable) |
| Labelling | hand-labelled from the notice text by the engineer preparing the evaluation |
| Generation mode | extractive for the baseline below; local `qwen2.5-coder:7b` for the re-measurement |
| Embeddings | `BAAI/bge-small-en-v1.5`, local CPU |
| Reranker | not exercised (cross-encoder was not loaded for these runs) |
| Runner | `backend/scripts/run_retrieval_evaluation.py --max-questions 12 --top-k 10` |

## Results — baseline (extractive, before the answerability fix)

| Metric | dense | sparse | hybrid |
| --- | --- | --- | --- |
| recall@5 | 0.5455 | 0.1818 | 0.5455 |
| recall@10 | 0.5455 | 0.1818 | 0.5455 |
| precision@5 | 0.3485 | 0.0409 | 0.2576 |
| MRR | 0.5455 | 0.1364 | 0.5455 |
| nDCG@10 | 0.5455 | 0.1483 | 0.5455 |
| keyword coverage | 0.4545 | 0.0909 | 0.5455 |
| answer correctness | 0.4545 | 0.0909 | 0.5455 |
| refusal correctness | 0.5833 | 0.5833 | 0.5833 |
| citation validity | 1.0 | 1.0 | 1.0 |
| mean latency (ms) | 20641 | 22374 | 21337 |
| questions | 12 | 12 | 12 |

Denominators differ per metric and are reported with each mean by the API
(`<metric>_n`): retrieval metrics use the 11 answerable questions, refusal
correctness uses all 12, citation validity only counts questions that displayed
citations (6). `page_coverage` and `reference_f1` are `null` because the set has
no page labels and no reference answers — they are excluded, not zeroed.

## Results — re-measured 11 November 2026 (LLM live, answerability fix in place)

Run with the same 12-question set, `--top-k 5`, generation through the local
model endpoint, and the paraphrase-aware coverage check:

| Metric | dense | hybrid_rerank |
| --- | --- | --- |
| recall@5 | 1.0 | 1.0 |
| recall@10 | 1.0 | 1.0 |
| precision@5 | 1.0 | 0.9394 |
| MRR | 1.0 | 1.0 |
| nDCG@10 | 1.0 | 1.0 |
| keyword coverage | 1.0 | 0.9545 |
| answer correctness | 1.0 | 0.9091 |
| refusal correctness | 0.9167 | 0.9167 |
| citation validity | 1.0 | 1.0 |
| mean latency (ms) | 4512 | 8625 |
| questions | 12 | 12 |

Two changes moved these numbers, and both are recorded above rather than
smoothed over: the answer pipeline can use the local model, and coverage now
recognises an entity written with different connectives and plurals. Before the
fix, a subject question whose notice said "… Recruitment and Management
Services" was refused for the question's "… recruitment service", even with six
independent documents in evidence.

Sparse and plain hybrid were not re-run; the baseline table above is still their
most recent measurement.

An end-to-end spot check outside the harness: "Which tender is for a master
vendor contingent workforce recruitment service?" returns the FSCS569 notice
with `status: supported`, one citation and two supporting documents (38.9 s cold,
including a 12 s query-understanding call), while "price in 2031 for the
Industrial Laptop X200" still refuses because the corpus holds no 2031 pricing.

`hybrid_rerank` is slower than `dense` here because the reranker adds a second
scoring pass and the model is called for understanding and generation; the
trade-off is precision@5 (1.0 vs 0.9394) and answer correctness (1.0 vs 0.9091)
favouring dense on this small set.

## What the numbers do and do not say

- **Dense retrieval carries this corpus.** The notices are unlabelled HTML pages
  with boilerplate menus; BM25 ranks the menu text highly (recall 0.18), which is
  why hybrid does not beat dense here.
- **Answer correctness tracks retrieval** (0.55 hybrid), because answers are
  extractive: if the passage is not retrieved, the answer cannot contain it.
- **Refusal correctness 0.58 is the weakest result.** Five answerable questions
  were refused or answered insufficiently under extractive mode, and the single
  unanswerable question is one data point — it cannot support a claim about
  refusal quality either way.
- **Latency ~21 s per question is too slow** for interactive use. This is a real
  finding: the pipeline pays embedding, BM25 index build and graph work per
  query on CPU. It has not been optimised or benchmarked beyond this run.
- **The set is 12 questions.** Wilson intervals at this size are wide (a 0.55
  rate spans roughly 0.28–0.79 at 95%); no headline quality claim should rest on
  it. It exists to catch regressions, not to rank the product.

## 120-question benchmark (TASK 4)

A separate, larger benchmark lives in `data/evaluation/benchmark_v3/` and is
documented in `docs/evaluation/BENCHMARK_120.md`: 120 questions across twelve
categories, with verbatim evidence and a recorded provenance trail. Its baseline
is stored under `data/evaluation/benchmark_v3/results/baseline/`. The numbers in
the tables above are the earlier 12-question set and are not comparable with it.

## Reproducing

```bash
cd backend
python scripts/run_retrieval_evaluation.py --experiments dense sparse hybrid --max-questions 12
```

Add `hybrid_rerank` (or `agentic`) only where the reranker/LLM endpoints are
available; the runner stores whatever the pipeline actually produced, including
`error` rows for questions that failed.
