# Gold fixtures

Synthetic gold fixtures live here as `*.expected.json` (canonical `Statement`).
Two layouts are versioned:

- `monthly_etat_des_ventes.expected.json` — product × month grid
- `period_etat_des_ventes.expected.json` — transaction list grouped by product

The matching `*.pdf` files are **rendered on demand, never committed**:

    python scripts/generate_gold.py            # render every *.expected.json
    python scripts/generate_gold.py --list     # list the fixtures

Rendering logic: `phaxtract.synth`. The native path's round-trip tests render each
expected JSON to a PDF, extract it back, and assert a cell-exact match — so the
fixtures stay honest with zero real pharmacy data.

Real Doc AI gold (197 documents) goes in `gold/real/` — gitignored.

## Real gold (photos, local-only)

Doc AI annotations live in `gold/jsons/` (+ images in `gold/images/`), gitignored.
Convert them into canonical `Statement` gold for benchmarking:

    python scripts/convert_gold.py

Output lands in `gold/converted/*.expected.json` (gitignored). Conversion logic:
`phaxtract.convert_docai`.
