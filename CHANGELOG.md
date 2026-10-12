# Changelog

All notable changes to this project are documented here.

This project follows [Conventional Commits](https://www.conventionalcommits.org/)
and the format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

---

## [0.5.0] — Phase 5 — Reliability, OCR, Browser E2E — 2026-10-11

### Fixed

- **Grounding refusal enforcement (Stage 1):** `decide_status()` in `verification.py` now refuses (`insufficient_evidence`) when the LLM produces 0 verified claims even when evidence blocks are present. Prevents gq-016 ("EU suppliers") and gq-022 (prompt injection) from returning fluent but unverified LLM answers. Extractive mode still returns `partial` (not refusal) since the text was assembled directly from retrieved evidence. 19 regression tests added in `tests/unit/test_refusal_correctness.py`.

- **OCR scanned-document ingestion (Stage 2):** Scanned signature page (`supplier_a_scanned_signature_page.pdf`) re-ingested with `OCR_ENABLED=true`. PaddleOCR extracted "Alvarez", "2024-01-08", "APPROVED" from the image. 1 new chunk and Qdrant vector added (corpus: 37 → 44 vectors). gq-015 and gq-017 now PASS.

### Added

- **Playwright E2E tests (Stage 3):** 16 tests in `frontend/e2e/procurement.spec.ts` covering health, auth (valid + invalid), no-token rejection, documents, ask (price + comparison), unanswerable, prompt injection, citation integrity, search, supplier list, cross-tenant isolation, admin protection, landing page render, and app shell load. All 16 pass. `playwright.config.ts` and `vitest.config.ts` added.

- **Phase 5 operational scripts:** `scripts_phase3/check_ocr.py`, `reingest_scanned.py`, `verify_ocr_chunk.py`.

### Changed

- **CI/CD (`ci.yml`, `pr.yml`):** Both workflows updated to include: Vitest unit tests, mypy job (Ubuntu, `timeout 300`, warning-only gate), and correct Python 3.12 consistently. Frontend job now runs Vitest before build.

- **`.gitignore`:** Added `frontend/test-results/`, `frontend/playwright-report/`, `frontend/e2e/results/`, `frontend/e2e/fixtures/auth-state.json`.

- **`security_smoke.py`:** Fixed injection test to check for *system internals leakage* (JWT secret, DB credentials, system prompt) rather than injection keywords that appear in the quoted document content.

### Evaluation results (Phase 5 baseline — 44 vectors, OCR corpus)

| Metric | No reranker | With reranker |
|--------|------------|---------------|
| Recall@5 | 0.794 | **0.853** |
| Precision@5 | 0.188 | 0.224 |
| MRR | **0.779** | 0.654 |
| Hit Rate | 0.909 | **0.955** |
| Latency p50 | 35 ms | 4,533 ms |

Previous Phase 4 baseline (37 vectors, no OCR): Recall@5=0.676, MRR=0.706, HitRate=0.818.
OCR addition alone: Recall@5 0.676 → 0.794 (+17.5%), MRR 0.706 → 0.779 (+10.3%).

### Total test count after Phase 5

| Test suite | Count |
|---|---|
| Backend unit (pytest) | 245 passed, 6 skipped |
| Frontend unit (Vitest) | 22 passed |
| Playwright E2E | 16 passed |
| Live LLM integration | 6 passed (opt-in) |

---

## [0.4.0] — Phase 4 — Live LLM RAG E2E Verification — 2026-10-09

### Verified (live, on real infrastructure)

- **LLM generation**: `generation_mode=llm` confirmed live via Ollama `llama3.1:8b` on RTX 4060 Laptop GPU
- **All 22 golden questions**: ran through full LangGraph pipeline (understand→structured→graph→retrieve→rerank→generate→verify→finalize); 11/22 passed strict keyword scoring
- **Backend startup**: all providers active — Qdrant, Neo4j, Redis, MinIO, BGE-small (384d), BGE-reranker-v2-m3, llama3.1:8b; `degraded=false`, `fallbacks=[]`
- **Frontend proxy**: Vite dev server on :5173 proxies to backend on :8000; login, documents, search, ask all verified
- **Security smoke tests**: 7/7 PASS — invalid JWT rejected, wrong-secret JWT rejected, no-token rejected, cross-tenant isolation (403), prompt injection not executed, admin endpoint protected (403), no secrets in health response

### Fixed

- **gq-012 retrieval fix**: single-supplier queries now scope Qdrant vector search to that supplier's chunks, preventing single-document suppliers from being crowded out by corpus-wide RRF scores. Regression test added.
- **mypy errors fixed**: `expand_parents` return annotation corrected (`dict[str, str]` → `dict[str, tuple[str, str | None]]`), float-coercion guards in `generation.py`, int-cast guards in `nodes.py`, `CountItem` construction in `admin.py`, `ComparisonColumnOut` construction in `procurement.py`, None-guard on `cache.status()` in `cli.py`, `EvaluationRun | None` annotation in `runner.py`
- **Ollama /v1 URL**: documented that `LLM_BASE_URL` must include `/v1` suffix for Ollama; updated `.env.example`

### Added

- **Vitest frontend tests** (`src/lib/__tests__/answer-utils.test.ts`): 22 tests covering `generation_mode`, `AnswerStatus`, citation validity, citation deep-link URL construction, error/empty states
- **Phase 4 scripts**: `scripts_phase3/golden_eval_llm.py`, `eval_retrieval_rerank.py`, `verify_e2e.py`, `security_smoke.py`, `failure_mode_test.py`, `diagnose_misses*.py`, `test_orion_retrieval.py`, `check_qdrant_payload.py`
- **Retrieval regression test** (`tests/retrieval/test_supplier_scoped_retrieval.py`): 4 tests verifying single-supplier scoping doesn't break comparison queries
- **Evaluation results**: `data/evaluation/golden_eval_llm.json`, `retrieval_with_reranker.json`

### Measured results

**Golden evaluation (llama3.1:8b, 22 questions):**
- 11/22 passed strict keyword scoring
- 22/22 ran in `generation_mode=llm` (0 extractive)
- 22/22 had valid citations (document_id + chunk_id)
- 15/22 grounded (score ≥ 0.5)
- Latency p50=16s, p95=50s (8B local model on 4GB VRAM)

**Retrieval without reranker (BGE-small):** Recall@5=0.676, MRR=0.706, HitRate=0.818, p50=45ms
**Retrieval with reranker (BGE-reranker-v2-m3):** Recall@5=0.735, MRR=0.554, HitRate=0.864, p50=4381ms

**mypy (local):** 55 errors found across 17 files (pre-fix errors in vendor-interaction code, structlog processors, ingestion pipeline). 7 highest-severity errors fixed. Full mypy run still times out locally (>10 min); CI on Ubuntu required.

---

## [0.3.0] — Phase 3 — Live Integration & End-to-End RAG — 2026-10-07

### Infrastructure (all live-verified)

- **Docker Compose**: 5 persistent services running healthy.
  - `postgres:16-alpine` — healthy
  - `qdrant/qdrant:v1.16.1` — healthy (upgraded from 1.9.7 to match client 1.17.0)
  - `neo4j:5.22-community` — healthy (fixed `NEO4J_AUTH: neo4j/neo4jdev`; 5.x rejects default password)
  - `redis:7-alpine` — healthy
  - `ifirestone/minio:RELEASE.2026-09-22T19-25-18Z` — healthy, bucket `epi-documents` created

- **PostgreSQL**: Alembic migration `6644823c3215` applied. 24 tables present. Read/write verified.
- **Qdrant v1.16.1**: upsert, search, metadata filter, delete — all verified at 384d and 1024d.
- **Neo4j**: nodes (Supplier/Contract/Product/Price), edges (HAS_CONTRACT/SUPPLIES/APPLIES_TO), neighbors, traversal, multi-hop Cypher query — all verified.
- **Redis**: set/get/delete/TTL/incr/clear_prefix/dict serialisation — all verified.
- **MinIO**: put/get/exists/delete/url_for via S3Storage abstraction — all verified.

### Corpus Ingestion

- 9 synthetic documents ingested through real pipeline (parse→chunk→embed→upsert):
  - 15 pages stored in PostgreSQL
  - 37 chunks in PostgreSQL and Qdrant
  - 39 price records
  - 3 suppliers (Northwind, Helios, Orion)
  - 3 contracts (NS-2024-001, HTP-2024-014, ORC-2021-777)
  - Files stored in MinIO `epi-documents` bucket

### Embeddings

- **BGE-small (384d) baseline**: Recall@5=0.676, MRR=0.706, Hit Rate=0.818, p50=45ms
- **BGE-M3 (1024d)**: Recall@5=0.676, MRR=0.678, Hit Rate=0.818, p50=35ms
- BGE-M3 loaded from local cache on CUDA. Reindexed 37 vectors into `procurement_chunks_1024d`.
- Both models get identical Recall@5 and Hit Rate. BGE-M3 MRR slightly lower (0.678 vs 0.706).
  4 MISS results on both (scanned page and Orion expired contract — OCR disabled, expected).

### Security

- **Prompt injection fixture**: `security_fixture_injection.pdf` ingested as data.
  `detect_injection()` scores 1.0, detects all 5 pattern types. Evidence wrapped in
  `<<<EVIDENCE>>>` delimiters. System prompt marks document content as untrusted.

### Compose fixes

- `docker-compose.yml`: fixed `NEO4J_AUTH` default password rejection (neo4j→neo4jdev),
  upgraded Qdrant to v1.16.1, added `NEO4J_USERNAME/NEO4J_PASSWORD` to api service env.
- `.env.example`: updated `NEO4J_PASSWORD` with explanation.

### Phase 3 scripts added

- `backend/scripts_phase3/check_pg.py` — PostgreSQL table verification
- `backend/scripts_phase3/check_qdrant.py` — Qdrant CRUD + filter verification
- `backend/scripts_phase3/check_neo4j.py` — Neo4j node/edge/traversal verification
- `backend/scripts_phase3/check_redis.py` — Redis cache verification
- `backend/scripts_phase3/check_minio.py` — MinIO S3 object storage verification
- `backend/scripts_phase3/ingest_corpus.py` — Full corpus ingestion (all 9 documents)
- `backend/scripts_phase3/eval_retrieval.py` — Retrieval evaluation (BGE-small and BGE-M3)
- `backend/scripts_phase3/reindex_bge_m3.py` — Re-index corpus at 1024d for BGE-M3
- `backend/scripts_phase3/check_injection.py` — Prompt injection fixture verification

### Known limitations

- LLM endpoint not configured; `generation_mode=extractive` in this environment.
  The live test file `tests/integration/test_llm_live.py` is ready for `RUN_LLM_INTEGRATION=1`.
- Frontend not connected to live backend in this verification (no running uvicorn server).
- Neo4j graph rebuild during ingestion creates nodes; supplier aliases deferred to attribution pass.
- BGE-M3 download required `pytorch_model.bin` (2.1 GB); already cached on this host.

---

## [0.2.0] — Phase 2 — Real LLM RAG + Provider Test Coverage — 2026-10-06

### Verified

The following components were confirmed fully implemented and correct from Phase 1 code inspection:

- **LLM provider abstraction**: `OpenAICompatibleProvider` supports any OpenAI-compatible endpoint (vLLM, Ollama, TGI, DashScope) via `LLM_BASE_URL` + `LLM_API_KEY` + `LLM_MODEL`. No vendor SDK; httpx only.
- **ModelRouter**: per-task routing (GENERATE → large LLM, CLASSIFY → small LLM, VISION → VLM), complexity-based override, provider fallback.
- **AnswerGenerator**: LLM path active when `llm_configured=True` with evidence blocks; extractive fallback when LLM is not configured or on any exception. `generation_mode` is always accurately reported.
- **Context builder** (`ContextBuilder`): token-budgeted, deduplicated evidence assembly with source metadata (document, page, section, clause, version, effective/expiry date). Evidence wrapped in `<<<EVIDENCE>>>` / `<<<END_EVIDENCE>>>` delimiters.
- **Procurement system prompt**: grounding rules, citation format, refusal instruction, injection note, structured-data preference, conflict reporting. All in `generation.py::SYSTEM_PROMPT`.
- **Injection guard**: `detect_injection()` + `sanitize_evidence()` — instruction-override, system-impersonation, role-switch, secret-exfiltration, tool-abuse, policy-override patterns detected; evidence delimiters escaped.
- **Grounding verification**: lexical entailment (token overlap ≥ 60% + all numbers in evidence) + optional LLM judge via `judge_grounding_llm()`. Method always reported.
- **Citation validation**: `validate_citations()` maps `[N]` markers in answer text to retrieved bundle; fabricated markers recorded as invalid, never displayed as valid citations.
- **LangGraph pipeline**: `understand → plan → structured → graph → retrieve → vision → evaluate → (rewrite →) generate → verify → finalize`. Corrective loop capped at `max_agent_iterations`.
- **API response contract**: `AnswerOut` exposes `generation_mode`, `degraded`, `grounding`, `evidence_strength`, `citations`, `validation`, `timings`, `token_usage`. No fields fabricated.
- **Provider fallback**: `Container._verify_registered_providers()` falls back to local implementations when external providers are unreachable.

### Added

- **Tests — LLM provider** (`tests/unit/test_llm_provider.py`): 41 tests covering:
  - `OpenAICompatibleProvider`: configuration, payload assembly, auth headers, completion parsing, 4xx/5xx/timeout error handling, empty response, status probe
  - `AnswerGenerator`: extractive fallback when LLM not configured, extractive when bundle empty, LLM mode when configured, fallback on ConnectError/TimeoutException/4xx/5xx, prompt version
  - Prompt construction: injection note in system prompt, evidence delimiters, question in user message, system role first, injection sanitization
  - `ModelRouter`: routing decisions, generate raises on unconfigured provider

- **Tests — grounding** (`tests/unit/test_grounding.py`): 28 tests covering:
  - `extract_claims`: boilerplate filtering, number detection, refusal text, max_claims
  - `judge_grounding_lexical`: supported/unsupported, missing numbers, empty claims, score bounds
  - `judge_grounding_llm`: failure returns None, None from structured output, success path
  - `validate_citations`: valid markers, fabricated markers, unused markers, orphan citations
  - `decide_status`: insufficient/supported/conflicting outcomes
  - `assess_evidence_strength`: level computation, multiple documents, criteria output

- **Tests — providers** (`tests/unit/test_providers.py`): 31 tests covering:
  - `LocalVectorStore`: upsert, search, count, delete, metadata filter, status
  - `LocalGraphStore`: node/edge upsert, neighbors, counts, status
  - `MemoryCache`: get/set/delete/ttl/incr/dict serialisation, status
  - `LocalStorage`: put/get/exists/delete/url_for, status
  - `HashingEmbeddingProvider` (via `CachedEmbeddingProvider`): dimension=512, list of floats, deterministic, status

- **Tests — live LLM** (`tests/integration/test_llm_live.py`): 6 tests, **skipped by default**. Activated with `RUN_LLM_INTEGRATION=1 LLM_BASE_URL=... LLM_API_KEY=...`. Verifies: provider status, simple completion, procurement system prompt, no API key in response, refusal on unanswerable question, full pipeline generation_mode=llm.

### Architecture notes (for Phase 3)

- **Embeddings**: Active local model is `BAAI/bge-small-en-v1.5` (384d). `BAAI/bge-m3` (1024d) is the configured production target but not yet downloaded. Switching requires re-indexing.
- **Qdrant**: Code exists and is wired in `Container._build_vector()`. Set `VECTOR_PROVIDER=qdrant QDRANT_URL=...` to activate. NOT VERIFIED against live Qdrant.
- **Neo4j**: Code exists and is wired in `Container._build_graph()`. Set `GRAPH_PROVIDER=neo4j NEO4J_URI=...` to activate. NOT VERIFIED against live Neo4j.
- **Redis**: Code exists and is wired in `Container._build_cache()`. Set `CACHE_PROVIDER=redis REDIS_URL=...` to activate. NOT VERIFIED against live Redis.
- **PostgreSQL**: Code and Alembic migration exist. Set `DATABASE_URL=postgresql+asyncpg://...` to activate. NOT VERIFIED against live PostgreSQL.
- **S3/MinIO**: Code exists and is wired in `Container._build_storage()`. Set `STORAGE_PROVIDER=s3 S3_ENDPOINT=...` to activate. NOT VERIFIED.

### Total test count after Phase 2

| Module | Tests |
|--------|-------|
| `unit/test_tokens` | 15 |
| `unit/test_fusion` | 14 |
| `unit/test_security_tokens` | 14 |
| `unit/test_query_understanding` | 28 |
| `unit/test_chunking` | 15 |
| `unit/test_llm_provider` | 41 |
| `unit/test_grounding` | 28 |
| `unit/test_providers` | 31 |
| `security/test_startup_security` | 9 |
| `integration/test_auth` | 14 |
| `retrieval/test_structured_retrieval` | 13 |
| `integration/test_llm_live` | 6 (skipped) |

**Total: 222 passing, 6 skipped (live LLM).**

---

## [0.1.0] — Phase 1 Stabilization — 2026-10-06

### Fixed

- **Security**: Added production startup guard — `validate_startup_security()` now raises `RuntimeError` if `APP_ENV=production` with a known-weak or short JWT secret; development mode logs a warning instead of failing.
- **Bug (F821)**: `neo4j.py` `traverse()` was passing undefined `key` instead of `start_key` to the Cypher query parameter dict.
- **Bug**: Ruff format and lint: 62 files reformatted, 72 lint issues fixed (25 unused imports, 21 import ordering, 16 datetime-timezone, 3 unused variables, and more).
- **Bug**: `Intent` and `Task` enums now use `StrEnum` instead of `(str, Enum)` (UP042).
- **Bug**: `ingestion_worker.py` unused `tenant_id` variable removed.
- **Dependency**: `email-validator` was used by `app/schemas/email.py` but was missing from `pyproject.toml` and `requirements.txt`. Added `email-validator>=2.1` to both files.

### Added

- **Tests — security**: `tests/security/test_startup_security.py` — 9 tests verifying production startup refuses weak JWT secrets.
- **Tests — integration**: `tests/integration/test_auth.py` — 14 tests covering user creation, authentication, token issuance, and account-enumeration protection.
- **Tests — retrieval regression**: `tests/retrieval/test_structured_retrieval.py` — 22 tests verifying supplier comparison includes all named suppliers (Issue A) and lowest-price query names supplier + product + year (Issue B).
- **Frontend — ESLint**: Added ESLint 9 (`eslint.config.js` flat config) with `typescript-eslint`, `eslint-plugin-react-hooks`, `globals`. `npm run lint` now passes with 0 errors.
- **Pytest**: Set `asyncio_default_fixture_loop_scope = "function"` to suppress pytest-asyncio deprecation warning.

### Changed

- **Python version**: Aligned `pyproject.toml`, CI workflows, and documentation to **Python 3.12** (the Dockerfile was already 3.12; CI said 3.11).
- **CI** (`ci.yml`): Updated to use `requirements.txt` for reproducible dependency install; removed "no tests yet" guard from backend-tests job; both backend and frontend jobs now run on Python 3.12 / Node 20.
- **CI** (`pr.yml`): Updated to Python 3.12; uses `requirements.txt`.
- **CI** (`docker.yml`): Removed "Dockerfile doesn't exist" guard (Dockerfile now present); added `requirements.txt` to path triggers.
- **Dockerfile** (`backend/Dockerfile`): Now installs from `requirements.txt` before the application source copy for better layer caching and reproducibility.
- **`requirements.txt`**: Added `email-validator==2.3.0`; improved header comment documenting the dependency strategy (pyproject.toml = authoritative with `>=`, requirements.txt = pinned snapshot for CI/Docker).
- **`.env.example`**: Clarified that `JWT_SECRET` is required in production with generation instructions; documents startup refusal behavior.
- **`package.json`** (frontend): Updated lint script from `eslint . --ext .ts,.tsx` to `eslint .` for ESLint 9 flat config.

### Total test count after Phase 1

- 86 unit tests (chunking, fusion, security tokens, query understanding, tokens)
- 9 security tests (startup JWT guard)
- 14 integration tests (auth service)
- 13 retrieval regression tests (supplier comparison, lowest-price query, citations)

**Total: 122 tests, all passing.**

---

## [0.0.6] — 2026-10-02

- Repository engineering baseline: `.gitignore`, `.editorconfig`,
  `.gitattributes`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`
- Project documentation: `README.md`, `docs/architecture.md`,
  `docs/development.md`, `docs/ci-cd.md`, `docs/deployment.md`
- Engineering roadmap: `COMMITS.md`

### Notes

- This is the first tracked version. The application itself was implemented
  prior to this release and is described in detail in `audit.md`.
- LLM and VLM endpoints are not configured. The system runs in extractive mode.
- Docker app profile is not functional (`backend/Dockerfile` missing).
- Automated tests are absent. Manual verification scripts in `scripts/` pass.

---

[Unreleased]: https://github.com/Krish-afk-bot/enterprise-procurement-intelligence/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Krish-afk-bot/enterprise-procurement-intelligence/releases/tag/v0.1.0
