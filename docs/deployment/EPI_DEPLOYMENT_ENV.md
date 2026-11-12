# EPI environment variables

Every variable the deployed system reads, grouped by concern. Values are dummy
examples only — never commit a real secret.

Legend — **Req**: `Y` = startup fails or the feature is broken without it;
`C` = conditionally required (see the note); `N` = optional with a safe default.
**Vis**: `secret` = server-side only, `public` = shipped in the browser bundle.

## 1. Platform-injected (do not set by hand)

| Variable | Purpose | Req | Vis | Service | Example |
| --- | --- | --- | --- | --- | --- |
| `PORT` | HTTP port the platform routes to | Y | public | Render web | `10000` |
| `RENDER` | Present in Render runtimes | N | public | Render | `true` |

Render injects `PORT`; the start command must bind `0.0.0.0:$PORT`. Setting it
manually to a fixed value is a common cause of failed health checks.

## 2. Application and HTTP

| Variable | Purpose | Req | Vis | Service | Example |
| --- | --- | --- | --- | --- | --- |
| `APP_ENV` | `development` / `test` / `staging` / `production`; controls startup guards and cookie defaults | Y | public | API, worker | `production` |
| `APP_NAME` | Display name in docs/health | N | public | API | `Enterprise Procurement Intelligence` |
| `API_PREFIX` | Route prefix | N | public | API | `/api/v1` |
| `DEBUG` | Debug responses; refused in production | N | public | API | `false` |
| `LOG_LEVEL` | `DEBUG`/`INFO`/`WARNING`/`ERROR` | N | public | API, worker | `INFO` |
| `LOG_JSON` | Structured JSON logs on stdout | N | public | API, worker | `true` |
| `CORS_ORIGINS` | Comma-separated browser origins allowed to call the API; `*` is refused in production | Y | public | API | `https://app.example.com` |
| `VAR_DIR` | Writable directory for local provider state | N | public | API, worker | `/tmp/epi` |

## 3. Authentication and security

| Variable | Purpose | Req | Vis | Service | Example |
| --- | --- | --- | --- | --- | --- |
| `JWT_SECRET` | HS256 signing key; ≥32 chars, known defaults refused outside dev | Y | secret | API | `replace-with-48-random-characters` |
| `JWT_ALGORITHM` | JWT algorithm | N | public | API | `HS256` |
| `ACCESS_TOKEN_TTL_MINUTES` | Access-token lifetime | N | public | API | `15` |
| `REFRESH_TOKEN_TTL_MINUTES` | Refresh-token lifetime | N | public | API | `10080` |
| `REFRESH_COOKIE_NAME` | Refresh cookie name | N | public | API | `epi_refresh` |
| `REFRESH_COOKIE_PATH` | Cookie scope | N | public | API | `/api/v1/auth` |
| `REFRESH_COOKIE_DOMAIN` | Cookie domain; unset = host-only | C | public | API | `.example.com` |
| `REFRESH_COOKIE_SAMESITE` | `strict`/`lax`/`none`; `none` needs HTTPS and is required for cross-site Vercel↔Render | C | public | API | `none` |
| `REFRESH_COOKIE_SECURE` | `Secure` flag; must be `true` in production | C | public | API | `true` |
| `ALLOW_SELF_REGISTRATION` | Whether anyone can create a workspace | N | public | API | `false` |
| `DEFAULT_TENANT_SLUG` | Workspace created for the first admin | N | public | API | `acme-procurement` |
| `BOOTSTRAP_TENANT_NAME` | Display name for that workspace | N | public | API | `Acme Procurement` |
| `BOOTSTRAP_ADMIN_EMAIL` | Creates/updates this admin at boot; leave unset when users are provisioned explicitly | N | secret | API | `admin@example.com` |
| `BOOTSTRAP_ADMIN_PASSWORD` | Password for the bootstrap admin | C | secret | API | `dummy-bootstrap-password` |

`REFRESH_COOKIE_DOMAIN` is only needed when the API and frontend share a
registrable domain. Never set it to a public suffix (`.com`, `.vercel.app`).

## 4. Database

| Variable | Purpose | Req | Vis | Service | Example |
| --- | --- | --- | --- | --- | --- |
| `DATABASE_URL` | SQLAlchemy async URL. Use `postgresql+asyncpg://` in production | Y | secret | API, worker | `postgresql+asyncpg://epi:pass@db.example.com:5432/epi` |
| `AUTO_CREATE_SCHEMA` | `create_all` at boot; must be `false` in production | N | public | API, worker | `false` |
| `DB_ECHO` | Echo SQL | N | public | API | `false` |
| `DB_POOL_SIZE` | Connection pool size per process | N | public | API, worker | `5` |
| `DB_MAX_OVERFLOW` | Pool overflow | N | public | API, worker | `5` |

