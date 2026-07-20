"""Build NuExtract fine-tune data (train/val/test JSONL) from the photo gold.

Pairs each ``gold/converted/*.expected.json`` with its source image, turns it into a
(image, template, target-JSON) example, and writes a deterministic split:

    python scripts/build_finetune_data.py \
        --converted gold/converted --images gold/images --out gold/finetune

Produces ``<out>/{train,val,test}.jsonl`` (one JSON object per line). Gold and the
generated data are gitignored (real, sensitive) — never commit them.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from phaxtract.benchmark import discover_pairs
from phaxtract.finetune_data import FinetuneExample, build_examples, split_dataset

ROOT = Path(__file__).resolve().parent.parent
CONVERTED_DIR = ROOT / "gold" / "converted"
IMAGES_DIR = ROOT / "gold" / "images"
OUT_DIR = ROOT / "gold" / "finetune"


def _write_jsonl(path: Path, examples: list[FinetuneExample]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for example in examples:
            handle.write(json.dumps(example._asdict()) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build NuExtract fine-tune JSONL from gold.")
    parser.add_argument("--converted", type=Path, default=CONVERTED_DIR, help="Gold JSON dir")
    parser.add_argument("--images", type=Path, default=IMAGES_DIR, help="Source images dir")
    parser.add_argument("--out", type=Path, default=OUT_DIR, help="Output dir for JSONL splits")
    parser.add_argument("--val", type=int, default=20, help="Validation set size")
    parser.add_argument("--test", type=int, default=18, help="Test set size (frozen)")
    parser.add_argument("--seed", type=int, default=42, help="Split seed (deterministic)")
    args = parser.parse_args()

    pairs, unmatched = discover_pairs(args.converted, args.images)
    if not pairs:
        print(f"No (image, gold) pairs found under {args.images} / {args.converted}")
        return

    examples = build_examples([(p.image, p.expected) for p in pairs])
    split = split_dataset(examples, val=args.val, test=args.test, seed=args.seed)

    args.out.mkdir(parents=True, exist_ok=True)
    for name, subset in split.items():
        _write_jsonl(args.out / f"{name}.jsonl", subset)

    print(f"Pairs:      {len(examples)}  (unmatched gold: {len(unmatched)})")
    print(f"Train/Val/Test: {len(split['train'])}/{len(split['val'])}/{len(split['test'])}")
    print(f"Wrote JSONL splits to {args.out}")


if __name__ == "__main__":
    main()
