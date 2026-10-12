"""Descriptive holdout errors with segment boundaries learned on training only."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

from quality_ml.evaluation.protocol import CLASSES, FEATURES, MIN_SAMPLE


def confusion_pairs(frame):
    counts = pd.crosstab(frame.actual_class, frame.predicted_class).reindex(
        index=CLASSES, columns=CLASSES, fill_value=0).fillna(0).astype(int)
    rows = [dict(actual_class=actual, predicted_class=predicted,
                 count=int(counts.loc[actual, predicted]),
                 percent_of_actual_class=100 * counts.loc[actual, predicted] / counts.loc[actual].sum())
            for actual in CLASSES for predicted in CLASSES
            if actual != predicted and counts.loc[actual].sum() > 0]
    return pd.DataFrame(rows).sort_values(
        ["count", "actual_class", "predicted_class"], ascending=[False, True, True]).reset_index(drop=True)


def class_summary(frame):
    matrix = confusion_matrix(frame.actual_class, frame.predicted_class, labels=CLASSES)
    precision, recall, f1, support = precision_recall_fscore_support(
        frame.actual_class, frame.predicted_class, labels=CLASSES, zero_division=0)
    rows = []
    for i, label in enumerate(CLASSES):
        n, tp = int(support[i]), int(matrix[i, i])
        status = ("INSUFFICIENT_SUPPORT" if n < MIN_SAMPLE else
                  "STRONGER" if f1[i] >= 0.85 else "WEAKER" if f1[i] < 0.70 else "INTERMEDIATE")
        rows.append(dict(actual_class=label, support=n, true_positive=tp, false_negative=n-tp,
            false_positive=int(matrix[:, i].sum())-tp, precision=precision[i],
            recall=recall[i], f1=f1[i], class_error_rate=(n-tp)/n if n else None, status=status))
    return pd.DataFrame(rows)


def training_segment_spec(training):
    """The labels, predictions and holdout are unavailable to this function."""
    result = {}
    for feature in FEATURES:
        values = training[feature]
        if values.isna().any() or not np.isfinite(values).all():
            raise ValueError("Nonfinite training segment measurements")
        if feature in ("TypeOfSteel_A300", "TypeOfSteel_A400"):
            if not set(values).issubset({0, 1}):
                raise ValueError("Nonbinary steel indicator")
            result[feature] = dict(kind="binary", values=[0, 1])
        else:
            # Repeated quartiles are removed by value, without observing errors.
            cuts = sorted(set(float(x) for x in values.quantile([0.25, 0.50, 0.75])))
            result[feature] = dict(kind="continuous", cuts=cuts, closure="right")
    return result


def _wilson(errors, n):
    if not n:
        return None, None
    z = 1.959963984540054
    proportion = errors / n
    center = (proportion + z*z/(2*n))/(1+z*z/n)
    half = z*np.sqrt(proportion*(1-proportion)/n + z*z/(4*n*n))/(1+z*z/n)
    return (0.0 if errors == 0 else max(0.0, center-half),
            1.0 if errors == n else min(1.0, center+half))


def segment_errors(holdout_features, frame, specification):
    if len(holdout_features) != len(frame) or not holdout_features.index.equals(frame.index):
        raise ValueError("Holdout features/predictions must be row-aligned")
    rows = []
    for feature, spec in specification.items():
        values = holdout_features[feature].to_numpy()
        if not np.isfinite(values).all():
            raise ValueError("Nonfinite holdout segment measurements")
        if spec["kind"] == "binary":
            if not set(values).issubset(set(spec["values"])):
                raise ValueError("Unseen steel indicator")
            masks = [(str(value), values == value) for value in spec["values"]]
        else:
            cuts = [-np.inf, *spec["cuts"], np.inf]
            masks = [(f"({lower:.8g}, {upper:.8g}]", (values > lower) & (values <= upper))
                     for lower, upper in zip(cuts[:-1], cuts[1:])]
        if not np.all(np.sum([mask.astype(int) for _, mask in masks], axis=0) == 1):
            raise ValueError("Segments must partition each feature")
        for segment, mask in masks:
            for actual in ("ALL", *CLASSES):
                selected = mask if actual == "ALL" else mask & (frame.actual_class.to_numpy() == actual)
                part = frame.loc[selected]
                n = len(part)
                correct = int(part.correct_prediction.sum())
                low, high = _wilson(n-correct, n)
                rows.append(dict(feature=feature, segment=segment, actual_class=actual,
                    n=n, correct=correct, errors=n-correct, error_rate=(n-correct)/n if n else None,
                    error_rate_wilson_low=low, error_rate_wilson_high=high,
                    status="INSUFFICIENT_DATA" if n < MIN_SAMPLE else "SUFFICIENT_DESCRIPTIVE"))
    return pd.DataFrame(rows)


def high_confidence_errors(frame, features, threshold, source):
    selected = frame.loc[(frame.max_probability >= threshold) & ~frame.correct_prediction].copy()
    selected.insert(0, "evidence_source", source)
    # Join through explicit original row position, never implicit frame order.
    return selected.merge(features, left_on="row_id", right_index=True,
                          how="left", validate="one_to_one").sort_values(
                              ["max_probability", "row_id"], ascending=[False, True])
