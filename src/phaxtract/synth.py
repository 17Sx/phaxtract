"""Render synthetic 'état des ventes' gold PDFs from a validated Statement."""

from __future__ import annotations

from phaxtract.config.loader import load_month_abbreviations


def month_column_label(month: str) -> str:
    """Return a French column label such as 'janv. 2026' for a 'YYYY-MM' code.

    The abbreviation is drawn from ``month_abbreviations.json`` (never hard-coded):
    among tokens mapping to the month, the longest one of at most four characters
    wins, so labels round-trip through :func:`phaxtract.normalize.normalize_month`.
    """
    year, num = month.split("-")
    best_token = ""
    best_key: tuple[bool, int, str] = (False, -1, "")
    for token, number in load_month_abbreviations().items():
        if number != num:
            continue
        key = (len(token) <= 4, len(token), token)
        if key > best_key:
            best_key, best_token = key, token
    if not best_token:
        msg = f"No abbreviation configured for month {month!r}"
        raise ValueError(msg)
    return f"{best_token}. {year}"
