# Specification

## One-liner

Replace **Google Document AI** with a **local, free** extractor that turns pharmacy sales statements (PDF or photos) into **structured, validated JSON**.

---

## Context

Labs receive **sales statements** from pharmacies. Today, extraction goes through **Google Document AI** (cloud, paid, ~197 manually annotated documents).

**Goal:** produce the same JSON, self-hosted, with no API calls.

| | Google Document AI | phaxtract (target) |
| --- | --- | --- |
| Cost | Pay per page | Free |
| Hosting | Google Cloud | Local (GPU for photos) |
| Data | Sent to cloud | Stays on-premises |
| Output | Entity JSON | Single canonical JSON |

---

## Document types

Two formats, **one output schema**:

| Type | Description |
| ---- | ----------- |
| **Monthly** | Product × month grid (EAN, designation, qty per month column) |
| **Period** | Transaction list (date, qty, amount) grouped by product |

Statements come from different **LGO** (pharmacy management systems): varied layouts, different column labels, French month abbreviations.

---

## Target pipeline

```mermaid
flowchart TB
    IN(["Statement\nPDF or photo"])

    IN --> ROUTE{"Usable\ntext layer?"}

    ROUTE -->|Yes| V1["Native path\npdfplumber"]
    ROUTE -->|No| V2["AI path\nNuExtract 3"]

    V1 --> DET
    V2 --> DET

    subgraph DET["Deterministic layer (shared)"]
        direction TB
        D1["Identify LGO"]
        D2["Normalize months & columns"]
        D3["Assemble rows"]
        D4["Validate & reconcile"]
        D1 --> D2 --> D3 --> D4
    end

    DET --> OUT(["JSON Statement"])
    OUT --> QA["Benchmark vs gold"]
```

**Principle:** two extraction paths, **one downstream business logic**. AI does not replace validation — it only reads the document.

---

## Path 1 — Native PDF

~495 PDFs with selectable text layer. No AI, no GPU.

```mermaid
flowchart LR
    A["PDF"] --> B["Text layer\ndetection"]
    B --> C["Table extraction\npdfplumber"]
    C --> D["Raw table\nheaders + rows + total"]
    D --> E["Deterministic layer"]
    E --> F["JSON"]
```

**Steps:**

1. **Ingestion** — open PDF, verify text layer presence (`ingest.has_text_layer`)
2. **Extraction** — read table grids/rows (pdfplumber, `extract_native`)
3. **Deterministic layer** — see dedicated section

**Status:** implemented for both **monthly** grids and **period** transaction lists.
Free, fast, reproducible — no AI, no GPU. Synthetic gold PDFs are rendered on demand
by `synth.py` / `scripts/generate_gold.py`, and a render → extract → compare
round-trip keeps the fixtures cell-exact with no real data. The **automatic
native-vs-photo router** stays deferred (Phase 4); today the CLI and
`pipeline.extract_statement` dispatch on the file suffix.

---

## Path 2 — Photo / scan ⭐ priority

Main volume: paper statement photos, scans, image-only PDFs. This is the priority
path — the real dataset is ~197 photos annotated with Google Document AI.

```mermaid
flowchart LR
    A["Image"] --> B["NuExtract 3\nlocal VLM"]
    B --> C["Raw JSON\ntemplate-guided"]
    C --> D["Mapping → canonical schema"]
    D --> E["Deterministic layer"]
    E --> F["JSON"]
```

**Steps:**

1. **Inference** — NuExtract 3 receives image + JSON template describing expected structure
2. **Mapping** — convert raw output to `Statement` schema
3. **Deterministic layer** — same as native path

