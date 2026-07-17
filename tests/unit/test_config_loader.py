"""Tests for config loader."""

from phaxtract.config.loader import (
    load_column_aliases,
    load_lgo_config,
    load_month_abbreviations,
)


def test_load_month_abbreviations_contains_jun() -> None:
    abbr = load_month_abbreviations()
    assert abbr["jun"] == "06"
    assert abbr["déc"] == "12"


def test_load_lgo_config_has_etat_des_ventes() -> None:
    config = load_lgo_config()
    ids = {lgo.id for lgo in config.lgos}
    assert "etat_des_ventes" in ids


def test_load_column_aliases() -> None:
    aliases = load_column_aliases()
    assert aliases["désignation"] == "designation"
