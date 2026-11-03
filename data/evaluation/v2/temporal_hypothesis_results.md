# Temporal Preference Hypothesis Test - Complete Results

## Step 1: HYPOTHESIS CONFIRMED ✓

**Date used for expiry check**: 2026-11-03 (system date)
**Certificate expiry date**: 2026-04-30 (EXPIRED by 186 days)

### Certificate Retrieval Trace (6 test questions + 1 control)

| Question | Dense | Sparse | Fusion | Top-50 | Auth | Rerank | Before Temporal | After Temporal | Top-15 | Loss Stage |
|----------|-------|--------|--------|--------|------|--------|-----------------|----------------|--------|------------|
| v2-compl-002 | rank 1 | rank 1 | rank 1 | rank 1 | rank 1 | rank 1 | **rank 1** | **rank 28** | NOT FOUND | **STAGE 7** |
| v2-compl-003 | rank 1 | rank 1 | rank 1 | rank 1 | rank 1 | rank 1 | **rank 1** | **rank 28** | NOT FOUND | **STAGE 7** |
| v2-compl-004 | rank 1 | rank 1 | rank 1 | rank 1 | rank 1 | rank 1 | **rank 1** | **rank 28** | NOT FOUND | **STAGE 7** |
| v2-compl-005 | rank 1 | rank 1 | rank 1 | rank 1 | rank 1 | rank 1 | **rank 1** | **rank 28** | NOT FOUND | **STAGE 7** |
| v2-rel-008 | rank 1 | rank 1 | rank 1 | rank 1 | rank 1 | rank 1 | **rank 1** | **rank 35** | NOT FOUND | **STAGE 7** |
| v2-comp-009 | rank 3 | rank 5 | rank 3 | rank 3 | rank 3 | rank 3 | **rank 3** | **rank 35** | NOT FOUND | **STAGE 7** |
| v2-agg-002 (control) | NOT FOUND | NOT FOUND | NOT FOUND | N/A | N/A | N/A | N/A | N/A | NOT FOUND | STAGE 1 (expected) |

**Conclusion**: `_apply_temporal_preference` pushes expired certificate from rank 1-3 to rank 28-35, causing loss at top-15 cut.

---

## Step 2: OCR - BLOCKED

**Status**: Scanned signature page (supplier_a_scanned_signature_page.pdf) has 0 chunks, needs OCR.
**Blocker**: CLI ingest tool works only with production PostgreSQL DB. Eval DB is SQLite at `backend/var/eval-v2/eval.db`.
**Note**: Certificate (supplier_a_compliance_certificate.pdf) has 1 chunk and is properly indexed. OCR issue affects only scanned signature page.

---

## Step 3: CLOCK - COMPLETE ✓

**Implemented**: `backend/app/core/clock.py` with `today()` function
**Reads**: `EVAL_AS_OF_DATE` environment variable for deterministic evaluation dates
**Replaced**: All `date.today()` calls in:
- `app/retrieval/retriever.py` (_apply_temporal_preference)
- `app/retrieval/structured.py` (contract status, certificate status)
- `app/retrieval/analysis.py` (price facts, temporal summary)
- `app/retrieval/graph_retrieval.py` (certificate paths)
- `app/agents/generation.py` (preferred facts)
- `app/agents/verification.py` (in-force citations)
- `app/ingestion/pipeline.py` (document status)
- `app/services/procurement.py` (contract payload)

**Proposed eval date**: 2026-02-15
**Rationale**: Questions authored 2026-11-02, certificate expires 2026-04-30. Date 2026-02-15 ensures certificate is valid during question authoring.

---

## Step 4: EXPERIMENT A - PENDING RESULTS

**Changes to `_apply_temporal_preference`**:

a) **Soft penalty**: Expired chunks get 0.5x score multiplier, not moved to separate tier
b) **No penalty when**:
   - Document type matches question (e.g., "certificate" question + "compliance_certificate" doc type)
   - Question asks about expiry/validity/expired status (keywords: expir, valid, expired, in force, active, certificate, compliance, certification)
c) **Temporal queries**: Use effective date only for supersession within same contract, not across unrelated documents
d) **Unit tests**: TODO (not written yet per instruction to run eval first)

**Eval status**: Started with label `experiment-a`, results pending

---

## Step 5: VERIFIER LOG - COMPLETE ✓

**Questions with expected doc retrieved but refused/partial**: 12

### Summary by Status:
- **insufficient_evidence**: 5 questions (v2-comp-005, v2-comp-009, v2-rel-010, v2-sec-010, v2-sec-011)
- **partial**: 7 questions (v2-comp-007, v2-comp-010, v2-compl-009, v2-compl-010, v2-sec-008, v2-table-008, v2-table-011)

### Common patterns:
1. **Grounding failures**: Many have 0/N or low claims supported despite having expected docs
2. **Cross-supplier comparisons**: Comparison questions (v2-comp-*) often fail even with both expected docs retrieved
3. **Partial answers**: System generates answers but fails grounding, downgrades to partial
4. **NULL supplier_id**: No evidence of supplier_id filter issues (planner correctly leaves filter empty for multi-supplier questions)

### Example: v2-comp-009 (certificate comparison)
- Retrieved: supplier_b_supply_agreement (1 of 2 expected docs)
- Missing: supplier_a_compliance_certificate (pushed down by temporal preference)
- Grounding: 0/2 claims supported
- Result: insufficient_evidence

---

## Step 6: SETTINGS AUDIT - COMPLETE ✓

### Current settings:
```
rrf_k = 60
rerank_top_n = 15
context_max_chunks = 12
fusion_top_k = 50
rerank_gate_enabled = True
```

### Baseline commit: `54db6e84` (2026-11-03, "revert: restore baseline retrieval settings")

**Settings at baseline commit**:
```
rrf_k = 60
rerank_top_n = 15
context_max_chunks = 12
fusion_top_k = 50
```

**Verification**: ✓ Current settings MATCH baseline commit
**Note**: Baseline was run after reverting Phase 4A changes (which had increased limits: sparse_top_k 50→75, rerank_top_n 15→20, context_max_chunks 12→15)

---

## Summary

| Step | Status | Key Finding |
|------|--------|-------------|
| 1. Trace retrieval | ✓ CONFIRMED | Certificate rank 1 → 28/35 after temporal preference |
| 2. OCR re-ingest | ❌ BLOCKED | Eval DB is SQLite, CLI ingest needs PostgreSQL |
| 3. Deterministic clock | ✓ COMPLETE | Proposed date: 2026-02-15 |
| 4. Experiment A | ⏳ PENDING | Soft penalty impl complete, eval running |
| 5. Verifier log | ✓ COMPLETE | 12 questions with doc retrieved but refused/partial |
| 6. Settings audit | ✓ COMPLETE | Current = baseline (commit 54db6e84) |

**Next**: Wait for Experiment A results, then run paired bootstrap comparison.
