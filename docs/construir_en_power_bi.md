# Cierre del entregable Power BI

Este documento define cómo convertir los activos ya versionados del repositorio en una **evidencia completa y verificable de Power BI**.

## Estado actual

El repositorio ya contiene:

- consultas Power Query M;
- modelo estrella definido;
- medidas DAX;
- tema visual;
- valores de control calculados de forma independiente en Python/SQL;
- pruebas automatizadas sobre la lógica analítica.

Lo que **todavía no debe afirmarse** hasta completar esta guía es que el informe fue ejecutado y validado en Power BI Desktop. El criterio de cierre no es "tener archivos DAX/M": es abrir, refrescar, calcular, visualizar y comprobar el modelo dentro de Power BI.

## Definition of Done

Power BI queda cerrado cuando se cumplan **todos** estos gates:

| Gate | Criterio | Evidencia mínima |
|---|---|---|
| G0 | Power BI Desktop abre el proyecto sin errores | captura de versión + archivo local |
| G1 | Power Query carga todas las tablas | 0 errores de consulta |
| G2 | Modelo y relaciones coinciden con el diseño | vista Modelo |
| G3 | Todas las medidas DAX compilan | 0 errores DAX |
| G4 | Las páginas y visuales responden a filtros | informe navegable |
| G5 | KPIs coinciden con valores esperados | checklist firmado |
| G6 | Informe guardado como PBIP y PBIX | ambos artefactos locales |
| G7 | Evidencia visual y/o demo publicada | capturas o enlace |
| G8 | README actualizado de "pendiente" a "validado" | commit final |

---

## G0 — Preparar Power BI Desktop

1. Usa Power BI Desktop actualizado en Windows.
2. Clona este repositorio.
3. Mantén intacto el CSV original en:
   `data/raw/steel_plates_faults.csv`
4. Decide el origen:
   - **recomendado para portafolio reproducible:** URL RAW de GitHub;
   - **alternativa local:** ruta absoluta al CSV.

La consulta `RutaCSV` acepta ambas opciones.

---

## G1 — Construir Power Query

En Power BI Desktop:

`Transformar datos > Nueva fuente > Consulta en blanco > Editor avanzado`

Crea las consultas en este orden y con **estos nombres exactos**:

1. `RutaCSV` ← `powerbi/powerquery/00_Parametros.pq`
2. `Raw_SteelPlates` ← `01_Raw_SteelPlates.pq`
3. `Dim_TipoDefecto` ← `02_Dim_TipoDefecto.pq`
4. `Dim_Acero` ← `03_Dim_Acero.pq`
5. `Dim_BandaTamano` ← `04_Dim_BandaTamano.pq`
6. `Fact_Defecto` ← `05_Fact_Defecto.pq`
7. `Param_Especificacion` ← `06_Param_Especificacion.pq`

Para `Raw_SteelPlates`, desactiva **Habilitar carga**.

### Control G1

Antes de continuar:

- `Fact_Defecto`: **1,941 filas**.
- Cada fila debe tener un único `id_tipo_defecto`.
- No debe haber errores en Power Query.
- `Param_Especificacion` debe tener una fila con `USL_px2 = 500`.

Si alguno falla, **no continúes**.

---

## G2 — Modelo semántico

Crea relaciones 1:* con filtro en una sola dirección:

- `Dim_TipoDefecto[id_tipo_defecto]` → `Fact_Defecto[id_tipo_defecto]`
- `Dim_Acero[id_acero]` → `Fact_Defecto[id_acero]`
- `Dim_BandaTamano[id_banda_tamano]` → `Fact_Defecto[id_banda_tamano]`

`Param_Especificacion` queda **desconectada** deliberadamente.

Oculta en la vista de informe:

- IDs técnicos del hecho;
- columnas que no aporten directamente al análisis.

### Control G2

La vista Modelo debe verse como una estrella: dimensiones → hecho, sin relaciones bidireccionales y sin ciclos.

---

## G3 — Medidas DAX

Crea una tabla vacía llamada `_Medidas` y pega, una por una, las medidas de:

`powerbi/dax/measures.dax`

No avances si una medida queda con error.

Medidas críticas para control:

- `Defectos`
- `COPQ MXN`
- `Defectos Grandes`
- `Cpk`
- `% Fuera de USL`
- `COPQ Acumulado %`
- `Accion Recomendada`
- `Texto ISO 10.2`

---

## G4 — Páginas del informe

