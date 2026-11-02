# Phase 3 Preparation - Over-Refusal Analysis

**Status**: Oracle evaluation running (31/90 complete as of 00:50)  
**Estimated completion**: 10-15 minutes  
**Current failures (dev set)**: 26 total, 20 refusal failures

---

## What Happens When Oracle Completes

### Automatic Actions

The `run_phase3_analysis.ps1` script will:

1. **Generate quick summaries** of both current and oracle runs
2. **Analyze oracle gap** to quantify retrieval vs generation failures  
3. **Generate over-refusal diagnostic table** with:
   - All false refusals listed
   - Refusal reason for each (coverage_check, claim_binding, grounding_score_low, etc.)
   - Evidence location (not_retrieved, retrieved_not_in_context, in_context)
   - Category and expected documents

### Commands to Run

```powershell
cd backend

# Run full Phase 3 analysis
.\scripts_phase3\run_phase3_analysis.ps1

# Or run components individually:
python scripts_phase3/quick_summary.py data/evaluation/v2/dev-baseline_dev_current_qwen2.5-coder-7b.json
python scripts_phase3/analyze_oracle_gap.py --dev --label dev-baseline
python scripts_phase3/analyze_over_refusal.py --dev --output ../docs/results/over-refusal-dev.md
```

---

## Expected Outputs

### 1. Oracle Gap Analysis (`docs/results/oracle-gap-dev.md`)

**Will tell us:**
- How many failures are due to retrieval (fixed by gold chunks)
- How many persist in oracle (generation/verification issues)
- Percentage split between retrieval and generation

**Example interpretation:**
```
"The 15% correctness gap between current and oracle mode indicates that
12 failures (46%) are due to retrieval (missing or dropped evidence).
14 failures (54%) persist in oracle mode, indicating generation or
verification issues that cannot be fixed by better retrieval alone."
```

### 2. Over-Refusal Table (`docs/results/over-refusal-dev.md`)

**Will show:**
```markdown
## Summary

Total false refusals: 20

### By Refusal Reason:
- coverage_check: 12
- claim_binding: 5
- grounding_score_low: 2
- no_supported_claims: 1

### By Evidence Location:
- retrieved_not_in_context: 8
- in_context: 7
- not_retrieved: 5

### By Category:
- comparison: 9
- aggregation: 6
- temporal: 3
- compliance: 2

## Detailed Table

| ID | Category | Refusal Reason | Evidence Location | Expected Docs |
|----|----------|----------------|-------------------|---------------|
| v2-comp-001 | comparison | coverage_check | retrieved_not_in_context | supplier_a_master_contract..., supplier_b... |
| v2-comp-005 | comparison | coverage_check | retrieved_not_in_context | supplier_a_master_contract..., supplier_b... |
...
```

---

## Decision Points

### ⚠️ STOP AND REVIEW

Before implementing any fixes, answer these questions from the over-refusal table:

1. **What is the most common refusal reason?**
   - If `coverage_check`: The system thinks evidence is incomplete
   - If `claim_binding`: The query understanding step failed to extract entities
   - If `grounding_score_low`: Generated answer doesn't match evidence well enough

2. **Where is the evidence?**
   - If `retrieved_not_in_context`: Passages are retrieved but dropped (context builder issue)
   - If `in_context`: Evidence is present but verification rejects it (too strict)
   - If `not_retrieved`: Evidence never made it to top-k (retrieval issue)

3. **Which categories are affected?**
   - If mostly `comparison`: Multi-supplier questions need special handling
   - If mostly `aggregation`: SQL path may be failing, falling back to retrieval
   - If scattered: System-wide verification threshold may be too strict

---

## Fix Strategy Template

Based on the table, use this decision tree:

### If `coverage_check` is top cause AND `retrieved_not_in_context` is common:
**Root cause**: Context builder drops relevant passages  
**Fix**: Build comparison/aggregation context with one passage per named entity before token budget cut  
**Module**: `app/agents/runtime.py` → `evaluate_evidence()`  
**Validation**: False refusals should drop without increasing false answers

### If `claim_binding` is top cause:
**Root cause**: Query understanding fails to extract entities  
**Fix**: Improve entity extraction or fallback when LLM planner uses placeholders  
**Module**: `app/agents/runtime.py` → `understand()`  
**Validation**: Check if unresolved entities are now satisfied

### If `grounding_score_low` is top cause AND `in_context` is common:
**Root cause**: Verification threshold too strict  
**Fix**: Relax grounding threshold from 0.5 to 0.4 (with safety checks)  
**Module**: `app/agents/runtime.py` → `verify()`  
**Validation**: Ensure no increase in false answers on unanswerable questions

---

## After Choosing a Fix

### Implementation Checklist

1. **Implement the fix** in the identified module
2. **Add a test** covering the specific failure mode
3. **Re-run dev evaluation**:
   ```powershell
   python scripts_phase3/eval_v2.py --mode current --dataset dev --label dev-after-fix-1
   ```
4. **Compare statistically**:
   ```powershell
   python scripts_phase3/paired_bootstrap.py `
       --before data/evaluation/v2/dev-baseline_dev_current_qwen2.5-coder-7b.json `
       --after data/evaluation/v2/dev-after-fix-1_dev_current_qwen2.5-coder-7b.json `
       --metric refusal.false_refusal
   ```
5. **Validate improvement**:
   - False refusals dropped by ≥2 with 95% confidence?
   - No increase in false answers (FN on unanswerable)?
   - If yes: Keep fix and commit
   - If no: Revert and try a different approach

---

## Iteration Strategy

### Fix Priority Order

1. **Address top 1 cause first** (highest count in refusal reason table)
2. **Validate** with paired bootstrap
3. **If improvement is significant**, proceed to #2 cause
4. **Repeat** until false refusals < 12 on dev set (current: 20)

### Stop Conditions

- **Success**: False refusals < 12, answer correctness > 75%, validated on held-out
- **Diminishing returns**: Each fix yields <2 point improvement
- **Regression**: False answers on unanswerable questions increase

---

## Documentation

After each fix:

1. **Update RESULTS.md** with new metrics and confidence intervals
2. **Record fix details** in commit message
3. **Track iteration** in a fixes log:
   ```markdown
   ## Fix Log
   
   ### Fix 1: Comparison context builder
   - Cause: coverage_check, retrieved_not_in_context (8 cases)
   - Change: Reserve one passage per supplier before token cut
   - Result: False refusals 20 → 14 (CI: [-8, -4], p<0.05)
   - Commit: abc1234
   ```

---

## Current Baseline (Before Fixes)

From `dev-baseline_dev_current` run:

- **Total failures**: 26
- **Refusal failures**: 20 (77% of failures)
- **Retrieval misses**: 2
- **Context selection**: 2
- **Verification misses**: 2

**Target after fixes:**
- Refusal failures: <10
- Answer correctness: >75%
- No regression on unanswerable questions

---

## Ready to Start

Once oracle completes:

```powershell
cd backend

# Run Phase 3 analysis
.\scripts_phase3\run_phase3_analysis.ps1

# Review the output
code ..\docs\results\over-refusal-dev.md
code ..\docs\results\oracle-gap-dev.md

# Identify top cause and plan fix
# (Do NOT implement yet - review tables first)
```

---

**Next**: Wait for oracle evaluation to complete, then run Phase 3 analysis and review the diagnostic tables.
