## Oracle vs Current Mode Analysis

**Answer Correctness**: current 68.1% → oracle 69.4%
(+1.4%, 0 questions)

**Refusal Precision**: current 0.469 → oracle 0.548 (+0.080)

**Refusal Recall**: current 0.833 → oracle 0.944 (+0.111)

**Failure Taxonomy**:

| Label | Current | Oracle | Interpretation |
|-------|---------|--------|----------------|
| error | 0 | 0 |  |
| generation_error | 0 | 1 | generation/LLM limitation (persists in oracle) |
| refusal_failure | 20 | 15 | over/under-refusal (verification issue) |
| retrieval_miss | 2 | 0 | 2 fixed by gold chunks (retrieval gap) |
| verification_miss | 2 | 6 |  |
| wrong_context_selected | 2 | 1 | 1 passages retrieved but dropped |

### Interpretation

The 1.4% correctness gap between current and oracle mode indicates that **3 failures (12% of 26 total) are due to retrieval** (missing or dropped evidence). 
**16 failures (62%) persist in oracle mode**, indicating generation or verification issues that cannot be fixed by better retrieval alone. 
Refusal precision improved from 0.469 to 0.548 in oracle mode, suggesting some false refusals are caused by insufficient retrieved evidence.