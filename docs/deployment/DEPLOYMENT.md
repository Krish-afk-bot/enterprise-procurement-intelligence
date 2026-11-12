# Deployment

## 1. What the repository ships

`docker-compose.yml` defines two profiles:

- **Infrastructure (default):** `postgres`, `qdrant`, `neo4j`, `redis`, `minio`,
  `minio-init`.
- **Application (`--profile app`):** `api`, `worker`, `web`.

The application services build from `backend/Dockerfile` and
`frontend/Dockerfile`, both of which are in this repository.

| Service | What it runs | Notes |
| --- | --- | --- |
| `api` | `alembic upgrade head && uvicorn app.main:app` | `WORKER_MODE=external`, so it never polls the ingestion queue |
| `worker` | `python -m app.workers.ingestion_worker` | Sole owner of ingestion; safe to scale (claims are atomic) |
| `web` | nginx serving the built SPA | Proxies `/api/` to `api:8000` and does not buffer SSE |

`web` needs no absolute API URL: the nginx `location /api/` proxy keeps browser
calls same-origin, so no CORS exception is required for the shipped stack.

## 2. Configuration

`.env` is read by every service (`env_file: .env`). Compose additionally
injects service hostnames and forces production behaviour:

```
DATABASE_URL=postgresql+asyncpg://…@postgres:5432/epi
AUTO_CREATE_SCHEMA=false
VECTOR_PROVIDER=qdrant   QDRANT_URL=http://qdrant:6333
GRAPH_PROVIDER=neo4j     NEO4J_URI=bolt://neo4j:7687
CACHE_PROVIDER=redis     REDIS_URL=redis://redis:6379/0
STORAGE_PROVIDER=s3      S3_ENDPOINT=http://minio:9000   S3_BUCKET=epi-documents
ALLOW_PROVIDER_FALLBACK=false
WORKER_MODE=external
```

Required secrets with no default (compose refuses to start without them):
`POSTGRES_PASSWORD`, `NEO4J_PASSWORD`, `MINIO_ROOT_PASSWORD`. In addition, a
non-development `APP_ENV` fails startup when `JWT_SECRET` is missing or known
weak, so set a strong `JWT_SECRET` (48+ random characters) before deploying.

Set `COOKIE_SECURE=true` and serve over HTTPS whenever the refresh cookie must
cross the network.

## 3. First deployment

```bash
# 1. Infrastructure
docker compose up -d postgres qdrant neo4j redis minio minio-init

# 2. Build and start the application (migrations run in the api entrypoint)
docker compose --profile app up -d --build api worker web

# 3. Verify
curl -fsS http://127.0.0.1:8000/api/v1/health
curl -fsS http://127.0.0.1:8000/api/v1/ready
```

`/health` reports each provider's real status. `degraded: true` means a required
provider (vector, graph, cache, storage, embedding) is unavailable. `/ready`
returns non-200 when the database, vector store or embedding provider is down, so
a load balancer should gate on it.

The first `api` start creates the bootstrap admin from
`BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD` (when set). Change that
password on first sign-in.

## 4. Migrations

Migrations are Alembic revisions in `backend/alembic/versions` (`0001`…`0004`).

- The compose `api` command runs `alembic upgrade head` before serving traffic.
- With `AUTO_CREATE_SCHEMA=false`, startup additionally verifies that
  `alembic_version` exists and equals this build's head, and refuses to start
  otherwise. A half-migrated database fails loudly instead of serving wrong data.
- To apply a migration manually: `docker compose run --rm api alembic upgrade head`.
- Local development may keep `AUTO_CREATE_SCHEMA=true`, which uses
  `create_all` and skips the gate.

## 5. Ingestion worker

Two hosting shapes:

- `WORKER_MODE=external` (compose default): the `worker` service owns the queue.
  Scale it with `docker compose --profile app up -d --scale worker=3`.
- `WORKER_MODE=embedded`: the API process runs the loops (single-process local
  development only).

Never run both against the same database: two owners double throughput on paper
and halve it in practice because they contend for the same claims.

The worker renews a lease per job (`WORKER_LEASE_SECONDS`, default 120). If a
worker dies, its job is requeued once the lease expires; the abandoned candidate
version is swept on the next worker start (`sweep_abandoned_candidates`).

## 6. Storage and data

Compose mounts `./data` read-only-ish into the app containers for the corpus and
`./backend/var` for local state. In production, use the managed services instead:

- Documents: S3 (or MinIO) bucket `S3_BUCKET`, with credentials from the secret
  store, not `.env` committed to source control.
- Vector data: Qdrant collections with volumes.
- Graph: Neo4j volumes.
- Relational: PostgreSQL volumes, with `pg_dump` backups on a schedule.

Back up PostgreSQL *and* the object store together: chunks reference stored
files, and a restore of one without the other leaves documents that cannot be
re-indexed.

## 7. What has and has not been verified here

Verified in this working tree:

- `docker compose config -q` and `docker compose --profile app config -q` parse
  cleanly with the Dockerfiles present.
- `npm run build` completes (TypeScript + Vite production build).
- The API runs locally against SQLite with local providers; migrations reach
  head `20261105120000` and the lease columns exist.
- `/health` and `/ready` were exercised over HTTP.

**Built and import-checked:** `epi-web:test` (96.9 MB) and `epi-api:test`
(5.16 GB) build on this machine, and `docker run --rm epi-api:test python -c
"import app.main"` succeeds. The first backend build failed on a PyPI read
timeout, so the Dockerfile now retries with `--timeout 180`; it also installs
torch from the CPU index, because `sentence-transformers` otherwise pulls ~2 GB
of CUDA libraries a CPU host cannot use.

**Not verified:** no container has been started — not the compose stack, and not
a single service against a live database or model endpoint. Runtime behaviour in
the container (uid, writable volumes, migrations on boot, network reach to
Ollama) is still untested.

## 8. Production hardening still required

1. TLS termination and `COOKIE_SECURE=true` (compose binds loopback only and
   serves plain HTTP).
2. Real secrets in a secret manager; rotate `JWT_SECRET` and provider keys.
3. Object-store lifecycle policy and encrypted backups with a tested restore.
4. Centralised logs/metrics: the API emits structured JSON to stdout; ship it.
5. Rate limits per tenant/user (current limits are per process).
6. A reverse proxy or ingress in front of `web`, plus HSTS/CSP headers.
