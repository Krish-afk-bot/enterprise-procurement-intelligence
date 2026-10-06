"""Provider container (dependency injection root).

Builds every provider from configuration, reports their real status, and falls
back to the locally-runnable implementation when an external service is
unreachable *and* fallback is permitted — always recording that it happened so
/health and the Admin UI can tell the truth about what is serving traffic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.config.settings import Settings, get_settings
from app.db.session import get_session_factory
from app.observability.logging import get_logger
from app.providers.cache import CacheLike, MemoryCache, RateLimiter, RedisCache
from app.providers.embedding import CachedEmbeddingProvider, HashingEmbeddingProvider, SentenceTransformerEmbeddingProvider
from app.providers.graph.local import LocalGraphStore
from app.providers.graph.neo4j import Neo4jGraphStore
from app.providers.llm.openai_compatible import OpenAICompatibleProvider
from app.providers.reranking import CrossEncoderReranker, DisabledReranker, LexicalReranker
from app.providers.router import ModelRouter
from app.providers.sparse import LocalBM25Index
from app.providers.storage import LocalStorage, S3Storage
from app.providers.types import ProviderStatus
from app.providers.vector.local import LocalVectorStore
from app.providers.vector.qdrant import QdrantVectorStore
from app.providers.vision import OpenAICompatibleVisionProvider

logger = get_logger(__name__)


@dataclass
class FallbackNote:
    kind: str
    configured: str
    active: str
    reason: str

    def as_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "configured": self.configured, "active": self.active, "reason": self.reason}


@dataclass
class Container:
    """Holds the live provider instances for the process."""

    settings: Settings
    vector: Any = None
    graph: Any = None
    cache: CacheLike | None = None
    storage: Any = None
    sparse: LocalBM25Index | None = None
    embeddings: CachedEmbeddingProvider | None = None
    reranker: Any = None
    llm: Any = None
    vision: OpenAICompatibleVisionProvider | None = None
    router: ModelRouter | None = None
    rate_limiter: RateLimiter | None = None
    started: bool = False
    fallbacks: list[FallbackNote] = field(default_factory=list)
    startup_errors: list[str] = field(default_factory=list)

    # ------------------------------------------------------------- bootstrap
    async def startup(self) -> None:
        if self.started:
            return
        settings = self.settings
        session_factory = get_session_factory(settings)

        # --- vector store
        self.vector = self._build_vector()
        # --- graph store
        self.graph = self._build_graph()
        # --- cache
        self.cache = self._build_cache()
        # --- storage
        self.storage = self._build_storage()
        # --- sparse index
        self.sparse = LocalBM25Index(session_factory)
        # --- rate limiter
        self.rate_limiter = RateLimiter(
            self.cache, enabled=settings.rate_limit_enabled, window_seconds=settings.rate_limit_window_seconds
        )
        # --- embeddings
        self.embeddings = self._build_embeddings()
        # --- reranker
        self.reranker = self._build_reranker()
        # --- llm + vision
        self.llm = self._build_llm()
        self.vision = self._build_vision()
        self.router = ModelRouter(
            settings,
            llm=self.llm,
            small_llm=self._build_small_llm(),
            vision=self.vision,
            embeddings=self.embeddings,
            reranker=self.reranker,
        )

        await self._verify_registered_providers()
        self.started = True
        logger.info(
            "container_started",
            vector=self.vector.name,
            graph=self.graph.name,
            cache=self.cache.name,
            storage=self.storage.name,
            llm_configured=settings.llm_configured,
            fallbacks=[note.as_dict() for note in self.fallbacks],
        )

    def _build_vector(self) -> Any:
        settings = self.settings
        if settings.vector_provider == "qdrant":
            return QdrantVectorStore(settings.qdrant_url, api_key=settings.qdrant_api_key)
        return LocalVectorStore(settings.var_dir / "vector_index")

    def _build_graph(self) -> Any:
        settings = self.settings
        if settings.graph_provider == "neo4j":
            return Neo4jGraphStore(
                settings.neo4j_uri,
                username=settings.neo4j_username,
                password=settings.neo4j_password,
                database=settings.neo4j_database,
            )
        return LocalGraphStore(settings.var_dir / "graph.db")

    def _build_cache(self) -> CacheLike:
        settings = self.settings
        if settings.cache_provider == "redis":
            return RedisCache(settings.redis_url)
        return MemoryCache()

    def _build_storage(self) -> Any:
        settings = self.settings
        if settings.storage_provider == "s3":
            return S3Storage(
                bucket=settings.s3_bucket,
                endpoint=settings.s3_endpoint,
                access_key=settings.s3_access_key,
                secret_key=settings.s3_secret_key,
                region=settings.s3_region,
            )
        return LocalStorage(settings.local_storage_dir)

    def _build_embeddings(self) -> CachedEmbeddingProvider:
        settings = self.settings
        if settings.embedding_provider == "hashing":
            return CachedEmbeddingProvider(HashingEmbeddingProvider())
        return CachedEmbeddingProvider(
            SentenceTransformerEmbeddingProvider(
                settings.embedding_model,
                device=settings.embedding_device,
                batch_size=settings.embedding_batch_size,
                allow_download=settings.embedding_allow_download,
            )
        )

    def _build_reranker(self) -> Any:
        settings = self.settings
        if not settings.reranker_enabled or settings.reranker_provider == "disabled":
            return DisabledReranker()
        if settings.reranker_provider == "lexical":
            return LexicalReranker()
        return CrossEncoderReranker(settings.reranker_model, device=settings.reranker_device)

    def _build_llm(self) -> Any:
        settings = self.settings
        return OpenAICompatibleProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
            max_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature,
        )

    def _build_small_llm(self) -> Any:
        settings = self.settings
        if not settings.llm_small_model:
            return self.llm
        return OpenAICompatibleProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_small_model,
            timeout_seconds=settings.llm_timeout_seconds,
            max_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature,
        )

    def _build_vision(self) -> OpenAICompatibleVisionProvider:
        settings = self.settings
        return OpenAICompatibleVisionProvider(
            base_url=settings.vlm_base_url or settings.llm_base_url,
            api_key=settings.vlm_api_key or settings.llm_api_key,
            model=settings.vlm_model,
        )

    async def _verify_registered_providers(self) -> None:
        """Fall back to local implementations when an external one is down."""
        settings = self.settings
        if not settings.allow_provider_fallback:
            return

        async def check(kind: str, provider: Any, local_factory) -> None:
            if provider is None:
                return
            try:
                status = await provider.status()
            except Exception as exc:  # noqa: BLE001
                status = ProviderStatus.of(kind, getattr(provider, "name", "?"), False, detail=str(exc))
            if status.available:
                return
            configured = getattr(provider, "name", "?")
            replacement = local_factory()
            self.fallbacks.append(
                FallbackNote(kind=kind, configured=configured, active=replacement.name, reason=status.detail)
            )
            logger.warning(
                "provider_fallback", kind=kind, configured=configured, active=replacement.name, reason=status.detail
            )
            if kind == "vector":
                self.vector = replacement
            elif kind == "graph":
                self.graph = replacement
            elif kind == "cache":
                self.cache = replacement
                self.rate_limiter = RateLimiter(
                    replacement,
                    enabled=settings.rate_limit_enabled,
                    window_seconds=settings.rate_limit_window_seconds,
                )
            elif kind == "storage":
                self.storage = replacement

        if settings.vector_provider != "local":
            await check("vector", self.vector, lambda: LocalVectorStore(self.settings.var_dir / "vector_index"))
        if settings.graph_provider != "local":
            await check("graph", self.graph, lambda: LocalGraphStore(self.settings.var_dir / "graph.db"))
        if settings.cache_provider != "memory":
            await check("cache", self.cache, MemoryCache)
        if settings.storage_provider != "local":
            await check("storage", self.storage, lambda: LocalStorage(self.settings.local_storage_dir))

    # --------------------------------------------------------------- shutdown
    async def shutdown(self) -> None:
        for provider in (self.vector, self.graph, self.cache, self.storage, self.llm, self.vision):
            closer = getattr(provider, "aclose", None)
            if closer is not None:
                try:
                    await closer()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("provider_close_failed", provider=getattr(provider, "name", "?"), error=str(exc))
        self.started = False

    # ----------------------------------------------------------------- health
    async def provider_statuses(self) -> dict[str, ProviderStatus]:
        statuses: dict[str, ProviderStatus] = {}
        for kind, provider in (
            ("vector", self.vector),
            ("graph", self.graph),
            ("cache", self.cache),
            ("storage", self.storage),
            ("sparse", self.sparse),
        ):
            if provider is None:
                continue
            try:
                statuses[kind] = await provider.status()
            except Exception as exc:  # noqa: BLE001
                statuses[kind] = ProviderStatus.of(kind, "unknown", False, detail=str(exc))
        if self.router is not None:
            statuses.update(await self.router.status())
        return statuses

    async def health_payload(self) -> dict[str, Any]:
        statuses = await self.provider_statuses()
        degraded = any(not status.available for status in statuses.values() if status.kind in {"vector", "graph", "cache", "storage", "embedding"})
        return {
            "config": self.settings.public_dict(),
            "providers": {name: status.model_dump() for name, status in statuses.items()},
            "fallbacks": [note.as_dict() for note in self.fallbacks],
            "degraded": degraded,
        }


_container: Container | None = None


def get_container() -> Container:
    """Process-wide container. FastAPI lifespan calls startup()/shutdown()."""
    global _container
    if _container is None:
        _container = Container(settings=get_settings())
    return _container


def set_container(container: Container | None) -> None:
    """Test hook."""
    global _container
    _container = container
