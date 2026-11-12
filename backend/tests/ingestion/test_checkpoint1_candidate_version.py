"""Checkpoint 1 — Candidate version foundation tests.

Covers:
1. Initial ingestion creates chunks with indexing_version=1, is_active=True.
2. reserve_candidate_version() stamps candidate_indexing_version on the document
   and creates a job carrying that version; it never touches active_indexing_version.
3. Duplicate / concurrent reservation raises VersionConflictError.
4. Candidate chunks are persisted with indexing_version=<candidate>, is_active=False.
5. Active chunks (is_active=True) remain untouched after candidate preparation.

Stop condition: candidate creation cannot overwrite or deactivate the existing
active version.

Schema requirement: tests are database-only (SQLite in-memory) and never touch
Qdrant, Neo4j, or any real external store.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.db.models as _models  # noqa: F401 — registers all ORM metadata
from app.db.base import Base
from app.db.models import Chunk, Document, IngestionJob
from app.core.errors import VersionConflictError
from app.ingestion.jobs import create_job, reserve_candidate_version


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
async def engine():
    """In-memory SQLite engine, schema auto-created."""
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture()
async def session(engine):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s


async def _make_document(session: AsyncSession, *, tenant_id: str = "t1") -> Document:
    """Persist a minimal indexed Document and return it."""
    doc = Document(
        tenant_id=tenant_id,
        document_type="contract",
        title="Test contract",
        filename="test.pdf",
        mime_type="application/pdf",
        status="indexed",
        stage="indexed",
        checksum=f"sha256-{datetime.now(UTC).timestamp()}",
        active_indexing_version=1,
        candidate_indexing_version=None,
    )
    session.add(doc)
    await session.flush()
    return doc


async def _make_active_chunk(
    session: AsyncSession, document_id: str, *, tenant_id: str = "t1"
) -> Chunk:
    """Persist a single active chunk for a document."""
    chunk = Chunk(
        tenant_id=tenant_id,
        document_id=document_id,
        content="Active chunk content",
        contextual_content="Active chunk content",
        content_type="paragraph",
        indexing_version=1,
        is_active=True,
    )
    session.add(chunk)
    await session.flush()
    return chunk


def _make_pipeline(settings=None):
    """Return an IngestionPipeline with all external deps mocked out."""
    from app.ingestion.pipeline import IngestionPipeline
    from app.config.settings import Settings

    if settings is None:
        settings = Settings(
            app_env="development",
            jwt_secret="test-secret-not-for-production",
            jwt_algorithm="HS256",
            database_url="sqlite+aiosqlite:///:memory:",
            auto_create_schema=False,
            vector_provider="local",
            graph_provider="local",
            cache_provider="memory",
            storage_provider="local",
        )
    container = MagicMock()
    container.graph = MagicMock()
    return IngestionPipeline(container, settings)


def _patched_scope_factory(factory):
    """Return a session_scope context manager backed by the given sessionmaker."""

    @asynccontextmanager
    async def _scope():
        async with factory() as s:
            yield s
            await s.commit()

    return _scope


# ---------------------------------------------------------------------------
# 1. Initial ingestion — job carries indexing_version=1 (active version)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestInitialIngestion:
    async def test_initial_job_carries_indexing_version_1(self, session: AsyncSession):
        """create_job for a new document stores indexing_version=1."""
        doc = await _make_document(session)
        job = await create_job(
            session,
            tenant_id=doc.tenant_id,
            document_id=doc.id,
            indexing_version=1,
        )
        await session.commit()

        fresh_job = await session.get(IngestionJob, job.id)
        assert fresh_job is not None
        assert fresh_job.indexing_version == 1
        assert fresh_job.status == "queued"

    async def test_initial_chunk_is_active(self, session: AsyncSession):
        """Chunks written during initial ingestion have is_active=True."""
        doc = await _make_document(session)
        chunk = await _make_active_chunk(session, doc.id)
        await session.commit()

        fresh_chunk = await session.get(Chunk, chunk.id)
        assert fresh_chunk is not None
        assert fresh_chunk.is_active is True
        assert fresh_chunk.indexing_version == 1


# ---------------------------------------------------------------------------
# 2. reserve_candidate_version — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestReserveCandidateVersion:
    async def test_reserve_increments_from_active(self, session: AsyncSession):
        """Candidate version is active + 1; document gains candidate_indexing_version."""
        doc = await _make_document(session)
        doc_id = doc.id

        _updated_doc, _job = await reserve_candidate_version(
            session, tenant_id=doc.tenant_id, document_id=doc_id
        )
        await session.commit()

        fresh_doc = await session.get(Document, doc_id)
        assert fresh_doc is not None
        assert fresh_doc.active_indexing_version == 1, "active version must not change"
        assert fresh_doc.candidate_indexing_version == 2

    async def test_job_carries_candidate_version(self, session: AsyncSession):
        """The created job is durably associated with the candidate version."""
        doc = await _make_document(session)

        _, job = await reserve_candidate_version(
            session, tenant_id=doc.tenant_id, document_id=doc.id
        )
        await session.commit()

        fresh_job = await session.get(IngestionJob, job.id)
        assert fresh_job is not None
        assert fresh_job.indexing_version == 2
        assert fresh_job.status == "queued"

    async def test_active_version_never_changes(self, session: AsyncSession):
        """active_indexing_version must remain 1 after candidate reservation."""
        doc = await _make_document(session)
        original_active = doc.active_indexing_version

        await reserve_candidate_version(
            session, tenant_id=doc.tenant_id, document_id=doc.id
        )
        await session.commit()

        fresh_doc = await session.get(Document, doc.id)
        assert fresh_doc.active_indexing_version == original_active


# ---------------------------------------------------------------------------
# 3. Duplicate / concurrent reservation protection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestConcurrencyProtection:
    async def test_duplicate_reservation_raises(self, session: AsyncSession):
        """A second reserve call while candidate is pending raises VersionConflictError."""
        doc = await _make_document(session)

        await reserve_candidate_version(
            session, tenant_id=doc.tenant_id, document_id=doc.id
        )
        await session.flush()

        with pytest.raises(VersionConflictError):
            await reserve_candidate_version(
                session, tenant_id=doc.tenant_id, document_id=doc.id
            )

    async def test_active_job_blocks_new_create_job(self, session: AsyncSession):
        """create_job raises VersionConflictError if an active job already exists."""
        doc = await _make_document(session)
        doc.status = "queued"

        await create_job(
            session,
            tenant_id=doc.tenant_id,
            document_id=doc.id,
            indexing_version=1,
        )
        await session.flush()

        with pytest.raises(VersionConflictError):
            await create_job(
                session,
                tenant_id=doc.tenant_id,
                document_id=doc.id,
                indexing_version=1,
            )

    async def test_wrong_tenant_blocked(self, session: AsyncSession):
        """reserve_candidate_version rejects a mismatched tenant_id."""
        doc = await _make_document(session, tenant_id="tenant-a")

        with pytest.raises(VersionConflictError):
            await reserve_candidate_version(
                session, tenant_id="tenant-b", document_id=doc.id
            )


# ---------------------------------------------------------------------------
# 4. Candidate chunk persistence — is_active=False, correct indexing_version
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCandidateChunkPersistence:
    async def test_candidate_chunks_persisted_inactive(self, engine):
        """Chunks written under a candidate version have is_active=False."""
        from app.ingestion.chunking import ChunkDraft
        from app.ingestion.metadata import ExtractedMetadata
        import app.db.session as db_session_module

        factory = async_sessionmaker(engine, expire_on_commit=False)

        async with factory() as s:
            doc = await _make_document(s)
            active_chunk = await _make_active_chunk(s, doc.id)
            await s.commit()
            document_id = doc.id
            tenant_id = doc.tenant_id
            active_chunk_id = active_chunk.id

        pipeline = _make_pipeline()

        draft = ChunkDraft(
            content="Candidate text",
            content_type="paragraph",
            page_number=1,
            token_count=5,
        )
        meta = ExtractedMetadata(
            document_type="contract",
            supplier_name=None,
            contract_number=None,
            version=None,
            effective_date=None,
            expiry_date=None,
            is_synthetic=False,
        )

        with (
            patch.object(db_session_module, "session_scope", _patched_scope_factory(factory)),
            # The pipeline binds session_scope at import time, so patching only
            # app.db.session leaves it writing to the real database.
            patch("app.ingestion.pipeline.session_scope", _patched_scope_factory(factory)),
        ):
            await pipeline._persist_chunks(
                [draft],
                tenant_id=tenant_id,
                document_id=document_id,
                page_ids={},
                supplier_id=None,
                contract_id=None,
                meta=meta,
                indexing_version=2,
                is_active=False,
            )

        async with factory() as s:
            all_chunks = (
                await s.execute(select(Chunk).where(Chunk.document_id == document_id))
            ).scalars().all()

            candidate_chunks = [c for c in all_chunks if c.indexing_version == 2]
            assert len(candidate_chunks) >= 1, "Candidate chunk must be written"
            for c in candidate_chunks:
                assert c.is_active is False, f"Candidate chunk {c.id} must be inactive"
                assert c.indexing_version == 2

            # Original active chunk must still be present and active
            original = next((c for c in all_chunks if c.id == active_chunk_id), None)
            assert original is not None, "Original active chunk must not be deleted"
            assert original.is_active is True, "Original active chunk must remain active"
            assert original.indexing_version == 1, "Active chunk version must not change"


# ---------------------------------------------------------------------------
# 5. Safety invariant: active chunks survive candidate preparation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestActiveSafetyInvariant:
    async def test_candidate_version_strictly_greater_than_active(self, session: AsyncSession):
        """The reserved candidate version must always be > active_indexing_version."""
        doc = await _make_document(session)
        assert doc.active_indexing_version == 1

        _, job = await reserve_candidate_version(
            session, tenant_id=doc.tenant_id, document_id=doc.id
        )
        await session.commit()

        fresh_doc = await session.get(Document, doc.id)
        assert fresh_doc.candidate_indexing_version > fresh_doc.active_indexing_version

    async def test_active_chunks_survive_candidate_write(self, engine):
        """Active chunks (is_active=True) are never removed during candidate preparation."""
        from app.ingestion.chunking import ChunkDraft
        from app.ingestion.metadata import ExtractedMetadata
        import app.db.session as db_session_module

        factory = async_sessionmaker(engine, expire_on_commit=False)

        async with factory() as s:
            doc = await _make_document(s)
            ch1 = await _make_active_chunk(s, doc.id)
            ch2 = await _make_active_chunk(s, doc.id)
            await s.commit()
            document_id = doc.id
            tenant_id = doc.tenant_id
            ch1_id, ch2_id = ch1.id, ch2.id

        pipeline = _make_pipeline()
        draft = ChunkDraft(
            content="Candidate replacement",
            content_type="paragraph",
            page_number=1,
            token_count=4,
        )
        meta = ExtractedMetadata(
            document_type="contract",
            supplier_name=None,
            contract_number=None,
            version=None,
            effective_date=None,
            expiry_date=None,
            is_synthetic=False,
        )

        with (
            patch.object(db_session_module, "session_scope", _patched_scope_factory(factory)),
            # The pipeline binds session_scope at import time, so patching only
            # app.db.session leaves it writing to the real database.
            patch("app.ingestion.pipeline.session_scope", _patched_scope_factory(factory)),
        ):
            await pipeline._persist_chunks(
                [draft],
                tenant_id=tenant_id,
                document_id=document_id,
                page_ids={},
                supplier_id=None,
                contract_id=None,
                meta=meta,
                indexing_version=2,
                is_active=False,
            )

        async with factory() as s:
            all_chunks = (
                await s.execute(select(Chunk).where(Chunk.document_id == document_id))
            ).scalars().all()

            ids_present = {c.id for c in all_chunks}
            assert ch1_id in ids_present, "Active chunk 1 must not be deleted"
            assert ch2_id in ids_present, "Active chunk 2 must not be deleted"
            for c in all_chunks:
                if c.id in {ch1_id, ch2_id}:
                    assert c.is_active is True
                    assert c.indexing_version == 1

    async def test_delete_artifacts_skips_active_in_candidate_mode(self, engine):
        """_delete_existing_artifacts in candidate mode must not delete active chunks."""
        import app.db.session as db_session_module

        factory = async_sessionmaker(engine, expire_on_commit=False)

        async with factory() as s:
            doc = await _make_document(s)
            ch = await _make_active_chunk(s, doc.id)
            await s.commit()
            document_id = doc.id
            chunk_id = ch.id

        pipeline = _make_pipeline()

        async with factory() as s:
            fresh_doc = await s.get(Document, document_id)
            # candidate_version=2 is strictly greater than active_version=1
            await pipeline._delete_existing_artifacts(s, fresh_doc, candidate_version=2)
            await s.commit()

        async with factory() as s:
            surviving_chunk = await s.get(Chunk, chunk_id)
            assert surviving_chunk is not None, "Active chunk must survive candidate artifact deletion"
            assert surviving_chunk.is_active is True
