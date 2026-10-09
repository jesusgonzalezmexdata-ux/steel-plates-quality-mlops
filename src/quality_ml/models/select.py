"""Pareto-style development selection and OOF probability diagnostics."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone

from quality_ml.data.audit import TARGET_COLUMNS
from quality_ml.models.baseline import validate_feature_matrix

HIGH_CONFIDENCE_ERROR_RATE_LIMIT = 0.05


def oof_probability_summary(
    model: object,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    cv_splits: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...],
    high_confidence_threshold: float = 0.80,
) -> dict[str, Any]:
    """Generate fold-local OOF confidence diagnostics on training only."""

    validate_feature_matrix(list(X_train.columns))
    probabilities = np.zeros((len(X_train), len(TARGET_COLUMNS)), dtype=float)
    predictions = np.empty(len(X_train), dtype=object)
    seen = np.zeros(len(X_train), dtype=bool)
    for train_idx, valid_idx in cv_splits:
        estimator = clone(model)
        estimator.fit(X_train.iloc[list(train_idx)], y_train.iloc[list(train_idx)])
        valid = list(valid_idx)
        proba = estimator.predict_proba(X_train.iloc[valid])
        classes = list(estimator.classes_)
        for column, label in enumerate(TARGET_COLUMNS):
            probabilities[valid, column] = proba[:, classes.index(label)]
        predictions[valid] = estimator.predict(X_train.iloc[valid])
        seen[valid] = True
    if not seen.all():
        raise AssertionError("OOF diagnostics must cover every training row exactly once")
    confidence = probabilities.max(axis=1)
    correct = predictions == y_train.to_numpy()
    high = confidence >= high_confidence_threshold
    return {
        "n_rows": int(len(y_train)),
        "confidence_mean": float(confidence.mean()),
        "confidence_std": float(confidence.std(ddof=1)),
        "confidence_quantiles": {
            str(q): float(np.quantile(confidence, q)) for q in (0.5, 0.9, 0.95, 0.99)
        },
        "high_confidence_threshold": high_confidence_threshold,
        "high_confidence_rows": int(high.sum()),
        "high_confidence_error_rows": int((high & ~correct).sum()),
        "high_confidence_error_rate": float((high & ~correct).sum() / high.sum()) if high.any() else 0.0,
        "overall_error_rate": float((~correct).mean()),
        "probability_rows_sum_to_one": bool(np.allclose(probabilities.sum(axis=1), 1.0, atol=1e-6)),
        "probabilities_finite": bool(np.isfinite(probabilities).all()),
        "holdout_accessed": False,
    }


def classify_candidates(
    evaluations: dict[str, dict[str, Any]],
    probability_summaries: dict[str, dict[str, Any]] | None = None,
) -> dict[str, str]:
    """Classify candidates without a weighted score or holdout information."""

    incumbent = evaluations["logistic_regression"]["metrics_mean"]
    statuses: dict[str, str] = {"logistic_regression": "INCUMBENT_REFERENCE"}
    for name in ("tuned_random_forest", "tuned_hist_gradient_boosting"):
        metrics = evaluations[name]["metrics_mean"]
        primary_better = metrics["macro_f1"] > incumbent["macro_f1"]
        balanced_better = metrics["balanced_accuracy"] >= incumbent["balanced_accuracy"]
        log_loss_no_worse = metrics["log_loss"] <= incumbent["log_loss"]
        high_confidence_limited = bool(
            probability_summaries
            and probability_summaries.get(name, {}).get("high_confidence_error_rate", 0.0)
            > HIGH_CONFIDENCE_ERROR_RATE_LIMIT
        )
        if primary_better and balanced_better and log_loss_no_worse and not high_confidence_limited:
            statuses[name] = "SELECTABLE"
        elif primary_better and balanced_better:
            statuses[name] = "SELECTABLE_WITH_LIMITATION"
        else:
            statuses[name] = "DOMINATED"
    return statuses


def choose_final_candidate(
    evaluations: dict[str, dict[str, Any]],
    statuses: dict[str, str],
) -> str:
    """Choose by Pareto evidence; never combine metrics into an arbitrary score."""

    selectable = [name for name, status in statuses.items() if status == "SELECTABLE"]
    limited = [name for name, status in statuses.items() if status == "SELECTABLE_WITH_LIMITATION"]
    pool = selectable or limited
    if not pool:
        return "logistic_regression"
    return max(
        pool,
        key=lambda name: (
            evaluations[name]["metrics_mean"]["macro_f1"],
            evaluations[name]["metrics_mean"]["balanced_accuracy"],
        ),
    )
