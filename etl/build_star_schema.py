"""CSV público de UCI -> esquema estrella en data/model/*.csv (misma lógica que Power Query M)."""
from pathlib import Path

import numpy as np
import pandas as pd

from qbi.config import BANDAS_TAMANO, DEFECTOS

ROOT = Path(__file__).resolve().parents[1]


def load_raw(path: Path | None = None) -> pd.DataFrame:
    return pd.read_csv(path or ROOT / "data/raw/steel_plates_faults.csv")


def build(raw: pd.DataFrame) -> dict[str, pd.DataFrame]:
    cols = list(DEFECTOS)
    etiquetas = raw[cols]
    if not (etiquetas.sum(axis=1) == 1).all():
        raise ValueError("Cada placa debe tener exactamente un tipo de defecto")

    dim_tipo = pd.DataFrame([
        {"id_tipo_defecto": i + 1, "columna_origen": c, "tipo_defecto": v[0],
         "familia": v[1], "costo_unitario_mxn": v[2]}
        for i, (c, v) in enumerate(DEFECTOS.items())])

    raw = raw.assign(
        tipo_acero=np.where(raw["TypeOfSteel_A300"] == 1, "A300", "A400"),
        columna_origen=etiquetas.idxmax(axis=1))
    dim_acero = (raw[["tipo_acero", "Steel_Plate_Thickness"]].drop_duplicates()
                 .sort_values(["tipo_acero", "Steel_Plate_Thickness"], ignore_index=True)
                 .rename(columns={"Steel_Plate_Thickness": "espesor"}))
    dim_acero.insert(0, "id_acero", range(1, len(dim_acero) + 1))

    lim = [b[0] for b in BANDAS_TAMANO]
    dim_banda = pd.DataFrame({"id_banda_tamano": range(1, len(lim) + 1),
                              "banda_tamano": [b[1] for b in BANDAS_TAMANO], "limite_inferior_px2": lim})

    fact = (raw.merge(dim_tipo[["id_tipo_defecto", "columna_origen"]], on="columna_origen")
               .merge(dim_acero.rename(columns={"espesor": "Steel_Plate_Thickness"}),
                      on=["tipo_acero", "Steel_Plate_Thickness"]))
    fact["id_banda_tamano"] = np.searchsorted(lim, fact["Pixels_Areas"], side="right")
    fact = fact.sort_values("id", ignore_index=True).rename(columns={
        "id": "id_defecto", "Pixels_Areas": "area_px2", "LogOfAreas": "log_area",
        "X_Perimeter": "perimetro_x", "Y_Perimeter": "perimetro_y", "Sum_of_Luminosity": "luminosidad_suma",
        "Minimum_of_Luminosity": "luminosidad_min", "Maximum_of_Luminosity": "luminosidad_max",
        "Length_of_Conveyer": "longitud_transportador", "Edges_Index": "indice_bordes",
        "Empty_Index": "indice_vacio", "Luminosity_Index": "indice_luminosidad"})
    keep = ["id_defecto", "id_tipo_defecto", "id_acero", "id_banda_tamano", "area_px2", "log_area",
            "perimetro_x", "perimetro_y", "luminosidad_suma", "luminosidad_min", "luminosidad_max",
            "longitud_transportador", "indice_bordes", "indice_vacio", "indice_luminosidad"]
    return {"Fact_Defecto": fact[keep], "Dim_TipoDefecto": dim_tipo,
            "Dim_Acero": dim_acero, "Dim_BandaTamano": dim_banda}


def main() -> None:
    out = ROOT / "data/model"
    out.mkdir(parents=True, exist_ok=True)
    for name, df in build(load_raw()).items():
        df.to_csv(out / f"{name}.csv", index=False)
        print(f"{name}: {len(df):,} filas")


if __name__ == "__main__":
    main()
