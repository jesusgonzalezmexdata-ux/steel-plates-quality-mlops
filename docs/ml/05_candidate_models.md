# Candidate model comparison

## Frozen comparison protocol

This phase compares exactly three families under the same Fase 4 protocol:

1. the incumbent Logistic Regression pipeline;
2. one declared Random Forest configuration;
3. one declared HistGradientBoosting configuration.

All models use the 27 `FULL_OBSERVATION_FEATURES`, the same five stratified
folds, and `random_state=42` where supported. The 389-row holdout remains
sealed. No tuning, feature selection, calibration or alternative fold
generation is performed.

The question is whether either non-linear family produces a reproducible,
stable and relevant improvement over the frozen Logistic baseline. A larger
mean score alone does not automatically make a final model.

## Configurations declared before evaluation

```text
Logistic Regression:
  Pipeline(StandardScaler, LogisticRegression(solver="lbfgs",
  max_iter=2000, random_state=42))

Random Forest:
  RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=1,
  class_weight=None, max_depth=None, min_samples_leaf=1)

HistGradientBoosting:
  HistGradientBoostingClassifier(max_iter=200, learning_rate=0.1,
  max_leaf_nodes=31, min_samples_leaf=20, l2_regularization=0.0,
  random_state=42)
```

`class_weight=None` is explicit for Random Forest: no class-weight variant is
explored in this phase. The tree models receive no scaler because their split
rules do not require one. Logistic scaling remains inside its pipeline and is
fit independently per fold.

## Reproduction and safeguards

```powershell
$env:PYTHONPATH = "src"
python -m pytest -q tests/test_candidates.py
```

The candidate evaluator accepts only `X_train`, `y_train` and the frozen CV
folds. It has no holdout parameter. It asserts the feature policy, seven
classes, five folds and finite probability rows. It records fold metrics,
per-class precision/recall/F1, fit and prediction times, and warnings.

The comparison labels a candidate `PROMISING`, `NOT_COMPETITIVE` or `UNSTABLE`
using fixed rules declared in `candidates.py` before metrics are observed. The
rules require a mean macro-F1 gain of at least 0.01, no negative fold delta,
no material balanced-accuracy drop and bounded variability for `PROMISING`.
They do not select a final model; final selection belongs to a later controlled
tuning phase.

## Results on training folds

All values are mean +/- sample standard deviation across the same five folds.

| Model | Macro-F1 | Balanced accuracy | Log loss | Fit seconds | Predict seconds |
|---|---:|---:|---:|---:|---:|
| Logistic Regression | 0.711 +/- 0.025 | 0.711 +/- 0.030 | 0.769 +/- 0.067 | 0.074 +/- 0.006 | 0.0025 +/- 0.0002 |
| Random Forest | 0.792 +/- 0.012 | 0.777 +/- 0.026 | 0.632 +/- 0.048 | 1.492 +/- 0.019 | 0.0528 +/- 0.0028 |
| HistGradientBoosting | 0.815 +/- 0.013 | 0.805 +/- 0.011 | 1.056 +/- 0.084 | 5.906 +/- 0.598 | 0.1402 +/- 0.0298 |

The complete evaluator also reports accuracy, macro precision, macro recall and
weighted F1 for every fold. The five macro-F1 values were:

| Model | Fold 1 | Fold 2 | Fold 3 | Fold 4 | Fold 5 |
|---|---:|---:|---:|---:|---:|
| Logistic Regression | 0.685 | 0.712 | 0.736 | 0.688 | 0.736 |
| Random Forest | 0.773 | 0.788 | 0.796 | 0.796 | 0.805 |
| HistGradientBoosting | 0.813 | 0.829 | 0.800 | 0.827 | 0.805 |

## Paired comparison with Logistic Regression

The fold-matched macro-F1 deltas versus Logistic Regression are:

| Candidate | Fold deltas | Mean delta | Min delta | Max delta | Status |
|---|---|---:|---:|---:|---|
| Random Forest | +0.089, +0.076, +0.060, +0.108, +0.069 | +0.080 | +0.060 | +0.108 | `PROMISING` |
| HistGradientBoosting | +0.128, +0.117, +0.064, +0.138, +0.069 | +0.103 | +0.064 | +0.138 | `PROMISING` |

Both non-linear candidates improve macro-F1 and balanced accuracy on every
fold under the frozen protocol. This is an observed, reproducible comparison,
not a claim of statistical significance from five folds. HistGradientBoosting
has the strongest classification scores but its log loss is worse than both
Logistic Regression and Random Forest, and its measured fit/predict cost is
higher.

## Per-class comparison

Mean F1 and recall across folds are:

| Class | Logistic F1 | Random Forest F1 | HistGradientBoosting F1 | Logistic recall | RF recall | HGB recall |
|---|---:|---:|---:|---:|---:|---:|
| `Pastry` | 0.548 | 0.615 | 0.632 | 0.508 | 0.524 | 0.596 |
| `Z_Scratch` | 0.814 | 0.868 | 0.938 | 0.842 | 0.842 | 0.941 |
| `K_Scatch` | 0.928 | 0.966 | 0.971 | 0.930 | 0.949 | 0.968 |
| `Stains` | 0.909 | 0.897 | 0.947 | 0.947 | 0.912 | 0.947 |
| `Dirtiness` | 0.529 | 0.840 | 0.833 | 0.497 | 0.819 | 0.775 |
| `Bumps` | 0.599 | 0.638 | 0.656 | 0.576 | 0.630 | 0.676 |
| `Other_Faults` | 0.654 | 0.719 | 0.727 | 0.675 | 0.764 | 0.730 |

Random Forest substantially improves `Dirtiness` recall, while
HistGradientBoosting improves `Pastry`, `Z_Scratch`, `K_Scatch` and `Bumps`.
Neither result authorizes a final model choice; the trade-off between class
coverage, probability loss, complexity and future calibration remains for the
controlled selection phase.

## Warnings and interpretation

No convergence or schema warnings were captured. HistGradientBoosting produced
one environment warning from joblib about detecting physical CPU cores and
falling back to logical cores; it was recorded in the result object. It does
not indicate target leakage or a model failure, but it is retained for
reproducibility.

`PROMISING` here means a fixed, predeclared rule was met: positive macro-F1
delta on every fold, at least 0.01 mean improvement, no material balanced-
accuracy drop and bounded variability. It does not select `FINAL_MODEL` and it
does not authorize opening the holdout.
