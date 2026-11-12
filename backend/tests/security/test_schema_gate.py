"""Startup schema gate.

A deployment with ``AUTO_CREATE_SCHEMA=false`` must refuse to serve when the
database has no schema, or is behind the revision this build expects.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.session import assert_schema_current


@pytest.fixture
async def engine():
    created = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    yield created
    await created.dispose()


@pytest.mark.asyncio
async def test_missing_schema_is_refused(engine):
    with pytest.raises(RuntimeError, match="not initialised"):
        await assert_schema_current(engine, expected_head="head-1")


@pytest.mark.asyncio
async def test_matching_head_is_accepted(engine):
    async with engine.begin() as connection:
        await connection.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        await connection.execute(text("INSERT INTO alembic_version VALUES ('head-1')"))

    assert await assert_schema_current(engine, expected_head="head-1") == "head-1"


@pytest.mark.asyncio
async def test_schema_behind_this_build_is_refused(engine):
    async with engine.begin() as connection:
        await connection.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        await connection.execute(text("INSERT INTO alembic_version VALUES ('old-1')"))

    with pytest.raises(RuntimeError, match="alembic upgrade head"):
        await assert_schema_current(engine, expected_head="head-1")
