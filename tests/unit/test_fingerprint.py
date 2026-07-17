"""Tests for LGO fingerprint detection."""

from phaxtract.fingerprint import identify_lgo


def test_identify_etat_des_ventes() -> None:
    sample = "ETAT DES VENTES\nPharmacie Dupont\nEAN Désignation"
    assert identify_lgo(sample) == "etat_des_ventes"


def test_identify_unknown() -> None:
    assert identify_lgo("Document inconnu") is None
