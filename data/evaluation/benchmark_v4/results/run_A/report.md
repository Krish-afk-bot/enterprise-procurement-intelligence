# Benchmark run — 2026-11-14T10:33:14.661078+00:00

- Questions: 150
- Strategy: pipeline default (top_k=10)
- Model: qwen2.5-coder:7b at http://localhost:11434/v1
- Embeddings: BAAI/bge-small-en-v1.5; reranker: True
- Generation modes: {"llm": 148, "refusal": 2}
- Duration: 1785.6 s

## Aggregate metrics

| Metric | Value | n |
| --- | --- | --- |
| Recall@5 | 0.949 | 98 |
| Recall@10 | 0.9796 | 98 |
| MRR | 0.8778 | 98 |
| nDCG@10 | 0.9028 | 98 |
| Answer correctness | 0.4404 | 109 |
| Citation precision | 0.6957 | 85 |
| Citation recall | 0.7551 | 85 |
| Faithfulness | 0.6734 | 99 |
| Unsupported claim rate | 0.3266 | 99 |
| Correct refusal accuracy | 0.72 | 150 |
| Refusal precision | 0.4925 | — |
| Refusal recall | 0.8049 | — |
| Temporal correctness | 0.7 | 10 |
| Latency p50 / p95 (ms) | 9316.0 / 29479.0 | 150 |
| Prompt / completion tokens | 280736 / 11221 | — |

## By category

| Category | Q | Answer correct | Recall@10 | Citation precision | Faithfulness | Refusal P/R | Temporal | p50 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| amendments | 8 | 0.0 | 1.0 | 1.0 | 1.0 | 0.875/1.0 | None | 8177.0 |
| award_criteria | 7 | 0.0 | 1.0 | 0.7083 | 0.4365 | 0.0/None | None | 11907.0 |
| clauses | 8 | None | None | None | 0.6667 | 1.0/0.875 | None | 6100.0 |
| compliance_check | 1 | 1.0 | 1.0 | 1.0 | 1.0 | None/None | None | 13828.0 |
| contract_terms | 2 | 0.0 | 1.0 | 1.0 | 0.375 | 0.0/None | None | 17767.0 |
| dates_and_duration | 23 | 0.5217 | 1.0 | 0.5703 | 0.6392 | 0.0/None | None | 8453.0 |
| document_metadata | 18 | 0.7778 | 1.0 | 0.8115 | 0.8824 | 0.0/None | None | 5566.0 |
| graph_multi_hop | 6 | 0.1667 | 0.6667 | 0.0 | 0.2 | 0.0/None | None | 16810.0 |
| historical_temporal | 10 | 0.7 | 1.0 | 0.875 | 0.8333 | 0.0/None | 0.7 | 10759.0 |
| obligations | 8 | 0.0 | 1.0 | 0.9286 | 0.7143 | 0.0/None | None | 10180.0 |
| parties | 11 | 0.5455 | 1.0 | 0.606 | 0.9156 | 0.0/None | None | 9267.0 |
| payment_terms | 8 | 0.5 | 0.5 | 1.0 | 0.5 | 0.6667/0.3333 | None | 6332.0 |
| pricing_schedules | 8 | None | None | None | None | 1.0/1.0 | None | 5855.0 |
| procurement_values | 10 | 0.5 | 1.0 | 0.5033 | 0.5625 | 0.0/None | None | 9509.0 |
| structured_data | 2 | 0.5 | 1.0 | 1.0 | 0.25 | 0.0/None | None | 13791.0 |
| supplier_buyer_relationships | 8 | 0.0 | None | None | 0.5 | 0.0/None | None | 16286.0 |
| unanswerable | 10 | None | None | None | 0.9524 | 1.0/0.7 | None | 11364.0 |
| unanswerable_near_miss | 2 | None | None | None | None | 1.0/1.0 | None | 8714.0 |

## Failure taxonomy

| Label | Count |
| --- | --- |
| retrieval_miss | 0 |
| wrong_context_selected | 8 |
| generation_error | 11 |
| verification_miss | 7 |
| refusal_failure | 42 |
| temporal_error | 1 |
| error | 0 |

## Failed-question analysis

### generation_error (11)

