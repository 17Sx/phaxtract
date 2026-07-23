"""End-to-end round-trip: render a gold Statement to PDF, extract, compare exact."""

from __future__ import annotations

import json
from pathlib import Path

from phaxtract.benchmark import compare_statements
from phaxtract.extract_native import extract_statement_from_pdf
from phaxtract.schema import Statement
from phaxtract.synth import render_statement_pdf

GOLD_DIR = Path(__file__).resolve().parents[2] / "gold"


def _roundtrip(name: str, tmp_path: Path) -> None:
    expected = Statement.model_validate(
        json.loads((GOLD_DIR / f"{name}.expected.json").read_text(encoding="utf-8"))
    )
    pdf = render_statement_pdf(expected, tmp_path / f"{name}.pdf")
    actual = extract_statement_from_pdf(pdf)
    report = compare_statements(expected, actual)
    assert report.cell_precision == 1.0, report.diffs
    assert report.reconciled_rate == 1.0
    assert report.cells_compared > 0


def test_monthly_roundtrip_is_exact(tmp_path: Path) -> None:
    _roundtrip("monthly_etat_des_ventes", tmp_path)
