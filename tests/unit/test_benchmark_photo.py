"""Tests for the NuExtract photo-dataset benchmark (aggregation, evaluation, pairing).

No GPU or model: evaluation runs against a fake engine, exactly like the extraction
orchestrator tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from phaxtract.benchmark import (
    BenchmarkReport,
    DatasetReport,
    PhotoPair,
    aggregate_reports,
    discover_pairs,
    evaluate_photo_dataset,
    filter_pairs_to_images,
)
from phaxtract.schema import Statement


def _expected_statement(code: str, month: str, qty: int) -> Statement:
    return Statement.model_validate(
        {
            "document": {
                "source_file": "gold.json",
                "lgo": "",
                "statement_type": "monthly",
                "pharmacy": {"name": ""},
                "months": [month],
            },
            "lines": [{"code_produit": code, "quantities": {month: qty}}],
            "validation": {"totals_reconciled": False, "row_count": 1},
        }
    )


class _FakeEngine:
    """Returns canned NuExtract JSON, keyed by image name, no model."""

    def __init__(self, by_image: dict[str, dict[str, Any]]) -> None:
        self._by_image = by_image

    def extract(self, image: str | Path, template: str) -> str:
        return json.dumps(self._by_image[Path(image).name])


# --- aggregate_reports ------------------------------------------------------


def test_aggregate_micro_precision() -> None:
    reports = [
        ("a.jpg", BenchmarkReport(cell_precision=1.0, reconciled_rate=1.0,
                                  cells_compared=3, cells_matched=3)),
        ("b.jpg", BenchmarkReport(cell_precision=0.5, reconciled_rate=0.0,
                                  cells_compared=2, cells_matched=1)),
    ]
    report = aggregate_reports(reports)
    assert isinstance(report, DatasetReport)
    assert report.files_evaluated == 2
    assert report.cells_compared == 5
    assert report.cells_matched == 4
    assert report.cell_precision == 4 / 5  # micro-average, not (1.0+0.5)/2
    assert report.reconciled_rate == 0.5


def test_aggregate_empty_is_safe() -> None:
    report = aggregate_reports([])
    assert report.files_evaluated == 0
    assert report.cell_precision == 1.0
    assert report.reconciled_rate == 0.0
    assert report.per_file == []


def test_aggregate_keeps_per_file_scores() -> None:
    reports = [
        ("a.jpg", BenchmarkReport(cell_precision=0.5, reconciled_rate=1.0,
                                  cells_compared=2, cells_matched=1)),
    ]
    report = aggregate_reports(reports)
    assert report.per_file[0].name == "a.jpg"
    assert report.per_file[0].cell_precision == 0.5
    assert report.per_file[0].cells_compared == 2
    assert report.per_file[0].reconciled is True


# --- evaluate_photo_dataset -------------------------------------------------


def test_evaluate_perfect_match() -> None:
    expected = _expected_statement("3614810004843", "2026-05", 5)
    engine = _FakeEngine(
        {
            "photo.jpg": {
                "products": [
                    {
                        "code_produit": "3614810004843",
                        "designation": "A",
                        "sales": [{"month": "2026-05-01", "quantity": 5}],
                    }
                ]
            }
        }
    )
    report = evaluate_photo_dataset([("photo.jpg", expected)], engine)
    assert report.files_evaluated == 1
    assert report.cell_precision == 1.0


def test_evaluate_detects_wrong_quantity() -> None:
    expected = _expected_statement("3614810004843", "2026-05", 5)
    engine = _FakeEngine(
        {
            "photo.jpg": {
                "products": [
                    {
                        "code_produit": "3614810004843",
                        "designation": "A",
                        "sales": [{"month": "2026-05-01", "quantity": 99}],
                    }
                ]
            }
        }
    )
    report = evaluate_photo_dataset([("photo.jpg", expected)], engine)
    assert report.cell_precision == 0.0


# --- discover_pairs ---------------------------------------------------------


def test_discover_pairs_matches_by_stem(tmp_path: Path) -> None:
    converted = tmp_path / "converted"
    images = tmp_path / "images"
    converted.mkdir()
    images.mkdir()
    (converted / "foo.expected.json").write_text(
        _expected_statement("3614810004843", "2026-05", 1).model_dump_json(),
        encoding="utf-8",
    )
    (images / "foo.jpg").write_bytes(b"img")

    pairs, unmatched = discover_pairs(converted, images)

    assert unmatched == []
    assert len(pairs) == 1
    assert pairs[0].image.name == "foo.jpg"
    assert pairs[0].expected.lines[0].code_produit == "3614810004843"


def test_discover_pairs_matches_trailing_digit_suffix(tmp_path: Path) -> None:
    # Real gold: converted stem is `X`, the image adds a trailing `_<digits>` frame id.
    converted = tmp_path / "converted"
    images = tmp_path / "images"
    converted.mkdir()
    images.mkdir()
    base = "136_310004022_250909_250909_021744"
    (converted / f"{base}.expected.json").write_text(
        _expected_statement("3614810004843", "2026-05", 1).model_dump_json(),
        encoding="utf-8",
    )
    (images / f"{base}_601.JPG").write_bytes(b"img")

    pairs, unmatched = discover_pairs(converted, images)

    assert unmatched == []
    assert len(pairs) == 1
    assert pairs[0].image.name == f"{base}_601.JPG"


def test_discover_pairs_does_not_cross_match_different_ids(tmp_path: Path) -> None:
    # A different record must NOT be paired just because both are numeric.
    converted = tmp_path / "converted"
    images = tmp_path / "images"
    converted.mkdir()
    images.mkdir()
    (converted / "20_110000480_251023_251027_040543.expected.json").write_text(
        _expected_statement("3614810004843", "2026-05", 1).model_dump_json(),
        encoding="utf-8",
    )
    (images / "20_110000705_250114_250115_120740_495.JPG").write_bytes(b"img")

    pairs, unmatched = discover_pairs(converted, images)

    assert pairs == []
    assert unmatched == ["20_110000480_251023_251027_040543.expected.json"]


def test_filter_pairs_to_images_keeps_only_named(tmp_path: Path) -> None:
    expected = _expected_statement("3614810004843", "2026-05", 1)
    pairs = [
        PhotoPair(image=Path("dir/a.jpg"), expected=expected),
        PhotoPair(image=Path("dir/b.png"), expected=expected),
        PhotoPair(image=Path("dir/c.JPG"), expected=expected),
    ]
    kept = filter_pairs_to_images(pairs, {"a.jpg", "c.JPG"})
    assert [p.image.name for p in kept] == ["a.jpg", "c.JPG"]


def test_discover_pairs_reports_unmatched(tmp_path: Path) -> None:
    converted = tmp_path / "converted"
    images = tmp_path / "images"
    converted.mkdir()
    images.mkdir()
    (converted / "orphan.expected.json").write_text(
        _expected_statement("3614810004843", "2026-05", 1).model_dump_json(),
        encoding="utf-8",
    )

    pairs, unmatched = discover_pairs(converted, images)

    assert pairs == []
    assert unmatched == ["orphan.expected.json"]
