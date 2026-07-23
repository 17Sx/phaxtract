"""Tests for the synthetic gold PDF renderer."""

from __future__ import annotations

import json
from pathlib import Path

from phaxtract.schema import Statement

GOLD = Path(__file__).resolve().parents[2] / "gold" / "monthly_etat_des_ventes.expected.json"


def test_month_column_label_roundtrips_through_normalize() -> None:
    from phaxtract.normalize import normalize_month
    from phaxtract.synth import month_column_label

    label = month_column_label("2026-01")
    assert normalize_month(label, 2000) == "2026-01"


def test_render_statement_pdf_writes_a_pdf(tmp_path: Path) -> None:
    from phaxtract.synth import render_statement_pdf

    stmt = Statement.model_validate(json.loads(GOLD.read_text(encoding="utf-8")))
    out = render_statement_pdf(stmt, tmp_path / "monthly.pdf")
    assert out.exists()
    assert out.read_bytes()[:5] == b"%PDF-"
