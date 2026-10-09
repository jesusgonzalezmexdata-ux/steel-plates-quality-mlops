"""Small, predeclared Random Forest and HistGradientBoosting searches."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.model_selection import RandomizedSearchCV

from quality_ml.data.audit import load_dataset
from quality_ml.data.split import RANDOM_STATE, make_split
from quality_ml.models.baseline import validate_feature_matrix
from quality_ml.models.evaluate import evaluate_models_cv

SEARCH_BUDGET_RF = 12
SEARCH_BUDGET_HGB = 12
SEARCH_RANDOM_STATE = RANDOM_STATE
PRIMARY_METRIC = "macro_f1"
SCORING = {
    "macro_f1": "f1_macro",
    "balanced_accuracy": "balanced_accuracy",
    "neg_log_loss": "neg_log_loss",
    "weighted_f1": "f1_weighted",
}

# These spaces are fixed before search. They are not expanded after seeing any
# result and are intentionally small enough to audit.
RF_SEARCH_SPACE: dict[str, list[Any]] = {
    "n_estimators": [300, 500],
    "max_depth": [None, 12, 20],
    "min_samples_leaf": [1, 2, 4],
    "max_features": ["sqrt", 0.5],
    "class_weight": [None, "balanced"],
}
HGB_SEARCH_SPACE: dict[str, list[Any]] = {
    "learning_rate": [0.03, 0.05, 0.10],
    "max_iter": [100, 200, 300],
    "max_leaf_nodes": [15, 31, 63],
    "min_samples_leaf": [10, 20, 30],
    "l2_regularization": [0.0, 0.1, 1.0],
}


def _validate_cv(cv_splits: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...]) -> None:
    if len(cv_splits) != 5:
        raise ValueError("Tuning requires the exact five Fase 4 folds")


def run_controlled_searches(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    cv_splits: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...],
) -> dict[str, RandomizedSearchCV]:
    """Run exactly one fixed-budget search per non-linear candidate."""

    validate_feature_matrix(list(X_train.columns))
    _validate_cv(cv_splits)
    common = {
        "scoring": SCORING,
        "refit": PRIMARY_METRIC,
        "cv": cv_splits,
        "random_state": SEARCH_RANDOM_STATE,
        "return_train_score": False,
        "n_jobs": 1,
    }
    rf_search = RandomizedSearchCV(
        RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=1),
        param_distributions=RF_SEARCH_SPACE,
        n_iter=SEARCH_BUDGET_RF,
        **common,
    )
    hgb_search = RandomizedSearchCV(
        HistGradientBoostingClassifier(random_state=RANDOM_STATE),
        param_distributions=HGB_SEARCH_SPACE,
        n_iter=SEARCH_BUDGET_HGB,
        **common,
    )
    # Only X_train and y_train are accepted; the sealed holdout is not an API
    # input and cannot be used by these searches.
    rf_search.fit(X_train, y_train)
    hgb_search.fit(X_train, y_train)
    return {"random_forest": rf_search, "hist_gradient_boosting": hgb_search}


def search_leaderboard(searches: dict[str, RandomizedSearchCV]) -> pd.DataFrame:
    """Return best and all sampled development-CV rows in tidy form."""

    rows: list[dict[str, Any]] = []
    for model_name, search in searches.items():
        for index in range(len(search.cv_results_["params"])):
            rows.append(
                {
                    "model": model_name,
                    "rank_macro_f1": int(search.cv_results_["rank_test_macro_f1"][index]),
                    "mean_macro_f1": float(search.cv_results_["mean_test_macro_f1"][index]),
                    "std_macro_f1": float(search.cv_results_["std_test_macro_f1"][index]),
                    "mean_balanced_accuracy": float(search.cv_results_["mean_test_balanced_accuracy"][index]),
                    "mean_log_loss": float(-search.cv_results_["mean_test_neg_log_loss"][index]),
                    "mean_weighted_f1": float(search.cv_results_["mean_test_weighted_f1"][index]),
                    "params": repr(search.cv_results_["params"][index]),
                }
            )
    return pd.DataFrame(rows).sort_values(["model", "rank_macro_f1"], ignore_index=True)


def evaluate_tuned_models(
    searches: dict[str, RandomizedSearchCV],
    X_train: pd.DataFrame,
    y_train: pd.Series,
    cv_splits: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...],
) -> dict[str, dict[str, Any]]:
    """Re-evaluate frozen best configurations on the same five development folds."""

    models = {
        "logistic_regression": __import__(
            "quality_ml.models.baseline", fromlist=["build_baselines"]
        ).build_baselines()["logistic_regression"],
        "tuned_random_forest": searches["random_forest"].best_estimator_,
        "tuned_hist_gradient_boosting": searches["hist_gradient_boosting"].best_estimator_,
    }
    return evaluate_models_cv(models, X_train, y_train, cv_splits)


def write_leaderboard(
    searches: dict[str, RandomizedSearchCV],
    output_path: str | Path,
) -> None:
    """Write sampled development-CV results without model artifacts."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    search_leaderboard(searches).to_csv(output, index=False)
