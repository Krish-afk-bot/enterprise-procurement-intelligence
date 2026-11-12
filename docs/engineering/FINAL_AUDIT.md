# Final Audit

**Build:** EPI 0.1.0 · branch `phase-2-pipeline-fixes` · 11 November 2026
**Verdict:** **demo-ready with limitations.** It is not production-ready; the
blocking gaps are listed in section K.

Everything below was verified in this working tree on this machine. Where a check
could not be run, it says so instead of assuming success.

---

## A. Repository and architecture audit

- Backend: 163 modules under `backend/app`; routers `health`, `auth`, `query`,
  `documents`, `procurement`, `graph`, `evaluation`, `admin`.
- Frontend: React 18 + TypeScript SPA in `frontend/src`, 16 route components,
  TanStack Query, Zustand, React Router, Tailwind, Radix, GSAP, Three.js.
- Database: SQLAlchemy async, 5 model modules, Alembic revisions `0001`–`0004`;
  live dev database at head `20261105120000` with the lease columns present.
- Providers are pluggable with local implementations and recorded fallbacks:
  vector (Qdrant/local), graph (Neo4j/local), cache (Redis/memory), storage
  (S3/local), embeddings, reranker, LLM/VLM, BM25.
- Documentation for the architecture, security model, testing and deployment is in
  `docs/architecture/OVERVIEW.md`, `docs/security/SECURITY.md`,
  `docs/testing/TESTING.md`, `docs/deployment/DEPLOYMENT.md`, with the measured
  retrieval results in `docs/engineering/EVALUATION.md`.

## B. Backend hardening

- Atomic job claiming (`UPDATE … WHERE status='queued'`, `rowcount` guard) —
  covered by `tests/reliability/test_ingestion_job_claim.py`.
- One queue owner via `WORKER_MODE` (`embedded` / `external` / `disabled`); the
  compose API runs `external` with a dedicated `worker` service.
- Worker leases with heartbeat; lease-aware requeue; terminal statuses clear the
  lease (`test_job_leases.py`).
- Bounded streaming uploads (`read_upload_bounded`), covered by
  `tests/ingestion/test_bounded_upload.py`.
- Document deletion removes derived rows explicitly (SQLite does not enforce
  cascades); `test_document_delete_cleanup.py`.
- Cancellation endpoint (`POST /documents/{id}/cancel`), audited, verified over
  HTTP (200, second cancel 404, viewer 403).
- Non-development startup schema gate (`assert_schema_current`);
  `tests/security/test_schema_gate.py`.
- Self-registration no longer joins the demo tenant; login resolves a unique
  email to its workspace and rejects ambiguous ones.
- **Fixed in this pass:** `/health` and `/ready` read `container._providers`,
  which never existed, so every call logged a provider-check failure and
  reported zero providers while returning 200. Both now use
  `Container.provider_map()`; a real-container regression test asserts every live
  provider is reported (`tests/unit/test_health_provider_reporting.py`). Verified
  over HTTP: `/health` returns `status: ok`, `degraded: false`, providers
  including `vector`, `graph`, `cache`, `storage`, `sparse`, `embedding`,
  `reranker`, `llm`, `vision`.

## C. Ingestion reliability

- **HTML notices are now supported** (`app/ingestion/parsers/html.py`,
  standard library only): headings, paragraphs, tables, script/style removal,
  honest "logical page 1" numbering. `.html`/`.htm` were added to upload
  validation and `ALLOWED_EXTENSIONS`. Without this, 18 of the 20 real tender
  documents could not be ingested at all.
- **Fixed:** first-time ingestion never left `processing`. A job's indexing
  version (1) was treated as a candidate version, and activation refuses to
  promote a candidate equal to the active version, so the document stayed
  `processing` forever with its chunks already written. `is_candidate_version`
  now requires a strictly different version, and the progress callback no longer
  overwrites terminal statuses. Confirmed by re-indexing all 20 documents:
  `19 indexed, 1 needs_review`.
- **Fixed:** one unreachable VLM failed the whole PDF even after successful
  parsing, OCR and chunking (`ConnectError`). Vision escalation now degrades the
  affected pages with a recorded warning and keeps the document.
- Recovery sweep for abandoned candidate versions and orphaned derived rows runs
  once per worker instance.

## D. RAG correctness and evaluation

- Retrieval, fusion, reranking, structured SQL and graph traversal are all
  tenant- and access-level filtered before content reaches a model.
- Metrics are computed by the pipeline that serves users, not a parallel harness.
- Recorded results (12 hand-labelled questions over the real corpus, extractive
  mode): hybrid recall@5 0.55 / MRR 0.55 / nDCG@10 0.55 / answer correctness
  0.55 / citation validity 1.0; dense 0.55 recall, sparse 0.18. Mean latency
  ~21 s per question. Full table and caveats in
  `docs/engineering/EVALUATION.md`.
- These numbers are weak-to-moderate and the set is small. They are reported as
  measurements, not as a quality claim.

## E. Frontend

