"""Tests for benchmark engine."""

from phaxtract.benchmark import compare_statements
from phaxtract.schema import Statement


def test_benchmark_perfect_match(sample_statement_data: dict) -> None:
    stmt = Statement.model_validate(sample_statement_data)
    report = compare_statements(stmt, stmt)
    assert report.cell_precision == 1.0
    assert report.reconciled_rate == 1.0


def test_benchmark_detects_diff(sample_statement_data: dict) -> None:
    expected = Statement.model_validate(sample_statement_data)
    actual_data = sample_statement_data.copy()
    actual_data["lines"] = [
        {
            **sample_statement_data["lines"][0],
            "quantities": {"2026-01": 99, "2025-12": 3},
        }
    ]
    actual = Statement.model_validate(actual_data)
    report = compare_statements(expected, actual)
    assert report.cell_precision < 1.0
    assert len(report.diffs) >= 1
