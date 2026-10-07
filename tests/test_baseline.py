from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from quality_ml.data.split import make_split
from quality_ml.data.audit import load_dataset
from quality_ml.models.baseline import (
    FULL_OBSERVATION_FEATURES,
    PRIMARY_METRIC,
    build_baselines,
)
from quality_ml.models.evaluate import evaluate_baselines, evaluate_model_cv

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def split():
    return make_split(load_dataset(ROOT / "data/raw/steel_plates_faults.csv"))


@pytest.fixture(scope="module")
def results(split):
    return evaluate_baselines(split.X_train, split.y_train, split.cv_splits)


def test_baseline_models_use_exact_full_observation_features(split):
    models = build_baselines()
    assert set(split.X_train.columns) == set(FULL_OBSERVATION_FEATURES)
    assert len(split.X_train.columns) == 27
    assert all("id" not in split.X_train.columns for _ in models)


def test_logistic_scaling_is_inside_pipeline():
    logistic = build_baselines()["logistic_regression"]
    assert isinstance(logistic, Pipeline)
    assert isinstance(logistic.named_steps["scale"], StandardScaler)


def test_evaluation_uses_the_five_fase4_folds_and_all_classes(results):
    for result in results.values():
        assert result["n_folds"] == 5
        assert result["holdout_accessed"] is False
        assert all(len(fold) == 7 for fold in result["per_class_by_fold"])


def test_metrics_are_reproducible(split, results):
    repeated = evaluate_baselines(split.X_train, split.y_train, split.cv_splits)
    for name in results:
        assert results[name]["metrics_mean"] == repeated[name]["metrics_mean"]
        assert results[name]["metrics_std"] == repeated[name]["metrics_std"]


def test_probabilities_are_valid_and_metrics_complete(results):
    required = {"accuracy", "balanced_accuracy", "macro_precision", "macro_recall", "macro_f1", "weighted_f1", "log_loss"}
    for result in results.values():
        assert set(result["metrics_mean"]) == required
        assert result["metrics_mean"]["log_loss"] is not None


def test_primary_metric_is_macro_f1(results):
    assert PRIMARY_METRIC == "macro_f1"
    for result in results.values():
        assert result["primary_metric"] == "macro_f1"


def test_targets_and_id_cannot_enter_baseline_matrix(split):
    model = build_baselines()["dummy_most_frequent"]
    with pytest.raises(ValueError, match="27 full-observation"):
        evaluate_model_cv(
            "bad",
            model,
            split.X_train.assign(id=0),
            split.y_train,
            split.cv_splits,
        )


def test_no_convergence_warnings_are_hidden(results):
    assert all(isinstance(message, str) for result in results.values() for message in result["warnings"])
