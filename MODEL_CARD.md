# Model Card — `tuned_random_forest` (rf-phase8-v1)

Full-observation multiclass classification of steel-plate defect type.
Decision-support prototype; not a production system.

| Field | Value |
|---|---|
| Model | `RandomForestClassifier(n_estimators=300, min_samples_leaf=2, max_features="sqrt", max_depth=20, class_weight="balanced", random_state=42, n_jobs=1)` |
| Status | `FINAL_MODEL_STATUS = FROZEN` (selected in Phase 7, evaluated once in Phase 8) |
| Artifact | [`artifacts/model/final_random_forest.joblib`](artifacts/model/final_random_forest.joblib), SHA256 `6f363b2c…0c44e6` |
| Manifest | [`artifacts/manifest.json`](artifacts/manifest.json) (fingerprints of data, split, feature policy, config, policy) |
| Validity scope | `FULL_OBSERVATION_CLASSIFICATION_ONLY` |
| Early prediction supported | `FALSE` |
| Recorded environment | Python 3.13.7, scikit-learn 1.7.1, numpy 2.2.6, pandas 2.3.3, joblib 1.5.1 |

## Intended use

Given the 27 measured attributes of a steel plate **already characterized as
defective**, assign one of seven defect types and expose the probability,
top-2 margin and a development-only review status, so that a quality analyst
can prioritize which classifications to check manually. Intended for portfolio
demonstration, method review and as a template for quality-intelligence work.

## Out-of-scope use

- Predicting whether a plate will be defective (the data contain no good plates).
- Predicting or preventing a defect before it occurs; predictive maintenance.
- Causal statements about which process variables produce a defect.
- Automatic accept/reject decisions, an operational SLA, or use on a different
  plant, product or measurement system without new validation.
- Any financial, scrap or savings claim.

## Dataset

Steel Plates Faults (UCI Machine Learning Repository, Semeion):
1,941 plates, 35 columns, all defective; one-hot target over seven classes.

| Class | Pastry | Z_Scratch | K_Scatch | Stains | Dirtiness | Bumps | Other_Faults |
|---|---:|---:|---:|---:|---:|---:|---:|
| n | 158 | 190 | 391 | 72 | 55 | 402 | 673 |

No timestamp, machine, shift, supplier or production-sequence variables exist.
Audit: [docs/ml/01_dataset_audit.md](docs/ml/01_dataset_audit.md).

## Target

Single defect type per plate (one-hot exclusivity verified). Contract:
[docs/ml/02_problem_contract.md](docs/ml/02_problem_contract.md).

## Features

`FEATURE_SET = FULL_OBSERVATION_FEATURES`, `N_FEATURES = 27` (geometry, luminosity,
conveyer length, steel type, thickness and derived indices). `id` and the seven
target columns are excluded. The temporal availability of these measurements is
**not demonstrated**: some may exist only after inspection, so they are not
"early" or "real-time" features. Leakage audit:
[docs/ml/03_leakage_audit.md](docs/ml/03_leakage_audit.md).

## Validation design

- Stratified split: 1,552 training / 389 final holdout ([split](src/quality_ml/data/split.py)).
- Development: `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)` on training only.
- Baseline → candidates → controlled tuning (12 RF + 12 HGB configurations) → selection
  on development evidence only ([04](docs/ml/04_baseline_evaluation.md),
  [05](docs/ml/05_candidate_models.md), [06](docs/ml/06_tuning_and_selection.md)).
- One final evaluation of the frozen model on the holdout
  ([07](docs/ml/07_final_holdout_evaluation.md)).

Selection note: HistGradientBoosting had higher CV macro-F1 (0.8223 vs 0.8008)
but a much higher out-of-fold high-confidence error rate (13.1% vs 1.9% at
confidence ≥ 0.80) and higher cost. Random Forest was chosen on that Pareto
evidence before the holdout was opened.

