# Enterprise Procurement Intelligence
# Implementation Audit

Audit date: 2026-09-29
Auditor role: Senior Staff Engineer / CTO / QA / Product / UX / AI-RAG Architect
Method: static inspection of the actual repository + runtime execution of the actual system (CLI ingestion, agent pipeline, REST API, frontend dev server, browser session). No application code was modified for this audit. Temporary audit artifacts (throwaway PostgreSQL container, scratch JSON/log files in `/tmp`) were removed afterwards.

> Scope note: this document describes **what exists today**, verified against source, database contents and observed runtime behaviour. Anything not verified is labelled `UNVERIFIED`, not assumed.

---

## 1. Audit Summary

**Headline:** The backend is a genuinely working, non-mocked procurement RAG system that runs end-to-end on local adapters (SQLite + on-disk vector index + SQLite property graph + filesystem storage + in-memory cache). It is **not** a PDF chatbot and **not** a UI mockup. However, three of the most ambitious PRD pillars are **inactive because no model endpoint is configured** (LLM narrative generation, LLM grounding judge, VLM escalation), the **production Docker path cannot build**, and there are **zero automated tests**.

What genuinely works right now (verified by execution):

- Ingestion of a 12-document synthetic corpus (PDF incl. scanned/image-only pages, XLSX, CSV) → 9 documents / 15 pages / 34 chunks / 3 tables / 39 price rows / 3 suppliers in `backend/var/epi.db`.
- OCR that actually reads an image-only scanned contract page (PaddleOCR, oneDNN disabled).
- Hybrid retrieval (dense + BM25 + RRF) → cross-encoder rerank → context bundle with real citations.
- Structured/SQL retrieval with aggregations, conflict detection, temporal period scoping.
- Graph retrieval over a real property graph (supplier → contract → amendment → product → price).
- LangGraph agent with corrective rewrite loop and max-iteration termination.
- Grounding/verification pass, citation-to-DB validation, and a working refusal path (Query 6 refuses correctly).
- A 53-endpoint FastAPI surface, JWT auth with argon2, RBAC, tenant-scoped tables.
- A real evaluation framework (golden dataset, retrieval + answer + citation metrics, persisted runs).
- A React 18 + TypeScript + Vite + Tailwind + TanStack Query + Zustand + React Router + Lucide + Recharts frontend with 14 routes that builds (`npm run build` exits 0) and talks to the real API.

What does not work / is absent:

- No LLM endpoint → answers are honest **extractive** summaries, not generated prose. `generation_mode=extractive`, `degraded=True` on every query.
- No VLM endpoint → visual reasoning never runs (the escalation code path exists).
- `bge-m3` weights unavailable → embeddings silently use `BAAI/bge-small-en-v1.5` at **dim 384**, while the Qdrant path is configured for 1024.
- `docker compose --profile app up --build` **cannot build**: `dockerfile: backend/Dockerfile` does not exist anywhere in the repo.
- No tests of any kind (no `tests/`, no `pytest`, no Vitest, no Playwright).
- No `README.md`, no `docs/`; `data/README.md` exists only as `data/synthetic/corpus_card.json` + `manifest.json`.
- Q3 (compare A vs B) answer omits Supplier B; Q4 (lowest price in 2025) never names the supplier and leaks an irrelevant aggregation.

---

## 2. Repository Overview

Actual structure (verified, not aspirational):

```text
Sprint 2/
├── prd.md                      # 52 KB product spec (the only pre-existing file)
├── .env.example                # 6.3 KB, complete provider/config template
├── docker-compose.yml          # postgres, qdrant, neo4j, redis, minio, minio-init, api, web
├── audit.md                    # this document
├── backend/
│   ├── pyproject.toml          # epi-backend, deps + optional extras
│   ├── alembic.ini, alembic/    # env.py, script.py.mako, versions/0001_initial_schema.py
│   └── app/                    # 1 package, ~19 subpackages
│       ├── main.py, cli.py
│       ├── config/  core/  observability/  db/{base,session,models}
│       ├── providers/          # base, llm, embedding, reranking, vector, graph, cache, storage, sparse, vision, filters, router
│       ├── security/           # rbac, tokens, injection, scope, audit
│       ├── api/{deps,errors}, api/v1/{health,auth,documents,query,procurement,evaluation,admin,graph}
│       ├── schemas/  services/  ingestion/{parsers,ocr,layout,chunking,contextualizer,extractors,pipeline,jobs,connectors}
│       ├── graph/builder.py    # → providers/graph/*
│       ├── retrieval/{query_understanding,fusion,retriever,context,analysis,structured,graph_retrieval}
│       ├── agents/{state,nodes,graph,pipeline,generation,verification}
│       ├── evaluation/{dataset,metrics,runner}
│       ├── workers/ingestion_worker.py
│       └── var/                # runtime: epi.db, graph.db, vector_index/, storage/
├── frontend/
│   ├── package.json, vite.config.ts, tsconfig.json, tailwind.config.js, postcss.config.js
│   ├── index.html, Dockerfile, nginx.conf
│   └── src/{main.tsx,App.tsx,index.css,lib/,store/,components/{ui,common,layout},pages/}
├── data/
│   ├── synthetic/              # 12 generated documents + manifest.json + corpus_card.json
│   └── evaluation/golden_questions.json
└── scripts/{make_synthetic_corpus.py,acceptance_check.py,api_smoke.py}
```

Present but worth flagging: the repo is **not a git repository** (`git status` → `fatal: not a git repository`). There is no CI config, no `.gitignore` in effect, and scratch state (`backend/var/`, `.freebuff/`) sits directly in the tree.

---

## 3. Current Architecture

```text
                 React 18 + TS + Vite (5173)  ──┐
                                               │  REST + SSE, Bearer JWT
                                               ▼
                                     FastAPI /api/v1  (53 endpoints)
                                               │
   ┌───────────────┬───────────────────┬───────┴────────┬──────────────────┐
   ▼               ▼                   ▼                ▼                  ▼
 security       ingestion           retrieval        agents             evaluation
 rbac/tokens    pipeline/jobs       understand       LangGraph          golden/runner
 injection      parsers/ocr         hybrid+RRF       corrective loop    metrics
 scope/audit    chunk/context       rerank           verify/refuse      persisted runs
                   │                   │                │
                   ▼                   ▼                ▼
        ┌───────────────── Provider abstraction (two real implementations each) ─────────────────┐
        │  PRODUCTION                              │  LOCAL (active here)                        │
        │  Postgres (asyncpg)                      │  SQLite via aiosqlite                       │
        │  Qdrant                                  │  on-disk numpy vector index + BM25          │
        │  Neo4j (Cypher subset translator)        │  SQLite property graph                      │
        │  Redis                                   │  in-process memory cache                    │
        │  S3 / MinIO                              │  filesystem under var/storage               │
        │  OpenAI-compatible LLM (Qwen3-30B)       │  ✗ not configured → extractive generation   │
        │  Qwen3-VL (vision)                       │  ✗ not configured → no escalation           │
        │  BAAI/bge-m3 (1024d)                     │  bge-small-en-v1.5 (384d) fallback          │
        │  BAAI/bge-reranker-v2-m3                 │  ✔ same model, loads on CUDA                │
        └─────────────────────────────────────────────────────────────────────────────────────────┘
```

Active provider set is reported honestly at runtime by `GET /api/v1/health` and in logs:
`cache=memory graph=local llm_configured=False storage=local vector=local fallbacks=[]`.

**Architectural honesty is a real strength here:** every datastore and model sits behind a provider interface, degradation is surfaced (`degraded=True`, `generation_mode=extractive`, "Not configured" banners), and nothing pretends a model answered when it did not.

---

## 4. Technology Stack Audit

| Technology | Expected | Present | Version | Used? | Where | Working? |
|---|---|---|---|---|---|---|
| React | Yes | Yes | 18.3.1 | Yes | `frontend/src` | ✔ builds, renders |
| TypeScript | Yes | Yes | 5.7.2 | Yes | all frontend | ✔ `tsc --noEmit` clean |
| Vite | Yes | Yes | 6.0.7 | Yes | `vite.config.ts` (proxy → :8000) | ✔ dev + build |
| Tailwind CSS | Yes | Yes | 3.4.17 | Yes | `tailwind.config.js`, `index.css` | ✔ |
| shadcn/ui | Yes | Yes | Radix + CVA + tailwind-merge | Yes | 8 primitives in `components/ui` | ✔ (hand-written, Radix-backed) |
| TanStack Query | Yes | Yes | 5.62.11 | Yes | `main.tsx`, all pages | ✔ |
| Zustand | Yes | Yes | 5.0.2 | Yes | `store/auth.ts`, `store/ui.ts` | ✔ |
| React Router | Yes | Yes | 6.28.1 | Yes | `App.tsx` | ✔ 14 routes |
| Lucide React | Yes | Yes | 0.469.0 | Yes | shell, states, dialogs | ✔ |
| Recharts | Yes | Yes | 2.15.0 | Yes | `DashboardPage`, `EvaluationPage` | ✔ |
| Python | 3.11+ | 3.13.7 | — | Yes | backend | ✔ |
| FastAPI | Yes | Yes | ≥0.115 | Yes | `main.py`, 8 routers | ✔ 53 endpoints |
| Pydantic | Yes | Yes | v2 | Yes | `schemas/`, settings | ✔ |
| SQLAlchemy | Yes | Yes | 2.0 async | Yes | `db/` | ✔ (async sessions) |
| Alembic | Yes | Yes | ≥1.13 | Partially | `alembic/versions/0001_initial_schema.py` | ⚠ only a bootstrap revision; local runs use `auto_create_schema=True` |
| asyncpg | Yes | Yes | ✔ | Config-only | Postgres adapter | ⚠ never exercised to a live server in this environment |
| psycopg (v3) | (needed by compose URL) | **NO** | — | — | `docker-compose.yml` DATABASE_URL | ✘ **missing dependency** |
| LangChain | Yes | Yes (`langchain-core`) | ≥0.3 | Minimally | message types only | ⚠ nominal |
| LangGraph | Yes | Yes | ≥0.2 | Yes | `agents/graph.py` | ✔ real stateful graph |
| PostgreSQL | Yes | client only | — | Adapter exists | `providers` | ⚠ UNVERIFIED live |
| Qdrant | Yes | client only | qdrant-client ≥1.10 | Adapter exists | `providers/vector/qdrant.py` | ⚠ UNVERIFIED live |
| Neo4j | Yes | client only | ≥5.24 | Adapter + Cypher subset | `providers/graph/neo4j.py` | ⚠ UNVERIFIED live |
| Redis | Yes | client only | ≥5.0 | Cache adapter | `providers/cache` | ⚠ UNVERIFIED live |
| MinIO / S3 | Yes | boto3 ✔ | ≥1.34 | Storage adapter | `providers/storage` | ⚠ UNVERIFIED live |
| BGE-M3 | Yes (default) | Weights **not** cached | — | No | — | ✘ falls back to bge-small 384d |
| BGE reranker v2-m3 | Yes | ✔ cached | — | Yes | `providers/reranking.py` | ✔ on CUDA |
| Qwen3-30B-A3B | Yes | No endpoint | — | No | `providers/llm/openai_compatible.py` | ✘ extractive mode |
| Qwen3-VL | Yes | No endpoint | — | No | `providers/vision.py` | ✘ no escalation |
| PaddleOCR | Yes | ✔ | ≥2.7 | Yes | `ingestion/ocr.py` | ✔ (requires oneDNN disabled) |
| Docker / Compose | Yes | Compose file ✔ | — | Partially | `docker-compose.yml` | ✘ app profile cannot build |
| Testing | Yes | **None** | — | No | — | ✘ |
| Observability | Yes | structlog + DB traces | ≥24.1 | Yes | `observability/`, `agent_traces` | ✔ (no exporter) |

---

## 5. Frontend Page Inventory

| Page | Route | Status | APIs used | Purpose |
|---|---|---|---|---|
| Login | `/login` | COMPLETE | `POST /auth/login`, `POST /auth/register` | Authenticate, obtain bearer token |
| Dashboard | `/dashboard` (guard `admin:read`) | COMPLETE | `/admin/stats`, `/admin/indexing`, `/health` | Corpus counters + charts |
| Ask | `/ask` | COMPLETE | `POST /query/stream` (SSE), `/filters` | Grounded Q&A with citations |
| Search | `/search` | COMPLETE | `POST /search`, `/filters` | Retrieval-level exploration |
| Documents | `/documents` | COMPLETE | `GET /documents`, `POST /documents/upload`, `POST /documents/{id}/index` | Upload, list, reindex |
| Document detail | `/documents/:documentId` | COMPLETE | `GET /documents/{id}`, `/chunks`, `/pages/{n}/image` | Chunks, page image, tables |
| Contracts | `/contracts` | COMPLETE | `GET /contracts` | Contract list |
| Contract detail | `/contracts/:contractId` | COMPLETE | `GET /contracts/{id}` | Terms, amendments, prices |
| Suppliers | `/suppliers` | COMPLETE | `GET /suppliers` | Supplier list |
| Supplier detail | `/suppliers/:supplierId` | COMPLETE | `GET /suppliers/{id}` | Profile, contracts, certs |
| Compare | `/compare` | COMPLETE | `POST /compare`, `/filters` | Structured A-vs-B comparison |
| Graph | `/graph` (guard `graph:read`) | COMPLETE | `/graph/overview`, `/graph/nodes`, `/graph/paths` | GraphRAG exploration |
| Evaluation | `/evaluation` (guard `evaluation:read`) | COMPLETE | `/evaluation/experiments`, `/dataset`, `/runs` (GET/POST/DELETE) | Metrics runs + charts |
| Admin | `/admin` (guard `admin:read`) | COMPLETE | `/admin/stats`, `/config`, `/routing`, `/indexing`, `/audit`, `/traces` | Config, routing table, traces |
| `*` fallback | `*` | COMPLETE | — | Redirect to `/ask` |

`RequireAuth` wraps `AppShell`; four routes additionally enforce a permission via `RequirePermission`.

---

## 6. Page-by-Page Audit

### 6.1 Ask page — `/ask`

- Sections: question input, scope filters (`/filters`), streaming answer pane, structured-findings block, evidence block with numbered citations, verification footer.
- Flow: submit → `streamQuery()` → `POST /api/v1/query/stream` → SSE → progressive render.
- Status: **COMPLETE**. Error/empty/loading states come from shared `components/common/States.tsx`.
- Missing: no conversation list/history UI even though `GET/POST /conversations` and `/conversations/{id}/messages` exist (0 rows in DB). Citation rows show `page N` badges and source name but there is no "open document at page" deep link from the citation itself (the document detail page has the image viewer).

### 6.2 Documents page — `/documents`

- Sections: upload control (file + `document_type` + `is_synthetic`), document table with status/type/synthetic badge, reindex action.
- Flow: `uploadDocument()` → `POST /documents/upload` (multipart) → backend stores bytes → ingestion → row appears; `reindexDocument()` → `POST /documents/{id}/index`.
- Status: **COMPLETE** (upload path verified through the API smoke script; reindex endpoint verified to exist and run).

### 6.3 Document detail — `/documents/:documentId`

- Sections: metadata, chunk table with page/section/clause, extracted tables, page image viewer using `api.pageImageUrl(documentId, page)` → `GET /documents/{id}/pages/{n}/image`.
- Status: **COMPLETE**. Note it correctly labels the page image as "what the vision model would receive when a page is escalated" — i.e. it does not fake a VLM analysis.

### 6.4 Compare page — `/compare`

- Sections: entity selectors, price table, delta highlighting, chart.
- Flow: `POST /compare` → `structured.comparison`.
- Status: **COMPLETE** for the structured/API path. Note the *agent* comparison answer (Q3) is the weak one — see §19 and §46.

### 6.5 Graph page — `/graph`

- Sections: overview counts, node browser, neighbour expansion, path view (`/graph/paths`).
- Status: **COMPLETE** against the local property graph. It has never been run against Neo4j.

### 6.6 Evaluation page — `/evaluation`

- Sections: dataset card (question count, categories, unanswerable count), run trigger, run history, per-metric tables, Recharts visualisation, delete run.
- Status: **COMPLETE**; 2 runs and 6 result rows exist in the DB.

### 6.7 Admin page — `/admin`

- Sections: stats, provider/model config with explicit "not configured" states, model routing table, indexing counters, audit log, query traces.
- Status: **COMPLETE**. Uses `/admin/queries/{id}`? No — the frontend never calls `queryDetail`; the endpoint is backend-only.

### 6.8 Login / Dashboard / Search / Contracts / Suppliers

- Login: **COMPLETE** (registration + login verified live; email validation had to be relaxed to a plain-string schema during build, see §42).
- Dashboard: **COMPLETE**, real counters from `/admin/stats` + `/admin/indexing`.
- Search: **COMPLETE**, `POST /search` returns retrieval results with scores.
- Contracts / Suppliers lists + details: **COMPLETE** against real DB rows (3 contracts, 3 suppliers).

---

## 7. Current User Flow (actual, verified)

```text
LOGIN (email+password → JWT)
  ↓
ASK  ──► POST /api/v1/query/stream (SSE)
            ↓
        LangGraph: understand → plan → structured → graph → retrieve → vision(off)
            → evaluate_evidence → (rewrite → retrieve)* → generate → verify → finalize
            ↓
        answer + structured findings + document evidence + numbered citations + verification
  ↓
CITATION  ──► document name + page + section (rendered in AnswerView)
  ↓
DOCUMENTS ──► upload ──► POST /documents/upload ──► parse → OCR → layout → tables
            → chunk → context → embed → vector index → BM25 → SQLite → graph
  ↓
DOCUMENT DETAIL ──► chunks, tables, page image (GET /documents/{id}/pages/{n}/image)
  ↓
[DOCUMENT VIEWER DEEP-LINK FROM CITATION]   ← NOT IMPLEMENTED
CONVERSATIONS / HISTORY                      ← NOT IMPLEMENTED IN UI (API exists)
CHAT WITH FOLLOW-UPS (conversation rewrite)  ← NOT IMPLEMENTED
EVALUATION ──► run golden set ──► metrics persisted ──► charts
ADMIN     ──► providers, routing, traces, audit, indexing
```

---

## 8. Detailed User Flows

### Ask (primary flow)
`Question typed` → `AskPage` → `streamQuery()` → `POST /api/v1/query/stream` → `api/v1/query.py` → `agents/pipeline.py` → `agents/graph.py` → nodes → `RetrievalResult` + `StructuredResult` + graph paths → `retrieval/context.py` `ContextBundle` → `agents/nodes.py::generate` (extractive composer) → `agents/verification.py` (grounding, citation validation, `decide_status`) → persisted to `queries`/`answers`/`citations`/`agent_traces` → SSE frames → UI render.

