# Benchmark run — 2026-11-14T11:00:04.465573+00:00

- Questions: 120
- Strategy: pipeline default (top_k=10)
- Model: qwen2.5-coder:7b at http://localhost:11434/v1
- Embeddings: BAAI/bge-small-en-v1.5; reranker: True
- Generation modes: {"llm": 119, "refusal": 1}
- Duration: 1355.2 s

## Aggregate metrics

| Metric | Value | n |
| --- | --- | --- |
| Recall@5 | 0.9429 | 70 |
| Recall@10 | 0.9714 | 70 |
| MRR | 0.8864 | 70 |
| nDCG@10 | 0.907 | 70 |
| Answer correctness | 0.4691 | 81 |
| Citation precision | 0.7407 | 61 |
| Citation recall | 0.7857 | 61 |
| Faithfulness | 0.7411 | 76 |
| Unsupported claim rate | 0.2589 | 76 |
| Correct refusal accuracy | 0.7083 | 120 |
| Refusal precision | 0.5345 | — |
| Refusal recall | 0.7949 | — |
| Temporal correctness | 0.7 | 10 |
| Latency p50 / p95 (ms) | 7812.0 / 33057.0 | 120 |
| Prompt / completion tokens | 231034 / 9382 | — |

## By category

| Category | Q | Answer correct | Recall@10 | Citation precision | Faithfulness | Refusal P/R | Temporal | p50 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| amendments | 8 | 0.0 | 1.0 | 1.0 | 1.0 | 0.875/1.0 | None | 7812.0 |
| clauses | 8 | None | None | None | 0.6667 | 1.0/0.875 | None | 6101.0 |
| dates_and_duration | 18 | 0.5556 | 1.0 | 0.5542 | 0.5406 | 0.0/None | None | 5765.0 |
| document_metadata | 18 | 0.7778 | 1.0 | 0.8115 | 0.8889 | 0.0/None | None | 5543.0 |
| graph_multi_hop | 6 | 0.1667 | 0.6667 | 0.0 | 0.1833 | 0.0/None | None | 20570.0 |
| historical_temporal | 10 | 0.7 | 1.0 | 0.875 | 0.8333 | 0.0/None | 0.7 | 10996.0 |
| obligations | 8 | 0.0 | 1.0 | 0.9375 | 0.9524 | 0.0/None | None | 10390.0 |
| parties | 10 | 0.5 | 1.0 | 0.6833 | 0.9381 | 0.0/None | None | 7332.0 |
| payment_terms | 8 | 0.5 | 0.5 | 1.0 | 0.5 | 0.6667/0.3333 | None | 6410.0 |
| pricing_schedules | 8 | None | None | None | None | 1.0/1.0 | None | 5798.0 |
| supplier_buyer_relationships | 8 | 0.0 | None | None | 1.0 | 0.0/None | None | 24347.0 |
| unanswerable | 10 | None | None | None | 0.9643 | 1.0/0.7 | None | 13355.0 |

## Failure taxonomy

| Label | Count |
| --- | --- |
| retrieval_miss | 0 |
| wrong_context_selected | 3 |
| generation_error | 4 |
| verification_miss | 8 |
| refusal_failure | 35 |
| temporal_error | 1 |
| error | 0 |

## Failed-question analysis

### generation_error (4)

- `DATE-012` When does the estimated contract period for 'Provision of a Human Resource System & Duties Management System' end? — missing facts: ['31 July 2032']
- `OBL-003` What does the 'Provision of a Human Resource System & Duties Management System' notice say the appointed supplier will deliver? — missing facts: ['You are invited to tender for the provision of a Human Resources']
- `OBL-004` What does the 'NBI Energy Centre - Next Generation Infrastructure Programme' notice say the appointed supplier will deliver? — missing facts: ['This package of works forms part of the Next Generation Infrastructure (NGI)']
- `REL-006` Which supplier is recorded against 'Replacement of Windows, Doors &  Associated Works - GU16 Postcode area, Camberley, Surrey' for buyer 'ACCENT HOUSING LIMITED'? — missing facts: ['D R JONES YEOVIL LTD.']

### refusal_failure (35)

- `META-005` Which CPV code leads the classification list for 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer'? — missing facts: ['79415200']
- `META-010` Which CPV code leads the classification list for 'Supporting Holocaust Survivor Testimony in Teaching'? — missing facts: ['80000000']
- `META-015` Which CPV code leads the classification list for 'Provision of a Human Resource System & Duties Management System'? — missing facts: ['48000000']
- `PARTY-002` Who is the named contact for the 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer' procurement? — missing facts: ['Chloe Higgins']
- `PARTY-006` Who is the named contact for the 'Supporting Holocaust Survivor Testimony in Teaching' procurement? — missing facts: ['Anne Hardy']
- `PARTY-007` Which region is recorded for the contracting authority of 'Supporting Holocaust Survivor Testimony in Teaching'? — missing facts: ['UKI32 - Westminster']
- … and 29 more

### temporal_error (1)

- `TIME-001` As of 2026-11-12, what publication date was recorded for 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer'? — missing facts: ['20 March 2025']

### verification_miss (8)

- `META-014` Which main procurement category is recorded for 'Provision of a Human Resource System & Duties Management System'? — missing facts: ['Goods']
- `PARTY-003` Which region is recorded for the contracting authority of 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer'? — missing facts: ['UKI33 - Kensington & Chelsea and Hammersmith & Fulham']
- `PARTY-010` Which region is recorded for the contracting authority of 'Provision of a Human Resource System & Duties Management System'? — missing facts: ['UKG13 - Warwickshire']
- `OBL-001` What does the 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer' notice say the appointed supplier will deliver? — missing facts: ['The NHM is looking to appoint design consultants to help us delivery']
- `OBL-002` What does the 'Supporting Holocaust Survivor Testimony in Teaching' notice say the appointed supplier will deliver? — missing facts: ['The Department for Education (the department) is looking for a provider to']
- `OBL-005` What does the 'ACE - Provision of Financial Management System' notice say the appointed supplier will deliver? — missing facts: ['This tender opportunity has been issued by Academies for Character and Excellence']
- … and 2 more

### wrong_context_selected (3)

- `DATE-006` When does the estimated contract period for 'Supporting Holocaust Survivor Testimony in Teaching' start? — missing facts: ['1 August 2025']
- `DATE-007` When does the estimated contract period for 'Supporting Holocaust Survivor Testimony in Teaching' end? — missing facts: ['31 March 2026']
- `DATE-017` What award decision date is estimated for 'NBI Energy Centre - Next Generation Infrastructure Programme'? — missing facts: ['8 May 2026']


## How to read this

- Answer correctness uses literal fact containment; a correct paraphrase is scored as a miss.
- Faithfulness is the pipeline's own grounding verdict, not an independent judge.
- No label in the dataset has been human-adjudicated; `auto_verified` means the evidence quote was machine-checked.
- Metrics with no applicable questions are `null`, never zero.
