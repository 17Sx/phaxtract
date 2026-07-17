"""Tests for synthetic gold PDF rendering."""

from __future__ import annotations

import json
from pathlib import Path

import fitz

from phaxtract.fingerprint import identify_lgo
from phaxtract.normalize import normalize_month
from phaxtract.schema import Statement
from phaxtract.synth import (
    month_column_label,
    render_expected_file,
    render_statement_pdf,
)


def _extract_text(pdf_path: Path) -> str:
    doc = fitz.open(pdf_path)
    try:
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()


def test_month_column_label_round_trips_through_normalize() -> None:
    label = month_column_label("2026-01")
    assert label == "janv. 2026"
    assert normalize_month(label, reference_year=2000) == "2026-01"


def test_month_column_label_december_keeps_accent() -> None:
    label = month_column_label("2025-12")
    assert label.startswith("déc")
    assert normalize_month(label, reference_year=2000) == "2025-12"


def test_render_statement_pdf_round_trips(
    sample_statement_data: dict, tmp_path: Path
) -> None:
    stmt = Statement.model_validate(sample_statement_data)
    out = render_statement_pdf(stmt, tmp_path / "gold.pdf")

    assert out.read_bytes().startswith(b"%PDF")
    text = _extract_text(out)

    # LGO signature is recognisable by the deterministic layer
    assert identify_lgo(text) == "etat_des_ventes"
    # every product EAN is present
    for line in stmt.lines:
        assert line.code_produit in text
    # month columns round-trip and a TOTAL row exists
    assert "janv. 2026" in text
    assert "déc. 2025" in text
    assert "TOTAL" in text


def test_render_expected_file_names_output_from_stem(
    sample_statement_data: dict, tmp_path: Path
) -> None:
    expected = tmp_path / "monthly_etat_des_ventes.expected.json"
    expected.write_text(json.dumps(sample_statement_data), encoding="utf-8")
    out_dir = tmp_path / "out"

    result = render_expected_file(expected, out_dir)

    assert result == out_dir / "monthly_etat_des_ventes.pdf"
    assert result.read_bytes().startswith(b"%PDF")
