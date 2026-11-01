"""Citations must support a claim and stay short."""

from __future__ import annotations

from app.agents.verification import ClaimCheck, select_supporting_citations
from app.retrieval.context import CitationDraft


def citation(index: int, score: float) -> CitationDraft:
    return CitationDraft(
        chunk_id=f"chk-{index}",
        document_id=f"doc-{index}",
        document_name=f"document-{index}.pdf",
        page=index,
        snippet=f"snippet {index}",
        score=score,
        rank=index,
    )


def check(refs: list[int], supported: bool = True) -> ClaimCheck:
    return ClaimCheck(claim="claim", supported=supported, support_score=1.0, evidence_refs=refs)


def test_only_the_block_bound_to_the_claim_survives() -> None:
    citations = [citation(index, 1.0 - index / 10) for index in range(1, 7)]
    selected, method = select_supporting_citations([check([2])], citations, cap=5)
    assert method == "claim_bound"
    assert [item.chunk_id for item in selected] == ["chk-2"]


def test_cap_keeps_the_highest_scoring_supporting_citations() -> None:
    citations = [citation(index, index / 10) for index in range(1, 7)]
    selected, _ = select_supporting_citations([check([1, 2, 3, 4, 5, 6])], citations, cap=3)
    assert len(selected) == 3
    assert [item.chunk_id for item in selected] == ["chk-6", "chk-5", "chk-4"]


def test_unsupported_claim_does_not_pull_its_citation() -> None:
    citations = [citation(1, 0.9), citation(2, 0.8)]
    selected, method = select_supporting_citations([check([1], supported=False)], citations, cap=5)
    assert method == "score_ranked_fallback"
    assert [item.chunk_id for item in selected] == ["chk-1", "chk-2"]


def test_fallback_is_ranked_by_score_not_context_order() -> None:
    citations = [citation(1, 0.1), citation(2, 0.9), citation(3, 0.5)]
    selected, _ = select_supporting_citations([], citations, cap=2)
    assert [item.chunk_id for item in selected] == ["chk-2", "chk-3"]


def test_cap_zero_disables_displayed_citations() -> None:
    selected, method = select_supporting_citations([check([1])], [citation(1, 1.0)], cap=0)
    assert selected == []
    assert method == "disabled"
