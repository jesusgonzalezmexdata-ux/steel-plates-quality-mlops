"""Modo «Triaje de revisión»: qué resultados del sistema automático revisa una persona, con los datos del usuario."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quality_ml import review_intake as ri, review_policy as rp, review_report as rr

NEGRO, LINEA, AMARILLO, ROJO = "#0E0F11", "#C9CDD1", "#FFD21F", "#D7261E"


def _md(text: str) -> str:
    return text.replace("$", "\\$")


@st.cache_data(show_spinner=False)
def _template():
    return ri.template_bytes()


@st.cache_data(show_spinner=False)
def _example(kind: str) -> bytes:
    df = ri.example_with_errors() if kind == "errores" else ri.example().drop(columns=["clase_real_oculta", "origen"])
    return ri.to_csv_bytes(df)


@st.cache_data(show_spinner="Calculando la política y validándola fuera de muestra…")
def _run(content: bytes, name: str, costos: rp.Costos):
    raw = ri.read_table(content, name)
    df, issues = ri.validate(raw)
    return len(raw), df, issues, rp.analyse(df, costos)


def _bands_fig(df, r):
    rev = df[df["revisada"]]
    edges = np.array([0, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0001])
    band = pd.cut(rev["confianza"], edges, right=False)
    t = rev.groupby(band, observed=True)["error"].agg(["mean", "size"]).reset_index()
    labels = [f"{iv.left:.2f}–{min(iv.right, 1):.2f}" for iv in t["confianza"]]
    corte = r["costos"].revision / r["costos"].escape
    fig = go.Figure(go.Bar(x=labels, y=t["mean"], marker_color=[NEGRO if v > corte else LINEA for v in t["mean"]],
                           text=[f"{v:.0%} · n={n}" for v, n in zip(t["mean"], t["size"], strict=True)], textposition="outside",
                           hovertemplate="confianza %{x}: %{y:.1%} de error<extra></extra>"))
    fig.add_hline(y=corte, line=dict(color=ROJO, dash="dash"))
    fig.update_layout(title=f"Tasa de error por confianza (muestra revisada) · en rojo, {corte:.1%}: arriba de eso conviene revisar", height=330, margin=dict(l=60, r=10, t=50, b=40),
                      plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF", font_color=NEGRO, font_family="Barlow, system-ui, sans-serif",
                      yaxis=dict(tickformat=".0%", gridcolor="#E9EBE7", range=[0, max(t["mean"].max(), corte) * 1.25]),
                      xaxis=dict(title="confianza del sistema"))
    return fig


def render():
    st.subheader("Triaje de revisión humana para inspección automática")
    st.markdown("Sube los resultados de tu sistema de inspección (clase y confianza) con una muestra revisada por personas y obtén "
                "**desde qué confianza aceptar cada clase sin revisión**, la carga de revisión esperada y la muestra para auditar lo "
                "aceptado. **El archivo se procesa en tu navegador: no se envía a ningún servidor.**")
    a, b = st.columns([1, 2])
    a.download_button("Descargar plantilla de Excel (con datos de ejemplo)", _template(), "plantilla_revision.xlsx",
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    ejemplo = b.selectbox("O prueba con un ejemplo", ["(ninguno)", "Placas de acero UCI: 1,941 reales, 30 % revisado",
                                                       "Placas de acero UCI con errores de captura"])
    st.caption("Columnas: *clase_predicha, confianza* y, en la muestra revisada, *clase_real*; opcional *pieza* y *fecha*. La muestra "
               "debe elegirse al azar dentro de cada banda de confianza. Mínimo 100 revisadas con 10 errores.")
    up = st.file_uploader("Resultados del sistema (.xlsx o .csv)", type=["xlsx", "csv"])
    linea = st.text_input("Línea o sistema (aparece en el reporte)", "Mi línea")
    c1, c2 = st.columns(2)
    c_rev = c1.number_input("Costo de una revisión (MXN)", 1, 100_000, 40, 5, help="Tiempo de la persona que revisa una pieza.")
    c_esc = c2.number_input("Costo de un error que llega al cliente (MXN)", 1, 10_000_000, 1_500, 100,
                            help="Reclamo, retrabajo, flete o descuento por una pieza con la clase equivocada.")
    if up is not None:
        content, name = up.getvalue(), up.name
    elif ejemplo != "(ninguno)":
        content, name = _example("errores" if "errores" in ejemplo else "limpio"), "ejemplo.csv"
        st.caption("Ejemplo con datos reales: cada placa tiene una predicción hecha sin ver su etiqueta (validación cruzada o la "
                   "evaluación final del modelo congelado); 3 de cada 10 conservan su clase real, elegidas al azar por banda de confianza.")
    else:
        st.info("Para probar, elige el ejemplo de placas de acero o sube la plantilla.")
        return

    costos = rp.Costos(revision=float(c_rev), escape=float(c_esc))
    try:
        n_raw, df, issues, r = _run(content, name, costos)
    except ri.DataError as exc:
        st.error(str(exc))
        return
    errors = [i for i in issues if i.nivel == "error"]
    st.markdown(f"**{len(df):,} de {n_raw:,} piezas válidas** · {len(errors)} filas excluidas · {r['revisadas']:,} revisadas por "
                f"personas con {r['errores']} errores del sistema")
    if issues:
        with st.expander("Ver errores y avisos de los datos", expanded=bool(errors)):
            st.dataframe(pd.DataFrame([dict(Nivel=i.nivel, Fila=str(i.fila) if i.fila else "—", Detalle=i.mensaje) for i in issues]),
                         hide_index=True)
    p = r["politica"]
    n = r["piezas"]
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Piezas a revisión", f"{p['revisiones'] / n:.0%}", border=True)
    k2.metric("Escapes por 1,000 piezas", f"{1000 * p['escapes'] / n:.1f}", border=True)
    k3.metric("Ahorro vs revisar todo", _md(rr.mxn(p["ahorro_vs_todo"])), border=True)
    lo, hi = p["ahorro_vs_todo_ic"]
    k4.metric(f"Intervalo {costos.nivel:.0%} del ahorro", f"{lo / 1e3:+,.0f} a {hi / 1e3:+,.0f} mil", border=True)
    (st.success if lo > 0 else st.warning)(_md(rr.headline(r)))

    t = r["tabla"]
    st.markdown("**Política por clase**")
    st.dataframe(pd.DataFrame({"Clase del sistema": t["clase"], "Piezas": t["piezas"], "Revisadas": t["revisadas"],
                               "Tasa de error": t["tasa_error"], "Aceptar si confianza ≥": t["umbral"].where(t["umbral"] <= 1),
                               "A revisión": t["pct_revision"]})
                 .style.format({"Tasa de error": "{:.1%}", "Aceptar si confianza ≥": "{:.2f}", "A revisión": "{:.0%}"}, na_rep="nunca"),
                 hide_index=True)
    left, right = st.columns([3, 2])
    left.plotly_chart(_bands_fig(df, r), theme=None)
    g = r["global_unico"]
    right.markdown("**Comparación**")
    right.dataframe(pd.DataFrame({"Estrategia": ["Política por clase", "Un solo umbral", "Revisar todo", "No revisar nada"],
                                  "Revisiones": [p["revisiones"], g["revisiones"], n, 0],
                                  "Escapes": [p["escapes"], g["escapes"], 0.0, r["ninguna"]["escapes"]],
                                  "Costo": [p["costo"], g["costo"], r["todo"]["costo"], r["ninguna"]["costo"]]})
                    .style.format({"Escapes": "{:.1f}", "Costo": "${:,.0f}"}), hide_index=True)
    a_ = r["auditoria"]
    right.caption(f"Auditoría: revisa al azar {a_['n']} piezas aceptadas por periodo; {a_['alarma']} o más errores = alarma.")
    if r["sesgo_muestra"] > 3:
        st.caption(f"La muestra revisada no es uniforme (una banda de confianza se revisó {r['sesgo_muestra']:.1f} veces más que otra); "
                   "se corrige con pesos por banda.")

    lst = rp.review_list(df, r)
    d1, d2, d3 = st.columns(3)
    d1.download_button("Descargar reporte de una página (HTML)", rr.report_html(r, issues, linea, (n_raw, len(df))).encode("utf-8"),
                       "politica_revision.html", "text/html", type="primary")
    d2.download_button(f"Lista de piezas a revisar ({len(lst):,}, CSV)", ri.to_csv_bytes(lst), "piezas_a_revisar.csv", "text/csv")
    d3.download_button("Tabla para Power BI (CSV)", ri.to_csv_bytes(rp.bi_export(r)), "seguimiento_revision.csv", "text/csv")
