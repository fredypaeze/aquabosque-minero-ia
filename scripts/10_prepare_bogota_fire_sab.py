"""Integra fuego estructural y lluvia SAB al Zoom Bogota.

Parte de `data/processed/bogota_zoom.csv` y sustituye:

- `score_fuego_estructural` con una capa real derivada de area afectada por
  evento forestal historico (Bomberos Bogota, 2009-2025)
- `score_operativo` con lluvia operacional actual del SAB / IDIGER

La salida sobreescribe `data/processed/bogota_zoom.csv`.
"""

from __future__ import annotations

import json
import math
import unicodedata
from pathlib import Path
from urllib.request import urlopen

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
IN_CSV = ROOT / "data" / "processed" / "bogota_zoom.csv"
URL_FIRE = (
    "https://serviciosgis.catastrobogota.gov.co/arcgis/services/emergencias/bomberos/"
    "MapServer/WFSServer?service=WFS&version=2.0.0&request=GetFeature&"
    "typeNames=bomberos:Area_Afectada_Evento_Forestal&outputFormat=geojson"
)
URL_SAB = "https://app.sab.gov.co//sab/ServletTipoSensores?idtiposensor=5"


def normalize_name(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")
    return " ".join(text.lower().split())


def download_json(url: str) -> dict:
    with urlopen(url, timeout=180) as resp:
        return json.load(resp)


def score_series(values: pd.Series) -> pd.Series:
    logged = values.fillna(0).astype(float).map(lambda x: math.log1p(max(x, 0.0)))
    lo = float(logged.min())
    hi = float(logged.max())
    if hi - lo < 1e-12:
        return pd.Series([0.0] * len(logged), index=values.index)
    return (logged - lo) / (hi - lo)


def classify_level(score: float) -> str:
    if score >= 0.67:
        return "Crítico"
    if score >= 0.56:
        return "Alto"
    if score >= 0.43:
        return "Medio"
    return "Bajo"


def build_fire() -> pd.DataFrame:
    rows: list[dict] = []
    data = download_json(URL_FIRE)
    for feat in data["features"]:
        props = feat["properties"]
        rows.append(
            {
                "localidad_norm": normalize_name(props.get("Localidad", "")),
                "fire_area_proxy": float(props.get("Area_Afectada") or 0.0),
                "fire_feature_count": 1,
                "fire_hist_event_count": 1,
            }
        )
    fire_df = pd.DataFrame(rows)
    if fire_df.empty:
        return pd.DataFrame(columns=["localidad_norm"])
    return fire_df.groupby("localidad_norm", as_index=False).agg(
        fire_area_proxy=("fire_area_proxy", "sum"),
        fire_feature_count=("fire_feature_count", "sum"),
        fire_hist_event_count=("fire_hist_event_count", "sum"),
    )


def build_sab() -> pd.DataFrame:
    data = download_json(URL_SAB)["TipoSensores"]
    rows = []
    for item in data:
        if int(item.get("VISIBLE") or 0) != 1:
            continue
        rows.append(
            {
                "localidad_norm": normalize_name(item.get("LOCALIDAD", "")),
                "sab_acumulado_dia_mm": float(item.get("ACUMULADODIA") or 0.0),
                "sab_valor_lectura_mm": float(item.get("VALORLECTURA") or 0.0),
                "sab_estacion": item.get("ESTACION", ""),
                "sab_fecha_lectura": item.get("FECHALECTURA", ""),
            }
        )
    sab_df = pd.DataFrame(rows)
    if sab_df.empty:
        return pd.DataFrame(columns=["localidad_norm"])
    agg = sab_df.groupby("localidad_norm", as_index=False).agg(
        sab_lluvia_max_mm=("sab_acumulado_dia_mm", "max"),
        sab_lluvia_mean_mm=("sab_acumulado_dia_mm", "mean"),
        sab_lectura_max_mm=("sab_valor_lectura_mm", "max"),
        sab_estaciones_activas=("sab_estacion", "count"),
        sab_ultima_lectura=("sab_fecha_lectura", "max"),
    )
    return agg


def main() -> None:
    base = pd.read_csv(IN_CSV, dtype={"codigo": str})
    base["localidad_norm"] = base["localidad"].map(normalize_name)
    fire = build_fire()
    sab = build_sab()

    df = base.merge(fire, on="localidad_norm", how="left").merge(sab, on="localidad_norm", how="left")
    for col in [
        "fire_area_proxy",
        "fire_feature_count",
        "fire_hist_event_count",
        "sab_lluvia_max_mm",
        "sab_lluvia_mean_mm",
        "sab_lectura_max_mm",
        "sab_estaciones_activas",
    ]:
        df[col] = df[col].fillna(0.0)
    df["sab_ultima_lectura"] = df["sab_ultima_lectura"].fillna("")

    df["score_fuego_demo"] = df["score_fuego_estructural"]
    df["score_operativo_demo"] = df["score_operativo"]

    df["score_fuego_real"] = (
        0.55 * score_series(df["fire_area_proxy"])
        + 0.30 * score_series(df["fire_feature_count"])
        + 0.15 * score_series(df["fire_hist_event_count"])
    ).round(3)

    df["score_operativo_real"] = (
        0.60 * score_series(df["sab_lluvia_max_mm"])
        + 0.25 * score_series(df["sab_lluvia_mean_mm"])
        + 0.15 * score_series(df["sab_estaciones_activas"])
    ).round(3)

    df["score_fuego_estructural"] = df["score_fuego_real"]
    df["score_operativo"] = df["score_operativo_real"]
    df["indice_bogota_base"] = (
        0.35 * df["score_fuego_estructural"]
        + 0.30 * df["score_agua"]
        + 0.35 * df["score_remocion"]
    ).round(3)
    df["indice_bogota_dinamico"] = df["score_operativo"].round(3)
    df["indice_presion_ecoterritorial_bogota"] = (
        0.65 * df["indice_bogota_base"] + 0.35 * df["indice_bogota_dinamico"]
    ).round(3)
    df["nivel"] = df["indice_presion_ecoterritorial_bogota"].map(classify_level)

    df["fuente_fuego_real"] = "Bomberos Bogota: Area afectada por evento forestal 2009-2025"
    df["fuente_operativa_real"] = "SAB IDIGER: pluviometros visibles idtiposensor=5"
    df = df.drop(columns=["localidad_norm"])
    df = df.sort_values("indice_presion_ecoterritorial_bogota", ascending=False)
    df.to_csv(IN_CSV, index=False)

    print(f"Actualice {IN_CSV}")
    print(
        df[
            [
                "localidad",
                "score_fuego_estructural",
                "score_agua",
                "score_operativo",
                "indice_presion_ecoterritorial_bogota",
                "nivel",
            ]
        ].head(10).to_string(index=False)
    )


if __name__ == "__main__":
    main()
