"""Generate synthetic gold fixtures (PDF + expected JSON).

Phase 1 ships expected JSON fixtures by hand. This script will render matching
synthetic PDFs reproducing real LGO layouts so the native path (phase 2) can be
benchmarked end-to-end without shipping sensitive real statements.
"""

from __future__ import annotations

import argparse
from pathlib import Path

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
    args = parser.parse_args()

    if args.list:
        for path in list_expected():
            print(path.name)
        return

    # TODO(phase-2): render synthetic PDFs matching each *.expected.json layout.
    print("Synthetic PDF generation lands in phase 2 (native PDF path).")


if __name__ == "__main__":
    main()
