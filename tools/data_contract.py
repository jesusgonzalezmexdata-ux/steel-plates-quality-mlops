"""SQL data contract (dbt + DuckDB) reconciled against the Python dataset audit.

Usage from the repository root: python -B -m tools.data_contract
Requires requirements-dbt.txt. Reads only the raw CSV; never touches the model.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
RAW = ROOT / "data/raw/steel_plates_faults.csv"
PROJECT = ROOT / "dbt"


def build(database: Path) -> None:
    from dbt.cli.main import dbtRunner

    os.environ["STEEL_RAW_CSV"] = RAW.as_posix()
    os.environ["STEEL_DUCKDB_PATH"] = database.as_posix()
    result = dbtRunner().invoke(["build", "--project-dir", str(PROJECT),
                                 "--profiles-dir", str(PROJECT),
                                 "--target-path", str(database.parent / "target"),
                                 "--log-path", str(database.parent / "logs")])
    if not result.success:
        raise SystemExit("dbt build failed: data contract violated")


def reconcile(database: Path) -> dict:
    import duckdb
    import numpy as np
    from quality_ml.data.audit import TARGET_COLUMNS, audit_dataset, load_dataset

    raw = load_dataset(RAW)
    audit = audit_dataset(raw)
    with duckdb.connect(str(database)) as con:
        table = con.execute("select * from plate_defects order by id").df()
    if len(table) != audit["rows"] or table.id.tolist() != raw.id.tolist():
        raise ValueError("Row identity differs between dbt and Python")
    counts = table.defect_class.value_counts().to_dict()
    if counts != audit["target_counts"]:
        raise ValueError(f"Class counts differ: {counts} vs {audit['target_counts']}")
    if not np.array_equal(table[list(raw.columns)].to_numpy(), raw.to_numpy()):
        raise ValueError("Values differ between dbt and Python")
    if not audit["one_target_per_row"] or not table.target_sum.eq(1).all():
        raise ValueError("One-hot target exclusivity violated")
    return dict(status="PASS", rows=len(table), columns=len(raw.columns),
                class_counts={c: counts[c] for c in TARGET_COLUMNS},
                reconciliation="dbt/DuckDB table identical to the pandas raw load")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        database = Path(tmp) / "contract.duckdb"
        build(database)
        print(json.dumps(reconcile(database), indent=2))


if __name__ == "__main__":
    main()
