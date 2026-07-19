"""Tests for the NuExtract output -> Statement mapping (the pure, GPU-free part)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from phaxtract.extract_ai import (
    extract_statement_from_image,
    nuextract_to_statement,
    parse_nuextract_output,
)
from phaxtract.nuextract_template import STATEMENT_TEMPLATE


def _raw(products: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {"products": products, **extra}


def test_template_mirrors_statement_shape() -> None:
    assert "products" in STATEMENT_TEMPLATE
    product = STATEMENT_TEMPLATE["products"][0]
    assert product["code_produit"] == "verbatim-string"
    assert product["sales"][0] == {"month": "date-time", "quantity": "integer"}


def test_spaced_code_is_normalized_and_quantities_aggregated() -> None:
    raw = _raw(
        [
            {
                "code_produit": "34009 22151014",
                "designation": "PRODUCT A",
                "sales": [{"month": "2026-05-01", "quantity": 4}],
            }
        ]
    )
    stmt = nuextract_to_statement(raw, "photo.jpg")
    line = stmt.lines[0]
    assert line.code_produit == "3400922151014"
    assert line.quantities == {"2026-05": 4}
    assert stmt.document.statement_type == "monthly"
    assert stmt.document.source_file == "photo.jpg"


def test_multiple_products_and_sorted_months() -> None:
    raw = _raw(
        [
            {
                "code_produit": "3614810004843",
                "designation": "A",
                "sales": [
                    {"month": "2026-01-01", "quantity": 3},
                    {"month": "2025-12-01", "quantity": 2},
                ],
            },
            {
                "code_produit": "5410765005533",
                "designation": "B",
                "sales": [{"month": "2026-01-01", "quantity": 1}],
            },
        ]
    )
    stmt = nuextract_to_statement(raw, "photo.jpg")
    assert stmt.document.months == ["2025-12", "2026-01"]
    assert len(stmt.lines) == 2


def test_invalid_code_is_skipped() -> None:
    raw = _raw(
        [
            {
                "code_produit": "5372381",
                "designation": "CIP7",
                "sales": [{"month": "2026-05-01", "quantity": 1}],
            },
            {
                "code_produit": "3614810004843",
                "designation": "OK",
                "sales": [{"month": "2026-05-01", "quantity": 2}],
            },
        ]
    )
    stmt = nuextract_to_statement(raw, "photo.jpg")
    assert [line.code_produit for line in stmt.lines] == ["3614810004843"]


def test_pharmacy_and_report_date_mapped() -> None:
    raw = _raw(
        [{"code_produit": "3614810004843", "designation": "A", "sales": []}],
        pharmacy={"name": "Pharmacie du Centre", "id": "FR-1"},
        report_date="2026-07-07",
    )
    stmt = nuextract_to_statement(raw, "photo.jpg")
    assert stmt.document.pharmacy.name == "Pharmacie du Centre"
    assert stmt.document.generated_at is not None
    assert stmt.document.generated_at.isoformat() == "2026-07-07"


def test_missing_or_messy_fields_do_not_crash() -> None:
    raw = _raw(
        [
            {"code_produit": "3614810004843"},  # no designation, no sales
            {"designation": "no code at all", "sales": [{"month": "2026-05-01", "quantity": 2}]},
        ]
    )
    stmt = nuextract_to_statement(raw, "photo.jpg")
    assert stmt.lines[0].code_produit == "3614810004843"
    assert stmt.lines[0].quantities == {}
    assert len(stmt.lines) == 1  # the code-less product is skipped


# --- parse_nuextract_output -------------------------------------------------


def test_parse_plain_json() -> None:
    assert parse_nuextract_output('{"products": []}') == {"products": []}


def test_parse_fenced_json() -> None:
    text = '```json\n{"supplier": "ACME"}\n```'
    assert parse_nuextract_output(text) == {"supplier": "ACME"}


def test_parse_json_with_trailing_prose() -> None:
    text = 'Here is the result:\n{"supplier": "ACME"}\nHope that helps.'
    assert parse_nuextract_output(text) == {"supplier": "ACME"}


def test_parse_malformed_returns_empty_dict() -> None:
    assert parse_nuextract_output("not json at all") == {}
    assert parse_nuextract_output("") == {}
    assert parse_nuextract_output("[1, 2, 3]") == {}  # JSON, but not an object


# --- extract_statement_from_image (orchestrator, fake engine) ---------------


class _FakeEngine:
    """Stand-in ExtractionEngine that returns canned NuExtract JSON, no GPU."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.calls: list[tuple[str, str]] = []

    def extract(self, image: str | Path, template: str) -> str:
        self.calls.append((str(image), template))
        return json.dumps(self._payload)


def test_extract_from_image_uses_engine_and_maps() -> None:
    engine = _FakeEngine(
        {
            "products": [
                {
                    "code_produit": "3614810004843",
                    "designation": "A",
                    "sales": [{"month": "2026-05-01", "quantity": 5}],
                }
            ]
        }
    )
    stmt = extract_statement_from_image("photo.jpg", engine=engine)
    assert stmt.lines[0].code_produit == "3614810004843"
    assert stmt.lines[0].quantities == {"2026-05": 5}
    # engine received the default template (json string of STATEMENT_TEMPLATE)
    _, template = engine.calls[0]
    assert json.loads(template) == STATEMENT_TEMPLATE


def test_extract_from_image_defaults_source_file_to_filename() -> None:
    engine = _FakeEngine({"products": []})
    stmt = extract_statement_from_image(Path("scans") / "etat_mai.png", engine=engine)
    assert stmt.document.source_file == "etat_mai.png"


def test_extract_from_image_respects_explicit_source_file() -> None:
    engine = _FakeEngine({"products": []})
    stmt = extract_statement_from_image("a.png", engine=engine, source_file="override.png")
    assert stmt.document.source_file == "override.png"
