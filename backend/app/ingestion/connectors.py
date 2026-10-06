"""External and CSV structured-data connectors (PRD s.17 Layer B, s.66).

Structured procurement data is not forced through the document pipeline: awards,
purchase lines and price lists arrive as *rows*, land in ``procurement_records``
and ``prices`` with full provenance, and are answered by SQL.

Every imported record keeps:

    source · source_url · retrieved_at · license · original_id

Connectors implement ``discover()`` / ``fetch()`` / ``normalize()`` so a new
source is a new adapter, never a hard-coded scraper.
"""

from __future__ import annotations

import csv
import io
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Protocol, runtime_checkable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import normalize_name
from app.db.models import ProcurementRecord, Supplier
from app.observability.logging import get_logger

logger = get_logger(__name__)

#: Column synonyms accepted for a structured procurement CSV.
COLUMN_SYNONYMS: dict[str, tuple[str, ...]] = {
    "award_id": ("award_id", "awardid", "id", "record_id", "contract_award_id"),
    "buyer": ("buyer", "buyer_name", "agency", "department", "organisation", "organization"),
    "supplier": ("supplier", "supplier_name", "vendor", "vendor_name", "awarded_to", "contractor"),
    "product": ("product", "product_name", "item", "item_description", "description"),
    "category": ("category", "category_name", "product_category", "cpv", "unspsc"),
    "quantity": ("quantity", "qty", "units"),
    "unit_price": ("unit_price", "unitprice", "price_per_unit", "rate"),
    "value": ("value", "amount", "contract_value", "total_value", "award_amount"),
    "currency": ("currency", "ccy"),
    "award_date": ("award_date", "date", "awarded_date", "contract_date", "publication_date"),
    "region": ("region", "location", "country", "place_of_performance"),
}


@dataclass(slots=True)
class NormalizedRecord:
    supplier_name: str
    buyer: str | None = None
    product_name: str | None = None
    category: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    value: float | None = None
    currency: str = "USD"
    award_date: date | None = None
    region: str | None = None
    original_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ImportResult:
    source: str
    records_seen: int = 0
    records_imported: int = 0
    suppliers_created: int = 0
    skipped: int = 0
    warnings: list[str] = field(default_factory=list)
    license: str | None = None
    source_url: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "records_seen": self.records_seen,
            "records_imported": self.records_imported,
            "suppliers_created": self.suppliers_created,
            "skipped": self.skipped,
            "warnings": self.warnings,
            "license": self.license,
            "source_url": self.source_url,
        }


@runtime_checkable
class ProcurementDataSource(Protocol):
    """Adapter contract for a structured procurement source."""

    name: str

    async def discover(self) -> dict[str, Any]: ...

    async def fetch(self) -> AsyncIterator[dict[str, Any]]: ...

    async def normalize(self, record: dict[str, Any]) -> NormalizedRecord | None: ...


class CsvProcurementSource:
    """CSV/xlsx-exported award or purchase-line data."""

    def __init__(
        self,
        *,
        content: bytes,
        source_name: str,
        source_url: str | None = None,
        license: str | None = None,
        delimiter: str | None = None,
    ) -> None:
        self.name = source_name
        self.source_url = source_url
        self.license = license
        text = content.decode("utf-8", errors="replace")
        if delimiter is None:
            try:
                dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
                delimiter = dialect.delimiter
            except csv.Error:
                delimiter = ","
        self._reader = list(csv.DictReader(io.StringIO(text), delimiter=delimiter))

    async def discover(self) -> dict[str, Any]:
        headers = list(self._reader[0].keys()) if self._reader else []
        return {
            "name": self.name,
            "rows": len(self._reader),
            "columns": headers,
            "mapped_columns": map_columns(headers),
            "license": self.license,
            "source_url": self.source_url,
        }

    async def fetch(self) -> AsyncIterator[dict[str, Any]]:
        for row in self._reader:
            yield row

    async def normalize(self, record: dict[str, Any]) -> NormalizedRecord | None:
        return normalize_row(record)


def map_columns(headers: Sequence[str]) -> dict[str, str]:
    """Map source column names onto the platform's record fields."""
    mapping: dict[str, str] = {}
    for header in headers:
        cleaned = (header or "").strip().lower().replace(" ", "_")
        for field_name, synonyms in COLUMN_SYNONYMS.items():
            if field_name in mapping:
                continue
            if cleaned in synonyms or any(synonym in cleaned for synonym in synonyms if len(synonym) > 3):
                mapping[field_name] = header
                break
    return mapping


