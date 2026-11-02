# Evaluation Trustworthiness Workflow

This document describes the systematic workflow for fixing over-refusal and making the evaluation trustworthy.

## Overview

**Goal**: Fix over-refusal and establish trustworthy metrics with statistical rigor.

**Status**: Phase 1 complete (hold-out split created). Ready for Phase 2 (oracle run).

## Phase 1: Hold-Out Split ✅ COMPLETE

Created stratified dev/held-out split:
- **Dev**: 90 questions (18 unanswerable) - for tuning and analysis
- **Held-out**: 40 questions (8 unanswerable) - frozen, do not read failures
- Stratified by category with fixed seed (42)
- Files: `data/evaluation/v2/questions_dev.json`, `questions_held_out.json`, `split.json`

**Command**:
```bash
cd backend
python scripts_phase3/create_holdout_split.py
```

## Phase 2: Oracle Run

**Purpose**: Measure how much of the failure is retrieval vs generation/verification.

Oracle mode provides gold chunks directly to the generator, bypassing retrieval. Comparing oracle vs current mode reveals:
- Retrieval gap: questions that fail in current but pass in oracle
- Generation gap: questions that fail in both modes

**Commands**:
```bash
cd backend

# Run both modes on dev set (takes ~30-45 min with local model)
python scripts_phase3/eval_v2.py --mode both --dataset dev --label dev-baseline

# Results will be in:
# - data/evaluation/v2/dev-baseline_dev_current_qwen2.5-coder-7b.json
# - data/evaluation/v2/dev-baseline_dev_oracle_qwen2.5-coder-7b.json
```

**Expected Output**: One paragraph stating:
- Answer correctness: current X% → oracle Y% (generation gap: Y-X points)
- Refusal precision: current A → oracle B (verification gap)
- Refusal recall: current C → oracle D
- Interpretation: "The X-point gap between current and oracle shows that Y% of failures are due to retrieval, Z% due to generation/verification"

**Analysis Script** (to be run after eval completes):
```bash
python scripts_phase3/analyze_oracle_gap.py --dev
```

## Phase 3: Over-Refusal Analysis (Dev Only)

**Purpose**: Understand *why* the system over-refuses.

For each false refusal on dev set:
1. Record category
2. Record which check refused (coverage, claim binding, grounding, answerability)
3. Record evidence status: in retrieved hits, in final context, or missing

**Output**: `docs/results/over-refusal.md` with:
- Table of all false refusals with diagnostic info
- Count by refusal reason
- Count by evidence location

**Command**:
```bash
cd backend
python scripts_phase3/analyze_over_refusal.py --dev --output ../docs/results/over-refusal.md
```

**STOP HERE** and review the table before changing code.

## Phase 4: Fix

Based on Phase 3 analysis, fix the largest cause first.

**Likely candidate**: Comparison/aggregation questions where passages for multiple suppliers don't all fit in context.

**Proposed fix**: Build comparison context with one passage per named supplier/product before applying token budget cut.

**Process**:
1. Identify the top cause from over-refusal.md
2. Implement fix in the relevant module (likely `app/agents/runtime.py` evaluate_evidence or context builder)
3. Re-run dev eval: `python scripts_phase3/eval_v2.py --mode current --dataset dev --label dev-after-fix-N`
4. **Keep fix only if**:
   - False refusals drop by ≥ 2
   - False answers on unanswerable questions do not rise
5. Repeat until false refusals < 10 on dev set

## Phase 5: Model Check

Run the same dev set with different models to isolate model contribution.

**Commands**:
```bash
# Instruct model (better instruction following, may reduce over-refusal)
LLM_MODEL=qwen2.5:7b-instruct python scripts_phase3/eval_v2.py --mode current --dataset dev --label dev-instruct

# Baseline coder model (current)
LLM_MODEL=qwen2.5-coder:7b python scripts_phase3/eval_v2.py --mode current --dataset dev --label dev-coder

# Larger model if available
LLM_MODEL=qwen2.5:14b-instruct python scripts_phase3/eval_v2.py --mode current --dataset dev --label dev-14b

# Compare
python scripts_phase3/compare_models.py dev-coder dev-instruct dev-14b
```

## Phase 6: Statistical Tests

