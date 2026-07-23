"""Tests for the file-type extraction dispatcher."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from phaxtract.pipeline import extract_statement
from phaxtract.schema import Statement
from phaxtract.synth import render_statement_pdf

GOLD_DIR = Path(__file__).resolve().parents[2] / "gold"


def test_extract_statement_routes_pdf_to_native(tmp_path: Path) -> None:
    expected = Statement.model_validate(
        json.loads((GOLD_DIR / "monthly_etat_des_ventes.expected.json").read_text("utf-8"))
    )
    pdf = render_statement_pdf(expected, tmp_path / "m.pdf")
    stmt = extract_statement(pdf)
    assert stmt.document.statement_type == "monthly"
    assert stmt.lines


def test_extract_statement_rejects_unknown_suffix(tmp_path: Path) -> None:
    junk = tmp_path / "x.txt"
    junk.write_text("nope", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported"):
        extract_statement(junk)
