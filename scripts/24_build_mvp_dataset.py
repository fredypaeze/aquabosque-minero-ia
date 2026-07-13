"""MVP: construcción del dataset integrado, priorización y modelo IA.

Integra ÚNICAMENTE resultados canónicos ya existentes en el repositorio
(territorio, minería MGN2025, calidad de agua Fase 4B.2, DTD 2025-IV, piloto
forestal Puerto Rico/Meta) — no descarga datos nuevos de minería, agua ni
bosque. Sí realiza UNA consulta acotada y ya validada al servicio DTD
(`fetch_all_dtd_attributes`, usada en las Fases 2D.2-2D.4) para agregar por
municipio el periodo 2025-IV, porque no existe todavía una tabla de
auditoría con esa agregación por `cod_mpio` guardada en disco.

No integra minería/agua a nivel de índice de riesgo ambiental ni afirma
causalidad. No clasifica legalmente calidad de agua. No detecta minería
ilegal. El modelo IsolationForest se presenta exclusivamente como detector
no supervisado de patrones territoriales atípicos.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
for p in (SRC_DIR, SCRIPTS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

mod20 = importlib.import_module("20_validate_forest_data_pilot")
mod21 = importlib.import_module("21_forest_dtd_and_colormap_robustness")

from aquabosque.features.dtd import PRECISION_COORDENADA, UMBRAL_APARICIONES_PLACEHOLDER  # noqa: E402
from aquabosque.utils.io import ensure_dir, write_json  # noqa: E402

DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
MVP_DIR = DATA_PROCESSED / "mvp"
MODELS_DIR = PROJECT_ROOT / "models"

TERRITORIO_PATH = DATA_PROCESSED / "territorio" / "universo_territorial_divipola.csv"
MINERIA_PATH = DATA_PROCESSED / "features" / "mineria_por_unidad_territorial_mgn2025.csv"
AGUA_UNIDAD_PATH = DATA_PROCESSED / "features" / "calidad_agua_por_unidad_territorial.csv"
AGUA_SITIO_PARAM_ANIO_PATH = DATA_PROCESSED / "integrated" / "calidad_agua_sitio_parametro_anio.csv"
CLASIFICACION_IDONEIDAD_PATH = DATA_PROCESSED / "reference" / "clasificacion_idoneidad_parametros_agua.csv"

MUNICIPIOS_PATH = MVP_DIR / "aquabosque_municipios_mvp.csv"
PRIORIZACION_PATH = MVP_DIR / "aquabosque_priorizacion_mvp.csv"
TOP20_PATH = MVP_DIR / "aquabosque_top20_mvp.csv"
DEMO_PATH = MVP_DIR / "municipios_demo.csv"
GEOJSON_SIMPLIFICADO_PATH = MVP_DIR / "municipios_mvp_simplificado.geojson"
MODEL_PATH = MODELS_DIR / "isolation_forest_mvp.joblib"

COD_PUERTO_RICO_META = "50590"

# Resultados reales ya validados en la Fase 2D.1/2D.2 (piloto WCS IDEAM,
# Puerto Rico/Meta) — NO se recalculan aquí, no se descarga de nuevo.
PILOTO_FORESTAL_PUERTO_RICO = {
    "cod_dane_mpio": COD_PUERTO_RICO_META,
    "bosque_2024_ha": 169209.70,
    "no_bosque_2024_ha": 171394.17,
    "pct_bosque_2024": round(169209.70 / (169209.70 + 171394.17) * 100, 2),
    "deforestacion_2023_2024_ha": 2972.71,
    "fuente_forestal": "IDEAM WCS Superficie_Bosque/Dinamica_Cambio_Cobertura_Bosque (piloto validado Fase 2D.1/2D.2)",
    "cobertura_forestal_disponible": True,
}


def _pct_rank(serie: pd.Series) -> pd.Series:
    """Percentil 0-100 (mayor valor -> percentil mayor), NaN se preserva."""
    return serie.rank(pct=True, na_option="keep") * 100.0


# ---------------------------------------------------------------------------
# 1. Universo (1.122 unidades DIVIPOLA vigentes)
# ---------------------------------------------------------------------------


def build_universo() -> pd.DataFrame:
    df = pd.read_csv(TERRITORIO_PATH, dtype={"cod_dane_mpio": str, "cod_dane_dpto": str})
    df = df[df["presente_divipola_vigente"] == True].copy()  # noqa: E712
    df["cod_dane_mpio"] = df["cod_dane_mpio"].str.zfill(5)
    df["cod_dane_dpto"] = df["cod_dane_dpto"].str.zfill(2)
    out = df[["cod_dane_mpio", "cod_dane_dpto", "nombre_mpio", "nombre_dpto", "tipo_unidad_territorial"]].copy()
    assert len(out) == 1122, f"universo esperado 1.122 filas, obtenido {len(out)}"
    assert out["cod_dane_mpio"].duplicated().sum() == 0, "códigos municipales duplicados en el universo"
    assert out["cod_dane_mpio"].isna().sum() == 0, "códigos municipales nulos en el universo"
    return out


# ---------------------------------------------------------------------------
# 2. Minería
# ---------------------------------------------------------------------------


def build_mineria(universo: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_csv(MINERIA_PATH, dtype={"cod_dane_mpio": str})
    df["cod_dane_mpio"] = df["cod_dane_mpio"].str.zfill(5)
    cols = [
        "cod_dane_mpio", "n_titulos_mineros", "tiene_titulos_mineros", "area_titulada_union_ha",
        "pct_area_unidad_titulada_union", "area_titulada_suma_ha", "anotaciones_total",
        "n_modalidades_distintas", "n_minerales_distintos",
    ]
    sub = df[cols].copy()
    merged = universo[["cod_dane_mpio"]].merge(sub, on="cod_dane_mpio", how="left")

    # score_presion_minera: combinación interpretable de percentiles — NUNCA
    # usa área SUMA (que duplica área por título superpuesto) como sustituto
    # del área UNIÓN (área real ocupada) para el componente de porcentaje.
    p_pct_area = _pct_rank(merged["pct_area_unidad_titulada_union"].fillna(0.0))
    p_n_titulos = _pct_rank(merged["n_titulos_mineros"].fillna(0.0))
    p_anotaciones = _pct_rank(merged["anotaciones_total"].fillna(0.0))
    merged["score_presion_minera"] = round(0.5 * p_pct_area + 0.3 * p_n_titulos + 0.2 * p_anotaciones, 2)
    merged["disponible_mineria"] = True  # el catastro minero cubre todo el universo; 0 títulos es un valor real, no ausente
    return merged


# ---------------------------------------------------------------------------
# 3. Señal hídrica estadística
# ---------------------------------------------------------------------------


def build_agua(universo: pd.DataFrame) -> pd.DataFrame:
    unidad = pd.read_csv(AGUA_UNIDAD_PATH, dtype={"cod_dane_mpio": str})
    unidad["cod_dane_mpio"] = unidad["cod_dane_mpio"].str.zfill(5)

    idoneidad = pd.read_csv(CLASIFICACION_IDONEIDAD_PATH)
    nivel_a = idoneidad[(idoneidad["nivel_idoneidad"] == "A") & (idoneidad["permite_indicador_numerico"])]
    combinaciones_aprobadas = set(zip(nivel_a["propiedad_observada_norm"], nivel_a["unidad_norm"]))

    sitio_param_anio = pd.read_csv(AGUA_SITIO_PARAM_ANIO_PATH, dtype={"cod_dane_mpio": str})
    sitio_param_anio["cod_dane_mpio"] = sitio_param_anio["cod_dane_mpio"].str.zfill(5)
    sitio_param_anio = sitio_param_anio[sitio_param_anio["n_resultados_numericos"] > 0].copy()
    sitio_param_anio["combo"] = list(zip(sitio_param_anio["propiedad_observada_norm"], sitio_param_anio["unidad_norm"]))
    sitio_param_anio = sitio_param_anio[sitio_param_anio["combo"].isin(combinaciones_aprobadas)]

    # Estadístico municipal por parámetro+unidad: mediana de las medianas
    # sitio-año (valores CUANTIFICADOS, nunca censurados), agrupado siempre
    # por parámetro+unidad (nunca mezclando unidades distintas del mismo
    # parámetro).
    municipio_parametro = (
        sitio_param_anio.groupby(["cod_dane_mpio", "propiedad_observada_norm", "unidad_norm"])["resultado_mediana"]
        .median()
        .reset_index()
        .rename(columns={"resultado_mediana": "valor_municipal"})
    )

    filas_anomalia = []
    for (propiedad, unidad_norm), grupo in municipio_parametro.groupby(["propiedad_observada_norm", "unidad_norm"]):
        if propiedad == "PH":
            distancia = (grupo["valor_municipal"] - 7.0).abs()
        else:
            mediana_nacional = grupo["valor_municipal"].median()
            mad = (grupo["valor_municipal"] - mediana_nacional).abs().median()
            mad_robusto = mad if mad > 0 else grupo["valor_municipal"].std(ddof=0) or 1.0
            distancia = (grupo["valor_municipal"] - mediana_nacional).abs() / mad_robusto
        percentil_anomalia = distancia.rank(pct=True) * 100.0
        for cod, pct in zip(grupo["cod_dane_mpio"], percentil_anomalia):
            filas_anomalia.append({"cod_dane_mpio": cod, "propiedad_observada_norm": propiedad, "anomalia_pct": pct})
    df_anomalia = pd.DataFrame(filas_anomalia)

    resumen = []
    for cod, grupo in df_anomalia.groupby("cod_dane_mpio"):
        top3 = grupo.sort_values("anomalia_pct", ascending=False).head(3)
        resumen.append({
            "cod_dane_mpio": cod,
            "score_senal_hidrica": round(top3["anomalia_pct"].mean(), 2),
            "n_parametros_hidricos_evaluables": int(grupo["propiedad_observada_norm"].nunique()),
            "principal_parametro_atipico": grupo.sort_values("anomalia_pct", ascending=False).iloc[0]["propiedad_observada_norm"],
        })
    df_resumen = pd.DataFrame(resumen)

    out = universo[["cod_dane_mpio"]].merge(df_resumen, on="cod_dane_mpio", how="left")
    out = out.merge(
        unidad[["cod_dane_mpio", "tiene_monitoreo_agua", "n_sitios_monitoreo", "anio_ultima_observacion", "monitoreo_desactualizado"]],
        on="cod_dane_mpio", how="left",
    )
    out["tiene_monitoreo_agua"] = out["tiene_monitoreo_agua"].fillna(False)
    out["n_sitios_monitoreo"] = out["n_sitios_monitoreo"].fillna(0).astype(int)
    out = out.rename(columns={"anio_ultima_observacion": "ultima_observacion_agua"})
    out["monitoreo_reciente"] = out["ultima_observacion_agua"].fillna(0) >= 2020
    out["brecha_monitoreo_agua"] = (~out["tiene_monitoreo_agua"].astype(bool)) | out["monitoreo_desactualizado"].fillna(True)
    out["disponible_agua"] = out["n_parametros_hidricos_evaluables"].fillna(0) > 0
    # La AUSENCIA de monitoreo no produce score cero: queda NaN, distinto de
    # "sin anomalía detectada" (que sí sería un score bajo real).
    out.loc[~out["disponible_agua"], "score_senal_hidrica"] = np.nan
    out = out.drop(columns=["monitoreo_desactualizado"])
    return out


# ---------------------------------------------------------------------------
# 4. DTD (2025-IV)
# ---------------------------------------------------------------------------


def fetch_dtd_periodo(anio: str, periodo: str) -> pd.DataFrame:
    """Consulta acotada (una sola vez) al servicio DTD ya usado en las Fases
    2D.1-2D.4, filtrando de una vez por `anio`/`periodo` en el `where` (no se
    trae el histórico completo)."""
    campos = "fid,cod_dtd,cod_mpio,nom_mpio,cod_depto,nucleo_tri,x,y"
    where = f"anio='{anio}' AND periodo='{periodo}'"
    filas = []
    offset = 0
    page_size = 2000
    while True:
        data, status = mod20.get_json(
            f"{mod20.DTD_URL}/query",
            {"where": where, "outFields": campos, "returnGeometry": "false", "resultOffset": offset, "resultRecordCount": page_size, "orderByFields": "fid", "f": "json"},
        )
        feats = (data or {}).get("features", [])
        if not feats:
            break
        filas.extend(f["attributes"] for f in feats)
        offset += len(feats)
        if len(feats) < page_size:
            break
    return pd.DataFrame(filas)


def build_dtd(universo: pd.DataFrame) -> pd.DataFrame:
    df = fetch_dtd_periodo("2025", "iv")
    df["cod_mpio"] = df["cod_mpio"].astype(str).str.zfill(5)
    df["nucleo_tri_norm"] = df["nucleo_tri"].astype(str).str.strip().replace({"": None, "nan": None})
    df["coord_redondeada"] = list(zip(df["x"].round(PRECISION_COORDENADA), df["y"].round(PRECISION_COORDENADA)))

    # Placeholder de `cod_dtd` (mismo criterio que la Fase 2D.2/2D.3: >10
    # apariciones DENTRO del periodo con más de una coordenada distinta).
    conteo_cod = df.groupby("cod_dtd")["cod_dtd"].transform("count")
    n_coords_por_cod = df.groupby("cod_dtd")["coord_redondeada"].transform("nunique")
    df["es_placeholder"] = (conteo_cod > UMBRAL_APARICIONES_PLACEHOLDER) & (n_coords_por_cod > 1)

    resumen = df.groupby("cod_mpio").agg(
        n_registros_dtd=("fid", "count"),
        n_coordenadas_dtd_unicas=("coord_redondeada", "nunique"),
        n_nucleos_dtd=("nucleo_tri_norm", "nunique"),
        n_registros_dtd_codigo_placeholder=("es_placeholder", "sum"),
    ).reset_index().rename(columns={"cod_mpio": "cod_dane_mpio"})

    out = universo[["cod_dane_mpio"]].merge(resumen, on="cod_dane_mpio", how="left")
    for c in ("n_registros_dtd", "n_coordenadas_dtd_unicas", "n_nucleos_dtd", "n_registros_dtd_codigo_placeholder"):
        out[c] = out[c].fillna(0).astype(int)
    out["tiene_dtd_reciente"] = out["n_registros_dtd"] > 0
    out["disponible_dtd"] = True  # 0 registros en 2025-IV es un valor real (ausencia de detección), no un dato faltante

    p_log_n = _pct_rank(np.log1p(out["n_registros_dtd"]))
    p_nucleos = _pct_rank(out["n_nucleos_dtd"])
    out["score_deteccion_temprana"] = round(0.7 * p_log_n + 0.3 * p_nucleos, 2)
    return out


# ---------------------------------------------------------------------------
# 5. Información forestal piloto (Puerto Rico, Meta)
# ---------------------------------------------------------------------------


def build_forest(universo: pd.DataFrame) -> pd.DataFrame:
    out = universo[["cod_dane_mpio"]].copy()
    for campo in ("bosque_2024_ha", "no_bosque_2024_ha", "pct_bosque_2024", "deforestacion_2023_2024_ha"):
        out[campo] = np.nan
    out["fuente_forestal"] = None
    out["cobertura_forestal_confirmada_mvp"] = False

    idx = out["cod_dane_mpio"] == COD_PUERTO_RICO_META
    for campo, valor in PILOTO_FORESTAL_PUERTO_RICO.items():
        if campo == "cod_dane_mpio":
            continue
        if campo == "cobertura_forestal_disponible":
            out.loc[idx, "cobertura_forestal_confirmada_mvp"] = valor
        else:
            out.loc[idx, campo] = valor
    return out


# ---------------------------------------------------------------------------
# 6. Cobertura + priorización de evidencia
# ---------------------------------------------------------------------------


def build_cobertura_y_prioridad(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["disponible_bosque_confirmado"] = out["cobertura_forestal_confirmada_mvp"]
    out["n_componentes_disponibles"] = (
        out["disponible_mineria"].astype(int) + out["disponible_agua"].astype(int)
        + out["disponible_dtd"].astype(int) + out["disponible_bosque_confirmado"].astype(int)
    )
    bins = [-1, 1, 2, 3, 4]
    labels = ["bajo", "medio", "alto", "completo"]
    out["nivel_disponibilidad_datos"] = pd.cut(out["n_componentes_disponibles"], bins=bins, labels=labels)
    out["score_brecha_informacion"] = round((4 - out["n_componentes_disponibles"]) / 4 * 100, 2)

    # Media ponderada renormalizada sobre componentes DISPONIBLES — nunca se
    # asigna 0 a un componente ausente (solo agua puede faltar; minería y DTD
    # siempre tienen un valor real, aunque sea 0).
    pesos_base = {"score_presion_minera": 0.40, "score_senal_hidrica": 0.35, "score_deteccion_temprana": 0.25}
    valores = out[list(pesos_base.keys())]
    disponibles = valores.notna()
    pesos_matriz = pd.DataFrame({c: disponibles[c] * w for c, w in pesos_base.items()})
    suma_pesos = pesos_matriz.sum(axis=1)
    numerador = (valores.fillna(0) * pesos_matriz).sum(axis=1)
    out["score_prioridad_evidencia"] = round(numerador / suma_pesos, 2)

    percentiles = _pct_rank(out["score_prioridad_evidencia"])
    condiciones = [percentiles >= 90, percentiles >= 75, percentiles >= 40]
    valores_nivel = ["Muy alta", "Alta", "Media"]
    out["nivel_prioridad"] = np.select(condiciones, valores_nivel, default="Baja")

    def _razones(row: pd.Series) -> str:
        partes = []
        if pd.notna(row["pct_area_unidad_titulada_union"]) and row["pct_area_unidad_titulada_union"] > 0:
            partes.append(f"{row['pct_area_unidad_titulada_union']:.1f}% del territorio titulado ({int(row['n_titulos_mineros'])} títulos mineros)")
        if pd.notna(row["score_senal_hidrica"]):
            partes.append(f"anomalía hídrica en {row['principal_parametro_atipico']} (percentil {row['score_senal_hidrica']:.0f})")
        elif not row["disponible_agua"]:
            partes.append("sin monitoreo hídrico evaluable")
        if row["n_registros_dtd"] > 0:
            partes.append(f"{int(row['n_registros_dtd'])} detecciones tempranas DTD en {int(row['n_nucleos_dtd'])} núcleo(s) (2025-IV)")
        if row["cobertura_forestal_confirmada_mvp"]:
            partes.append(f"deforestación confirmada {row['deforestacion_2023_2024_ha']:.0f} ha (2023-2024, piloto)")
        return "; ".join(partes) if partes else "sin señales destacadas en los componentes disponibles"

    def _advertencias(row: pd.Series) -> str:
        adv = []
        if not row["disponible_agua"]:
            adv.append("cobertura hídrica limitada o ausente")
        if not row["cobertura_forestal_confirmada_mvp"]:
            adv.append("sin cobertura forestal nacional confirmada en el MVP (no equivale a cero deforestación)")
        if row["n_componentes_disponibles"] <= 2:
            adv.append("cobertura de datos limitada — interpretar con cautela")
        return "; ".join(adv) if adv else "cobertura de datos completa para los componentes evaluados"

    out["principales_razones"] = out.apply(_razones, axis=1)
    out["advertencias_datos"] = out.apply(_advertencias, axis=1)
    out["resumen_explicativo"] = out.apply(
        lambda r: f"Prioridad {r['nivel_prioridad'].lower()} (percentil {percentiles.loc[r.name]:.0f}): {r['principales_razones']}.",
        axis=1,
    )
    return out


# ---------------------------------------------------------------------------
# Modelo IA: IsolationForest
# ---------------------------------------------------------------------------


def build_isolation_forest(df: pd.DataFrame) -> tuple[pd.DataFrame, IsolationForest]:
    variables = pd.DataFrame({
        "log1p_n_titulos_mineros": np.log1p(df["n_titulos_mineros"].fillna(0)),
        "pct_area_unidad_titulada_union": df["pct_area_unidad_titulada_union"].fillna(0),
        "score_senal_hidrica": df["score_senal_hidrica"],
        "log1p_n_registros_dtd": np.log1p(df["n_registros_dtd"].fillna(0)),
        "n_sitios_monitoreo": df["n_sitios_monitoreo"].fillna(0),
        "n_parametros_hidricos_evaluables": df["n_parametros_hidricos_evaluables"].fillna(0),
        "disponible_agua": df["disponible_agua"].astype(int),
        "disponible_bosque_confirmado": df["disponible_bosque_confirmado"].astype(int),
    })
    medianas_imputacion = variables.median(numeric_only=True)
    variables_imputadas = variables.fillna(medianas_imputacion)

    modelo = IsolationForest(random_state=42, contamination=0.10, n_estimators=200, n_jobs=-1)
    modelo.fit(variables_imputadas)

    anomaly_score_raw = -modelo.score_samples(variables_imputadas)  # mayor = mas atipico
    es_atipico = modelo.predict(variables_imputadas) == -1
    percentil_anomalia = pd.Series(anomaly_score_raw).rank(pct=True) * 100.0

    z = (variables_imputadas - variables_imputadas.mean()) / variables_imputadas.std(ddof=0).replace(0, 1)

    def _explicacion(i: int) -> str:
        fila_z = z.iloc[i].abs().sort_values(ascending=False)
        top2 = fila_z.index[:2]
        return "Perfil atípico por: " + "; ".join(f"{col} (z={z.iloc[i][col]:+.1f})" for col in top2)

    df = df.copy()
    df["anomaly_score_raw"] = anomaly_score_raw
    df["anomalia_ia_percentil"] = round(percentil_anomalia, 2)
    df["es_perfil_atipico"] = es_atipico
    df["explicacion_anomalia"] = [_explicacion(i) if es_atipico[i] else "Perfil dentro del rango esperado" for i in range(len(df))]
    return df, modelo


# ---------------------------------------------------------------------------
# Municipios demo
# ---------------------------------------------------------------------------


def select_demo_municipios(df: pd.DataFrame) -> pd.DataFrame:
    filas = []
    pr = df[df["cod_dane_mpio"] == COD_PUERTO_RICO_META].iloc[0]
    filas.append({
        "cod_dane_mpio": pr["cod_dane_mpio"], "nombre_mpio": pr["nombre_mpio"], "nombre_dpto": pr["nombre_dpto"],
        "razon_seleccion": "Obligatorio: único municipio con cobertura forestal nacional confirmada en el piloto (Fase 2D.1/2D.2) — deforestación 2023-2024 real y validada.",
    })

    candidatos_2 = df[
        (df["cod_dane_mpio"] != COD_PUERTO_RICO_META) & (df["disponible_agua"]) & (df["n_titulos_mineros"] > 0)
        & (df["nivel_prioridad"].isin(["Muy alta", "Alta"]))
    ].sort_values("score_prioridad_evidencia", ascending=False)
    m2 = candidatos_2.iloc[0]
    filas.append({
        "cod_dane_mpio": m2["cod_dane_mpio"], "nombre_mpio": m2["nombre_mpio"], "nombre_dpto": m2["nombre_dpto"],
        "razon_seleccion": f"Prioridad {m2['nivel_prioridad']} con cobertura minera y hídrica disponibles (score_prioridad_evidencia={m2['score_prioridad_evidencia']:.1f}).",
    })

    candidatos_3 = df[
        (~df["cod_dane_mpio"].isin([pr["cod_dane_mpio"], m2["cod_dane_mpio"]]))
        & (df["es_perfil_atipico"]) & (~df["disponible_agua"])
    ].sort_values("anomalia_ia_percentil", ascending=False)
    if candidatos_3.empty:
        candidatos_3 = df[~df["cod_dane_mpio"].isin([pr["cod_dane_mpio"], m2["cod_dane_mpio"]])].sort_values("anomalia_ia_percentil", ascending=False)
    m3 = candidatos_3.iloc[0]
    filas.append({
        "cod_dane_mpio": m3["cod_dane_mpio"], "nombre_mpio": m3["nombre_mpio"], "nombre_dpto": m3["nombre_dpto"],
        "razon_seleccion": f"Perfil atípico (percentil IA={m3['anomalia_ia_percentil']:.0f}) con cobertura de datos distinta al municipio 2 (agua disponible={bool(m3['disponible_agua'])}) — muestra un caso contrastante.",
    })
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# Geometría simplificada SOLO para visualización (nunca para análisis)
# ---------------------------------------------------------------------------


def build_geojson_simplificado(df: pd.DataFrame) -> dict[str, Any]:
    """Geometría simplificada (tolerancia ~0,01°, ≈1 km) para el mapa
    Streamlit — reduce el peso del GeoJSON sin modificar la geometría
    analítica canónica (`data/processed/territorio/...`), que nunca se toca."""
    from shapely.geometry import mapping, shape

    feats = mod20.load_mgn2025_geometries()
    columnas_mapa = df.set_index("cod_dane_mpio")[[
        "nombre_mpio", "nombre_dpto", "score_prioridad_evidencia", "nivel_prioridad",
        "anomalia_ia_percentil", "es_perfil_atipico", "score_presion_minera", "score_senal_hidrica",
        "n_registros_dtd", "disponible_agua", "cobertura_forestal_confirmada_mvp",
    ]]

    out_feats = []
    for f in feats:
        cod = f["properties"]["cod_dane_mpio"]
        if cod not in columnas_mapa.index:
            continue
        geom_simple = shape(f["geometry"]).simplify(0.01, preserve_topology=True)
        props = {"cod_dane_mpio": cod, **columnas_mapa.loc[cod].to_dict()}
        out_feats.append({"type": "Feature", "geometry": mapping(geom_simple), "properties": props})

    return {"type": "FeatureCollection", "features": out_feats}


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> int:
    print("MVP: construyendo dataset integrado, priorización y modelo IA")
    ensure_dir(MVP_DIR)
    ensure_dir(MODELS_DIR)

    universo = build_universo()
    print(f"  Universo: {len(universo)} unidades DIVIPOLA vigentes")

    mineria = build_mineria(universo)
    agua = build_agua(universo)
    dtd = build_dtd(universo)
    forest = build_forest(universo)

    df = universo.merge(mineria, on="cod_dane_mpio", how="left") \
        .merge(agua, on="cod_dane_mpio", how="left") \
        .merge(dtd, on="cod_dane_mpio", how="left") \
        .merge(forest, on="cod_dane_mpio", how="left")
    assert len(df) == 1122, f"dataset integrado esperado 1.122 filas, obtenido {len(df)}"

    df = build_cobertura_y_prioridad(df)
    df, modelo = build_isolation_forest(df)

    municipios_cols = [
        "cod_dane_mpio", "cod_dane_dpto", "nombre_mpio", "nombre_dpto", "tipo_unidad_territorial",
        "n_titulos_mineros", "tiene_titulos_mineros", "area_titulada_union_ha", "pct_area_unidad_titulada_union",
        "area_titulada_suma_ha", "anotaciones_total", "n_modalidades_distintas", "n_minerales_distintos", "score_presion_minera",
        "score_senal_hidrica", "n_parametros_hidricos_evaluables", "principal_parametro_atipico", "tiene_monitoreo_agua",
        "n_sitios_monitoreo", "ultima_observacion_agua", "monitoreo_reciente", "brecha_monitoreo_agua",
        "n_registros_dtd", "n_coordenadas_dtd_unicas", "n_nucleos_dtd", "n_registros_dtd_codigo_placeholder",
        "tiene_dtd_reciente", "score_deteccion_temprana",
        "bosque_2024_ha", "no_bosque_2024_ha", "pct_bosque_2024", "deforestacion_2023_2024_ha", "fuente_forestal",
        "cobertura_forestal_confirmada_mvp",
        "disponible_mineria", "disponible_agua", "disponible_dtd", "disponible_bosque_confirmado",
        "n_componentes_disponibles", "nivel_disponibilidad_datos", "score_brecha_informacion",
    ]
    df[municipios_cols].to_csv(MUNICIPIOS_PATH, index=False, encoding="utf-8")
    print(f"  {MUNICIPIOS_PATH.name}: {len(df)} filas")

    priorizacion_cols = [
        "cod_dane_mpio", "nombre_mpio", "nombre_dpto", "score_prioridad_evidencia", "nivel_prioridad",
        "score_brecha_informacion", "principales_razones", "advertencias_datos", "resumen_explicativo",
        "anomaly_score_raw", "anomalia_ia_percentil", "es_perfil_atipico", "explicacion_anomalia",
    ]
    df_prior = df[priorizacion_cols].sort_values("score_prioridad_evidencia", ascending=False).reset_index(drop=True)
    df_prior.to_csv(PRIORIZACION_PATH, index=False, encoding="utf-8")
    print(f"  {PRIORIZACION_PATH.name}: {len(df_prior)} filas")

    top20 = df_prior.head(20)
    top20.to_csv(TOP20_PATH, index=False, encoding="utf-8")
    print(f"  {TOP20_PATH.name}: {len(top20)} filas")

    demo = select_demo_municipios(df)
    demo.to_csv(DEMO_PATH, index=False, encoding="utf-8")
    print(f"  {DEMO_PATH.name}: {len(demo)} filas")

    joblib.dump(modelo, MODEL_PATH)
    print(f"  {MODEL_PATH}")

    geojson_simplificado = build_geojson_simplificado(df)
    write_json(GEOJSON_SIMPLIFICADO_PATH, geojson_simplificado)
    print(f"  {GEOJSON_SIMPLIFICADO_PATH.name}: {len(geojson_simplificado['features'])} features")

    for path, n_filas, desc in [
        (MUNICIPIOS_PATH, len(df), "Dataset integrado del MVP (minería, agua, DTD, bosque piloto) sobre las 1.122 unidades DIVIPOLA vigentes."),
        (PRIORIZACION_PATH, len(df_prior), "Priorización de evidencia + resultados IsolationForest, ordenado por score_prioridad_evidencia."),
        (TOP20_PATH, len(top20), "Top 20 municipios por score_prioridad_evidencia."),
        (DEMO_PATH, len(demo), "3 municipios seleccionados para la demo (Puerto Rico obligatorio + 2 contrastantes)."),
    ]:
        write_json(path.with_suffix(path.suffix + ".metadata.json"), {"fuente": "MVP - dataset integrado y priorizacion", "n_filas": n_filas, "descripcion": desc})

    print("\nResumen:")
    print(f"  n_componentes_disponibles distribución: {df['nivel_disponibilidad_datos'].value_counts().to_dict()}")
    print(f"  nivel_prioridad distribución: {df['nivel_prioridad'].value_counts().to_dict()}")
    print(f"  es_perfil_atipico: {int(df['es_perfil_atipico'].sum())}/{len(df)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
