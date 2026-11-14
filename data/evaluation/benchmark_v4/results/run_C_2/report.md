# Benchmark run — 2026-11-14T11:24:06.704617+00:00

- Questions: 50
- Strategy: pipeline default (top_k=10)
- Model: qwen2.5-coder:7b at http://localhost:11434/v1
- Embeddings: BAAI/bge-small-en-v1.5; reranker: True
- Generation modes: {"llm": 50}
- Duration: 594.2 s

## Aggregate metrics

| Metric | Value | n |
| --- | --- | --- |
| Recall@5 | 1.0 | 32 |
| Recall@10 | 1.0 | 32 |
| MRR | 0.9089 | 32 |
| nDCG@10 | 0.932 | 32 |
| Answer correctness | 0.3611 | 36 |
| Citation precision | 0.5827 | 28 |
| Citation recall | 0.6875 | 28 |
| Faithfulness | 0.6438 | 33 |
| Unsupported claim rate | 0.3562 | 33 |
| Correct refusal accuracy | 0.68 | 50 |
| Refusal precision | 0.4545 | — |
| Refusal recall | 0.7143 | — |
| Temporal correctness | 0.6667 | 3 |
| Latency p50 / p95 (ms) | 8639.0 / 21137.0 | 50 |
| Prompt / completion tokens | 93454 / 3556 | — |

## By category

| Category | Q | Answer correct | Recall@10 | Citation precision | Faithfulness | Refusal P/R | Temporal | p50 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| amendments | 3 | None | None | None | None | 1.0/1.0 | None | 8291.0 |
| award_criteria | 2 | 0.0 | 1.0 | 0.3333 | 0.4445 | 0.0/None | None | 15933.0 |
| clauses | 3 | None | None | None | 0.5 | 1.0/0.6667 | None | 8052.0 |
| contract_terms | 1 | 0.0 | 1.0 | None | 0.0 | 0.0/None | None | 17648.0 |
| dates_and_duration | 8 | 0.25 | 1.0 | 0.3646 | 0.5595 | 0.0/None | None | 6738.0 |
| document_metadata | 6 | 0.8333 | 1.0 | 0.68 | 0.8333 | 0.0/None | None | 7945.0 |
| graph_multi_hop | 2 | 0.0 | 1.0 | None | 0.0 | 0.0/None | None | 21039.0 |
| historical_temporal | 3 | 0.6667 | 1.0 | 0.6667 | 0.8333 | None/None | 0.6667 | 14955.0 |
| obligations | 3 | 0.0 | 1.0 | 1.0 | 0.6667 | None/None | None | 11103.0 |
| parties | 4 | 0.5 | 1.0 | 0.6666 | 1.0 | 0.0/None | None | 8115.0 |
| payment_terms | 3 | 1.0 | 1.0 | 1.0 | 0.6667 | None/0.0 | None | 8283.0 |
| pricing_schedules | 3 | None | None | None | None | 1.0/1.0 | None | 6420.0 |
| procurement_values | 3 | 0.3333 | 1.0 | 0.3333 | 0.6667 | None/None | None | 9414.0 |
| supplier_buyer_relationships | 3 | 0.0 | None | None | None | 0.0/None | None | 12686.0 |
| unanswerable | 3 | None | None | None | 1.0 | 1.0/0.6667 | None | 12068.0 |

## Failure taxonomy

| Label | Count |
| --- | --- |
| retrieval_miss | 0 |
| wrong_context_selected | 5 |
| generation_error | 5 |
| verification_miss | 0 |
| refusal_failure | 16 |
| temporal_error | 1 |
| error | 0 |

## Failed-question analysis

### generation_error (5)

- `V4-020` What is the tender submission deadline for the Loan Management System? — missing facts: ['8 May 2026, 11:55pm']
- `OBL-004` What does the 'NBI Energy Centre - Next Generation Infrastructure Programme' notice say the appointed supplier will deliver? — missing facts: ['This package of works forms part of the Next Generation Infrastructure (NGI)']
- `OBL-007` What does the 'Dockless bike hire concession services Lot 1 (contract 1)' notice say the appointed supplier will deliver? — missing facts: ['The London Borough of Camden are seeking to award concession contracts for']
- `OBL-003` What does the 'Provision of a Human Resource System & Duties Management System' notice say the appointed supplier will deliver? — missing facts: ['You are invited to tender for the provision of a Human Resources']
- `V4-024` What percentage of the BGS waste management award is allocated to Social Value? — missing facts: ['Social Value 10.00%']

### refusal_failure (16)

- `META-015` Which CPV code leads the classification list for 'Provision of a Human Resource System & Duties Management System'? — missing facts: ['48000000']
- `PARTY-002` Who is the named contact for the 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer' procurement? — missing facts: ['Chloe Higgins']
- `PARTY-007` Which region is recorded for the contracting authority of 'Supporting Holocaust Survivor Testimony in Teaching'? — missing facts: ['UKI32 - Westminster']
- `DATE-002` When does the estimated contract period for 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer' end? — missing facts: ['1 August 2027']
- `DATE-001` When does the estimated contract period for 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer' start? — missing facts: ['7 July 2025']
- `PAY-007` What payment terms does the 'RFQ 2025/59 - NMANDD PEACEPLUS Thriving Together Cross Community Festivals Programme Castlewellan Peace Maze: Connecting Generations' notice specify?
- … and 10 more

### temporal_error (1)

- `TIME-001` As of 2026-11-12, what publication date was recorded for 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer'? — missing facts: ['20 March 2025']

### wrong_context_selected (5)

- `DATE-003` What contract duration is estimated for 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer'? — missing facts: ['2 years, 26 days']
- `DATE-007` When does the estimated contract period for 'Supporting Holocaust Survivor Testimony in Teaching' end? — missing facts: ['31 March 2026']
- `DATE-017` What award decision date is estimated for 'NBI Energy Centre - Next Generation Infrastructure Programme'? — missing facts: ['8 May 2026']
- `V4-002` What is the total estimated value of the Critical Ventilation contract including VAT? — missing facts: ['318,000']
- `V4-005` What is the total estimated value of the NBI Energy Centre procurement including VAT? — missing facts: ['14,160,000']


## How to read this

- Answer correctness uses literal fact containment; a correct paraphrase is scored as a miss.
- Faithfulness is the pipeline's own grounding verdict, not an independent judge.
- No label in the dataset has been human-adjudicated; `auto_verified` means the evidence quote was machine-checked.
- Metrics with no applicable questions are `null`, never zero.
