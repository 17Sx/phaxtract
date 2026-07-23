"""Tests for normalization helpers."""

import pytest

from phaxtract.normalize import normalize_column, normalize_month, parse_french_decimal


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("jun", "2025-06"),
        ("Jun 2025", "2025-06"),
        ("déc", "2025-12"),
    ],
)
def test_normalize_month(raw: str, expected: str) -> None:
    assert normalize_month(raw, reference_year=2025) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1 234,56", 1234.56),
        ("-3,5", -3.5),
    ],
)
def test_parse_french_decimal(raw: str, expected: float) -> None:
    assert parse_french_decimal(raw) == expected


def test_normalize_column() -> None:
    assert normalize_column("Désignation") == "designation"


def test_normalize_column_period_headers() -> None:
    assert normalize_column("Date") == "date"
    assert normalize_column("Date de vente") == "date"
    assert normalize_column("Montant") == "amount"
    assert normalize_column("Qté") == "quantity"
