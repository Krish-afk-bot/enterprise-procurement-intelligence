# Deployment Guide

This document describes how to run the platform locally and what the target production deployment looks like.

---

## Current Local Deployment

The application runs entirely on local providers — no external services required.

### What runs locally

| Component | Implementation |
|---|---|
| Backend API | `uvicorn app.main:app` (port 8000) |
| Frontend dev server | `vite` (port 5173) |
| Database | SQLite at `backend/var/epi.db` |
| Vector index | On-disk numpy + BM25 at `backend/var/vector_index/` |
| Knowledge graph | SQLite property graph at `backend/var/graph.db` |
| Object storage | Filesystem at `backend/var/storage/` |
| Cache | In-process memory |
| Embeddings | `bge-small-en-v1.5` (384d, auto-downloaded on first use) |
| Reranker | `BAAI/bge-reranker-v2-m3` (auto-downloaded, CUDA if available) |
| LLM | Not configured — extractive mode |
| VLM | Not configured — vision escalation disabled |

### Steps

1. Set up the backend and frontend following [docs/development.md](development.md).
2. Copy `.env.example` to `.env` and set `JWT_SECRET` to something non-default.
3. Start the backend: `cd backend && uvicorn app.main:app --reload --port 8000`
4. Start the frontend: `cd frontend && npm run dev`
5. Open `http://localhost:5173`.

### Local database lifetime

The SQLite database and vector index are stored in `backend/var/`. This directory is excluded from git (see `.gitignore`). They persist across restarts. To reset:

```bash
rm -rf backend/var/epi.db backend/var/vector_index/ backend/var/graph.db backend/var/storage/
```

On next startup with `AUTO_CREATE_SCHEMA=true`, the schema is recreated empty.

---

## Infrastructure Services (Docker Compose)

The `docker-compose.yml` defines the full production-equivalent infrastructure stack. The infra services run independently and do not require the app Dockerfile.

```bash
# Start infra services only
docker compose up -d postgres qdrant neo4j redis minio
```

Service ports:

| Service | Port |
|---|---|
| PostgreSQL | 5432 |
| Qdrant | 6333 (HTTP), 6334 (gRPC) |
| Neo4j | 7474 (Browser), 7687 (Bolt) |
| Redis | 6379 |
| MinIO | 9000 (API), 9001 (Console) |

Stop services:

```bash
docker compose down

# Including volumes (destroys all data)
docker compose down -v
```

> **Note:** The `api` and `web` services in the compose file use the `app` profile and reference `backend/Dockerfile`, which does not currently exist. `docker compose --profile app up --build` will fail until the Dockerfile is created. This is tracked in [COMMITS.md](../COMMITS.md).

---

## Pointing the Backend at Docker Infra

With the Docker infra services running, update `.env`:

```dotenv
DATABASE_URL=postgresql+asyncpg://epi:epi@localhost:5432/epi
AUTO_CREATE_SCHEMA=false

VECTOR_PROVIDER=qdrant
QDRANT_URL=http://localhost:6333

GRAPH_PROVIDER=neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=neo4j

CACHE_PROVIDER=redis
REDIS_URL=redis://localhost:6379/0

STORAGE_PROVIDER=s3
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=epi-documents
```

Then run migrations and start the backend:

```bash
cd backend
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

---

## Configuring LLM and VLM Endpoints

Without an LLM endpoint, all answers are extractive and labelled `degraded=True`.

To enable full generation, set in `.env`:

```dotenv
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=http://<your-vllm-host>:8080/v1
LLM_API_KEY=<your-api-key-or-empty>
LLM_MODEL=Qwen/Qwen3-30B-A3B-Instruct-2507
```

To enable vision escalation (used for visually complex document pages):

```dotenv
VLM_ENABLED=true
VLM_MODEL=Qwen/Qwen3-VL-30B-A3B-Instruct
VLM_BASE_URL=http://<your-vlm-host>:8080/v1
VLM_API_KEY=<your-api-key-or-empty>
```

Any OpenAI-compatible endpoint works (vLLM, TGI, Ollama, cloud inference APIs).

---

## Embedding Model

The production embedding model is `BAAI/bge-m3` (1024-dimensional). It is not downloaded by default because it is large (~570 MB).

To use it:

```dotenv
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_ALLOW_DOWNLOAD=true
```

On first startup with this setting, `sentence-transformers` will download the weights to the local cache.

> If you switch embedding models after ingesting documents, you must re-index all documents, because the vector dimensions change.

---

## Target Production Architecture (PLANNED)

The following describes the intended production deployment. None of this is currently configured or verified.

```
                   Users
                     │
                     ▼
              Load Balancer / CDN
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
    Nginx (frontend)     FastAPI (backend)
    React static build   uvicorn workers
          │                     │
          └──────────┬──────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   PostgreSQL      Qdrant       Neo4j
   (relational)  (vector DB)  (graph DB)
        │
        ▼
      Redis            MinIO / S3
     (cache)        (object storage)
                         │
                    Original files
                    Page images
                    OCR artifacts

                GPU Inference Server
                   vLLM
            ┌──────┴──────┐
            ▼             ▼
     Qwen3-30B-A3B    Qwen3-VL-30B
      (LLM)             (VLM)

             Embedding Server
             BAAI/bge-m3 (1024d)

             Reranker
             BAAI/bge-reranker-v2-m3
```

### Production Configuration Requirements (PLANNED)

| Requirement | Status |
|---|---|
| backend/Dockerfile | Missing — must be created |
| Frontend Dockerfile | Exists (`frontend/Dockerfile`) |
| docker-compose.yml app profile | Exists but broken (missing backend Dockerfile) |
| Alembic migration verified against Postgres | Not verified |
| GPU inference server | Not configured — no cloud provider chosen |
| Secrets management (vault or CI secrets) | Not configured |
| Observability / monitoring | structlog + DB traces exist; no exporter configured |
| OTEL exporter | Not configured (`OTEL_EXPORTER_OTLP_ENDPOINT` unset) |
| LangSmith tracing | Not configured (`LANGSMITH_TRACING=false`) |

---

## Environment Variable Reference

See `.env.example` for the full documented list. Key variables for deployment:

| Variable | Purpose | Default |
|---|---|---|
| `APP_ENV` | `development` / `staging` / `production` | `development` |
| `JWT_SECRET` | Token signing key — **must be changed** | `dev-insecure-change-me` |
| `DATABASE_URL` | SQLAlchemy connection string | SQLite local |
| `VECTOR_PROVIDER` | `local` or `qdrant` | `local` |
| `GRAPH_PROVIDER` | `local` or `neo4j` | `local` |
| `CACHE_PROVIDER` | `memory` or `redis` | `memory` |
| `STORAGE_PROVIDER` | `local` or `s3` | `local` |
| `LLM_BASE_URL` | OpenAI-compatible LLM endpoint | empty (extractive mode) |
| `EMBEDDING_MODEL` | Sentence-transformers model name | `BAAI/bge-m3` |
| `RERANKER_ENABLED` | Enable cross-encoder reranking | `true` |
| `AUTO_CREATE_SCHEMA` | Create tables on startup | `true` (set `false` for Postgres + Alembic) |
| `BOOTSTRAP_ADMIN_EMAIL` | Create admin on first startup | empty |
