"""Cell-by-cell benchmark against expected gold JSON."""

from __future__ import annotations

from dataclasses import dataclass, field

from phaxtract.schema import Statement


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
