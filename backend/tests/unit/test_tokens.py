"""Unit tests for app.ingestion.tokens — token counting and text utilities.

These tests have no I/O, no database, and no model dependencies.
"""

from __future__ import annotations

from app.ingestion.tokens import count_tokens, split_sentences, truncate_to_tokens


class TestCountTokens:
    def test_empty_string_returns_zero(self) -> None:
        assert count_tokens("") == 0

    def test_single_word(self) -> None:
        # "Hello" → 1 word × 1.3 ≈ 2, ceil(5/4) = 2 → max(2, 2, 1) = 2
        result = count_tokens("Hello")
        assert result >= 1

    def test_longer_text_increases_count(self) -> None:
        short = count_tokens("Hello")
        long = count_tokens("Hello world, this is a longer sentence with more words.")
        assert long > short

    def test_whitespace_only_returns_at_least_one(self) -> None:
        # Single spaces have no words but ceil(len/4) ≥ 1
        result = count_tokens("   ")
        assert result >= 1

    def test_approximately_four_chars_per_token(self) -> None:
        # 400 characters of text should produce roughly 100 tokens (±50%)
        text = "a" * 400
        result = count_tokens(text)
        assert 50 <= result <= 200

    def test_repeatable(self) -> None:
        text = "The price is $92 per unit under Amendment 2."
        assert count_tokens(text) == count_tokens(text)


class TestTruncateToTokens:
    def test_short_text_unchanged(self) -> None:
        text = "Short text."
        assert truncate_to_tokens(text, 1000) == text

    def test_empty_string(self) -> None:
        assert truncate_to_tokens("", 100) == ""

    def test_zero_max_tokens_returns_empty(self) -> None:
        assert truncate_to_tokens("some text", 0) == ""

    def test_truncation_reduces_token_count(self) -> None:
        long_text = " ".join(["word"] * 500)
        truncated = truncate_to_tokens(long_text, 50)
        assert count_tokens(truncated) <= count_tokens(long_text)
        assert len(truncated) < len(long_text)

    def test_result_is_non_empty_for_reasonable_input(self) -> None:
        text = "Supplier A agreed to a unit price of $92 effective January 2026."
        result = truncate_to_tokens(text, 20)
        assert len(result) > 0


class TestSplitSentences:
    def test_empty_string_returns_empty_list(self) -> None:
        assert split_sentences("") == []

    def test_single_sentence(self) -> None:
        result = split_sentences("The price is fixed.")
        assert len(result) >= 1
        assert "price" in result[0]

    def test_multiple_sentences_split(self) -> None:
        text = "The price is $92. This is valid from January 2026. Contact procurement."
        result = split_sentences(text)
        assert len(result) >= 2

    def test_no_trailing_empty_strings(self) -> None:
        text = "First sentence. Second sentence."
        result = split_sentences(text)
        assert all(s.strip() for s in result)
