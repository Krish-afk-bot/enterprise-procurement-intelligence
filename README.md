# Enterprise Procurement Intelligence

A procurement intelligence platform for grounded, evidence-backed analysis across supplier contracts, pricing agreements, amendments, compliance documents, and structured procurement data.

---

## Problem

Enterprise procurement teams hold hundreds of supplier contracts, pricing agreements, amendments, and compliance documents. Answers to critical questions — what price did Supplier A negotiate for Product X, is that price still valid, which amendment changed it — are scattered across many documents. Buyers cannot quickly verify negotiated terms without manually searching multiple files.

This platform converts that fragmented information into a searchable, queryable intelligence system where every answer is traceable to evidence and every document version is understood.

---

## Current Capabilities

The table below reflects the actual state of the repository as verified by the audit conducted 2026-09-29. See [audit.md](audit.md) for the full detail.

### Document Intelligence

| Capability | Status |
|---|---|
| PDF ingestion (text-layer + scanned/image-only pages) | **Implemented** |
| DOCX / XLSX / CSV ingestion | **Implemented** |
| PaddleOCR (image-only pages) | **Implemented** (oneDNN disabled) |
| Layout and table extraction | **Implemented** |
| Page-level image storage and retrieval | **Implemented** |
| Contract-aware chunking | **Implemented** |
| Contextual chunk enrichment | **Implemented** |
| Document metadata, version, and replacement | **Implemented** |
| VLM escalation for visually complex pages | Code path exists — **not configured** (no VLM endpoint) |

### Retrieval Intelligence

| Capability | Status |
|---|---|
| Dense vector retrieval | **Implemented** |
| Sparse / BM25 retrieval | **Implemented** |
| Hybrid retrieval with RRF fusion | **Implemented** |
| Cross-encoder reranking (BGE reranker v2-m3) | **Implemented, running** |
| Metadata filtering | **Implemented** |
| Temporal / version-aware retrieval | **Implemented** |
| Query understanding and intent classification | **Implemented** |
| Structured / SQL retrieval | **Implemented** |
| Graph retrieval | **Implemented** |
| Query rewriting and multi-query | **Implemented** (disabled by default, configurable) |
| Parent-child context construction | **Implemented** |

### Embedding Model

| Model | Status |
|---|---|
| `BAAI/bge-m3` (1024d, intended production model) | **Not downloaded** — falls back automatically |
| `BAAI/bge-small-en-v1.5` (384d fallback) | **Active locally** |

> Note: the local vector index runs at 384d. The Qdrant production provider is configured for 1024d. Switching to bge-m3 requires downloading weights and re-indexing.

### Agentic Reasoning

| Capability | Status |
|---|---|
| LangGraph orchestration (corrective RAG loop) | **Implemented** |
| Evidence evaluation and sufficiency check | **Implemented** |
| Query rewrite on insufficient evidence | **Implemented** |
| Grounding / verification pass | **Implemented** |
| Citation validation against database | **Implemented** |
| Conflict detection | **Implemented** |
| Refusal when evidence is absent | **Implemented** |
| LLM narrative generation (Qwen3-30B-A3B-Instruct-2507) | **Not configured** — no LLM endpoint set |
| VLM visual reasoning (Qwen3-VL) | **Not configured** — no VLM endpoint set |

> With no LLM endpoint configured, the system runs in **extractive mode**: answers are composed from retrieved evidence and clearly labelled `degraded=True`. The pipeline is architecturally complete; generation quality improves immediately once an LLM endpoint is pointed at it.

### Answer Quality

| Capability | Status |
|---|---|
| Evidence block with numbered citations | **Implemented** |
| Page-level source attribution | **Implemented** |
| Structured findings (prices, terms, entities) | **Implemented** |
| Conflict explanation | **Implemented** |
| Refusal for unanswerable questions | **Implemented** |
| Conversation history / follow-up queries | Schema exists, UI not implemented |
| Citation deep-link to document page | Not implemented |

### Enterprise Platform

| Capability | Status |
|---|---|
| JWT authentication (argon2 passwords) | **Implemented** |
| RBAC with tenant isolation | **Implemented** |
| 53-endpoint FastAPI surface | **Implemented** |
| Supplier comparison (structured) | **Implemented** |
| Knowledge graph (supplier → contract → amendment → product → price) | **Implemented** |
| Evaluation framework with golden dataset | **Implemented** |
| Retrieval and generation metrics | **Implemented** |
| Admin dashboard (providers, routing, audit, traces) | **Implemented** |

### Infrastructure

| Component | Status |
|---|---|
| Local runtime (SQLite + on-disk vector + SQLite graph + filesystem) | **Working** |
| Docker Compose (postgres, qdrant, neo4j, redis, minio) | File present — **app profile cannot build** (backend/Dockerfile missing) |
| PostgreSQL adapter | Code exists — **not verified** against live server |
| Qdrant adapter | Code exists — **not verified** against live server |
| Neo4j adapter | Code exists — **not verified** against live server |
| Redis adapter | Code exists — **not verified** against live server |
| S3/MinIO adapter | Code exists — **not verified** against live server |
| Alembic migrations | One revision — **not verified** against live Postgres |

