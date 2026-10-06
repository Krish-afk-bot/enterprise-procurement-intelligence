"""Context construction (PRD s.27, s.45, s.73).

Turns retrieved chunks into the model context:

* de-duplicates the same evidence retrieved by several routes,
* attaches parent-section context for parent-child retrieval,
* keeps the exact source text (never a paraphrase) so citations are quotable,
* sanitises untrusted document text and wraps it in non-authoritative markers,
* enforces a token budget so retrieval cannot overflow the window.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.ingestion.tokens import count_tokens, truncate_to_tokens
from app.observability.logging import get_logger
from app.retrieval.retriever import RetrievedChunk
from app.security.injection import (
    EVIDENCE_CLOSE,
    EVIDENCE_OPEN,
    INJECTION_SYSTEM_NOTE,
    detect_injection,
    sanitize_evidence,
)

logger = get_logger(__name__)


@dataclass(slots=True)
class CitationDraft:
    chunk_id: str | None
    document_id: str | None
    document_name: str
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
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def label(self) -> str:
        parts = [self.document_name]
        if self.page:
            parts.append(f"p.{self.page}")
        if self.section:
            parts.append(self.section[:60])
        return " — ".join(parts)

    def as_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "document_name": self.document_name,
            "document_type": self.document_type,
            "page": self.page,
            "section": self.section,
            "clause": self.clause,
            "snippet": self.snippet,
            "source_uri": self.source_uri,
            "score": self.score,
            "rank": self.rank,
            "evidence_type": self.evidence_type,
            "is_synthetic": self.is_synthetic,
            "verified": self.verified,
            "label": self.label,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class ContextBlock:
    marker: str
    text: str
    citation: CitationDraft
    content_type: str
    is_synthetic: bool
    injection: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ContextBundle:
    blocks: list[ContextBlock] = field(default_factory=list)
    citations: list[CitationDraft] = field(default_factory=list)
    token_estimate: int = 0
    truncated: bool = False
    dropped: int = 0
    injection_flags: list[dict[str, Any]] = field(default_factory=list)
    parents_used: int = 0

    def render(self) -> str:
        return "\n".join([EVIDENCE_OPEN, *[block.text for block in self.blocks], EVIDENCE_CLOSE])

    @property
    def system_note(self) -> str:
        return INJECTION_SYSTEM_NOTE

    def as_dict(self) -> dict[str, Any]:
        return {
            "blocks": len(self.blocks),
            "token_estimate": self.token_estimate,
            "truncated": self.truncated,
            "dropped": self.dropped,
            "injection_flags": self.injection_flags,
            "parents_used": self.parents_used,
        }


class ContextBuilder:
    def __init__(self, *, max_chunks: int = 12, max_tokens: int = 6000, snippet_chars: int = 700) -> None:
        self.max_chunks = max_chunks
        self.max_tokens = max_tokens
        self.snippet_chars = snippet_chars

    def build(
        self,
        chunks: list[RetrievedChunk],
        *,
        parents: dict[str, tuple[str, str | None]] | None = None,
        extra_blocks: list[tuple[CitationDraft, str, str]] | None = None,
    ) -> ContextBundle:
        bundle = ContextBundle()
        seen: set[tuple[str, int | None, str]] = set()

        for chunk in chunks:
            key = (chunk.document_id, chunk.page, chunk.content[:200])
            if key in seen:
                bundle.dropped += 1
                continue
            seen.add(key)
            if len(bundle.blocks) >= self.max_chunks:
                bundle.dropped += 1
                continue

            body = chunk.content.strip()
            parent_text = None
            if parents and chunk.parent_chunk_id and chunk.parent_chunk_id in parents:
                candidate, _section = parents[chunk.parent_chunk_id]
                if candidate and candidate.strip() != body:
                    parent_text = candidate.strip()
                    bundle.parents_used += 1

            report = detect_injection(body)
            if report.suspicious:
                bundle.injection_flags.append(
                    {"chunk_id": chunk.chunk_id, "document_id": chunk.document_id, **report.as_dict()}
                )

            header = self._header(chunk)
            editorial = ""
            if parent_text:
                editorial = f"[Section context: {truncate_to_tokens(parent_text, 220)}]\n"
            marker = f"[{len(bundle.blocks) + 1}]"
            budget = self.max_tokens - bundle.token_estimate
            if budget <= 120:
                bundle.truncated = True
                bundle.dropped += 1
                continue
            quoted = sanitize_evidence(body, max_chars=2400)
            text = f"{marker} {header}\n{editorial}{quoted}"
            block_tokens = count_tokens(text)
            if block_tokens > budget:
                text = truncate_to_tokens(text, budget - 10)
                block_tokens = count_tokens(text)
                bundle.truncated = True

            bundle.token_estimate += block_tokens
            citation = CitationDraft(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                document_name=chunk.document_name,
                document_type=chunk.document_type,
                page=chunk.page,
                section=chunk.section,
                clause=chunk.clause,
                snippet=body[: self.snippet_chars],
                source_uri=None,
                score=chunk.rerank_score if chunk.rerank_score is not None else chunk.fused_score,
                rank=chunk.rank,
                evidence_type="document",
                is_synthetic=chunk.is_synthetic,
                verified=True,
                metadata={
                    "content_type": chunk.content_type,
                    "matched_by": chunk.matched_by,
                    "version": chunk.version,
                    "effective_date": chunk.effective_date.isoformat() if chunk.effective_date else None,
                    "expiry_date": chunk.expiry_date.isoformat() if chunk.expiry_date else None,
                    "access_level": chunk.access_level,
                    "tables": chunk.tables,
                    # Instruction-like text is recorded on the citation so the
                    # interface can mark the passage as untrusted document
                    # content instead of showing it as ordinary evidence.
                    **({"injection": report.as_dict()} if report.patterns else {}),
                },
            )
            bundle.blocks.append(
                ContextBlock(
                    marker=marker,
                    text=text,
                    citation=citation,
                    content_type=chunk.content_type,
                    is_synthetic=chunk.is_synthetic,
                    injection=report.as_dict(),
                )
            )
            bundle.citations.append(citation)

        for citation, text, content_type in extra_blocks or []:
            if len(bundle.blocks) >= self.max_chunks:
                bundle.dropped += 1
                continue
            marker = f"[{len(bundle.blocks) + 1}]"
            block_text = f"{marker} {text}"
            tokens = count_tokens(block_text)
            if bundle.token_estimate + tokens > self.max_tokens:
                continue
            bundle.token_estimate += tokens
            bundle.blocks.append(
                ContextBlock(
                    marker=marker, text=block_text, citation=citation, content_type=content_type, is_synthetic=False
                )
            )
            bundle.citations.append(citation)

        return bundle

    @staticmethod
    def _header(chunk: RetrievedChunk) -> str:
        parts = [f"Source: {chunk.document_name}"]
        if chunk.document_type:
            parts.append(chunk.document_type.replace("_", " "))
        if chunk.page:
            parts.append(f"page {chunk.page}")
        if chunk.section:
            parts.append(f"section: {chunk.section}")
        if chunk.clause:
            parts.append(f"clause {chunk.clause}")
        if chunk.version and chunk.version > 1:
            parts.append(f"version {chunk.version}")
        if chunk.effective_date:
            parts.append(f"effective {chunk.effective_date.isoformat()}")
        if chunk.expiry_date:
            parts.append(f"expires {chunk.expiry_date.isoformat()}")
        if chunk.is_synthetic:
            parts.append("SYNTHETIC TEST DATA")
        return " | ".join(parts)


def prompt_evidence_header(bundle: ContextBundle, title: str) -> str:
    return (
        f"{title}\n"
        f"{INJECTION_SYSTEM_NOTE}\n"
        f"Evidence blocks: {len(bundle.blocks)}; approximate tokens: {bundle.token_estimate}."
    )
