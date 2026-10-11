"""One-shot evaluation of the Phase 7 frozen candidate; no selection API."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score,
    log_loss, precision_recall_fscore_support, precision_score, recall_score,
)
from sklearn.model_selection import train_test_split

from quality_ml.data.audit import TARGET_COLUMNS
from quality_ml.data.leakage import build_feature_sets
from quality_ml.data.split import build_multiclass_target
from quality_ml.models.baseline import validate_feature_matrix

PHASE_7 = "52132ddd052e3fde4a8dd846c5268abaf742fa69"
PHASE_7_STATE = "0e9722aaf78e65ae1613dca155eaab5e3388de27"
MODEL_NAME = "tuned_random_forest"
MODEL_CONFIG = dict(n_estimators=300, min_samples_leaf=2, max_features="sqrt",
                    max_depth=20, class_weight="balanced", random_state=42, n_jobs=1)
TRAIN_SIZE, HOLDOUT_SIZE, N_FEATURES = 1552, 389, 27
OUTPUT = Path("reports/ml/final_holdout")
STATE = Path("docs/PROJECT_EXECUTION_STATE.md")


def build_final_model():
    return RandomForestClassifier(**MODEL_CONFIG)


def _git(root, *args):
    return subprocess.check_output(
        ["git", "-c", f"safe.directory={root.as_posix()}", *args],
        cwd=root, text=True, encoding="utf-8",
    ).strip()


def preflight(root):
    """Original tracked files must still exactly match the frozen checkpoint."""
    if _git(root, "rev-parse", "HEAD") != PHASE_7_STATE:
        raise ValueError("BLOCKED: unexpected HEAD")
    if _git(root, "rev-parse", "HEAD^") != PHASE_7:
        raise ValueError("BLOCKED: unexpected Phase 7 checkpoint")
    _git(root, "diff", "--check")
    if _git(root, "diff", "HEAD", "--name-only"):
        raise ValueError("BLOCKED: frozen tracked files changed")
    status = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    allowed = {"src/quality_ml/models/final_holdout.py", "tests/test_final_holdout.py",
               "docs/ml/07_final_holdout_evaluation.md"}
    if any(line[:3] != "?? " or line[3:] not in allowed for line in status.splitlines()):
        raise ValueError("BLOCKED: unexpected working-tree change")
    state = (root / STATE).read_text(encoding="utf-8")
    for expected in ("LAST_COMPLETED_PHASE = 7", "HOLDOUT_STATUS = SEALED",
                     f"FINAL_MODEL_CANDIDATE = {MODEL_NAME}",
                     "FEATURE_SET = FULL_OBSERVATION_FEATURES"):
        if expected not in state.splitlines():
            raise ValueError(f"BLOCKED: missing {expected}")
    selection = json.loads((root / "reports/ml/model_selection/selection.json").read_text())
    frozen = {k: v for k, v in MODEL_CONFIG.items() if k not in ("random_state", "n_jobs")}
    if not (selection["final_model_candidate"] == MODEL_NAME
            and selection["final_model_config"] == frozen
            and selection["feature_set"] == "FULL_OBSERVATION_FEATURES"
            and selection["n_features"] == N_FEATURES
            and selection["primary_metric"] == "macro_f1"
            and selection["holdout_status"] == "SEALED"
            and selection["holdout_accessed"] is False
            and selection["cv_protocol"] == "StratifiedKFold(n_splits=5, shuffle=True, random_state=42)"):
        raise ValueError("BLOCKED: Phase 7 selection mismatch")
    cv = selection["evaluations"][MODEL_NAME]
    if (round(cv["metrics_mean"]["macro_f1"], 4) != 0.8008
            or round(cv["metrics_std"]["macro_f1"], 4) != 0.0282):
        raise ValueError("BLOCKED: frozen CV mismatch")
    if (root / OUTPUT).exists():
        raise ValueError("BLOCKED: final evaluation already reserved or consumed")
    return dict(branch=_git(root, "branch", "--show-current"), head=PHASE_7_STATE,
                phase_7_checkpoint=PHASE_7, phase_7_state_checkpoint=PHASE_7_STATE,
                frozen_tracked_files_unchanged=True, git_diff_check="PASS",
                permitted_untracked_phase_8_files=status.splitlines())


def validate_probabilities(probabilities, classes, n_rows=HOLDOUT_SIZE):
    if len(classes) != 7 or set(classes) != set(TARGET_COLUMNS):
        raise ValueError("Expected exactly seven probability classes")
    if probabilities.shape != (n_rows, 7):
        raise ValueError("Invalid probability shape")
    if not np.isfinite(probabilities).all():
        raise ValueError("Nonfinite probabilities")
    if ((probabilities < 0) | (probabilities > 1)).any():
        raise ValueError("Probabilities outside [0, 1]")
    if not np.allclose(probabilities.sum(axis=1), 1, rtol=0, atol=1e-12):
        raise ValueError("Probability rows do not sum to one")


def score_predictions(actual, probabilities, classes, positions):
    """Pure scoring: no fitting, raw-data loading, or model invocation."""
    validate_probabilities(probabilities, classes)
    if len(actual) != HOLDOUT_SIZE or set(actual) != set(TARGET_COLUMNS):
        raise ValueError("Holdout must contain 389 rows and seven classes")
    if len(positions) != HOLDOUT_SIZE or len(set(positions)) != HOLDOUT_SIZE:
        raise ValueError("Invalid row identifiers")
    # RF.predict is the argmax of predict_proba, with the same class tie order.
    predicted = np.asarray(classes)[probabilities.argmax(axis=1)]
    values = dict(
        accuracy=float(accuracy_score(actual, predicted)),
        balanced_accuracy=float(balanced_accuracy_score(actual, predicted)),
        macro_precision=float(precision_score(actual, predicted, average="macro", zero_division=0)),
        macro_recall=float(recall_score(actual, predicted, average="macro", zero_division=0)),
        macro_f1=float(f1_score(actual, predicted, average="macro", zero_division=0)),
        weighted_f1=float(f1_score(actual, predicted, average="weighted", zero_division=0)),
        log_loss=float(log_loss(actual, probabilities[:, np.argsort(classes)], labels=sorted(classes))),
    )
    precision, recall, f1, support = precision_recall_fscore_support(
        actual, predicted, labels=list(TARGET_COLUMNS), zero_division=0)
    per_class = {label: dict(precision=float(precision[i]), recall=float(recall[i]),
                             f1=float(f1[i]), support=int(support[i]))
                 for i, label in enumerate(TARGET_COLUMNS)}
    matrix = pd.DataFrame(confusion_matrix(actual, predicted, labels=list(TARGET_COLUMNS)),
                          index=TARGET_COLUMNS, columns=TARGET_COLUMNS)
    matrix.index.name = "actual_class"
    predictions = pd.DataFrame(dict(row_index=positions, actual_class=np.asarray(actual),
                                    predicted_class=predicted,
                                    correct_prediction=predicted == np.asarray(actual),
                                    max_probability=probabilities.max(axis=1)))
    for label in TARGET_COLUMNS:
        predictions[f"probability_{label}"] = probabilities[:, list(classes).index(label)]
    return values, per_class, matrix, predictions


def _write_json(path, value):
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def _read_rows(csv_path, positions):
    selected = set(positions)
    return pd.read_csv(csv_path, skiprows=lambda line: line > 0 and line - 1 not in selected)


def evaluate_once(root):
    """Exclusive persistent reservation prevents a second real-data evaluation."""
    evidence = preflight(root)
    output = root / OUTPUT
    output.mkdir()  # Atomic reservation; never remove it or offer a force option.
    ledger = dict(status="RESERVED", holdout_accessed=False, holdout_invalidated=False,
                  preflight=evidence)
    _write_json(output / "execution.json", ledger)
    try:
        csv_path = root / "data/raw/steel_plates_faults.csv"
        # Reconstruct the EXISTING split from targets alone. Labels were already
        # used for stratification in Phase 4; holdout measurements are not loaded.
        targets = pd.read_csv(csv_path, usecols=list(TARGET_COLUMNS))
        y = build_multiclass_target(targets)
        train_positions, test_positions = train_test_split(
            list(range(len(y))), test_size=0.20, random_state=42, stratify=y)
        train_positions, test_positions = sorted(train_positions), sorted(test_positions)
        if (len(train_positions), len(test_positions)) != (TRAIN_SIZE, HOLDOUT_SIZE):
            raise ValueError("Unexpected partition sizes")
        if set(train_positions) & set(test_positions):
            raise ValueError("Overlapping partitions")
        training = _read_rows(csv_path, train_positions)
        features = build_feature_sets(training.columns)["full_observation_features"]
        validate_feature_matrix(features)
        y_train = build_multiclass_target(training)
        if set(y_train) != set(TARGET_COLUMNS):
            raise ValueError("Training must contain seven classes")
        model = build_final_model()
        model.fit(training[features], y_train)
        # Persist consumption BEFORE opening the measurements: a crash cannot
        # silently restore SEALED or trigger another evaluation.
        ledger.update(status="CONSUMED_FINAL_EVALUATION", holdout_accessed=True,
                      fit_rows=TRAIN_SIZE, fit_calls=1, prediction_calls=0)
        _write_json(output / "execution.json", ledger)
        state_path = root / STATE
        state_text = state_path.read_text(encoding="utf-8")
        state_text = state_text.replace("HOLDOUT_STATUS = SEALED",
                                        "HOLDOUT_STATUS = CONSUMED_FINAL_EVALUATION", 1)
        state_path.write_text(state_text + "\nHOLDOUT_ACCESSED = TRUE\n", encoding="utf-8")
        holdout = _read_rows(csv_path, test_positions)
        if list(holdout[features].columns) != list(model.feature_names_in_):
            raise ValueError("Feature order changed")
        probabilities = model.predict_proba(holdout[features])
        ledger["prediction_calls"] = 1
        # Save the only prediction call before deriving any metrics.
        raw_predictions = pd.DataFrame(probabilities, columns=model.classes_)
        raw_predictions.insert(0, "row_index", test_positions)
        raw_predictions.to_csv(output / "probabilities_snapshot.csv", index=False)
        actual = build_multiclass_target(holdout)
        values, per_class, matrix, predictions = score_predictions(
            actual, probabilities, model.classes_, test_positions)
        predictions.to_csv(output / "predictions.csv", index=False)
        matrix.to_csv(output / "confusion_matrix.csv")
        result = dict(
            final_model=MODEL_NAME, final_model_config=MODEL_CONFIG,
            feature_set="FULL_OBSERVATION_FEATURES", features=features,
            train_size=TRAIN_SIZE, holdout_size=HOLDOUT_SIZE, n_features=N_FEATURES,
            holdout_first_access=True, holdout_status="CONSUMED_FINAL_EVALUATION",
            holdout_accessed=True, holdout_invalidated=False,
            metrics=values, per_class_results=per_class,
            confusion_matrix=matrix.to_numpy().tolist(), class_order=list(TARGET_COLUMNS),
            cv_macro_f1_mean=0.8008, cv_macro_f1_std=0.0282,
            generalization_gap=values["macro_f1"] - 0.8008,
            probability_check=dict(available=True, shape=list(probabilities.shape),
                                   finite=True, within_bounds=True, rows_sum_to_one=True,
                                   absolute_tolerance=1e-12),
            post_holdout_tuning=False, alternative_models_tested_on_holdout=False,
            calibration_performed=False, feature_selection_performed=False,
            validity_scope="FULL_OBSERVATION_CLASSIFICATION_ONLY",
            early_prediction_supported=False,
            split=dict(test_size=0.20, random_state=42, stratified=True,
                       train_positions=train_positions, holdout_positions=test_positions),
            environment=dict(python=platform.python_version(), numpy=np.__version__,
                             pandas=pd.__version__, sklearn=sklearn.__version__),
            preflight=evidence,
        )
        _write_json(output / "metrics.json", result)
        ledger.update(completed=True, artifacts_sha256={
            name: hashlib.sha256((output / name).read_bytes()).hexdigest()
            for name in ("predictions.csv", "metrics.json", "confusion_matrix.csv",
                         "probabilities_snapshot.csv")})
        _write_json(output / "execution.json", ledger)
        return result
    except Exception as error:
        ledger.update(completed=False, failure=f"{type(error).__name__}: {error}",
                      holdout_invalidated=ledger["holdout_accessed"])
        _write_json(output / "execution.json", ledger)
        if ledger["holdout_accessed"]:
            state_path = root / STATE
            with state_path.open("a", encoding="utf-8") as stream:
                stream.write("\nHOLDOUT_INVALIDATED = TRUE\n")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-final-once", action="store_true", required=True)
    parser.parse_args()
    result = evaluate_once(Path(__file__).resolve().parents[3])
    print(json.dumps(result["metrics"], indent=2))
