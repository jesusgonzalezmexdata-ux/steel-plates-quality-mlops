# Baseline evaluation

## Scope

This report evaluates only two preregistered baselines on the 1,552-row
training partition using the five stratified folds from Fase 4. The 389-row
holdout is sealed and is not passed to the evaluation API. No model selection,
calibration, tuning, feature selection or holdout inspection occurs here.

The experiment uses the 27 `FULL_OBSERVATION_FEATURES`. It is a classification
experiment under full observation of the recorded measurements, not evidence of
early inference in a plant.

## Models

| Model | Purpose |
|---|---|
| `DummyClassifier(strategy="most_frequent")` | Naive majority-class reference. It establishes the performance floor expected from always predicting the most common training class. |
| `LogisticRegression` in a `Pipeline(StandardScaler, LogisticRegression)` | Simple linear multiclass baseline. Scaling is fitted independently inside each training fold. |

The primary metric is provisional `macro_f1`. The task has seven classes with
material imbalance; macro-F1 gives each defect class equal weight and prevents
`Other_Faults` from dominating the headline result. Accuracy is retained as a
context metric, not as the sole criterion.

## Reproduction

From the repository root, with the existing environment:

```powershell
$env:PYTHONPATH = "src"
python -m pytest -q tests/test_baseline.py
```

The evaluation functions accept only `X_train`, `y_train` and the five Fase 4
folds. They have no holdout argument and assert the exact 27-feature policy.

## Protocol checks

- holdout accessed: `FALSE`;
- CV folds: 5, shuffled and seeded with `42`;
- target and `id`: absent from `X`;
- transformations: no global transformation; scaling is inside the Logistic
  Regression pipeline;
- probabilities: checked to sum to one when available;
- seven classes: checked in every evaluation fold;
- convergence/warnings: captured and reported rather than hidden.

The metric table and per-class results are generated from the evaluation output
after the authorized baseline run. No result from the sealed holdout is used to
select or compare these baselines.

## Cross-validation results

The following means and sample standard deviations come from the five training
folds. `log_loss` is computed from fold-local probabilities.

| Model | Accuracy | Balanced accuracy | Macro precision | Macro recall | Macro-F1 | Weighted F1 | Log loss |
|---|---:|---:|---:|---:|---:|---:|---:|
| Dummy most frequent | 0.347 ± 0.001 | 0.143 ± 0.000 | 0.050 ± 0.000 | 0.143 ± 0.000 | 0.074 ± 0.000 | 0.178 ± 0.001 | 23.549 ± 0.052 |
| Logistic Regression | 0.714 ± 0.027 | 0.711 ± 0.030 | 0.724 ± 0.019 | 0.711 ± 0.030 | **0.711 ± 0.025** | 0.711 ± 0.026 | 0.769 ± 0.067 |

Per-fold values for the primary metric, balanced accuracy and log loss were:

| Model | Fold 1 | Fold 2 | Fold 3 | Fold 4 | Fold 5 |
|---|---|---|---|---|---|
| Dummy macro-F1 | 0.074 | 0.074 | 0.073 | 0.073 | 0.074 |
| Logistic macro-F1 | 0.685 | 0.712 | 0.736 | 0.688 | 0.736 |
| Dummy balanced accuracy | 0.143 | 0.143 | 0.143 | 0.143 | 0.143 |
| Logistic balanced accuracy | 0.671 | 0.715 | 0.743 | 0.691 | 0.734 |
| Dummy log loss | 23.527 | 23.527 | 23.603 | 23.603 | 23.487 |
| Logistic log loss | 0.790 | 0.847 | 0.752 | 0.788 | 0.666 |

Mean fit time was approximately 0.001 seconds per Dummy fold and 0.059 seconds
per Logistic Regression fold in the local run. No convergence or fit warnings
were captured.

## Per-class behaviour

Mean F1 and recall across the five folds show that the linear baseline does not
perform uniformly across defect types:

| Class | Dummy F1 | Logistic F1 | Logistic recall |
|---|---:|---:|---:|
| `Pastry` | 0.000 | 0.548 | 0.508 |
| `Z_Scratch` | 0.000 | 0.814 | 0.842 |
| `K_Scatch` | 0.000 | 0.928 | 0.930 |
| `Stains` | 0.000 | 0.909 | 0.947 |
| `Dirtiness` | 0.000 | 0.529 | 0.497 |
| `Bumps` | 0.000 | 0.599 | 0.576 |
| `Other_Faults` | 0.515 | 0.654 | 0.675 |

The baseline improves macro-F1 over the naive reference, but the lower recall
for `Dirtiness`, `Pastry` and `Bumps` is a reason to require later error
analysis and uncertainty checks. These results are conditional on full
observation and must not be interpreted as early detection or production
performance.
