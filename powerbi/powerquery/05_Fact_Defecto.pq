// Tabla de hechos: una fila por placa defectuosa. UNPIVOT de las 7 columnas indicadoras -> tipo de defecto.
let
    Fuente    = Raw_SteelPlates,
    Tipo      = Table.AddColumn(Fuente, "tipo_acero", each if [TypeOfSteel_A300] = 1 then "A300" else "A400", type text),
    Unpivot   = Table.UnpivotOtherColumns(Tipo, List.RemoveItems(Table.ColumnNames(Tipo),
                    {"Pastry","Z_Scratch","K_Scatch","Stains","Dirtiness","Bumps","Other_Faults"}), "columna_origen", "marca"),
    SoloUno   = Table.SelectRows(Unpivot, each [marca] = 1),
    ConTipo   = Table.NestedJoin(SoloUno, {"columna_origen"}, Dim_TipoDefecto, {"columna_origen"}, "t", JoinKind.Inner),
    IdTipo    = Table.ExpandTableColumn(ConTipo, "t", {"id_tipo_defecto"}),
    ConAcero  = Table.NestedJoin(IdTipo, {"tipo_acero", "Steel_Plate_Thickness"}, Dim_Acero, {"tipo_acero", "espesor"}, "a", JoinKind.Inner),
    IdAcero   = Table.ExpandTableColumn(ConAcero, "a", {"id_acero"}),
    Banda     = Table.AddColumn(IdAcero, "id_banda_tamano", each
                    if [Pixels_Areas] < 50 then 1 else if [Pixels_Areas] < 200 then 2
                    else if [Pixels_Areas] < 1000 then 3 else if [Pixels_Areas] < 5000 then 4 else 5, Int64.Type),
    Renombra  = Table.RenameColumns(Banda, {
                    {"id","id_defecto"}, {"Pixels_Areas","area_px2"}, {"LogOfAreas","log_area"},
                    {"X_Perimeter","perimetro_x"}, {"Y_Perimeter","perimetro_y"}, {"Sum_of_Luminosity","luminosidad_suma"},
                    {"Minimum_of_Luminosity","luminosidad_min"}, {"Maximum_of_Luminosity","luminosidad_max"},
                    {"Length_of_Conveyer","longitud_transportador"}, {"Edges_Index","indice_bordes"},
                    {"Empty_Index","indice_vacio"}, {"Luminosity_Index","indice_luminosidad"}}),
    Columnas  = Table.SelectColumns(Renombra, {"id_defecto","id_tipo_defecto","id_acero","id_banda_tamano","area_px2","log_area",
                    "perimetro_x","perimetro_y","luminosidad_suma","luminosidad_min","luminosidad_max",
                    "longitud_transportador","indice_bordes","indice_vacio","indice_luminosidad"}),
    Orden     = Table.Sort(Columnas, {{"id_defecto", Order.Ascending}})
in
    Orden