Add paired bootstrap comparison for every before/after claim.

**Script**: `scripts_phase3/paired_bootstrap.py`

**Usage**:
```python
from scripts_phase3.paired_bootstrap import paired_bootstrap_test

result = paired_bootstrap_test(
    before_file="data/evaluation/v2/dev-baseline_dev_current_qwen2.5-coder-7b.json",
    after_file="data/evaluation/v2/dev-after-fix-1_dev_current_qwen2.5-coder-7b.json",
    metric="answer.correct",
    n_resamples=1000
)

print(f"Difference: {result['mean_diff']:.1%}")
print(f"95% CI: [{result['ci_low']:.1%}, {result['ci_high']:.1%}]")
print(f"Significant: {result['significant']}")  # True if CI excludes 0
```

Update `docs/RESULTS.md` to report confidence intervals for all comparisons.

## Phase 7: CI Gate Enhancement

Replace flat threshold with record/replay and statistical comparison.

**Changes**:
1. Record LLM responses for a fixed 40-question subset (stored in `data/evaluation/v2/ci_responses/`)
2. CI gate replays these responses (deterministic)
3. Gate compares using paired bootstrap:
   - Refusal precision drop > 5 points with 95% confidence → fail
   - Answer correctness drop > 5 points with 95% confidence → fail

**Implementation**: Update `scripts_phase3/eval_ci.py`

## Phase 8: Frontend Checks

Validate the UI under realistic conditions.

**Commands**:
```bash
# Start full stack
docker compose up -d
cd backend; uvicorn app.main:app --port 8000 &
cd ../frontend; npm run dev &

# Run accessibility, visual, and Lighthouse checks
cd frontend
E2E_PASSWORD=admin npx playwright test e2e/a11y-visual.spec.ts

# Lighthouse on production build
npm run build
npx vite preview --port 4173 &
npx lighthouse http://localhost:4173/ask --only-categories=performance,accessibility --output=json --output-path=../docs/results/lighthouse-ask.json

# Measure bundle sizes
npm run build
ls -lh dist/assets/*.js
```

**Record in RESULTS.md**:
- Accessibility: pass/fail for Ask, Documents, Login
- Lighthouse scores (performance, accessibility)
- Bundle sizes: entry bundle, three.js lazy chunk (gzipped)

## Phase 9: Final Held-Out Run

**After all fixes are complete on dev**, run held-out set once:

```bash
cd backend
python scripts_phase3/eval_v2.py --mode current --dataset held-out --label final-held-out

# Generate final report with dev and held-out columns
python scripts_phase3/generate_final_report.py --dev dev-after-fix-N --held-out final-held-out --output ../docs/RESULTS.md
```

## Results Format

`docs/RESULTS.md` should have:
- **Before/After table** with dev and held-out columns
- **Confidence intervals** for all comparisons (paired bootstrap)
- **Final held-out run** at the end
- **Explicit statement** of what is still not fixed

Example format:
```markdown
| Metric | Baseline (dev) | After fixes (dev) | Change (95% CI) | Held-out |
|--------|----------------|-------------------|-----------------|----------|
| Answer correctness | 68.3% | 75.6% | +7.3% [+3.2%, +11.4%] | 70.0% |
| Refusal precision | 0.478 | 0.667 | +0.189 [+0.08, +0.30] | 0.625 |
| False refusals | 24 | 12 | -12 [-18, -6] | 15 |
```

## What We Know (As of Phase 1)

From the current `docs/RESULTS.md`:
- 130 questions total: 104 answerable, 26 unanswerable
- Current metrics (full set): 68.3% correctness, 0.478 precision, 0.846 recall
- 28 refusal failures (mostly answerable questions refused)
- Main issue: comparison/aggregation questions refused due to coverage/binding checks

## Open Questions (To Be Answered by Phases 2-3)

1. How much of the 28 refusal failures are due to retrieval vs generation?
2. For the false refusals, which check is rejecting them? (coverage, binding, grounding)
3. Are the needed passages retrieved but dropped from context, or never retrieved?
4. Which specific failure mode is most common? (multi-supplier comparison, temporal reasoning, table extraction)

---

**Note**: This workflow is designed to be run incrementally with explicit decision points. Do not skip the STOP and review steps.
