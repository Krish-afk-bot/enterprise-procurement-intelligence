"""Shared pytest fixtures and configuration.

Fixtures defined here are available to all test modules without importing.
"""

from __future__ import annotations

import pytest

from app.config.settings import Settings


@pytest.fixture(scope="session")
def settings() -> Settings:
    """A minimal Settings instance wired for local SQLite / in-memory providers.

    Uses env-independent defaults so tests never require a .env file.
    """
    return Settings(
        app_env="development",
        debug=False,
        jwt_secret="test-secret-not-for-production",
        jwt_algorithm="HS256",
        access_token_ttl_minutes=60,
        refresh_token_ttl_minutes=1440,
        database_url="sqlite+aiosqlite:///./var/test.db",
        auto_create_schema=True,
        vector_provider="local",
        graph_provider="local",
        cache_provider="memory",
        storage_provider="local",
        chunk_target_tokens=320,
        chunk_max_tokens=700,
        chunk_overlap_tokens=60,
        embedding_provider="sentence_transformers",
        embedding_model="BAAI/bge-small-en-v1.5",
        reranker_enabled=False,
        llm_provider="openai_compatible",
        llm_base_url="",
    )
