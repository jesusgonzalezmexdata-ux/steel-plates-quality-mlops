"""Strict, local batch inference from the frozen artifact."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import pandas as pd

from quality_ml.evaluation.protocol import CLASSES, FEATURES, assert_frozen
from quality_ml.evaluation.uncertainty import policy_labels
from quality_ml.inference.artifact import load_artifact
from quality_ml.models.final_holdout import validate_probabilities


def validate_schema(frame):
    if not frame.columns.is_unique:
        raise ValueError("Duplicate input columns")
    missing = set(FEATURES) - set(frame.columns)
    extra = set(frame.columns) - set(FEATURES) - {"row_id"}
    if missing or extra:
        raise ValueError(f"Incompatible schema: missing={sorted(missing)}, unexpected={sorted(extra)}")
    if frame.empty:
        raise ValueError("Empty batch")
    if "row_id" in frame and (frame.row_id.isna().any() or frame.row_id.duplicated().any()):
        raise ValueError("row_id must be nonmissing and unique")
    X = frame[list(FEATURES)]
    if any(not pd.api.types.is_numeric_dtype(t) or pd.api.types.is_bool_dtype(t)
           for t in X.dtypes):
        raise ValueError("All features must be numeric, not text or boolean")
    if not np.isfinite(X.to_numpy(dtype=float)).all():
        raise ValueError("Missing or nonfinite feature values")
    steel = X[["TypeOfSteel_A300", "TypeOfSteel_A400"]]
    if not steel.isin([0, 1]).all().all() or not steel.sum(axis=1).eq(1).all():
        raise ValueError("Steel indicators must be one-hot")
    return X


def read_batch(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as source:
        header = next(csv.reader(source), [])
    if len(header) != len(set(header)):
        raise ValueError("Duplicate CSV header")
    frame = pd.read_csv(path, float_precision="round_trip")
    validate_schema(frame)
    return frame


def predict_frame(frame, model, manifest):
    X = validate_schema(frame)
    assert_frozen(model, X.columns)
    probabilities = model.predict_proba(X)
    validate_probabilities(probabilities, model.classes_, n_rows=len(X))
    ordered = np.sort(probabilities, axis=1)
    result = pd.DataFrame(dict(
        row_id=frame.row_id.to_numpy() if "row_id" in frame else np.arange(len(frame)),
        predicted_class=model.classes_[probabilities.argmax(axis=1)],
        max_probability=ordered[:, -1], second_probability=ordered[:, -2],
        probability_margin=ordered[:, -1] - ordered[:, -2],
    ))
    for label in CLASSES:
        result[f"probability_{label}"] = probabilities[:, list(model.classes_).index(label)]
    result["review_status"] = policy_labels(result, manifest["review_policy"])
    result["policy_status"] = manifest["review_policy"]["status"]
    result["model_version"] = manifest["model_version"]
    result["validity_scope"] = manifest["validity_scope"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error("Output must not overwrite input")
    if args.output.exists():
        parser.error("Output exists; choose a new output path")
    model, manifest = load_artifact(args.root)
    result = predict_frame(read_batch(args.input), model, manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False, lineterminator="\n", float_format="%.17g")
    print(f"{len(result)} rows; {manifest['model_version']}; policy DEVELOPMENT_ONLY")


if __name__ == "__main__":
    main()