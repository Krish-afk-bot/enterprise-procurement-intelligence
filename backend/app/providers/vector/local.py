"""Local, dependency-free vector store.

Real cosine-similarity search over an on-disk numpy matrix with payload
filtering. Used when ``VECTOR_PROVIDER=local`` (the default so the platform runs
without external services) — it is a genuine retrieval index, not a stub. For
production scale, switch ``VECTOR_PROVIDER=qdrant``.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from app.observability.logging import get_logger
from app.providers.filters import matches
from app.providers.types import ProviderStatus, VectorHit, VectorPoint

logger = get_logger(__name__)


class LocalVectorStore:
    name = "local"

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._collections: dict[str, _LocalCollection] = {}
        self._lock = asyncio.Lock()

    def _collection(self, name: str) -> _LocalCollection:
        if name not in self._collections:
            self._collections[name] = _LocalCollection(self.root / name)
        return self._collections[name]

    async def ensure_collection(self, name: str, dimension: int) -> None:
        collection = self._collection(name)
        if collection.dimension and dimension and collection.dimension != dimension:
            raise ValueError(
                f"collection '{name}' has dimension {collection.dimension}, refusing write of dimension {dimension}"
            )
        collection.dimension = collection.dimension or dimension

    async def upsert(self, collection: str, points: Sequence[VectorPoint]) -> int:
        if not points:
            return 0
        async with self._lock:
            target = self._collection(collection)
            await target.load()
            written = target.upsert(points)
            target.persist()
            return written

    async def search(
        self,
        collection: str,
        vector: Sequence[float],
        *,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorHit]:
        target = self._collection(collection)
        await target.load()
        if target.size == 0:
            return []
        query = np.asarray(vector, dtype=np.float32)
        norm = float(np.linalg.norm(query))
        if norm:
            query = query / norm
        scored: list[VectorHit] = []
        for index, (point_id, payload) in enumerate(zip(target.ids, target.payloads, strict=False)):
            if not matches(payload, filters):
                continue
            score = float(np.dot(target.vectors[index], query))
            scored.append(VectorHit(id=point_id, score=score, payload=payload, source="dense"))
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:limit]

    async def delete(self, collection: str, point_ids: Sequence[str]) -> int:
        if not point_ids:
            return 0
        async with self._lock:
            target = self._collection(collection)
            await target.load()
            removed = target.delete(set(point_ids))
            if removed:
                target.persist()
            return removed

    async def delete_by_document(self, collection: str, document_id: str) -> int:
        async with self._lock:
            target = self._collection(collection)
            await target.load()
            keep = [
                i for i, payload in enumerate(target.payloads) if payload.get("document_id") != document_id
            ]
            removed = target.size - len(keep)
            if removed:
                target.retain(keep)
                target.persist()
            return removed

    async def count(self, collection: str) -> int:
        target = self._collection(collection)
        await target.load()
        return target.size

    async def status(self) -> ProviderStatus:
        collections = {name: coll.size for name, coll in self._collections.items()}
        return ProviderStatus.of(
            "vector",
            self.name,
            True,
            detail=f"on-disk numpy index at {self.root}",
            collections=collections,
        )


class _LocalCollection:
    """Tiny persistent index: normalised float32 matrix + JSON payload sidecar."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.vectors: np.ndarray = np.zeros((0, 0), dtype=np.float32)
        self.ids: list[str] = []
        self.payloads: list[dict[str, Any]] = []
        self.dimension: int = 0
        self._loaded = False

    @property
    def size(self) -> int:
        return len(self.ids)

    async def load(self) -> None:
        if self._loaded:
            return
        await asyncio.to_thread(self._load_sync)
        self._loaded = True

    def _load_sync(self) -> None:
        vector_path = self.directory / "vectors.npy"
        meta_path = self.directory / "meta.json"
        if not vector_path.exists() or not meta_path.exists():
            return
        self.vectors = np.load(vector_path).astype(np.float32)
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        self.ids = list(meta.get("ids", []))
        self.payloads = list(meta.get("payloads", []))
        self.dimension = int(meta.get("dimension", self.vectors.shape[1] if self.vectors.size else 0))

    def upsert(self, points: Sequence[VectorPoint]) -> int:
        index = {pid: i for i, pid in enumerate(self.ids)}
        new_vectors: list[list[float]] = []
        for point in points:
            vector = np.asarray(point.vector, dtype=np.float32)
            norm = float(np.linalg.norm(vector))
            if norm:
                vector = vector / norm
            if self.dimension and vector.shape[0] != self.dimension:
                raise ValueError(
                    f"vector dimension {vector.shape[0]} does not match collection dimension {self.dimension}"
                )
            self.dimension = self.dimension or int(vector.shape[0])
            if point.id in index:
                slot = index[point.id]
                self.vectors[slot] = vector
                self.payloads[slot] = point.payload
            else:
                index[point.id] = len(self.ids)
                self.ids.append(point.id)
                self.payloads.append(point.payload)
                new_vectors.append(vector.tolist())
        if new_vectors:
            block = np.asarray(new_vectors, dtype=np.float32)
            self.vectors = block if self.vectors.size == 0 else np.vstack([self.vectors, block])
        return len(points)

    def delete(self, point_ids: set[str]) -> int:
        keep = [i for i, pid in enumerate(self.ids) if pid not in point_ids]
        removed = len(self.ids) - len(keep)
        if removed:
            self.retain(keep)
        return removed

    def retain(self, keep: list[int]) -> None:
        self.ids = [self.ids[i] for i in keep]
        self.payloads = [self.payloads[i] for i in keep]
        self.vectors = self.vectors[keep] if self.vectors.size else self.vectors

    def persist(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        np.save(self.directory / "vectors.npy", self.vectors)
        (self.directory / "meta.json").write_text(
            json.dumps(
                {"ids": self.ids, "payloads": self.payloads, "dimension": self.dimension},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