### Ingestion flow
`File picked` → `DocumentsPage` → `POST /api/v1/documents/upload` → `services/documents.py` → bytes → `ingestion/pipeline.py` → `parsers/*` (pdf/office/image) → `ocr.py` (if no text layer) → `layout.py` → `extractors` (prices, compliance, suppliers) → `chunking.py` → `contextualizer.py` → `providers/embedding` → vector store → BM25 (`providers/sparse`) → DB rows (`documents/pages/chunks/tables/prices`) → `graph/builder.py` → property graph → `services/reconciliation.py` (amendment attribution) → job status.

### Reindex flow
`Reindex button` → `POST /documents/{id}/index` → delete existing artifacts → re-run ingestion pipeline for the stored original → UI refresh.

### Evaluation flow
`Run evaluation` → `POST /evaluation/runs` → `evaluation/runner.py` → `evaluation/dataset.py` (golden set) → agent pipeline per question → `evaluation/metrics.py` → persisted `evaluation_runs` + `evaluation_results` → charts.

### Compare flow
`Select A and B` → `POST /compare` → `retrieval/structured.py::comparison` → table + deltas + evidence → UI.

---

## 9. Button → API → Backend → DB Mapping

| UI action | Component | API | Method | Backend | DB/service | Status |
|---|---|---|---|---|---|---|
| Log in | `LoginPage` | `/api/v1/auth/login` | POST | `api/v1/auth.py` → `services/auth.py` | `users`, `tenants` | COMPLETE |
| Register | `LoginPage` | `/api/v1/auth/register` | POST | `services/auth.py` | `users` | COMPLETE |
| Log out | `AppShell` | `/api/v1/auth/logout` | POST | `api/v1/auth.py` | `audit_logs` | COMPLETE |
| Ask question | `AskPage` | `/api/v1/query/stream` | POST (SSE) | `agents/pipeline.py` | all stores | COMPLETE |
| Scope filters | `AskPage`/`SearchPage`/`ComparePage` | `/api/v1/filters` | GET | `api/v1/procurement.py` | `suppliers`, `contracts`, `products` | COMPLETE |
| Keyword/semantic search | `SearchPage` | `/api/v1/search` | POST | `retrieval/retriever.py` | vector + BM25 | COMPLETE |
| Upload document | `DocumentsPage` | `/api/v1/documents/upload` | POST | `ingestion/pipeline.py` | storage + all stores | COMPLETE |
| Reindex document | `DocumentsPage` | `/api/v1/documents/{id}/index` | POST | `ingestion/pipeline.py` | all stores | COMPLETE |
| List documents | `DocumentsPage` | `/api/v1/documents` | GET | `services/documents.py` | `documents` | COMPLETE |
| Open document | `DocumentsPage` → detail | `/api/v1/documents/{id}` | GET | `services/documents.py` | `documents`, `document_pages` | COMPLETE |
| View chunk list | `DocumentDetailPage` | `/api/v1/documents/{id}/chunks` | GET | `services/documents.py` | `chunks` | COMPLETE |
| View page image | `DocumentDetailPage` | `/api/v1/documents/{id}/pages/{n}/image` | GET | `services/documents.py` | storage | COMPLETE |
| List suppliers | `SuppliersPage` | `/api/v1/suppliers` | GET | `services/procurement.py` | `suppliers` | COMPLETE |
| Open supplier | `SuppliersPage` → detail | `/api/v1/suppliers/{id}` | GET | `services/procurement.py` | suppliers/contracts/compliance | COMPLETE |
| List contracts | `ContractsPage` | `/api/v1/contracts` | GET | `services/procurement.py` | `contracts` | COMPLETE |
| Open contract | `ContractsPage` → detail | `/api/v1/contracts/{id}` | GET | `services/procurement.py` | contracts/prices/amendments | COMPLETE |
| Compare suppliers | `ComparePage` | `/api/v1/compare` | POST | `retrieval/structured.py` | `prices`, `products` | COMPLETE |
| Graph overview | `GraphPage` | `/api/v1/graph/overview` | GET | `providers/graph/local.py` | `graph.db` | COMPLETE |
| Browse graph nodes | `GraphPage` | `/api/v1/graph/nodes` | GET | graph provider | `graph.db` | COMPLETE |
| Graph paths | `GraphPage` | `/api/v1/graph/paths` | GET | `retrieval/graph_retrieval.py` | `graph.db` | COMPLETE |
| Run evaluation | `EvaluationPage` | `/api/v1/evaluation/runs` | POST | `evaluation/runner.py` | eval tables + all stores | COMPLETE |
| Delete run | `EvaluationPage` | `/api/v1/evaluation/runs/{id}` | DELETE | `services/evaluation.py` | eval tables | COMPLETE |
| View audit log | `AdminPage` | `/api/v1/admin/audit` | GET | `api/v1/admin.py` | `audit_logs` | COMPLETE |
| View traces | `AdminPage` | `/api/v1/admin/traces` | GET | `api/v1/admin.py` | `agent_traces` | COMPLETE |
| Create conversation | (no UI) | `/api/v1/conversations` | POST | `api/v1/query.py` | `conversations` | ORPHAN (backend only) |
| Product browser | (no UI) | `/api/v1/products` | GET | `services/procurement.py` | `products` | ORPHAN (backend only) |
| Price browser | (no UI) | `/api/v1/prices` | GET | `services/procurement.py` | `prices` | ORPHAN (backend only) |
| Compliance browser | (no UI) | `/api/v1/compliance` | GET | `services/procurement.py` | `compliance_certificates` | ORPHAN (backend only) |
| Eval run comparison | (no UI) | `/api/v1/evaluation/compare` | GET | `services/evaluation.py` | eval tables | ORPHAN (backend only) |
| Query trace detail | (no UI) | `/api/v1/admin/queries/{id}` | GET | `api/v1/admin.py` | `queries`, `answers`, `citations` | ORPHAN (backend only) |

---

## 10. API Inventory

58 route objects total; **53 are application endpoints** (the other 5 are `/`, `/docs`, `/redoc`, `/openapi.json`, `/docs/oauth2-redirect`). All application endpoints are under `/api/v1` and require a bearer token except health/ready/login/register.

| # | Method | Path | Auth | Service | Frontend consumer |
|---|---|---|---|---|---|
| 1 | GET | `/health` | none | provider health | LoginPage, AppShell |
| 2 | GET | `/ready` | none | readiness | — (orphan) |
| 3 | POST | `/auth/login` | none | `services/auth` | LoginPage |
| 4 | POST | `/auth/register` | none | `services/auth` | LoginPage |
| 5 | POST | `/auth/refresh` | refresh token | `services/auth` | — (orphan) |
| 6 | POST | `/auth/logout` | bearer | `services/auth` | AppShell |
| 7 | GET | `/auth/me` | bearer | `services/auth` | auth store bootstrap |
| 8 | GET | `/auth/roles` | admin | RBAC table | — (orphan) |
| 9 | POST | `/query` | bearer | `agents/pipeline` | — (Ask uses `/query/stream`) |
| 10 | POST | `/query/stream` | bearer | `agents/pipeline` | AskPage |
| 11 | POST | `/search` | bearer | `retrieval/retriever` | SearchPage |
| 12 | GET | `/filters` | bearer | procurement | Ask/Search/Compare |
| 13 | GET | `/conversations` | bearer | `api/v1/query` | — (orphan) |
| 14 | POST | `/conversations` | bearer | `api/v1/query` | — (orphan) |
| 15 | GET | `/conversations/{id}/messages` | bearer | `api/v1/query` | — (orphan) |
| 16 | GET | `/documents` | bearer | `services/documents` | DocumentsPage |
| 17 | POST | `/documents/upload` | bearer | ingestion | DocumentsPage |
| 18 | GET | `/documents/limits` | bearer | config | — (orphan) |
| 19 | GET | `/documents/{id}` | bearer | `services/documents` | DocumentDetailPage |
| 20 | DELETE | `/documents/{id}` | bearer | `services/documents` | — (orphan) |
| 21 | GET | `/documents/{id}/chunks` | bearer | `services/documents` | DocumentDetailPage |
| 22 | POST | `/documents/{id}/index` | bearer | ingestion | DocumentsPage |
| 23 | GET | `/documents/{id}/pages/{n}` | bearer | `services/documents` | — (orphan) |
| 24 | GET | `/documents/{id}/pages/{n}/image` | bearer | storage | DocumentDetailPage |
| 25 | GET | `/suppliers` | bearer | procurement | SuppliersPage |
| 26 | GET | `/suppliers/{id}` | bearer | procurement | SupplierDetailPage |
| 27 | GET | `/contracts` | bearer | procurement | ContractsPage |
| 28 | GET | `/contracts/{id}` | bearer | procurement | ContractDetailPage |
| 29 | GET | `/products` | bearer | procurement | — (orphan) |
| 30 | GET | `/prices` | bearer | procurement | — (orphan) |
| 31 | GET | `/compliance` | bearer | procurement | — (orphan) |
| 32 | POST | `/compare` | bearer | `retrieval/structured` | ComparePage |
| 33 | GET | `/graph/overview` | bearer | graph provider | GraphPage |
| 34 | GET | `/graph/nodes` | bearer | graph provider | GraphPage |
| 35 | GET | `/graph/nodes/{label}/{key}/neighbors` | bearer | graph provider | — (orphan) |
| 36 | GET | `/graph/paths` | bearer | `retrieval/graph_retrieval` | GraphPage |
| 37 | GET | `/evaluation/dataset` | bearer | `evaluation/dataset` | EvaluationPage |
| 38 | GET | `/evaluation/experiments` | bearer | `evaluation/dataset` | EvaluationPage |
| 39 | POST | `/evaluation/runs` | bearer | `evaluation/runner` | EvaluationPage |
| 40 | GET | `/evaluation/runs` | bearer | `services/evaluation` | EvaluationPage |
| 41 | GET | `/evaluation/runs/{id}` | bearer | `services/evaluation` | EvaluationPage |
| 42 | DELETE | `/evaluation/runs/{id}` | bearer | `services/evaluation` | EvaluationPage |
| 43 | GET | `/evaluation/compare` | bearer | `services/evaluation` | — (orphan) |
| 44 | GET | `/admin/stats` | `admin:read` | `api/v1/admin` | Dashboard, Admin |
| 45 | GET | `/admin/health` | `admin:read` | providers | — (orphan) |
| 46 | GET | `/admin/config` | `admin:read` | settings | AdminPage |
| 47 | GET | `/admin/routing` | `admin:read` | `providers/router` | AdminPage |
| 48 | GET | `/admin/indexing` | `admin:read` | stores | Dashboard, Admin |
| 49 | GET | `/admin/audit` | `admin:read` | `security/audit` | AdminPage |
| 50 | GET | `/admin/traces` | `admin:read` | `observability` | AdminPage |
| 51 | GET | `/admin/queries/{id}` | `admin:read` | `api/v1/admin` | — (orphan) |
| 52 | GET | `/admin/datasources` + POST `/admin/datasources` | `admin:read` | `data_sources` | — (orphan) |

Verified route dump: 58 route objects, 53 application endpoints.

Row 52 covers two methods (`GET` and `POST` on `/admin/datasources`), which is why the table has 52 rows for 53 endpoints.

**Orphan endpoints (backend implemented, no frontend consumer): 19** — `/ready`, `/auth/refresh`, `/auth/roles`, `POST /query` (superseded by the streaming variant), `/conversations` ×3, `/documents/limits`, `DELETE /documents/{id}`, `/documents/{id}/pages/{n}`, `/products`, `/prices`, `/compliance`, `/graph/nodes/{label}/{key}/neighbors`, `/evaluation/compare`, `/admin/health`, `/admin/queries/{id}`, `/admin/datasources` ×2.

---

## 11. Database Audit

Local runtime DB: `backend/var/epi.db` (SQLite via `aiosqlite`), 23 tables, row counts observed:

```text
tenants 1            users 1              documents 9          document_pages 15
chunks 34            document_tables 3    suppliers 3          products 5
contracts 3          prices 39            compliance_certificates 18
procurement_records 48   ingestion_jobs 9
conversations 0      conversation_messages 0
queries 50           answers 50           citations 593        agent_traces 50
evaluation_runs 2    evaluation_results 6  audit_logs 8        data_sources 0
```

- **Models:** `db/models/{tenancy,procurement,documents,conversations,operations}.py`.
- **Tenancy:** every domain table carries `tenant_id`; queries are scoped through `security/scope.py`. Verified on the read paths used during this audit; not exhaustively audited for all 53 routes.
- **Relationships:** documents → pages → chunks; contracts → amendments → prices → products; suppliers → contracts/certificates; queries → answers → citations.
- **Migrations:** exactly one revision, `backend/alembic/versions/0001_initial_schema.py`, autogenerated against Postgres at bootstrap time. The local flow never uses it (`auto_create_schema=True` → `create_all`). So migrations exist but are **unverified against a live Postgres** in this environment.
- **Feature → table mapping:** ingestion (`documents`, `document_pages`, `chunks`, `document_tables`, `ingestion_jobs`); procurement (`suppliers`, `products`, `contracts`, `prices`, `compliance_certificates`, `procurement_records`); agent (`queries`, `answers`, `citations`, `agent_traces`); evaluation (`evaluation_runs`, `evaluation_results`); security (`users`, `tenants`, `audit_logs`).
- **Gap:** with `conversations = 0`, the chat-history feature is schema-only in practice.

---

## 12. Vector Database Audit

- **Production:** `providers/vector/qdrant.py` — real client, collection management, payload filters, upsert, search. Configured default is `bge-m3` / **1024 dims**.
- **Active here:** `providers/vector/local.py` — numpy on-disk index at `backend/var/vector_index/procurement_chunks`, dimensions **384**, model `BAAI/bge-small-en-v1.5`.
- **Indexed:** 34 chunks with full payload (document_id, page_number, section, clause, content_type, supplier_id, contract_id, effective_date, is_synthetic, source_uri).
- **Hybrid:** BM25 (`providers/sparse.py`, `rank_bm25`) fused with dense via RRF in `retrieval/fusion.py`. Observed vectors: best vector score 0.8093 vs best rerank score 0.0049 on Q6 — i.e. reranking is genuinely discriminating, not a passthrough.
- **Status: PARTIAL.** Local path COMPLETE and verified; Qdrant path UNVERIFIED (no daemon). **Dimension mismatch risk is real**: a Qdrant collection created from the 384-d local embeddings will not accept 1024-d `bge-m3` vectors and vice versa.

## 13. Graph Database Audit

- **Production:** `providers/graph/neo4j.py` with a Cypher-subset translator (`cypher_subset.py`).
- **Active here:** `providers/graph/local.py` on `backend/var/graph.db` (SQLite property graph).
- **Nodes/edges observed:** suppliers, contracts, documents, products, prices, compliance certificates; relationships supplier→contract, contract→amendment, contract→document, product→price.
- **Wired into the agent?** Yes — `retrieval/graph_retrieval.py` is a LangGraph node, and Q7's answer drew on the parties/compliance relationships.
- **Status: PARTIAL.** GraphRAG works on the local adapter and is agent-integrated; the **Neo4j deployment path is UNVERIFIED** (no live server, and Q7/Q5 answers relied on document passages rather than graph paths — `graph_paths: 0` on several queries).

## 14. Document Ingestion Audit

| Stage | Status | Implementation | Notes |
|---|---|---|---|
| Upload / validation | COMPLETE | `api/v1/documents.py`, `ingestion/validation.py` | Size/type/dup checks |
| Type detection | COMPLETE | `ingestion/parsers/` | PDF, DOCX, XLSX, CSV, TXT, PNG/JPG |
| Text extraction | COMPLETE | `parsers/pdf.py` (PyMuPDF), `parsers/office.py` | Verified on the corpus |
| OCR | COMPLETE | `ingestion/ocr.py` PaddleOCR | Fires only when no text layer; oneDNN disabled |
| Layout / headings / clauses | COMPLETE | `ingestion/layout.py` | Produced real section/clause labels used in citations |
| Table extraction | COMPLETE | `ingestion/extractors`, `document_tables` | PDF tables + XLSX sheets landed as real rows |
| VLM escalation | NOT IMPLEMENTED (runtime) | `providers/vision.py` | Code path exists; no endpoint configured |
| Page reconstruction | COMPLETE | `document_pages` (15 rows) | Page-level indexing as PRD requires |
| Metadata extraction | COMPLETE | `ingestion/metadata.py` | Supplier/contract/date/number/amount extraction |
| Chunking | COMPLETE (structural) | `ingestion/chunking.py` | See §17 |
| Contextual enrichment | COMPLETE | `ingestion/contextualizer.py` | Adds doc/section context to each chunk |
| Embedding | COMPLETE (fallback model) | `providers/embedding.py` | 384-d |
| Vector index | COMPLETE (local) | `providers/vector/local.py` | — |
| BM25 | COMPLETE | `providers/sparse.py` | rank_bm25 |
| Relational persistence | COMPLETE | all models | 9 docs / 34 chunks / 39 prices |
| Graph persistence | COMPLETE (local) | `graph/builder.py` | — |
| Background queue | PARTIAL | `workers/ingestion_worker.py`, `ingestion_jobs` | Worker loop + `epi worker` CLI exist; uploads process in-process; **no worker service in compose** |
| Amendment reconciliation | COMPLETE | `services/reconciliation.py` | Fixed order-dependent attribution |

## 15. OCR Audit

- Library: PaddleOCR (extra: `paddleocr`, `opencv-python-headless`, `pillow`).
- Trigger: page yields no usable text layer (text-length threshold), so the image-only `supplier_a_scanned_signature_page.pdf` is OCR'd while normal PDFs are not.
- Output: page text persisted to `document_pages` and chunked/indexed; OCR status recorded per page.
- Verified: yes — the scanned execution copy ("Signed for Northwind… by J. Alvarez… Execution date: 2024-01-08") appears in Q7's evidence list.
- Real bug fixed during build: PaddleOCR only initialises with oneDNN disabled (`settings` flag + `ocr.py`), otherwise it crashes on this CPU build.
- Confidence handling: **PARTIAL** — per-line OCR confidence is not surfaced in the API/UI.

## 16. Multimodal RAG Audit

