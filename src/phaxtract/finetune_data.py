"""Build NuExtract fine-tune examples from gold ``Statement`` data.

Each gold pair (image + expected :class:`~phaxtract.schema.Statement`) becomes a
training example: the image, the extraction template, and the target JSON the model
should produce (the inverse mapping, :func:`~phaxtract.extract_ai.statement_to_nuextract_output`).
A deterministic, seeded split holds out val/test sets for honest evaluation.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import NamedTuple, TypeVar

from phaxtract.extract_ai import statement_to_nuextract_output
from phaxtract.nuextract_template import STATEMENT_TEMPLATE
from phaxtract.schema import Statement

T = TypeVar("T")


class FinetuneExample(NamedTuple):
    """One training example: image path, template string, and target output JSON."""

    image: str
    template: str
    output: str


def build_examples(pairs: list[tuple[str | Path, Statement]]) -> list[FinetuneExample]:
    """Turn ``(image, expected Statement)`` pairs into fine-tune examples."""
    template = json.dumps(STATEMENT_TEMPLATE)
    return [
        FinetuneExample(
            image=str(image),
            template=template,
            output=json.dumps(statement_to_nuextract_output(expected)),
        )
        for image, expected in pairs
    ]


def split_dataset(items: list[T], *, val: int, test: int, seed: int) -> dict[str, list[T]]:
    """Deterministically partition ``items`` into ``train`` / ``val`` / ``test``.

    The same ``seed`` always yields the same split; ``test`` items are drawn first,
    then ``val``, and the remainder is ``train``. No overlap, nothing dropped.
    """
    shuffled = list(items)
    random.Random(seed).shuffle(shuffled)
    test_items = shuffled[:test]
    val_items = shuffled[test : test + val]
    train_items = shuffled[test + val :]
    return {"train": train_items, "val": val_items, "test": test_items}
