"""Self-reflective verification (PRD s.40-43, s.74).

After generation the answer is checked before it is shown:

1. **Claim extraction** — factual sentences are isolated.
2. **Grounding judge** — each claim is checked against the evidence. The default
   judge is deterministic lexical entailment: content tokens must be supported by
   the evidence and *every number in a claim must appear in the evidence*. When a
   model is configured it can be used as the judge instead, and the method is
   reported either way.
3. **Citation validation** — only citations that map to actually retrieved
   evidence survive; fabricated references are dropped and recorded.
4. **Evidence strength** — computed from explicit criteria (independent document
   count, structured corroboration, retrieval scores, in-force status), never an
   invented percentage.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.observability.logging import get_logger
from app.retrieval.context import CitationDraft, ContextBundle
from app.retrieval.structured import StructuredResult

logger = get_logger(__name__)

NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]{2,}")
STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "are", "was", "were", "has", "have", "had", "not",
    "but", "from", "into", "under", "over", "each", "per", "any", "all", "which", "while", "there",
    "their", "than", "then", "when", "where", "according", "system", "evidence", "available",
    "summary", "extractive", "configured", "platform", "documents",
}

REFUSAL_TEXT = "I couldn't verify this from the available procurement documents."


@dataclass(slots=True)
class ClaimCheck:
    claim: str
    supported: bool
    support_score: float
    missing_numbers: list[str] = field(default_factory=list)
    evidence_refs: list[int] = field(default_factory=list)
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim,
            "supported": self.supported,
            "support_score": round(self.support_score, 3),
            "missing_numbers": self.missing_numbers,
            "evidence_refs": self.evidence_refs,
            "reason": self.reason,
        }


@dataclass(slots=True)
class GroundingResult:
    method: str = "lexical_overlap"
    claims: list[ClaimCheck] = field(default_factory=list)
    score: float | None = None
    supported: int = 0
    total: int = 0
    unsupported: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def all_supported(self) -> bool:
        return self.total > 0 and self.supported == self.total

    def as_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "score": self.score,
            "supported_claims": self.supported,
            "total_claims": self.total,
            "unsupported_claims": self.unsupported,
            "details": self.details,
        }


@dataclass(slots=True)
class EvidenceStrength:
    level: str = "none"
    method: str = "criteria_v1"
    criteria: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"level": self.level, "method": self.method, "criteria": self.criteria}


@dataclass(slots=True)
class CoverageResult:
    """Whether the evidence actually covers the entities and period asked about.

    Retrieval always returns *something*; a question can therefore look answered
    while nothing in the evidence is about the named supplier or the named year.
    This check records, per constraint the question imposed, whether any piece of
    evidence satisfies it. It is what makes "Supplier C's price in 2030" a
    refusal instead of a stale figure from a different period.
    """

    constraints: list[dict[str, Any]] = field(default_factory=list)
    method: str = "constraint_coverage_v1"

    @property
    def unsatisfied(self) -> list[dict[str, Any]]:
        return [item for item in self.constraints if not item.get("satisfied")]

    @property
    def satisfied(self) -> bool:
        return not self.unsatisfied

    def as_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "satisfied": self.satisfied,
            "constraints": self.constraints,
            "unsatisfied": [item["constraint"] for item in self.unsatisfied],
        }


def _mentions(text: str, needle: str) -> bool:
    if not needle:
        return False
    return needle.lower() in text.lower()


def assess_query_coverage(
    plan: dict[str, Any] | None,
    bundle: ContextBundle,
    structured: StructuredResult | None,
) -> CoverageResult:
    """Check the evidence against the constraints the question itself imposed."""
    plan = plan or {}
    result = CoverageResult()
    structured = structured if structured is not None else StructuredResult(queried=False)
    texts = [(block.text or "") + " " + (block.citation.snippet or "") for block in bundle.blocks]
    blob = "\n".join(texts)
    price_intent = plan.get("intent") in {
        "price_lookup",
        "aggregation",
        "comparison",
        "temporal_change",
    }

    # ---------------------------------------------------------- supplier constraint
    ids = list(plan.get("supplier_ids") or [])
    names = list(plan.get("suppliers") or [])
    for index, name in enumerate(names):
        supplier_id = ids[index] if index < len(ids) else None
        fact_hits = [fact for fact in structured.facts if supplier_id and fact.supplier_id == supplier_id]
        certificate_hits = [item for item in structured.compliance if supplier_id and item.get("supplier_id") == supplier_id]
        text_hits = sum(1 for text in texts if _mentions(text, name))
        if fact_hits:
            satisfied, detail = True, f"{len(fact_hits)} structured price row(s) for {name}"
        elif certificate_hits:
            satisfied, detail = True, f"{len(certificate_hits)} compliance record(s) for {name}"
        elif text_hits:
            satisfied, detail = True, f"{text_hits} retrieved passage(s) name {name}"
        elif structured.suppliers and not price_intent:
            satisfied, detail = True, f"a supplier record exists for {name}"
        else:
            satisfied, detail = False, f"no retrieved price row or passage is about {name}"
        result.constraints.append(
            {"kind": "supplier", "constraint": f"supplier={name}", "satisfied": satisfied, "detail": detail}
        )

    # ----------------------------------------------------------- product constraint
    product_ids = list(plan.get("product_ids") or [])
    for index, name in enumerate(plan.get("products") or []):
        product_id = product_ids[index] if index < len(product_ids) else None
        fact_hits = [fact for fact in structured.facts if product_id and fact.product_id == product_id]
        text_hits = sum(1 for text in texts if _mentions(text, name))
        if fact_hits:
            satisfied, detail = True, f"{len(fact_hits)} structured price row(s) for {name}"
        elif text_hits:
            satisfied, detail = True, f"{text_hits} retrieved passage(s) mention {name}"
        else:
            satisfied, detail = False, f"no retrieved row or passage is about {name}"
        result.constraints.append(
            {"kind": "product", "constraint": f"product={name}", "satisfied": satisfied, "detail": detail}
        )

    # ------------------------------------------------------------ period constraint
    date_from, date_to = plan.get("date_from"), plan.get("date_to")
    if date_from or date_to:
        scope_rows = [
            fact
            for fact in structured.facts
            if _within(fact.effective_date, fact.expiry_date, date_from, date_to)
        ]
        year_rows = [
            aggregation
            for aggregation in structured.aggregations
            if aggregation.row_count and (aggregation.group or {}).get("year") in _period_years(date_from, date_to)
        ]
        corpus_years: set[str] = set()
        for text in texts:
            corpus_years.update(re.findall(r"\b(?:19|20)\d{2}\b", text))
        wanted_years = _period_years(date_from, date_to)
        text_year_hits = sorted(year for year in wanted_years if year in corpus_years)
        label = _period_label(date_from, date_to)
        if scope_rows:
            satisfied, detail = True, f"{len(scope_rows)} price row(s) valid in {label}"
        elif year_rows:
            satisfied, detail = True, f"{len(year_rows)} aggregation(s) computed for {label}"
        elif text_year_hits:
            satisfied, detail = True, f"retrieved passages reference {', '.join(text_year_hits)}"
        else:
            satisfied, detail = False, f"no retrieved row or passage falls in {label}"
        result.constraints.append(
            {"kind": "period", "constraint": f"period={label}", "satisfied": satisfied, "detail": detail}
        )

    return result


def _period_years(date_from: Any, date_to: Any) -> set[str]:
    years: set[str] = set()
    for value in (date_from, date_to):
        text = str(value or "")
        if len(text) >= 4 and text[:4].isdigit():
            years.add(text[:4])
    return years


def _period_label(date_from: Any, date_to: Any) -> str:
    if date_from and date_from == date_to:
        return str(date_from)
    return f"{date_from or '…'} to {date_to or '…'}"


def _within(effective: Any, expiry: Any, date_from: Any, date_to: Any) -> bool:
    """Whether [effective, expiry] intersects [date_from, date_to] (ISO strings)."""
    if date_from is not None and expiry is not None and str(expiry) < str(date_from):
        return False
    if date_to is not None and effective is not None and str(effective) > str(date_to):
        return False
    return True


def relevant_conflicts(conflicts: list[Any], plan: dict[str, Any] | None) -> list[Any]:
    """Keep only conflicts that concern an entity the question asked about.

    A genuine price disagreement between two suppliers the question never
    mentions is real data, but it is not an answer to this question and must not
    turn the answer into a conflict report.
    """
    plan = plan or {}
    supplier_ids = {value for value in (plan.get("supplier_ids") or []) if value}
    product_ids = {value for value in (plan.get("product_ids") or []) if value}
    if not supplier_ids and not product_ids:
        return list(conflicts)
    relevant: list[Any] = []
    for conflict in conflicts:
        values = conflict.get("values") if isinstance(conflict, dict) else getattr(conflict, "values", [])
        for value in values or []:
            if value.get("supplier_id") in supplier_ids or value.get("product_id") in product_ids:
                relevant.append(conflict)
                break
    return relevant


@dataclass(slots=True)
class CitationCheck:
    valid: list[CitationDraft] = field(default_factory=list)
    invalid: list[CitationDraft] = field(default_factory=list)
    referenced_markers: list[int] = field(default_factory=list)
    unused_markers: list[int] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid_citations": len(self.valid),
            "invalid_citations": len(self.invalid),
            "referenced_markers": self.referenced_markers,
            "unused_markers": self.unused_markers,
        }


BOILERPLATE_MARKERS = (
    "answer",
    "evidence",
    "verification",
    "extractive summary",
    "structured findings",
    "document evidence",
    "the evidence below is what the system found",
    "no document-level evidence was retrieved",
    "no evidence retrieved",
    "evidence strength:",
    "i couldn't verify this from the available procurement documents",
    "why:",
    "retrieval summary:",
    "note:",
    "resolution:",
)


def extract_claims(answer_text: str, *, max_claims: int = 12) -> list[str]:
    """Isolate factual sentences (numbers, money, dates or entity-ish nouns).

    Platform boilerplate (headings, the extractive-mode notice, the evidence
    list and the verification line) is skipped: it is not a factual claim about
    the domain and must not be judged as one.
    """
    lines: list[str] = []
    for raw in answer_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        stripped_bullet = line.lstrip("•- []0123456789").strip()
        lowered = stripped_bullet.lower()
        if lowered.startswith(BOILERPLATE_MARKERS):
            continue
        if "no language model is configured" in lowered:
            continue
        lines.append(line)
    claims: list[str] = []
    for line in lines:
        for sentence in re.split(r"(?<=[.!?])\s+", line):
            sentence = sentence.strip(" •-")
            if len(sentence) < 25:
                continue
            if NUMBER_RE.search(sentence) or len(_content_tokens(sentence)) >= 6:
                claims.append(sentence)
        if len(claims) >= max_claims:
            break
    return claims[:max_claims]


def _content_tokens(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text) if token.lower() not in STOPWORDS]


def _normalise_number(raw: str) -> str:
    """Normalise numeric literals so '874.00' and '874' compare equal."""
    cleaned = raw.replace(",", "").strip()
    try:
        value = float(cleaned)
    except ValueError:
        return cleaned
    if value.is_integer():
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def judge_grounding_lexical(claims: list[str], evidence_texts: list[str]) -> GroundingResult:
    """Deterministic entailment check: token support plus number containment."""
    evidence_blob = "\n".join(evidence_texts)
    evidence_tokens = set(_content_tokens(evidence_blob))
    evidence_numbers = {_normalise_number(value) for value in NUMBER_RE.findall(evidence_blob)}

    checks: list[ClaimCheck] = []
    for claim in claims:
        tokens = _content_tokens(claim)
        numbers = [_normalise_number(value) for value in NUMBER_RE.findall(claim)]
        if not tokens:
            continue
        supported_tokens = [token for token in tokens if token in evidence_tokens]
        token_ratio = len(supported_tokens) / len(tokens)
        missing_numbers = [value for value in numbers if value not in evidence_numbers]
        supported = token_ratio >= 0.6 and not missing_numbers
        reason = "supported by evidence text"
        if missing_numbers:
            reason = f"numbers not found in evidence: {', '.join(missing_numbers[:4])}"
        elif token_ratio < 0.6:
            reason = f"only {token_ratio:.0%} of content terms appear in the evidence"
        checks.append(
            ClaimCheck(
                claim=claim,
                supported=supported,
                support_score=token_ratio,
                missing_numbers=missing_numbers,
                reason=reason,
            )
        )
    supported = sum(1 for check in checks if check.supported)
    score = (supported / len(checks)) if checks else None
    return GroundingResult(
        method="lexical_overlap",
        claims=checks,
        score=score,
        supported=supported,
        total=len(checks),
        unsupported=[check.claim for check in checks if not check.supported],
        details={
            "criteria": "content-term overlap >= 60% and every numeric value present in the evidence",
            "missing_numbers": sorted({value for check in checks for value in check.missing_numbers}),
        },
    )


async def judge_grounding_llm(
    claims: list[str], evidence_texts: list[str], router: Any
) -> GroundingResult | None:
    """Optional model-based judge. Returns None when unavailable."""
    from pydantic import BaseModel, Field

    from app.providers.router import Task
    from app.providers.types import LLMMessage

    class Judgement(BaseModel):
        supported: list[int] = Field(default_factory=list)
        unsupported: list[int] = Field(default_factory=list)
        reason: str = ""

    numbered = "\n".join(f"[{index}] {claim}" for index, claim in enumerate(claims))
    evidence = "\n---\n".join(evidence_texts)[:12000]
    try:
        result = await router.generate_structured(
            [
                LLMMessage(
                    role="system",
                    content=(
                        "You verify claims against evidence. For each numbered claim decide whether the "
                        "evidence directly supports it. A number that does not appear in the evidence is "
                        "not supported. Return JSON with supported claim indices and unsupported indices."
                    ),
                ),
                LLMMessage(role="user", content=f"EVIDENCE:\n{evidence}\n\nCLAIMS:\n{numbered}"),
            ],
            Judgement,
            task=Task.VERIFY,
        )
    except Exception as exc:  # noqa: BLE001
        logger.info("llm_grounding_unavailable", error=str(exc))
        return None
    if result is None:
        return None
    supported_indices = set(result.supported)
    checks = [
        ClaimCheck(
            claim=claim,
            supported=index in supported_indices,
            support_score=1.0 if index in supported_indices else 0.0,
            reason="model judgement",
        )
        for index, claim in enumerate(claims)
    ]
    supported_count = sum(1 for check in checks if check.supported)
    return GroundingResult(
        method="llm_judge",
        claims=checks,
        score=(supported_count / len(checks)) if checks else None,
        supported=supported_count,
        total=len(checks),
        unsupported=[check.claim for check in checks if not check.supported],
        details={"model_reason": result.reason},
    )


def validate_citations(answer_text: str, bundle: ContextBundle) -> CitationCheck:
    """Keep only citations backed by retrieved evidence; record broken references.

    A marker in the answer that does not correspond to a retrieved evidence block
    is a fabrication and is recorded in ``details`` rather than displayed.
    """
    markers = {int(value) for value in re.findall(r"\[(\d{1,2})\]", answer_text)}
    available = {index: citation for index, citation in enumerate(bundle.citations, start=1)}
    valid: list[CitationDraft] = []
    invalid: list[CitationDraft] = []
    referenced: list[int] = []
    for marker, citation in available.items():
        if marker not in markers:
            continue
        referenced.append(marker)
        if citation.chunk_id or citation.document_id:
            valid.append(citation)
        else:  # pragma: no cover - defensive: a citation with no source is not displayable
            invalid.append(citation)
    return CitationCheck(
        valid=valid,
        invalid=invalid,
        referenced_markers=sorted(referenced),
        unused_markers=sorted(marker for marker in available if marker not in markers)[:20],
    )


def assess_evidence_strength(
    bundle: ContextBundle,
    structured: StructuredResult | None,
    *,
    conflicts: list[Any] | None = None,
    groundings: GroundingResult | None = None,
) -> EvidenceStrength:
    """Explicit, auditable criteria — no invented percentage."""
    documents = {citation.document_id for citation in bundle.citations if citation.document_id}
    structured_rows = len(structured.facts) if structured else 0
    corroborated = structured_rows > 0 and len(documents) >= 1
    best_score = max(
        (citation.score or 0.0 for citation in bundle.citations),
        default=0.0,
    )
    today = date.today()
    in_force = any(
        (citation.metadata.get("expiry_date") is None)
        or (str(citation.metadata.get("expiry_date")) >= today.isoformat())
        for citation in bundle.citations
    )

    criteria = {
        "independent_documents": len(documents),
        "evidence_blocks": len(bundle.blocks),
        "structured_rows": structured_rows,
        "structured_corroboration": corroborated,
        "best_retrieval_score": round(best_score, 4),
        "evidence_in_force": in_force,
        "conflicts_detected": len(conflicts or []),
        "grounding_score": groundings.score if groundings else None,
    }

    # "Evidence strength" describes the retrieved evidence itself, so it is
    # deliberately independent of the answer: whether the written answer is
    # supported is reported separately as groundedness (grounding_score).
    # Criteria: whether structured rows are corroborated by more than one
    # document, how many independent documents carry the evidence, and whether
    # that evidence is still in force today.
    if not documents and structured_rows == 0:
        level = "none"
    elif corroborated and len(documents) >= 2:
        level = "strong"
    elif len(documents) >= 3 and in_force:
        level = "strong"
    elif len(documents) >= 1 and (structured_rows > 0 or in_force):
        level = "moderate"
    else:
        level = "limited"
    if conflicts and level == "strong":
        criteria["note"] = "Conflicting sources detected; the conflict is reported explicitly."
    return EvidenceStrength(level=level, criteria=criteria)


def decide_status(
    *,
    grounding: GroundingResult | None,
    conflicts: list[Any],
    bundle: ContextBundle,
    structured: StructuredResult | None,
    generation_mode: str = "llm",
    coverage: CoverageResult | None = None,
) -> str:
    """Decide the answer status.

    A refusal is produced when there is nothing to cite *for what was asked*.
    ``conflicts`` must already be limited to the entities in the question (see
    ``relevant_conflicts``), and ``coverage`` carries whether the evidence
    satisfies the named supplier/product/period — an unrelated price dispute
    elsewhere in the corpus never turns this answer into a conflict report.

    In extractive mode the text is assembled *from* the evidence, so an
    individual failed claim check downgrades the status to ``partial`` and is
    listed in the verification block — the answer is not discarded.
    """
    has_evidence = bool(bundle.blocks) or bool(structured and (structured.facts or structured.aggregations))
    if not has_evidence:
        return "insufficient_evidence"
    # The evidence must cover the question's own constraints before it can be
    # reported as an answer. Uncovered constraints mean the question is
    # unanswerable from this corpus, whatever else was retrieved.
    if coverage is not None and not coverage.satisfied and not conflicts:
        return "insufficient_evidence"
    if conflicts:
        return "conflicting"
    if coverage is not None and not coverage.satisfied:
        return "partial"
    if grounding is None or grounding.total == 0:
        return "partial"
    if grounding.all_supported:
        return "supported"
    if grounding.supported == 0:
        return "partial" if generation_mode == "extractive" else "insufficient_evidence"
    return "partial"


def refusal_reason(
    bundle: ContextBundle,
    structured: StructuredResult | None,
    coverage: CoverageResult | None = None,
) -> str:
    if coverage is not None and coverage.unsatisfied:
        gaps = "; ".join(f"{item['constraint']} — {item['detail']}" for item in coverage.unsatisfied)
        return (
            "The corpus holds no evidence for the entities or period asked about "
            f"({gaps}). Nothing is asserted because there is nothing to cite."
        )
    if not bundle.blocks and not (structured and structured.has_data):
        return (
            "No indexed evidence matched the question. Nothing is asserted because there is nothing to cite."
        )
    return "The evidence retrieved did not directly support the generated statements."
