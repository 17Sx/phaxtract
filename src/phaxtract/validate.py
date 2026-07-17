"""Validation and quantity reconciliation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping

from phaxtract.schema import Statement, ValidationResult


def reconcile_quantities(
    line_quantities: list[Mapping[str, int | float]],
    printed_totals: Mapping[str, int | float],
) -> ValidationResult:
    """Compare summed line quantities against printed document totals."""
    sums: dict[str, float] = defaultdict(float)
    for row in line_quantities:
        for month, qty in row.items():
            sums[month] += float(qty)

    flags: list[str] = []
    for month, expected in printed_totals.items():
        actual = sums.get(month, 0.0)
        if actual != float(expected):
            flags.append(f"month {month}: computed={actual}, printed={expected}")

    return ValidationResult(
        totals_reconciled=len(flags) == 0,
        row_count=len(line_quantities),
        flags=flags,
    )


def validate_statement(stmt: Statement) -> ValidationResult:
    """Run lightweight structural validation on a Statement."""
    flags: list[str] = []
    if not stmt.lines:
        flags.append("no product lines extracted")

    return ValidationResult(
        totals_reconciled=stmt.validation.totals_reconciled,
        row_count=len(stmt.lines),
        flags=flags,
    )
