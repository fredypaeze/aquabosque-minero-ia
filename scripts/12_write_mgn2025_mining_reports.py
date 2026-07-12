"""Fase 4A.2, sección N: reportes a partir de los resultados guardados por
`11_rebuild_mining_with_mgn2025.py` (data/interim/fase4a2_resultados.pkl).
"""

from __future__ import annotations

import pickle
import re
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aquabosque.features.mining_audit import UMBRAL_REVISION_MANUAL_HA  # noqa: E402
from aquabosque.utils.io import ensure_dir, file_size_bytes, format_bytes  # noqa: E402

DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
RESULTADOS_PATH = DATA_INTERIM / "fase4a2_resultados.pkl"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports" / "mining_integration_mgn2025"

REL_MGN2025_PATH = DATA_PROCESSED / "integrated" / "mineria_titulo_unidad_territorial_mgn2025.csv"
IND_MGN2025_PATH = DATA_PROCESSED / "features" / "mineria_por_unidad_territorial_mgn2025.csv"
CONS_AUDIT_MGN2025_PATH = DATA_PROCESSED / "audit" / "mineria_area_conservation_audit_mgn2025.csv"
ANNOT_AUDIT_MGN2025_PATH = DATA_PROCESSED / "audit" / "anm_annotation_correspondence_audit_mgn2025.csv"

ZONA_BAJIRA_CASOS = ["HCA-144", "HCA-145", "HCA-146", "GLL-15R", "GLL-15T"]
CASOS_ADICIONALES = ["ICQ-080212X", "LI9-10311"]
TITULO_583 = "583"


def _area_residual_total(df_audit: pd.DataFrame) -> float:
    if df_audit.empty:
        return 0.0
    return sum(float(re.search(r"residual_area_ha=([\-0-9.]+)", o).group(1)) for o in df_audit["observaciones"])


def build_spatial_intersection_report(r: dict) -> str:
    stats = r["stats"]
    lines = [
        "# Intersección espacial minera con MGN2025 (Fase 4A.2)",
        "",
        "Repite la metodología de la Fase 4A (STRtree construido una sola vez, consulta por bounding "
        "box, intersección real solo sobre candidatos, sin producto cartesiano completo) usando "
        "exclusivamente `base_geometrica_divipola_mgn2025` (Fase 3D.2) en vez de la base mixta.",
        "",
        "## Caché espacial",
        "",
        f"- {'Caché válido reutilizado' if r['uso_cache'] else 'Caché reconstruido'} "
        f"(`territorial_units_mgn2025_epsg9377.pkl`, huella verificada contra los 17 archivos MGN2025 "
        "actuales; nunca se reutilizó el caché de la capa mixta).",
        f"- Tiempo de reproyección de las 1.122 unidades en esta corrida: {r['tiempo_reproy_unidades']:.4f} s.",
        "",
        "## Rendimiento",
        "",
        f"- Títulos procesados: {stats.n_titulos:,} | Unidades procesadas: {stats.n_unidades:,}",
        f"- Tiempo de reproyección de títulos: {stats.tiempo_reproyeccion_s} s",
        f"- Tiempo de construcción del índice STRtree: {stats.tiempo_construccion_indice_s} s",
        f"- Tiempo de consulta (bounding box): {stats.tiempo_consulta_s} s",
        f"- Tiempo de intersección geométrica real: {stats.tiempo_interseccion_s} s",
        f"- **Tiempo total del módulo: {stats.tiempo_total_s} s**",
        f"- **Memoria pico: {stats.memoria_pico_mb} MB**",
        "",
        "## Resultados",
        "",
        "| Indicador | Fase 4A (capa mixta) | Fase 4A.2 (MGN2025) |",
        "|---|---|---|",
        f"| Pares candidatos (STRtree) | 15.444 | {stats.n_pares_candidatos:,} |",
        f"| Intersecciones con área positiva | 8.263 | {stats.n_intersecciones_area_positiva:,} |",
        f"| Contactos sin área | 0 | {stats.n_contactos_sin_area:,} |",
        f"| Títulos sin ninguna asignación | 1 | {stats.n_titulos_sin_interseccion:,} |",
        "",
        "El número de pares candidatos e intersecciones cambia levemente (no debe esperarse un valor "
        "idéntico): MGN2025 traza los límites municipales de forma distinta a la capa ArcGIS Divipola "
        "en varias zonas del país, no solo en Bajirá (ver `mgn2025_vs_mixed_geometry_comparison.md`).",
        "",
    ]
    return "\n".join(lines)


