# Render configuration

Two services from one image: `epi-api` (web) and `epi-worker` (background). The
blueprint lives in `render.yaml` at the repository root.

## 1. Services

| Setting | epi-api | epi-worker |
| --- | --- | --- |
| Type | Web Service | Background Worker |
| Runtime | Docker | Docker |
| Dockerfile | `backend/Dockerfile` | `backend/Dockerfile` |
| Context | repository root | repository root |
| Plan | Standard (2 GB+; embeddings need headroom) | Starter or Standard |
| Health check | `GET /api/v1/ready` | none |
| Instances | 1 (SQLite is single-writer; scale only with PostgreSQL and Redis) | 1–3 (claims are atomic) |
| Auto-deploy | off until the environment is verified | off |

The Docker runtime is used because the backend image installs CPU-only torch and
the system libraries `sentence-transformers`/OpenCV need — the same build the
repository already ships and import-checks. Expect a large image (multi-GB) and
a slow first pull.

## 2. Start commands

API:

```sh
alembic upgrade head &&
uvicorn app.main:app --host 0.0.0.0 --port $PORT \
  --proxy-headers --forwarded-allow-ips='*' --timeout-keep-alive 30
```

- Binding `$PORT` is mandatory; Render routes only to the injected port.
- `--proxy-headers` makes the app see the real scheme/host behind Render's proxy.
- Migration on boot is acceptable for a single API instance. For zero-downtime
  deploys use Render's pre-deploy command instead and remove it from the start
  command (see §5).

Worker:

```sh
python -m app.workers.ingestion_worker
```

The worker handles `SIGTERM`: it stops claiming, lets the current job finish or
abandon cleanly, releases its lease and closes providers. Without that handler a
deploy would leave a lease to expire before recovery requeued the job.

## 3. Environment

Set the shared values once in the `epi-backend` environment group; both services
inherit them. Secret values are `sync: false` in the blueprint, which means they
are entered in the dashboard and never stored in git. The full variable list is
in `EPI_DEPLOYMENT_ENV.md`.

Minimum for a working deployment:

```
APP_ENV=production
DATABASE_URL=postgresql+asyncpg://…
JWT_SECRET=<48 random chars>
CORS_ORIGINS=https://app.example.com
VECTOR_PROVIDER=qdrant   QDRANT_URL=…  QDRANT_API_KEY=…
GRAPH_PROVIDER=neo4j     NEO4J_URI=…   NEO4J_USERNAME=…  NEO4J_PASSWORD=…
CACHE_PROVIDER=redis     REDIS_URL=rediss://…
STORAGE_PROVIDER=s3      S3_BUCKET=…   S3_ACCESS_KEY=…   S3_SECRET_KEY=…  S3_REGION=…
LLM_BASE_URL=…           LLM_API_KEY=… LLM_MODEL=…
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
ALLOW_PROVIDER_FALLBACK=false
WORKER_MODE=external
AUTO_CREATE_SCHEMA=false
REFRESH_COOKIE_SECURE=true
REFRESH_COOKIE_SAMESITE=none   # cross-site Vercel → Render
```

If the frontend and API share a registrable domain (for example
`app.example.com` + `api.example.com`), `REFRESH_COOKIE_SAMESITE=lax` is
acceptable and stricter. With `*.vercel.app` calling `*.onrender.com`, the
refresh cookie is cross-site and must be `none` + `secure`; see
`EPI_VERCEL_CONFIG.md` §4.

## 4. Health, timeouts and limits

- `/api/v1/health` reports every provider and never 200s away a missing provider
  (it reports `degraded`). Use it for dashboards, not for routing.
- `/api/v1/ready` returns **503** when the database or any required provider
  (`vector`, `graph`, `cache`, `storage`, `embedding`) is unavailable; that is the
  platform health-check path. With `CACHE_PROVIDER=redis`, Redis is required for
  readiness — provision it before pointing the API at it.
- `--timeout-keep-alive 30` bounds idle connections; long answers are SSE and
  stream through, so raise the platform request timeout only if a proxy buffers.
- Upload limit is `MAX_UPLOAD_MB` (50 in the blueprint). Render's proxy also has
  a body limit; keep the application limit at or below it.
- `WORKER_CONCURRENCY=2` per worker instance. Each concurrent job runs the
  embedding model, so size the instance for memory, not CPU alone.
- Set `TRUST_FORWARDED_FOR=true` only because Render's proxy overwrites the
  header; otherwise the client address is the proxy.

## 5. Migrations

Preferred, for a paid plan with pre-deploy commands:

1. Add `preDeployCommand: alembic upgrade head` to `epi-api`.
2. Remove `alembic upgrade head &&` from the start command.
3. Deploy the API first; the worker must not start against an unmigrated schema.

Manual/one-off job (works on any plan):

```sh
# Render Shell on epi-api, or a one-off job with the same image and env
cd /app/backend
alembic current
alembic upgrade head
```

With `AUTO_CREATE_SCHEMA=false`, an API booted against a schema that is not at
head refuses to start (`assert_schema_current`), so a missed migration fails
loudly rather than serving wrong data. Revisions are `0001`–`0004` in
`backend/alembic/versions`.

Order for a first deploy: database reachable → run migrations → deploy API →
confirm `/api/v1/ready` is 200 → deploy worker.

## 6. Storage and persistence

Render's filesystem is ephemeral. Documents, page images and table extracts must
go to external object storage: `STORAGE_PROVIDER=s3` with a bucket the API and
worker can both reach. Do not rely on a Render disk for documents; a disk is
per-instance and is not shared with the worker.

The embedding and reranker models are downloaded at first use
(`EMBEDDING_ALLOW_DOWNLOAD=true`). That adds cold-start time on every new
instance. Options: bake the models into the image, or mount a disk for the
Hugging Face cache and accept per-instance downloads.

## 7. Scaling and failure behaviour

- **API**: keep one instance until Redis backs rate limits and the cache; otherwise
  limits are per process and each instance holds its own counters.
- **Worker**: horizontal scaling is safe — job claims are conditional updates and
  leases prevent duplicate execution. Do not run `WORKER_MODE=embedded` on the
  API at the same time.
- **Provider outage**: with `ALLOW_PROVIDER_FALLBACK=false` the app reports
  `degraded` and refuses rather than silently using local stores. Keep it false.
- **Deploy failure**: the previous instance keeps serving until the new one passes
  the readiness check; a failed migration leaves the old release running.

## 8. What is not configured here

No Render service has been created and nothing has been deployed from this
repository. The blueprint is a starting point; plan, region, instance counts and
secrets must be confirmed against the account before use.
