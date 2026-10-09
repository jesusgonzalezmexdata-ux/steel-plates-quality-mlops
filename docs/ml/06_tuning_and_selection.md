# Controlled tuning and model selection

## Scope and protocol

This is development CV, not a final generalization estimate. The 389-row
holdout remains sealed and is not an input to search, refit, calibration,
feature selection or comparison. Logistic Regression remains the frozen
incumbent; only Random Forest and HistGradientBoosting were tuned.

```text
FEATURE_SET = FULL_OBSERVATION_FEATURES (27)
CV = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
PRIMARY_METRIC = macro_f1
SEARCH_BUDGET_RF = 12
SEARCH_BUDGET_HGB = 12
HOLDOUT_STATUS = SEALED
HOLDOUT_ACCESSED = FALSE
```

Each search used `RandomizedSearchCV` with the same five precomputed folds,
multi-metric scoring (`macro_f1`, balanced accuracy, negative log-loss and
weighted F1), `refit="macro_f1"`, `random_state=42`, and `n_jobs=1`. The spaces
were fixed before results were observed. No extra algorithm or hidden search
was introduced.

## Best configurations

```text
Random Forest:
  n_estimators=300
  min_samples_leaf=2
  max_features="sqrt"
  max_depth=20
  class_weight="balanced"

HistGradientBoosting:
  min_samples_leaf=20
  max_leaf_nodes=63
  max_iter=200
  learning_rate=0.1
  l2_regularization=1.0
```

The complete 24 sampled configurations and the structured decision are in
[`reports/ml/model_selection/leaderboard.csv`](../../reports/ml/model_selection/leaderboard.csv)
and [`reports/ml/model_selection/selection.json`](../../reports/ml/model_selection/selection.json).

## Development CV results

| Model | Macro-F1 mean ± SD | Balanced accuracy | Log loss | Fit seconds | Predict seconds |
|---|---:|---:|---:|---:|---:|
| Logistic reference | 0.7115 ± 0.0248 | 0.7107 ± 0.0297 | 0.7686 ± 0.0665 | 0.103 ± 0.007 | 0.0033 ± 0.0006 |
| Tuned Random Forest | 0.8008 ± 0.0282 | 0.7932 ± 0.0335 | 0.6319 ± 0.0403 | 1.817 ± 0.166 | 0.0618 ± 0.0075 |
| Tuned HistGradientBoosting | 0.8223 ± 0.0193 | 0.8178 ± 0.0277 | 0.6511 ± 0.0500 | 6.700 ± 1.583 | 0.1573 ± 0.0490 |

These are observed development-fold values. Five folds do not support a claim
of statistical significance or final deployment generalization.

## Paired fold comparison

| Difference | Fold deltas | Mean | SD | Min | Max | Folds won |
|---|---|---:|---:|---:|---:|---:|
| RF - Logistic | +0.082, +0.064, +0.073, +0.131, +0.096 | +0.089 | 0.026 | +0.064 | +0.131 | 5/5 |
| HGB - Logistic | +0.124, +0.111, +0.069, +0.132, +0.118 | +0.111 | 0.024 | +0.069 | +0.132 | 5/5 |
| HGB - RF | +0.042, +0.047, -0.004, +0.001, +0.021 | +0.021 | 0.023 | -0.004 | +0.047 | 4/5 |

HGB improves macro-F1 over RF on four of five folds, with one near-tie/slight
loss. It also has higher fit and prediction cost.

## Per-class development results

| Class | Logistic F1 | Tuned RF F1 | Tuned HGB F1 | Tuned RF recall | Tuned HGB recall |
|---|---:|---:|---:|---:|---:|
| `Pastry` | 0.548 | 0.672 | 0.656 | 0.508 | 0.612 |
| `Z_Scratch` | 0.814 | 0.864 | 0.932 | 0.842 | 0.941 |
| `K_Scatch` | 0.928 | 0.959 | 0.971 | 0.930 | 0.974 |
| `Stains` | 0.909 | 0.891 | 0.942 | 0.947 | 0.965 |
| `Dirtiness` | 0.529 | 0.857 | 0.853 | 0.497 | 0.819 |
| `Bumps` | 0.599 | 0.649 | 0.662 | 0.576 | 0.664 |
| `Other_Faults` | 0.654 | 0.714 | 0.740 | 0.675 | 0.749 |

Both tuned candidates improve the weak Logistic performance on `Pastry`,
`Dirtiness` and `Bumps`. The result does not imply that every operational
segment is equally reliable.

## Probability behaviour and high-confidence errors

No calibration was performed. OOF diagnostics use a fixed descriptive
threshold of 0.80 on the five training folds:

| Model | Mean confidence | 90th percentile | High-confidence rows | High-confidence errors | Error rate |
|---|---:|---:|---:|---:|---:|
| Tuned RF | 0.680 | 0.9967 | 478 | 9 | 1.9% |
| Tuned HGB | 0.897 | 0.9999 | 1,219 | 160 | 13.1% |

HGB improves classification while producing much more concentrated
probabilities and substantially more high-confidence errors. This is evidence
of an uncertainty limitation, not a reason to calibrate inside this phase.
Calibration belongs to Fase 9.

## Selection decision

The selection uses Pareto evidence rather than a weighted score:

- Tuned Random Forest: `SELECTABLE`. It improves macro-F1 and balanced
  accuracy over Logistic, has the best log-loss, and has lower complexity than
  HGB.
- Tuned HistGradientBoosting: `SELECTABLE_WITH_LIMITATION`. It has the highest
  macro-F1 and balanced accuracy, but its OOF high-confidence error rate and
  cost are materially higher than RF.
- Logistic Regression: `INCUMBENT_REFERENCE`.

`FINAL_MODEL_CANDIDATE = tuned_random_forest` is frozen for the next phase.
Its configuration is the RF configuration above. This is a development choice
under full observation; the holdout remains sealed and no hyperparameter may be
changed using it.

## Reproducibility and limitations

The ML tests pass with the fixed spaces, budgets, folds, feature policy,
probability checks and no-calibration assertions. The full repository suite
also passes after installing the already declared `streamlit` and `duckdb`
dependencies. The joblib CPU detection warning is environmental and was
recorded. Hardware timings are descriptive for this environment, not a
production SLA.
