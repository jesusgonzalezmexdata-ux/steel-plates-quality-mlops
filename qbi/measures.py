"""Réplica en Python de las medidas DAX (powerbi/dax/measures.dax). Las pruebas las contrastan con SQL."""
from pathlib import Path

import numpy as np
import pandas as pd

from qbi.config import (N_MIN_GRUPO, SIGMA_K, UMBRAL_COPQ_PCT, UMBRAL_CPK, UMBRAL_FUERA_USL_PCT,
                        USL_AREA_PX)

ROOT = Path(__file__).resolve().parents[1]


def load_model(folder: Path | None = None) -> dict[str, pd.DataFrame]:
    folder = folder or ROOT / "data/model"
    return {n: pd.read_csv(folder / f"{n}.csv") for n in
            ["Fact_Defecto", "Dim_TipoDefecto", "Dim_Acero", "Dim_BandaTamano"]}


def flat(m: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Hecho + dimensiones (lo que ve un visual de Power BI)."""
    return (m["Fact_Defecto"].merge(m["Dim_TipoDefecto"], on="id_tipo_defecto")
            .merge(m["Dim_Acero"], on="id_acero").merge(m["Dim_BandaTamano"], on="id_banda_tamano"))


def pareto(df: pd.DataFrame, by: str = "tipo_defecto") -> pd.DataFrame:
    t = (df.assign(copq=df["costo_unitario_mxn"]).groupby(by)
         .agg(defectos=("id_defecto", "count"), copq_mxn=("copq", "sum")).reset_index()
         .sort_values("copq_mxn", ascending=False, ignore_index=True))
    t["copq_acum_pct"] = t["copq_mxn"].cumsum() / t["copq_mxn"].sum()
    t["defectos_pct"] = t["defectos"] / t["defectos"].sum()
    return t


def carta_medias(df: pd.DataFrame, by: str = "espesor", var: str = "log_area",
                 k: float = SIGMA_K, n_min: int = 5) -> pd.DataFrame:
    """Media por grupo con límites mu ± k·s/√n (s global, muestral). Equivale a las medidas UCL/LCL de DAX."""
    mu, s = df[var].mean(), df[var].std(ddof=1)
    g = df.groupby(by)[var].agg(media="mean", n="count").reset_index()
    g["lc"], g["ucl"], g["lcl"] = mu, mu + k * s / np.sqrt(g["n"]), mu - k * s / np.sqrt(g["n"])
    g["fuera"] = (g["media"] > g["ucl"]) | (g["media"] < g["lcl"])
    g["n_suficiente"] = g["n"] >= n_min
    return g


def cpu(x: pd.Series, usl: float = USL_AREA_PX) -> float:
    """Capacidad unilateral superior del tamaño del defecto (log10 del área), con USL en px²."""
    return (np.log10(usl) - x.mean()) / (3 * x.std(ddof=1))


def semaforo(v: float) -> str:
    return "verde" if v >= UMBRAL_CPK else "amarillo" if v >= 1.0 else "rojo"


def capacidad(df: pd.DataFrame, by: str, usl: float = USL_AREA_PX) -> pd.DataFrame:
    t = df.groupby(by)["log_area"].apply(lambda x: pd.Series({"n": len(x), "cpu": cpu(x, usl)})).unstack().reset_index()
    t["semaforo"] = t["cpu"].map(semaforo)
    return t


def fuera_usl(df: pd.DataFrame, usl: float = USL_AREA_PX) -> float:
    """Fracción empírica de placas con defecto mayor al USL (no supone normalidad)."""
    return float((df["area_px2"] > usl).mean())


def decisiones(df: pd.DataFrame, usl: float = USL_AREA_PX) -> pd.DataFrame:
    """Regla de decisión por tipo de defecto. Cada acción cita la cláusula ISO 9001:2015 que la respalda."""
    p = pareto(df).set_index("tipo_defecto")
    filas = []
    for tipo, g in df.groupby("tipo_defecto"):
        share, fuera, cpk_ = p.loc[tipo, "copq_mxn"] / p["copq_mxn"].sum(), fuera_usl(g, usl), cpu(g["log_area"], usl)
        acciones = []
        if fuera >= UMBRAL_FUERA_USL_PCT:
            acciones.append("Contener e inspeccionar 100 % (8.7)")
        if share >= UMBRAL_COPQ_PCT:
            acciones.append("Causa raíz y acción correctiva (10.2)")
        if len(g) >= N_MIN_GRUPO and cpk_ < 1.0 and not acciones:
            acciones.append("Vigilar y evaluar (9.1.3)")
        filas.append({"tipo_defecto": tipo, "placas": len(g), "copq_pct": share, "fuera_usl_pct": fuera, "cpk": cpk_,
                      "accion": " + ".join(acciones) or "Sin acción: dentro de umbrales"})
    return pd.DataFrame(filas).sort_values("copq_pct", ascending=False, ignore_index=True)