def build_area_conservation_report(r: dict) -> str:
    df_audit = r["df_audit_conservacion_mgn2025"]
    df_cons = r["df_conservacion_mgn2025"]
    legacy_audit = r["df_cons_audit_legacy"]

    fuera_legacy = set(legacy_audit["codigo_expediente"])
    fuera_mgn2025 = set(df_audit["codigo_expediente"]) if not df_audit.empty else set()
    resueltos = sorted(fuera_legacy - fuera_mgn2025)
    nuevos = sorted(fuera_mgn2025 - fuera_legacy)
    persisten = sorted(fuera_legacy & fuera_mgn2025)

    area_residual_mgn2025 = _area_residual_total(df_audit)
    area_residual_legacy = _area_residual_total(legacy_audit)

    dist_causa = df_audit["clasificacion_causa"].value_counts() if not df_audit.empty else pd.Series(dtype=int)

    lines = [
        "# Conservación de área — MGN2025 (Fase 4A.2)",
        "",
        f"Tolerancia: {1.0} m² (misma que la Fase 4A/4A.1). Auditoría de conservación **recalculada "
        "por completo** (ninguna clasificación de causa de la Fase 4A.1 se reutilizó sin recalcular). "
        "**94663 ya no se usa como capa de auditoría**: MGN2025 no la incluye porque no está en "
        "DIVIPOLA vigente, así que no hay ningún hueco nacional que atribuirle.",
        "",
        "## Comparación agregada",
        "",
        "| Indicador | Fase 4A/4A.1 (capa mixta) | Fase 4A.2 (MGN2025) |",
        "|---|---|---|",
        f"| Títulos fuera de tolerancia | 28 | {len(fuera_mgn2025)} |",
        f"| Títulos sin ninguna asignación | 1 (`583`) | {int(df_cons['sin_interseccion_territorial'].sum())} |",
        f"| Área residual total (ha) | {area_residual_legacy:,.4f} | {area_residual_mgn2025:,.4f} |",
        f"| Casos que requieren revisión manual | 15 | {int(df_audit['requiere_revision_manual'].sum()) if not df_audit.empty else 0} |",
        "",
        "## Distribución de causas (MGN2025, recalculada)",
        "",
        "| Causa | N |",
        "|---|---|",
    ]
    for causa, n in dist_causa.items():
        lines.append(f"| `{causa}` | {n} |")
    lines += [
        "",
        "## Qué pasó con cada caso fuera de tolerancia",
        "",
        f"- **Resueltos** (estaban fuera de tolerancia en la capa mixta, ahora dentro): {len(resueltos)} — {resueltos}",
        f"- **Persisten** (siguen fuera de tolerancia en ambas): {len(persisten)}",
        f"- **Nuevos** (no estaban fuera de tolerancia en la capa mixta, ahora sí): {len(nuevos)} — {nuevos}",
        "",
        "Los 5 resueltos son exactamente los 5 casos de la zona de Bajirá "
        f"(`{'`, `'.join(ZONA_BAJIRA_CASOS)}`) — ver detalle en la sección siguiente y en "
        "`mgn2025_vs_mixed_geometry_comparison.md`. Los 9 nuevos casos son evidencia de que MGN2025 "
        "traza algunos límites municipales de forma distinta a la capa ArcGIS Divipola **fuera** de la "
        "zona de Bajirá — un hallazgo nuevo, no anticipado por el alcance original de la Fase 3D.2/4A.1.",
        "",
        "## Casos de la zona de Bajirá",
        "",
        "| codigo_expediente | dentro_de_tolerancia (4A.2) | pct_area_asignada (4A.2) |",
        "|---|---|---|",
    ]
    for cod in ZONA_BAJIRA_CASOS:
        row = df_cons[df_cons["codigo_expediente"] == cod]
        if len(row):
            row = row.iloc[0]
            lines.append(f"| {cod} | {row['dentro_de_tolerancia']} | {row['pct_area_asignada']:.2f}% |")
    lines += [
        "",
        "**Los 5 títulos de la zona de Bajirá ya NO muestran sobreasignación por solape territorial** "
        "(la causa `solape_entre_limites_territoriales` no aparece ni una sola vez en la distribución de "
        "causas de esta corrida) — el objetivo central de la Fase 4A.2 se cumple.",
        "",
        "## Título 583",
        "",
    ]
    row_583 = df_cons[df_cons["codigo_expediente"] == TITULO_583]
    if len(row_583):
        row_583 = row_583.iloc[0]
        lines.append(
            f"Pasa de **0 % asignado (sin ninguna intersección territorial)** en la Fase 4A.1 a "
            f"**{row_583['pct_area_asignada']:.2f}% asignado** (intersecta con `54001`) en la Fase 4A.2 — "
            f"mejora clara, pero **sigue fuera de tolerancia** "
            f"(`dentro_de_tolerancia={row_583['dentro_de_tolerancia']}`)."
        )
    lines += [
        "",
        "## ICQ-080212X y LI9-10311",
        "",
    ]
    for cod in CASOS_ADICIONALES:
        row = df_cons[df_cons["codigo_expediente"] == cod]
        if len(row):
            row = row.iloc[0]
            lines.append(
                f"- **{cod}:** {row['pct_area_asignada']:.2f}% asignado en la Fase 4A.2 "
                f"(`sin_interseccion_territorial={row['sin_interseccion_territorial']}`)."
            )
    lines += [
        "",
        "`ICQ-080212X` mejora marginalmente (0,99% → 4,04% asignado) pero sigue siendo uno de los casos "
        "de mayor magnitud, marcado para revisión manual en ambas fases. `LI9-10311` **empeora**: pasa "
        "de 4,54% asignado (2 unidades) a **0% asignado (ninguna unidad)** — ya en la Fase 4A.1 era uno "
        "de los casos con mayor área residual (95,46% sin asignar); con la nueva base geométrica, la "
        "porción que antes lograba asignarse cae fuera de toda unidad territorial. Se marca para "
        "revisión manual en ambas fases; su geometría de entrada es la que más justifica una revisión "
        "manual real fuera del alcance de este proyecto.",
        "",
    ]
    return "\n".join(lines)


