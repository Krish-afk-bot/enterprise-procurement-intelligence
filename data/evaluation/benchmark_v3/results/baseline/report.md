# Benchmark run — 2026-11-12T20:06:37.489030+00:00

- Questions: 120
- Strategy: pipeline default (top_k=10)
- Model: qwen2.5-coder:7b at http://localhost:11434/v1
- Embeddings: BAAI/bge-small-en-v1.5; reranker: True
- Generation modes: {"llm": 106, "extractive": 9, "null": 3, "refusal": 2}
- Duration: 1169.5 s

## Aggregate metrics

| Metric | Value | n |
| --- | --- | --- |
| Recall@5 | 0.8676 | 70 |
| Recall@10 | 0.8676 | 70 |
| MRR | 0.802 | 70 |
| nDCG@10 | 0.8187 | 70 |
| Answer correctness | 0.3974 | 78 |
| Citation precision | 0.774 | 43 |
| Citation recall | 0.5588 | 43 |
| Faithfulness | 0.6938 | 65 |
| Unsupported claim rate | 0.3062 | 65 |
| Correct refusal accuracy | 0.5812 | 120 |
| Refusal precision | 0.4286 | — |
| Refusal recall | 0.7692 | — |
| Temporal correctness | 0.7 | 10 |
| Latency p50 / p95 (ms) | 9151.0 / 16279.0 | 120 |
| Prompt / completion tokens | 195964 / 7094 | — |

## By category

| Category | Q | Answer correct | Recall@10 | Citation precision | Faithfulness | Refusal P/R | Temporal | p50 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| amendments | 8 | 0.0 | 0.0 | None | None | 0.875/1.0 | None | 12575.0 |
| clauses | 8 | None | None | None | 0.5 | 1.0/0.75 | None | 7054.0 |
| dates_and_duration | 18 | 0.3889 | 1.0 | 0.6148 | 0.5241 | 0.0/None | None | 8958.0 |
| document_metadata | 18 | 0.7222 | 1.0 | 0.8988 | 0.8824 | 0.0/None | None | 5639.0 |
| graph_multi_hop | 6 | 0.0 | 0.3333 | 0.0 | None | 0.0/None | None | 8359.0 |
| historical_temporal | 10 | 0.7 | 1.0 | 0.875 | 0.8889 | 0.0/None | 0.7 | 10784.0 |
| obligations | 8 | 0.0 | 0.875 | 0.6389 | 0.4333 | 0.0/None | None | 11604.0 |
| parties | 10 | 0.375 | 0.5 | 0.8333 | 0.75 | 0.0/None | None | 4511.0 |
| payment_terms | 8 | 0.5 | 0.5 | 1.0 | 0.5833 | 0.6667/0.3333 | None | 7866.0 |
| pricing_schedules | 8 | None | None | None | None | 1.0/1.0 | None | 8853.0 |
| supplier_buyer_relationships | 8 | 0.0 | None | None | 0.5 | 0.0/None | None | 12781.0 |
| unanswerable | 10 | None | None | None | 0.8333 | 1.0/0.7 | None | 12685.0 |

## Failure taxonomy

| Label | Count |
| --- | --- |
| retrieval_miss | 0 |
| wrong_context_selected | 2 |
| generation_error | 3 |
| verification_miss | 1 |
| refusal_failure | 49 |
| temporal_error | 1 |
| error | 3 |

## Failed-question analysis

### error (3)

- `PARTY-002` Who is the named contact for the 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer' procurement?
- `PARTY-006` Who is the named contact for the 'Supporting Holocaust Survivor Testimony in Teaching' procurement?
- `REL-005` Which supplier is recorded against 'Insurance and related services for Property, legal liability and other general (non-life) insurable risks, as required by Accent Group Ltd.' for buyer 'ACCENT HOUSING LIMITED'?

### generation_error (3)

- `PARTY-010` Which region is recorded for the contracting authority of 'Provision of a Human Resource System & Duties Management System'? — missing facts: ['UKG13 - Warwickshire']
- `OBL-001` What does the 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer' notice say the appointed supplier will deliver? — missing facts: ['The NHM is looking to appoint design consultants to help us delivery']
- `OBL-004` What does the 'NBI Energy Centre - Next Generation Infrastructure Programme' notice say the appointed supplier will deliver? — missing facts: ['This package of works forms part of the Next Generation Infrastructure (NGI)']

### refusal_failure (49)

- `META-005` Which CPV code leads the classification list for 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer'? — missing facts: ['79415200']
- `META-010` Which CPV code leads the classification list for 'Supporting Holocaust Survivor Testimony in Teaching'? — missing facts: ['80000000']
- `META-013` When was the notice for 'Provision of a Human Resource System & Duties Management System' published? — missing facts: ['18 September 2025']
- `META-015` Which CPV code leads the classification list for 'Provision of a Human Resource System & Duties Management System'? — missing facts: ['48000000']
- `META-018` When was the notice for 'NBI Energy Centre - Next Generation Infrastructure Programme' published? — missing facts: ['14 November 2025']
- `PARTY-001` Which organisation is the contracting authority for 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer'? — missing facts: ['Natural History Museum']
- … and 43 more

### temporal_error (1)

- `TIME-001` As of 2026-11-12, what publication date was recorded for 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer'? — missing facts: ['20 March 2025']

### verification_miss (1)

- `OBL-003` What does the 'Provision of a Human Resource System & Duties Management System' notice say the appointed supplier will deliver? — missing facts: ['You are invited to tender for the provision of a Human Resources']

### wrong_context_selected (2)

- `DATE-001` When does the estimated contract period for 'Gallery 33 - 3D and 2D Exhibition Design/Lead Designer' start? — missing facts: ['7 July 2025']
- `DATE-008` What contract duration is estimated for 'Supporting Holocaust Survivor Testimony in Teaching'? — missing facts: ['8 months']


## How to read this

- Answer correctness uses literal fact containment; a correct paraphrase is scored as a miss.
- Faithfulness is the pipeline's own grounding verdict, not an independent judge.
- No label in the dataset has been human-adjudicated; `auto_verified` means the evidence quote was machine-checked.
- Metrics with no applicable questions are `null`, never zero.
