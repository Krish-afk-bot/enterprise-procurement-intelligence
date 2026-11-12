"""Temporal validity of graph edges.

Versions are stored, not overwritten, so traversal has to be able to ask what was
in force on a given date. These tests pin the boundary behaviour: an edge with no
dates stays visible (unknown is not expired), an edge outside its window is
hidden, and a badly formatted date is an error rather than a silent "show all".
"""

from __future__ import annotations

from datetime import date

import pytest

from app.providers.graph.temporal import edge_valid_at, normalise_as_of


class TestNormalise:
    def test_missing_value_is_open_ended(self) -> None:
        assert normalise_as_of(None) is None
        assert normalise_as_of("") is None

    def test_iso_string_is_accepted(self) -> None:
        assert normalise_as_of("2024-03-31") == "2024-03-31"

    def test_timestamp_is_truncated_to_the_day(self) -> None:
        assert normalise_as_of("2024-03-31T14:22:00Z") == "2024-03-31"

    def test_date_object_is_accepted(self) -> None:
        assert normalise_as_of(date(2024, 3, 31)) == "2024-03-31"

    def test_garbage_raises(self) -> None:
        with pytest.raises(ValueError, match="ISO date"):
            normalise_as_of("March 2024")


class TestEdgeValidity:
    def test_no_as_of_keeps_everything(self) -> None:
        assert edge_valid_at({"effective_date": "2024-01-01", "expiry_date": "2024-02-01"}, None)

    def test_dates_are_ignored_when_absent(self) -> None:
        assert edge_valid_at({}, "2024-06-01")
        assert edge_valid_at(None, "2024-06-01")

    def test_edge_inside_its_window_is_valid(self) -> None:
        props = {"effective_date": "2024-01-01", "expiry_date": "2024-12-31"}
        assert edge_valid_at(props, "2024-06-01")

    def test_edge_not_yet_effective_is_hidden(self) -> None:
        assert not edge_valid_at({"effective_date": "2024-07-01"}, "2024-06-30")

    def test_superseded_edge_is_hidden(self) -> None:
        assert not edge_valid_at({"expiry_date": "2024-05-31"}, "2024-06-01")

    def test_boundary_days_are_inclusive(self) -> None:
        props = {"effective_date": "2024-01-01", "expiry_date": "2024-12-31"}
        assert edge_valid_at(props, "2024-01-01")
        assert edge_valid_at(props, "2024-12-31")

    def test_open_ended_start_is_valid_before_expiry(self) -> None:
        assert edge_valid_at({"expiry_date": "2030-01-01"}, "2024-06-01")
