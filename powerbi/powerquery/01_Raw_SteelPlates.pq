// Consulta base (deshabilitar "Habilitar carga"): lee el CSV una sola vez y tipifica.
// RutaCSV admite tanto una URL HTTPS como una ruta local de Windows.
let
    Ruta     = Text.Trim(RutaCSV),
    Binario  = if Text.StartsWith(Text.Lower(Ruta), "http://") or Text.StartsWith(Text.Lower(Ruta), "https://")
               then Web.Contents(Ruta)
               else File.Contents(Ruta),
    Origen   = Csv.Document(Binario, [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Cabecera = Table.PromoteHeaders(Origen, [PromoteAllScalars = true]),
    Tipos    = Table.TransformColumnTypes(Cabecera, List.Transform(Table.ColumnNames(Cabecera), each {_, type number}))
in
    Tipos