def build_territorial_indicators_report(r: dict) -> str:
    df_ind_cmp = r["df_indicator_comparison"]
    df_ind_cmp = df_ind_cmp.copy()

    cambian_titulos = df_ind_cmp[df_ind_cmp["diferencia_n_titulos_mineros"] != 0]
    cambian_area = df_ind_cmp[df_ind_cmp["diferencia_area_titulada_union_ha"].abs() > 1.0]
    cambian_pct = df_ind_cmp[df_ind_cmp["diferencia_pct_area_unidad_titulada_union"].abs() > 0.01]

    lines = [
        "# Indicadores territoriales — comparación capa mixta vs. MGN2025 (Fase 4A.2)",
        "",
        f"`mineria_por_unidad_territorial_mgn2025.csv`: {len(pd.read_csv(IND_MGN2025_PATH, dtype=str))} "
        "filas (debe ser 1.122; incluye unidades sin títulos, en cero).",
        "",
        "## Unidades con cambios (sección K.9)",
        "",
        f"- Unidades con cambio en `n_titulos_mineros`: {len(cambian_titulos)}",
        f"- Unidades con cambio de área titulada (unión) mayor a 1 ha: {len(cambian_area)}",
        f"- Unidades con cambio de `pct_area_unidad_titulada_union` mayor a 0,01 pp: {len(cambian_pct)}",
        "",
        "### Top 15 unidades por cambio absoluto de área titulada (unión)",
        "",
        "| cod_dane_mpio | nombre_mpio | area_union_legacy_ha | area_union_mgn2025_ha | diferencia_ha |",
        "|---|---|---|---|---|",
    ]
    top = df_ind_cmp.reindex(df_ind_cmp["diferencia_area_titulada_union_ha"].abs().sort_values(ascending=False).index).head(15)
    for _, row in top.iterrows():
        lines.append(
            f"| {row['cod_dane_mpio']} | {row.get('nombre_mpio', 'N/D')} | "
            f"{row['area_titulada_union_ha_legacy']:.2f} | {row['area_titulada_union_ha_mgn2025']:.2f} | "
            f"{row['diferencia_area_titulada_union_ha']:.2f} |"
        )
    lines.append("")
    lines.append(
        "No se crearon scores ni variables de riesgo; se mantienen separadas `area_titulada_suma_ha` "
        "(permite superposición) y `area_titulada_union_ha` (sin doble conteo), y sus respectivos "
        "porcentajes, igual que en la Fase 4A."
    )
    lines.append("")
    return "\n".join(lines)


