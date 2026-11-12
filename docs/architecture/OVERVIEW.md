# Architecture Overview

This document describes the system that exists in this repository, not an
intended future design. Where something is optional, the default is stated.

## 1. Shape of the system

```
Browser (React SPA)
   │  HTTPS + JSON, SSE for streaming answers, httpOnly refresh cookie
   ▼
FastAPI application  (backend/app)
   ├── api/v1            HTTP surface: health, auth, query, documents,
   │                     procurement, graph, evaluation, admin
   ├── services          business rules (documents, auth, procurement,
   │                     evaluation, reconciliation)
   ├── ingestion         queue + parsers + chunking + OCR + cleanup
   ├── retrieval         hybrid retrieval, fusion, reranking, structured SQL
   ├── agents            answer pipeline, generation, grounding, claim binding
   ├── providers         vector, graph, cache, storage, embeddings, reranker,
   │                     LLM/VLM, BM25, model router
   ├── security          JWT, RBAC, audit, revocation, injection guards, scope
   ├── db                SQLAlchemy models + async session, Alembic migrations
   └── workers           ingestion worker (queue poller, heartbeat, recovery)
   │
   ├── PostgreSQL (production) / SQLite (development)
   ├── Qdrant or on-disk numpy vector index
   ├── Neo4j or SQLite property graph
   ├── Redis or in-process cache
   └── S3/MinIO or local filesystem storage
```

Every external dependency has a locally runnable implementation, selected by
`*_PROVIDER` settings. `Container` (`backend/app/config/container.py`) builds the
providers once per process and records any fallback it had to take, so `/health`
and the Admin screen report what is actually serving traffic rather than what was
configured.

## 2. Request path for a question

1. `POST /api/v1/query/query` (or `/query/stream` for SSE) with a `Principal`
   resolved from the bearer token; the tenant comes from the token, never from
   the request body.
2. `AnswerPipeline` (`backend/app/agents/pipeline.py`) runs query understanding,
   planning, retrieval, reranking, context construction, generation, grounding
   and citation assembly. `AnswerPipeline.answer(strategy=...)` also backs the
   evaluation experiments, which is why an experiment measures the real pipeline.
3. Retrieval (`backend/app/retrieval/`) combines dense vectors, BM25, structured
   SQL over procurement tables, and graph traversal. Results are fused with
   reciprocal rank fusion and reranked (cross-encoder, lexical, or disabled).
4. Generation uses the model router. With no LLM endpoint configured the system
   answers extractively from retrieved evidence instead of inventing text.
5. Grounding verifies each claim against the cited chunk and reports supported
   versus total claims; citations carry document, page and chunk identifiers.
6. Every answer, citation and agent trace is persisted, tenant-scoped.

Tenant and access-level filters are applied inside retrieval and structured SQL
before any content reaches a model or a response.

## 3. Ingestion

Uploads (`POST /api/v1/documents/upload`) are bounded while streaming
(`read_upload_bounded`, `MAX_UPLOAD_MB`) and validated by extension, declared
MIME, sniffed content type and size (`ingestion/validation.py`). Supported
formats: PDF, DOCX, XLSX/XLSM, CSV, TXT, Markdown, HTML, and images
(PNG/JPEG/TIFF) through OCR.

The upload creates a `documents` row and a queued `ingestion_jobs` row; the
request returns immediately.

The worker (`app/workers/ingestion_worker.py`) owns the queue:

- **Atomic claim** — `claim_next_job` issues a conditional `UPDATE … WHERE status
  = 'queued'` and only proceeds when `rowcount == 1`, incrementing `attempts` in
  the same statement.
- **Leases** — a claim stamps `lease_token`/`lease_expires_at`; a heartbeat task
  renews the lease every third of `WORKER_LEASE_SECONDS`. `requeue_stuck_jobs`
  only requeues jobs whose lease expired (legacy rows without a lease fall back
  to start time). A worker that loses its lease stops the pipeline instead of
  writing results it no longer owns.
