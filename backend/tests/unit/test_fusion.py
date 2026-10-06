"""Unit tests for app.retrieval.fusion — Reciprocal Rank Fusion.

Pure logic tests: no I/O, no database, no model dependencies.
"""

from __future__ import annotations

import pytest

from app.providers.types import VectorHit
from app.retrieval.fusion import FusedHit, describe_fusion, reciprocal_rank_fusion


def make_hits(ids: list[str], base_score: float = 1.0) -> list[VectorHit]:
    return [
        VectorHit(id=id_, score=base_score - i * 0.05, payload={"chunk_id": id_})
        for i, id_ in enumerate(ids)
    ]


class TestReciprocalRankFusion:
    def test_empty_inputs_return_empty(self) -> None:
        result = reciprocal_rank_fusion([], [])
        assert result == []

    def test_dense_only(self) -> None:
        dense = make_hits(["a", "b", "c"])
        result = reciprocal_rank_fusion(dense, [])
        assert len(result) == 3
        ids = [h.id for h in result]
        assert set(ids) == {"a", "b", "c"}

    def test_sparse_only(self) -> None:
        sparse = make_hits(["x", "y"])
        result = reciprocal_rank_fusion([], sparse)
        assert len(result) == 2

    def test_union_of_both_lists(self) -> None:
        dense = make_hits(["a", "b", "c"])
        sparse = make_hits(["b", "c", "d"])
        result = reciprocal_rank_fusion(dense, sparse)
        ids = {h.id for h in result}
        assert ids == {"a", "b", "c", "d"}

    def test_overlap_increases_score(self) -> None:
        """A hit present in both lists should score higher than one in only one."""
        dense = make_hits(["shared", "dense_only"])
        sparse = make_hits(["shared", "sparse_only"])
        result = reciprocal_rank_fusion(dense, sparse)
        by_id = {h.id: h for h in result}
        assert by_id["shared"].fused_score > by_id["dense_only"].fused_score
        assert by_id["shared"].fused_score > by_id["sparse_only"].fused_score

    def test_sorted_descending_by_score(self) -> None:
        dense = make_hits(["a", "b", "c", "d"])
        sparse = make_hits(["b", "c"])
        result = reciprocal_rank_fusion(dense, sparse)
        scores = [h.fused_score for h in result]
        assert scores == sorted(scores, reverse=True)

    def test_matched_by_populated(self) -> None:
        dense = make_hits(["a"])
        sparse = make_hits(["a"])
        result = reciprocal_rank_fusion(dense, sparse)
        assert "dense" in result[0].matched_by
        assert "sparse" in result[0].matched_by

    def test_dense_only_matched_by(self) -> None:
        dense = make_hits(["a"])
        result = reciprocal_rank_fusion(dense, [])
        assert result[0].matched_by == ["dense"]

    def test_higher_k_reduces_scores(self) -> None:
        """Larger k constant dampens score differences."""
        dense = make_hits(["a", "b"])
        r1 = reciprocal_rank_fusion(dense, [], k=10)
        r2 = reciprocal_rank_fusion(dense, [], k=100)
        assert r1[0].fused_score > r2[0].fused_score

    def test_weights_scale_contribution(self) -> None:
        """Doubling dense weight should give dense-only hits higher scores."""
        dense = make_hits(["a"])
        sparse = make_hits(["b"])
        r_equal = reciprocal_rank_fusion(dense, sparse, weights=(1.0, 1.0))
        r_dense = reciprocal_rank_fusion(dense, sparse, weights=(2.0, 1.0))
        by_id_equal = {h.id: h for h in r_equal}
        by_id_dense = {h.id: h for h in r_dense}
        assert by_id_dense["a"].fused_score > by_id_equal["a"].fused_score

    def test_payload_preserved(self) -> None:
        dense = [VectorHit(id="doc1", score=0.9, payload={"source": "contract_a"})]
        result = reciprocal_rank_fusion(dense, [])
        assert result[0].payload["source"] == "contract_a"

    def test_rank_metadata_recorded(self) -> None:
        dense = make_hits(["a", "b"])
        sparse = make_hits(["b", "c"])
        result = reciprocal_rank_fusion(dense, sparse)
        by_id = {h.id: h for h in result}
        assert by_id["a"].dense_rank == 1
        assert by_id["b"].dense_rank == 2
        assert by_id["b"].sparse_rank == 1

    def test_top_k_first_rank_formula(self) -> None:
        """Verify the exact RRF formula: score = 1/(k+rank)."""
        dense = [VectorHit(id="only", score=1.0, payload={})]
        k = 60
        result = reciprocal_rank_fusion(dense, [], k=k)
        expected = 1.0 / (k + 1)
        assert abs(result[0].fused_score - expected) < 1e-9


class TestDescribeFusion:
    def test_returns_expected_keys(self) -> None:
        info = describe_fusion(50, 50, 70, 60)
        assert info["algorithm"] == "reciprocal_rank_fusion"
        assert info["k"] == 60
        assert info["dense_candidates"] == 50
        assert info["sparse_candidates"] == 50
        assert info["unique_fused"] == 70
