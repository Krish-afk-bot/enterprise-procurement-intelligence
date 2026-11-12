# EPI deployment guide

Target shape: static frontend on **Vercel**, FastAPI API and ingestion worker on
**Render**, traces in **LangSmith**. PostgreSQL, Qdrant, Neo4j, Redis and an
S3-compatible bucket are external managed services.

Nothing in this repository has been deployed. Accounts, domains and secrets are
placeholders (`example.com`), and no provider was contacted.

Companion documents:

| Document | Contents |
| --- | --- |
| `EPI_DEPLOYMENT_ENV.md` | every variable, with required/secret/service/example |
| `EPI_RENDER_CONFIG.md` | API and worker services, health checks, migrations |
| `EPI_VERCEL_CONFIG.md` | build settings, environment scopes, cookies/CORS |
| `EPI_INFRASTRUCTURE_DEPENDENCIES.md` | databases, storage, models, failure modes |

## 1. Architecture

```
browser ──HTTPS──► Vercel (static SPA)
   │                    │
   └──HTTPS/SSE────────►│
                        ▼
                 Render epi-api  ──► PostgreSQL (documents, jobs, users, procurement)
                        │      ──► Qdrant (dense retrieval)
                        │      ──► Neo4j (entity graph)
                        │      ──► Redis (limits, revocation)
                        │      ──► S3 bucket (originals, page images)
                        │      ──► LLM/VLM endpoint (optional)
                        │      ──► LangSmith (traces, I/O hidden)
                        ▼
                 Render epi-worker ──► same PostgreSQL, Qdrant, Neo4j, S3
```

The API runs with `WORKER_MODE=external`; the worker runs as its own process. Both
use the same image and environment group.

## 2. Prerequisites

- PostgreSQL 15+ with a database and a TLS-capable connection string.
- Qdrant instance (cloud or self-hosted) and an API key.
- Neo4j 5 instance (Aura or self-hosted) with a database.
- Redis with TLS (optional but recommended).
- S3-compatible bucket; do not plan on local disk storage.
- An OpenAI-compatible LLM endpoint (optional) and outbound HTTPS from Render.
- LangSmith account with two projects: `epi-staging`, `epi-prod`.
- Render account/workspace; Vercel account; a domain you control (strongly
  recommended, see §6).

## 3. Deploy order

1. **Provision data services.** Create PostgreSQL, Qdrant, Neo4j, Redis, bucket.
   Record endpoints and credentials in a secret manager.
2. **Configure the Render blueprint.** Import `render.yaml`, fill the
   `epi-backend` environment group (`sync: false` values), set plans and region.
3. **Run migrations** against the new database (§5). Do this before the API
   starts: `AUTO_CREATE_SCHEMA=false` plus the schema check means a stale schema
   refuses to boot.
4. **Deploy `epi-api`.** Wait for `/api/v1/ready` to return 200. Check logs for
   `startup_security_validated`, provider warnings and the CORS origins list.
5. **Deploy `epi-worker`.** Confirm it logs a started worker and claims jobs;
   upload a small PDF through the API to prove the pipeline end to end.
6. **Configure Vercel.** Root directory `frontend`, `VITE_API_BASE_URL` per
   environment, deploy.
7. **Point the frontend at the API.** Add the Vercel origin(s) to
   `CORS_ORIGINS` on Render and restart the API.
8. **Verify** with the checklist in §7, then attach custom domains.

## 4. Backend behaviour in production

- **Startup validation.** `validate_startup_security()` refuses to start in
  production with a default/weak `JWT_SECRET`, `DEBUG=true`, wildcard CORS, or
  provider fallback enabled.
- **Schema gate.** `assert_schema_current()` compares the database revision with
  the Alembic head and fails closed.
- **Logging.** JSON logs on stdout (`LOG_JSON=true`, `LOG_LEVEL=INFO`) with
  request ids; no document text or credentials are logged.
- **CORS.** Explicit origins only, credentials allowed. A wildcard is rejected
  at startup in production.
- **Shutdown.** The API stops accepting requests, closes the container and
  disposes the engine on `SIGTERM`; the worker stops claiming, finishes or
  abandons the current job, releases its lease and shuts down providers.
- **Readiness.** `/api/v1/ready` returns 503 if the database is unavailable or
  any required provider (`vector`, `graph`, `cache`, `storage`, `embedding`) is
  missing or down. That means a Redis outage also fails readiness when
  `CACHE_PROVIDER=redis`. `/api/v1/health` reports all providers without gating
  traffic.
