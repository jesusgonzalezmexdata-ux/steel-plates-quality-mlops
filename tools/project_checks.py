"""Repository commands; run from a checkout without an editable installation."""
from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def check(action, root=ROOT):
    from quality_ml.evaluation.protocol import FEATURES, load_phase8
    from quality_ml.inference.artifact import (
        load_artifact, training_data, validate_artifact,
    )
    from quality_ml.inference.predict import predict_frame
    root = Path(root)
    if action == "lint":
        files = [p for folder in ("src", "qbi", "etl", "tools", "tests")
                 for p in (root / folder).rglob("*.py")]
        files.append(root / "streamlit_app.py")
        for path in files:
            ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path.relative_to(root)))
        return dict(status="PASS", check="Python AST syntax (not Ruff)", files=len(files))
    if action == "test":
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        subprocess.run([sys.executable, "-B", "-m", "pytest"], cwd=root, env=env, check=True)
        return dict(status="PASS")
    if action == "validate-data":
        from quality_ml.data.audit import audit_dataset, load_dataset
        audit = audit_dataset(load_dataset(root / "data/raw/steel_plates_faults.csv"))
        if audit["rows"] != 1941 or audit["missing_total"] != 0 or audit["duplicate_rows"] != 0:
            raise ValueError("Dataset audit mismatch")
        load_phase8(root)
        return dict(status="PASS", rows=1941, features=len(FEATURES))
    if action == "validate-artifact":
        return validate_artifact(root)
    if action == "batch-smoke":
        model, manifest = load_artifact(root)
        metrics, _, _ = load_phase8(root)
        X, _ = training_data(root, metrics)
        result = predict_frame(X.iloc[:8], model, manifest)
        return dict(status="PASS", rows=len(result), input_role="TRAINING_ONLY",
                    model_version=manifest["model_version"])
    if action == "train-smoke":
        import numpy as np
        from quality_ml.evaluation.protocol import assert_frozen
        metrics, _, _ = load_phase8(root)
        X, y = training_data(root, metrics)
        model = assert_frozen().fit(X.iloc[:128], y.iloc[:128])
        validation = X.iloc[128:160]
        probabilities = model.predict_proba(validation)
        if not np.allclose(probabilities.sum(axis=1), 1):
            raise ValueError("Smoke probabilities invalid")
        return dict(status="PASS", fit_rows=128, validation_rows=32,
                    input_role="TRAINING_ONLY", purpose="Execution smoke; no scientific metric")
    if action == "validate-evidence":
        load_phase8(root)
        validate_artifact(root)
        from quality_ml.inference.bi_export import validate_export
        return validate_export(root)
    raise ValueError(action)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["validate-data", "test", "lint", "train-smoke",
        "validate-artifact", "batch-smoke", "validate-evidence"])
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(check(args.action, args.root), indent=2))


if __name__ == "__main__":
    main()