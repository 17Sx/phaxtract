"""Command-line interface for phaxtract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from phaxtract.benchmark import compare_statements
from phaxtract.config.loader import load_lgo_config
from phaxtract.schema import Statement

app = typer.Typer(
    name="phaxtract",
    help="Extract pharmacy sales statements to structured JSON — locally, for free.",
    no_args_is_help=True,
)
console = Console()


@app.command("validate-config")
def validate_config() -> None:
    """Validate embedded JSON business-rule configs."""
    config = load_lgo_config()
    console.print(f"[green]OK[/green] — {len(config.lgos)} LGO fingerprint(s) loaded")


@app.command("benchmark")
def benchmark(
    expected: Annotated[Path, typer.Argument(help="Path to expected .json gold file")],
    actual: Annotated[Path, typer.Argument(help="Path to actual extraction .json")],
) -> None:
    """Compare an extraction result against expected gold JSON."""
    expected_stmt = Statement.model_validate(json.loads(expected.read_text(encoding="utf-8")))
    actual_stmt = Statement.model_validate(json.loads(actual.read_text(encoding="utf-8")))
    report = compare_statements(expected_stmt, actual_stmt)

    table = Table(title="Benchmark Report")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Cell precision", f"{report.cell_precision:.2%}")
    table.add_row("Reconciliation match", f"{report.reconciled_rate:.2%}")
    table.add_row("Cells compared", str(report.cells_compared))
    table.add_row("Diffs", str(len(report.diffs)))
    console.print(table)

    if report.diffs:
        for diff in report.diffs[:10]:
            console.print(f"  [yellow]{diff.path}[/yellow]: {diff.expected!r} → {diff.actual!r}")
        if len(report.diffs) > 10:
            console.print(f"  … and {len(report.diffs) - 10} more")


if __name__ == "__main__":
    app()
