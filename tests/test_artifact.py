"""Phase 10 training membership, serialization, schema and lineage checks."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier

from quality_ml.evaluation.protocol import FEATURES, file_hash, load_phase8
from quality_ml.inference import artifact
from quality_ml.inference.predict import predict_frame, read_batch, validate_schema

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def isolated(tmp_path):
    for name in ("data/raw/steel_plates_faults.csv", artifact.POLICY_PATH,
                 artifact.MANIFEST_PATH, artifact.MODEL_PATH):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    shutil.copytree(ROOT / "reports/ml/final_holdout", tmp_path / "reports/ml/final_holdout")
    return tmp_path


@pytest.fixture
def batch():
    metrics, _, _ = load_phase8(ROOT)
    X, _ = artifact.training_data(ROOT, metrics)
    return X.iloc[:16].reset_index(drop=True)


def test_training_only_reconstruction_and_determinism(isolated, monkeypatch):
    expected = json.loads((ROOT / artifact.MANIFEST_PATH).read_text())
    metrics, _, _ = load_phase8(ROOT)
    train_ids = metrics["split"]["train_positions"]
    holdout_ids = set(metrics["split"]["holdout_positions"])
    original_fit = RandomForestClassifier.fit
    original_predict = RandomForestClassifier.predict_proba
    fits, predictions = [], []

    def fit(model, X, y, **kwargs):
        assert list(X.columns) == list(FEATURES)
        assert list(X.index) == train_ids
        assert not holdout_ids.intersection(X.index)
        fits.append(len(X))
        return original_fit(model, X, y, **kwargs)

    def predict(model, X, **kwargs):
        assert set(X.index).issubset(train_ids)
        assert len(X) == 32
        predictions.append(len(X))
        return original_predict(model, X, **kwargs)

    monkeypatch.setattr(RandomForestClassifier, "fit", fit)
    monkeypatch.setattr(RandomForestClassifier, "predict_proba", predict)
    first = artifact.build_artifact(isolated, git_sha=expected["git_sha"])
    rebuilt = joblib.load(isolated / artifact.MODEL_PATH)
    second = artifact.build_artifact(isolated, git_sha=expected["git_sha"])
    assert first == second
    assert fits == [1552, 1552] and predictions
    # Pickle stream bytes depend on the serializing platform; the frozen artifact
    # was serialized on Windows. Everywhere, the rebuilt forest must be identical
    # to the committed one; byte identity is asserted on the recording platform.
    sha = "model_artifact_sha256"
    assert {k: v for k, v in first.items() if k != sha} == {
        k: v for k, v in expected.items() if k != sha}
    committed, _ = artifact.load_artifact(ROOT)
    assert len(committed.estimators_) == len(rebuilt.estimators_) == 300
    for a, b in zip(committed.estimators_, rebuilt.estimators_):
        for field in ("children_left", "children_right", "feature", "threshold",
                      "value", "n_node_samples", "weighted_n_node_samples"):
            assert np.array_equal(getattr(a.tree_, field), getattr(b.tree_, field))
    if sys.platform == "win32":
        assert first[sha] == expected[sha]
        assert file_hash(isolated / artifact.MODEL_PATH) == expected[sha]


def test_artifact_lineage_and_native_reconstruction():
    result = artifact.validate_artifact(ROOT)
    assert result["status"] == "PASS"
    model, _ = artifact.load_artifact(ROOT)
    native = pd.read_csv(ROOT / "reports/ml/interpretability/native_feature_importance.csv")
    np.testing.assert_allclose(
        model.feature_importances_,
        native.set_index("feature").loc[list(FEATURES), "importance"].to_numpy(),
        rtol=0, atol=1e-12)


def test_predict_class_alignment_no_model_mutation(batch):
    model, manifest = artifact.load_artifact(ROOT)
    before = file_hash(ROOT / artifact.MODEL_PATH)
    batch.insert(0, "row_id", range(100, 116))
    result = predict_frame(batch, model, manifest)
    again = predict_frame(batch[batch.columns[::-1]], model, manifest)
    pd.testing.assert_frame_equal(result, again, check_exact=True)
    p = result[[f"probability_{c}" for c in manifest["classes"]]].to_numpy()
    assert np.isfinite(p).all() and ((0 <= p) & (p <= 1)).all()
    np.testing.assert_allclose(p.sum(axis=1), 1, rtol=0, atol=1e-12)
    assert result.policy_status.eq("DEVELOPMENT_ONLY").all()
    assert result.row_id.tolist() == list(range(100, 116))
    assert before == file_hash(ROOT / artifact.MODEL_PATH)


@pytest.mark.parametrize("problem", ["missing", "extra", "target", "nan", "infinity",
                                    "text", "bool", "steel", "duplicate_id", "duplicate_column", "empty"])
def test_schema_fail_closed(batch, problem):
    if problem == "missing":
        batch = batch.drop(columns=[FEATURES[0]])
    elif problem in ("extra", "target"):
        batch["surprise" if problem == "extra" else "Pastry"] = 1
    elif problem == "nan":
        batch.loc[0, FEATURES[0]] = np.nan
    elif problem == "infinity":
        batch[FEATURES[0]] = np.inf
    elif problem == "text":
        batch[FEATURES[0]] = "12"
    elif problem == "bool":
        batch[FEATURES[0]] = True
    elif problem == "steel":
        batch["TypeOfSteel_A300"] = batch["TypeOfSteel_A400"] = 1
    elif problem == "duplicate_id":
        batch["row_id"] = 0
    elif problem == "duplicate_column":
        batch = pd.concat([batch, batch[[FEATURES[0]]]], axis=1)
    else:
        batch = batch.iloc[:0]
    with pytest.raises(ValueError):
        validate_schema(batch)


@pytest.mark.parametrize("key,value", [("feature_count", 26), ("train_size", 1941),
    ("model_name", "alternative"), ("post_holdout_tuning", True),
    ("model_artifact", "../untrusted.joblib"), ("model_config_fingerprint", "invalid"),
    ("final_holdout_macro_f1", 1.0), ("dataset_fingerprint", "invalid"),
    ("review_policy_fingerprint", "invalid")])
def test_manifest_tamper_rejected(isolated, key, value):
    path = isolated / artifact.MANIFEST_PATH
    m = json.loads(path.read_text())
    m[key] = value
    artifact.write_json(path, m)
    with pytest.raises(ValueError):
        artifact.validate_artifact(isolated)


def test_corrupt_binary_rejected_before_deserialization(isolated, monkeypatch):
    with (isolated / artifact.MODEL_PATH).open("ab") as f:
        f.write(b"corruption")
    def forbidden(*args, **kwargs):
        raise AssertionError("Corrupt artifact was deserialized")
    monkeypatch.setattr(artifact.joblib, "load", forbidden)
    with pytest.raises(ValueError, match="SHA256"):
        artifact.load_artifact(isolated)


def test_runtime_incompatibility_rejected(isolated, monkeypatch):
    versions = artifact.runtime_versions()
    versions["scikit-learn"] = "0.0"
    monkeypatch.setattr(artifact, "runtime_versions", lambda: versions)
    with pytest.raises(ValueError, match="runtime"):
        artifact.load_artifact(isolated)


def test_batch_cli_and_duplicate_header(tmp_path, batch):
    source, target = tmp_path / "input.csv", tmp_path / "output.csv"
    batch.to_csv(source, index=False)
    import os
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONDONTWRITEBYTECODE="1")
    run = subprocess.run([sys.executable, "-B", "-m", "quality_ml.inference.predict",
        "--root", str(ROOT), "--input", str(source), "--output", str(target)],
        cwd=tmp_path, env=env, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert len(pd.read_csv(target)) == len(batch)
    before = target.read_bytes()
    rerun = subprocess.run([sys.executable, "-B", "-m", "quality_ml.inference.predict",
        "--root", str(ROOT), "--input", str(source), "--output", str(target)],
        cwd=tmp_path, env=env, capture_output=True, text=True)
    assert rerun.returncode != 0 and target.read_bytes() == before
    source.write_text("a,a\n1,2\n")
    with pytest.raises(ValueError, match="Duplicate"):
        read_batch(source)