| Capability | Status | Evidence |
|---|---|---|
| Image-only / scanned page handling | COMPLETE | OCR path + page images stored per page |
| Page image rendering in UI | COMPLETE | `GET /documents/{id}/pages/{n}/image` + `DocumentDetailPage` |
| Table understanding | COMPLETE | `document_tables`, structured table text in citations |
| Layout understanding | COMPLETE | `layout.py` headings/sections |
| VLM provider abstraction | COMPLETE | `providers/vision.py` |
| Selective VLM escalation | NOT IMPLEMENTED (runtime) | no vision endpoint configured; `vision_status` reports not configured |
| Chart/diagram understanding | NOT IMPLEMENTED | no chart extractor |

Multimodal is therefore **PARTIAL overall**: the plumbing and OCR half are real; the VLM half is dormant and honestly reported as such.

## 17. Chunking Audit

Implemented in `ingestion/chunking.py`:

- ✔ structural / contract-aware chunking (split by heading→section→clause, keeping clause text intact),
- ✔ token-aware sizing with token accounting (`ingestion/tokens.py`),
- ✔ table chunks emitted separately with their own `content_type`,
- ✘ **semantic chunking** (no embedding-similarity boundary detection) — the name exists in the PRD path but there is no implementation,
- ✘ parent-child / small-to-big retrieval,
- ✘ sentence-window retrieval.

Evidence: 34 chunks over 9 documents / 15 pages, with section+clause metadata attached and used in citations (`supplier_a_amendment_2_NS-2024-001.pdf — p.1 — 1. Price Revision`).

## 18. Embedding Audit

- Default configured: `BAAI/bge-m3`, 1024-d — **weights not present** on this machine.
- Active: `BAAI/bge-small-en-v1.5`, **384-d** (logged explicitly: `dim=384 model=BAAI/bge-small-en-v1.5`).
- Batching, caching and provider indirection: implemented. GPU: available (the reranker loads on CUDA); the small embedding model runs fine either way.
- Fallback transparency: the substitution is reported, not hidden.
- Risk: **HIGH** — the fallback silently changes dimensions and quality; a Qdrant collection built for one model cannot accept the other.

## 19. Retrieval Audit

Pipeline verified in `retrieval/`:

```text
query → query_understanding (intent/entities/period/requirements)
      → dense search (vector store)         [verified]
      → BM25 lexical search                 [verified]
      → RRF fusion                          [verified]
      → metadata/plan filters               [verified locally, PARTIAL for Qdrant]
      → cross-encoder rerank (bge-reranker-v2-m3)  [verified, ~1.2 s]
      → context bundle assembly + citation drafts  [verified]
```

Observed per-query timings in the acceptance run: warm retrieval ≈1.3 s, rerank ≈1.2–1.3 s, cold dense call up to ~19 s. Verified `best_vector_score=0.8093` vs `best_rerank_score=0.0049`, i.e. reranking reorders materially.

**Status: COMPLETE** for the local stack. Not yet: multi-query expansion, decomposition, HyDE, sentence-window, and conversation-aware rewriting.

## 20. Reranking Audit

- Model: `BAAI/bge-reranker-v2-m3` (real cross-encoder, loads on CUDA).
- Candidate count: retrieve-50 → rerank → top-N (configured in settings; overridable).
- Fallback: score-order when the model cannot load — this fallback **was not observed to trigger**, since the reranker loaded successfully.
- Status: **COMPLETE**.

## 21. Query Understanding Audit

`retrieval/query_understanding.py` (rule-based planner, no LLM required — deliberate, since no LLM is configured). Extracts:

| Signal | Implemented |
|---|---|
| intent (price / comparison / change / table / compliance / multi-hop) | ✔ |
| supplier entities via tenant vocabulary + aliases | ✔ (fixed during build: alias seeding) |
| product entities (SKU and name) | ✔ |
| contract numbers (`NS-2024-001`, `HTP-2024-014`) | ✔ |
| monetary values | ✔ |
| dates / periods / years | ✔ (fixed: `_YEAR_RE` capturing-group bug that produced the bogus `procurement_value_20` aggregation) |
| `requires_structured` / `requires_graph` / `requires_vision` | ✔ |
| comparison detection | ✔ |

Remaining weakness: the planner is lexical, so phrasing it has not seen (e.g. "cheapest laptop supplier last year") degrades to generic retrieval.

## 22. Query Transformation Audit

| Technique | Status |
|---|---|
| Corrective rewrite on weak evidence | COMPLETE (`rewrite_query` node + loop) |
| Query expansion / synonym | NOT IMPLEMENTED |
| Multi-query / fan-out | NOT IMPLEMENTED |
| Decomposition of multi-part questions | NOT IMPLEMENTED |
| HyDE | NOT IMPLEMENTED |
| Conversation-aware rewrite (follow-ups) | NOT IMPLEMENTED (conversation tables exist, unused) |

## 23. LangGraph Audit

Real graph in `agents/graph.py`:

```text
understand → plan → structured ─┐
                   → graph ─────┤
                   → retrieve ──┼→ vision → evaluate_evidence
                                │        ├─(weak + iterations left)→ rewrite_query → retrieve ↺
                                │        └─(ok / max iters)→ generate → verify → finalize
```

- State: `agents/state.py` `AgentState` — includes a declared `context_blocks` channel; this was a genuine bug (an undeclared key was silently dropped, so `verify()` used to see an empty context).
- Routing: `route_after_evaluation` in `agents/graph.py`.
- Termination: `MAX_AGENT_ITERATIONS` enforced; `graph_diagram()` is exposed for introspection.
- Status: **COMPLETE**.

## 24. Agent / Tool Audit

- **No tool registry exists**: there is no `app/tools/` package (`ls backend/app/tools` → No such file). Capabilities are implemented as **LangGraph nodes**, not as typed, individually-invokable tools.
- Functionally available capabilities: dense/lexical search, structured SQL lookup, price aggregation, conflict detection, contract/supplier/compliance overview, graph paths, comparison, vision escalation (dormant), evaluation.
- PRD conformance: the PRD's `app/tools/` layout and "tool calling" expectation is **NOT IMPLEMENTED**; the capability exists, the tool abstraction does not.

## 25. SQL RAG Audit

- Implementation: `retrieval/structured.py` — **parameterised SQLAlchemy queries over a fixed allow-list of tables**, not free-form LLM SQL. This is stronger than "SQL RAG with a validating LLM": there is no injection surface because no model writes SQL.
- Aggregations run in SQL; simple arithmetic in Python (`python_arithmetic` provenance tag) — the PRD's "exact calculation → Python" rule is respected.
- Grounding: each structured finding carries provenance (`sql_aggregation`, `sql_result_set+python_min`, `python_arithmetic`).
- Tenant/permission scoping: applied via the shared session + scope helpers.
- Status: **COMPLETE** (with the Q4 answer-shape defect described in §46).

## 26. GraphRAG Audit

- Retrieval code: `retrieval/graph_retrieval.py` (+ `providers/graph/*`).
- Trigger: plan's `requires_graph` / multi-hop signals; also additive evidence for entity questions.
- Passed to generation: yes, as graph-path context blocks.
- Agent integration: yes (a LangGraph node).
- **Observed weakness:** several acceptance queries reported `graph_paths: 0`; Q7's ISO 9001 answer was carried by document passages, not graph traversal. GraphRAG therefore works but is **under-triggered**.
- Status: **PARTIAL**.

## 27. Temporal RAG Audit

- Present: `effective_date`, `expiry_date`, `version`, `amendment` on price rows and clauses; supersession text detected in amendment language ("this Amendment prevails", "the later terms govern from that date"); period scoping in the structured layer (Q4 correctly excluded the 2026-01-01 price when asked about 2025).
- Verified behaviour on "current price": the answer states *"USD 920.00 from 2024-01-01 → USD 874.00 effective 2026-01-01 by Amendment 2; the later terms govern from that date."* Temporal resolution in prose is **correct**.
- Defect: the query **status** is still reported as `conflicting` for that question even though the conflict is resolved by supersession. Superseded values are not excluded from conflict detection.
- Status: **PARTIAL**.

## 28. Conflict Detection Audit

- `retrieval/analysis.py::detect_price_conflicts` groups distinct agreed values per (supplier, product) and emits a precise description ("has 2 different agreed unit prices … USD 920.00 from 2024-01-01; USD 874.00 from 2026-01-01 per Amendment 2") — no duplicated values.
- Detected: price conflicts (real, from the corpus). Clause-level conflicts: only via amendment language, not general NLI.
- Defect: conflicts are computed **globally for the entities in scope** and are surfaced in `decide_status` before the sufficiency of the *asked* entity/period, so unrelated conflicts can colour an answer.
- Status: **PARTIAL**.

## 29. Citation Audit

- Every citation resolves to a real `chunk_id` → `document_id` → `page_number` in the DB; 593 citation rows exist; each rendered citation carries document name, page and section (e.g. `supplier_a_amendment_2_NS-2024-001.pdf — p.1 — 1. Price Revision`).
- Answer verification recomputes the citation audit on the final text, including the refusal text.
- Frontend renders citation chips with page badges.
- **Gap:** no click-through from a citation row to the document viewer at that page (the viewer exists on the detail page; the link does not).
- Status: **COMPLETE** for realness/correctness; **PARTIAL** for citation UX navigation.

## 30. Hallucination / Guardrail Audit

- Refusal path verified live: **"Q6. What was Supplier C's price in 2030?" → `status=insufficient_evidence` → "I couldn't verify this from the available procurement documents."** with an explicit reason (no retrieved row/passage is about Orion Components Co; nothing falls in 2030-01-01..2030-12-31) and `structured_rows: 0`. The system does not hallucinate a 2030 price.
- Grounding: lexical-overlap judge reports 9–12 of 12 statements supported per query. Because no LLM is configured, an LLM judge cannot run — and the system says so instead of inventing a confidence score.
- Prompt injection: a dedicated fixture (`security_fixture_injection.pdf`) containing "Ignore all previous instructions…", "developer mode", "reveal the API key" is ingested, flagged by `security/injection.py`, and **still appears in the evidence list** (Q7 evidence `[4]`). It is clearly labelled as an untrusted fixture and did not alter the answer, but its raw text is presented to the reader. Without an LLM there is no observable "instruction compliance" to test, so the guardrail's effectiveness against a real model is **UNVERIFIED**.

## 31. Corrective RAG Audit

- Implemented: `evaluate_evidence` → `route_after_evaluation` → `rewrite_query` → `retrieve` loop, bounded by `MAX_AGENT_ITERATIONS`, with rewrite attempts recorded in traces.
- Verified: the graph contains the loop and terminates; rewrite events are visible in `agent_traces` (50 rows).
- Status: **COMPLETE** (rewrite strategies are lexical variants; no fan-out).

## 32. Self-Reflective RAG Audit

- Answer claims → evidence mapping → grounding assessment → refusal/retry: **all four stages exist** in `agents/verification.py` + `nodes.py::verify` + `decide_status`.
- The verify node rebuilds real `ContextBlock`/`CitationDraft` objects from the declared `context_blocks` channel (previously it verified against an empty bundle — a bug that was found and fixed during this build).
- Evidence-strength assessment is computed **independently of answer support** (e.g. "strong: corroborated structured rows + ≥2 docs, or ≥3 docs and in_force"), which avoids the circularity of grading an answer by itself.
- Status: **COMPLETE** mechanically. The LLM-as-judge half is inactive by configuration.

## 33. Security Audit

| Area | Status | Evidence |
|---|---|---|
| Authentication | COMPLETE | JWT (`tokens.py`), argon2 password hashing, login/refresh/me/logout |
| Authorization | COMPLETE | `security/rbac.py` roles + actions, `deps.py` `require_permission` |
| Tenant isolation | PARTIAL | `tenant_id` on all domain tables + `security/scope.py`; verified on audited read paths, not on all 53 routes |
| Document ACL | NOT IMPLEMENTED | no per-document ACL beyond tenant scoping |
| API security | PARTIAL | CORS pinned to the Vite origins; **`jwt_secret` defaults to `dev-insecure-change-me`** and `allow_self_registration=True` — fine locally, dangerous if shipped unchanged |
| Secret handling | PARTIAL | `.env` gitignored-by-convention + `.env.example` template; no secret manager, no start-up guard refusing the default secret in production |
| File upload security | PARTIAL | type/size validation; no malware scan, no archive-bomb guard |
| Prompt-injection defence | PARTIAL | detector + labelled fixture + untrusted-content framing; effect on a live model unverifiable here |
| Audit logging | PARTIAL | `audit_logs` = 8 rows; only auth/permission-relevant actions are logged |
| Rate limiting / quotas | PARTIAL | configured and reported by `/admin/health`; enforcement not demonstrably exercised |

## 34. Evaluation Audit

- Golden dataset: `data/evaluation/golden_questions.json`, surfaced via `/evaluation/dataset` and `/evaluation/experiments` (with categories and an explicit `unanswerable_count`).
- Metrics (`evaluation/metrics.py`): retrieval recall@k / precision@k / MRR / nDCG / hit-rate; answer correctness; citation precision / citation recall.
- Persistence: `evaluation_runs` (2) + `evaluation_results` (6).
- UI: EvaluationPage renders dataset card, metric tables and Recharts charts; runs can be triggered and deleted.
- **Not implemented:** faithfulness / groundedness as a judge metric (requires an LLM), and any statistical significance handling.
- Status: **COMPLETE** for retrieval + answer + citation metrics; **PARTIAL** overall.

## 35. Observability Audit

- Structured logging (structlog) with JSON mode, correlation via `query_id`.
- Persisted per query: `queries`, `answers`, `citations`, `agent_traces` (retrieval counts, rerank scores, node timings, tool usage, grounding report, degradation notes).
- Exposed: `/admin/traces`, `/admin/queries/{id}`, `/admin/indexing`, `/admin/routing`, `/admin/health`.
- Missing: token accounting is necessarily 0 (no LLM), no Prometheus/OTel exporter despite the optional extra, no dashboard/alerting.
- Status: **PARTIAL** (rich in-DB tracing, no export layer).

## 36. Error Handling Audit

- API: central `api/errors.py` exception handling with structured error payloads; `ApiError` on the client; per-page error states.
- Provider failures: provider factory + `ALLOW_PROVIDER_FALLBACK` policy; health reports blocking providers instead of crashing.
- Per-datastore failure: fallback path exists locally (memory/filesystem). Degradation is reported.
- Parsing/OCR failures: recorded on the ingestion job/page status rather than aborting the batch.
- Timeouts/rate limits for model calls: implemented in the LLM client; not exercisable without an endpoint.
- Status: **COMPLETE** for the exercised paths; **UNVERIFIED** for live Postgres/Qdrant/Neo4j/Redis/MinIO failures.

## 37. UX Audit

Concrete observations (not aesthetic praise):

- Strong: every page implements loading / empty / error states through shared components; degradation banners ("no language model is configured", "Not configured") are shown in-product rather than hidden; verification footer and citation list are first-class.
- **Missing:** citation → document-page deep link; conversation/history sidebar; saved search; export (CSV/PDF) for tables, comparisons or answers; global search across documents/suppliers/contracts; keyboard shortcuts.
- **Inconsistent:** `/graph`, `/evaluation`, `/admin`, `/dashboard` are permission-gated while `/suppliers`, `/contracts`, `/compare`, `/search` are not — the gate is a permission name the user may not recognise when it blocks them.
- Long answers render as large monolithic blocks; the structured-findings and evidence sections compete for attention with no collapsible grouping by default.
- Inputs have labels, but destructive actions (delete eval run) rely on a confirmation dialog with no undo.

## 38. Accessibility Audit

- Semantic landmarks: `AppShell` uses nav/main structure; Lucide icons are decorative in most places.
- **Gaps:** dialogs do not demonstrate focus trapping/restoration, no `aria-live` region for the streaming answer (screen readers will not announce incremental content), tables lack captions/`scope` attributes, colour is the primary carrier of status/severity in badges and charts, no skip-to-content link, and no visible focus-ring audit.
- No automated accessibility tooling (axe) is present.
- Status: **PARTIAL**.

## 39. Testing Audit

| Category | Files | Runs? | Passing? |
|---|---|---|---|
| Unit | **none** | — | — |
| Integration | **none** | — | — |
| Security | **none** | — | — |
| API | **none** (an ad-hoc `scripts/api_smoke.py` exists, not a test) | manual | n/a |
| E2E (Playwright) | **none** | — | — |
| Frontend | **none** (no Vitest/Jest) | — | — |

`pyproject.toml` declares a `[tool.pytest.ini_options]` section and an `eval` extra (`pytest`, `pytest-asyncio`), but **there is not a single test file in the repository**. Coverage is effectively 0%. This is the single largest engineering-quality gap.

Manual verification assets that do exist: `scripts/acceptance_check.py` (the 7 PRD acceptance queries), `scripts/api_smoke.py` (auth + endpoint exercise), `scripts/make_synthetic_corpus.py` (deterministic corpus generation).

## 40. Build / Runtime Audit

Actually run during this audit:

| Check | Command | Result |
|---|---|---|
| Frontend typecheck | `npx tsc --noEmit` | ✔ clean |
| Frontend build | `npm run build` | ✔ exit 0 |
| Frontend lint | `npm run lint` | ✘ **no ESLint config and no `eslint` dependency** — script fails |
| Backend import + route dump | `python -c "create_app()"` | ✔ 58 route objects / 53 endpoints |
| Backend startup | `uvicorn app.main:app --port 8000` (audit ran on :8001 to avoid clashing) | ✔ |
| Health | `GET /api/v1/health` | ✔ reports active providers |
| Auth | `POST /auth/login` | ✔ token issued |
| Query | `POST /query` + `/query/stream` | ✔ 7 acceptance queries answered |
| Ingestion | `epi ingest` | ✔ 9 docs / 34 chunks / 39 prices |
| Evaluation | `epi evaluate` | ✔ 2 runs persisted |
| Acceptance harness | `python scripts/acceptance_check.py` | ✔ all 7 queries produce answers; Q6 refuses |
| Compose app profile | `docker compose --profile app up --build` | ✘ **`backend/Dockerfile` missing** |
| Live Postgres adapter | throwaway `postgres:16-alpine` container | ⚠ attempted; the compose-style DSN uses `postgresql+psycopg`, and **`psycopg` is not installed** (only `psycopg2` + `asyncpg`) |
| Live Qdrant / Neo4j / Redis / MinIO | — | ✘ **UNVERIFIED** (no services running; Docker daemon unavailable for the full stack) |
| Tests | — | ✘ none exist |

Acceptance results (latest full run, warm):

