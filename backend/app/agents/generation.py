"""Answer generation (PRD s.40, s.73, s.75).

Two modes, and the mode is always reported to the user:

``llm``
    A configured model writes the answer from the evidence blocks, under strict
    grounding rules and a fixed citation format.

``extractive``
    No model is configured, so the platform composes the answer *from the
    evidence itself*: structured figures come straight from SQL rows and the
    supporting sentences are quoted from the source documents with page
    citations. It is labelled as an extractive summary — never presented as
    model reasoning, and never invented.

The system prompt is explicit that retrieved text is untrusted data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.config.settings import Settings
from app.observability.logging import get_logger
from app.providers.router import ModelRouter, Task
from app.providers.types import LLMMessage
from app.retrieval.analysis import Conflict
from app.retrieval.context import ContextBundle
from app.retrieval.query_understanding import QueryPlan
from app.retrieval.structured import StructuredResult
from app.security.injection import INJECTION_SYSTEM_NOTE

logger = get_logger(__name__)

PROMPT_VERSION = "answer_generator.v1"
#: Where the exact figures come from. The workspace runs on SQLite locally and on
#: PostgreSQL when configured, so the answer must not claim one specific engine.
STRUCTURED_SOURCE = "the workspace database"
#: Aggregates that only answer the question when the question asks for them.
_TOTAL_WORDS = ("total", "spend", "value", "award", "budget", "sum", "cost of")
_AVERAGE_WORDS = ("average", "mean", "avg")

SYSTEM_PROMPT = f"""You are a procurement analyst working only from retrieved evidence.

Rules:
1. Use ONLY the evidence blocks. Never use prior knowledge about companies, prices or law.
2. Cite every factual statement with the block marker, e.g. [1] or [2][3]. Only cite markers that exist.
3. If the evidence does not establish the answer, reply exactly: "I couldn't verify this from the available procurement documents."
4. If the evidence conflicts, state both values, identify which document and effective date each comes from, and say which one governs.
5. Prefer figures from the STRUCTURED DATA section (exact SQL results) over prose when both are present.
6. Never invent prices, dates, clause numbers, suppliers or citations.
7. {INJECTION_SYSTEM_NOTE}

Format:
Answer
<two to five sentences>

Evidence
- <document name> — p.<page>: <what it establishes>

