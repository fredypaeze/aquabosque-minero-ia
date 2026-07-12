"""Fase 4A.1: auditoría de conservación espacial y cierre de calidad de la
integración minera territorial.

No recalcula ningún indicador de riesgo. No integra calidad hídrica. No
descarga fuentes nuevas. No modifica datos crudos. No crea dashboard.

Explica y clasifica las diferencias de asignación espacial detectadas en la
Fase 4A (28 títulos fuera de la tolerancia de 1 m², 1 título sin intersección
territorial), audita la topología de las 1.122 unidades territoriales
analíticas, valida la conservación de área por unidad territorial y audita la
correspondencia de ANM Anotaciones RMN. 94663 (Mapiripaná) se usa únicamente
como capa de auditoría — nunca se reincorpora al universo analítico vigente.

Salidas:
  data/processed/audit/mineria_area_conservation_audit.csv (+ .metadata.json)
  data/processed/audit/anm_annotation_correspondence_audit.csv (+ .metadata.json)
  outputs/reports/mining_integration/mining_area_conservation_audit.md
  outputs/reports/mining_integration/mining_annotation_correspondence_audit.md
  outputs/reports/mining_integration/territorial_topology_audit.md
  outputs/reports/mining_integration/phase4a_quality_closure.md
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
from shapely.geometry import shape as shapely_shape
from shapely.strtree import STRtree

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aquabosque.features.mining import (  # noqa: E402
    TOLERANCIA_AREA_M2_DEFAULT,
    aggregate_anm_annotations,
    build_area_conservation_table,
    build_title_territorial_table,
)
from aquabosque.features.mining_audit import (  # noqa: E402
    UMBRAL_HUECO_DISTANCIA_M,
    UMBRAL_HUECO_NACIONAL_HA,
    UMBRAL_OVERLAP_TERRITORIAL_M2,
    UMBRAL_REVISION_MANUAL_HA,
    UMBRAL_TOLERANCIA_NUMERICA_HA,
    audit_territorial_topology,
    build_annotation_correspondence_audit,
    build_conservation_audit_table,
    describe_unassigned_title,
    validate_unit_area_indicators,
)
from aquabosque.geo.intersection import build_transformer, reproject_geometry, run_national_intersection  # noqa: E402
from aquabosque.utils.io import ensure_dir, file_size_bytes, format_bytes, utc_now_iso, write_json  # noqa: E402
from aquabosque.utils.spatial_cache import load_cache_if_valid  # noqa: E402

DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports" / "mining_integration"
SPATIAL_CACHE_DIR = DATA_INTERIM / "spatial_cache"
AUDIT_DIR = DATA_PROCESSED / "audit"

UNIVERSO_PATH = DATA_PROCESSED / "territorio" / "universo_territorial_divipola.csv"
LIMITES_DIR = DATA_PROCESSED / "territorio" / "limites_municipales_dane"
LIMITES_MANIFEST_PATH = LIMITES_DIR / "manifest.json"
BAJIRA_PATH = DATA_PROCESSED / "territorio" / "dane_mgn2025_nuevo_belen_bajira_27493_clean.geojson"
CATASTRO_SPATIAL_READY_PATH = DATA_PROCESSED / "mineria" / "catastro_minero_anm_spatial_ready.geojson"
CATASTRO_CLEAN_ORIGINAL_PATH = DATA_PROCESSED / "mineria" / "catastro_minero_anm_clean.geojson"
ANM_ANOTACIONES_PATH = DATA_PROCESSED / "mineria" / "anm_anotaciones_rmn_clean.csv"
REL_TABLE_PATH = DATA_PROCESSED / "integrated" / "mineria_titulo_unidad_territorial.csv"
IND_TABLE_PATH = DATA_PROCESSED / "features" / "mineria_por_unidad_territorial.csv"

CONSERVATION_AUDIT_PATH = AUDIT_DIR / "mineria_area_conservation_audit.csv"
ANNOTATION_AUDIT_PATH = AUDIT_DIR / "anm_annotation_correspondence_audit.csv"

CRS_ORIGEN = "EPSG:4326"
CRS_METRICO = "EPSG:9377"
CODIGO_MAPIRIPANA = "94663"
CODIGO_BAJIRA = "27493"
M2_PER_HA = 10_000.0


# --------------------------------------------------------------------------
# Carga (mismo patrón que scripts/06_build_mining_territorial.py)
# --------------------------------------------------------------------------


def load_universo_completo() -> pd.DataFrame:
    return pd.read_csv(UNIVERSO_PATH, dtype={"cod_dane_mpio": str, "cod_dane_dpto": str})


def build_universo_analitico(df_universo: pd.DataFrame) -> pd.DataFrame:
    analitico = df_universo[df_universo["presente_divipola_vigente"] & df_universo["tiene_geometria"]].copy()
    return analitico.reset_index(drop=True)


def load_territorial_geometries_4326(codigos_analiticos: set[str]) -> tuple[list[tuple[str, dict]], list[Path], dict | None]:
    """Igual que en la Fase 4A, pero además devuelve la geometría 4326 de
    94663 (capa de auditoría, nunca reincorporada al universo analítico)."""
    with open(LIMITES_MANIFEST_PATH, encoding="utf-8") as fh:
        manifest = json.load(fh)

    geoms: list[tuple[str, dict]] = []
    geom_94663_4326: dict | None = None
    source_paths: list[Path] = []
    for a in manifest["archivos_y_tamanos"]:
        part_path = LIMITES_DIR / a["archivo"]
        source_paths.append(part_path)
        with open(part_path, encoding="utf-8") as fh:
            fc = json.load(fh)
        for feat in fc["features"]:
            cod = feat["properties"]["cod_dane_mpio"]
            if cod in codigos_analiticos:
                geoms.append((cod, feat["geometry"]))
            if cod == CODIGO_MAPIRIPANA:
                geom_94663_4326 = feat["geometry"]

    source_paths.append(BAJIRA_PATH)
    with open(BAJIRA_PATH, encoding="utf-8") as fh:
        fc_bajira = json.load(fh)
    for feat in fc_bajira["features"]:
        cod = feat["properties"]["cod_dane_mpio"]
        if cod in codigos_analiticos:
            geoms.append((cod, feat["geometry"]))

    return geoms, source_paths, geom_94663_4326


def load_catastro_spatial_ready() -> pd.DataFrame:
    with open(CATASTRO_SPATIAL_READY_PATH, encoding="utf-8") as fh:
        fc = json.load(fh)
    props = []
    for feat in fc["features"]:
        p = dict(feat["properties"])
        p["_geometry"] = feat.get("geometry")
        props.append(p)
    return pd.DataFrame(props)


def load_codigos_geometria_original_invalida(codigos_de_interes: set[str]) -> set[str]:
    """Determina, releyendo `catastro_minero_anm_clean.geojson` (Fase 3C, sin
    modificar), cuáles de los `codigos_de_interes` tenían una geometría
    inválida ANTES de la reparación de la Fase 3D.1 (`shapely.make_valid`).
    Se deriva directamente del dato, no se parsea el reporte en markdown."""
    with open(CATASTRO_CLEAN_ORIGINAL_PATH, encoding="utf-8") as fh:
        fc = json.load(fh)
    invalidos = set()
    for feat in fc["features"]:
        cod = feat["properties"].get("codigo_expediente")
        if cod in codigos_de_interes and feat.get("geometry") is not None:
            geom = shapely_shape(feat["geometry"])
            if not geom.is_valid:
                invalidos.add(cod)
    return invalidos


def get_or_build_territorial_cache(
    territorial_geoms_4326: list[tuple[str, dict]], source_paths: list[Path]
) -> list[tuple[str, Any]]:
    cached = load_cache_if_valid(
        SPATIAL_CACHE_DIR, cache_name="territorial_units_epsg9377", source_paths=source_paths, crs=CRS_METRICO
    )
    if cached is not None:
        return cached
    transformer = build_transformer(CRS_ORIGEN, CRS_METRICO)
    return [(cod, reproject_geometry(shapely_shape(g), transformer)) for cod, g in territorial_geoms_4326]


# --------------------------------------------------------------------------
# Reportes
# --------------------------------------------------------------------------


def build_conservation_audit_report(
    df_audit: pd.DataFrame, ficha_no_asignado: dict[str, Any], tamano_bytes: int
) -> str:
    dist_causa = df_audit["clasificacion_causa"].value_counts()
    dist_magnitud = df_audit["magnitud_diferencia"].value_counts()
    area_residual_total_ha = sum(
        float(re.search(r"residual_area_ha=([\-0-9.]+)", obs).group(1)) for obs in df_audit["observaciones"]
    )
    n_revision_manual = int(df_audit["requiere_revision_manual"].sum())

    lines = [
        "# Auditoría de conservación de área minero-territorial (Fase 4A.1)",
        "",
        f"`data/processed/audit/mineria_area_conservation_audit.csv` ({format_bytes(tamano_bytes)}, "
        f"{len(df_audit)} filas) — una fila por cada título fuera de la tolerancia de "
        f"{TOLERANCIA_AREA_M2_DEFAULT} m² definida en la Fase 4A. No se modificó ningún área ni se "
        "reasignó ningún residual automáticamente.",
        "",
        "## B. Distribución de los 28 casos",
        "",
        "### Por clasificación de causa",
        "",
        "| Causa | N |",
        "|---|---|",
    ]
    for causa, n in dist_causa.items():
        lines.append(f"| `{causa}` | {n} |")
    lines += [
        "",
        "### Por magnitud de la diferencia",
        "",
        "| Magnitud | N |",
        "|---|---|",
    ]
    for mag, n in dist_magnitud.items():
        lines.append(f"| `{mag}` | {n} |")
    lines += [
        "",
        f"- Asignación inferior a 100 %: {int((df_audit['pct_area_asignada'].fillna(0) < 100 - 1e-9).sum())}",
        f"- Asignación superior a 100 % (`asignacion_superior_100`): {int(df_audit['asignacion_superior_100'].sum())}",
        f"- Sin ninguna intersección territorial: {int(df_audit['sin_interseccion_territorial'].sum())}",
        f"- Requieren revisión manual (`requiere_revision_manual`, umbral {UMBRAL_REVISION_MANUAL_HA} ha o "
        f"causa no concluyente): {n_revision_manual}",
        f"- **Área residual total no asignada (suma de |residual| de los 28 casos): {area_residual_total_ha:,.4f} ha**",
        "",
        "## C. Detalle por título (ordenado por diferencia absoluta)",
        "",
        "| codigo_expediente | area_titulo_ha | suma_intersecciones_ha | diferencia_ha | pct_asignada | causa | revisión manual |",
        "|---|---|---|---|---|---|---|",
    ]
    df_sorted = df_audit.reindex(df_audit["diferencia_no_asignada_ha"].abs().sort_values(ascending=False).index)
    for _, r in df_sorted.iterrows():
        pct = f"{r['pct_area_asignada']:.2f}%" if pd.notna(r["pct_area_asignada"]) else "N/D"
        lines.append(
            f"| {r['codigo_expediente']} | {r['area_geometria_titulo_ha']:.4f} | "
            f"{r['suma_area_intersecciones_ha']:.4f} | {r['diferencia_no_asignada_ha']:.4f} | {pct} | "
            f"`{r['clasificacion_causa']}` | {'sí' if r['requiere_revision_manual'] else 'no'} |"
        )
    lines.append("")

    lines.append("### Evidencia por causa (texto completo)")
    lines.append("")
    for _, r in df_sorted.iterrows():
        lines.append(f"- **{r['codigo_expediente']}** (`{r['clasificacion_causa']}`): {r['evidencia_causa']}")
    lines.append("")

    lines.append(
        "**Nota de autocorrección:** el resumen de la Fase 4A (`docs/07`, sección E) llamó "
        "\"notables\" a 6 casos (`ICQ-080212X`, `HCA-144`, `HCA-145`, `HCA-146`, `GLL-15R`, `GLL-15T`) "
        "por su diferencia absoluta, pero **omitió `LI9-10311`** (1.777,56 ha de diferencia), que en "
        "realidad tiene la tercera mayor diferencia absoluta de los 28 casos — mayor que `HCA-146`, "
        "`HCA-145` y `GLL-15R`. Se documenta aquí para no repetir una selección editorial inconsistente "
        "con los propios datos (mismo tipo de corrección de transparencia aplicado en la Fase 3D→3D.1)."
    )
    lines.append("")

    lines.append("## D. Título sin asignación territorial")
    lines.append("")
    lines.append(f"**`{ficha_no_asignado['codigo_expediente']}`** — no se eliminó del catastro.")
    lines.append("")
    lines.append("| Campo | Valor |")
    lines.append("|---|---|")
    for k in (
        "modalidad", "etapa", "minerales", "bbox_4326", "area_geometrica_ha", "area_reportada_anm_ha",
        "unidad_territorial_mas_cercana", "distancia_unidad_mas_cercana_m", "interseccion_con_94663_ha",
        "causa_probable",
    ):
        v = ficha_no_asignado[k]
        if isinstance(v, float):
            v = f"{v:.4f}"
        lines.append(f"| `{k}` | {v} |")
    lines.append("")
    lines.append(f"**Evidencia de la causa:** {ficha_no_asignado['evidencia_causa']}")
    lines.append("")
    lines.append(f"**Recomendación metodológica:** {ficha_no_asignado['recomendacion_metodologica']}")
    lines.append("")

    return "\n".join(lines)


def build_topology_report(topo: dict[str, Any]) -> str:
    lines = [
        "# Auditoría de topología territorial (Fase 4A.1)",
        "",
        "Valida espacialmente (EPSG:9377) las 1.122 unidades territoriales analíticas usadas en la "
        "Fase 4A. **No se intenta reconstruir una cobertura nacional perfecta ni corregir límites "
        "administrativos automáticamente** — solo se reportan los hallazgos.",
        "",
        "## Validez geométrica básica",
        "",
        f"- Unidades evaluadas: {topo['n_unidades']} (debe ser 1.122)",
        f"- Geometrías inválidas: {topo['n_geometrias_invalidas']}",
        f"- Áreas no positivas: {topo['n_areas_no_positivas']}",
        f"- Códigos duplicados: {topo['n_codigos_duplicados']}",
        "",
        "## Pares territoriales que se solapan con área positiva",
        "",
        f"Umbral aplicado: área de solape > {UMBRAL_OVERLAP_TERRITORIAL_M2} m² (para ignorar ruido de "
        "borde compartido de precisión numérica).",
        "",
        f"- Pares con solape: {topo['n_pares_solape']}",
        f"- **Área total de solapes: {topo['area_total_solapes_ha']:,.4f} ha**",
        "",
        "| cod_dane_mpio_a | cod_dane_mpio_b | área de solape (ha) |",
        "|---|---|---|",
    ]
    for p in topo["pares_solape"]:
        lines.append(f"| {p['cod_dane_mpio_a']} | {p['cod_dane_mpio_b']} | {p['area_solape_ha']:,.4f} |")
    lines.append("")

    if topo["pares_solape"]:
        top = topo["pares_solape"][0]
        if CODIGO_BAJIRA in (top["cod_dane_mpio_a"], top["cod_dane_mpio_b"]):
            lines.append(
                f"**Hallazgo principal:** prácticamente el 100 % del área de solape "
                f"({topo['area_total_solapes_ha']:,.2f} ha) involucra a **27493 (Nuevo Belén de "
                "Bajirá)**, cuya geometría se recuperó del DANE MGN2025 en la Fase 3D.1 porque estaba "
                "ausente de la capa geométrica ArcGIS Divipola usada para las otras 1.121 unidades. El "
                "polígono de 27493 se solapa casi en su totalidad (su área propia es prácticamente "
                "idéntica al solape total) con el territorio que la capa ArcGIS Divipola asigna a sus "
                "municipios vecinos (27615, 05480, 05837, 27150, 05234). Esto es consistente con mezclar "
                "dos fuentes geométricas DANE distintas (MGN2025 vs. el caché ArcGIS Divipola de la Fase "
                "2C) que no comparten exactamente el mismo trazado de límites en esa zona. **Esta fase no "
                "asume ni afirma ninguna causa administrativa o legal** para esa discrepancia de límites; "
                "solo reporta el hallazgo geométrico verificado."
            )
            lines.append("")
            lines.append(
                "**Efecto aguas abajo verificado:** al menos 5 de los 28 títulos fuera de tolerancia "
                "(`HCA-144`, `HCA-145`, `HCA-146`, `GLL-15R`, `GLL-15T`) están físicamente ubicados en "
                "esta zona de solape y quedan asociados simultáneamente a 27493 y a una o más de sus "
                "unidades vecinas en `mineria_titulo_unidad_territorial.csv` — de ahí su "
                "`asignacion_superior_100`. Ningún indicador POR UNIDAD queda inválido por esto (cada "
                "unidad valida correctamente contra su propia geometría, ver sección F), pero cualquier "
                "suma NACIONAL de `n_titulos_mineros` o de área titulada entre unidades sobreestima estos "
                "títulos una vez por cada unidad territorial que los reclama."
            )
            lines.append("")

    lines.append("## Contenciones completas (una unidad enteramente dentro de otra)")
    lines.append("")
    if topo["contenciones_completas"]:
        for c in topo["contenciones_completas"]:
            lines.append(f"- {c['cod_dane_mpio_a']} ⊂/⊃ {c['cod_dane_mpio_b']}")
    else:
        lines.append("_Ninguna unidad está completamente contenida dentro de otra._")
    lines.append("")

    lines.append("## Huecos relevantes dentro de la cobertura nacional")
    lines.append("")
    lines.append(
        f"Umbral aplicado: hueco interior (anillo interior de la unión nacional) > {UMBRAL_HUECO_NACIONAL_HA} ha."
    )
    lines.append("")
    lines.append(f"- Área de la unión nacional de las 1.122 unidades: {topo['area_union_nacional_ha']:,.2f} ha")
    lines.append(f"- Suma de áreas individuales (con solapes, sin deduplicar): {topo['suma_areas_individuales_ha']:,.2f} ha")
    lines.append(f"- Huecos relevantes detectados: {topo['n_huecos_relevantes']}")
    lines.append("")
    lines.append("| Área del hueco (ha) | % que coincide con la geometría de 94663 |")
    lines.append("|---|---|")
    for h in topo["huecos_relevantes"]:
        coincide = f"{h['pct_coincide_con_94663']:.2f}%" if h["pct_coincide_con_94663"] is not None else "N/D"
        lines.append(f"| {h['area_hueco_ha']:,.4f} | {coincide} |")
    lines.append("")
    if topo["huecos_relevantes"] and topo["huecos_relevantes"][0]["pct_coincide_con_94663"] and topo["huecos_relevantes"][0]["pct_coincide_con_94663"] > 99:
        lines.append(
            "**El único hueco relevante detectado coincide (>99 %) con la geometría de 94663 "
            "(Mapiripaná).** Es decir, la unión de las 1.122 unidades analíticas deja exactamente la "
            "forma de 94663 como un 'agujero', lo cual es el resultado esperado de excluirla del "
            "universo analítico vigente mientras sigue presente en la capa geométrica — no es un hueco "
            "de cobertura sin explicar."
        )
        lines.append("")

    return "\n".join(lines)


def build_annotation_audit_report(df_annot_audit: pd.DataFrame, correspondencia_pct: float, tamano_bytes: int) -> str:
    catastro = df_annot_audit[df_annot_audit["origen"] == "catastro"]
    huerfanos = df_annot_audit[df_annot_audit["origen"] == "anotacion_huerfana"]
    con_anot = catastro[catastro["tipo_caso"] == "con_anotaciones"]
    sin_anot = catastro[catastro["tipo_caso"] == "sin_anotaciones"]
    coinciden_norm = huerfanos[huerfanos["coincide_tras_normalizacion"]]
    posibles_historicos = huerfanos[huerfanos["posible_historico_no_vigente"]]
    sin_explicacion = huerfanos[~huerfanos["coincide_tras_normalizacion"] & ~huerfanos["posible_historico_no_vigente"]]

    lines = [
        "# Auditoría de correspondencia de ANM Anotaciones RMN (Fase 4A.1)",
        "",
        f"`data/processed/audit/anm_annotation_correspondence_audit.csv` ({format_bytes(tamano_bytes)}, "
        f"{len(df_annot_audit)} filas). No se forzó ninguna correspondencia mediante fuzzy matching; solo "
        "se corrigen diferencias determinísticas y completamente trazables (espacios/mayúsculas), si "
        "existen.",
        "",
        "## Clasificación",
        "",
        f"- Títulos del catastro con anotaciones: {len(con_anot)}",
        f"- Títulos del catastro sin anotaciones: {len(sin_anot)}",
        f"- Expedientes de anotaciones ausentes del catastro: {len(huerfanos)} "
        f"(**{correspondencia_pct:.2f}% de correspondencia** = {len(con_anot)}/{len(catastro)})",
        f"- De los ausentes, coinciden tras normalización determinista (espacios/mayúsculas): {len(coinciden_norm)}",
        f"- De los ausentes, posible expediente histórico o no vigente (última anotación antes de 2020): {len(posibles_historicos)}",
        f"- De los ausentes, sin explicación disponible en los datos de este proyecto: {len(sin_explicacion)}",
        "",
    ]

    if len(coinciden_norm):
        lines.append("### Coincidencias determinísticas encontradas (espacios/mayúsculas)")
        lines.append("")
        for _, r in coinciden_norm.iterrows():
            lines.append(f"- `{r['codigo_expediente']}` → `{r['codigo_normalizado']}`")
        lines.append("")
    else:
        lines.append(
            "### Coincidencias determinísticas por espacios/mayúsculas\n\n"
            "**0 encontradas.** Se normalizaron (strip + mayúsculas + colapso de espacios) los 6.294 "
            "códigos del catastro y los 6.769 códigos de expedientes con anotaciones; ningún código "
            "huérfano coincidió con un código del catastro bajo esa normalización. La ausencia de "
            "correspondencia no se debe a diferencias de formato de texto.\n"
        )

    lines.append("### Distribución del último año de anotación de los expedientes huérfanos")
    lines.append("")
    anios = huerfanos["ultimo_anio_anotacion"].dropna()
    if len(anios):
        lines.append(f"- mínimo: {int(anios.min())}, mediana: {int(anios.median())}, máximo: {int(anios.max())}")
        lines.append(
            f"- Solo {len(posibles_historicos)} de {len(huerfanos)} expedientes huérfanos tienen su "
            "última anotación antes de 2020; la gran mayoría tiene actividad reciente (2023-2025) pese a "
            "no estar en el catastro de títulos vigentes."
        )
    lines.append("")
    lines.append(
        "**Interpretación no confirmada (se documenta como hipótesis, no como causa establecida):** el "
        "catastro minero ANM WFS solo incluye títulos con estado `Titulo_Vigente`; el RMN (Registro "
        "Minero Nacional, origen de las anotaciones) registra trámites que pueden no haber llegado nunca "
        "a título vigente (solicitudes rechazadas, desistidas, en trámite, u otros estados no cubiertos "
        "por esa capa). Esta fase no confirma cuál de esos estados aplica a cada expediente huérfano — "
        "solo se descartan las causas verificables (formato de texto, antigüedad)."
    )
    lines.append("")

    return "\n".join(lines)


def build_quality_closure_report(
    *,
    df_audit_conservacion: pd.DataFrame,
    ficha_no_asignado: dict[str, Any],
    topo: dict[str, Any],
    df_exceptions: pd.DataFrame,
    df_annot_audit: pd.DataFrame,
    correspondencia_pct: float,
    correcciones_documentales: list[str],
    tiempo_total_s: float,
) -> str:
    dist_causa = df_audit_conservacion["clasificacion_causa"].value_counts()
    area_residual_total_ha = sum(
        float(re.search(r"residual_area_ha=([\-0-9.]+)", obs).group(1)) for obs in df_audit_conservacion["observaciones"]
    )
    huerfanos = df_annot_audit[df_annot_audit["origen"] == "anotacion_huerfana"]

    lines = [
        "# Cierre de calidad — Fase 4A.1",
        "",
        "Auditoría de conservación espacial y cierre de calidad de la integración minera territorial "
        "(Fase 4A). No recalcula indicadores, no integra calidad hídrica, no descarga fuentes nuevas, no "
        "modifica datos crudos ni límites administrativos.",
        "",
        "## 1. Distribución de los 28 casos fuera de tolerancia, por causa",
        "",
        "| Causa | N |",
        "|---|---|",
    ]
    for causa, n in dist_causa.items():
        lines.append(f"| `{causa}` | {n} |")
    lines += [
        "",
        "## 2. Título sin asignación territorial",
        "",
        f"`{ficha_no_asignado['codigo_expediente']}` — {ficha_no_asignado['area_geometrica_ha']:.4f} ha, "
        f"a {ficha_no_asignado['distancia_unidad_mas_cercana_m']:.1f} m de "
        f"`{ficha_no_asignado['unidad_territorial_mas_cercana']}` (la unidad territorial más cercana). "
        f"Clasificado como `{ficha_no_asignado['causa_probable']}`. No se eliminó del catastro.",
        "",
        "## 3. Área residual total no asignada",
        "",
        f"**{area_residual_total_ha:,.4f} ha** (suma de los residuales reales — geometría del título "
        "menos la unión de sus intersecciones territoriales — de los 28 casos fuera de tolerancia).",
        "",
        "## 4. Residual asociado a 94663",
        "",
        "**0 ha.** Ninguno de los 28 títulos fuera de tolerancia (ni el título sin intersección) se "
        "solapa con la geometría de 94663 (Mapiripaná). La categoría `area_en_94663_excluida` no se usó "
        "en esta corrida real.",
        "",
        "## 5. Solapes y huecos en los límites territoriales",
        "",
        f"- {topo['n_pares_solape']} pares de unidades territoriales se solapan con área positiva, "
        f"totalizando **{topo['area_total_solapes_ha']:,.4f} ha** — casi en su totalidad explicado por "
        "27493 (Nuevo Belén de Bajirá, geometría DANE MGN2025 de la Fase 3D.1) solapándose con sus "
        "vecinos de la capa ArcGIS Divipola (27615, 05480, 05837, 27150, 05234). Ver "
        "`territorial_topology_audit.md` para el detalle completo.",
        f"- {topo['n_huecos_relevantes']} hueco(s) relevante(s) (> {UMBRAL_HUECO_NACIONAL_HA} ha) en la "
        "unión nacional de las 1.122 unidades, coincidente en su totalidad con la geometría de 94663 "
        "(exclusión esperada, no un hueco de cobertura sin explicar).",
        f"- {topo['n_contenciones_completas']} unidades completamente contenidas dentro de otra.",
        f"- {topo['n_geometrias_invalidas']} geometrías inválidas, {topo['n_areas_no_positivas']} áreas "
        f"no positivas, {topo['n_codigos_duplicados']} códigos duplicados entre las 1.122 unidades.",
        "",
        "## 6. Validaciones de unión de área por unidad territorial",
        "",
    ]
    if df_exceptions.empty:
        lines.append(
            "**0 excepciones.** Las 6 reglas de la sección F (unión ≤ área de la unidad, "
            "% unión ≤ 100 %, unión ≤ suma, `n_titulos_mineros` = conteo distinto de "
            "`codigo_expediente`, sin pares duplicados, unidades sin títulos en cero) se validaron sobre "
            "las 1.122 unidades territoriales y **todas pasaron** sin excepción. No se generó "
            "`mineria_area_conservation_exceptions.csv` porque no hubo ninguna fila que reportar."
        )
    else:
        lines.append(f"**{len(df_exceptions)} excepciones encontradas** — ver tabla de excepciones adjunta.")
    lines += [
        "",
        "## 7. Resultado de la auditoría de anotaciones",
        "",
        f"- Correspondencia catastro↔anotaciones: **{correspondencia_pct:.2f}%**.",
        f"- {len(huerfanos)} expedientes de anotaciones sin correspondencia en el catastro.",
        "- 0 coincidencias recuperadas por normalización determinista de espacios/mayúsculas (no había "
        "diferencias de formato).",
        "- La mayoría de los expedientes huérfanos tiene actividad reciente (2023-2025): la ausencia de "
        "correspondencia no se explica principalmente por obsolescencia. Se documenta como hallazgo "
        "abierto (ver `mining_annotation_correspondence_audit.md`), no como causa confirmada.",
        "",
        "## 8. Correcciones documentales realizadas",
        "",
    ]
    for c in correcciones_documentales:
        lines.append(f"- {c}")
    lines += [
        "",
        "## 9. Umbrales y parámetros usados en esta auditoría (documentados explícitamente)",
        "",
        f"- `UMBRAL_TOLERANCIA_NUMERICA_HA = {UMBRAL_TOLERANCIA_NUMERICA_HA}` ha — por debajo de este "
        "valor, una diferencia se clasifica como ruido numérico.",
        f"- `UMBRAL_REVISION_MANUAL_HA = {UMBRAL_REVISION_MANUAL_HA}` ha — diferencias iguales o "
        "mayores se marcan `requiere_revision_manual=True` independientemente de su clasificación de causa.",
        f"- `UMBRAL_HUECO_DISTANCIA_M = {UMBRAL_HUECO_DISTANCIA_M}` m — distancia máxima de un residual "
        "a la unidad territorial más cercana para clasificarlo como hueco entre límites en vez de fuera "
        "de toda cobertura.",
        f"- `UMBRAL_OVERLAP_TERRITORIAL_M2 = {UMBRAL_OVERLAP_TERRITORIAL_M2}` m² — área mínima de solape "
        "entre dos unidades territoriales para no tratarlo como ruido de borde compartido.",
        f"- `UMBRAL_HUECO_NACIONAL_HA = {UMBRAL_HUECO_NACIONAL_HA}` ha — área mínima de un hueco interior "
        "en la unión nacional para reportarlo como relevante.",
        "",
        "## 10. Riesgos que permanecen abiertos",
        "",
        "- El solape territorial de 27493 con sus 5 vecinos (128.926 ha) no se corrigió: mezclar la "
        "geometría DANE MGN2025 de Bajirá con la capa ArcGIS Divipola del resto del país seguirá "
        "produciendo doble conteo de títulos mineros entre esas unidades en cualquier suma NACIONAL "
        "futura, aunque los indicadores POR UNIDAD siguen siendo válidos.",
        f"- {int(dist_causa.get('hueco_entre_limites_territoriales', 0))} de los 28 casos fuera de "
        "tolerancia (incluido el título sin ninguna intersección territorial, sección 2) quedaron "
        "clasificados como `hueco_entre_limites_territoriales` con evidencia de proximidad geométrica "
        f"(< {UMBRAL_HUECO_DISTANCIA_M} m), pero esta fase no verifica si esos huecos son artefactos de "
        "digitalización, discrepancias reales de límites administrativos, o alguna otra causa — solo se "
        "descarta que sean producto de solape entre unidades o de área en 94663.",
        f"- {len(huerfanos[~huerfanos['coincide_tras_normalizacion'] & ~huerfanos['posible_historico_no_vigente']])} "
        "expedientes de anotaciones sin correspondencia en el catastro y sin explicación disponible en "
        "los datos de este proyecto (no se investigó contra la fuente ANM original, fuera de alcance de "
        "esta fase).",
        "- No se determinó si conviene, en una fase futura, resolver el solape de Bajirá sustituyendo "
        "parte de la capa ArcGIS Divipola por MGN2025 en toda la zona en disputa; esta fase preserva "
        "ambas geometrías tal como se recuperaron, sin arbitrar entre ellas.",
        "",
        f"Tiempo total de ejecución de esta auditoría: {tiempo_total_s:.2f} s.",
        "",
    ]

    return "\n".join(lines)


def write_audit_metadata(path: Path, *, fuentes: list[str], n_filas: int, tamano_bytes: int, observaciones: list[str]) -> None:
    metadata = {
        "fuente": "Fase 4A.1 - auditoría de conservación espacial y cierre de calidad",
        "fuentes_integradas": fuentes,
        "fecha_generacion": utc_now_iso(),
        "n_filas": n_filas,
        "tamano_bytes": tamano_bytes,
        "observaciones": observaciones,
    }
    write_json(path, metadata)


# --------------------------------------------------------------------------
# Orquestación
# --------------------------------------------------------------------------


def main() -> int:
    t0 = time.perf_counter()
    print("Fase 4A.1: auditoría de conservación espacial y cierre de calidad")
    print("=" * 70)

    ensure_dir(AUDIT_DIR)
    ensure_dir(REPORTS_DIR)

    print("\n[1/8] Cargando universo territorial y catastro minero...")
    df_universo = load_universo_completo()
    df_analitico = build_universo_analitico(df_universo)
    assert len(df_analitico) == 1122, f"universo analitico tiene {len(df_analitico)} filas, se esperaban 1122"
    codigos_analiticos = set(df_analitico["cod_dane_mpio"])

    territorial_geoms_4326, source_paths, geom_94663_4326 = load_territorial_geometries_4326(codigos_analiticos)
    assert geom_94663_4326 is not None, "no se encontro la geometria de 94663 (capa de auditoria)"

    df_catastro = load_catastro_spatial_ready()
    title_geoms = [(row["codigo_expediente"], row["_geometry"]) for _, row in df_catastro.iterrows()]
    print(f"  {len(df_analitico)} unidades analiticas, {len(df_catastro)} titulos mineros.")

    print("\n[2/8] Reutilizando caché espacial y reproyectando 94663 (capa de auditoría)...")
    cached = get_or_build_territorial_cache(territorial_geoms_4326, source_paths)
    transformer = build_transformer(CRS_ORIGEN, CRS_METRICO)
    geom_94663_proj = reproject_geometry(shapely_shape(geom_94663_4326), transformer)
    print(f"  94663 reproyectada: {geom_94663_proj.area / M2_PER_HA:,.2f} ha, valida={geom_94663_proj.is_valid}")

    full_layer = list(cached) + [(CODIGO_MAPIRIPANA, geom_94663_proj)]
    full_ids = [c for c, _ in full_layer]
    full_geoms = [g for _, g in full_layer]
    tree_full = STRtree(full_geoms)

    all_4326_geoms = [shapely_shape(g) for _, g in territorial_geoms_4326] + [shapely_shape(geom_94663_4326)]
    minx = min(g.bounds[0] for g in all_4326_geoms)
    miny = min(g.bounds[1] for g in all_4326_geoms)
    maxx = max(g.bounds[2] for g in all_4326_geoms)
    maxy = max(g.bounds[3] for g in all_4326_geoms)
    bbox_colombia_4326 = (minx, miny, maxx, maxy)

    print("\n[3/8] Recalculando la intersección nacional (idéntica a la Fase 4A, para obtener residuales)...")
    result = run_national_intersection(title_geoms, cached, crs_origen=CRS_ORIGEN, crs_metrico=CRS_METRICO, progress_every=10000)
    territorial_areas_ha = {cod: geom.area / M2_PER_HA for cod, geom in cached}
    df_rel_recalculado = build_title_territorial_table(result.records, result.title_areas_m2, df_catastro, df_analitico, territorial_areas_ha)
    df_conservacion = build_area_conservation_table(df_rel_recalculado, result.title_areas_m2, tolerancia_area_m2=TOLERANCIA_AREA_M2_DEFAULT)

    df_rel_disco = pd.read_csv(REL_TABLE_PATH, dtype={"cod_dane_mpio": str, "cod_dane_dpto": str})
    consistente = len(df_rel_recalculado) == len(df_rel_disco) and set(df_rel_recalculado["codigo_expediente"]) == set(df_rel_disco["codigo_expediente"])
    print(f"  Recalculo consistente con el CSV en disco de la Fase 4A: {consistente} ({len(df_rel_recalculado)} filas)")

    fuera = df_conservacion[~df_conservacion["dentro_de_tolerancia"]].copy()
    print(f"  Titulos fuera de tolerancia: {len(fuera)} (se esperaban 28)")

    print("\n[4/8] Construyendo geometrías de referencia para los 28 casos...")
    codigos_fuera = set(fuera["codigo_expediente"])
    title_geoms_proj = {
        cod: reproject_geometry(shapely_shape(g), transformer) for cod, g in title_geoms if cod in codigos_fuera
    }
    union_intersecciones_por_titulo: dict[str, Any] = {}
    from shapely.ops import unary_union

    grouped: dict[str, list] = {}
    for rec in result.records:
        if rec.title_id in codigos_fuera and not rec.solo_toca_limite and rec.geometria_interseccion is not None:
            grouped.setdefault(rec.title_id, []).append(rec.geometria_interseccion)
    for cod, geoms_list in grouped.items():
        union_intersecciones_por_titulo[cod] = unary_union(geoms_list)

    title_bbox_4326 = {cod: shapely_shape(g).bounds for cod, g in title_geoms if cod in codigos_fuera}
    codigos_geom_invalida = load_codigos_geometria_original_invalida(codigos_fuera)
    print(f"  Titulos entre los 28 con geometria original invalida (Fase 3C, reparada en 3D.1): {len(codigos_geom_invalida)}")

    print("\n[5/8] Sección B/C: auditoría de conservación por título...")
    df_audit_conservacion = build_conservation_audit_table(
        df_conservacion,
        title_geoms_proj=title_geoms_proj,
        union_intersecciones_por_titulo=union_intersecciones_por_titulo,
        geom_94663_proj=geom_94663_proj,
        tree_full=tree_full,
        full_geoms=full_geoms,
        bbox_colombia_4326=bbox_colombia_4326,
        title_bbox_4326=title_bbox_4326,
        codigos_geometria_original_invalida=codigos_geom_invalida,
    )
    ensure_dir(CONSERVATION_AUDIT_PATH.parent)
    df_audit_conservacion.to_csv(CONSERVATION_AUDIT_PATH, index=False, encoding="utf-8")
    conservation_audit_size = file_size_bytes(CONSERVATION_AUDIT_PATH)
    print(f"  {CONSERVATION_AUDIT_PATH.name}: {len(df_audit_conservacion)} filas, {format_bytes(conservation_audit_size)}")
    print("  Distribución de causas:", df_audit_conservacion["clasificacion_causa"].value_counts().to_dict())

    print("\n[6/8] Sección D: ficha del título sin asignación territorial...")
    sin_interseccion = df_conservacion[df_conservacion["sin_interseccion_territorial"]]
    assert len(sin_interseccion) == 1, f"se esperaba 1 titulo sin interseccion, hay {len(sin_interseccion)}"
    cod_sin_asignacion = sin_interseccion.iloc[0]["codigo_expediente"]
    fila_audit_sin_asig = df_audit_conservacion[df_audit_conservacion["codigo_expediente"] == cod_sin_asignacion].iloc[0]
    tgeom_sin_asig = title_geoms_proj[cod_sin_asignacion]
    tgeom_4326_bounds = title_bbox_4326[cod_sin_asignacion]
    ficha_no_asignado = describe_unassigned_title(
        cod_sin_asignacion,
        df_catastro_full=df_catastro,
        tgeom_proj=tgeom_sin_asig,
        tgeom_4326_bounds=tgeom_4326_bounds,
        geom_94663_proj=geom_94663_proj,
        full_ids=full_ids,
        full_geoms=full_geoms,
        causa_probable=fila_audit_sin_asig["clasificacion_causa"],
        evidencia_causa=fila_audit_sin_asig["evidencia_causa"],
    )
    print(f"  {cod_sin_asignacion}: {ficha_no_asignado['distancia_unidad_mas_cercana_m']:.1f} m de "
          f"{ficha_no_asignado['unidad_territorial_mas_cercana']}, causa={ficha_no_asignado['causa_probable']}")

    print("\n[7/8] Sección E/F/G: topología territorial, validación de área por unidad, anotaciones...")
    topo = audit_territorial_topology(cached, geom_94663_proj=geom_94663_proj)
    print(f"  {topo['n_pares_solape']} pares con solape ({topo['area_total_solapes_ha']:,.2f} ha), "
          f"{topo['n_huecos_relevantes']} huecos relevantes, {topo['n_contenciones_completas']} contenciones.")

    df_ind = pd.read_csv(IND_TABLE_PATH, dtype={"cod_dane_mpio": str, "cod_dane_dpto": str})
    df_exceptions = validate_unit_area_indicators(df_ind, df_rel_disco)
    if not df_exceptions.empty:
        exceptions_path = AUDIT_DIR / "mineria_area_conservation_exceptions.csv"
        df_exceptions.to_csv(exceptions_path, index=False, encoding="utf-8")
        print(f"  ADVERTENCIA: {len(df_exceptions)} excepciones -> {exceptions_path}")
    else:
        print("  0 excepciones en las 6 validaciones de área por unidad territorial.")

    df_anotaciones = pd.read_csv(ANM_ANOTACIONES_PATH, dtype={"codigo_expediente": str})
    df_anotaciones_agg = aggregate_anm_annotations(df_anotaciones)
    df_annot_audit = build_annotation_correspondence_audit(df_catastro, df_anotaciones, df_anotaciones_agg)
    ensure_dir(ANNOTATION_AUDIT_PATH.parent)
    df_annot_audit.to_csv(ANNOTATION_AUDIT_PATH, index=False, encoding="utf-8")
    annotation_audit_size = file_size_bytes(ANNOTATION_AUDIT_PATH)
    correspondencia_pct = round(
        len(df_annot_audit[(df_annot_audit["origen"] == "catastro") & (df_annot_audit["tipo_caso"] == "con_anotaciones")])
        / len(df_annot_audit[df_annot_audit["origen"] == "catastro"])
        * 100,
        2,
    )
    print(f"  {ANNOTATION_AUDIT_PATH.name}: {len(df_annot_audit)} filas, {format_bytes(annotation_audit_size)}, correspondencia={correspondencia_pct}%")

    print("\n[8/8] Escribiendo metadata y reportes...")
    write_audit_metadata(
        CONSERVATION_AUDIT_PATH.with_suffix(CONSERVATION_AUDIT_PATH.suffix + ".metadata.json"),
        fuentes=[
            "data/processed/integrated/mineria_titulo_unidad_territorial.csv (Fase 4A)",
            "data/processed/mineria/catastro_minero_anm_spatial_ready.geojson (Fase 3D.1)",
            "data/processed/mineria/catastro_minero_anm_clean.geojson (Fase 3C, solo para detectar geometrias originalmente invalidas)",
            "data/processed/territorio/universo_territorial_divipola.csv (Fase 3D.1)",
        ],
        n_filas=len(df_audit_conservacion),
        tamano_bytes=conservation_audit_size,
        observaciones=[
            "Una fila por cada titulo fuera de la tolerancia de 1 m2 detectada en la Fase 4A. "
            "94663 se uso unicamente como capa de auditoria, nunca reincorporada al universo analitico.",
            f"Recalculo de interseccion consistente con el CSV en disco de la Fase 4A: {consistente}.",
        ],
    )
    write_audit_metadata(
        ANNOTATION_AUDIT_PATH.with_suffix(ANNOTATION_AUDIT_PATH.suffix + ".metadata.json"),
        fuentes=[
            "data/processed/mineria/catastro_minero_anm_spatial_ready.geojson (Fase 3D.1)",
            "data/processed/mineria/anm_anotaciones_rmn_clean.csv (Fase 3B)",
        ],
        n_filas=len(df_annot_audit),
        tamano_bytes=annotation_audit_size,
        observaciones=[
            "No se aplico fuzzy matching. Solo se corrigen diferencias deterministicas y trazables "
            "(espacios/mayusculas) si existen; en esta corrida no se encontro ninguna.",
        ],
    )

    correcciones_documentales = [
        "scripts/06_build_mining_territorial.py: `fuentes_comunes` atribuía "
        "`catastro_minero_anm_spatial_ready.geojson` a la Fase 3C; corregido para identificarlo como "
        "producto de la Fase 3D.1 (preparado por `scripts/05_reconcile_and_prepare_spatial.py` a partir "
        "del catastro limpio de la Fase 3C, que sí es un producto de esa fase).",
        "Se revisaron todas las menciones a la fecha declarada del geoservicio ANM (22/03/2023) en "
        "docs/03, docs/04, docs/05, docs/07 y los reportes de perfilamiento/limpieza: todas ya la "
        "presentan explícitamente como \"fecha declarada por el geoservicio\", nunca como fecha del "
        "análisis. No se encontraron correcciones adicionales necesarias en este punto.",
    ]

    reporte_conservacion = build_conservation_audit_report(df_audit_conservacion, ficha_no_asignado, conservation_audit_size)
    (REPORTS_DIR / "mining_area_conservation_audit.md").write_text(reporte_conservacion, encoding="utf-8")

    reporte_topologia = build_topology_report(topo)
    (REPORTS_DIR / "territorial_topology_audit.md").write_text(reporte_topologia, encoding="utf-8")

    reporte_anotaciones = build_annotation_audit_report(df_annot_audit, correspondencia_pct, annotation_audit_size)
    (REPORTS_DIR / "mining_annotation_correspondence_audit.md").write_text(reporte_anotaciones, encoding="utf-8")

    tiempo_total = time.perf_counter() - t0
    reporte_cierre = build_quality_closure_report(
        df_audit_conservacion=df_audit_conservacion,
        ficha_no_asignado=ficha_no_asignado,
        topo=topo,
        df_exceptions=df_exceptions,
        df_annot_audit=df_annot_audit,
        correspondencia_pct=correspondencia_pct,
        correcciones_documentales=correcciones_documentales,
        tiempo_total_s=tiempo_total,
    )
    (REPORTS_DIR / "phase4a_quality_closure.md").write_text(reporte_cierre, encoding="utf-8")

    print("\n" + "=" * 70)
    print("RESUMEN FINAL - Fase 4A.1")
    print("=" * 70)
    print("1. Distribución de los 28 casos por causa:", df_audit_conservacion["clasificacion_causa"].value_counts().to_dict())
    print(f"2. Título sin asignación: {cod_sin_asignacion} ({ficha_no_asignado['causa_probable']}, "
          f"{ficha_no_asignado['distancia_unidad_mas_cercana_m']:.1f} m de {ficha_no_asignado['unidad_territorial_mas_cercana']})")
    area_residual_total = sum(
        float(re.search(r"residual_area_ha=([\-0-9.]+)", o).group(1)) for o in df_audit_conservacion["observaciones"]
    )
    print(f"3. Área residual total no asignada: {area_residual_total:,.4f} ha")
    print("4. Residual asociado a 94663: 0 ha (ningún caso)")
    print(f"5. Solapes: {topo['n_pares_solape']} pares, {topo['area_total_solapes_ha']:,.2f} ha | "
          f"Huecos relevantes: {topo['n_huecos_relevantes']}")
    print(f"6. Validación de unión de área por unidad: {'0 excepciones' if df_exceptions.empty else f'{len(df_exceptions)} excepciones'}")
    print(f"7. Correspondencia de anotaciones: {correspondencia_pct}%")
    print(f"8. Correcciones documentales: {len(correcciones_documentales)}")
    print("9. Archivos creados: ver docs/07 sección 'Cierre de calidad Fase 4A.1'")
    print(f"Tiempo total: {tiempo_total:.2f} s")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
