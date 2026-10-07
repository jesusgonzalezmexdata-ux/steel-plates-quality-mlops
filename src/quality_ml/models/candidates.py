"""Exactly two non-linear candidate families plus the frozen incumbent."""

from __future__ import annotations

from typing import Any

from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier

from quality_ml.models.baseline import build_baselines

RANDOM_STATE = 42

# These are declared once, before candidate evaluation. They are not a search
# space and must not be changed after observing results in this phase.
RANDOM_FOREST_CONFIG: dict[str, Any] = {
    "n_estimators": 300,
    "random_state": RANDOM_STATE,
    "n_jobs": 1,
    "class_weight": None,
    "max_depth": None,
    "min_samples_leaf": 1,
}
HIST_GRADIENT_BOOSTING_CONFIG: dict[str, Any] = {
    "max_iter": 200,
    "learning_rate": 0.1,
    "max_leaf_nodes": 31,
    "min_samples_leaf": 20,
    "l2_regularization": 0.0,
    "random_state": RANDOM_STATE,
}

MIN_PROMISING_DELTA = 0.01
MAX_BALANCED_ACCURACY_DROP = 0.02
MAX_VARIABILITY_RATIO = 1.5


def build_candidate_models(random_state: int = RANDOM_STATE) -> dict[str, object]:
    """Build exactly the frozen incumbent and two declared candidates."""

    if random_state != RANDOM_STATE:
        raise ValueError("Candidate protocol is frozen at random_state=42")
    baselines = build_baselines(random_state=RANDOM_STATE)
    return {
        "logistic_regression": baselines["logistic_regression"],
        "random_forest": RandomForestClassifier(**RANDOM_FOREST_CONFIG),
        "hist_gradient_boosting": HistGradientBoostingClassifier(**HIST_GRADIENT_BOOSTING_CONFIG),
    }


def compare_to_logistic(results: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Compare each candidate fold-by-fold with the frozen Logistic baseline."""

    incumbent = results["logistic_regression"]
    logistic_f1 = [fold["macro_f1"] for fold in incumbent["fold_metrics"]]
    logistic_balanced = incumbent["metrics_mean"]["balanced_accuracy"]
    logistic_std = incumbent["metrics_std"]["macro_f1"]
    comparison: dict[str, dict[str, Any]] = {}
    for name, result in results.items():
        if name == "logistic_regression":
            continue
        candidate_f1 = [fold["macro_f1"] for fold in result["fold_metrics"]]
        deltas = [candidate - incumbent_f1 for candidate, incumbent_f1 in zip(candidate_f1, logistic_f1)]
        mean_delta = sum(deltas) / len(deltas)
        candidate_std = result["metrics_std"]["macro_f1"]
        balanced_delta = result["metrics_mean"]["balanced_accuracy"] - logistic_balanced
        if (
            mean_delta >= MIN_PROMISING_DELTA
            and min(deltas) >= 0
            and balanced_delta >= -MAX_BALANCED_ACCURACY_DROP
            and candidate_std <= logistic_std * MAX_VARIABILITY_RATIO
        ):
            status = "PROMISING"
        elif mean_delta <= -MIN_PROMISING_DELTA:
            status = "NOT_COMPETITIVE"
        else:
            status = "UNSTABLE"
        comparison[name] = {
            "delta_macro_f1_vs_logistic_by_fold": deltas,
            "mean_delta": mean_delta,
            "min_delta": min(deltas),
            "max_delta": max(deltas),
            "balanced_accuracy_delta": balanced_delta,
            "status": status,
        }
    return comparison
