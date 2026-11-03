# Over-Refusal Analysis (Dev Set)

**Total false refusals**: 17

## Summary

### By Refusal Reason:

- unknown: 9
- answerability_other: 8

### By Evidence Location:

- not_retrieved: 15
- n/a: 2

### By Category:

- compliance: 4
- relationships: 4
- comparison: 3
- multimodal: 3
- aggregation: 2
- security: 1

## Detailed Table

| ID | Category | Refusal Reason | Evidence Location | Expected Docs |
|----|----------|----------------|-------------------|---------------|
| v2-agg-007 | aggregation | answerability_other | n/a |  |
| v2-agg-010 | aggregation | unknown | n/a |  |
| v2-comp-005 | comparison | answerability_other | not_retrieved | supplier_a_master_contract_NS-2024-001.pdf, suppli |
| v2-comp-009 | comparison | answerability_other | not_retrieved | supplier_a_compliance_certificate.pdf, supplier_b_ |
| v2-comp-010 | comparison | unknown | not_retrieved | supplier_a_master_contract_NS-2024-001.pdf, suppli |
| v2-compl-002 | compliance | unknown | not_retrieved | supplier_a_compliance_certificate.pdf |
| v2-compl-003 | compliance | answerability_other | not_retrieved | supplier_a_compliance_certificate.pdf |
| v2-compl-004 | compliance | answerability_other | not_retrieved | supplier_a_compliance_certificate.pdf |
| v2-compl-005 | compliance | answerability_other | not_retrieved | supplier_a_compliance_certificate.pdf |
| v2-mm-002 | multimodal | unknown | not_retrieved | supplier_a_scanned_signature_page.pdf |
| v2-mm-006 | multimodal | unknown | not_retrieved | supplier_a_scanned_signature_page.pdf |
| v2-mm-007 | multimodal | unknown | not_retrieved | supplier_a_scanned_signature_page.pdf |
| v2-rel-006 | relationships | unknown | not_retrieved | supplier_a_scanned_signature_page.pdf |
| v2-rel-007 | relationships | unknown | not_retrieved | supplier_a_scanned_signature_page.pdf |
| v2-rel-008 | relationships | unknown | not_retrieved | supplier_a_compliance_certificate.pdf |
| v2-rel-010 | relationships | answerability_other | not_retrieved | supplier_a_master_contract_NS-2024-001.pdf, suppli |
| v2-sec-010 | security | answerability_other | not_retrieved | security_fixture_injection.pdf |

## Interpretation

The most common refusal reason is **unknown** (9 cases). This should be addressed first.