# Phase 7.3: Reliability & Observability - Baseline and Findings

**Date**: October 19, 2026  
**Repository**: https://github.com/Krish-afk-bot/enterprise-procurement-intelligence  
**Commit**: `5a980a6` (Phase 7.2B: Authorization audit logging & security operations)  
**Branch**: `master`

---

## 1. Baseline Verification

### Working Tree Status
```
On branch master
Your branch is up to date with 'origin/master'.
nothing to commit, working tree clean
```

### Test Suite Baseline
```
================================ test session starts =================================
platform win32 -- Python 3.13.7, pytest-8.3.3, pluggy-1.6.0
collected 293 items

================ 287 passed, 6 skipped, 14 warnings in 6.56s ====================
```

**Baseline Result**: ✅ **CLEAN** - 287 tests pass, 6 skipped (live LLM tests), 0 failures

### Known Issues (Preserved)
- None - all tests passing

---

## 2. Health and Readiness Audit

### Current Implementation

**File**: `backend/app/api/v1/health.py`

#### Health Endpoint (`/health`)
- ✅ Returns application health and provider status
- ✅ Checks database connectivity (`SELECT 1`)
- ✅ Checks all provider statuses via `container.provider_statuses()`
- ✅ Reports capabilities (vector_search, graph_traversal, embeddings, etc.)
- ✅ Returns `degraded` if database or required providers unavailable
- ✅ Does NOT expose secrets, internal addresses, or PII

**Required Providers**:
```python
REQUIRED_KINDS = {"vector", "graph", "cache", "storage", "embedding"}
```

#### Readiness Endpoint (`/ready`)
- ✅ Separate from health (liveness vs readiness distinction)
- ✅ Checks database connectivity
- ✅ Checks `vector` and `embedding` providers (blocking dependencies)
- ✅ Returns `ready: false` with `blocking: [...]` list
- ✅ Does NOT expose secrets

### Findings

#### ✅ COMPLIANT: Health/Readiness Separation
- Liveness: `/health` (reports degraded state but stays up)
- Readiness: `/ready` (blocks traffic if critical dependencies down)