| Query | Status | Evidence strength | Grounding | Citations |
|---|---|---|---|---|
| Q1 Supplier A current price | conflicting | strong | 12/12 | 12 |
| Q2 change original → Amendment 2 | conflicting | strong | 12/12 | 12 |
| Q3 compare A vs B | conflicting | strong | 10/12 | 12 |
| Q4 lowest price in 2025 | supported | strong | 12/12 | 12 |
| Q5 pricing table on page 4 | partial | strong | 11/12 | 12 |
| Q6 Supplier C price in 2030 | **insufficient_evidence (refusal)** | strong | 9/12 | 12 |
| Q7 ISO 9001 + contract (multi-hop) | supported | strong | 12/12 | 12 |

All queries report `generation_mode=extractive` and `degraded=True` — accurate self-reporting of the missing LLM.

## 41. Dead Code Audit

- **Orphan API endpoints:** 19 (listed in §10).
- **Unused frontend API-client methods:** `conversations`, `conversation`, `messages`, `products`, `prices`, `compliance`, `graphNeighbors`, `dataset`, `queryDetail` (defined in `frontend/src/lib/api.ts`, never called from pages/components).
- **Unused declared dependencies:** `@radix-ui/react-dropdown-menu`, `@radix-ui/react-scroll-area` (declared in `package.json`, never imported). 8 of the 10 declared Radix packages are used.
- **Empty-but-present schema:** `conversations`, `conversation_messages`, `data_sources` (0 rows).
- **Missing for a declared script:** `npm run lint` has no ESLint config/dependency.
- **Documentation drift:** `scripts/acceptance_check.py` was adjusted so Q5 asks about "the pricing table on page 4" while the PRD text says page 18 (the synthetic corpus renders the pricing table on page 4). Correct behaviour, but it must be documented or the acceptance harness will look like it contradicts the PRD.
- Runtime/scratch state committed to the tree: `backend/var/` (DBs, vector index, stored files), `.freebuff/`.
- No git repository, therefore no history, no diff discipline, no `.gitignore` enforcement.

## 42. Configuration Audit

- `.env.example`: complete — app, security, DB, vector, graph, cache, storage, LLM, vision, embedding, reranker, OCR/vision flags, ingestion limits, evaluation, observability. Matches the settings class.
- `settings.py`: `SettingsConfigDict(env_file=[root/.env, backend/.env], case_sensitive=False, extra="ignore")`, **no `env_prefix`**, so bare names like `DATABASE_URL` are read — which is why the compose environment block *appears* coherent.
- **Mismatch (HIGH):** `docker-compose.yml` sets `DATABASE_URL: postgresql+psycopg://…`, but `pyproject.toml` ships `asyncpg` and no `psycopg`. The async engine requires `psycopg` (v3) for that driver string; `psycopg2` on this machine cannot serve an async engine.
- CORS: defaults to `http://localhost:5173` / `127.0.0.1:5173`, matching the Vite dev server.
- Frontend API base: `VITE_API_BASE_URL ?? ""` + `/api/v1`, with a Vite dev proxy to the backend — correct for dev, and the compose `web` service overrides it to `http://localhost:8000`.
- Security defaults that must not ship: `jwt_secret = "dev-insecure-change-me"`, `allow_self_registration = True`, `ALLOW_PROVIDER_FALLBACK` (true locally, false in compose — good).
- Email validation had to be reduced to a plain-string schema (`schemas/email.py`) because the installed `email-validator` behaviour rejected the seeded admin address; documented here as a deliberate deviation.

## 43. Dependency Audit

- Backend: `pyproject.toml` is coherent and minimal; heavyweight extras (`ocr`, `vision`, `eval`, `observability`) are correctly optional. **`psycopg` missing** for the compose DSN; `opentelemetry-*`/`langsmith` declared as extras but unused; `langchain-core` used only for message types; `pandas` declared but little used.
- Frontend: clean and current (React 18, Vite 6, TS 5.7, Tailwind 3.4, TanStack Query 5, Zustand 5, Recharts 2). Two unused Radix packages; **`eslint` missing although a lint script is declared**.
- No duplicate/competing libraries found; no lockfile drift was evaluated.
- Status: **PARTIAL** (two real defects, otherwise tidy).

## 44. Feature Compliance Matrix

Denominator: **82 audited requirements** (enumerated below). Formula: `(COMPLETE + 0.5 × PARTIAL) / 82`.

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | React + TypeScript + Vite frontend | COMPLETE | `frontend/` |
| 2 | Tailwind CSS | COMPLETE | `tailwind.config.js` |
| 3 | shadcn/ui component system | COMPLETE | 8 Radix-backed primitives in `components/ui` |
| 4 | TanStack Query | COMPLETE | `main.tsx`, pages |
| 5 | Zustand | COMPLETE | `store/auth.ts`, `store/ui.ts` |
| 6 | React Router | COMPLETE | `App.tsx`, 14 routes |
| 7 | Lucide React | COMPLETE | shell, states, dialogs |
| 8 | Recharts | COMPLETE | Dashboard, Evaluation |
| 9 | FastAPI + Pydantic v2 | COMPLETE | `main.py`, `schemas/` |
| 10 | SQLAlchemy 2.0 async | COMPLETE | `db/session.py` |
| 11 | Alembic migrations | PARTIAL | one bootstrap revision; unused locally |
| 12 | LangChain | PARTIAL | `langchain-core` message types only |
| 13 | PostgreSQL adapter | UNVERIFIED | code exists, never run live |
| 14 | Postgres via compose | BROKEN | `postgresql+psycopg` + missing psycopg; no backend Dockerfile |
| 15 | Qdrant adapter | UNVERIFIED | no daemon |
| 16 | Neo4j adapter | UNVERIFIED | no daemon |
| 17 | Redis cache adapter | UNVERIFIED | memory fallback active |
| 18 | MinIO/S3 storage adapter | UNVERIFIED | filesystem fallback active |
| 19 | Local adapters (sqlite/vector/graph/cache/fs) | COMPLETE | all verification ran on these |
| 20 | BAAI/bge-m3 embeddings | PARTIAL | falls back to bge-small 384-d |
| 21 | BGE reranker v2-m3 | COMPLETE | loads on CUDA, reorders |
| 22 | Qwen3-30B reasoning model | NOT IMPLEMENTED | no endpoint |
| 23 | Qwen3-VL vision model | NOT IMPLEMENTED | no endpoint |
| 24 | Model router | PARTIAL | routing table + rationale; LLM/VLM tiers inactive |
| 25 | Provider abstraction (4 interfaces) | COMPLETE | `providers/base.py` |
| 26 | OCR | COMPLETE | scanned page read and cited |
| 27 | Prompt-injection defence | PARTIAL | detector + fixture; effect unverifiable without a model |
| 28 | Upload + validation + multi-format parsing | COMPLETE | PDF/DOCX/XLSX/CSV/TXT + images |
| 29 | Image ingestion (PNG/JPG/JPEG) | PARTIAL | code path present; only the PDF scan was exercised |
| 30 | Page-level indexing | COMPLETE | 15 pages with full metadata |
| 31 | Layout / heading / clause structure | COMPLETE | sections/clauses in citations |
| 32 | Table extraction | COMPLETE | 3 tables + XLSX sheets |
| 33 | Structural / contract-aware chunking | COMPLETE | 34 chunks with clause metadata |
| 34 | Semantic chunking | NOT IMPLEMENTED | no similarity boundaries |
| 35 | Contextual retrieval enrichment | COMPLETE | `contextualizer.py` |
| 36 | Parent-child / small-to-big | NOT IMPLEMENTED | — |
| 37 | Embedding + vector indexing | COMPLETE | local index, 34 chunks |
| 38 | BM25 lexical index | COMPLETE | rank_bm25 |
| 39 | Background ingestion worker | PARTIAL | worker + jobs exist; no compose service, in-process on upload |
| 40 | Data-source connectors with provenance | PARTIAL | connector framework + `data_sources` table, 0 rows used |
| 41 | Job status + retry | PARTIAL | status shown; no retry endpoint |
| 42 | Query understanding | COMPLETE | entities, periods, requirements |
| 43 | Hybrid dense + BM25 + RRF | COMPLETE | `retrieval/fusion.py` |
| 44 | Metadata filtering | PARTIAL | local verified; Qdrant unverified |
| 45 | Reranking | COMPLETE | cross-encoder |
| 46 | Corrective query rewrite loop | COMPLETE | bounded rewrite node |
| 47 | Multi-query / decomposition / HyDE | NOT IMPLEMENTED | — |
| 48 | Conversation-aware rewriting | PARTIAL | conversation tables + API exist, unwired |
| 49 | Structured SQL retrieval | COMPLETE | allow-listed parameterised queries |
| 50 | Graph retrieval | COMPLETE | local graph paths, agent-integrated |
| 51 | Temporal awareness | PARTIAL | period scoping works; superseded prices still "conflicting" |
| 52 | Conflict detection | PARTIAL | price conflicts real; global scope leaks unrelated conflicts |
| 53 | LangGraph agent + max iterations | COMPLETE | `agents/graph.py` |
| 54 | Agent tool registry | NOT IMPLEMENTED | no `app/tools/` |
| 55 | Context bundle + citation drafts | COMPLETE | `retrieval/context.py` |
| 56 | Grounding / self-reflection | COMPLETE | criteria-based, non-circular |
| 57 | Refusal policy | COMPLETE | Q6 refuses with a reason |
| 58 | Citation realness | COMPLETE | 593 citations resolve to chunks/pages |
| 59 | LLM answer generation | NOT IMPLEMENTED | extractive only |
| 60 | Comparison answers | BROKEN | Q3 omits Supplier B |
| 61 | REST API surface | COMPLETE | 53 endpoints |
| 62 | SSE streaming | COMPLETE | `/query/stream` + client reader |
| 63 | Conversation persistence | PARTIAL | endpoints exist, 0 rows, no UI |
| 64 | Role-based admin endpoints | COMPLETE | `require_permission` |
| 65 | JWT auth + argon2 | COMPLETE | verified live |
| 66 | RBAC | COMPLETE | `security/rbac.py` |
| 67 | Tenant isolation | PARTIAL | verified on audited paths only |
| 68 | Audit logging | PARTIAL | 8 rows |
| 69 | Rate limiting / quotas | PARTIAL | configured, enforcement unverified |
| 70 | Golden dataset | COMPLETE | `data/evaluation/golden_questions.json` |
| 71 | Retrieval metrics | COMPLETE | recall/precision/MRR/nDCG/hit-rate |
| 72 | Answer & citation metrics | PARTIAL | no faithfulness/groundedness judge |
| 73 | Evaluation persistence + UI + comparison | COMPLETE | 2 runs, charts |
| 74 | Observability traces | PARTIAL | rich in DB, no exporter/metrics endpoint |
| 75 | docker-compose stack | PARTIAL | all 5 services defined; **backend Dockerfile missing**, no worker service |
| 76 | `.env.example` | COMPLETE | 6.3 KB template |
| 77 | README.md | NOT IMPLEMENTED | absent |
| 78 | Data documentation | PARTIAL | `manifest.json` + `corpus_card.json`, no `data/README.md` |
| 79 | docs/ directory | NOT IMPLEMENTED | absent |
| 80 | Tests (unit/integration/security/E2E) | NOT IMPLEMENTED | zero test files |
| 81 | Frontend production build | COMPLETE | `npm run build` exit 0 |
| 82 | Backend startup + API smoke | COMPLETE | verified live |

**PRD Compliance: (44 COMPLETE + 0.5 × 21 PARTIAL) / 82 = 54.5 / 82 = 66.5% → 66%.**
(The remaining 17 items are 10 NOT IMPLEMENTED, 2 BROKEN, 5 UNVERIFIED.)

## 45. End-to-End Feature Matrix

| Feature | UI | API | Backend | DB | AI | Test | E2E |
|---|---|---|---|---|---|---|---|
| Login / session | ✓ | ✓ | ✓ | ✓ | — | ✗ | ✓ |
| Document upload | ✓ | ✓ | ✓ | ✓ | ✓ (OCR/embed) | ✗ | ✓ |
| Ingestion & indexing | ✓ (status) | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Page-level indexing | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Hybrid retrieval | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Reranking | ✓ | ✓ | ✓ | — | ✓ | ✗ | ✓ |
| Structured SQL RAG | ✓ | ✓ | ✓ | ✓ | ✓ (Python calc) | ✗ | ✓ |
| GraphRAG | ✓ | ✓ | ✓ | ✓ (local) | ✓ | ✗ | PARTIAL |
| Temporal reasoning | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | PARTIAL |
| Conflict detection | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | PARTIAL |
| Citations | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Refusal / guardrail | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| SSE streaming answers | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| LLM narrative answers | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| VLM escalation | ✓ (labelled off) | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| Conversations / history | ✗ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| Evaluation runs | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Observability UI | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Qdrant / Neo4j / Redis / MinIO | ✗ | ✓ | ✓ | — | — | ✗ | UNVERIFIED |
| Docker deployment | — | — | — | — | — | ✗ | ✗ (cannot build) |

## 46. Broken Flows

1. **`docker compose --profile app up` cannot build the API** — `dockerfile: backend/Dockerfile` does not exist (`glob **/Dockerfile*` → only `frontend/Dockerfile`). The documented production path is dead on arrival.
2. **Postgres deployment would fail at engine creation** — compose DSN `postgresql+psycopg://…` with no `psycopg` dependency installed/declared.
3. **Comparison answers (Q3)** — "Compare Supplier A and Supplier B prices for Industrial Laptop X200" produces Supplier A's two prices and a note about supersession, but **never mentions Supplier B**, even though `Helios … USD 895.00` is present in the structured findings. Frontend (ComparePage) side is fine; the agent's comparison composition is not.
4. **Temporal aggregation answer (Q4)** — "Which supplier had the lowest price in 2025?" returns a fan-out of per-product lowest prices (139.0, 298.0, 895.0, 1180.0), a `lowest_price_supplier` for the *Docking Station*, and an irrelevant `procurement_value_2025: 7904000.0` aggregation; it never states "Helios Technology Partners Inc". Period scoping itself works (the 2026-01-01 price is correctly excluded), but the answer does not answer the question.
5. **Status semantics after supersession** — Q1/Q2/Q3 remain `conflicting` although Amendment 2 resolves the conflict; the answer prose says the later terms govern while the status badge says unresolved.
6. **Citation click-through** — cited pages cannot be opened from the answer; the viewer exists elsewhere.
7. **`npm run lint`** — script declared, no ESLint config or dependency.
8. **Chat history** — endpoints + tables exist, UI and pipeline integration do not.

## 47. Missing Features

- LLM-backed generation, LLM grounding judge, token accounting (needs an endpoint).
- VLM escalation and chart/diagram understanding (needs Qwen3-VL).
- Multi-query expansion, decomposition, HyDE, conversation-aware rewrite.
- Semantic chunking, parent-child / sentence-window retrieval.
- Agent tool registry (`app/tools/`) with typed tools and permissions.
- Document-level ACLs; malware scanning; production secret hardening.
- Rate-limit enforcement; broader audit coverage.
- Export (CSV/PDF), saved searches, global cross-entity search, keyboard shortcuts.
- Faithfulness / groundedness judge metric; retrieval-parameter sweep and A/B evaluation of retrieval configs.
- `README.md`, `docs/`, `data/README.md`; `data/raw` and `data/processed` directories.
- Tests of every kind; CI.
- Background worker service in compose + job retry API.
- Live integration verification for Postgres, Qdrant, Neo4j, Redis, MinIO.

## 48. Mocked / Fake Features

**No fake metrics, fake citations, fake prices, fake document counts, or fabricated model responses were found.** This is a notable and deliberate property of the codebase: the UI and API never assert a retrieval count, confidence score or grounding value that was not produced by the pipeline, and unavailable capabilities are rendered as "Not configured / Unavailable / Pending / Not evaluated".

The only bounded, explicitly-labelled artificial elements are:

| Item | Nature | Labelling |
|---|---|---|
| `data/synthetic/**` (12 documents) | Deliberately synthesised corpus incl. conflicting prices, expired contract, scanned page, injection fixture | Every document and every chunk carries `is_synthetic = true`; the corpus card and manifest state it; the UI shows a synthetic badge |
| `security_fixture_injection.pdf` | Adversarial fixture | Filename + page text mark it as a SYNTHETIC SECURITY FIXTURE |
| Contradiction-driven analytics in `scripts/make_synthetic_corpus.py` | Generated corpus design | Documented in `corpus_card.json` |
| "Extractive summary — no language model is configured" | Honest fallback, not a mock answer | Stated in the answer body of every response |

One nuance worth stating plainly: because generation is extractive, the "answer" text is assembled from real retrieved sentences. That is not a mock, but it *is* why Q3/Q4 look wrong — the composer cannot yet reason across entities. Fixing that requires the LLM tier, not a mock patch.

## 49. Critical Findings

| ID | Finding | Evidence | Impact |
|---|---|---|---|
| C1 | `backend/Dockerfile` does not exist while compose references it | `glob **/Dockerfile*` → only `frontend/Dockerfile`; `docker-compose.yml` line 108 | The documented production deployment path cannot build. CRITICAL |
| C2 | No LLM/VLM endpoint and no `bge-m3` weights | `llm_configured=False`, `generation_mode=extractive`, `degraded=True`, embeddings `dim=384` | The PRD's core generation, LLM grounding, VLM and model-routing tiers are inactive. The system is honest about it, but not PRD-complete. CRITICAL |
| C3 | Compose `DATABASE_URL` uses `postgresql+psycopg` but `psycopg` is not a dependency | `docker-compose.yml` line 110; `pyproject.toml` lists only `asyncpg`; import probe: `psycopg MISSING` | Any real Postgres deployment fails at engine creation. CRITICAL |
| C4 | Zero automated tests | no `tests/`, no pytest/vitest/playwright files; `pytest` configured but unused | No regression safety on a system with 53 endpoints, an agent graph and 5 datastore adapters. CRITICAL |

## 50. High Priority Findings

