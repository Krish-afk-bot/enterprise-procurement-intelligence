# Failure taxonomy (v2 baseline)

Produced by `python scripts_phase3/eval_v2.py --mode both`. Every failed question carries exactly one label; the totals below are read straight from `data/evaluation/v2/baseline_*.json`.

| failure label | current | oracle | meaning |
| --- | ---: | ---: | --- |
| retrieval_miss | 4 | 0 | no labelled source reached the retrieved set |
| wrong_context_selected | 0 | 0 | a labelled source was retrieved but dropped before generation |
| generation_error | 6 | 4 | labelled evidence was present but the answer still missed the facts |
| verification_miss | 2 | 4 | wrong answer was reported as supported/verified |
| refusal_failure | 33 | 30 | answered something that should be refused, or refused something answerable |
| error | 0 | 0 | the question raised an exception |

| metric family | current | oracle |
| --- | --- | --- |
| retrieval recall@10 | 0.7391 | 0.8913 |
| retrieval MRR | 0.6214 | 0.8913 |
| answer correctness | 63.5% (53.9%-72.1%) | 70.2% (60.8%-78.1%) |
| refusal precision | 0.4222 | 0.4524 |
| refusal recall | 0.7308 | 0.7308 |
| citation precision | 0.3157 | 0.9004 |
| latency p50 (ms) | 8691.0 | 5224.0 |
| latency p95 (ms) | 12678.0 | 7620.0 |
