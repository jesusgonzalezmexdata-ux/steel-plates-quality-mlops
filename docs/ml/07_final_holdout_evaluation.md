# Final holdout evaluation

## Frozen protocol and preflight

Phase 8 estimates the final performance of the Phase 7 selection. It does not
select a model. The model and feature set were frozen before holdout evaluation.

- Branch: `feat/quality-mlops-platform`.
- Phase 7 checkpoint: `52132ddd052e3fde4a8dd846c5268abaf742fa69`.
- Phase 7 state checkpoint and initial HEAD:
  `0e9722aaf78e65ae1613dca155eaab5e3388de27`.
- Initial `git status --porcelain=v1`: empty (CLEAN).
- Initial `git diff --check`: exit 0 (PASS).
- Initial documented status: `SEALED`, `holdout_accessed=false` in selection.json.
- Candidate: `tuned_random_forest`.
- Features: `FULL_OBSERVATION_FEATURES`, 27 columns in original dataset order;
  all seven target columns and the technical identifier are excluded.

```python
RandomForestClassifier(
    n_estimators=300,
    min_samples_leaf=2,
    max_features="sqrt",
    max_depth=20,
    class_weight="balanced",
    random_state=42,
    n_jobs=1,
)
```

The exception `git -c safe.directory=<local checkout path>`
is scoped to individual commands. No persistent Git configuration, Windows
ownership, directory permission, or global setting is changed.

## Meaning of the sealed holdout

The repository stores one original CSV, not a physically isolated holdout file.
Phase 4 already used all target labels for stratification and the existing split
tests inspect class presence and sizes. Here, "first access" means the first final
predictive evaluation, not the first historical byte read of those observations.
No previous holdout model evaluation is recorded in the frozen Phase 7 evidence.

The final evaluator reconstructs exactly the existing stratified 80/20 split
using target columns only, `random_state=42`, and sorted original row positions.
It loads only training rows for the single fit. Only after that fit does it load
holdout measurements, invoke `predict_proba` once, and derive predictions from
its argmax using the estimator's class order (the same rule as RF.predict).
No additional CV is used to choose or modify the final model.

The output directory is an exclusive persistent reservation. Consumption is
recorded before holdout measurements are loaded. A second invocation refuses to
run; there is no force/overwrite option. Failure after opening the holdout leaves
the reservation and records invalidation. Never remove this guard to retry.

## DEVELOPMENT CV RESULTS

Frozen Phase 7 evidence, not recalculated for the final comparison:

| Metric | Value |
|---|---:|
| Macro-F1 mean | 0.8008 |
| Macro-F1 standard deviation across five folds | 0.0282 |

## FINAL HOLDOUT RESULTS

One fit on all **1,552 training rows**, followed by one probability prediction
on **389 holdout rows**, with **27 features**. The execution ledger records
`fit_calls=1`, `prediction_calls=1`, and `completed=true`.

| Metric | Final holdout value |
|---|---:|
| Accuracy | 0.7892030848 |
| Balanced accuracy | 0.8048726800 |
| Macro precision | 0.8267286415 |
| Macro recall | 0.8048726800 |
| Macro-F1 (primary) | 0.8146728102 |
| Weighted F1 | 0.7917125646 |
| Log-loss | 0.6893136714 |

### Per-class results

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| Pastry | 0.571429 | 0.625000 | 0.597015 | 32 |
| Z_Scratch | 0.970588 | 0.868421 | 0.916667 | 38 |
| K_Scatch | 0.972603 | 0.910256 | 0.940397 | 78 |
| Stains | 0.923077 | 0.857143 | 0.888889 | 14 |
| Dirtiness | 0.909091 | 0.909091 | 0.909091 | 11 |
| Bumps | 0.714286 | 0.679012 | 0.696203 | 81 |
| Other_Faults | 0.726027 | 0.785185 | 0.754448 | 135 |

Pastry and Bumps remain the lowest-F1 classes. Stains and Dirtiness have only
14 and 11 observations, respectively, so their apparently strong results have
limited support. These observations do not trigger model changes.

### Confusion matrix

Rows are actual classes; columns are predictions, in the same order below.

| Actual / predicted | Pastry | Z_Scratch | K_Scatch | Stains | Dirtiness | Bumps | Other_Faults |
|---|---:|---:|---:|---:|---:|---:|---:|
| Pastry | 20 | 0 | 0 | 0 | 0 | 3 | 9 |
| Z_Scratch | 0 | 33 | 1 | 0 | 0 | 2 | 2 |
| K_Scatch | 0 | 0 | 71 | 0 | 0 | 1 | 6 |
| Stains | 0 | 0 | 0 | 12 | 0 | 1 | 1 |
| Dirtiness | 0 | 0 | 0 | 0 | 10 | 0 | 1 |
| Bumps | 4 | 0 | 0 | 0 | 1 | 55 | 21 |
| Other_Faults | 11 | 1 | 1 | 1 | 0 | 15 | 106 |

