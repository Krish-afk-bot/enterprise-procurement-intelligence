"""Model router (PRD s.16/s.67).

Business logic calls ``router.generate(task=...)`` and never a vendor SDK or a
hard-coded model name. Routing decides between the small and large LLM, the VLM,
and the non-LLM engines (PostgreSQL for aggregation, Python for arithmetic, the
graph store for traversal) so an expensive model is never used for work that has
an exact answer.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel

from app.config.settings import Settings
from app.observability.logging import get_logger
from app.providers.base import LLMProvider, RerankerProvider, UnavailableProviderError
from app.providers.embedding import CachedEmbeddingProvider
from app.providers.reranking import CrossEncoderReranker, DisabledReranker, LexicalReranker
from app.providers.types import LLMMessage, LLMResponse, ProviderStatus, RerankScore, VisionResponse
from app.providers.vision import OpenAICompatibleVisionProvider

logger = get_logger(__name__)


class Task(str, Enum):
    """Routing tasks. The value documents the intended engine."""

    CLASSIFY = "classify"          # cheap structure extraction
    PLAN = "plan"                  # query planning / tool selection
    REWRITE = "rewrite"            # query rewriting / expansion
    GENERATE = "generate"          # final grounded answer
    COMPARE = "compare"            # multi-document synthesis
    VERIFY = "verify"              # grounding / claim verification
    VISION = "vision"              # page image understanding
    EXTRACT = "extract"            # table/metadata extraction from text


#: engine kinds the router can select
ENGINE_LLM = "llm"
ENGINE_SMALL_LLM = "small_llm"
ENGINE_VLM = "vlm"
ENGINE_PYTHON = "python"       # deterministic arithmetic
ENGINE_SQL = "sql"            # PostgreSQL aggregation
ENGINE_GRAPH = "graph"        # Neo4j traversal


@dataclass(slots=True)
class RouteDecision:
    task: Task
    engine: str
    model: str | None
    reason: str


#: Default engine per task. Deterministic engines are chosen when the task has an
#: exact answer available, matching the PRD routing table.
_DEFAULT_ENGINES: dict[Task, str] = {
    Task.CLASSIFY: ENGINE_SMALL_LLM,
    Task.PLAN: ENGINE_LLM,
    Task.REWRITE: ENGINE_SMALL_LLM,
    Task.GENERATE: ENGINE_LLM,
    Task.COMPARE: ENGINE_LLM,
    Task.VERIFY: ENGINE_LLM,
    Task.VISION: ENGINE_VLM,
    Task.EXTRACT: ENGINE_SMALL_LLM,
}


class ModelRouter:
    """Facade over every model provider, with per-task routing."""

    def __init__(
        self,
        settings: Settings,
        *,
        llm: LLMProvider,
        small_llm: LLMProvider | None = None,
        vision: OpenAICompatibleVisionProvider | None = None,
        embeddings: CachedEmbeddingProvider | None = None,
        reranker: CrossEncoderReranker | LexicalReranker | DisabledReranker | None = None,
        routing_overrides: dict[str, str] | None = None,
    ) -> None:
        self.settings = settings
        self.llm = llm
        self.small_llm = small_llm or llm
        self.vision_provider = vision
        self.embeddings = embeddings
        self.reranker = reranker
        self.routing_overrides = routing_overrides or {}

    # ---------------------------------------------------------------- routing
    def route(self, task: Task, *, complexity: str | None = None, requires_vision: bool = False) -> RouteDecision:
        """Decide which engine serves a task."""
        override = self.routing_overrides.get(task.value)
        if override:
            return RouteDecision(task, override, self._model_for_engine(override), "routing override")

        if requires_vision or task is Task.VISION:
            if self.vision_provider is None or not self.vision_provider.configured:
                return RouteDecision(task, ENGINE_LLM, None, "vision unavailable; falling back to text evidence")
            return RouteDecision(task, ENGINE_VLM, self.settings.vlm_model, "visual task")

        engine = _DEFAULT_ENGINES.get(task, ENGINE_LLM)
        if engine == ENGINE_SMALL_LLM and self.small_llm is self.llm and not self.settings.llm_small_model:
            engine = ENGINE_LLM
        if complexity == "high":
            engine = ENGINE_LLM
        return RouteDecision(task, engine, self._model_for_engine(engine), f"default route for {task.value}")

    def _model_for_engine(self, engine: str) -> str | None:
        if engine == ENGINE_SMALL_LLM:
            return self.settings.llm_small_model or self.settings.llm_model
        if engine == ENGINE_VLM:
            return self.settings.vlm_model
        if engine == ENGINE_LLM:
            return self.settings.llm_model
        return None

    def _provider_for(self, engine: str) -> LLMProvider:
        if engine == ENGINE_SMALL_LLM:
            return self.small_llm
        return self.llm

    # --------------------------------------------------------------- generate
    async def generate(
        self,
        messages: Sequence[LLMMessage],
        *,
        task: Task = Task.GENERATE,
        complexity: str | None = None,
        requires_vision: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        decision = self.route(task, complexity=complexity, requires_vision=requires_vision)
        if decision.engine == ENGINE_VLM:  # pragma: no cover - guarded by callers
            raise UnavailableProviderError("llm", "vlm", "text generation cannot be routed to the VLM")
        provider = self._provider_for(decision.engine)
        response = await provider.complete(
            messages,
            model=decision.model,
            temperature=temperature,
            max_tokens=max_tokens,
            metadata={"task": task.value, "route_reason": decision.reason},
        )
        return response

    async def stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        task: Task = Task.GENERATE,
        complexity: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        decision = self.route(task, complexity=complexity)
        provider = self._provider_for(decision.engine)
        async for chunk in provider.stream(
            messages, model=decision.model, temperature=temperature, max_tokens=max_tokens
        ):
            yield chunk

    async def generate_structured(
        self,
        messages: Sequence[LLMMessage],
        schema: type[BaseModel],
        *,
        task: Task = Task.CLASSIFY,
        complexity: str | None = None,
    ) -> BaseModel | None:
        decision = self.route(task, complexity=complexity)
        if decision.engine == ENGINE_VLM:
            decision = RouteDecision(task, ENGINE_LLM, self.settings.llm_model, "structured output needs a text model")
        provider = self._provider_for(decision.engine)
        return await provider.complete_structured(messages, schema, model=decision.model)

    async def vision(
        self,
        image_bytes: bytes,
        prompt: str,
        *,
        mime_type: str = "image/png",
    ) -> VisionResponse:
        decision = self.route(Task.VISION, requires_vision=True)
        if decision.engine != ENGINE_VLM or self.vision_provider is None:
            return VisionResponse(text="", provider="none", model=None, mode="unavailable")
        return await self.vision_provider.describe(image_bytes, prompt, mime_type=mime_type)

    # ------------------------------------------------------------- embeddings
    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if self.embeddings is None:
            raise UnavailableProviderError("embedding", "none", "no embedding provider configured")
        return await self.embeddings.embed_documents(texts)

    async def embed_query(self, text: str) -> list[float]:
        if self.embeddings is None:
            raise UnavailableProviderError("embedding", "none", "no embedding provider configured")
        return await self.embeddings.embed_query(text)

    @property
    def embedding_dimension(self) -> int:
        return self.embeddings.dimension if self.embeddings else 0

    # --------------------------------------------------------------- rerankng
    async def rerank(self, query: str, documents: Sequence[str], *, top_n: int | None = None) -> list[RerankScore]:
        if self.reranker is None:
            return [RerankScore(index=i, score=0.0) for i in range(len(documents))]
        return await self.reranker.rank(query, documents, top_n=top_n)

    @property
    def reranker_name(self) -> str:
        return self.reranker.name if self.reranker else "none"

    # ----------------------------------------------------------------- status
    async def status(self) -> dict[str, ProviderStatus]:
        statuses: dict[str, ProviderStatus] = {}
        try:
            statuses["llm"] = await self.llm.status()
        except Exception as exc:  # noqa: BLE001
            statuses["llm"] = ProviderStatus.of("llm", "unknown", False, detail=str(exc))
        if self.small_llm is not self.llm:
            try:
                statuses["small_llm"] = await self.small_llm.status()
            except Exception as exc:  # noqa: BLE001
                statuses["small_llm"] = ProviderStatus.of("llm", "unknown", False, detail=str(exc))
        if self.vision_provider is not None:
            try:
                statuses["vision"] = await self.vision_provider.status()
            except Exception as exc:  # noqa: BLE001
                statuses["vision"] = ProviderStatus.of("vision", "unknown", False, detail=str(exc))
        if self.embeddings is not None:
            try:
                statuses["embedding"] = await self.embeddings.status()
            except Exception as exc:  # noqa: BLE001
                statuses["embedding"] = ProviderStatus.of("embedding", "unknown", False, detail=str(exc))
        if self.reranker is not None:
            try:
                statuses["reranker"] = await self.reranker.status()
            except Exception as exc:  # noqa: BLE001
                statuses["reranker"] = ProviderStatus.of("reranker", "unknown", False, detail=str(exc))
        return statuses

    async def routing_table(self) -> list[dict[str, Any]]:
        """Human-readable routing table for the admin UI."""
        rows: list[dict[str, Any]] = []
        for task in Task:
            decision = self.route(task)
            rows.append(
                {
                    "task": task.value,
                    "engine": decision.engine,
                    "model": decision.model,
                    "reason": decision.reason,
                }
            )
        rows.extend(
            [
                {"task": "deterministic_calculation", "engine": ENGINE_PYTHON, "model": None, "reason": "exact arithmetic"},
                {"task": "aggregation", "engine": ENGINE_SQL, "model": None, "reason": "exact SQL aggregation over stored rows"},
                {"task": "relationship_traversal", "engine": ENGINE_GRAPH, "model": None, "reason": "graph store traversal"},
                {"task": "embedding", "engine": "embedding", "model": self.settings.embedding_model if self.embeddings else None, "reason": "dense retrieval"},
                {"task": "reranking", "engine": "reranker", "model": self.settings.reranker_model if self.reranker else None, "reason": "retrieval precision"},
            ]
        )
        return rows
