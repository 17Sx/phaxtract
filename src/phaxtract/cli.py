"""Command-line interface for phaxtract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from phaxtract.benchmark import compare_statements
from phaxtract.config.loader import load_lgo_config
from phaxtract.extract_ai import extract_statement_from_image
from phaxtract.nuextract_engine import ExtractionDependencyError, NuExtractEngine
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


@app.command("extract")
def extract(
    image: Annotated[
        Path, typer.Argument(exists=True, dir_okay=False, help="Photo/scan to extract")
    ],
    out: Annotated[
        Path | None,
        typer.Option("--out", "-o", help="Write the Statement JSON here (default: stdout)"),
    ] = None,
    model: Annotated[
        str, typer.Option("--model", help="NuExtract HuggingFace model id")
    ] = "numind/NuExtract3",
    adapter: Annotated[
        str | None,
        typer.Option("--adapter", help="Path to a trained LoRA adapter to apply"),
    ] = None,
    four_bit: Annotated[
        bool,
        typer.Option("--4bit", help="Load the model 4-bit quantized (fits a 12 GB GPU)"),
    ] = False,
    thinking: Annotated[
        bool,
        typer.Option("--thinking", help="Enable NuExtract reasoning (better on dense tables)"),
    ] = False,
    max_pixels: Annotated[
        int | None,
        typer.Option("--max-pixels", help="Cap input image resolution (width x height)"),
    ] = None,
    max_new_tokens: Annotated[
        int,
        typer.Option("--max-new-tokens", help="Generation token budget (raise for thinking)"),
    ] = 4096,
    pretty: Annotated[bool, typer.Option("--pretty", help="Indent the JSON output")] = False,
) -> None:
    """Extract a pharmacy statement from a photo/scan via NuExtract.

    Requires the optional AI dependencies (the "ai" extra); see the README.
    """
    engine = NuExtractEngine(
        model_id=model,
        adapter_path=adapter,
        load_in_4bit=four_bit,
        thinking=thinking,
        max_pixels=max_pixels,
        max_new_tokens=max_new_tokens,
    )
    try:
        statement = extract_statement_from_image(image, engine=engine)
    except ExtractionDependencyError as exc:
        console.print(f"[red]Error[/red] — {escape(str(exc))}")
        raise typer.Exit(code=1) from exc

    payload = statement.model_dump_json(indent=2 if pretty else None)
    if out is not None:
        out.write_text(payload, encoding="utf-8")
        rows = statement.validation.row_count
        console.print(f"[green]OK[/green] — wrote {rows} line(s) to {out}")
    else:
        print(payload)


if __name__ == "__main__":
    app()
