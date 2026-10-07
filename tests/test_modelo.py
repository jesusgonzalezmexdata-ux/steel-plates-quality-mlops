import re
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from etl.build_star_schema import build, load_raw
from qbi import measures as M
from qbi.config import DEFECTOS

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def modelo():
    return M.load_model()


@pytest.fixture(scope="module")
def plano(modelo):
    return M.flat(modelo)


def test_crudo_es_el_dataset_uci():
    raw = load_raw()
    assert raw.shape == (1941, 35) and raw.isna().sum().sum() == 0
    assert (raw[list(DEFECTOS)].sum(axis=1) == 1).all()


def test_csv_del_repo_coincide_con_el_etl(modelo):
    fresco = build(load_raw())
    for n, df in fresco.items():
        pd.testing.assert_frame_equal(df.reset_index(drop=True), modelo[n], check_dtype=False)


def test_integridad_estrella(modelo):
    f = modelo["Fact_Defecto"]
    assert f["id_defecto"].is_unique and len(f) == 1941
    for dim, llave in [("Dim_TipoDefecto", "id_tipo_defecto"), ("Dim_Acero", "id_acero"),
                       ("Dim_BandaTamano", "id_banda_tamano")]:
        assert modelo[dim][llave].is_unique
        assert f[llave].isin(modelo[dim][llave]).all(), f"huérfanos en {llave}"


def test_conteos_por_tipo_coinciden_con_el_crudo(plano):
    raw = load_raw()
    esperado = raw[list(DEFECTOS)].sum()
    obtenido = plano.groupby("columna_origen").size()
    assert (obtenido[esperado.index] == esperado).all()


def test_bandas_de_tamano(plano):
    assert (plano.loc[plano.id_banda_tamano == 5, "area_px2"] >= 5000).all()
    assert (plano.loc[plano.id_banda_tamano == 1, "area_px2"] < 50).all()


def test_pareto_acumula_100_y_esta_ordenado(plano):
    p = M.pareto(plano)
    assert p["copq_mxn"].is_monotonic_decreasing and p["copq_acum_pct"].iloc[-1] == pytest.approx(1)
    assert p["copq_mxn"].sum() == 2_242_600


def test_carta_de_medias_formula(plano):
    c = M.carta_medias(plano, "espesor").set_index("espesor")
    mu, s = plano.log_area.mean(), plano.log_area.std(ddof=1)
    g = plano[plano.espesor == 40].log_area
    assert c.loc[40, "media"] == pytest.approx(g.mean())
    assert c.loc[40, "ucl"] == pytest.approx(mu + 3 * s / np.sqrt(len(g)))
    assert c.loc[40, "lcl"] == pytest.approx(mu - 3 * s / np.sqrt(len(g)))


def test_capacidad_y_semaforo(plano):
    k = plano[plano.columna_origen == "K_Scatch"].log_area
    assert M.cpu(k) == pytest.approx((np.log10(500) - k.mean()) / (3 * k.std(ddof=1)))
    assert M.cpu(k) < 0
    assert (M.semaforo(1.5), M.semaforo(1.33), M.semaforo(1.0), M.semaforo(0.99)) == \
        ("verde", "verde", "amarillo", "rojo")


def test_sql_independiente_coincide_con_python(modelo, plano):
    """Segunda implementación (SQL en DuckDB) de COPQ, Pareto, límites de control y Cpk."""
    con = duckdb.connect()
    for n, df in modelo.items():
        con.register(n, df)
    sql = con.execute("""
        SELECT t.tipo_defecto, count(*) AS defectos, sum(t.costo_unitario_mxn) AS copq
        FROM Fact_Defecto f JOIN Dim_TipoDefecto t USING (id_tipo_defecto)
        GROUP BY 1 ORDER BY copq DESC""").df()
    p = M.pareto(plano)
    assert sql["tipo_defecto"].tolist() == p["tipo_defecto"].tolist()
    assert sql["copq"].tolist() == p["copq_mxn"].tolist()

    lim = con.execute("""
        WITH g AS (SELECT stddev_samp(log_area) s, avg(log_area) m FROM Fact_Defecto)
        SELECT a.espesor, avg(f.log_area) media, count(*) n,
               g.m + 3*g.s/sqrt(count(*)) ucl, g.m - 3*g.s/sqrt(count(*)) lcl
        FROM Fact_Defecto f JOIN Dim_Acero a USING (id_acero), g
        GROUP BY a.espesor, g.m, g.s ORDER BY a.espesor""").df()
    c = M.carta_medias(plano, "espesor")
    np.testing.assert_allclose(lim[["media", "ucl", "lcl"]].values, c[["media", "ucl", "lcl"]].values)

    cpk = con.execute("""
        SELECT t.tipo_defecto, (log10(500) - avg(f.log_area)) / (3*stddev_samp(f.log_area)) cpu
        FROM Fact_Defecto f JOIN Dim_TipoDefecto t USING (id_tipo_defecto) GROUP BY 1""").df().set_index("tipo_defecto")["cpu"]
    py = M.capacidad(plano, "tipo_defecto").set_index("tipo_defecto")["cpu"]
    np.testing.assert_allclose(cpk.sort_index().values, py.sort_index().values)


