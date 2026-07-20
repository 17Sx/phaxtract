"""Tests for building NuExtract fine-tune data from gold Statements."""

from __future__ import annotations

import json

from phaxtract.finetune_data import FinetuneExample, build_examples, split_dataset
from phaxtract.nuextract_template import STATEMENT_TEMPLATE
from phaxtract.schema import Statement


def _statement(code: str, month: str, qty: int) -> Statement:
    return Statement.model_validate(
        {
            "document": {
                "source_file": "g.json",
                "lgo": "",
                "statement_type": "monthly",
                "pharmacy": {"name": "P"},
                "months": [month],
            },
            "lines": [{"code_produit": code, "designation": "D", "quantities": {month: qty}}],
            "validation": {"row_count": 1},
        }
    )


def test_build_examples_carries_image_template_and_output() -> None:
    pairs = [("photo.jpg", _statement("3614810004843", "2026-05", 4))]
    examples = build_examples(pairs)
    assert len(examples) == 1
    ex = examples[0]
    assert isinstance(ex, FinetuneExample)
    assert ex.image == "photo.jpg"
    assert json.loads(ex.template) == STATEMENT_TEMPLATE
    output = json.loads(ex.output)
    assert output["products"][0]["code_produit"] == "3614810004843"
    assert output["products"][0]["sales"][0]["quantity"] == 4


def test_split_dataset_is_deterministic_and_partitions() -> None:
    items = list(range(20))
    split_a = split_dataset(items, val=4, test=3, seed=42)
    split_b = split_dataset(items, val=4, test=3, seed=42)
    assert split_a == split_b  # deterministic

    assert len(split_a["test"]) == 3
    assert len(split_a["val"]) == 4
    assert len(split_a["train"]) == 13

    combined = split_a["train"] + split_a["val"] + split_a["test"]
    assert sorted(combined) == items  # partition, no overlap, no loss


def test_split_dataset_different_seed_differs() -> None:
    items = list(range(20))
    one = split_dataset(items, val=4, test=3, seed=1)
    two = split_dataset(items, val=4, test=3, seed=2)
    assert one != two
