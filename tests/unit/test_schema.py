"""Tests for Pydantic schema models."""

from phaxtract.schema import Statement


def test_statement_monthly_roundtrip(sample_statement_data: dict) -> None:
    stmt = Statement.model_validate(sample_statement_data)
    assert stmt.document.statement_type == "monthly"
    assert stmt.lines[0].quantities["2026-01"] == 3
    dumped = stmt.model_dump(mode="json")
    assert dumped["document"]["lgo"] == "etat_des_ventes"
