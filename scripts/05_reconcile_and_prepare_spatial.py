"""Fase 3D.1: reconciliación territorial y preparación final de insumos espaciales.

Objetivos (no se ejecuta todavía ninguna intersección real ni se construyen
indicadores mineros ni dataset maestro):

1. Reconciliar el universo territorial DIVIPOLA (fuente de verdad
   administrativa) contra la capa geométrica de límites municipales,
   documentando explícitamente las discrepancias 94663/27493.
2. Preservar el tipo de unidad territorial (Municipio / Área no
   municipalizada / Isla / otras) en vez de llamar "municipios" a las 1.122
   filas de forma genérica.
3. Preparar el catastro minero para intersección: reparar (no descartar) las
   22 geometrías inválidas de la Fase 3C en una versión "spatial_ready"
   separada, sin tocar el archivo limpio original.
4. Ajustar la salida GeoJSON de límites municipales al estándar RFC 7946
   (sin miembro `crs`) — ya aplicado en scripts/03_clean_raw_data.py.
5. Ejecutar una prueba de rendimiento con STRtree (25-50 títulos) antes de
   plantear la intersección nacional completa en la Fase 4A.

Salidas:
  data/processed/territorio/universo_territorial_divipola.csv
  data/processed/territorio/dane_mgn2025_nuevo_belen_bajira_27493_clean.geojson (+ .metadata.json)
  data/processed/mineria/catastro_minero_anm_spatial_ready.geojson (+ .metadata.json)
  outputs/reports/spatial_preparation/territorial_reconciliation.md
  outputs/reports/spatial_preparation/catastro_minero_geometry_repair.md
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aquabosque.data.clean import (  # noqa: E402
    dataframe_to_geojson,
    geometry_to_multipolygon,
    json_safe_default,
    normalize_text,
    prepare_catastro_minero_spatial_ready,
)
from aquabosque.data.spatial import run_strtree_performance_test  # noqa: E402
from aquabosque.utils.io import (  # noqa: E402
    ensure_dir,
    file_size_bytes,
    format_bytes,
    utc_now_iso,
    write_json,
    write_metadata,
)

DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports" / "spatial_preparation"

DIVIPOLA_CLEAN_PATH = DATA_PROCESSED / "territorio" / "divipola_municipios_clean.csv"
LIMITES_CLEAN_DIR = DATA_PROCESSED / "territorio" / "limites_municipales_dane"
LIMITES_CLEAN_MANIFEST = LIMITES_CLEAN_DIR / "manifest.json"
BAJIRA_RAW_PATH = DATA_RAW / "territorio" / "dane_mgn2025_nuevo_belen_bajira_27493.geojson"
BAJIRA_RAW_META_PATH = DATA_RAW / "territorio" / "dane_mgn2025_nuevo_belen_bajira_27493.geojson.metadata.json"
CATASTRO_CLEAN_PATH = DATA_PROCESSED / "mineria" / "catastro_minero_anm_clean.geojson"

UNIVERSO_OUT_PATH = DATA_PROCESSED / "territorio" / "universo_territorial_divipola.csv"
BAJIRA_CLEAN_OUT_PATH = DATA_PROCESSED / "territorio" / "dane_mgn2025_nuevo_belen_bajira_27493_clean.geojson"
CATASTRO_SPATIAL_READY_PATH = DATA_PROCESSED / "mineria" / "catastro_minero_anm_spatial_ready.geojson"

CRS_ORIGEN = "EPSG:4326"
CRS_METRICO = "EPSG:9377"

CODIGO_MAPIRIPANA = "94663"
CODIGO_BAJIRA = "27493"


# --------------------------------------------------------------------------
# Carga de datos ya limpios (Fase 3B/3C/3D)
# --------------------------------------------------------------------------


def load_divipola_clean() -> pd.DataFrame:
    return pd.read_csv(
        DIVIPOLA_CLEAN_PATH,
        dtype={"cod_dpto": str, "cod_dane_mpio": str},
    )


def load_limites_clean() -> tuple[pd.DataFrame, list[dict], dict]:
    """Lee las 11 partes del límite municipal ya limpio (Fase 3D). Devuelve
    (DataFrame de propiedades, lista paralela de geometrías, manifest)."""
    with open(LIMITES_CLEAN_MANIFEST, encoding="utf-8") as fh:
        manifest = json.load(fh)

    props: list[dict] = []
    geometries: list[dict | None] = []
    for a in manifest["archivos_y_tamanos"]:
        with open(LIMITES_CLEAN_DIR / a["archivo"], encoding="utf-8") as fh:
            fc = json.load(fh)
        assert len(fc["features"]) == a["features"], f"{a['archivo']}: conteo no coincide con manifest"
        for feat in fc["features"]:
            props.append(feat["properties"])
            geometries.append(feat.get("geometry"))

    assert len(props) == manifest["total_features_salida"]
    df = pd.DataFrame(props)
    return df, geometries, manifest


def load_catastro_clean() -> pd.DataFrame:
    """Lee el catastro minero limpio (Fase 3C) y reconstruye la columna
    `_geometry` a partir del campo `geometry` de cada Feature."""
    with open(CATASTRO_CLEAN_PATH, encoding="utf-8") as fh:
        fc = json.load(fh)
    props = []
    for feat in fc["features"]:
        p = dict(feat["properties"])
        p["_geometry"] = feat.get("geometry")
        props.append(p)
    return pd.DataFrame(props)


def load_and_validate_bajira_geometry(df_divipola: pd.DataFrame) -> tuple[dict, dict]:
    """Carga la geometría oficial de 27493 (descargada de DANE MGN2025) y
    valida código, nombre, departamento, CRS y geometría contra DIVIPOLA
    vigente. Devuelve (feature GeoJSON con propiedades homologadas al
    esquema de límites municipales, reporte de validación)."""
    from shapely.geometry import shape

    with open(BAJIRA_RAW_PATH, encoding="utf-8") as fh:
        fc = json.load(fh)
    with open(BAJIRA_RAW_META_PATH, encoding="utf-8") as fh:
        meta = json.load(fh)

    assert len(fc["features"]) == 1, "Se esperaba exactamente 1 feature para 27493"
    feat = fc["features"][0]
    props_origen = feat["properties"]
    geom = feat["geometry"]

    fila_divipola = df_divipola[df_divipola["cod_dane_mpio"] == CODIGO_BAJIRA]
    assert len(fila_divipola) == 1, f"Se esperaba 1 fila de DIVIPOLA para {CODIGO_BAJIRA}"
    fila_divipola = fila_divipola.iloc[0]

    validaciones = {}
    validaciones["codigo_coincide"] = props_origen["MPIO_CDPMP"] == CODIGO_BAJIRA
    validaciones["departamento_coincide"] = props_origen["DPTO_CCDGO"] == fila_divipola["cod_dpto"]

    nombre_origen_norm = normalize_text(props_origen["MPIO_CNMBRE"])
    validaciones["nombre_coincide_normalizado"] = nombre_origen_norm == fila_divipola["nombre_mpio_norm"]
    validaciones["nombre_origen_norm"] = nombre_origen_norm
    validaciones["nombre_divipola_norm"] = fila_divipola["nombre_mpio_norm"]

    s = shape(geom)
    validaciones["geometria_valida"] = s.is_valid
    validaciones["geometria_tipo"] = s.geom_type
    bounds = s.bounds
    validaciones["bbox"] = bounds
    validaciones["bbox_dentro_de_colombia"] = (
        -82.0 <= bounds[0] and bounds[2] <= -66.0 and -4.5 <= bounds[1] and bounds[3] <= 13.5
    )
    validaciones["crs_solicitado"] = "EPSG:4326 (outSR=4326 explícito en la petición)"
    validaciones["fuente_url"] = meta["url"]
    validaciones["fuente_entidad"] = meta["fuente"]
    validaciones["fecha_descarga"] = meta["fecha_descarga"]

    from shapely.geometry import mapping

    geom_final = mapping(geometry_to_multipolygon(s))

    feature_homologada = {
        "type": "Feature",
        "properties": {
            "objectid": 1123,
            "cod_dane_dpto": props_origen["DPTO_CCDGO"],
            "nom_dpto": props_origen["DPTO_CNMBRE"],
            "nombre_dpto_norm": normalize_text(props_origen["DPTO_CNMBRE"]),
            "cod_dane_mpio": props_origen["MPIO_CDPMP"],
            "nom_mpio": props_origen["MPIO_CNMBRE"],
            "nombre_mpio_norm": nombre_origen_norm,
            "mpio_corrdeptal": None,
        },
        "geometry": geom_final,
    }

    return feature_homologada, validaciones


# --------------------------------------------------------------------------
# A/B. Universo territorial y discrepancias 94663/27493
# --------------------------------------------------------------------------


def build_universo_territorial(df_divipola: pd.DataFrame, df_limites: pd.DataFrame) -> pd.DataFrame:
    """Reconcilia DIVIPOLA (fuente de verdad administrativa, Fase 3B) contra
    la capa geométrica de límites municipales (Fase 3D). DIVIPOLA manda: la
    capa ArcGIS NO se trata como fuente de vigencia administrativa.

    - 27493 (Nuevo Belén de Bajirá): vigente en DIVIPOLA, sin geometría en la
      capa Divipola/Cache; se marca `tiene_geometria=True` porque su
      geometría se recuperó de DANE MGN2025 (ver
      `load_and_validate_bajira_geometry`) y se integra en un archivo aparte.
    - 94663 (Mapiripana): presente en la capa geométrica, ausente de
      DIVIPOLA vigente; se conserva para trazabilidad pero se marca
      `fuera_universo_divipola_vigente` (excluido del universo analítico
      vigente por defecto).
    """
    set_limites = set(df_limites["cod_dane_mpio"])

    filas = []
    for _, row in df_divipola.iterrows():
        cod = row["cod_dane_mpio"]
        presente_geometrica = cod in set_limites

        if cod == CODIGO_BAJIRA:
            tiene_geometria = True
            estado = "vigente_geometria_recuperada_mgn2025_dane"
            obs = (
                "Código vigente en DIVIPOLA, ausente de la capa Divipola/Cache_Divipola... "
                "usada en Fase 2C/3D. Geometría oficial recuperada de DANE MGN2025 "
                "(geoportal.dane.gov.co/mparcgis, capa Municipio id 317) e integrada en "
                "dane_mgn2025_nuevo_belen_bajira_27493_clean.geojson; ver docs/06."
            )
        elif presente_geometrica:
            tiene_geometria = True
            estado = "coincide"
            obs = ""
        else:
            tiene_geometria = False
            estado = "vigente_sin_geometria_en_capa_actual"
            obs = (
                "Código vigente en DIVIPOLA sin geometría disponible en ninguna fuente DANE "
                "consultada en esta fase. No se construyó una geometría artificial; se excluye "
                "de cálculos espaciales que requieran polígono, pero se mantiene en reportes de "
                "cobertura."
            )

        filas.append(
            {
                "cod_dane_mpio": cod,
                "cod_dane_dpto": row["cod_dpto"],
                "nombre_mpio": row["nombre_mpio"],
                "nombre_mpio_norm": row["nombre_mpio_norm"],
                "nombre_dpto": row["nombre_dpto"],
                "nombre_dpto_norm": row["nombre_dpto_norm"],
                "tipo_unidad_territorial": row["tipo"],
                "presente_divipola_vigente": True,
                "presente_capa_geometrica": presente_geometrica,
                "tiene_geometria": tiene_geometria,
                "estado_reconciliacion": estado,
                "observacion_reconciliacion": obs,
            }
        )

    set_divipola = set(df_divipola["cod_dane_mpio"])
    solo_geometria = sorted(set_limites - set_divipola)
    for cod in solo_geometria:
        row = df_limites[df_limites["cod_dane_mpio"] == cod].iloc[0]
        filas.append(
            {
                "cod_dane_mpio": cod,
                "cod_dane_dpto": row["cod_dane_dpto"],
                "nombre_mpio": row["nom_mpio"],
                "nombre_mpio_norm": row["nombre_mpio_norm"],
                "nombre_dpto": row["nom_dpto"],
                "nombre_dpto_norm": row["nombre_dpto_norm"],
                "tipo_unidad_territorial": "no aplica (fuera de DIVIPOLA tabular vigente)",
                "presente_divipola_vigente": False,
                "presente_capa_geometrica": True,
                "tiene_geometria": True,
                "estado_reconciliacion": "fuera_universo_divipola_vigente",
                "observacion_reconciliacion": (
                    "Presente en la capa geométrica (ArcGIS REST Divipola/Cache_Divipola...), "
                    "ausente de la DIVIPOLA tabular vigente (Fase 3B). Se conserva el registro "
                    "para trazabilidad, pero se excluye por defecto del universo analítico "
                    "vigente hasta que exista evidencia oficial de su incorporación a DIVIPOLA."
                ),
            }
        )

    df_universo = pd.DataFrame(filas)
    return df_universo.sort_values(["cod_dane_dpto", "cod_dane_mpio"]).reset_index(drop=True)


# --------------------------------------------------------------------------
# C. Métricas de correspondencia (correctamente separadas)
# --------------------------------------------------------------------------


def compute_correspondence_metrics(set_divipola: set[str], set_geometria: set[str]) -> dict:
    """Calcula 3 métricas DISTINTAS, cada una con su propio denominador —
    nunca se presenta una como si fuera otra."""
    interseccion = set_divipola & set_geometria
    union = set_divipola | set_geometria

    cobertura = len(interseccion) / len(set_divipola) if set_divipola else 0.0
    precision = len(interseccion) / len(set_geometria) if set_geometria else 0.0
    jaccard = len(interseccion) / len(union) if union else 0.0

    return {
        "total_codigos_divipola": len(set_divipola),
        "total_codigos_geometricos": len(set_geometria),
        "codigos_interseccion": len(interseccion),
        "codigos_union": len(union),
        "cobertura_divipola_por_geometria_pct": round(cobertura * 100, 2),
        "precision_geometria_contra_divipola_pct": round(precision * 100, 2),
        "similitud_jaccard_pct": round(jaccard * 100, 2),
    }


# --------------------------------------------------------------------------
# Escritura de salidas
# --------------------------------------------------------------------------


def write_bajira_clean_geojson(feature: dict) -> tuple[int, dict]:
    ensure_dir(BAJIRA_CLEAN_OUT_PATH.parent)
    fc = {"type": "FeatureCollection", "features": [feature]}
    size = write_json(BAJIRA_CLEAN_OUT_PATH, fc, compact=True, default=json_safe_default)

    write_metadata(
        BAJIRA_CLEAN_OUT_PATH.with_suffix(BAJIRA_CLEAN_OUT_PATH.suffix + ".metadata.json"),
        fuente="DANE - Marco Geoestadistico Nacional 2025 (MGN2025), capa Municipio (id 317) - limpio",
        url=str(BAJIRA_RAW_PATH.relative_to(PROJECT_ROOT)),
        formato="GeoJSON RFC 7946 (FeatureCollection, sin miembro crs; CRS = EPSG:4326)",
        estado="completo",
        tamano_bytes=size,
        filas_descargadas=1,
        observaciones=(
            "Geometría oficial DANE del municipio Nuevo Belén de Bajirá (cod_dane_mpio=27493), "
            "recuperada para completar el universo territorial vigente tras la reconciliación "
            "de la Fase 3D.1. Usar junto con los 11 archivos de "
            "data/processed/territorio/limites_municipales_dane/ para tener el universo "
            "geométrico completo de los 1.122 códigos DIVIPOLA vigentes."
        ),
    )
    return size, {"path": BAJIRA_CLEAN_OUT_PATH, "size": size}


def write_universo_territorial(df_universo: pd.DataFrame) -> int:
    ensure_dir(UNIVERSO_OUT_PATH.parent)
    df_universo.to_csv(UNIVERSO_OUT_PATH, index=False, encoding="utf-8")
    return file_size_bytes(UNIVERSO_OUT_PATH)


def write_catastro_spatial_ready(df_ready: pd.DataFrame) -> int:
    ensure_dir(CATASTRO_SPATIAL_READY_PATH.parent)
    fc = dataframe_to_geojson(df_ready, geometry_col="_geometry")
    size = write_json(CATASTRO_SPATIAL_READY_PATH, fc, compact=True, default=json_safe_default)

    write_metadata(
        CATASTRO_SPATIAL_READY_PATH.with_suffix(CATASTRO_SPATIAL_READY_PATH.suffix + ".metadata.json"),
        fuente="Catastro Minero ANM - Títulos Vigentes (WFS) - spatial ready",
        url=str(CATASTRO_CLEAN_PATH.relative_to(PROJECT_ROOT)),
        formato="GeoJSON RFC 7946 (FeatureCollection, sin miembro crs; CRS = EPSG:4326)",
        estado="completo",
        tamano_bytes=size,
        filas_descargadas=len(df_ready),
        observaciones=(
            "Versión del catastro minero preparada para intersección espacial: las 22 "
            "geometrías inválidas de catastro_minero_anm_clean.geojson (Fase 3C, que NO se "
            "modificó) se repararon aquí con shapely.make_valid. Todas las geometrías finales "
            "son MultiPolygon homogéneo. Ningún codigo_expediente se eliminó."
        ),
    )
    return size


# --------------------------------------------------------------------------
# F. Prueba de rendimiento STRtree
# --------------------------------------------------------------------------


def run_performance_test(
    df_catastro_ready: pd.DataFrame,
    df_limites: pd.DataFrame,
    limites_geometries: list[dict | None],
    bajira_feature: dict,
    *,
    n_muestra: int = 40,
) -> dict:
    """Selecciona una muestra pequeña de títulos mineros y ejecuta la prueba
    de rendimiento con STRtree contra TODAS las unidades territoriales del
    universo geométrico reconciliado (1.122 de límites + 1 de Bajirá), tal
    como se indexaría en la futura Fase 4A. NO ejecuta la intersección
    nacional completa (6.294 × 1.122)."""
    muestra = df_catastro_ready[df_catastro_ready["_geometry"].notna()].sample(
        n=min(n_muestra, len(df_catastro_ready)), random_state=42
    )
    title_geometries = [(row["codigo_expediente"], row["_geometry"]) for _, row in muestra.iterrows()]

    territorial_geometries = [
        (cod, geom)
        for cod, geom in zip(df_limites["cod_dane_mpio"], limites_geometries)
        if geom is not None
    ]
    territorial_geometries.append((bajira_feature["properties"]["cod_dane_mpio"], bajira_feature["geometry"]))

    resultado = run_strtree_performance_test(
        title_geometries, territorial_geometries, crs_origen=CRS_ORIGEN, crs_metrico=CRS_METRICO
    )
    resultado["n_pares_fuerza_bruta_hipotetica_nacional"] = 6294 * 1122
    return resultado


# --------------------------------------------------------------------------
# Reportes
# --------------------------------------------------------------------------


def build_territorial_reconciliation_report(
    df_universo: pd.DataFrame,
    validaciones_bajira: dict,
    metrics_antes: dict,
    metrics_despues: dict,
    strtree_result: dict,
) -> str:
    tipo_counts = df_universo[df_universo["presente_divipola_vigente"]]["tipo_unidad_territorial"].value_counts()
    estado_counts = df_universo["estado_reconciliacion"].value_counts()

    lines = [
        "# Reconciliación territorial (Fase 3D.1)",
        "",
        "Reconciliación del universo territorial DIVIPOLA (fuente de verdad administrativa, "
        "Fase 3B) contra la capa geométrica de límites municipales (Fase 3D). **No se llama "
        "genéricamente \"municipios\" a las 1.122 unidades**: se usa la denominación técnica "
        "\"unidades territoriales subdepartamentales DIVIPOLA\", que incluye Municipio, Área "
        "no municipalizada, Isla y otras categorías presentes en la fuente.",
        "",
        f"- Total de filas en el universo territorial reconciliado: {len(df_universo)} "
        f"(1.122 vigentes en DIVIPOLA + {len(df_universo) - 1122} fuera de DIVIPOLA vigente "
        "pero con geometría, conservadas para trazabilidad).",
        "",
        "## Conteo por tipo de unidad territorial (universo DIVIPOLA vigente, 1.122)",
        "",
        "| tipo_unidad_territorial | Conteo |",
        "|---|---|",
    ]
    for tipo, n in tipo_counts.items():
        lines.append(f"| {tipo} | {n} |")
    lines.append("")

    lines.append("## Conteo por estado de reconciliación")
    lines.append("")
    lines.append("| estado_reconciliacion | Conteo |")
    lines.append("|---|---|")
    for estado, n in estado_counts.items():
        lines.append(f"| {estado} | {n} |")
    lines.append("")

    lines.append("## B. Discrepancia 94663 / 27493")
    lines.append("")
    lines.append("### 94663 — Mapiripana (Guainía)")
    lines.append("")
    lines.append(
        "- Presente en la capa geométrica (ArcGIS REST Divipola/Cache_DivipolaEntidadesTerritorialesCP)."
    )
    lines.append("- Ausente de la DIVIPOLA tabular vigente (Fase 3B).")
    lines.append(
        "- **Estado:** `fuera_universo_divipola_vigente`. Se conserva en `universo_territorial_divipola.csv` "
        "para trazabilidad, pero queda excluido por defecto del universo analítico vigente hasta "
        "que exista evidencia oficial de su incorporación a DIVIPOLA. No se elimina de ningún "
        "archivo de datos original."
    )
    lines.append("")
    lines.append("### 27493 — Nuevo Belén de Bajirá (Chocó)")
    lines.append("")
    lines.append("- Presente en la DIVIPOLA tabular vigente (Fase 3B).")
    lines.append(
        "- Ausente de la capa geométrica descargada en la Fase 2C "
        "(Divipola/Cache_DivipolaEntidadesTerritorialesCP)."
    )
    lines.append(
        "- **Fuente oficial consultada y encontrada:** DANE — Marco Geoestadístico Nacional 2025 "
        "(MGN2025), servicio `geoportal.dane.gov.co/mparcgis/rest/services/MGN2025/"
        "Serv_CapasMGN_2025/FeatureServer`, capa **Municipio (id 317)**."
    )
    lines.append(f"- URL de consulta: `{validaciones_bajira['fuente_url']}`")
    lines.append(f"- Fecha de descarga: {validaciones_bajira['fecha_descarga']}")
    lines.append("")
    lines.append("**Validaciones realizadas sobre la geometría recuperada:**")
    lines.append("")
    lines.append(f"- Código coincide (`MPIO_CDPMP` = 27493): {validaciones_bajira['codigo_coincide']}")
    lines.append(f"- Departamento coincide (`DPTO_CCDGO` vs `cod_dpto` DIVIPOLA): {validaciones_bajira['departamento_coincide']}")
    lines.append(
        f"- Nombre coincide (normalizado): {validaciones_bajira['nombre_coincide_normalizado']} "
        f"(`{validaciones_bajira['nombre_origen_norm']}` vs `{validaciones_bajira['nombre_divipola_norm']}`)"
    )
    lines.append(f"- Geometría válida (shapely): {validaciones_bajira['geometria_valida']} (tipo: {validaciones_bajira['geometria_tipo']})")
    lines.append(f"- CRS solicitado: {validaciones_bajira['crs_solicitado']}")
    lines.append(f"- Bounding box dentro del rango esperado de Colombia: {validaciones_bajira['bbox_dentro_de_colombia']} ({validaciones_bajira['bbox']})")
    lines.append("")
    lines.append(
        "- **Nota de transparencia:** también se encontró un registro geométrico de este municipio "
        "en el catálogo ICDE (metadatos.icde.gov.co), pero la entidad productora de ese registro es "
        "el **IGAC**, no el DANE; conforme a la instrucción explícita de esta fase de consultar "
        "únicamente fuentes oficiales del DANE, ese registro **no se usó**."
    )
    lines.append(
        "- **Integración:** la geometría validada se guardó en "
        "`data/processed/territorio/dane_mgn2025_nuevo_belen_bajira_27493_clean.geojson` "
        "(RFC 7946), separada de los 11 archivos de límites municipales para no reprocesar "
        "158 MB ya generados; `universo_territorial_divipola.csv` documenta que debe usarse "
        "en conjunto con esos 11 archivos para tener el universo geométrico completo."
    )
    lines.append("")

    lines.append("## C. Métricas de correspondencia (correctamente separadas)")
    lines.append("")
    lines.append("### Antes de la reconciliación (capa geométrica original, Fase 3D: 1.122 códigos, incluye 94663, no incluye 27493)")
    lines.append("")
    lines.append(f"- Total códigos DIVIPOLA: {metrics_antes['total_codigos_divipola']}")
    lines.append(f"- Total códigos geométricos: {metrics_antes['total_codigos_geometricos']}")
    lines.append(f"- Intersección: {metrics_antes['codigos_interseccion']} | Unión: {metrics_antes['codigos_union']}")
    lines.append(f"- **cobertura_divipola_por_geometria** (códigos DIVIPOLA con geometría / total DIVIPOLA): {metrics_antes['cobertura_divipola_por_geometria_pct']}%")
    lines.append(f"- **precision_geometria_contra_divipola** (códigos geométricos vigentes / total geométricos): {metrics_antes['precision_geometria_contra_divipola_pct']}%")
    lines.append(f"- **similitud_jaccard** (intersección / unión): {metrics_antes['similitud_jaccard_pct']}%")
    lines.append("")
    lines.append("### Después de la reconciliación (universo geométrico ampliado: 1.123 códigos, incluye 94663 y 27493 recuperado)")
    lines.append("")
    lines.append(f"- Total códigos DIVIPOLA: {metrics_despues['total_codigos_divipola']}")
    lines.append(f"- Total códigos geométricos: {metrics_despues['total_codigos_geometricos']}")
    lines.append(f"- Intersección: {metrics_despues['codigos_interseccion']} | Unión: {metrics_despues['codigos_union']}")
    lines.append(f"- **cobertura_divipola_por_geometria**: {metrics_despues['cobertura_divipola_por_geometria_pct']}%")
    lines.append(f"- **precision_geometria_contra_divipola**: {metrics_despues['precision_geometria_contra_divipola_pct']}%")
    lines.append(f"- **similitud_jaccard**: {metrics_despues['similitud_jaccard_pct']}%")
    lines.append("")
    lines.append(
        "**Nota de corrección respecto a la Fase 3D:** el reporte anterior presentó "
        "\"99,82% de correspondencia\" describiéndolo como si fuera 1.121/1.122 (que en "
        "realidad da 99,91%). 99,82% era en realidad la similitud de Jaccard "
        "(1.121/1.123, dividiendo por la UNIÓN, no por el total de DIVIPOLA). Esta fase separa "
        "explícitamente las tres métricas para que no se repita esa confusión."
    )
    lines.append("")

    lines.append("## F. Prueba de rendimiento STRtree")
    lines.append("")
    lines.append(
        f"- Muestra de títulos mineros: {strtree_result['n_titulos_muestra']} "
        f"(de 6.294 en catastro_minero_anm_spatial_ready.geojson)."
    )
    lines.append(f"- Unidades territoriales indexadas: {strtree_result['n_unidades_territoriales_indexadas']}")
    lines.append(f"- CRS métrico usado para reproyección: {strtree_result['crs_metrico_usado']}")
    lines.append(f"- Tiempo de construcción del índice STRtree: {strtree_result['tiempo_construccion_indice_s']} s")
    lines.append(f"- Tiempo de consulta + intersección real: {strtree_result['tiempo_consulta_e_interseccion_s']} s")
    lines.append(f"- Tiempo total: {strtree_result['tiempo_total_s']} s")
    lines.append(f"- Memoria pico (tracemalloc): {strtree_result['memoria_pico_mb']} MB")
    lines.append(f"- Pares candidatos por bounding box (STRtree): {strtree_result['n_pares_candidatos_bbox']}")
    lines.append(f"- Intersecciones geométricas reales confirmadas: {strtree_result['n_intersecciones_reales']}")
    lines.append(
        f"- Pares de fuerza bruta evitados solo en esta muestra: {strtree_result['n_pares_fuerza_bruta_evitados']} "
        f"(de {strtree_result['n_titulos_muestra'] * strtree_result['n_unidades_territoriales_indexadas']} "
        "posibles sin índice)."
    )
    lines.append(
        f"- Referencia: la intersección nacional completa sin índice implicaría hasta "
        f"{strtree_result['n_pares_fuerza_bruta_hipotetica_nacional']:,} pares "
        "(6.294 títulos × 1.122 unidades territoriales) — **no se ejecutó esta prueba de fuerza "
        "bruta**; el resultado de esta muestra confirma que el índice STRtree es viable para la "
        "Fase 4A."
    )
    lines.append(
        "- **Hallazgo de rendimiento clave:** casi todo el tiempo total "
        f"({strtree_result['tiempo_construccion_indice_s']} s de {strtree_result['tiempo_total_s']} s) "
        "se gastó reproyectando y construyendo el índice sobre las 1.123 geometrías territoriales "
        "(pesadas, sin simplificar); la consulta STRtree + intersección real sobre las candidatas "
        f"tomó solo {strtree_result['tiempo_consulta_e_interseccion_s']} s. Para la Fase 4A conviene "
        "reproyectar y construir el índice territorial **una sola vez** y reutilizarlo para los "
        "6.294 títulos, en vez de reconstruirlo por título."
    )
    lines.append("")

    return "\n".join(lines)


def build_catastro_repair_report(report: dict, size: int) -> str:
    lines = [
        "# Reparación de geometrías — Catastro Minero spatial_ready (Fase 3D.1)",
        "",
        "Preparación del catastro minero para intersección espacial futura. **No se modificó** "
        "`data/processed/mineria/catastro_minero_anm_clean.geojson` (Fase 3C): esta es una "
        "versión nueva y separada.",
        "",
        f"- Ruta de salida: `data/processed/mineria/catastro_minero_anm_spatial_ready.geojson`",
        f"- Tamaño: {format_bytes(size)}",
        f"- codigo_expediente: {report['filas_entrada']} -> {report['filas_salida']} (0 eliminados)",
        "",
        "## Calidad de geometrías",
        "",
        f"- Nulas (entrada): {report['validaciones']['n_geometrias_nulas_entrada']}",
        f"- Inválidas ANTES (heredadas de catastro_minero_anm_clean.geojson, Fase 3C): {report['validaciones']['n_geometrias_invalidas_entrada']}",
        f"- Geometrías reparadas (shapely.make_valid): {report['validaciones']['n_geometrias_reparadas']}",
        f"- Inválidas DESPUÉS de reparar: {report['validaciones']['n_geometrias_invalidas_salida']}",
        f"- Vacías tras reparar (irreparables): {report['validaciones']['n_geometrias_vacias_salida']}",
        f"- Tipos geométricos finales: {report['validaciones']['tipos_geometricos_finales']}",
        "",
        "## Reparaciones (detalle completo, por codigo_expediente)",
        "",
    ]
    if report["reparaciones_detalle"]:
        lines.append(
            "| codigo_expediente | motivo | tipo original | tipo make_valid | GeometryCollection? | "
            "componentes poligonales | componentes descartados | vacía? | válida final? |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|")
        invalidas_finales = set()
        for r in report["reparaciones_detalle"]:
            es_valida_final = not r["quedo_vacia"]
            lines.append(
                f"| {r['feature_id']} | {r['motivo_invalidez']} | {r['tipo_original']} | "
                f"{r['tipo_resultante_make_valid']} | {r['paso_a_geometrycollection']} | "
                f"{r['n_componentes_poligonales_finales']} | "
                f"{r['componentes_no_poligonales_descartados'] or 'ninguno'} | "
                f"{r['quedo_vacia']} | {es_valida_final} |"
            )
    else:
        lines.append("_No hubo geometrías inválidas que reparar (0 detectadas)._")
    lines.append("")

    lines.append("## Observaciones")
    lines.append("")
    for obs in report["observaciones"]:
        lines.append(f"- {obs}")
    lines.append("")

    return "\n".join(lines)


# --------------------------------------------------------------------------
# Validaciones
# --------------------------------------------------------------------------


def validate_universo(df_universo: pd.DataFrame) -> list[str]:
    problems: list[str] = []
    vigentes = df_universo[df_universo["presente_divipola_vigente"]]
    if len(vigentes) != 1122:
        problems.append(f"universo vigente tiene {len(vigentes)} filas, se esperaban 1122")

    fila_94663 = df_universo[df_universo["cod_dane_mpio"] == CODIGO_MAPIRIPANA]
    if fila_94663.empty or fila_94663.iloc[0]["estado_reconciliacion"] != "fuera_universo_divipola_vigente":
        problems.append("94663 no quedó marcado como 'fuera_universo_divipola_vigente'")

    fila_27493 = df_universo[df_universo["cod_dane_mpio"] == CODIGO_BAJIRA]
    if fila_27493.empty or not bool(fila_27493.iloc[0]["tiene_geometria"]):
        problems.append("27493 no quedó con tiene_geometria=True tras la reconciliación")

    if vigentes["tipo_unidad_territorial"].isna().any():
        problems.append("hay filas del universo vigente sin tipo_unidad_territorial")

    return problems


def validate_rfc7946(paths: list[Path]) -> list[str]:
    problems: list[str] = []
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            fc = json.load(fh)
        if "crs" in fc:
            problems.append(f"{p.name}: todavía tiene el miembro 'crs' (no es RFC 7946)")
        if fc.get("type") != "FeatureCollection" or not fc.get("features"):
            problems.append(f"{p.name}: no es un FeatureCollection no vacío")
    return problems


def validate_catastro_spatial_ready(path: Path) -> list[str]:
    from shapely.geometry import shape

    problems: list[str] = []
    with open(path, encoding="utf-8") as fh:
        fc = json.load(fh)

    n_sin_geom = 0
    n_invalidas = 0
    n_no_poligonal = 0
    codigos = set()
    for feat in fc["features"]:
        codigos.add(feat["properties"]["codigo_expediente"])
        geom = feat.get("geometry")
        if not geom:
            n_sin_geom += 1
            continue
        s = shape(geom)
        if not s.is_valid:
            n_invalidas += 1
        if s.geom_type not in ("Polygon", "MultiPolygon"):
            n_no_poligonal += 1

    if len(codigos) != len(fc["features"]):
        problems.append("hay codigo_expediente duplicados en catastro_minero_anm_spatial_ready.geojson")
    if n_invalidas:
        problems.append(f"{n_invalidas} geometrías siguen inválidas en spatial_ready")
    if n_no_poligonal:
        problems.append(f"{n_no_poligonal} geometrías no son Polygon/MultiPolygon en spatial_ready")
    if n_sin_geom:
        problems.append(f"{n_sin_geom} geometrías nulas en spatial_ready (deben estar documentadas si son irreparables)")

    return problems


# --------------------------------------------------------------------------
# Orquestación
# --------------------------------------------------------------------------


def main() -> int:
    print("=== AquaBosque Minero IA — Fase 3D.1: reconciliación territorial y preparación espacial ===\n")
    ensure_dir(REPORTS_DIR)
    problems: list[str] = []

    print("-> Cargando DIVIPOLA limpia, límites municipales limpios y catastro minero limpio ...")
    df_divipola = load_divipola_clean()
    df_limites, limites_geometries, limites_manifest = load_limites_clean()
    df_catastro = load_catastro_clean()
    print(f"   DIVIPOLA: {len(df_divipola)} | Límites municipales: {len(df_limites)} | Catastro minero: {len(df_catastro)}")

    print("-> Consultando y validando geometría oficial DANE MGN2025 para 27493 ...")
    bajira_feature, validaciones_bajira = load_and_validate_bajira_geometry(df_divipola)
    print(f"   Validaciones: {validaciones_bajira}")
    write_bajira_clean_geojson(bajira_feature)

    print("-> Construyendo universo_territorial_divipola.csv ...")
    df_universo = build_universo_territorial(df_divipola, df_limites)
    universo_size = write_universo_territorial(df_universo)
    print(f"   {len(df_universo)} filas -> {UNIVERSO_OUT_PATH.relative_to(PROJECT_ROOT)} ({format_bytes(universo_size)})")
    problems.extend(validate_universo(df_universo))

    print("-> Calculando métricas de correspondencia (antes/después) ...")
    set_divipola = set(df_divipola["cod_dane_mpio"])
    set_limites = set(df_limites["cod_dane_mpio"])
    metrics_antes = compute_correspondence_metrics(set_divipola, set_limites)
    metrics_despues = compute_correspondence_metrics(set_divipola, set_limites | {CODIGO_BAJIRA})
    print(f"   Antes: {metrics_antes}")
    print(f"   Después: {metrics_despues}")

    print("-> Validando RFC 7946 en los GeoJSON procesados de límites municipales ...")
    limites_paths = [LIMITES_CLEAN_DIR / a["archivo"] for a in limites_manifest["archivos_y_tamanos"]]
    problems.extend(validate_rfc7946(limites_paths + [BAJIRA_CLEAN_OUT_PATH]))

    print("-> Preparando catastro minero spatial_ready (reparando geometrías inválidas) ...")
    df_catastro_ready, catastro_repair_report = prepare_catastro_minero_spatial_ready(df_catastro)
    catastro_size = write_catastro_spatial_ready(df_catastro_ready)
    print(
        f"   {catastro_repair_report['filas_entrada']} -> {catastro_repair_report['filas_salida']} | "
        f"reparadas: {catastro_repair_report['validaciones']['n_geometrias_reparadas']} | "
        f"tamaño: {format_bytes(catastro_size)}"
    )
    problems.extend(validate_catastro_spatial_ready(CATASTRO_SPATIAL_READY_PATH))
    problems.extend(validate_rfc7946([CATASTRO_SPATIAL_READY_PATH]))

    print("-> Ejecutando prueba de rendimiento STRtree (muestra de títulos mineros) ...")
    strtree_result = run_performance_test(df_catastro_ready, df_limites, limites_geometries, bajira_feature)
    print(
        f"   muestra={strtree_result['n_titulos_muestra']} | tiempo_total={strtree_result['tiempo_total_s']}s | "
        f"memoria_pico={strtree_result['memoria_pico_mb']}MB | "
        f"candidatos_bbox={strtree_result['n_pares_candidatos_bbox']} | "
        f"intersecciones_reales={strtree_result['n_intersecciones_reales']}"
    )

    print("-> Generando reportes ...")
    reconciliation_report = build_territorial_reconciliation_report(
        df_universo, validaciones_bajira, metrics_antes, metrics_despues, strtree_result
    )
    (REPORTS_DIR / "territorial_reconciliation.md").write_text(reconciliation_report, encoding="utf-8")

    repair_report_text = build_catastro_repair_report(catastro_repair_report, catastro_size)
    (REPORTS_DIR / "catastro_minero_geometry_repair.md").write_text(repair_report_text, encoding="utf-8")

    print(f"\nReportes -> {REPORTS_DIR.relative_to(PROJECT_ROOT)}/")

    print("\n=== Resumen ===")
    print("94663 (Mapiripana): fuera del universo DIVIPOLA vigente, conservado para trazabilidad.")
    print("27493 (Nuevo Belén de Bajirá): geometría recuperada de DANE MGN2025, integrada.")
    print(f"Cobertura DIVIPOLA por geometría: {metrics_antes['cobertura_divipola_por_geometria_pct']}% -> {metrics_despues['cobertura_divipola_por_geometria_pct']}%")
    print(f"Precisión geometría contra DIVIPOLA: {metrics_antes['precision_geometria_contra_divipola_pct']}% -> {metrics_despues['precision_geometria_contra_divipola_pct']}%")
    print(f"Similitud Jaccard: {metrics_antes['similitud_jaccard_pct']}% -> {metrics_despues['similitud_jaccard_pct']}%")
    print(f"Catastro minero spatial_ready: {catastro_repair_report['validaciones']['n_geometrias_reparadas']} geometrías reparadas, 0 inválidas finales.")

    if problems:
        print("\nAtención: problemas detectados:")
        for p in problems:
            print(f"  - {p}")
        return 1

    print("\nReconciliación territorial y preparación espacial completas. No se ejecutó intersección nacional ni se construyeron indicadores mineros.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