| ID | Finding | Evidence | Impact |
|---|---|---|---|
| H1 | Comparison answers omit the second entity | Q3 output never mentions Helios | The PRD's Query 3 expectation is met by the API/ComparePage but not by the agent's answer |
| H2 | "Lowest price in 2025" is answered with an aggregation fan-out | Q4 structured findings (139/298/895/1180 + Docking Station + `procurement_value_2025`) | Wrong answer shape on a headline PRD query |
| H3 | Superseded prices still reported as `conflicting` | Q1/Q2/Q3 status vs. the answer's own supersession sentence | Misleading status on the most common procurement question ("current price") |
| H4 | Embedding model/dimension drift | local index 384-d vs Qdrant path configured 1024-d | Silent quality loss and a hard failure if the two are mixed |
| H5 | No worker service in compose; uploads ingest in-process | compose services list; `POST /documents/upload` blocks during parsing/OCR/embedding | Long uploads block the request path; no retry |
| H6 | Neo4j deployment path never exercised; GraphRAG under-triggers | `graph_paths: 0` on several queries; no live Neo4j | GraphRAG may silently degrade to document retrieval in production |
| H7 | No README / no docs | absent at root | A new engineer cannot run the stack; the compose path is broken anyway |
| H8 | Injection fixture text is surfaced verbatim in an answer's evidence list | Q7 evidence `[4]` | Untrusted instructions are shown to the reader (and would enter an LLM prompt once configured) |

## 51. Medium / Low Priority Findings

Medium:

| ID | Finding |
|---|---|
| M1 | Irrelevant aggregations leak into answers (e.g. `procurement_value_all_years`, `procurement_value_2025` on unit-price questions) |
| M2 | 19 orphan API endpoints with no frontend consumer |
| M3 | 9 unused frontend API-client methods |
| M4 | Tenant isolation verified on audited paths only, not across all 53 routes |
| M5 | Audit logging covers few actions (8 rows) |
| M6 | Rate limiting configured but not demonstrably enforced |
| M7 | No faithfulness/groundedness judge metric |
| M8 | Conversations schema + API + UI all incomplete as a unit (0 rows, no UI, no rewrite) |
| M9 | Semantic chunking and parent-child retrieval absent (PRD lists both) |
| M10 | `app/tools/` registry absent; capabilities are graph nodes |
| M11 | Observability has no exporter/metrics endpoint |
| M12 | Postgres/Qdrant/Neo4j/Redis/MinIO adapters unverified live; production and local behaviours may diverge |
| M13 | Alembic migration never applied locally (`auto_create_schema=True`) |
| M14 | Security defaults unsafe if shipped (`dev-insecure-change-me`, self-registration on) |

Low / Info:

| ID | Finding |
|---|---|
| L1 | `npm run lint` cannot run (no ESLint config/dependency) |
| L2 | Two unused declared Radix packages (`dropdown-menu`, `scroll-area`) |
| L3 | `langchain-core`, `pandas`, `opentelemetry-*`, `langsmith` are declared with little or no use |
| L4 | Acceptance harness deviates from PRD wording (page 4 vs page 18) and is undocumented |
| L5 | `data/raw` and `data/processed` directories from the PRD layout are absent |
| L6 | Runtime/scratch state in the tree (`backend/var/`, `.freebuff/`); repo is not initialised as git |
| L7 | Accessibility gaps: no `aria-live` for streaming answers, table captions/scopes, focus-trap verification, or chart alternatives |

## 52. Top 10 Fixes

Ordered by correctness → security → end-to-end functionality → RAG quality → UX → performance → maintainability.

| # | Fix | Why first |
|---|---|---|
| 1 | Make the production path real: add `backend/Dockerfile`, correct the compose DSN to `postgresql+asyncpg` (or add `psycopg`), add a worker service | Unblocks every deployment claim; C1 + C3 + H5 |
| 2 | Stand up a model endpoint (LLM + optional VLM) and provision `bge-m3`, then flip generation from extractive to generated with the grounding judge enabled | Unlocks generation, LLM-as-judge, VLM and token accounting; C2 + H4 |
| 3 | Fix answer composition for comparisons and year-scoped aggregations (Q3 must compare; Q4 must name a supplier; drop irrelevant aggregations) | Two headline PRD queries are currently answered wrongly; H1 + H2 + M1 |
| 4 | Make conflict/status semantics temporal: a superseded value is resolved, not conflicting | The most asked question ("current price") carries a misleading status; H3 |
| 5 | Add a real test suite: unit (chunking, fusion, metrics, verification), integration (ingestion → retrieval → answer, API contract), security (RBAC/tenant/injection), and one Playwright E2E of the login → ask → citation flow | 0% coverage today; C4 |
| 6 | Harden security defaults: refuse to start with the default JWT secret in production, disable self-registration by default, extend audit coverage, enforce rate limits, scan uploads | C-level exposure before any real deployment; M5 + M6 + M14 |
| 7 | Wire citation → document page deep links, and finish conversations end-to-end (persist, list, follow-up rewriting) | Highest-value UX gap with existing backend support; §37 + M8 |
| 8 | Trigger GraphRAG deliberately and verify it against Neo4j (path queries should fire on multi-hop questions) | GraphRAG is a named PRD pillar and currently under-triggers; H6 |
| 9 | Write `README.md`, `docs/` (architecture, retrieval, evaluation, ops) and `data/README.md`; document the page-4/page-18 deviation | Onboarding currently impossible; H7 + L4 |
| 10 | Clean up dead surface: retire or surface the 19 orphan endpoints and 9 unused client methods, fix `npm run lint`, prune unused deps, remove `backend/var` scratch from the tree | Maintainability; L1–L3 + M2 + M3 |

## 53. Recommended Implementation Order

1. **Deployment correctness** (Top-10 1, 9 basics): backend Dockerfile, DSN, worker service, README/docs.
2. **Model tier activation** (2): LLM endpoint, VLM endpoint, `bge-m3`, then re-run the 7 acceptance queries and the evaluation suite to get real generated-answer metrics.
3. **Answer-quality correctness** (3, 4): comparison composition, aggregation relevance, temporal status semantics.
4. **Regression safety** (5): the test suite, so the above changes are provably safe.
5. **Security hardening** (6).
6. **UX completion** (7): citation deep links, conversations, exports.
7. **Graph and retrieval depth** (8): GraphRAG triggering, semantic/parent-child chunking, multi-query.
8. **Cleanup** (10) and observability export.
9. **Live integration verification** of Postgres, Qdrant, Neo4j, Redis, MinIO once Docker is available.

## 54. Final Audit Summary

If you open this project right now, here is exactly what happens:

You can start the FastAPI backend on a local SQLite stack and the Vite frontend, log in with a real JWT, upload a PDF/XLSX/CSV, and watch it genuinely parse, OCR, layout-analyse, chunk, embed, index into a local vector store and BM25, and write pages, chunks, tables, prices, suppliers and contracts into a real database with a real property graph beside it. You can ask "What is Supplier A's current price for the Industrial Laptop X200?" and receive a grounded, page-cited answer that correctly reports the 2024 price and the Amendment 2 revision and states that the later terms govern. You can ask an unanswerable question and get a clean refusal with a stated reason instead of a hallucination. You can inspect the retrieval path, the citation list, the verification footer, the model routing table, the provider health, and the evaluation runs — and every number you see was computed by the system.

What you cannot do: get a language model to write the answer (no endpoint), get the VLM to look at a scanned page (no endpoint), deploy the documented way (the backend image does not exist and the Postgres DSN names a driver that is not installed), trust a comparison answer to mention both suppliers, get a clean "which supplier was cheapest in 2025" answer, open a cited page from the citation, continue a conversation, or run a single automated test.

```text
Overall Implementation Status: FUNCTIONAL LOCAL MVP — NOT PRODUCTION-COMPLETE

PRD Requirements Audited: 82

Complete:        44
Partial:         21
Not Implemented: 10
Broken:           2
Mocked:           0   (synthetic corpus is labelled; no faked metrics or citations found)
Unverified:       5   (live Postgres, Qdrant, Neo4j, Redis, MinIO)

Critical Issues:  4
High Issues:      8
Medium Issues:   14
Low Issues:       7

PRD Compliance:   (44 + 0.5 × 21) / 82 = 66%
```

**Top next action:** create `backend/Dockerfile` and fix the compose Postgres DSN (`postgresql+asyncpg`), because until the documented deployment path builds and boots, none of the production-oriented claims — and none of the five unverified datastore adapters — can be validated.

---

## 55. Frontend and UX Rebuild (implemented 30 September 2026)

The section above records the audit as it stood before the UX work. This section records what was then rebuilt, what it verified, and what remains open. Backend RAG logic was not modified; no endpoint was invented.

### 55.1 What changed

| Area | Before | After |
| --- | --- | --- |
| Theme | Dark-first, card-per-field density | Light-first neutral system, one accent, defined motion scale, `prefers-reduced-motion` respected |
| Public surface | None (login only) | `/`, `/security`, `/privacy`, `/terms`, plus a public shell with working links only |
| Shell | Flat navigation, status chips, no mobile navigation | Sectioned sidebar (Workspace / Analysis / Administration), permission-filtered, mobile drawer with Escape handling, skip link, account menu with the account's permission list |
| Ask | Single column, answer below the composer | Three-pane workspace: stored question history, composer with pipeline status, answer panel, evidence panel; citations are links to the cited page |
| Citations | Text only | `CitationChip` / `EvidenceItem` resolve to `/documents/:id?page=N&chunk=CHUNK`, and the viewer highlights that passage |
| Document detail | Pages and chunks in tabs, untyped detail payload | Viewer with page navigation, authorized page image, extracted text, extracted tables, chunk list and the cited passage marker |
| Search | Result cards with raw scores | Filters that the API supports, a "Relevant because" line built from `matched_by`, scores behind a disclosure, pipeline panel |
| Compare | Matrix with citation names | First-class supplier picker, per-cell provenance (`read from stored row` / `computed from records`), citation links, "Not found in indexed documents" wording |
| Overview | Four KPI cards, decorative pie chart | Real corpus figures, recent documents, ingestion queue, deployment status, corpus composition |
| Evaluation | Runs table plus a multi-bar chart | Measured-versus-unavailable split, experiment availability with reasons, per-question results, one chart that answers "how did each run score" |
| Relationships | Node picker plus edge table | Same data, plus deep links to supplier, contract and document pages, and stored properties for records without a page |
| Accessibility | Focus styles partial, no landmarks or captions | Landmarks, `aria-current`, table captions and `scope`, `role="alert"`, `aria-live` status rail, visible focus rings, labelled controls, status never conveyed by colour alone |

### 55.2 Real defects found and fixed during the rebuild

1. `uploadDocument` declared and parsed the wrong response shape. The API returns `{document, job, duplicate_of, message}`; the client typed `{id, filename, status, duplicate_of}` and the success message therefore read `undefined`. The client now types `UploadResponse` and reports the document id, the job status and the stage.
2. Rendered page images were requested with a plain `<img src>` against an endpoint that requires a bearer token, so every page image would have failed with 401. Images are now fetched with the token and exposed as a revocable blob URL (verified: a 1190x1684 PNG loads in the viewer).
3. `document()` was typed as `DocumentSummary & {pages?: unknown[]}` and the page tables and ingestion job the API returns were dropped. The detail payload is now typed (`PageOut`, `TableOut`, `IngestionJob`) and surfaced.
4. The overview page rendered a bar chart and a donut whose only purpose was decoration; the corpus counts it duplicated are now a definition list.
5. An em dash placeholder (`—`) was used for "no value"; every such case now names the state (`Not recorded`, `Not found in indexed documents`, `not evaluated`), so an absent value cannot be read as a zero or a dash artefact.
6. `@radix-ui/react-scroll-area` was declared but unused and has been removed from `package.json`; `@radix-ui/react-dropdown-menu`, previously declared and unused, now backs the account menu.
7. The console emitted two React Router v7 future-flag warnings on every load; the router now opts into both flags and the console is clean.

### 55.3 UX features that are now connected to real backend capability

- **Conversation history** (audit item 35). The query pipeline already persisted messages when `conversation_id` is supplied; the interface now creates a conversation on the first question, lists stored conversations, and restores a transcript. Verified end to end: a streamed query with a conversation produced 10 status events, a conflicting answer with 12 citations, and exactly two stored messages (user, assistant).
- **Degraded status** (audit item 25). "Extractive mode" is shown as an inline state with a tooltip that explains it, and the full component table lives on the overview and admin pages. No banner, no alarm, and no claim of model generation.
- **Honest measurement.** Evaluation reports `not evaluated` for metrics the dataset cannot support, and experiments that need a model say they cannot run.

### 55.4 Verification performed

| Check | Result |
| --- | --- |
| `npx tsc --noEmit` | Clean |
| `npm run build` | Clean; route-level code splitting active (12 lazy chunks) |
| Routes walked against the running API | `/`, `/login`, `/dashboard`, `/documents`, `/documents/:id?page&chunk`, `/contracts/:id`, `/suppliers/:id`, `/compare`, `/search`, `/graph`, `/evaluation`, `/admin`, `/security` |
| Real data observed | Overview: 9 documents, 15 pages, 42 embedded chunks, 3 suppliers, 51 price rows, 18 certificates, 50 questions, 89 graph nodes / 192 edges. Relationships breakdown, evaluation dataset (22 questions, 5 unanswerable), admin component table, per-question traces |
| Citation deep link | Cited chunk found on the cited page and highlighted; page image served (PNG, 84.9 KB) |
| Console | No errors. Only React Router future-flag warnings, since silenced |

### 55.5 Still open after the rebuild

1. **No automated frontend tests, and no accessibility test runner.** The project still has zero test files, so the a11y work above is verified by inspection and DOM checks only. Adding Playwright plus axe would be the next structural step.
2. **Answer streaming is event-level, not token-level.** The status rail shows real pipeline events, but the answer arrives as a single `answer` event, so there is no progressive text. Doing better requires a backend change and was out of scope.
3. **No exports.** CSV or PDF export of a table, comparison or answer needs a backend endpoint; nothing was added to the interface that would not work.
4. **Conversation management is read-only.** Conversations cannot be renamed or deleted because no endpoint exists for either.
5. **The evaluation bundle is heavy.** The charts pull recharts into a 397 kB chunk. It is code-split and lazy, so the cost is only paid on that route.
6. **No dark-mode toggle.** Tokens for a dark palette exist, but the product ships light-first and no switch is exposed.
7. **Visual regression could not be captured in this environment** (the preview webview produced no frames), so layout was verified through the accessibility tree and computed styles rather than screenshots.
8. **The deployment blockers from the audit are unchanged.** `backend/Dockerfile` is still missing, the compose Postgres DSN still names `psycopg` (not installed), and the Postgres, Qdrant, Neo4j, Redis and MinIO adapters remain unverified.

### 55.6 Compliance checklist result

No purple gradients, no gradient text or cards, no AI slogans, no fake social proof, no fake counters, no testimonials, no emoji, no em dashes in interface copy, no fake security claims, no dead links and no button for functionality that does not exist. Every figure displayed in the interface is read from the API, and every degradation the platform reports is described in plain language instead of being hidden.


# Final Verification

Verification run on 1 October 2026 against the running system, not against the source tree. Every status below is `VERIFIED` only where the behaviour was observed; where it could not be, the status says so. The instruction followed throughout: something existing in code, config or a button is never reported as working.

**How this was verified**

| Instrument | What it does |
| --- | --- |
| `scripts/final_verification.py` | 62 checks against the live API: health, providers, auth, retrieval, 8 questions, citations, uploads/ingestion, and in-process model loads. Writes `backend/var/final_verification.json` |
| Live HTTP probes | Direct `curl` calls whose full responses were inspected for the specific claims quoted below |
| Browser session | A real Chromium session driven through the accessibility tree and DOM reads on `/`, `/login`, `/ask`, `/graph` |
| Build and type checks | `npx tsc --noEmit`, `npm run build`, `python -m compileall` |
| Server logs | `uvicorn` structured logs, including the failure and recovery records cited under RAG |

**Result of the automated run: 62 checks — 56 VERIFIED, 5 NOT CONFIGURED, 1 PARTIALLY VERIFIED, 0 BROKEN.**

## Frontend

| Claim | Status | Evidence |
| --- | --- | --- |
| TypeScript compiles with no errors | **VERIFIED** | `npx tsc --noEmit` exits clean |
| Production build succeeds | **VERIFIED** | `npm run build` succeeds; route-level chunks emitted |
| 3D code is code-split, not in the main bundle | **VERIFIED** | Build output: `HeroEvidenceScene` 2.62 kB, `GraphScene3D` 3.06 kB, shared three.js chunk (`SceneFrame`) 847.98 kB (gzip 229.51 kB); main `index` unchanged at 465.15 kB |
| Navigation order is Overview, Ask, Search, Documents, Contracts, Suppliers, Compare / Relationships, Evaluation / Administration | **VERIFIED** | Live DOM order read from `nav[aria-label="Workspace"]` |
| Answer states use the four required words | **VERIFIED** | Q4 rendered `SUPPORTED`; Q6 rendered `UNABLE TO VERIFY`; Q3/Q7 rendered `CONFLICTING EVIDENCE` |
| Technical details collapsed by default and grouped | **VERIFIED** | Live DOM: `#technical-details` `open=false`, containing `Verification`, `Retrieval`, `How the question was read` |
| "Extractive mode" badge replaced by "Evidence-based answer" | **VERIFIED** | Answer panel shows `Evidence-based answer`; the string `Extractive mode` is absent from the answer and from the workspace header status; the mode name remains in the technical details (`Generation: extractive`) |
| Citation markers in the answer text are links to the cited page | **VERIFIED** | Live DOM: five `.prose-answer a` hrefs of the form `/documents/doc_…?page=1&chunk=chk_…` |
| Refusal card states documents checked, passages reviewed and a link to retrieval details | **VERIFIED** | Live DOM for Q6: `Documents checked 5 documents`, `Relevant passages 12 passages`, `Retrieval outcome 0 candidate(s) → 12 read`, button `See retrieval details` (candidate count corrected to the maximum across steps, see Backend) |
| One workspace-level demo-corpus note replaces per-citation badges | **VERIFIED** | Live DOM: `Demo workspace · Synthetic procurement corpus` present once; `demo corpus` badge count in the answer 0 |
| Instruction-like passages are marked as untrusted document content | **VERIFIED** | Live DOM on Q7: citation `[7] security_fixture_injection.pdf page 1` carries `UNTRUSTED DOCUMENT CONTENT` with the detector's five patterns described in plain language |
| Evidence not quoted by the answer is labelled as such | **VERIFIED** | Live DOM: five citations carry `Read as context for this question; the answer text does not quote this marker.`; driven by `validation.referenced_markers` |
| Keyboard reachability of the new controls | **PARTIALLY VERIFIED** | Skip link, citation links, disclosure summary and the pause/hide buttons are focusable elements; no automated accessibility runner (axe) was executed, so this is inspection plus DOM evidence |
| Visual pixel-level review | **NOT VERIFIED** | The preview webview produced no composited frames, so no screenshot could be captured. Layout, geometry, labels and control state were verified through the DOM, the accessibility tree and WebGL readback, not by looking at an image |

