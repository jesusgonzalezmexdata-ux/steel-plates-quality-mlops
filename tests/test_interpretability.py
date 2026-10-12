"""Fold stability, nonmutation and deterministic case examples."""

import numpy as np
import pandas as pd
import pytest

from quality_ml.evaluation import interpretability as importance
from quality_ml.evaluation.protocol import FEATURES, assert_frozen


def test_all_features_retained_and_importance_consistent(phase9_run):
    frames = phase9_run[0]
    native = frames["interpretability/native_feature_importance.csv"]
    table = frames["interpretability/permutation_importance.csv"]
    repeats = frames["interpretability/permutation_by_fold.csv"]
    assert set(native.feature) == set(table.feature) == set(FEATURES)
    assert len(native) == len(table) == 27 and len(repeats) == 27 * 5 * 5
    assert native.importance.sum() == pytest.approx(1)
    pd.testing.assert_frame_equal(importance.aggregate_importance(repeats), table)
    assert table.positive_fold_count.between(0, 5).all()
    with pytest.raises(ValueError, match="missing"):
        importance.aggregate_importance(repeats.iloc[1:])


def test_importance_computation_does_not_mutate_fitted_estimator():
    rng = np.random.default_rng(42)
    X = pd.DataFrame(rng.normal(size=(70, 27)), columns=FEATURES)
    y = pd.Series(["Pastry", "Z_Scratch", "K_Scatch", "Stains", "Dirtiness", "Bumps", "Other_Faults"] * 10)
    model = assert_frozen()
    model.fit(X.iloc[:49], y.iloc[:49])
    before = importance.estimator_fingerprint(model)
    expected = model.predict_proba(X.iloc[49:]).copy()
    importance.native_importance(model)
    importance.fold_permutation(model, X.iloc[49:], y.iloc[49:], 1)
    assert importance.estimator_fingerprint(model) == before
    np.testing.assert_array_equal(model.predict_proba(X.iloc[49:]), expected)
    assert_frozen(model, X.columns)


def test_cases_follow_extremes_and_deterministic_row_id_tie_break(phase9_run):
    cases = phase9_run[1]["interpretability/case_examples.json"]
    assert len(cases) == 4
    assert all("row_id" in case for case in cases)
    for case in cases:
        assert "no local or causal" in case["attribution_scope"]
        assert len(case["globally_associated_feature_values"]) == 5
    frame = pd.DataFrame(dict(row_id=[9, 2, 7, 4],
        actual_class=["Pastry"]*4, predicted_class=["Pastry"]*4,
        correct_prediction=[True]*4, max_probability=[0.9, 0.9, 0.3, 0.3],
        probability_margin=[0.8, 0.8, 0.1, 0.1]))
    X = pd.DataFrame(1.0, index=[9, 2, 7, 4], columns=FEATURES)
    policy = dict(status="DEVELOPMENT_ONLY", high_threshold=0.8, low_threshold=0.5)
    ranking = pd.DataFrame(dict(feature=FEATURES))
    selected = importance.case_examples(frame, X, policy, ranking)
    assert selected[0]["row_id"] == 2 and selected[1]["row_id"] == 4
    assert selected[2]["status"] == selected[3]["status"] == "NO_MATCHING_CASE"


def test_figures_reproduce_byte_for_byte(phase9_run, tmp_path):
    from pathlib import Path
    from quality_ml.evaluation.__main__ import render_figures
    from quality_ml.evaluation.protocol import file_hash
    root = Path(__file__).resolve().parents[1]
    for directory in ("error_analysis", "uncertainty", "interpretability"):
        (tmp_path / directory).mkdir()
    render_figures(tmp_path, phase9_run[0], phase9_run[2])
    for name in ("error_analysis/confusion_matrix.png", "uncertainty/reliability.png",
                 "interpretability/feature_importance.png"):
        assert file_hash(tmp_path / name) == file_hash(root / "reports/ml" / name)
