"""Portable metadata filter DSL.

The same filter document is accepted by the local vector store, the BM25 index
and translated to a Qdrant ``Filter`` — so authorization and metadata filtering
behave identically regardless of which backend is active::

    {"tenant_id": "ten_1", "document_type": {"$in": ["contract", "amendment"]},
     "effective_date": {"$lte": "2026-01-01"}}

Supported operators: ``$eq $ne $in $nin $gte $lte $gt $lt $exists $contains``.
Top level keys are AND-ed. ``$or`` takes a list of filter documents.
"""

from __future__ import annotations

from typing import Any

_OPERATORS = {"$eq", "$ne", "$in", "$nin", "$gte", "$lte", "$gt", "$lt", "$exists", "$contains"}

#: Fields the platform relies on for isolation/temporal logic; always exportable.
FILTERABLE_FIELDS = (
    "tenant_id",
    "supplier_id",
    "contract_id",
    "product_id",
    "document_id",
    "document_type",
    "category",
    "region",
    "version",
    "effective_date",
    "expiry_date",
    "access_level",
    "content_type",
    "is_synthetic",
)


def _as_comparable(value: Any) -> Any:
    return value.isoformat() if hasattr(value, "isoformat") else value


def _compare(left: Any, right: Any, op: str) -> bool:
    left, right = _as_comparable(left), _as_comparable(right)
    try:
        if op == "$gte":
            return left is not None and left >= right
        if op == "$lte":
            return left is not None and left <= right
        if op == "$gt":
            return left is not None and left > right
        if op == "$lt":
            return left is not None and left < right
    except TypeError:
        return False
    return False


def matches(payload: dict[str, Any], filters: dict[str, Any] | None) -> bool:
    """Evaluate ``filters`` against a stored payload."""
    if not filters:
        return True
    for key, expected in filters.items():
        if key == "$or":
            if not any(matches(payload, clause) for clause in expected):
                return False
            continue
        if key == "$and":
            if not all(matches(payload, clause) for clause in expected):
                return False
            continue
        if key not in _OPERATORS and key.startswith("$"):
            continue
        actual = payload.get(key)
        if isinstance(expected, dict) and set(expected) & _OPERATORS:
            for op, operand in expected.items():
                if op == "$eq" and _as_comparable(actual) != _as_comparable(operand):
                    return False
                if op == "$ne" and _as_comparable(actual) == _as_comparable(operand):
                    return False
                if op == "$in" and _as_comparable(actual) not in {_as_comparable(v) for v in operand}:
                    return False
                if op == "$nin" and _as_comparable(actual) in {_as_comparable(v) for v in operand}:
                    return False
                if op == "$exists" and bool(operand) != (actual is not None):
                    return False
                if op == "$contains":
                    if not isinstance(actual, (list, tuple, str)) or operand not in actual:
                        return False
                if op in {"$gte", "$lte", "$gt", "$lt"} and not _compare(actual, operand, op):
                    return False
            continue
        if _as_comparable(actual) != _as_comparable(expected):
            return False
    return True


def to_qdrant_filter(filters: dict[str, Any] | None) -> Any:
    """Translate the DSL into a ``qdrant_client`` Filter (import kept local)."""
    if not filters:
        return None
    from qdrant_client.http import models as qmodels

    conditions: list[Any] = []
    for key, expected in filters.items():
        if key == "$or":
            conditions.append(
                qmodels.Filter(should=[to_qdrant_filter(clause) for clause in expected if clause])
            )
            continue
        if isinstance(expected, dict) and set(expected) & _OPERATORS:
            for op, operand in expected.items():
                if op in {"$eq", "$gte", "$lte", "$gt", "$lt"}:
                    conditions.append(
                        qmodels.FieldCondition(
                            key=key,
                            range=qmodels.Range(**{_range_key(op): _as_comparable(operand)})
                            if op != "$eq"
                            else None,
                            match=qmodels.MatchValue(value=_as_comparable(operand)) if op == "$eq" else None,
                        )
                    )
                elif op in {"$in", "$nin"}:
                    conditions.append(
                        qmodels.FieldCondition(
                            key=key,
                            match=qmodels.MatchAny(any=[_as_comparable(v) for v in operand]),
                        )
                    )
                elif op == "$exists" and operand:
                    conditions.append(qmodels.IsNullCondition(is_null=qmodels.PayloadField(key=key)))
        else:
            conditions.append(
                qmodels.FieldCondition(key=key, match=qmodels.MatchValue(value=_as_comparable(expected)))
            )
    return qmodels.Filter(must=conditions) if conditions else None


def _range_key(op: str) -> str:
    return {"$gte": "gte", "$lte": "lte", "$gt": "gt", "$lt": "lt"}[op]
