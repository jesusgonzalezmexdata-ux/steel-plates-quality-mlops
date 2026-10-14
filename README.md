# Quality intelligence: steel-plate defect classification

[![CI](https://github.com/jesusgonzalezmexdata-ux/steel-plates-quality-mlops-/actions/workflows/ci.yml/badge.svg)](https://github.com/jesusgonzalezmexdata-ux/steel-plates-quality-mlops-/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/jesusgonzalezmexdata-ux/steel-plates-quality-mlops-)](https://github.com/jesusgonzalezmexdata-ux/steel-plates-quality-mlops-/releases)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Data: CC BY 4.0](https://img.shields.io/badge/data-CC%20BY%204.0-lightgrey)](NOTICE)

**English** · [Español](README.es.md)

**An industrial quality problem turned into measurable evidence: a data contract, scientific validation, a model evaluated once on an independent holdout, error analysis and Power BI decision support, all reproducible from this repository.**

## In one minute

| | |
|---|---|
| **Problem** | A quality team needs to know which defect type each inspected plate has, where the classification fails and which cases deserve human review. |
| **Data** | *Steel Plates Faults* (UCI): 1,941 plates, **all defective**, 27 measurements per plate, 7 defect types. No timestamps, machines, shifts or suppliers. |
| **What the model predicts** | Given the measurements of a plate **already characterized as defective**, its defect type among 7 classes (`FULL_OBSERVATION_CLASSIFICATION_ONLY`). |
| **What it does NOT predict** | Whether a plate will be defective, a defect before it happens, or its causes. It is not predictive maintenance or a production system (`EARLY_PREDICTION_SUPPORTED = FALSE`). |
| **Final model** | Frozen Random Forest (300 trees, `class_weight="balanced"`, `random_state=42`), selected with cross-validation only. |
| **Holdout result** | 389 plates never used for any decision: **macro-F1 0.815**, balanced accuracy 0.805, log-loss 0.689. Development CV: macro-F1 0.801 ± 0.028. |
| **Power BI role** | Quality-intelligence layer: defect distribution, COPQ with assumed costs, group control chart, reference Cpk and a model performance and review page. |
| **Evidence** | [Model Card](MODEL_CARD.md) · [Evidence pack](docs/evidence/README.md) · [model manifest](artifacts/manifest.json) |

## From problem to evidence

1. **Measurable formulation.** Problem contract and feature policy: 27 measurements, no `id` or target columns ([contract](docs/ml/02_problem_contract.md), [leakage audit](docs/ml/03_leakage_audit.md)).
2. **Scientific validation.** Stratified 1,552 / 389 split; `StratifiedKFold(5, shuffle=True, random_state=42)` on training only; baseline → candidates → controlled tuning → selection ([04](docs/ml/04_baseline_evaluation.md)–[06](docs/ml/06_tuning_and_selection.md)).
3. **Independent evaluation.** The frozen model was evaluated **once** on the holdout, with no later tuning, no alternative models on the holdout and no calibration ([07](docs/ml/07_final_holdout_evaluation.md)).
4. **Errors and uncertainty.** 82 errors out of 389; the Bumps ↔ Other_Faults confusion explains 36. Pastry is the weakest class (F1 0.60). Probabilities are not calibrated ([08](docs/ml/08_error_uncertainty_interpretability.md)).
5. **Decision support.** Development-only review policy: confidence ≥ 0.80 is accepted, everything else goes to review. Applied post hoc to the holdout, it sends 261 cases to review, which contain 81 of the 82 errors. It is not a validated operating threshold.
6. **Reproducibility.** Model artifact with SHA256 fingerprints of data, split, features and configuration; strict-schema batch inference; SQL data contract; ONNX export; Docker; CI ([09](docs/ml/09_model_lineage_and_batch_inference.md)).

### Per-class performance (holdout)

| Class | Precision | Recall | F1 | n |
|---|---:|---:|---:|---:|
| Pastry | 0.571 | 0.625 | 0.597 | 32 |
| Z_Scratch | 0.971 | 0.868 | 0.917 | 38 |
| K_Scatch | 0.973 | 0.910 | 0.940 | 78 |
| Stains | 0.923 | 0.857 | 0.889 | 14 |
| Dirtiness | 0.909 | 0.909 | 0.909 | 11 |
| Bumps | 0.714 | 0.679 | 0.696 | 81 |
| Other_Faults | 0.726 | 0.785 | 0.754 | 135 |

Stains and Dirtiness have too little support for stable conclusions.

## Quality-intelligence layer (Power BI and Streamlit)

The dashboard answers where to act first on a limited budget, using **assumed** management thresholds and the ISO 9001:2015 clause behind each action:

| Signal | Threshold (management assumption) | Action | ISO 9001:2015 |
|---|---|---|---|
| ≥ 10 % of plates with a defect larger than 500 px² | `UMBRAL_FUERA_USL_PCT` | Contain: segregate and inspect 100 % | 8.7 |
| One type weighs ≥ 20 % of COPQ | `UMBRAL_COPQ_PCT` | Root-cause analysis and corrective action | 10.2 |
| Cpk < 1.00 with no other signal | Reference, not a sole criterion | Monitor and evaluate | 9.1.3 |

Descriptive findings (with **illustrative costs**, not demonstrated savings): three types concentrate 77.7 % of the assumed COPQ; K-scratches account for 267 of the 289 defects ≥ 5,000 px² and are almost confined to A400 steel and thickness 40 (710 of 1,941 plates). Every conclusion was [stress-tested](docs/pruebas_de_estres.md): the top-cost trio holds in 99 % of 2,000 simulations, but the first place does not.

![Dashboard: decisions by defect type](reports/figures/decisiones.png)

- PBIP project in [`powerbi/project/`](powerbi/project/) and PBIX in [`powerbi/artifacts/`](powerbi/artifacts/) (Git LFS: run `git lfs pull` after cloning).
- The *MODEL PERFORMANCE & REVIEW* page and the `ML_Holdout` table were reconciled against Python (389 rows, 307 correct, 82 errors, 261 to review) at export level only: [reconciliation](docs/evidence/powerbi_ml_reconciliation.md).
- **Power BI Desktop runtime validation is pending** (open, refresh, render, save): `POWER_BI_RUNTIME = MANUAL_VALIDATION_REQUIRED`. Exact steps in the [handoff](docs/evidence/powerbi_runtime_handoff.md). The published PBIX does not yet contain the ML page.
- The PBIP `RutaCSV` parameter ships with a placeholder (`C:\path\to\...`); set it in Desktop to `data/raw/steel_plates_faults.csv` in your clone.

## Reproduce

Requires Python 3.13 (recorded environment: 3.13.7) and Git LFS.

```bash
git clone https://github.com/jesusgonzalezmexdata-ux/steel-plates-quality-mlops-.git
cd steel-plates-quality-mlops-
git lfs pull
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

python -B -m tools.project_checks validate-data       # dataset audit (1,941 rows)
python -B -m tools.project_checks validate-artifact   # lineage and SHA256 of the frozen model
python -B -m tools.project_checks batch-smoke         # batch inference (training rows)
python -B -m tools.project_checks validate-evidence   # Power BI export vs. Python evidence
python -B -m pytest -q                                # full suite (~10 min, includes replays)
streamlit run streamlit_app.py                        # equivalent Streamlit dashboard
```

| Extra | Command | What it proves |
|---|---|---|
| SQL data contract (dbt + DuckDB) | `pip install -r requirements-dbt.txt` then `python -B -m tools.data_contract` | 56 checks on names, types, nulls, one-hot targets, class counts, geometry and index ranges, reconciled row by row with pandas ([`dbt/`](dbt/)) |
| ONNX + Node.js | `pip install -r requirements-onnx.txt`, `python -B -m tools.export_onnx --check`, then `cd examples/onnx-node && npm ci && node predict.mjs` | Deterministic ONNX export equivalent to scikit-learn (max probability diff 8.3e-7, same class and review status) and usable from JavaScript ([report](reports/onnx/verification.json)) |
| Docker | `docker build -t steel-plates-quality-mlops .` then `docker run --rm steel-plates-quality-mlops` | Same OS and dependencies on any machine; CI runs the checks and the full suite inside the image |

### Predict on your own CSV

The input needs the 27 feature columns (optionally a unique `row_id`); the schema is validated strictly and fails closed.

```bash
pip install .
steel-predict --root . --input input.csv --output predictions.csv
```

The output contains the predicted class, seven probabilities, top-2 margin and the development-only review status. Load the model only from a trusted checkout: joblib/pickle executes code on load (see [SECURITY.md](SECURITY.md)).

## Limitations

- **Full-observation classification only.** No good plates and no temporal variables; the temporal availability of the 27 measurements is not demonstrated.
- **Consumed holdout.** It is no longer an untouched test set; any new model would need new data.
- **Small classes and a review policy without prospective validation.** Feature importance is associative, not causal; probabilities are not calibrated.
- **Power BI Desktop not validated at runtime**; reconciliation covers the Python export.
- **Assumed costs, specification limit and action thresholds.** No financial impact or production deployment is claimed.
- **Thickness and defect type are confounded**: 99 % of K-scratches fall at thickness 40.

## Contributing

Issues and pull requests are welcome; read [CONTRIBUTING.md](CONTRIBUTING.md) first. Changes to the frozen model, its evidence or the holdout policy are out of scope by design.

## License and citation

- **Code and documentation:** [Apache License 2.0](LICENSE). See [NOTICE](NOTICE).
- **Dataset:** Buscema, M., Terzi, S., & Tastle, W. (2010). *Steel Plates Faults* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5J88N, licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The Apache license does not apply to the data.
- **Cite this repository:** use GitHub's *Cite this repository* button ([CITATION.cff](CITATION.cff)). Version history in the [CHANGELOG](CHANGELOG.md).

---

**Jesús R. L. González** · Data Analyst and Data Scientist · Manufacturing operations and quality · [LinkedIn](https://www.linkedin.com/in/jesus-r-l-gonzalez)
