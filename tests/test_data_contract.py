"""SQL data contract: passes on the raw CSV, reconciles with pandas, fails closed on corruption."""
import os
from pathlib import Path
import shutil
import subprocess

import pandas as pd
import pytest

pytest.importorskip("dbt.cli.main", reason="requires requirements-dbt.txt")
from tools import data_contract  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def run_dbt(csv, tmp_path):
    env = dict(os.environ, STEEL_RAW_CSV=Path(csv).as_posix(),
               STEEL_DUCKDB_PATH=(tmp_path / "contract.duckdb").as_posix())
    dbt = shutil.which("dbt")
    return subprocess.run([dbt, "build", "--project-dir", str(ROOT / "dbt"),
                           "--profiles-dir", str(ROOT / "dbt"),
                           "--target-path", str(tmp_path / "target"),
                           "--log-path", str(tmp_path / "logs")],
                          env=env, capture_output=True, text=True)


def test_contract_passes_and_reconciles(tmp_path):
    database = tmp_path / "contract.duckdb"
    data_contract.build(database)
    result = data_contract.reconcile(database)
    assert result["status"] == "PASS" and result["rows"] == 1941
    assert sum(result["class_counts"].values()) == 1941


MUTATIONS = {
    "two_classes": (lambda d: d.assign(Bumps=d.Bumps.where(d.index != 0, 1)), "target_sum"),
    "duplicate_id": (lambda d: d.assign(id=d.id.where(d.index != 1, 0)), "unique_plate_defects_id"),
    "steel_one_hot": (lambda d: d.assign(TypeOfSteel_A400=d.TypeOfSteel_A400.where(
        d.index != 2, d.TypeOfSteel_A300)), "assert_steel_type_one_hot"),
    "geometry": (lambda d: d.assign(X_Maximum=d.X_Maximum.where(d.index != 3, -1)),
                 "assert_geometry_consistency"),
    "dropped_row": (lambda d: d.iloc[1:], "assert_row_count"),
}


@pytest.mark.parametrize("name", MUTATIONS)
def test_contract_rejects_corruption(name, tmp_path):
    mutate, expected_failure = MUTATIONS[name]
    csv = tmp_path / "mutated.csv"
    mutate(pd.read_csv(ROOT / "data/raw/steel_plates_faults.csv")).to_csv(csv, index=False)
    run = run_dbt(csv, tmp_path)
    assert run.returncode != 0
    failed = [line for line in run.stdout.splitlines() if " FAIL " in line]
    assert any(expected_failure in line for line in failed), failed