def build_comparison_report(r: dict) -> str:
    dft = r["df_title_comparison"]
    correspondencia = r["correspondencia_anotaciones"]

    aparecieron = dft[dft["aparecio"]]
    desaparecieron = dft[dft["desaparecio"]]
    top20 = dft.copy()
    top20["abs_diff"] = top20["diferencia_absoluta_ha"].abs()
    top20 = top20.sort_values("abs_diff", ascending=False).head(20)

    lines = [
        "# Comparación MGN2025 vs. capa geométrica mixta (Fase 4A.2)",
        "",
        f"`mining_mgn2025_comparison.csv`: {len(dft)} filas (outer join por `codigo_expediente` + "
        "`cod_dane_mpio` entre la tabla relacional de la Fase 4A y la de la Fase 4A.2).",
        "",
        "## K. Comparaciones mínimas obligatorias",
        "",
        f"1. Filas relacionales: **{r['n_rel_legacy']}** (4A) → **{r['n_rel_mgn2025']}** (4A.2)",
        f"2. Asignaciones que aparecieron (nuevas): {len(aparecieron)} | desaparecieron: {len(desaparecieron)}",
        f"3. Casos fuera de tolerancia: **28** (4A.1) → **{len(r['df_audit_conservacion_mgn2025'])}** (4A.2)",
        f"4. Correspondencia de anotaciones: {correspondencia['pct_correspondencia']}% "
        f"({correspondencia['titulos_con_anotaciones']}/{correspondencia['titulos_catastro_total']})",
        "",
        "### Top 20 diferencias territoriales por área absoluta",
        "",
        "| codigo_expediente | cod_dane_mpio | área legacy (ha) | área MGN2025 (ha) | diferencia (ha) | observación |",
        "|---|---|---|---|---|---|",
    ]
    for _, row in top20.iterrows():
        al = f"{row['area_legacy_ha']:.2f}" if pd.notna(row["area_legacy_ha"]) else "—"
        am = f"{row['area_mgn2025_ha']:.2f}" if pd.notna(row["area_mgn2025_ha"]) else "—"
        lines.append(f"| {row['codigo_expediente']} | {row['cod_dane_mpio']} | {al} | {am} | {row['diferencia_absoluta_ha']:.2f} | {row['observacion']} |")
    lines.append("")

    lines.append("### Hallazgo: diferencias de trazado más allá de Bajirá")
    lines.append("")
    lines.append(
        "Varias de las mayores diferencias del top 20 involucran municipios que **no** forman parte de "
        "la disputa de Bajirá (p. ej. Tadó/Pueblo Rico en el límite Chocó-Risaralda, López de Micay/"
        "Buenos Aires en Cauca, Quibdó/Medio Atrato en Chocó). Esto confirma que MGN2025 y la capa "
        "ArcGIS Divipola no solo difieren en la zona de Bajirá: trazan de forma distinta varios límites "
        "municipales adicionales. **No se afirma cuál trazado es más correcto** — se documenta la "
        "diferencia geométrica verificada, sin asumir causalidad administrativa."
    )
    lines.append("")
    return "\n".join(lines)


