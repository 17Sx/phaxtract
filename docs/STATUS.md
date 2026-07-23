# État du projet — phaxtract

> Snapshot vivant de l'avancement. Dernière mise à jour : **2026-07-23** (chemin PDF natif codé).
> Pour le plan complet des phases, voir [ROADMAP.md](ROADMAP.md).

---

## 🎯 En une phrase

phaxtract transforme des relevés de ventes de pharmacie (photos/scans, PDF) en un
JSON `Statement` canonique et validé, **en local et hors-ligne**. Le **chemin PDF
natif (pdfplumber)** est codé (monthly + period) ; le **chemin photo (NuExtract 3)**
reste à chiffrer sur GPU.

---

## 📍 Vous êtes ici

```
Phase 1 — Fondations                ████████████████████  ✅ TERMINÉE
Phase 2 — Chemin photo (NuExtract)  ████████████████░░░░  🔨 EN COURS
Phase 3 — PDF natif (pdfplumber)    ██████████████████░░  ✅ CODÉE  ← ICI
Phase 4 — Qualité & UI              ░░░░░░░░░░░░░░░░░░░░░  ⏸️  NON COMMENCÉE
```

**Concrètement :** toute la « plomberie » du chemin photo est faite et testée
(schéma, couche déterministe, template, mapping, **moteur d'inférence NuExtract**,
CLI, **et le harness de benchmark**). Il ne reste plus qu'à **exécuter** le benchmark
sur le serveur GPU pour chiffrer la précision réelle, et selon le résultat, un
éventuel fine-tuning.

---

## ✅ Ce qui est FAIT

### Phase 1 — Fondations (100 %)
- [x] Schéma Pydantic `Statement` (validation EAN-13, mois `YYYY-MM`)
- [x] Règles métier en config JSON (LGO, alias de colonnes, mois)
- [x] Couche déterministe : `normalize`, `validate`, `reconcile`, `fingerprint`
- [x] Benchmark cellule-par-cellule + CLI (`validate-config`, `benchmark`)
- [x] Tests unitaires + CI (ruff, mypy strict, pytest sur 3.11/3.12/3.13)

### Phase 2 — Chemin photo (parties faites)
- [x] **Converter Doc AI → `Statement` gold** — transforme les ~197 exports Google
      Document AI annotés en `*.expected.json` canoniques (local, gitignoré)
- [x] **Template d'extraction** — le « formulaire vide » que NuExtract remplit
- [x] **Mapping** sortie NuExtract brute → `Statement` (`nuextract_to_statement`)
- [x] **Moteur d'inférence NuExtract 3** — `nuextract_engine.py` : chargement modèle
      (lazy, caché), décodage greedy déterministe, torch isolé
- [x] **Orchestrateur** `extract_statement_from_image()` (engine injectable)
- [x] **CLI** `phaxtract extract <image> [--out] [--model] [--pretty]`
- [x] **Harness de benchmark** — `discover_pairs` + `evaluate_photo_dataset` +
      `aggregate_reports` + `scripts/benchmark_nuextract.py` (précision micro)
- [x] 56 tests verts, coverage ~89 %, import `extract_ai` sans torch (vérifié)

### Phase 3 — PDF natif (pdfplumber) — CODÉE
- [x] **Ingestion** — `ingest.has_text_layer` (détection de couche texte via pdfplumber)
- [x] **Extraction native** — `extract_native` : mapping pur testable
      (`assemble_monthly` / `assemble_period`) + orchestrateur `extract_statement_from_pdf`
- [x] **Deux layouts** — grille mensuelle **et** liste de transactions period
- [x] **Rendu gold synthétique** — `synth.py` (`Statement` → PDF grillé) +
      `scripts/generate_gold.py` ; round-trip render → extract → compare **cellule-exact**
- [x] **Dispatcher** `pipeline.extract_statement` (par type de fichier) + CLI `extract *.pdf`
- [x] **87 tests verts, coverage 90 %**, aucune donnée réelle (fixtures rendues à la demande)
- [ ] Routeur automatique natif/photo → **différé Phase 4** (`has_text_layer` prêt)

---

## 🔨 CE QU'IL RESTE À FAIRE

### Phase 2 — pour la clôturer (priorité immédiate)

| # | Tâche | Détail | Où | État |
|---|-------|--------|-----|------|
| ~~1~~ | ~~Harness de benchmark~~ | ~~`discover_pairs` + `evaluate_photo_dataset` + `aggregate_reports` + script~~ | PC | ✅ FAIT |
| **2** | **Exécuter le benchmark** | `pip install -e ".[ai]"` puis `python scripts/benchmark_nuextract.py` — chiffre la précision **et** valide que la sortie réelle du modèle colle au mapping | **Serveur GPU** | 👉 À FAIRE |
| **3** | **Analyser les écarts** | Regarder les pires fichiers (`--out report.json`) ; ajuster template/mapping si le modèle structure autrement | PC | Dépend de #2 |
| **4** | **LoRA fine-tune** (conditionnel) | **Seulement si** précision < 90 % au #2 | Serveur GPU | Dépend de #2 |

> Une fois #2→#3 faits (et #4 si nécessaire), la **Phase 2 est terminée**.

### Phase 3 — PDF natif (pdfplumber) — CODÉE ✅
Voir le bloc « Ce qui est FAIT » ci-dessus. Reste :
- [ ] Routeur automatique PDF natif vs photo → **différé Phase 4** (`has_text_layer` prêt)

### Phase 4 — Qualité & UI (non commencée)
- [ ] Routeur automatique natif/photo (via `ingest.has_text_layer`)
- [ ] Gestion multi-pages
- [ ] App Streamlit (dashboard + visualiseur)
- [ ] Durcir la réconciliation (cas sans ligne Total)
- [ ] Doc de déploiement GPU

---

## 🧭 Prochaine action recommandée — **sur le serveur GPU**

```bash
git pull                              # récupérer le harness
pip install -e ".[ai]"                # torch + transformers + pillow
nvidia-smi                            # vérifier ~8-10 Go VRAM libres

# smoke sur 10 photos d'abord (valide inférence + format de sortie)
python scripts/benchmark_nuextract.py --limit 10

# puis le dataset complet + rapport détaillé
python scripts/benchmark_nuextract.py --out report.json
```

→ Tu obtiens la **précision cellule (micro)** et les pires fichiers. Selon le score :
au-dessus de ~90 %, Phase 2 quasi bouclée ; en dessous, on regarde `report.json` (PC)
et on décide template/mapping vs LoRA.

---

## 📌 État Git

- **Branche de travail** : `feat/nuextract-mapping` (5 commits au-dessus de `main`)
  - mapping + template · roadmap resync · moteur d'inférence · fix mypy CI · harness benchmark
- **PR ouverte** : [#4](https://github.com/17Sx/phaxtract/pull/4) → `main`
- **À faire** : merger la PR une fois la CI verte, puis attaquer le benchmark

---

## 📚 Docs de référence

- [ROADMAP.md](ROADMAP.md) — plan des phases + décisions verrouillées
- [SPECIFICATION.md](SPECIFICATION.md) — spec produit complète
- [ARCHITECTURE.md](ARCHITECTURE.md) — principes de conception
- `docs/superpowers/specs/` — design docs par feature (local, gitignoré)
