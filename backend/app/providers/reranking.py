"""Reranking providers.

Pipeline (PRD s.15): retrieve 50-100 candidates, rerank, keep top 10-20.

Three concrete implementations:
  * ``cross_encoder`` — a real bge/cross-encoder model (production path).
  * ``lexical``       — BM25-style term-overlap scoring, clearly labelled as a
                        non-neural fallback when no reranker model is loadable.
  * ``disabled``      — explicit no-op, reported as ``available=False`` so the
                        API can say "reranking disabled" instead of implying it ran.
"""

from __future__ import annotations

import asyncio
import math
import re
import time
from collections import Counter
from collections.abc import Sequence
from typing import Any

from app.observability.logging import get_logger
from app.providers.types import ProviderStatus, RerankScore

logger = get_logger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _device(requested: str) -> str:
    if requested and requested != "auto":
        return requested
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except Exception:  # noqa: BLE001
        pass
    return "cpu"


class CrossEncoderReranker:
    """Cross-encoder reranker (default model: BAAI/bge-reranker-v2-m3)."""

    name = "cross_encoder"

    def __init__(self, model_name: str, *, device: str = "auto", enabled: bool = True) -> None:
        self.model_name = model_name
        self.device = _device(device)
        self.enabled = enabled
        self._model: Any = None
        self._lock = asyncio.Lock()
        self._load_error: str | None = None

    def _load_model(self) -> Any:
        from sentence_transformers import CrossEncoder

        return CrossEncoder(self.model_name, device=self.device)

    async def ensure_loaded(self) -> None:
        if self._model is not None:
            return
        async with self._lock:
            if self._model is None:
                try:
                    self._model = await asyncio.to_thread(self._load_model)
                    logger.info("reranker_loaded", model=self.model_name, device=self.device)
                except Exception as exc:  # noqa: BLE001
                    self._load_error = f"{type(exc).__name__}: {exc}"
                    raise

    async def rank(self, query: str, documents: Sequence[str], *, top_n: int | None = None) -> list[RerankScore]:
        if not documents:
            return []
        await self.ensure_loaded()
        assert self._model is not None

        def _run() -> list[float]:
            pairs = [(query, doc) for doc in documents]
            scores = self._model.predict(pairs, show_progress_bar=False)
            return [float(s) for s in scores]

        started = time.perf_counter()
        scores = await asyncio.to_thread(_run)
        logger.info("rerank_complete", candidates=len(documents), latency_ms=int((time.perf_counter() - started) * 1000))
        ranked = sorted(
            (RerankScore(index=i, score=s) for i, s in enumerate(scores)), key=lambda r: r.score, reverse=True
        )
        return ranked[:top_n] if top_n else ranked

    async def status(self) -> ProviderStatus:
        if not self.enabled:
            return ProviderStatus.of("reranker", self.name, False, detail="disabled by configuration", model=self.model_name)
        loaded = self._model is not None
        return ProviderStatus.of(
            "reranker",
            self.name,
            self._load_error is None,
            detail=self._load_error or ("loaded" if loaded else "not loaded yet (loads on first use)"),
            model=self.model_name,
            device=self.device,
            neural=True,
        )


class LexicalReranker:
    """BM25-style lexical reranker used when no neural reranker is available."""

    name = "lexical"

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b

    async def rank(self, query: str, documents: Sequence[str], *, top_n: int | None = None) -> list[RerankScore]:
        if not documents:
            return []
        doc_tokens = [_TOKEN_RE.findall(d.lower()) for d in documents]
        lengths = [len(t) or 1 for t in doc_tokens]
        avg_len = sum(lengths) / len(lengths)
        query_terms = _TOKEN_RE.findall(query.lower())

        df: Counter[str] = Counter()
        for tokens in doc_tokens:
            for term in set(tokens):
                df[term] += 1
        total_docs = len(doc_tokens)

        scores: list[float] = []
        for tokens, length in zip(doc_tokens, lengths, strict=False):
            tf = Counter(tokens)
            score = 0.0
            for term in query_terms:
                freq = tf.get(term, 0)
                if not freq:
                    continue
                idf = math.log(1 + (total_docs - df[term] + 0.5) / (df[term] + 0.5))
                denom = freq + self.k1 * (1 - self.b + self.b * length / avg_len)
                score += idf * (freq * (self.k1 + 1)) / denom
            scores.append(score / (1 + len(query_terms) ** 0.5))
        ranked = sorted(
            (RerankScore(index=i, score=s) for i, s in enumerate(scores)), key=lambda r: r.score, reverse=True
        )
        return ranked[:top_n] if top_n else ranked

    async def status(self) -> ProviderStatus:
        return ProviderStatus.of(
            "reranker",
            self.name,
            True,
            detail="lexical BM25-style reranking (neural reranker unavailable)",
            neural=False,
        )


class DisabledReranker:
    """Explicit no-op. Retrieval order is preserved and reported as unrEranked."""

    name = "disabled"

    async def rank(self, query: str, documents: Sequence[str], *, top_n: int | None = None) -> list[RerankScore]:
        ranked = [RerankScore(index=i, score=0.0) for i in range(len(documents))]
        return ranked[:top_n] if top_n else ranked

    async def status(self) -> ProviderStatus:
        return ProviderStatus.of("reranker", self.name, False, detail="reranking disabled", neural=False)


RerankerLike = CrossEncoderReranker | LexicalReranker | DisabledReranker
