"""Golden dataset loading and validation.

The dataset lives as a JSON file on disk (``data/evaluation/golden_questions.json``)
so the ground truth is reviewable, versionable and independent of the code that
is being measured.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.core.errors import ValidationError


@dataclass(slots=True)
class GoldenQuestion:
    id: str
    question: str
    category: str
    difficulty: str = "medium"
    expected_answer: str | None = None
    expected_documents: list[str] = field(default_factory=list)
    expected_pages: list[int] = field(default_factory=list)
    expected_keywords: list[str] = field(default_factory=list)
    minimum_keyword_hits: int = 0
    is_unanswerable: bool = False
    notes: str | None = None

    @property
    def keyword_target(self) -> int:
        if self.minimum_keyword_hits:
            return self.minimum_keyword_hits
        return len(self.expected_keywords)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "question": self.question,
            "category": self.category,
            "difficulty": self.difficulty,
            "expected_answer": self.expected_answer,
            "expected_documents": self.expected_documents,
            "expected_pages": self.expected_pages,
            "expected_keywords": self.expected_keywords,
            "minimum_keyword_hits": self.minimum_keyword_hits,
            "is_unanswerable": self.is_unanswerable,
            "notes": self.notes,
        }


@dataclass(slots=True)
class GoldenDataset:
    name: str
    version: str = "0"
    path: str = ""
    questions: list[GoldenQuestion] = field(default_factory=list)

    @property
    def categories(self) -> list[str]:
        return sorted({question.category for question in self.questions})

    def filtered(self, *, categories: list[str] | None = None, limit: int | None = None) -> list[GoldenQuestion]:
        questions = self.questions
        if categories:
            wanted = {category.lower() for category in categories}
            questions = [question for question in questions if question.category.lower() in wanted]
        if limit is not None:
            questions = questions[:limit]
        return questions


def load_golden_dataset(directory: Path | str, *, filename: str = "golden_questions.json") -> GoldenDataset:
    """Read and validate the golden dataset from ``directory``."""
    root = Path(directory)
    path = root / filename
    if not path.exists():
        raise ValidationError(
            "No golden evaluation dataset found.",
            details={"expected_path": str(path)},
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    questions = [
        GoldenQuestion(
            id=str(item["id"]),
            question=str(item["question"]),
            category=str(item.get("category", "general")),
            difficulty=str(item.get("difficulty", "medium")),
            expected_answer=item.get("expected_answer"),
            expected_documents=[str(value) for value in item.get("expected_documents", [])],
            expected_pages=[int(value) for value in item.get("expected_pages", [])],
            expected_keywords=[str(value) for value in item.get("expected_keywords", [])],
            minimum_keyword_hits=int(item.get("minimum_keyword_hits", 0)),
            is_unanswerable=bool(item.get("is_unanswerable", False)),
            notes=item.get("notes"),
        )
        for item in raw.get("questions", [])
    ]
    seen: set[str] = set()
    for question in questions:
        if question.id in seen:
            raise ValidationError("Duplicate question id in the golden dataset.", details={"id": question.id})
        seen.add(question.id)
    return GoldenDataset(
        name=str(raw.get("name", path.stem)),
        version=str(raw.get("version", "0")),
        path=str(path),
        questions=questions,
    )
