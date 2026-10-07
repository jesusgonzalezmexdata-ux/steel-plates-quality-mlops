"""Small, justified baseline models for the full-observation experiment."""

from __future__ import annotations

from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from quality_ml.data.audit import TARGET_COLUMNS
from quality_ml.data.leakage import QUESTIONABLE_FEATURES, SAFE_FEATURES

PRIMARY_METRIC = "macro_f1"
FULL_OBSERVATION_FEATURES = tuple(SAFE_FEATURES + QUESTIONABLE_FEATURES)


def validate_feature_matrix(columns: list[str] | tuple[str, ...]) -> None:
    """Require exactly the 27 features allowed by the leakage policy."""

    observed = list(columns)
    if set(observed) != set(FULL_OBSERVATION_FEATURES) or len(observed) != 27:
        raise ValueError("Baseline matrix must contain exactly the 27 full-observation features")
    if set(observed) & (set(TARGET_COLUMNS) | {"id"}):
        raise ValueError("Target columns and id must remain outside X")


def build_baselines(random_state: int = 42) -> dict[str, object]:
    """Return the two pre-registered baselines without fitting either one."""

    return {
        # Naive reference: always predict the majority class in each training fold.
        "dummy_most_frequent": DummyClassifier(strategy="most_frequent"),
        # Linear multiclass baseline; scaling is learned inside each CV fold.
        "logistic_regression": Pipeline(
            steps=[
                ("scale", StandardScaler()),
                (
                    "classifier",
                    LogisticRegression(
                        solver="lbfgs",
                        max_iter=2000,
                        random_state=random_state,
                    ),
                ),
            ]
        ),
    }
