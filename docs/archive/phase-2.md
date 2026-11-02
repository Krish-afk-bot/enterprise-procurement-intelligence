# Phase 2 — pipeline fixes (archived report)

Archived after Phase 5 consolidated the final numbers into
[docs/RESULTS.md](../RESULTS.md). This report keeps the iteration history: the
pipeline was measured three times, and the middle run is why three verification
fixes were added rather than reverting the phase.

## Iterations

| Run | Artifact | Answer | Refusal P / R | Citation precision | p50 |
|---|---|---|---|---|---|
| Start | `phase-2-start_*.json` | 68.3% (71/104) | 0.500 / 0.808 | 0.316 | 10,154 ms |
| After Phase 2 changes | `phase-2-after_*.json` | 63.5% (66/104) | 0.440 / 0.846 | 0.561 | 5,744 ms |
| Final (fixes in `e7a0066`) | `phase-2-final_*.json` | 68.3% (71/104) | 0.478 / 0.846 | 0.545 | 6,932 ms |

The middle run exposed a real regression: answer correctness fell 4.8 points
and refusal precision 6 points, while citation precision and latency improved
substantially. Diagnosis found three defects rather than a bad design:

1. **Phantom entities.** `qwen2.5-coder:7b` returned `supplier1`/`supplier2` for
   "Which supplier offers the larger volume discount?", and the planner kept
   unresolved names without checking that the reader wrote them. The coverage
   check then demanded an entity that cannot exist and forced a refusal on an
   answerable question. Fix: keep an unresolved supplier/product only when it is
   mentioned in the question.
2. **Grounding metric key mismatch.** `state["grounding"]` is
   `GroundingResult.as_dict()`, which publishes `total_claims`/`supported_claims`;
   the runner read `total`/`supported`, so every row reported 0/0 and
   verification failures were invisible or mislabelled. Fix: read the published
   keys.
3. **Refusal beside the draft.** `decide_status` ignores a price supersession
   when deciding whether an answer is conflicting, so coverage failure still
   yields `insufficient_evidence`. The replacement guard tested the raw
   relevant-conflict list, so a supersession about the named supplier skipped
   replacing the draft: the row reported a refusal while returning the ungrounded
   answer, which then scored as correct. Fix: replace the draft whenever the
   verdict is `insufficient_evidence`.

## Decision

The Phase 2 changes were kept because they improve the metrics they target
(citation precision +22.9 points, p50 −32%) and the fixes recovered the
answer-correctness and refusal-precision losses. Refusal precision remains 2.2
points below baseline; that residue is over-refusal, recorded in
[docs/RESULTS.md](../RESULTS.md) as not fixed.

## Tests added

- `backend/tests/unit/test_query_understanding.py` — placeholder suppliers and
  products are dropped; a supplier the reader actually named is kept.
- `backend/tests/unit/test_evaluation_v2.py` — the runner scores
  `total_claims`/`supported_claims`.
- `backend/tests/unit/test_refusal_correctness.py` — a refusal replaces the draft
  even when a relevant price supersession is present.