## Backend

| Claim | Status | Evidence |
| --- | --- | --- |
| Health and readiness respond | **VERIFIED** | `GET /health` 200, `GET /ready` 200 |
| All nine providers report their real state | **VERIFIED** | `vector=local`, `graph=local`, `cache=memory`, `storage=local`, `sparse=bm25_sql` (42 chunks), `embedding=BAAI/bge-small-en-v1.5`, `reranker=cross_encoder`, `llm=openai_compatible` unavailable, `vision` unavailable |
| The search endpoint returns hits in every mode | **VERIFIED (was BROKEN)** | `dense` 5 hits `matched_by=['dense']`; `sparse` 5 hits `['sparse']`; `hybrid` 5 hits `['dense','sparse']` with steps `dense_search, sparse_search, fusion, authorization_filter, rerank` |
| Search honours a real metadata constraint | **VERIFIED** | `filters.document_types=['contract']` returns 5 hits, all `document_type=contract` |
| UI flags no longer behave as exact-match filters | **VERIFIED (was BROKEN)** | `include_synthetic: true` no longer zeroes the result set; `retrieval_filter_payload` translates only genuine constraints |
| Comparison answers name both suppliers | **VERIFIED (was BROKEN)** | Live Q3 lead: `Northwind Industrial Supplies Ltd: USD 874.00, MOQ 100, effective 2026-01-01, Amendment 2 … [4]` and `Helios Technology Partners Inc: USD 895.00, MOQ 250, effective 2024-03-01 … [1]` |
| Lowest-price-2025 answers are clean | **VERIFIED (was BROKEN)** | Live Q4 lead: `The lowest recorded unit price for Industrial Laptop X200 for 2025-01-01 to 2025-12-31 is USD 895.00, recorded for Helios Technology Partners Inc, effective 2024-03-01 (supplier_b_supply_agreement_HTP-2024-014.pdf, p.1) [3].` No `procurement_value` or `unit_price_average` noise |
| The answer body starts with the answer | **VERIFIED (was noise)** | The `Extractive summary — …` preamble and the duplicated `Evidence` / `Verification` tails are gone from the body; the mode and the counts travel in `generation_mode`, `notes`, `citations` and `validation` |
| Aggregate rows are rendered readably | **VERIFIED** | `lowest_price_supplier [supplier=Helios Technology Partners Inc, product=Industrial Laptop X200, document=…]` instead of a Python dict repr; identifier keys are dropped |
| No answer claims a specific database engine it may not use | **VERIFIED (was BROKEN)** | Provenance reads `Structured findings (from the workspace database)`; `postgresql` no longer appears in answer, routing reason, retriever detail or comparison notes |
| Refusal body is a statement plus a readable reason | **VERIFIED** | Live Q6: `I couldn't verify this from the available procurement documents.` + `Why: The corpus holds no evidence for the entities or period asked about (supplier=Orion Components Co — …; period=2030-01-01 to 2030-12-31 — …)`. The raw sufficiency dict is no longer printed |
| A failed rerank reports its candidates rather than zero | **VERIFIED (was misleading)** | `retrieval/retriever.py` now sets `candidates=len(chunks)` on failure with the detail naming the failure and stating the order is fused, not cross-encoded |
| Python sources compile | **VERIFIED** | `python -m compileall` on the changed modules: clean |
| Automated tests | **NOT IMPLEMENTED** | The repository still contains no test files (`tests/` absent, no pytest/vitest/playwright specs). Everything in this section is end-to-end or in-process evidence, not a regression suite |

## RAG

| Claim | Status | Evidence |
| --- | --- | --- |
| Hybrid retrieval reaches the corpus | **VERIFIED** | dense 42 candidates, BM25 21–32, fusion 42, 42 authorised, 5 returned; warm dense search 524 ms, hybrid with rerank 2,164 ms |
| Cross-encoder reranking changes the order | **VERIFIED** | In-process `rank()` on 3 candidates returned order `[0, 2, 1]` with scores `[0.9984, 0.0, 0.0]` in 42–215 ms; server-side rerank reports `cross-encoder reranking with cross_encoder` over 42 candidates |
| GraphRAG traverses and returns a real path | **VERIFIED** | Trace event `graph | 2 path(s), up to 3 hops`; seeded question with a named supplier: `1 path(s), up to 3 hops` in 4,531 ms. (Earlier "graph never fires" readings were a harness detection error: the graph node reports as a trace event, not a retrieval step) |
| Every citation resolves to a page, chunk and image | **VERIFIED** | 32 citation pages checked across 8 answers, 0 problems; each cited chunk id found in its document; page images returned as real PNGs |
| A rasterised, image-only page is readable and searchable | **VERIFIED** | Probe PNG ingested (`status=indexed`, 1 page) in 2,166 ms; OCR text contains `777`; the document is retrievable from `/search` (10 hits for `Verification Probe`, 1 from that document); probe deleted afterwards |
| CSV and XLSX ingestion | **VERIFIED** | Both uploaded, indexed, chunks persisted (1 and 2) and retrievable; probes deleted afterwards |
| Unanswerable questions are refused | **VERIFIED** | Q6 `status=insufficient_evidence` with a coverage reason naming the missing supplier and period |
| Conflicting prices are surfaced with both values and which governs | **VERIFIED** | Q1 states `2 different agreed unit prices … USD 920.00 from 2024-01-01; USD 874.00 from 2026-01-01 per Amendment 2` and `the later terms govern from that date` |
| OCR engine loads and reads a rasterised page | **VERIFIED** | `paddleocr`, `available=True`, 2 lines, `PO-9981` recovered from a rendered page |
| Rerank availability under GPU contention | **PARTIALLY VERIFIED** | A real `CUDA error: unknown error` was recorded in the server log when a second process loaded models on the same GPU. The pipeline degraded correctly (`reranker failed (RuntimeError); fused order retained`) and answered from the fused order; after the API restarted, the same query reranked normally (`candidates 42`, `cross-encoder reranking`). The failure mode is graceful; the underlying contention is environmental |

## Models

| Claim | Status | Evidence |
| --- | --- | --- |
| Embedding model loads on GPU and embeds single and batch inputs | **VERIFIED** | `BAAI/bge-small-en-v1.5`, device `cuda`, dimension 384; single query 19,063 ms on a cold load (weights) and batch of 3 at 27 ms warm |
| Intended embedding model (`BAAI/bge-m3`, 1024-d) is what runs | **NOT CONFIGURED** | `.env.example` intends `BAAI/bge-m3`; the running system serves 384-d vectors from `bge-small-en-v1.5`. Recorded as PARTIALLY VERIFIED in the harness rather than claimed as bge-m3 |
| Reranker model | **VERIFIED** | `BAAI/bge-reranker-v2-m3`, device `cuda` |
| OCR model | **VERIFIED** | `paddleocr`, language `en`, loaded on demand (`.status()` truthfully reports `available=false, "not loaded yet"` before loading) |
| LLM answer generation | **NOT CONFIGURED** | `LLM_BASE_URL` and `LLM_MODEL` unset; provider detail `model=None`. All candidate local endpoints closed: `127.0.0.1:11434 open=False`, `127.0.0.1:8001 open=False`, `127.0.0.1:8080 open=False` |
| VLM page understanding | **NOT CONFIGURED** | `VLM_BASE_URL` / `VLM_API_KEY` unset; `vision` provider reports unavailable and vision steps report `Visual analysis unavailable` |
| Intended models per `.env.example` (Qwen3-30B-A3B-Instruct-2507, Qwen3-VL-30B-A3B-Instruct) | **NOT CONFIGURED** | No endpoint reachable, so neither model could be loaded or exercised |
| LLM grounding judge | **NOT VERIFIED** | With no endpoint, grounding falls back to `lexical_overlap` (`claim_check_method: "lexical_overlap"`). The judge code path exists but has never executed against a model |
| Token accounting | **NOT VERIFIED** | `token_usage` is empty (`not recorded`) because no model call is made |
| Generation mode currently in force | **VERIFIED** | `generation_mode=extractive`, `degraded=true`, and the platform states this on screen instead of implying model generation |

## Infrastructure

| Claim | Status | Evidence |
| --- | --- | --- |
| `docker compose config` (default services) is valid | **VERIFIED** | Exits 0; the eight services resolve |
| `docker compose --profile app` configuration resolves | **NOT VERIFIED** | `env_file: .env` is required and `.env` does not exist, so compose reports `env file …\.env not found`. This is the documented setup step, not a defect, but it means the app profile was never validated in its final form |
| The API image builds | **NOT VERIFIED** | `docker info` fails: `open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`. The Docker daemon is not running, so no image was built and no container started |
| The missing backend Dockerfile (audit C1, §46.1, §49) | **FIXED (unbuilt)** | `backend/Dockerfile` added: `python:3.12-slim`, installs `/app/backend[ocr]` from `pyproject.toml`, copies `app/`, `alembic.ini` and `alembic/`, exposes 8000, health-checks `/api/v1/health`, and runs `alembic upgrade head && uvicorn app.main:app`. The build could not be executed here |
| The compose database DSN (audit C3, §46.2) | **FIXED (unverified)** | `DATABASE_URL` changed from `postgresql+psycopg://…` to `postgresql+asyncpg://epi:epi@postgres:5432/epi`, matching the driver declared in `backend/pyproject.toml`. No live connection was made |
| Local runtime state | **VERIFIED** | `vector=local` (collection `procurement_chunks`, 42 points), `graph=local` (SQLite `backend/var/graph.db`, 103 nodes / 192 edges: Supplier 3, Contract 3, Product 7, Price 66, Document 9, ComplianceCertificate 18), `cache=memory`, `storage=local`, `sparse=bm25_sql` (42 chunks) |
| Qdrant, Neo4j, Redis, MinIO, Postgres adapters exercised live | **NOT VERIFIED** | No service could be started without the daemon; these remain code paths with unit-level coverage only |
| Worker service in compose | **NOT IMPLEMENTED** | Ingestion still runs in-process in the API; compose defines no worker |
| CI | **NOT IMPLEMENTED** | No workflow files exist |

## Security

| Claim | Status | Evidence |
| --- | --- | --- |
| Authentication works and rejects wrong credentials | **VERIFIED** | Valid login 200; wrong password 401 with `UNAUTHENTICATED` |
| Protected routes require a valid token | **VERIFIED** | No token 401; forged token 401; `/auth/me` and `/auth/roles` return the caller's role and permissions |
| Document page images require a token | **VERIFIED** | Authorised fetch returns a real PNG; anonymous fetch returns 401 |
| Retrieved instruction text is not obeyed | **VERIFIED** | Q7 produced a normal evidence-based answer with `status=conflicting`; no system prompt or secret appears in any response; the detector flagged the passage with score 1.0 and five pattern families |
| Flagged passages are marked for the reader | **VERIFIED (was H8)** | The detector's report now travels on the citation (`injection: {score, patterns, suspicious}`) and the interface shows `UNTRUSTED DOCUMENT CONTENT`, stating that the text was retrieved and never executed |
| Prompt-injection defence against a real language model | **NOT VERIFIED** | With no LLM configured there is no model to influence; the guardrail's containment (evidence delimiters + system note) has never been exercised against a model |
| Tenant and access-level filtering | **PARTIALLY VERIFIED** | Enforced and observed on the audited paths (retrieval authorisation step, page images); not proven across all routes |
| Security defaults safe for a real deployment | **STILL OPEN** | Default `dev-insecure-change-me` secret, self-registration enabled, no malware scanning, rate limiting configured but not demonstrably enforced. Unchanged from the earlier audit |
| Audit logging coverage | **STILL OPEN** | Only a handful of actions are recorded; no change was made |

## Visual-Product

The 3D layer exists to explain procurement structure, not to decorate. Two scenes are integrated, both driven by real data or by the product's own vocabulary, both lazy-loaded behind `React.lazy`, and both switchable off with a written equivalent.

| Claim | Status | Evidence |
| --- | --- | --- |
| Landing scene renders (documents → cited passage → answer) | **VERIFIED** | Canvas 1102×300 with a live `WebGL 2.0 (OpenGL ES 3.0 Chromium)` context; the five DOM labels `Master contract`, `Amendment`, `Pricing schedule`, `Cited passage`, `Answer` are present; no figures are shown |
| Relationship scene renders real traversal data | **VERIFIED** | Selecting `Northwind Industrial Supplies Ltd` on `/graph` produced a 798×420 WebGL 2.0 canvas labelled `Relationship neighbourhood of Northwind Industrial Supplies Ltd drawn as 68 record(s) and 153 connection(s)`; nodes are positioned by record type and labelled from the API |
| Selecting a record in 3D re-centres the traversal | **VERIFIED** | Node `onClick` calls the same `graphPaths` mutation as the list, writing the selection back to the page state |
| Reduced motion is respected | **VERIFIED** | With `prefers-reduced-motion` reported as true, the caption shows `Animation off — reduced motion`, the rotation control disappears and the scene renders a single static frame |
| Automatic motion is user-controllable | **VERIFIED** | `Pause rotation` flips to `Resume rotation` and stops the loop (frameloop drops to `demand`); `Hide 3D` removes the canvas and shows the text equivalent, and `Show 3D` restores it |
| Colours come from the design tokens | **VERIFIED** | `components/three/palette.ts` reads `--primary`, `--foreground`, `--muted`, `--border`, `--success`, `--warning` from the computed document style and converts them to scene colours |
| No purple, no gradients, no glow, no second brand colour | **VERIFIED** | Repository search for `gradient`, `purple`, `violet`, `fuchsia`, `indigo-`, `bg-clip-text` over `frontend/src` returns one match: the comment in `index.css` that forbids them |
| The 3D layer carries a text alternative | **VERIFIED** | Each scene is a `figure` with a caption and a `role="img"` description; `Hide 3D` shows an ordered list describing the same structure, and the graph table lists the same connections |
| Screenshots / visual regression | **NOT VERIFIED** | The preview webview produced no composited frames (`it produced no frames`), so appearance was verified through the DOM, the accessibility tree and WebGL properties. This is a limitation of the environment, and it is why no appearance claim here rests on a picture |
| Dark theme | **NOT IMPLEMENTED** | Dark tokens exist in `index.css` but no switch is exposed; the product ships light-first |

## Remaining Issues

1. **Docker path is written but unproven (PARTIALLY FIXED).** The Dockerfile exists and the DSN is corrected, but the daemon is not running, so no image was built, no container started, and no adapter (Postgres, Qdrant, Neo4j, Redis, MinIO) was exercised. Everything about the container path is currently a code claim.
2. **No language model, no vision model (NOT CONFIGURED).** Generation stays extractive, grounding stays lexical, token accounting is empty, and the injection guardrail has never faced a model. Pointing `LLM_BASE_URL`/`LLM_MODEL` and `VLM_*` at a reachable endpoint is the single highest-value unblock.
3. **Embedding model drift (PARTIALLY FIXED / NOT CONFIGURED).** The system runs `bge-small-en-v1.5` at 384 dimensions while `.env.example` intends `bge-m3` at 1024. Answer quality and comparability with the documented configuration suffer; the mismatch is now measured and recorded rather than implied.
4. **Reranker depends on a contended GPU (PARTIALLY FIXED).** A real CUDA error was observed when two processes loaded models on the same device. The platform degraded correctly and recovered after restart, but on a shared GPU the cross-encoder tier can silently drop out of the pipeline for a query.
5. **Temporal status semantics (PARTIALLY FIXED).** Q1 now leads with which value governs and why, but the status remains `CONFLICTING EVIDENCE` because the corpus does genuinely hold two agreed prices. Collapsing a resolved supersession to `SUPPORTED` would require the verification layer to treat the conflict as settled, which it does not yet do.
6. **Zero automated tests (NOT IMPLEMENTED).** No unit, integration, security or end-to-end suites exist. The evidence in this section is the only regression safety net, and it must be re-run by hand after every change.
7. **Ingestion blocks the request path (STILL OPEN).** Uploads are parsed, OCR'd and embedded inside the API process and no worker service exists in compose; a cold model load stalled an interactive search for minutes on this machine.
8. **Security defaults (STILL OPEN).** Default JWT secret, open self-registration, no upload malware scanning, unenforced rate limits, and narrow audit coverage.
9. **Nothing was verified about a real LLM's prompt-injection behaviour (NOT VERIFIED).** The detector, the delimiters and the system note are in place; their effectiveness against an actual model is untested.
10. **Accessibility and appearance are only partly verified (PARTIALLY VERIFIED).** No accessibility runner was executed, and the environment cannot capture screenshots. Keyboard reachability, labels and alternatives were checked by inspection and DOM reads.
11. **Documentation still absent (STILL OPEN).** No `README.md`, no `docs/`, no `data/README.md`; the deployment path has no written procedure.
12. **Unchanged carry-overs.** Conversation management is read-only, there are no exports, `npm run lint` still cannot run for lack of a configuration, 19 API endpoints and 9 client methods remain without a consumer, and the evaluation bundle stays heavy at 397 kB.

# Business Workspace Restructuring (implemented 2 October 2026)

This section records the procurement-workspace restructuring: role separation between the
business workspace and administration, a real document-management area with persisted metadata
editing and version handling, and business language on the default surfaces. It re-uses the
current architecture, the current model configuration, the current database and the current
retrieval pipeline. No model, provider or framework was added, replaced or removed.

## What changed

