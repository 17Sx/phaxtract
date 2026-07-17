"""Tests for validation and reconciliation."""

from phaxtract.validate import reconcile_quantities


def test_reconcile_matching_totals() -> None:
    quantities = [{"2026-01": 3, "2025-12": 3}, {"2026-01": 1, "2025-12": 0}]
    printed = {"2026-01": 4, "2025-12": 3}
    result = reconcile_quantities(quantities, printed)
    assert result.totals_reconciled is True
    assert result.flags == []


def test_reconcile_mismatch() -> None:
    quantities = [{"2026-01": 3}]
    printed = {"2026-01": 5}
    result = reconcile_quantities(quantities, printed)
    assert result.totals_reconciled is False
    assert len(result.flags) == 1
