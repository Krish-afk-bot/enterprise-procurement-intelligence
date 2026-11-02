"""v2 golden dataset (``data/evaluation/v2/questions.json``).

Schema v2 exists because the v1 dataset could not support the measurements the
project needs:

* ``expected_facts`` is a list of literal strings, so answer correctness is
  "does the answer contain this exact figure/term", not a fuzzy keyword count;
* ``expected_refusal`` separates the answerable questions from the
  unanswerable/adversarial ones, so refusal *precision* and *recall* can be
  reported instead of a single mixed accuracy;
* ``corpus`` and ``adversarial`` record where the question came from and whether
  it targets the system's failure modes.

Labels were written from the corpus generator (``scripts/make_synthetic_corpus.py``)
and the generated files on disk — never from the pipeline that is being
measured, so a run cannot mark its own homework.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.core.errors import ValidationError

DEFAULT_FILENAME = "questions.json"


@dataclass(slots=True)
class V2Question:
    id: str
    question: str
    category: str
    corpus: str = "synthetic"
    difficulty: str = "medium"
    expected_answer: str | None = None
    #: Literal strings a correct answer must contain (case-insensitive).
    expected_facts: list[str] = field(default_factory=list)
    expected_documents: list[str] = field(default_factory=list)
    #: 1-based page numbers, only where the page is part of the label.
    expected_pages: list[int] = field(default_factory=list)
    expected_refusal: bool = False
    adversarial: bool = False
    notes: str | None = None

    @property
    def answerable(self) -> bool:
        return not self.expected_refusal

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "question": self.question,
            "category": self.category,
            "corpus": self.corpus,
            "difficulty": self.difficulty,
            "expected_answer": self.expected_answer,
            "expected_facts": self.expected_facts,
            "expected_documents": self.expected_documents,
            "expected_pages": self.expected_pages,
            "expected_refusal": self.expected_refusal,
            "adversarial": self.adversarial,
            "notes": self.notes,
        }


@dataclass(slots=True)
class V2Dataset:
    name: str
    version: str = "0"
    path: str = ""
    created: str = ""
    questions: list[V2Question] = field(default_factory=list)

    @property
    def categories(self) -> list[str]:
        return sorted({question.category for question in self.questions})

    @property
    def refusal_count(self) -> int:
        return sum(1 for question in self.questions if question.expected_refusal)

    @property
    def adversarial_count(self) -> int:
        return sum(1 for question in self.questions if question.adversarial)

    def filtered(
        self, *, categories: list[str] | None = None, limit: int | None = None
    ) -> list[V2Question]:
        questions = self.questions
        if categories:
            wanted = {category.lower() for category in categories}
            questions = [question for question in questions if question.category.lower() in wanted]
        if limit is not None:
            questions = questions[:limit]
        return questions

    def summary(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "path": self.path,
            "created": self.created,
            "question_count": len(self.questions),
            "categories": self.categories,
            "refusal_expected": self.refusal_count,
            "adversarial": self.adversarial_count,
            "refusal_share": round(self.refusal_count / len(self.questions), 4) if self.questions else None,
        }


def load_v2_dataset(directory: Path | str, *, filename: str = DEFAULT_FILENAME) -> V2Dataset:
    """Read and validate the v2 golden dataset from ``directory``."""
    root = Path(directory)
    path = root / filename
    if not path.exists():
        raise ValidationError(
            "No v2 golden evaluation dataset found.",
            details={"expected_path": str(path)},
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    questions = [
        V2Question(
            id=str(item["id"]),
            question=str(item["question"]),
            category=str(item.get("category", "general")),
            corpus=str(item.get("corpus", "synthetic")),
            difficulty=str(item.get("difficulty", "medium")),
            expected_answer=item.get("expected_answer"),
            expected_facts=[str(value) for value in item.get("expected_facts", [])],
            expected_documents=[str(value) for value in item.get("expected_documents", [])],
            expected_pages=[int(value) for value in item.get("expected_pages", [])],
            expected_refusal=bool(item.get("expected_refusal", False)),
            adversarial=bool(item.get("adversarial", False)),
            notes=item.get("notes"),
        )
        for item in raw.get("questions", [])
    ]
    if not questions:
        raise ValidationError("The v2 golden dataset is empty.", details={"path": str(path)})
    seen: set[str] = set()
    for question in questions:
        if question.id in seen:
            raise ValidationError("Duplicate question id in the v2 golden dataset.", details={"id": question.id})
        seen.add(question.id)
    return V2Dataset(
        name=str(raw.get("name", path.stem)),
        version=str(raw.get("version", "0")),
        path=str(path),
        created=str(raw.get("created", "")),
        questions=questions,
    )


__all__ = ["DEFAULT_FILENAME", "V2Dataset", "V2Question", "load_v2_dataset"]
