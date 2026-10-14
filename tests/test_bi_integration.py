"""Saved-holdout export and additive textual Power BI validation, not Desktop tests."""
import hashlib
import json
from pathlib import Path
import re
import shutil

import pandas as pd
import pytest

from quality_ml.inference.bi_export import (
    BASELINE_PATH, COLUMNS, EXPORT_PATH, export_frame, validate_export,
)
from tools.prepare_ml_powerbi import PAGE, REPORT, SEMANTIC, prepare

ROOT = Path(__file__).resolve().parents[1]


def test_export_reconciles_frozen_predictions_and_role():
    result = validate_export(ROOT)
    assert (result["rows"], result["correct"], result["errors"], result["review_rows"]) == (389, 307, 82, 261)
    frame, metrics = export_frame(ROOT)
    assert tuple(frame.columns) == COLUMNS
    assert frame.row_id.tolist() == metrics["split"]["holdout_positions"]
    assert set(frame.row_id).isdisjoint(metrics["split"]["train_positions"])
    assert frame.dataset_role.eq("FINAL_HOLDOUT_EVALUATION").all()
    assert frame.policy_application.eq("POST_HOC_ONLY").all()
    assert frame.loc[frame.review_status.eq("HIGH_CONFIDENCE"), "confidence"].ge(.8).all()
    assert frame.loc[frame.review_status.eq("LOW_CONFIDENCE"), "confidence"].lt(.5).all()
    assert frame.loc[frame.row_id.eq(1277), "correct_prediction"].item() == 0
    assert frame.loc[frame.row_id.eq(1277), "review_required"].item() == 0


RUTA_CSV_BASELINE = (b'expression RutaCSV = "C:\\\\Users\\\\Lowo\\\\Downloads\\\\'
                     b'steel-plates-quality-bi-main\\\\data\\\\raw\\\\steel_plates_faults.csv"')
RUTA_CSV_PLACEHOLDER = (b'expression RutaCSV = "C:\\\\path\\\\to\\\\steel-plates-quality-mlops-'
                        b'\\\\data\\\\raw\\\\steel_plates_faults.csv"')


def test_previous_powerbi_preserved():
    baseline = json.loads((ROOT / BASELINE_PATH).read_text())
    exceptions = {f"{REPORT}/pages.json", f"{SEMANTIC}/model.tmdl",
                  f"{SEMANTIC}/expressions.tmdl"}
    for name, identity in baseline["files"].items():
        data = (ROOT / name).read_bytes()
        if name.endswith(".pbix"):
            # A checkout without LFS materialization cannot verify PBIX bytes.
            if data.startswith(b"version https://git-lfs.github.com/spec/v1"):
                assert b"oid sha256:" + identity["sha256"].encode() in data
            else:
                assert hashlib.sha256(data).hexdigest() == identity["sha256"]
        elif name not in exceptions:
            assert hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest() == identity["lf_sha256"]
        elif name.endswith("model.tmdl"):
            original = data.replace(b"\r\n", b"\n").split(b"\nref table ML_Holdout\n")[0]
            assert hashlib.sha256(original.replace(b"\r\n", b"\n")).hexdigest() == identity["lf_sha256"]
        elif name.endswith("expressions.tmdl"):
            original = data.replace(b"\r\n", b"\n").split(b"\nexpression RutaMLCSV =")[0]
            # Only documented change: the RutaCSV default no longer carries the
            # original author's local path (portability and privacy). Every other
            # byte of the pre-ML definition must still match the baseline.
            assert original.count(RUTA_CSV_PLACEHOLDER) == 1
            original = original.replace(RUTA_CSV_PLACEHOLDER, RUTA_CSV_BASELINE)
            assert hashlib.sha256(original.replace(b"\r\n", b"\n")).hexdigest() == identity["lf_sha256"]
    index = json.loads((ROOT / REPORT / "pages.json").read_text())
    assert index["pageOrder"] == ["5ee9939d0101076d3381", "f50491653678cb19a699",
        "1f75dde540a696f2b18f", "cb973d91eb46886907c2", PAGE]
    assert index["activePageName"] == "5ee9939d0101076d3381"


def test_draft_structure_and_field_bindings():
    table = (ROOT / SEMANTIC / "tables/ML_Holdout.tmdl").read_text()
    columns = set(re.findall(r"^\tcolumn (\w+)$", table, re.M))
    measures = set(re.findall(r"^\tmeasure '([^']+)' =", table, re.M))
    assert columns == set(COLUMNS)
    assert "0.8146728101764369" in table and "0.8048726799979933" in table
    assert 'Table.RowCount(Tipos) = 389' in table
    assert "mode: import" in table and "File.Contents(RutaMLCSV)" in table
    base = ROOT / REPORT / PAGE
    page = json.loads((base / "page.json").read_text())
    visuals = list((base / "visuals").glob("*/visual.json"))
    assert len(visuals) == 12
    positions = []
    types = []
    for path in visuals:
        item = json.loads(path.read_text())
        assert item["name"] == path.parent.name
        p = item["position"]
        assert 0 <= p["x"] <= page["width"] - p["width"]
        assert 0 <= p["y"] <= page["height"] - p["height"]
        for other in positions:
            assert (p["x"] + p["width"] <= other["x"] or other["x"] + other["width"] <= p["x"]
                or p["y"] + p["height"] <= other["y"] or other["y"] + other["height"] <= p["y"])
        positions.append(p)
        view = item["visual"]
        types.append(view["visualType"])
        for role in view.get("query", {}).get("queryState", {}).values():
            for projection in role["projections"]:
                kind, field = next(iter(projection["field"].items()))
                assert field["Expression"]["SourceRef"]["Entity"] == "ML_Holdout"
                assert field["Property"] in (measures if kind == "Measure" else columns)
    assert types.count("listSlicer") == 3 and types.count("tableEx") == 4
    assert types.count("cardVisual") == 4 and types.count("textbox") == 1


def test_text_generation_idempotent(tmp_path):
    shutil.copytree(ROOT / "powerbi/project", tmp_path / "powerbi/project",
                    ignore=shutil.ignore_patterns(".pbi"))
    for name in (BASELINE_PATH, "reports/ml/final_holdout/metrics.json"):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    names = [p.relative_to(ROOT) for p in (ROOT / REPORT / PAGE).rglob("*.json")]
    names += [Path(SEMANTIC, "tables/ML_Holdout.tmdl"), Path(SEMANTIC, "model.tmdl"),
              Path(SEMANTIC, "expressions.tmdl"), Path(REPORT, "pages.json")]
    before = {str(p): (tmp_path / p).read_bytes() for p in names}
    prepare(tmp_path)
    prepare(tmp_path)
    assert before == {str(p): (tmp_path / p).read_bytes() for p in names}


def test_new_sources_and_artifacts_have_no_host_dependency():
    paths = [* (ROOT / "src/quality_ml/inference").glob("*.py"),
        ROOT / "artifacts/manifest.json", ROOT / EXPORT_PATH,
        ROOT / SEMANTIC / "tables/ML_Holdout.tmdl"]
    for path in paths:
        contents = path.read_text().lower()
        assert "c:\\users\\" not in contents
        assert "c:/users/" not in contents
        assert "downloads\\" not in contents