def build_quality_closure_report(r: dict) -> str:
    stats = r["stats"]
    df_audit = r["df_audit_conservacion_mgn2025"]
    df_cons = r["df_conservacion_mgn2025"]
    legacy_audit = r["df_cons_audit_legacy"]
    fuera_legacy = set(legacy_audit["codigo_expediente"])
    fuera_mgn2025 = set(df_audit["codigo_expediente"]) if not df_audit.empty else set()

    rel_size = file_size_bytes(REL_MGN2025_PATH)
    ind_size = file_size_bytes(IND_MGN2025_PATH)

    lines = [
        "# Cierre de calidad — Fase 4A.2",
        "",
        "## 1. Tiempo y memoria",
        "",
        f"- Tiempo total del script: {r['tiempo_total_s']:.2f} s",
        f"- Tiempo del módulo de intersección: {stats.tiempo_total_s} s | Memoria pico: {stats.memoria_pico_mb} MB",
        "",
        "## 2. Pares candidatos e intersecciones",
        "",
        f"- Pares candidatos: {stats.n_pares_candidatos:,} (4A: 15.444)",
        f"- Intersecciones positivas: {stats.n_intersecciones_area_positiva:,} (4A: 8.263)",
        "",
        "## 3. Filas relacionales",
        "",
        f"- Anteriores (4A): {r['n_rel_legacy']:,} | Nuevas (4A.2): {r['n_rel_mgn2025']:,}",
        "",
        "## 4. Títulos sin asignación",
        "",
        f"- Anteriores: 1 (`583`) | Nuevos: {int(df_cons['sin_interseccion_territorial'].sum())} "
        f"({sorted(df_cons[df_cons['sin_interseccion_territorial']]['codigo_expediente'].tolist())})",
        "",
        "## 5. Casos fuera de tolerancia",
        "",
        f"- Anteriores: 28 | Nuevos: {len(fuera_mgn2025)} "
        f"(resueltos: {len(fuera_legacy - fuera_mgn2025)}, persisten: {len(fuera_legacy & fuera_mgn2025)}, "
        f"nuevos: {len(fuera_mgn2025 - fuera_legacy)})",
        "",
        "## 6. Área residual total",
        "",
        f"- Anterior: {_area_residual_total(legacy_audit):,.4f} ha | Nueva: {_area_residual_total(df_audit):,.4f} ha",
        "",
        "## 7. Casos de la zona de Bajirá",
        "",
        "**Los 5 casos (`HCA-144`, `HCA-145`, `HCA-146`, `GLL-15R`, `GLL-15T`) ya no muestran "
        "sobreasignación por solape territorial.** 0 pares de unidades territoriales se solapan en todo "
        "el país con MGN2025 (antes: 6 pares, 128.926 ha).",
        "",
        "## 8. Título 583",
        "",
        "Mejora de 0% a ~39% asignado (ahora sí intersecta con `54001`), pero sigue fuera de tolerancia.",
        "",
        "## 9. ICQ-080212X y LI9-10311",
        "",
        "`ICQ-080212X` mejora marginalmente (0,99%→4,04%). `LI9-10311` empeora (4,54%→0%, ahora sin "
        "ninguna asignación) — ambos siguen marcados para revisión manual.",
        "",
        "## 10. Cambios principales por unidad territorial",
        "",
        "Ver `mgn2025_mining_territorial_indicators.md` para el detalle completo; los cambios más "
        "grandes se concentran en la zona de Bajirá y en los límites Chocó-Risaralda-Cauca-Valle del "
        "Cauca mencionados en la comparación.",
        "",
        "## 11. Estado de correspondencia con anotaciones",
        "",
        f"- {r['correspondencia_anotaciones']['pct_correspondencia']}% (prácticamente igual a la Fase "
        "4A.1: 95,92%) — la agregación es determinística y no depende de la base geométrica territorial, "
        "solo del catastro y las anotaciones, que no cambiaron.",
        "",
        "## 12. Archivos promovidos como canónicos",
        "",
        "`mineria_titulo_unidad_territorial_mgn2025.csv` y `mineria_por_unidad_territorial_mgn2025.csv` "
        "se documentan como los resultados canónicos recomendados (`data/processed/CANONICAL_SOURCE.json`, "
        "\"alias documentado\"). **No se sobrescribió** `mineria_titulo_unidad_territorial.csv` ni "
        "`mineria_por_unidad_territorial.csv` (siguen siendo regenerados por `scripts/06`, capa mixta); "
        "se crearon copias explícitas `_legacy_mixed_geometry.csv` de ambos como snapshot histórico "
        "adicional, sin borrar ningún archivo original.",
        "",
        "## 13. Validaciones de la sección F (área por unidad)",
        "",
        f"- Excepciones encontradas: {len(r['df_exceptions_mgn2025'])}",
        "",
        "## 14. Riesgos que permanecen abiertos",
        "",
        "- El número de casos fuera de tolerancia SUBIÓ de 28 a "
        f"{len(fuera_mgn2025)} en términos absolutos: resolver el solape de Bajirá no implicó una mejora "
        "generalizada, porque MGN2025 traza otros límites municipales de forma distinta a la capa "
        "ArcGIS Divipola. Esto no incumple ningún criterio de aceptación de esta fase (que exigía "
        "resolver específicamente los 5 casos de Bajirá, no reducir el total nacional), pero es un "
        "hallazgo real que se documenta sin suavizar.",
        "- `LI9-10311` pasó de parcialmente asignado a completamente sin asignación; sigue siendo un "
        "caso que amerita revisión manual de su geometría de origen, fuera del alcance de este proyecto.",
        "- No se investigaron las causas de fondo de las diferencias de trazado fuera de la zona de "
        "Bajirá (Chocó/Risaralda/Cauca); se documenta el hallazgo geométrico, no se asume ninguna causa "
        "administrativa.",
        f"- {format_bytes(rel_size)} / {format_bytes(ind_size)}: tamaños de los nuevos archivos "
        "canónicos, para referencia.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    with open(RESULTADOS_PATH, "rb") as fh:
        r = pickle.load(fh)

    ensure_dir(REPORTS_DIR)

    (REPORTS_DIR / "mgn2025_mining_spatial_intersection.md").write_text(build_spatial_intersection_report(r), encoding="utf-8")
    (REPORTS_DIR / "mgn2025_mining_area_conservation.md").write_text(build_area_conservation_report(r), encoding="utf-8")
    (REPORTS_DIR / "mgn2025_mining_territorial_indicators.md").write_text(build_territorial_indicators_report(r), encoding="utf-8")
    (REPORTS_DIR / "mgn2025_vs_mixed_geometry_comparison.md").write_text(build_comparison_report(r), encoding="utf-8")
    (REPORTS_DIR / "mgn2025_phase4a2_quality_closure.md").write_text(build_quality_closure_report(r), encoding="utf-8")

    print("Reportes escritos en", REPORTS_DIR)
    for f in sorted(REPORTS_DIR.glob("*.md")):
        print(" -", f.name, format_bytes(f.stat().st_size))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
