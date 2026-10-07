"""Reproducible feature-status policy for the steel plates dataset.

This module classifies columns from their documented meaning and availability
evidence. It deliberately does not use correlation, model performance, or
feature selection to decide leakage.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import pandas as pd

from quality_ml.data.audit import TARGET_COLUMNS, load_dataset

STATUS_EXCLUDE = "EXCLUDE"
STATUS_SAFE = "SAFE"
STATUS_QUESTIONABLE = "QUESTIONABLE"

TECHNICAL_ID_COLUMNS = ("id",)

SAFE_FEATURES: tuple[str, ...] = ()

QUESTIONABLE_FEATURES = (
    "TypeOfSteel_A300",
    "TypeOfSteel_A400",
    "Steel_Plate_Thickness",
    "X_Minimum",
    "X_Maximum",
    "Y_Minimum",
    "Y_Maximum",
    "Pixels_Areas",
    "X_Perimeter",
    "Y_Perimeter",
    "Sum_of_Luminosity",
    "Minimum_of_Luminosity",
    "Maximum_of_Luminosity",
    "Length_of_Conveyer",
    "Edges_Index",
    "Empty_Index",
    "Square_Index",
    "Outside_X_Index",
    "Edges_X_Index",
    "Edges_Y_Index",
    "Outside_Global_Index",
    "LogOfAreas",
    "Log_X_Index",
    "Log_Y_Index",
    "Orientation_Index",
    "Luminosity_Index",
    "SigmoidOfAreas",
)


def _ordered_intersection(columns: Iterable[str], candidates: Iterable[str]) -> list[str]:
    candidate_set = set(candidates)
    return [column for column in columns if column in candidate_set]


def build_feature_sets(
    columns: Iterable[str],
    technical_id_columns: Iterable[str] = TECHNICAL_ID_COLUMNS,
) -> dict[str, list[str] | dict[str, str]]:
    """Classify a dataset schema and validate all feature-set invariants."""

    ordered_columns = list(columns)
    targets = _ordered_intersection(ordered_columns, TARGET_COLUMNS)
    technical_ids = _ordered_intersection(ordered_columns, technical_id_columns)
    safe = _ordered_intersection(ordered_columns, SAFE_FEATURES)
    questionable = _ordered_intersection(ordered_columns, QUESTIONABLE_FEATURES)

    if set(targets) != set(TARGET_COLUMNS):
        missing_targets = sorted(set(TARGET_COLUMNS) - set(targets))
        raise ValueError(f"Missing target columns: {missing_targets}")

    known = set(targets) | set(technical_ids) | set(safe) | set(questionable)
    unknown = [column for column in ordered_columns if column not in known]
    if unknown:
        raise ValueError(f"Unclassified columns require explicit review: {unknown}")

    excluded = technical_ids + targets
    full_observation = safe + questionable
    restricted_information = safe
    status_by_feature = {
        column: STATUS_EXCLUDE for column in excluded
    }
    status_by_feature.update({column: STATUS_SAFE for column in safe})
    status_by_feature.update({column: STATUS_QUESTIONABLE for column in questionable})

    if set(full_observation) & set(excluded):
        raise AssertionError("Excluded columns entered FULL_OBSERVATION_FEATURES")
    if set(restricted_information) & (set(excluded) | set(questionable)):
        raise AssertionError("Restricted features contain excluded/questionable columns")
    if set(full_observation) | set(excluded) != set(ordered_columns):
        raise AssertionError("Feature sets do not cover the dataset schema")
    # The restricted set is intentionally a subset of the full set. Any
    # overlap here is allowed because both are predictor sets; overlap with
    # targets or technical identifiers above is prohibited.
    if set(restricted_information) & set(full_observation):
        assert set(restricted_information).issubset(set(full_observation))
    if set(TARGET_COLUMNS) & set(full_observation + restricted_information):
        raise AssertionError("Target column entered a predictor set")
    if set(technical_id_columns) & set(full_observation + restricted_information):
        raise AssertionError("Technical identifier entered a predictor set")

    return {
        "status_by_feature": status_by_feature,
        "excluded_features": excluded,
        "safe_features": safe,
        "questionable_features": questionable,
        "full_observation_features": full_observation,
        "restricted_information_features": restricted_information,
    }


def audit_csv(path: str | Path) -> dict[str, list[str] | dict[str, str]]:
    """Build and validate feature lists from a CSV schema without fitting a model."""

    return build_feature_sets(load_dataset(path).columns)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit_csv(args.csv), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
