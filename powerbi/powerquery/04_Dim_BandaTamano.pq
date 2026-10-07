let
    Origen = #table(
        type table [id_banda_tamano = Int64.Type, banda_tamano = text, limite_inferior_px2 = number],
        {
            {1, "1 · < 50 px²",           0},
            {2, "2 · 50–199 px²",        50},
            {3, "3 · 200–999 px²",      200},
            {4, "4 · 1,000–4,999 px²", 1000},
            {5, "5 · ≥ 5,000 px²",     5000}
        })
in
    Origen
