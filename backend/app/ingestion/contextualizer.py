"""Contextual retrieval enrichment (PRD s.26).

A bare chunk like *"The price shall remain fixed for 12 months."* is embedded
with its identity attached::

    Supplier: Northwind Industrial · Contract: CTR-2024-001 (v1) · Document:
    Master Supply Agreement · Section: Pricing · Page 4
    ---
    The price shall remain fixed for 12 months.

The original content is preserved untouched next to the enriched representation —
the enriched text is what is embedded and BM25-indexed, the original is what is
shown to the user and quoted in citations.

When an LLM is configured and ``CONTEXTUAL_LLM_ENRICHMENT`` is enabled, a short
situating preamble is generated and prepended; otherwise the deterministic
contextual header is used. Both modes are recorded on the chunk so evaluation can
compare them.
"""

from __future__ import annotations

from app.config.settings import Settings
from app.ingestion.chunking import ChunkDraft
from app.observability.logging import get_logger
from app.providers.router import ModelRouter, Task
from app.providers.types import LLMMessage

logger = get_logger(__name__)

CONTEXT_SEPARATOR = "\n---\n"

SYSTEM_PROMPT = (
    "You situate an excerpt inside its source document so it can be retrieved on its own. "
    "Reply with ONE or TWO short sentences naming the supplier, the contract/document and the "
    "topic of the excerpt. Use only the supplied facts. Output no preamble, no bullet points."
)


def build_context_header(
    draft: ChunkDraft,
    *,
    document_title: str,
    document_type: str,
    supplier_name: str | None,
    contract_number: str | None,
    version: int | None,
    is_synthetic: bool,
) -> str:
    parts: list[str] = []
    if supplier_name:
        parts.append(f"Supplier: {supplier_name}")
    if contract_number:
        label = f"Contract: {contract_number}"
        if version:
            label += f" (v{version})"
        parts.append(label)
    if document_title:
        parts.append(f"Document: {document_title}")
    if document_type:
        parts.append(f"Type: {document_type.replace('_', ' ')}")
    if draft.section:
        parts.append(f"Section: {draft.section}")
    if draft.subsection and draft.subsection != draft.section:
        parts.append(f"Subsection: {draft.subsection}")
    if draft.clause:
        parts.append(f"Clause: {draft.clause}")
    if draft.page_number:
        parts.append(f"Page: {draft.page_number}")
    if is_synthetic:
        parts.append("Data classification: synthetic test corpus")
    return " · ".join(parts)


def enrich_drafts(
    drafts: list[ChunkDraft],
    *,
    document_title: str,
    document_type: str,
    supplier_name: str | None = None,
    contract_number: str | None = None,
    version: int | None = None,
    is_synthetic: bool = False,
    settings: Settings | None = None,
) -> list[ChunkDraft]:
    """Attach a contextual representation to every draft (in place)."""
    enabled = settings.contextual_enrichment if settings else True
    for draft in drafts:
        if not enabled:
            draft.metadata["contextual"] = "disabled"
            continue
        header = build_context_header(
            draft,
            document_title=document_title,
            document_type=document_type,
            supplier_name=supplier_name,
            contract_number=contract_number,
            version=version,
            is_synthetic=is_synthetic,
        )
        draft.metadata["context_header"] = header
        draft.metadata["contextual"] = "header"
        draft.parent_content = draft.parent_content or None
    return drafts


def contextual_text(draft: ChunkDraft) -> str:
    """The string that is embedded/BM25-indexed."""
    header = draft.metadata.get("context_header") or ""
    if not header:
        return draft.content
    return f"{header}{CONTEXT_SEPARATOR}{draft.content}"


async def enrich_drafts_with_llm(
    drafts: list[ChunkDraft],
    *,
    document_title: str,
    router: ModelRouter,
    max_chunks: int = 40,
) -> tuple[list[ChunkDraft], dict[str, int]]:
    """Optional LLM-situated context (adds real model calls; off by default).

    Returns the drafts and a usage summary; if the model is unavailable the
    deterministic header is kept and the caller records the degradation.
    """
    usage = {"attempted": 0, "succeeded": 0, "failed": 0, "skipped": 0}
    for draft in drafts[:max_chunks]:
        header = draft.metadata.get("context_header") or ""
        usage["attempted"] += 1
        try:
            response = await router.generate(
                [
                    LLMMessage(role="system", content=SYSTEM_PROMPT),
                    LLMMessage(
                        role="user",
                        content=(
                            f"Known facts:\n{header or 'none'}\n\n"
                            f"Excerpt:\n{draft.content[:1500]}\n\n"
                            "Write the situating text."
                        ),
                    ),
                ],
                task=Task.EXTRACT,
                max_tokens=120,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("contextual_llm_failed", error=str(exc))
            usage["failed"] += 1
            continue
        text = (response.text or "").strip()
        if not text:
            usage["failed"] += 1
            continue
        draft.metadata["context_header"] = f"{header} · {text}" if header else text
        draft.metadata["contextual"] = "llm"
        usage["succeeded"] += 1
    usage["skipped"] = max(0, len(drafts) - max_chunks)
    return drafts, usage
