"""Tests for the v2 evaluation harness (metrics, dataset, failure taxonomy).

These lock the invariants the Phase 1 baseline depends on:

* a metric with no data is ``None``, never a fabricated 0;
* latency percentiles keep the outliers;
* refusal is scored with precision *and* recall;
* a dataset question that is answered from structured records must not claim a
  document source (the label defect that inflated the baseline);
* every failure gets exactly one taxonomy label.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.errors import ValidationError
from app.evaluation.metrics import (
    citation_precision,
    latency_percentiles,
    refusal_confusion,
    refusal_precision_recall,
    wilson_interval,
)
from app.evaluation.v2_dataset import load_v2_dataset
from app.evaluation.v2_runner import FAILURE_LABELS, _failure_label

#: A miniature dataset that satisfies the v2 schema. The production dataset
#: (`data/evaluation/v2/questions.json`) was removed by the repository cleanup, so
#: these tests exercise the loader and its invariants against a fixture rather
#: than asserting the size of a benchmark that no longer exists.
FIXTURE_QUESTIONS = [
    {
        "id": "q-1",
        "question": "What unit price is recorded for the reagent pack?",
        "category": "price_lookup",
        "expected_facts": ["12.50"],
        "expected_documents": ["price_schedule.pdf"],
    },
    {
        "id": "q-2",
        "question": "How many records are in the 2025 purchase history?",
        "category": "aggregation",
        "expected_facts": ["42"],
        # Structured-only: it must never claim a document source.
        "expected_documents": [],
    },
    {
        "id": "q-3",
        "question": "What does clause 7.2 say about termination?",
        "category": "contract_terms",
        "expected_facts": ["clause 7.2"],
        "expected_documents": ["master_agreement.pdf"],
    },
    {
        "id": "q-4",
        "question": "What warranty period applies to the 2019 agreement?",
        "category": "adversarial",
        "expected_refusal": True,
        "adversarial": True,
        "expected_facts": [],
        "expected_documents": [],
    },
]


def _write_fixture(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": "v2-fixture",
        "version": "1",
        "created": "2026-11-11",
        "questions": FIXTURE_QUESTIONS,
    }
    (directory / "questions.json").write_text(json.dumps(payload), encoding="utf-8")
    return directory


# --------------------------------------------------------------------- metrics
def test_wilson_interval_matches_known_values() -> None:
    interval = wilson_interval(5, 10)
    assert interval is not None
    assert interval["rate"] == 0.5
    assert interval["low"] == 0.2366
    assert interval["high"] == 0.7634
    assert interval["successes"] == 5 and interval["total"] == 10


def test_wilson_interval_without_data_is_none() -> None:
    assert wilson_interval(0, 0) is None


def test_wilson_interval_stays_inside_zero_one() -> None:
    low = wilson_interval(0, 3)
    high = wilson_interval(3, 3)
    assert low is not None and low["low"] == 0.0
    assert high is not None and high["high"] == 1.0


def test_latency_percentiles_keep_outliers() -> None:
    stats = latency_percentiles([10, 20, 30, 40, 1000])
    assert stats["count"] == 5
    assert stats["p50"] == 30.0
    assert stats["p95"] == 1000.0
    assert stats["max"] == 1000.0
    assert stats["mean"] == 220.0


def test_latency_percentiles_ignore_missing_values() -> None:
    stats = latency_percentiles([None, 100, None])
    assert stats["count"] == 1
    assert stats["p50"] == 100.0


def test_latency_percentiles_without_data_report_none() -> None:
    stats = latency_percentiles([])
    assert stats == {"count": 0, "p50": None, "p95": None, "max": None, "mean": None}


def test_refusal_confusion_and_precision_recall() -> None:
    rows = [
        {"expected_refusal": True, "refused": True},    # tp
        {"expected_refusal": True, "refused": False},   # fn
        {"expected_refusal": False, "refused": True},   # fp
        {"expected_refusal": False, "refused": False},  # tn
    ]
    counts = refusal_confusion(rows)
    assert counts == {"tp": 1, "fp": 1, "fn": 1, "tn": 1}
    scores = refusal_precision_recall(counts)
    assert scores["precision"] == 0.5
    assert scores["recall"] == 0.5


def test_refusal_scores_are_none_without_a_denominator() -> None:
    scores = refusal_precision_recall({"tp": 0, "fp": 0, "fn": 0, "tn": 4})
    assert scores["precision"] is None
    assert scores["recall"] is None


def test_citation_precision_counts_only_labelled_sources() -> None:
    assert citation_precision(["a.pdf", "z.pdf"], ["a.pdf", "b.pdf"]) == 0.5
    assert citation_precision([], ["a.pdf"]) is None
    assert citation_precision(["a.pdf"], []) is None


# --------------------------------------------------------------------- dataset
def test_v2_dataset_shape(tmp_path: Path) -> None:
    dataset = load_v2_dataset(_write_fixture(tmp_path / "v2"))
    summary = dataset.summary()
    assert summary["name"] == "v2-fixture"
    assert summary["question_count"] == len(FIXTURE_QUESTIONS)
    assert summary["categories"] == ["adversarial", "aggregation", "contract_terms", "price_lookup"]
    assert summary["refusal_share"] == 0.25
    assert summary["adversarial"] == 1
    assert len({question.id for question in dataset.questions}) == len(dataset.questions)


def test_aggregation_questions_have_no_document_label(tmp_path: Path) -> None:
    """Regression: an SQL-answered question must not claim a document source.

    A structured row set is never imported as a document, so labelling
    aggregation questions with it inflates the retrieval denominator with
    sources that could never be retrieved.
    """
    dataset = load_v2_dataset(_write_fixture(tmp_path / "v2"))
    aggregation = [q for q in dataset.questions if q.category == "aggregation"]
    assert aggregation
    assert all(not q.expected_documents for q in aggregation)


def test_every_answerable_question_has_facts_and_a_source(tmp_path: Path) -> None:
    dataset = load_v2_dataset(_write_fixture(tmp_path / "v2"))
    for question in dataset.questions:
        if question.expected_refusal:
            continue
        assert question.expected_facts, question.id
        # every answerable question is either document-backed or structured
        assert question.expected_documents or question.category == "aggregation", question.id


def test_unanswerable_questions_do_not_claim_sources(tmp_path: Path) -> None:
    dataset = load_v2_dataset(_write_fixture(tmp_path / "v2"))
    for question in dataset.questions:
        if question.expected_refusal:
            assert not question.expected_documents, question.id


def test_missing_dataset_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        load_v2_dataset(tmp_path)


# -------------------------------------------------------------------- taxonomy
def _row(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "error": None,
        "expected_refusal": False,
        "refused": False,
        "answer_correct": True,
        "expected_documents": ["a.pdf"],
        "retrieved_documents": ["a.pdf"],
        "cited_documents": ["a.pdf"],
        "grounding_total": 1,
        "grounding_supported": 1,
        "status": "supported",
    }
    base.update(overrides)
    return base


def test_failure_labels_are_a_fixed_set() -> None:
    assert set(FAILURE_LABELS) == {
        "retrieval_miss",
        "wrong_context_selected",
        "generation_error",
        "verification_miss",
        "refusal_failure",
        "error",
    }


def test_correct_answer_has_no_label() -> None:
    assert _failure_label(_row()) is None


def test_correct_refusal_has_no_label() -> None:
    assert _failure_label(_row(expected_refusal=True, refused=True, answer_correct=None)) is None


def test_exception_is_labelled_error() -> None:
    assert _failure_label(_row(error="boom")) == "error"


def test_over_refusal_is_a_refusal_failure() -> None:
    assert _failure_label(_row(refused=True)) == "refusal_failure"


def test_under_refusal_is_a_refusal_failure() -> None:
    assert _failure_label(_row(expected_refusal=True, refused=False, answer_correct=None)) == "refusal_failure"


def test_missing_source_is_a_retrieval_miss() -> None:
    row = _row(answer_correct=False, retrieved_documents=["other.pdf"], cited_documents=[])
    assert _failure_label(row) == "retrieval_miss"


def test_retrieved_but_not_cited_is_wrong_context() -> None:
    row = _row(answer_correct=False, cited_documents=["other.pdf"])
    assert _failure_label(row) == "wrong_context_selected"


def test_wrong_answer_reported_as_verified_is_a_verification_miss() -> None:
    row = _row(answer_correct=False, status="supported", grounding_total=2, grounding_supported=2)
    assert _failure_label(row) == "verification_miss"


def test_wrong_answer_not_verified_is_a_generation_error() -> None:
    row = _row(answer_correct=False, status="partial", grounding_total=2, grounding_supported=1)
    assert _failure_label(row) == "generation_error"


# ------------------------------------------------------------- runner row scoring
def test_score_reads_the_grounding_result_keys() -> None:
    """``GroundingResult.as_dict()`` says ``total_claims``/``supported_claims``.

    The runner used to read ``total``/``supported``, so every row reported 0/0
    and a supported answer could be mislabelled ``verification_miss``.
    """
    from app.evaluation.v2_dataset import V2Question
    from app.evaluation.v2_runner import V2Runner

    runner = object.__new__(V2Runner)
    question = V2Question(id="q-1", question="What is the unit price?", category="price_lookup", expected_facts=["100"])
    row = runner._score(
        question,
        {
            "answer_text": "The unit price is 100.",
            "status": "partial",
            "grounding": {"supported_claims": 1, "total_claims": 3},
        },
    )
    assert row["grounding_supported"] == 1
    assert row["grounding_total"] == 3
