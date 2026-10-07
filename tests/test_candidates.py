from pathlib import Path

import numpy as np
import pytest
from sklearn.pipeline import Pipeline

from quality_ml.data.audit import TARGET_COLUMNS, load_dataset
from quality_ml.data.split import make_split
from quality_ml.models.baseline import FULL_OBSERVATION_FEATURES
from quality_ml.models.candidates import (
    HIST_GRADIENT_BOOSTING_CONFIG,
    RANDOM_FOREST_CONFIG,
    build_candidate_models,
    compare_to_logistic,
)
from quality_ml.models.evaluate import evaluate_models_cv

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def split():
    return make_split(load_dataset(ROOT / "data/raw/steel_plates_faults.csv"))


@pytest.fixture(scope="module")
def results(split):
    return evaluate_models_cv(build_candidate_models(), split.X_train, split.y_train, split.cv_splits)


def test_exactly_three_families_and_frozen_configs():
    models = build_candidate_models()
    assert list(models) == ["logistic_regression", "random_forest", "hist_gradient_boosting"]
    assert RANDOM_FOREST_CONFIG["random_state"] == 42
    assert RANDOM_FOREST_CONFIG["n_estimators"] == 300
    assert HIST_GRADIENT_BOOSTING_CONFIG["random_state"] == 42
    assert not any("Search" in type(model).__name__ for model in models.values())


def test_logistic_incumbent_and_tree_preprocessing(split):
    models = build_candidate_models()
    assert isinstance(models["logistic_regression"], Pipeline)
    assert not isinstance(models["random_forest"], Pipeline)
    assert not isinstance(models["hist_gradient_boosting"], Pipeline)
    assert set(split.X_train.columns) == set(FULL_OBSERVATION_FEATURES)
    assert len(split.X_train.columns) == 27
    assert "id" not in split.X_train.columns
    assert not set(TARGET_COLUMNS) & set(split.X_train.columns)


def test_same_fase4_folds_and_holdout_unavailable(split, results):
    assert all(result["n_folds"] == 5 for result in results.values())
    assert all(result["holdout_accessed"] is False for result in results.values())
    assert all(set(split.y_train) == set(TARGET_COLUMNS) for _ in results)


def test_candidate_probabilities_and_metrics_are_valid(results):
    required = {"accuracy", "balanced_accuracy", "macro_precision", "macro_recall", "macro_f1", "weighted_f1", "log_loss"}
    for result in results.values():
        assert set(result["metrics_mean"]) == required
        assert result["metrics_mean"]["log_loss"] is not None
        assert len(result["per_class_by_fold"]) == 5
        assert all(set(fold) == set(TARGET_COLUMNS) for fold in result["per_class_by_fold"])


def test_candidate_results_are_reproducible(split, results):
    repeated = evaluate_models_cv(build_candidate_models(), split.X_train, split.y_train, split.cv_splits)
    for name in results:
        assert results[name]["metrics_mean"] == repeated[name]["metrics_mean"]
        assert results[name]["metrics_std"] == repeated[name]["metrics_std"]


def test_pairwise_comparison_has_five_deltas(results):
    comparison = compare_to_logistic(results)
    assert set(comparison) == {"random_forest", "hist_gradient_boosting"}
    for value in comparison.values():
        assert len(value["delta_macro_f1_vs_logistic_by_fold"]) == 5
        assert value["min_delta"] <= value["mean_delta"] <= value["max_delta"]
        assert value["status"] in {"PROMISING", "NOT_COMPETITIVE", "UNSTABLE"}


def test_no_global_preprocessing_or_search_symbols():
    source = (ROOT / "src/quality_ml/models/candidates.py").read_text(encoding="utf-8")
    assert "GridSearchCV" not in source
    assert "RandomizedSearchCV" not in source