### Testing

| Area | Status |
|---|---|
| Automated backend unit tests | **Absent** |
| Automated frontend tests | **Absent** |
| Manual verification scripts (`scripts/`) | **Present and passing** |
| 29/29 document API verification harness | **Passing** |

---

## Frontend

React 18 + TypeScript + Vite + Tailwind CSS application with 14 routes:

| Route | Purpose |
|---|---|
| `/ask` | Grounded Q&A with SSE streaming, citations, evidence panel |
| `/search` | Retrieval-level exploration |
| `/documents` | Upload, list, reindex documents |
| `/documents/:id` | Chunks, extracted tables, page image viewer |
| `/contracts` / `/contracts/:id` | Contract list and detail |
| `/suppliers` / `/suppliers/:id` | Supplier list and detail |
| `/compare` | Structured supplier/price comparison |
| `/graph` | Knowledge graph exploration |
| `/evaluation` | Metrics runs and charts |
| `/admin` | Provider config, routing, audit log, traces |
| `/dashboard` | Corpus counters and charts |
| `/login` | Authentication |

`npm run build` and `tsc --noEmit` pass cleanly.

---

## Technology Stack

**Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0 async, Alembic, LangChain, LangGraph, Pydantic v2, structlog, PyJWT + argon2.

**Frontend:** React 18, TypeScript 5.7, Vite 6, Tailwind CSS 3, shadcn/ui (Radix-backed), TanStack Query 5, Zustand, React Router 6, Recharts, Lucide.

**AI:** sentence-transformers (BGE), cross-encoder reranking (BGE reranker), PaddleOCR, LangGraph agentic orchestration.

**Storage providers (abstracted, two implementations each):**
- Relational: SQLite (local) / PostgreSQL asyncpg (production)
- Vector: on-disk numpy + BM25 (local) / Qdrant (production)
- Graph: SQLite property graph (local) / Neo4j (production)
- Cache: in-process memory (local) / Redis (production)
- Object storage: filesystem (local) / S3/MinIO (production)

---

## Quickstart (Local Development)

See [docs/development.md](docs/development.md) for the full guide.

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e ".[ocr]"
cp ../.env.example ../.env    # review and edit .env
python -m app.cli ingest      # ingest the synthetic corpus (optional)
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

The application is then available at `http://localhost:5173`.

---

## Repository Structure

```
.
├── backend/
│   ├── app/
│   │   ├── agents/        # LangGraph orchestration
│   │   ├── api/v1/        # FastAPI routers
│   │   ├── config/        # Settings, DI container
│   │   ├── db/            # Models, sessions
│   │   ├── evaluation/    # Golden dataset, metrics, runner
│   │   ├── graph/         # Graph builder
│   │   ├── ingestion/     # Pipeline, parsers, OCR, chunking
│   │   ├── providers/     # Abstracted LLM/embedding/vector/graph/cache/storage
│   │   ├── retrieval/     # Hybrid, structured, graph retrieval
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── security/      # RBAC, JWT, audit, scope, injection guards
│   │   ├── services/      # Business logic
│   │   └── workers/       # Background ingestion worker
│   ├── alembic/           # Database migrations
│   └── pyproject.toml
├── frontend/
│   └── src/
│       ├── components/    # UI primitives, common states, layout shell
│       ├── pages/         # One file per route
│       ├── store/         # Zustand auth and UI stores
│       └── lib/           # API client, utilities
├── data/
│   ├── synthetic/         # 12 synthetic procurement documents + corpus card
│   └── evaluation/        # Golden question set (10 questions, 6 categories)
├── scripts/               # Manual verification harnesses
├── docs/                  # Architecture, development, CI/CD, deployment guides
├── docker-compose.yml     # Infra services (postgres, qdrant, neo4j, redis, minio)
├── .env.example           # Full environment template with documentation
├── audit.md               # Detailed verification audit (2026-09-29)
├── prd.md                 # Product requirements document
└── COMMITS.md             # Engineering roadmap and commit ledger
```

---

## Documentation

- [docs/architecture.md](docs/architecture.md) — system architecture and data flows
- [docs/development.md](docs/development.md) — local development setup
- [docs/ci-cd.md](docs/ci-cd.md) — CI/CD pipeline (current state and roadmap)
- [docs/deployment.md](docs/deployment.md) — local and production deployment
- [COMMITS.md](COMMITS.md) — engineering roadmap and commit history
- [audit.md](audit.md) — detailed implementation audit
- [CONTRIBUTING.md](CONTRIBUTING.md) — contribution guidelines
- [SECURITY.md](SECURITY.md) — security policy

---

## License

Not yet specified. All rights reserved until a license is chosen.