### Página 1 — Resumen ejecutivo

Fila superior:

- Tarjeta: `Defectos`
- Tarjeta: `COPQ MXN`
- Tarjeta: `Defectos Grandes`
- Tarjeta: `Cpk`

Visual central:

- Pareto por `Dim_TipoDefecto[tipo_defecto]`
- columnas: `COPQ MXN`
- línea: `COPQ Acumulado %`

Visual de decisión:

- tabla por tipo de defecto;
- `Defectos`;
- `COPQ % del Total`;
- `% Fuera de USL`;
- `Cpk`;
- `Accion Recomendada`.

Tarjeta de texto:

- `Texto ISO 10.2`

### Página 2 — Control y capacidad

Carta de medias por:

- eje: `Dim_Acero[espesor]`
- valores: `Media Log Area`, `Linea Central`, `UCL`, `LCL`.

Añade una tabla auxiliar con:

- espesor;
- `n Grupo`;
- `Fuera de Limites`.

Incluye Cpk por tipo de defecto o tipo de acero con formato condicional usando `Semaforo Cpk Color`.

### Página 3 — Exploración

Incluye:

- segmentador de tipo de defecto;
- segmentador de acero;
- segmentador de espesor;
- distribución por `Dim_BandaTamano[banda_tamano]`;
- área del defecto y variables descriptivas pertinentes.

### Tooltip

Página oculta de tipo Tooltip:

- `Defectos`;
- `COPQ MXN`;
- distribución por banda de tamaño.

Actívala sobre el Pareto.

---

## G5 — Validación contra referencia independiente

Sin filtros y con `USL = 500 px²`:

| Control | Valor esperado |
|---|---:|
| Defectos | **1,941** |
| COPQ | **2,242,600 MXN** |
| Defectos ≥ 5,000 px² | **289** |
| Cpk global | **≈ 0.09** |
| Top 1 Pareto COPQ | **Otros defectos** |
| Top 2 Pareto COPQ | **Rayón en K** |
| Top 3 Pareto COPQ | **Abolladuras** |

Acepta una diferencia de redondeo en Cpk, no una diferencia estructural.

Además comprueba manualmente:

- al filtrar un tipo de defecto cambian tarjetas, Pareto y decisión;
- al cambiar el USL cambia `% Fuera de USL`, Cpk y la acción;
- el Pareto acumulado termina en 100 %;
- no existe una visual temporal que trate `id_defecto` como fecha/secuencia de producción.

Si Power BI no coincide con estos valores, el gate queda **FAIL** hasta explicar la diferencia.

---

## G6 — Guardado y versionado

Guarda dos artefactos locales:

1. `steel-plates-quality-bi.pbix` — artefacto ejecutable para abrir en Power BI Desktop.
2. proyecto `.pbip` — fuente textual versionable.

### Regla de repositorio

- **PBIP:** sí debe versionarse.
- **PBIX:** no es obligatorio versionarlo; al ser binario, puede mantenerse como artefacto local o adjuntarse a una Release si su tamaño y licencia lo permiten.

No afirmar "Power BI validado" únicamente por existir un PBIX. Debe haber pasado G1–G5.

---

## G7 — Evidencia pública

Capturas mínimas:

1. resumen ejecutivo;
2. modelo semántico;
3. control/capacidad;
4. interacción o filtro aplicado.

Guárdalas en:

`docs/img/powerbi/`

Si publicas en Power BI Service, agrega el enlace al campo **Homepage** del repositorio y al README.

No publiques datos privados. Este proyecto usa UCI, pero cualquier publicación debe seguir las condiciones del dataset y de Microsoft Power BI.

---

## G8 — Cambio de estado en README

Solo después de G0–G7 sustituye la limitación actual por una declaración equivalente a:

> **Power BI validado.** El modelo, Power Query y las medidas DAX fueron ejecutados en Power BI Desktop y contrastados contra la referencia independiente de Python/SQL. El proyecto PBIP está versionado; el PBIX se conserva como artefacto de ejecución.

Hasta entonces debe permanecer explícitamente como **pendiente de validación en Power BI Desktop**.

---

## Qué demuestra el cierre

Al completar estos gates, el repositorio deja de demostrar solamente:

> diseño de una solución compatible con Power BI

y pasa a demostrar:

> construcción, ejecución, validación y documentación de una solución Power BI reproducible.

Ese es el estándar necesario para usar este repositorio como evidencia fuerte de Power BI en GitHub o LinkedIn.
