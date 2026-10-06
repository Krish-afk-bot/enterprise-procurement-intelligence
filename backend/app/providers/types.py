"""Provider-neutral data types shared by every adapter.

No vendor SDK types ever leak past this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant", "tool"]


class ProviderStatus(BaseModel):
    """Reported by /health so the UI can show 'unavailable' instead of guessing."""

    kind: str
    name: str
    available: bool
    detail: str = ""
    model: str | None = None
    is_model: bool = True
    attributes: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def of(
        cls,
        kind: str,
        name: str,
        available: bool,
        *,
        detail: str = "",
        model: str | None = None,
        is_model: bool = True,
        **attributes: Any,
    ) -> ProviderStatus:
        return cls(
            kind=kind,
            name=name,
            available=available,
            detail=detail,
            model=model,
            is_model=is_model,
            attributes=attributes,
        )


@dataclass(slots=True)
class LLMMessage:
    role: Role
    content: str
    name: str | None = None

    def as_dict(self) -> dict[str, str]:
        payload = {"role": self.role, "content": self.content}
        if self.name:
            payload["name"] = self.name
        return payload


class LLMResponse(BaseModel):
    text: str
    model: str | None = None
    provider: str
    mode: Literal["llm", "extractive", "deterministic"] = "llm"
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: int | None = None
    finish_reason: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

    @property
    def total_tokens(self) -> int | None:
        if self.prompt_tokens is None and self.completion_tokens is None:
            return None
        return (self.prompt_tokens or 0) + (self.completion_tokens or 0)


class VisionResponse(BaseModel):
    text: str
    provider: str
    model: str | None = None
    mode: Literal["vlm", "ocr", "unavailable"] = "vlm"
    latency_ms: int | None = None


class RerankScore(BaseModel):
    index: int
    score: float


class VectorPoint(BaseModel):
    id: str
    vector: list[float]
    payload: dict[str, Any] = Field(default_factory=dict)


class VectorHit(BaseModel):
    id: str
    score: float
    payload: dict[str, Any] = Field(default_factory=dict)
    source: Literal["dense", "sparse", "fused", "rerank"] = "dense"


class GraphNode(BaseModel):
    label: str
    key: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    type: str
    start_label: str
    start_key: str
    end_label: str
    end_key: str
    properties: dict[str, Any] = Field(default_factory=dict)


@dataclass(slots=True)
class GraphPath:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    hops: int = 0


@dataclass(slots=True)
class StoredObject:
    key: str
    size: int
    content_type: str | None = None
    uri: str | None = None
