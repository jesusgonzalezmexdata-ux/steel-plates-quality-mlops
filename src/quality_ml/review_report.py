"""Reporte de una página de la política de revisión humana."""
from __future__ import annotations

import datetime as dt
import html

import pandas as pd


def mxn(v) -> str:
    return "—" if v is None or pd.isna(v) else (f"${v / 1e6:,.2f} M" if abs(v) >= 1e6 else f"${v:,.0f}")


def _e(x) -> str:
    return html.escape(str(x))


def _table(df: pd.DataFrame) -> str:
    head = "".join(f"<th>{_e(c)}</th>" for c in df.columns)
    body = "".join("<tr>" + "".join(f"<td>{_e(v)}</td>" for v in row) + "</tr>" for row in df.itertuples(index=False))
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def headline(r) -> str:
    p, n = r["politica"], r["piezas"]
    lo, hi = p["ahorro_vs_todo_ic"]
    text = (f"Acepta el resultado del sistema cuando su confianza supera el umbral de su clase y revisa lo demás: "
            f"{p['revisiones'] / n:.0%} de las piezas a revisión en lugar del 100 %, con ≈ {1000 * p['escapes'] / n:.1f} errores "
            f"que escapan por cada 1,000 piezas (intervalo {1000 * p['escapes_ic'][0] / n:.1f}–{1000 * p['escapes_ic'][1] / n:.1f}).")
    if lo > 0:
        text += f" Ahorra {mxn(p['ahorro_vs_todo'])} frente a revisar todo en estas {n:,} piezas (intervalo {mxn(lo)} a {mxn(hi)})."
    else:
        text += (f" Frente a revisar todo, el ahorro estimado es {mxn(p['ahorro_vs_todo'])} pero su intervalo ({mxn(lo)} a {mxn(hi)}) "
                 "incluye pérdida: conviene ampliar la muestra revisada antes de cambiar la inspección.")
    return text


