"""Rank fusion.

Reciprocal Rank Fusion is used because dense cosine scores and BM25 scores are
not comparable in magnitude: RRF combines *ranks*, which is stable, needs no
score normalisation and is the documented fusion algorithm for this platform
(PRD s.29).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.providers.types import VectorHit


@dataclass(slots=True)
class FusedHit:
    id: str
    fused_score: float
    payload: dict = field(default_factory=dict)
    dense_score: float | None = None
    sparse_score: float | None = None
    dense_rank: int | None = None
    sparse_rank: int | None = None
    matched_by: list[str] = field(default_factory=list)


def reciprocal_rank_fusion(
    dense: list[VectorHit],
    sparse: list[VectorHit],
    *,
    k: int = 60,
    weights: tuple[float, float] = (1.0, 1.0),
) -> list[FusedHit]:
    """Fuse dense and sparse rankings.

    ``score = w_dense / (k + rank_dense) + w_sparse / (k + rank_sparse)``
    """
    fused: dict[str, FusedHit] = {}
    for rank, hit in enumerate(dense, start=1):
        entry = fused.setdefault(hit.id, FusedHit(id=hit.id, fused_score=0.0, payload=dict(hit.payload)))
        entry.fused_score += weights[0] / (k + rank)
        entry.dense_score = hit.score
        entry.dense_rank = rank
        entry.matched_by.append("dense")
        entry.payload = entry.payload or dict(hit.payload)
    for rank, hit in enumerate(sparse, start=1):
        entry = fused.setdefault(hit.id, FusedHit(id=hit.id, fused_score=0.0, payload=dict(hit.payload)))
        entry.fused_score += weights[1] / (k + rank)
        entry.sparse_score = hit.score
        entry.sparse_rank = rank
        entry.matched_by.append("sparse")
        if not entry.payload:
            entry.payload = dict(hit.payload)
    ordered = sorted(fused.values(), key=lambda item: item.fused_score, reverse=True)
    return ordered


def describe_fusion(dense_count: int, sparse_count: int, fused_count: int, k: int) -> dict[str, object]:
    return {
        "algorithm": "reciprocal_rank_fusion",
        "k": k,
        "dense_candidates": dense_count,
        "sparse_candidates": sparse_count,
        "unique_fused": fused_count,
    }