`sqlite+aiosqlite://` is accepted but single-writer; it is not a production
database for a multi-instance deployment.

## 5. Vector store

| Variable | Purpose | Req | Vis | Service | Example |
| --- | --- | --- | --- | --- | --- |
| `VECTOR_PROVIDER` | `local` or `qdrant` | N | public | API, worker | `qdrant` |
| `QDRANT_URL` | Qdrant HTTP endpoint | C (qdrant) | secret | API, worker | `https://qdrant.example.com:6333` |
| `QDRANT_API_KEY` | Qdrant API key | C (managed qdrant) | secret | API, worker | `dummy-qdrant-key` |
| `QDRANT_COLLECTION_CHUNKS` | Chunk collection | N | public | API, worker | `procurement_chunks` |
| `QDRANT_COLLECTION_PAGES` | Page collection | N | public | API, worker | `document_pages` |
| `QDRANT_COLLECTION_TABLES` | Table collection | N | public | API, worker | `table_chunks` |
| `VECTOR_DIM` | Vector dimension; `0` infers from the embedding model | N | public | API, worker | `0` |

## 6. Graph store

| Variable | Purpose | Req | Vis | Service | Example |
| --- | --- | --- | --- | --- | --- |
| `GRAPH_PROVIDER` | `local` or `neo4j` | N | public | API, worker | `neo4j` |
| `NEO4J_URI` | Bolt URI | C (neo4j) | secret | API, worker | `neo4j+s://xxxx.databases.neo4j.io` |
| `NEO4J_USERNAME` | Neo4j user | C (neo4j) | secret | API, worker | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | C (neo4j) | secret | API, worker | `dummy-neo4j-password` |
| `NEO4J_DATABASE` | Database name | N | public | API, worker | `neo4j` |

## 7. Cache and rate limiting

| Variable | Purpose | Req | Vis | Service | Example |
| --- | --- | --- | --- | --- | --- |
| `CACHE_PROVIDER` | `memory` or `redis` | N | public | API | `redis` |
| `REDIS_URL` | Redis URL, TLS (`rediss://`) for managed services | C (redis) | secret | API | `rediss://default:pass@redis.example.com:6379/0` |
| `CACHE_TTL_SECONDS` | Default cache TTL | N | public | API | `300` |
| `RATE_LIMIT_ENABLED` | Enable fixed-window limits | N | public | API | `true` |
| `RATE_LIMIT_WINDOW_SECONDS` | Window length | N | public | API | `60` |
| `RATE_LIMIT_LOGIN` | Login attempts per window per client | N | public | API | `20` |
| `RATE_LIMIT_UPLOAD` | Uploads per window per principal | N | public | API | `60` |
| `RATE_LIMIT_QUERY` | Queries per window per principal | N | public | API | `120` |
| `RATE_LIMIT_MODEL` | Model calls per window | N | public | API | `240` |
| `TRUST_FORWARDED_FOR` | Honour `X-Forwarded-For`; only behind a trusted proxy | N | public | API | `false` |

Rate limits with `CACHE_PROVIDER=memory` are per process. A multi-instance API
needs Redis for limits to hold cluster-wide.

## 8. Object storage

| Variable | Purpose | Req | Vis | Service | Example |
| --- | --- | --- | --- | --- | --- |
| `STORAGE_PROVIDER` | `local` or `s3`; production must use `s3` | Y | public | API, worker | `s3` |
| `S3_ENDPOINT` | S3-compatible endpoint; omit for AWS | C | secret | API, worker | `https://s3.us-east-1.amazonaws.com` |
| `S3_ACCESS_KEY` | Access key id | C | secret | API, worker | `AKIADUMMYEXAMPLE` |
| `S3_SECRET_KEY` | Secret access key | C | secret | API, worker | `dummy-secret-key` |
| `S3_BUCKET` | Bucket for originals, page images and table extracts | Y | public | API, worker | `epi-documents-prod` |
| `S3_REGION` | Bucket region | C | public | API, worker | `us-east-1` |
| `LOCAL_STORAGE_DIR` | Filesystem root when `STORAGE_PROVIDER=local` | N | public | API, worker | `/tmp/epi-storage` |

Credentials should come from the platform secret store or an instance role, not
from a committed file. A Render disk is not a substitute: it is per instance and
lost on replacement.

## 9. Models

