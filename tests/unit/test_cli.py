"""Tests for CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from phaxtract.cli import app

runner = CliRunner()


def test_validate_config_command() -> None:
    result = runner.invoke(app, ["validate-config"])
    assert result.exit_code == 0
    assert "LGO fingerprint" in result.stdout


class _FakeEngine:
    """Fake NuExtractEngine: returns canned JSON, never loads a model."""

    def __init__(self, *_: object, **__: object) -> None:
        pass

    def extract(self, image: str | Path, template: str) -> str:
        return json.dumps(
            {
                "products": [
                    {
                        "code_produit": "3614810004843",
                        "designation": "A",
                        "sales": [{"month": "2026-05-01", "quantity": 7}],
                    }
                ]
            }
        )


def test_extract_command_writes_statement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("phaxtract.cli.NuExtractEngine", _FakeEngine)
    image = tmp_path / "photo.png"
    image.write_bytes(b"not-a-real-image")
    out = tmp_path / "result.json"

    result = runner.invoke(app, ["extract", str(image), "--out", str(out)])

    assert result.exit_code == 0, result.stdout
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["document"]["source_file"] == "photo.png"
    assert data["lines"][0]["code_produit"] == "3614810004843"
    assert data["lines"][0]["quantities"] == {"2026-05": 7}


def test_extract_command_prints_to_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("phaxtract.cli.NuExtractEngine", _FakeEngine)
    image = tmp_path / "photo.png"
    image.write_bytes(b"not-a-real-image")

    result = runner.invoke(app, ["extract", str(image)])

    assert result.exit_code == 0
    assert "3614810004843" in result.stdout


def test_extract_pdf_uses_native_path(tmp_path: Path) -> None:
    from phaxtract.schema import Statement
    from phaxtract.synth import render_statement_pdf

    gold = Path(__file__).resolve().parents[2] / "gold" / "monthly_etat_des_ventes.expected.json"
    expected = Statement.model_validate(json.loads(gold.read_text(encoding="utf-8")))
    pdf = render_statement_pdf(expected, tmp_path / "m.pdf")
    out = tmp_path / "out.json"

    result = runner.invoke(app, ["extract", str(pdf), "--out", str(out)])
    assert result.exit_code == 0, result.output
    written = Statement.model_validate(json.loads(out.read_text(encoding="utf-8")))
    assert written.document.statement_type == "monthly"
    assert written.lines


def test_extract_command_reports_missing_ai_extra(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from phaxtract.nuextract_engine import ExtractionDependencyError

    class _NoBackendEngine(_FakeEngine):
        def extract(self, image: str | Path, template: str) -> str:
            raise ExtractionDependencyError("install phaxtract[ai]")

    monkeypatch.setattr("phaxtract.cli.NuExtractEngine", _NoBackendEngine)
    image = tmp_path / "photo.png"
    image.write_bytes(b"x")

    result = runner.invoke(app, ["extract", str(image)])

    assert result.exit_code == 1
    assert "phaxtract[ai]" in result.stdout
