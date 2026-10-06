"""Query / answer / citation records — the audit trail behind every answer."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.ids import new_id
from app.db.base import Base, TenantScopedMixin, TimestampMixin

ANSWER_STATUSES = ("supported", "partial", "insufficient_evidence", "conflicting", "error")


class Conversation(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("cnv"))
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), default="New conversation", nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Message(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "conversation_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("msg"))
    conversation_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    query_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)


class QueryRecord(Base, TenantScopedMixin, TimestampMixin):
    """One row per user question; the query_id joins to the agent trace."""

    __tablename__ = "queries"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("qry"))
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    classification: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    rewritten_queries: Mapped[list[Any]] = mapped_column(default=list, nullable=False)
    strategy: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tool_calls: Mapped[list[Any]] = mapped_column(default=list, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retrieval_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generation_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_usage: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    degraded: Mapped[bool] = mapped_column(default=False, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class AnswerRecord(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "answers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("ans"))
    query_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="supported", nullable=False, index=True)
    generation_mode: Mapped[str] = mapped_column(String(64), default="extractive", nullable=False)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_strength: Mapped[str | None] = mapped_column(String(32), nullable=True)
    grounding: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    conflicts: Mapped[list[Any]] = mapped_column(default=list, nullable=False)
    verification: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    retrieval_plan: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)

    citations: Mapped[list[Citation]] = relationship(
        back_populates="answer", cascade="all, delete-orphan"
    )


class Citation(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("cit"))
    answer_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("answers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    query_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    chunk_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    document_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    document_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section: Mapped[str | None] = mapped_column(String(512), nullable=True)
    clause: Mapped[str | None] = mapped_column(String(255), nullable=True)
    snippet: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_type: Mapped[str] = mapped_column(String(64), default="document", nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(default=False, nullable=False)
    verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)

    answer: Mapped[AnswerRecord] = relationship(back_populates="citations")
