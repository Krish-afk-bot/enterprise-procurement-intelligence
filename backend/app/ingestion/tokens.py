"""Token counting.

The platform does not depend on a specific tokenizer (the served model may change
without redeployment), so an explicit, documented approximation is used for chunk
budgets and cost telemetry: ~4 characters per token for English text, with a
word-count floor so whitespace-poor text is not under-counted.
"""

from __future__ import annotations

import math
import re

_WORD_RE = re.compile(r"\S+")


def count_tokens(text: str) -> int:
    """Approximate token count. Approximation is documented, not hidden."""
    if not text:
        return 0
    by_chars = math.ceil(len(text) / 4)
    by_words = int(len(_WORD_RE.findall(text)) * 1.3)
    return max(by_chars, by_words, 1)


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    if max_tokens <= 0 or not text:
        return ""
    if count_tokens(text) <= max_tokens:
        return text
    # ~4 chars per token, trimmed at a word/sentence boundary where possible.
    limit = max_tokens * 4
    clipped = text[:limit]
    for separator in ("\n", ". ", "; "):
        index = clipped.rfind(separator)
        if index > limit * 0.6:
            return clipped[: index + len(separator)].rstrip()
    return clipped.rstrip()


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?;:])\s+(?=[A-Z0-9(\"'])", text)
    return [part.strip() for part in parts if part.strip()]
