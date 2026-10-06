"""Query / search / answer schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import Field

from app.schemas.common import APIModel

Strategy = Literal["dense", "sparse", "hybrid", "hybrid_rerank", "hybrid_rerank_contextual", "agentic"]


class QueryFilters(APIModel):
    supplier_ids: list[str] = Field(default_factory=list)
    contract_ids: list[str] = Field(default_factory=list)
    document_ids: list[str] = Field(default_factory=list)
    document_types: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    effective_date_from: date | None = None
    effective_date_to: date | None = None
    include_expired: bool = True
    include_synthetic: bool = True
    include_structured: bool = True
    include_graph: bool = True
    include_vision: bool = True


def retrieval_filter_payload(filters: QueryFilters) -> dict[str, Any]:
    """Translate the API filter document into the retrieval filter DSL.

    Only fields that describe the corpus are forwarded, and each is forwarded
    only when it is actually set. A UI flag such as ``include_synthetic=True``
    or an unset list is *not* a corpus constraint: forwarding it verbatim makes
    the DSL require equality with a key the stored payload does not contain,
    which silently filters out every candidate.
    """
    payload: dict[str, Any] = {}
    for field, key in (
        ("supplier_ids", "supplier_id"),
        ("contract_ids", "contract_id"),
        ("document_ids", "document_id"),
        ("document_types", "document_type"),
        ("categories", "category"),
        ("regions", "region"),
    ):
        values = getattr(filters, field)
        if values:
            payload[key] = {"$in": list(values)}
    if not filters.include_synthetic:
        payload["is_synthetic"] = False
    return payload


class QueryRequest(APIModel):
    query: str = Field(min_length=2, max_length=4000)
    conversation_id: str | None = None
    filters: QueryFilters = Field(default_factory=QueryFilters)
    top_k: int | None = Field(default=None, ge=1, le=50)
    strategy: Strategy | None = None
    max_iterations: int | None = Field(default=None, ge=1, le=5)
    #: External research is opt-in and never mixed with enterprise evidence.
    external_research: bool = False
    include_trace: bool = False


class CitationOut(APIModel):
    chunk_id: str | None = None
    document_id: str | None = None
    document_name: str | None = None
    document_type: str | None = None
    page: int | None = None
    section: str | None = None
    clause: str | None = None
    snippet: str = ""
    source_uri: str | None = None
    score: float | None = None
    rank: int | None = None
    evidence_type: str = "document"
    is_synthetic: bool = False
    verified: bool = False
    #: Set when the prompt-injection detector matched instruction-like text in
    #: this passage: ``{score, patterns, suspicious}``. The passage stays
    #: evidence; its instructions are never treated as commands.
    injection: dict[str, Any] | None = None
    label: str = ""


class EvidenceStrengthOut(APIModel):
    level: Literal["strong", "moderate", "limited", "none"] = "none"
    method: str = ""
    criteria: dict[str, Any] = Field(default_factory=dict)


class GroundingOut(APIModel):
    method: str = ""
    supported_claims: int = 0
    total_claims: int = 0
    score: float | None = None
    unsupported_claims: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class ConflictOut(APIModel):
    kind: str
    description: str
    values: list[dict[str, Any]] = Field(default_factory=list)
    resolution: str = ""
    preferred: dict[str, Any] | None = None
    citations: list[CitationOut] = Field(default_factory=list)


class RetrievalStepOut(APIModel):
    name: str
    status: str = "ok"
    detail: str = ""
    candidates: int = 0
    latency_ms: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnswerOut(APIModel):
    query_id: str
    answer_text: str
    status: Literal["supported", "partial", "insufficient_evidence", "conflicting", "error"] = "supported"
    generation_mode: str = "extractive"
    model: str | None = None
    prompt_version: str | None = None
    evidence_strength: EvidenceStrengthOut = Field(default_factory=EvidenceStrengthOut)
    grounding: GroundingOut = Field(default_factory=GroundingOut)
    conflicts: list[ConflictOut] = Field(default_factory=list)
    citations: list[CitationOut] = Field(default_factory=list)
    retrieval_steps: list[RetrievalStepOut] = Field(default_factory=list)
    plan: dict[str, Any] = Field(default_factory=dict)
    validation: dict[str, Any] = Field(default_factory=dict)
    timings: dict[str, int] = Field(default_factory=dict)
    token_usage: dict[str, int] = Field(default_factory=dict)
    degraded: bool = False
    degradation_reasons: list[str] = Field(default_factory=list)
    external_sources: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)


class SearchRequest(APIModel):
    query: str = Field(min_length=1, max_length=2000)
    mode: Literal["hybrid", "dense", "sparse"] = "hybrid"
    filters: QueryFilters = Field(default_factory=QueryFilters)
    limit: int = Field(default=20, ge=1, le=100)
    rerank: bool = True


class SearchHitOut(APIModel):
    chunk_id: str
    document_id: str
    document_name: str
    document_type: str | None = None
    page: int | None = None
    section: str | None = None
    clause: str | None = None
    content: str = ""
    content_type: str = "paragraph"
    score: float | None = None
    dense_score: float | None = None
    sparse_score: float | None = None
    rerank_score: float | None = None
    fused_score: float | None = None
    rank: int | None = None
    is_synthetic: bool = False
    access_level: str = "internal"
    effective_date: date | None = None
    expiry_date: date | None = None
    version: int = 1
    matched_by: list[str] = Field(default_factory=list)


class SearchResponse(APIModel):
    query: str
    mode: str
    hits: list[SearchHitOut] = Field(default_factory=list)
    total: int = 0
    steps: list[RetrievalStepOut] = Field(default_factory=list)
    reranker: str | None = None
    embedding_model: str | None = None


class ConversationOut(APIModel):
    id: str
    title: str
    summary: str | None = None
    message_count: int = 0


class ConversationMessageOut(APIModel):
    id: str
    role: str
    content: str
    query_id: str | None = None
    created_at: datetime | None = None
