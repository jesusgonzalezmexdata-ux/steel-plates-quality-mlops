"""Final-holdout BI export from frozen predictions, never from new inference."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd

from quality_ml.evaluation.protocol import (
    CLASSES, CONFIDENCE_EDGES, digest, file_hash, load_phase8,
)
from quality_ml.evaluation.uncertainty import policy_labels
from quality_ml.inference.artifact import MODEL_VERSION, POLICY_PATH, write_json

EXPORT_PATH = "powerbi/data/ml_holdout_evaluation.csv"
BASELINE_PATH = "docs/evidence/pre_ml_powerbi_hashes.json"
EXPECTED_PATH = "reports/ml/integration/reconciliation_expected.json"
COLUMNS = ("row_id", "source_id", "actual_defect", "predicted_defect",
    "correct_prediction", "confidence", "review_status", "review_required",
    "steel_type", "steel_plate_thickness", "pixels_area", "confidence_bin",
    "dataset_role", "policy_status", "policy_application", "model_version")


def export_frame(root):
    root = Path(root)
    metrics, predictions, _ = load_phase8(root)
    protocol = json.loads((root / POLICY_PATH).read_text(encoding="utf-8"))
    policy = protocol["review_policy_candidate"]
    if digest(policy) != protocol["review_policy_hash"]:
        raise ValueError("Review policy changed")
    raw = pd.read_csv(root / "data/raw/steel_plates_faults.csv")
    features = raw.iloc[predictions.row_index].reset_index(drop=True)
    labels = policy_labels(predictions, policy)
    confidence = predictions.max_probability.to_numpy()
    bins = np.minimum(np.searchsorted(CONFIDENCE_EDGES, confidence, side="right") - 1, 5)
    bin_labels = ["[0.00,0.50)", "[0.50,0.60)", "[0.60,0.70)",
                  "[0.70,0.80)", "[0.80,0.90)", "[0.90,1.00]"]
    result = pd.DataFrame(dict(
        row_id=predictions.row_index, source_id=features.id,
        actual_defect=predictions.actual_class, predicted_defect=predictions.predicted_class,
        correct_prediction=predictions.correct_prediction.astype(int),
        confidence=confidence, review_status=labels,
        review_required=(labels != "HIGH_CONFIDENCE").astype(int),
        steel_type=np.where(features.TypeOfSteel_A300.eq(1), "A300", "A400"),
        steel_plate_thickness=features.Steel_Plate_Thickness,
        pixels_area=features.Pixels_Areas, confidence_bin=np.array(bin_labels)[bins],
        dataset_role="FINAL_HOLDOUT_EVALUATION", policy_status=policy["status"],
        policy_application="POST_HOC_ONLY", model_version=MODEL_VERSION,
    ))
    if tuple(result.columns) != COLUMNS:
        raise ValueError("BI column order mismatch")
    return result, metrics


def reconciliation(frame, metrics):
    correct = frame.correct_prediction.astype(bool)
    review = frame.review_required.astype(bool)
    return dict(
        dataset_role="FINAL_HOLDOUT_EVALUATION", runtime_status="PENDING_DESKTOP",
        rows=len(frame), correct=int(correct.sum()), errors=int((~correct).sum()),
        review_rows=int(review.sum()), accepted_rows=int((~review).sum()),
        errors_sent_to_review=int((review & ~correct).sum()),
        errors_not_captured=int((~review & ~correct).sum()),
        review_rate=float(review.mean()), macro_f1=metrics["metrics"]["macro_f1"],
        balanced_accuracy=metrics["metrics"]["balanced_accuracy"],
        actual_counts={c: int(frame.actual_defect.eq(c).sum()) for c in CLASSES},
        prediction_counts={c: int(frame.predicted_defect.eq(c).sum()) for c in CLASSES},
        review_counts={c: int(frame.review_status.eq(c).sum())
            for c in ("HIGH_CONFIDENCE", "REVIEW_REQUIRED", "LOW_CONFIDENCE")},
        class_counts=[dict(actual_class=c, support=int(frame.actual_defect.eq(c).sum()),
            errors=int((frame.actual_defect.eq(c) & ~correct).sum())) for c in CLASSES],
    )


def snapshot_powerbi(root):
    """One-time pre-change inventory. Never overwrite the baseline."""
    root = Path(root)
    output = root / BASELINE_PATH
    if output.exists():
        raise ValueError("Pre-ML baseline already exists")
    command = ["git", "-c", f"safe.directory={root.resolve().as_posix()}"]
    tracked = subprocess.check_output(command + ["ls-files", "powerbi"], cwd=root, text=True).splitlines()
    files = {}
    for name in tracked:
        path = root / name
        data = path.read_bytes()
        import hashlib
        files[name] = dict(sha256=file_hash(path), bytes=len(data))
        if path.suffix.lower() != ".pbix":
            files[name]["lf_sha256"] = hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()
    result = dict(source_head=subprocess.check_output(
        command + ["rev-parse", "HEAD"], cwd=root, text=True).strip(),
        purpose="PRE_ML_POWER_BI_HASHES", files=files)
    write_json(output, result)
    return dict(files=len(files), output=BASELINE_PATH)


def validate_export(root):
    root = Path(root)
    expected, metrics = export_frame(root)
    actual = pd.read_csv(root / EXPORT_PATH, float_precision="round_trip")
    pd.testing.assert_frame_equal(actual, expected, check_exact=False, rtol=0, atol=1e-12)
    if len(actual) != 389 or actual.row_id.duplicated().any():
        raise ValueError("BI row identities mismatch")
    if json.loads((root / EXPECTED_PATH).read_text(encoding="utf-8")) != reconciliation(expected, metrics):
        raise ValueError("Reconciliation expectation mismatch")
    return dict(status="PASS", rows=len(actual), correct=int(actual.correct_prediction.sum()),
                errors=int((1 - actual.correct_prediction).sum()),
                review_rows=int(actual.review_required.sum()),
                scope="Python export only; Desktop reconciliation PENDING")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["export", "validate", "snapshot"])
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    if args.action == "snapshot":
        result = snapshot_powerbi(args.root)
    elif args.action == "validate":
        result = validate_export(args.root)
    else:
        frame, metrics = export_frame(args.root)
        output = args.root / EXPORT_PATH
        output.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(output, index=False, lineterminator="\n", float_format="%.17g")
        write_json(args.root / EXPECTED_PATH, reconciliation(frame, metrics))
        result = validate_export(args.root)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()