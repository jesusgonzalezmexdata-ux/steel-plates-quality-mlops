"""Review-policy cost sensitivity: consistent with frozen evidence and with brute force."""
import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd
import pytest

from tools import review_cost

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    root = tmp_path_factory.mktemp("repo")
    for name in ("artifacts/manifest.json", review_cost.OOF, review_cost.HOLDOUT):
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, root / name)
    return review_cost.run(root)


def test_counts_match_recorded_evidence(result):
    tradeoff = pd.read_csv(ROOT / "reports/ml/uncertainty/threshold_tradeoff.csv").set_index("threshold")
    oof = result["development_oof"]["counts"]
    assert (oof["n_accepted"], oof["n_review"], oof["errors_accepted"]) == (
        tradeoff.loc[0.8, "accepted_rows"], tradeoff.loc[0.8, "review_rows"],
        tradeoff.loc[0.8, "high_confidence_errors"])
    holdout = result["holdout_post_hoc"]["counts"]
    assert (holdout["n"], holdout["errors"], holdout["n_review"], holdout["errors_in_review"]) == (389, 82, 261, 81)
    assert result["threshold"] == 0.8 and result["policy_status"] == "DEVELOPMENT_ONLY"


@pytest.mark.parametrize("part", ["development_oof", "holdout_post_hoc"])
@pytest.mark.parametrize("recall", review_cost.RECALLS)
def test_break_even_matches_brute_force(result, part, recall):
    c = result[part]["counts"]
    bounds = result[part]["break_even"][str(recall)]
    lower, upper = (bounds["frozen_policy_cheapest_if_ratio_above"],
                    bounds["frozen_policy_cheapest_if_ratio_below"])
    for ratio in np.linspace(0.5, 300, 6000):
        costs = review_cost.policy_costs(c, ratio, recall)
        frozen_cheapest = costs["FROZEN_POLICY"] < min(costs["NO_REVIEW"], costs["REVIEW_ALL"])
        assert frozen_cheapest == (lower < ratio < upper)


def test_committed_report_is_reproducible(result):
    committed = json.loads((ROOT / review_cost.OUTPUT).read_text(encoding="utf-8"))
    assert committed == json.loads(json.dumps(result))


def test_per_1000_summary_matches_grid(result):
    c = result["development_oof"]["counts"]
    for ratio, row in result["development_oof"]["per_1000_plates_review_units"].items():
        costs = review_cost.policy_costs(c, float(ratio), 1.0)
        for policy, value in row.items():
            assert value == round(1000 * costs[policy] / c["n"], 1)
