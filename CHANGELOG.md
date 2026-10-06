# Changelog

All notable changes to this project are documented here.

This project follows [Conventional Commits](https://www.conventionalcommits.org/)
and the format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

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
