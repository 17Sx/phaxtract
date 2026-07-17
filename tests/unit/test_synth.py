"""Tests for synthetic gold PDF rendering."""

from __future__ import annotations

from phaxtract.normalize import normalize_month
from phaxtract.synth import month_column_label


def test_month_column_label_round_trips_through_normalize() -> None:
    label = month_column_label("2026-01")
    assert label == "janv. 2026"
    assert normalize_month(label, reference_year=2000) == "2026-01"


def test_month_column_label_december_keeps_accent() -> None:
    label = month_column_label("2025-12")
    assert label.startswith("déc")
    assert normalize_month(label, reference_year=2000) == "2025-12"
