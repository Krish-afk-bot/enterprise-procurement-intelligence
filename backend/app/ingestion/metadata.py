"""Document metadata extraction.

Deterministic, auditable extraction of the fields procurement users cite most:
contract number, parties, dates, version/amendment label, currency and total
value. Each extracted field records the snippet and page it came from so the UI
can show evidence for metadata too — nothing is inferred silently.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from dateutil import parser as date_parser

from app.ingestion.types import ParsedDocument
from app.observability.logging import get_logger

logger = get_logger(__name__)

CONTRACT_NUMBER_RE = re.compile(
    r"\b(?:contract|agreement|agreement\s+no\.?|contract\s+no\.?|contract\s+number|ref(?:erence)?)\s*[:#]?\s*"
    r"([A-Z]{2,6}[-/][A-Z0-9][A-Z0-9\-/]{2,24})",
    re.IGNORECASE,
)
CONTRACT_NUMBER_LOOSE_RE = re.compile(r"\b([A-Z]{2,5}-\d{4}-\d{2,5}(?:-[A-Z0-9]{1,6})?)\b")
AMENDMENT_RE = re.compile(
    r"\b(amendment|addendum|variation|change\s+order)\s*(?:no\.?|number|#)?\s*(\d+|[IVX]+|[A-Z])\b",
    re.IGNORECASE,
)
VERSION_RE = re.compile(r"\b(?:version|revision|rev)\.?\s*[:#]?\s*(\d+(?:\.\d+)?)\b", re.IGNORECASE)
PARTIES_RE = re.compile(
    r"between\s+(?P<buyer>[A-Z][A-Za-z0-9&.,'\- ]{3,80}?)\s+(?:\(|,)?\s*(?:and|&)\s+"
    r"(?P<supplier>[A-Z][A-Za-z0-9&.,'\- ]{3,80}?)\s*(?:\(|,|\.|\n|$)",
    re.IGNORECASE,
)
SUPPLIER_FIELD_RE = re.compile(r"\b(?:supplier|vendor|contractor)\s*(?:name)?\s*[:#]\s*([^\n]{3,80})", re.IGNORECASE)
SUPPLIER_PHRASE_RE = re.compile(
    r"\b(?:supplied\s+by|issued\s+to|provided\s+by|on\s+behalf\s+of)\s*[:]?\s+([A-Z][A-Za-z0-9&.,'\- ]{3,80}?)"
    r"(?=\s+(?:under|per|for|pursuant|in\s+respect|$)|[\n,;.]|$)",
    re.IGNORECASE,
)
EFFECTIVE_RE = re.compile(
    r"\b(?:effective(?:\s+date)?|commencement(?:\s+date)?|start\s+date|dated)\b\s*(?:as\s+of|on|:)?\s*"
    r"([A-Za-z0-9,\.\-/ ]{6,40}?)(?=\n|;|\.|$)",
    re.IGNORECASE,
)
EXPIRY_RE = re.compile(
    r"\b(?:expir(?:y|es|ation)(?:\s+date)?|end\s+date|termination\s+date|valid\s+until)\b\s*(?:on|:)?\s*"
    r"([A-Za-z0-9,\.\-/ ]{6,40}?)(?=\n|;|\.|$)",
    re.IGNORECASE,
)
CURRENCY_RE = re.compile(r"\b(USD|EUR|GBP|CAD|AUD|INR|JPY|CHF|SEK|NOK|CNY|ZAR)\b")
CURRENCY_SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}
TOTAL_VALUE_RE = re.compile(
    r"\b(?:total\s+(?:contract\s+)?value|contract\s+value|total\s+amount|not\s+to\s+exceed)\b"
    r"\s*(?:of|:)?\s*([$€£¥]?\s?[\d,]+(?:\.\d{1,2})?)\s*(million|m|k|thousand)?",
    re.IGNORECASE,
)

DOCUMENT_TYPE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("amendment", ("amendment", "addendum", "variation", "change order", "amended")),
    ("compliance_certificate", ("certificate", "iso 9001", "compliance certificate", "certification", "audit certificate")),
    ("pricing_schedule", ("price list", "pricing schedule", "rate card", "price schedule", "unit prices")),
    ("pricing_agreement", ("pricing agreement", "price agreement", "rebate agreement")),
    ("purchase_order", ("purchase order", "po number")),
    ("invoice", ("invoice", "tax invoice", "amount due")),
    ("specification", ("specification", "statement of work", "technical requirement")),
    ("tender", ("tender", "request for proposal", "rfp", "invitation to bid")),
    ("contract", ("agreement", "contract", "master service", "terms and conditions")),
)


@dataclass(slots=True)
class ExtractedMetadata:
    document_type: str = "other"
    title: str = ""
    contract_number: str | None = None
    supplier_name: str | None = None
    buyer_name: str | None = None
    amendment_label: str | None = None
    amendment_number: int | None = None
    version: int | None = None
    revision_label: str | None = None
    effective_date: date | None = None
    expiry_date: date | None = None
    currency: str | None = None
    total_value: float | None = None
    keywords: list[str] = field(default_factory=list)
    evidence: dict[str, dict[str, Any]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    is_synthetic: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "document_type": self.document_type,
            "title": self.title,
            "contract_number": self.contract_number,
            "supplier_name": self.supplier_name,
            "buyer_name": self.buyer_name,
            "amendment_label": self.amendment_label,
            "amendment_number": self.amendment_number,
            "version": self.version,
            "revision_label": self.revision_label,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "currency": self.currency,
            "total_value": self.total_value,
            "keywords": self.keywords,
            "evidence": self.evidence,
            "warnings": self.warnings,
            "is_synthetic": self.is_synthetic,
        }


def _page_of(text: str, needle: str, document: ParsedDocument) -> int | None:
    for page in document.pages:
        if needle[:60] in page.best_text:
            return page.page_number
    return None


def _record(meta: ExtractedMetadata, field_name: str, value: Any, snippet: str, page: int | None) -> None:
    meta.evidence[field_name] = {"snippet": snippet.strip()[:280], "page": page, "method": "rule"}


def extract_metadata(
    document: ParsedDocument,
    *,
    filename: str = "",
    declared_type: str | None = None,
    prefer_first_pages: int = 3,
) -> ExtractedMetadata:
    meta = ExtractedMetadata()
    full_text = document.full_text
    head = "\n".join(page.best_text for page in document.pages[:prefer_first_pages]) or full_text

    meta.title = (document.title or "").strip() or _title_from_text(head) or _title_from_filename(filename)
    meta.is_synthetic = "synthetic" in full_text.lower() and "test corpus" in full_text.lower()

    # --- contract number
    for pattern in (CONTRACT_NUMBER_RE, CONTRACT_NUMBER_LOOSE_RE):
        match = pattern.search(head) or pattern.search(full_text)
        if match:
            meta.contract_number = match.group(1).strip().upper()
            _record(meta, "contract_number", meta.contract_number, match.group(0), _page_of(full_text, match.group(0), document))
            break

    # --- amendment / version
    amendment = AMENDMENT_RE.search(head) or AMENDMENT_RE.search(full_text)
    if amendment:
        label = f"{amendment.group(1).title()} {amendment.group(2).upper()}"
        meta.amendment_label = label
        meta.amendment_number = _roman_or_int(amendment.group(2))
        _record(meta, "amendment_label", label, amendment.group(0), _page_of(full_text, amendment.group(0), document))
    version_match = VERSION_RE.search(head)
    if version_match:
        try:
            meta.version = int(float(version_match.group(1)))
        except ValueError:
            meta.version = None
        _record(meta, "version", meta.version, version_match.group(0), _page_of(full_text, version_match.group(0), document))

    # --- parties
    parties = PARTIES_RE.search(head) or PARTIES_RE.search(full_text)
    if parties:
        supplier = _clean_party(parties.group("supplier"))
        buyer = _clean_party(parties.group("buyer"))
        if supplier:
            meta.supplier_name = supplier
            _record(meta, "supplier_name", supplier, parties.group(0), _page_of(full_text, parties.group(0), document))
        if buyer:
            meta.buyer_name = buyer
    if not meta.supplier_name:
        phrase_match = SUPPLIER_PHRASE_RE.search(head) or SUPPLIER_PHRASE_RE.search(full_text)
        if phrase_match:
            meta.supplier_name = _clean_party(phrase_match.group(1))
            _record(
                meta,
                "supplier_name",
                meta.supplier_name,
                phrase_match.group(0),
                _page_of(full_text, phrase_match.group(0), document),
            )
    if not meta.supplier_name:
        field_match = SUPPLIER_FIELD_RE.search(head) or SUPPLIER_FIELD_RE.search(full_text)
        if field_match:
            meta.supplier_name = _clean_party(field_match.group(1))
            _record(
                meta,
                "supplier_name",
                meta.supplier_name,
                field_match.group(0),
                _page_of(full_text, field_match.group(0), document),
            )

    # --- dates
    effective = EFFECTIVE_RE.search(head) or EFFECTIVE_RE.search(full_text)
    if effective:
        parsed = _parse_date(effective.group(1))
        if parsed:
            meta.effective_date = parsed
            _record(meta, "effective_date", parsed.isoformat(), effective.group(0), _page_of(full_text, effective.group(0), document))
    expiry = EXPIRY_RE.search(head) or EXPIRY_RE.search(full_text)
    if expiry:
        parsed = _parse_date(expiry.group(1))
        if parsed:
            meta.expiry_date = parsed
            _record(meta, "expiry_date", parsed.isoformat(), expiry.group(0), _page_of(full_text, expiry.group(0), document))

    # --- money
    currency = CURRENCY_RE.search(head)
    if currency:
        meta.currency = currency.group(1).upper()
    else:
        for symbol, code in CURRENCY_SYMBOLS.items():
            if symbol in head:
                meta.currency = code
                break
    total = TOTAL_VALUE_RE.search(head) or TOTAL_VALUE_RE.search(full_text)
    if total:
        amount = _parse_amount(total.group(1), total.group(2))
        if amount is not None:
            meta.total_value = amount
            _record(meta, "total_value", amount, total.group(0), _page_of(full_text, total.group(0), document))

    # --- document type
    meta.document_type = declared_type or _classify_type(
        f"{filename} {meta.title} {meta.amendment_label or ''}", head
    )
    if meta.document_type == "contract" and meta.amendment_label:
        meta.document_type = "amendment"

    # --- revision label
    if meta.amendment_label:
        meta.revision_label = meta.amendment_label
    elif meta.version and meta.version > 1:
        meta.revision_label = f"v{meta.version}"

    meta.keywords = _keywords(head)
    if not meta.effective_date:
        meta.warnings.append("No effective date was detected in the document text.")
    return meta


_ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10}


def _roman_or_int(raw: str) -> int | None:
    value = (raw or "").strip().upper()
    if value.isdigit():
        return int(value)
    if value in _ROMAN:
        return _ROMAN[value]
    if len(value) == 1 and value.isalpha():
        return ord(value) - ord("A") + 1
    return None


def _title_from_text(head: str) -> str:
    for line in head.splitlines():
        candidate = line.strip()
        if 6 <= len(candidate) <= 120 and any(ch.isalpha() for ch in candidate):
            if candidate.isupper() or candidate.istitle():
                return candidate
    return ""


def _title_from_filename(filename: str) -> str:
    from pathlib import Path

    stem = Path(filename).stem if filename else ""
    return re.sub(r"[_\-]+", " ", stem).strip().title()


def _clean_party(value: str) -> str:
    cleaned = re.sub(r"[\"'\(\)]", "", value or "").strip(" .,:;-")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:120]


def _classify_type(haystack: str, body: str) -> str:
    text = haystack.lower()
    for doc_type, keywords in DOCUMENT_TYPE_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return doc_type
    body_lower = body.lower()
    for doc_type, keywords in DOCUMENT_TYPE_KEYWORDS:
        if any(body_lower.count(keyword) >= 2 for keyword in keywords):
            return doc_type
    return "other"


def _parse_amount(raw: str, magnitude: str | None) -> float | None:
    cleaned = re.sub(r"[$€£¥,\s]", "", raw or "")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    if magnitude:
        factor = {"million": 1_000_000, "m": 1_000_000, "k": 1_000, "thousand": 1_000}.get(
            magnitude.lower(), 1
        )
        value *= factor
    return value


def _parse_date(raw: str) -> date | None:
    candidate = (raw or "").strip().rstrip(".,;:")
    candidate = re.sub(r"^(?:as\s+of|on|the)\s+", "", candidate, flags=re.IGNORECASE)
    if not candidate or len(candidate) < 6:
        return None
    try:
        return date_parser.parse(candidate, fuzzy=True, default=datetime(2000, 1, 1)).date()
    except (ValueError, OverflowError, TypeError):
        return None


_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "shall", "will", "from", "such", "have", "been",
    "which", "under", "upon", "any", "all", "not", "are", "its", "may", "each", "other", "herein",
}


def _keywords(text: str, limit: int = 25) -> list[str]:
    counts: dict[str, int] = {}
    for token in re.findall(r"[A-Za-z][A-Za-z\-]{3,}", text.lower()):
        if token in _STOPWORDS:
            continue
        counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    return [word for word, _ in ranked[:limit]]