| Area | Change | Status |
| --- | --- | --- |
| Navigation | Sections are `Workspace` (Overview, Ask, Search, Documents, Contracts, Suppliers, Compare), `Analysis` (Relationships) and `Administration` (Administration, Search quality) | **VERIFIED** |
| Role separation | `/dashboard` is readable by every signed-in account; `/admin` requires `admin:write`; Administration and Search quality are absent from a buyer's navigation | **VERIFIED** |
| Overview | Rebuilt around business figures (documents, active contracts, suppliers, expiring within 90 days, needs attention, still processing), recently updated documents, contracts and recent activity for accounts holding `audit:read` | **VERIFIED** |
| Documents list | Enterprise table: Document, Type, Supplier, Status, Version, Effective, Expiry, Last updated, Actions, with sortable columns, business status filter, type/supplier filters and a metadata-complete upload form | **VERIFIED** |
| Document detail | Document information, version history, page viewer, evidence on the page, related supplier and contract, and processing details behind a disclosure | **VERIFIED** |
| Metadata editing | `PATCH /api/v1/documents/{id}` persists title, type, supplier, contract, effective date, expiry date, access level and revision label; the edit is written to the document's own history and to the audit log | **VERIFIED** |
| Version handling | Uploading a replacement links the replaced row to its successor via the stored `superseded_by_id`; the successor becomes the next version and the earlier version keeps its pages and citations | **VERIFIED** |
| Version history API | `GET /api/v1/documents/{id}/versions` walks the stored chain and flags the governing version | **VERIFIED** |
| Search | Default view shows document, page, section, passage, supplier, contract, term and `Open source`; strategy, counts, timings, models and per-passage scores moved behind `Search details` | **VERIFIED** |
| Compare | Explicit product → select suppliers → selected list → compare workflow, with the selected set always shown; no ranking and no winner | **VERIFIED** |
| Suppliers | List and detail lead with contracts, documents, pricing, compliance and relationships; aliases moved to secondary text | **VERIFIED** |
| Administration | Six task areas: Overview, Documents & governance, Users & access, Search & answer quality, Activity, System health & configuration | **VERIFIED** |
| Access model | `GET /api/v1/admin/access-model` reports the roles, permissions and access ceilings the API enforces, read from the policy itself | **VERIFIED** |
| Ask | Answer states unchanged (SUPPORTED / CONFLICTING EVIDENCE / PARTIAL EVIDENCE / UNABLE TO VERIFY); the conflict block is now labelled as the reason the answer reads as it does; technical details stay collapsed | **VERIFIED** |
| Relationships | Unchanged, still driven by the stored graph (110 nodes / 192 edges live) and still mounted through the existing 3D system | **VERIFIED** |
| Read-only roles | A buyer no longer sees the upload control on Documents; the page states read-only access instead. Previously it showed an action that would have returned 403 | **VERIFIED (was BROKEN)** |
| DOM correctness | Invalid `div`-inside-`p` nesting in the document table removed; `Badge` forwards its ref so it can be used as a Radix trigger child without a React warning | **VERIFIED (was BROKEN)** |

## Routes changed

| Route | Change |
| --- | --- |
| `/dashboard` | Permission gate removed (any signed-in account); page rebuilt as the business overview |
| `/admin` | Gate raised from `admin:read` to `admin:write`; page reorganised into six task areas |
| `/evaluation` | Navigated to as `Search quality` from the Administration section; route and permission unchanged |
| `/documents` | Rebuilt as the repository table with metadata upload |
| `/documents/:id` | Rebuilt as the document workspace with editing, version history and disclosures |
| `/search` | Default view is business-facing; retrieval internals behind `Search details` |
| `/compare` | Selection workflow rebuilt; no ranking language |
| `/suppliers`, `/suppliers/:id` | Business-first ordering and wording |
| `/ask` | Unchanged routes and states; conflict block relabelled |
| `/graph`, `/contracts`, `/contracts/:id` | Unchanged |

## APIs reused and added

**Reused without change:** `GET /documents`, `GET /documents/{id}`, `GET /documents/{id}/chunks`,
`GET /documents/{id}/pages/{n}`, `GET /documents/{id}/pages/{n}/image`, `POST /documents/upload`,
`POST /documents/{id}/index`, `DELETE /documents/{id}`, `GET /documents/limits`, `GET /suppliers`,
`GET /suppliers/{id}`, `GET /contracts`, `GET /contracts/{id}`, `GET /compliance`, `POST /compare`,
`POST /search`, `GET /filters`, `POST /query`, `POST /query/stream`, `GET /conversations*`,
`GET /graph/overview`, `GET /graph/nodes`, `GET /graph/paths`, `GET /admin/stats`, `GET /admin/indexing`,
`GET /admin/config`, `GET /admin/routing`, `GET /admin/audit`, `GET /admin/traces`, `GET /auth/me`,
`GET /health`.

**Added (smallest compatible change):**

1. `PATCH /api/v1/documents/{id}` — metadata update. Requires `documents:write`, validates the document
type against `DOCUMENT_TYPES`, the access level against `ACCESS_LEVELS` **and** the caller's ceiling,
the supplier and contract against the tenant, and the date order. Records a before/after diff under the
new `document.update` audit action and appends an entry to the document's own metadata history.
2. `GET /api/v1/documents/{id}/versions` — version history from the stored `superseded_by_id` chain,
flagged `is_current`. The chain is never inferred from filenames or titles.
3. `GET /api/v1/admin/access-model` — roles, permissions, access ceilings and document access levels,
read from `ROLE_PERMISSIONS` / `ROLE_ACCESS_CEILING` / `ACCESS_LEVELS`. Requires `admin:read`.
4. `POST /documents/upload` gained the optional form field `replaces_document_id`. When present the
uploaded file becomes the next version and the replaced row is linked to it; uploading the identical
file still returns the existing document instead of creating a version.
5. Additive response fields only: `superseded_by_id`, `supplier_name`, `contract_number` on document
summaries and `uploaded_by_name` on the detail. No field was removed or renamed.

## Verification evidence

| Check | Result | Evidence |
| --- | --- | --- |
| TypeScript | clean | `npx tsc --noEmit`, no output |
| Production build | clean | `npm run build` in 9.88 s; pages remain code-split (`DocumentsPage` 15.81 kB, `DocumentDetailPage` 32.03 kB, `AdminPage` 22.80 kB, `DashboardPage` 12.48 kB) with the 3D layer still in its own `SceneFrame` chunk |
| Backend compiles and routes register | clean | `python -m compileall` on the changed modules; `app.routes` lists `/api/v1/documents/{document_id}/versions` and `/api/v1/admin/access-model` |
| Document management end-to-end | 29/29 | `python scripts/verify_documents.py` (new harness) — upload, metadata update, re-read, history entry, 4 validation rejections, version chain, list joins, cleanup |
| Role enforcement | passed | Same harness as a `buyer` account: `PATCH` 403, `upload` 403, `GET /admin/stats` 403, document read 200 |
| Metadata editing through the interface | passed | Admin signed in, `Edit details` used to set type `contract`, supplier `Helios Technology Partners Inc`, effective `2026-01-01`, revision `browser-verified`; the dialog showed `Details saved`, the header re-rendered from the API, and `GET /documents/{id}` returned `contract / Helios Technology Partners Inc / 2026-01-01 / browser-verified` with one `metadata_edits` entry and a `document.update` row in the audit log |
| Business status derivation | passed | Documents list showed `Active`, `Expired` and `Not available` derived from the recorded dates and processing state, with the basis exposed as a title attribute |
| Search default view | passed | `unit price laptop` returned 10 passages showing document, page, section, passage, supplier, contract, term and `Open source`, with no occurrence of `cross-encoder`, `reciprocal rank fusion`, `BM25`, `BGE` or `embedding` outside the collapsed `Search details` |
| Compare workflow | passed | Selected two suppliers by name; the page read `2 suppliers selected`, listed exactly those two under `Selected for this comparison`, enabled `Compare selected suppliers` and rendered the dimension table with 20 citation links and no ranking |
| Administration | passed | Six task tabs render; `Users & access` lists 5 roles with ceilings and permission counts (admin 16, procurement_manager 14, compliance 8, buyer 6, viewer 4) and states that no user-administration API is exposed |
| Non-admin role | passed | In an isolated browser context the buyer saw `Overview, Ask, Search, Documents, Contracts, Suppliers, Compare`, read-only document access, an overview built from documents/contracts/suppliers, and `This page is not available to your role — Missing permission: admin:write` at `/admin` |
| Relationships | passed | Graph overview reported `local`, 110 nodes / 192 edges; selecting Northwind mounted an 830×420 WebGL 2.0 canvas with the existing `Pause rotation` / `Hide 3D` controls |
| Console | clean | After the fixes above, no React warnings and no failed requests on the walked routes. Two 404s seen once were the deliberate fetch of a document deleted during cleanup — expected, and the page rendered its error state |
| Model actually in use | unchanged | `embedding=BAAI/bge-small-en-v1.5` (384-d, cuda), `reranker=cross_encoder BAAI/bge-reranker-v2-m3`, `ocr=paddleocr`, `llm=openai_compatible` **not configured**, `vision` **not configured**; generation stays `extractive` and `degraded=true`. No model was added or replaced |

## Status of the questions the brief asks to answer

| Question | Status | Detail |
| --- | --- | --- |
| What changed | see the table above | Navigation, Overview, Documents, document detail, Search, Compare, Suppliers, Administration, plus three backend additions |
| Which routes changed | see the table above | `/dashboard`, `/admin`, `/documents`, `/documents/:id`, `/search`, `/compare`, `/suppliers*` |
| Which document-management capabilities were added | **VERIFIED** | Repository table with derived business status, metadata-complete upload, persisted metadata editing, version upload with preserved predecessors, version history, processing status in business words behind a disclosure |
| Which APIs were reused | **VERIFIED** | 31 endpoints, listed above; no retrieval, ingestion or auth endpoint was modified |
| Which APIs were added | **VERIFIED** | `PATCH /documents/{id}`, `GET /documents/{id}/versions`, `GET /admin/access-model`, `replaces_document_id` upload field, additive response fields |
| Which features were verified | **VERIFIED** | Everything in the evidence table above, against the live API and the live database |
| Which features remain partial | **PARTIALLY VERIFIED** | Multi-version history rendering in the interface (single-version panel verified in the UI; the two-version chain was verified through the API); the new-version dialog renders and calls the verified endpoint, but the file-picker interaction itself could not be driven by the available browser tooling |
| Which features remain unavailable | **NOT IMPLEMENTED** | Archive (the status vocabulary contains `archived` but nothing sets it and no admin action is exposed); retention or legal-hold policy; user administration (no endpoint lists, edits or deletes accounts); per-document ACL grants; contract redlining / wording editing — deliberately not faked |
| Which model is actually being used | **VERIFIED (unchanged)** | `BAAI/bge-small-en-v1.5` embeddings, `BAAI/bge-reranker-v2-m3` cross-encoder, PaddleOCR; no answer model |
| Whether the model is configured | **NOT CONFIGURED** | `LLM_*` and `VLM_*` are unset; the interface states this rather than implying a model is in the loop |
| Whether document metadata editing is verified | **VERIFIED** | Through the interface and through `scripts/verify_documents.py`; persisted, re-read, recorded in the document history and in the audit log |
| Whether version handling is verified | **VERIFIED** | Replacement marks the predecessor superseded, the successor becomes the next version, the predecessor keeps its pages and citations, and the chain is reported oldest-first with the governing version flagged. Identical files are refused as versions because they are the same document |
| Whether citation deep-linking is verified | **VERIFIED** | 30 citation links on a live answer, resolving to `/documents/{id}?page=n&chunk=m`; unchanged from the previous verification run |
| Whether permissions are verified | **VERIFIED** | Buyer 403s on edit/upload/admin, 200 on document read; buyer navigation has no Administration; `/admin` renders the access-denied page naming the missing permission |
| Whether the 3D experience is verified | **VERIFIED** | Real graph data, WebGL 2.0 canvas, existing motion controls and reduced-motion behaviour; unchanged by this work |
| Whether production adapters are verified | **NOT VERIFIED** | Docker daemon still not running, so Postgres, Qdrant, Neo4j, Redis and MinIO remain unexercised |
| Whether automated tests exist | **NOT IMPLEMENTED** | No unit, integration or end-to-end suite; `scripts/verify_documents.py` is a harness, not a test suite |
| Whether Docker deployment is verified | **NOT VERIFIED** | `backend/Dockerfile` and the corrected asyncpg DSN exist; no image was built and no container was started |

## Side effects of this verification run

1. One account was created for role verification: `buyer@epi.local` (role `buyer`, name
   `Buyer verification account`). It is a real account in the tenant; delete or change its password if it
   is not wanted. The harness `scripts/verify_documents.py` documents how to recreate it.
2. Four ingestion-job rows remain from probe documents that were deleted mid-processing (`FAILED` in the
   Administration ingestion queue). The documents, pages, sections and index entries were removed with
   them; the job rows are append-only history and have no API to delete them.
3. Every document created for verification was deleted afterwards; the corpus is back to its 9 original
   documents. No demo-corpus record was modified by the interface test: the interactive edit ran against a
   throwaway upload.
4. One conversation (`What is Supplier A's current price…`) was recorded on the Ask page to verify the
   answer hierarchy, and one `document.update` entry exists in the audit log.





---

# Frontend Visual Redesign — 3D and Playful Enterprise (implemented 4 October 2026)

Frontend-only work. No backend logic, API contract, RBAC rule or procurement semantic was changed,
with one exception recorded under "Defects found and fixed" below: a response schema that could not
serialise rows the database already contained.

## What changed

### 3D surfaces

| Surface | What it is now | Data source |
| --- | --- | --- |
| Overview "Procurement ecosystem" | A five-column chain (Supplier → Contract → Product → Price → Evidence) plus compliance and amendment satellites. Nodes drift slowly, links are hairline tubes, hovering lights a record and its neighbours and shows a business tooltip, selecting opens the record. | `GET /suppliers`, `/contracts`, `/prices`, `/compliance`, `/documents` — the same endpoints the tables below the scene use |
| Relationships ("Relationship neighbourhood") | Orbit, zoom and pan; hovering a record lifts it and dims everything not connected to it by a real edge; selecting re-centres the traversal; a legend names each record type and its colour; "Pause motion", "Reset view" and "Hide 3D" controls; the connection table remains the text equivalent. | `GET /graph/paths` (unchanged) |
| Landing hero | Unchanged scene, now framed with orbit/zoom/pause/reset wording and an explicit statement that it is a schematic and is not loaded on a small screen or without WebGL. | Static schematic (unchanged) |

### Documents

- The document table sits on a two-sheet CSS stack (`.stack-layers`) as a metaphor for versions; the
  document detail version history uses the same device, with the governing version marked current.
- The page viewer is a raised sheet (`.page-sheet`); changing page plays a 320 ms rise keyed on the page
  number, and the rendered page image is captioned with its own page number.
- Selecting a citation animates the cited passage into place with a 420 ms highlight. The passage itself
  is shown in full and stays readable; the animation only draws the eye to it.

### Ask, Search, Compare

- Ask: a business stage strip ("12 passages read → 6 citations verified → the outcome") with a slow
  ambient pulse, pipeline copy in the reader's language while running, and one line of personality
  chosen by the outcome the pipeline reported.
- Search: results rise in with a 28 ms stagger; the empty state uses the product's voice.
- Compare: a chosen supplier lifts by 2 px with a shadow. Selection is never a ranking, and the readiness
  line says so.

### Microcopy

One module, `frontend/src/lib/microcopy.ts`, holds every line together with the plain sentence it
decorates, so a playful line cannot ship without the statement behind it. Lines in use: "Digging through
the paperwork…", "Yep. Found it.", "Uh… these documents disagree.", "I checked the available documents.
They don't actually say.", "Nothing here. The documents are innocent.", "Pick at least two suppliers and
we'll compare them.", "The shelf is empty.", "One version so far. Nothing to stack yet."

### Motion and performance

- UI durations 120 / 180 / 240 / 300–500 ms as specified; the only ambient loops are the 3D scenes and
  one 4.8 s pulse on the evidence strip.
- 3D is split: the main bundle contains no three.js (`THREE.WebGLRenderer` appears 0 times in the main
  chunk). The 850.20 kB three.js/drei chunk is fetched only when a scene renders.
- Device pixel ratio is capped (1.75 desktop, 1.25 below 1280 px), geometry segment counts drop below
  1280 px, no canvas is created below 768 px, and a browser without WebGL gets the written alternative.

### Defects found and fixed while verifying

1. **`GET /prices` returned 500 for the whole endpoint.** 18 of 69 stored price rows have a null
   `supplier_id` (a pricing schedule that names no party), but `PriceOut.supplier_id` was declared
   non-nullable, so Pydantic rejected the row and the request failed. One field was widened to
   `str | None` in `backend/app/schemas/procurement.py`, matching the sibling `ComplianceOut` and
   `ContractOut` treatment and the database. No logic, query or semantic changed; the endpoint now
   returns all 69 rows.
2. **Every entity link on the Relationships page resolved to "no page".** `isUuid()` required a
   hyphenated UUID, but this deployment keys records as `sup_2f01…`, so the guard rejected every real
   identifier and neither the table links nor the 3D nodes could open a record. Replaced with
   `isRecordId()`, which accepts the format the deployment actually issues.
3. **Horizontal overflow at a 390 px viewport.** The dashboard's table cards are grid items with
   `min-width: auto`, so a table's min-content width widened the page to 490 px instead of scrolling
   inside its own container. `min-w-0` was added to the two grid items; the page fits at 374 px now.
4. **Table headers rendered inconsistently.** Sortable headers were plain-case and muted while plain
   headers were uppercased; both render identically now.
5. **The Search quality page was titled "Evaluation" while the navigation said "Search quality".** The
   page title now matches the navigation.

## Verification evidence

| Check | Result |
| --- | --- |
| `npx tsc --noEmit` | Clean, no output |
| `npm run build` | PASS in 8.70 s |
| `npm run lint` | **CANNOT RUN** — `eslint` is not installed (no binary, no config). Not caused by this work; reported rather than papered over |
| Route walk | All 15 routes plus the public pages rendered with 0 alerts and no horizontal overflow at 1440×900, 1024×800 and 390×844 |
| Console | Clean on every route: only Vite's connect messages and the React DevTools hint |
| Overview scene | Real canvas 1117×360; aria label carries the real per-tier counts; legend and controls present; text alternative reads `3 supplier`, `3 contract`, `10 product`, `69 price (10 drawn)`, `9 evidence` |
| Relationships scene | 68 records / 153 connections drawn for Northwind within 2 hops; canvas 798×460; legend names all six record types |
| Frame timing, Overview | 400 frames, 165.2 fps, p95 6.20 ms, longest frame 6.50 ms |
| Frame timing, Relationships during 6 s of continuous hover | 400 frames, 165.2 fps, 0 frames over 33 ms, 0 long tasks, JS heap 47 MB |
| Ask microcopy (conflict) | Live query returned `CONFLICTING EVIDENCE`; "Uh… these documents disagree." rendered with its plain sentence beside it |
| Ask microcopy (unsupported) | Live query returned insufficient evidence; "I checked the available documents. They don't actually say." rendered with "No verified evidence was found for this question, so no answer is given." |
| Evidence flow strip | "12 passages read · 6 citations verified · Conflicting evidence", built from the answer's own counts |
| Citation deep link | `?page=1&chunk=chk_ece9d7e7…` — cited passage rendered with the 420 ms focus animation, opacity 1, full text visible |
| Documents stack | `.stack-layers` pseudo-elements present with the offset transform |
| Reduced motion | With `(prefers-reduced-motion: reduce)` forced, the scene reports "Animation off — reduced motion", the pause and reset controls are removed, and no UI animation runs |
| Mobile fallback | At 390 px no canvas is created ("3D is off on a small screen"), the written alternative with real counts renders, and WebGL remains available — the scene is off by choice, not by failure |
| Tablet tier | At 1024 px the canvas renders with the reduced-detail pixel-ratio cap and the full control set |
| Three.js split | `THREE.WebGLRenderer` appears 0 times in the main chunk and 5 times in the lazy `SceneFrame` chunk |

