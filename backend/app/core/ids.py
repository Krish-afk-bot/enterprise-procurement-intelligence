"""Identifier and hashing helpers."""

from __future__ import annotations

import hashlib
import re
import unicodedata
import uuid


def new_id(prefix: str | None = None) -> str:
    raw = uuid.uuid4().hex
    return f"{prefix}_{raw}" if prefix else raw


def sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_hex(text.encode("utf-8"))


def normalize_name(value: str | None) -> str:
    """Normalize a supplier/product name for matching and BM25 keys."""
    if not value:
        return ""
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"\b(inc|llc|ltd|limited|gmbh|plc|corp|corporation|company|co)\b\.?", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "item"
