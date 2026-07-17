# Gold fixtures

Synthetic gold fixtures live here (`*.pdf` + `*.expected.json`).

Real Doc AI gold (197 documents) goes in `gold/real/` — gitignored.

## Real gold (photos, local-only)

Doc AI annotations live in `gold/jsons/` (+ images in `gold/images/`), gitignored.
Convert them into canonical `Statement` gold for benchmarking:

    python scripts/convert_gold.py

Output lands in `gold/converted/*.expected.json` (gitignored). Conversion logic:
`phaxtract.convert_docai`.
