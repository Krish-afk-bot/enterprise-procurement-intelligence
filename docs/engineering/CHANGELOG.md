# Engineering Changelog

## Unreleased — 12 November 2026

### Added

- **Deployment preparation for Vercel + Render + LangSmith.** `render.yaml` defines the `epi-api` web service
  (health check on `/api/v1/ready`, migrations before boot, `WORKER_MODE=external`) and the `epi-worker` background
  worker from the same image; `frontend/vercel.json` pins the Vite build, `dist` output, SPA rewrite and security
  headers. Five documents under `docs/deployment/` cover the runbook, every environment variable, both platforms and
  the infrastructure dependencies. No deployment was performed.

### Changed

- **`/ready` now returns HTTP 503 when a critical provider is unavailable.** It previously returned 200 with
  `ready: false`, so a platform health check would keep routing traffic to an unready instance. (`app/api/v1/health.py`)
- **The ingestion worker handles SIGTERM/SIGINT.** It stops claiming, releases its lease and closes providers instead
  of being killed mid-job, which used to leave the job leased until recovery requeued it.
  (`app/workers/ingestion_worker.py`)
- **LangSmith hides inputs and outputs by default.** Prompts carry retrieved document text; `LANGSMITH_HIDE_IO`
  (default `true`) sets `LANGSMITH_HIDE_INPUTS`/`LANGSMITH_HIDE_OUTPUTS` so traces keep latency and errors without the
  procurement content. (`app/observability/tracing.py`, `app/config/settings.py`)

## Unreleased — 11 November 2026

### Fixed

- **`/health` and `/ready` reported no providers.** Both endpoints iterated `container._providers`, an attribute
  `Container` never had, so every call logged `health_check_provider_check_failed` and returned 200 with an empty
  provider map. `Container.provider_map()` now exposes the live providers; a regression test builds a real container
  and asserts each one is reported. (`app/config/container.py`, `app/api/v1/health.py`,
  `tests/unit/test_health_provider_reporting.py`)
- **A successfully ingested document stayed at `processing`.** First-time ingestion stamps the job with indexing
  version 1, which the pipeline treated as a candidate version; activation refuses to promote a candidate equal to
  the active version, so the document never reached `indexed` even though its chunks were written. `is_candidate_version`
  now requires a strictly different version, and the worker's progress callback no longer overwrites terminal
  statuses. (`app/ingestion/pipeline.py`, `app/workers/ingestion_worker.py`)
- **One unreachable VLM failed an entire document.** Vision escalation called the provider without a guard, so a
  `ConnectError` aborted ingestion after parsing and chunking had already succeeded. The failure is now recorded as a
  warning and the page keeps its text/OCR extraction. (`app/ingestion/pipeline.py`)

### Added

- **HTML notice parsing.** Procurement portals publish tenders as HTML; 18 of the 20 downloaded notices could not be
  ingested before this. New standard-library parser handles headings, paragraphs, tables and script/style removal,
  with honest logical page numbering. `.html`/`.htm` are accepted upload types.
  (`app/ingestion/parsers/html.py`, `app/ingestion/validation.py`, `app/config/settings.py`)
- **Real corpus import with provenance.** `scripts/ingest_real_corpus.py` uploads the OCDS notices through the public
  API and writes `data/real_procurement_ocds/sample/ingestion_provenance.json` (SHA-256, OCID, source URL, licence,
  document id, pages, chunks, status). 20 notices imported: 19 `indexed`, 1 `needs_review` (empty portal page).
- **Labelled evaluation set and recorded metrics.** `data/evaluation/golden_questions.json` (12 questions labelled
  from the notice text) plus `scripts/run_retrieval_evaluation.py`; results in `docs/engineering/EVALUATION.md`.
- **Deployment artifacts.** `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf` and `.dockerignore`
  files, so `docker-compose.yml` can build; both compose profiles validate with `docker compose config`.
- **Documentation:** `docs/architecture/OVERVIEW.md`, `docs/security/SECURITY.md`, `docs/testing/TESTING.md`,
  `docs/deployment/DEPLOYMENT.md`, `docs/engineering/EVALUATION.md`, `docs/engineering/FINAL_AUDIT.md`.
- **Tests:** `tests/ingestion/test_html_parser.py`, `tests/ingestion/test_ingestion_resilience.py`,
  `tests/unit/test_health_provider_reporting.py`.

### Fixed (test suite)

