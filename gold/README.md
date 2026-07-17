# Gold fixtures

Each fixture is a versioned `*.expected.json` (the canonical `Statement`).
The matching synthetic PDF is **not committed** — render it on demand from the
expected JSON:

    python scripts/generate_gold.py --out <dir>

This keeps git free of binary blobs and guarantees the PDF always matches its
expected JSON. Rendering lives in `phaxtract.synth.render_expected_file`.

Real Doc AI gold goes in `gold/images/` + `gold/jsons/` — gitignored, never committed.
