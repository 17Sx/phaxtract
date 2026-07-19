# phaxtract

[![CI](https://github.com/17Sx/phaxtract/actions/workflows/ci.yml/badge.svg)](https://github.com/17Sx/phaxtract/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

**Local, free extraction of pharmacy sales statements → structured JSON.**

Replace Google Document AI with a self-hosted pipeline that keeps data on-premises and produces validated, canonical JSON from PDFs and photos.

## Why phaxtract?

| | Google Document AI | phaxtract |
| --- | --- | --- |
| Cost | Pay per page | Free |
| Hosting | Google Cloud | Local |
| Data | Sent to cloud | On-premises |
| Output | Entity JSON | Single canonical JSON |

## Features

- **Two extraction paths** — photo/scan (NuExtract 3, the priority) and native PDF (pdfplumber)
- **One deterministic layer** — LGO fingerprinting, normalization, validation, reconciliation
- **JSON-driven rules** — add a new LGO without changing code
- **Self-validating output** — Σ quantities must match printed totals
- **Offline by default** — no network calls in production

## Quick start

```bash
# Clone and install
git clone https://github.com/17Sx/phaxtract.git
cd phaxtract
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Validate config
phaxtract validate-config

# Run tests
pytest

# Benchmark an extraction against gold
phaxtract benchmark gold/monthly_etat_des_ventes.expected.json output.json
```

### Extract a photo/scan with NuExtract

The photo path runs a local [NuExtract](https://huggingface.co/numind/NuExtract3)
vision-language model. It needs the optional `ai` extra (torch + transformers) and,
for practical speed, a GPU:

```bash
pip install -e ".[ai]"

# Photo/scan -> canonical Statement JSON (stdout, or -o to a file)
phaxtract extract statement.jpg --pretty
phaxtract extract statement.jpg -o statement.json
phaxtract extract statement.jpg --model numind/NuExtract-2.0-4B  # pick another model
```

The model reads the image plus the extraction template and fills it; the raw output
is mapped to a validated `Statement` by the same deterministic layer every path
shares. The first run downloads the model from HuggingFace; everything else is offline.

## Project status

**Phase 1 — Foundations** ✅ complete

Primary input is **photos/scans**, so the next priority is the **AI/photo path (NuExtract)**; the native-PDF path is deferred.

- [x] Pydantic `Statement` schema
- [x] JSON business rules (LGO, columns, months)
- [x] Deterministic layer (normalize, validate, reconcile, fingerprint)
- [x] Cell-by-cell benchmark + CLI
- [x] Doc AI → `Statement` gold converter (real photo dataset)
- [x] NuExtract photo extraction — template, mapping, inference engine, `extract` CLI
- [ ] **Next:** benchmark NuExtract vs real gold (Phase 2)
- [ ] Native PDF extraction (Phase 3, deferred)

See [ROADMAP](docs/ROADMAP.md) for details.

## Documentation

- [Specification](docs/SPECIFICATION.md) — full product spec
- [Architecture](docs/ARCHITECTURE.md) — pipeline and design principles
- [Implementation plan](docs/superpowers/plans/2026-07-17-phaxtract-foundations.md) — phase 1 task breakdown

## Output schema

```jsonc
{
  "document": {
    "source_file": "statement.pdf",
    "lgo": "etat_des_ventes",
    "statement_type": "monthly",
    "pharmacy": { "name": "...", "address": "...", "id": "..." },
    "months": ["2026-01", "2025-12"]
  },
  "lines": [{
    "code_produit": "3614810004843",
    "designation": "Product A",
    "quantities": { "2026-01": 3, "2025-12": 3 },
    "confidence": 0.98
  }],
  "validation": {
    "totals_reconciled": true,
    "row_count": 1,
    "flags": []
  }
}
```

## Development

```bash
pip install -e ".[dev]"
ruff check src tests
mypy src
pytest --cov=phaxtract
```

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache-2.0 — see [LICENSE](LICENSE).