- **The backend suite is green.** The 12 checkpoint tests failed because their fixtures predated the lease/versioning
  work: jobs carried no `indexing_version`, a "ready" job defaulted to `pending`, exact `execute()` call counts no
  longer matched the SQL (candidate-count + CAS + three deactivate/activate pairs = 8), and the tests patched
  `app.db.session.session_scope` while the pipeline holds its own imported reference. Fixtures now describe a ready
  job and both namespaces are patched.
- **A failed candidate run no longer downgrades a live document.** The pipeline set `status="processing"` on every
  run, including candidate re-indexing, so a failed candidate left a serving document looking "processing". Only a
  first ingestion moves the document to processing now; the active version keeps its status until activation.
- **Activation survives a missing job row.** A prepared candidate can be activated after its bookkeeping job row is
  gone; the absence is logged instead of stranding the document.
- **RAG pipeline smoke test imports the current API** (providers are built by `Container`; the old factory names no
  longer exist) and asserts the graph diagram rather than starting a run that needs a model endpoint.
- **Frontend tests and CI restored.** `vitest.config.ts`, `src/test/setup.ts` and `.github/workflows/ci.yml` were
  deleted by the cleanup; with them back, `npm test` runs 33 tests across 4 files and CI covers backend + frontend.

### Fixed (answerability and evidence matching)

- **A well-evidenced subject question could never be answered.** Coverage compared an entity name
  from the question against evidence as a literal phrase, so "master vendor contingent workforce
  recruitment service" did not match the notice's "Master Vendor Contingent Workforce Recruitment
  and Management Services". The gap forced `insufficient_evidence` even with six independent
  documents and fully supported claims. Multi-word names now match when every word appears in the
  text, with plurals and connectives normalised; a single-word name still has to appear, and an
  entity the corpus never mentions is still refused (the existing refusals stay covered by tests).
- **A live query now answers:** "Which tender is for a master vendor contingent workforce recruitment
  service?" returns the FSCS569 notice with `status: supported`, one citation and two supporting
  documents, while "price in 2031 for the Industrial Laptop X200" still refuses for the right reason.

### Added (browser suite, images)

- **Playwright suite restored:** `playwright.config.ts` plus `e2e/smoke.spec.ts` cover the landing
  page, sign-in, a real retrieval journey and the auth guard. Four tests pass against the dev server.
- **Both images build.** `epi-web:test` (96.9 MB) from the Node/nginx Dockerfile, and
  `epi-api:test` (5.16 GB) from the backend Dockerfile, which imports `app.main` inside the
  container. The first backend build failed on a PyPI read timeout mid-download, so the install now
  retries with a longer timeout, and torch comes from the CPU index: `sentence-transformers` was
  otherwise pulling ~2 GB of CUDA libraries a CPU deployment cannot use.
- **Evaluation re-measured with the model live:** dense recall@5 1.0 / answer 1.0 / refusal 0.9167 at
  4.5 s mean; hybrid_rerank recall@5 1.0 / answer 0.9091 / refusal 0.9167 at 8.6 s. Baseline and
  re-measurement are both in `docs/engineering/EVALUATION.md`; sparse and plain hybrid were not re-run.

### Frontend (workspace screens)

- **Ask** now opens on the corpus it answers against: a masthead with supplier, contract and document-type counts,
  the question as the page's centrepiece with a focus-lit composer, example questions as a numbered grid, and an
  evidence column that explains what arrives with an answer instead of listing the same counts twice.
- **Ask no longer claims the workspace is synthetic.** The old banner said every document was generated; the
  corpus now holds imported notices, so the note states that labelled passages are demo data and unlabelled ones
  are the imported notices.
- **Search** draws a bounded semantic-match meter (only the cosine score is bounded; fusion and rerank scores keep
  their own scales and stay in the numeric detail), so a ranked row can be judged at a glance without a misleading bar.
- **Documents** gained a lifecycle strip counted from the same derivation as the table, and a sticky header on the
  registry table.
- The browser suite now also checks that all three screens render without a page error.

### Knowledge graph

- **The graph overview contradicted itself.** `edges_total` was populated while `edges_by_type` was empty, because
  `counts()` aggregated node labels only. Both providers now group edges by type, and a contract test asserts the
  shape the explorer reads.
- **The graph carried prose as entities.** Party patterns accepted "any other party" and "the rest of the country",
  so supplier nodes were created for them. Extraction now requires a capitalised, non-generic name, while corpus
  labels such as "Supplier A" remain valid; `scripts/audit_graph_entities.py` lists the rows already written so an
  operator can review them without anything being deleted.
- **A real supplier was being dropped.** `PARTIES_RE` ended a name at its first period, capturing
  "C. & P. ENGINEERING SERVICES LIMITED" as "C. & P"; the name groups now end on an alphanumeric character.
