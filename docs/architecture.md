# Architecture

This document describes the actual architecture of the Enterprise Procurement Intelligence platform as it exists in the repository. It distinguishes the **current local runtime** from the **target production architecture**.

---

## Overview

The system is a multi-layer procurement intelligence platform combining unstructured document retrieval, structured SQL retrieval, knowledge graph traversal, and an agentic LangGraph orchestration layer — all served through a FastAPI backend and consumed by a React/TypeScript frontend.

---

## Query Flow

```
React 18 + TypeScript (localhost:5173)
           │
           │  POST /api/v1/query/stream  (SSE, Bearer JWT)
           ▼
   FastAPI /api/v1  (uvicorn, port 8000)
           │
           ├─ Authentication (JWT, argon2)
           ├─ RBAC + Tenant scope enforcement
           ├─ Prompt injection guard
           │
           ▼
   agents/pipeline.py  →  agents/graph.py  (LangGraph)
           │
           ├─ Query Understanding
           │     intent classification, entity extraction, supplier/product/date
           │
           ├─ Retrieval Planning
           │     decides: hybrid | structured | graph | combined
           │
           ├─ Parallel Retrieval
           │     ├─ Dense vector search   (providers/vector)
           │     ├─ BM25 sparse search    (providers/sparse)
           │     ├─ Metadata filter push-down
           │     ├─ Structured SQL query  (retrieval/structured.py)
           │     └─ Graph traversal       (retrieval/graph_retrieval.py)
           │
           ├─ RRF Fusion  (retrieval/fusion.py)
           │
           ├─ Cross-encoder Reranking  (providers/reranking)
           │
           ├─ Context Construction  (retrieval/context.py)
           │     parent-child chunk assembly, token budget, citation building
           │
           ├─ Evidence Evaluation
           │     sufficiency threshold check
           │     if insufficient → Query Rewrite → re-retrieve (max 2 iterations)
           │
           ├─ Generation  (agents/nodes.py → agents/generation.py)
           │     WITH LLM endpoint:    LLM narrative generation
           │     WITHOUT LLM endpoint: extractive composition (current local state)
           │
           ├─ Verification  (agents/verification.py)
           │     grounding check, citation-to-DB validation, conflict detection
           │     decide_status: supported | conflicting | unsupported | refusal
           │
           └─ Finalise
                 persist to queries/answers/citations/agent_traces
                 stream SSE frames to frontend
```

---

## Ingestion Flow

```
File upload (multipart POST /api/v1/documents/upload)
           │
           ▼
   ingestion/pipeline.py
           │
           ├─ File validation + type detection
           ├─ Security check (filename, extension, size)
           │
           ├─ Extraction (ingestion/parsers/)
           │     ├─ PDF:   PyMuPDF → page text + layout
           │     ├─ DOCX:  python-docx
           │     ├─ XLSX / CSV: pandas / openpyxl
           │     └─ Image: OCR path
           │
           ├─ OCR (ingestion/ocr.py — PaddleOCR)
           │     triggered when page has < OCR_MIN_CHARS_PER_PAGE text chars
           │     oneDNN disabled for compatibility
           │
           ├─ Layout analysis (ingestion/layout.py)
           │     table detection, coordinates, page reconstruction
           │
           ├─ Structured extraction (ingestion/extractors.py)
           │     prices, compliance terms, supplier mentions
           │
           ├─ Contract-aware chunking (ingestion/chunking.py)
           │     structural → token-aware → clause-preserving
           │
           ├─ Contextual enrichment (ingestion/contextualizer.py)
           │     prepend supplier/contract/section context to each chunk
           │
           ├─ Embedding (providers/embedding)
           │     currently: bge-small-en-v1.5 (384d)
           │     target:    BAAI/bge-m3 (1024d)
           │
           ├─ Vector index (providers/vector)
           │     local: on-disk numpy + BM25
           │     production: Qdrant
           │
           ├─ Graph extraction (graph/builder.py)
           │     builds supplier → contract → amendment → product → price nodes/edges
           │     local: SQLite property graph
           │     production: Neo4j
           │
           ├─ Relational storage (db/models/)
           │     documents, pages, chunks, tables, prices, suppliers, contracts
           │     local: SQLite via aiosqlite
           │     production: PostgreSQL via asyncpg
           │
           └─ Reconciliation (services/reconciliation.py)
                 amendment attribution to parent contracts
```

---

## Provider Abstraction

Every infrastructure concern sits behind a provider interface with two real implementations:

