# Roadmap

## Phase 1 — Foundations ✅ (in progress)

- [x] Pydantic `Statement` schema
- [x] JSON config (LGO, aliases, months)
- [x] Deterministic layer: normalize, validate, reconcile, fingerprint
- [x] Cell-by-cell benchmark
- [x] CLI `validate-config`, `benchmark`
- [x] Unit tests + CI
- [x] Synthetic gold PDF + expected JSON

## Phase 2 — Native PDF path

- [ ] Ingestion (text layer detection)
- [ ] pdfplumber table extraction
- [ ] Pipeline ingest → extract → assemble → JSON
- [ ] CLI `phaxtract extract statement.pdf`
- [ ] Benchmark on synthetic gold then real gold

## Phase 3 — AI path (photos)

- [ ] NuExtract 3 zero-shot inference (local GPU)
- [ ] Extraction template + mapping to `Statement`
- [ ] Automatic router: native PDF vs photo
- [ ] LoRA fine-tune if precision < 90%

## Phase 4 — Quality & UI

- [ ] Multi-page handling
- [ ] Streamlit app (dashboard + viewer)
- [ ] Harden reconciliation (cases without Total row)
- [ ] GPU deployment documentation

## Locked decisions

| Topic | Choice | Reason |
| ----- | ------ | ------ |
| PDF path | pdfplumber | Free, reliable on native text |
| Photo path | NuExtract 3 | Zero-shot, fine-tune possible |
| LayoutLMv3 | No | Dataset too small |
| Geometric OCR | No | Insufficient precision |
| Google Doc AI | Gold only | Benchmark reference, not production |
| Business rules | JSON config | Add an LGO without touching code |
