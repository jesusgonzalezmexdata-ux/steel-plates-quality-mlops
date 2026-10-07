"""Deterministic, leakage-aware holdout and cross-validation protocol.

The protocol evaluates classification under full observation of the recorded
measurements. It is not an early-inference or pre-production protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
from sklearn.model_selection import StratifiedKFold, train_test_split

from quality_ml.data.audit import TARGET_COLUMNS, load_dataset
from quality_ml.data.leakage import build_feature_sets

RANDOM_STATE = 42
TEST_SIZE = 0.20
# The smallest source class has 55 rows. A 20% sealed holdout leaves 44 rows
# in training; five folds keep roughly 8-9 examples of that class per
# validation fold. Ten folds would leave roughly four per validation fold and
# would make the estimate unnecessarily fragile for this dataset.
N_SPLITS = 5
OBSERVATION_COMPLETE_WARNING = (
    "This protocol validates classification under full observation of the "
    "recorded measurements; it does not establish early plant inference."
)


@dataclass(frozen=True)
class SplitResult:
    """Immutable result of the holdout and training-only CV protocol."""

    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_test: pd.Series
    train_positions: tuple[int, ...]
    test_positions: tuple[int, ...]
    cv_splits: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...]
    feature_status: dict[str, str]


def build_multiclass_target(df: pd.DataFrame) -> pd.Series:
    """Convert the seven one-hot columns to one label without changing ``df``."""

    missing = sorted(set(TARGET_COLUMNS) - set(df.columns))
    if missing:
        raise ValueError(f"Missing target columns: {missing}")
    target = df[list(TARGET_COLUMNS)]
    if not target.apply(lambda column: set(column.dropna().unique()).issubset({0, 1})).all():
        raise ValueError("Target columns must contain only binary values")
    if not (target.sum(axis=1) == 1).all():
        raise ValueError("Each row must have exactly one positive target")
    return target.idxmax(axis=1).rename("target")


def _positions(values: Iterable[int]) -> tuple[int, ...]:
    return tuple(int(value) for value in values)


def validate_split(result: SplitResult, all_positions: Iterable[int]) -> None:
    """Raise if holdout, CV, target and feature invariants are violated."""

    all_positions_set = set(all_positions)
    train_set = set(result.train_positions)
    test_set = set(result.test_positions)
    if not train_set.isdisjoint(test_set):
        raise AssertionError("A row appears in both train and test")
    if train_set | test_set != all_positions_set:
        raise AssertionError("Train and test do not cover the input rows")
    if set(result.X_train.columns) != set(result.X_test.columns):
        raise AssertionError("Train and test feature schemas differ")
    if set(TARGET_COLUMNS) & set(result.X_train.columns):
        raise AssertionError("A target column entered X")
    if "id" in result.X_train.columns:
        raise AssertionError("Technical id entered X")
    classes = set(result.y_train) | set(result.y_test)
    if len(classes) != len(TARGET_COLUMNS):
        raise AssertionError("Not all seven classes are represented")
    if set(result.y_train) != set(result.y_test):
        raise AssertionError("Train and test class supports differ")

    minimum_train_count = result.y_train.value_counts().min()
    if len(result.cv_splits) != N_SPLITS:
        raise AssertionError(f"Expected {N_SPLITS} CV folds")
    for cv_train, cv_valid in result.cv_splits:
        if set(cv_train) & set(cv_valid):
            raise AssertionError("A row appears in both CV train and validation")
        if len(cv_train) + len(cv_valid) != len(result.y_train):
            raise AssertionError("A CV fold does not cover training rows")
        expected_classes = set(TARGET_COLUMNS)
        if set(result.y_train.iloc[list(cv_train)]) != expected_classes:
            raise AssertionError("A CV training fold lost a target class")
        if set(result.y_train.iloc[list(cv_valid)]) != expected_classes:
            raise AssertionError("A CV validation fold lost a target class")
        if minimum_train_count < N_SPLITS:
            raise AssertionError("Training class counts cannot support five folds")


def make_split(
    df: pd.DataFrame,
    *,
    test_size: float = TEST_SIZE,
    random_state: int = RANDOM_STATE,
    n_splits: int = N_SPLITS,
) -> SplitResult:
    """Create a sealed stratified holdout and CV folds on training only.

    No imputation, scaling, feature selection or other learned transformation
    occurs here. Such transformations must be fitted inside a later pipeline
    using only each training fold.
    """

    y = build_multiclass_target(df)
    feature_sets = build_feature_sets(df.columns)
    full_features = feature_sets["full_observation_features"]
    if not isinstance(full_features, list):
        raise AssertionError("FULL_OBSERVATION_FEATURES must be a list")

    positions = list(range(len(df)))
    train_positions, test_positions = train_test_split(
        positions,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )
    train_positions = sorted(train_positions)
    test_positions = sorted(test_positions)
    y_train = y.iloc[train_positions].reset_index(drop=True)
    y_test = y.iloc[test_positions].reset_index(drop=True)

    if y_train.value_counts().min() < n_splits:
        raise ValueError(
            f"n_splits={n_splits} exceeds the smallest training class count "
            f"({y_train.value_counts().min()})"
        )
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    cv_splits = tuple(
        (_positions(cv_train), _positions(cv_valid))
        for cv_train, cv_valid in cv.split(df.iloc[train_positions][full_features], y_train)
    )

    result = SplitResult(
        X_train=df.iloc[train_positions][full_features].reset_index(drop=True).copy(),
        X_test=df.iloc[test_positions][full_features].reset_index(drop=True).copy(),
        y_train=y_train,
        y_test=y_test,
        train_positions=_positions(train_positions),
        test_positions=_positions(test_positions),
        cv_splits=cv_splits,
        feature_status=feature_sets["status_by_feature"],
    )
    validate_split(result, positions)
    return result


def split_csv(path: str | Path) -> SplitResult:
    """Load a CSV and apply the prescribed protocol."""

    return make_split(load_dataset(path))
