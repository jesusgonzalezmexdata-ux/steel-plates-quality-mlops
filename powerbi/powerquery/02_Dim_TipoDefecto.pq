// Dimensión de tipo de defecto con mapeo de terminología y costo unitario (SUPUESTO editable).
let
    Origen = #table(
        type table [id_tipo_defecto = Int64.Type, columna_origen = text, tipo_defecto = text, familia = text, costo_unitario_mxn = number],
        {
            {1, "Pastry",       "Pastelado (Pastry)",     "Superficie", 1800},
            {2, "Z_Scratch",    "Rayón en Z",             "Superficie",  900},
            {3, "K_Scatch",     "Rayón en K (K_Scatch)",  "Superficie", 1500},
            {4, "Stains",       "Manchas",                "Superficie",  400},
            {5, "Dirtiness",    "Suciedad",               "Superficie",  300},
            {6, "Bumps",        "Abolladuras (Bumps)",    "Forma",      1200},
            {7, "Other_Faults", "Otros defectos",         "Otros",      1000}
        })
in
    Origen
