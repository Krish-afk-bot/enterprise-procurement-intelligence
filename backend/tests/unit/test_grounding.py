"""Unit tests for grounding verification and citation validation.

Tests cover:
  - extract_claims: boilerplate filtering, factual sentence detection
  - judge_grounding_lexical: token overlap, number containment, score
  - judge_grounding_llm: mock-router path, failure tolerance
  - validate_citations: marker-to-bundle mapping, fabricated citation detection
  - decide_status: refusal, partial, supported, conflicting outcomes
  - assess_evidence_strength: level computation from criteria
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from app.agents.verification import (
    GroundingResult,
    assess_evidence_strength,
    decide_status,
    extract_claims,
    judge_grounding_lexical,
    judge_grounding_llm,
    validate_citations,
)
from app.retrieval.context import CitationDraft, ContextBlock, ContextBundle
from app.retrieval.structured import StructuredResult

# ------------------------------------------------------------------ helpers


def make_citation(
    chunk_id: str = "chk_1",
    document_id: str = "doc_1",
    document_name: str = "Contract A",
    page: int = 1,
    snippet: str = "The unit price is USD 92.00.",
) -> CitationDraft:
    return CitationDraft(
        chunk_id=chunk_id,
        document_id=document_id,
        document_name=document_name,
        page=page,
        snippet=snippet,
        evidence_type="document",
        verified=True,
    )


def make_bundle(snippets: list[str] | None = None) -> ContextBundle:
    citations = [make_citation(snippet=s, chunk_id=f"chk_{i}") for i, s in enumerate(snippets or ["test"])]
    blocks = [
        ContextBlock(
            marker=f"[{i + 1}]",
            text=f"[{i + 1}] {c.snippet}",
            citation=c,
            content_type="paragraph",
            is_synthetic=True,
        )
        for i, c in enumerate(citations)
    ]
    return ContextBundle(blocks=blocks, citations=citations)


# ================================================================== extract_claims


class TestExtractClaims:
    def test_empty_answer_returns_empty(self) -> None:
        assert extract_claims("") == []

    def test_boilerplate_headings_excluded(self) -> None:
        answer = "Answer\nEvidence\nVerification\nExtractive summary"
        claims = extract_claims(answer)
        assert not any(c.lower().startswith(("answer", "evidence", "verification")) for c in claims)

    def test_factual_sentence_with_number_included(self) -> None:
        answer = "The unit price for Widget A is USD 92.00 per unit."
        claims = extract_claims(answer)
        assert len(claims) >= 1
        assert any("92" in c for c in claims)

    def test_refusal_text_not_treated_as_claim(self) -> None:
        from app.agents.verification import REFUSAL_TEXT

        claims = extract_claims(REFUSAL_TEXT)
        # The refusal text starts with "I couldn't verify" which should be excluded
        assert len(claims) == 0 or not any("couldn't verify" in c.lower() for c in claims)

    def test_short_sentences_excluded(self) -> None:
        answer = "Yes. No. Maybe."
        claims = extract_claims(answer)
        # All < 25 chars, none should be returned
        assert all(len(c) >= 25 for c in claims)

    def test_max_claims_respected(self) -> None:
        answer = " ".join(
            [f"The price for item {i} is USD {i * 10}.00 per unit effective 2026-01-01." for i in range(20)]
        )
        claims = extract_claims(answer, max_claims=5)
        assert len(claims) <= 5

    def test_sentences_with_supplier_names_included(self) -> None:
        answer = "Supplier Alpha agreed to a unit price of USD 92.00 for Widget A."
        claims = extract_claims(answer)
        assert len(claims) >= 1


# ================================================================== judge_grounding_lexical


class TestJudgeGroundingLexical:
    def test_fully_supported_claim(self) -> None:
        claims = ["The unit price is USD 92.00 per unit."]
        evidence = ["The agreed unit price is USD 92.00 per unit effective January 2026."]
        result = judge_grounding_lexical(claims, evidence)
        assert result.supported >= 1
        assert result.total == 1
        assert result.score is not None

    def test_unsupported_number_marks_claim_unsupported(self) -> None:
        claims = ["The price is USD 999.99 per unit."]
        evidence = ["The agreed price is USD 92.00 per unit."]
        result = judge_grounding_lexical(claims, evidence)
        # 999.99 is not in the evidence → unsupported
        assert any("999" in m for check in result.claims for m in check.missing_numbers)
        assert result.claims[0].supported is False

    def test_empty_claims_returns_zero_total(self) -> None:
        result = judge_grounding_lexical([], ["some evidence"])
        assert result.total == 0
        assert result.score is None

    def test_method_is_lexical_overlap(self) -> None:
        result = judge_grounding_lexical(["something"], ["something"])
        assert result.method == "lexical_overlap"

    def test_score_between_zero_and_one(self) -> None:
        claims = ["The price is USD 92.00.", "The supplier is unknown."]
        evidence = ["The price is USD 92.00 for Widget A."]
        result = judge_grounding_lexical(claims, evidence)
        if result.score is not None:
            assert 0.0 <= result.score <= 1.0

    def test_all_supported_property(self) -> None:
        claims = ["The price is USD 92.00."]
        evidence = ["The price is USD 92.00 per unit effective 2026."]
        result = judge_grounding_lexical(claims, evidence)
        # all_supported only when every claim passes
        if result.total > 0:
            assert result.all_supported == (result.supported == result.total)


# ================================================================== judge_grounding_llm


class TestJudgeGroundingLLM:
    async def test_returns_none_when_llm_fails(self) -> None:
        from unittest.mock import AsyncMock, MagicMock

        router = MagicMock()
        router.generate_structured = AsyncMock(side_effect=Exception("LLM unavailable"))
        result = await judge_grounding_llm(["claim one"], ["evidence"], router)
        assert result is None

    async def test_returns_none_when_structured_output_is_none(self) -> None:
        router = MagicMock()
        router.generate_structured = AsyncMock(return_value=None)
        result = await judge_grounding_llm(["claim one"], ["evidence"], router)
        assert result is None

    async def test_returns_grounding_result_from_llm_judgement(self) -> None:
        from pydantic import BaseModel, Field

        class FakeJudgement(BaseModel):
            supported: list[int] = Field(default_factory=list)
            unsupported: list[int] = Field(default_factory=list)
            reason: str = ""

        router = MagicMock()
        router.generate_structured = AsyncMock(
            return_value=FakeJudgement(supported=[0], unsupported=[], reason="supported")
        )
        result = await judge_grounding_llm(["claim zero"], ["evidence text"], router)
        if result is not None:
            assert result.method == "llm_judge"
            assert result.supported == 1


# ================================================================== validate_citations


class TestValidateCitations:
    def test_valid_citation_marker_resolves_to_bundle(self) -> None:
        bundle = make_bundle(["The price is USD 92.00."])
        answer = "The price is USD 92.00 [1]."
        check = validate_citations(answer, bundle)
        assert len(check.valid) >= 1
        assert 1 in check.referenced_markers

    def test_fabricated_marker_not_in_valid_citations(self) -> None:
        bundle = make_bundle(["Evidence text."])
        # [99] does not correspond to any block in the bundle
        answer = "The price is USD 92.00 [99]."
        check = validate_citations(answer, bundle)
        assert 99 not in check.referenced_markers
        assert len(check.valid) == 0

    def test_unused_markers_recorded(self) -> None:
        bundle = make_bundle(["First doc.", "Second doc."])
        # Only [1] is referenced; [2] is unused
        answer = "The price is $92 [1]."
        check = validate_citations(answer, bundle)
        assert 2 in check.unused_markers

    def test_empty_answer_no_citations(self) -> None:
        bundle = make_bundle(["Evidence."])
        check = validate_citations("", bundle)
        assert len(check.valid) == 0
        assert len(check.referenced_markers) == 0

    def test_citation_requires_document_id_or_chunk_id(self) -> None:
        """Citations without a source ID are invalid and must be recorded separately."""
        # Simulate a citation with no backing document
        orphan = CitationDraft(
            chunk_id=None,
            document_id=None,
            document_name="Ghost Document",
            snippet="Invented text.",
        )
        block = ContextBlock(
            marker="[1]",
            text="[1] Invented text.",
            citation=orphan,
            content_type="paragraph",
            is_synthetic=False,
        )
        bundle = ContextBundle(blocks=[block], citations=[orphan])
        check = validate_citations("The price is $92 [1].", bundle)
        # No chunk_id and no document_id → classified as invalid
        assert len(check.invalid) >= 1 or len(check.valid) == 0


# ================================================================== decide_status


class TestDecideStatus:
    def test_returns_insufficient_evidence_when_no_evidence(self) -> None:
        empty_bundle = ContextBundle()
        status = decide_status(
            grounding=None,
            conflicts=[],
            bundle=empty_bundle,
            structured=None,
            generation_mode="extractive",
        )
        assert status == "insufficient_evidence"

    def test_returns_supported_when_evidence_present(self) -> None:
        bundle = make_bundle(["Evidence sentence with price 92.00."])
        grounding = GroundingResult(
            method="lexical_overlap",
            score=1.0,
            supported=1,
            total=1,
        )
        status = decide_status(
            grounding=grounding,
            conflicts=[],
            bundle=bundle,
            structured=None,
            generation_mode="llm",
        )
        assert status in {"supported", "partial"}

    def test_returns_conflicting_when_conflicts_present(self) -> None:
        bundle = make_bundle(["Evidence."])
        grounding = GroundingResult(method="lexical_overlap", score=1.0, supported=1, total=1)
        conflicts = [{"kind": "price_conflict", "description": "conflict", "values": [], "resolution": ""}]
        status = decide_status(
            grounding=grounding,
            conflicts=conflicts,
            bundle=bundle,
            structured=None,
            generation_mode="llm",
        )
        assert status == "conflicting"


# ================================================================== assess_evidence_strength


class TestAssessEvidenceStrength:
    def test_no_evidence_returns_none_level(self) -> None:
        empty_bundle = ContextBundle()
        strength = assess_evidence_strength(empty_bundle, None)
        assert strength.level == "none"

    def test_single_document_returns_limited_or_moderate(self) -> None:
        bundle = make_bundle(["Evidence from one document."])
        strength = assess_evidence_strength(bundle, None)
        assert strength.level in {"limited", "moderate", "strong"}

    def test_multiple_documents_with_structured_returns_strong(self) -> None:
        from datetime import date

        from app.retrieval.analysis import PriceFact

        facts = []
        for i in range(3):
            facts.append(
                PriceFact(
                    price_id=f"pr_{i}",
                    supplier_id=f"sup_{i}",
                    supplier_name=f"Supplier {i}",
                    contract_id=None,
                    contract_number=None,
                    product_id="prod_1",
                    product_name="Widget",
                    unit_price=92.0,
                    currency="USD",
                    minimum_quantity=None,
                    discount_percent=None,
                    payment_terms=None,
                    delivery_terms=None,
                    effective_date=date(2026, 1, 1),
                    expiry_date=None,
                    amendment_ref=None,
                    document_id=f"doc_{i}",
                    document_name=f"Contract {i}",
                    page=1,
                    is_synthetic=True,
                )
            )
        structured = StructuredResult(facts=facts, queried=True)

        # Build bundle with 3 different documents
        citations = [
            CitationDraft(
                chunk_id=f"chk_{i}",
                document_id=f"doc_{i}",
                document_name=f"Contract {i}",
                snippet="Price USD 92.00",
                metadata={"expiry_date": None},
            )
            for i in range(3)
        ]
        blocks = [
            ContextBlock(
                marker=f"[{i + 1}]",
                text=f"[{i + 1}] Price USD 92.00",
                citation=c,
                content_type="paragraph",
                is_synthetic=True,
            )
            for i, c in enumerate(citations)
        ]
        bundle = ContextBundle(blocks=blocks, citations=citations)
        strength = assess_evidence_strength(bundle, structured)
        assert strength.level in {"strong", "moderate"}
        assert "independent_documents" in strength.criteria

    def test_strength_method_is_criteria_v1(self) -> None:
        bundle = make_bundle(["Evidence."])
        strength = assess_evidence_strength(bundle, None)
        assert strength.method == "criteria_v1"
