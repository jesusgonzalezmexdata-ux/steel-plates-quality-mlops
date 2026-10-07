"""Pruebas de estrés de las conclusiones. Genera docs/pruebas_de_estres.md (semilla fija, reproducible)."""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from qbi import measures as M

ROOT = Path(__file__).resolve().parents[1]


def correr(n: int = 2000, seed: int = 7) -> dict:
    d = M.flat(M.load_model())
    rng = np.random.default_rng(seed)
    cuenta = d.groupby("tipo_defecto").size()
    c0 = d.groupby("tipo_defecto").costo_unitario_mxn.first()
    top0 = set((cuenta * c0).nlargest(3).index)
    mismo, lider_k, share = 0, 0, []
    for _ in range(n):
        t = (cuenta * (c0 * rng.uniform(0.7, 1.3, len(c0)))).sort_values(ascending=False)
        mismo += set(t.index[:3]) == top0
        lider_k += t.index[0] == "Rayón en K (K_Scatch)"
        share.append(t.iloc[:3].sum() / t.sum())
    boot = [M.cpu(pd.Series(rng.choice(d.log_area.values, len(d))), 500) for _ in range(n)]
    usl = {u: (M.cpu(d.log_area, u), int((M.capacidad(d, "tipo_defecto", u).semaforo == "verde").sum()))
           for u in (200, 500, 1000, 2000, 5000)}
    sw = {t: (stats.skew(g), stats.shapiro(g).pvalue) for t, g in d.groupby("tipo_defecto").log_area}
    sin_k = M.carta_medias(d[d.columna_origen != "K_Scatch"], "espesor")
    todo = M.carta_medias(d, "espesor")
    bumps = M.carta_medias(d[d.tipo_defecto == "Abolladuras (Bumps)"], "espesor")
    f = lambda c: (int((c.fuera & c.n_suficiente).sum()), int(c.n_suficiente.sum()))
    return {"top3_estable": mismo / n, "k_lidera": lider_k / n, "share_top3": np.percentile(share, [2.5, 50, 97.5]),
            "cpk_ic": np.percentile(boot, [2.5, 97.5]), "usl": usl, "normalidad": sw,
            "carta": {"todos": f(todo), "sin_rayon_k": f(sin_k), "solo_abolladuras": f(bumps)},
            "fuera_usl": d.groupby("tipo_defecto").apply(M.fuera_usl, include_groups=False).to_dict()}


def main() -> None:
    r = correr()
    L = ["# Pruebas de estrés y errores corregidos", "",
         "Generado por `tools/stress_tests.py` (semilla 7, 2,000 repeticiones). Cada prueba intenta romper una conclusión del README.", "",
         "## 1. ¿El Pareto depende de los costos supuestos?",
         f"Se variaron los 7 costos al azar ±30 %. El mismo trío (otros defectos, rayón en K, abolladuras) quedó arriba en **{r['top3_estable']:.1%}** de las simulaciones "
         f"y su peso fue de {r['share_top3'][0]:.0%} a {r['share_top3'][2]:.0%} del COPQ (mediana {r['share_top3'][1]:.0%}).",
         f"**Lo que no resiste:** el primer lugar. El rayón en K encabeza solo en {r['k_lidera']:.0%} de los casos. La conclusión sólida es «tres tipos concentran el costo», no «el número uno es X».", "",
         "## 2. ¿El semáforo del Cpk depende del límite supuesto?",
         "| USL (px²) | Cpk global | Tipos en verde (de 7) |", "|---|---|---|"]
    L += [f"| {u:,} | {c:.2f} | {v} |" for u, (c, v) in r["usl"].items()]
    L += ["", f"Con USL = 500, el intervalo bootstrap al 95 % del Cpk global es {r['cpk_ic'][0]:.2f} a {r['cpk_ic'][1]:.2f}. "
          "Aun con un límite diez veces mayor, el Cpk global sigue por debajo de 1.00: la conclusión «no capaz» es robusta al supuesto; el valor exacto no.", "",
          "## 3. ¿Se cumple el supuesto de normalidad del Cpk?",
          "**No.** Prueba de Shapiro-Wilk sobre log10 del área, por tipo de defecto:", "",
          "| Tipo | Asimetría | Valor p |", "|---|---|---|"]
    L += [f"| {t} | {s:.2f} | {'< 0.001' if p < 0.001 else f'{p:.3f}'} |" for t, (s, p) in r["normalidad"].items()]
    L += ["", "Todas rechazan la normalidad y el rayón en K es asimétrico a la izquierda. **Corrección:** el Cpk queda como referencia y la regla de decisión usa la fracción empírica de placas sobre el USL, que no supone ninguna distribución:", "",
          "| Tipo | % de placas sobre 500 px² |", "|---|---|"]
    L += [f"| {t} | {v:.0%} |" for t, v in sorted(r["fuera_usl"].items(), key=lambda x: -x[1])]
    c = r["carta"]
    L += ["", "## 4. ¿La carta de medias mide el espesor o el tipo de defecto?",
          f"Grupos fuera de límites (n ≥ 5): con todos los datos **{c['todos'][0]} de {c['todos'][1]}**; sin rayón en K **{c['sin_rayon_k'][0]} de {c['sin_rayon_k'][1]}**; "
          f"solo abolladuras **{c['solo_abolladuras'][0]} de {c['solo_abolladuras'][1]}**. "
          "La señal se reduce de 7 a 4 al quitar el rayón en K y a 1 dentro de abolladuras: gran parte de lo que parece efecto del espesor es el tipo de defecto. Por eso el README advierte la confusión.", "",
          "## Errores que aparecieron y cómo se corrigieron",
          "| Qué falló | Cómo se detectó | Corrección |", "|---|---|---|",
          "| El brief pedía % de scrap, `Dim_Tiempo`, `Dim_Maquina` y `Dim_Turno` | El dataset solo tiene placas defectuosas y ninguna de esas columnas | No se fabricaron. Esquema con las dimensiones reales y límites declarados en el README |",
          "| Primera idea: carta de control en el orden de `id` | Al revisar el archivo, el `id` agrupa los 7 tipos en 7 bloques consecutivos | Se descartó la carta temporal. Se usa una carta entre grupos y se documenta que no es una serie de tiempo |",
          "| Cpk presentado como criterio único | La prueba de normalidad (sección 3) la rechaza | La decisión se apoya en la fracción empírica sobre el USL |",
          "| Líneas de límites en escalón en la primera versión de la carta | Revisión visual: parecían rangos continuos entre espesores | Líneas simples sobre eje categórico ordenado |",
          "| La prueba automática de las medidas DAX falló | Su expresión regular no aceptaba nombres con punto (`Texto ISO 10.2`) | Expresión corregida; la prueba ahora exige que cada medida citada exista |"]
    (ROOT / "docs/pruebas_de_estres.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("docs/pruebas_de_estres.md")


if __name__ == "__main__":
    main()
