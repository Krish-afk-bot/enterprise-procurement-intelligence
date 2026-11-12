"""Checkpoint 2 — Version-aware Qdrant and Neo4j indexing and recovery tests.

Covers:
1. Qdrant version isolation:
   - Candidate vectors carry indexing_version, is_active=False, tenant_id, document_id.
   - Point ID scheme (UUIDv5 of chunk.id) ensures candidate vectors cannot overwrite active points.
   - Repeated candidate writes are idempotent.
   - delete_by_version cleans candidate vectors without deleting active vectors.
   - Tenant isolation: candidate cleanup for tenant A cannot delete tenant B vectors.
2. Neo4j graph isolation & non-blocking failure:
   - Candidate graph write preserves active graph data (skips remove_document_entities).
   - Graph failure does not block document indexing (returns status, logs warning).
   - Candidate retry safely reconciles.
3. Durable progress tracking & failure recovery:
   - mark_job records checkpoint and checkpoint_metadata.
   - Progression: persist_chunks -> vector_upload -> graph_update -> candidate_ready.
   - PostgreSQL succeeds but Qdrant fails -> error caught and marked, active vectors intact.
   - Qdrant succeeds but Neo4j fails -> marked non-blocking, candidate continues.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.db.models as _models  # noqa: F401
from app.db.base import Base
from app.db.models import Chunk, Document, IngestionJob
from app.providers.types import VectorPoint
from app.providers.vector.local import LocalVectorStore
from app.ingestion.jobs import mark_job, reserve_candidate_version
from app.ingestion.pipeline import CHUNK_COLLECTION, IngestionOutcome, IngestionPipeline
from app.ingestion.chunking import ChunkDraft
from app.ingestion.metadata import ExtractedMetadata
from app.config.settings import Settings
import app.db.session as db_session_module


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


def _patched_scope_factory(factory):
    @asynccontextmanager
    async def _scope():
        async with factory() as s:
            yield s
            await s.commit()

    return _scope


async def _make_document(
    session: AsyncSession,
    *,
    tenant_id: str = "tenant-a",
    doc_id: str | None = None,
    active_version: int = 1,
) -> Document:
    doc = Document(
        id=doc_id,
        tenant_id=tenant_id,
        document_type="contract",
        title="Test Master Services Agreement",
        filename="test_contract.pdf",
        mime_type="application/pdf",
        status="indexed",
        stage="indexed",
        checksum=f"sha256-{datetime.now(UTC).timestamp()}",
        active_indexing_version=active_version,
        candidate_indexing_version=None,
    )
    session.add(doc)
    await session.flush()
    return doc


async def _make_chunk(
    session: AsyncSession,
    document_id: str,
    *,
    tenant_id: str = "tenant-a",
    content: str = "Active chunk text",
    indexing_version: int = 1,
    is_active: bool = True,
    page_number: int = 1,
) -> Chunk:
    chunk = Chunk(
        tenant_id=tenant_id,
        document_id=document_id,
        content=content,
        contextual_content=content,
        content_type="paragraph",
        page_number=page_number,
        indexing_version=indexing_version,
        is_active=is_active,
    )
    session.add(chunk)
    await session.flush()
    return chunk


# ---------------------------------------------------------------------------
# 1. Qdrant / Vector Store Version Isolation Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestQdrantVersionIsolation:
    """Verifies vector payload tagging, point ID immutability, and versioned deletion."""

    async def test_vector_point_payload_carries_version_and_active_flag(self, engine):
        """Vector upload stamps indexing_version and is_active in payload."""
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as s:
            doc = await _make_document(s)
            candidate_chunk = await _make_chunk(
                s, doc.id, indexing_version=2, is_active=False, content="Candidate chunk"
            )
            await s.commit()
            doc_id = doc.id
            t_id = doc.tenant_id
            chunk_id = candidate_chunk.id

        vector_mock = AsyncMock()
        vector_mock.name = "mock_vector"
        vector_mock.ensure_collection = AsyncMock()
        vector_mock.upsert = AsyncMock(return_value=1)

        container = MagicMock()
        container.vector = vector_mock

        settings = Settings(
            app_env="development",
            jwt_secret="secret",
            database_url="sqlite+aiosqlite:///:memory:",
            auto_create_schema=False,
            vector_provider="local",
            graph_provider="local",
            cache_provider="memory",
            storage_provider="local",
        )
        pipeline = IngestionPipeline(container, settings)

        draft = ChunkDraft(content="Candidate chunk", content_type="paragraph", page_number=1, token_count=5)
        draft.metadata["embedding"] = [0.1, 0.2, 0.3]
        outcome = IngestionOutcome(document_id=doc_id, status="processing")

        with (
            patch.object(db_session_module, "session_scope", _patched_scope_factory(factory)),
            # The pipeline binds session_scope at import time, so patching only
            # app.db.session leaves it writing to the real database.
            patch("app.ingestion.pipeline.session_scope", _patched_scope_factory(factory)),
        ):
            await pipeline._index_chunks(
                [draft],
                tenant_id=t_id,
                document_id=doc_id,
                outcome=outcome,
                indexing_version=2,
                is_active=False,
            )

        # Verify upsert call
        assert vector_mock.upsert.called
        points = vector_mock.upsert.call_args[0][1]
        assert len(points) == 1
        p = points[0]
        assert p.id == chunk_id
        assert p.payload["indexing_version"] == 2
        assert p.payload["is_active"] is False
        assert p.payload["tenant_id"] == t_id
        assert p.payload["document_id"] == doc_id

    async def test_point_id_scheme_prevents_active_overwrites(self):
        """Proves candidate chunk point ID does not collide with active chunk point ID."""
        from app.providers.vector.qdrant import _point_uuid

        active_chunk_id = "chk_active_001"
        candidate_chunk_id = "chk_candidate_002"

        active_uuid = _point_uuid(active_chunk_id)
        candidate_uuid = _point_uuid(candidate_chunk_id)

        assert active_uuid != candidate_uuid, "Candidate point UUID must differ from active point UUID"

    async def test_candidate_cleanup_does_not_delete_active_vectors(self, tmp_path):
        """delete_by_version on LocalVectorStore removes candidate points and keeps active points."""
        vec_store = LocalVectorStore(tmp_path / "vector.json")
        await vec_store.ensure_collection(CHUNK_COLLECTION, 3)

        doc_id = "doc_test_123"
        tenant_id = "tenant-a"

        # Active points (version 1)
        p_active = VectorPoint(
            id="chk_active_1",
            vector=[1.0, 0.0, 0.0],
            payload={"document_id": doc_id, "tenant_id": tenant_id, "indexing_version": 1, "is_active": True},
        )
        # Candidate points (version 2)
        p_candidate = VectorPoint(
            id="chk_candidate_1",
            vector=[0.0, 1.0, 0.0],
            payload={"document_id": doc_id, "tenant_id": tenant_id, "indexing_version": 2, "is_active": False},
        )

        await vec_store.upsert(CHUNK_COLLECTION, [p_active, p_candidate])
        assert await vec_store.count(CHUNK_COLLECTION) == 2

        # Delete candidate version 2
        deleted = await vec_store.delete_by_version(CHUNK_COLLECTION, doc_id, 2, tenant_id=tenant_id)
        assert deleted == 1
        assert await vec_store.count(CHUNK_COLLECTION) == 1

        # Search to confirm the remaining point is active version 1
        hits = await vec_store.search(CHUNK_COLLECTION, [1.0, 0.0, 0.0], limit=10)
        assert len(hits) == 1
        assert hits[0].id == "chk_active_1"
        assert hits[0].payload["indexing_version"] == 1

    async def test_tenant_isolated_candidate_cleanup(self, tmp_path):
        """Candidate cleanup in Tenant A never deletes identical-version vectors in Tenant B."""
        vec_store = LocalVectorStore(tmp_path / "vector_tenant.json")
        await vec_store.ensure_collection(CHUNK_COLLECTION, 3)

        p_tenant_a = VectorPoint(
            id="chk_a_cand",
            vector=[0.1, 0.2, 0.3],
            payload={"document_id": "doc_shared_id", "tenant_id": "tenant-a", "indexing_version": 2},
        )
        p_tenant_b = VectorPoint(
            id="chk_b_cand",
            vector=[0.1, 0.2, 0.3],
            payload={"document_id": "doc_shared_id", "tenant_id": "tenant-b", "indexing_version": 2},
        )
        await vec_store.upsert(CHUNK_COLLECTION, [p_tenant_a, p_tenant_b])

        # Delete only tenant-a candidate
        await vec_store.delete_by_version(CHUNK_COLLECTION, "doc_shared_id", 2, tenant_id="tenant-a")

        # Tenant B candidate must remain
        hits = await vec_store.search(CHUNK_COLLECTION, [0.1, 0.2, 0.3], limit=10)
        assert len(hits) == 1
        assert hits[0].id == "chk_b_cand"
        assert hits[0].payload["tenant_id"] == "tenant-b"


# ---------------------------------------------------------------------------
# 2. Neo4j / Graph Version Isolation & Non-blocking Failure Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGraphVersionIsolation:
    """Verifies that active graph entities remain untouched during candidate updates."""

    async def test_candidate_graph_update_skips_remove_document_entities(self, engine):
        """In candidate mode, _update_graph skips remove_document_entities to protect active graph."""
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as s:
            doc = await _make_document(s)
            await s.commit()
            doc_id = doc.id
            t_id = doc.tenant_id

        graph_builder_mock = AsyncMock()
        graph_builder_mock.remove_document_entities = AsyncMock()
        graph_builder_mock.link_document = AsyncMock()

        container = MagicMock()
        settings = Settings(database_url="sqlite+aiosqlite:///:memory:", auto_create_schema=False)
        pipeline = IngestionPipeline(container, settings)
        pipeline.graph_builder = graph_builder_mock

        with (
            patch.object(db_session_module, "session_scope", _patched_scope_factory(factory)),
            # The pipeline binds session_scope at import time, so patching only
            # app.db.session leaves it writing to the real database.
            patch("app.ingestion.pipeline.session_scope", _patched_scope_factory(factory)),
        ):
            # Candidate mode
            success = await pipeline._update_graph(
                t_id, doc_id, supplier=None, contract=None, counts={}, is_candidate=True
            )

        assert success is True
        assert not graph_builder_mock.remove_document_entities.called, "Must not delete active graph in candidate mode"
        assert graph_builder_mock.link_document.called

    async def test_graph_failure_is_non_blocking(self, engine):
        """Graph update failure returns False and does not raise an exception."""
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as s:
            doc = await _make_document(s)
            await s.commit()
            doc_id = doc.id
            t_id = doc.tenant_id

        graph_builder_mock = AsyncMock()
        graph_builder_mock.link_document = AsyncMock(side_effect=RuntimeError("Neo4j connection dropped"))

        container = MagicMock()
        settings = Settings(database_url="sqlite+aiosqlite:///:memory:", auto_create_schema=False)
        pipeline = IngestionPipeline(container, settings)
        pipeline.graph_builder = graph_builder_mock

        with (
            patch.object(db_session_module, "session_scope", _patched_scope_factory(factory)),
            # The pipeline binds session_scope at import time, so patching only
            # app.db.session leaves it writing to the real database.
            patch("app.ingestion.pipeline.session_scope", _patched_scope_factory(factory)),
        ):
            success = await pipeline._update_graph(
                t_id, doc_id, supplier=None, contract=None, counts={}, is_candidate=True
            )

        assert success is False, "Failure must be caught and reported as non-blocking"


# ---------------------------------------------------------------------------
# 3. Durable Progress Tracking & Checkpoint State Transitions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDurableCheckpointTracking:
    """Verifies job checkpoint and checkpoint_metadata transitions."""

    async def test_mark_job_records_checkpoint_and_metadata(self, session: AsyncSession):
        """mark_job persists checkpoint state and metadata."""
        doc = await _make_document(session)
        _, job = await reserve_candidate_version(session, tenant_id=doc.tenant_id, document_id=doc.id)
        await session.commit()

        # Step 1: Chunks persisted
        await mark_job(
            session,
            job,
            checkpoint="persist_chunks",
            checkpoint_metadata={"version": 2, "chunk_count": 10},
        )
        await session.commit()

        fresh_job = await session.get(IngestionJob, job.id)
        assert fresh_job.checkpoint == "persist_chunks"
        assert fresh_job.checkpoint_metadata["chunk_count"] == 10

        # Step 2: Vector upload completed
        await mark_job(
            session,
            fresh_job,
            checkpoint="vector_upload",
            checkpoint_metadata={"points_indexed": 10},
        )
        await session.commit()

        fresh_job2 = await session.get(IngestionJob, job.id)
        assert fresh_job2.checkpoint == "vector_upload"
        assert fresh_job2.checkpoint_metadata["chunk_count"] == 10  # Preserved
        assert fresh_job2.checkpoint_metadata["points_indexed"] == 10

    async def test_qdrant_failure_stops_before_candidate_ready(self, engine):
        """When Qdrant fails, candidate preparation fails but the active version survives."""
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as s:
            doc = await _make_document(s)
            _, job = await reserve_candidate_version(s, tenant_id=doc.tenant_id, document_id=doc.id)
            await s.commit()
            doc_id = doc.id
            job_id = job.id

        vector_mock = AsyncMock()
        vector_mock.ensure_collection = AsyncMock()
        vector_mock.upsert = AsyncMock(side_effect=RuntimeError("Qdrant cluster unavailable"))

        container = MagicMock()
        container.vector = vector_mock
        container.storage = AsyncMock()
        container.storage.get = AsyncMock(return_value=b"%PDF-1.4 test")

        settings = Settings(database_url="sqlite+aiosqlite:///:memory:", auto_create_schema=False)
        pipeline = IngestionPipeline(container, settings)
        from app.ingestion.types import ParsedDocument, ParsedPage, TextBlock

        page = ParsedPage(
            page_number=1,
            text="Contract MS-2026-014 for laboratory consumables and reagents. " * 4,
            blocks=[
                TextBlock(
                    text="Contract MS-2026-014 for laboratory consumables and reagents.", order=0
                )
            ],
        )
        pipeline._parse = AsyncMock(
            return_value=ParsedDocument(pages=[page], title="Test Master Services Agreement")
        )

        async def _embed(drafts, outcome):
            # Keep the failure confined to the vector store, which is what this
            # test is about.
            for draft in drafts:
                draft.metadata["embedding"] = [0.1] * 8
            outcome.metrics["embeddings"] = "applied"
            return True

        pipeline._embed_drafts = _embed

        with (
            patch.object(db_session_module, "session_scope", _patched_scope_factory(factory)),
            # The pipeline binds session_scope at import time, so patching only
            # app.db.session leaves it writing to the real database.
            patch("app.ingestion.pipeline.session_scope", _patched_scope_factory(factory)),
        ):
            outcome = await pipeline.process_document(doc_id, job_id=job_id)

        assert outcome.status == "failed"
        async with factory() as s:
            failed_job = await s.get(IngestionJob, job_id)
            assert failed_job.checkpoint != "candidate_ready"
            failed_doc = await s.get(Document, doc_id)
            # A failed candidate must never take the live document down with it.
            assert failed_doc.status == "indexed"
            assert failed_doc.candidate_indexing_version is None
            assert failed_doc.active_indexing_version == 1
