from pathlib import Path

import pandas as pd
import pytest

from quality_ml.data.audit import TARGET_COLUMNS, load_dataset
from quality_ml.data.leakage import build_feature_sets
from quality_ml.data.split import (
    N_SPLITS,
    OBSERVATION_COMPLETE_WARNING,
    RANDOM_STATE,
    build_multiclass_target,
    make_split,
    validate_split,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def raw() -> pd.DataFrame:
    return load_dataset(ROOT / "data/raw/steel_plates_faults.csv")


@pytest.fixture(scope="module")
def split(raw: pd.DataFrame):
    return make_split(raw)


def test_target_is_reproducible_multiclass_and_source_is_unchanged(raw):
    before = raw.copy(deep=True)
    target = build_multiclass_target(raw)
    assert target.nunique() == 7
    assert target.value_counts().sum() == len(raw)
    pd.testing.assert_frame_equal(raw, before)


def test_full_observation_features_exclude_targets_and_id(raw, split):
    expected = build_feature_sets(raw.columns)["full_observation_features"]
    assert list(split.X_train.columns) == expected
    assert not set(TARGET_COLUMNS) & set(split.X_train.columns)
    assert "id" not in split.X_train.columns


def test_holdout_is_stratified_and_all_classes_remain(split):
    assert len(split.X_train) == 1552
    assert len(split.X_test) == 389
    assert set(split.y_train) == set(TARGET_COLUMNS)
    assert set(split.y_test) == set(TARGET_COLUMNS)
    assert split.y_train.value_counts().min() >= N_SPLITS
    assert split.y_test.value_counts().min() >= 1


def test_no_rows_are_shared_between_train_and_test(split):
    assert set(split.train_positions).isdisjoint(split.test_positions)
    validate_split(split, range(1941))


def test_split_and_cv_are_reproducible(raw, split):
    repeat = make_split(raw, random_state=RANDOM_STATE)
    assert split.train_positions == repeat.train_positions
    assert split.test_positions == repeat.test_positions
    assert split.cv_splits == repeat.cv_splits
    pd.testing.assert_frame_equal(split.X_train, repeat.X_train)
    pd.testing.assert_series_equal(split.y_test, repeat.y_test)


def test_cv_has_five_stratified_training_folds(split):
    assert len(split.cv_splits) == 5
    for train_fold, valid_fold in split.cv_splits:
        assert set(train_fold).isdisjoint(valid_fold)
        assert len(train_fold) + len(valid_fold) == len(split.X_train)
        assert set(split.y_train.iloc[list(train_fold)]) == set(TARGET_COLUMNS)
        assert set(split.y_train.iloc[list(valid_fold)]) == set(TARGET_COLUMNS)


def test_learned_transformations_are_not_applied(split, raw):
    expected = raw.iloc[list(split.train_positions)][split.X_train.columns].reset_index(drop=True)
    pd.testing.assert_frame_equal(split.X_train, expected)


def test_fold_count_cannot_exceed_smallest_training_class(raw):
    with pytest.raises(ValueError, match="smallest training class count"):
        make_split(raw, n_splits=45)


def test_protocol_warning_is_explicit():
    assert "full observation" in OBSERVATION_COMPLETE_WARNING
    assert "early" in OBSERVATION_COMPLETE_WARNING
