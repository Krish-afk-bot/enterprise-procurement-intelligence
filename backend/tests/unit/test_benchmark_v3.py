"""Benchmark v3 dataset and scoring.

The dataset is checked as data, not as a fixture: every answerable question must
carry facts and an evidence quote, every unanswerable one must expect a refusal,
and no question may claim human review that did not happen. The scoring helpers
are tested on synthetic rows so a change in matching cannot silently inflate
recall.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.evaluation.benchmark import load_benchmark_dataset
from app.evaluation.benchmark_runner import (
    _citation_precision,
    _doc_hit,
    _failure_label,
    _ndcg_at_k,
    _recall_at_k,
    _reciprocal_rank,
)
from app.retrieval.query_understanding import understand_query_rule_based

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATASET_DIR = PROJECT_ROOT / "data" / "evaluation" / "benchmark_v3"

EXPECTED_CATEGORIES = {
    "document_metadata",
    "parties",
    "dates_and_duration",
    "payment_terms",
    "pricing_schedules",
    "clauses",
    "obligations",
    "amendments",
    "supplier_buyer_relationships",
    "graph_multi_hop",
    "historical_temporal",
    "unanswerable",
}


@pytest.fixture(scope="module")
def dataset():
    return load_benchmark_dataset(DATASET_DIR)


def test_dataset_has_120_questions_across_the_twelve_categories(dataset) -> None:
    assert len(dataset.questions) == 120
    assert {question.category for question in dataset.questions} == EXPECTED_CATEGORIES
    assert len({question.id for question in dataset.questions}) == 120


def test_every_answerable_question_carries_evidence(dataset) -> None:
    for question in dataset.questions:
        if question.answerability == "unanswerable":
            continue
        assert question.expected_facts, question.id
        assert question.evidence_quote, question.id
        assert question.evidence_verification.get("quote_matched") is True, question.id


def test_unanswerable_questions_expect_a_refusal(dataset) -> None:
    unanswerable = [q for q in dataset.questions if q.answerability == "unanswerable"]
    assert unanswerable
    for question in unanswerable:
        assert question.expected_refusal is True, question.id
        assert question.expected_facts == [], question.id
        assert question.evidence_verification.get("method") == "corpus_absence", question.id


def test_no_question_claims_human_review(dataset) -> None:
    assert all(question.review_status != "human_reviewed" for question in dataset.questions)
    assert all(question.reviewer is None for question in dataset.questions)


def test_temporal_labels_match_the_derived_as_of(dataset) -> None:
    temporal = [q for q in dataset.questions if q.temporal]
    assert temporal
    for question in temporal:
        plan = understand_query_rule_based(question.question)
        assert plan.as_of is not None, question.id
        assert plan.as_of.isoformat() == question.temporal["expected_as_of"], question.id


def test_document_matching_ignores_the_file_extension() -> None:
    assert _doc_hit("04f6f2_tender_10.html", ["04f6f2_tender_10"])
    assert not _doc_hit("04f6f2_tender_10.html", ["0508f7_tender_5"])


def test_retrieval_metrics_use_the_labelled_document() -> None:
    retrieved = ["a.html", "b.html", "c.html"]
    assert _recall_at_k(retrieved, ["b.html"], 5) == 1.0
    assert _recall_at_k(retrieved, ["b.html", "z.html"], 5) == 0.5
    assert _reciprocal_rank(retrieved, ["b.html"]) == 0.5
    assert _ndcg_at_k(retrieved, ["a.html"], 10) == 1.0
    assert _citation_precision(["a.html", "x.html"], ["a.html"]) == 0.5


def test_failure_labels_are_assigned_once() -> None:
    assert _failure_label({"error": "boom"}) == "error"
    assert _failure_label({"expected_refusal": True, "refused": False}) == "refusal_failure"
    assert _failure_label({"expected_refusal": True, "refused": True}) is None
    assert _failure_label(
        {
            "expected_refusal": False,
            "refused": False,
            "answer_correct": False,
            "expected_documents": ["a.html"],
            "retrieved_documents": ["b.html"],
        }
    ) == "retrieval_miss"
    assert _failure_label(
        {
            "expected_refusal": False,
            "refused": False,
            "answer_correct": False,
            "expected_documents": ["a.html"],
            "retrieved_documents": ["a.html"],
            "cited_documents": ["b.html"],
        }
    ) == "wrong_context_selected"
