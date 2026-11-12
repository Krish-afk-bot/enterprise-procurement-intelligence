# Backend hardening review

Scope: FastAPI routes, ingestion and uploads, job claiming, tenant isolation,
retrieval, caching, MCP tools, error handling and configuration. Findings are
listed with what changed and what remains. Only gaps with evidence were touched;
the working job-claim, lease, versioning and RBAC code was not rewritten.

## Changes in this pass

| Finding | Severity | Change |
| --- | --- | --- |
| DOCX/XLSX uploads were never inspected as archives. A ZIP bomb, a ZIP with `../` entry names, an encrypted container, or an arbitrary ZIP renamed `.docx` reached the extractor after only a four-byte signature check. | High | `app/ingestion/archive.py` inspects the central directory before extraction: entry-count limit, declared uncompressed-size limit, compression-ratio limit, path-traversal rejection, encrypted-entry rejection, and a required marker part (`word/document.xml`, `xl/workbook.xml`). Wired into `validate_upload`. |
| `X-Forwarded-For` was trusted unconditionally for client identity, and unauthenticated rate limits (login, upload) were keyed on it. A caller could rotate the header to obtain a fresh bucket per request. | High | `TRUST_FORWARDED_FOR` (default `false`); `get_client_ip` and the rate-limit dependency only use the header when a trusted proxy is configured. |
| Production startup only checked the JWT secret. `ALLOW_PROVIDER_FALLBACK`, `AUTO_CREATE_SCHEMA`, `DEBUG`, wildcard CORS and an enabled MCP server without a fixed tenant/account all passed. | Medium | `Settings.validate_startup_security()` now collects and refuses all of them in one startup error; development and test remain exempt. |

## Controls verified (no change needed)

- **Atomic job claiming** — `ingestion/jobs.py:claim_next_job` uses a conditional
  `UPDATE ... WHERE status='queued'`; a lost race yields `rowcount == 0` and is
  skipped. Attempts are incremented in the same statement.
- **Leases and recovery** — a running job with a valid lease is never requeued;
  expired leases go back to the queue up to `max_attempts`, then fail. The worker
  checks the lease before writing results.
- **Idempotent ingestion** — candidate versions are reserved with a compare-and-set
  on `candidate_indexing_version`, activation is a single CAS plus chunk
  activation and is idempotent on retry.
- **Upload streaming bound** — `read_upload_bounded` reads 1 MiB chunks and
  refuses as soon as the limit is crossed; the body is not buffered first.
- **Signature/extension agreement** — `sniff_mime` checks magic numbers and
  rejects content that contradicts the extension.
- **Duplicate uploads** — checksum lookup is tenant-scoped, so the same bytes in
  another tenant do not collide.
- **Tenant isolation** — `build_retrieval_filters` applies tenant and readable
  access levels last, whatever extra filters a caller supplies; SQL queries carry
  `tenant_id`; Qdrant deletes and graph traversal take a tenant; rate-limit keys
  are `tenant:user`.
- **Error envelope** — unhandled exceptions return a generic message plus request
  id; stack traces and exception text stay in the logs.
- **MCP** — tools are guarded per role with fixed tenant/user from configuration,
  not from tool arguments (see `app/mcp_server/guards.py` and its tests).

## Migration requirements

None. The changes are runtime validation only; no schema change, no data change.

## Tests added

- `tests/security/test_archive_validation.py` — 10 cases: valid DOCX, declared
  expansion, compression ratio, entry count, three traversal forms, missing
  marker, xlsx renamed to docx, non-ZIP bytes.
- `tests/security/test_forwarded_for_trust.py` — header ignored by default, used
  when trusted, missing client falls back to `None`.
- `tests/security/test_startup_security.py` — 7 new cases for the production
  configuration guards, including combined reporting.

## Remaining risks

1. **Uploads are bounded in memory, not streamed to disk.** A 100 MB PDF still
   occupies ~100 MB of process memory before validation. Lower `MAX_UPLOAD_MB` or
   move the body to a temp file before extraction for a stricter bound.
2. **No malware scanning.** Signature and container checks do not detect a
   malicious but structurally valid PDF/DOCX. A ClamAV/ICAP step is the control
   for that; it is not implemented.
3. **Macro-enabled workbooks (`.xlsm`) are accepted.** They are never evaluated
   server-side, but a client that opens a stored copy inherits the risk.
4. **Archive nesting depth is not limited.** Nested archives inside an OOXML
   container are counted in the declared size but not recursively inspected.
   The outer size/ratio limits bound the expansion.
5. **Fixed-window rate limiting.** Two bursts at a window boundary can pass 2×
   the nominal limit, and the in-memory provider is per process. Redis is needed
   for a cluster-wide limit.
6. **The graph store persists nodes only** (`var/graph.db` has no edge table), so
   graph consistency relies on rebuilding from SQL rows; a rebuild failure would
   leave the graph incomplete rather than corrupt the source rows.
7. **No answer cache exists**, so there is no cache-invalidation surface yet.
   Adding one must key on `tenant_id`, access ceiling, question and filters.
8. **SQLite deployments are single-writer.** The default configuration is fine
   for local use; production should run PostgreSQL and `alembic upgrade head`.
