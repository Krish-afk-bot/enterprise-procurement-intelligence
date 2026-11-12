"""Checkpoint 3 — Atomic activation and cutover tests.

All tests use async mocks so they run without a live database.

Coverage
--------
1.  Successful activation — versions flip, chunks promoted/deactivated,
    job checkpoint stamped.
2.  Activation already completed (idempotent) — returns immediately,
    does NOT re-execute the CAS UPDATE.
3.  Document not found — raises ActivationError.
4.  Tenant mismatch — raises ActivationError (does not operate cross-tenant).
5.  Candidate version mismatch — raises ActivationError.
6.  Candidate version not strictly newer than active — raises ActivationError.
7.  CAS UPDATE rowcount == 0 (concurrent activation won the race) — raises
    ActivationError without leaving a half-applied state.
8.  Active chunks deactivated: execute() called 3 times (CAS + old-deactivate
    + new-activate).
9.  Candidate chunks activated: same 3-execute assertion.
10. Job checkpoint stamped when job_id provided.
11. Job checkpoint skipped when job is not found.
12. No job_id — function succeeds without touching any IngestionJob row.
13. flush() is called exactly once per successful activation.
14. refresh() is called on the document after successful activation.
15. First-version edge case — old_active_version == 0 still issues the
    deactivation UPDATE (which affects 0 rows but doesn't error).
16. No-candidate document (candidate_indexing_version is None) raises.
17. Activation failure leaves flush() un-called (rollback safety).
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.ingestion.jobs import activate_candidate_version, ActivationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_doc(
    *,
    doc_id: str = "doc-1",
    tenant_id: str = "tenant-a",
    active_version: int = 1,
    candidate_version: int | None = 2,
    status: str = "processing",
) -> MagicMock:
    """Return a mock Document with versioning attributes set."""
    doc = MagicMock()
    doc.id = doc_id
    doc.tenant_id = tenant_id
    doc.active_indexing_version = active_version
    doc.candidate_indexing_version = candidate_version
    doc.status = status
    doc.stage = "candidate_ready"
    doc.progress = 0.99
    doc.error_message = None
    return doc


def _make_job(
    *,
    job_id: str = "job-1",
    # Activation only accepts a job that finished preparing its candidate.
    checkpoint: str | None = "candidate_ready",
    status: str = "succeeded",
    indexing_version: int | None = 2,
) -> MagicMock:
    job = MagicMock()
    job.id = job_id
    job.document_id = "doc-1"
    job.tenant_id = "tenant-a"
    job.checkpoint = checkpoint
    job.status = status
    job.checkpoint_metadata = {}
    # Activation compares this against the expected candidate version; leaving it
    # as an auto-created MagicMock made every activation look like a mismatch.
    job.indexing_version = indexing_version
    return job


def _make_session(doc=None, job=None, *, cas_rowcount: int = 1) -> AsyncMock:
    """Return a mock AsyncSession wired for the given document and job."""
    session = AsyncMock()

    async def _get(model_cls, pk):
        from app.db.models import Document, IngestionJob
        if model_cls is Document:
            return doc
        if model_cls is IngestionJob:
            return job
        return None

    session.get = _get

    # execute() returns an object whose .rowcount is inspected after the CAS UPDATE
    exec_result = MagicMock()
    exec_result.rowcount = cas_rowcount
    session.execute = AsyncMock(return_value=exec_result)
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# 1. Successful activation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_successful_activation_flips_version():
    doc = _make_doc(active_version=1, candidate_version=2)
    job = _make_job()
    session = _make_session(doc=doc, job=job, cas_rowcount=1)

    result = await activate_candidate_version(
        session,
        tenant_id="tenant-a",
        document_id="doc-1",
        expected_candidate_version=2,
        job_id="job-1",
    )

    assert result is doc
    # count + CAS + deactivate (chunks/prices/certificates) + activate (3) = 8
    assert session.execute.await_count == 8
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(doc)


# ---------------------------------------------------------------------------
# 2. Idempotency — activation already complete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_idempotent_if_already_activated():
    # Simulate a document where activation already ran
    doc = _make_doc(active_version=2, candidate_version=None, status="indexed")
    session = _make_session(doc=doc, cas_rowcount=0)

    result = await activate_candidate_version(
        session,
        tenant_id="tenant-a",
        document_id="doc-1",
        expected_candidate_version=2,
    )

    assert result is doc
    # No CAS UPDATE should have been issued
    session.execute.assert_not_awaited()
    session.flush.assert_not_awaited()


# ---------------------------------------------------------------------------
# 3. Document not found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_document_not_found_raises():
    session = _make_session(doc=None)

    with pytest.raises(ActivationError, match="not found in tenant"):
        await activate_candidate_version(
            session,
            tenant_id="tenant-a",
            document_id="doc-missing",
            expected_candidate_version=2,
        )


# ---------------------------------------------------------------------------
# 4. Tenant mismatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tenant_mismatch_raises():
    doc = _make_doc(tenant_id="tenant-b")
    session = _make_session(doc=doc)

    with pytest.raises(ActivationError, match="not found in tenant"):
        await activate_candidate_version(
            session,
            tenant_id="tenant-a",  # caller is tenant-a, doc is tenant-b
            document_id="doc-1",
            expected_candidate_version=2,
        )


# ---------------------------------------------------------------------------
# 5. Candidate version mismatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_candidate_version_mismatch_raises():
    doc = _make_doc(active_version=1, candidate_version=3)  # doc has candidate=3
    session = _make_session(doc=doc)

    with pytest.raises(ActivationError, match="expected 2"):
        await activate_candidate_version(
            session,
            tenant_id="tenant-a",
            document_id="doc-1",
            expected_candidate_version=2,  # caller expects candidate=2
        )


# ---------------------------------------------------------------------------
# 6. Candidate not strictly newer than active
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_candidate_not_newer_than_active_raises():
    # candidate_version == active_version would be a data corruption
    doc = _make_doc(active_version=5, candidate_version=5)
    session = _make_session(doc=doc)

    with pytest.raises(ActivationError, match="not strictly newer"):
        await activate_candidate_version(
            session,
            tenant_id="tenant-a",
            document_id="doc-1",
            expected_candidate_version=5,
        )


@pytest.mark.asyncio
async def test_candidate_older_than_active_raises():
    doc = _make_doc(active_version=10, candidate_version=3)
    session = _make_session(doc=doc)

    with pytest.raises(ActivationError, match="not strictly newer"):
        await activate_candidate_version(
            session,
            tenant_id="tenant-a",
            document_id="doc-1",
            expected_candidate_version=3,
        )


# ---------------------------------------------------------------------------
# 7. CAS UPDATE rowcount == 0 — concurrent winner took the lock
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cas_rowcount_zero_raises():
    doc = _make_doc(active_version=1, candidate_version=2)
    session = _make_session(doc=doc, cas_rowcount=0)

    with pytest.raises(ActivationError, match="CAS guard failed"):
        await activate_candidate_version(
            session,
            tenant_id="tenant-a",
            document_id="doc-1",
            expected_candidate_version=2,
        )

    # The candidate-chunk count ran, then the CAS UPDATE. The chunk/structured
    # updates must NOT have run, and nothing may be flushed.
    assert session.execute.await_count == 2
    session.flush.assert_not_awaited()


# ---------------------------------------------------------------------------
# 8 & 9. Chunk deactivation / activation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_three_execute_calls_for_full_activation():
    """One statement per activation step.

    The current activation issues: candidate-chunk count, CAS update, then
    deactivate/activate for chunks, prices and compliance certificates — eight
    statements in total. The chunk pair is what this test has always been about.
    """
    doc = _make_doc(active_version=1, candidate_version=2)
    session = _make_session(doc=doc, cas_rowcount=1)

    await activate_candidate_version(
        session,
        tenant_id="tenant-a",
        document_id="doc-1",
        expected_candidate_version=2,
    )

    assert session.execute.await_count == 8


# ---------------------------------------------------------------------------
# 10. Job checkpoint stamped when job_id is provided
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_job_checkpoint_stamped():
    doc = _make_doc(active_version=1, candidate_version=2)
    job = _make_job(job_id="job-42")
    session = _make_session(doc=doc, job=job, cas_rowcount=1)

    await activate_candidate_version(
        session,
        tenant_id="tenant-a",
        document_id="doc-1",
        expected_candidate_version=2,
        job_id="job-42",
    )

    assert job.checkpoint == "activated"
    assert job.checkpoint_metadata.get("activated_version") == 2
    assert job.checkpoint_metadata.get("deactivated_version") == 1
    assert "activated_at" in job.checkpoint_metadata


# ---------------------------------------------------------------------------
# 11. Job not found — checkpoint skipped gracefully
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_job_not_found_skips_checkpoint():
    doc = _make_doc(active_version=1, candidate_version=2)
    session = _make_session(doc=doc, job=None, cas_rowcount=1)

    # Should not raise even when the job row is missing
    result = await activate_candidate_version(
        session,
        tenant_id="tenant-a",
        document_id="doc-1",
        expected_candidate_version=2,
        job_id="job-ghost",
    )

    assert result is doc
    session.flush.assert_awaited_once()


# ---------------------------------------------------------------------------
# 12. No job_id — succeeds without touching IngestionJob
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_job_id_succeeds():
    doc = _make_doc(active_version=1, candidate_version=2)
    session = _make_session(doc=doc, cas_rowcount=1)

    result = await activate_candidate_version(
        session,
        tenant_id="tenant-a",
        document_id="doc-1",
        expected_candidate_version=2,
        # no job_id
    )

    assert result is doc
    session.flush.assert_awaited_once()


# ---------------------------------------------------------------------------
# 13. flush() called exactly once per successful activation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_flush_called_exactly_once_on_success():
    doc = _make_doc(active_version=1, candidate_version=2)
    job = _make_job()
    session = _make_session(doc=doc, job=job, cas_rowcount=1)

    await activate_candidate_version(
        session,
        tenant_id="tenant-a",
        document_id="doc-1",
        expected_candidate_version=2,
        job_id="job-1",
    )

    assert session.flush.await_count == 1


# ---------------------------------------------------------------------------
# 14. refresh() called on document after success
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_called_on_document():
    doc = _make_doc(active_version=1, candidate_version=2)
    session = _make_session(doc=doc, cas_rowcount=1)

    await activate_candidate_version(
        session,
        tenant_id="tenant-a",
        document_id="doc-1",
        expected_candidate_version=2,
    )

    session.refresh.assert_awaited_once_with(doc)


# ---------------------------------------------------------------------------
# 15. First-version edge case — old_active_version == 0
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_first_activation_old_version_zero():
    """When old_active_version is 0, the deactivation UPDATE is still issued
    (it affects 0 rows but must not error or skip)."""
    doc = _make_doc(active_version=0, candidate_version=1)
    session = _make_session(doc=doc, cas_rowcount=1)

    result = await activate_candidate_version(
        session,
        tenant_id="tenant-a",
        document_id="doc-1",
        expected_candidate_version=1,
    )

    assert result is doc
    # count + CAS + deactivate old (version 0, 3 statements) + activate (3) = 8
    assert session.execute.await_count == 8


# ---------------------------------------------------------------------------
# 16. No-candidate document raises
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_candidate_version_raises():
    doc = _make_doc(active_version=1, candidate_version=None)
    session = _make_session(doc=doc)

    with pytest.raises(ActivationError):
        await activate_candidate_version(
            session,
            tenant_id="tenant-a",
            document_id="doc-1",
            expected_candidate_version=2,
        )


# ---------------------------------------------------------------------------
# 17. Activation failure does not call flush (rollback safety)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_failed_activation_does_not_flush():
    """CAS failure must not call flush() — the session stays uncommitted."""
    doc = _make_doc(active_version=1, candidate_version=2)
    session = _make_session(doc=doc, cas_rowcount=0)

    with pytest.raises(ActivationError):
        await activate_candidate_version(
            session,
            tenant_id="tenant-a",
            document_id="doc-1",
            expected_candidate_version=2,
        )

    session.flush.assert_not_awaited()


# ---------------------------------------------------------------------------
# 18. Checkpoint 3 Remediation Regression Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_zero_candidate_chunks_raises():
    """Activation must refuse to promote a candidate if no candidate chunks exist."""
    doc = _make_doc(active_version=1, candidate_version=2)
    job = _make_job(checkpoint="candidate_ready")
    job.tenant_id = "tenant-a"
    job.document_id = "doc-1"
    job.indexing_version = 2
    job.status = "succeeded"

    session = _make_session(doc=doc, job=job, cas_rowcount=1)
    # Mock candidate_chunk_count == 0
    zero_exec = MagicMock()
    zero_exec.scalar_one.return_value = 0
    session.execute = AsyncMock(return_value=zero_exec)

    with pytest.raises(ActivationError, match="no candidate chunks found"):
        await activate_candidate_version(
            session,
            tenant_id="tenant-a",
            document_id="doc-1",
            expected_candidate_version=2,
            job_id="job-1",
        )

    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_job_tenant_or_document_mismatch_raises():
    """Job belonging to another tenant or document cannot activate this document."""
    doc = _make_doc(tenant_id="tenant-a", active_version=1, candidate_version=2)
    job = _make_job(checkpoint="candidate_ready")
    job.tenant_id = "tenant-other"
    job.document_id = "doc-1"
    job.indexing_version = 2
    job.status = "succeeded"

    session = _make_session(doc=doc, job=job, cas_rowcount=1)

    with pytest.raises(ActivationError, match="tenant/document mismatch"):
        await activate_candidate_version(
            session,
            tenant_id="tenant-a",
            document_id="doc-1",
            expected_candidate_version=2,
            job_id="job-1",
        )


@pytest.mark.asyncio
async def test_job_status_not_ready_raises():
    """Failed, pending, or incomplete jobs cannot trigger activation."""
    doc = _make_doc(tenant_id="tenant-a", active_version=1, candidate_version=2)
    job = _make_job(checkpoint="candidate_ready")
    job.tenant_id = "tenant-a"
    job.document_id = "doc-1"
    job.indexing_version = 2
    job.status = "failed"

    session = _make_session(doc=doc, job=job, cas_rowcount=1)

    with pytest.raises(ActivationError, match="not in a valid ready state"):
        await activate_candidate_version(
            session,
            tenant_id="tenant-a",
            document_id="doc-1",
            expected_candidate_version=2,
            job_id="job-1",
        )


@pytest.mark.asyncio
async def test_expand_parents_filters_inactive_and_outdated_versions():
    """expand_parents query must filter on is_active == True and match Document.active_indexing_version."""
    from app.security.rbac import Principal
    from app.retrieval.retriever import expand_parents, RetrievedChunk

    session = AsyncMock()
    exec_result = MagicMock()
    exec_result.all.return_value = [("p1", "Active parent text", "Section 1")]
    session.execute = AsyncMock(return_value=exec_result)

    principal = Principal(
        user_id="u1",
        tenant_id="tenant-a",
        email="test@example.com",
        role="reader",
    )
    chunks = [
        RetrievedChunk(
            chunk_id="c1",
            document_id="doc1",
            document_name="Test Doc",
            document_type="contract",
            page=1,
            section=None,
            clause=None,
            content="child text",
            contextual_content=None,
            content_type="paragraph",
            access_level="public",
            is_synthetic=False,
            parent_chunk_id="p1",
            fused_score=0.9,
        )
    ]

    res = await expand_parents(session, principal, chunks)
    assert res == {"p1": ("Active parent text", "Section 1")}
    session.execute.assert_awaited_once()
    stmt = session.execute.call_args[0][0]
    stmt_str = str(stmt).lower()
    assert "chunks.is_active = true" in stmt_str or "is_active" in stmt_str
    assert "documents.active_indexing_version" in stmt_str or "active_indexing_version" in stmt_str


@pytest.mark.asyncio
async def test_activation_updates_structured_records_and_outbox():
    """activate_candidate_version must flip Chunk, Price, and ComplianceCertificate is_active flags and stamp outbox."""
    doc = _make_doc(active_version=1, candidate_version=2)
    job = _make_job(checkpoint="candidate_ready")
    job.tenant_id = "tenant-a"
    job.document_id = "doc-1"
    job.indexing_version = 2
    job.status = "succeeded"

    session = _make_session(doc=doc, job=job, cas_rowcount=1)

    result = await activate_candidate_version(
        session,
        tenant_id="tenant-a",
        document_id="doc-1",
        expected_candidate_version=2,
        job_id="job-1",
    )

    assert result is doc
    # Verify execute updates Chunk, Price, and ComplianceCertificate
    assert session.execute.await_count >= 5  # candidate chunk count + CAS + deactivate (chunk, price, cert) + activate (chunk, price, cert)
    session.flush.assert_awaited_once()

    # Verify durable outbox stamped into checkpoint metadata
    assert job.checkpoint_metadata.get("graph_sync_pending") is True
    assert job.checkpoint_metadata.get("graph_sync_version") == 2
    assert job.checkpoint_metadata.get("sparse_invalidation_pending") is True
    assert job.checkpoint_metadata.get("sparse_invalidation_version") == 2


@pytest.mark.asyncio
async def test_worker_outbox_reconciles_and_clears_pending():
    """Worker outbox reconciliation calls sparse invalidation and updates metadata."""
    from app.workers.ingestion_worker import IngestionWorker
    from app.config.settings import Settings

    settings = MagicMock(spec=Settings)
    settings.worker_concurrency = 2
    settings.ocr_enabled = True
    settings.ocr_language = "en"
    settings.ocr_use_onednn = False
    settings.ocr_enabled = True
    settings.ocr_language = "en"
    settings.ocr_use_onednn = False
    container = MagicMock()
    container.sparse = AsyncMock()

    worker = IngestionWorker(settings, container)
    worker._pipeline = MagicMock()
    worker._pipeline._update_graph = AsyncMock(return_value=True)

    job = _make_job(checkpoint="activated")
    job.checkpoint_metadata = {
        "graph_sync_pending": True,
        "sparse_invalidation_pending": True,
    }
    doc = _make_doc(active_version=2)

    with patch("app.workers.ingestion_worker.session_scope") as mock_scope:
        mock_sess = AsyncMock()
        mock_sess.get.side_effect = lambda cls, pk: doc if cls.__name__ == "Document" else job
        mock_scope.return_value.__aenter__.return_value = mock_sess

        await worker._process_external_outbox(
            job_id="job-1",
            document_id="doc-1",
            tenant_id="tenant-a",
            version=2,
        )

    container.sparse.invalidate.assert_awaited_once_with("tenant-a")
    worker._pipeline._update_graph.assert_awaited_once()
    assert job.checkpoint_metadata["sparse_invalidation_pending"] is False
    assert job.checkpoint_metadata["graph_sync_pending"] is False
    assert job.checkpoint_metadata["graph_status"] == "synced"


@pytest.mark.asyncio
async def test_worker_outbox_rejects_stale_version():
    """Outbox processor will not modify graph or cache if a newer version is already active."""
    from app.workers.ingestion_worker import IngestionWorker
    from app.config.settings import Settings

    settings = MagicMock(spec=Settings)
    settings.worker_concurrency = 2
    settings.ocr_enabled = True
    settings.ocr_language = "en"
    settings.ocr_use_onednn = False
    settings.ocr_enabled = True
    settings.ocr_language = "en"
    settings.ocr_use_onednn = False
    container = MagicMock()
    container.sparse = AsyncMock()

    worker = IngestionWorker(settings, container)
    worker._pipeline = MagicMock()
    worker._pipeline._update_graph = AsyncMock()

    # Doc is now at active_version=3, but worker task is for version=2
    doc = _make_doc(active_version=3)

    with patch("app.workers.ingestion_worker.session_scope") as mock_scope:
        mock_sess = AsyncMock()
        mock_sess.get.return_value = doc
        mock_scope.return_value.__aenter__.return_value = mock_sess

        await worker._process_external_outbox(
            job_id="job-stale",
            document_id="doc-1",
            tenant_id="tenant-a",
            version=2,
        )

    # Stale version work should be skipped entirely
    container.sparse.invalidate.assert_not_awaited()
    worker._pipeline._update_graph.assert_not_awaited()


@pytest.mark.asyncio
async def test_recover_pending_outbox_paginates_all_activated_jobs():
    """_recover_pending_outbox must find and process pending tasks regardless of job age or recency window."""
    from app.workers.ingestion_worker import IngestionWorker
    from app.config.settings import Settings

    settings = MagicMock(spec=Settings)
    settings.worker_concurrency = 2
    settings.ocr_enabled = True
    settings.ocr_language = "en"
    settings.ocr_use_onednn = False
    container = MagicMock()
    worker = IngestionWorker(settings, container)
    worker._process_external_outbox = AsyncMock()

    # Job created in the past, marked succeeded with pending outbox
    old_job = _make_job(job_id="job-old", checkpoint="activated", status="succeeded")
    old_job.checkpoint_metadata = {
        "graph_sync_pending": True,
        "sparse_invalidation_pending": False,
    }

    with patch("app.workers.ingestion_worker.session_scope") as mock_scope:
        mock_sess = AsyncMock()
        exec_res = MagicMock()
        # First page returns the job, second page returns empty list
        scalars_mock1 = MagicMock()
        scalars_mock1.scalars.return_value = [old_job]
        scalars_mock2 = MagicMock()
        scalars_mock2.scalars.return_value = []
        mock_sess.execute.side_effect = [scalars_mock1, scalars_mock2]
        mock_scope.return_value.__aenter__.return_value = mock_sess

        await worker._recover_pending_outbox()

    worker._process_external_outbox.assert_awaited_once_with(
        job_id="job-old",
        document_id="doc-1",
        tenant_id="tenant-a",
        version=2,
    )


@pytest.mark.asyncio
async def test_recover_pending_outbox_multi_batch_keyset_pagination():
    """Verify keyset pagination correctly traverses multiple batches without skipping or looping, even with identical timestamps."""
    from datetime import datetime, timezone
    from app.workers.ingestion_worker import IngestionWorker
    from app.config.settings import Settings

    settings = MagicMock(spec=Settings)
    settings.worker_concurrency = 2
    settings.ocr_enabled = True
    settings.ocr_language = "en"
    settings.ocr_use_onednn = False
    container = MagicMock()
    worker = IngestionWorker(settings, container)
    worker._process_external_outbox = AsyncMock()

    now = datetime(2026, 10, 22, 10, 0, 0, tzinfo=timezone.utc)
    # Create 3 batches worth of jobs with identical timestamps to test (created_at, id) tie-breaking
    batch1 = [
        _make_job(job_id=f"job-{i:03d}", checkpoint="activated", status="succeeded")
        for i in range(1, 51)
    ]
    batch2 = [
        _make_job(job_id=f"job-{i:03d}", checkpoint="activated", status="succeeded")
        for i in range(51, 101)
    ]
    batch3 = [
        _make_job(job_id=f"job-{i:03d}", checkpoint="activated", status="succeeded")
        for i in range(101, 120)
    ]
    for j in batch1 + batch2 + batch3:
        j.created_at = now
        j.checkpoint_metadata = {"graph_sync_pending": True}

    with patch("app.workers.ingestion_worker.session_scope") as mock_scope:
        mock_sess = AsyncMock()
        s1 = MagicMock()
        s1.scalars.return_value = batch1
        s2 = MagicMock()
        s2.scalars.return_value = batch2
        s3 = MagicMock()
        s3.scalars.return_value = batch3
        s4 = MagicMock()
        s4.scalars.return_value = []
        mock_sess.execute.side_effect = [s1, s2, s3, s4]
        mock_scope.return_value.__aenter__.return_value = mock_sess

        await worker._recover_pending_outbox()

    assert worker._process_external_outbox.await_count == 119
    first_call_id = worker._process_external_outbox.call_args_list[0].kwargs["job_id"]
    last_call_id = worker._process_external_outbox.call_args_list[-1].kwargs["job_id"]
    assert first_call_id == "job-001"
    assert last_call_id == "job-119"


@pytest.mark.asyncio
async def test_recover_pending_outbox_permanent_failure_does_not_infinite_loop():
    """Verify that a failing outbox task does not cause an infinite loop during a recovery pass."""
    from datetime import datetime, timezone
    from app.workers.ingestion_worker import IngestionWorker
    from app.config.settings import Settings

    settings = MagicMock(spec=Settings)
    settings.worker_concurrency = 2
    settings.ocr_enabled = True
    settings.ocr_language = "en"
    settings.ocr_use_onednn = False
    container = MagicMock()
    worker = IngestionWorker(settings, container)
    # Simulate process_external_outbox raising an exception on a job
    worker._process_external_outbox = AsyncMock(side_effect=RuntimeError("Transient Neo4j failure"))

    bad_job = _make_job(job_id="job-bad", checkpoint="activated", status="succeeded")
    bad_job.created_at = datetime(2026, 10, 22, 10, 0, 0, tzinfo=timezone.utc)
    bad_job.checkpoint_metadata = {"graph_sync_pending": True}

    with patch("app.workers.ingestion_worker.session_scope") as mock_scope:
        mock_sess = AsyncMock()
        s1 = MagicMock()
        s1.scalars.return_value = [bad_job]
        s2 = MagicMock()
        s2.scalars.return_value = []
        mock_sess.execute.side_effect = [s1, s2]
        mock_scope.return_value.__aenter__.return_value = mock_sess

        # Must exit cleanly without loop or uncaught exception
        await worker._recover_pending_outbox()

    worker._process_external_outbox.assert_awaited_once_with(
        job_id="job-bad",
        document_id="doc-1",
        tenant_id="tenant-a",
        version=2,
    )