- **The graph layer had no tests.** `tests/unit/test_graph_store_contract.py` now covers per-type counts, tenant
  isolation, hop limits and edge provenance; `tests/ingestion/test_party_name_validation.py` covers name acceptance
  and rejection.
- `docs/architecture/KNOWLEDGE_GRAPH.md` documents the implemented graph and its confirmed gaps — MCP is not
  implemented, entity resolution is name-based, and no graph evaluation exists.

### MCP server

- **Implemented the MCP tool boundary** (`app/mcp_server/`) on the official SDK: seven read-only tools
  (`search_documents`, `get_document`, `search_contracts`, `get_supplier_profile`, `get_contract_amendments`,
  `get_ingestion_status`, `get_evaluation_metrics`).
- **Identity is deployment configuration, not tool input.** The process serves one tenant and one account from
  `MCP_TENANT_ID` / `MCP_USER_EMAIL` / `MCP_ROLE`; a missing value is a startup error rather than a default, and no
  tool schema accepts a tenant parameter.
- **Every call is guarded:** permission check before work, per-call timeout, per-tool rate limit, audited
  success/denial/timeout/error, and a JSON-only result so ORM objects cannot leak. Tests in
  `tests/unit/test_mcp_server.py` cover each guarantee plus the tool registry.
- **Verified through a real client session over stdio.** `scripts/verify_mcp_stdio.py` spawns the server, completes the
  handshake (7 tools advertised), runs `get_ingestion_status` and `search_documents`, and confirms a viewer is refused
  `get_supplier_profile`; the same check is `tests/integration/test_mcp_stdio.py` under `EPI_MCP_STDIO=1`.
- **Graph tools added:** `search_graph` (label-allowlisted entity search) and `get_entity_neighbours`
  (tenant-scoped traversal with an optional `as_of` date), both behind `graph:read`, verified over stdio.
- **Temporal traversal:** `providers/graph/temporal.py` drops edges outside their effective/expiry window;
  the local and Neo4j providers both honour it, and it is exposed on `GET /graph/paths?as_of=` and the MCP tool.
- `docs/architecture/MCP_ARCHITECTURE.md` records the design and its gaps: no external connectors, graph access
  read-only, stdio only, per-process limits, and an opt-in wire test.

### Knowledge graph

- **Clause and obligation nodes are now written.** Clause-tagged chunks are grouped by clause number into `Clause`
  nodes (`Document -CONTAINS-> Clause`); a clause whose text contains a duty verb (`shall`, `must`, `agrees to`, …)
  also gets an `Obligation` node with `Clause -IMPOSES-> Obligation` and an `EVIDENCED_BY` edge back to the document.
  Candidate re-index versions are excluded so the graph keeps serving the live version until activation.
  Covered by `tests/unit/test_graph_clauses.py` (grouping, provenance, duty detection, edge shape).
- **Clause detection now works on prose.** `layout.py` recognises `3.2 …` or `Clause 7.1 …` at the start of a long
  paragraph (a year or a bare list number is not a clause), and `chunking.py` splits a unit that spans several
  clauses so each chunk carries its own label. Covered by `tests/unit/test_clause_detection.py`.

### Frontend

- **Landing page simplified** from ten sections to six: hero, platform pillars, four capability cards, the evidence
  trace, the honesty section and the closing CTA. The pinned workflow, horizontal capability rail, architecture and
  security deep-dives and three duplicate capability cards were removed, along with the scroll-refresh effect they
  needed.
- **Corpus copy corrected.** The landing and privacy pages no longer describe the bundled corpus as synthetic; it is
  20 public OCDS notices from the UK Find a Tender Service under OGL-UK-3.0, and the interface explains the
  demo-corpus label only as something an uploader can apply.

### Known state at this revision

- Full backend suite passes: 634 passed, 8 skipped: seven environment-gated live-model tests and the opt-in MCP stdio handshake (EPI_MCP_STDIO=1).
- No LLM/VLM endpoint reachable, so answers are extractive; retrieval metrics are weak-to-moderate and the set is
  small (see `docs/engineering/EVALUATION.md`).
- Both images build (`epi-web:test` 96.9 MB, `epi-api:test` 5.16 GB) and the API image imports
  `app.main`; the composed stack has not been started against a live database and model endpoints.
- Frontend unit-test and Playwright configs are still absent from the working tree.

## Unreleased — 5 November 2026

### Fixed

