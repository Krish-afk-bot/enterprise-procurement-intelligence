# Next Steps - Evaluation Improvement

**Current Status**: Oracle evaluation running (62/90, ~69% complete)  
**Estimated Completion**: 5-10 minutes  
**All Infrastructure**: ✅ Complete and committed

---

## Immediate Actions (Once Oracle Completes)

### 1. Run Phase 3 Analysis (Automated)

```powershell
cd backend
.\scripts_phase3\run_phase3_analysis.ps1
```

**This will generate:**
- Quick summaries of current and oracle runs
- Oracle gap analysis → `docs/results/oracle-gap-dev.md`
- Over-refusal diagnostic table → `docs/results/over-refusal-dev.md`

**Expected Runtime**: < 1 minute

---

### 2. Review Diagnostic Tables ⚠️ STOP GATE

**DO NOT SKIP THIS STEP**

Open and read:
1. `docs/results/over-refusal-dev.md` - The key diagnostic output
2. `docs/results/oracle-gap-dev.md` - Understanding retrieval vs generation

**Look for:**
- Top refusal reason (likely `coverage_check`)
- Top evidence location (likely `retrieved_not_in_context`)
- Most affected category (likely `comparison`)

---

### 3. Plan Your Fix (Use Decision Tree)

Refer to `docs/phase3-preparation.md` for the decision tree.

**Most Likely Scenario:**
- **Top cause**: `coverage_check` (12+ cases)
- **Evidence**: `retrieved_not_in_context` (8+ cases)
- **Category**: `comparison` (9+ cases)

**Root Cause**: Context builder drops supplier passages for multi-entity questions

**Recommended Fix**:
```python
# In app/agents/runtime.py → evaluate_evidence()
# Before applying token budget:
# 1. Extract named entities from query (suppliers, products)
# 2. Reserve one passage per entity
# 3. Fill remaining budget with other passages
# 4. Apply token cut only to non-reserved passages
```

---

### 4. Implement First Fix

**Steps:**
1. Open `backend/app/agents/runtime.py`
2. Find `evaluate_evidence()` method
3. Implement entity-aware context building
4. Add test case in `backend/tests/`
5. Commit with descriptive message

**Estimated Time**: 1-2 hours

---

### 5. Validate Fix Statistically

```powershell
cd backend

# Re-run dev evaluation (~30 minutes)
python scripts_phase3/eval_v2.py --mode current --dataset dev --label dev-after-fix-1

# Statistical comparison
python scripts_phase3/paired_bootstrap.py `
    --before data/evaluation/v2/dev-baseline_dev_current_qwen2.5-coder-7b.json `
    --after data/evaluation/v2/dev-after-fix-1_dev_current_qwen2.5-coder-7b.json `
    --metric refusal.false_refusal

# Expected output:
# Mean difference: -8.0 (20 → 12 false refusals)
# 95% CI: [-12, -4]
# Significant: True
```

**Keep fix if:**
- ✅ False refusals drop ≥2 with 95% confidence
- ✅ No increase in false answers on unanswerable
- ✅ Answer correctness maintained or improved

**If not**, revert and try alternative approach

---

### 6. Iterate

Repeat steps 4-5 for the #2 cause, #3 cause, etc.

**Stop when:**
- False refusals < 12 (currently 20)
- Answer correctness > 75% (currently ~68%)
- Diminishing returns (<2 point improvement)

---

### 7. Final Held-Out Validation

```powershell
# After all fixes validated on dev
python scripts_phase3/eval_v2.py --mode current --dataset held-out --label final-held-out

# Update RESULTS.md with dev vs held-out comparison
```

---

## Alternative: Model Comparison First

If you want to know how much is model-dependent before fixing:

```powershell
# Test instruct model
$env:LLM_MODEL="qwen2.5:7b-instruct"
python scripts_phase3/eval_v2.py --mode current --dataset dev --label dev-instruct

# Compare
python scripts_phase3/compare_models.py dev-baseline dev-instruct --output ../docs/results/model-comparison.md
```

**This helps decide**: Should we fix the code, or just switch models?

---

## Monitoring Oracle Progress

```powershell
cd backend

# Real-time monitor
.\scripts_phase3\monitor_eval.ps1

# Or manual check
Get-Content eval_dev_baseline.log | Select-String "\[ *[0-9]+/90\]" | Select-Object -Last 1
```

---

## Quick Reference

### Key Files

| Path | Purpose |
|------|---------|
| `docs/evaluation-workflow.md` | Complete 9-phase process |
| `docs/evaluation-quickstart.md` | Command reference |
| `docs/phase3-preparation.md` | Fix strategy decision tree |
| `backend/scripts_phase3/run_phase3_analysis.ps1` | Automated Phase 3 |
| `data/evaluation/v2/split.json` | Dev/held-out split |

### Key Commands

```powershell
# Phase 3 analysis
.\scripts_phase3\run_phase3_analysis.ps1

# Run dev eval
python scripts_phase3/eval_v2.py --mode current --dataset dev --label <label>

# Statistical comparison
python scripts_phase3/paired_bootstrap.py --before <file1> --after <file2> --metric <metric>

# Model comparison
python scripts_phase3/compare_models.py <label1> <label2>
```

---

## Success Criteria Reminder

**Phase Goals:**
- Reduce false refusals: 20 → <12
- Improve correctness: 68% → >75%
- Validate on held-out: no regression
- All claims with 95% CI

**Measurement Principle**: No claim without a number, measure before acting

---

## Contact Points

If you need to stop and resume later:

1. **Current state is saved**: All commits pushed to GitHub
2. **Oracle will complete**: Results saved to `data/evaluation/v2/`
3. **Resume with**: `.\scripts_phase3\run_phase3_analysis.ps1`

Everything is documented and reproducible. You can pick up exactly where you left off.

---

**Ready to proceed once oracle completes (ETA: 5-10 minutes)**
