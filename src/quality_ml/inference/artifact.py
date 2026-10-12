"""Persist the frozen training reconstruction; never evaluate the holdout."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import subprocess
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from quality_ml.evaluation.protocol import (
    ATOL, CLASSES, CONFIG, FEATURES, assert_frozen, digest, file_hash,
    frozen_contract, load_phase8,
)
from quality_ml.models.final_holdout import _read_rows

MODEL_VERSION = "rf-phase8-v1"
MODEL_PATH = "artifacts/model/final_random_forest.joblib"
MANIFEST_PATH = "artifacts/manifest.json"
POLICY_PATH = "reports/ml/error_analysis/analysis_protocol.json"
PACKAGES = ("scikit-learn", "numpy", "pandas", "joblib")


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def runtime_versions():
    return dict(python=platform.python_version(),
                **{name: importlib.metadata.version(name) for name in PACKAGES})


def training_data(root, metrics):
    positions = metrics["split"]["train_positions"]
    if len(positions) != 1552 or positions != sorted(set(positions)):
        raise ValueError("Frozen training membership/order mismatch")
    frame = _read_rows(root / "data/raw/steel_plates_faults.csv", positions)
    frame.index = positions
    labels = frame[list(CLASSES)]
    if not labels.isin([0, 1]).all().all() or not labels.sum(axis=1).eq(1).all():
        raise ValueError("Training target must be exactly one-hot")
    X = frame[list(FEATURES)]
    if not np.isfinite(X.to_numpy()).all():
        raise ValueError("Nonfinite training features")
    return X, labels.idxmax(axis=1)


def builder_fingerprint():
    package = Path(__file__).resolve().parents[1]
    names = ("inference/artifact.py", "inference/predict.py", "evaluation/protocol.py",
             "evaluation/uncertainty.py", "models/final_holdout.py")
    return digest({name: (package / name).read_text(encoding="utf-8") for name in names})


def lineage(root, metrics, X, y):
    policy_document = json.loads((root / POLICY_PATH).read_text(encoding="utf-8"))
    policy = policy_document["review_policy_candidate"]
    if digest(policy) != policy_document["review_policy_hash"]:
        raise ValueError("Frozen development policy hash mismatch")
    return dict(
        builder_fingerprint=builder_fingerprint(),
        dataset_fingerprint=file_hash(root / "data/raw/steel_plates_faults.csv"),
        training_data_fingerprint=digest(dict(row_ids=X.index.tolist(),
            features=list(X.columns), values=X.to_numpy().tolist(), labels=y.tolist())),
        training_split_fingerprint=digest(metrics["split"]),
        feature_policy_fingerprint=frozen_contract()["contract_hash"],
        model_config_fingerprint=digest(dict(CONFIG)),
        review_policy=policy, review_policy_fingerprint=digest(policy),
    )


def build_artifact(root, git_sha=None):
    """One fixed fit on saved training membership. Save/load smoke uses training only."""
    root = Path(root)
    metrics, _, _ = load_phase8(root)
    X, y = training_data(root, metrics)
    if git_sha is None:
        git_sha = subprocess.check_output(
            ["git", "-c", f"safe.directory={root.resolve().as_posix()}",
             "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if len(git_sha) != 40 or any(c not in "0123456789abcdef" for c in git_sha):
        raise ValueError("A source Git commit SHA is required")
    identity = lineage(root, metrics, X, y)
    model = assert_frozen()
    model.fit(X, y)
    assert_frozen(model)
    target = root / MODEL_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, target, compress=3, protocol=5)
    restored = joblib.load(target)  # Locally generated, trusted artifact only.
    smoke = X.iloc[:32]
    np.testing.assert_array_equal(model.predict(smoke), restored.predict(smoke))
    np.testing.assert_allclose(model.predict_proba(smoke), restored.predict_proba(smoke),
                               rtol=0, atol=ATOL)
    manifest = dict(
        project="steel-plates-quality-mlops", model_name="tuned_random_forest",
        model_version=MODEL_VERSION, model_config=dict(CONFIG),
        classes=list(CLASSES), estimator_classes=sorted(CLASSES),
        feature_names=list(FEATURES), feature_count=27,
        **identity, model_artifact=MODEL_PATH,
        model_artifact_sha256=file_hash(target), git_sha=git_sha,
        git_sha_role="Scientific baseline before Phase 10; builder identified by builder_fingerprint",
        random_state=42, train_size=1552, holdout_size=389,
        development_cv_macro_f1=metrics["cv_macro_f1_mean"],
        development_cv_macro_f1_std=metrics["cv_macro_f1_std"],
        final_holdout_macro_f1=metrics["metrics"]["macro_f1"],
        final_balanced_accuracy=metrics["metrics"]["balanced_accuracy"],
        final_log_loss=metrics["metrics"]["log_loss"],
        validity_scope="FULL_OBSERVATION_CLASSIFICATION_ONLY",
        early_prediction_supported=False, created_from_phase=10,
        scientific_selection_phase=7, final_evaluation_phase=8,
        training_membership_source="reports/ml/final_holdout/metrics.json#split.train_positions",
        holdout_status="CONSUMED_FINAL_EVALUATION",
        post_holdout_tuning=False, serialization=dict(compression=3, protocol=5),
        environment=runtime_versions(),
        verification=dict(save_load_prediction_match=True,
            save_load_probability_atol=ATOL, smoke_rows=32,
            smoke_source="TRAINING_ONLY", new_holdout_inference=False),
    )
    write_json(root / MANIFEST_PATH, manifest)
    return manifest


def load_artifact(root):
    """Only load a trusted repository artifact; a digest is not an authenticity signature."""
    root = Path(root)
    m = json.loads((root / MANIFEST_PATH).read_text(encoding="utf-8"))
    contract = dict(model_name="tuned_random_forest", model_version=MODEL_VERSION,
        model_config=dict(CONFIG), classes=list(CLASSES), estimator_classes=sorted(CLASSES),
        feature_names=list(FEATURES), feature_count=27, train_size=1552, holdout_size=389,
        model_artifact=MODEL_PATH, validity_scope="FULL_OBSERVATION_CLASSIFICATION_ONLY",
        early_prediction_supported=False, post_holdout_tuning=False,
        holdout_status="CONSUMED_FINAL_EVALUATION")
    for key, value in contract.items():
        if m.get(key) != value:
            raise ValueError(f"Manifest contract mismatch: {key}")
    if m["model_config_fingerprint"] != digest(dict(CONFIG)):
        raise ValueError("Model configuration fingerprint mismatch")
    if m["feature_policy_fingerprint"] != frozen_contract()["contract_hash"]:
        raise ValueError("Feature policy fingerprint mismatch")
    policy_document = json.loads((root / POLICY_PATH).read_text(encoding="utf-8"))
    if (m["review_policy"] != policy_document["review_policy_candidate"]
            or m["review_policy_fingerprint"] != digest(m["review_policy"])
            or m["review_policy_fingerprint"] != policy_document["review_policy_hash"]):
        raise ValueError("Development policy changed")
    current = runtime_versions()
    for package in ("scikit-learn", "numpy", "joblib"):
        if m["environment"][package] != current[package]:
            raise ValueError(f"Unsupported serialized-model runtime: {package}")
    if m["environment"]["python"].split(".")[:2] != current["python"].split(".")[:2]:
        raise ValueError("Python major/minor differs from artifact runtime")
    if file_hash(root / MODEL_PATH) != m["model_artifact_sha256"]:
        raise ValueError("Model artifact SHA256 mismatch")
    model = assert_frozen(joblib.load(root / MODEL_PATH))
    if (model.n_features_in_ != 27 or len(model.estimators_) != 300
            or any(t.tree_.weighted_n_node_samples[0] <= 0 for t in model.estimators_)):
        raise ValueError("Incomplete fitted estimator")
    return model, m


def validate_artifact(root):
    root = Path(root)
    model, m = load_artifact(root)
    metrics, _, _ = load_phase8(root)
    X, y = training_data(root, metrics)
    for key, value in lineage(root, metrics, X, y).items():
        if m[key] != value:
            raise ValueError(f"Lineage mismatch: {key}")
    for manifest_key, metric_key in (
        ("final_holdout_macro_f1", "macro_f1"),
        ("final_balanced_accuracy", "balanced_accuracy"), ("final_log_loss", "log_loss")
    ):
        if m[manifest_key] != metrics["metrics"][metric_key]:
            raise ValueError("Final metric lineage mismatch")
    if m["development_cv_macro_f1"] != metrics["cv_macro_f1_mean"]:
        raise ValueError("Development metric lineage mismatch")
    from quality_ml.inference.predict import predict_frame
    prediction = predict_frame(X.iloc[:8].reset_index(drop=True), model, m)
    if len(prediction) != 8:
        raise ValueError("Batch smoke failed")
    return dict(status="PASS", model_artifact_sha256=m["model_artifact_sha256"],
                training_data_fingerprint=m["training_data_fingerprint"],
                smoke_source="TRAINING_ONLY", smoke_rows=8)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["build", "validate"])
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    result = build_artifact(args.root) if args.action == "build" else validate_artifact(args.root)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()