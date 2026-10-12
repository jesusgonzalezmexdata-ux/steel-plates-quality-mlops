"""Training-only OOF, confidence and diagnostic calibration calculations."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold

from quality_ml.models.evaluate import _metrics
from quality_ml.models.final_holdout import validate_probabilities
from quality_ml.evaluation.protocol import (
    ATOL, CANDIDATE_THRESHOLD, CLASSES, CONFIDENCE_EDGES, FEATURES, LOW_THRESHOLD,
    MIN_SAMPLE, THRESHOLDS, assert_frozen,
)


def prediction_frame(row_ids, actual, probabilities, estimator_classes):
    validate_probabilities(probabilities, estimator_classes, n_rows=len(actual))
    actual = np.asarray(actual)
    row_ids = np.asarray(row_ids)
    if len(set(row_ids)) != len(actual) or len(row_ids) != len(actual):
        raise ValueError("Duplicate or missing row identifiers")
    predicted = np.asarray(estimator_classes)[probabilities.argmax(axis=1)]
    ordered = np.sort(probabilities, axis=1)
    result = pd.DataFrame(dict(row_id=row_ids, actual_class=actual, predicted_class=predicted,
        correct_prediction=actual == predicted, max_probability=ordered[:, -1],
        second_probability=ordered[:, -2], probability_margin=ordered[:, -1] - ordered[:, -2]))
    for label in CLASSES:
        result[f"probability_{label}"] = probabilities[:, list(estimator_classes).index(label)]
    return result


def frame_metrics(frame):
    probabilities = frame[[f"probability_{c}" for c in sorted(CLASSES)]].to_numpy()
    validate_probabilities(probabilities, sorted(CLASSES), n_rows=len(frame))
    return _metrics(frame.actual_class, frame.predicted_class.to_numpy(),
                    probabilities, sorted(CLASSES))


def frozen_folds(X, y):
    return tuple((train, valid) for train, valid in
                 StratifiedKFold(n_splits=5, shuffle=True, random_state=42).split(X, y))


def validate_folds(folds, n_rows):
    if len(folds) != 5:
        raise ValueError("Exactly five frozen folds required")
    seen = np.zeros(n_rows, dtype=int)
    for train, valid in folds:
        if (len(set(train)) != len(train) or len(set(valid)) != len(valid)
                or set(train) & set(valid) or set(train) | set(valid) != set(range(n_rows))):
            raise ValueError("Fold leakage, duplicates or missing rows")
        seen[valid] += 1
    if not np.all(seen == 1):
        raise ValueError("Every row must be validated exactly once")


def reconstruct_oof(X, y, row_ids, fold_callback=None):
    """Each newly built frozen RF fits only that fold's training rows."""
    assert_frozen(features=X.columns)
    if len(X) != 1552 or len(y) != 1552 or len(set(row_ids)) != 1552:
        raise ValueError("Expected the 1552 unique frozen training rows")
    folds = frozen_folds(X, y)
    validate_folds(folds, len(X))
    frames, audit, fold_metrics = [], [], []
    for fold, (train, valid) in enumerate(folds, 1):
        model = assert_frozen()
        model.fit(X.iloc[train], y.iloc[train])
        assert_frozen(model)
        predicted = prediction_frame(np.asarray(row_ids)[valid], y.iloc[valid],
                                    model.predict_proba(X.iloc[valid]), model.classes_)
        predicted.insert(1, "fold", fold)
        frames.append(predicted)
        fold_metrics.append(frame_metrics(predicted))
        audit.append(dict(fold=fold, train_row_ids=np.asarray(row_ids)[train].tolist(),
                          validation_row_ids=np.asarray(row_ids)[valid].tolist(),
                          train_validation_overlap=0))
        if fold_callback is not None:
            fold_callback(model, X.iloc[valid], y.iloc[valid], fold)
        assert_frozen(model)
    result = pd.concat(frames).sort_values("row_id").reset_index(drop=True)
    if (len(result) != 1552 or result.row_id.duplicated().any()
            or set(result.row_id) != set(row_ids)):
        raise ValueError("Invalid OOF coverage")
    return result, audit, fold_metrics


