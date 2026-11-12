"""Benchmark v3 dataset: 120 questions with a recorded provenance trail.

Schema differences from v2:

* every question carries ``source_document_id``, the supporting page/section,
  the verbatim ``evidence_quote`` and how that quote was verified;
* ``answerability`` separates ``answerable`` from ``unanswerable`` and
  ``needs_review`` (evidence exists but no human has adjudicated the label);
* ``review_status`` records whether a human actually reviewed the label — the
  builder sets ``auto_verified`` only when the evidence was matched
  programmatically, and ``pending_review`` otherwise. Nothing is marked
  human-reviewed by the builder;
* ``temporal`` carries the as-of date the question depends on, if any.

The file is produced by ``scripts/build_benchmark_v3.py`` and is read-only for
the runner.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.core.errors import ValidationError

DEFAULT_FILENAME = "questions.json"

ANSWERABILITY = ("answerable", "unanswerable", "needs_review")
REVIEW_STATUSES = ("auto_verified", "pending_review", "human_reviewed")


@dataclass(slots=True)
class BenchmarkQuestion:
    id: str
    question: str
    category: str
    source_document_id: str | None = None
    source_document: str | None = None
    expected_answer: str | None = None
    expected_facts: list[str] = field(default_factory=list)
    expected_documents: list[str] = field(default_factory=list)
    expected_pages: list[int] = field(default_factory=list)
    supporting_section: str | None = None
    evidence_quote: str | None = None
    evidence_verification: dict = field(default_factory=dict)
    answerability: str = "answerable"
    review_status: str = "pending_review"
    reviewer: str | None = None
    adjudication_notes: str | None = None
    expected_refusal: bool = False
    temporal: dict | None = None
    provenance: dict = field(default_factory=dict)
    difficulty: str = "medium"

    @property
    def answerable(self) -> bool:
        return not self.expected_refusal

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "question": self.question,
            "category": self.category,
            "source_document_id": self.source_document_id,
            "source_document": self.source_document,
            "expected_answer": self.expected_answer,
            "expected_facts": self.expected_facts,
            "expected_documents": self.expected_documents,
            "expected_pages": self.expected_pages,
            "supporting_section": self.supporting_section,
            "evidence_quote": self.evidence_quote,
            "evidence_verification": self.evidence_verification,
            "answerability": self.answerability,
            "review_status": self.review_status,
            "reviewer": self.reviewer,
            "adjudication_notes": self.adjudication_notes,
            "expected_refusal": self.expected_refusal,
            "temporal": self.temporal,
            "provenance": self.provenance,
            "difficulty": self.difficulty,
        }


@dataclass(slots=True)
class BenchmarkDataset:
    name: str
    version: str = "0"
    path: str = ""
    created: str = ""
    corpus: dict = field(default_factory=dict)
    questions: list[BenchmarkQuestion] = field(default_factory=list)

    @property
    def categories(self) -> list[str]:
        return sorted({question.category for question in self.questions})

    def filtered(
        self, *, categories: list[str] | None = None, limit: int | None = None
    ) -> list[BenchmarkQuestion]:
        questions = self.questions
        if categories:
            wanted = {category.lower() for category in categories}
            questions = [question for question in questions if question.category.lower() in wanted]
        if limit is not None:
            questions = questions[:limit]
        return questions

    def summary(self) -> dict:
        counts: dict[str, int] = {}
        for question in self.questions:
            counts[question.category] = counts.get(question.category, 0) + 1
        verification: dict[str, int] = {}
        for question in self.questions:
            key = str(question.evidence_verification.get("method", "none"))
            verification[key] = verification.get(key, 0) + 1
        return {
            "name": self.name,
            "version": self.version,
            "path": self.path,
            "created": self.created,
            "question_count": len(self.questions),
            "categories": counts,
            "answerable": sum(1 for q in self.questions if q.answerability == "answerable"),
            "unanswerable": sum(1 for q in self.questions if q.answerability == "unanswerable"),
            "needs_review": sum(1 for q in self.questions if q.answerability == "needs_review"),
            "auto_verified": sum(1 for q in self.questions if q.review_status == "auto_verified"),
            "pending_review": sum(1 for q in self.questions if q.review_status == "pending_review"),
            "human_reviewed": sum(1 for q in self.questions if q.review_status == "human_reviewed"),
            "verification_methods": verification,
            "corpus": self.corpus,
        }


def load_benchmark_dataset(directory: Path | str, *, filename: str = DEFAULT_FILENAME) -> BenchmarkDataset:
    root = Path(directory)
    path = root / filename
    if not path.exists():
        raise ValidationError(
            "No benchmark dataset found.", details={"expected_path": str(path)}
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    questions: list[BenchmarkQuestion] = []
    for item in raw.get("questions", []):
        answerability = str(item.get("answerability", "answerable"))
        review_status = str(item.get("review_status", "pending_review"))
        if answerability not in ANSWERABILITY:
            raise ValidationError(
                "Unknown answerability value.", details={"id": item.get("id"), "value": answerability}
            )
        if review_status not in REVIEW_STATUSES:
            raise ValidationError(
                "Unknown review status.", details={"id": item.get("id"), "value": review_status}
            )
        questions.append(
            BenchmarkQuestion(
                id=str(item["id"]),
                question=str(item["question"]),
                category=str(item["category"]),
                source_document_id=item.get("source_document_id"),
                source_document=item.get("source_document"),
                expected_answer=item.get("expected_answer"),
                expected_facts=[str(value) for value in item.get("expected_facts", [])],
                expected_documents=[str(value) for value in item.get("expected_documents", [])],
                expected_pages=[int(value) for value in item.get("expected_pages", [])],
                supporting_section=item.get("supporting_section"),
                evidence_quote=item.get("evidence_quote"),
                evidence_verification=item.get("evidence_verification") or {},
                answerability=answerability,
                review_status=review_status,
                reviewer=item.get("reviewer"),
                adjudication_notes=item.get("adjudication_notes"),
                expected_refusal=bool(item.get("expected_refusal", False)),
                temporal=item.get("temporal"),
                provenance=item.get("provenance") or {},
                difficulty=str(item.get("difficulty", "medium")),
            )
        )
    if not questions:
        raise ValidationError("The benchmark dataset is empty.", details={"path": str(path)})
    seen: set[str] = set()
    for question in questions:
        if question.id in seen:
            raise ValidationError("Duplicate question id in the benchmark.", details={"id": question.id})
        seen.add(question.id)
    return BenchmarkDataset(
        name=str(raw.get("name", path.stem)),
        version=str(raw.get("version", "0")),
        path=str(path),
        created=str(raw.get("created", "")),
        corpus=raw.get("corpus") or {},
        questions=questions,
    )


__all__ = [
    "ANSWERABILITY",
    "BenchmarkDataset",
    "BenchmarkQuestion",
    "DEFAULT_FILENAME",
    "REVIEW_STATUSES",
    "load_benchmark_dataset",
]