def report_html(r, issues=None, linea: str = "Línea", data_rows=None) -> str:
    c, p, t, a = r["costos"], r["politica"], r["tabla"], r["auditoria"]
    parts = [f"<h1>Política de revisión humana · {_e(linea)}</h1>",
             f"<p class='meta'>Emitido el {dt.date.today():%d/%m/%Y} · Jesús R. L. González</p>", f"<p class='lead'>{_e(headline(r))}</p>"]
    err = sum(i.nivel == "error" for i in (issues or []))
    leidos = f"{data_rows[1]:,} de {data_rows[0]:,} filas válidas ({err} excluidas por error) · " if data_rows else ""
    parts.append(f"<h2>1 · Datos</h2><p>{leidos}{r['piezas']:,} piezas, {r['revisadas']:,} revisadas por personas con {r['errores']} errores "
                 f"del sistema. Costo de una revisión {mxn(c.revision)}; costo de un error que llega al cliente {mxn(c.escape)}. "
                 "Los datos se procesaron en el equipo del usuario.</p>")
    parts.append("<h2>2 · Política por clase</h2>" + _table(pd.DataFrame({
        "Clase del sistema": t["clase"], "Piezas": t["piezas"], "Revisadas": t["revisadas"],
        "Tasa de error": t["tasa_error"].map(lambda v: "—" if pd.isna(v) else f"{v:.1%}"),
        "Aceptar si confianza ≥": t["umbral"].map(lambda v: "nunca" if v > 1 else f"{v:.2f}"),
        "A revisión": t["pct_revision"].map("{:.0%}".format)}))
        + f"<p class='note'>Se acepta donde la probabilidad de error × {mxn(c.escape)} es menor que {mxn(c.revision)}, es decir con "
          f"P(error) &lt; {c.revision / c.escape:.1%}. P(error) sale de una regresión logística ponderada sobre la muestra revisada; las "
          "clases con pocas piezas revisadas se acercan al promedio.</p>")
    rows = [("Política por clase", p["revisiones"], p["escapes"], p["costo"]),
            ("Un solo umbral para todas", r["global_unico"]["revisiones"], r["global_unico"]["escapes"], r["global_unico"]["costo"]),
            ("Revisar todo", r["todo"]["revisiones"], 0.0, r["todo"]["costo"]),
            ("No revisar nada", 0, r["ninguna"]["escapes"], r["ninguna"]["costo"])]
    parts.append("<h2>3 · Comparación</h2>" + _table(pd.DataFrame({
        "Estrategia": [x[0] for x in rows], "Revisiones": [f"{x[1]:,}" for x in rows], "Errores que escapan": [f"{x[2]:.1f}" for x in rows],
        "Costo": [mxn(x[3]) for x in rows]}))
        + "<p class='note'>Los escapes de las políticas se miden fuera de muestra (umbrales ajustados sin las piezas con que se cuentan) "
          f"con intervalo de Jeffreys del {c.nivel:.0%}. Con cero errores observados la cota superior no es cero.</p>")
    semanal = r.get("semanal")
    carga = (f" Con ≈ {semanal['piezas']:,.0f} piezas por semana, la carga de revisión es ≈ {semanal['revisiones']:,.0f} piezas por semana."
             if semanal else "")
    parts.append(f"<h2>4 · Auditoría de lo aceptado</h2><p>Cada periodo, revisa al azar <b>{a['n']}</b> piezas aceptadas. Si aparecen "
                 f"<b>{a['alarma']} o más</b> errores, la tasa de escapes subió: vuelve a revisar todo y recalibra con una muestra nueva. "
                 f"Con cero errores en {a['n']} piezas se demuestra, con {c.nivel:.0%} de confianza, una tasa menor a {a['cota']:.1%}.{_e(carga)}</p>")
    parts.append("<h2>5 · Límites</h2><ul><li>La muestra revisada debe ser al azar dentro de cada banda de confianza; si alguien eligió "
                 "qué revisar por otro criterio, la estimación se sesga.</li><li>Si el sistema automático se recalibra o cambia el producto, "
                 "la política deja de valer hasta revisar una muestra nueva.</li><li>La confianza del sistema no tiene que ser una probabilidad "
                 "calibrada; basta con que ordene los errores.</li></ul>")
    parts.append("<p class='note'>ISO 9001:2015 · 8.6 Liberación de productos (criterio documentado de aceptación) · 8.7 Control de salidas "
                 "no conformes · 9.1.1 Seguimiento y medición (muestra de auditoría). Seguimiento en Power BI con la tabla "
                 "<code>seguimiento_revision.csv</code>.</p>")
    css = """body{font-family:Barlow,system-ui,-apple-system,'Segoe UI',sans-serif;color:#0E0F11;max-width:900px;margin:24px auto;
padding:0 16px;font-size:14px;line-height:1.5}h1{font:700 26px/1.1 'Barlow Condensed','Arial Narrow',sans-serif;margin-bottom:4px}
h2{font:700 18px/1.2 'Barlow Condensed','Arial Narrow',sans-serif;margin:22px 0 6px;border-bottom:3px solid #0E0F11;padding-bottom:2px}
.meta{color:#4A4E54;margin-top:0}.lead{font-size:15px;background:#FFD21F;padding:10px 12px;border-top:4px solid #0E0F11}
table{border-collapse:collapse;margin:6px 0;font-size:13px}th,td{border:1px solid #C9CDD1;padding:4px 8px;text-align:left}
th{background:#F6F7F5}.note{color:#4A4E54;font-size:12.5px}@media print{body{margin:0}h2{break-after:avoid}}"""
    return ("<!doctype html><html lang='es'><head><meta charset='utf-8'><title>Política de revisión · "
            f"{_e(linea)}</title><style>{css}</style></head><body>" + "".join(parts)
            + "<p class='note'>© 2026 Jesús R. L. González · Código bajo licencia Apache 2.0</p></body></html>")
