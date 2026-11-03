# All Failures Analysis (Dev Set)

**Total failures**: 26

## By Failure Type

- **false_refusal**: 17 (65.4%)
- **wrong_answer**: 6 (23.1%)
- **under_refusal**: 3 (11.5%)

## By Root Cause

- **retrieval_failure**: 19 (73.1%)
- **reasoning_failure**: 4 (15.4%)
- **refusal_gate_missed**: 3 (11.5%)

## Retrieval vs Non-Retrieval Issues

- **Retrieval issues**: 19 (73.1%)
- **Non-retrieval issues**: 7 (26.9%)

## By Subcause

- **not_retrieved**: 19 (73.1%)
- **should_have_refused**: 3 (11.5%)
- **reasoning_error**: 2 (7.7%)
- **answerability_other**: 2 (7.7%)

## Cross-Tabulation: Failure Type × Root Cause

| Failure Type | Retrieval | Reasoning | Refusal Gate | Total |
|--------------|-----------|-----------|--------------|-------|
| false_refusal | 15 | 2 | 0 | 17 |
| under_refusal | 0 | 0 | 3 | 3 |
| wrong_answer | 4 | 2 | 0 | 6 |

## Detailed Failure Table

| ID | Type | Root Cause | Subcause | Category |
|----|------|------------|----------|----------|
| v2-agg-007 | false_refusal | reasoning_failure | answerability_other | aggregation |
| v2-agg-010 | false_refusal | reasoning_failure | answerability_other | aggregation |
| v2-comp-005 | false_refusal | retrieval_failure | not_retrieved | comparison |
| v2-comp-009 | false_refusal | retrieval_failure | not_retrieved | comparison |
| v2-comp-010 | false_refusal | retrieval_failure | not_retrieved | comparison |
| v2-compl-002 | false_refusal | retrieval_failure | not_retrieved | compliance |
| v2-compl-003 | false_refusal | retrieval_failure | not_retrieved | compliance |
| v2-compl-004 | false_refusal | retrieval_failure | not_retrieved | compliance |
| v2-compl-005 | false_refusal | retrieval_failure | not_retrieved | compliance |
| v2-mm-002 | false_refusal | retrieval_failure | not_retrieved | multimodal |
| v2-mm-006 | false_refusal | retrieval_failure | not_retrieved | multimodal |
| v2-mm-007 | false_refusal | retrieval_failure | not_retrieved | multimodal |
| v2-rel-006 | false_refusal | retrieval_failure | not_retrieved | relationships |
| v2-rel-007 | false_refusal | retrieval_failure | not_retrieved | relationships |
| v2-rel-008 | false_refusal | retrieval_failure | not_retrieved | relationships |
| v2-rel-010 | false_refusal | retrieval_failure | not_retrieved | relationships |
| v2-sec-010 | false_refusal | retrieval_failure | not_retrieved | security |
| v2-unans-001 | under_refusal | refusal_gate_missed | should_have_refused | unanswerable |
| v2-unans-012 | under_refusal | refusal_gate_missed | should_have_refused | unanswerable |
| v2-unans-017 | under_refusal | refusal_gate_missed | should_have_refused | unanswerable |
| v2-agg-006 | wrong_answer | reasoning_failure | reasoning_error | aggregation |
| v2-agg-011 | wrong_answer | reasoning_failure | reasoning_error | aggregation |
| v2-comp-002 | wrong_answer | retrieval_failure | not_retrieved | comparison |
| v2-comp-007 | wrong_answer | retrieval_failure | not_retrieved | comparison |
| v2-mm-001 | wrong_answer | retrieval_failure | not_retrieved | multimodal |
| v2-temp-013 | wrong_answer | retrieval_failure | not_retrieved | temporal |

## Key Insights

1. **Retrieval issues**: 19/26 failures (73.1%) are due to retrieval problems. Improving retrieval could fix these.

2. **Non-retrieval issues**: 7/26 failures (26.9%) occur even when correct evidence is in context. These require prompt/reasoning improvements, not retrieval changes.

3. **Top non-retrieval issue**: should_have_refused (3 cases). Focus here for reasoning improvements.
