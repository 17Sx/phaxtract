"""Tests for the Doc AI -> Statement converter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from phaxtract.convert_docai import convert_docai_file, docai_to_statement
from phaxtract.schema import Statement


def _product_line(ean: str, designation: str, months: dict[str, int]) -> dict[str, Any]:
    props: list[dict[str, Any]] = [
        {"type": "product_designation", "mentionText": designation},
        {"type": "product_ean", "mentionText": ean},
    ]
    for day, qty in months.items():
        props.append(
            {
                "type": "sales_by_month",
                "properties": [
                    {"type": "month_period_normalized", "normalizedValue": {"text": day}},
                    {"type": "sales_quantity", "normalizedValue": {"text": str(qty)}},
                ],
            }
        )
    return {"type": "product_line", "confidence": 1.0, "properties": props}


def _docai(entities: list[dict[str, Any]], text: str = "ETAT DES VENTES") -> dict[str, Any]:
    return {"text": text, "entities": entities}


def test_spaced_ean_is_normalized_and_kept() -> None:
    docai = _docai([_product_line("34009 22151014", "PRODUCT A", {"2026-05-01": 4})])
    result = docai_to_statement(docai, "doc.json")
    assert result.skipped == []
    line = result.statement.lines[0]
    assert line.code_produit == "3400922151014"
    assert line.quantities == {"2026-05": 4}


def test_multi_month_line_and_sorted_months() -> None:
    docai = _docai(
        [_product_line("3614810004843", "A", {"2026-01-01": 3, "2025-12-01": 2})]
    )
    result = docai_to_statement(docai, "doc.json")
    assert result.statement.document.months == ["2025-12", "2026-01"]
    assert result.statement.lines[0].quantities == {"2026-01": 3, "2025-12": 2}


def test_residual_code_is_skipped_and_reported() -> None:
    docai = _docai([_product_line("5372381", "CIP7 PRODUCT", {"2026-05-01": 1})])
    result = docai_to_statement(docai, "doc.json")
    assert result.statement.lines == []
    assert len(result.skipped) == 1
    assert result.skipped[0].raw_code == "5372381"


def test_report_date_and_lgo_and_type() -> None:
    docai = _docai(
        [
            {"type": "report_date", "normalizedValue": {"text": "2026-07-07"}},
            _product_line("3614810004843", "A", {"2026-05-01": 1}),
        ]
    )
    result = docai_to_statement(docai, "doc.json")
    doc = result.statement.document
    assert doc.generated_at is not None and doc.generated_at.isoformat() == "2026-07-07"
    assert doc.lgo == "etat_des_ventes"
    assert doc.statement_type == "monthly"
    assert doc.source_file == "doc.json"


def _total_line(months: dict[str, int]) -> dict[str, Any]:
    props = []
    for day, qty in months.items():
        props.append(
            {
                "type": "sales_by_month",
                "properties": [
                    {"type": "month_period_normalized", "normalizedValue": {"text": day}},
                    {"type": "sales_quantity", "normalizedValue": {"text": str(qty)}},
                ],
            }
        )
    return {"type": "total_line", "properties": props}


def test_reconciles_against_total_line() -> None:
    docai = _docai(
        [
            _product_line("3614810004843", "A", {"2026-05-01": 4}),
            _product_line("5410765005533", "B", {"2026-05-01": 1}),
            _total_line({"2026-05-01": 5}),
        ]
    )
    result = docai_to_statement(docai, "doc.json")
    assert result.statement.validation.totals_reconciled is True


def test_no_total_line_leaves_reconciled_false() -> None:
    docai = _docai([_product_line("3614810004843", "A", {"2026-05-01": 4})])
    result = docai_to_statement(docai, "doc.json")
    assert result.statement.validation.totals_reconciled is False


def test_convert_docai_file_writes_reloadable_gold(tmp_path: Path) -> None:
    docai = _docai(
        [
            {"type": "report_date", "normalizedValue": {"text": "2026-07-07"}},
            _product_line("34009 22151014", "PRODUCT A", {"2026-05-01": 4}),
        ]
    )
    src = tmp_path / "listing_x.json"
    src.write_text(json.dumps(docai), encoding="utf-8")
    out_dir = tmp_path / "converted"

    out_path, result = convert_docai_file(src, out_dir)

    assert out_path == out_dir / "listing_x.expected.json"
    reloaded = Statement.model_validate(json.loads(out_path.read_text(encoding="utf-8")))
    assert reloaded.lines[0].code_produit == "3400922151014"
    assert result.skipped == []
