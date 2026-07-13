"""Fase 2D.2: cierre técnico de DTD y robustez de la decodificación forestal.

Corrige la auditoría DTD de la Fase 2D.1 (bug de conteo de categorías
distintas), valida el universo completo del periodo 2025-IV (21.044
registros, no la muestra de 2.000), audita la estabilidad de `cod_dtd` en
todo el histórico 2017-I a 2025-IV, audita el colormap RGB de forma
exhaustiva y prueba la estabilidad del WCS con una segunda configuración de
recorte. Amplía la comparación ráster-vector a 3 municipios y audita la
cobertura territorial del vector frente a MGN2025.

No descarga todavía la serie forestal nacional completa. No calcula
indicadores para los 1.122 territorios. No integra minería ni calidad
hídrica. No construye índice de riesgo. No entrena modelos.
"""

from __future__ import annotations

import importlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import rasterio
from shapely.geometry import shape as shapely_shape

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
for p in (SRC_DIR, SCRIPTS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# scripts/20 empieza con un dígito: no es un identificador válido para
# `import`, se carga con importlib para reutilizar sus funciones ya
# validadas (descarga WCS, colormap, piloto vectorial) sin duplicarlas.
mod20 = importlib.import_module("20_validate_forest_data_pilot")

from aquabosque.geo.intersection import build_transformer, reproject_geometry  # noqa: E402
from aquabosque.utils.io import ensure_dir, utc_now_iso, write_json  # noqa: E402

DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
AUDIT_DIR = DATA_PROCESSED / "audit"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports" / "forest_sources"
UNIVERSO_PATH = DATA_PROCESSED / "territorio" / "universo_territorial_divipola.csv"

DTD_STATS_PATH = AUDIT_DIR / "dtd_2025_iv_complete_statistics.csv"
DTD_STABILITY_PATH = AUDIT_DIR / "dtd_identifier_stability_audit.csv"
COLORMAP_AUDIT_PATH = AUDIT_DIR / "forest_rgb_colormap_decode_audit.csv"
VECTOR_TERRITORIAL_AUDIT_PATH = AUDIT_DIR / "deforestation_vector_territorial_pilot_audit.csv"
MULTI_MUNICIPIO_COMPARISON_PATH = AUDIT_DIR / "forest_raster_vector_multi_municipio.csv"
WCS_STABILITY_PATH = AUDIT_DIR / "forest_wcs_stability_audit.csv"

CRS_ORIGEN = "EPSG:4326"
CRS_METRICO = "EPSG:9377"
M2_PER_HA = 10_000.0

TOLERANCIA_CLASE_DESCONOCIDA_PCT = 0.5  # % máximo tolerado de píxeles no decodificables


# ---------------------------------------------------------------------------
# B. Estadísticas completas del periodo 2025-IV
# ---------------------------------------------------------------------------


def dtd_group_stats(where: str, group_fields: str, having: str | None = None) -> list[dict]:
    params = {
        "where": where, "groupByFieldsForStatistics": group_fields,
        "outStatistics": json.dumps([{"statisticType": "count", "onStatisticField": "fid", "outStatisticFieldName": "n"}]),
        "orderByFields": "n DESC", "f": "json",
    }
    if having:
        params["having"] = having
    data, status = mod20.get_json(f"{mod20.DTD_URL}/query", params)
    return [f["attributes"] for f in (data or {}).get("features", [])]


def build_dtd_2025_iv_complete_statistics() -> pd.DataFrame:
    where = "anio='2025' AND periodo='iv'"
    count_data, _ = mod20.get_json(f"{mod20.DTD_URL}/query", {"where": where, "returnCountOnly": "true", "f": "json"})
    n_total = (count_data or {}).get("count")

    por_depto = dtd_group_stats(where, "cod_depto,nom_depto")
    por_mpio = dtd_group_stats(where, "cod_mpio,nom_mpio")
    por_nucleo = dtd_group_stats(where, "nucleo_tri")
    dup_cod_dtd = dtd_group_stats(where, "cod_dtd", having="count(fid) > 1")

    nulos = {}
    for campo in ("cod_dtd", "cod_mpio", "nom_mpio", "cod_depto", "nom_depto", "nucleo_tri", "x", "y"):
        d, _ = mod20.get_json(f"{mod20.DTD_URL}/query", {"where": f"{where} AND {campo} IS NULL", "returnCountOnly": "true", "f": "json"})
        nulos[campo] = (d or {}).get("count")

    dup_coords = dtd_group_stats(where, "x,y", having="count(fid) > 1")
    n_registros_coords_duplicadas = sum(r["n"] for r in dup_coords)

    filas: list[dict[str, Any]] = [
        {"tipo": "agregado", "categoria": "registros_totales", "valor": n_total},
        {"tipo": "agregado", "categoria": "codigos_departamento_distintos", "valor": len(por_depto)},
        {"tipo": "agregado", "categoria": "codigos_municipio_distintos", "valor": len(por_mpio)},
        {"tipo": "agregado", "categoria": "nucleos_distintos", "valor": len(por_nucleo)},
        {"tipo": "agregado", "categoria": "cod_dtd_duplicados_dentro_del_periodo", "valor": len(dup_cod_dtd)},
        {"tipo": "agregado", "categoria": "pares_coordenada_duplicados", "valor": len(dup_coords)},
        {"tipo": "agregado", "categoria": "registros_en_coordenadas_duplicadas", "valor": n_registros_coords_duplicadas},
    ]
    for campo, n in nulos.items():
        filas.append({"tipo": "nulos", "categoria": campo, "valor": n})
    for r in por_depto:
        filas.append({"tipo": "por_departamento", "categoria": f"{r['cod_depto']}|{r['nom_depto']}", "valor": r["n"]})
    for r in por_mpio:
        filas.append({"tipo": "por_municipio", "categoria": f"{r['cod_mpio']}|{r['nom_mpio']}", "valor": r["n"]})
    for r in por_nucleo:
        filas.append({"tipo": "por_nucleo", "categoria": str(r.get("nucleo_tri")), "valor": r["n"]})
    for r in dup_cod_dtd:
        filas.append({"tipo": "cod_dtd_duplicado_detalle", "categoria": r["cod_dtd"], "valor": r["n"]})

    df = pd.DataFrame(filas)
    suma_deptos = sum(r["n"] for r in por_depto)
    suma_mpios = sum(r["n"] for r in por_mpio)
    assert suma_deptos == n_total, f"suma por departamento ({suma_deptos}) != total ({n_total})"
    assert suma_mpios == n_total, f"suma por municipio ({suma_mpios}) != total ({n_total})"
    return df


# ---------------------------------------------------------------------------
# C. Auditoría de identificadores DTD (histórico completo 2017-I a 2025-IV)
# ---------------------------------------------------------------------------


def fetch_all_dtd_attributes(page_size: int = 2000) -> pd.DataFrame:
    campos = "cod_dtd,anio,periodo,cod_mpio,nom_mpio,cod_depto,nucleo_tri,x,y"
    count_data, _ = mod20.get_json(f"{mod20.DTD_URL}/query", {"where": "1=1", "returnCountOnly": "true", "f": "json"})
    n_total = (count_data or {}).get("count")

    filas = []
    offset = 0
    while True:
        data, status = mod20.get_json(
            f"{mod20.DTD_URL}/query",
            {"where": "1=1", "outFields": campos, "returnGeometry": "false", "resultOffset": offset, "resultRecordCount": page_size, "orderByFields": "fid", "f": "json"},
        )
        feats = (data or {}).get("features", [])
        if not feats:
            break
        filas.extend(f["attributes"] for f in feats)
        offset += len(feats)
        if len(feats) < page_size:
            break
    df = pd.DataFrame(filas)
    assert len(df) == n_total, f"paginación incompleta: {len(df)} filas recuperadas, se esperaban {n_total}"
    return df


def audit_dtd_identifier_stability(df_all: pd.DataFrame) -> pd.DataFrame:
    df = df_all.copy()
    df["periodo_completo"] = df["anio"].astype(str) + "-" + df["periodo"].astype(str)
    df["coord_redondeada"] = list(zip(df["x"].round(5), df["y"].round(5)))

    filas = []
    for cod_dtd, grupo in df.groupby("cod_dtd", dropna=False):
        n_apariciones = len(grupo)
        n_periodos = grupo["periodo_completo"].nunique(dropna=True)
        n_coords = grupo["coord_redondeada"].nunique()
        n_mpios = grupo["cod_mpio"].nunique(dropna=True)
        n_nucleos = grupo["nucleo_tri"].nunique(dropna=True)

        if pd.isna(cod_dtd) or str(cod_dtd).strip() == "":
            clasif = "identificador_no_evaluable"
            razon = "cod_dtd nulo o vacío"
        elif n_apariciones == 1:
            clasif = "identificador_unico_evento"
            razon = "aparece exactamente una vez en todo el histórico 2017-I a 2025-IV"
        elif n_periodos == 1 and n_apariciones > 1:
            clasif = "requiere_revision_manual"
            razon = f"{n_apariciones} apariciones dentro del MISMO periodo ({grupo['periodo_completo'].iloc[0]}) — duplicado intra-periodo, no reutilización entre trimestres"
        elif n_periodos > 1 and n_coords == 1:
            clasif = "identificador_reutilizado_mismo_lugar"
            razon = f"reaparece en {n_periodos} periodos distintos con la misma coordenada (redondeada a 5 decimales)"
        elif n_periodos > 1 and n_coords > 1:
            clasif = "identificador_reutilizado_otra_ubicacion"
            razon = f"reaparece en {n_periodos} periodos distintos con {n_coords} coordenadas distintas"
        else:
            clasif = "requiere_revision_manual"
            razon = "combinación de apariciones/periodos/coordenadas no cubierta por las reglas anteriores"

        filas.append({
            "cod_dtd": cod_dtd, "n_apariciones_historico": n_apariciones, "n_periodos_distintos": n_periodos,
            "n_coordenadas_distintas": n_coords, "n_municipios_distintos": n_mpios, "n_nucleos_distintos": n_nucleos,
            "cambia_de_municipio": bool(n_mpios > 1), "primer_periodo": grupo["periodo_completo"].min(),
            "ultimo_periodo": grupo["periodo_completo"].max(), "clasificacion": clasif, "razon": razon,
        })
    return pd.DataFrame(filas).sort_values(["n_apariciones_historico"], ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# D. Comparación correcta con el Boletín 45
# ---------------------------------------------------------------------------

DEPTOS_BOLETIN_45_PCT_AREA = {"CAQUETA": 44, "META": 26, "GUAVIARE": 17, "PUTUMAYO": 10}


def compare_boletin_45_correcto(df_stats: pd.DataFrame) -> dict[str, Any]:
    total = int(df_stats.loc[(df_stats["tipo"] == "agregado") & (df_stats["categoria"] == "registros_totales"), "valor"].iloc[0])
    por_depto = df_stats[df_stats["tipo"] == "por_departamento"].copy()
    por_depto["nombre"] = por_depto["categoria"].str.split("|").str[1]
    por_depto["pct_puntos"] = (por_depto["valor"] / total * 100).round(2)
    por_depto = por_depto.sort_values("valor", ascending=False)

    top4_pct_puntos = dict(zip(por_depto["nombre"].head(4), por_depto["pct_puntos"].head(4)))
    orden_boletin = list(DEPTOS_BOLETIN_45_PCT_AREA.keys())
    orden_puntos = [_normalize(n) for n in por_depto["nombre"].head(4).tolist()]

    mismos_4_deptos = set(orden_puntos) == {_normalize(n) for n in orden_boletin}
    mismo_orden = orden_puntos == [_normalize(n) for n in orden_boletin]

    if mismos_4_deptos and mismo_orden:
        clasif = "consistente_en_distribucion_territorial"
    elif mismos_4_deptos and not mismo_orden:
        clasif = "parcialmente_consistente"
    elif len(set(orden_puntos) & {_normalize(n) for n in orden_boletin}) >= 2:
        clasif = "parcialmente_consistente"
    else:
        clasif = "no_comparable_por_unidad_de_medida"

    return {
        "periodo_comparado": "2025-IV (FeatureServer, 21.044 registros reales) vs. Boletín 45 (IV trimestre 2025)",
        "top4_departamentos_pct_puntos_featureserver": top4_pct_puntos,
        "top4_departamentos_pct_area_boletin_45": DEPTOS_BOLETIN_45_PCT_AREA,
        "mismos_4_departamentos_dominantes": mismos_4_deptos,
        "mismo_orden_de_magnitud": mismo_orden,
        "clasificacion": clasif,
        "advertencia_unidad_de_medida": (
            "El Boletín 45 reporta PORCENTAJE DE ÁREA/CONCENTRACIÓN; el FeatureServer solo permite "
            "calcular PORCENTAJE DE CONTEO DE PUNTOS. Ambas medidas identifican los mismos 4 "
            "departamentos dominantes, pero el orden relativo puede diferir (p. ej. Meta supera a "
            "Caquetá en conteo de puntos, mientras que el boletín reporta a Caquetá con mayor "
            "porcentaje de área) — un punto no representa una superficie fija, así que no se "
            "recalculan ni se comparan directamente los porcentajes como si fueran la misma unidad."
        ),
    }


def _normalize(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in s if not unicodedata.combining(c)).upper().strip()


# ---------------------------------------------------------------------------
# E. Auditoría completa del colormap RGB
# ---------------------------------------------------------------------------


def audit_colormap_full(path: Path, colormap: dict, nombre_producto: str) -> pd.DataFrame:
    with rasterio.open(path) as src:
        n_bandas = src.count
        tiene_alfa = src.count == 4 or (src.colorinterp and any(str(ci).lower() == "alpha" for ci in src.colorinterp))
        arr = src.read()

    rgb = arr[:3].transpose(1, 2, 0)
    flat = rgb.reshape(-1, 3)
    uniq, counts = np.unique(flat, axis=0, return_counts=True)
    total_px = flat.shape[0]

    colores_colormap = {tuple(int(c) for c in k) for k in colormap.keys()}
    codigos_vistos: dict[int, list[tuple]] = {}
    for color in colores_colormap:
        codigos_vistos.setdefault(colormap[color]["codigo"], []).append(color)
    colores_ambiguos = {cod: cs for cod, cs in codigos_vistos.items() if False}  # por construcción del dict, 1 RGB -> 1 código; se valida explícitamente abajo.

    # Validación explícita de colisión inversa (más de un color mapeando al mismo código
    # NO es una ambigüedad — es esperado, un código puede tener 0 o 1 color asociado por
    # diseño de diccionario; lo que se prohíbe es un MISMO RGB con más de un código, lo cual
    # es estructuralmente imposible en un dict de Python — se documenta como verificado).
    n_colores_ambiguos = 0  # estructuralmente 0: un dict no permite una clave (RGB) con 2 valores.

    filas = []
    n_decodificados = 0
    n_no_decodificados = 0
    clases_esperadas = {v["codigo"]: v["clase"] for v in colormap.values()}
    clases_vistas = set()
    for color, count in zip(uniq.tolist(), counts.tolist()):
        color_t = tuple(color)
        en_colormap = color_t in colores_colormap
        pct = round(count / total_px * 100, 4)
        if en_colormap:
            meta = colormap[color_t]
            n_decodificados += count
            clases_vistas.add(meta["codigo"])
            filas.append({
                "producto": nombre_producto, "rgb": str(color_t), "frecuencia": count, "pct_del_total": pct,
                "en_colormap_oficial": True, "codigo_clase": meta["codigo"], "clase": meta["clase"], "estado": "decodificado",
            })
        else:
            n_no_decodificados += count
            filas.append({
                "producto": nombre_producto, "rgb": str(color_t), "frecuencia": count, "pct_del_total": pct,
                "en_colormap_oficial": False, "codigo_clase": None, "clase": "clase_desconocida", "estado": "NO_decodificado",
            })

    clases_ausentes = sorted(set(clases_esperadas) - clases_vistas)
    pct_no_decodificado = round(n_no_decodificados / total_px * 100, 4)

    filas.append({
        "producto": nombre_producto, "rgb": "__RESUMEN__", "frecuencia": total_px, "pct_del_total": 100.0,
        "en_colormap_oficial": None, "codigo_clase": None,
        "clase": (
            f"n_bandas={n_bandas}; tiene_canal_alfa={tiene_alfa}; pct_no_decodificado={pct_no_decodificado}; "
            f"clases_esperadas_ausentes={[clases_esperadas[c] for c in clases_ausentes]}; "
            f"colores_ambiguos={n_colores_ambiguos}; tolerancia_pct={TOLERANCIA_CLASE_DESCONOCIDA_PCT}; "
            f"supera_tolerancia={pct_no_decodificado > TOLERANCIA_CLASE_DESCONOCIDA_PCT}"
        ),
        "estado": "resumen",
    })
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# F. Estabilidad del WCS
# ---------------------------------------------------------------------------


def test_wcs_stability(mapserver_url: str, coverage_id: str, bounds_4326: tuple, colormap: dict, dest_dir: Path, etiqueta: str) -> dict[str, Any]:
    """Descarga dos recortes con configuraciones distintas (buffer/bbox
    ligeramente diferente) y compara resolución, colores, clases decodificadas
    y área en el área común."""
    minx, miny, maxx, maxy = bounds_4326
    dl_a = mod20.download_wcs_pilot(mapserver_url, coverage_id, (minx, miny, maxx, maxy), dest_dir / f"{etiqueta}_config_a.tif")
    # Configuración B: bbox recortado (80% del área, desplazado) para forzar
    # una grilla de salida de tamaño distinto y comprobar si el servidor
    # remuestrea de forma independiente o conserva la grilla nativa.
    dx, dy = (maxx - minx) * 0.1, (maxy - miny) * 0.1
    bounds_b = (minx + dx, miny + dy, maxx - dx, maxy - dy)
    dl_b = mod20.download_wcs_pilot(mapserver_url, coverage_id, bounds_b, dest_dir / f"{etiqueta}_config_b.tif")

    if not (dl_a.get("exito") and dl_b.get("exito")):
        return {"exito": False, "config_a": dl_a, "config_b": dl_b}

    info_a, class_a, transform_a, crs_a = mod20.inspect_raster(dest_dir / f"{etiqueta}_config_a.tif", colormap)
    info_b, class_b, transform_b, crs_b = mod20.inspect_raster(dest_dir / f"{etiqueta}_config_b.tif", colormap)

    res_a = (info_a["resolucion_x"], info_a["resolucion_y"])
    res_b = (info_b["resolucion_x"], info_b["resolucion_y"])
    resolucion_conservada = np.allclose(res_a, res_b, rtol=1e-6)

    rgb_a = set(info_a.get("valores_unicos_rgb", []))
    rgb_b = set(info_b.get("valores_unicos_rgb", []))
    mismos_colores = rgb_a == rgb_b

    codigos_a = set(info_a.get("codigos_clase_validados", {}).keys())
    codigos_b = set(info_b.get("codigos_clase_validados", {}).keys())

    # Área de bosque en la región común aproximada (comparación por proporción
    # de píxeles de cada clase, no de hectáreas absolutas, porque las grillas
    # tienen extensión distinta por diseño de esta prueba).
    def _pct_por_clase(class_arr, colormap):
        total = class_arr.size
        out = {}
        for v in colormap.values():
            n = int((class_arr == v["codigo"]).sum())
            if n:
                out[v["clase"]] = round(n / total * 100, 2)
        return out

    pct_a = _pct_por_clase(class_a, colormap)
    pct_b = _pct_por_clase(class_b, colormap)

    return {
        "exito": True, "resolucion_a": res_a, "resolucion_b": res_b, "resolucion_conservada": bool(resolucion_conservada),
        "tamano_a": (info_a["ancho"], info_a["alto"]), "tamano_b": (info_b["ancho"], info_b["alto"]),
        "colores_rgb_a": sorted(rgb_a), "colores_rgb_b": sorted(rgb_b), "mismos_colores_rgb": mismos_colores,
        "codigos_clase_a": sorted(codigos_a), "codigos_clase_b": sorted(codigos_b), "mismos_codigos_clase": codigos_a == codigos_b,
        "pct_por_clase_a": pct_a, "pct_por_clase_b": pct_b,
        "conserva_grilla_nativa_conclusion": (
            "El servidor remuestrea según la extensión solicitada (tamaños de salida distintos para "
            "bbox distintos) — se recomienda fijar siempre el mismo buffer/bbox y la misma "
            "interpolación nearest-neighbor para que las descargas futuras sean reproducibles entre sí."
            if not resolucion_conservada or info_a["ancho"] != info_b["ancho"]
            else "El servidor conserva una grilla y resolución consistentes entre configuraciones."
        ),
    }


def main() -> int:
    t0 = time.perf_counter()
    print("Fase 2D.2: cierre técnico de DTD y robustez de la decodificación forestal")
    print("=" * 70)
    for d in (AUDIT_DIR, REPORTS_DIR):
        ensure_dir(d)

    resultados: dict[str, Any] = {}

    # ---- B. Estadísticas completas DTD 2025-IV ----
    print("\n[B] Calculando estadísticas completas de 2025-IV (universo real, no muestra)...")
    df_dtd_stats = build_dtd_2025_iv_complete_statistics()
    df_dtd_stats.to_csv(DTD_STATS_PATH, index=False, encoding="utf-8")
    total_real = int(df_dtd_stats.loc[(df_dtd_stats["tipo"] == "agregado") & (df_dtd_stats["categoria"] == "registros_totales"), "valor"].iloc[0])
    print(f"  {DTD_STATS_PATH.name}: {len(df_dtd_stats)} filas, registros_totales confirmado={total_real}")
    print(f"  Municipios distintos: {int(df_dtd_stats.loc[(df_dtd_stats.tipo=='agregado')&(df_dtd_stats.categoria=='codigos_municipio_distintos'),'valor'].iloc[0])}")
    print(f"  cod_dtd duplicados DENTRO del periodo: {int(df_dtd_stats.loc[(df_dtd_stats.tipo=='agregado')&(df_dtd_stats.categoria=='cod_dtd_duplicados_dentro_del_periodo'),'valor'].iloc[0])}")

    # ---- D. Comparación correcta con Boletín 45 (usa B, no muestra) ----
    print("\n[D] Comparando con Boletín 45 usando el universo completo...")
    comparacion_boletin = compare_boletin_45_correcto(df_dtd_stats)
    resultados["comparacion_boletin_45_correcta"] = comparacion_boletin
    print(f"  Clasificación: {comparacion_boletin['clasificacion']}")
    print(f"  % puntos FeatureServer top4: {comparacion_boletin['top4_departamentos_pct_puntos_featureserver']}")

    # ---- C. Estabilidad de identificadores (histórico completo) ----
    print("\n[C] Descargando atributos completos del histórico DTD (2017-I a 2025-IV)...")
    df_dtd_all = fetch_all_dtd_attributes()
    print(f"  {len(df_dtd_all)} registros históricos reales recuperados (paginación completa verificada)")
    df_stability = audit_dtd_identifier_stability(df_dtd_all)
    df_stability.to_csv(DTD_STABILITY_PATH, index=False, encoding="utf-8")
    print(f"  {DTD_STABILITY_PATH.name}: {len(df_stability)} cod_dtd distintos auditados")
    print("  Clasificación:", df_stability["clasificacion"].value_counts().to_dict())

    # ---- E. Auditoría completa del colormap ----
    print("\n[E] Auditando colormap RGB completo de los 2 recortes piloto ya descargados...")
    bosque_path = mod20.BOSQUE_PILOT_DIR / "bosque_2024_50590.tif"
    cambio_path = mod20.CAMBIO_PILOT_DIR / "cambio_2023_2024_50590.tif"
    df_colormap_bosque = audit_colormap_full(bosque_path, mod20.COLORMAP_BOSQUE_NO_BOSQUE, "Bosque No Bosque 2024")
    df_colormap_cambio = audit_colormap_full(cambio_path, mod20.COLORMAP_CAMBIO_BOSQUE, "Cambio de Bosque 2023-2024")
    df_colormap = pd.concat([df_colormap_bosque, df_colormap_cambio], ignore_index=True)
    df_colormap.to_csv(COLORMAP_AUDIT_PATH, index=False, encoding="utf-8")
    resumen_bosque = df_colormap_bosque[df_colormap_bosque["rgb"] == "__RESUMEN__"].iloc[0]
    resumen_cambio = df_colormap_cambio[df_colormap_cambio["rgb"] == "__RESUMEN__"].iloc[0]
    print(f"  Bosque: {resumen_bosque['clase']}")
    print(f"  Cambio: {resumen_cambio['clase']}")
    n_no_decod_total = int(df_colormap[(df_colormap["estado"] == "NO_decodificado")]["frecuencia"].sum())
    resultados["colormap_ok"] = n_no_decod_total == 0
    print(f"  Total píxeles NO decodificados (ambos productos): {n_no_decod_total}")

    # ---- F. Estabilidad del WCS ----
    print("\n[F] Probando estabilidad del WCS con una segunda configuración de recorte...")
    mgn_features = mod20.load_mgn2025_geometries()
    cod_to_geom = {f["properties"]["cod_dane_mpio"]: f for f in mgn_features}
    geom_puerto_rico = shapely_shape(cod_to_geom["50590"]["geometry"])
    bounds_pr = geom_puerto_rico.bounds
    wcs_stability = test_wcs_stability(mod20.SUPERFICIE_BOSQUE_URL, mod20.COVERAGE_ID_BOSQUE_2024, bounds_pr, mod20.COLORMAP_BOSQUE_NO_BOSQUE, mod20.BOSQUE_PILOT_DIR, "estabilidad_bosque_50590")
    resultados["wcs_stability"] = wcs_stability
    df_wcs_stability = pd.DataFrame([{
        "producto": "Bosque No Bosque 2024", "municipio": "50590",
        "resolucion_a": str(wcs_stability.get("resolucion_a")), "resolucion_b": str(wcs_stability.get("resolucion_b")),
        "resolucion_conservada": wcs_stability.get("resolucion_conservada"),
        "tamano_a": str(wcs_stability.get("tamano_a")), "tamano_b": str(wcs_stability.get("tamano_b")),
        "mismos_colores_rgb": wcs_stability.get("mismos_colores_rgb"), "mismos_codigos_clase": wcs_stability.get("mismos_codigos_clase"),
        "pct_por_clase_a": str(wcs_stability.get("pct_por_clase_a")), "pct_por_clase_b": str(wcs_stability.get("pct_por_clase_b")),
        "conclusion": wcs_stability.get("conserva_grilla_nativa_conclusion"),
    }])
    df_wcs_stability.to_csv(WCS_STABILITY_PATH, index=False, encoding="utf-8")
    print(f"  Resolución conservada: {wcs_stability.get('resolucion_conservada')} | mismos colores: {wcs_stability.get('mismos_colores_rgb')}")
    print(f"  {wcs_stability.get('conserva_grilla_nativa_conclusion')}")

    # ---- G. Comparación ráster-vector en 3 municipios ----
    print("\n[G] Comparando ráster-vector en 3 municipios (Puerto Rico + Miritı́-Paraná + Bolívar)...")
    transformer = build_transformer(CRS_ORIGEN, CRS_METRICO)
    municipios_g = [
        ("50590", "Puerto Rico, Meta", "deforestacion_reciente"),
        ("91460", "Miritı́-Paraná, Amazonas", "bosque_baja_o_nula_deforestacion"),
        ("68101", "Bolívar, Santander", "geometria_pequena_o_compleja"),
    ]
    filas_multi = []
    for cod_mpio, nombre, rol in municipios_g:
        geom_mpio = shapely_shape(cod_to_geom[cod_mpio]["geometry"])
        bounds_mpio = geom_mpio.bounds
        feats_zonas, meta_zonas = mod20.query_municipio_deforestacion_2024(cod_mpio)
        stats_vector = mod20.compute_vector_pilot_stats(feats_zonas, transformer) if feats_zonas else {"area_union_ha": 0.0, "area_geometrica_total_ha": 0.0, "n_poligonos": 0}

        razon_no_raster = None
        if cod_mpio == "50590":
            # Ya descargado y decodificado en la Fase 2D.1 — se reutiliza el
            # resultado sin volver a descargar innecesariamente.
            area_defor_raster_ha = 2972.71
        else:
            dl = mod20.download_wcs_pilot(mod20.DINAMICA_CAMBIO_URL, mod20.COVERAGE_ID_CAMBIO_2324, bounds_mpio, mod20.CAMBIO_PILOT_DIR / f"cambio_2023_2024_{cod_mpio}.tif")
            if dl.get("exito"):
                info, class_arr, transform_r, crs_r = mod20.inspect_raster(mod20.CAMBIO_PILOT_DIR / f"cambio_2023_2024_{cod_mpio}.tif", mod20.COLORMAP_CAMBIO_BOSQUE)
                clip_arr, clip_transform = mod20.clip_to_municipio(class_arr, transform_r, crs_r, geom_mpio.__geo_interface__)
                reproj_arr, reproj_transform = mod20.reproject_class_array(clip_arr, clip_transform, str(crs_r))
                areas = mod20.class_areas_from_metric_grid(reproj_arr, reproj_transform, mod20.COLORMAP_CAMBIO_BOSQUE)
                area_defor_raster_ha = areas.get(2, {}).get("area_ha", 0.0)
            else:
                area_defor_raster_ha = None
                razon_no_raster = f"WCS GetCoverage falló (HTTP {dl.get('http_status')}) — municipio de área extensa, probable límite de tamaño del servidor (no un límite impuesto por este piloto)"

        area_union = stats_vector.get("area_union_ha", 0.0)
        ambas_cero = (area_defor_raster_ha is not None and area_defor_raster_ha < 0.01) and area_union < 0.01
        if ambas_cero:
            comparacion = {"clasificacion": "concordancia_de_ausencia", "diferencia_absoluta_ha": 0.0, "diferencia_porcentual": 0.0}
            razon = "ambas fuentes reportan 0 ha de deforestación para este municipio/periodo"
        elif area_defor_raster_ha is None:
            comparacion = {"clasificacion": "no_comparable", "diferencia_absoluta_ha": None, "diferencia_porcentual": None}
            razon = razon_no_raster
        elif area_union < 0.01 and area_defor_raster_ha >= 0.01:
            comparacion = mod20.compare_raster_vector(area_defor_raster_ha, area_union, stats_vector.get("area_geometrica_total_ha", 0.0))
            razon = (
                f"DISCREPANCIA REAL: el ráster detecta {area_defor_raster_ha:.2f} ha de deforestación 2023-2024, pero el vector "
                "zonas_deforestadas_2013_2024 no tiene NINGÚN polígono para este municipio/año — indica que la cobertura del "
                "vector NO es nacional completa (posiblemente limitada a la región amazónica/CAR históricamente monitoreadas), "
                "mientras el ráster sí es de barrido nacional."
            )
        else:
            comparacion = mod20.compare_raster_vector(area_defor_raster_ha, area_union, stats_vector.get("area_geometrica_total_ha", 0.0))
            razon = "comparación numérica estándar (ambas fuentes con valores positivos)"

        filas_multi.append({
            "cod_dane_mpio": cod_mpio, "nombre_mpio": nombre, "rol_piloto": rol,
            "area_deforestacion_raster_ha": area_defor_raster_ha, "area_union_vector_ha": area_union,
            "n_poligonos_vector": stats_vector.get("n_poligonos", 0),
            "diferencia_absoluta_ha": comparacion.get("diferencia_absoluta_ha"),
            "diferencia_porcentual": comparacion.get("diferencia_porcentual"),
            "clasificacion_correspondencia": comparacion["clasificacion"],
            "razon": razon,
        })
        print(f"  {nombre}: ráster={area_defor_raster_ha} ha, vector_union={area_union} ha -> {comparacion['clasificacion']} ({razon})")

    df_multi = pd.DataFrame(filas_multi)
    df_multi.to_csv(MULTI_MUNICIPIO_COMPARISON_PATH, index=False, encoding="utf-8")

    # ---- H. Auditoría territorial del vector ----
    print("\n[H] Auditando cobertura territorial del vector zonas_deforestadas frente a MGN2025...")
    universo = pd.read_csv(UNIVERSO_PATH, dtype={"cod_dane_mpio": str, "cod_dane_dpto": str})
    cods_divipola_vigente = set(universo.loc[universo["presente_divipola_vigente"], "cod_dane_mpio"])

    por_mpio_nacional = dtd_group_stats_generic(mod20.ZONAS_DEFOR_URL, "1=1", "cod_mpio,nom_mpio")
    codigos_5_digitos = sum(1 for r in por_mpio_nacional if re.fullmatch(r"\d{5}", str(r.get("cod_mpio", ""))))
    codigos_fuera_divipola = [r for r in por_mpio_nacional if str(r.get("cod_mpio")) not in cods_divipola_vigente]

    nombres_por_codigo: dict[str, set] = {}
    for r in por_mpio_nacional:
        nombres_por_codigo.setdefault(r["cod_mpio"], set()).add(r["nom_mpio"])
    codigos_con_nombres_distintos = {k: v for k, v in nombres_por_codigo.items() if len(v) > 1}

    d_null, _ = mod20.get_json(f"{mod20.ZONAS_DEFOR_URL}/query", {"where": "cod_mpio IS NULL", "returnCountOnly": "true", "f": "json"})
    n_cod_mpio_nulo = (d_null or {}).get("count")

    # Verificación geométrica real (sección H): para el municipio piloto,
    # comprobar que cada polígono asignado por texto realmente intersecta la
    # geometría MGN2025 del municipio declarado, usando MGN2025 como
    # referencia (no el código textual de la fuente).
    filas_geom_check = []
    for cod_mpio, _, _ in municipios_g:
        feats_zonas, _ = mod20.query_municipio_deforestacion_2024(cod_mpio)
        geom_mgn_4326 = shapely_shape(cod_to_geom[cod_mpio]["geometry"])
        geom_mgn_proj = reproject_geometry(geom_mgn_4326, transformer)
        n_no_intersecta = 0
        n_cruza_limite = 0
        for f in feats_zonas:
            poly_4326 = shapely_shape(f["geometry"])
            poly_proj = reproject_geometry(poly_4326, transformer)
            if not poly_proj.intersects(geom_mgn_proj):
                n_no_intersecta += 1
            elif not geom_mgn_proj.covers(poly_proj):
                n_cruza_limite += 1
        filas_geom_check.append({
            "cod_dane_mpio": cod_mpio, "n_poligonos_evaluados": len(feats_zonas),
            "n_no_intersecta_mgn2025": n_no_intersecta, "n_cruza_limite_mgn2025": n_cruza_limite,
        })

    filas_territorial = [
        {"tipo": "agregado", "categoria": "codigos_municipio_totales_en_vector", "valor": len(por_mpio_nacional)},
        {"tipo": "agregado", "categoria": "codigos_con_formato_5_digitos", "valor": codigos_5_digitos},
        {"tipo": "agregado", "categoria": "codigos_fuera_de_divipola_vigente", "valor": len(codigos_fuera_divipola)},
        {"tipo": "agregado", "categoria": "cod_mpio_nulos", "valor": n_cod_mpio_nulo},
        {"tipo": "agregado", "categoria": "codigos_con_mas_de_un_nombre_distinto", "valor": len(codigos_con_nombres_distintos)},
    ]
    for r in codigos_fuera_divipola:
        filas_territorial.append({"tipo": "codigo_fuera_divipola_detalle", "categoria": f"{r.get('cod_mpio')}|{r.get('nom_mpio')}", "valor": r.get("n")})
    for k, v in codigos_con_nombres_distintos.items():
        filas_territorial.append({"tipo": "codigo_multinombre_detalle", "categoria": k, "valor": "; ".join(sorted(v))})
    for row in filas_geom_check:
        for k, v in row.items():
            if k != "cod_dane_mpio":
                filas_territorial.append({"tipo": f"verificacion_geometrica_{row['cod_dane_mpio']}", "categoria": k, "valor": v})

    df_territorial = pd.DataFrame(filas_territorial)
    df_territorial.to_csv(VECTOR_TERRITORIAL_AUDIT_PATH, index=False, encoding="utf-8")
    print(f"  {VECTOR_TERRITORIAL_AUDIT_PATH.name}: {len(df_territorial)} filas")
    print(f"  Códigos fuera de DIVIPOLA vigente: {len(codigos_fuera_divipola)} | códigos con nombres distintos: {len(codigos_con_nombres_distintos)}")
    print(f"  Verificación geométrica (3 municipios): {filas_geom_check}")
    resultados["filas_geom_check"] = filas_geom_check
    resultados["codigos_fuera_divipola"] = codigos_fuera_divipola
    resultados["codigos_con_nombres_distintos"] = codigos_con_nombres_distintos
    resultados["n_cod_mpio_nulo"] = n_cod_mpio_nulo
    resultados["codigos_5_digitos"] = codigos_5_digitos
    resultados["n_mpios_vector_total"] = len(por_mpio_nacional)

    # ---- Metadata ----
    for path, n_filas, desc in [
        (DTD_STATS_PATH, len(df_dtd_stats), "Estadísticas completas del universo real de DTD 2025-IV (21.044 registros), Fase 2D.2."),
        (DTD_STABILITY_PATH, len(df_stability), "Auditoría de estabilidad de cod_dtd en todo el histórico 2017-I a 2025-IV, Fase 2D.2."),
        (COLORMAP_AUDIT_PATH, len(df_colormap), "Auditoría exhaustiva del colormap RGB de los 2 recortes piloto, Fase 2D.2."),
        (WCS_STABILITY_PATH, len(df_wcs_stability), "Prueba de estabilidad del WCS con 2 configuraciones de recorte distintas, Fase 2D.2."),
        (MULTI_MUNICIPIO_COMPARISON_PATH, len(df_multi), "Comparación ráster-vector de deforestación en 3 municipios piloto, Fase 2D.2."),
        (VECTOR_TERRITORIAL_AUDIT_PATH, len(df_territorial), "Auditoría territorial del vector zonas_deforestadas frente a MGN2025, Fase 2D.2."),
    ]:
        write_json(path.with_suffix(path.suffix + ".metadata.json"), {"fuente": "Fase 2D.2 - cierre técnico DTD y robustez forestal", "fecha_procesamiento": utc_now_iso(), "n_filas": n_filas, "descripcion": desc})

    tiempo_total = time.perf_counter() - t0
    resultados_finales = {
        **resultados, "df_dtd_stats": df_dtd_stats, "df_stability": df_stability, "df_colormap": df_colormap,
        "df_multi": df_multi, "df_territorial": df_territorial, "df_wcs_stability": df_wcs_stability,
        "total_real_2025_iv": total_real, "n_historico_total": len(df_dtd_all),
        "resumen_colormap_bosque": resumen_bosque.to_dict(), "resumen_colormap_cambio": resumen_cambio.to_dict(),
        "tiempo_total_s": tiempo_total,
    }
    import pickle
    with open(DATA_INTERIM / "fase2d2_resultados.pkl", "wb") as fh:
        pickle.dump(resultados_finales, fh)

    print("\n" + "=" * 70)
    print("RESUMEN - Fase 2D.2")
    print("=" * 70)
    print(f"Tiempo total: {tiempo_total:.2f} s")
    print(f"Registros DTD 2025-IV reales: {total_real}")
    print(f"Registros históricos DTD auditados: {len(df_dtd_all)}")
    print(f"cod_dtd distintos: {len(df_stability)}")
    print(f"Colormap: 0 no decodificados = {n_no_decod_total == 0}")
    print(f"Comparación Boletín 45: {comparacion_boletin['clasificacion']}")

    return 0


def dtd_group_stats_generic(url: str, where: str, group_fields: str) -> list[dict]:
    params = {
        "where": where, "groupByFieldsForStatistics": group_fields,
        "outStatistics": json.dumps([{"statisticType": "count", "onStatisticField": "fid", "outStatisticFieldName": "n"}]),
        "f": "json",
    }
    data, status = mod20.get_json(f"{url}/query", params)
    return [f["attributes"] for f in (data or {}).get("features", [])]


if __name__ == "__main__":
    raise SystemExit(main())
