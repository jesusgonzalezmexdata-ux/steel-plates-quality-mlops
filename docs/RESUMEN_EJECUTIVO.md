# Resumen ejecutivo

[English](EXECUTIVE_SUMMARY.md) · **Español**

**Pregunta.** Un área de calidad inspecciona placas de acero defectuosas y debe asignar a cada una un tipo de defecto (7 clases). ¿Puede hacerlo un modelo de forma fiable y qué casos debe seguir revisando una persona?

**Respuesta.** Sí, para placas ya medidas: en 389 placas que nunca se usaron para construir ni elegir el modelo, alcanza **macro-F1 0.815** (exactitud 0.789). Es fuerte en rayones, manchas y suciedad (F1 0.89–0.94) y más débil en Pastry, Abolladuras y Otros defectos (F1 0.60–0.75), que suele confundir entre sí.

## La decisión que habilita

| Política | Placas que revisa una persona | Errores que se escapan |
|---|---:|---:|
| Aceptar todas las predicciones | 0 | 82 de 389 (21 %) |
| **Revisar si la confianza es < 0.80** | **261 de 389 (67 %)** | **1 de 389** |
| Revisar todo | 389 de 389 | 0 |

*Cifras del holdout, aplicando a posteriori la política definida solo con datos de desarrollo.*

Qué política es la más barata depende de un solo número: **cuánto más cuesta un error no detectado que una revisión humana** (R). Con los datos de desarrollo y un revisor perfecto, la política de revisión con umbral 0.80 es la más barata de las tres cuando **3.1 < R < 53**. Por debajo de ese rango no compensa revisar; por encima, conviene revisar todo. Con un revisor imperfecto, el rango se desplaza a 3.4–59 (recall del 90 %) o 3.9–66 (recall del 80 %). La descripción con el holdout da un rango coherente (3.2–128). Ver [review_cost.json](../reports/ml/decision/review_cost.json) y `python -B -m tools.review_cost`.

**Lo que vale por cada 1,000 placas.** Costo en unidades de una revisión humana, datos de desarrollo, revisor perfecto. R es tu supuesto, no un costo medido:

| Política | R = 10 | R = 20 |
|---|---:|---:|
| Aceptar todas las predicciones | 2,294 | 4,588 |
| Revisar todo | 1,000 | 1,000 |
| **Revisar si la confianza < 0.80** | **750** | **808** |

Con R = 10 la política de revisión cuesta 25 % menos que revisar todo y 67 % menos que aceptar todas las predicciones. Lo reproduce `python -B -m tools.review_cost` (`per_1000_plates_review_units`).

**Cómo usarlo.** Estima R para tu planta (por ejemplo, el costo de una disposición errónea del defecto frente a unos minutos de un inspector). Si R cae dentro del rango, la política de revisión es un punto de partida razonable para un piloto.

## Lo que no afirma

- **No** predice si una placa tendrá defecto ni previene defectos: todas las placas de los datos ya son defectuosas.
- **No muestra costos ni ahorros reales**; la razón de costos es un supuesto que aportas tú.
- El umbral 0.80 es **solo de desarrollo** y no se ha validado de forma prospectiva. Se desconocen la precisión y el tiempo del revisor.
- La importancia de variables es asociativa, no causal. Dos clases (Manchas, Suciedad) tienen muy pocos casos.

## Por qué el resultado es confiable

- El modelo se eligió solo con validación cruzada y se evaluó **una vez** en un holdout independiente. Después no se ajustó nada.
- Cada cifra de este resumen se reproduce con tests en la CI desde un clon limpio, con Docker, un contrato de datos SQL y un ONNX verificado byte a byte.
- Detalle completo: [Model Card](../MODEL_CARD.md) y [Evidence pack](evidence/README.md).

**Monitoreo.** `python -B -m tools.drift_check` compara un lote de placas con las de entrenamiento (PSI y porcentaje fuera de rango por medición). El holdout pasa; un cambio de unidad en el espesor y una recalibración de luminosidad de +15 % generan alerta ([drift.json](../reports/ml/monitoring/drift.json)).

**Siguiente paso para un despliegue real:** un piloto breve con placas nuevas de la planta objetivo, midiendo la precisión y el tiempo del revisor, antes de fijar cualquier umbral.
