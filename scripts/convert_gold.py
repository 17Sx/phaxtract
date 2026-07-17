"""Batch-convert Doc AI annotations into canonical Statement gold.

Reads gold/jsons/*.json (Google Document AI exports, gitignored) and writes
gold/converted/*.expected.json (also gitignored). Never commit either directory.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from phaxtract.convert_docai import convert_docai_file

ROOT = Path(__file__).resolve().parent.parent
JSONS_DIR = ROOT / "gold" / "jsons"
OUT_DIR = ROOT / "gold" / "converted"


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert Doc AI gold to Statement gold.")
    parser.add_argument("--jsons", type=Path, default=JSONS_DIR, help="Input Doc AI JSON dir")
    parser.add_argument("--out", type=Path, default=OUT_DIR, help="Output Statement gold dir")
    args = parser.parse_args()

    files = sorted(args.jsons.glob("*.json"))
    if not files:
        print(f"No *.json found in {args.jsons}")
        return

    converted = 0
    total_skipped = 0
    failed: list[str] = []
    for json_path in files:
        try:
            _, result = convert_docai_file(json_path, args.out)
        except (ValueError, KeyError, TypeError) as exc:
            failed.append(f"{json_path.name}: {exc}")
            continue
        converted += 1
        total_skipped += len(result.skipped)

    print(f"Converted:     {converted}/{len(files)}")
    print(f"Skipped lines: {total_skipped}")
    print(f"Failed files:  {len(failed)}")
    for entry in failed:
        print(f"  ! {entry}")


if __name__ == "__main__":
    main()
