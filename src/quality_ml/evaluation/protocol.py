"""Immutable Phase 9 contract and read-only checks of Phase 8 evidence."""

from __future__ import annotations

import hashlib
import json
from types import MappingProxyType

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from quality_ml.data.audit import TARGET_COLUMNS
from quality_ml.models import final_holdout
from quality_ml.models.baseline import validate_feature_matrix

PHASE_8 = "269b38cdced47f8c392a59b0bf9b6bbd298a363a"
PHASE_8_STATE = "dfe5185b26da3133ed0a6c4b26b7bc906eae177b"
CONFIG = MappingProxyType(dict(n_estimators=300, min_samples_leaf=2,
    max_features="sqrt", max_depth=20, class_weight="balanced", random_state=42, n_jobs=1))
FEATURES = (
    "X_Minimum", "X_Maximum", "Y_Minimum", "Y_Maximum", "Pixels_Areas",
    "X_Perimeter", "Y_Perimeter", "Sum_of_Luminosity", "Minimum_of_Luminosity",
    "Maximum_of_Luminosity", "Length_of_Conveyer", "TypeOfSteel_A300",
    "TypeOfSteel_A400", "Steel_Plate_Thickness", "Edges_Index", "Empty_Index",
    "Square_Index", "Outside_X_Index", "Edges_X_Index", "Edges_Y_Index",
    "Outside_Global_Index", "LogOfAreas", "Log_X_Index", "Log_Y_Index",
    "Orientation_Index", "Luminosity_Index", "SigmoidOfAreas",
)
CLASSES = ("Pastry", "Z_Scratch", "K_Scatch", "Stains", "Dirtiness", "Bumps", "Other_Faults")
MIN_SAMPLE = 30
CONFIDENCE_EDGES = (0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
MARGIN_EDGES = (0.0, 0.1, 0.2, 0.4, 0.6, 0.8, 1.0)
THRESHOLDS = (0.60, 0.70, 0.80, 0.90)
CANDIDATE_THRESHOLD = 0.80
LOW_THRESHOLD = 0.50
PERMUTATION_REPEATS = 5
ATOL = 1e-12
PHASE_8_HASHES = {
    "predictions.csv": "f365dba807442658aded2e86b58bfd72b9625240a9504bdeb8e071dcbc946d50",
    "metrics.json": "18d4fbd6d41e845eb2f975bc3ded28dc1bdc9851f49db81a80a28fe5a5e603f3",
    "confusion_matrix.csv": "d5ee3bc12d0ba22ec3658605711de60f09d88e84ef13fe2bede2c031b6c88826",
    "probabilities_snapshot.csv": "cbebd26329164c387bffd6fbd265cdb1f4ce04696512c2331829754582035b44",
}
RAW_SHA256 = "cb07fc4284cb1bea5b308ef1822f4440e83e16d53703b5d3254a0b5def76f408"


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen_contract():
    contract = dict(final_model="tuned_random_forest", final_model_config=dict(CONFIG),
                    feature_set="FULL_OBSERVATION_FEATURES", features=list(FEATURES),
                    class_order=list(CLASSES), estimator_class_order=sorted(CLASSES))
    return dict(**contract, final_model_config_hash=digest(dict(CONFIG)),
                contract_hash=digest(contract))


def assert_frozen(model=None, features=FEATURES):
    if final_holdout.MODEL_CONFIG != dict(CONFIG):
        raise ValueError("Frozen model configuration changed")
    if final_holdout.MODEL_NAME != "tuned_random_forest" or tuple(TARGET_COLUMNS) != CLASSES:
        raise ValueError("Frozen model/class identity changed")
    if tuple(features) != FEATURES:
        raise ValueError("Frozen feature order or membership changed")
    validate_feature_matrix(features)
    model = final_holdout.build_final_model() if model is None else model
    expected = RandomForestClassifier(**CONFIG)
    if type(model) is not RandomForestClassifier or model.get_params() != expected.get_params():
        raise ValueError("Frozen estimator changed")
    if hasattr(model, "feature_names_in_") and tuple(model.feature_names_in_) != FEATURES:
        raise ValueError("Fitted feature order changed")
    if hasattr(model, "classes_") and list(model.classes_) != sorted(CLASSES):
        raise ValueError("Estimator class order changed")
    return model


def load_phase8(root):
    """Read saved predictions only; never invoke Phase 8 fitting or inference."""
    output = root / "reports/ml/final_holdout"
    for name, expected in PHASE_8_HASHES.items():
        if file_hash(output / name) != expected:
            raise ValueError(f"BLOCKED: Phase 8 artifact changed: {name}")
    if file_hash(root / "data/raw/steel_plates_faults.csv") != RAW_SHA256:
        raise ValueError("BLOCKED: raw data changed")
    metrics = json.loads((output / "metrics.json").read_text())
    ledger = json.loads((output / "execution.json").read_text())
    if not (ledger["completed"] and ledger["fit_calls"] == ledger["prediction_calls"] == 1
            and not ledger["holdout_invalidated"] and ledger["artifacts_sha256"] == PHASE_8_HASHES):
        raise ValueError("BLOCKED: inconsistent final evaluation ledger")
    if not (metrics["final_model_config"] == dict(CONFIG)
            and metrics["features"] == list(FEATURES) and metrics["class_order"] == list(CLASSES)
            and metrics["holdout_status"] == "CONSUMED_FINAL_EVALUATION"
            and metrics["train_size"] == 1552 and metrics["holdout_size"] == 389
            and not metrics["holdout_invalidated"]):
        raise ValueError("BLOCKED: Phase 8 contract mismatch")
    assert_frozen()
    saved = pd.read_csv(output / "predictions.csv", float_precision="round_trip")
    probs = saved[[f"probability_{c}" for c in CLASSES]].to_numpy()
    values, per_class, matrix, derived = final_holdout.score_predictions(
        saved.actual_class, probs, CLASSES, saved.row_index)
    for key, value in values.items():
        if not np.isclose(value, metrics["metrics"][key], rtol=0, atol=ATOL):
            raise ValueError(f"BLOCKED: saved metric mismatch: {key}")
    if per_class != metrics["per_class_results"]:
        raise ValueError("BLOCKED: per-class metrics mismatch")
    pd.testing.assert_frame_equal(saved, derived, check_exact=True)
    pd.testing.assert_frame_equal(matrix, pd.read_csv(output / "confusion_matrix.csv", index_col=0))
    snapshot = pd.read_csv(output / "probabilities_snapshot.csv", float_precision="round_trip")
    if not np.array_equal(snapshot[list(CLASSES)].to_numpy(), probs):
        raise ValueError("BLOCKED: probability snapshot mismatch")
    train_ids = metrics["split"]["train_positions"]
    holdout_ids = metrics["split"]["holdout_positions"]
    if (saved.row_index.tolist() != holdout_ids or len(set(train_ids)) != 1552
            or len(set(holdout_ids)) != 389 or set(train_ids) & set(holdout_ids)
            or set(train_ids) | set(holdout_ids) != set(range(1941))):
        raise ValueError("BLOCKED: partition identities changed")
    return metrics, saved, matrix


def analysis_protocol():
    return dict(
        **frozen_contract(), phase_8_checkpoint=PHASE_8, phase_8_state_checkpoint=PHASE_8_STATE,
        final_model_frozen=True, post_holdout_tuning=False,
        alternative_model_evaluation=False, feature_selection_after_holdout=False,
        phase_8_artifact_sha256=PHASE_8_HASHES, raw_sha256=RAW_SHA256,
        min_sample=MIN_SAMPLE, confidence_edges=CONFIDENCE_EDGES, margin_edges=MARGIN_EDGES,
        fixed_thresholds=THRESHOLDS, candidate_threshold=CANDIDATE_THRESHOLD,
        low_threshold=LOW_THRESHOLD,
        policy_support_rule="n>=30 in low/middle/high; error(low)>error(middle)>error(high)",
        segment_rule="Training quartiles, unique interior cuts, right-closed; binary steel values",
        class_rule="n<30 INSUFFICIENT_SUPPORT; otherwise F1>=0.85 STRONGER, F1<0.70 WEAKER, else INTERMEDIATE",
        permutation=dict(scoring="f1_macro", repeats=PERMUTATION_REPEATS,
                         random_state=42, n_jobs=1, std_ddof=1,
                         stability_rule="mean<=0 LOW; positive in all 5 and std<=mean STABLE; else VARIABLE"),
        case_rule="Holdout post-hoc: high>=0.80, low<0.50; high descending confidence, low ascending; row_id ascending tie break",
        brier_definition="mean_i sum_k (p_ik - 1[y_i=k])^2; unnormalized, range [0,2]",
        ece_definition="sum_b n_b/N * abs(accuracy_b - mean_top1_b); fixed confidence bins",
        probability_comparison_rule="UNCERTAIN: descriptive comparison only; no independent equivalence test",
        shap_status="NOT_REQUIRED", association_not_causation=True,
        reproducibility_absolute_tolerance=ATOL,
    )
