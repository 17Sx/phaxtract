"""Generate synthetic gold fixtures (PDF) from the versioned expected JSON.

The synthetic PDFs reproduce real LGO layouts with non-sensitive data so the
native path (phase 2) can be benchmarked end-to-end without shipping real
statements. PDFs are rendered on demand and are *not* committed to git.
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from phaxtract.synth import render_expected_file

GOLD_DIR = Path(__file__).resolve().parent.parent / "gold"


def list_expected() -> list[Path]:
    """Return the expected JSON gold fixtures currently versioned."""
    return sorted(GOLD_DIR.glob("*.expected.json"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic gold fixtures.")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List expected JSON fixtures currently in gold/",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory for rendered PDFs (default: a temp dir)",
    )
    args = parser.parse_args()

    if args.list:
        for path in list_expected():
            print(path.name)
        return

    out_dir = args.out or Path(tempfile.mkdtemp(prefix="phaxtract-gold-"))
    for expected in list_expected():
        pdf = render_expected_file(expected, out_dir)
        print(f"{expected.name} -> {pdf}")


if __name__ == "__main__":
    main()