- Every route in `App.tsx` resolves; heavy analysis pages are lazy-loaded.
- `npm run build` succeeds (TypeScript + Vite, 19.6 s, one chunk-size warning).
- The dev server runs at `http://localhost:5173` and the landing page renders
  correctly (headline, platform sections, capability panels, security section,
  footer); the preview is registered in this thread.
- The landing page states plainly what is not implemented (SSO, MFA, malware
  scanning, independent review) rather than implying certification.
- Workspace pages are functional but share one visual vocabulary; the
  surface-by-surface art direction work called for in the design brief was not
  completed for contracts/suppliers/compare/graph/evaluation/admin in this pass.

## F. Dataset and corpus

- Real corpus imported through the API from
  `data/real_procurement_ocds/sample/document_validation` (20 notices, 2.5 MB):
  PDF, DOCX and HTML, with `source`, `source_url`, `license` (OGL-UK-3.0) and
  `original_id` (OCID) recorded on each document.
- Provenance manifest: `data/real_procurement_ocds/sample/ingestion_provenance.json`
  with SHA-256, OCID, source URL, document id, pages, chunks and final status per
  file. Rebuild it any time with `python scripts/ingest_real_corpus.py --reconcile`.
- One file (`0664eb_tender_13.html`, 806 bytes) is an empty portal page. It is
  correctly `needs_review` with zero chunks; no text was invented for it.
- Structured procurement data already in the database: 65,402 suppliers and
  83,724 OCDS records. The nine synthetic documents referenced by earlier work
  were not present in this working tree and were not recreated.

## G. Testing

- 61 test modules; **the full backend suite passes**: 634 passed, 8 skipped
  (exit 0). The skips are environment-gated live-model tests.
