# Security

This describes the controls that are implemented in code, and the ones that are
not. Nothing here is aspirational: each item names the file that enforces it.

## 1. Authentication

- **Access tokens** are JWTs signed with `JWT_SECRET` (HS256 by default,
  `JWT_ALGORITHM` configurable) and short-lived (`ACCESS_TOKEN_TTL_MINUTES`).
  They carry user id, tenant id, role and token type (`security/tokens.py`).
- **Refresh tokens** are JWTs delivered in an httpOnly, SameSite cookie
  (`REFRESH_COOKIE_*` settings) and rotated on every `/auth/refresh`. The
  presented token is revoked in the cache before a new one is issued, so a replayed
  rotated token is rejected as theft (`security/revocation.py`,
  `api/v1/auth.py:refresh`).
- **Passwords** are hashed with Argon2 (`argon2-cffi`).
- **Login** is rate-limited (`rate_limit("login", "rate_limit_login")`), and both
  successful and failed attempts are written to the audit log.
- **Logout** revokes the refresh token and clears the cookie; the audit record is
  written server-side.
- Self-registration is off unless `ALLOW_SELF_REGISTRATION=true`. When on, an
  account without an explicit `tenant_slug` creates its own workspace and is its
  `admin`; joining an existing workspace must be explicit. Login without a slug
  resolves a unique email to its workspace and rejects an email that exists in
  more than one workspace.

## 2. Authorization

Two independent axes, both enforced server-side (`security/rbac.py`):

- **Permissions** (`resource:action`) per role: `admin`,
  `procurement_manager`, `buyer`, `compliance`, `viewer`. Every route calls
  `principal.require(...)`; a missing permission is a 403, recorded in the audit
  log.
- **Document access ceiling** per role (`public` < `internal` < `confidential` <
  `restricted`). Retrieval, structured SQL and document reads filter by the
  caller's readable levels, so a `buyer` cannot retrieve `confidential` content
  even if it matches the query. Unknown access levels rank as the most
  restrictive.

The frontend hides routes and buttons it knows a user cannot use, but that is
convenience only; the API is the control.

## 3. Tenant isolation

- The tenant id comes from the verified token, never from a request parameter.
- Every query is tenant-scoped, including retrieval, structured SQL, document
  reads, job lookups, evaluation runs and audit queries.
- Document deletion and derived-row cleanup are tenant-scoped; a document id from
  another tenant returns 404, not 403, so existence is not disclosed.
- Cross-tenant behaviour is covered by `tests/security/test_tenant_isolation.py`.

## 4. Input handling

- **Uploads**: extension, declared MIME, sniffed content type and size are all
  checked before a parser runs (`ingestion/validation.py`), and the body is read
  in bounded chunks so an oversized upload is refused while streaming rather than
  after it is buffered.
- **Injection**: retrieved text is treated as untrusted content. The injection
  module (`security/injection.py`) detects instruction-like content and the answer
  pipeline refuses to follow embedded instructions; refusal behaviour is covered
  by `tests/unit/test_injection_refusal.py`.
- **SQL**: procurement aggregation uses bound parameters through SQLAlchemy; no
  user string is concatenated into SQL.
- **Structured output**: model output is parsed into validated schemas; invalid
  output is discarded rather than passed through.

## 5. Secrets and configuration

- `Settings.validate_startup_security()` fails startup in non-development
  environments when `JWT_SECRET` is missing or a known-weak default; development
  only logs a warning.
- Secrets live in environment variables (`.env` for local development, the
  platform's secret store in deployment). No secret is committed, logged, or sent
  to the browser.
- The access token is kept in memory in the frontend, not in `localStorage`, so
  XSS cannot read it from storage; the refresh token is httpOnly.
- `COOKIE_SECURE` must be true wherever traffic is HTTPS.

## 6. Transport and browser policy

- CORS is an explicit allow-list (`CORS_ORIGINS`); no wildcard with credentials.
- Responses carry `x-request-id` for correlation.
- The API does not serve the SPA; the frontend is served separately, so CSP and
  TLS termination belong to the deployment platform.

## 7. Audit trail

`security/audit.py` writes append-only audit rows for login, failed login,
registration, logout, document upload/cancel/delete, evaluation runs, admin
changes and authorization failures, including actor, tenant, IP address and
outcome. Long detail payloads are truncated rather than dropped
(`tests/security/test_audit_truncation.py`).

## 8. Availability and abuse controls

- Rate limiting is backed by the cache provider (in-process or Redis) with
  per-route limits (`rate_limit_*` settings).
- `/health` bounds each provider check with a timeout and reports
  `degraded` instead of hanging.
- `/ready` fails when the database, vector store or embedding provider is
  unavailable, so a load balancer stops sending traffic.
- Upload size is capped (`MAX_UPLOAD_MB`) and ingestion concurrency is bounded
  (`WORKER_CONCURRENCY`).

## 9. Known gaps

These are real and should be closed before a production launch:

1. **No MFA** and no SSO/SAML/OIDC integration.
2. **No TLS in the repository**: HTTPS is expected from the platform or reverse
   proxy. `docker-compose.yml` is a development stack.
3. **Audit logs are not tamper-evident**: they are ordinary rows, not signed or
   hash-chained, and no retention policy is enforced.
4. **No per-tenant rate limits**: limits are per process, not per tenant or user.
5. **No file antivirus/malware scan** on uploads.
6. **No dependency or container scanning** in this repository (no CI pipeline is
   present in the working tree).
7. **Embeddings and answers can be cached in process memory**; the in-process
   cache is not shared between workers, so cache invalidation is per process.

## 9. Upload container validation

A DOCX/XLSX is a ZIP container, so `ingestion/validation.py` delegates to
`ingestion/archive.py` before any parser sees the bytes. The archive is inspected
from its central directory only — nothing is extracted:

- entry count (`MAX_ARCHIVE_ENTRIES`, default 2000);
- declared uncompressed size (`MAX_ARCHIVE_UNCOMPRESSED_MB`, default 500);
- compression ratio over 10 MB of expansion (`MAX_ARCHIVE_COMPRESSION_RATIO`,
  default 200);
- entry names with `..`, absolute paths or drive letters are rejected;
- encrypted entries are rejected;
- the marker part for the extension must exist (`word/document.xml` for DOCX,
  `xl/workbook.xml` for XLSX/XLSM).

The upload body itself is read in 1 MiB chunks and refused as soon as it crosses
`MAX_UPLOAD_MB`, so a client cannot force an unbounded allocation before the
check runs.

## 10. Trusted proxy

`X-Forwarded-For` is self-asserted unless a proxy overwrites it. It is only used
for audit and unauthenticated rate-limit scoping when `TRUST_FORWARDED_FOR=true`;
by default the socket peer address is used. Enabling it without a trusted proxy
would let a caller rotate the header and bypass login/upload limits.

## 11. Production startup validation

`Settings.validate_startup_security()` runs in the application lifespan and
refuses a non-development deployment when: the JWT secret is a known default or
shorter than 32 characters; `ALLOW_PROVIDER_FALLBACK` is true;
`AUTO_CREATE_SCHEMA` is true (migrations must run explicitly); `DEBUG` is true;
`CORS_ORIGINS` contains `*`; or MCP is enabled without a fixed
`MCP_TENANT_ID`/`MCP_USER_EMAIL`. All violations are reported in one error.
