"""Normalize months, column headers, and French numeric formats."""

from __future__ import annotations

import re

from phaxtract.config.loader import load_column_aliases, load_month_abbreviations

_FRENCH_DECIMAL = re.compile(r"[^\d,.\-]")
_YEAR_PATTERN = re.compile(r"(20\d{2})")


def normalize_column(header: str) -> str | None:
    aliases = load_column_aliases()
    return aliases.get(header.strip().lower())


def normalize_month(label: str, reference_year: int) -> str:
    """Convert a French month label to canonical YYYY-MM."""
    cleaned = label.strip().lower()
    year_match = _YEAR_PATTERN.search(cleaned)
    year = int(year_match.group(1)) if year_match else reference_year

    abbr = load_month_abbreviations()
    for token, month_num in abbr.items():
        if re.search(rf"\b{re.escape(token)}\b", cleaned):
            return f"{year}-{month_num}"

    msg = f"Unable to parse month label: {label!r}"
    raise ValueError(msg)


def parse_french_decimal(value: str) -> float:
    """Parse French-formatted numbers such as '1 234,56'."""
    cleaned = _FRENCH_DECIMAL.sub("", value.strip())
    cleaned = cleaned.replace(",", ".")
    return float(cleaned)
