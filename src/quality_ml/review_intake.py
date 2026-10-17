"""Entrada del triaje de revisión humana: resultados del sistema automático y una muestra revisada por personas.

Una fila por pieza inspeccionada: clase que dio el sistema, su confianza y, solo en la muestra revisada,
la clase que confirmó la persona. Acepta Excel o CSV; los mensajes van en español con número de fila.
"""
from __future__ import annotations

import io
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ALIASES = {"id": "pieza", "pieza_id": "pieza", "serie": "pieza", "item": "pieza", "placa": "pieza", "tarjeta": "pieza",
           "prediccion": "clase_predicha", "clase_sistema": "clase_predicha", "predicted_class": "clase_predicha", "defecto_sistema": "clase_predicha",
           "score": "confianza", "probabilidad": "confianza", "confidence": "confianza", "max_probability": "confianza",
           "clase_verdadera": "clase_real", "revision": "clase_real", "defecto_real": "clase_real", "true_class": "clase_real",
           "date": "fecha", "fecha_inspeccion": "fecha"}
MIN_REVIEWED, MIN_ERRORS = 100, 10
EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "review_triage" / "inspeccion_placas.csv"

INSTRUCTIONS = [
    ("Columna", "Obligatoria", "Qué poner"),
    ("pieza", "No", "Identificador de la pieza, placa o tarjeta"),
    ("clase_predicha", "Sí", "Clase o defecto que asignó el sistema automático"),
    ("confianza", "Sí", "Confianza del sistema en esa clase: de 0 a 1, o de 0 a 100"),
    ("clase_real", "Solo en la muestra", "Clase confirmada por una persona. Vacío si la pieza no se revisó"),
    ("fecha", "No", "Fecha de inspección (para calcular la carga por semana)"),
    ("", "", "La muestra revisada debe elegirse al azar dentro de cada banda de confianza (no solo las dudosas). Mínimo 100 piezas "
     "revisadas con 10 errores del sistema. El archivo se procesa en tu navegador y no se envía a ningún servidor."),
]


class DataError(ValueError):
    """El archivo no se puede analizar."""


@dataclass
class Issue:
    nivel: str
    fila: int | None
    mensaje: str


def _key(text) -> str:
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    key = "_".join(text.strip().lower().replace("-", " ").split())
    return ALIASES.get(key, key)


def read_table(source, name: str = "") -> pd.DataFrame:
    raw = source.getvalue() if hasattr(source, "getvalue") else source
    name = name or getattr(source, "name", "")
    try:
        if isinstance(raw, (str, Path)):
            name, raw = str(raw), Path(raw).read_bytes()
        if str(name).lower().endswith(".csv") or raw[:2] != b"PK":
            text = raw.decode("utf-8-sig")
            head = text.split("\n", 1)[0]
            df = pd.read_csv(io.StringIO(text), sep=";" if head.count(";") > head.count(",") else ",", dtype=str, keep_default_na=False)
        else:
            sheets = pd.read_excel(io.BytesIO(raw), sheet_name=None, dtype=str)
            df = next((d for n, d in sheets.items() if _key(n) == "inspeccion"), next(iter(sheets.values())))
    except Exception as exc:
        raise DataError(f"No se pudo leer el archivo como Excel (.xlsx) o CSV: {exc}") from exc
    return df.rename(columns=_key).dropna(how="all")


def validate(df: pd.DataFrame):
    """Devuelve (piezas con clase_predicha, confianza en [0, 1], clase_real o NA, revisada, fecha opcional; avisos)."""
    df = df.rename(columns=_key)
    missing = [c for c in ("clase_predicha", "confianza") if c not in df.columns]
    if missing:
        raise DataError("Faltan columnas obligatorias: " + ", ".join(missing) + ". Usa la plantilla descargable.")
    issues: list[Issue] = []
    rows = pd.Series(np.arange(len(df)) + 2, index=df.index)
    pred = df["clase_predicha"].astype(str).str.strip()
    conf_txt = df["confianza"].astype(str).str.strip().str.replace("%", "", regex=False).str.replace(",", ".", regex=False)
    conf = pd.to_numeric(conf_txt, errors="coerce")
    if conf.dropna().gt(1).mean() > 0.5 or df["confianza"].astype(str).str.contains("%").any():
        conf = conf / 100
        issues.append(Issue("aviso", None, "La confianza viene de 0 a 100: se convirtió a 0–1."))
    bad = pred.isin(["", "nan", "None"]) | conf.isna() | ~conf.between(0, 1)
    for r in df.index[bad][:30]:
        what = "«clase_predicha» vacía" if pred[r] in ("", "nan", "None") else f"«confianza» debe estar entre 0 y 1 (valor: {df.at[r, 'confianza']!r})"
        issues.append(Issue("error", int(rows[r]), what))
    if bad.sum() > 30:
        issues.append(Issue("error", None, f"{int(bad.sum())} filas excluidas en total."))
    real = df["clase_real"].astype(str).str.strip() if "clase_real" in df.columns else pd.Series("", index=df.index)
    real = real.where(~real.isin(["", "nan", "None"]))
    out = pd.DataFrame({"pieza": df["pieza"].astype(str) if "pieza" in df.columns else [f"#{r}" for r in rows],
                        "clase_predicha": pred, "confianza": conf, "clase_real": real})
    if "fecha" in df.columns:
        f = df["fecha"].astype(str).str.strip().str.slice(0, 10)
        out["fecha"] = pd.to_datetime(f, format="%Y-%m-%d", errors="coerce").fillna(pd.to_datetime(f, format="%d/%m/%Y", errors="coerce"))
    out = out[~bad].reset_index(drop=True)
    out["revisada"] = out["clase_real"].notna()
    out["error"] = out["revisada"] & (out["clase_real"] != out["clase_predicha"])
    n_rev, n_err = int(out["revisada"].sum()), int(out["error"].sum())
    if n_rev < MIN_REVIEWED or n_err < MIN_ERRORS:
        raise DataError(f"Se necesitan al menos {MIN_REVIEWED} piezas revisadas por personas con {MIN_ERRORS} errores del sistema; "
                        f"hay {n_rev} revisadas con {n_err} errores.")
    nuevas = sorted(set(out.loc[out["revisada"], "clase_real"]) - set(out["clase_predicha"]))
    if nuevas:
        issues.append(Issue("aviso", None, "Clases confirmadas que el sistema nunca asigna: " + ", ".join(nuevas[:8]) + "."))
    return out, issues


# ---------------------------------------------------------------- ejemplos
def example() -> pd.DataFrame:
    """1,941 placas reales de UCI con predicciones fuera de muestra; 30 % revisado por estratos de confianza."""
    return pd.read_csv(EXAMPLE, dtype=str, keep_default_na=False)


def example_with_errors() -> pd.DataFrame:
    df = example().drop(columns=["clase_real_oculta", "origen"])
    df.loc[3, "confianza"] = "1.7"
    df.loc[8, "clase_predicha"] = ""
    df["confianza"] = (df["confianza"].astype(float) * 100).round(1).astype(str)
    df.loc[3, "confianza"] = "170"
    return df


def template_bytes() -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xl:
        example().drop(columns=["clase_real_oculta", "origen"]).to_excel(xl, sheet_name="inspeccion", index=False)
        pd.DataFrame(INSTRUCTIONS[1:], columns=INSTRUCTIONS[0]).to_excel(xl, sheet_name="instrucciones", index=False)
    return buf.getvalue()


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")
