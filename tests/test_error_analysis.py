"""Artifact consistency and train-defined segment checks."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from quality_ml.evaluation import error_analysis as errors
from quality_ml.evaluation.protocol import (
    ATOL, FEATURES, MIN_SAMPLE, PHASE_8_HASHES, file_hash, load_phase8,
)

ROOT = Path(__file__).resolve().parents[1]


def test_phase8_predictions_metrics_and_hashes_unchanged():
    metrics, predictions, matrix = load_phase8(ROOT)
    assert len(predictions) == 389 and matrix.to_numpy().sum() == 389
    assert metrics["metrics"]["macro_f1"] == pytest.approx(0.8146728101764369, abs=ATOL)
    for name, expected in PHASE_8_HASHES.items():
        assert file_hash(ROOT / "reports/ml/final_holdout" / name) == expected
    assert np.trace(matrix.to_numpy()) == predictions.correct_prediction.sum() == 307


def test_class_and_confusion_accounting(phase9_run):
    frames, docs, matrix = phase9_run
    classes = frames["error_analysis/class_error_summary.csv"]
    pairs = frames["error_analysis/confusion_pairs.csv"]
    assert pairs["count"].sum() == classes.false_negative.sum() == 82
    assert classes.false_positive.sum() == 82
    assert classes.support.sum() == 389
    assert (pairs.actual_class != pairs.predicted_class).all()
    assert pairs["count"].is_monotonic_decreasing
    assert classes.loc[classes.support < MIN_SAMPLE, "status"].eq("INSUFFICIENT_SUPPORT").all()
    assert (classes.true_positive + classes.false_negative == classes.support).all()
    assert docs["error_analysis/analysis_summary.json"]["total_correct"] == 307


def test_segment_spec_is_training_only_and_applied_without_rebinning():
    training = pd.DataFrame({f: np.arange(100, dtype=float) for f in FEATURES})
    training["TypeOfSteel_A300"] = np.arange(100) % 2
    training["TypeOfSteel_A400"] = 1 - training.TypeOfSteel_A300
    spec = errors.training_segment_spec(training)
    assert spec["Pixels_Areas"]["cuts"] == [24.75, 49.5, 74.25]
    holdout = training.iloc[:4].copy().reset_index(drop=True)
    holdout["Pixels_Areas"] = [-100, 24.75, 49.5, 1000]
    frame = pd.DataFrame({"actual_class": ["Pastry"] * 4,
                          "correct_prediction": [True, False, True, False]})
    before = json.dumps(spec, sort_keys=True)
    result = errors.segment_errors(holdout, frame, spec)
    area = result.loc[(result.feature == "Pixels_Areas") & (result.actual_class == "ALL")]
    assert area.n.tolist() == [2, 1, 0, 1]
    assert result.status.eq("INSUFFICIENT_DATA").all()
    assert json.dumps(spec, sort_keys=True) == before


def test_segments_partition_and_small_samples_are_marked(phase9_run):
    table = phase9_run[0]["error_analysis/segment_errors.csv"]
    overall = table.loc[table.actual_class == "ALL"]
    assert set(overall.feature) == set(FEATURES)
    assert overall.groupby("feature").n.sum().eq(389).all()
    assert overall.groupby("feature").errors.sum().eq(82).all()
    assert (table.correct + table.errors == table.n).all()
    assert table.loc[table.n < MIN_SAMPLE, "status"].eq("INSUFFICIENT_DATA").all()
    defined = table.loc[table.n > 0]
    assert (defined.error_rate_wilson_low <= defined.error_rate).all()
    assert (defined.error_rate_wilson_high >= defined.error_rate).all()


@pytest.mark.parametrize("n", [1, 3, 10, 30, 100, 389])
def test_wilson_exact_endpoints(n):
    assert errors._wilson(0, n)[0] == 0.0
    assert errors._wilson(n, n)[1] == 1.0