- The 18 failures found at the start of this pass are fixed: 12 checkpoint
  fixture defects (missing `indexing_version`, wrong job state defaults, stale
  `execute()` counts, wrong patch target for the pipeline's `session_scope`),
  4 evaluation-v2 tests now driven by an in-test fixture, and the RAG smoke test
  updated to the current provider/agent API. Repairing the checkpoint tests
  exposed a real bug, now fixed: a failed candidate re-index marked the live
  document `processing`.
- New tests added in this pass: health provider reporting (3), HTML parsing (3),
  ingestion resilience (4), all passing.
- Frontend: `npm test` runs again — 33 tests across 4 files, all passing, after
  restoring `vitest.config.ts` and the jest-dom setup file. `npm run build`
  succeeds. `npm run e2e` runs five Playwright journeys against the dev server
  (landing, sign-in, real retrieval, auth guard, and a render pass over Ask,
  Documents and Search that fails on an uncaught page error); all five pass.

## H. Deployment

- `docker-compose.yml` now has Dockerfiles to build: `backend/Dockerfile`
  (dependencies read from `pyproject.toml`), `frontend/Dockerfile` (node build +
  nginx with SPA fallback and an `/api/` proxy) and `frontend/nginx.conf`.
- `docker compose config -q` and `docker compose --profile app config -q` parse
  cleanly.
- **Built and import-checked:** `epi-web:test` built at 96.9 MB and `epi-api:test`
  at 5.16 GB; `docker run --rm epi-api:test python -c "import app.main"` prints
  `IMPORT_OK`. The first backend build failed on a PyPI read timeout (fixed with
  retries and a CPU-only torch install).
- **Not verified:** no container has been started against a live database or
  model endpoint, so compose runtime behaviour is untested.
- Migrations run in the `api` entrypoint; production startup refuses a missing or
  stale schema; `/ready` gates traffic on database, vector and embedding health.

## I. Documentation

Added in this pass: architecture overview, security model, testing guide,
deployment guide, evaluation results, and this audit. They describe the code as
it is, including the gaps below.

## J. Security posture

Implemented: Argon2 passwords, short-lived JWT access tokens, rotating refresh
tokens in httpOnly cookies with replay detection, five-role RBAC plus document
access ceilings enforced in retrieval, tenant scoping from the token only, audit
logging with truncation, upload validation with bounded reads, injection guards
on retrieved text, per-route rate limiting, startup secret validation, CORS
allow-list.

Not implemented (and not claimed on the landing page): SSO/SAML/OIDC, MFA,
per-document ACLs, application-level encryption at rest, malware scanning,
tamper-evident audit logs, per-tenant rate limits.

## K. Verdict and blockers

**Demo-ready with limitations.**

Blocking for production:

1. **Latency is still too high for interactive use.** Dense answers average
   4.5 s and `hybrid_rerank` 8.6 s on this machine; a cold question adds a ~12 s
   query-understanding model call. The numbers are measured, not estimated.
2. **The composed stack has never been started.** Both images now build —
   `epi-web:test` at 96.9 MB and `epi-api:test` at 5.16 GB — and the API image
   imports `app.main` cleanly, but no container has been run against a live
   database and model endpoints, so runtime behaviour in the compose topology is
   unverified. The first build failed on a PyPI read timeout; the Dockerfile now
   retries and installs CPU-only torch instead of the ~2 GB CUDA wheel set.
3. **`hybrid_rerank` and `agentic` were measured only on 12 questions.** Recall
   and MRR are now 1.0 on that set, which mostly means the set is small and the
   corpus is small; it is a regression guard, not a quality claim at scale.
4. **The 120-question v2 benchmark is still missing.** The tests and runner work,
   but the production dataset the project used to measure baselines was deleted,
   and a replacement cannot be honestly generated in a single session.
5. **The browser suite is not in CI.** It needs the API, a seeded database and a
   running dev server; adding it means a service container plus seeding, which is
   a deployment decision rather than a code fix.

Recommended next steps, in order: start the compose stack once and fix what the
first boot breaks; profile the query path before adding features; exercise the
MCP server through a real client and add the connectors that earn their place;
build a graph evaluation set before claiming Graph RAG improves quality.

## L. Knowledge graph

Implemented and verified in this tree:

- A property graph derived from ingested rows, with two interchangeable
  providers — local SQLite (`var/graph.db`) and Neo4j — behind one interface.
- Typed nodes and edges for supplier, contract, amendment, product, price,
  compliance certificate, document and category, carrying `document_id`,
  `source_page` and temporal properties so a graph path is citable.
- Multi-hop traversal, tenant scoping enforced in the query, a documented
  read-only Cypher subset, and four HTTP endpoints behind `graph:read`.
- GraphRAG integrated into the answer path for relationship and supplier-scoped
  questions, with graph edges turned into citations.
- `tests/unit/test_graph_store_contract.py` covers per-type counts, tenant
  isolation, hop limits and provenance; `tests/ingestion/test_party_name_validation.py`
  covers which extracted phrases may become entities.
- `docs/architecture/KNOWLEDGE_GRAPH.md` records the design and its gaps.

Confirmed gaps:

1. **MCP is read-only, internal and stdio-only.** The server exists with seven
   guarded read tools (section M), but it has no external connectors, no graph
   tool, no HTTP transport, and no client handshake has been exercised here.
2. **Entity resolution is name-based only.** No identifier scheme, no merge
   review queue, no candidate list.
3. **Historical rows were created from prose.** Names such as "the council" were
   stored as suppliers before the name check existed. Extraction now rejects
   them; `scripts/audit_graph_entities.py` lists the existing rows read-only and
   nothing is deleted automatically. On the imported corpus it reports 277
   candidates out of 65,406 supplier rows — most are numeric identifiers from
   the FTS dataset rather than prose.
4. **No graph evaluation.** No extraction-accuracy set, no multi-hop recall
   measurement, so no graph-versus-vector comparison can be claimed.
5. **Temporal filtering is implemented but not derived automatically.**
   `providers/graph/temporal.py` drops edges outside their
   effective/expiry window, and the filter is reachable through
   `GET /graph/paths?as_of=` and `get_entity_neighbours`. The answer pipeline
   does not yet infer an as-of date from a question, so GraphRAG traverses
   without one.
6. **Clause and obligation nodes are written, with limits.** Clause-tagged chunks
   become `Clause` nodes (`Document -CONTAINS-> Clause`) and clauses containing
   `shall`/`must`/`agrees to` gain an `Obligation` node (`Clause -IMPOSES->`).
   Detection is lexical, not legal interpretation. Documents indexed before this
   change need re-indexing, and a chunker that emits no clause number produces
   no clause nodes.

## M. MCP tool boundary

Implemented in `app/mcp_server/` on the official SDK (`mcp>=1.21`), with
`docs/architecture/MCP_ARCHITECTURE.md` as the record:

- Nine read-only tools over the same tenant-scoped session/service layer as the
  HTTP API: document and contract search, document metadata, supplier profile,
  contract amendments, ingestion status, evaluation metrics, graph entity search
  and neighbourhood traversal (with an optional as-of date).
- The process is bound to one tenant and one account by configuration
  (`MCP_TENANT_ID`, `MCP_USER_EMAIL`, `MCP_ROLE`). No tool accepts a tenant
  argument, so a client cannot widen its scope; a missing value is a startup
  error, not a default.
- Every call is authorised against the tool's declared permission before any
  work, bounded by a per-call timeout and a per-tool rate limit, audited with its
  outcome, and required to return JSON-native data so internals cannot leak.
- `tests/unit/test_mcp_server.py` covers identity binding, unknown permissions,
  denial auditing, timeout, rate limit, non-JSON output and the tool registry.

- The boundary was then exercised **over the wire**, not just in process:
  `scripts/verify_mcp_stdio.py` spawns the server, completes the handshake,
  confirms seven advertised tools, runs two read tools and confirms a viewer is
  refused. The same check is `tests/integration/test_mcp_stdio.py` under
  `EPI_MCP_STDIO=1`.

Gaps: no external connectors, graph access is read-only and label-allowlisted,
stdio transport only, limits are per process, and the wire test is opt-in rather
than part of the default suite.
