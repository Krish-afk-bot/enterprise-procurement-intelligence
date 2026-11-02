# Phase 0 — Hygiene & security: results

Branch: `phase-0-hygiene-security`
Base commit: `50d0947` (`feat(ingestion): versioned procurement data with cross-store consistency`)

Every claim below is backed by a command that was run in this repository; the
output is pasted verbatim. Nothing in this document is "should work" — if it is
not pasted, it is not claimed.

## Commits

| Commit | Message |
| --- | --- |
| `72ecf4a` | `chore(security): add .dockerignore and drop .fb_token from the tree` |
| `6b1c786` | `feat(security): refuse weak JWT_SECRET in staging as well as production` |
| `7ba3adc` | `chore(compose): dev-only stack with loopback ports and required secrets` |
| `7fc9e91` | `fix(api): repair the AppError envelope and stop wrapping request bodies` |
| `56f8b02` | `feat(auth): rotate refresh tokens via an httpOnly cookie` |
| `7194692` | `feat(security): shorten the default access-token TTL to 15 minutes` |

`7fc9e91` is an incidental fix: two latent bugs made the documented API
contract unreachable and blocked the Phase 0.4 tests. It is not a Phase 0 item
but had to be fixed to make the auth work testable.

---

## 0.1 — Secrets and junk out of the tree

- Committed `.fb_token` was removed from tracking (`git rm --cached`), and
  `.fb_token`, `*.fb_token`, `.freebuff/`, `backend/var/`, `.mypy_cache/`,
  `.ruff_cache/` were added to `.gitignore`.
- A new `.dockerignore` (91 lines) keeps secrets, caches, local runtime state
  and VCS metadata out of image build layers.

Evidence — nothing secret is tracked:

```text
$ git ls-files | Select-String -Pattern "fb_token|freebuff"
(none above = good)
```

Evidence — the paths are actually ignored (`git check-ignore -v`):

```text
.gitignore:107:*.fb_token       .fb_token
.gitignore:105:.freebuff/       .freebuff/
.gitignore:69:backend/var/      backend/var/
.gitignore:25:.mypy_cache/      .mypy_cache/
.gitignore:26:.ruff_cache/      .ruff_cache/
```

Status: **done**.

---

## 0.2 — Refuse a weak `JWT_SECRET` outside local development

Startup validation refuses to boot in any non-dev environment (`staging`,
`production`, …) when `JWT_SECRET` is a known default or shorter than 32
characters. `staging` was added to the guarded environments and to the
`app_env` literal.

Evidence:

```text
$ python -m pytest tests/security/test_startup_security.py -q --tb=line
................                                                         [100%]
```

(16 tests, all passing — the suite covers dev / staging / production, known
defaults, short secrets, and the boundary at exactly 32 characters.)

Status: **done**.

---

## 0.3 — `docker-compose.yml` is dev-only and fails closed

- Header comment marks the file DEV ONLY.
- Every published port is bound to `127.0.0.1` (postgres 5432, qdrant 6333/6334,
  neo4j 7474/7687, redis 6379, minio 9000/9001, api 8000, web 5173).
- Every credential is interpolated with `${VAR:?required}` from `.env`.

Evidence — with no secrets present the stack refuses to start:

```text
$ docker compose config --quiet
error while interpolating services.minio.environment.MINIO_ROOT_PASSWORD: required variable MINIO_ROOT_PASSWORD is missing a value: MINIO_ROOT_PASSWORD is required — see .env.example
error while interpolating services.neo4j.environment.NEO4J_AUTH: required variable NEO4J_PASSWORD is missing a value: NEO4J_PASSWORD is required — see .env.example
error while interpolating services.postgres.environment.POSTGRES_PASSWORD: required variable POSTGRES_PASSWORD is missing a value: POSTGRES_PASSWORD is required — see .env.example
exit=1
```

Evidence — with the secrets provided the file validates:

```text
$ docker compose config --quiet
compose config exit=0 (0 = all required vars resolved)
```

Status: **done**.

---

## 0.4 — Access token in memory, refresh token in an httpOnly cookie

