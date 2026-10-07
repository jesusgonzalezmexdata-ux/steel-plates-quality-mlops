"""Reproducible, model-free audit of the steel plates dataset.

The audit intentionally stops at data understanding. It does not train a
model, fit preprocessing, or select features.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

TARGET_COLUMNS = (
    "Pastry",
    "Z_Scratch",
    "K_Scatch",
    "Stains",
    "Dirtiness",
    "Bumps",
    "Other_Faults",
)


def load_dataset(path: str | Path) -> pd.DataFrame:
    """Load the raw CSV without changing values or column names."""

    return pd.read_csv(path)


def _json_value(value: Any) -> Any:
    """Convert numpy scalars and non-finite values to JSON-safe values."""

    if isinstance(value, (np.integer, np.floating)):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def audit_dataset(df: pd.DataFrame) -> dict[str, Any]:
    """Return deterministic schema, quality, distribution and association checks."""

    missing = df.isna().sum()
    numeric = df.select_dtypes(include=np.number).columns.tolist()
    feature_columns = [column for column in df.columns if column not in TARGET_COLUMNS]
    binary = [
        column
        for column in df.columns
        if set(df[column].dropna().unique()).issubset({0, 1})
    ]

    target_present = [column for column in TARGET_COLUMNS if column in df.columns]
    target_sum = df[target_present].sum(axis=1) if target_present else pd.Series(dtype=float)
    labels = (
        df[target_present].idxmax(axis=1)
        if target_present and len(target_present) == len(TARGET_COLUMNS)
        else pd.Series(dtype=object)
    )

    outliers: dict[str, int] = {}
    for column in feature_columns:
        if column not in numeric:
            continue
        q1, q3 = df[column].quantile([0.25, 0.75])
        iqr = q3 - q1
        if iqr == 0:
            outliers[column] = 0
            continue
        outliers[column] = int(
            ((df[column] < q1 - 1.5 * iqr) | (df[column] > q3 + 1.5 * iqr)).sum()
        )

    feature_correlation = df[feature_columns].select_dtypes(include=np.number).corr()
    correlations = []
    for left_index, left in enumerate(feature_correlation.columns):
        for right in feature_correlation.columns[left_index + 1 :]:
            value = feature_correlation.loc[left, right]
            correlations.append(
                {"feature_a": left, "feature_b": right, "pearson_r": _json_value(value)}
            )
    correlations.sort(key=lambda item: abs(item["pearson_r"] or 0), reverse=True)

    result: dict[str, Any] = {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "column_names": df.columns.tolist(),
        "dtypes": {column: str(dtype) for column, dtype in df.dtypes.items()},
        "missing": {column: int(value) for column, value in missing.items()},
        "missing_total": int(missing.sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "cardinality": {column: int(value) for column, value in df.nunique().items()},
        "binary_columns": binary,
        "numeric_feature_columns": [column for column in feature_columns if column in numeric],
        "target_columns": list(TARGET_COLUMNS),
        "target_present": target_present,
        "target_counts": {
            column: int(df[column].sum()) for column in target_present
        },
        "one_target_per_row": bool((target_sum == 1).all()) if len(target_sum) else False,
        "target_class_count": int(labels.nunique()) if len(labels) else 0,
        "outlier_counts_iqr": outliers,
        "top_feature_correlations": correlations[:20],
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit_dataset(load_dataset(args.csv)), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
