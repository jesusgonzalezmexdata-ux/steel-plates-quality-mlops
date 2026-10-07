# Pruebas de estrés y errores corregidos

Generado por `tools/stress_tests.py` (semilla 7, 2,000 repeticiones). Cada prueba intenta romper una conclusión del README.

## 1. ¿El Pareto depende de los costos supuestos?
Se variaron los 7 costos al azar ±30 %. El mismo trío (otros defectos, rayón en K, abolladuras) quedó arriba en **99.2%** de las simulaciones y su peso fue de 72% a 83% del COPQ (mediana 78%).
**Lo que no resiste:** el primer lugar. El rayón en K encabeza solo en 27% de los casos. La conclusión sólida es «tres tipos concentran el costo», no «el número uno es X».

## 2. ¿El semáforo del Cpk depende del límite supuesto?
| USL (px²) | Cpk global | Tipos en verde (de 7) |
|---|---|---|
| 200 | -0.08 | 1 |
| 500 | 0.09 | 1 |
| 1,000 | 0.21 | 1 |
| 2,000 | 0.34 | 1 |
| 5,000 | 0.51 | 2 |

Con USL = 500, el intervalo bootstrap al 95 % del Cpk global es 0.07 a 0.10. Aun con un límite diez veces mayor, el Cpk global sigue por debajo de 1.00: la conclusión «no capaz» es robusta al supuesto; el valor exacto no.

## 3. ¿Se cumple el supuesto de normalidad del Cpk?
**No.** Prueba de Shapiro-Wilk sobre log10 del área, por tipo de defecto:

| Tipo | Asimetría | Valor p |
|---|---|---|
| Abolladuras (Bumps) | 1.28 | < 0.001 |
| Manchas | 1.07 | < 0.001 |
| Otros defectos | 1.20 | < 0.001 |
| Pastelado (Pastry) | 1.01 | < 0.001 |
| Rayón en K (K_Scatch) | -1.82 | < 0.001 |
| Rayón en Z | 0.97 | < 0.001 |
| Suciedad | 0.30 | < 0.001 |

Todas rechazan la normalidad y el rayón en K es asimétrico a la izquierda. **Corrección:** el Cpk queda como referencia y la regla de decisión usa la fracción empírica de placas sobre el USL, que no supone ninguna distribución:

| Tipo | % de placas sobre 500 px² |
|---|---|
| Rayón en K (K_Scatch) | 87% |
| Suciedad | 31% |
| Rayón en Z | 23% |
| Pastelado (Pastry) | 19% |
| Otros defectos | 18% |
| Abolladuras (Bumps) | 9% |
| Manchas | 0% |

## 4. ¿La carta de medias mide el espesor o el tipo de defecto?
Grupos fuera de límites (n ≥ 5): con todos los datos **7 de 19**; sin rayón en K **4 de 19**; solo abolladuras **1 de 9**. La señal se reduce de 7 a 4 al quitar el rayón en K y a 1 dentro de abolladuras: gran parte de lo que parece efecto del espesor es el tipo de defecto. Por eso el README advierte la confusión.

## Errores que aparecieron y cómo se corrigieron
| Qué falló | Cómo se detectó | Corrección |
|---|---|---|
| El brief pedía % de scrap, `Dim_Tiempo`, `Dim_Maquina` y `Dim_Turno` | El dataset solo tiene placas defectuosas y ninguna de esas columnas | No se fabricaron. Esquema con las dimensiones reales y límites declarados en el README |
| Primera idea: carta de control en el orden de `id` | Al revisar el archivo, el `id` agrupa los 7 tipos en 7 bloques consecutivos | Se descartó la carta temporal. Se usa una carta entre grupos y se documenta que no es una serie de tiempo |
| Cpk presentado como criterio único | La prueba de normalidad (sección 3) la rechaza | La decisión se apoya en la fracción empírica sobre el USL |
| Líneas de límites en escalón en la primera versión de la carta | Revisión visual: parecían rangos continuos entre espesores | Líneas simples sobre eje categórico ordenado |
| La prueba automática de las medidas DAX falló | Su expresión regular no aceptaba nombres con punto (`Texto ISO 10.2`) | Expresión corregida; la prueba ahora exige que cada medida citada exista |
