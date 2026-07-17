# Roadmap

> **Primary input is photos/scans.** The lab receives most statements as photos,
> scans, or image-only PDFs — so the **AI/photo path (NuExtract)** is the priority.
> The native-PDF path stays in the plan but is **deferred** until native-text PDFs
> are actually part of the workflow.

## Phase 1 — Foundations ✅

- [x] Pydantic `Statement` schema
- [x] JSON config (LGO, aliases, months)
- [x] Deterministic layer: normalize, validate, reconcile, fingerprint
- [x] Cell-by-cell benchmark + CLI (`validate-config`, `benchmark`)
- [x] Unit tests + CI

## Phase 2 — AI / photo path (NuExtract) ⭐ priority

Turn the real photo dataset into measurable ground truth, then extract against it.

- [ ] **Doc AI → `Statement` converter** — convert the ~197 annotated Google
      Document AI JSONs into canonical `*.expected.json` gold (local, gitignored)
- [ ] Real-data benchmark harness — run `compare_statements` over the photo gold
- [ ] NuExtract 3 zero-shot inference (local GPU) in `extract_ai.py`
- [ ] Extraction template + mapping raw output → `Statement`
- [ ] Benchmark NuExtract vs real gold
- [ ] LoRA fine-tune if precision < 90%

## Phase 3 — Native PDF path (deferred)

Only relevant once native-text PDFs are part of the input. A rendering prototype
(synthetic gold PDFs) already exists on the unmerged `feat/synthetic-gold-pdf` branch.

- [ ] Ingestion (text-layer detection)
- [ ] pdfplumber table extraction
- [ ] Pipeline: ingest → extract → assemble → JSON
- [ ] CLI `phaxtract extract statement.pdf`
- [ ] Synthetic gold PDF fixtures (prototype on branch) + benchmark
- [ ] Automatic router: native PDF vs photo

## Phase 4 — Quality & UI

- [ ] Multi-page handling
- [ ] Streamlit app (dashboard + viewer)
- [ ] Harden reconciliation (cases without Total row)
- [ ] GPU deployment documentation

## Locked decisions

| Topic | Choice | Reason |
| ----- | ------ | ------ |
| Primary input | Photos / scans | Main real-world volume → AI path first |
| Photo path | NuExtract 3 | Zero-shot, fine-tune possible |
| Native PDF path | pdfplumber | Free on native text — deferred until needed |
| LayoutLMv3 | No | Dataset too small |
| Geometric OCR | No | Insufficient precision |
| Google Doc AI | Gold source + reference | Convert its exports into `Statement` gold; not production |
| Business rules | JSON config | Add an LGO without touching code |
