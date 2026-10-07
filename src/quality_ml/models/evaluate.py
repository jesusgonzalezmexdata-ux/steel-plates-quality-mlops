"""Cross-validated baseline evaluation on training data only."""

from __future__ import annotations

import time
import warnings
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    log_loss,
    precision_recall_fscore_support,
    precision_score,
    recall_score,
)

from quality_ml.data.audit import TARGET_COLUMNS
from quality_ml.models.baseline import PRIMARY_METRIC, build_baselines, validate_feature_matrix

METRIC_NAMES = (
    "accuracy",
    "balanced_accuracy",
    "macro_precision",
    "macro_recall",
    "macro_f1",
    "weighted_f1",
    "log_loss",
)


def _metrics(
    y_true: pd.Series,
    y_pred: np.ndarray,
    probabilities: np.ndarray | None,
    probability_labels: list[str] | None = None,
) -> dict[str, float | None]:
    values: dict[str, float | None] = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "macro_precision": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "macro_recall": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "log_loss": None,
    }
    if probabilities is not None:
        values["log_loss"] = float(
            log_loss(y_true, probabilities, labels=probability_labels or list(TARGET_COLUMNS))
        )
    return values


def evaluate_model_cv(
    name: str,
    model: object,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    cv_splits: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...],
) -> dict[str, Any]:
    """Evaluate a model on the supplied training folds; no holdout argument exists."""

    validate_feature_matrix(list(X_train.columns))
    if set(y_train) != set(TARGET_COLUMNS):
        raise ValueError("Baseline evaluation requires all seven target classes")
    if len(cv_splits) != 5:
        raise ValueError("Baseline evaluation requires the five Fase 4 folds")

    fold_metrics: list[dict[str, float | None]] = []
    fold_per_class: list[dict[str, dict[str, float | int]]] = []
    warning_messages: list[str] = []
    fit_times: list[float] = []
    predict_times: list[float] = []
    for fold_number, (train_idx, valid_idx) in enumerate(cv_splits, start=1):
        estimator = clone(model)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            started = time.perf_counter()
            estimator.fit(X_train.iloc[list(train_idx)], y_train.iloc[list(train_idx)])
            fit_times.append(time.perf_counter() - started)
        warning_messages.extend(f"fold {fold_number}: {item.message}" for item in caught)

        X_valid = X_train.iloc[list(valid_idx)]
        y_valid = y_train.iloc[list(valid_idx)]
        prediction_started = time.perf_counter()
        y_pred = estimator.predict(X_valid)
        probabilities = estimator.predict_proba(X_valid) if hasattr(estimator, "predict_proba") else None
        predict_times.append(time.perf_counter() - prediction_started)
        if probabilities is not None and not np.allclose(probabilities.sum(axis=1), 1.0, atol=1e-6):
            raise AssertionError("Predicted probabilities must sum to one")
        probability_labels = list(getattr(estimator, "classes_", TARGET_COLUMNS))
        fold_metrics.append(_metrics(y_valid, y_pred, probabilities, probability_labels))
        precision, recall, f1, support = precision_recall_fscore_support(
            y_valid, y_pred, labels=list(TARGET_COLUMNS), zero_division=0
        )
        fold_per_class.append(
            {
                label: {
                    "precision": float(precision[index]),
                    "recall": float(recall[index]),
                    "f1": float(f1[index]),
                    "support": int(support[index]),
                }
                for index, label in enumerate(TARGET_COLUMNS)
            }
        )

    means: dict[str, float | None] = {}
    stds: dict[str, float | None] = {}
    for metric in METRIC_NAMES:
        values = [row[metric] for row in fold_metrics if row[metric] is not None]
        means[metric] = float(np.mean(values)) if values else None
        stds[metric] = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0

    return {
        "model": name,
        "primary_metric": PRIMARY_METRIC,
        "fold_metrics": fold_metrics,
        "metrics_mean": means,
        "metrics_std": stds,
        "per_class_by_fold": fold_per_class,
        "warnings": warning_messages,
        "fit_time_seconds_mean": float(np.mean(fit_times)),
        "fit_time_seconds_std": float(np.std(fit_times, ddof=1)),
        "predict_time_seconds_mean": float(np.mean(predict_times)),
        "predict_time_seconds_std": float(np.std(predict_times, ddof=1)),
        "n_folds": len(cv_splits),
        "holdout_accessed": False,
    }


def evaluate_models_cv(
    models: dict[str, object],
    X_train: pd.DataFrame,
    y_train: pd.Series,
    cv_splits: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...],
) -> dict[str, dict[str, Any]]:
    """Evaluate a fixed model dictionary using only training data and CV folds."""

    return {
        name: evaluate_model_cv(name, model, X_train, y_train, cv_splits)
        for name, model in models.items()
    }


def evaluate_baselines(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    cv_splits: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...],
    random_state: int = 42,
) -> dict[str, dict[str, Any]]:
    """Evaluate registered baselines using only X_train, y_train and CV folds."""

    return evaluate_models_cv(build_baselines(random_state=random_state), X_train, y_train, cv_splits)
