"""Cost sensitivity of the development-only human-review policy.

Usage from the repository root: python -B -m tools.review_cost

Compares three policies under an explicit, assumed cost model:
  NO_REVIEW      accept every prediction
  REVIEW_ALL     send every plate to human review
  FROZEN_POLICY  review when top-1 confidence < 0.80 (frozen in Phase 9)

cost = c_review * reviewed_rows + c_miss * uncaught_errors, where a reviewer
catches each error sent to review with probability r (reviewer recall).
Only the ratio R = c_miss / c_review matters. The frozen policy is cheapest
exactly when n_review / (r * errors_in_review) < R < n_accepted / (r * errors_accepted).

Development OOF predictions are the primary evidence. The holdout rows are the
saved post-hoc application already reported; they are described, never used to
choose a threshold. No costs are real: they are user-supplied assumptions.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OOF = "reports/ml/uncertainty/oof_predictions.csv"
HOLDOUT = "powerbi/data/ml_holdout_evaluation.csv"
OUTPUT = "reports/ml/decision/review_cost.json"
RATIOS = [1, 2, 3, 5, 10, 20, 50, 100, 200]
RECALLS = [1.0, 0.9, 0.8]
EXAMPLE_RATIOS = [10, 20]  # illustrative R values for the per-1,000-plates summary


def counts(correct, confidence, threshold):
    correct = correct.astype(bool)
    review = confidence < threshold
    return dict(n=int(len(correct)), n_review=int(review.sum()), n_accepted=int((~review).sum()),
                errors=int((~correct).sum()), errors_in_review=int((~correct & review).sum()),
                errors_accepted=int((~correct & ~review).sum()))


def policy_costs(c, ratio, recall):
    """Cost per unit of review cost (c_review = 1, c_miss = ratio)."""
    missed_in_review = (1 - recall) * c["errors_in_review"]
    return {
        "NO_REVIEW": ratio * c["errors"],
        "REVIEW_ALL": c["n"] + ratio * (1 - recall) * c["errors"],
        "FROZEN_POLICY": c["n_review"] + ratio * (c["errors_accepted"] + missed_in_review),
    }


def break_even(c, recall):
    lower = c["n_review"] / (recall * c["errors_in_review"])
    upper = (c["n_accepted"] / (recall * c["errors_accepted"])
             if c["errors_accepted"] else float("inf"))
    return dict(frozen_policy_cheapest_if_ratio_above=lower,
                frozen_policy_cheapest_if_ratio_below=upper)


def analyse(c):
    table = []
    for recall in RECALLS:
        for ratio in RATIOS:
            costs = policy_costs(c, ratio, recall)
            table.append(dict(reviewer_recall=recall, cost_ratio_miss_to_review=ratio,
                              cheapest=min(costs, key=costs.get),
                              **{k: round(v, 6) for k, v in costs.items()}))
    per_1000 = {str(r): {k: round(1000 * v / c["n"], 1) for k, v in policy_costs(c, r, 1.0).items()}
                for r in EXAMPLE_RATIOS}
    return dict(counts=c, break_even={str(r): break_even(c, r) for r in RECALLS}, grid=table,
                per_1000_plates_review_units=per_1000)


def run(root=ROOT) -> dict:
    root = Path(root)
    manifest = json.loads((root / "artifacts/manifest.json").read_text(encoding="utf-8"))
    threshold = manifest["review_policy"]["high_threshold"]
    oof = pd.read_csv(root / OOF)
    holdout = pd.read_csv(root / HOLDOUT)
    result = dict(
        purpose="Assumption-based cost sensitivity; no real costs, savings or new thresholds",
        policy_status=manifest["review_policy"]["status"],
        threshold=threshold,
        cost_model="cost = c_review*reviewed + c_miss*uncaught_errors; reviewer catches an error with probability r",
        development_oof=dict(evidence="DEVELOPMENT_OOF",
                             **analyse(counts(oof.correct_prediction, oof.max_probability, threshold))),
        holdout_post_hoc=dict(evidence="POST_HOC_DESCRIPTION_ONLY",
                              **analyse(counts(holdout.correct_prediction, holdout.confidence, threshold))),
    )
    (root / OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    (root / OUTPUT).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    result = run()
    for part in ("development_oof", "holdout_post_hoc"):
        c, b = result[part]["counts"], result[part]["break_even"]["1.0"]
        print(f"{part}: review {c['n_review']}/{c['n']}, errors caught {c['errors_in_review']}/{c['errors']}; "
              f"frozen policy cheapest for {b['frozen_policy_cheapest_if_ratio_above']:.2f} < R < "
              f"{b['frozen_policy_cheapest_if_ratio_below']:.2f} (perfect reviewer)")


if __name__ == "__main__":
    main()
