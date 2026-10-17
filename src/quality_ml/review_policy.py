"""Política de revisión humana para un sistema de inspección automática, independiente del dataset de UCI.

Decide, por clase predicha, desde qué confianza se acepta el resultado del sistema y qué se manda a una
persona, minimizando costo de revisión + costo de los errores que escapan al cliente.

* La tasa de error por confianza se estima con la muestra revisada por personas, ponderada por banda de
  confianza (si se revisó más lo dudoso, los pesos lo corrigen; dentro de cada banda la muestra debe ser al azar).
* P(error | confianza, clase) con regresión logística ponderada; se acepta donde P(error) × costo de escape es
  menor que el costo de revisar. Las clases con pocas piezas revisadas se acercan al promedio por regularización.
* Los escapes se miden fuera de muestra: umbrales ajustados con 4/5 de la muestra y errores contados en el 1/5
  restante, con intervalo bootstrap; tamaño de la muestra de auditoría para vigilar lo aceptado.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import binom

GLOBAL = "(todas)"

# stlite carga un pyarrow incompleto y scikit-learn pregunta por sus clases al validar entradas: se completan con
# tipos vacíos (nunca coinciden con un arreglo), sin tocar un pyarrow real.
_pa = sys.modules.get("pyarrow")
if _pa is not None:
    for _name in ("Table", "RecordBatch", "Array", "ChunkedArray"):
        if not hasattr(_pa, _name):
            setattr(_pa, _name, type(_name, (), {}))


@dataclass(frozen=True)
class Costos:
    revision: float = 40.0        # tiempo de una persona revisando una pieza (MXN)
    escape: float = 1_500.0       # pieza con clase equivocada que llega al cliente: reclamo, retrabajo, flete
    nivel: float = 0.95
    remuestreos: int = 1000
    folds: int = 5
    semilla: int = 7


def weights(df: pd.DataFrame, bins: int = 10) -> tuple[pd.Series, pd.DataFrame]:
    """Peso de cada pieza revisada = piezas en su banda de confianza / piezas revisadas en esa banda."""
    rev = df["revisada"]
    edges = np.unique(np.quantile(df.loc[rev, "confianza"], np.linspace(0, 1, bins + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    band = pd.cut(df["confianza"], edges, include_lowest=True)
    tab = pd.DataFrame({"piezas": band.value_counts(sort=False), "revisadas": band[rev].value_counts(sort=False)})
    tab["fraccion_revisada"] = tab["revisadas"] / tab["piezas"]
    w = (band.map(tab["piezas"] / tab["revisadas"]).astype(float)).where(rev, 0.0)
    return w, tab


def _logit(p):
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def _design(df: pd.DataFrame, classes: list[str], by_class: bool) -> np.ndarray:
    x = _logit(df["confianza"].to_numpy())[:, None]
    if not by_class:
        return x
    return np.hstack([x, (df["clase_predicha"].to_numpy()[:, None] == np.asarray(classes)[None, :]).astype(float)])


def fit_thresholds(df: pd.DataFrame, w: pd.Series, c: Costos, fit_mask: np.ndarray | None = None, by_class: bool = True) -> dict:
    """Umbral de confianza por clase donde P(error | confianza, clase) = costo_revisión / costo_escape.

    P(error) sale de una regresión logística ponderada sobre la muestra revisada: pendiente común en
    logit(confianza) y un intercepto por clase con regularización, que acerca al promedio las clases con
    pocas piezas revisadas. Un corte exacto por clase memoriza la muestra; esta curva no."""
    from sklearn.linear_model import LogisticRegression

    fit = df["revisada"].to_numpy() if fit_mask is None else fit_mask
    classes = sorted(df["clase_predicha"].unique())
    X, y, sw = _design(df, classes, by_class)[fit], df["error"].to_numpy(int)[fit], w.to_numpy()[fit]
    model = LogisticRegression(C=1.0, max_iter=2000).fit(X, y, sample_weight=sw / sw.mean())
    b0, b1 = float(model.intercept_[0]), float(model.coef_[0, 0])
    target = _logit(c.revision / c.escape)

    def cut(bc: float) -> float:
        if b1 >= 0:  # la confianza no ordena los errores: aceptar todo o nada según el costo
            return 0.0 if b0 + bc + b1 * _logit(0.5) < target else float(np.nextafter(1.0, 2.0))
        return float(1 / (1 + np.exp(-(target - b0 - bc) / b1)))

    out = {GLOBAL: cut(float(np.average(model.coef_[0, 1:], weights=[(df["clase_predicha"] == k).sum() for k in classes])) if by_class else 0.0)}
    for i, cls in enumerate(classes):
        out[cls] = cut(float(model.coef_[0, 1 + i])) if by_class else out[GLOBAL]
    return out


def accept(df: pd.DataFrame, thr: dict) -> np.ndarray:
    t = df["clase_predicha"].map(thr).fillna(thr[GLOBAL]).to_numpy(float)
    return df["confianza"].to_numpy() >= t


def evaluate(df: pd.DataFrame, w: pd.Series, acc: np.ndarray, c: Costos, mask: np.ndarray | None = None) -> dict:
    """Revisiones (todas las piezas) y escapes estimados con la muestra (o con la parte ``mask`` de ella)."""
    m = df["revisada"].to_numpy() if mask is None else mask
    scale = df["revisada"].sum() / max(1, m.sum())
    escapes = float((w.to_numpy() * df["error"].to_numpy() * acc * m).sum() * scale)
    reviews = int((~acc).sum())
    return dict(piezas=len(df), revisiones=reviews, aceptadas=int(acc.sum()), escapes=escapes,
                costo=c.revision * reviews + c.escape * escapes)


def _crossfit(df, w, c: Costos, by_class: bool = True) -> np.ndarray:
    """Para cada pieza revisada, si la habría aceptado una política ajustada sin ella (validación cruzada estratificada)."""
    rev_idx = np.flatnonzero(df["revisada"].to_numpy())
    rng = np.random.default_rng(c.semilla)
    folds = np.empty(len(rev_idx), int)
    for _, g in df.iloc[rev_idx].groupby("clase_predicha").indices.items():
        folds[g] = rng.permutation(np.arange(len(g)) % c.folds)
    acc_oof = np.zeros(len(df), bool)
    for k in range(c.folds):
        test = np.zeros(len(df), bool)
        test[rev_idx[folds == k]] = True
        acc = accept(df, fit_thresholds(df, w, c, df["revisada"].to_numpy() & ~test, by_class))
        acc_oof[test] = acc[test]
    return acc_oof


def _honest(df, w, acc_full, acc_oof, c: Costos) -> dict:
    """Revisiones de la política final (no dependen de etiquetas) y escapes fuera de muestra con intervalo.

    La tasa de error de lo aceptado se estima con las piezas revisadas que la política ajustada sin ellas
    habría aceptado (ponderadas por banda). El intervalo es de Jeffreys sobre el tamaño efectivo de muestra:
    con cero errores observados la cota superior no es cero, a diferencia de un bootstrap."""
    from scipy.stats import beta

    rev = df["revisada"].to_numpy()
    wv, err = w.to_numpy(), df["error"].to_numpy()
    m = rev & acc_oof
    q = [(1 - c.nivel) / 2, (1 + c.nivel) / 2]
    n_acc, reviews = int(acc_full.sum()), int((~acc_full).sum())
    if m.any():
        wm = wv[m]
        rate_w = float((wm * err[m]).sum() / wm.sum())
        m_eff = float(wm.sum() ** 2 / (wm ** 2).sum())
        k_eff = rate_w * m_eff
        rate = (k_eff + 0.5) / (m_eff + 1)
        lo, hi = beta.ppf(q, k_eff + 0.5, m_eff - k_eff + 0.5)
    else:  # la política no acepta nada: no hay escapes posibles
        rate = lo = hi = 0.0
        m_eff = 0.0
    esc, esc_lo, esc_hi = rate * n_acc, lo * n_acc, hi * n_acc
    cost = c.revision * reviews + c.escape * esc
    none_err = float((wv * err).sum())
    return dict(piezas=len(df), revisiones=reviews, aceptadas=n_acc, escapes=esc, escapes_ic=(float(esc_lo), float(esc_hi)),
                tasa_escape=float(rate), tasa_escape_ic=(float(lo), float(hi)), muestra_aceptadas=m_eff, costo=cost,
                ahorro_vs_todo=c.revision * len(df) - cost,
                ahorro_vs_todo_ic=(c.revision * len(df) - (c.revision * reviews + c.escape * esc_hi),
                                   c.revision * len(df) - (c.revision * reviews + c.escape * esc_lo)),
                ahorro_vs_ninguna=c.escape * none_err - cost)


def audit_sample(rate: float, upper: float, level: float = 0.95) -> dict:
    """Muestra al azar de lo aceptado para vigilar los escapes: cuántas piezas revisar y cuántos errores disparan alarma.

    n es el tamaño con el que cero errores demuestran, con confianza ``level``, que la tasa está por debajo de la
    cota superior estimada hoy; la alarma es el número de errores que la tasa esperada daría con probabilidad < 1 %."""
    upper = float(np.clip(upper, 1e-3, 0.5))
    n = int(np.ceil(np.log(1 - level) / np.log(1 - upper)))
    return dict(n=n, cota=upper, alarma=int(binom.ppf(0.99, n, max(rate, 1e-6))) + 1, tasa=rate)


def analyse(df: pd.DataFrame, c: Costos | None = None) -> dict:
    c = c or Costos()
    w, bands = weights(df)
    thr = fit_thresholds(df, w, c)
    acc = accept(df, thr)
    pol = _honest(df, w, acc, _crossfit(df, w, c), c)
    thr_g = fit_thresholds(df, w, c, by_class=False)
    glob = _honest(df, w, accept(df, thr_g), _crossfit(df, w, c, by_class=False), c)
    none = evaluate(df, w, np.ones(len(df), bool), c)
    all_ = dict(piezas=len(df), revisiones=len(df), aceptadas=0, escapes=0.0, costo=c.revision * len(df))

    rows = []
    for cls, g in df.groupby("clase_predicha"):
        a, wg, rv = acc[g.index], w[g.index], g["revisada"].to_numpy()
        err_rate = float((wg * g["error"]).sum() / wg.sum()) if rv.any() else np.nan
        esc = float((wg * g["error"] * a).sum())
        rows.append(dict(clase=cls, piezas=len(g), revisadas=int(rv.sum()), tasa_error=err_rate, umbral=thr[cls],
                         a_revision=int((~a).sum()), pct_revision=float((~a).mean()),
                         errores_en_aceptadas=esc, aceptadas=int(a.sum())))
    tabla = pd.DataFrame(rows).sort_values("piezas", ascending=False).reset_index(drop=True)
    weekly = None
    if "fecha" in df.columns and df["fecha"].notna().mean() > 0.8:
        wk = df["fecha"].dt.to_period("W-SUN")
        weekly = dict(piezas=float(df.groupby(wk).size().median()),
                      revisiones=float(pd.Series(~acc).groupby(wk.to_numpy()).sum().median()))
    return dict(costos=c, umbrales=thr, umbral_global=thr_g[GLOBAL], aceptada=acc, tabla=tabla, politica=pol, global_unico=glob,
                ninguna=none, todo=all_, auditoria=audit_sample(pol['tasa_escape'], pol['tasa_escape_ic'][1], c.nivel), semanal=weekly, bandas=bands,
                sesgo_muestra=float(bands["fraccion_revisada"].max() / max(1e-9, bands["fraccion_revisada"].min())),
                piezas=len(df), revisadas=int(df["revisada"].sum()), errores=int(df["error"].sum()))


def review_list(df: pd.DataFrame, r: dict) -> pd.DataFrame:
    """Piezas que la política manda a revisión y todavía no tienen revisión humana, de menor a mayor confianza."""
    m = ~r["aceptada"] & ~df["revisada"].to_numpy()
    return df.loc[m, ["pieza", "clase_predicha", "confianza"]].sort_values("confianza").reset_index(drop=True)


def bi_export(r: dict) -> pd.DataFrame:
    """Tabla para la página de seguimiento en Power BI: una fila por clase con su umbral y su carga."""
    t = r["tabla"].copy()
    t.insert(0, "fecha_corte", pd.Timestamp.today().normalize().date())
    t["costo_revision"] = r["costos"].revision
    t["costo_escape"] = r["costos"].escape
    t["clausula_iso9001"] = "8.6 Liberación de productos y servicios; 8.7 Control de salidas no conformes"
    return t
