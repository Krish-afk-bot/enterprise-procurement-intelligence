"""Temporal interpretation for questions about earlier contract states.

Policy (documented, and deliberately conservative):

* **Timezone** — all dates are calendar dates. No timezone conversion is applied,
  because procurement documents record dates, not instants. "Today" comes from
  ``app.core.clock.today()``, which honours ``EVAL_AS_OF_DATE`` so evaluation is
  reproducible; that is the reference date for every relative expression.
* **Point in time vs period** — "as of <date>" yields that exact date. A question
  that names a period ("during 2024", "in June 2025") is evaluated at the *end*
  of that period: asking what was in force during a window is answered by the
  state at the window's close.
* **Ambiguity is not guessed.** A numeric date like ``03/04/2025`` is day-first
  in UK procurement and month-first in US usage; when neither component exceeds
  12 the date is left unresolved and a note is recorded. An unresolved question
  falls back to the established default (no as-of filter, i.e. current state),
  never to an invented date.
* **Which date is which** — the as-of filter applies to the *validity* window of
  a relationship (contract effective/expiry, price effective/expiry, amendment
  date). Document creation, publication and ingestion timestamps are never used
  as a substitute: they record when the platform saw a file, not when a term was
  agreed.
* **Originals** — "original terms" is a version question, not a date question, so
  it yields ``ORIGINAL`` with no as-of date and the caller prefers the earliest
  recorded version.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import StrEnum

TIMEZONE = "UTC"
REFERENCE_POLICY = "calendar date in UTC; EVAL_AS_OF_DATE overrides today()"

_MONTHS = {name.lower(): index for index, name in enumerate(calendar.month_name) if name}
_MONTHS.update({name.lower(): index for index, name in enumerate(calendar.month_abbr) if name})

_ISO_DATE = re.compile(r"\b(?P<y>(?:19|20)\d{2})-(?P<m>\d{1,2})-(?P<d>\d{1,2})\b")
_DAY_MONTH_YEAR = re.compile(
    r"\b(?P<d>\d{1,2})\s+(?P<month>"
    + "|".join(sorted(_MONTHS, key=len, reverse=True))
    + r")\s+(?P<y>(?:19|20)\d{2})\b",
    re.IGNORECASE,
)
_MONTH_YEAR = re.compile(
    r"\b(?P<month>" + "|".join(sorted(_MONTHS, key=len, reverse=True)) + r")\s+(?P<y>(?:19|20)\d{2})\b",
    re.IGNORECASE,
)
_NUMERIC_DATE = re.compile(r"\b(?P<a>\d{1,2})/(?P<b>\d{1,2})/(?P<y>(?:19|20)\d{2})\b")
#: A bare year only counts as a period when a temporal preposition introduces
#: it. Without that guard a document title such as "RFQ 2025/59" would silently
#: turn an ordinary question into a historical one.
_BARE_YEAR = re.compile(
    r"\b(?:in|during|for|since|throughout|as of|as at|by|calendar year)\s+(?P<y>(?:19|20)\d{2})\b(?!\s*/)",
    re.IGNORECASE,
)

_AS_OF_HINT = re.compile(r"\b(as of|as at|on the|effective on|status on)\b", re.IGNORECASE)
_ORIGINAL_HINT = re.compile(r"\b(original|initial|first agreed|as first signed)\b", re.IGNORECASE)
_AFTER_AMENDMENT = re.compile(r"\b(after|since)\b.*\bamendment\b", re.IGNORECASE)
_CURRENT_HINT = re.compile(r"\b(current|currently|latest|today|still (?:in force|valid))\b", re.IGNORECASE)
_LAST_YEAR = re.compile(r"\blast year\b", re.IGNORECASE)
_LAST_QUARTER = re.compile(r"\blast quarter\b", re.IGNORECASE)
_LAST_MONTH = re.compile(r"\blast month\b", re.IGNORECASE)


class TemporalIntent(StrEnum):
    AS_OF = "as_of"
    RANGE = "range"
    ORIGINAL = "original"
    CHANGE = "change"
    CURRENT = "current"
    NONE = "none"


@dataclass(slots=True)
class TemporalResolution:
    as_of: date | None = None
    intent: TemporalIntent = TemporalIntent.NONE
    source: str = "none"
    confidence: str = "none"
    ambiguous: bool = False
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "as_of": self.as_of.isoformat() if self.as_of else None,
            "intent": self.intent.value,
            "source": self.source,
            "confidence": self.confidence,
            "ambiguous": self.ambiguous,
            "notes": self.notes,
        }


def end_of_month(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def quarter_end(day: date) -> date:
    end_month = ((day.month - 1) // 3 + 1) * 3
    return end_of_month(day.year, end_month)


def previous_quarter_end(day: date) -> date:
    start = date(day.year, ((day.month - 1) // 3) * 3 + 1, 1)
    return start - timedelta(days=1)


def _parse_explicit(text: str) -> tuple[date | None, list[str], bool]:
    """Return (date, notes, ambiguous) for the first explicit date in the text."""
    match = _ISO_DATE.search(text)
    if match:
        try:
            return date(int(match["y"]), int(match["m"]), int(match["d"])), [], False
        except ValueError:
            return None, [f"'{match.group(0)}' is not a real calendar date."], False

    match = _DAY_MONTH_YEAR.search(text)
    if match:
        month = _MONTHS[match["month"].lower()]
        try:
            return date(int(match["y"]), month, int(match["d"])), [], False
        except ValueError:
            return None, [f"'{match.group(0)}' is not a real calendar date."], False

    match = _NUMERIC_DATE.search(text)
    if match:
        first, second, year = int(match["a"]), int(match["b"]), int(match["y"])
        if first > 12 and second <= 12:
            day, month = first, second
        elif second > 12 and first <= 12:
            month, day = first, second
        else:
            return (
                None,
                [f"'{match.group(0)}' is ambiguous (day-first or month-first); no as-of date was applied."],
                True,
            )
        try:
            return date(year, month, day), [], False
        except ValueError:
            return None, [f"'{match.group(0)}' is not a real calendar date."], False

    match = _MONTH_YEAR.search(text)
    if match:
        month = _MONTHS[match["month"].lower()]
        year = int(match["y"])
        # Month precision only: evaluate at the end of the month.
        return end_of_month(year, month), ["Month precision: resolved to the last day of the month."], False

    return None, [], False


def derive_as_of(
    question: str,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    year: int | None = None,
    requires_temporal: bool = False,
    reference: date | None = None,
) -> TemporalResolution:
    """Interpret the temporal part of a question. Never invents a date."""
    reference = reference or _reference()
    text = question or ""
    resolution = TemporalResolution()

    if _ORIGINAL_HINT.search(text):
        resolution.intent = TemporalIntent.ORIGINAL
        resolution.source = "version"
        resolution.confidence = "high"
        resolution.notes.append(
            "The question asks for the original terms; the earliest recorded version is preferred and no as-of date is applied."
        )
        return resolution

    if _AFTER_AMENDMENT.search(text):
        resolution.intent = TemporalIntent.CHANGE
        resolution.source = "amendment"
        resolution.notes.append(
            "The question compares states across amendments; amendment dates are read from the contract rows rather than guessed."
        )
        return resolution

    explicit, notes, ambiguous = _parse_explicit(text)
    resolution.notes.extend(notes)
    resolution.ambiguous = ambiguous
    if explicit is not None:
        resolution.as_of = explicit
        resolution.intent = TemporalIntent.AS_OF
        resolution.source = "explicit_date"
        resolution.confidence = "high"
        return resolution
    if ambiguous:
        return resolution

    # Relative expressions, resolved against the documented reference date.
    if _LAST_YEAR.search(text):
        resolution.as_of = date(reference.year - 1, 12, 31)
        resolution.intent = TemporalIntent.AS_OF
        resolution.source = "relative:last_year"
        resolution.confidence = "high"
        resolution.notes.append(f"'Last year' resolved to {resolution.as_of.isoformat()}.")
        return resolution
    if _LAST_QUARTER.search(text):
        resolution.as_of = previous_quarter_end(reference)
        resolution.intent = TemporalIntent.AS_OF
        resolution.source = "relative:last_quarter"
        resolution.confidence = "high"
        resolution.notes.append(
            f"'Last quarter' resolved to the quarter ending {resolution.as_of.isoformat()}."
        )
        return resolution
    if _LAST_MONTH.search(text):
        resolution.as_of = reference.replace(day=1) - timedelta(days=1)
        resolution.intent = TemporalIntent.AS_OF
        resolution.source = "relative:last_month"
        resolution.confidence = "high"
        resolution.notes.append(f"'Last month' resolved to {resolution.as_of.isoformat()}.")
        return resolution

    # A bare year names a period, not a point: "active during 2024" is answered
    # by the state at the end of that year, and the intent stays RANGE.
    year_match = _BARE_YEAR.search(text)
    if year_match:
        year = int(year_match["y"])
        resolution.as_of = date(year, 12, 31)
        resolution.intent = TemporalIntent.RANGE
        resolution.source = "period:year"
        resolution.confidence = "medium"
        resolution.notes.append(f"Only the year {year} was named; the state at 31 December {year} is used.")
        return resolution

    if _CURRENT_HINT.search(text):
        resolution.as_of = reference
        resolution.intent = TemporalIntent.CURRENT
        resolution.source = "reference_date"
        resolution.confidence = "high"
        resolution.notes.append(f"'Current' resolved to the reference date {resolution.as_of.isoformat()}.")
        return resolution

    # A period the rule-based planner already parsed.
    if date_from is not None and date_to is not None:
        resolution.as_of = date_to
        resolution.intent = TemporalIntent.RANGE
        resolution.source = "period"
        resolution.confidence = "medium"
        resolution.notes.append(
            f"The question names the period {date_from.isoformat()} to {date_to.isoformat()}; "
            "the state at the end of the period is used."
        )
        return resolution
    if year is not None:
        resolution.as_of = date(year, 12, 31)
        resolution.intent = TemporalIntent.RANGE
        resolution.source = "period:year"
        resolution.confidence = "medium"
        resolution.notes.append(f"The question names {year}; the state at 31 December {year} is used.")
        return resolution

    if requires_temporal or _AS_OF_HINT.search(text):
        resolution.notes.append(
            "The question is temporal but names no resolvable date; no as-of filter is applied."
        )
    return resolution


def _reference() -> date:
    from app.core.clock import today

    return today()


__all__ = [
    "REFERENCE_POLICY",
    "TIMEZONE",
    "TemporalIntent",
    "TemporalResolution",
    "derive_as_of",
    "end_of_month",
    "previous_quarter_end",
    "quarter_end",
]