- **Limits.** `MAX_UPLOAD_MB`, archive bomb limits, rate limits per principal and
  per client, LLM timeouts and bounded agent iterations.

## 5. Migration procedure

Revisions live in `backend/alembic/versions` (`0001`–`0004`). `alembic upgrade
head` is idempotent.

On Render, either:

- **pre-deploy command** (preferred): `preDeployCommand: alembic upgrade head` on
  `epi-api`, and remove the migration from the start command; or
- **boot migration** (default in `render.yaml`): `alembic upgrade head && uvicorn …`
  — safe with a single API instance, but concurrent instances would race.

Manual run:

```sh
cd backend
alembic current
alembic upgrade head
alembic current        # must equal head
```

Rollback of a schema change is a forward fix, not `downgrade`, unless the
migration was written to be reversible and the data impact was assessed with a
backup in hand. Keep a database snapshot before any migration that drops or
rewrites columns.

Deploy the API before the worker. A worker started against an old schema fails
its queries; a worker running ahead of the API is harmless because migrations are
additive.

## 6. Domains, cookies and CORS

The refresh token is an httpOnly cookie on the API origin. The SPA holds the
access token in memory only.

- **Preferred:** `app.example.com` (Vercel) + `api.example.com` (Render). Same
  site, so `REFRESH_COOKIE_SAMESITE=lax` works, the cookie is first-party and
  third-party-cookie blocking is irrelevant.
- **Default hosting domains:** `*.vercel.app` → `*.onrender.com` is cross-site.
  The refresh cookie then needs `REFRESH_COOKIE_SAMESITE=none` and
  `REFRESH_COOKIE_SECURE=true`, and some browsers will still block it. Do not
  ship this as the final configuration.

`CORS_ORIGINS` must contain the exact frontend origin(s), comma-separated, no
trailing slash. Preview deployments have unique origins; add only the stable
alias you actually use.

## 7. Verification checklist

Run after every deploy; none of it has been executed here.

- [ ] `GET https://api.example.com/api/v1/health` → 200, `status` not `unhealthy`,
      every expected provider present.
- [ ] `GET https://api.example.com/api/v1/ready` → 200 with `ready: true`.
- [ ] Stop or block Qdrant → `/ready` returns 503 (not 200).
- [ ] `docker compose` is **not** used on Render; services start from the image.
- [ ] API logs are JSON, include a request id, and contain no document text.
- [ ] Preflight from the frontend origin returns the exact `Access-Control-Allow-Origin`
      and `Access-Control-Allow-Credentials: true`.
- [ ] Sign in, reload the page, confirm the session is restored from the refresh
      cookie; sign out clears it.
- [ ] Upload a PDF, watch the worker claim and finish the job, query a fact from it
      and check the citation resolves to the stored page image.
- [ ] Restart the worker during a job; the lease expires and the job is requeued
      rather than lost.
- [ ] LangSmith shows runs in the correct project and **no** prompt or document
      text (I/O hidden).
- [ ] Backups exist for PostgreSQL and the bucket, and a restore was tested.

## 8. Rollback

- **API/worker:** redeploy the previous image tag in Render. Migrations are
  additive; if a release included a destructive migration, restore the snapshot
  instead.
- **Frontend:** promote the previous Vercel deployment.
- **Order:** roll back the frontend first only if it depends on a removed API
  shape; otherwise API first, then frontend.

## 9. Security notes for operators

- Never commit `.env`, `.env.production`, or filled blueprint secrets.
- `JWT_SECRET` ≥32 random characters; rotate it only with a planned sign-out of
  all users.
- Keep `ALLOW_PROVIDER_FALLBACK=false` and `AUTO_CREATE_SCHEMA=false`. They exist
  to make misconfiguration fail loudly, not to be "fixed" during an incident.
- Rotate LangSmith, model, database and storage credentials on a schedule; keep
  each environment's keys separate.
- `TRUST_FORWARDED_FOR=true` is only correct behind a proxy that overwrites the
  header (Render does). Enabling it on a direct-exposed service re-opens the
  rate-limit bypass.
- The MCP server is a separate stdio process and must not be exposed publicly.

## 10. Known gaps

- The compose stack was never booted during this preparation; runtime wiring is
  documented from configuration and code, not from an observed deployment.
- No Render or Vercel project exists; `render.yaml` and `frontend/vercel.json`
  have not been applied by either platform.
- Model cold-start time on Render (weights downloaded per instance) is unmeasured.
- Cross-site cookie behaviour in Safari/Firefox with third-party cookies blocked
  is untested; custom domains avoid the question.