def confidence_bins(frame, edges=CONFIDENCE_EDGES, column="max_probability"):
    """Half-open bins, with exactly 1 included in the last bin."""
    values = frame[column].to_numpy()
    if not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
        raise ValueError("Invalid confidence values")
    edges = np.asarray(edges)
    if edges[0] != 0 or edges[-1] != 1 or not (np.diff(edges) > 0).all():
        raise ValueError("Invalid bin edges")
    membership = np.minimum(np.searchsorted(edges, values, side="right") - 1, len(edges) - 2)
    rows = []
    for index, (lower, upper) in enumerate(zip(edges[:-1], edges[1:])):
        part = frame.loc[membership == index]
        n = len(part)
        accuracy = float(part.correct_prediction.mean()) if n else None
        rows.append(dict(bin=f"[{lower:.2f}, {upper:.2f}{']' if index == len(edges)-2 else ')'}",
            lower=float(lower), upper=float(upper), n=n, coverage=n / len(frame),
            accuracy=accuracy, error_rate=1 - accuracy if n else None,
            mean_confidence=float(part[column].mean()) if n else None,
            status="SUFFICIENT_DESCRIPTIVE" if n >= MIN_SAMPLE else "INSUFFICIENT_DATA"))
    return pd.DataFrame(rows)


def calibration_metrics(frame, label):
    probabilities = frame[[f"probability_{c}" for c in CLASSES]].to_numpy()
    validate_probabilities(probabilities, CLASSES, n_rows=len(frame))
    one_hot = frame.actual_class.to_numpy()[:, None] == np.asarray(CLASSES)[None, :]
    bins = confidence_bins(frame)
    nonempty = bins.loc[bins.n > 0]
    return dict(evidence=label, n=len(frame),
        multiclass_log_loss=frame_metrics(frame)["log_loss"],
        multiclass_brier_score=float(np.mean(np.sum((probabilities - one_hot) ** 2, axis=1))),
        top_label_ece=float(np.sum(nonempty.coverage *
            abs(nonempty.accuracy - nonempty.mean_confidence))),
        mean_confidence=float(frame.max_probability.mean()),
        observed_accuracy=float(frame.correct_prediction.mean()),
        calibration_model_fitted=False)


def threshold_tradeoff(oof):
    rows = []
    for threshold in THRESHOLDS:
        accepted = oof.max_probability >= threshold
        errors = int((accepted & ~oof.correct_prediction).sum())
        n = int(accepted.sum())
        rows.append(dict(threshold=threshold, accepted_rows=n, review_rows=len(oof) - n,
            coverage=n / len(oof), review_rate=1 - n / len(oof),
            accepted_accuracy=float(oof.loc[accepted, "correct_prediction"].mean()) if n else None,
            accepted_error_rate=errors / n if n else None, high_confidence_errors=errors))
    return pd.DataFrame(rows)


def candidate_policy(oof):
    """No holdout argument or threshold optimization: confirm the fixed proposal."""
    groups = [oof.max_probability < LOW_THRESHOLD,
              (oof.max_probability >= LOW_THRESHOLD) & (oof.max_probability < CANDIDATE_THRESHOLD),
              oof.max_probability >= CANDIDATE_THRESHOLD]
    sizes = [int(mask.sum()) for mask in groups]
    errors = [float((~oof.loc[mask, "correct_prediction"]).mean()) if mask.any() else None
              for mask in groups]
    supported = min(sizes) >= MIN_SAMPLE and errors[0] > errors[1] > errors[2]
    return dict(status="DEVELOPMENT_ONLY" if supported else "NOT_SUPPORTED",
                high_threshold=CANDIDATE_THRESHOLD, low_threshold=LOW_THRESHOLD,
                group_order=["LOW_CONFIDENCE", "REVIEW_REQUIRED", "HIGH_CONFIDENCE"],
                group_n=sizes, group_error_rate=errors, evidence="DEVELOPMENT_OOF_ONLY")


def policy_labels(frame, policy):
    if policy["status"] != "DEVELOPMENT_ONLY":
        return np.full(len(frame), "NOT_SUPPORTED", dtype=object)
    return np.where(frame.max_probability >= policy["high_threshold"], "HIGH_CONFIDENCE",
                    np.where(frame.max_probability < policy["low_threshold"],
                             "LOW_CONFIDENCE", "REVIEW_REQUIRED"))


def apply_policy(frame, policy):
    labels = policy_labels(frame, policy)
    accepted = labels == "HIGH_CONFIDENCE"
    errors = ~frame.correct_prediction.to_numpy()
    return dict(evidence="POST_HOC_ONLY", policy_status=policy["status"],
        accepted_rows=int(accepted.sum()), review_rows=int((~accepted).sum()),
        coverage=float(accepted.mean()), review_rate=float((~accepted).mean()),
        accepted_error_rate=float(errors[accepted].mean()) if accepted.any() else None,
        errors_sent_to_review=int((errors & ~accepted).sum()),
        errors_not_captured=int((errors & accepted).sum()))