- **Ingestion claims are atomic.** `claim_next_job` replaced `SELECT` + Python mutation with a conditional
  `UPDATE … WHERE id = ? AND status = 'queued'`, gated on `rowcount`. Two workers can no longer take the
  same job; `attempts` is incremented in the same statement so a crash cannot lose the count.
  (`backend/app/ingestion/jobs.py`)
- **One owner for the ingestion queue.** New `WORKER_MODE` setting (`embedded` | `external` | `disabled`).
  The API starts loops only when embedded; `docker-compose.yml` runs the API with `WORKER_MODE=external` and
  adds a dedicated `worker` service. (`backend/app/config/settings.py`, `backend/app/main.py`,
  `docker-compose.yml`, `.env.example`)
- **Uploads are bounded while streaming.** New `read_upload_bounded` reads 1 MB chunks and rejects the
  request as soon as `MAX_UPLOAD_MB` is exceeded, instead of buffering the entire body first.
  (`backend/app/ingestion/validation.py`, `backend/app/api/v1/documents.py`)

### Fixed (queue durability)

- **Worker leases replace the fixed requeue cutoff.** `IngestionJob` gained `lease_token` and
  `lease_expires_at` (migration `20261105120000`). A claim stamps a token and a lease; the worker renews it
  from a heartbeat task every third of `WORKER_LEASE_SECONDS`. `requeue_stuck_jobs` now requeues only jobs whose
  lease has expired (or legacy jobs with no lease and an old start time), so a healthy multi-hour ingestion is
  never stolen. A worker that loses its lease cancels the pipeline instead of writing results it no longer
  owns, and terminal statuses clear the lease.

### Fixed (data integrity)

- **Deleting a document left derived rows behind.** `delete_document` relied on `ON DELETE CASCADE`, which SQLite
  does not enforce unless foreign keys are enabled per connection. Confirmed in the live database: 0 documents but
  23 orphan chunks. The delete path now removes chunks, pages, tables, prices, certificates and ingestion jobs
  explicitly, tenant-scoped. `purge_orphaned_derived_rows` runs on worker recovery to clear rows already orphaned.

### Fixed (tenant boundary)

- **Self-registration joined the default tenant.** Confirmed over HTTP: a freshly registered account received
  `buyer` in the demo tenant and could read its documents (200). Registration without an explicit `tenant_slug`
  now creates a workspace the account owns (`admin`); joining a named workspace stays an explicit act. Login without
  a slug resolves a unique email to its workspace and rejects ambiguous emails.

### Added (startup safety)

- **Schema gate for non-development deployments.** With `AUTO_CREATE_SCHEMA=false` (the production setting),
  startup now verifies `alembic_version` exists and matches this build's head, raising a clear error instead of
  serving on a missing or stale schema. Development and test keep `create_all` behaviour.
  (`app/db/session.py`, `app/main.py`)

### Added (cancellation)

- **Ingestion jobs can be cancelled.** `POST /api/v1/documents/{id}/cancel` (permission `documents:write`, audited
  as `document.cancel`) marks the queued or running job cancelled, clears its lease so a running worker abandons
  at its next heartbeat, and releases the reserved candidate version. A document with no active job returns 404.

### Added (candidate cleanup)

- **Abandoned candidate versions are swept.** New `app/ingestion/cleanup.py` deletes chunks, prices,
  certificates and vector points for a stale candidate version and clears the reservation, so a crash or lost
  lease no longer blocks every future re-index of that document. It skips any document with a queued or running
  job, deletes only candidate-version rows (the active version is untouched), and tolerates vector-store failures
  because stale points carry a version no query selects. Wired into `IngestionWorker._recover`, running once per
  worker instance.

### Added

- `backend/tests/reliability/test_ingestion_job_claim.py` — claim ordering, single-claim guarantee, attempt
  counting, non-queued rows never claimed.
- `backend/tests/ingestion/test_bounded_upload.py` — over-limit refusal stops near the limit, at-limit
  acceptance, empty body.
- `backend/tests/reliability/test_job_leases.py` — lease creation, heartbeat renewal, superseded-token
  rejection, valid lease never requeued, expired lease requeued, attempt-limit failure, legacy fallback,
  terminal release.
- `docs/engineering/REPOSITORY_AUDIT.md` — Stage Zero inventory with findings classified by type.

### Known gaps at this revision

- Lease loss abandons the pipeline mid-run; the reserved candidate version is now cleaned up by the recovery
  sweep, but only after it goes stale (default 1 hour) — there is no immediate cancellation cleanup.
- No schema-existence gate in non-development environments.
- No real procurement corpus ingested; the nine synthetic documents are unchanged.
- Frontend workspace routes other than dashboard/search/login remain token-inherited, not art-directed.

