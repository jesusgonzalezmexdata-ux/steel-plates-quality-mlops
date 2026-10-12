"""Frozen contract, probability, OOF provenance and deterministic replay tests."""

import ast
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from quality_ml.data.audit import load_dataset
from quality_ml.data.split import make_split
from quality_ml.evaluation import protocol, uncertainty
from quality_ml.models import final_holdout

ROOT = Path(__file__).resolve().parents[1]


def test_exact_frozen_contract_and_mutation_rejection(monkeypatch):
    model = protocol.assert_frozen()
    contract = protocol.frozen_contract()
    assert dict(protocol.CONFIG) == dict(n_estimators=300, min_samples_leaf=2,
        max_features="sqrt", max_depth=20, class_weight="balanced", random_state=42, n_jobs=1)
    assert len(protocol.FEATURES) == 27
    assert contract["final_model_config_hash"] == protocol.digest(dict(protocol.CONFIG))
    model.set_params(max_depth=21)
    with pytest.raises(ValueError, match="estimator"):
        protocol.assert_frozen(model)
    with pytest.raises(ValueError, match="feature"):
        protocol.assert_frozen(features=protocol.FEATURES[::-1])
    monkeypatch.setitem(final_holdout.MODEL_CONFIG, "n_estimators", 301)
    with pytest.raises(ValueError, match="configuration"):
        protocol.assert_frozen()


def test_no_search_alternative_model_calibration_or_feature_selection_route():
    forbidden = {"GridSearchCV", "RandomizedSearchCV", "CalibratedClassifierCV",
                 "LogisticRegression", "HistGradientBoostingClassifier", "RFE",
                 "RFECV", "SelectKBest", "SelectFromModel", "choose_final_candidate",
                 "run_controlled_searches", "evaluate_once", "train_test_split"}
    for path in (ROOT / "src/quality_ml/evaluation").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        names |= {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        names |= {alias.name for node in ast.walk(tree)
                  if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
        assert not names & forbidden, path


def test_oof_once_no_leakage_exact_phase4_folds(phase9_run):
    frames, docs, _ = phase9_run
    frame = frames["uncertainty/oof_predictions.csv"]
    audit = docs["uncertainty/oof_fold_audit.json"]
    # Independent comparison to unchanged Phase 4 code, never fit/predict holdout.
    split = make_split(load_dataset(ROOT / "data/raw/steel_plates_faults.csv"))
    assert len(frame) == 1552 and frame.row_id.nunique() == 1552
    assert set(frame.row_id) == set(split.train_positions)
    assert not set(frame.row_id) & set(split.test_positions)
    for entry, (train, valid) in zip(audit, split.cv_splits):
        expected_train = [split.train_positions[i] for i in train]
        expected_valid = [split.train_positions[i] for i in valid]
        assert entry["train_row_ids"] == expected_train
        assert entry["validation_row_ids"] == expected_valid
        assert set(expected_train).isdisjoint(expected_valid)
        assert set(frame.loc[frame.fold == entry["fold"], "row_id"]) == set(expected_valid)
    assert sum(len(fold["validation_row_ids"]) for fold in audit) == 1552


def test_bad_folds_rejected():
    folds = [(np.array([2, 3, 4]), np.array([0, 1]))] * 5
    with pytest.raises(ValueError, match="exactly once"):
        uncertainty.validate_folds(folds, 5)
    folds[0] = (np.array([0, 2, 3, 4]), np.array([0, 1]))
    with pytest.raises(ValueError, match="leakage"):
        uncertainty.validate_folds(folds, 5)


def test_probabilities_and_internal_cv_consistency(phase9_run):
    frames, docs, _ = phase9_run
    frame = frames["uncertainty/oof_predictions.csv"]
    probs = frame[[f"probability_{c}" for c in protocol.CLASSES]].to_numpy()
    assert np.isfinite(probs).all() and ((probs >= 0) & (probs <= 1)).all()
    np.testing.assert_allclose(probs.sum(axis=1), 1, rtol=0, atol=protocol.ATOL)
    sorted_probs = np.sort(probs, axis=1)
    np.testing.assert_array_equal(frame.max_probability, sorted_probs[:, -1])
    np.testing.assert_array_equal(frame.probability_margin, sorted_probs[:, -1] - sorted_probs[:, -2])
    summary = docs["error_analysis/analysis_summary.json"]
    assert summary["phase_7_fold_metrics_match"]
    assert np.mean([row["macro_f1"] for row in summary["fold_metrics"]]) == pytest.approx(0.8008, abs=0.00005)


def test_bin_boundaries_include_zero_one_and_each_row_once(phase9_run):
    boundaries = pd.DataFrame(dict(max_probability=[0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
                                   correct_prediction=[True] * 7))
    bins = uncertainty.confidence_bins(boundaries)
    assert bins.n.tolist() == [1, 1, 1, 1, 1, 2]
    assert bins.n.sum() == 7
    real = phase9_run[0]["uncertainty/confidence_bins.csv"]
    assert real.n.sum() == 1552 and real.coverage.sum() == pytest.approx(1)
    assert real.loc[real.n < 30, "status"].eq("INSUFFICIENT_DATA").all()
    boundaries.loc[0, "max_probability"] = np.nan
    with pytest.raises(ValueError, match="Invalid confidence"):
        uncertainty.confidence_bins(boundaries)


def test_fixed_threshold_conservation_and_policy_no_holdout(phase9_run):
    frames, docs, _ = phase9_run
    oof = frames["uncertainty/oof_predictions.csv"]
    before = oof.copy(deep=True)
    trade = uncertainty.threshold_tradeoff(oof)
    assert trade.threshold.tolist() == [0.6, 0.7, 0.8, 0.9]
    assert (trade.accepted_rows + trade.review_rows).eq(1552).all()
    assert trade.accepted_rows.is_monotonic_decreasing
    assert uncertainty.candidate_policy(oof) == docs["error_analysis/analysis_summary.json"]["review_policy_candidate"]
    pd.testing.assert_frame_equal(oof, before, check_exact=True)
    policy = uncertainty.candidate_policy(oof)
    assert policy["high_threshold"] == 0.8 and policy["low_threshold"] == 0.5
    rejected = uncertainty.candidate_policy(oof.assign(correct_prediction=True))
    assert rejected["status"] == "NOT_SUPPORTED"


def test_multiclass_brier_and_ece_known_probabilities():
    classes = sorted(protocol.CLASSES)
    actual = classes * 2
    probabilities = np.eye(7)[np.arange(14) % 7]
    frame = uncertainty.prediction_frame(range(14), actual, probabilities, classes)
    metrics = uncertainty.calibration_metrics(frame, "SYNTHETIC")
    assert metrics["multiclass_brier_score"] == 0
    assert metrics["top_label_ece"] == 0
    wrong = uncertainty.prediction_frame(range(14), actual, np.roll(probabilities, 1, axis=1), classes)
    assert uncertainty.calibration_metrics(wrong, "SYNTHETIC")["multiclass_brier_score"] == 2


def test_complete_numeric_replay_matches_persisted_artifacts(phase9_run):
    frames, docs, _ = phase9_run
    for name, frame in frames.items():
        saved = pd.read_csv(ROOT / "reports/ml" / name, float_precision="round_trip")
        pd.testing.assert_frame_equal(frame, saved, check_dtype=False, check_exact=False,
                                      rtol=0, atol=protocol.ATOL)
    for name, value in docs.items():
        saved = json.loads((ROOT / "reports/ml" / name).read_text(encoding="utf-8"))
        assert json.loads(json.dumps(value)) == saved