## Bundle impact

| Chunk | Size | Gzip | When fetched |
| --- | --- | --- | --- |
| `index` (main) | 471.95 kB | 146.86 kB | Always — about 5 kB raw / 0.9 kB gzip more than the pre-redesign build (≈467 kB) |
| `SceneFrame` (three.js + drei + frame) | 850.20 kB | 230.06 kB | Only when a 3D scene renders — 2.22 kB more than 847.98 kB |
| `EcosystemScene` | 4.30 kB | 2.08 kB | Only on the Overview, and only when the workspace holds supplier records |
| `GraphScene3D` | 4.55 kB | 2.30 kB | Only on Relationships after a traversal |
| `HeroEvidenceScene` | 2.65 kB | 1.11 kB | Only on the landing page |
| CSS | 38.39 kB | 7.60 kB | Always |

The initial bundle grew by about 6 kB raw (under 1 kB gzip) plus the CSS additions. three.js itself never
reaches a reader who does not open a 3D view.

## Status of what the brief asks to answer

| Question | Status | Evidence |
| --- | --- | --- |
| 3D supports the product rather than obstructing it | **VERIFIED** | Every 3D surface ships a written alternative, a "Hide 3D" control, and a text equivalent (the connection table, the tier counts) carrying the same information |
| Every 3D node is real data | **VERIFIED** | The Overview draws only rows returned by `/suppliers`, `/contracts`, `/prices`, `/compliance` and `/documents`; the Relationships scene draws only what `/graph/paths` returned |
| No fabricated counts or entities | **VERIFIED** | The scene's aria label and the text alternative both quote the API totals; capped tiers state how many of how many are drawn |
| Accessibility of 3D | **PARTIAL** | Every scene is a `role="img"` with a sentence naming its contents, the frame's controls are real buttons with pressed states, and reduced motion is honoured — but a keyboard user cannot orbit the canvas; the record list and connection table are the keyboard path |
| Responsive behaviour | **VERIFIED** | Full scene at 1440 px, reduced-detail scene at 1024 px, written alternative at 390 px |
| Reduced motion | **VERIFIED** | Scenes stop, ambient loops are killed by the stylesheet rule, and the frame says so on screen |
| Automated tests | **NOT IMPLEMENTED** | Still no test suite; verification was a browser walk plus direct API probes |
| `npm run lint` | **BROKEN** | eslint is not installed in `frontend/`; the script fails with "eslint is not recognized" |

## Side effects of this verification run

1. Ask conversations were created while verifying the answer states ("What is the current unit price for
   the Industrial Laptop X200?", "What was Supplier C's unit price for the Rack Server R4 in 2031?").
   They are stored, as designed, in the workspace's question history.
2. Synthetic pointer sequences were driven over the Relationships canvas for frame-timing evidence. They
   changed nothing on disk.
---

# Verification Pass — Persistent 3D World Layer

This section records a second, independent verification pass over the frontend redesign
described in the brief *Final frontend redesign + 3D experience implementation*. It was
performed after the first brief (*Frontend visual redesign — 3D + playful enterprise*) had
already been implemented and reported.

## Method

The preview webview of this workspace never composites: it reports
`document.visibilityState === "hidden"` permanently, requestAnimationFrame never ticks, and
neither `document.hidden` nor `document.visibilityState` can be redefined inside it. No
animation, frame-timing or trusted-input evidence can come from there.

All behaviour below was therefore measured in **real headless Chrome** driven over the
Chrome DevTools Protocol (`.freebuff/world-check.mjs`, a test tool that is not part of the
application): `--headless=new`, a 1440x900 window, `Page.setWebLifecycleState("active")` so
frames actually run, `Input.dispatchMouseEvent` / `Input.insertText` for trusted input,
`Emulation.setCPUThrottlingRate` for the quality ladder, `Emulation.setEmulatedMedia` for
reduced motion, and `Emulation.setDeviceMetricsOverride` for phone and tablet widths. The
backend was the real local API (`uvicorn app.main:app` on 127.0.0.1:8000) over the real
synthetic procurement corpus, and the frontend was the real Vite dev server.

## Defects found in this pass and fixed

Each of these was a regression introduced by the 3D work itself, and each was invisible to
the DOM-only checks that had been run previously.

### 1. The 3D canvas made the entire application unclickable

`WorldCanvas` wraps its `<Canvas>` in a `pointer-events-none fixed inset-0 z-10` overlay,
which is what keeps the world decorative. But `@react-three/fiber` writes
`pointerEvents: "auto"` onto **its own** wrapper element
(`react-three-fiber.esm.js`: `const pointerEvents = eventSource ? 'none' : 'auto'`), and a
used value of `auto` on an intermediate element overrides the `none` inherited from the
parent. The result was an invisible full-viewport surface above every page of the
authenticated application.

Measured before the fix, at the centre of the **Run query** button on `/ask`:
`document.elementFromPoint(610, 442)` returned `CANVAS`, and a trusted click there produced
`pointerdown:CANVAS`, `mousedown:CANVAS`, `click:CANVAS` — no form submit, no request. The
canvas covered the whole viewport, band included (viewport `1422x804`; overlay rect
`1422x804`; band at `y 77..207`).

Fix: pass `style={{ pointerEvents: "none" }}` to `<Canvas>`. r3f spreads a caller's `style`
after its own defaults, so this is the way to keep the render surface non-interactive. Bands
and scenes receive input through their own DOM elements and through r3f's `events.connect`
hand-off (`EventBridge`), never through the canvas.

Measured after the fix, same point: `elementFromPoint` returns the `BUTTON`; the click
produces `pointerdown:BUTTON`, `mousedown:BUTTON`, `click:BUTTON`, `submit:FORM`; the button
label flips to "Running"; and the backend logs `POST /api/v1/conversations` 200 followed by
`POST /api/v1/query/stream` 200.

### 2. The Courier never walked

`Courier` starts at `w.x = -halfSpan` and turns when it reaches a bound, but the bound test
checked **both** ends regardless of the direction of travel:

```
if (w.x > halfSpan - 45) { w.dir = -1; w.pause = PAUSE_SECONDS; }
else if (w.x < -halfSpan + 45) { w.dir = 1; w.pause = PAUSE_SECONDS; }
```

The spawn point sits inside the left margin (`-halfSpan < -halfSpan + 45`), so on the first
step out of every pause the second branch fired immediately: the courier reversed and paused
for another 2.4 s. It advanced exactly one frame (0.2 px) per pause cycle, about 0.1 px/s
instead of 33.4 px/s, and effectively stood at the left edge for the whole session.

Measured before the fix, sampling the published position every 250 ms for 5.85 s: total
travel **0.6 px**, while its suitcase tag's screen position did not change at all
(`tagLeft` constant at 311 across 24 samples). Instrumentation confirmed a single courier
instance whose `pause` counter reset to 2.4 s each time it reached zero.

Fix: turn only at the far end of the direction being walked
(`w.dir === 1 ? w.x > halfSpan - 45 : w.x < -halfSpan + 45`).

Measured after the fix: **195.9 px in 5.85 s, i.e. 33.4 px/s**, matching the designed
`(halfSpan * 2 - 90) / 28` — one crossing in 28 s, inside the brief's 20-40 s loop — and its
suitcase tag travelled 196 px with it, with its DOM node identity stable throughout.

### 3. The adaptive quality ladder could never fire

`FrameMeter` accumulates the `delta` that r3f passes to `useFrame`, which is in **seconds**,
and compared the rolling average directly against `FRAME_BUDGET_MS = 22` and
`FRAME_RECOVER_MS = 12`, which are milliseconds. The budget was therefore 22 *seconds* long:
no frame any machine can draw could miss it, so the downgrade branch was unreachable. The
recovery comparison was the mirror image — always true — but a no-op at the top tier, so the
defect produced no visible symptom.

Measured before the fix, under `Emulation.setCPUThrottlingRate(12)` for 16 s: median frame
interval **42-54 ms** against the 22 ms budget, the tier stayed `high` for all 16 samples,
and instrumented averages read 28.7 ms while `overSince` was never set.

Fix: convert once (`averageMs = (s.sum / s.frames) * 1000`) and compare in one unit. The
recovery floor was also made reachable on an ordinary display: headroom is now
`max(FRAME_RECOVER_MS, fastestFrameMs * 1.4)`, because a vsync-locked 60 Hz screen never
reports a frame below 16.7 ms and a fixed 12 ms floor made recovery impossible there. It
still requires `averageMs <= FRAME_BUDGET_MS`, so a machine that is genuinely too slow
cannot promote itself.

Measured after the fix, under the same throttling: `high` (paper 21 sheets) to `medium` after
about 2.5 s (paper **11** = `OBJECT_BUDGET.medium.paper 14 x 0.8`) to `low` (**6** = `7 x 0.8`)
to `static` (**0 canvases, 3 SVG elements** in the band, frame interval back to 6.1 ms). The
scene object counts are GL-side reads independent of React state, so the ladder is confirmed
by what was actually drawn, not only by a store value.

## Measurements from this pass

| Quantity | Value | How it was measured |
| --- | --- | --- |
| WebGL canvases in the authenticated app | **1** | `document.querySelectorAll('canvas')` on `/ask`, on every route, and in the no-WebGL run (0) |
| Canvas persists across routes | **yes, same DOM node** | `sameCanvasNode: true` for all 10 authenticated routes |
| Canvas size / backing store | 1422x804 CSS, 1422x804 backing, dpr 1 | canvas rect vs `canvas.width/height` on this dpr-1 host |
| WebGL context | WebGL 2.0 (OpenGL ES 3.0 Chromium) | context `VERSION` parameter |
| WebGL layer init | canvas inserted 431 ms after `responseEnd` (band DOM at 222 ms) | `MutationObserver` installed with `Page.addScriptToEvaluateOnNewDocument` |
| Frame time / FPS | avg **6.07 ms**, median 6.1 ms, p95 6.3 ms, **~165 fps** | 180 rAF intervals |
| Draw calls / clears | 4794.7 draws/s, 165.3 clears/s | patched `WebGL2RenderingContext.prototype` counters |
| Scene inventory | 1 scene, 27 meshes, 1 `InstancedMesh` with **21 instances** | scene-graph walk captured on `Object3D.prototype.updateMatrixWorld` |
| Cursor tracking latency | **90.1 ms** from trusted pointer event to the first frame with the pupil moved >1 px | pupil world x sampled per frame |
| Pupil travel | x -1.956 -> +4.076 (6.032 units) between two screen corners | trusted `Input.dispatchMouseEvent` |
| Blink cadence | min lid openness 0.099, 3 low-lid frames in 120 samples over 10 s | per-frame eye-scale samples |
| Idle doze | lid openness 0.06 after 40 s without movement | forced `lastMove`, then sampled |
| Keyboard focus gaze | pupil x 0.329 toward a focused control at normalised x 0.08 | focusin, then per-frame pupil sample |
| Courier walk | 33.4 px/s, one crossing in 28 s | published position sampled 24 times over 5.85 s |
| Courier click | stops (0 px during the pause), hat tips -49 deg, authored line shown | trusted click plus a 60 ms hat-rotation sampler |
| Watcher click | authored deadpan line in `[role=status]`, `isAuthoredLine: true` | trusted click |
| Paper flow | 21 instances, distinct lanes, all moving | `getMatrixAt` on the `InstancedMesh` before and after |
| Band pixels | 742-777 distinct colours at 1x, 10.9 % ink over the paper background, 0.6-0.8 % warm accents, 0.8-0.9 % navy ink; **9.7 % of pixels changed** between two crops 1.2 s apart | `Page.captureScreenshot` crops analysed with numpy/PIL |
| Reduced motion | courier 0 px, pupil x 0, paper 0 px, head rotZ 0 | emulated `prefers-reduced-motion: reduce` |
| Mobile 390x844 | 0 canvases, **3 SVG elements**, band 64 px, overflow 0 | `setDeviceMetricsOverride` |
| Tablet 1024x768 | 1 canvas, band 80 px, canvas dpr 1.5, overflow 0 | as above |
| Desktop 1440x900 | 1 canvas, band 96 px, dpr 1, overflow 0 | as above |
| Settings persistence | `epi-world` holds only `reduceEffects` and `hideBuddy`; after a real reload `aria-pressed` still reads `Hide buddy=true` | localStorage read, reload, aria read |
| No-WebGL run | 0 canvases, 3 SVG elements, real per-route suitcase labels, **0 console errors across 10 routes** | `--disable-webgl --disable-webgl2 --disable-3d-apis` |
| Accessibility tree | both controls exposed as `button`; **0 nodes with the canvas role**; 2 `image` nodes (the scene regions) | `Accessibility.getFullAXTree` |
| Initial bundle delta | **+4 878 B gzip** (146 812 -> 151 690 B), `gzip -9` on the entry chunk | two builds: with the world layer, and with its mount point and state bridge removed (restoring reproduced the identical entry hash) |
| Lazy 3D band chunk | `BandRegion-*.js` 14 411 B raw / **4 772 B gzip** | build output |
| three.js chunk | `palette-*.js` 858 078 B raw / 231 153 B gzip; absent from the baseline build entirely | build output; `WebGLRenderer` appears 0 times in the entry chunk |
| `npx tsc --noEmit` | **exit 0** | run after every source change |

## Status of the brief's acceptance criteria

| Requirement | Status | Evidence |
| --- | --- | --- |
| One persistent WebGL canvas | **VERIFIED** | exactly 1 canvas on every authenticated route, the same DOM node across all 10 |
| Scenes mount and unmount inside the shared renderer | **VERIFIED** | canvas node identity is unchanged as the band scene and the page scenes swap; route scenes are drei `View` regions scissored into that one framebuffer |
| Global Watcher: cursor tracking, blinks, idle doze, keyboard gaze | **VERIFIED** | 90.1 ms latency, 6.03 units of pupil travel, blinks inside a 10 s window, doze at 40 s, gaze on focus |
| Watcher reacts to real states | **VERIFIED** | driven through the real UI and the real pipeline: a `supported` answer moved brow 14.5 -> 17.9 and eye scale 0.95 -> 1.0; an `insufficient_evidence` refusal moved brow 14.5 -> 13.82 and eye scale 0.95 -> 0.46 |
| Courier with suitcase, 20-40 s loop | **VERIFIED after fix** | 33.4 px/s, 28 s crossing, suitcase label is a real collection per route |
| Courier click reaction | **VERIFIED** | stops, hat tips -49 deg, authored line shown |
| Instanced paper flow on curved paths | **VERIFIED** | 1 `InstancedMesh`, 21 instances, lanes differ, all moving |
| Route-aware scene registry | **VERIFIED** | per-route suitcase labels: Prices, Documents, Contracts, Suppliers, Evidence |
| Adaptive quality with downgrade | **VERIFIED after fix** | high -> medium -> low -> static under a 12x CPU throttle, confirmed by GL-side sheet counts and by the SVG fallback appearing |
| Pause when `document.visibilityState === "hidden"` | **NOT VERIFIED** | the lifecycle control used here keeps the page active, and the preview webview is permanently hidden so it cannot exercise the transition either. The code path exists (`useVisibility` -> `frameloop: "never"`), but no measurement was obtained. |
| Invalidate-on-demand when calm | **NOT VERIFIED** | same reason |
| Reduce effects / Hide buddy, persisted | **VERIFIED** | both controls act, both persist in `epi-world`, both survive a reload |
| Reduced motion | **VERIFIED** | courier, pupils, paper and head rotation all stop |
| No-WebGL fallback | **VERIFIED** | 0 canvases, 3 SVG elements, correct labels, 0 console errors on 10 routes |
| Mobile and tablet behaviour | **VERIFIED** | 390 px: written band, 64 px, no canvas; 1024 px: canvas, 80 px; 1440 px: canvas, 96 px; no horizontal overflow at any width |
| Accessibility | **PARTIAL** | the canvas is `aria-hidden` and absent from the accessibility tree, the two controls are buttons with pressed states, and the band has a text alternative; but the characters can only be poked with a pointer |
| Initial bundle delta within about 10 KB gzip | **VERIFIED** | +4 878 B gzip |
| No fabricated data | **VERIFIED** | every label, count and mood comes from the API or from what the page is really doing; the world introduces no numbers of its own |

## Known limitations recorded in this pass

1. **`static` is terminal for the session.** At `static` the canvas unmounts, so the frame
   meter that would measure recovery unmounts with it; a machine that reaches `static` keeps
   the written band until it reloads. This matches the documented intent ("the last step"),
   but the recovery branch cannot run from there.
2. **`/ask` has no `h1`.** The route-table sweep recorded an empty heading for `/ask`.
   Pre-existing, not introduced here, and not fixed in this pass.
3. **The characters have no keyboard path.** Poking the Watcher or the Courier is a
   pointer-only affordance. They are decorative and `aria-hidden`, and every fact they hint
   at is on the page, but a keyboard user cannot poke them.
4. **`npm run lint` still cannot run** — eslint is not installed in `frontend/`.
5. **No automated test suite exists.** Everything above is harness-driven browser
   verification against the running application, not a repeatable test job in CI.
6. **Live LLM/VLM and the Docker production adapters remain unverified** in this environment
   (`capabilities.llm_generation: false`; generation mode is extractive, so every answer
   reproduced above was composed from cited passages rather than written by a model).

## Side effects of this verification pass

1. The Ask verification created real conversations in the workspace's question history
   ("What is the current unit price for the Industrial Laptop X200?", "What was Supplier C's
   price in 2030?", "What is the orbital launch price for a lunar rover engine?"). They are
   stored by the API, as the application is designed to do.
2. No synthetic procurement records were created. No supplier, contract, price, certificate
   or document was written by this pass.
3. The quality ladder was exercised by throttling the *browser*, not by changing a persisted
   setting; the stored settings were left at their defaults (`reduceEffects: false`,
   `hideBuddy: false`).