| Variable | Purpose | Req | Vis | Service | Example |
| --- | --- | --- | --- | --- | --- |
| `LLM_PROVIDER` | `openai_compatible` or `none` | N | public | API | `openai_compatible` |
| `LLM_BASE_URL` | OpenAI-compatible base URL, including `/v1` | C | secret | API | `https://llm.example.com/v1` |
| `LLM_API_KEY` | Provider key | C | secret | API | `dummy-llm-key` |
| `LLM_MODEL` | Generation model id | C | public | API | `qwen3-30b-instruct` |
| `LLM_SMALL_MODEL` | Cheaper model for classification | N | public | API | `qwen3-8b-instruct` |
| `LLM_TIMEOUT_SECONDS` | Per-call timeout | N | public | API | `90` |
| `LLM_MAX_TOKENS` | Generation cap | N | public | API | `2048` |
| `LLM_TEMPERATURE` | Sampling temperature | N | public | API | `0.1` |
| `VISION_PROVIDER` | Vision provider name | N | public | API | `openai_compatible` |
| `VLM_ENABLED` | Enable page-vision escalation | N | public | API | `true` |
| `VLM_BASE_URL` | Vision endpoint; defaults to `LLM_BASE_URL` | N | secret | API | `https://vlm.example.com/v1` |
| `VLM_API_KEY` | Vision key | N | secret | API | `dummy-vlm-key` |
| `VLM_MODEL` | Vision model id | N | public | API | `qwen3-vl-30b` |
| `EMBEDDING_PROVIDER` | `sentence_transformers` or `hashing` | N | public | API, worker | `sentence_transformers` |
| `EMBEDDING_MODEL` | Embedding model id | N | public | API, worker | `BAAI/bge-small-en-v1.5` |
| `EMBEDDING_DEVICE` | `auto`/`cpu`/`cuda` | N | public | API, worker | `cpu` |
| `EMBEDDING_BATCH_SIZE` | Batch size | N | public | API, worker | `16` |
| `EMBEDDING_ALLOW_DOWNLOAD` | Allow downloading model weights at runtime | N | public | API, worker | `true` |
| `RERANKER_PROVIDER` | `cross_encoder`/`lexical`/`disabled` | N | public | API | `cross_encoder` |
| `RERANKER_MODEL` | Reranker id | N | public | API | `BAAI/bge-reranker-v2-m3` |
| `RERANKER_ENABLED` | Enable reranking | N | public | API | `true` |

With `LLM_BASE_URL` unset the API still answers in labelled extractive mode; it
is not a degraded-error state, but it is not model generation either.

## 10. Retrieval and ingestion

| Variable | Purpose | Req | Vis | Service | Example |
| --- | --- | --- | --- | --- | --- |
| `DENSE_TOP_K` / `SPARSE_TOP_K` / `FUSION_TOP_K` | Candidate counts | N | public | API | `50` |
| `RERANK_TOP_N` | Chunks kept after reranking | N | public | API | `15` |
| `CONTEXT_MAX_CHUNKS` / `CONTEXT_MAX_TOKENS` | Context budget | N | public | API | `12` / `6000` |
| `MAX_AGENT_ITERATIONS` | Corrective loop bound | N | public | API | `2` |
| `EVIDENCE_SUFFICIENCY_THRESHOLD` | Refusal threshold | N | public | API | `0.45` |
| `MAX_UPLOAD_MB` | Upload size cap | N | public | API | `50` |
| `ALLOWED_EXTENSIONS` | Accepted extensions | N | public | API | `.pdf,.docx,.xlsx,.csv,.txt,.md,.png,.jpg` |
| `MAX_ARCHIVE_ENTRIES` / `MAX_ARCHIVE_UNCOMPRESSED_MB` / `MAX_ARCHIVE_COMPRESSION_RATIO` | Container bomb limits | N | public | API | `2000` / `500` / `200` |
| `OCR_ENABLED` | OCR fallback | N | public | Worker | `true` |
| `CHUNK_TARGET_TOKENS` / `CHUNK_MAX_TOKENS` / `CHUNK_OVERLAP_TOKENS` | Chunking | N | public | Worker | `320` / `700` / `60` |
| `WORKER_MODE` | `external` on Render (API never polls); `embedded` on the worker container | Y | public | API, worker | `external` |
| `WORKER_CONCURRENCY` | Jobs per worker process | N | public | Worker | `2` |
| `WORKER_POLL_INTERVAL_SECONDS` | Queue poll interval | N | public | Worker | `1.0` |
| `WORKER_LEASE_SECONDS` | Claim lease before recovery may requeue | N | public | Worker | `120` |
| `ALLOW_PROVIDER_FALLBACK` | Replace an unreachable provider with a local one; must be `false` in production | N | public | API, worker | `false` |

