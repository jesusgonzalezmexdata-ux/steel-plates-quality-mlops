"""Input-drift monitoring for the frozen classifier (python -B -m tools.drift_check).

Reference: the 1,552 training plates. For a batch of new plates it reports, per measurement,
the population stability index (PSI) and the share of values outside the training range.
It never changes the model. The holdout batch is a sanity check (same population, should pass);
the perturbed batches show what a unit change or a camera recalibration would look like.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from quality_ml.evaluation.protocol import FEATURES  # noqa: E402
from quality_ml.models.final_holdout import _read_rows  # noqa: E402
OUTPUT = "reports/ml/monitoring/drift.json"
PSI_MODERATE, PSI_MAJOR, OUT_OF_RANGE = 0.10, 0.25, 0.05
EPS = 1e-4


def reference(train: pd.DataFrame, bins: int = 10) -> dict:
    ref = {}
    for f in FEATURES:
        v = train[f].to_numpy(dtype=float)
        edges = np.unique(np.quantile(v, np.linspace(0, 1, bins + 1)[1:-1]))
        counts = np.bincount(np.searchsorted(edges, v, side="right"), minlength=len(edges) + 1)
        ref[f] = dict(edges=edges.tolist(), proportions=(counts / len(v)).tolist(),
                      low=float(v.min()), high=float(v.max()))
    return ref


def psi(expected, actual) -> float:
    e = np.clip(np.asarray(expected, dtype=float), EPS, None)
    a = np.clip(np.asarray(actual, dtype=float), EPS, None)
    return float(np.sum((a - e) * np.log(a / e)))


def check(ref: dict, batch: pd.DataFrame) -> dict:
    rows = {}
    for f, r in ref.items():
        v = batch[f].to_numpy(dtype=float)
        counts = np.bincount(np.searchsorted(np.asarray(r["edges"]), v, side="right"), minlength=len(r["edges"]) + 1)
        rows[f] = dict(psi=round(psi(r["proportions"], counts / len(v)), 4),
                       out_of_range=round(float(np.mean((v < r["low"]) | (v > r["high"]))), 4))
    major = sorted(f for f, r in rows.items() if r["psi"] >= PSI_MAJOR)
    moderate = sorted(f for f, r in rows.items() if PSI_MODERATE <= r["psi"] < PSI_MAJOR)
    outside = sorted(f for f, r in rows.items() if r["out_of_range"] > OUT_OF_RANGE)
    status = "ALERT" if major or outside else ("WARN" if moderate else "OK")
    return dict(status=status, plates=int(len(batch)), psi_major=major, psi_moderate=moderate,
                out_of_range=outside, max_psi=max(r["psi"] for r in rows.values()))


def run(root: Path = ROOT) -> dict:
    root = Path(root)
    split = json.loads((root / "reports/ml/final_holdout/metrics.json").read_text(encoding="utf-8"))["split"]
    raw = root / "data/raw/steel_plates_faults.csv"
    train = _read_rows(raw, split["train_positions"])[list(FEATURES)]
    holdout = _read_rows(raw, split["holdout_positions"])[list(FEATURES)]
    ref = reference(train)
    thickness_cm = holdout.assign(Steel_Plate_Thickness=holdout["Steel_Plate_Thickness"] / 10)
    brighter = holdout.copy()
    for f in ("Sum_of_Luminosity", "Minimum_of_Luminosity", "Maximum_of_Luminosity"):
        brighter[f] = brighter[f] * 1.15
    batches = {
        "Holdout plates (same population)": holdout,
        "Unit change: thickness reported in cm instead of mm": thickness_cm,
        "Camera recalibration: luminosity +15 %": brighter,
    }
    result = dict(reference="1,552 training plates", thresholds=dict(psi_moderate=PSI_MODERATE, psi_major=PSI_MAJOR,
                  out_of_range=OUT_OF_RANGE), batches={k: check(ref, v) for k, v in batches.items()})
    (root / OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    (root / OUTPUT).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    for name, r in run()["batches"].items():
        print(f"{name}: {r['status']} major={r['psi_major']} outside={r['out_of_range']} max_psi={r['max_psi']}")
