"""Tests for the native PDF pure mapping (no pdfplumber import)."""

from __future__ import annotations

from phaxtract.extract_native import (
    RawPage,
    assemble_monthly,
    detect_statement_type,
    native_to_statement,
)

MONTHLY_HEADER = [
    "Code EAN",
    "Désignation",
    "PA cat",
    "PA cat net",
    "PV TTC",
    "janv. 2026",
    "déc. 2025",
]


def test_detect_statement_type_monthly() -> None:
    assert detect_statement_type(MONTHLY_HEADER) == "monthly"


def test_assemble_monthly_builds_lines_and_totals() -> None:
    rows = [
        ["3614810004843", "Product A", "32,00", "20,48", "49,95", "3", "3"],
        ["3400930000000", "Product B", "15,00", "9,60", "22,50", "1", "0"],
        ["", "TOTAL", "", "", "", "4", "3"],
    ]
    lines, printed = assemble_monthly(MONTHLY_HEADER, rows, reference_year=2000)

    assert [ln.code_produit for ln in lines] == ["3614810004843", "3400930000000"]
    assert lines[0].quantities == {"2026-01": 3, "2025-12": 3}
    assert lines[0].prices.pa_cat == 32.0
    assert printed == {"2026-01": 4, "2025-12": 3}


def test_native_to_statement_reconciles_monthly() -> None:
    rows = [
        ["3614810004843", "Product A", "", "", "", "3", "3"],
        ["3400930000000", "Product B", "", "", "", "1", "0"],
        ["", "TOTAL", "", "", "", "4", "3"],
    ]
    page = RawPage(tables=[[MONTHLY_HEADER, *rows]], text="ETAT DES VENTES\nPharma Test")
    stmt = native_to_statement([page], "x.pdf")

    assert stmt.document.statement_type == "monthly"
    assert stmt.document.lgo == "etat_des_ventes"
    assert stmt.validation.totals_reconciled is True
    assert stmt.validation.row_count == 2


PERIOD_HEADER = ["Code EAN", "Désignation", "Date", "Qté", "Montant"]


def test_detect_statement_type_period() -> None:
    assert detect_statement_type(PERIOD_HEADER) == "period"


def test_assemble_period_groups_transactions_by_product_and_month() -> None:
    from phaxtract.extract_native import assemble_period

    rows = [
        ["3614810004843", "Product A", "2026-01-05", "2", "40,00"],
        ["3614810004843", "Product A", "2026-01-20", "1", "20,00"],
        ["3400930000000", "Product B", "2025-12-11", "3", "30,00"],
    ]
    lines = assemble_period(PERIOD_HEADER, rows)

    assert [ln.code_produit for ln in lines] == ["3614810004843", "3400930000000"]
    assert lines[0].quantities == {"2026-01": 3}
    assert lines[1].quantities == {"2025-12": 3}


def test_native_to_statement_flags_mismatched_totals() -> None:
    rows = [
        ["3614810004843", "Product A", "", "", "", "3", "3"],
        ["", "TOTAL", "", "", "", "9", "9"],
    ]
    page = RawPage(tables=[[MONTHLY_HEADER, *rows]], text="ETAT DES VENTES")
    stmt = native_to_statement([page], "x.pdf")

    assert stmt.validation.totals_reconciled is False
    assert stmt.validation.flags