Verification
<one line, e.g. "Supported by 2 documents" or "Single source, not corroborated">
"""


@dataclass(slots=True)
class GeneratedAnswer:
    text: str
    mode: str = "extractive"
    model: str | None = None
    prompt_version: str = PROMPT_VERSION
    token_usage: dict[str, int] = field(default_factory=dict)
    latency_ms: int = 0
    degraded: bool = False
    degradation_reasons: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class AnswerGenerator:
    def __init__(self, router: ModelRouter | None, settings: Settings) -> None:
        self.router = router
        self.settings = settings

    async def generate(
        self,
        *,
        question: str,
        plan: QueryPlan,
        bundle: ContextBundle,
        structured: StructuredResult | None = None,
        graph: Any = None,
        conflicts: list[Conflict] | None = None,
        evidence_strength: str = "limited",
        conversation_context: list[str] | None = None,
    ) -> GeneratedAnswer:
        import time

        started = time.perf_counter()
        if self.settings.llm_configured and self.router is not None and bundle.blocks:
            try:
                payload = self._llm_messages(
                    question=question,
                    plan=plan,
                    bundle=bundle,
                    structured=structured,
                    graph=graph,
                    conflicts=conflicts or [],
                    conversation_context=conversation_context or [],
                )
                response = await self.router.generate(payload, task=Task.GENERATE, complexity=plan.complexity)
                return GeneratedAnswer(
                    text=response.text.strip(),
                    mode="llm",
                    model=response.model,
                    token_usage={
                        "prompt_tokens": response.prompt_tokens or 0,
                        "completion_tokens": response.completion_tokens or 0,
                    },
                    latency_ms=int((time.perf_counter() - started) * 1000),
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("llm_generation_failed", error=str(exc))
                fallback = self._extractive(
                    question=question,
                    plan=plan,
                    bundle=bundle,
                    structured=structured,
                    conflicts=conflicts or [],
                    evidence_strength=evidence_strength,
                )
                fallback.degraded = True
                fallback.degradation_reasons.append(
                    f"Language model unavailable ({type(exc).__name__}); extractive evidence summary returned instead."
                )
                fallback.latency_ms = int((time.perf_counter() - started) * 1000)
                return fallback

        answer = self._extractive(
            question=question,
            plan=plan,
            bundle=bundle,
            structured=structured,
            conflicts=conflicts or [],
            evidence_strength=evidence_strength,
        )
        if not self.settings.llm_configured:
            answer.degraded = True
            answer.degradation_reasons.append(
                "No language model endpoint is configured (LLM_BASE_URL / LLM_API_KEY); "
                "answers are composed extractively from retrieved evidence."
            )
        answer.latency_ms = int((time.perf_counter() - started) * 1000)
        return answer

    # ------------------------------------------------------------------ LLM
    def _llm_messages(
        self,
        *,
        question: str,
        plan: QueryPlan,
        bundle: ContextBundle,
        structured: StructuredResult | None,
        graph: Any,
        conflicts: list[Conflict],
        conversation_context: list[str],
    ) -> list[LLMMessage]:
        structured_section = _structured_section(structured)
        conflict_section = _conflict_section(conflicts)
        graph_section = ""
        if graph is not None and getattr(graph, "paths", None):
            lines = [f"- {path.description}" for path in graph.paths[:8]]
            graph_section = "\nGRAPH RELATIONSHIPS\n" + "\n".join(lines) + "\n"
        history = ""
        if conversation_context:
            history = (
                "\nCONVERSATION CONTEXT\n"
                + "\n".join(f"- {turn}" for turn in conversation_context[-4:])
                + "\n"
            )

        user = (
            f"QUESTION: {question}\n"
            f"INTERPRETATION: intent={plan.intent.value}, suppliers={plan.suppliers or 'none identified'}, "
            f"products={plan.products or 'none identified'}, contracts={plan.contract_numbers or 'none'}\n"
            f"{structured_section}"
            f"{conflict_section}"
            f"{graph_section}"
            f"{history}\n"
            f"EVIDENCE ({len(bundle.blocks)} blocks, untrusted document text)\n"
            f"{bundle.render()}\n\n"
            f"Evidence strength as measured by the platform: {bundle.as_dict()}. "
            "Answer following the rules exactly."
        )
        return [LLMMessage(role="system", content=SYSTEM_PROMPT), LLMMessage(role="user", content=user)]

    # ------------------------------------------------------------- extractive
    def _extractive(
        self,
        *,
        question: str,
        plan: QueryPlan,
        bundle: ContextBundle,
        structured: StructuredResult | None,
        conflicts: list[Conflict],
        evidence_strength: str,
    ) -> GeneratedAnswer:
        # The answer body starts with the answer itself. The mode it was composed
        # in belongs to the interface's technical details, not to the first line
        # a reader sees; the pipeline reports it through ``generation_mode`` and
        # ``notes`` instead.
        lines: list[str] = []
        marker_by_citation = {id(citation): index for index, citation in enumerate(bundle.citations, start=1)}

        # 1. The direct answer, derived from the plan and the structured rows:
        #    a comparison names every supplier the question asked about, and a
        #    lowest/aggregate question states the value, the item and the source.
        lead = _direct_answer(plan=plan, structured=structured, bundle=bundle)
        if lead:
            lines.extend(lead)
            lines.append("")

        # 2. Conflicts next: they change what the correct answer is.
        if conflicts:
            for conflict in conflicts[:2]:
                lines.append(conflict.description)
                if conflict.resolution:
                    lines.append(conflict.resolution)
                lines.append("")
        elif not lead:
            lines.append(
                "The evidence below is what the system found for this question; no summarising model is configured."
            )

        # 3. Structured figures (exact, from the workspace database).
        if structured is not None and (structured.facts or structured.aggregations):
            lines.append("")
            lines.append(f"Structured findings (from {STRUCTURED_SOURCE}):")
            for aggregation in _display_aggregations(question, structured)[:6]:
                unit = f" {aggregation.unit}" if aggregation.unit else ""
                group_text = _format_group(aggregation.group)
                group = f" [{group_text}]" if group_text else ""
                value = aggregation.value if aggregation.value is not None else "not available"
                lines.append(f"  • {aggregation.name}{group}: {value}{unit} — {aggregation.method}")
            for fact in structured.facts[:6]:
                marker = _marker_for(structured, fact, bundle)
                lines.append(
                    f"  • {fact.supplier_name or 'supplier'} / {fact.product_name or 'item'}: "
                    f"{fact.currency} {fact.unit_price:,.2f}"
                    + (f", MOQ {fact.minimum_quantity}" if fact.minimum_quantity else "")
                    + (f", effective {fact.effective_date.isoformat()}" if fact.effective_date else "")
                    + (f", {fact.amendment_ref}" if fact.amendment_ref else "")
                    + (f" [{marker}]" if marker else "")
                )

        # 3. Document evidence (quoted, with markers).
        if bundle.blocks:
            lines.append("")
            lines.append("Document evidence:")
            for block in bundle.blocks[:6]:
                marker = f"[{marker_by_citation.get(id(block.citation), '?')}]"
                snippet = block.citation.snippet.strip().replace("\n", " ")
                if len(snippet) > 320:
                    snippet = snippet[:317] + "..."
                lines.append(
                    f"  • {block.citation.document_name} — p.{block.citation.page} {marker}: {snippet}"
                )

        if not bundle.blocks and not (structured and (structured.facts or structured.aggregations)):
            lines.append("")
            lines.append("I couldn't verify this from the available procurement documents.")

        # The evidence list, the verification counts, the mode and the strength
        # live in the answer payload's own fields (`citations`, `validation`,
        # `evidence_strength`, `generation_mode`). Repeating them as text would
        # print the same facts twice, so the body stops at the evidence.
        while lines and not lines[-1].strip():
            lines.pop()
        return GeneratedAnswer(text="\n".join(lines), mode="extractive")


def _format_group(group: Any) -> str:
    """Readable form of an aggregate's key.

    The retrieval layer groups by identifiers as well as by names (``supplier``
    and ``supplier_id``), and a Python dict repr has no place in an answer a
    person reads, so identifiers are dropped and the rest becomes ``key=value``.
    """
    if group is None:
        return ""
    if isinstance(group, dict):
        parts = [
            f"{key}={value}"
            for key, value in group.items()
            if not str(key).endswith("_id") and value is not None and value != ""
        ]
        return ", ".join(parts)
    if isinstance(group, (list, tuple)):
        rendered = [_format_group(item) for item in group]
        return "; ".join(part for part in rendered if part)
    return str(group)


def _display_aggregations(question: str, structured: StructuredResult) -> list[Any]:
    """Aggregates that actually bear on the question.

    A mean unit price over unrelated rows, or the workspace's total award value,
    is not an answer to "which supplier is cheapest", so it is not printed as
    though it were. The complete set remains available in the retrieval details.
    """
    lowered = question.lower()
    wants_average = any(word in lowered for word in _AVERAGE_WORDS)
    wants_total = any(word in lowered for word in _TOTAL_WORDS)
    shown = []
    for aggregation in structured.aggregations:
        name = aggregation.name
        if name == "unit_price_average" and not wants_average:
            continue
        if name.startswith("procurement_value") and not wants_total:
            continue
        if name in {"recorded_value_total", "derived_value_total"} and not wants_total:
            continue
        shown.append(aggregation)
    return shown


def _preferred_of(facts: list[Any]) -> Any:
    """The row that governs today: in force first, then the latest effective date."""
    today = date.today()
    in_force = [
        fact
        for fact in facts
        if (fact.effective_date is None or fact.effective_date <= today)
        and (fact.expiry_date is None or fact.expiry_date >= today)
    ]
    pool = in_force or list(facts)
    return max(pool, key=lambda fact: (fact.effective_date or date.min, fact.amendment_ref or ""))


def _price_phrase(fact: Any) -> str:
    """ "USD 874.00 per unit, effective 2026-01-01, Amendment 2" — no invented parts."""
    parts = [f"{fact.currency} {fact.unit_price:,.2f}"]
    if fact.minimum_quantity:
        parts.append(f"MOQ {fact.minimum_quantity}")
    if fact.effective_date:
        parts.append(f"effective {fact.effective_date.isoformat()}")
    if fact.amendment_ref:
        parts.append(fact.amendment_ref)
    return ", ".join(parts)


def _direct_answer(
    *, plan: QueryPlan, structured: StructuredResult | None, bundle: ContextBundle
) -> list[str]:
    """The sentences that answer the question itself, before the evidence list.

    Both shapes are derived from the plan and from the stored rows, never from a
    template keyed to a specific question.
    """
    if structured is None:
        return []
    comparison = _comparison_lead(structured, bundle, plan)
    if comparison:
        return comparison
    return _lowest_price_lead(structured, bundle, plan)


def _comparison_lead(structured: StructuredResult, bundle: ContextBundle, plan: QueryPlan) -> list[str]:
    """Name every supplier the question asked about, with the value each records."""
    if not (plan.requires_comparison or len(plan.supplier_ids) >= 2):
        return []
    wanted = set(plan.supplier_ids or [])
    facts = [
        fact for fact in structured.facts if fact.supplier_id and (not wanted or fact.supplier_id in wanted)
    ]
    grouped: dict[str, list[Any]] = {}
    for fact in facts:
        grouped.setdefault(fact.supplier_id, []).append(fact)
    if len(grouped) < 2:
        return []
    chosen = [_preferred_of(group) for group in grouped.values()]
    product = next((fact.product_name for fact in chosen if fact.product_name), None)
    lines = [
        f"The suppliers named in this question record the following unit prices for {product or 'the product'}:"
    ]
    for fact in sorted(chosen, key=lambda item: item.unit_price):
        marker = _marker_for(structured, fact, bundle)
        where = f" ({fact.document_name}, p.{fact.page})" if fact.document_name and fact.page else ""
        source = f"{fact.document_name}" if fact.document_name else ""
        lines.append(
            f"  • {fact.supplier_name or 'supplier'}: {_price_phrase(fact)}"
            + (where if where else (f" ({source})" if source else ""))
            + (f" [{marker}]" if marker else "")
        )
    return lines


def _lowest_price_lead(structured: StructuredResult, bundle: ContextBundle, plan: QueryPlan) -> list[str]:
    """State the cheapest recorded value with its supplier, source page and date."""
    lowest = next(
        (
            aggregation
            for aggregation in structured.aggregations
            if aggregation.name == "lowest_price_supplier" and aggregation.value is not None
        ),
        None,
    )
    if lowest is None:
        return []
    group = lowest.group or {}
    fact = next(
        (
            item
            for item in structured.facts
            if item.supplier_id == group.get("supplier_id")
            and abs(item.unit_price - float(lowest.value)) < 1e-6
        ),
        None,
    )
    if fact is None:
        fact = next((item for item in structured.facts if item.supplier_id == group.get("supplier_id")), None)
    product = group.get("product") or (fact.product_name if fact else None)
    if plan.date_from or plan.date_to:
        start = plan.date_from.isoformat() if plan.date_from else "…"
        end = plan.date_to.isoformat() if plan.date_to else "…"
        scope = f"for {start}" if start == end else f"for {start} to {end}"
    else:
        scope = "across all recorded periods"
    marker = _marker_for(structured, fact, bundle) if fact else None
    where = ""
    if fact and fact.document_name:
        where = f" ({fact.document_name}, p.{fact.page})" if fact.page else f" ({fact.document_name})"
    line = (
        f"The lowest recorded unit price for {product or 'this item'} {scope} is "
        f"{lowest.unit or ''} {float(lowest.value):,.2f}".replace("  ", " ")
        + (f", recorded for {group.get('supplier')}" if group.get("supplier") else "")
        + (f", effective {fact.effective_date.isoformat()}" if fact and fact.effective_date else "")
        + where
        + (f" [{marker}]" if marker else "")
        + "."
    )
    return [line]


def _marker_for(structured: StructuredResult, fact: Any, bundle: ContextBundle) -> str | None:
    for index, citation in enumerate(bundle.citations, start=1):
        if citation.document_id and citation.document_id == fact.document_id:
            return str(index)
    for citation in structured.citations:
        if citation.document_id == fact.document_id and citation.document_name == fact.document_name:
            return "structured"
    return None


def _structured_section(structured: StructuredResult | None) -> str:
    if structured is None or not structured.has_data:
        return "\nSTRUCTURED DATA\n(none matched)\n"
    lines = [f"\nSTRUCTURED DATA (exact results from {STRUCTURED_SOURCE}; treat as authoritative figures)"]
    for aggregation in structured.aggregations:
        group = f" {aggregation.group}" if aggregation.group else ""
        lines.append(
            f"- {aggregation.name}{group} = {aggregation.value} ({aggregation.method}; {aggregation.detail})"
        )
    for fact in structured.facts[:20]:
        lines.append(
            f"- price row {fact.price_id}: supplier={fact.supplier_name} product={fact.product_name} "
            f"unit_price={fact.unit_price} {fact.currency} moq={fact.minimum_quantity} "
            f"effective={fact.effective_date} expiry={fact.expiry_date} amendment={fact.amendment_ref} "
            f"source={fact.document_name} p.{fact.page}"
        )
    for contract in structured.contracts:
        lines.append(
            f"- contract {contract['contract_number']} status={contract['status']} version={contract['version']} "
            f"effective={contract['effective_date']} expiry={contract['expiry_date']} supplier={contract['supplier_name']}"
        )
    for certificate in structured.compliance[:12]:
        lines.append(
            f"- compliance {certificate['certificate_type']} supplier={certificate['supplier_name']} "
            f"status={certificate['status']} expiry={certificate['expiry_date']}"
        )
    if structured.notes:
        lines.extend(f"- note: {note}" for note in structured.notes)
    return "\n".join(lines) + "\n"


def _conflict_section(conflicts: list[Conflict]) -> str:
    if not conflicts:
        return "\nCONFLICTS DETECTED\n(none)\n"
    lines = ["\nCONFLICTS DETECTED (report these explicitly)"]
    for conflict in conflicts:
        lines.append(f"- {conflict.description}")
        lines.append(f"  resolution: {conflict.resolution}")
    return "\n".join(lines) + "\n"
