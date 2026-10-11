"""Synthetic-only tests: never invoke the production holdout evaluation."""

import ast
import inspect
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import log_loss

from quality_ml.data.audit import TARGET_COLUMNS
from quality_ml.models.baseline import FULL_OBSERVATION_FEATURES, validate_feature_matrix
from quality_ml.models import final_holdout as final


def test_frozen_estimator_and_all_parameters():
    expected = RandomForestClassifier(n_estimators=300, min_samples_leaf=2,
        max_features="sqrt", max_depth=20, class_weight="balanced", random_state=42, n_jobs=1)
    model = final.build_final_model()
    assert type(model) is RandomForestClassifier
    assert model.get_params(deep=True) == expected.get_params(deep=True)
    assert final.MODEL_NAME == "tuned_random_forest"


@pytest.mark.parametrize("extra", ["id", *TARGET_COLUMNS])
def test_targets_and_id_rejected(extra):
    with pytest.raises(ValueError):
        validate_feature_matrix([*FULL_OBSERVATION_FEATURES[:-1], extra])


def test_exactly_27_features_required():
    validate_feature_matrix(FULL_OBSERVATION_FEATURES)
    with pytest.raises(ValueError):
        validate_feature_matrix(FULL_OBSERVATION_FEATURES[:-1])


@pytest.fixture
def probability_example():
    classes = np.asarray(sorted(TARGET_COLUMNS))
    actual = pd.Series([TARGET_COLUMNS[i % 7] for i in range(389)])
    probabilities = np.full((389, 7), 0.05)
    probabilities[np.arange(389), [list(classes).index(x) for x in actual]] = 0.70
    return actual, probabilities, classes


def test_metrics_class_alignment_and_confusion(probability_example):
    actual, probabilities, classes = probability_example
    metrics, per_class, matrix, predictions = final.score_predictions(
        actual, probabilities, classes, range(389))
    assert metrics["macro_f1"] == metrics["accuracy"] == 1
    assert metrics["log_loss"] == pytest.approx(-np.log(0.7))
    assert sum(v["support"] for v in per_class.values()) == 389
    assert list(per_class) == list(TARGET_COLUMNS)
    assert matrix.to_numpy().sum() == np.trace(matrix.to_numpy()) == 389
    assert predictions.correct_prediction.all()
    order = np.array([6, 2, 4, 0, 5, 1, 3])
    reordered = final.score_predictions(actual, probabilities[:, order], classes[order], range(389))
    assert reordered[0] == metrics
    pd.testing.assert_frame_equal(reordered[3], predictions)


@pytest.mark.parametrize("problem", ["shape", "nan", "infinity", "negative", "sum", "classes"])
def test_invalid_probabilities_rejected(probability_example, problem):
    _, proba, classes = probability_example
    if problem == "shape":
        proba = proba[:-1]
    elif problem == "nan":
        proba[0, 0] = np.nan
    elif problem == "infinity":
        proba[0, 0] = np.inf
    elif problem == "negative":
        proba[0, 0] = -0.1
    elif problem == "sum":
        proba[0] = 0.1
    else:
        classes[0] = classes[1]
    with pytest.raises(ValueError):
        final.validate_probabilities(proba, classes)


def test_missing_holdout_class_rejected(probability_example):
    _, proba, classes = probability_example
    with pytest.raises(ValueError, match="seven classes"):
        final.score_predictions(pd.Series(["Pastry"] * 389), proba, classes, range(389))


def test_single_fit_and_prediction_route_without_selection():
    tree = ast.parse(inspect.getsource(final))
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    methods = [node.func.attr for node in calls if isinstance(node.func, ast.Attribute)]
    assert methods.count("fit") == 1
    assert methods.count("predict_proba") == 1
    assert "predict" not in methods
    imports = {alias.name for node in ast.walk(tree)
               if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    forbidden = {"RandomizedSearchCV", "GridSearchCV", "CalibratedClassifierCV",
                 "SelectKBest", "RFE", "HistGradientBoostingClassifier",
                 "LogisticRegression", "cross_validate", "cross_val_score"}
    assert not imports & forbidden


def test_one_shot_training_only_fit_and_failure_closed(tmp_path, monkeypatch):
    # The entire fixture is synthetic, including its raw CSV and state file.
    root = tmp_path
    (root / "data/raw").mkdir(parents=True)
    (root / "reports/ml").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / final.STATE).write_text("HOLDOUT_STATUS = SEALED\n", encoding="utf-8")
    rng = np.random.default_rng(11)
    raw = pd.DataFrame(rng.normal(size=(1941, 27)), columns=FULL_OBSERVATION_FEATURES)
    raw.insert(0, "id", np.arange(1941))
    for i, label in enumerate(TARGET_COLUMNS):
        raw[label] = (np.arange(1941) % 7 == i).astype(int)
    raw.to_csv(root / "data/raw/steel_plates_faults.csv", index=False)
    monkeypatch.setattr(final, "preflight", lambda root: {"synthetic_test": True})
    calls = []
    fitted = []
    original_fit = RandomForestClassifier.fit
    original_predict = RandomForestClassifier.predict_proba
    original_read = final._read_rows

    def read_rows(path, positions):
        if len(positions) == 389:
            assert fitted == [1552]
            ledger = json.loads((root / final.OUTPUT / "execution.json").read_text())
            assert ledger["holdout_accessed"] is True
        calls.append(tuple(positions))
        return original_read(path, positions)

    def fit(model, X, y, **kwargs):
        assert X.shape == (1552, 27)
        assert "id" not in X and not set(TARGET_COLUMNS) & set(X)
        fitted.append(len(X))
        pd.testing.assert_frame_equal(X, raw.iloc[list(calls[0])][list(X)].reset_index(drop=True))
        return original_fit(model, X, y, **kwargs)

    predictions = []
    def predict(model, X):
        assert X.shape == (389, 27)
        assert len(calls) == 2 and set(calls[0]).isdisjoint(calls[1])
        predictions.append(len(X))
        return original_predict(model, X)

    monkeypatch.setattr(final, "_read_rows", read_rows)
    monkeypatch.setattr(RandomForestClassifier, "fit", fit)
    monkeypatch.setattr(RandomForestClassifier, "predict_proba", predict)
    result = final.evaluate_once(root)
    assert fitted == [1552] and predictions == [389]
    assert result["train_size"] == 1552 and result["holdout_size"] == 389
    assert result["n_features"] == 27
    assert result["post_holdout_tuning"] is False
    assert result["alternative_models_tested_on_holdout"] is False
    assert result["calibration_performed"] is False
    with pytest.raises(FileExistsError):
        final.evaluate_once(root)
    assert fitted == [1552] and predictions == [389]


def test_preflight_rejects_consumed_state(tmp_path, monkeypatch):
    (tmp_path / "docs").mkdir()
    (tmp_path / final.STATE).write_text("HOLDOUT_STATUS = CONSUMED_FINAL_EVALUATION\n")
    def git(root, *args):
        return {("rev-parse", "HEAD"): final.PHASE_7_STATE,
                ("rev-parse", "HEAD^"): final.PHASE_7}.get(args, "")
    monkeypatch.setattr(final, "_git", git)
    with pytest.raises(ValueError, match="BLOCKED"):
        final.preflight(tmp_path)
