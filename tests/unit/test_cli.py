"""Tests for CLI commands."""

from typer.testing import CliRunner

from phaxtract.cli import app

runner = CliRunner()


def test_validate_config_command() -> None:
    result = runner.invoke(app, ["validate-config"])
    assert result.exit_code == 0
    assert "LGO fingerprint" in result.stdout