#### ✅ COMPLIANT: Required vs Optional Dependencies
- Required: database, vector, embedding
- Optional: sparse search, graph (reports degraded but doesn't block)

#### ✅ COMPLIANT: No Secret Exposure
- Health response includes `database_url_scheme` but NOT full URL
- Provider statuses report connectivity but not credentials
- No internal addresses exposed

#### ⚠️ GAP-1: Health Check Timeouts
**Issue**: Health checks have NO explicit timeouts

**Evidence**:
```python
# backend/app/api/v1/health.py
async def health(...):
    await session.execute(text("SELECT 1"))  # No timeout
    statuses = await container.provider_statuses()  # No timeout
```

**Risk**: Slow provider can hang health check indefinitely

**Recommendation**: Add bounded timeouts (5s for health, 3s for readiness)

#### ⚠️ GAP-2: Provider Status Checks Not Cached
**Issue**: Every health check calls `provider.status()` synchronously

**Evidence**:
```python
# backend/app/config/container.py
async def provider_statuses(self) -> dict[str, ProviderStatus]:
    for kind, provider in self._providers.items():
        try:
            statuses[kind] = await provider.status()  # Every call is fresh
```

**Risk**: High-frequency health checks can overwhelm slow providers

**Recommendation**: Cache provider statuses for 10-30 seconds

---

## 3. Structured Logging and Request Tracing Audit

### Current Implementation

**File**: `backend/app/observability/logging.py`

#### Request ID Propagation
- ✅ Request ID injected via middleware (`backend/app/main.py`)
- ✅ Accepts `X-Request-ID` header or generates UUID
- ✅ Propagated via `contextvars.ContextVar`
- ✅ Injected into all structured logs
- ✅ Returned in response header (`x-request-id`)
- ✅ Included in error responses

**Context Variables**:
```python
request_id_var: ContextVar[str | None]
query_id_var: ContextVar[str | None]
tenant_id_var: ContextVar[str | None]
user_id_var: ContextVar[str | None]
```

#### Secret Redaction
- ✅ Sensitive keys automatically redacted
- ✅ Prevents accidental credential logging

**Redacted Keys**:
```python
_SENSITIVE_KEYS = {
    "password", "hashed_password", "token", "access_token",
    "refresh_token", "api_key", "authorization", "jwt_secret",
    "secret", "neo4j_password", "s3_secret_key", "llm_api_key"
}
```

#### Structured Output
- ✅ JSON logging for production
- ✅ Console logging for development
- ✅ ISO timestamps, log levels, exc_info

### Findings

#### ✅ COMPLIANT: Request Correlation
- Request IDs propagate through all operations
- Logs include tenant_id, user_id, query_id when available

#### ✅ COMPLIANT: Secret Safety
- Credentials never logged
- Redaction prevents accidental exposure

#### ⚠️ GAP-3: Query ID Not Propagated to LLM Calls
**Issue**: Query ID (`query_id_var`) set in answer pipeline but NOT propagated to LLM provider logs

**Evidence**:
```python
# backend/app/agents/pipeline.py - sets query_id_var
# backend/app/providers/llm/openai_compatible.py - logs WITHOUT query_id
logger.info("llm_completion", model=..., latency_ms=...)  # query_id missing
```

**Impact**: Cannot correlate LLM failures with specific user queries

**Recommendation**: Ensure LLM logs include `query_id` from context

#### ⚠️ GAP-4: Ingestion Job ID Not Propagated
**Issue**: Ingestion worker logs document_id but NOT job_id in all log statements

**Evidence**:
```python
# backend/app/ingestion/pipeline.py
logger.error("ingestion_failed", document_id=document_id, ...)  # No job_id
```

**Impact**: Cannot trace all logs for a specific ingestion attempt

**Recommendation**: Add `job_id` to ingestion context vars

---

## 4. Timeouts, Retries, and Recovery Audit

### Timeout Configurations

#### Database Timeouts
**Status**: ⚠️ **NO EXPLICIT TIMEOUTS**

**Evidence**:
```python
# backend/app/db/session.py
# SQLAlchemy create_async_engine() - no timeout parameter
kwargs = {"echo": settings.db_echo, "future": True, "pool_size": ..., ...}
# Default timeout: depends on driver (asyncpg default = 60s)
```

**Recommendation**: Add explicit `connect_timeout` and `command_timeout`

#### LLM Timeouts
**Status**: ✅ **CONFIGURED**

**Evidence**:
```python
# backend/app/config/settings.py
llm_timeout_seconds: float = 90.0

# backend/app/providers/llm/openai_compatible.py
self._client = httpx.AsyncClient(timeout=self.timeout_seconds)
```

**Default**: 90 seconds (reasonable for LLM generation)

#### Vector Store Timeouts
**Status**: ✅ **CONFIGURED**

**Evidence**:
```python
# backend/app/providers/vector/qdrant.py
def __init__(self, url: str, *, timeout: float = 10.0) -> None:
    self._client = AsyncQdrantClient(url=self.url, timeout=self.timeout)
```

**Default**: 10 seconds

#### Vision API Timeouts
**Status**: ✅ **CONFIGURED**

**Evidence**:
```python
# backend/app/providers/vision.py
timeout_seconds: float = 120.0  # Longer for image processing
async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
```

**Default**: 120 seconds (reasonable for vision models)

### Retry Logic

#### ⚠️ GAP-5: LLM Structured Output Has Unsafe Retry
**Issue**: Structured output retries on validation failure WITHOUT idempotency check

**Evidence**:
```python
# backend/app/providers/llm/openai_compatible.py
async def complete_structured(...):
    response = await self.complete(messages, ...)
    try:
        return schema.model_validate(json.loads(response.text))
    except ValidationError:
        # Retry with explicit JSON instruction
        retry_messages = list(messages) + [...]
        retry = await self.complete(retry_messages, ...)  # Second LLM call
        parsed = _parse_json(retry.text)
        return schema.model_validate(parsed)
```

**Risk**: Non-idempotent operations (e.g., document classification) called twice

**Recommendation**: 
- Log retry attempts
- Consider prompt engineering to reduce validation failures
- Add retry counter to prevent infinite loops

#### ⚠️ GAP-6: No Retry for Transient Network Failures
**Issue**: HTTP calls to LLM, vector, or graph providers do NOT retry on transient failures

**Evidence**:
```python
# backend/app/providers/llm/openai_compatible.py
response = await client.post(...)  # No retry on connection error
response.raise_for_status()  # Raises on 5xx without retry
```

**Risk**: Transient 503/504 errors fail immediately

**Recommendation**: Add bounded retries (3 attempts, exponential backoff) for:
- HTTP 429 (rate limit)
- HTTP 502, 503, 504 (service unavailable)
- Connection errors (except SSL/DNS failures)

### Recovery Logic

#### ✅ COMPLIANT: Ingestion Job Recovery
**Status**: IMPLEMENTED

**Evidence**:
```python
# backend/app/ingestion/jobs.py
async def requeue_stuck_jobs(session, *, older_than_seconds=1800):
    # Find jobs stuck in "running" for >30min
    # Requeue if attempts < max_attempts
    # Mark as failed if attempts exhausted
```

**How it works**:
1. Worker startup calls `_recover()` 
2. Finds jobs stuck in `running` status for >30 minutes
3. Requeues jobs under `max_attempts` limit (default: 2)
4. Marks jobs as `failed` if attempts exhausted

**Strengths**:
- Automatic recovery on worker restart
- Bounded retry (max_attempts)
- System-level operation (no tenant filtering - intentional)

#### ⚠️ GAP-7: Ingestion Job Not Idempotent
**Issue**: Re-running an ingestion job deletes old vectors but may leave orphans on failure

**Evidence**:
```python
# backend/app/ingestion/pipeline.py
async def process_document(...):
    # Step 1: Delete old vectors
    await self.container.vector.delete_by_document(collection, document.id)
    # Step 2: Generate new chunks (can fail here)
    chunks = await self._chunk_document(...)
    # Step 3: Upload new vectors (can fail here)
    await self.container.vector.upsert(collection, chunks)
```

**Risk**: If step 2 or 3 fails, document has NO vectors (old deleted, new not created)

**Recommendation**: 
- Option A: Soft delete (mark deleted, clean up later)
- Option B: Upload new vectors BEFORE deleting old ones
- Option C: Transaction-like semantic (upload with temp prefix, swap on success)

---

## 5. Graceful Degradation Audit

### Current Behavior

#### Database Failure
**Status**: ✅ **DEGRADES CORRECTLY**

**Evidence**:
- `/health` returns `status: "degraded"` with `database: false`
- `/ready` returns `ready: false` with `blocking: ["database"]`
- API requests fail with `500 INTERNAL_ERROR` (no silent failure)

#### Vector Store Failure
**Status**: ✅ **DEGRADES CORRECTLY**

**Evidence**:
- `/health` shows `vector_search: false`
- `/ready` blocks traffic (`blocking: ["vector"]`)
- Query requests fail with explicit error (no silent skip)

#### LLM Failure
**Status**: ⚠️ **PARTIAL DEGRADATION**

**Evidence**:
```python
# backend/app/agents/generation.py
async def generate(...):
    try:
        return await self._generative(...)
    except Exception as exc:  # noqa: BLE001
        logger.warning("llm_generation_failed", error=str(exc))
        fallback = self._extractive(...)  # Falls back to extractive
```

**Behavior**: 
- ✅ Falls back to extractive answer (good)
- ⚠️ Silent degradation (user not informed that generative failed)

**Recommendation**: Include degradation info in answer response (e.g., `degraded: true`, `fallback: "extractive"`)

#### Graph Store Failure
**Status**: ⚠️ **SILENTLY SKIPPED**

**Evidence**:
```python
# backend/app/ingestion/pipeline.py
try:
    await self._update_graph(...)
except Exception as exc:  # noqa: BLE001
    logger.warning("graph_update_failed", ...)  # Logged but not surfaced
    # Ingestion continues, document marked as "indexed"
```

**Risk**: Document appears successful but graph missing, retrieval degraded

**Recommendation**: 
- Mark document status as `indexed_partial` or `needs_review` when graph fails
- Include graph status in document metadata

#### Embedding Failure
**Status**: ⚠️ **FAILS INGESTION (TOO STRICT)**

**Evidence**:
```python
# backend/app/ingestion/pipeline.py
try:
    vectors = await self.container.router.embed_documents(texts)
except Exception as exc:  # noqa: BLE001
    outcome.metrics["embeddings"] = "unavailable"
    # Continues but vectors will be empty, upsert will fail
```

**Behavior**: Embedding failure causes entire ingestion to fail

**Recommendation**: Consider whether keyword-only fallback is acceptable (sparse index only)

### Findings

#### ✅ COMPLIANT: No Silent Security Skips
- Tenant filters ALWAYS applied (never skipped on error)
- Authorization checks ALWAYS enforced
- Audit logging failures logged but don't break request

#### ⚠️ GAP-8: Partial Failures Reported as Success
**Issue**: Document ingestion may succeed with missing graph/metadata

**Risk**: Users assume document fully indexed when it's partially broken

**Recommendation**: Add `status: "indexed_partial"` and `warnings: []` field

---

## 6. Exception Handling Audit

### Broad Exception Catching

**Pattern**: `except Exception: # noqa: BLE001`

**Total Occurrences**: 35+ uses across codebase

**Analysis**:
- ✅ **Appropriate** in health checks (must not crash on provider failure)
- ✅ **Appropriate** in worker loops (must not crash entire worker)
- ✅ **Appropriate** in audit logging (must not break error responses)
- ⚠️ **Risk** in LLM/embedding calls (hides configuration errors)
- ⚠️ **Risk** in ingestion pipeline (may hide bugs)

**Recommendation**: 
- Keep broad catches for resilience boundaries (health, workers)
- Add specific catches for configuration errors (missing API keys, bad URLs)
- Log full exception type and traceback for debugging

### Error Context

#### ✅ COMPLIANT: Errors Include Context
**Evidence**:
```python
logger.error("ingestion_failed", document_id=document_id, error=str(exc), exc_info=True)
```

**Logs Include**:
- Error message
- Document/job/resource IDs
- Full stack trace (`exc_info=True`)
- Request ID (via context var)

#### ⚠️ GAP-9: Some Errors Missing Stack Traces
**Issue**: Some exception logs do NOT include `exc_info=True`

**Examples**:
```python
logger.warning("llm_generation_failed", error=str(exc))  # No stack trace
logger.warning("vision_failed", error=str(exc))  # No stack trace
```

**Impact**: Hard to debug unexpected failures

**Recommendation**: Add `exc_info=True` for unexpected errors (not just warnings)

---

## 7. Summary of Findings

### Critical Issues (Must Fix)
- None

### High Priority (Should Fix)
1. **GAP-1**: Health check timeouts (5s/3s limits)
2. **GAP-6**: No retry for transient network failures (LLM, vector)
3. **GAP-7**: Ingestion job not idempotent (orphaned vectors on failure)

### Medium Priority (Nice to Have)
4. **GAP-2**: Provider status checks not cached (performance optimization)
5. **GAP-3**: Query ID not propagated to LLM logs (tracing)
6. **GAP-4**: Job ID not propagated in ingestion logs (tracing)
7. **GAP-5**: LLM structured output retry without idempotency check
8. **GAP-8**: Partial failures reported as success (UX clarity)
9. **GAP-9**: Some errors missing stack traces (debugging)

### Low Priority (Document Only)
- Database connection timeout (driver default acceptable)
- LLM fallback silent degradation (inform user)
- Graph failure doesn't fail ingestion (may be intentional)

---

## 8. Strengths (No Changes Needed)

1. ✅ **Request ID Propagation**: Full correlation across all logs
2. ✅ **Secret Redaction**: Credentials never logged
3. ✅ **Health/Readiness Separation**: Proper liveness vs readiness
4. ✅ **Ingestion Recovery**: Stuck job requeuing works
5. ✅ **Timeouts Configured**: LLM, vector, vision all have explicit timeouts
6. ✅ **No Silent Security Skips**: Authorization always enforced
7. ✅ **Structured Logging**: JSON output, proper context injection

---

## 9. Recommended Implementation Plan

### Phase 7.3A: High Priority Fixes
1. Add health check timeouts (5s)
2. Add transient failure retries (LLM, vector)
3. Fix ingestion idempotency (soft delete or upload-before-delete)

### Phase 7.3B: Tracing Improvements
4. Propagate query_id to LLM logs
5. Propagate job_id to ingestion logs
6. Add exc_info=True to warning/error logs

### Phase 7.3C: UX and Observability
7. Cache provider statuses (10-30s TTL)
8. Add `indexed_partial` status for partial failures
9. Include degradation info in LLM fallback responses

### Phase 7.3D: Failure Injection Tests
10. Test LLM timeout and retry
11. Test vector store failure during retrieval
12. Test interrupted ingestion recovery
13. Test health/readiness during outages

---

## 10. Test Strategy

### Unit Tests (Mocked Failures)
- LLM timeout simulation
- Vector store unavailable
- Database connection failure
- Validation retry logic

### Integration Tests (Real Services)
- Health check timeout enforcement
- Stuck job recovery
- Request ID propagation end-to-end

### Load Tests (Optional)
- Health check under high frequency
- Provider status cache effectiveness

---

## Next Steps

1. Review findings with team
2. Implement Phase 7.3A (high priority fixes)
3. Add failure-injection tests
4. Re-run full test suite
5. Generate completion report

**Status**: READY FOR IMPLEMENTATION
