// Dimensión de acero: combinaciones únicas de tipo de acero y espesor.
let
    Fuente   = Raw_SteelPlates,
    Tipo     = Table.AddColumn(Fuente, "tipo_acero", each if [TypeOfSteel_A300] = 1 then "A300" else "A400", type text),
    Reducida = Table.SelectColumns(Tipo, {"tipo_acero", "Steel_Plate_Thickness"}),
    Unicos   = Table.Distinct(Reducida),
    Renombra = Table.RenameColumns(Unicos, {{"Steel_Plate_Thickness", "espesor"}}),
    Orden    = Table.Sort(Renombra, {{"tipo_acero", Order.Ascending}, {"espesor", Order.Ascending}}),
    Id       = Table.AddIndexColumn(Orden, "id_acero", 1, 1, Int64.Type),
    Final    = Table.ReorderColumns(Id, {"id_acero", "tipo_acero", "espesor"})
in
    Final
