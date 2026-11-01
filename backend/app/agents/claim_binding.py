"""Bind each factual claim to the passage that actually supports it.

The old grounding check compared a claim against the *concatenation* of every
evidence block. That proves a number exists somewhere in the context, not that
the number belongs to the supplier, product and period the claim attaches it to.
A generated sentence such as "Northwind's laptop price is 895.00" therefore
passed whenever some other supplier's 895.00 appeared in the context.

This module keeps the deterministic lexical judge as a cheap pre-filter and adds
an entailment-style binding step:

* a claim is split into independent clauses (``while``/``whereas``/``and``);
* each clause's numeric literals must appear in **one** passage;
* every entity the clause names (supplier, product) must be the entity of that
  same passage;
* every date/period token the clause names must appear in that passage too.

When a clause carries no numbers there is nothing to bind, so the lexical
overlap result decides it. The output is per claim so the interface and the
evaluation can show exactly which sentence failed and why.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]{1,}")

# Words that appear in many entity names and therefore do not identify one.
_GENERIC_ENTITY_TOKENS = {
    "supplier",
    "suppliers",
    "industrial",
    "industries",
    "supplies",
    "supply",
    "ltd",
    "limited",
    "inc",
    "incorporated",
    "co",
    "company",
    "corp",
    "corporation",
    "technology",
    "technologies",
    "partners",
    "partner",
    "enterprise",
    "enterprises",
    "components",
    "solutions",
    "group",
    "holdings",
    "international",
    "the",
    "and",
    "for",
    "with",
    "services",
}

_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "are",
    "was",
    "were",
    "has",
    "have",
    "had",
    "not",
    "but",
    "from",
    "into",
    "under",
    "over",
    "each",
    "per",
    "any",
    "all",
    "which",
    "while",
    "there",
    "their",
    "than",
    "then",
    "when",
    "where",
    "according",
    "evidence",
    "documents",
    "document",
    "source",
    "page",
    "section",
    "clause",
    "shows",
    "states",
    "offers",
    "offered",
    "recorded",
    "stated",
    "listed",
    "total",
    "unit",
    "price",
    "prices",
    "value",
    "values",
}

_CLAUSE_SPLIT_RE = re.compile(r"\s*(?:;|\bwhile\b|\bwhereas\b|\band\b)\s*", re.IGNORECASE)


@dataclass(slots=True)
class EvidencePassage:
    """One independently citable piece of evidence."""

    ref: int
    text: str
    document_name: str = ""
    page: int | None = None
    supplier: str | None = None
    product: str | None = None
    effective_date: str | None = None
    expiry_date: str | None = None
    kind: str = "document"


@dataclass(slots=True)
class BindingCheck:
    claim: str
    supported: bool
    support_score: float
    evidence_refs: list[int] = field(default_factory=list)
    missing_numbers: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    reason: str = ""


def normalise_number(raw: str) -> str:
    cleaned = raw.replace(",", "").strip()
    try:
        value = float(cleaned)
    except ValueError:
        return cleaned
    if value.is_integer():
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _numbers(text: str) -> set[str]:
    return {normalise_number(value) for value in NUMBER_RE.findall(text)}


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text) if token.lower() not in _STOPWORDS]


def _entity_tokens(name: str) -> set[str]:
    """Distinctive tokens that identify a supplier/product name."""
    tokens = {token.lower() for token in _TOKEN_RE.findall(name)}
    distinctive = {token for token in tokens if token not in _GENERIC_ENTITY_TOKENS and len(token) > 2}
    # If a name is literally "Supplier A"/"Vendor 1", the only usable marker is
    # the letter/number, which is already covered by numeric/entity checks.
    return distinctive


class EntityIndex:
    """Maps the canonical entities in scope to the tokens that identify them."""

    def __init__(self, names: Iterable[str]) -> None:
        self._tokens: dict[str, set[str]] = {}
        for name in names:
            if not name:
                continue
            key = " ".join(str(name).lower().split())
            tokens = _entity_tokens(str(name))
            if tokens:
                self._tokens[key] = tokens

    def mentioned(self, text: str) -> list[str]:
        lowered = text.lower()
        found: list[str] = []
        for name, tokens in self._tokens.items():
            if any(re.search(rf"\b{re.escape(token)}\b", lowered) for token in tokens):
                found.append(name)
        return found

    def tokens_for(self, names: Iterable[str]) -> set[str]:
        wanted: set[str] = set()
        for name in names:
            wanted.update(self._tokens.get(name, set()))
        return wanted

    def __bool__(self) -> bool:  # pragma: no cover - trivial
        return bool(self._tokens)


def _split_clauses(claim: str) -> list[str]:
    parts = [part.strip(" ,.") for part in _CLAUSE_SPLIT_RE.split(claim)]
    return [part for part in parts if part]


def _passage_text(passage: EvidencePassage) -> str:
    parts = [
        passage.text,
        passage.document_name,
        passage.supplier or "",
        passage.product or "",
        passage.effective_date or "",
        passage.expiry_date or "",
    ]
    return " ".join(parts)


def _bind_clause(
    clause: str,
    passages: list[EvidencePassage],
    index: EntityIndex,
) -> tuple[bool, list[int], list[str], list[str], str]:
    """Return (supported, refs, missing_numbers, entities, reason) for a clause."""
    numbers = _numbers(clause)
    entities = index.mentioned(clause)

    if not numbers:
        # Nothing factual to bind; measure lexical overlap with the best passage.
        clause_tokens = set(_tokens(clause))
        if not clause_tokens:
            return True, [], [], entities, "no factual content to check"
        best_ratio = 0.0
        best_ref: list[int] = []
        for passage in passages:
            passage_tokens = set(_tokens(_passage_text(passage)))
            ratio = len(clause_tokens & passage_tokens) / len(clause_tokens)
            if ratio > best_ratio:
                best_ratio = ratio
                best_ref = [passage.ref]
        return (
            best_ratio >= 0.6,
            best_ref if best_ratio >= 0.6 else [],
            [],
            entities,
            f"lexical overlap {best_ratio:.0%}",
        )

    candidates = passages
    if entities:
        # Every entity the clause names must be the entity of the same passage.
        # Matching *any* token would let "Northwind ... 895.00" bind to Helios
        # merely because both passages mention the product.
        candidates = [
            passage
            for passage in candidates
            if all(
                any(
                    re.search(rf"\b{re.escape(token)}\b", _passage_text(passage).lower())
                    for token in index.tokens_for([entity])
                )
                for entity in entities
            )
        ]
    matching = [passage for passage in candidates if numbers <= _numbers(_passage_text(passage))]

    if matching:
        supported = matching[0]
        return (
            True,
            [supported.ref],
            [],
            entities,
            f"numbers {', '.join(sorted(numbers))} and entity/period found together in evidence [{supported.ref}]",
        )

    # Report the numbers that have no support *under the named entity*; a
    # number that only appears for a different supplier is exactly the failure
    # this check exists to catch.
    scoped = candidates if entities else passages
    missing = sorted(
        number
        for number in numbers
        if not any(number in _numbers(_passage_text(passage)) for passage in scoped)
    )
    if entities and missing:
        reason = (
            f"numbers {', '.join(missing[:4])} appear in evidence, but not for "
            f"{', '.join(entities)}"
        )
    else:
        reason = f"no single passage carries numbers {', '.join(sorted(numbers)[:4])} with the named entity/period"
    return False, [], missing, entities, reason


def bind_claims(
    claims: list[str],
    passages: list[EvidencePassage],
    *,
    known_entities: Iterable[str] = (),
) -> list[BindingCheck]:
    """Bind every claim to evidence; a claim passes only if all clauses bind."""
    index = EntityIndex(known_entities)
    checks: list[BindingCheck] = []
    for claim in claims:
        claim_numbers = _numbers(claim)
        if claim_numbers:
            clause_results = [
                _bind_clause(clause, passages, index)
                for clause in _split_clauses(claim)
                if _numbers(clause)
            ]
        else:
            # A claim with no figures is a statement about a document or an
            # entity; splitting it on "and" would only make it harder to match.
            clause_results = [_bind_clause(claim, passages, index)]
        refs = sorted({ref for _ok, refs_, _n, _e, _r in clause_results for ref in refs_})
        missing = sorted({number for _ok, _r, numbers, _e, _x in clause_results for number in numbers})
        entities = sorted({entity for _ok, _r, _n, ents, _x in clause_results for entity in ents})
        failed = [result for result in clause_results if not result[0]]
        supported = bool(clause_results) and not failed
        score = 0.0 if not clause_results else (sum(1 for result in clause_results if result[0]) / len(clause_results))
        if supported:
            reason = "all clauses bound to evidence"
        elif failed:
            reason = failed[0][4]
        else:
            reason = "claim contained no checkable clause"
        checks.append(
            BindingCheck(
                claim=claim,
                supported=supported,
                support_score=score,
                evidence_refs=refs,
                missing_numbers=missing,
                entities=entities,
                reason=reason,
            )
        )
    return checks


def passages_from_blocks(
    blocks: Iterable[dict[str, Any]],
    *,
    structured_facts: Iterable[Any] = (),
    aggregations: Iterable[Any] = (),
    conflicts: Iterable[dict[str, Any]] = (),
    known_entities: Iterable[str] = (),
) -> tuple[list[EvidencePassage], list[str]]:
    """Build the passage list and entity vocabulary a verification run binds to."""
    passages: list[EvidencePassage] = []
    names: set[str] = {name for name in known_entities if name}

    for block in blocks:
        citation = block.get("citation") or {}
        metadata = citation.get("metadata") or {}
        passages.append(
            EvidencePassage(
                ref=len(passages) + 1,
                text=block.get("text") or "",
                document_name=citation.get("document_name") or "",
                page=citation.get("page"),
                effective_date=metadata.get("effective_date"),
                expiry_date=metadata.get("expiry_date"),
                kind="document",
            )
        )

    for fact in structured_facts:
        supplier = getattr(fact, "supplier_name", None)
        product = getattr(fact, "product_name", None)
        names.update(name for name in (supplier, product) if name)
        text = (
            f"{supplier or ''} {product or ''} {getattr(fact, 'unit_price', '')} "
            f"{getattr(fact, 'currency', '')} effective {getattr(fact, 'effective_date', '')} "
            f"expires {getattr(fact, 'expiry_date', '')} document {getattr(fact, 'document_name', '')}"
        )
        passages.append(
            EvidencePassage(
                ref=len(passages) + 1,
                text=text,
                document_name=str(getattr(fact, "document_name", "") or ""),
                supplier=supplier,
                product=product,
                effective_date=str(getattr(fact, "effective_date", "") or ""),
                expiry_date=str(getattr(fact, "expiry_date", "") or ""),
                kind="structured_fact",
            )
        )

    for aggregation in aggregations:
        text = (
            f"{getattr(aggregation, 'name', '')} {getattr(aggregation, 'group', '')} "
            f"{getattr(aggregation, 'value', '')} {getattr(aggregation, 'unit', '')} "
            f"{getattr(aggregation, 'method', '')}"
        )
        passages.append(
            EvidencePassage(ref=len(passages) + 1, text=text, kind="aggregation")
        )

    for conflict in conflicts:
        text = " ".join(
            str(conflict.get(key) or "") for key in ("description", "resolution", "preferred")
        )
        passages.append(EvidencePassage(ref=len(passages) + 1, text=text, kind="conflict"))
        for value in conflict.get("values") or []:
            if isinstance(value, dict):
                names.update(
                    str(value.get(key))
                    for key in ("supplier_name", "product_name")
                    if value.get(key)
                )

    return passages, sorted(names)


__all__ = [
    "BindingCheck",
    "EntityIndex",
    "EvidencePassage",
    "bind_claims",
    "normalise_number",
    "passages_from_blocks",
]
