"""Typed application configuration.

Every external dependency (database, vector store, graph store, cache, object
storage, models) is configured here and resolved through a provider factory so
that no business logic ever imports a vendor SDK directly.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_VAR_DIR = BACKEND_DIR / "var"

VectorProviderName = Literal["local", "qdrant"]
GraphProviderName = Literal["local", "neo4j"]
CacheProviderName = Literal["memory", "redis"]
StorageProviderName = Literal["local", "s3"]
LLMProviderName = Literal["openai_compatible", "none"]
EmbeddingProviderName = Literal["sentence_transformers", "hashing"]
RerankerProviderName = Literal["cross_encoder", "lexical", "disabled"]

# Secrets that are obviously unsafe for production use.
_KNOWN_WEAK_SECRETS = frozenset(
    {
        "dev-insecure-change-me",
        "changeme",
        "secret",
        "your-secret-key",
        "example-secret",
        "replace-me",
        "test-secret-not-for-production",
    }
)


def _default_sqlite_url() -> str:
    (DEFAULT_VAR_DIR).mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{(DEFAULT_VAR_DIR / 'epi.db').as_posix()}"


class Settings(BaseSettings):
    """Environment-driven settings. All values have safe local defaults."""

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ------------------------------------------------------------------ app
    app_name: str = "Enterprise Procurement Intelligence"
    app_env: Literal["development", "test", "production"] = "development"
    api_prefix: str = "/api/v1"
    debug: bool = False
    log_level: str = "INFO"
    log_json: bool = True
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    var_dir: Path = DEFAULT_VAR_DIR

    # ------------------------------------------------------------- security
    jwt_secret: str = "dev-insecure-change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 720
    refresh_token_ttl_minutes: int = 10080
    allow_self_registration: bool = True
    default_tenant_slug: str = "acme-procurement"
    bootstrap_tenant_name: str = "Acme Procurement"
    #: When both are set, startup creates/updates this admin account. Leave unset
    #: in production and create users explicitly instead.
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None

    @field_validator("jwt_secret", mode="after")
    @classmethod
    def _reject_weak_jwt_secret_in_production(cls, value: str) -> str:
        # Checked lazily at access time so tests can still supply their own
        # value without environment gymnastics.  The real guard is in
        # validate_startup_security() which main.py calls during lifespan.
        return value

    # ------------------------------------------------------------ data layer
    database_url: str = Field(default_factory=_default_sqlite_url)
    #: Dev/test convenience. Production runs ``alembic upgrade head`` instead.
    auto_create_schema: bool = True
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 5

    # --------------------------------------------------------- vector store
    vector_provider: VectorProviderName = "local"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection_chunks: str = "procurement_chunks"
    qdrant_collection_pages: str = "document_pages"
    qdrant_collection_tables: str = "table_chunks"
    vector_dim: int = 0  # 0 => infer from the embedding provider

    # ---------------------------------------------------------- graph store
    graph_provider: GraphProviderName = "local"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "neo4j"
    neo4j_database: str = "neo4j"

    # ---------------------------------------------------------------- cache
    cache_provider: CacheProviderName = "memory"
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 300
    rate_limit_enabled: bool = True

    # -------------------------------------------------------------- storage
    storage_provider: StorageProviderName = "local"
    s3_endpoint: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_bucket: str = "epi-documents"
    s3_region: str = "us-east-1"
    local_storage_dir: Path = DEFAULT_VAR_DIR / "storage"

    # ------------------------------------------------------------------ llm
    llm_provider: LLMProviderName = "openai_compatible"
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "Qwen/Qwen3-30B-A3B-Instruct-2507"
    llm_small_model: str | None = None  # routed for cheap classification tasks
    llm_timeout_seconds: float = 90.0
    llm_max_tokens: int = 2048
    llm_temperature: float = 0.1

    vision_provider: str = "openai_compatible"
    vlm_model: str = "Qwen/Qwen3-VL-30B-A3B-Instruct"
    vlm_base_url: str | None = None
    vlm_api_key: str | None = None
    vlm_enabled: bool = True

    embedding_provider: EmbeddingProviderName = "sentence_transformers"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_device: str = "auto"
    embedding_batch_size: int = 16
    embedding_dim: int = 0  # 0 => infer
    embedding_allow_download: bool = True

    reranker_provider: RerankerProviderName = "cross_encoder"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_enabled: bool = True
    reranker_device: str = "auto"

    #: When a configured external provider is unreachable in development, fall
    #: back to the locally-runnable implementation and say so in /health instead
    #: of failing every request. Must stay False in production.
    allow_provider_fallback: bool = True

    # ------------------------------------------------------------ retrieval
    dense_top_k: int = 50
    sparse_top_k: int = 50
    fusion_top_k: int = 50
    rrf_k: int = 60
    rerank_top_n: int = 15
    context_max_chunks: int = 12
    context_max_tokens: int = 6000
    max_agent_iterations: int = 2
    evidence_sufficiency_threshold: float = 0.45
    enable_query_rewrite: bool = False
    enable_multi_query: bool = False
    enable_hyde: bool = False

    # ----------------------------------------------------------- ingestion
    max_upload_mb: int = 100
    allowed_extensions: list[str] = Field(
        default_factory=lambda: [
            ".pdf",
            ".docx",
            ".xlsx",
            ".xlsm",
            ".csv",
            ".txt",
            ".md",
            ".png",
            ".jpg",
            ".jpeg",
            ".tif",
            ".tiff",
        ]
    )
    ocr_enabled: bool = True
    ocr_min_chars_per_page: int = 40
    ocr_language: str = "en"
    #: Some Paddle CPU builds fail on the oneDNN/PIR path; leaving this False is
    #: the stable configuration and costs little on CPU-only hosts.
    ocr_use_onednn: bool = False
    chunk_target_tokens: int = 320
    chunk_max_tokens: int = 700
    chunk_overlap_tokens: int = 60
    contextual_enrichment: bool = True
    vision_escalation_enabled: bool = True
    vision_min_table_complexity: int = 4
    worker_poll_interval_seconds: float = 1.0
    worker_concurrency: int = 2

    # --------------------------------------------------------- observability
    langsmith_api_key: str | None = None
    langsmith_project: str = "epi-procurement"
    langsmith_tracing: bool = False
    otel_exporter_otlp_endpoint: str | None = None
    trace_store_limit: int = 200

    # ------------------------------------------------------------ rate limits
    rate_limit_login: int = 20
    rate_limit_upload: int = 60
    rate_limit_query: int = 120
    rate_limit_model: int = 240
    rate_limit_window_seconds: int = 60

    # ------------------------------------------------------------- evaluation
    evaluation_dir: Path = PROJECT_ROOT / "data" / "evaluation"
    synthetic_dir: Path = PROJECT_ROOT / "data" / "synthetic"
    seed_corpus_dir: Path = PROJECT_ROOT / "data" / "raw"

    @field_validator("var_dir", "local_storage_dir", mode="after")
    @classmethod
    def _ensure_dir(cls, value: Path) -> Path:
        value = Path(value)
        value.mkdir(parents=True, exist_ok=True)
        return value

    # -------------------------------------------------------------- helpers
    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_provider == "openai_compatible" and self.llm_base_url and self.llm_model)

    @property
    def vlm_configured(self) -> bool:
        base = self.vlm_base_url or self.llm_base_url
        key = self.vlm_api_key or self.llm_api_key
        return bool(self.vlm_enabled and base and key)

    def public_dict(self) -> dict[str, object]:
        """Config safe to expose to the frontend (never contains secrets)."""
        return {
            "app_name": self.app_name,
            "app_env": self.app_env,
            "vector_provider": self.vector_provider,
            "graph_provider": self.graph_provider,
            "cache_provider": self.cache_provider,
            "storage_provider": self.storage_provider,
            "embedding_provider": self.embedding_provider,
            "reranker_provider": self.reranker_provider,
            "allow_provider_fallback": self.allow_provider_fallback,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model if self.llm_configured else None,
            "llm_configured": self.llm_configured,
            "vlm_configured": self.vlm_configured,
            "embedding_model": self.embedding_model,
            "reranker_model": self.reranker_model if self.reranker_enabled else None,
            "ocr_enabled": self.ocr_enabled,
            "vision_escalation_enabled": self.vision_escalation_enabled,
            "langsmith_tracing": bool(self.langsmith_tracing and self.langsmith_api_key),
            "max_agent_iterations": self.max_agent_iterations,
        }

    def is_jwt_secret_safe(self) -> bool:
        """Return True when the JWT secret is strong enough for the current env."""
        if self.app_env == "production":
            return self.jwt_secret not in _KNOWN_WEAK_SECRETS and len(self.jwt_secret) >= 32
        # In development/test a weak secret is allowed but warned about.
        return True

    def validate_startup_security(self) -> None:
        """Raise RuntimeError if running in production with an insecure secret.

        Called by the application lifespan so that a misconfigured production
        deployment fails fast at boot rather than silently signing tokens with a
        known-weak key.
        """
        if self.app_env == "production":
            if self.jwt_secret in _KNOWN_WEAK_SECRETS:
                raise RuntimeError(
                    "Production startup refused: JWT_SECRET is set to a known "
                    "insecure default value. Set JWT_SECRET to a securely-generated "
                    "random string of at least 32 characters."
                )
            if len(self.jwt_secret) < 32:
                raise RuntimeError(
                    f"Production startup refused: JWT_SECRET is only "
                    f"{len(self.jwt_secret)} characters long. "
                    "Use a secret of at least 32 characters."
                )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    """Used by tests that mutate the environment."""
    get_settings.cache_clear()


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