| Concern | Local (active) | Production (target) |
|---|---|---|
| Relational DB | SQLite via `aiosqlite` | PostgreSQL via `asyncpg` |
| Vector store | On-disk numpy + BM25 (`providers/vector/local.py`) | Qdrant (`providers/vector/qdrant.py`) |
| Knowledge graph | SQLite property graph (`providers/graph/local.py`) | Neo4j (`providers/graph/neo4j.py`) |
| Cache | In-process dict (`providers/cache/memory.py`) | Redis |
| Object storage | Filesystem under `backend/var/storage/` | S3 / MinIO |
| LLM | **Not configured** → extractive mode | OpenAI-compatible endpoint (Qwen3-30B-A3B-Instruct-2507 via vLLM) |
| Vision model | **Not configured** → escalation disabled | OpenAI-compatible vision endpoint (Qwen3-VL) |
| Embedding | `bge-small-en-v1.5` (384d, fallback) | `BAAI/bge-m3` (1024d) |
| Reranking | `BAAI/bge-reranker-v2-m3` — **running** (CUDA) | Same |

Provider selection is controlled by environment variables (`VECTOR_PROVIDER`, `GRAPH_PROVIDER`, `CACHE_PROVIDER`, `STORAGE_PROVIDER`, `LLM_PROVIDER`, `EMBEDDING_PROVIDER`).

The system reports its active provider set at `GET /api/v1/health`:

```json
{
  "cache": "memory",
  "graph": "local",
  "llm_configured": false,
  "storage": "local",
  "vector": "local",
  "fallbacks": []
}
```

---

## Data Model

### Core tables (23 total in SQLite)

```
tenants              users               audit_logs
documents            document_pages      chunks
document_tables      ingestion_jobs      data_sources
suppliers            contracts           products
prices               compliance_certificates  procurement_records
conversations        conversation_messages
queries              answers             citations             agent_traces
evaluation_runs      evaluation_results
```

### Relationships

```
documents     → document_pages → chunks
documents     → document_tables
contracts     → amendments (self-referential) → prices → products
suppliers     → contracts → compliance_certificates
queries       → answers → citations
queries       → agent_traces
evaluation_runs → evaluation_results
```

All domain tables carry `tenant_id`. Queries are scoped through `security/scope.py`.

---

## Security Architecture

```
Request
   │
   ├─ Rate limiting  (per client, per endpoint)
   ├─ JWT verification  (security/tokens.py — PyJWT, HS256)
   ├─ RBAC enforcement  (security/rbac.py — per-endpoint permission check)
   ├─ Tenant scope injection  (security/scope.py — all DB queries)
   ├─ Document ACL check  (before context construction)
   └─ Prompt injection guard  (security/injection.py — document content sandboxed from system instructions)
```

Passwords are hashed with argon2-cffi. The default JWT secret in `.env.example` is labelled insecure and must be rotated before any deployment.

---

## Evaluation Architecture

```
evaluation/dataset.py     — loads golden_questions.json (10 questions, 6 categories)
evaluation/runner.py      — runs each question through the full agent pipeline
evaluation/metrics.py     — computes recall@k, MRR, faithfulness, citation precision
```

Results are persisted to `evaluation_runs` / `evaluation_results` and surfaced through the `/evaluation` frontend route and `GET /api/v1/evaluation/runs`.

---

## Current vs Target Architecture

| Dimension | Current (local runtime) | Target (production) |
|---|---|---|
| Database | SQLite | PostgreSQL |
| Vector store | On-disk numpy | Qdrant |
| Graph DB | SQLite property graph | Neo4j |
| Cache | In-process dict | Redis |
| Object storage | Local filesystem | S3 / MinIO |
| Embeddings | bge-small-en-v1.5 (384d) | BAAI/bge-m3 (1024d) |
| LLM | None — extractive mode | Qwen3-30B-A3B-Instruct-2507 via vLLM |
| VLM | None — escalation disabled | Qwen3-VL-30B via vLLM |
| Reranker | BGE reranker v2-m3 (CUDA) | Same |
| Infrastructure | Manual uvicorn + vite dev | Docker Compose / container orchestrator |
| Tests | Manual scripts only | Automated (planned — see COMMITS.md) |
| CI/CD | None | GitHub Actions (planned — see docs/ci-cd.md) |

---

## Known Architecture Gaps

These are tracked in [COMMITS.md](../COMMITS.md):

- **LLM / VLM not configured**: all query answers are currently extractive. The agent pipeline is complete; connecting an OpenAI-compatible endpoint activates full generation and vision escalation.
- **bge-m3 not downloaded**: the local index runs at 384d. Re-indexing with bge-m3 weights will improve retrieval quality and align dimension with the Qdrant production config.
- **Docker app profile broken**: `backend/Dockerfile` referenced in `docker-compose.yml` does not exist. Building the app profile will fail.
- **Alembic migrations unverified**: the single revision has not been applied to a live PostgreSQL instance.
- **Conversation UI not implemented**: the conversations API exists (`/conversations`, `/conversations/{id}/messages`) but has no frontend consumer.
- **Citation deep-links not implemented**: citations display page and document name but do not link to the document page image viewer.
- **No automated tests**: the test scaffolding (`pytest`, `pytest-asyncio`) is declared in `pyproject.toml[eval]` but no test files exist.
