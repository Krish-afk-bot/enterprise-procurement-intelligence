"""Temporal validity for graph edges.

Edges carry ``effective_date`` and ``expiry_date`` when the entity behind them is
versioned. A historical question ("which price applied in March 2024?") must not
be answered with a superseded or not-yet-effective row, so traversal filters on
an as-of date rather than on today.

Dates are stored as ISO-8601 strings (``YYYY-MM-DD``) by the builder, so lexicographic
comparison on the date portion is exact and avoids parsing every property.
"""

from __future__ import annotations

from datetime import date
from typing import Any


def normalise_as_of(as_of: str | date | None) -> str | None:
    """Validate an as-of date and return it as ``YYYY-MM-DD``."""
    if as_of is None:
        return None
    if isinstance(as_of, date):
        return as_of.isoformat()
    text = str(as_of).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError as exc:
        raise ValueError(f"as_of must be an ISO date (YYYY-MM-DD), got {as_of!r}") from exc


def _date_prefix(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:10]


def edge_valid_at(properties: dict[str, Any] | None, as_of: str | date | None) -> bool:
    """Whether an edge was in force on ``as_of``.

    An edge without temporal properties is always in force: the builder only
    stamps dates it actually extracted, and treating "unknown" as "expired" would
    silently drop evidence instead of reporting it.
    """
    day = normalise_as_of(as_of)
    if day is None:
        return True
    properties = properties or {}
    effective = _date_prefix(properties.get("effective_date"))
    expiry = _date_prefix(properties.get("expiry_date"))
    if effective and effective > day:
        return False
    if expiry and expiry < day:
        return False
    return True


__all__ = ["edge_valid_at", "normalise_as_of"]
