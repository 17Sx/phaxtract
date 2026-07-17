"""Shared pytest fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_statement_data() -> dict:
    return {
        "document": {
            "source_file": "statement.pdf",
            "lgo": "etat_des_ventes",
            "statement_type": "monthly",
            "pharmacy": {"name": "Test Pharmacy", "address": "1 Test Street", "id": "123"},
            "supplier": "Example Labs",
            "months": ["2026-01", "2025-12"],
            "generated_at": "2026-02-27",
            "page_count": 1,
        },
        "lines": [
            {
                "code_produit": "3614810004843",
                "designation": "Product A",
                "prices": {"pa_cat": 32.0, "pa_cat_net": 20.48, "pv_ttc": 49.95},
                "quantities": {"2026-01": 3, "2025-12": 3},
                "confidence": 0.98,
                "source": {"page": 1, "row_bbox": [0.0, 0.0, 100.0, 10.0]},
            }
        ],
        "validation": {"totals_reconciled": True, "row_count": 1, "flags": []},
    }
