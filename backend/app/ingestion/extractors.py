"""Structured extraction (the bridge from documents into SQL facts).

Tables and clause text are mined with explicit header synonyms and value parsers
so that aggregated questions ("total 2025 spend", "lowest unit price") can be
answered by PostgreSQL instead of being guessed by a language model.

Every extracted record carries the source document and page it came from, which
is what makes the numbers defensible.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from app.ingestion.metadata import ExtractedMetadata
from app.ingestion.types import ParsedDocument, ParsedTable
from app.observability.logging import get_logger

logger = get_logger(__name__)

HEADER_SYNONYMS: dict[str, tuple[str, ...]] = {
    "product": ("product", "item", "description", "material", "service", "sku", "part number", "goods"),
    "unit_price": ("unit price", "price per unit", "net price", "unit cost", "rate", "price", "unit rate"),
    "currency": ("currency", "ccy", "curr"),
    "moq": ("moq", "minimum order quantity", "min qty", "minimum quantity", "min order"),
    "discount": ("discount", "discount %", "rebate", "discount rate"),
    "quantity": ("quantity", "qty", "ordered qty", "annual volume", "volume"),
    "line_total": ("total", "amount", "extended", "line total", "net amount"),
    "effective_date": ("effective date", "valid from", "start date", "from"),
    "expiry_date": ("expiry date", "valid to", "end date", "expires", "to"),
    "payment_terms": ("payment terms", "payment", "terms of payment"),
    "delivery_terms": ("delivery", "lead time", "delivery terms", "incoterms"),
    "supplier": ("supplier", "vendor", "awarded to"),
}

_AMOUNT_RE = re.compile(r"([$€£¥]?)\s?([\d][\d,]*(?:\.\d{1,4})?)\s*(%|percent|k|m|million|thousand)?", re.IGNORECASE)
_DATE_RE = re.compile(
    r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|[A-Z][a-z]{2,8}\s+\d{1,2},?\s+\d{4}|\d{1,2}\s+[A-Z][a-z]{2,8}\s+\d{4})\b"
)
TERM_PATTERNS: dict[str, re.Pattern[str]] = {
    "payment_terms": re.compile(
        r"payment\s+terms?\s*(?:are|shall be|:)?\s*(net\s*\d+[^\n.;]{0,40}|[^\n.;]{0,60}days[^\n.;]{0,20})",
        re.IGNORECASE,
    ),
    "delivery_terms": re.compile(
        r"(?:delivery|lead\s+time)\s*(?:terms?|time)?\s*(?:are|shall be|is|:)?\s*([^\n.;]{4,80})",
        re.IGNORECASE,
    ),
    "renewal": re.compile(r"(renewal[^\n.;]{0,120})", re.IGNORECASE),
    "termination_notice": re.compile(r"(terminat\w+[^\n.;]{0,100}(?:notice|days)[^\n.;]{0,40})", re.IGNORECASE),
    "discount": re.compile(r"(\d{1,2}(?:\.\d+)?)\s*%\s*(?:discount|rebate)", re.IGNORECASE),
    "warranty": re.compile(r"(warranty[^\n.;]{0,120})", re.IGNORECASE),
    "governing_law": re.compile(r"(governing law[^\n.;]{0,80})", re.IGNORECASE),
}

COMPLIANCE_PATTERNS: dict[str, re.Pattern[str]] = {
    "ISO 9001": re.compile(r"\biso\s*9001(?::\d{4})?\b", re.IGNORECASE),
    "ISO 14001": re.compile(r"\biso\s*14001(?::\d{4})?\b", re.IGNORECASE),
    "ISO 27001": re.compile(r"\biso\s*27001(?:\s*/\s*27002)?\b", re.IGNORECASE),
    "SOC 2": re.compile(r"\bsoc\s*2(?:\s*type\s*(?:i|ii))?\b", re.IGNORECASE),
    "GDPR": re.compile(r"\bgdpr\b", re.IGNORECASE),
    "Modern Slavery Act": re.compile(r"\bmodern\s+slavery\s+act\b", re.IGNORECASE),
    "REACH": re.compile(r"\breach\b", re.IGNORECASE),
    "RoHS": re.compile(r"\brohs\b", re.IGNORECASE),
}


@dataclass(slots=True)
class ExtractedPrice:
    product_name: str
    unit_price: float
    currency: str = "USD"
    minimum_quantity: int | None = None
    discount_percent: float | None = None
    payment_terms: str | None = None
    delivery_terms: str | None = None
    quantity: int | None = None
    line_total: float | None = None
    effective_date: date | None = None
    expiry_date: date | None = None
    source_page: int | None = None
    source_table_index: int | None = None
    row_index: int = 0
    raw_row: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ExtractedCompliance:
    certificate_type: str
    certificate_number: str | None = None
    issued_date: date | None = None
    expiry_date: date | None = None
    source_page: int | None = None
    scope: str | None = None


@dataclass(slots=True)
class ExtractedTerms:
    payment_terms: str | None = None
    delivery_terms: str | None = None
    renewal: str | None = None
    termination_notice: str | None = None
    discount_percent: float | None = None
    warranty: str | None = None
    governing_law: str | None = None
    evidence: dict[str, dict[str, object]] = field(default_factory=dict)


@dataclass(slots=True)
class ExtractionResult:
    prices: list[ExtractedPrice] = field(default_factory=list)
    compliance: list[ExtractedCompliance] = field(default_factory=list)
    terms: ExtractedTerms = field(default_factory=ExtractedTerms)
    notes: list[str] = field(default_factory=list)


def extract_structured(
    document: ParsedDocument, meta: ExtractedMetadata, *, default_currency: str = "USD"
) -> ExtractionResult:
    result = ExtractionResult()
    currency = meta.currency or default_currency

    for page in document.pages:
        for index, table in enumerate(page.tables):
            if not table.headers:
                continue
            mapping = _map_headers(table.headers)
            if "unit_price" not in mapping and "line_total" not in mapping:
                continue
            for row_index, row in enumerate(table.rows):
                price = _price_from_row(
                    row,
                    mapping,
                    page_number=page.page_number,
                    table_index=index,
                    row_index=row_index,
                    currency=currency,
                    meta=meta,
                    headers=table.headers,
                )
                if price is not None:
                    result.prices.append(price)

    if not result.prices:
        result.notes.append(
            "No pricing table with a recognisable unit-price column was found; "
            "pricing questions for this document rely on clause text retrieval."
        )

    result.terms = _extract_terms(document)
    result.compliance = _extract_compliance(document, meta)
    return result


def _map_headers(headers: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for position, header in enumerate(headers):
        normalized = re.sub(r"[^a-z0-9% ]", "", (header or "").lower()).strip()
        if not normalized:
            continue
        for field_name, synonyms in HEADER_SYNONYMS.items():
            if field_name in mapping:
                continue
            if any(normalized == synonym or synonym in normalized for synonym in synonyms):
                mapping[field_name] = position
                break
    return mapping


def _cell(row: list[str], mapping: dict[str, int], key: str) -> str | None:
    index = mapping.get(key)
    if index is None or index >= len(row):
        return None
    value = (row[index] or "").strip()
    return value or None


def _price_from_row(
    row: list[str],
    mapping: dict[str, int],
    *,
    page_number: int,
    table_index: int,
    row_index: int,
    currency: str,
    meta: ExtractedMetadata,
    headers: list[str],
) -> ExtractedPrice | None:
    product = _cell(row, mapping, "product")
    unit_price_raw = _cell(row, mapping, "unit_price")
    total_raw = _cell(row, mapping, "line_total")
    quantity_raw = _cell(row, mapping, "quantity")
    moq_raw = _cell(row, mapping, "moq")

    unit_price = _parse_amount(unit_price_raw)
    quantity = _parse_int(quantity_raw)
    line_total = _parse_amount(total_raw)
    if unit_price is None and line_total is not None and quantity:
        unit_price = round(line_total / quantity, 4)
    if unit_price is None:
        return None
    if product is None:
        # Fall back to the row's first non-numeric cell as the product label.
        for cell in row:
            if cell and _parse_amount(cell) is None and len(cell) > 1:
                product = cell.strip()
                break
    if product is None:
        return None

    discount = _parse_percent(_cell(row, mapping, "discount"))
    row_currency = (_cell(row, mapping, "currency") or currency).upper()
    price = ExtractedPrice(
        product_name=product[:200],
        unit_price=unit_price,
        currency=re.sub(r"[^A-Z]", "", row_currency)[:3] or currency,
        minimum_quantity=_parse_int(moq_raw),
        discount_percent=discount,
        payment_terms=_cell(row, mapping, "payment_terms"),
        delivery_terms=_cell(row, mapping, "delivery_terms"),
        quantity=quantity,
        line_total=line_total,
        effective_date=_parse_date(_cell(row, mapping, "effective_date")) or meta.effective_date,
        expiry_date=_parse_date(_cell(row, mapping, "expiry_date")) or meta.expiry_date,
        source_page=page_number,
        source_table_index=table_index,
        row_index=row_index,
        raw_row=[cell for cell in row][:12],
    )
    if not price.effective_date:
        price.notes.append("No effective date on the row or the document; the price is treated as undated.")
    return price


def _parse_amount(raw: str | None) -> float | None:
    if raw is None:
        return None
    if "%" in raw:
        return None
    match = _AMOUNT_RE.search(raw.replace(" ", ""))
    if not match:
        return None
    digits = match.group(2).replace(",", "")
    try:
        value = float(digits)
    except ValueError:
        return None
    magnitude = (match.group(3) or "").lower()
    if magnitude in {"k", "thousand"}:
        value *= 1_000
    elif magnitude in {"m", "million"}:
        value *= 1_000_000
    return value


def _parse_int(raw: str | None) -> int | None:
    if raw is None:
        return None
    match = re.search(r"(\d[\d,]*)", raw)
    if not match:
        return None
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return None


def _parse_percent(raw: str | None) -> float | None:
    if raw is None:
        return None
    match = re.search(r"(\d{1,3}(?:\.\d{1,2})?)\s*%?", raw)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    match = _DATE_RE.search(raw)
    if not match:
        return None
    from app.ingestion.metadata import _parse_date as parse

    return parse(match.group(1))


def _extract_terms(document: ParsedDocument) -> ExtractedTerms:
    text = document.full_text
    terms = ExtractedTerms()
    for field_name, pattern in TERM_PATTERNS.items():
        match = pattern.search(text)
        if not match:
            continue
        value = re.sub(r"\s+", " ", match.group(1)).strip(" .,:;-")
        if not value:
            continue
        if field_name == "discount":
            parsed = _parse_percent(value)
            if parsed is None:
                continue
            terms.discount_percent = parsed
        else:
            setattr(terms, field_name, value[:200])
        page = next(
            (page.page_number for page in document.pages if match.group(0)[:40] in page.best_text), None
        )
        terms.evidence[field_name] = {"snippet": match.group(0)[:240], "page": page}
    return terms


def _extract_compliance(document: ParsedDocument, meta: ExtractedMetadata) -> list[ExtractedCompliance]:
    text = document.full_text
    found: list[ExtractedCompliance] = []
    for certificate_type, pattern in COMPLIANCE_PATTERNS.items():
        if not pattern.search(text):
            continue
        page = next((p.page_number for p in document.pages if pattern.search(p.best_text)), None)
        number_match = re.search(
            rf"{re.escape(certificate_type)}[^\n]{{0,40}}?(?:certificate|cert)\s*(?:no\.?|number|#)\s*[:#]?\s*([A-Z0-9\-]{{4,24}})",
            text,
            re.IGNORECASE,
        )
        issues = re.search(
            rf"{re.escape(certificate_type)}[^\n]{{0,80}}?(?:issued|valid from)\s*([0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}})",
            text,
            re.IGNORECASE,
        )
        expiry = re.search(
            rf"{re.escape(certificate_type)}[^\n]{{0,80}}?(?:expires?|valid (?:until|to)|expiry)\s*([0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}})",
            text,
            re.IGNORECASE,
        )
        found.append(
            ExtractedCompliance(
                certificate_type=certificate_type,
                certificate_number=number_match.group(1) if number_match else None,
                issued_date=_parse_date(issues.group(1)) if issues else None,
                expiry_date=_parse_date(expiry.group(1)) if expiry else meta.expiry_date,
                source_page=page,
                scope="Referenced in document text",
            )
        )
    return found


__all__ = [
    "ExtractedCompliance",
    "ExtractedPrice",
    "ExtractedTerms",
    "ExtractionResult",
    "ParsedTable",
    "extract_structured",
]