def normalize_row(record: dict[str, Any]) -> NormalizedRecord | None:
    mapping = {value: key for key, value in map_columns(list(record.keys())).items()}
    values: dict[str, Any] = {}
    for column, value in record.items():
        field_name = mapping.get(column)
        if field_name:
            values[field_name] = value
    supplier_name = str(values.get("supplier") or "").strip()
    if not supplier_name:
        return None
    return NormalizedRecord(
        supplier_name=supplier_name,
        buyer=_clean(values.get("buyer")),
        product_name=_clean(values.get("product")),
        category=_clean(values.get("category")),
        quantity=_to_float(values.get("quantity")),
        unit_price=_to_float(values.get("unit_price")),
        value=_to_float(values.get("value")),
        currency=(_clean(values.get("currency")) or "USD").upper()[:3],
        award_date=_to_date(values.get("award_date")),
        region=_clean(values.get("region")),
        original_id=_clean(values.get("award_id")),
        raw={str(key): value for key, value in record.items()},
    )


class ProcurementDataImporter:
    """Writes normalized records into PostgreSQL with supplier resolution."""

    def __init__(self, session: AsyncSession, *, tenant_id: str, is_synthetic: bool = False) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.is_synthetic = is_synthetic
        self._supplier_cache: dict[str, Supplier] = {}

    async def _resolve_supplier(self, name: str, result: ImportResult) -> Supplier | None:
        normalized = normalize_name(name)
        if normalized in self._supplier_cache:
            return self._supplier_cache[normalized]
        supplier = (
            await self.session.execute(
                select(Supplier).where(
                    Supplier.tenant_id == self.tenant_id, Supplier.normalized_name == normalized
                )
            )
        ).scalar_one_or_none()
        if supplier is None:
            supplier = Supplier(
                tenant_id=self.tenant_id,
                name=name,
                normalized_name=normalized,
                region=None,
                status="active",
                is_synthetic=self.is_synthetic,
                source=result.source,
                source_url=result.source_url,
                license=result.license,
            )
            self.session.add(supplier)
            await self.session.flush()
            result.suppliers_created += 1
        else:
            if not supplier.source:
                supplier.source = result.source
                supplier.source_url = result.source_url or supplier.source_url
                supplier.license = result.license or supplier.license
        self._supplier_cache[normalized] = supplier
        return supplier

    async def import_row(self, record: NormalizedRecord, result: ImportResult) -> bool:
        supplier = await self._resolve_supplier(record.supplier_name, result)
        if supplier is None:
            result.skipped += 1
            return False
        row = ProcurementRecord(
            tenant_id=self.tenant_id,
            buyer=record.buyer,
            supplier_name=record.supplier_name,
            supplier_id=supplier.id,
            product_name=record.product_name,
            category=record.category,
            quantity=record.quantity,
            unit_price=record.unit_price,
            value=record.value if record.value is not None else _derive_value(record),
            currency=record.currency,
            award_date=record.award_date,
            region=record.region,
            raw=record.raw,
            is_synthetic=self.is_synthetic,
            source=result.source,
            source_url=result.source_url,
            license=result.license,
            original_id=record.original_id,
            retrieved_at=datetime.now(timezone.utc),
        )
        self.session.add(row)
        result.records_imported += 1
        return True


async def import_csv_source(
    session: AsyncSession,
    *,
    tenant_id: str,
    content: bytes,
    source_name: str,
    source_url: str | None = None,
    license: str | None = None,
    is_synthetic: bool = False,
) -> ImportResult:
    source = CsvProcurementSource(
        content=content, source_name=source_name, source_url=source_url, license=license
    )
    result = ImportResult(source=source_name, license=license, source_url=source_url)
    importer = ProcurementDataImporter(session, tenant_id=tenant_id, is_synthetic=is_synthetic)
    async for raw in source.fetch():
        result.records_seen += 1
        normalized = await source.normalize(raw)
        if normalized is None:
            result.skipped += 1
            continue
        await importer.import_row(normalized, result)
    if result.skipped:
        result.warnings.append(
            f"{result.skipped} row(s) were skipped because the supplier column was empty or unmapped."
        )
    logger.info("structured_source_imported", **result.as_dict())
    return result


def _derive_value(record: NormalizedRecord) -> float | None:
    if record.quantity is not None and record.unit_price is not None:
        return round(record.quantity * record.unit_price, 2)
    return None


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).replace(",", "").replace("$", "").replace("€", "").replace("£", "").strip()
    try:
        return float(text)
    except ValueError:
        return None


def _to_date(value: Any) -> date | None:
    if value is None:
        return None
    text = str(value).strip()
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:10], pattern).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text[:10]).date()
    except ValueError:
        return None


__all__ = [
    "CsvProcurementSource",
    "ImportResult",
    "NormalizedRecord",
    "ProcurementDataImporter",
    "ProcurementDataSource",
    "import_csv_source",
    "map_columns",
    "normalize_row",
]
