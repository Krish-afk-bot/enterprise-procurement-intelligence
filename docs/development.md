# Development Guide

This document explains how to set up the repository for local development.

---

## Prerequisites

| Tool | Minimum version | Notes |
|---|---|---|
| Python | 3.11 | 3.13.x is used in the verified environment |
| Node.js | 20 | LTS recommended |
| npm | 9+ | Comes with Node.js |
| Git | 2.x | |

Optional (for OCR):

| Tool | Notes |
|---|---|
| PaddleOCR dependencies | Installed via `pip install -e ".[ocr]"` — may require C++ build tools on Windows |

Optional (for production providers):

| Tool | Notes |
|---|---|
| Docker + Docker Compose | For postgres, qdrant, neo4j, redis, minio |

---

## Repository Structure

```
Sprint 2/
├── backend/          Python FastAPI backend
├── frontend/         React/TypeScript frontend
├── data/             Synthetic corpus + evaluation golden set
├── scripts/          Manual verification harnesses
└── docs/             This documentation
```

---

## Backend Setup

```bash
cd backend

# Create a virtual environment
python -m venv .venv

# Activate (Windows CMD)
.venv\Scripts\activate.bat

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate (macOS / Linux)
source .venv/bin/activate

# Install the package with OCR extras
pip install -e ".[ocr]"

# For reranking / vision model support (heavy, optional)
pip install -e ".[ocr,vision]"

# For evaluation tools (adds pytest)
pip install -e ".[ocr,eval]"
```

---

## Environment Configuration

```bash
# From the repo root
cp .env.example .env
```

Open `.env` and review. The defaults run the system entirely on local providers (SQLite, on-disk vector index, SQLite graph, filesystem, in-memory cache). Nothing needs to be changed to run locally except:

```dotenv
# IMPORTANT: change before any deployment
JWT_SECRET=dev-insecure-change-me

# Optional: bootstrap an admin account on first startup
BOOTSTRAP_ADMIN_EMAIL=admin@example.com
BOOTSTRAP_ADMIN_PASSWORD=change-me
```

All other defaults work for local development.

---

## Running the Backend

```bash
cd backend

# Development server (auto-reload)
uvicorn app.main:app --reload --port 8000

# Production-style (no reload)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API is at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

On first startup with `AUTO_CREATE_SCHEMA=true` (the default), all tables are created automatically from the SQLAlchemy models. No migration needs to be run locally.

---

## Running the Frontend

```bash
cd frontend

# Install dependencies (first time only)
npm install

# Development server with hot reload (proxies /api/* to port 8000)
npm run dev
```

The app is at `http://localhost:5173`.

The Vite dev proxy forwards `/api` to `http://localhost:8000`, so the backend must be running.

---

## Ingest the Synthetic Corpus (Optional)

The repository includes 12 synthetic procurement documents in `data/synthetic/`:

```bash
cd backend

# Ingest all documents from the synthetic corpus directory
python -m app.cli ingest --dir ../data/synthetic

# Or use the CLI directly
epi ingest --dir ../data/synthetic
```

After ingestion, the local database (`backend/var/epi.db`) will contain 9 documents, 15 pages, 34 chunks, 3 suppliers, 3 contracts, 39 price rows, and a populated property graph — enough to use the full Ask, Search, Compare, and Graph features.

---

## Database Migrations

The local runtime uses `AUTO_CREATE_SCHEMA=true` which calls `create_all()` on startup. No migrations are needed locally.

For PostgreSQL (production):

```bash
cd backend

# Set DATABASE_URL to your PostgreSQL connection string first
alembic upgrade head
```

The single existing revision is `backend/alembic/versions/0001_initial_schema.py`. It was generated against PostgreSQL but has not been verified against a live instance.

---

## Build Commands

### Frontend

```bash
cd frontend

# Type check only (no output files)
npm run typecheck

# Lint
npm run lint

# Production build (output to frontend/dist/)
npm run build

# Preview the production build locally
npm run preview
```

### Backend

```bash
cd backend

# Lint
ruff check .

# Format check (dry run)
ruff format --check .

# Apply formatting
ruff format .

# Type check
mypy app/
```

---

## Manual Verification Scripts

These scripts are the current safety net while automated tests are absent. Run them with the backend running.

```bash
# Basic API smoke test — exercises auth, health, and key endpoints
python scripts/api_smoke.py

# Document API verification — 29 assertions covering upload, index, retrieval
python scripts/verify_documents.py

# Full acceptance check — exercises all major flows end to end
python scripts/acceptance_check.py

# Final verification — the most complete manual harness
python scripts/final_verification.py
```

All four pass with the synthetic corpus ingested and the backend running.

---

## Local Runtime Behaviour

When running with default settings (no `.env` changes beyond `JWT_SECRET`):

- **Database**: SQLite at `backend/var/epi.db`
- **Vector index**: on-disk numpy at `backend/var/vector_index/` (384d with bge-small-en-v1.5)
- **Graph**: SQLite property graph at `backend/var/graph.db`
- **Storage**: filesystem at `backend/var/storage/`
- **Cache**: in-process memory (no Redis needed)
- **LLM**: not configured — answers are extractive, clearly labelled `degraded=True`
- **VLM**: not configured — vision escalation is skipped
- **Reranker**: BGE reranker v2-m3 runs if a GPU is available; falls back gracefully to CPU

The health endpoint reports the active provider set:

```bash
curl http://localhost:8000/api/v1/health
```

Expected response when running locally:

```json
{
  "status": "ok",
  "cache": "memory",
  "graph": "local",
  "llm_configured": false,
  "storage": "local",
  "vector": "local"
}
```

---

## Production Providers (Docker Compose)

To run with the production provider stack locally:

```bash
# Start infra services only (no app containers — app profile is currently broken)
docker compose up -d postgres qdrant neo4j redis minio
```

Then update `.env`:

```dotenv
DATABASE_URL=postgresql+asyncpg://epi:epi@localhost:5432/epi
AUTO_CREATE_SCHEMA=false
VECTOR_PROVIDER=qdrant
QDRANT_URL=http://localhost:6333
GRAPH_PROVIDER=neo4j
NEO4J_URI=bolt://localhost:7687
CACHE_PROVIDER=redis
REDIS_URL=redis://localhost:6379/0
STORAGE_PROVIDER=s3
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=epi-documents
```

Then run Alembic and start the backend:

```bash
cd backend
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

> Note: The app Docker profile (`docker compose --profile app up`) references `backend/Dockerfile` which does not currently exist. This is a known gap tracked in [COMMITS.md](../COMMITS.md).

---

## Useful Commands Summary

| Task | Command |
|---|---|
| Start backend (dev) | `cd backend && uvicorn app.main:app --reload --port 8000` |
| Start frontend (dev) | `cd frontend && npm run dev` |
| Frontend type check | `cd frontend && npm run typecheck` |
| Frontend lint | `cd frontend && npm run lint` |
| Frontend build | `cd frontend && npm run build` |
| Backend lint | `cd backend && ruff check .` |
| Backend type check | `cd backend && mypy app/` |
| Run smoke test | `python scripts/api_smoke.py` |
| Run doc verification | `python scripts/verify_documents.py` |
| Run acceptance check | `python scripts/acceptance_check.py` |
| Ingest corpus | `cd backend && epi ingest --dir ../data/synthetic` |
| Start infra services | `docker compose up -d postgres qdrant neo4j redis minio` |
| Alembic upgrade | `cd backend && alembic upgrade head` |
