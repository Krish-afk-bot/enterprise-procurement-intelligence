"""Deleting a document must not leave derived rows behind.

SQLite does not enforce ``ON DELETE CASCADE`` unless foreign keys are enabled on
every connection, so the delete path removes derived rows explicitly and a
recovery sweep clears anything orphaned by earlier deletions.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import (
    Chunk,
    ComplianceCertificate,
    Document,
    IngestionJob,
    Price,
    Tenant,
)
from app.ingestion.cleanup import purge_orphaned_derived_rows
from app.services.documents import delete_document


class _Vector:
    async def delete_by_document(self, collection: str, document_id: str) -> int:
        return 0


class _Graph:
    async def delete_subgraph(self, document_id: str) -> int:
        return 0


class _Container:
    vector = _Vector()
    graph = _Graph()
    sparse = None
    storage = None


class _Principal:
    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id

    def require(self, permission: str) -> None:
        return None

    def can_read_level(self, level: str) -> bool:
        return True


@pytest.fixture
async def factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def _seed(factory) -> tuple[str, str]:
    moment = datetime.now(UTC)
    async with factory() as session:
        tenant = Tenant(name="Delete tenant", slug="delete-tenant")
        session.add(tenant)
        await session.flush()
        document = Document(
            tenant_id=tenant.id,
            title="Framework agreement",
            filename="framework.pdf",
            checksum="delete-checksum",
        )
        session.add(document)
        await session.flush()
        session.add_all(
            [
                Chunk(tenant_id=tenant.id, document_id=document.id, content="clause 1"),
                Price(tenant_id=tenant.id, source_document_id=document.id, unit_price=9.5),
                ComplianceCertificate(
                    tenant_id=tenant.id,
                    source_document_id=document.id,
                    certificate_type="iso_14001",
                ),
                IngestionJob(
                    tenant_id=tenant.id,
                    document_id=document.id,
                    status="succeeded",
                    stage="indexed",
                    queued_at=moment,
                ),
            ]
        )
        await session.commit()
        return tenant.id, document.id


async def _counts(factory) -> dict[str, int]:
    async with factory() as session:
        return {
            "chunks": int((await session.execute(select(func.count()).select_from(Chunk))).scalar_one()),
            "prices": int((await session.execute(select(func.count()).select_from(Price))).scalar_one()),
            "certificates": int(
                (await session.execute(select(func.count()).select_from(ComplianceCertificate))).scalar_one()
            ),
            "jobs": int(
                (await session.execute(select(func.count()).select_from(IngestionJob))).scalar_one()
            ),
            "documents": int(
                (await session.execute(select(func.count()).select_from(Document))).scalar_one()
            ),
        }


@pytest.mark.asyncio
async def test_delete_removes_derived_rows(factory):
    tenant_id, document_id = await _seed(factory)

    async with factory() as session:
        await delete_document(session, _Container(), _Principal(tenant_id), document_id)
        await session.commit()

    assert await _counts(factory) == {
        "chunks": 0,
        "prices": 0,
        "certificates": 0,
        "jobs": 0,
        "documents": 0,
    }


@pytest.mark.asyncio
async def test_orphan_purge_clears_rows_without_a_document(factory):
    tenant_id, _ = await _seed(factory)
    async with factory() as session:
        session.add(Chunk(tenant_id=tenant_id, document_id="doc_that_never_existed", content="ghost"))
        await session.commit()

    async with factory() as session:
        purged = await purge_orphaned_derived_rows(session)
        await session.commit()

    assert purged["chunks"] == 1
    async with factory() as session:
        contents = list((await session.execute(select(Chunk.content))).scalars())
    assert contents == ["clause 1"], "only rows whose document still exists survive"