- `DATE-012` When does the estimated contract period for 'Provision of a Human Resource System & Duties Management System' end? — missing facts: ['31 July 2032']
- `DATE-016` When does the estimated contract period for 'NBI Energy Centre - Next Generation Infrastructure Programme' end? — missing facts: ['11 January 2028']
- `OBL-003` What does the 'Provision of a Human Resource System & Duties Management System' notice say the appointed supplier will deliver? — missing facts: ['You are invited to tender for the provision of a Human Resources']
- `OBL-004` What does the 'NBI Energy Centre - Next Generation Infrastructure Programme' notice say the appointed supplier will deliver? — missing facts: ['This package of works forms part of the Next Generation Infrastructure (NGI)']
- `OBL-007` What does the 'Dockless bike hire concession services Lot 1 (contract 1)' notice say the appointed supplier will deliver? — missing facts: ['The London Borough of Camden are seeking to award concession contracts for']
- `REL-006` Which supplier is recorded against 'Replacement of Windows, Doors &  Associated Works - GU16 Postcode area, Camberley, Surrey' for buyer 'ACCENT HOUSING LIMITED'? — missing facts: ['D R JONES YEOVIL LTD.']
- … and 5 more

### refusal_failure (42)

- `META-005` Which CPV code leads the classification list for 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer'? — missing facts: ['79415200']
- `META-010` Which CPV code leads the classification list for 'Supporting Holocaust Survivor Testimony in Teaching'? — missing facts: ['80000000']
- `META-015` Which CPV code leads the classification list for 'Provision of a Human Resource System & Duties Management System'? — missing facts: ['48000000']
- `PARTY-002` Who is the named contact for the 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer' procurement? — missing facts: ['Chloe Higgins']
- `PARTY-006` Who is the named contact for the 'Supporting Holocaust Survivor Testimony in Teaching' procurement? — missing facts: ['Anne Hardy']
- `PARTY-007` Which region is recorded for the contracting authority of 'Supporting Holocaust Survivor Testimony in Teaching'? — missing facts: ['UKI32 - Westminster']
- … and 36 more

### temporal_error (1)

- `TIME-001` As of 2026-11-12, what publication date was recorded for 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer'? — missing facts: ['20 March 2025']

### verification_miss (7)

- `META-014` Which main procurement category is recorded for 'Provision of a Human Resource System & Duties Management System'? — missing facts: ['Goods']
- `PARTY-003` Which region is recorded for the contracting authority of 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer'? — missing facts: ['UKI33 - Kensington & Chelsea and Hammersmith & Fulham']
- `OBL-001` What does the 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer' notice say the appointed supplier will deliver? — missing facts: ['The NHM is looking to appoint design consultants to help us delivery']
- `OBL-005` What does the 'ACE - Provision of Financial Management System' notice say the appointed supplier will deliver? — missing facts: ['This tender opportunity has been issued by Academies for Character and Excellence']
- `OBL-006` What does the 'RFQ 2025/59 - NMANDD PEACEPLUS Thriving Together Cross Community Festivals Programme Castlewellan Peace Maze: Connecting Generations' notice say the appointed supplier will deliver? — missing facts: ['Newry, Mourne and Down District Council (NMDDC) seeks a suitably experienced supplier']
- `V4-013` What are the quality and price weightings for the NBI Energy Centre CHP engines? — missing facts: ['Quality | 60%', 'Price | 40%']
- … and 1 more

### wrong_context_selected (8)

- `DATE-003` What contract duration is estimated for 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer'? — missing facts: ['2 years, 26 days']
- `DATE-006` When does the estimated contract period for 'Supporting Holocaust Survivor Testimony in Teaching' start? — missing facts: ['1 August 2025']
- `DATE-007` When does the estimated contract period for 'Supporting Holocaust Survivor Testimony in Teaching' end? — missing facts: ['31 March 2026']
- `DATE-017` What award decision date is estimated for 'NBI Energy Centre - Next Generation Infrastructure Programme'? — missing facts: ['8 May 2026']
- `V4-004` What is the total estimated value of the HR and Duties Management System procurement excluding VAT? — missing facts: ['2,750,000']
- `V4-005` What is the total estimated value of the NBI Energy Centre procurement including VAT? — missing facts: ['14,160,000']
- … and 2 more


## How to read this

- Answer correctness uses literal fact containment; a correct paraphrase is scored as a miss.
- Faithfulness is the pipeline's own grounding verdict, not an independent judge.
- No label in the dataset has been human-adjudicated; `auto_verified` means the evidence quote was machine-checked.
- Metrics with no applicable questions are `null`, never zero.
