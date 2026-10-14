"""ONNX export of the frozen model: deterministic and equivalent to scikit-learn."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("skl2onnx", reason="requires requirements-onnx.txt")
ort = pytest.importorskip("onnxruntime", reason="requires requirements-onnx.txt")
from tools import export_onnx  # noqa: E402
from quality_ml.evaluation.protocol import FEATURES, load_phase8  # noqa: E402
from quality_ml.inference.artifact import load_artifact, training_data  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def frozen():
    model, manifest = load_artifact(ROOT)
    metrics, _, _ = load_phase8(ROOT)
    X, y = training_data(ROOT, metrics)
    return model, manifest, X, y, export_onnx.export(model)


def test_export_is_deterministic_and_matches_report(frozen):
    model, manifest, _, _, onnx_bytes = frozen
    report = json.loads((ROOT / export_onnx.REPORT_PATH).read_text(encoding="utf-8"))
    assert hashlib.sha256(onnx_bytes).hexdigest() == report["onnx_sha256"]
    assert export_onnx.export(model) == onnx_bytes
    assert report["source_model_sha256"] == manifest["model_artifact_sha256"]
    assert report["input"]["features"] == list(FEATURES)
    assert report["classes"] == list(model.classes_)
    assert report["holdout_inference"] is False


def test_onnx_equivalent_to_sklearn(frozen):
    model, _, X, _, onnx_bytes = frozen
    result = export_onnx.verify(model, onnx_bytes, X)
    for part in result.values():
        assert part["max_abs_probability_diff"] <= export_onnx.ATOL
        assert part["predicted_class_equal"] and part["review_status_equal"]


def test_fixture_is_training_only_and_covers_every_class(frozen):
    model, _, X, y, onnx_bytes = frozen
    fixture = json.loads((ROOT / export_onnx.FIXTURE_PATH).read_text(encoding="utf-8"))
    rows = np.array(fixture["rows"])
    expected = X.loc[y.groupby(y).head(1).index].to_numpy()
    np.testing.assert_array_equal(rows, expected)
    assert sorted(y.loc[y.groupby(y).head(1).index]) == sorted(model.classes_)
    session = ort.InferenceSession(onnx_bytes, providers=["CPUExecutionProvider"])
    _, probabilities = session.run(None, {"input": rows.astype(np.float32)})
    np.testing.assert_allclose(probabilities, fixture["expected_probabilities"],
                               rtol=0, atol=fixture["atol"])


def test_divergent_model_is_rejected(frozen):
    model, _, X, _, onnx_bytes = frozen
    from sklearn.base import clone
    other = clone(model).set_params(n_estimators=10).fit(X, model.predict(X))
    with pytest.raises(ValueError, match="diverges"):
        export_onnx.verify(model, export_onnx.export(other), X)