- **Single owner** — `WORKER_MODE` is `embedded` (default, API owns the loops),
  `external` (dedicated `worker` service; the compose API runs this way) or
  `disabled`.
- **Recovery** — on start the worker sweeps abandoned candidate versions
  (`sweep_abandoned_candidates`) and purges derived rows whose document no
  longer exists (`purge_orphaned_derived_rows`).
- **Cancellation** — `POST /api/v1/documents/{id}/cancel` marks the job
  cancelled, clears the lease and releases the reserved candidate version.

Parsers (`ingestion/parsers/`) dispatch on the sniffed MIME type: `pdf.py`
(PyMuPDF with a pypdf text-only fallback), `office.py` (DOCX/XLSX/CSV/text),
`html.py` (standard-library HTML notices, including tables) and `image.py`
(OCR). DOCX/XLSX/HTML have no physical pages, so they declare logical or sheet
numbering in metadata rather than fabricating page numbers.

Re-indexing writes a new candidate version and activates it only on success; the
previous active version keeps serving queries until then.

## 4. Data model

`backend/app/db/models/` groups the schema:

| Module | Tables |
| --- | --- |
| `tenancy.py` | tenants, users |
| `documents.py` | documents, document_pages, chunks, document_tables, document_versions, ingestion_jobs |
| `procurement.py` | suppliers, contracts, products, prices, compliance_certificates, procurement_records |
| `conversations.py` | conversations, conversation_messages, queries, answers, citations, agent_traces |
| `operations.py` | audit_logs, evaluation_runs, evaluation_results, data_sources |

Migrations live in `backend/alembic/versions` (`0001` initial schema, `0002`
cross-store consistency, `0003` versioned procurement data, `0004` ingestion job
leases). Production startup verifies `alembic_version` matches this build's head
when `AUTO_CREATE_SCHEMA=false`.

SQLite does not enforce `ON DELETE CASCADE` by default, so document deletion
removes derived rows explicitly (`services/documents.delete_document`).

## 5. Frontend

`frontend/src` is a React 18 + TypeScript SPA built with Vite.

- Routing: React Router (`App.tsx`). Public routes: `/`, `/security`, `/privacy`,
  `/terms`. Authenticated: `/dashboard`, `/ask`, `/search`, `/documents`,
  `/documents/:id`, `/contracts`, `/contracts/:id`, `/suppliers`,
  `/suppliers/:id`, `/compare`, `/graph`, `/evaluation`, `/admin`.
- Server state: TanStack Query. Client state: Zustand (`store/auth` keeps the
  access token in memory only and bootstraps via the refresh cookie).
- Heavy analysis pages are lazy-loaded.
- Permission-gated routes use `RequirePermission`, which is convenience only —
  the API enforces the same permissions.
- Styling is Tailwind with Radix primitives; motion uses GSAP where it is
  loaded lazily; the landing page has a Three.js scene.

## 6. Observability and operations

- Structured JSON logging (`observability/logging.py`) with a request id
  propagated through `request_id_var` and echoed as `x-request-id`; response
  time is returned as `x-response-time-ms`.
- Optional tracing via `observability/tracing.py`, enabled by settings.
- `/api/v1/health` reports database status and per-provider availability with
  per-provider timeouts; `/api/v1/ready` blocks traffic on database, vector or
  embedding failure. `/api/v1/admin/indexing` reports queue depth and recent
  jobs; `/api/v1/admin/stats` reports corpus counts.

## 7. Known architectural limits

- Ingestion is a polling queue, not a broker: there is no dead-letter queue and
  no cross-process cancellation signal (cancellation is cooperative at the next
  heartbeat).
- The local vector store and local graph store are single-process, file-backed
  implementations intended for development and small deployments.
- HTML notices have no page structure, so citations for them point at the whole
  notice (logical page 1).
- Vision escalation requires a configured VLM endpoint; without one the pipeline
  stays text-only and says so in `/health`.
