"""Background jobs, audit log, agent traces and evaluation runs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.ids import new_id
from app.db.base import Base, TenantScopedMixin, TimestampMixin

JOB_STATUSES = ("queued", "running", "succeeded", "failed", "cancelled")


class IngestionJob(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "ingestion_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("job"))
    document_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False, index=True)
    stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    stages_completed: Mapped[list[Any]] = mapped_column(default=list, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("aud"))
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    outcome: Mapped[str] = mapped_column(String(32), default="success", nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)


class AgentTrace(Base, TenantScopedMixin, TimestampMixin):
    """Execution trace of one agent run (safe events only, no chain-of-thought)."""

    __tablename__ = "agent_traces"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("trc"))
    query_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    iterations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    events: Mapped[list[Any]] = mapped_column(default=list, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    errors: Mapped[list[Any]] = mapped_column(default=list, nullable=False)


class EvaluationRun(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("evr"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    experiment: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dataset_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    config: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    summary: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    results: Mapped[list[EvaluationResult]] = relationship(back_populates="run", cascade="all, delete-orphan")


class EvaluationResult(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "evaluation_results"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("evq"))
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[str] = mapped_column(String(64), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    difficulty: Mapped[str | None] = mapped_column(String(32), nullable=True)
    expected_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_documents: Mapped[list[Any]] = mapped_column(default=list, nullable=False)
    expected_pages: Mapped[list[Any]] = mapped_column(default=list, nullable=False)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    retrieved_chunk_ids: Mapped[list[Any]] = mapped_column(default=list, nullable=False)
    retrieved_document_ids: Mapped[list[Any]] = mapped_column(default=list, nullable=False)
    retrieved_pages: Mapped[list[Any]] = mapped_column(default=list, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped[EvaluationRun] = relationship(back_populates="results")