**Model:** [NuExtract 3](https://huggingface.co/numind/NuExtract3) (~4B, Apache-2.0)  
**Hardware:** 12 GB GPU min (RTX 4070, 4-bit inference)  
**Fine-tuning:** optional LoRA on annotated gold if zero-shot is insufficient

**Out of scope:** LayoutLMv3, geometric OCR, cloud APIs.

---

## Deterministic layer

Core business logic. Independent of input path.

```mermaid
flowchart TB
    RAW["Raw input\n(table or AI JSON)"]

    RAW --> ID["1. LGO fingerprint\n(JSON config)"]
    ID --> NORM["2. Normalization\nmonths → YYYY-MM\ncolumn aliases"]
    NORM --> ASM["3. Assembly\nmonthly / period rows"]
    ASM --> VAL["4. Validation\nFR numbers, dates"]
    VAL --> REC["5. Reconciliation\nΣ qty = printed Total"]
    REC --> SCORE["6. Confidence & flags\nper row"]

    SCORE --> OUT["Statement"]
```

| Step | Responsibility |
| ---- | -------------- |
| Fingerprint | Recognize which LGO produced the statement (regex + config signatures) |
| Normalization | `jun` → `2025-06`, map column labels to canonical fields |
| Assembly | Build row objects for monthly or period type |
| Validation | Parse FR decimals, dates, type coercion |
| Reconciliation | Verify Σ quantities = document Total row |
| Scoring | Assign confidence score and explicit flags |

**Golden rule:** all business rules (months, aliases, LGO signatures) live in **JSON config**, never hard-coded.

---

## Output JSON schema

Single `Statement` model for both statement types:

```jsonc
{
  "document": {
    "source_file": "statement.pdf",
    "lgo": "etat_des_ventes",
    "statement_type": "monthly",
    "pharmacy": { "name": "...", "address": "...", "id": "..." },
    "supplier": "...",
    "months": ["2026-01", "2025-12"],
    "generated_at": "2026-02-27",
    "page_count": 5
  },
  "lines": [{
    "code_produit": "3614810004843",
    "designation": "...",
    "prices": { "pa_cat": 32.0, "pa_cat_net": 20.48, "pv_ttc": 49.95 },
    "quantities": { "2026-01": 3, "2025-12": 3 },
    "confidence": 0.98,
    "source": { "page": 1, "row_bbox": [0, 0, 0, 0] }
  }],
  "validation": {
    "totals_reconciled": true,
    "row_count": 9,
    "flags": []
  }
}
```

**Reconciliation** (`totals_reconciled`) is the primary quality criterion: each document validates itself.

---

## Gold set & quality

```mermaid
flowchart LR
    G1["Synthetic gold\nPDF + expected.json\n(versioned, CI)"]
    G2["Real gold\n197 Doc AI JSON\n(external, gitignored)"]
    SYS["phaxtract extractor"]

    G1 --> BENCH["Cell-by-cell\nbenchmark"]
    G2 --> BENCH
    SYS --> BENCH
    BENCH --> RAP["Report\nprecision + reconciliation"]
```

| Metric | Target |
| ------ | ------ |
| Cell-level precision | ≥ 98% |
| Reconciliation rate | ≥ 95% |
| LGO coverage | ≥ 3 different LGOs |

**Real gold (primary):** the ~197 Google Document AI exports, converted into
canonical `Statement` JSON, are the real-world benchmark for the photo path.  
**Synthetic gold (secondary):** PDFs rendered on demand from the versioned expected
JSON (`synth.py`) reproducing real layouts — CI round-trip tests for the native path.

---

## Review interface (optional, phase 4)

Local read-only Streamlit app:

- **Dashboard** — quality metrics per LGO, comparison vs gold
- **Viewer** — upload a statement, visualize extraction

No auth, no database, no editing in v1.

---

## Tech stack

| Component | Choice |
| --------- | ------ |
| Language | Python ≥ 3.11 |
| Schema | Pydantic v2 |
| Native PDF | pdfplumber + PyMuPDF |
| Normalization | rapidfuzz, python-dateutil |
| Photo AI | NuExtract 3, transformers, PEFT/LoRA |
| UI | Streamlit (phase 4) |
| Tests | pytest |
| Network | None in production |

---

## Implementation phases

```mermaid
flowchart LR
    P1["Phase 1\nFoundations"] --> P2["Phase 2\nAI path (NuExtract)"]
    P2 --> P3["Phase 3\nPDF path (pdfplumber)"]
    P3 --> P4["Phase 4\nQuality & UI"]
```

> Primary input is photos, so the **AI path was the priority**; the native PDF path
> (monthly + period) is now implemented, with the automatic router left to Phase 4.

### Phase 1 — Foundations ✅

- Pydantic schema (`Statement`, `Line`, `Document`…)
- JSON config (LGO fingerprints, column aliases, month abbreviations)
- Deterministic layer: normalize, validate, reconcile
- Cell-by-cell benchmark + CLI
- Unit tests on deterministic layer

### Phase 2 — AI path (photos) ⭐ priority

- **Doc AI → `Statement` converter** — turn the ~197 annotated exports into real gold
- Real-data benchmark harness (`compare_statements` over the photo gold)
- NuExtract 3 inference (zero-shot)
- Extraction template + mapping to `Statement`
- Benchmark NuExtract vs real gold
- LoRA fine-tune if precision < 90%

### Phase 3 — Native PDF path ✅

- Ingestion (text layer detection)
- Table extraction (pdfplumber) — monthly grid + period transaction list
- Pipeline: file-type dispatcher (ingest → extract → assemble → JSON)
- CLI: `extract statement.pdf`
- Synthetic gold PDFs (`synth.py` + `generate_gold.py`) + round-trip tests
- Automatic router: native PDF vs photo → deferred to Phase 4

### Phase 4 — Quality & UI

- Multi-page handling (split + merge)
- Streamlit app (dashboard + viewer)
- Harden reconciliation (cases without Total row)
- Operational documentation (GPU deployment)

---

## Target repository layout

```
phaxtract/
├── src/phaxtract/
│   ├── schema.py           # Pydantic models
│   ├── config/             # JSON business rules
│   ├── ingest.py           # document type detection
│   ├── extract_native.py   # PDF path
│   ├── extract_ai.py       # NuExtract path
│   ├── normalize.py        # normalization
│   ├── validate.py         # validation + reconciliation
│   ├── fingerprint.py      # LGO identification
│   ├── pipeline.py         # orchestrator
│   ├── benchmark.py        # scoring vs gold
│   └── cli.py              # CLI entry point
├── gold/
│   ├── *.pdf               # synthetic gold (versioned)
│   └── *.expected.json
├── tests/
├── scripts/
│   ├── generate_gold.py
│   └── ml/                 # train, eval, predict NuExtract
├── app/                    # Streamlit (phase 4)
├── docs/
│   └── ARCHITECTURE.md
├── pyproject.toml
└── README.md
```

---

## Locked decisions

| Topic | Choice | Reason |
| ----- | ------ | ------ |
| Primary input | Photos / scans | Main real-world volume → AI path first |
| Photo path | NuExtract 3 | Zero-shot, simple pipeline, fine-tune possible |
| Native PDF path | pdfplumber | Free on native text — implemented (monthly + period) |
| LayoutLMv3 | No | Dataset too small, complex assembler |
| Geometric OCR | No | Insufficient precision (~5%) |
| Google Doc AI | Gold source + reference | Convert exports into `Statement` gold; not production |
| Business rules | JSON config | Add an LGO without touching code |
