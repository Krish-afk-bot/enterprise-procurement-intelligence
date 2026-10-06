"""Query understanding (PRD s.31).

Produces a typed plan for each question: intent, linked entities, temporal and
comparison requirements, and which engines are needed (vector / BM25 / SQL /
graph / vision).

Two implementations are provided:

* **Rule-based** (always available) — regex extraction plus *real entity linking*
  against the tenant's supplier, product, contract and SKU records.
* **LLM-based** (used when an endpoint is configured) — validated against the
  same schema; on any failure the rule-based result is kept and the degradation
  is recorded.

The visible output is a plan, never hidden reasoning.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Contract, Document, Product, Supplier
from app.observability.logging import get_logger
from app.providers.router import ModelRouter, Task
from app.providers.types import LLMMessage

logger = get_logger(__name__)


class Intent(str, Enum):
    PRICE_LOOKUP = "price_lookup"
    CONTRACT_TERMS = "contract_terms"
    COMPARISON = "comparison"
    TEMPORAL_CHANGE = "temporal_change"
    COMPLIANCE_CHECK = "compliance_check"
    AGGREGATION = "aggregation"
    RELATIONSHIP = "relationship"
    DOCUMENT_LOOKUP = "document_lookup"
    GENERAL = "general"


class LinkedEntity(BaseModel):
    kind: str
    value: str
    matched_id: str | None = None
    matched_name: str | None = None
    method: str = "exact"


class QueryPlan(BaseModel):
    query: str
    intent: Intent = Intent.GENERAL
    entities: list[LinkedEntity] = Field(default_factory=list)
    suppliers: list[str] = Field(default_factory=list)
    supplier_ids: list[str] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)
    product_ids: list[str] = Field(default_factory=list)
    contract_numbers: list[str] = Field(default_factory=list)
    contract_ids: list[str] = Field(default_factory=list)
    skus: list[str] = Field(default_factory=list)
    document_types: list[str] = Field(default_factory=list)
    keyword_terms: list[str] = Field(default_factory=list)
    date_from: date | None = None
    date_to: date | None = None
    year: int | None = None
    requires_comparison: bool = False
    requires_temporal: bool = False
    requires_structured: bool = False
    requires_graph: bool = False
    requires_vision: bool = False
    complexity: str = "low"
    method: str = "rule_based"
    notes: list[str] = Field(default_factory=list)
    sub_queries: list[str] = Field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


COMPARISON_PATTERNS = (
    r"\bcompare\b", r"\bvs\.?\b", r"\bversus\b", r"\bdifference between\b",
    r"\bwhich (?:supplier|vendor) (?:is )?(?:cheaper|cheapest|more expensive)\b",
    r"\bbetter (?:price|deal)\b", r"\bcheaper\b",
)
TEMPORAL_PATTERNS = (
    r"\bcurrent(?:ly)?\b", r"\blatest\b", r"\bmost recent\b", r"\bstill valid\b", r"\bvalid\b",
    r"\bamended\b", r"\bamendment\b", r"\bwhat changed\b", r"\bchanged between\b", r"\bsupersed\w*\b",
    r"\bexpired?\b", r"\bafter the (?:latest )?amendment\b", r"\bnew price\b", r"\bin force\b",
)
AGGREGATION_PATTERNS = (
    r"\btotal\b", r"\bsum\b", r"\bcombined\b", r"\baverage\b", r"\bmean\b", r"\bhow much\b",
    r"\bcount\b", r"\bnumber of\b", r"\blowest\b", r"\bhighest\b", r"\bcheapest\b", r"\bmost expensive\b",
    r"\bspend\b", r"\bspent\b", r"\bvalue of\b", r"\baggregate\b",
)
GRAPH_PATTERNS = (
    r"\bwhich (?:suppliers?|vendors?)\b", r"\brelated\b", r"\bconnected\b", r"\bchain\b",
    r"\bthrough\b.*\bcontract\b", r"\blinked\b", r"\bamendment\b.*\bproduct\b",
    r"\bsuppl\w+ .*\bcompliance\b", r"\bmulti-?hop\b",
)
VISION_PATTERNS = (
    r"\btable\b", r"\bchart\b", r"\bdiagram\b", r"\bsignature\b", r"\bstamp\b", r"\bscanned\b",
    r"\bpage \d+\b", r"\bimage\b", r"\bfigure\b", r"\bvisual\b",
)
COMPLIANCE_PATTERNS = (r"\biso\b", r"\bsoc ?2\b", r"\bcertificat\w+\b", r"\bcomplian\w+\b", r"\baudit\b")
PRICE_PATTERNS = (
    r"\bprice\b", r"\bpricing\b", r"\brate\b", r"\bcost\b", r"\bunit price\b", r"\bhow much\b",
    r"\b(?:moq|minimum order)\b", r"\bdiscount\b", r"\bquote\b",
)
TERMS_PATTERNS = (
    r"\bpayment terms?\b", r"\bdelivery\b", r"\blead time\b", r"\brenewal\b", r"\btermination\b",
    r"\bwarranty\b", r"\bgoverning law\b", r"\bclause\b", r"\bterms\b",
)
DOCUMENT_TYPE_HINTS: tuple[tuple[str, str], ...] = (
    (r"\bamendment\b|\baddendum\b", "amendment"),
    (r"\bcertificat\w*\b|\bcompliance\b", "compliance_certificate"),
    (r"\bpricing (?:schedule|table|list)\b|\brate card\b", "pricing_schedule"),
    (r"\bcontract\b|\bagreement\b", "contract"),
    (r"\binvoice\b", "invoice"),
    (r"\bpurchase order\b|\bpo\b", "purchase_order"),
)

_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_CONTRACT_RE = re.compile(r"\b[A-Z]{2,6}-\d{4}-\d{2,5}(?:-[A-Z0-9]{1,6})?\b")
_SKU_RE = re.compile(r"\b(?:SKU|PART|P/N)[- ]?[A-Z0-9]{2,}[-0-9A-Z]*\b", re.IGNORECASE)
_CLAUSE_RE = re.compile(r"\b(?:clause|section|article)\s+\d+(?:\.\d+)*\b", re.IGNORECASE)
_MONEY_RE = re.compile(r"[$€£]\s?\d[\d,]*(?:\.\d+)?")

_STOPWORDS = {
    "what", "which", "who", "whose", "when", "where", "why", "how", "is", "are", "was", "were",
    "the", "a", "an", "of", "for", "to", "in", "on", "at", "and", "or", "do", "does", "did",
    "we", "our", "us", "it", "its", "this", "that", "these", "those", "any", "all", "with",
    "between", "from", "by", "as", "be", "been", "has", "have", "had", "can", "could", "should",
    "would", "will", "please", "show", "me", "give", "tell", "about", "there",
}


def _matches_any(query: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, query, re.IGNORECASE) for pattern in patterns)


def keyword_terms(query: str, limit: int = 24) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", query)
    return [token for token in tokens if token.lower() not in _STOPWORDS][:limit]


@dataclass(slots=True)
class TenantVocabulary:
    """Real entity inventory used to link query mentions to database rows."""

    suppliers: list[tuple[str, str]] = field(default_factory=list)  # (id, name)
    products: list[tuple[str, str, str]] = field(default_factory=list)  # (id, name, sku)
    contracts: list[tuple[str, str]] = field(default_factory=list)  # (id, number)
    regions: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    #: alias/initials label → (supplier_id, supplier_name). Populated from data the
    #: platform actually holds (supplier attributes plus dataset labels), never
    #: guessed: 'Supplier A' resolves only because the corpus labels it so.
    supplier_aliases: dict[str, tuple[str, str]] = field(default_factory=dict)


async def load_vocabulary(session: AsyncSession, tenant_id: str, *, limit: int = 400) -> TenantVocabulary:
    vocabulary = TenantVocabulary()
    supplier_rows = (
        await session.execute(
            select(Supplier.id, Supplier.name, Supplier.attributes).where(Supplier.tenant_id == tenant_id).limit(limit)
        )
    ).all()
    vocabulary.suppliers = [(row[0], row[1]) for row in supplier_rows]
    for supplier_id, supplier_name, attributes in supplier_rows:
        for alias in (attributes or {}).get("aliases", []) or []:
            vocabulary.supplier_aliases[str(alias).strip().lower()] = (supplier_id, supplier_name)
        initial = _initials(supplier_name)
        if initial and initial not in vocabulary.supplier_aliases:
            vocabulary.supplier_aliases[initial] = (supplier_id, supplier_name)
    vocabulary.products = [
        (row[0], row[1], row[2] or "")
        for row in (
            await session.execute(
                select(Product.id, Product.name, Product.sku).where(Product.tenant_id == tenant_id).limit(limit)
            )
        ).all()
    ]
    vocabulary.contracts = [
        (row[0], row[1])
        for row in (
            await session.execute(
                select(Contract.id, Contract.contract_number)
                .where(Contract.tenant_id == tenant_id)
                .limit(limit)
            )
        ).all()
    ]
    vocabulary.regions = [
        row[0]
        for row in (
            await session.execute(
                select(func.distinct(Supplier.region)).where(
                    Supplier.tenant_id == tenant_id, Supplier.region.is_not(None)
                )
            )
        ).all()
        if row[0]
    ]
    vocabulary.categories = [
        row[0]
        for row in (
            await session.execute(
                select(func.distinct(Supplier.category)).where(
                    Supplier.tenant_id == tenant_id, Supplier.category.is_not(None)
                )
            )
        ).all()
        if row[0]
    ]
    return vocabulary


def understand_query_rule_based(
    query: str, vocabulary: TenantVocabulary | None = None, *, max_sub_queries: int = 4
) -> QueryPlan:
    text = query.strip()
    lowered = text.lower()
    plan = QueryPlan(query=text, method="rule_based")
    vocabulary = vocabulary or TenantVocabulary()

    # ---------------------------------------------------------- entity linking
    for supplier_id, supplier_name in vocabulary.suppliers:
        if _name_mentioned(text, supplier_name):
            plan.supplier_ids.append(supplier_id)
            plan.suppliers.append(supplier_name)
            plan.entities.append(
                LinkedEntity(kind="supplier", value=supplier_name, matched_id=supplier_id, matched_name=supplier_name)
            )

    # "supplier A" / "supplier northwind" style references use recorded aliases.
    for match in re.finditer(r"\bsuppliers?\s+([a-z0-9][a-z0-9\- '.&]{0,40}?)(?:'s|s'|\b)", lowered):
        label = match.group(1).strip(" .'")
        for candidate in (label, label.split()[0] if label else ""):
            if not candidate:
                continue
            hit = vocabulary.supplier_aliases.get(candidate)
            if hit is None:
                continue
            supplier_id, supplier_name = hit
            if supplier_id in plan.supplier_ids:
                continue
            plan.supplier_ids.append(supplier_id)
            plan.suppliers.append(supplier_name)
            plan.entities.append(
                LinkedEntity(
                    kind="supplier",
                    value=f"supplier {candidate}",
                    matched_id=supplier_id,
                    matched_name=supplier_name,
                    method="alias",
                )
            )
            break

    for product_id, product_name, sku in vocabulary.products:
        if _name_mentioned(text, product_name) or (sku and sku.lower() in lowered):
            plan.product_ids.append(product_id)
            plan.products.append(product_name)
            plan.entities.append(
                LinkedEntity(kind="product", value=product_name, matched_id=product_id, matched_name=product_name)
            )

    for contract_id, contract_number in vocabulary.contracts:
        if contract_number.lower() in lowered:
            plan.contract_ids.append(contract_id)
            plan.contract_numbers.append(contract_number)
            plan.entities.append(
                LinkedEntity(kind="contract", value=contract_number, matched_id=contract_id, matched_name=contract_number)
            )

    # ----------------------------------------------------- literal identifiers
    for match in _CONTRACT_RE.findall(text):
        if match.upper() not in {number.upper() for number in plan.contract_numbers}:
            plan.contract_numbers.append(match.upper())
    plan.skus.extend({match.upper() for match in _SKU_RE.findall(text)})
    clause_refs = _CLAUSE_RE.findall(text)
    plan.keyword_terms = keyword_terms(text)
    plan.keyword_terms.extend(ref.lower() for ref in clause_refs)
    plan.keyword_terms.extend(match for match in _MONEY_RE.findall(text))

    # ------------------------------------------------------------- date ranges
    iso_dates = [date.fromisoformat(value) for value in _DATE_RE.findall(text)]
    years = [int(value) for value in _YEAR_RE.findall(text)]
    if iso_dates:
        plan.date_from = min(iso_dates)
        plan.date_to = max(iso_dates)
    if years:
        year = max(years)
        plan.year = year
        if not iso_dates:
            plan.date_from = date(year, 1, 1)
            plan.date_to = date(year, 12, 31)

    # ----------------------------------------------------------- intent rules
    requires_comparison = _matches_any(lowered, COMPARISON_PATTERNS) or len(plan.suppliers) >= 2
    requires_temporal = _matches_any(lowered, TEMPORAL_PATTERNS)
    requires_aggregation = _matches_any(lowered, AGGREGATION_PATTERNS)
    requires_compliance = _matches_any(lowered, COMPLIANCE_PATTERNS)
    requires_graph = _matches_any(lowered, GRAPH_PATTERNS)
    requires_vision = _matches_any(lowered, VISION_PATTERNS)
    is_price = _matches_any(lowered, PRICE_PATTERNS)
    is_terms = _matches_any(lowered, TERMS_PATTERNS)

    if requires_comparison:
        plan.intent = Intent.COMPARISON
    elif requires_aggregation:
        plan.intent = Intent.AGGREGATION
    elif requires_temporal and is_price:
        plan.intent = Intent.TEMPORAL_CHANGE
    elif is_price:
        plan.intent = Intent.PRICE_LOOKUP
    elif requires_compliance:
        plan.intent = Intent.COMPLIANCE_CHECK
    elif is_terms:
        plan.intent = Intent.CONTRACT_TERMS
    elif requires_graph:
        plan.intent = Intent.RELATIONSHIP
    elif re.search(r"\b(document|file|pdf|upload)\b", lowered):
        plan.intent = Intent.DOCUMENT_LOOKUP

    for pattern, document_type in DOCUMENT_TYPE_HINTS:
        if re.search(pattern, lowered):
            plan.document_types.append(document_type)

    # ------------------------------------------------- engine requirements
    plan.requires_comparison = requires_comparison
    plan.requires_temporal = requires_temporal
    # Price/date questions are answered from the structured rows (exact SQL), not
    # by asking a model to read numbers out of prose.
    plan.requires_structured = (
        requires_aggregation
        or bool(plan.year)
        or requires_comparison
        or (requires_temporal and (is_price or is_terms))
        # A temporal question about contract documents ("what changed between the
        # original contract and Amendment 2") is answered from the versioned
        # structured rows, not by comparing prose.
        or (requires_temporal and bool(plan.document_types))
    )
    plan.requires_graph = requires_graph or (requires_compliance and bool(plan.suppliers)) or len(plan.suppliers) >= 2
    plan.requires_vision = requires_vision
    plan.complexity = _complexity(plan)

    # ------------------------------------------------------- decomposition
    plan.sub_queries = _decompose(text, plan, max_sub_queries=max_sub_queries)

    if not plan.suppliers and not plan.products:
        plan.notes.append(
            "No supplier or product record matched the question text; retrieval relies on document text only."
        )
    return plan


def _complexity(plan: QueryPlan) -> str:
    signals = sum(
        [
            plan.requires_comparison,
            plan.requires_temporal,
            plan.requires_structured,
            plan.requires_graph,
            len(plan.suppliers) > 1,
            len(plan.products) > 0 and plan.requires_structured,
        ]
    )
    if signals >= 3:
        return "high"
    if signals >= 1:
        return "medium"
    return "low"


def _decompose(query: str, plan: QueryPlan, *, max_sub_queries: int) -> list[str]:
    """Split a multi-part question into focused sub-questions (rule-based)."""
    parts: list[str] = []
    if plan.requires_comparison and len(plan.suppliers) >= 2 and plan.products:
        product = plan.products[0]
        for supplier in plan.suppliers:
            parts.append(f"{supplier} price for {product}")
    if plan.requires_temporal and plan.contract_numbers:
        number = plan.contract_numbers[0]
        parts.extend(
            [
                f"{number} original price and terms",
                f"{number} amendments and changed prices",
            ]
        )
    if not parts:
        parts.append(query)
    seen: list[str] = []
    for part in parts:
        if part.lower() not in {item.lower() for item in seen}:
            seen.append(part)
    return seen[:max_sub_queries]


def _name_mentioned(text: str, name: str) -> bool:
    """Match a stored entity name against freely written question text."""
    if not name:
        return False
    lowered = text.lower()
    candidate = name.lower().strip()
    if candidate in lowered:
        return True
    tokens = [token for token in re.findall(r"[a-z0-9]+", candidate) if len(token) > 2]
    if not tokens:
        return False
    distinctive = [token for token in tokens if token not in {"inc", "ltd", "llc", "co", "corp", "group", "limited", "supplies", "supply", "industrial", "partners"}]
    if not distinctive:
        distinctive = tokens[:1]
    hits = sum(1 for token in distinctive if token in lowered)
    if len(distinctive) == 1:
        return hits == 1 and len(distinctive[0]) >= 5
    return hits >= max(1, len(distinctive) - 1)


def _initials(name: str) -> str | None:
    """Initials of a supplier name, e.g. 'Northwind Industrial Supplies' → 'N'.

    Used only as a fallback alias when the data itself records no label.
    """
    cleaned = (name or "").strip()
    if not cleaned:
        return None
    return cleaned[0].upper()


UNDERSTANDING_SCHEMA_HINT = (
    "Classify the procurement question. Respond with JSON: intent (one of price_lookup, "
    "contract_terms, comparison, temporal_change, compliance_check, aggregation, relationship, "
    "document_lookup, general), suppliers (names), products (names), contract_numbers, keywords, "
    "requires_comparison, requires_temporal, requires_structured, requires_graph, requires_vision, "
    "complexity (low|medium|high)."
)


class LLMUnderstanding(BaseModel):
    intent: str = "general"
    suppliers: list[str] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)
    contract_numbers: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    requires_comparison: bool = False
    requires_temporal: bool = False
    requires_structured: bool = False
    requires_graph: bool = False
    requires_vision: bool = False
    complexity: str = "low"


async def understand_query(
    query: str,
    *,
    session: AsyncSession | None = None,
    tenant_id: str | None = None,
    router: ModelRouter | None = None,
    use_llm: bool = True,
) -> QueryPlan:
    """Understand a query, preferring the LLM when it is configured."""
    vocabulary = None
    if session is not None and tenant_id:
        try:
            vocabulary = await load_vocabulary(session, tenant_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("vocabulary_load_failed", error=str(exc))
    plan = understand_query_rule_based(query, vocabulary)

    if not use_llm or router is None:
        return plan
    try:
        result = await router.generate_structured(
            [
                LLMMessage(role="system", content=UNDERSTANDING_SCHEMA_HINT),
                LLMMessage(role="user", content=query),
            ],
            LLMUnderstanding,
            task=Task.CLASSIFY,
        )
    except Exception as exc:  # noqa: BLE001 - degrade to the rule-based plan
        logger.info("llm_understanding_unavailable", error=str(exc))
        plan.notes.append("LLM query understanding unavailable; rule-based understanding used.")
        return plan

    if result is None:
        plan.notes.append("LLM understanding returned no valid structure; rule-based understanding used.")
        return plan

    try:
        intent = Intent(result.intent)
    except ValueError:
        intent = plan.intent
    plan.intent = intent
    plan.requires_comparison = plan.requires_comparison or result.requires_comparison
    plan.requires_temporal = plan.requires_temporal or result.requires_temporal
    plan.requires_structured = plan.requires_structured or result.requires_structured
    plan.requires_graph = plan.requires_graph or result.requires_graph
    plan.requires_vision = plan.requires_vision or result.requires_vision
    plan.complexity = result.complexity if result.complexity in {"low", "medium", "high"} else plan.complexity
    for name in result.suppliers:
        if name not in plan.suppliers:
            plan.suppliers.append(name)
    for name in result.products:
        if name not in plan.products:
            plan.products.append(name)
    for number in result.contract_numbers:
        if number not in plan.contract_numbers:
            plan.contract_numbers.append(number)
    for keyword in result.keywords:
        if keyword and keyword.lower() not in {term.lower() for term in plan.keyword_terms}:
            plan.keyword_terms.append(keyword)
    plan.keyword_terms = plan.keyword_terms[:30]
    plan.method = "llm+rule_based"
    return plan


async def document_type_inventory(session: AsyncSession, tenant_id: str) -> list[str]:
    rows = await session.execute(
        select(Document.document_type).where(Document.tenant_id == tenant_id).distinct()
    )
    return [str(row[0]) for row in rows.all() if row[0]]
