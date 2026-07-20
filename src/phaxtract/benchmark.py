"""Cell-by-cell benchmark against expected gold JSON.

Beyond the single-document :func:`compare_statements`, this module also scores a
whole photo dataset: :func:`discover_pairs` finds each gold ``*.expected.json`` and
its source image, :func:`evaluate_photo_dataset` runs an extraction engine over the
pairs, and :func:`aggregate_reports` micro-averages the per-file results.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

from phaxtract.schema import Statement

if TYPE_CHECKING:
    from phaxtract.nuextract_engine import ExtractionEngine

_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".tif", ".tiff")


@dataclass
class CellDiff:
    path: str
    expected: object
    actual: object


@dataclass
class BenchmarkReport:
    cell_precision: float
    reconciled_rate: float
    diffs: list[CellDiff] = field(default_factory=list)
    cells_compared: int = 0
    cells_matched: int = 0


def _compare_quantities(
    expected: Statement,
    actual: Statement,
    diffs: list[CellDiff],
) -> tuple[int, int]:
    matched = 0
    compared = 0

    expected_by_code = {line.code_produit: line for line in expected.lines}
    for actual_line in actual.lines:
        exp_line = expected_by_code.get(actual_line.code_produit)
        if exp_line is None:
            diffs.append(
                CellDiff(
                    path=f"lines[{actual_line.code_produit}]",
                    expected="<missing>",
                    actual=actual_line.code_produit,
                )
            )
            continue

        all_months = set(exp_line.quantities) | set(actual_line.quantities)
        for month in sorted(all_months):
            compared += 1
            exp_val = exp_line.quantities.get(month)
            act_val = actual_line.quantities.get(month)
            if exp_val == act_val:
                matched += 1
            else:
                diffs.append(
                    CellDiff(
                        path=f"lines[{actual_line.code_produit}].quantities[{month}]",
                        expected=exp_val,
                        actual=act_val,
                    )
                )

    return matched, compared


def compare_statements(expected: Statement, actual: Statement) -> BenchmarkReport:
    diffs: list[CellDiff] = []
    matched, compared = _compare_quantities(expected, actual, diffs)

    precision = 1.0 if compared == 0 else matched / compared
    reconciled = (
        1.0
        if expected.validation.totals_reconciled == actual.validation.totals_reconciled
        else 0.0
    )

    return BenchmarkReport(
        cell_precision=precision,
        reconciled_rate=reconciled,
        diffs=diffs,
        cells_compared=compared,
        cells_matched=matched,
    )


@dataclass
class FileScore:
    """Per-file score inside a :class:`DatasetReport`."""

    name: str
    cell_precision: float
    cells_compared: int
    reconciled: bool


@dataclass
class DatasetReport:
    """Aggregate score over a photo dataset.

    ``cell_precision`` is micro-averaged (total matched cells / total compared
    cells), so files with more rows weigh more; ``reconciled_rate`` is the mean of
    the per-file reconciliation matches.
    """

    files_evaluated: int
    cells_compared: int
    cells_matched: int
    cell_precision: float
    reconciled_rate: float
    per_file: list[FileScore] = field(default_factory=list)


def aggregate_reports(named_reports: list[tuple[str, BenchmarkReport]]) -> DatasetReport:
    """Micro-average a list of ``(name, BenchmarkReport)`` into a dataset report."""
    cells_compared = sum(report.cells_compared for _, report in named_reports)
    cells_matched = sum(report.cells_matched for _, report in named_reports)
    precision = 1.0 if cells_compared == 0 else cells_matched / cells_compared
    reconciled_rate = (
        sum(report.reconciled_rate for _, report in named_reports) / len(named_reports)
        if named_reports
        else 0.0
    )
    per_file = [
        FileScore(
            name=name,
            cell_precision=report.cell_precision,
            cells_compared=report.cells_compared,
            reconciled=report.reconciled_rate == 1.0,
        )
        for name, report in named_reports
    ]
    return DatasetReport(
        files_evaluated=len(named_reports),
        cells_compared=cells_compared,
        cells_matched=cells_matched,
        cell_precision=precision,
        reconciled_rate=reconciled_rate,
        per_file=per_file,
    )


class PhotoPair(NamedTuple):
    """A gold image paired with its expected :class:`Statement`."""

    image: Path
    expected: Statement


def discover_pairs(converted_dir: Path, images_dir: Path) -> tuple[list[PhotoPair], list[str]]:
    """Pair each ``*.expected.json`` under ``converted_dir`` with an image by stem.

    Returns ``(pairs, unmatched)`` where ``unmatched`` lists the expected-file names
    that had no sibling image (case-insensitive extension match).
    """
    images_by_stem = {
        path.stem: path
        for path in sorted(images_dir.rglob("*"))
        if path.suffix.lower() in _IMAGE_EXTS
    }
    pairs: list[PhotoPair] = []
    unmatched: list[str] = []
    for expected_path in sorted(converted_dir.glob("*.expected.json")):
        stem = expected_path.name.removesuffix(".expected.json")
        image = images_by_stem.get(stem)
        if image is None:
            unmatched.append(expected_path.name)
            continue
        expected = Statement.model_validate(json.loads(expected_path.read_text(encoding="utf-8")))
        pairs.append(PhotoPair(image=image, expected=expected))
    return pairs, unmatched


def evaluate_photo_dataset(
    pairs: list[tuple[str | Path, Statement]],
    engine: ExtractionEngine,
    *,
    template: str | None = None,
) -> DatasetReport:
    """Run ``engine`` over each ``(image, expected)`` pair and aggregate the scores."""
    from phaxtract.extract_ai import extract_statement_from_image

    named_reports: list[tuple[str, BenchmarkReport]] = []
    for image, expected in pairs:
        actual = extract_statement_from_image(image, engine=engine, template=template)
        named_reports.append((Path(image).name, compare_statements(expected, actual)))
    return aggregate_reports(named_reports)
