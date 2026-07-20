"""Benchmark NuExtract against the photo gold dataset.

Pairs each gold ``gold/converted/*.expected.json`` with its source image in
``gold/images/``, runs NuExtract on every photo, and reports the micro-averaged
cell precision plus the worst-scoring files.

Requires the optional ``[ai]`` extra (torch + transformers) and, in practice, a GPU:

    pip install -e ".[ai]"
    python scripts/benchmark_nuextract.py                 # full dataset
    python scripts/benchmark_nuextract.py --limit 10      # quick smoke over 10 photos
    python scripts/benchmark_nuextract.py --out report.json

Both gold folders are gitignored (real, sensitive data) — never commit them.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from phaxtract.benchmark import discover_pairs, evaluate_photo_dataset
from phaxtract.nuextract_engine import ExtractionDependencyError, NuExtractEngine

ROOT = Path(__file__).resolve().parent.parent
CONVERTED_DIR = ROOT / "gold" / "converted"
IMAGES_DIR = ROOT / "gold" / "images"


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark NuExtract vs photo gold.")
    parser.add_argument(
        "--converted", type=Path, default=CONVERTED_DIR, help="Gold *.expected.json dir"
    )
    parser.add_argument("--images", type=Path, default=IMAGES_DIR, help="Source images dir")
    parser.add_argument(
        "--model", default="numind/NuExtract3", help="NuExtract HuggingFace model id"
    )
    parser.add_argument(
        "--adapter", default=None, help="Path to a trained LoRA adapter to evaluate"
    )
    parser.add_argument(
        "--4bit", dest="four_bit", action="store_true", help="Load 4-bit quantized (12 GB GPU)"
    )
    parser.add_argument(
        "--thinking", action="store_true", help="Enable NuExtract reasoning (dense tables)"
    )
    parser.add_argument(
        "--max-pixels", type=int, default=None, help="Cap input image resolution (w x h)"
    )
    parser.add_argument(
        "--max-new-tokens", type=int, default=4096, help="Generation token budget"
    )
    parser.add_argument("--limit", type=int, default=None, help="Benchmark only the first N pairs")
    parser.add_argument("--out", type=Path, default=None, help="Write the full JSON report here")
    args = parser.parse_args()

    pairs, unmatched = discover_pairs(args.converted, args.images)
    if args.limit is not None:
        pairs = pairs[: args.limit]
    if not pairs:
        print(f"No (image, gold) pairs found under {args.images} / {args.converted}")
        return

    engine = NuExtractEngine(
        model_id=args.model,
        adapter_path=args.adapter,
        load_in_4bit=args.four_bit,
        thinking=args.thinking,
        max_pixels=args.max_pixels,
        max_new_tokens=args.max_new_tokens,
    )
    print(f"Loading {args.model} … (first run downloads the model)")
    try:
        report = evaluate_photo_dataset([(p.image, p.expected) for p in pairs], engine)
    except ExtractionDependencyError as exc:
        raise SystemExit(f"Error — {exc}") from exc

    print(f"\nFiles evaluated:  {report.files_evaluated}")
    print(f"Unmatched gold:   {len(unmatched)}")
    print(f"Cells compared:   {report.cells_compared}")
    print(f"Cell precision:   {report.cell_precision:.2%}  (micro-average)")
    print(f"Reconciliation:   {report.reconciled_rate:.2%}")

    worst = sorted(report.per_file, key=lambda f: f.cell_precision)[:10]
    if worst:
        print("\nWorst files:")
        for score in worst:
            print(f"  {score.cell_precision:6.1%}  {score.name}  ({score.cells_compared} cells)")

    if args.out is not None:
        payload = {
            "summary": {
                "files_evaluated": report.files_evaluated,
                "cells_compared": report.cells_compared,
                "cells_matched": report.cells_matched,
                "cell_precision": report.cell_precision,
                "reconciled_rate": report.reconciled_rate,
            },
            "per_file": [asdict(score) for score in report.per_file],
        }
        args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nWrote full report to {args.out}")


if __name__ == "__main__":
    main()
