# EPI Repository Audit — Stage Zero

Date: 5 November 2026 · Scope: `backend/` (163 Python modules), `frontend/src/` (119 TS/TSX files),
`backend/tests/` (46 test modules), `alembic/versions/` (3 revisions), `docker-compose.yml`, `.env.example`.

This is the inventory taken before changes. Findings are classified as the brief requires; only items
marked **confirmed defect** were verified by reading the code path or executing it.

## 1. Architecture as built

```
Browser (React 18 + Vite, TanStack Query, Zustand, GSAP, R3F)
   │  /api/v1  (Vite dev proxy → FastAPI)
FastAPI (app/main.py, lifespan-managed)
   ├── API routers: auth, documents, query, procurement, graph, admin, evaluation, health
   ├── services/: auth, documents, procurement, evaluation, reconciliation
   ├── agents/: LangGraph-style pipeline (state → nodes → pipeline → claim_binding → verification)
   ├── retrieval/: query_understanding, retriever, fusion, structured, graph_retrieval, context
   ├── ingestion/: validation, parsers (pdf/office/image), layout, ocr, extractors, chunking, pipeline, jobs
   ├── providers/: embedding, reranking, llm, vision, vector (local/qdrant), graph (local/neo4j),
   │               cache (memory/redis), storage (local/s3), sparse
   ├── security/: tokens, rbac, scope, audit, injection, revocation
   ├── workers/ingestion_worker.py  (asyncio loops; also a process entrypoint)
   └── db/: SQLAlchemy 2.0 async models + Alembic
```

Local-first by design: with an empty `.env` the stack runs on SQLite, an on-disk numpy vector index, a
SQLite property graph, in-memory cache and filesystem storage, and labels the absence of a language model
instead of simulating one. Optional Docker services (Postgres, Qdrant, Neo4j, Redis, MinIO) are wired in
`docker-compose.yml` behind the `app` profile.

## 2. Data model

19 tables across four model modules: tenants/users, documents/pages/chunks/tables, procurement domain
(suppliers, contracts, contract parties, awards, prices, compliance certificates), operations
(ingestion jobs, audit log, agent traces, evaluation runs). Documents carry `active_indexing_version`
and `candidate_indexing_version`; chunks, prices and certificates carry `indexing_version` + `is_active`,
so re-indexing is a staged cutover rather than an overwrite.

## 3. Findings

### Confirmed defects (all in the ingestion job path unless noted)

| # | Finding | Evidence | Status |
|---|---|---|---|
| 1 | `claim_next_job` was not atomic: `SELECT` then Python mutation | `app/ingestion/jobs.py` read at `claim_next_job`; two loops under `WORKER_CONCURRENCY=2` can select the same `queued` row before either commits | **Fixed** — conditional `UPDATE … WHERE id = ? AND status = 'queued'`, `rowcount` decides the winner, `attempts` incremented in the same statement |
| 2 | The API process always started its own `IngestionWorker`, while `python -m app.workers.ingestion_worker` starts another | `app/main.py` lifespan unconditionally constructed `IngestionWorker` | **Fixed** — `WORKER_MODE` (`embedded`/`external`/`disabled`); compose runs the API as `external` and adds a dedicated `worker` service |
| 3 | Uploads were fully buffered before the size limit was checked | `documents.py`: `content = await file.read()` then `validate_upload(...)` compares `len(content)` | **Fixed** — `read_upload_bounded` streams 1 MB chunks and raises `FileValidationError` on the chunk that crosses `MAX_UPLOAD_MB` |
| 4 | Compose docstring referenced a `worker` service that did not exist | `docker-compose.yml` header vs services list | **Fixed** — service added |

### Architectural risks (not yet proven at runtime)

- **SQLite default in “production-ish” runs.** `AUTO_CREATE_SCHEMA=true` is the `.env.example` default and
  compose forces it to `false`, but a deployment that forgets to run Alembic starts with no schema. Needs a
  startup assertion, not a warning.
- **Ingestion worker lives in the same event loop as the API when `embedded`.** Long CPU-bound parsing can
  stall request handling. Acceptable for local development, not for production.
- **Resolved in this pass: leases.** Claims now carry `lease_token` + `lease_expires_at`; the worker renews
  from a heartbeat and cancels its pipeline if renewal fails. A crash or lost lease leaves a partially written
  candidate version; `app/ingestion/cleanup.py` sweeps it once stale (no live job, older than the cutoff),
  deleting only candidate-version rows and vectors and clearing the reservation.
- **Provider fallback.** `ALLOW_PROVIDER_FALLBACK=true` is the default; the audit did not yet trace whether
  a fallback is always surfaced in the response payload.
- **Search/analytics truthfulness.** Dashboard and analytics were verified to read from the API, but each
  endpoint's aggregation query has not yet been reconciled against the database by hand.

### Missing capabilities

- No OCR fallback verification against a scanned PDF in this environment (`OCR_ENABLED=true`, but the
  OCR stack is optional and untested here).
- No real procurement corpus imported — the nine synthetic documents remain the only corpus, untouched.
- No evaluation run has been recorded against real filings; `app/evaluation` exists and is unit-tested only.
- No CI workflow file was found; checks are run locally.

### Performance concerns

- Frontend production entry is 542.89 kB (163.51 kB gz) with the WebGL hero; Lighthouse performance
  measured 76 on this machine (reported separately in `docs/redesign/PERFORMANCE_REPORT.md`).
- No index was verified for the cross-store reconciliation query used by the worker's outbox pass.

### Requires runtime verification

- Upload streaming through the real ASGI stack (tests cover the reader, not a multipart request).
- Concurrent claims across two uvicorn/worker **processes** (SQLite serialises writes; the guard is
  exercised in-process, PostgreSQL row locking is not exercised here).
- Worker crash recovery during activation, partial vector upload, and graph sync retries.

## 4. Test inventory

46 modules: unit (chunking, fusion, claim binding, grounding, refusal, tokens, citation selection,
entity resolution, reranker cost, tracing), security (tenant isolation, authorization audit, startup
security, audit truncation), retrieval (compare, structured, supplier scoping, temporal filtering),
ingestion (candidate version, version indexing, activation), integration (API contract, auth, refresh, RAG
pipeline, live LLM — the last requires a configured provider), reliability (failure injection).

`pytest` is configured with `asyncio_mode = "auto"`; the suite runs against SQLite with local providers.

## 5. Plan (priority order)

1. **Ingestion correctness** (done in this pass): atomic claim, single worker owner, bounded upload, tests.
2. ~~**Queue durability**: leases/heartbeats replacing the fixed 30-minute requeue cutoff~~ — leases and
   heartbeat-driven cancellation are implemented and tested; cleanup of abandoned candidate versions remains.
3. **Schema/migration gate**: refuse to serve on a missing schema in non-development environments.
4. **Retrieval and citation verification** against a real document set with recorded metrics.
5. **Frontend workspace art direction** for contracts, suppliers, compare, graph, evaluation, admin.
6. **Real corpus import** (SEC Exhibit 10 / SAM.gov) with a provenance manifest, in an isolated database.

Stages 3–9 of the brief are not complete; this document is the baseline the rest is measured against.
