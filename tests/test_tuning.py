from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import StratifiedKFold

from quality_ml.data.audit import TARGET_COLUMNS, load_dataset
from quality_ml.data.split import make_split
from quality_ml.models.baseline import FULL_OBSERVATION_FEATURES
from quality_ml.models.select import oof_probability_summary
from quality_ml.models.tuning import (
    HGB_SEARCH_SPACE,
    RF_SEARCH_SPACE,
    SEARCH_BUDGET_HGB,
    SEARCH_BUDGET_RF,
    run_controlled_searches,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def split():
    return make_split(load_dataset(ROOT / "data/raw/steel_plates_faults.csv"))


@pytest.fixture(scope="module")
def searches(split):
    return run_controlled_searches(split.X_train, split.y_train, split.cv_splits)


def test_only_rf_and_hgb_are_tuned(searches):
    assert set(searches) == {"random_forest", "hist_gradient_boosting"}
    assert all(search.refit == "macro_f1" for search in searches.values())


def test_budgets_and_spaces_are_frozen(searches):
    assert SEARCH_BUDGET_RF == SEARCH_BUDGET_HGB == 12
    assert len(searches["random_forest"].cv_results_["params"]) == SEARCH_BUDGET_RF
    assert len(searches["hist_gradient_boosting"].cv_results_["params"]) == SEARCH_BUDGET_HGB
    assert set(RF_SEARCH_SPACE) == {"n_estimators", "max_depth", "min_samples_leaf", "max_features", "class_weight"}
    assert set(HGB_SEARCH_SPACE) == {"learning_rate", "max_iter", "max_leaf_nodes", "min_samples_leaf", "l2_regularization"}


def test_search_uses_exact_features_and_five_folds(split, searches):
    assert set(split.X_train.columns) == set(FULL_OBSERVATION_FEATURES)
    assert len(split.X_train.columns) == 27
    assert "id" not in split.X_train.columns
    assert not set(TARGET_COLUMNS) & set(split.X_train.columns)
    assert all(len(search.cv) == 5 for search in searches.values())


def test_best_parameters_and_scores_are_reproducible_on_small_fixture():
    rng = np.random.default_rng(42)
    X = pd.DataFrame(rng.normal(size=(70, 27)), columns=FULL_OBSERVATION_FEATURES)
    y = pd.Series(list(TARGET_COLUMNS) * 10, name="target")
    cv = tuple(
        (tuple(train), tuple(valid))
        for train, valid in StratifiedKFold(n_splits=5, shuffle=True, random_state=42).split(X, y)
    )
    repeated = run_controlled_searches(X, y, cv)
    first = run_controlled_searches(X, y, cv)
    for name in first:
        assert first[name].best_params_ == repeated[name].best_params_
        assert first[name].best_score_ == pytest.approx(repeated[name].best_score_)


def test_oof_probabilities_are_valid_and_holdout_is_unavailable(split, searches):
    for search in searches.values():
        probabilities = search.best_estimator_.predict_proba(split.X_train.iloc[:10])
        assert probabilities.shape == (10, 7)
        assert probabilities.dtype.kind in "fc"
        assert probabilities.sum(axis=1).round(6).tolist() == [1.0] * 10
    assert oof_probability_summary(searches["random_forest"].best_estimator_, split.X_train, split.y_train, split.cv_splits)["holdout_accessed"] is False


def test_no_calibration_or_search_of_new_algorithms():
    source = (ROOT / "src/quality_ml/models/tuning.py").read_text(encoding="utf-8")
    assert "CalibratedClassifierCV" not in source
    assert "XGB" not in source and "LGBM" not in source
