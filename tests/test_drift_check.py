"""Input-drift monitoring: same population passes, unit change and recalibration are caught."""
import json
import shutil
from pathlib import Path

from tools import drift_check

ROOT = Path(__file__).resolve().parents[1]


def test_psi_basics():
    assert drift_check.psi([0.5, 0.5], [0.5, 0.5]) == 0
    assert drift_check.psi([0.5, 0.5], [0.9, 0.1]) > drift_check.PSI_MAJOR


def test_report_is_reproducible_and_separates_batches(tmp_path):
    for name in ("data/raw/steel_plates_faults.csv", "reports/ml/final_holdout/metrics.json"):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, tmp_path / name)
    result = drift_check.run(tmp_path)
    committed = json.loads((ROOT / drift_check.OUTPUT).read_text(encoding="utf-8"))
    assert committed == json.loads(json.dumps(result))
    b = result["batches"]
    assert b["Holdout plates (same population)"]["status"] == "OK"
    assert "Steel_Plate_Thickness" in b["Unit change: thickness reported in cm instead of mm"]["psi_major"]
    assert b["Camera recalibration: luminosity +15 %"]["status"] == "ALERT"
