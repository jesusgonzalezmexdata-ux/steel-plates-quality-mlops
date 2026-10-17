# MVP «Triaje de revisión humana»: protocolo de piloto

**Para quién:** ingeniero de calidad con inspección automática instalada: superficie de acero, vidrio, plástico o textil, o inspección óptica automática de tarjetas electrónicas (AOI).
**Qué decide:** desde qué confianza se acepta el resultado del sistema en cada clase y qué revisa una persona; cuánta carga de revisión esperar y cuántas piezas aceptadas auditar.
**Dónde se usa:** demo de este repositorio → modo «Triaje de revisión». El archivo se procesa en el navegador; no se envía a ningún servidor.

## 1. Datos

| Columna | Obligatoria | Contenido |
|---|---|---|
| clase_predicha | Sí | Clase o defecto que asignó el sistema |
| confianza | Sí | Confianza del sistema, de 0 a 1 o de 0 a 100 |
| clase_real | En la muestra | Clase confirmada por una persona; vacío si no se revisó |
| pieza, fecha | No | Identificador y fecha (para la carga por semana) |

**La muestra revisada debe elegirse al azar dentro de cada banda de confianza.** Puede revisarse más lo dudoso: los pesos por banda lo corrigen. Lo que no se corrige es elegir por otro criterio (por ejemplo, solo lo que alguien vio raro). Mínimo 100 piezas revisadas con 10 errores del sistema.

## 2. Cómo decide

1. **Pesos por banda:** cada pieza revisada representa a las piezas de su banda de confianza que no se revisaron.
2. **P(error | confianza, clase):** regresión logística ponderada, con pendiente común en la confianza y un ajuste por clase regularizado (las clases con pocas piezas revisadas se acercan al promedio).
3. **Umbral por clase:** se acepta donde P(error) × costo de un escape < costo de una revisión.
4. **Estimación honesta:** los escapes se cuentan con piezas que la política ajustada sin ellas habría aceptado (validación cruzada en 5 partes), con intervalo de Jeffreys; con cero errores observados la cota superior no es cero.
5. **Auditoría:** revisar al azar *n* piezas aceptadas por periodo; *n* es el tamaño con el que cero errores demuestran que la tasa está bajo la cota de hoy, y hay un número de errores que dispara la alarma.

**Ejemplo con datos reales (UCI, 1,941 placas, 30 % revisado):** con revisión de 40 MXN y escape de 1,500 MXN, la política manda a revisión el 79 % y estima 1.6 escapes (intervalo 0 a 8.2). La verdad oculta del ejemplo da 5 escapes reales, dentro del intervalo. Con escape de 5,000 MXN el intervalo del ahorro incluye pérdida y el reporte lo dice.

## 3. Fases

| Fase | Duración | Actividad | Entregable |
|---|---|---|---|
| 0 · Acuerdo | 1 semana | Exportación de resultados del sistema con confianza; diseño de la muestra estratificada | Plan de muestreo |
| 1 · Revisión | 2–4 semanas | Personas revisan la muestra sin ver la confianza; se captura la clase real | Muestra en la plantilla |
| 2 · Política | 2 días | Umbrales, carga de revisión y auditoría; revisión con el dueño del proceso | Reporte de una página |
| 3 · Operación vigilada | 4 semanas | Se aplica la política y se audita lo aceptado cada semana | Escapes medidos contra la alarma |

## 4. Criterios definidos antes de empezar

**Éxito:** misma tasa de escapes con menos revisiones (la auditoría de la fase 3 no dispara la alarma).
**Abandono:** el sistema automático no entrega confianza por resultado, o la muestra no puede elegirse al azar por banda.

## 5. Seguimiento en Power BI

El modo descarga `seguimiento_revision.csv` (una fila por clase y fecha de corte). Las medidas están en `powerbi/dax/revision_humana.dax`. La página en Power BI Desktop está pendiente: no se puede validar sin Desktop.
