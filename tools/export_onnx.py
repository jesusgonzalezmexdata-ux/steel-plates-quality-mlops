"""Export the frozen Random Forest to ONNX and verify it against scikit-learn.

Usage from the repository root:
  python -B -m tools.export_onnx            # export + verify + write the report
  python -B -m tools.export_onnx --check    # export + verify against the committed report

Requires requirements-onnx.txt. The ONNX file is a derived artifact: it never
replaces the frozen joblib model and is verified only on training rows and
seeded synthetic rows (no holdout inference).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
ONNX_PATH = "artifacts/onnx/final_random_forest.onnx"
REPORT_PATH = "reports/onnx/verification.json"
FIXTURE_PATH = "reports/onnx/fixture.json"
ATOL = 1e-6  # float32 tree semantics (scikit-learn casts inputs to float32)
TARGET_OPSET = {"": 17, "ai.onnx.ml": 3}


def export(model) -> bytes:
    from skl2onnx import to_onnx
    from skl2onnx.common.data_types import FloatTensorType

    return to_onnx(model, initial_types=[("input", FloatTensorType([None, 27]))],
                   options={id(model): {"zipmap": False}},
                   target_opset=TARGET_OPSET).SerializeToString()


def review_status(probabilities):
    top = probabilities.max(axis=1)
    return np.where(top >= .8, "HIGH_CONFIDENCE",
                    np.where(top >= .5, "REVIEW_REQUIRED", "LOW_CONFIDENCE"))


def verify(model, onnx_bytes, X) -> dict:
    import onnxruntime as ort

    session = ort.InferenceSession(onnx_bytes, providers=["CPUExecutionProvider"])
    rng = np.random.default_rng(42)
    base = X.to_numpy(dtype=np.float64)
    synthetic = base[rng.integers(0, len(base), 2000)] * rng.uniform(.95, 1.05, (2000, 27))
    result = {}
    for name, rows in (("training_rows", base), ("synthetic_rows", synthetic)):
        expected = model.predict_proba(rows)
        labels, observed = session.run(None, {"input": rows.astype(np.float32)})
        diff = float(np.abs(observed - expected).max())
        result[name] = dict(
            n=len(rows), max_abs_probability_diff=diff,
            predicted_class_equal=bool((labels == model.classes_[expected.argmax(1)]).all()),
            review_status_equal=bool((review_status(observed) == review_status(expected)).all()))
        if diff > ATOL or not result[name]["predicted_class_equal"] \
                or not result[name]["review_status_equal"]:
            raise ValueError(f"ONNX diverges from scikit-learn on {name}: {result[name]}")
    return result


def run(check: bool) -> dict:
    import onnx
    import onnxruntime
    import skl2onnx
    from quality_ml.evaluation.protocol import FEATURES, load_phase8
    from quality_ml.inference.artifact import load_artifact, training_data

    model, manifest = load_artifact(ROOT)
    metrics, _, _ = load_phase8(ROOT)
    X, y = training_data(ROOT, metrics)
    onnx_bytes = export(model)
    report = dict(
        source_model=manifest["model_artifact"],
        source_model_sha256=manifest["model_artifact_sha256"],
        model_version=manifest["model_version"],
        onnx_artifact=ONNX_PATH,
        onnx_sha256=hashlib.sha256(onnx_bytes).hexdigest(),
        input=dict(name="input", dtype="float32", shape=[None, 27], features=list(FEATURES)),
        outputs=dict(label="predicted class", probabilities="columns in classes order"),
        classes=list(model.classes_),
        target_opset=TARGET_OPSET,
        tolerance=dict(max_abs_probability_diff=ATOL),
        verification=verify(model, onnx_bytes, X),
        holdout_inference=False,
        versions={"skl2onnx": skl2onnx.__version__, "onnx": onnx.__version__,
                  "onnxruntime": onnxruntime.__version__},
    )
    if check:
        committed = json.loads((ROOT / REPORT_PATH).read_text(encoding="utf-8"))
        if committed["onnx_sha256"] != report["onnx_sha256"]:
            raise ValueError("ONNX export is not byte-identical to the recorded artifact")
    (ROOT / ONNX_PATH).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / ONNX_PATH).write_bytes(onnx_bytes)
    if not check:
        write_json(ROOT / REPORT_PATH, report)
        rows = X.loc[y.groupby(y).head(1).index]
        write_json(ROOT / FIXTURE_PATH, dict(
            source="first training row of each class (TRAINING_ONLY)", features=list(FEATURES),
            classes=list(model.classes_), rows=rows.to_numpy().tolist(),
            expected_probabilities=model.predict_proba(rows).tolist(), atol=ATOL))
    return dict(status="PASS", onnx_sha256=report["onnx_sha256"],
                max_abs_probability_diff=max(v["max_abs_probability_diff"]
                                             for v in report["verification"].values()))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    print(json.dumps(run(parser.parse_args().check), indent=2))


if __name__ == "__main__":
    main()
