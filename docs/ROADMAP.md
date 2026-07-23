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

- [x] **Doc AI → `Statement` converter** — convert the ~197 annotated Google
      Document AI JSONs into canonical `*.expected.json` gold (local, gitignored)
- [x] Extraction template + mapping raw output → `Statement`
- [x] NuExtract 3 zero-shot inference (local GPU) — `nuextract_engine.py` +
      `extract_statement_from_image()` + `phaxtract extract <image>` CLI
- [x] Real-data benchmark harness — `discover_pairs` + `evaluate_photo_dataset` +
      `aggregate_reports` + `scripts/benchmark_nuextract.py`
- [x] Benchmark NuExtract vs real gold — ran on a 12 GB GPU. Zero-shot NuExtract3
      reads structure (codes, designations, months) well but **misaligns the dense
      monthly quantity grid** (reads the printed totals row as a product line).
- [x] LoRA fine-tune scaffolding — `build_finetune_data.py` (train/val/test split),
      `finetune_nuextract.py` (QLoRA), adapter eval via `--adapter`. **Trains on
      12 GB** (4-bit + Liger fused CE + attn-only LoRA + length/resolution capping).
- [ ] **Run the fine-tune on a ≥ 16 GB GPU** — 12 GB fits NuExtract-2.0-2B training
      but that model does not extract in our stack; NuExtract3 (which extracts) OOMs
      at the loss on 12 GB (Liger lacks its arch). Deferred to a larger GPU.
- [ ] Few-shot in-context examples (`--examples`) — wired, but multi-image prompts
      need NuExtract's `process_all_vision_info` to interleave example/query images.

### Known limitation

The monthly **quantity grid** is the hard part: zero-shot NuExtract3 gets the layout
but not the per-cell alignment on dense statements. The surest fix is the LoRA
fine-tune on a larger GPU (scaffolding ready); few-shot is a lighter, unproven lever.

## Phase 3 — Native PDF path ✅

Native-text PDFs, no AI and no GPU. Both statement layouts are supported, with a
deterministic render → extract → compare round-trip so no real data is committed.

- [x] Ingestion (text-layer detection) — `ingest.has_text_layer`
- [x] pdfplumber table extraction — `extract_native.extract_statement_from_pdf`
- [x] Assembly: monthly grid **and** period transaction list → `Statement`
- [x] Pipeline: file-type dispatcher (`pipeline.extract_statement`)
- [x] CLI `phaxtract extract statement.pdf`
- [x] Synthetic gold PDFs (`synth.py` + `scripts/generate_gold.py`) + round-trip tests
- [ ] Automatic router: native PDF vs photo (a text-less PDF falling back to the
      photo path) — **deferred to Phase 4**; `has_text_layer` already provides the
      discriminant

## Phase 4 — Quality & UI

- [ ] Automatic router: native PDF vs photo (via `ingest.has_text_layer`)
- [ ] Multi-page handling
- [ ] Streamlit app (dashboard + viewer)
- [ ] Harden reconciliation (cases without Total row)
- [ ] GPU deployment documentation

## Locked decisions

| Topic | Choice | Reason |
| ----- | ------ | ------ |
| Primary input | Photos / scans | Main real-world volume → AI path first |
| Photo path | NuExtract 3 | Zero-shot, fine-tune possible |
| Native PDF path | pdfplumber | Free on native text — implemented (monthly + period) |
| LayoutLMv3 | No | Dataset too small |
| Geometric OCR | No | Insufficient precision |
| Google Doc AI | Gold source + reference | Convert its exports into `Statement` gold; not production |
| Business rules | JSON config | Add an LGO without touching code |
