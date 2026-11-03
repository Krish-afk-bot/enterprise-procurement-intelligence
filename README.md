<div align="center">

# 🏢 Enterprise Procurement Intelligence

### Retrieval-Augmented Intelligence for Supplier Contracts & Pricing

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18-61dafb.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

**Answer procurement questions with page-level evidence. Every fact cites a document and page. Every answer is verified against retrieved evidence before it reaches the user.**

[Features](#-key-capabilities) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [Documentation](#-additional-documentation)

</div>

---

## 🎯 The Problem

Enterprise procurement teams hold hundreds of supplier contracts, pricing schedules, amendments and compliance documents. Getting a reliable answer to "what price did Supplier A negotiate for Product X, and does Amendment 2 change it?" normally requires manually searching multiple files, cross-referencing versions and hoping nothing was missed.

This platform makes that knowledge searchable and answerable — with citations you can verify.

---

## 🏗️ Architecture

```mermaid
flowchart TD
    FE["React 18 + TypeScript\n(Vite, Tailwind, Zustand)"]
    API["FastAPI · JWT Auth · RBAC\nTenant isolation · Rate limiting"]
    LG["LangGraph Agent\nunderstand → plan → retrieve → generate → verify"]
    STR["Structured SQL Retrieval\nPrices · Contracts · Compliance"]
    VEC["Dense Retrieval\nBGE-small-en-v1.5 384d → Qdrant"]
    BM25["Sparse Retrieval\nBM25 / SQL index"]
    RERANK["Cross-encoder Reranker\nBGE-reranker-v2-m3"]
    CTX["Context Builder\nToken budget · Injection guard · Dedup"]
    LLM["OpenAI-compatible LLM\nllama3.1:8b (local) or Qwen3-30B (prod)"]
    GRD["Grounding & Citation Validation\nLexical entailment · Fabrication rejection"]
    DB[("PostgreSQL\nDocuments · Chunks · Prices")]
    GRAPH[("Neo4j\nSupplier → Contract → Product")]
    STORE["MinIO / S3\nOriginal documents"]
    CACHE["Redis\nRate limits · Query cache"]

    FE -->|"POST /api/v1/query (SSE)"| API
    API --> LG
    LG --> STR & VEC & BM25
    VEC & BM25 -->|RRF Fusion| RERANK
    STR & RERANK --> CTX
    CTX --> LLM --> GRD --> API
    LG <-->|"ORM / SQL"| DB
    LG <-->|"Cypher / Bolt"| GRAPH
    API <--> STORE & CACHE
```

### Local development mode

SQLite · on-disk vector index · SQLite property graph · filesystem · memory cache · extractive fallback

### Production target

PostgreSQL · Qdrant · Neo4j · Redis · MinIO/S3 · real LLM endpoint

---

## ✨ Key Capabilities

| Capability | Measured result (v2 evaluation, 130 questions, 2026-11-02) |
|---|---|
| Hybrid dense + BM25 retrieval with RRF fusion | recall@10 **73.4%**, MRR **0.631**, nDCG@10 **0.649**, hit rate@10 **76.1%** |
| Cross-encoder reranking (top 20) | enabled; MRR 0.621 → 0.631; p50 latency 10.2 s → 6.9 s with concurrent retrieval |
| Structured price/contract SQL retrieval | exercised by the labelled set; answer correctness **68.3%** overall, not isolated per path |
| Supplier/contract/product graph traversal | exercised by the labelled set; not measured separately |
| Citation validation — fabricated markers rejected | citation precision **0.545** (baseline 0.316); unit tests cover fabricated markers |
| Grounding verification before answer delivery | per-claim entity/date/number binding; verification pass rate **0.50**, `verification_miss` **2** |
| Prompt-injection detection and containment | 12 security questions in the set; refusal recall **0.846** overall |
| Refusal behaviour | precision **0.478**, recall **0.846** — over-refuses some comparison questions (see results) |
| Latency on the local model | p50 **6.9 s**, p95 **10.5 s**, max **43.8 s**; 5 s target not met |
| Answer generation (OpenAI-compatible) | `qwen2.5-coder:7b`; answer correctness **68.3%** (71/104 answerable) |
| Deterministic CI evaluation gate | passes; all six tracked metrics equal the committed baseline |
| Multi-format ingestion (PDF, DOCX, XLSX, CSV) | not measured in this run |
| OCR for scanned/image-only pages (PaddleOCR) | not measured in this run |
| JWT authentication + Argon2 password hashing | covered by backend tests; not performance-measured |
| Tenant isolation — cross-tenant data blocked | covered by backend/security tests; not re-measured |
| Extractive fallback when LLM unavailable | exercised by the CI gate (no LLM endpoint, exit 0) |
| VLM visual reasoning for complex pages | not measured — no VLM was configured |
| Neo4j / Qdrant / MinIO / Redis / PostgreSQL adapters | not measured — the evaluation ran on the local adapters |
| Production Qwen3-30B accuracy | not measured — requires a production endpoint |

Full before/after table, failure taxonomy and reproduction commands:
[docs/RESULTS.md](docs/RESULTS.md).

---

## 🛠️ Technology Stack

**Frontend:** React 18 · TypeScript 5 · Vite 6 · Tailwind CSS 3 · TanStack Query · Zustand · React Router 6 · Three.js/R3F

**Backend:** Python 3.12 · FastAPI · LangGraph · SQLAlchemy 2 async · Alembic · Pydantic v2 · structlog · PyJWT · Argon2

**Retrieval:** sentence-transformers (BGE-small-en-v1.5 384d / BGE-M3 1024d) · BGE-reranker-v2-m3 · rank-bm25 · PaddleOCR · PyMuPDF

**Databases:** PostgreSQL 16 · Qdrant 1.16 · Neo4j 5.22 · Redis 7 · MinIO (S3-compatible)

**Testing:** pytest 8 · pytest-asyncio · Vitest 2 · Playwright · httpx

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12 · Node.js 20 · Docker and Docker Compose

### 1. Start infrastructure

```bash
docker compose up -d postgres qdrant neo4j redis minio
# Wait ~20 s for health checks; verify with:
docker compose ps
```

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e ".[eval]"

cp ../.env.example ../.env         # Edit — set JWT_SECRET and LLM_BASE_URL at minimum
python -m alembic upgrade head     # Apply database migrations

# Generate and ingest the synthetic corpus (optional but recommended)
cd ..
python scripts/make_synthetic_corpus.py
cd backend
python scripts_phase3/ingest_corpus.py

# Start the API
uvicorn app.main:app --port 8000 --reload
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

### 4. Health check

```bash
curl http://localhost:8000/api/v1/health
```

Expected: `{"status":"ok","degraded":false,...}`

> **No LLM configured?** The platform runs in *extractive mode*: answers are assembled directly from retrieved evidence and labelled `degraded: true`. Full narrative answers require `LLM_BASE_URL` and `LLM_API_KEY`.

---

## 👤 User Flow and Default Credentials

### Default Test Credentials

When self-registration is enabled (`ALLOW_SELF_REGISTRATION=true` in `.env`), you can create accounts through the UI. For testing purposes, the following credentials are commonly used in development:

| Email | Password | Role |
|---|---|---|
| `admin@epi.local` | `admin-local-password` | Admin |
| `buyer@epi.local` | `buyer-local-password` | Analyst/Buyer |

**Bootstrap Admin:** Set `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` in `.env` to create an admin user automatically on first startup.

### User Flow

1. **Registration/Login**
   - Navigate to `http://localhost:5173`
   - Register a new account or log in with existing credentials
   - JWT tokens are issued (access token valid for 15 minutes, refresh token for 7 days)
   - Tokens are stored securely (httpOnly cookies for refresh, memory for access)

2. **Document Upload** (Admin/Analyst roles)
   - Navigate to **Documents** page
   - Click **Upload Document**
   - Select PDF/DOCX/XLSX/CSV files (max 100MB per file)
   - Documents are:
     - Parsed and chunked
     - OCR applied to scanned pages (if `OCR_ENABLED=true`)
     - Embedded with BGE model
     - Indexed in vector store
     - Metadata stored in PostgreSQL/SQLite

3. **Ask Questions**
   - Navigate to **Ask** page
   - Type your procurement question (e.g., "What is the price for Product X from Supplier A?")
   - The system:
     - Understands intent and extracts entities
     - Retrieves relevant evidence (hybrid dense + BM25 + structured SQL)
     - Generates an answer with citations
     - Validates grounding and citations
     - Returns answer with page-level evidence
   - Click citation markers `[1]` `[2]` to view source documents

4. **View Suppliers & Contracts** (optional)
   - Navigate to **Suppliers** page
   - Browse supplier relationships and contracts
   - Explore the knowledge graph visualization

5. **Admin Functions** (Admin role only)
   - **User Management:** Create users, assign roles, manage tenants
   - **Document Management:** View all documents, delete, re-ingest
   - **System Monitoring:** View health status, provider status, audit logs

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and set the values relevant to your environment. The most important variables:

| Variable | Required | Purpose |
|---|---|---|
| `JWT_SECRET` | **Yes (production)** | ≥32-char random string; startup fails if weak in production |
| `LLM_BASE_URL` | For LLM mode | OpenAI-compatible endpoint, **must include `/v1`** |
| `LLM_API_KEY` | For LLM mode | API key; use `ollama` for local Ollama |
| `LLM_MODEL` | For LLM mode | e.g. `llama3.1:8b` or `Qwen/Qwen3-30B-A3B-Instruct-2507` |
| `DATABASE_URL` | Production | `postgresql+asyncpg://user:pass@host:5432/db` |
| `VECTOR_PROVIDER` | Production | `qdrant` |
| `QDRANT_URL` | If Qdrant | `http://localhost:6333` |
| `GRAPH_PROVIDER` | Production | `neo4j` |
| `NEO4J_URI` | If Neo4j | `bolt://localhost:7687` |
| `NEO4J_PASSWORD` | If Neo4j | Neo4j 5.x rejects `neo4j` as password — use a non-default value |
| `OCR_ENABLED` | For scanned docs | `true` enables PaddleOCR |

### Free local LLM with Ollama

```bash
# Install Ollama: https://ollama.com
ollama pull llama3.1:8b
ollama serve                       # starts on port 11434
```

```bash
# In .env:
LLM_BASE_URL=http://localhost:11434/v1   # /v1 is required
LLM_API_KEY=ollama
LLM_MODEL=llama3.1:8b
```

---

## 🔄 How the RAG Pipeline Works

```mermaid
sequenceDiagram
    participant U as User
    participant API as FastAPI
    participant LG as LangGraph
    participant RET as Retrieval
    participant LLM as LLM
    participant VER as Verification

    U->>API: POST /api/v1/query
    API->>LG: understand query (intent, entities, dates)
    LG->>RET: structured SQL + hybrid dense/BM25 + graph
    RET-->>LG: ranked evidence chunks
    LG->>LLM: system prompt + evidence blocks (injection-guarded)
    LLM-->>LG: generated answer with citation markers
    LG->>VER: grounding check + citation validation
    VER-->>LG: status (supported / partial / insufficient_evidence)
    LG-->>API: AnswerOut (mode, citations, grounding, status)
    API-->>U: answer + citations + evidence strength
```

1. **Ingestion** — PDFs/DOCX/XLSX parsed, OCR applied to scanned pages, chunks created with parent-child hierarchy
2. **Embedding** — BGE-small-en-v1.5 (384d) or BGE-M3 (1024d), stored in Qdrant
3. **Retrieval** — dense vector + BM25 hybrid, merged with RRF, optional cross-encoder reranking
4. **Structured retrieval** — SQL aggregations for price/date questions
5. **Context** — token-budgeted, deduplicated, injection-sanitised evidence blocks
6. **Generation** — LLM answer from evidence blocks; extractive fallback when no LLM configured
7. **Verification** — lexical grounding check; LLM judge when available; fabricated citations dropped; refusal enforced

---

## 📊 Evaluation and Measured Results

> Evaluated on a 22-question golden set over the synthetic procurement corpus.
> Hardware: Windows / RTX 4060 Laptop GPU (4 GB VRAM). Local LLM: llama3.1:8b via Ollama.

### Retrieval (without reranker vs with BGE-reranker-v2-m3)

| Metric | No reranker | With reranker | Change |
|---|---|---|---|
| Recall@5 | 0.794 | **0.853** | +7.5% |
| Precision@5 | 0.188 | **0.224** | +19% |
| MRR | **0.779** | 0.654 | −16% |
| Hit Rate | 0.909 | **0.955** | +5% |
| Latency p50 | **35 ms** | 4,533 ms | +4.5 s |

**Recommended default:** reranker enabled. It improves recall and hit rate. The MRR reduction means the top-ranked document is occasionally second or third, not absent. The 4.5 s reranker overhead is acceptable for quality-first procurement queries; disable it for latency-sensitive use.

### End-to-end with local LLM (llama3.1:8b, reranker on)

- Total API p50: ~16 s · p95: ~50 s (dominated by 8B local model on 4 GB VRAM)
- LLM mode: 22/22 questions ran in `generation_mode: llm`
- Citations: 22/22 had valid `document_id` + `chunk_id` backing
- Grounded: 15/22 (score ≥ 0.5)
- 11/22 passed strict keyword scoring

> Production latency with Qwen3-30B on a capable GPU will differ. The numbers above are integration-testing baselines, not production benchmarks.

---

## 🧪 Testing

```bash
# Backend — unit + integration + retrieval tests (no LLM key needed)
cd backend
pytest tests/ -q
# → 245 passed, 6 skipped

# Frontend — Vitest unit tests
cd frontend
npm run test
# → 22 passed

# Frontend — Playwright E2E (requires backend + frontend running)
cd frontend
npm run e2e
# → 16 passed

# Backend — live LLM integration (optional, requires Ollama or remote endpoint)
cd backend
RUN_LLM_INTEGRATION=1 \
  LLM_BASE_URL=http://localhost:11434/v1 \
  LLM_API_KEY=ollama \
  LLM_MODEL=llama3.1:8b \
  pytest tests/integration/test_llm_live.py -v
# → 6 passed

# Lint and format
cd backend
ruff format --check .
ruff check .

# TypeScript
cd frontend
npm run typecheck    # tsc --noEmit
npm run lint         # ESLint 9

# Production build
cd frontend
npm run build
```

### mypy status

mypy is configured (`pyproject.toml`) and runs in CI on Ubuntu. It times out on Windows (>10 min loading stubs). **55 pre-existing errors** were identified in Phase 4 across vendor-interaction code; 7 highest-severity errors were fixed. Full CI verification: **NOT RUN locally** — see `.github/workflows/ci.yml` for the Ubuntu CI job.

---

## 📁 Repository Structure

```
.
├── backend/
│   ├── app/
│   │   ├── agents/        # LangGraph pipeline (understand→verify)
│   │   ├── api/v1/        # FastAPI routers (auth, query, documents, admin…)
│   │   ├── config/        # Settings, DI container
│   │   ├── db/            # SQLAlchemy models, Alembic session
│   │   ├── evaluation/    # Golden dataset runner and metrics
│   │   ├── ingestion/     # Parse → OCR → chunk → embed pipeline
│   │   ├── providers/     # LLM, embedding, vector, graph, cache, storage
│   │   ├── retrieval/     # Hybrid retrieval, fusion, structured SQL, graph
│   │   ├── schemas/       # Pydantic request/response models
│   │   └── security/      # JWT, RBAC, injection guard, audit
│   ├── alembic/           # Database migrations
│   ├── tests/             # pytest: unit, integration, retrieval, security
│   ├── scripts_phase3/    # Operational scripts: ingest, eval, verify
│   ├── pyproject.toml
│   └── requirements.txt   # Pinned dependency snapshot
├── frontend/
│   ├── src/
│   │   ├── components/    # UI primitives, layout, answer panel, 3D scenes
│   │   ├── pages/         # One file per route (Ask, Documents, Suppliers…)
│   │   ├── store/         # Zustand state (auth, UI, world)
│   │   └── lib/           # API client, types, utilities
│   ├── e2e/               # Playwright E2E tests
│   └── vitest.config.ts
├── data/
│   ├── synthetic/         # 12 synthetic procurement documents
│   └── evaluation/        # Golden questions + recorded metrics
├── scripts/               # Corpus generation, acceptance checks
├── docs/                  # Architecture, development, CI/CD, deployment
├── docker-compose.yml     # Infrastructure services
└── .env.example           # Full environment variable reference
```

---

## 🔒 Security

- **Authentication:** JWT (HS256) with Argon2-hashed passwords. Production startup refuses a known-weak `JWT_SECRET`.
- **Authorisation:** Role-based (admin / analyst / viewer) with per-tenant row-level isolation. Cross-tenant document access is blocked at the SQL and vector search layers.
- **Prompt injection:** All retrieved document text is wrapped in `<<<EVIDENCE>>>` delimiters, passed through `detect_injection()` before context construction, and marked untrusted in the system prompt.
- **Citation safety:** Generated `[N]` markers are validated against the actual retrieved bundle. Fabricated citations are dropped and recorded, never displayed as verified.
- **Grounding enforcement:** An LLM answer with 0 verified claims is refused (`status: insufficient_evidence`), not returned as `partial`.
- **Secrets:** Never log API keys or passwords. `JWT_SECRET` is never exposed in `/health` or any public endpoint.

> **Development warning:** The Docker Compose credentials (postgres password `epi`, MinIO password `minioadmin`, Neo4j password `neo4jdev`) are intentionally trivial and must not be exposed publicly.

---

## ⚠️ Known Limitations

1. **gq-012 (Orion expired contract):** Retrieval miss when the query is processed without tenant-vocabulary entity linking (rule-based path). Fixed when the full pipeline loads supplier entities from the DB. The eval script uses rule-based-only for reproducibility.
2. **Refusal in extractive mode:** An unanswerable question in extractive mode returns `status: partial` when structured retrieval surfaces out-of-period data. The LLM pipeline correctly refuses the same question.
3. **LLM quality on 8B model:** llama3.1:8b paraphrases exact prices and occasionally omits numeric values. Production accuracy requires a larger model.
4. **Browser E2E:** 16/16 Playwright tests pass at API level. Full browser interaction for citation deep-link navigation requires the React app to fully hydrate, which depends on auth state injection timing.
5. **mypy:** ~55 pre-existing errors in vendor-interaction code. 7 highest-severity fixed. Full mypy run: NOT VERIFIED locally (Windows timeout). CI Ubuntu job is the authoritative check.
6. **OCR:** PaddleOCR works on the synthetic scanned page. Production accuracy on arbitrary scanned documents has not been evaluated.
7. **Production LLM:** Only llama3.1:8b has been live-tested. Qwen3-30B evaluation requires a capable GPU and production endpoint.

---

## 🗺️ Roadmap

| Status | Item |
|---|---|
| Done | Hybrid retrieval (dense + BM25 + RRF) |
| Done | Reranking with BGE-reranker-v2-m3 |
| Done | Grounding verification + refusal enforcement |
| Done | OCR ingestion for scanned documents |
| Done | Citation validation — fabricated markers rejected |
| Done | Tenant isolation + RBAC |
| Done | Prompt injection detection |
| Done | Playwright E2E (16 tests) |
| Done | Vitest unit tests (22 tests) |
| Done | PostgreSQL / Qdrant / Neo4j / Redis / MinIO all live-verified |
| In progress | mypy — 7 errors fixed; full CI verification on Ubuntu |
| Planned | Citation deep-link browser navigation (Playwright end-to-end) |
| Planned | Conversation history UI |
| Planned | Production Qwen3-30B accuracy evaluation |
| Planned | Automatic BGE-M3 re-indexing on model switch |
| Planned | Vitest coverage for citation rendering components |

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch conventions, commit format, code-style commands and testing policy.

---

## 📚 Additional Documentation

| Document | Contents |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Query flow, ingestion flow, provider abstraction table |
| [docs/development.md](docs/development.md) | Full local setup guide, env vars, ingestion, migration |
| [docs/ci-cd.md](docs/ci-cd.md) | CI pipeline, workflow status, gates policy |
| [docs/deployment.md](docs/deployment.md) | Docker Compose, production target architecture |
| [docs/RESULTS.md](docs/RESULTS.md) | Measured before/after metrics, failure taxonomy, reproduction commands |
| [docs/archive/](docs/archive/) | Earlier phase reports and the capability audit |
| [CHANGELOG.md](CHANGELOG.md) | Per-phase change log |
| [prd.md](prd.md) | Product requirements document |
| [data/evaluation/](data/evaluation/) | Golden question set and recorded retrieval metrics |

---

<div align="center">

## 📝 License

This project is available under the MIT License.

## 👥 Contributors

Made with ❤️ by [Krish-afk-bot](https://github.com/Krish-afk-bot)

---

> ⚠️ **Development Status**: This project is not production-ready. Infrastructure is verified against a local Docker Compose stack. Production deployment requires proper secrets management, hardened credentials, and performance evaluation against a real workload.

</div>
