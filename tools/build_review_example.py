"""Builds the example for the human-review triage MVP from the real UCI plates.

python -B -m tools.build_review_example

Every plate gets a prediction that its own label never touched: out-of-fold scores from the frozen
cross-validation for the 1,552 training plates and the frozen model's single evaluation for the 389
holdout plates. A stratified 30 % sample by confidence keeps its true class, as a human review would;
the rest keeps it in ``clase_real_oculta`` only so tests can check the estimates against the truth.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from quality_ml.data.split import split_csv
from quality_ml.evaluation.uncertainty import reconstruct_oof

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples" / "review_triage" / "inspeccion_placas.csv"
SAMPLE, SEED = 0.30, 7


def main() -> pd.DataFrame:
    split = split_csv(ROOT / "data" / "raw" / "steel_plates_faults.csv")
    oof, _, _ = reconstruct_oof(split.X_train, split.y_train, list(split.train_positions))
    train = pd.DataFrame({"row": oof.row_id, "clase_real": oof.actual_class, "clase_predicha": oof.predicted_class,
                          "confianza": oof.max_probability, "origen": "validación cruzada"})
    hold = pd.read_csv(ROOT / "reports" / "ml" / "final_holdout" / "predictions.csv")
    hold = pd.DataFrame({"row": hold.row_index, "clase_real": hold.actual_class, "clase_predicha": hold.predicted_class,
                         "confianza": hold.max_probability, "origen": "evaluación final"})
    df = pd.concat([train, hold]).sort_values("row").reset_index(drop=True)
    rng = np.random.default_rng(SEED)
    band = pd.cut(df.confianza, [0, 0.5, 0.65, 0.8, 0.9, 1.0], include_lowest=True)
    reviewed = np.zeros(len(df), bool)
    for _, idx in df.groupby(band, observed=True).groups.items():
        idx = np.asarray(list(idx))
        reviewed[rng.choice(idx, size=int(round(len(idx) * SAMPLE)), replace=False)] = True
    out = pd.DataFrame({"pieza": [f"P{r:04d}" for r in df.row], "clase_predicha": df.clase_predicha,
                        "confianza": df.confianza.round(4), "clase_real": np.where(reviewed, df.clase_real, ""),
                        "clase_real_oculta": df.clase_real, "origen": df.origen})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    return out


if __name__ == "__main__":
    o = main()
    print(f"{len(o)} plates, {int((o.clase_real != '').sum())} reviewed, written to {OUT.relative_to(ROOT)}")
