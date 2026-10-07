"""Catálogo de defectos, supuestos de costo y especificación.

Los costos y el límite de especificación NO vienen del dataset: son supuestos
ilustrativos y editables. Reemplázalos con datos de planta.
"""
UMBRAL_CPK = 1.33          # estándar de la industria automotriz
USL_AREA_PX = 500          # tamaño máximo aceptable de un defecto (px²), supuesto
SIGMA_K = 3                # límites de control a ±3 sigmas

# columna original -> (nombre en español, familia, costo unitario MXN por placa afectada)
DEFECTOS = {
    "Pastry":       ("Pastelado (Pastry)",        "Superficie", 1800),
    "Z_Scratch":    ("Rayón en Z",                "Superficie", 900),
    "K_Scatch":     ("Rayón en K (K_Scatch)",     "Superficie", 1500),
    "Stains":       ("Manchas",                   "Superficie", 400),
    "Dirtiness":    ("Suciedad",                  "Superficie", 300),
    "Bumps":        ("Abolladuras (Bumps)",       "Forma",      1200),
    "Other_Faults": ("Otros defectos",            "Otros",      1000),
}
BANDAS_TAMANO = [  # (límite inferior incluido, etiqueta)
    (0, "1 · < 50 px²"), (50, "2 · 50–199 px²"), (200, "3 · 200–999 px²"),
    (1000, "4 · 1,000–4,999 px²"), (5000, "5 · ≥ 5,000 px²"),
]

# Umbrales de acción (supuestos de gestión; ajustar con la política de la planta)
UMBRAL_COPQ_PCT = 0.20     # un tipo con >= 20 % del COPQ abre análisis de causa raíz
UMBRAL_FUERA_USL_PCT = 0.10  # >= 10 % de placas con defecto mayor al USL activa contención
N_MIN_GRUPO = 30           # tamaño mínimo para tratar un grupo fuera de límites como señal
