"""Reranker cost controls: confidence gate, head cap and cache."""

from __future__ import annotations

from types import SimpleNamespace

from app.providers.reranking import CrossEncoderReranker
from app.providers.types import RerankScore
from app.retrieval.retriever import HybridRetriever


def settings(**overrides):
    base = {
        "rerank_candidate_limit": 20,
        "rerank_top_n": 10,
        "rerank_gate_enabled": True,
        "rerank_gate_min_score": 0.62,
        "rerank_gate_min_margin": 0.04,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def chunk(index: int, dense: float, name: str | None = None):
    return SimpleNamespace(
        chunk_id=name or f"chk-{index}",
        content=f"document {index}",
        dense_score=dense,
        rerank_score=None,
    )


def test_confident_dense_head_skips_the_reranker() -> None:
    retriever = HybridRetriever(container=None, settings=settings())
    chunks = [chunk(index, score) for index, score in enumerate([0.90, 0.70, 0.66, 0.60, 0.50])]
    assert retriever._rerank_confident(chunks) is True


def test_close_dense_head_is_not_confident() -> None:
    retriever = HybridRetriever(container=None, settings=settings())
    chunks = [chunk(index, score) for index, score in enumerate([0.90, 0.89, 0.88, 0.88, 0.87])]
    assert retriever._rerank_confident(chunks) is False


def test_low_dense_score_is_not_confident() -> None:
    retriever = HybridRetriever(container=None, settings=settings())
    chunks = [chunk(index, score) for index, score in enumerate([0.50, 0.30, 0.2, 0.1, 0.05])]
    assert retriever._rerank_confident(chunks) is False


async def test_only_the_top_twenty_candidates_are_reranked() -> None:
    seen: list[int] = []

    class Router:
        async def rerank(self, query, documents, *, top_n=None):
            seen.append(len(documents))
            return [RerankScore(index=index, score=1.0 - index * 0.01) for index in range(len(documents))]

    container = SimpleNamespace(router=Router(), reranker=SimpleNamespace(name="fake"))
    retriever = HybridRetriever(container=container, settings=settings())
    chunks = [chunk(index, 1.0 - index / 100) for index in range(30)]
    ordered, step = await retriever._rerank("query", chunks)
    assert seen == [20]
    assert step.metadata["reranked"] == 20
    assert step.metadata["unranked_tail"] == 10
    assert len(ordered) == 30
    # The head is reordered by the fake score; the tail keeps fused order.
    assert [item.chunk_id for item in ordered[:3]] == ["chk-0", "chk-1", "chk-2"]


async def test_repeated_rerank_calls_hit_the_cache() -> None:
    calls: list[int] = []

    class Model:
        def predict(self, pairs, show_progress_bar=False):
            calls.append(len(pairs))
            return [1.0 for _ in pairs]

    reranker = CrossEncoderReranker("fake-model")
    reranker._model = Model()
    first = await reranker.rank("query", ["a", "b"])
    second = await reranker.rank("query", ["a", "b"])
    assert calls == [2]
    assert [score.score for score in first] == [score.score for score in second]
