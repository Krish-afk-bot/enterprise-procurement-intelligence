# Infrastructure dependencies

Everything the deployed system talks to, what happens when it is missing, and
which variables bind it. Nothing here is assumed to be provisioned: a variable
being set only tells the application where to look.

## 1. Relational database

| | |
| --- | --- |
| Purpose | Documents, chunks, jobs, users/tenants, audit, procurement records |
| Required | Yes |
| Options | Managed PostgreSQL (recommended), Render PostgreSQL, Neon, Supabase |
| Binding | `DATABASE_URL=postgresql+asyncpg://…` |
| Failure | API and worker fail readiness/startup; no degraded mode |
| Capacity | Start small; ingestion writes chunks in batches and evaluates 80k+ award rows |
| Backup | Daily automated backup plus tested restore; back up with the object bucket |

`sqlite+aiosqlite://` works for a single local process and is what the tests use.
It is single-writer and unsuitable for a web service with more than one instance
or with a separate worker.

## 2. Vector database

| | |
| --- | --- |
| Purpose | Dense chunk retrieval over 384–1024-dimension embeddings |
| Required | Yes for answers; `/ready` gates on it |
| Options | Qdrant Cloud (recommended), self-hosted Qdrant, local numpy index for a single host |
| Binding | `VECTOR_PROVIDER=qdrant`, `QDRANT_URL`, `QDRANT_API_KEY` |
| Failure | Readiness fails; queries cannot retrieve dense evidence |
| Capacity | One collection per content type; rebuildable from documents + embeddings |

The local provider is a real cosine index on disk, but it is per-instance and not
shared with the worker. Use Qdrant when the API and worker are separate services.

## 3. Graph database

| | |
| --- | --- |
| Purpose | Entity relationships and multi-hop traversal |
| Required | Yes; `/ready` gates on it when `GRAPH_PROVIDER=neo4j` |
| Options | Neo4j Aura (recommended), self-hosted Neo4j, local SQLite property graph |
| Binding | `GRAPH_PROVIDER=neo4j`, `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` |
| Failure | Graph paths are empty; answers fall back to vector/SQL evidence |
| Capacity | Small: nodes and edges are derived from documents and procurement rows |

The graph is derived data. It can be rebuilt from the relational rows and object
store; a lost graph is an availability problem, not a data-loss problem.

## 4. Redis

| | |
| --- | --- |
| Purpose | Rate-limit counters, refresh-token revocation, optional cache |
| Required | Yes when `CACHE_PROVIDER=redis` (`/ready` gates on it); `memory` works for one process |
| Options | Upstash, Redis Cloud, Render Redis |
| Binding | `CACHE_PROVIDER=redis`, `REDIS_URL` (`rediss://` for TLS) |
| Failure | With `memory`, limits are per process; with Redis down, auth refresh and limits fail |
| Capacity | Tiny; counters and revoked token ids only |

Without Redis, a multi-instance API lets each instance enforce its own limits and
forgets revocations on restart.

## 5. Object storage

| | |
| --- | --- |
| Purpose | Original documents, page images, OCR artifacts, table extracts |
| Required | Yes in production (`STORAGE_PROVIDER=s3`) |
| Options | AWS S3, Cloudflare R2, Backblaze B2 (S3 API), MinIO |
| Binding | `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`, `S3_REGION` |
| Failure | Uploads fail at the storage step; existing documents are unreadable |
| Capacity | Originals dominate; page images multiply by page count |
| Backup | Versioning + lifecycle policy; object lock if originals are regulated |

The database stores keys, not bytes. A Render disk is not object storage: it is
per-instance, ephemeral, and invisible to the worker.

## 6. Language and vision models

| | |
| --- | --- |
| Purpose | Query understanding, answer generation, page vision |
| Required | No — the app answers extractively and labels the degradation |
| Options | Any OpenAI-compatible endpoint (vLLM, TGI, hosted provider) |
| Binding | `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `VLM_*` |
| Failure | Extractive answers; `/health` reports `llm_generation: false` |
| Capacity | Concurrency is bounded by rate limits and model provider quotas |

`LLM_BASE_URL` must include `/v1`; the provider appends `/chat/completions`.

## 7. Embedding and reranker models

| | |
| --- | --- |
| Purpose | Dense vectors (both query and ingestion) and cross-encoder reranking |
| Required | Embeddings: yes. Reranker: no (`RERANKER_ENABLED=false`) |
| Options | Local `sentence-transformers` (default) or hashing embeddings |
| Binding | `EMBEDDING_MODEL`, `EMBEDDING_DEVICE`, `RERANKER_MODEL` |
| Failure | Without embeddings, `/ready` fails and ingestion cannot index |
| Capacity | CPU is workable for small corpora; models download at first use |

The embedding model must be identical for ingestion and query. Changing it
requires re-indexing every chunk and recreating the vector collection.

## 8. LangSmith

| | |
| --- | --- |
| Purpose | Trace agent runs, latency and errors |
| Required | No |
| Binding | `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` |
| Failure | Tracing stops; answers are unaffected |
| Data | Prompts and retrieved context by default — hidden with `LANGSMITH_HIDE_IO=true` (default) |

Use separate projects per environment (`epi-staging`, `epi-prod`). Even with I/O
hidden, run metadata includes question lengths and document counts; treat the
project as production data and restrict access.

## 9. OpenTelemetry collector (optional)

`OTEL_EXPORTER_OTLP_ENDPOINT` exports spans. Unset means spans are created but
not exported. This is separate from LangSmith and can be enabled independently.

## 10. Network and startup order

| From | To | Port/Protocol | Required |
| --- | --- | --- | --- |
| Vercel browser | Render API | 443 HTTPS (+ WSS for SSE) | Yes |
| API | PostgreSQL | 5432 TCP/TLS | Yes |
| API | Qdrant | 6333 HTTPS | Yes |
| API | Neo4j | 7687 bolt+TLS | Yes |
| API | Redis | 6379 TLS | Recommended |
| API/worker | S3 endpoint | 443 HTTPS | Yes |
| API | LLM/VLM endpoint | 443 HTTPS | Optional |
| Worker | PostgreSQL, Qdrant, Neo4j, Redis, S3 | as above | Yes |
| API/worker | LangSmith | 443 HTTPS | Optional |

Startup order: PostgreSQL → Qdrant → Neo4j → Redis → bucket exists → migrations →
API → worker → frontend.

## 11. Dependency failure summary

| Dependency down | API | Worker | User-visible effect |
| --- | --- | --- | --- |
| PostgreSQL | not ready | fails | everything unavailable |
| Qdrant | not ready | ingestion fails | no document answers |
| Neo4j | not ready | graph writes fail | graph paths empty |
| Redis | not ready when configured | unaffected | limits/revocation unavailable |
| Object storage | not ready | ingestion fails | uploads and page images fail |
| LLM | healthy | unaffected | extractive answers |
| LangSmith | healthy | unaffected | no traces |
