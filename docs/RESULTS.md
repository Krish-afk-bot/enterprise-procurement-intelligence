# Results

Measured results for the review-driven work. Every number below comes from a
command in this repository; nothing here is estimated.

## Evaluation setup

| | |
|---|---|
| Dataset | 130 labelled questions in `data/evaluation/v2/questions.json` (>=20% unanswerable/adversarial, expected facts, documents and pages) |
| Generator | `qwen2.5-coder:7b` at a local OpenAI-compatible endpoint |
| Embeddings / reranker | `BAAI/bge-small-en-v1.5`, cross-encoder reranker over the top 20 |
| Isolation | SQLite eval database and local vector/storage under `backend/var/eval-v2/`; the production corpus is not used |
| Run date | 2026-11-02 |
| Artifacts | `data/evaluation/v2/phase-2-start_*.json`, `phase-2-final_*.json`, `ci_baseline.json` |

Baseline is the pipeline as it stood at the start of Phase 2. Final is the same
pipeline after the Phase 2 changes and the three verification fixes committed in
`e7a0066`.

## Before / after

| Metric | Baseline | Final | Change |
|---|---|---|---|
| Retrieval recall@10 | 73.9% | 73.4% | -0.5 pt |
| Hit rate@10 | 76.1% | 76.1% | 0 |
| MRR | 0.621 | 0.631 | +0.010 |
| nDCG@10 | 0.640 | 0.649 | +0.009 |
| Answer correctness | 68.3% (71/104) | 68.3% (71/104) | 0 |
| Refusal precision | 0.500 (tp21/fp21) | 0.478 (tp22/fp24) | -0.022 |
| Refusal recall | 0.808 (tp21/fn5) | 0.846 (tp22/fn4) | +0.038 |
| Citation precision | 0.316 | 0.545 | **+0.229** |
| Latency p50 | 10,154 ms | 6,932 ms | **-32%** |
| Latency p95 | 15,349 ms | 10,464 ms | **-32%** |
| Latency max | 49,804 ms | 43,751 ms | -12% |
| Failures | 38 | 37 | -1 |

The answer-correctness and refusal columns are the honest picture: the Phase 2
changes did not move overall answer correctness, and refusal precision is 2.2
points below baseline because the pipeline now refuses four questions it used to
answer (recall rose 3.8 points). The three fixes recovered the interim
regression: the run immediately after the Phase 2 changes scored 63.5% answer
correctness and 0.44 refusal precision, so the fixes restored +4.8 points of
correctness and +3.8 points of precision while keeping the citation and latency
gains. What remains is over-refusal, not under-refusal.

## Failure taxonomy

| Label | Baseline | Final |
|---|---|---|
| `refusal_failure` | 26 | 28 |
| `generation_error` | 7 | 1 |
| `retrieval_miss` | 4 | 3 |
| `verification_miss` | 1 | 2 |
| `wrong_context_selected` | 0 | 3 |
| `error` | 0 | 0 |
| **Total** | **38** | **37** |

`generation_error` fell from 7 to 1: most fluent-but-wrong drafts are now either
bound to evidence or replaced by a refusal. The remaining bucket is
`refusal_failure`, almost entirely answerable questions refused after a coverage
or binding check (for example comparison questions whose supplier passages rank
below the context cut).

## Verifications fixes and their effect

| Fix | Defect | Effect in the final run |
|---|---|---|
| Unresolved LLM entities must appear in the question | A 7B planner invented `supplier1`/`supplier2` for "which supplier…", creating unsatisfiable constraints | Removed the forced refusal on that class; contributes to the +4.8 pt correctness recovery |
| Runner reads `total_claims`/`supported_claims` | Every row reported 0/0 grounding, so verification outcomes were mislabelled | Grounding is now scored; `verification_miss` is measurable (2) instead of hidden |
| Refusal replaces the draft regardless of supersession conflicts | A refusal status could sit beside the ungrounded draft, scoring it correct | Removed the status/answer contradiction; the four `fn` → `tp` shift is visible in recall |

