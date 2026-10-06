"""Embedding providers.

``sentence_transformers`` is the production path (BAAI/bge-m3 by default).
``hashing`` is a deterministic, offline feature-hashing embedding used only when
a real model cannot be loaded; it is explicitly non-semantic and every status
payload reports which one is active so nothing is overstated.
"""

from __future__ import annotations

import asyncio
import hashlib
import math
import re
from collections.abc import Sequence
from typing import Any

from app.observability.logging import get_logger
from app.providers.base import UnavailableProviderError
from app.providers.types import ProviderStatus

logger = get_logger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _device(requested: str) -> str:
    if requested and requested != "auto":
        return requested
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
    except Exception:  # noqa: BLE001 - torch is optional
        pass
    return "cpu"


class SentenceTransformerEmbeddingProvider:
    """Dense embeddings from a sentence-transformers model."""

    name = "sentence_transformers"

    def __init__(self, model_name: str, *, device: str = "auto", batch_size: int = 16, allow_download: bool = True) -> None:
        self.model_name = model_name
        self.device = _device(device)
        self.batch_size = batch_size
        self.allow_download = allow_download
        self._model: Any = None
        self._dimension: int = 0
        self._lock = asyncio.Lock()
        self._load_error: str | None = None

    @property
    def dimension(self) -> int:
        return self._dimension

    async def ensure_loaded(self) -> int:
        if self._dimension:
            return self._dimension
        async with self._lock:
            if self._dimension:
                return self._dimension
            try:
                self._model = await asyncio.to_thread(self._load_model)
                dim_fn = getattr(self._model, "get_sentence_embedding_dimension", None)
                self._dimension = int(dim_fn()) if dim_fn else len(self._model.encode(["x"])[0])
                logger.info("embedding_model_loaded", model=self.model_name, device=self.device, dim=self._dimension)
            except Exception as exc:  # noqa: BLE001
                self._load_error = f"{type(exc).__name__}: {exc}"
                self._model = None
                raise UnavailableProviderError(
                    "embedding", self.name, f"model '{self.model_name}' could not be loaded: {self._load_error}"
                ) from exc
        return self._dimension

    def _load_model(self) -> Any:
        from sentence_transformers import SentenceTransformer

        local_only = not self.allow_download
        return SentenceTransformer(self.model_name, device=self.device, local_files_only=local_only)

    async def _encode(self, texts: Sequence[str], *, is_query: bool) -> list[list[float]]:
        await self.ensure_loaded()
        assert self._model is not None
        prefix = "query: " if is_query else "passage: "

        def _run() -> list[list[float]]:
            batch = [prefix + t for t in texts]
            vectors = self._model.encode(
                batch, batch_size=self.batch_size, normalize_embeddings=True, show_progress_bar=False
            )
            return [list(map(float, v)) for v in vectors]

        return await asyncio.to_thread(_run)

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        return await self._encode(texts, is_query=False)

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self._encode([text], is_query=True)
        return vectors[0]

    async def status(self) -> ProviderStatus:
        available = self._dimension > 0 or self._load_error is None
        if self._dimension:
            detail = f"loaded on {self.device}"
        elif self._load_error:
            available = False
            detail = self._load_error
        else:
            detail = "not loaded yet (loads on first use)"
        return ProviderStatus.of(
            "embedding",
            self.name,
            available,
            detail=detail,
            model=self.model_name,
            device=self.device,
            dimension=self._dimension or None,
            semantic=True,
        )


class HashingEmbeddingProvider:
    """Deterministic feature-hashing embedder (offline fallback).

    It is real, reproducible math — but it captures lexical overlap only, not
    semantics. It exists so unit tests and air-gapped installs can run without a
    model download, and it advertises itself as ``semantic=False``.
    """

    name = "hashing"
    model_name = "feature-hashing-fallback"

    def __init__(self, dimension: int = 512) -> None:
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self._dimension
        tokens = _TOKEN_RE.findall(text.lower())
        if not tokens:
            return vector
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self._dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(v * v for v in vector))
        if norm:
            vector = [v / norm for v in vector]
        return vector

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    async def status(self) -> ProviderStatus:
        return ProviderStatus.of(
            "embedding",
            self.name,
            True,
            detail="offline feature hashing (lexical only, NOT semantic)",
            model=self.model_name,
            dimension=self._dimension,
            semantic=False,
        )


class CachedEmbeddingProvider:
    """Wraps an embedding provider with an in-process LRU-free memo cache."""

    def __init__(self, inner: SentenceTransformerEmbeddingProvider | HashingEmbeddingProvider, max_entries: int = 4096) -> None:
        self._inner = inner
        self._cache: dict[str, list[float]] = {}
        self._max = max_entries

    name = "cached"

    @property
    def model_name(self) -> str:
        return self._inner.model_name

    @property
    def dimension(self) -> int:
        return self._inner.dimension

    def _remember(self, key: str, vector: list[float]) -> None:
        if len(self._cache) >= self._max:
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = vector

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        missing = [t for t in texts if _key(t) not in self._cache]
        if missing:
            vectors = await self._inner.embed_documents(missing)
            for text, vector in zip(missing, vectors, strict=False):
                self._remember(_key(text), vector)
        return [self._cache[_key(t)] for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        key = "q:" + _key(text)
        if key not in self._cache:
            self._remember(key, await self._inner.embed_query(text))
        return self._cache[key]

    async def status(self) -> ProviderStatus:
        inner = await self._inner.status()
        return ProviderStatus.of(
            "embedding",
            f"cached({self._inner.name})",
            inner.available,
            detail=inner.detail,
            model=inner.model,
            cached_entries=len(self._cache),
            **{k: v for k, v in inner.attributes.items() if k in {"semantic", "dimension", "device"}},
        )

    async def ensure_loaded(self) -> int:
        ensure = getattr(self._inner, "ensure_loaded", None)
        if ensure is not None:
            return await ensure()
        return self._inner.dimension


def _key(text: str) -> str:
    return hashlib.blake2b(text.encode("utf-8"), digest_size=16).hexdigest()
