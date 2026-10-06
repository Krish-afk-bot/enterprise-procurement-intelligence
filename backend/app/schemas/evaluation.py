"""Evaluation schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import APIModel

EXPERIMENTS = (
    "dense",
    "hybrid",
    "hybrid_rerank",
    "hybrid_rerank_contextual",
    "agentic",
    "agentic_graph_sql",
    "multimodal",
)


class GoldenQuestionOut(APIModel):
    id: str
    question: str
    category: str
    difficulty: str = "medium"
    expected_answer: str | None = None
    expected_documents: list[str] = Field(default_factory=list)
    expected_pages: list[int] = Field(default_factory=list)
    expected_keywords: list[str] = Field(default_factory=list)
    is_unanswerable: bool = False
    notes: str | None = None


class EvaluationRunRequest(APIModel):
    name: str | None = None
    experiments: list[str] = Field(default_factory=lambda: ["hybrid_rerank"])
    categories: list[str] = Field(default_factory=list)
    dataset: str | None = None
    top_k: int = Field(default=10, ge=1, le=50)
    max_questions: int | None = Field(default=None, ge=1, le=500)


class MetricSummaryOut(APIModel):
    name: str
    value: float | None = None
    count: int = 0
    display: str = ""
    description: str = ""


class EvaluationRunOut(APIModel):
    id: str
    name: str
    experiment: str
    dataset_name: str | None = None
    status: str
    question_count: int = 0
    summary: dict[str, Any] = Field(default_factory=dict)
    metrics: list[MetricSummaryOut] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None


class EvaluationResultOut(APIModel):
    id: str
    question_id: str
    question: str
    category: str | None = None
    difficulty: str | None = None
    expected_answer: str | None = None
    answer_text: str | None = None
    answer_status: str | None = None
    retrieved_document_ids: list[str] = Field(default_factory=list)
    retrieved_pages: list[int] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    latency_ms: int | None = None
    error: str | None = None


class EvaluationRunDetailOut(EvaluationRunOut):
    results: list[EvaluationResultOut] = Field(default_factory=list)


class EvaluationComparisonOut(APIModel):
    metric: str
    rows: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    has_data: bool = False


class ExperimentInfoOut(APIModel):
    name: str
    description: str
    requires: list[str] = Field(default_factory=list)
    runnable: bool = True
    unavailable_reason: str | None = None
