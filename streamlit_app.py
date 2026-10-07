"""Inteligencia de manufactura sobre UCI Steel Plates. Misma lógica que las medidas DAX (qbi/measures.py)."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from qbi import measures as M
from qbi.config import UMBRAL_COPQ_PCT, UMBRAL_CPK, UMBRAL_FUERA_USL_PCT, USL_AREA_PX

AZUL, GRIS, ROJO, VERDE, AMBAR = "#0B5394", "#8A94A3", "#C62828", "#2E7D32", "#F9A825"
COLOR = {"verde": VERDE, "amarillo": AMBAR, "rojo": ROJO}

st.set_page_config(page_title="Inteligencia de manufactura · Placas de acero", layout="wide")


@st.cache_data
def datos() -> pd.DataFrame:
    return M.flat(M.load_model())


base = datos()
st.title("Defectos en placas de acero: costo, control y capacidad")
st.caption("Datos reales: UCI Steel Plates Faults (1,941 placas defectuosas). Costos y especificación: supuestos editables.")

with st.sidebar:
    st.header("Filtros")
    familias = st.multiselect("Familia de defecto", sorted(base.familia.unique()), default=sorted(base.familia.unique()))
    aceros = st.multiselect("Tipo de acero", ["A300", "A400"], default=["A300", "A400"])
    st.header("Supuestos")
    usl = st.slider("Tamaño máximo aceptable de un defecto (px²)", 50, 5000, USL_AREA_PX, step=50)
    st.caption("Costo por placa afectada (MXN)")
    costos = {}
    for _, r in base[["tipo_defecto", "costo_unitario_mxn"]].drop_duplicates().sort_values("tipo_defecto").iterrows():
        costos[r.tipo_defecto] = st.number_input(r.tipo_defecto, 0, 20000, int(r.costo_unitario_mxn), step=100)

df = base[base.familia.isin(familias) & base.tipo_acero.isin(aceros)].copy()
df["costo_unitario_mxn"] = df.tipo_defecto.map(costos)
if df.empty:
    st.warning("Sin datos con esos filtros.")
    st.stop()

p = M.pareto(df)
cpk_global = M.cpu(df.log_area, usl)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Placas defectuosas", f"{len(df):,}")
c2.metric("COPQ (supuesto)", f"{p.copq_mxn.sum() / 1e6:.2f} M MXN")
c3.metric("Defectos ≥ 5,000 px²", f"{(df.area_px2 >= 5000).mean():.1%}")
c4.metric("Cpk del tamaño de defecto", f"{cpk_global:.2f}", help=f"Verde ≥ {UMBRAL_CPK}; amarillo ≥ 1.00")
st.markdown(f"<div style='border-left:6px solid {COLOR[M.semaforo(cpk_global)]};padding:6px 12px;background:#F1F4F8'>"
            f"<b>ISO 9001:2015 · 10.2</b> No conformidad y acción correctiva: prioridad de causa raíz → "
            f"<b>{p.tipo_defecto.iloc[0]}</b> ({p.copq_mxn.iloc[0] / p.copq_mxn.sum():.0%} del COPQ).</div>", unsafe_allow_html=True)

t0, t1, t2, t3, t4, t5 = st.tabs(["Decisiones", "Pareto del COPQ", "Carta de medias", "Capacidad", "Explorar un defecto", "Modelo y límites"])

with t0:
    st.write(f"Qué hacer con cada tipo de defecto. Umbrales (supuestos de gestión): contención si ≥ {UMBRAL_FUERA_USL_PCT:.0%} de las placas "
             f"supera {usl} px²; causa raíz si el tipo pesa ≥ {UMBRAL_COPQ_PCT:.0%} del COPQ. Las cláusulas son de ISO 9001:2015.")
    dec = M.decisiones(df, usl)
    st.dataframe(dec.rename(columns={"tipo_defecto": "Tipo de defecto", "placas": "Placas", "copq_pct": "% del COPQ",
                                     "fuera_usl_pct": f"% mayor a {usl} px²", "cpk": "Cpk", "accion": "Acción recomendada"})
                 .style.format({"% del COPQ": "{:.0%}", f"% mayor a {usl} px²": "{:.0%}", "Cpk": "{:.2f}"}), hide_index=True,
                 use_container_width=True)
    st.caption("El Cpk supone distribución normal y aquí no se cumple (ver docs/pruebas_de_estres.md); por eso la decisión se apoya "
               "en la fracción empírica sobre el USL y el Cpk queda como referencia.")

with t1:
    fig = go.Figure()
    fig.add_bar(x=p.tipo_defecto, y=p.copq_mxn, marker_color=AZUL, name="COPQ (MXN)")
    fig.add_scatter(x=p.tipo_defecto, y=p.copq_acum_pct, yaxis="y2", mode="lines+markers", line=dict(color=ROJO), name="% acumulado")
    fig.update_layout(yaxis=dict(title="MXN"), yaxis2=dict(overlaying="y", side="right", range=[0, 1], tickformat=".0%", tickvals=[0, .25, .5, .75, 1]),
                      legend=dict(orientation="h", y=1.12), margin=dict(t=30), height=420)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(p.rename(columns={"tipo_defecto": "Tipo de defecto", "defectos": "Placas", "copq_mxn": "COPQ (MXN)",
                                   "copq_acum_pct": "COPQ acumulado", "defectos_pct": "% de placas"})
                 .style.format({"COPQ (MXN)": "{:,.0f}", "COPQ acumulado": "{:.1%}", "% de placas": "{:.1%}"}), hide_index=True)

with t2:
    st.write("Media del tamaño del defecto (log10 del área) por espesor, con límites **μ ± 3·s/√n** del conjunto filtrado. "
             "Es una comparación **entre grupos** (como un análisis de medias); el dataset no tiene fecha, "
             "así que **no es una carta en el tiempo**. Grupos con n < 5 se muestran sin evaluar.")
    c = M.carta_medias(df, "espesor").sort_values("espesor")
    c["x"] = c.espesor.astype(str)
    fig = go.Figure()
    fig.add_scatter(x=c.x, y=c.ucl, mode="lines", line=dict(color=GRIS, dash="dash"), name="UCL")
    fig.add_scatter(x=c.x, y=c.lcl, mode="lines", line=dict(color=GRIS, dash="dash"), name="LCL")
    fig.add_scatter(x=c.x, y=c.lc, mode="lines", line=dict(color=GRIS), name="Línea central")
    estado = np.where(~c.n_suficiente, GRIS, np.where(c.fuera, ROJO, AZUL))
    fig.add_scatter(x=c.x, y=c.media, mode="markers", marker=dict(color=estado, size=np.clip(np.sqrt(c.n) * 2.2, 7, 26)),
                    customdata=c.n, hovertemplate="Espesor %{x}<br>media %{y:.2f}<br>n=%{customdata}<extra></extra>", name="Media del grupo")
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=c.x.tolist())
    fig.update_layout(xaxis_title="Espesor de la placa", yaxis_title="Media de log10(área px²)", height=420,
                      legend=dict(orientation="h", y=1.12), margin=dict(t=30))
    st.plotly_chart(fig, use_container_width=True)
    n_f = int((c.fuera & c.n_suficiente).sum())
    st.info(f"{n_f} de {int(c.n_suficiente.sum())} grupos quedan fuera de límites. "
            "Cuidado al leerlo: el espesor 40 concentra el 99 % del rayón en K, que es el defecto más grande; "
            "tipo de defecto y espesor están mezclados.")

with t3:
    por = st.radio("Calcular por", ["tipo_defecto", "tipo_acero"], horizontal=True,
                   format_func=lambda x: "Tipo de defecto" if x == "tipo_defecto" else "Tipo de acero")
    cap = M.capacidad(df, por, usl).sort_values("cpu")
    cap["semaforo"] = cap["cpu"].map(M.semaforo)
    fig = go.Figure(go.Bar(x=cap.cpu, y=cap[por], orientation="h", marker_color=[COLOR[s] for s in cap.semaforo],
                           text=cap.cpu.round(2), textposition="outside"))
    fig.add_vline(x=UMBRAL_CPK, line_dash="dash", line_color=VERDE, annotation_text="1.33")
    fig.add_vline(x=1.0, line_dash="dot", line_color=AMBAR, annotation_text="1.00")
    fig.update_layout(height=380, xaxis_title=f"Cpk unilateral (tamaño ≤ {usl} px²)", margin=dict(t=20))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Cpk = (log10 USL − media) / (3·s) sobre log10 del área. El USL es un supuesto: con un valor distinto de la planta cambia el semáforo. "
               "Un Cpk negativo significa que la media del defecto ya supera el límite.")

with t4:
    tipo = st.selectbox("Tipo de defecto", sorted(df.tipo_defecto.unique()))
    s = df[df.tipo_defecto == tipo]
    a, b, c_ = st.columns(3)
    a.metric("Placas", f"{len(s):,}")
    b.metric("COPQ", f"{s.costo_unitario_mxn.sum():,.0f} MXN")
    c_.metric("Área mediana", f"{s.area_px2.median():,.0f} px²")
    ca, cb = st.columns(2)
    h = go.Figure(go.Histogram(x=s.log_area, marker_color=AZUL, nbinsx=30))
    h.add_vline(x=np.log10(usl), line_color=ROJO, line_dash="dash", annotation_text="USL")
    h.update_layout(title="Tamaño (log10 px²)", height=320, margin=dict(t=40))
    ca.plotly_chart(h, use_container_width=True)
    e = s.groupby(["tipo_acero", "espesor"]).size().reset_index(name="placas").sort_values("placas", ascending=False).head(8)
    e["acero y espesor"] = e.tipo_acero + " · " + e.espesor.astype(str)
    cb.plotly_chart(go.Figure(go.Bar(x=e.placas, y=e["acero y espesor"], orientation="h", marker_color=AZUL))
                    .update_layout(title="Acero y espesor más afectados", height=320, margin=dict(t=40),
                                   yaxis=dict(autorange="reversed")), use_container_width=True)

with t5:
    st.markdown("""
**Esquema estrella** (`Fact_Defecto` rodeada de `Dim_TipoDefecto`, `Dim_Acero`, `Dim_BandaTamano`).

**Qué sí y qué no tiene este dataset**
- Sí: 1,941 placas **con defecto**, un solo tipo por placa, tamaño, perímetros, luminosidad, tipo de acero y espesor.
- No: placas buenas (no hay % de scrap), fechas, máquinas, turnos ni costos.
- Por eso: el COPQ usa costos **supuestos**, la carta compara **grupos** (no el tiempo) y el Cpk usa un límite **supuesto**.
- El archivo viene ordenado por tipo de defecto; el `id` no es una secuencia de producción.
""")
    st.dataframe(base.head(20), hide_index=True)
