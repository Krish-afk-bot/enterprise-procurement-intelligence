"""Temporal as-of derivation.

Pinned against a fixed reference date so the assertions do not depend on when the
suite runs. The cases mirror the questions the brief names, plus the failure
modes that matter more than the happy path: an ambiguous numeric date, a
temporal question with no anchor, and a version question that must not be turned
into a date filter.
"""

from __future__ import annotations

from datetime import date

from app.retrieval.temporal import (
    TemporalIntent,
    derive_as_of,
    end_of_month,
    previous_quarter_end,
)

REF = date(2026, 11, 12)


def resolve(question: str, **kwargs):
    return derive_as_of(question, reference=REF, **kwargs)


class TestExplicitDates:
    def test_iso_date(self) -> None:
        result = resolve("What was the contract status as of 2025-03-31?")
        assert result.as_of == date(2025, 3, 31)
        assert result.intent is TemporalIntent.AS_OF
        assert result.confidence == "high"

    def test_written_date(self) -> None:
        assert resolve("What was the contract status as of 31 March 2025?").as_of == date(2025, 3, 31)

    def test_month_and_year_resolves_to_month_end(self) -> None:
        result = resolve("Which amendment was effective in June 2025?")
        assert result.as_of == date(2025, 6, 30)
        assert any("Month precision" in note for note in result.notes)

    def test_unambiguous_numeric_date(self) -> None:
        assert resolve("as of 31/03/2025").as_of == date(2025, 3, 31)

    def test_ambiguous_numeric_date_is_not_guessed(self) -> None:
        result = resolve("as of 03/04/2025")
        assert result.as_of is None
        assert result.ambiguous is True


class TestRelativeDates:
    def test_last_year(self) -> None:
        assert resolve("Which supplier agreement was active last year?").as_of == date(2025, 12, 31)

    def test_last_quarter(self) -> None:
        # Reference 2026-11-12 sits in Q4; the previous quarter ended 30 September.
        assert resolve("What changed last quarter?").as_of == date(2026, 9, 30)

    def test_last_month(self) -> None:
        assert resolve("Which prices changed last month?").as_of == date(2026, 10, 31)

    def test_current_uses_reference_date(self) -> None:
        result = resolve("What are the current payment terms?")
        assert result.as_of == REF
        assert result.intent is TemporalIntent.CURRENT

    def test_helpers(self) -> None:
        assert end_of_month(2024, 2) == date(2024, 2, 29)
        assert previous_quarter_end(date(2026, 1, 15)) == date(2025, 12, 31)


class TestVersionQuestions:
    def test_original_terms_are_a_version_question(self) -> None:
        result = resolve("What were the original payment terms?")
        assert result.intent is TemporalIntent.ORIGINAL
        assert result.as_of is None

    def test_changes_after_an_amendment_use_recorded_dates(self) -> None:
        result = resolve("What terms changed after the second amendment?")
        assert result.intent is TemporalIntent.CHANGE
        assert result.as_of is None


class TestPeriodsAndDefaults:
    def test_year_question_uses_year_end(self) -> None:
        result = resolve("Which supplier agreement was active during 2024?")
        assert result.as_of == date(2024, 12, 31)
        assert result.intent is TemporalIntent.RANGE

    def test_parsed_period_uses_its_end(self) -> None:
        result = resolve(
            "What was in force?",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 12, 31),
        )
        assert result.as_of == date(2024, 12, 31)

    def test_temporal_question_without_an_anchor_is_not_invented(self) -> None:
        result = resolve("What changed when the contract was amended?", requires_temporal=True)
        assert result.as_of is None
        assert any("no resolvable date" in note for note in result.notes)

    def test_untemporal_question_has_no_as_of(self) -> None:
        result = resolve("Which supplier supplies laptops?")
        assert result.as_of is None
        assert result.intent is TemporalIntent.NONE