The access token was persisted to `localStorage` under zustand key `epi-auth`,
so any XSS could reach a long-lived credential.

Backend:

- every token now carries a unique `jti` (`app/security/tokens.py`);
- `app/security/revocation.py` keeps a `jti` denylist on the existing cache
  provider (shared across workers when Redis is configured);
- `POST /auth/refresh` reads the refresh token from the cookie (a body token is
  still accepted for non-browser clients), rejects an already-revoked `jti` as
  reuse, then rotates;
- `POST /auth/logout` revokes the presented `jti` and clears the cookie;
- the refresh token is **no longer returned in the response body**, so it is
  unreachable from JavaScript.

Frontend:

- `api.ts` sends `credentials: "include"` on every call, refreshes once on a
  401 with single-flight dedup, replays the request once, and signs the user out
  when the refresh fails;
- `store/auth.ts` drops the `persist` middleware and silently recovers a session
  from the cookie on load; `App.tsx` waits for that bootstrap before routing;
- e2e setup seeds storage state with cookies instead of a `localStorage` key
  that never matched the store.

Evidence — backend cookie/rotation/contract tests:

```text
$ python -m pytest tests/integration/test_auth_refresh.py tests/integration/test_api_contract.py tests/security -q
............................................                             [100%]
```

(44 passed; `test_auth_refresh.py` alone is 7 tests: httponly / samesite=strict /
path, no `refresh_token` in the body, cookie not `Secure` in dev and `Secure` in
staging, rotation issues a new pair, replaying a rotated token is 401, refresh
without a token is 401 `UNAUTHENTICATED`, an access token cannot be used to
refresh, and logout revokes + clears the cookie.)

Evidence — frontend unit tests:

```text
$ npm run test
 ✓ src/lib/__tests__/answer-utils.test.ts (22 tests) 7ms
 ✓ src/lib/__tests__/api-auth.test.ts (4 tests) 20ms
 Test Files  2 passed (2)
      Tests  26 passed (26)
```

Evidence — typecheck and lint:

```text
$ npm run typecheck      -> exit 0 (tsc --noEmit, no output)
$ npm run lint           -> exit 0 (0 errors, 7 warnings; all pre-existing)
```

Status: **done for unit/contract level**. The Playwright e2e specs were updated
to the cookie model but **were not executed** (they need the backend on :8000 and
the frontend on :5173, plus an ingested corpus). See "Not verified" below.

---

## 0.5 — Shorten the default access-token TTL

`access_token_ttl_minutes` default changed `720` → `15` in
`backend/app/config/settings.py` and in `.env.example`.

Evidence:

```text
$ python -c "from app.config.settings import Settings; s=Settings(); print('ttl=', s.access_token_ttl_minutes)"
ttl= 15
```

A repo-wide search for the old default (excluding `node_modules`) returned no
remaining `720`.

Status: **done**.

---

## Pre-existing test failures (not caused by, and not fixed in, Phase 0)

`python -m pytest -q` in `backend/` reports **17 failures**, all in
`tests/ingestion/`. They pre-date Phase 0.

Evidence — they fail identically at the base commit:

```text
$ git worktree add <tmp> 50d0947
$ (cd <tmp>/backend && python -m pytest tests/ingestion -q --tb=no)
18 failed   # at 50d0947
$ (backend && python -m pytest tests/ingestion -q --tb=no)
17 failed   # on this branch
```

Diff of the failing test ids:

```text
--- ONLY IN NOW (new failures) ---
(none)
--- ONLY IN BASE ---
tests/ingestion/test_checkpoint1_candidate_version.py::TestActiveSafetyInvariant::test_active_chunks_survive_candidate_write
```

So Phase 0 introduced **zero** new failures; one base failure no longer fails
(likely order-dependent). Sample root causes observed: tests importing
`app.core.auth` (module does not exist) and tests reading
`worker_concurrency` off a `MagicMock`.

These are out of Phase 0 scope and were left untouched.

---

## Not verified

- Playwright e2e (`npm run e2e`) — requires running backend + frontend and an
  ingested corpus; not started in this session.
- `docker compose up` — only `docker compose config` was validated; no
  containers were started.