Regression tests: `backend/tests/unit/test_query_understanding.py`
(hallucinated supplier/product placeholders),
`backend/tests/unit/test_evaluation_v2.py` (grounding keys),
`backend/tests/unit/test_refusal_correctness.py` (supersession-conflict refusal
replacement).

## CI gate

`python scripts_phase3/eval_ci.py` runs the same 130 questions on the
deterministic stack (hashing embeddings, lexical reranker, extractive
generation) and fails when a tracked metric drops more than three points below
`data/evaluation/v2/ci_baseline.json`.

```
retrieval.recall_at_10 0.7609   retrieval.mrr 0.7337   answer.correct 0.6154
refusal.precision      1.0000   refusal.recall 0.4615  citation.precision 0.3958
CI gate passed (exit 0)
```

Every metric equals the committed baseline, so the gate is green on this branch.
The deterministic stack refuses only when the extractive answer has no
supporting evidence, which is why its refusal recall is lower than the
LLM run's; it measures the pipeline, not the model.

## Frontend

| Check | Result |
|---|---|
| Pages over 300 lines | none; AdminPage 66, DocumentDetailPage 214, DocumentsPage 270 |
| TypeScript | `npx tsc --noEmit` exit 0 |
| Unit/component tests | 33 passed (Vitest) |
| Entry bundle, `VITE_ENABLE_WORLD=false` | 467.1 KiB |
| Entry bundle, `VITE_ENABLE_WORLD=true` | 478.0 KiB |
| three.js | 838.2 KiB lazy chunk in both builds; never in the entry bundle |
| axe, WCAG 2.1 A/AA (Ask, Documents, Login) | **3/3 pass** after fixing three real defects |
| Visual snapshots, light/dark (Ask, Documents, Login) | **6/6 pass**; baselines committed |
| Lighthouse, production preview, Ask | performance **89**, accessibility **100**; FCP 1.7 s, LCP 2.1 s, TBT 40 ms, CLS 0.188 |

The 3D band is off by default and its scenes are separate lazy chunks; enabling
the flag adds 10.9 KiB to the entry (the loader) and fetches the three.js chunk
only when the world mounts.

The accessibility run found real defects rather than only confirming the pages:
the sidebar wrapped `NavLink` in `TooltipTrigger asChild`, which passes
`className` through as a string, so React Router's `className` callback never
ran and every item carried both the active and inactive classes (muted text on
the active background, 4.46:1). The login brand link and the account button had
`aria-label`s that omitted their visible text (WCAG 2.5.3). All three are fixed;
the checks now pass and are committed as a regression gate.

## Not fixed / not measured

- Refusal precision remains 2.2 points below baseline: the stricter coverage and
  claim binding over-refuse some comparison and aggregation questions. The next
  step is to widen the comparison context (one passage per named supplier) rather
  than relax the checks.
- p50 latency is 6.9 s, above the 5 s target. It improved 32% but the local
  cross-encoder and generation dominate.
- OCR/VLM paths, production models and the oracle-mode after-run were not part
  of this final measurement.
- Lighthouse CLS is 0.188, above the 0.1 "good" threshold; the shifting
  element was not investigated in this pass.
- The checks ran against the local SQLite dev database and a production preview
  build, not the full Docker Compose stack.

## Reproduce

```bash
# Full evaluation (local model required, ~15 minutes)
cd backend
python scripts_phase3/eval_v2.py --mode current --label phase-2-final --write-taxonomy

# Deterministic CI gate (no model, no Docker)
python scripts_phase3/eval_ci.py

# Backend tests
python -m pytest tests/unit -q

# Frontend
cd ../frontend
npm ci
npx tsc --noEmit
npx vitest run
npm run build
VITE_ENABLE_WORLD=true npm run build   # compare dist/assets/index-*.js

# Accessibility and visual checks (requires backend :8000, frontend :5173,
# seeded admin account and the Docker Compose services)
# E2E_PASSWORD defaults to the Compose seed; set it for the local dev database.
E2E_PASSWORD=admin-local-password npx playwright test e2e/a11y-visual.spec.ts

# Lighthouse against the built app (the Ask page needs a signed-in session)
npm run build
npx vite preview --port 4173
npx lighthouse http://localhost:4173/ask --only-categories=performance,accessibility
```
