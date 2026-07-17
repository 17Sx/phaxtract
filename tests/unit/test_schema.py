"""Tests for Pydantic schema models."""

import pytest

from phaxtract.schema import Line, Statement


def test_statement_monthly_roundtrip(sample_statement_data: dict) -> None:
    stmt = Statement.model_validate(sample_statement_data)
    assert stmt.document.statement_type == "monthly"
    assert stmt.lines[0].quantities["2026-01"] == 3
    dumped = stmt.model_dump(mode="json")
    assert dumped["document"]["lgo"] == "etat_des_ventes"


def test_code_produit_strips_spaces_and_dashes() -> None:
    assert Line(code_produit="34009 22151014").code_produit == "3400922151014"
    assert Line(code_produit="3700928800450 -").code_produit == "3700928800450"


def test_code_produit_allows_empty() -> None:
    assert Line(code_produit="").code_produit == ""


def test_code_produit_rejects_non_13_digit() -> None:
    with pytest.raises(ValueError, match="EAN-13"):
        Line(code_produit="5372381")  # CIP7, 7 digits after normalization