### Advanced tuning (defaults are safe; change with an evaluation run)

| Variable | Purpose | Example |
| --- | --- | --- |
| `EMBEDDING_DIM` | Expected vector size; `0` infers from the model | `384` |
| `RRF_K` | Reciprocal-rank-fusion constant | `60` |
| `ENABLE_QUERY_REWRITE` / `ENABLE_MULTI_QUERY` / `ENABLE_HYDE` | Query-expansion toggles | `true` / `false` / `false` |
| `CONTEXTUAL_ENRICHMENT` | Prepend document context to chunks at ingestion | `true` |
| `RERANK_CANDIDATE_LIMIT` / `RERANK_GATE_ENABLED` / `RERANK_GATE_MIN_SCORE` / `RERANK_GATE_MIN_MARGIN` | Reranker candidate cap and skip-gate | `40` / `true` / `0.2` / `0.05` |
| `RERANKER_DEVICE` | Reranker device | `cpu` |
| `CITATION_MAX` | Citations returned per answer | `8` |
| `GROUNDING_LLM_JUDGE_ENABLED` | LLM-as-judge grounding check (costs tokens) | `false` |
| `OCR_ENABLED` / `OCR_LANGUAGE` / `OCR_MIN_CHARS_PER_PAGE` / `OCR_USE_ONEDNN` | OCR fallback behaviour | `true` / `eng` / `80` / `false` |
| `VISION_ESCALATION_ENABLED` / `VISION_MIN_TABLE_COMPLEXITY` | Page-vision escalation trigger | `true` / `0.6` |
| `EVALUATION_DIR` / `SEED_CORPUS_DIR` / `SYNTHETIC_DIR` | Local evaluation and seed data paths | `data/evaluation` |
| `OTEL_SERVICE_NAME` | Service name on spans | `epi-api` |

## 11. Observability

| Variable | Purpose | Req | Vis | Service | Example |
| --- | --- | --- | --- | --- | --- |
| `LANGSMITH_TRACING` | Enable LangSmith tracing | N | public | API, worker | `true` |
| `LANGSMITH_API_KEY` | LangSmith key | C | secret | API, worker | `lsv2_pt_dummy` |
| `LANGSMITH_PROJECT` | Project name; use different names per environment | C | public | API, worker | `epi-prod` |
| `LANGSMITH_HIDE_IO` | Hide prompts/retrieved text in traces (default true) | N | public | API, worker | `true` |
| `OTEL_ENABLED` | Create OpenTelemetry spans | N | public | API | `true` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP/HTTP collector | N | secret | API | `https://otel.example.com/v1/traces` |
| `TRACE_STORE_LIMIT` | In-memory trace entries | N | public | API | `200` |

The application sets `LANGSMITH_HIDE_INPUTS`/`LANGSMITH_HIDE_OUTPUTS` from
`LANGSMITH_HIDE_IO`; even so, keep staging and production in separate LangSmith
projects and never enable tracing on a corpus you are not allowed to send to a
third party.

## 12. MCP server (optional)

| Variable | Purpose | Req | Vis | Service | Example |
| --- | --- | --- | --- | --- | --- |
| `MCP_ENABLED` | Start the MCP tool server | N | public | MCP process | `false` |
| `MCP_TENANT_ID` | Fixed tenant for every tool call | C | secret | MCP process | `ten_example` |
| `MCP_USER_EMAIL` | Fixed account whose role scopes tools | C | secret | MCP process | `ops@example.com` |
| `MCP_ROLE` | Role ceiling for tools | N | public | MCP process | `viewer` |
| `MCP_RATE_LIMIT_PER_MINUTE` | Tool calls per minute | N | public | MCP process | `60` |
| `MCP_TOOL_TIMEOUT_SECONDS` | Per-call timeout | N | public | MCP process | `20` |

MCP is a separate stdio process; it is not exposed by the Render web service.

## 13. Frontend (Vercel)

| Variable | Purpose | Req | Vis | Service | Example |
| --- | --- | --- | --- | --- | --- |
| `VITE_API_BASE_URL` | Absolute API origin used by the browser | Y | public | Vercel | `https://api.example.com` |
| `VITE_ENABLE_WORLD` | Opt-in 3D landing band | N | public | Vercel | `false` |
| `VITE_API_PROXY_TARGET` | Dev/preview proxy target (not used in a Vercel build) | N | public | local dev only | `http://localhost:8000` |

Only `VITE_*` variables reach the bundle. Nothing secret may carry that prefix.
