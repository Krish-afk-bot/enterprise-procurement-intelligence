"""Retrieval and answer metrics.

Every metric is computed from the run's own outputs:

* retrieval metrics compare the retrieved documents/pages with the labelled
  ground truth (``expected_documents`` / ``expected_pages``);
* answer metrics check that the literal ground-truth strings appear in the
  answer (``expected_keywords``), that citations were verified, and that
  unanswerable questions were refused.

Unavailable metrics are returned as ``None`` and reported as such — never as 0
or 1, which would look like a measurement.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from typing import Any


def _unique(values: Sequence[str]) -> list[str]:
    seen: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in seen:
            seen.append(text)
    return seen


def _match(expected: str, actual: Sequence[str]) -> bool:
    needle = expected.lower()
    return any(needle == candidate.lower() or needle in candidate.lower() for candidate in actual)


def recall_at_k(retrieved: Sequence[str], expected: Sequence[str], k: int | None = None) -> float | None:
    """Fraction of the labelled sources that were retrieved."""
    if not expected:
        return None
    pool = _unique(retrieved[:k] if k else retrieved)
    hits = sum(1 for item in expected if _match(item, pool))
    return round(hits / len(expected), 4)


def precision_at_k(retrieved: Sequence[str], expected: Sequence[str], k: int) -> float | None:
    """Fraction of the top-k retrieved sources that are labelled as relevant."""
    if not expected:
        return None
    pool = _unique(retrieved[:k])
    if not pool:
        return 0.0
    hits = sum(1 for item in pool if _match(item, expected))
    return round(hits / len(pool), 4)


def reciprocal_rank(retrieved: Sequence[str], expected: Sequence[str]) -> float | None:
    """1/rank of the first labelled source in the ranking."""
    if not expected:
        return None
    for index, item in enumerate(_unique(retrieved), start=1):
        if _match(item, expected):
            return round(1.0 / index, 4)
    return 0.0


def ndcg_at_k(retrieved: Sequence[str], expected: Sequence[str], k: int = 10) -> float | None:
    """Binary-relevance nDCG over the retrieved ranking."""
    if not expected:
        return None
    pool = _unique(retrieved[:k])
    dcg = 0.0
    for index, item in enumerate(pool, start=1):
        if _match(item, expected):
            dcg += 1.0 / math.log2(index + 1)
    ideal_hits = min(len(expected), k)
    idcg = sum(1.0 / math.log2(index + 1) for index in range(1, ideal_hits + 1))
    if idcg == 0:
        return None
    return round(dcg / idcg, 4)


def page_coverage(retrieved_pages: Sequence[int], expected_pages: Sequence[int]) -> float | None:
    if not expected_pages:
        return None
    pool = {int(value) for value in retrieved_pages}
    hits = sum(1 for page in expected_pages if int(page) in pool)
    return round(hits / len(expected_pages), 4)


def answer_keywords(answer_text: str, keywords: Sequence[str]) -> dict[str, Any]:
    """Which ground-truth strings the answer actually contains."""
    lowered = (answer_text or "").lower()
    found = [keyword for keyword in keywords if keyword.lower() in lowered]
    missing = [keyword for keyword in keywords if keyword.lower() not in lowered]
    coverage = round(len(found) / len(keywords), 4) if keywords else None
    return {"found": found, "missing": missing, "coverage": coverage}


def answered_expected(answer_text: str, keywords: Sequence[str], minimum_hits: int) -> bool | None:
    if not keywords:
        return None
    return len(answer_keywords(answer_text, keywords)["found"]) >= max(1, minimum_hits)


def citation_validity(validation: dict[str, Any] | None) -> float | None:
    """Share of displayed citations that passed verification."""
    validation = validation or {}
    valid = int(validation.get("valid_citations") or 0)
    invalid = int(validation.get("invalid_citations") or 0)
    if valid + invalid == 0:
        return None
    return round(valid / (valid + invalid), 4)


def refusal_correct(is_unanswerable: bool, status: str | None, refusal_triggered: bool) -> bool:
    """A refusal is correct for an unanswerable question and wrong otherwise."""
    refused = bool(refusal_triggered) or status == "insufficient_evidence"
    return refused if is_unanswerable else not refused


def hallucinated_numbers(answer_text: str, numbers_checked: dict[str, Any] | None) -> int:
    """Numeric values in the answer that the grounding judge could not find."""
    details = (numbers_checked or {}).get("missing_numbers") or []
    return len(details)


def _metric(row: dict[str, Any], key: str) -> Any:
    """A metric may live at the top of the row or inside its ``metrics`` payload."""
    if key in row:
        return row[key]
    return (row.get("metrics") or {}).get(key)


def aggregate(rows: list[dict[str, Any]], keys: Sequence[str]) -> dict[str, Any]:
    """Mean of each metric across rows, ignoring rows where it is unavailable.

    A metric that is unavailable for a question (``None``) is excluded from the
    mean and counted separately in ``<key>_n``, so an aggregate never silently
    treats a missing measurement as a zero.
    """
    summary: dict[str, Any] = {}
    for key in keys:
        values = [value for row in rows if (value := _metric(row, key)) is not None]
        numeric = [float(value) for value in values if isinstance(value, (int, float, bool))]
        summary[key] = round(sum(numeric) / len(numeric), 4) if numeric else None
        summary[f"{key}_n"] = len(numeric)
    return summary


def word_overlap(answer_text: str, expected_answer: str | None) -> float | None:
    """Token F1 against the reference answer (diagnostic, not a headline metric)."""
    if not expected_answer:
        return None
    tokens = lambda text: {token for token in re.findall(r"[a-z0-9.\-]+", text.lower()) if len(token) > 2}  # noqa: E731
    reference = tokens(expected_answer)
    produced = tokens(answer_text or "")
    if not reference or not produced:
        return 0.0
    overlap = reference & produced
    if not overlap:
        return 0.0
    precision = len(overlap) / len(produced)
    recall = len(overlap) / len(reference)
    return round(2 * precision * recall / (precision + recall), 4)
