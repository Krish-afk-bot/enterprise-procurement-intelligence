# Routing and engine report (Run A)

## Configured engines

| Engine | Available | Evidence |
| --- | --- | --- |
| Large LLM | yes (`qwen2.5-coder:7b`, Ollama) | `model` on 148/150 rows |
| Small LLM | no | `LLM_SMALL_MODEL` is unset; every generation falls back to the large model |
| VLM | no usable model | Ollama `/chat/completions` returned 404 during page-vision escalation; pages kept text/OCR |
| Python/SQL (structured) | yes | `structured_ms` on 87/150 rows |
| Graph | yes (local SQLite) | `graph_ms` on 17/150 rows |
| Embeddings + reranker | yes (BGE-small 384d; bge-reranker) | retrieval/rerank stages on 150/150 |

## Routing sample (30 questions)

| id | intent | engines used | generation | status |
| --- | --- | --- | --- | --- |
| OBL-005 | contract_terms | understand, retrieval, parallel, generation, verification | llm | supported |
| DATE-011 | contract_terms | understand, structured, retrieval, parallel, generation, verification | llm | supported |
| TIME-002 | temporal_change | understand, structured, retrieval, parallel, generation, verification | refusal | insufficient_evidence |
| META-013 | document_lookup | understand, structured, retrieval, parallel, generation, verification | llm | supported |
| PARTY-001 | relationship | understand, retrieval, parallel, generation, verification | llm | supported |
| V4-018 | contract_terms | understand, structured, retrieval, parallel, generation, verification | llm | partial |
| PARTY-007 | relationship | understand, retrieval, parallel, generation, verification | llm | partial |
| REL-008 | relationship | understand, graph, retrieval, parallel, generation, verification | llm | insufficient_evidence |
| META-015 | document_lookup | understand, retrieval, parallel, generation, verification | llm | insufficient_evidence |
| V4-010 | price_lookup | understand, structured, retrieval, parallel, generation, verification | llm | partial |
| PRICE-001 | price_lookup | understand, structured, retrieval, parallel, generation, verification | llm | partial |
| META-010 | document_lookup | understand, retrieval, parallel, generation, verification | llm | insufficient_evidence |
| PARTY-005 | relationship | understand, retrieval, parallel, generation, verification | llm | partial |
| UNANS-002 | general | understand, structured, graph, retrieval, parallel, generation, verification | llm | partial |
| TIME-008 | temporal_change | understand, structured, retrieval, parallel, generation, verification | llm | insufficient_evidence |
| META-018 | document_lookup | understand, structured, retrieval, parallel, generation, verification | llm | supported |
| PRICE-008 | price_lookup | understand, structured, retrieval, parallel, generation, verification | llm | partial |
| PARTY-006 | relationship | understand, retrieval, parallel, generation, verification | llm | partial |
| TIME-009 | temporal_change | understand, structured, retrieval, parallel, generation, verification | llm | supported |
| META-016 | document_lookup | understand, retrieval, parallel, generation, verification | llm | supported |
| DATE-004 | contract_terms | understand, structured, retrieval, parallel, generation, verification | llm | partial |
| PRICE-004 | price_lookup | understand, structured, retrieval, parallel, generation, verification | llm | partial |
| V4-011 | comparison | understand, retrieval, parallel, generation, verification | llm | insufficient_evidence |
| AMEND-004 | temporal_change | understand, structured, retrieval, parallel, generation, verification | llm | partial |
| AMEND-005 | temporal_change | understand, structured, retrieval, parallel, generation, verification | llm | partial |
| PAY-005 | contract_terms | understand, retrieval, parallel, generation, verification | llm | partial |
| META-007 | document_lookup | understand, retrieval, parallel, generation, verification | llm | supported |
| DATE-001 | contract_terms | understand, structured, retrieval, parallel, generation, verification | llm | partial |
| META-006 | document_lookup | understand, retrieval, parallel, generation, verification | llm | supported |
| AMEND-002 | temporal_change | understand, structured, retrieval, parallel, generation, verification | llm | partial |

## Aggregate

- Generation modes: {'llm': 148, 'refusal': 2}
- Structured engine invoked on 87 questions; graph on 17.
- Refusals: 67/150; verification statuses {'supported': 41, 'partial': 84, 'insufficient_evidence': 25}.
- Every question went to the large model: the small-model route is configured to fall back because no small model is installed.
- The deterministic engines were reached only on questions whose plan requested them; no question was routed to SQL/graph speculatively.
- VLM escalation is configured (`VLM_ENABLED=true`) but no vision model exists locally, so 5 PDF pages logged a 404 and kept their text.

## What is not verified

- Per-question routing *correctness* against a hand-labelled engine expectation was not measured; the sample records the engines actually used.
- The small-LLM and VLM fallbacks could not be exercised end to end because those models are absent.