## Temporal query understanding

### Added

- `backend/app/retrieval/temporal.py` — one derived as-of date per question, with the
  documented policy (UTC calendar dates, reference date from `today()`/`EVAL_AS_OF_DATE`,
  periods evaluated at their close, month precision to month end, ambiguity reported
  rather than guessed, originals treated as a version question).
- `QueryPlan.as_of`, `temporal_intent`, `temporal_notes`; derivation runs in the
  rule-based planner so SQL, vector and graph retrieval read the same interpretation.
- Graph traversal now receives the as-of date (previously only the API accepted one),
  and compliance certificate validity plus contract `is_expired` are judged at that date.
- `docs/architecture/TEMPORAL_SEMANTICS.md` — policy, dates that must not be confused,
  worked examples and limitations.
- Tests: `tests/unit/test_temporal_as_of.py` (16 cases),
  `tests/unit/test_temporal_plan_wiring.py` (7 cases).

### Fixed

- Compliance paths compared expiry dates against the `today` function object rather
  than a date, so every expiring certificate was reported not in force.

### Known limitations

- Vector retrieval reorders by date but does not hard-filter on as-of.
- Relative expressions outside the listed patterns ("since the framework was renewed")
  degrade to no filter with a note rather than being resolved.

## 120-question evaluation benchmark

### Added

- `data/evaluation/benchmark_v3/questions.json` — 120 questions across the twelve
  requested categories: 66 answerable (evidence verified), 39 unanswerable
  (corpus absence), 15 needing human review. Each carries its source document,
  page/section, verbatim evidence quote, verification method, answerability and
  review status. No question claims human review.
- `data/evaluation/benchmark_v3/ground_truth_manifest.json` — corpus counts,
  verification methods, per-question provenance.
- `backend/scripts/build_benchmark_v3.py` — reproducible builder that reads only
  stored page text, original HTML files, procurement records and graph rows.
- `backend/app/evaluation/benchmark.py`, `benchmark_runner.py` and
  `backend/scripts/run_benchmark_v3.py` — loader, runner and CLI measuring
  recall@5/10, MRR, nDCG@10, answer correctness, citation precision/recall,
  faithfulness, unsupported claim rate, refusal precision/recall/accuracy,
  temporal correctness, latency and tokens.
- `docs/evaluation/BENCHMARK_120.md` — composition, provenance policy, baseline
  results and failed-question analysis.
- `backend/tests/unit/test_benchmark_v3.py` — 8 tests over the dataset invariants
  and the scoring helpers.

### Fixed (after the baseline was recorded)

- Structured aggregation read `procurement_records.award_date` as a date, so the
  empty strings some award rows carry crashed the query with
  `Invalid isoformat string: ''`. It now reads the column as text and compares the
  year prefix; three baseline questions had errored on this.

### Baseline (12 November 2026)

Recall@10 0.8676 (n=70), MRR 0.8020, nDCG@10 0.8187, answer correctness 0.3974
(31/78), citation precision 0.7740 / recall 0.5588 (n=43), faithfulness 0.6938,
unsupported claim rate 0.3062, refusal precision 0.4286 / recall 0.7692, temporal
correctness 0.7000 (7/10), latency p50 9,151 ms / p95 16,279 ms, 195,964 prompt
and 7,094 completion tokens. No tuning was applied before this run.

## Backend hardening (TASK 5)

### Fixed

- DOCX/XLSX uploads are now validated as archives before extraction
  (`app/ingestion/archive.py`): entry-count, declared-expansion and
  compression-ratio limits, traversal and encrypted-entry rejection, and a
  required marker part. Previously only the four-byte ZIP signature was checked.
- `X-Forwarded-For` is no longer trusted for client identity or unauthenticated
  rate-limit scoping unless `TRUST_FORWARDED_FOR=true`, closing a header-rotation
  bypass of login and upload limits.
- Production startup refuses `ALLOW_PROVIDER_FALLBACK=true`,
  `AUTO_CREATE_SCHEMA=true`, `DEBUG=true`, wildcard CORS, and MCP enabled without
  a fixed tenant/account, in addition to the existing weak-JWT-secret guard.

### Tests

- `tests/security/test_archive_validation.py` (10 cases) and
  `tests/security/test_forwarded_for_trust.py` (3 cases); seven production
  configuration guards added to `tests/security/test_startup_security.py`.
- Full backend suite: 642 collected, 634 passed, 8 skipped, 0 failed.

See `docs/security/HARDENING.md` for the review, verified controls and remaining
risks.
