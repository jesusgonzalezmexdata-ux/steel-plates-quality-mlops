"""Associative importance for the frozen RF; never feature selection."""

from __future__ import annotations

import hashlib
import pickle

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance

from quality_ml.evaluation.protocol import (
    CANDIDATE_THRESHOLD, FEATURES, LOW_THRESHOLD, PERMUTATION_REPEATS, assert_frozen,
)
from quality_ml.evaluation.uncertainty import policy_labels


def estimator_fingerprint(model):
    return hashlib.sha256(pickle.dumps(model, protocol=5)).hexdigest()


def native_importance(model):
    assert_frozen(model)
    before = estimator_fingerprint(model)
    result = pd.DataFrame(dict(feature=FEATURES, importance=model.feature_importances_))
    if before != estimator_fingerprint(model):
        raise ValueError("Native importance mutated estimator")
    return result.sort_values(["importance", "feature"], ascending=[False, True]).reset_index(drop=True)


def fold_permutation(model, X_valid, y_valid, fold):
    """Drop in validation macro-F1 over five fixed permutations per predictor."""
    assert_frozen(model, X_valid.columns)
    before = estimator_fingerprint(model)
    result = permutation_importance(model, X_valid, y_valid, scoring="f1_macro",
                                    n_repeats=PERMUTATION_REPEATS, random_state=42, n_jobs=1)
    if before != estimator_fingerprint(model):
        raise ValueError("Permutation importance mutated estimator")
    return pd.DataFrame([dict(fold=fold, feature=feature, repeat=repeat+1,
                              importance=float(result.importances[i, repeat]))
                         for i, feature in enumerate(FEATURES)
                         for repeat in range(PERMUTATION_REPEATS)])


def aggregate_importance(repeats):
    expected = pd.MultiIndex.from_product(
        [range(1, 6), FEATURES, range(1, PERMUTATION_REPEATS+1)],
        names=["fold", "feature", "repeat"])
    actual = pd.MultiIndex.from_frame(repeats[["fold", "feature", "repeat"]])
    if len(actual) != len(expected) or actual.duplicated().any() or set(actual) != set(expected):
        raise ValueError("Permutation repetitions missing or duplicated")
    means = repeats.groupby(["feature", "fold"]).importance.mean()
    rows = []
    for feature in FEATURES:
        values = means.loc[feature].to_numpy()
        mean, std = float(values.mean()), float(values.std(ddof=1))
        positive = int((values > 0).sum())
        status = ("LOW_IMPORTANCE" if mean <= 0 else
                  "STABLE_IMPORTANCE" if positive == 5 and std <= mean else "VARIABLE_IMPORTANCE")
        rows.append(dict(feature=feature, importance_mean=mean, importance_std=std,
                         importance_min=float(values.min()), importance_max=float(values.max()),
                         positive_fold_count=positive, status=status))
    return pd.DataFrame(rows).sort_values(
        ["importance_mean", "feature"], ascending=[False, True]).reset_index(drop=True)


def case_examples(frame, features, policy, importance):
    """Deterministic extremes; top global features are context, not local attribution."""
    context_features = importance.head(5).feature.tolist()
    rows = []
    for name, correct, high in (
        ("HIGH_CONFIDENCE_CORRECT", True, True), ("LOW_CONFIDENCE_CORRECT", True, False),
        ("HIGH_CONFIDENCE_ERROR", False, True), ("LOW_CONFIDENCE_ERROR", False, False),
    ):
        mask = (frame.max_probability >= CANDIDATE_THRESHOLD if high
                else frame.max_probability < LOW_THRESHOLD)
        candidates = frame.loc[mask & (frame.correct_prediction == correct)].sort_values(
            ["max_probability", "row_id"], ascending=[not high, True])
        if candidates.empty:
            rows.append(dict(case_type=name, status="NO_MATCHING_CASE"))
            continue
        row = candidates.iloc[0]
        row_id = int(row.row_id)
        rows.append(dict(case_type=name, evidence="FINAL_HOLDOUT_POST_HOC",
            row_id=row_id, actual=row.actual_class, predicted=row.predicted_class,
            confidence=float(row.max_probability), margin=float(row.probability_margin),
            review_policy_status=str(policy_labels(candidates.iloc[:1], policy)[0]),
            globally_associated_feature_values={
                f: float(features.loc[row_id, f]) for f in context_features},
            attribution_scope="Global ranking context only; no local or causal explanation"))
    return rows