### Generalization and probabilities

`GENERALIZATION_GAP = 0.8146728101764369 - 0.8008 = +0.013872810176436934`.
`GENERALIZATION_ASSESSMENT = CONSISTENT`: the holdout macro-F1 is modestly
higher than the frozen CV mean, with no observed degradation on the primary
metric. This is a cautious qualitative description, not a significance claim
or a category determined by a new numerical threshold. The CV standard deviation
0.0282 describes fold variation; it is not a confidence bound for this comparison.

`predict_proba` is available. Its output is `(389, 7)`, all values are finite
and within [0, 1], and row sums equal 1 within absolute tolerance `1e-12`.
Probabilities have not been calibrated and the log-loss is reported without
suppressing any class or observation.

Artifacts under [`reports/ml/final_holdout`](../../reports/ml/final_holdout):

- [predictions.csv](../../reports/ml/final_holdout/predictions.csv)
- [metrics.json](../../reports/ml/final_holdout/metrics.json)
- [confusion_matrix.csv](../../reports/ml/final_holdout/confusion_matrix.csv)
- [probabilities_snapshot.csv](../../reports/ml/final_holdout/probabilities_snapshot.csv)
- [execution.json](../../reports/ml/final_holdout/execution.json), including SHA-256
  checksums and the consumption ledger.

Environment: Python 3.13.7, NumPy 2.2.6, pandas 2.3.3, scikit-learn 1.7.1.

## Reproducibility and interpretation

The sole real-data entry point is:

```powershell
$env:PYTHONPATH = 'src;.'
python -B -m quality_ml.models.final_holdout --execute-final-once
```

This command is for the original authorized execution only. After consumption,
inspect the saved predictions and metrics; do not rerun fitting or inference.
`row_index` is the zero-based original CSV data-row position, not a predictor.
The predictions artifact includes actual/predicted labels, correctness, maximum
probability, and seven explicitly named probability columns. Log-loss uses
probabilities ordered to match sorted class labels. A raw probability snapshot
preserves the output of the sole inference call before scoring.

The reported generalization gap is holdout macro-F1 minus **0.8008**, the requested
rounded frozen reference. Any qualitative assessment is descriptive. The CV fold
standard deviation is not a confidence interval or a predeclared hypothesis-test
threshold. There was no predeclared numerical cutoff for degradation categories.

There is no confidence decision policy. The Phase 7 threshold 0.80 remains
exploratory and is neither optimized nor applied to holdout decision-making.

## Validation and limits

New evaluation tests use synthetic data only. The complete inherited suite also
runs its existing training-only CV/search regression tests; those test results
are not selection evidence and do not update Phase 7 artifacts or the candidate.
The full suite passed **68 tests in 613.91 seconds**, before opening the final
holdout, with `python -B -m pytest -q -p no:cacheprovider` and `PYTHONPATH=src;.`.
The 21 new tests also passed separately. No software was installed or updated.
Independent verification from the saved predictions reproduced all seven
metrics, per-class results and the confusion matrix; row identifiers matched
the reserved holdout partition and were disjoint from training. All execution
artifact SHA-256 checksums matched. This verification performed no model fitting
or inference. `git diff --check` passed and Power BI had no differences from
the Phase 7 state checkpoint before committing.

```text
VALIDITY_SCOPE = FULL_OBSERVATION_CLASSIFICATION_ONLY
EARLY_PREDICTION_SUPPORTED = FALSE
POST_HOLDOUT_TUNING = FALSE
ALTERNATIVE_MODELS_TESTED_ON_HOLDOUT = FALSE
CALIBRATION_PERFORMED = FALSE
HOLDOUT_FIRST_ACCESS = TRUE
HOLDOUT_STATUS = CONSUMED_FINAL_EVALUATION
HOLDOUT_ACCESSED = TRUE
HOLDOUT_INVALIDATED = FALSE
VERDICT = PASS_WITH_LIMITATION
```

No post-holdout tuning, feature selection, calibration, threshold change, or
alternative-model evaluation is permitted. Error observations can inform a
separately authorized Phase 9 analysis, not a new configuration selected on
this holdout. Phase 9 is not started here.

The limitation is full-observation classification only, uneven per-class
performance, small minority-class supports, and the logical (not physical)
holdout sealing described above. This evaluation does not establish early
prediction, deployment readiness, or calibrated confidence.
