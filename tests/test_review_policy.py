"""MVP «Triaje de revisión humana»: entrada, política, estimación honesta contra la verdad oculta y reporte."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from quality_ml import review_intake as ri, review_policy as rp, review_report as rr

FAST = rp.Costos(remuestreos=200)


@pytest.fixture(scope="module")
def case():
    raw = ri.example()
    df, issues = ri.validate(raw)
    truth = (raw["clase_real_oculta"] != raw["clase_predicha"]).to_numpy()
    return raw, df, issues, truth


def test_example_is_built_from_out_of_sample_predictions(case):
    raw, df, _, _ = case
    assert len(raw) == 1941 and set(raw["origen"]) == {"validación cruzada", "evaluación final"}
    assert (raw["origen"] == "evaluación final").sum() == 389
    assert 0.28 < df["revisada"].mean() < 0.32 and df["error"].sum() > 100


def test_template_round_trip():
    pytest.importorskip("openpyxl")
    df, _ = ri.validate(ri.read_table(ri.template_bytes(), "plantilla.xlsx"))
    assert len(df) == 1941 and df["revisada"].sum() == 582


def test_errors_percent_confidence_and_aliases():
    df, issues = ri.validate(ri.read_table(ri.to_csv_bytes(ri.example_with_errors()), "x.csv"))
    errors = [i for i in issues if i.nivel == "error"]
    assert {i.fila for i in errors} == {5, 10} and any("0 a 100" in i.mensaje for i in issues)
    assert df["confianza"].between(0, 1).all() and len(df) == 1939
    alias = pd.DataFrame({"Prediccion": ["A", "B"] * 100, "Score": [0.9, 0.4] * 100, "Clase verdadera": ["A", "A"] * 100})
    d, _ = ri.validate(alias)
    assert d["error"].sum() == 100


def test_needs_a_reviewed_sample():
    df = ri.example().drop(columns=["clase_real_oculta", "origen"])
    df["clase_real"] = ""
    with pytest.raises(ri.DataError, match="revisadas"):
        ri.validate(df)


def test_weights_restore_the_population_when_doubtful_items_were_over_reviewed(case):
    raw, _, _, truth = case
    biased = raw.copy()
    conf = biased["confianza"].astype(float)
    rng = np.random.default_rng(1)
    keep = np.where(conf < 0.6, rng.random(len(raw)) < 0.6, rng.random(len(raw)) < 0.1)  # se revisó mucho más lo dudoso
    biased["clase_real"] = np.where(keep, biased["clase_real_oculta"], "")
    df, _ = ri.validate(biased)
    w, _ = rp.weights(df)
    naive = df.loc[df["revisada"], "error"].mean()
    weighted = (w * df["error"]).sum() / w.sum()
    assert abs(weighted - truth.mean()) < abs(naive - truth.mean()) and abs(weighted - truth.mean()) < 0.03


def test_policy_reviews_less_than_everything_and_estimates_escapes_honestly(case):
    _, df, _, truth = case
    for escape in (400.0, 1500.0, 5000.0):
        r = rp.analyse(df, rp.Costos(escape=escape, remuestreos=200))
        p = r["politica"]
        real = int((truth & r["aceptada"]).sum())
        assert p["escapes_ic"][0] - 1 <= real <= p["escapes_ic"][1] + 1, (escape, real, p["escapes_ic"])
        assert p["revisiones"] < len(df)


def test_more_expensive_escapes_never_lower_reviews(case):
    _, df, _, _ = case
    reviews = [rp.analyse(df, rp.Costos(escape=e, remuestreos=50))["politica"]["revisiones"] for e in (200, 800, 3000)]
    assert reviews == sorted(reviews)


def test_easy_classes_are_accepted_more(case):
    _, df, _, _ = case
    t = rp.analyse(df, FAST)["tabla"].set_index("clase")
    assert t.loc["K_Scatch", "pct_revision"] < t.loc["Bumps", "pct_revision"]  # K_Scatch casi no falla; Bumps se confunde con Other_Faults


def test_zero_observed_errors_still_give_a_positive_upper_bound(case):
    _, df, _, _ = case
    p = rp.analyse(df, rp.Costos(escape=1500.0, remuestreos=50))["politica"]
    assert p["escapes_ic"][1] > 0 and p["tasa_escape_ic"][1] > p["tasa_escape"]


def test_audit_sample_size_and_alarm():
    a = rp.audit_sample(0.005, 0.02)
    assert a["n"] == int(np.ceil(np.log(0.05) / np.log(0.98))) and a["alarma"] >= 1


def test_review_list_and_bi_export(case):
    _, df, _, _ = case
    r = rp.analyse(df, FAST)
    lst = rp.review_list(df, r)
    assert len(lst) == int((~r["aceptada"] & ~df["revisada"].to_numpy()).sum()) and lst["confianza"].is_monotonic_increasing
    bi = rp.bi_export(r)
    assert {"clase", "umbral", "pct_revision", "clausula_iso9001"} <= set(bi.columns) and len(bi) == df["clase_predicha"].nunique()


def test_report_is_self_contained(case):
    _, df, issues, _ = case
    html = rr.report_html(rp.analyse(df, FAST), issues, "Laminado 2", (len(df), len(df)))
    for text in ("Política de revisión humana · Laminado 2", "Auditoría de lo aceptado", "ISO 9001", "Apache 2.0"):
        assert text in html
    assert "<script" not in html


def test_ui_mode_renders_example():
    AppTest = pytest.importorskip("streamlit.testing.v1").AppTest
    app = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    at = AppTest.from_file(str(app), default_timeout=300).run()
    at.button_group[0].set_value("Triaje de revisión").run()
    at.selectbox[0].set_value("Placas de acero UCI: 1,941 reales, 30 % revisado").run()
    assert not at.exception
    assert any(m.label == "Piezas a revisión" for m in at.metric)


def test_runs_with_the_stub_pyarrow_of_the_browser(monkeypatch, case):
    import importlib
    import types

    stub = types.ModuleType("pyarrow")  # como el de stlite: sin RecordBatch
    stub.Table, stub.Array, stub.ChunkedArray = (type(n, (), {}) for n in ("Table", "Array", "ChunkedArray"))
    monkeypatch.setitem(__import__("sys").modules, "pyarrow", stub)
    importlib.reload(rp)
    assert rp.analyse(case[1], rp.Costos(remuestreos=20))["politica"]["revisiones"] > 0
