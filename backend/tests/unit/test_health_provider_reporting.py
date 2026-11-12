"""Regression tests for provider reporting in /health and /ready.

Both endpoints used to iterate ``container._providers``, an attribute that
``Container`` never defined. Every call therefore logged
``health_check_provider_check_failed`` and reported zero providers while still
returning HTTP 200. These tests drive a real ``Container`` so a re-break fails
loudly.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import Response

from app.api.v1.health import health, ready
from app.config.container import Container

HEALTH_KINDS = ("vector", "graph", "cache", "storage", "sparse", "embedding")


@pytest.fixture
def live_container(settings, tmp_path):
    cfg = settings.model_copy(
        update={
            "var_dir": tmp_path / "var",
            "local_storage_dir": tmp_path / "storage",
            "embedding_provider": "hashing",
            "reranker_enabled": False,
            "llm_base_url": "",
            "llm_api_key": "",
        }
    )
    container = Container(settings=cfg)
    return container


@pytest.fixture
def healthy_session():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=None)
    session.rollback = AsyncMock()
    return session


async def test_health_reports_every_live_provider(live_container, healthy_session):
    await live_container.startup()
    try:
        result = await health(
            container=live_container,
            settings=live_container.settings,
            session=healthy_session,
        )
    finally:
        await live_container.shutdown()

    assert result.details["database_error"] is None
    for kind in HEALTH_KINDS:
        assert kind in result.providers, f"/health did not report provider {kind!r}"
    assert result.providers["vector"].available
    assert result.providers["embedding"].available
    assert result.capabilities["vector_search"] is True
    assert result.capabilities["embeddings"] is True
    assert result.capabilities["database"] is True


async def test_ready_uses_container_provider_map(live_container, healthy_session):
    await live_container.startup()
    try:
        result = await ready(Response(), container=live_container, session=healthy_session)
    finally:
        await live_container.shutdown()

    assert result.database is True
    assert result.blocking == [], result.blocking
    assert result.ready is True


async def test_ready_returns_503_when_a_critical_provider_is_down():
    """A platform health check gates on the status code, so it must be non-200."""

    class _EmptyContainer:
        def provider_map(self):
            return {}

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=RuntimeError("database unavailable"))
    response = Response()

    result = await ready(response, container=_EmptyContainer(), session=session)  # type: ignore[arg-type]

    assert result.ready is False
    assert "database" in result.blocking
    assert response.status_code == 503


def test_provider_map_is_empty_before_startup():
    # A container that has not started has no providers; the accessor must not
    # raise or invent entries.
    container = Container(settings=None)  # type: ignore[arg-type]
    assert container.provider_map() == {}
