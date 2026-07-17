# Contributing to phaxtract

Thank you for your interest in contributing!

## Getting started

1. Fork the repository
2. Create a branch: `git checkout -b feat/my-feature`
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Make your changes
5. Run checks: `ruff check src tests && mypy src && pytest`
6. Open a pull request

## Code guidelines

- **Python ≥ 3.11**, type hints required on public APIs
- **Business rules in JSON config** — never hard-code LGO signatures, column aliases, or month mappings
- **Tests first** for deterministic layer changes
- **Small PRs** — one logical change per pull request
- Follow existing naming and module structure

## Adding a new LGO

1. Add fingerprints to `src/phaxtract/config/lgo_fingerprints.json`
2. Add column aliases to `src/phaxtract/config/column_aliases.json` if needed
3. Add a synthetic gold fixture in `gold/`
4. Add unit tests for fingerprint detection

No Python code changes should be required for a new LGO with an existing layout pattern.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(normalize): support abbreviated month labels
fix(validate): handle missing total row
test(benchmark): add cell diff edge cases
docs(readme): update quick start
```

## Reporting issues

Include:

- Input document type (native PDF / photo / scan)
- LGO if known
- Expected vs actual JSON (redact sensitive pharmacy data)
- Python version and OS

## Code of conduct

Be respectful and constructive. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