Integrity invariants: `HOLDOUT_STATUS = CONSUMED_FINAL_EVALUATION`,
`POST_HOLDOUT_TUNING = FALSE`, `ALTERNATIVE_MODELS_TESTED_ON_HOLDOUT = FALSE`,
`CALIBRATION_PERFORMED = FALSE`, `HOLDOUT_INVALIDATED = FALSE`.

## Cross-validation (development)

Macro-F1 **0.8008 ± 0.0282** (mean ± SD, 5 folds).

## Final holdout (n = 389, evaluated once)

| Metric | Value |
|---|---:|
| Accuracy | 0.7892 |
| Balanced accuracy | 0.8049 |
| Macro precision | 0.8267 |
| Macro recall | 0.8049 |
| **Macro-F1** | **0.8147** |
| Weighted F1 | 0.7917 |
| Log-loss | 0.6893 |

Gap vs CV: +0.0139 macro-F1, consistent with CV; not a significance claim.

## Class behavior (holdout)

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| Pastry | 0.571 | 0.625 | 0.597 | 32 |
| Z_Scratch | 0.971 | 0.868 | 0.917 | 38 |
| K_Scatch | 0.973 | 0.910 | 0.940 | 78 |
| Stains | 0.923 | 0.857 | 0.889 | 14 |
| Dirtiness | 0.909 | 0.909 | 0.909 | 11 |
| Bumps | 0.714 | 0.679 | 0.696 | 81 |
| Other_Faults | 0.726 | 0.785 | 0.754 | 135 |

Stains (14) and Dirtiness (11) have too little support for stable conclusions.

## Known failure modes

- 82 errors / 389. Bumps ↔ Other_Faults accounts for 36 of them
  (Bumps → Other_Faults 21; Other_Faults → Bumps 15).
- Pastry is the weakest class (F1 0.597), confused mainly with Other_Faults.
- Confident mistakes exist: e.g. holdout row 1277 (Other_Faults predicted as
  K_Scatch with confidence 1.0).
- Details: [docs/ml/08 §4–§7, §12](docs/ml/08_error_uncertainty_interpretability.md).

## Uncertainty

No calibrator was fitted. Diagnostics only: top-label ECE 0.091 (OOF) and 0.100
(holdout), multiclass Brier 0.326 / 0.314. Probabilities tend to be
under-confident at the top label; `PROBABILITY_BEHAVIOR = UNCERTAIN`.
Probabilities are not calibrated and must not be read as frequencies.
Artifacts: [reports/ml/uncertainty/](reports/ml/uncertainty/).

## Interpretability

Permutation importance on validation folds (associative, not causal). Stable
leaders: Length_of_Conveyer, Orientation_Index, Edges_Y_Index,
Steel_Plate_Thickness. Correlated features share or mask importance.
Artifacts: [reports/ml/interpretability/](reports/ml/interpretability/).

## Human review

Development-only candidate policy on top-1 confidence: ≥ 0.80 `HIGH_CONFIDENCE`;
0.50–0.80 `REVIEW_REQUIRED`; < 0.50 `LOW_CONFIDENCE` (the last two mean review).
OOF: 478 accepted rows with 9 errors. Post-hoc on the holdout (not a validation):
128 accepted with 1 error; 261 sent to review containing 81 of 82 errors.
`POLICY_STATUS = DEVELOPMENT_ONLY`; no prospective validation, review cost or
reviewer accuracy is known.

## Limitations

- Conditional defect-type classification only; no good-vs-bad detection.
- Random split inherited; batch/entity/temporal independence cannot be shown.
- Small minority classes and segments; review policy not independently validated.
- The pickle stream is byte-identical only in the recorded platform; on other
  platforms the rebuilt forest is verified tree-by-tree identical instead.
- joblib/pickle executes code on load: load only from a trusted checkout.
- No production deployment, monitoring or financial impact is demonstrated.