def test_dax_tiene_todas_las_medidas_y_parentesis_balanceados():
    dax = (ROOT / "powerbi/dax/measures.dax").read_text(encoding="utf-8")
    codigo = "\n".join(l for l in dax.splitlines() if not l.strip().startswith("//"))
    assert codigo.count("(") == codigo.count(")")
    medidas = set(re.findall(r"^([A-Za-zÁ-ú0-9 %.]+?) =", codigo, flags=re.M))
    for esperada in ["Defectos", "COPQ MXN", "COPQ Acumulado %", "UCL", "LCL", "Cpk",
                     "Semaforo Cpk Color", "Texto ISO 10.2"]:
        assert esperada in medidas, esperada
    llamadas = set(re.findall(r"\[([^\]]+)\]", codigo))
    columnas = {c for c in pd.concat([m.columns.to_series() for m in M.load_model().values()])}
    desconocidas = {x for x in llamadas if x not in medidas and x not in columnas and x != "USL_px2"}
    assert not desconocidas, desconocidas


def test_m_consultas_existen_y_referencian_columnas_reales():
    raw_cols = set(load_raw().columns)
    for archivo in (ROOT / "powerbi/powerquery").glob("*.pq"):
        assert archivo.read_text(encoding="utf-8").count("(") == archivo.read_text(encoding="utf-8").count(")")
    m = (ROOT / "powerbi/powerquery/05_Fact_Defecto.pq").read_text(encoding="utf-8")
    usadas = set(re.findall(r'"([A-Z][A-Za-z_]+)"', m)) & raw_cols
    assert {"Pixels_Areas", "LogOfAreas", "Pastry", "Bumps"} <= usadas


def test_valores_citados_en_el_readme(plano):
    assert len(plano) == 1941 and (plano.area_px2 >= 5000).sum() == 289
    assert M.cpu(plano.log_area) == pytest.approx(0.0873, abs=5e-4)
    k = plano[plano.columna_origen == "K_Scatch"]
    assert (k.area_px2 >= 5000).sum() == 267
    assert (k.espesor == 40).mean() > 0.98 and (k.tipo_acero == "A400").mean() > 0.99
    assert (plano.espesor == 40).sum() == 710
    p = M.pareto(plano)
    assert p.copq_acum_pct.iloc[2] == pytest.approx(0.777, abs=1e-3)


def test_decisiones_siguen_los_umbrales(plano):
    d = M.decisiones(plano).set_index("tipo_defecto")
    assert "8.7" in d.loc["Rayón en K (K_Scatch)", "accion"] and "10.2" in d.loc["Rayón en K (K_Scatch)", "accion"]
    assert d.loc["Manchas", "accion"].startswith("Sin acción")
    assert d.copq_pct.sum() == pytest.approx(1)
    assert d.loc["Rayón en K (K_Scatch)", "fuera_usl_pct"] == pytest.approx((plano[plano.columna_origen == "K_Scatch"].area_px2 > 500).mean())


def test_pruebas_de_estres_sostienen_las_conclusiones():
    from tools.stress_tests import correr
    r = correr(n=300)
    assert r["top3_estable"] > 0.95
    assert all(c < 1.0 for c, _ in [r["usl"][u] for u in (200, 500, 1000, 2000, 5000)])
    assert all(p < 0.05 for _, p in r["normalidad"].values())
    assert r["carta"]["solo_abolladuras"][0] < r["carta"]["todos"][0]
