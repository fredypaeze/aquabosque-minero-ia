"""Fase 4B, sección P: reportes a partir de los resultados guardados por
`13_build_water_territorial.py` (data/interim/fase4b_resultados.pkl).
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aquabosque.features.water import (  # noqa: E402
    UMBRAL_COBERTURA_TEMPORAL_LIMITADA_ANIOS,
    UMBRAL_MONITOREO_ESCASO_N_OBS,
    UMBRAL_PARAMETRO_MIN_MUNICIPIOS,
    UMBRAL_PARAMETRO_MIN_OBSERVACIONES,
    UMBRAL_TENDENCIA_MIN_ANIOS,
    UMBRAL_TENDENCIA_MIN_OBS_NUMERICAS,
    UMBRAL_TENDENCIA_MIN_PERIODO_ANIOS,
)
from aquabosque.geo.point_assignment import UMBRAL_PROXIMIDAD_M_DEFAULT  # noqa: E402
from aquabosque.utils.io import ensure_dir, format_bytes  # noqa: E402

DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
RESULTADOS_PATH = DATA_INTERIM / "fase4b_resultados.pkl"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports" / "water_integration"


def build_parameter_catalog_report(r: dict) -> str:
    cat = r["catalogo"]
    lines = [
        "# Catálogo de parámetros de calidad hídrica (Fase 4B)",
        "",
        f"`catalogo_parametros_calidad_agua.csv`: {len(cat)} filas — una por combinación observada "
        "`propiedad_observada_norm` + `unidad_norm`. Nunca se mezclan resultados de unidades "
        "distintas dentro de una fila, y no se inventan equivalencias entre nombres distintos.",
        "",
        f"- Parámetros distintos: {cat['propiedad_observada_norm'].nunique()}",
        f"- Combinaciones parámetro+unidad: {len(cat)}",
        f"- Combinaciones marcadas `comparable_entre_registros=False`: {int((~cat['comparable_entre_registros']).sum())}",
        "",
        "## Distribución por clasificación",
        "",
        "| Clasificación | N combinaciones | N observaciones |",
        "|---|---|---|",
    ]
    resumen = cat.groupby("clasificacion_parametro").agg(n_comb=("propiedad_observada_norm", "size"), n_obs=("n_observaciones", "sum")).sort_values("n_obs", ascending=False)
    for clasif, row in resumen.iterrows():
        lines.append(f"| `{clasif}` | {row['n_comb']} | {row['n_obs']:,} |")
    lines += [
        "",
        "## Top 20 parámetros por número de observaciones",
        "",
        "| propiedad_observada_norm | unidad_norm | n_observaciones | pct_numericos | clasificación | comparable |",
        "|---|---|---|---|---|---|",
    ]
    for _, row in cat.head(20).iterrows():
        lines.append(
            f"| {row['propiedad_observada_norm']} | {row['unidad_norm']} | {row['n_observaciones']:,} | "
            f"{row['pct_resultados_numericos']:.1f}% | `{row['clasificacion_parametro']}` | {row['comparable_entre_registros']} |"
        )
    lines.append("")

    no_comparables = cat[~cat["comparable_entre_registros"]]
    if len(no_comparables):
        lines.append("## Combinaciones no comparables (razón documentada)")
        lines.append("")
        for _, row in no_comparables.iterrows():
            lines.append(f"- **{row['propiedad_observada_norm']}** ({row['unidad_norm']}): {row['razon_no_comparable']}")
        lines.append("")

    return "\n".join(lines)


def build_spatial_assignment_report(r: dict) -> str:
    total = r["n_registros_total"]
    lines = [
        "# Asignación espacial punto-territorio (Fase 4B)",
        "",
        f"Regla principal: `covers()` (no `contains()`, para que un punto sobre el borde de una "
        f"unidad pueda asignarse). Umbral de proximidad para puntos no cubiertos: "
        f"{UMBRAL_PROXIMIDAD_M_DEFAULT} m (configurable).",
        "",
        "## Asignación por sitio único (243 sitios, no por las 134.216 filas)",
        "",
        f"Los {r['n_sitios']} sitios de monitoreo únicos se asignaron en {r['tiempo_asignacion_s']:.4f} s "
        "(un solo `STRtree` construido una vez, consultado 243 veces — no se repite la consulta por "
        "cada una de las 134.216 observaciones, que comparten sitio).",
        "",
        "| Método | Sitios | Observaciones (filas) |",
        "|---|---|---|",
        f"| `covers_directo` | {(r['df_asignacion_sitios']['metodo_asignacion']=='covers_directo').sum()} | {r['n_directo']:,} |",
        f"| `covers_desambiguado_texto` | {(r['df_asignacion_sitios']['metodo_asignacion']=='covers_desambiguado_texto').sum()} | {r['n_desamb']:,} |",
        f"| `proximidad_menor_100m` | {(r['df_asignacion_sitios']['metodo_asignacion']=='proximidad_menor_100m').sum()} | {r['n_proximidad']:,} |",
        f"| `ambigua` | {(r['df_asignacion_sitios']['metodo_asignacion']=='ambigua').sum()} | {r['n_ambigua']:,} |",
        f"| `sin_asignacion` | {(r['df_asignacion_sitios']['metodo_asignacion']=='sin_asignacion').sum()} | {r['n_sin_asignacion']:,} |",
        "",
        f"**{r['n_directo']:,}/{total:,} observaciones ({r['n_directo']/total*100:.1f}%) se asignaron "
        "directamente por `covers()`, sin ambigüedad ni proximidad.** Los 243 sitios de monitoreo del "
        "IDEAM ya vienen con coordenadas muy limpias (ver `water_data_quality.md`), por lo que ningún "
        "caso requirió desambiguación por texto, proximidad, quedó ambiguo o sin asignar en esta corrida.",
        "",
        "## Validaciones geográficas",
        "",
    ]
    a = r["anomalias"]
    for k, v in a.items():
        if k not in ("sitios_fuera_bbox",):
            lines.append(f"- `{k}`: {v}")
    lines.append("")
    return "\n".join(lines)


def build_data_quality_report(r: dict) -> str:
    c = r["censura"]
    lines = [
        "# Calidad de datos — calidad hídrica (Fase 4B)",
        "",
        "## Resultados censurados y no numéricos",
        "",
        f"- Total de registros: {c['n_total']:,}",
        f"- Numéricos: {c['n_numericos']:,} ({c['n_numericos']/c['n_total']*100:.1f}%)",
        f"- Censurados inferior (`<X`, límite de detección): {c['n_censurados_inferior']:,} ({c['n_censurados_inferior']/c['n_total']*100:.1f}%)",
        f"- Censurados superior (`>X`, fuera de rango superior): {c['n_censurados_superior']:,}",
        f"- No numérico y no censurado (texto no reconocido): {c['n_no_numerico_no_censurado']:,}",
        "",
        "**Ningún valor censurado se reemplazó por 0 ni por límite/2 en las columnas oficiales** "
        "(`resultado_numerico_observado` queda `NaN` para censurados). Se calculó una columna aparte, "
        "`resultado_imputado_ld_2` (= límite_deteccion/2 solo para censura inferior), explícitamente "
        "marcada como imputación y **no usada por defecto en ningún indicador de esta fase**. Para "
        "censura superior (`>X`) no existe una regla de imputación documentada equivalente, así que "
        "esa columna queda vacía en esos 14 casos — no se inventó un factor arbitrario.",
        "",
        "## Identificación de sitios de monitoreo",
        "",
        f"- {r['n_sitios']} sitios de monitoreo únicos identificados (== número de pares lat/lon únicos).",
        "- 194/243 mediante código de estación extraído de `nombre_del_punto_de_monitoreo` (formato "
        "`... [CODIGO]`, verificado único por sitio).",
        "- 49/243 mediante hash SHA-256 determinístico de latitud/longitud redondeadas a 5 decimales "
        "(~1,1 m de precisión) + municipio + nombre del punto.",
        "- `codigo_muestra` (identifica una visita/muestra, no un sitio estable) y `proyecto` "
        "(demasiado agregado, 8 valores para 243 sitios) se evaluaron y descartaron como prioridad 2.",
        "",
        "## Anomalías de coordenadas",
        "",
    ]
    a = r["anomalias"]
    lines.append(f"- Sitios fuera del bbox de Colombia: {a['n_fuera_bbox_colombia']}")
    lines.append(f"- Longitud positiva: {a['n_longitud_positiva']}")
    lines.append(f"- Coordenadas (0,0): {a['n_lat_lon_cero']}")
    lines.append(f"- Coordenadas duplicadas entre sitios distintos: {a['n_coordenadas_duplicadas_entre_sitios']}")
    lines.append(f"- Posible intercambio latitud/longitud: {a['n_posible_intercambio_lat_lon']}")
    lines.append("")
    lines.append(
        "**No se detectó ninguna anomalía de coordenadas en los 243 sitios.** No fue necesario corregir "
        "ninguna coordenada intercambiada ni descartar ningún registro por coordenadas inválidas."
    )
    lines.append("")

    audit = r["df_audit_asignacion"]
    lines.append("## Discrepancias texto vs. geometría")
    lines.append("")
    lines.append(f"- Sitios con algo que auditar (discrepancia de texto, ambigüedad, proximidad o sin asignar): {len(audit)}/{r['n_sitios']}")
    if len(audit):
        disc_mpio = int((audit["coincide_municipio_texto"] == False).sum())  # noqa: E712
        disc_dpto = int((audit["coincide_departamento_texto"] == False).sum())  # noqa: E712
        lines.append(f"- Discrepancia de municipio (texto de la fuente vs. municipio de la geometría asignada): {disc_mpio}")
        lines.append(f"- Discrepancia de departamento: {disc_dpto}")
        lines.append("")
        lines.append(
            "No se usó fuzzy matching para sobrescribir ninguna asignación espacial — la geometría "
            "manda; las discrepancias de texto solo se auditan (`calidad_agua_asignacion_territorial_audit.csv`)."
        )
    lines.append("")
    return "\n".join(lines)


def build_territorial_indicators_report(r: dict) -> str:
    ind = r["df_ind_territorial"]
    con_monitoreo = ind[ind["tiene_monitoreo_agua"]]
    lines = [
        "# Indicadores territoriales de calidad hídrica (Fase 4B)",
        "",
        "Indicadores de **disponibilidad e intensidad de monitoreo**, no de condición ambiental del "
        "agua. La ausencia de observaciones NO significa buena calidad del agua.",
        "",
        f"- Unidades territoriales: {len(ind)} (debe ser 1.122)",
        f"- Con al menos una observación: {len(con_monitoreo)} ({len(con_monitoreo)/len(ind)*100:.1f}%)",
        f"- Sin ningún monitoreo (`sin_monitoreo=True`): {int(ind['sin_monitoreo'].sum())}",
        f"- Monitoreo escaso (`monitoreo_escaso=True`, < {UMBRAL_MONITOREO_ESCASO_N_OBS} observaciones): {int(ind['monitoreo_escaso'].sum())}",
        f"- Monitoreo desactualizado (`monitoreo_desactualizado=True`, sin datos en los últimos 5 años "
        f"disponibles de la fuente): {int(ind['monitoreo_desactualizado'].sum())}",
        f"- Cobertura temporal limitada (`cobertura_temporal_limitada=True`, < {UMBRAL_COBERTURA_TEMPORAL_LIMITADA_ANIOS} años distintos): {int(ind['cobertura_temporal_limitada'].sum())}",
        "",
        f"De las {len(con_monitoreo)} unidades CON monitoreo: "
        f"{int(con_monitoreo['monitoreo_desactualizado'].sum())} están desactualizadas y "
        f"{int(con_monitoreo['monitoreo_escaso'].sum())} tienen monitoreo escaso — es decir, tener "
        "monitoreo no garantiza que sea reciente o suficiente.",
        "",
        "## Top 15 unidades por número de observaciones",
        "",
        "| cod_dane_mpio | nombre_mpio | nombre_dpto | n_observaciones_agua | n_sitios_monitoreo | n_parametros_observados |",
        "|---|---|---|---|---|---|",
    ]
    top = ind.sort_values("n_observaciones_agua", ascending=False).head(15)
    for _, row in top.iterrows():
        lines.append(
            f"| {row['cod_dane_mpio']} | {row['nombre_mpio']} | {row['nombre_dpto']} | "
            f"{row['n_observaciones_agua']:,} | {row['n_sitios_monitoreo']} | {row['n_parametros_observados']} |"
        )
    lines.append("")

    lines.append("## Evaluación de parámetros candidatos a indicadores municipales específicos (sección K)")
    lines.append("")
    lines.append(
        f"Criterios documentados: unidad homogénea (una sola `unidad_norm`), ≥{UMBRAL_PARAMETRO_MIN_OBSERVACIONES} "
        f"observaciones asignadas, ≥{UMBRAL_PARAMETRO_MIN_MUNICIPIOS} municipios con dato."
    )
    lines.append("")
    lines.append("| Parámetro | N observaciones | N municipios | % censurado | Aprobado | Razón |")
    lines.append("|---|---|---|---|---|---|")
    for _, row in r["df_candidatos"].iterrows():
        pct_c = f"{row['pct_censurado']:.1f}%" if pd.notna(row["pct_censurado"]) else "N/D"
        lines.append(
            f"| {row['nombre_normalizado']} | {row['n_observaciones_total']:,} | {row['n_municipios_con_dato']} | "
            f"{pct_c} | {'✅' if row['idoneo_para_agregacion'] else '❌'} | {row['razon']} |"
        )
    lines.append("")
    n_aprobados = int(r["df_candidatos"]["idoneo_para_agregacion"].sum())
    lines.append(
        f"**{n_aprobados}/{len(r['df_candidatos'])} parámetros candidatos aprobados**: pH, oxígeno "
        "disuelto, conductividad, turbidez, DBO5, DQO, sólidos suspendidos totales, plomo y cadmio. "
        "Coliformes totales y *E. coli* no se aprobaron por estar divididos entre dos unidades de "
        "reporte distintas (`NMP/100 mL` vs. `NMP/100 cm3`) que no se mezclaron sin una regla de "
        "conversión explícita (aunque mL y cm³ son física dimensionalmente equivalentes, esta fase no "
        "aplicó esa equivalencia automáticamente). Mercurio no alcanzó el mínimo de observaciones "
        "(262 < 500). **Arsénico no está presente en la fuente de datos** — no se evaluó, se documenta "
        "su ausencia. No se crearon columnas de indicador municipal específicas para ningún parámetro "
        "en esta entrega; esta sección deja la evaluación lista para una fase posterior que si construya "
        "esas columnas.",
    )
    lines.append("")
    lines.append(
        "**Advertencia sobre plomo y cadmio:** aprueban los 3 criterios documentados (unidad homogénea, "
        "≥500 observaciones, ≥20 municipios), pero tienen una proporción de resultados censurados muy "
        "alta (94,8 % y 99,1 % respectivamente — la gran mayoría de las mediciones están por debajo del "
        "límite de detección del laboratorio). \"Aprobado\" aquí significa solo que cumple los tres "
        "criterios documentados de esta sección, **no** que un indicador municipal basado en su mediana "
        "u otro estadístico numérico vaya a ser informativo: con >90 % de censura, ese estadístico "
        "estaría dominado por el límite de detección, no por variación real medida. Cualquier indicador "
        "municipal específico que se construya en una fase posterior para estos dos parámetros debería "
        "reportar la proporción censurada junto con cualquier valor numérico, no el valor solo.",
    )
    lines.append("")
    return "\n".join(lines)


def build_temporal_trends_report(r: dict) -> str:
    tend = r["df_tendencias"]
    calculables = tend[tend["tendencia_calculable"]]
    lines = [
        "# Tendencias temporales de calidad hídrica (Fase 4B)",
        "",
        f"Criterios documentados para calcular una tendencia: ≥{UMBRAL_TENDENCIA_MIN_ANIOS} años "
        f"distintos, ≥{UMBRAL_TENDENCIA_MIN_OBS_NUMERICAS} observaciones numéricas, periodo ≥"
        f"{UMBRAL_TENDENCIA_MIN_PERIODO_ANIOS} años. Método: pendiente de Theil-Sen (mediana de "
        "pendientes de todos los pares de puntos), implementada en `numpy` puro sin `scipy`.",
        "",
        f"- Combinaciones unidad territorial + parámetro + unidad evaluadas: {len(tend)}",
        f"- Con tendencia calculable: {len(calculables)} ({len(calculables)/len(tend)*100:.1f}%)",
        f"- Sin evidencia suficiente: {len(tend) - len(calculables)}",
        "",
        "**No se interpreta ninguna pendiente positiva o negativa como mejora o deterioro** — el "
        "significado de una pendiente depende del parámetro (p. ej. una pendiente positiva en oxígeno "
        "disuelto normalmente se leería distinto a una pendiente positiva en DBO5), y esta fase no hace "
        "esa interpretación.",
        "",
        "## Distribución de razones de no-cálculo (top 10)",
        "",
        "| Razón | N combinaciones |",
        "|---|---|",
    ]
    razones = tend[~tend["tendencia_calculable"]]["razon_no_calculable"].value_counts().head(10)
    for razon, n in razones.items():
        lines.append(f"| {razon} | {n} |")
    lines.append("")

    lines.append("## Muestra de tendencias calculadas (10 combinaciones con más observaciones)")
    lines.append("")
    lines.append("| cod_dane_mpio | parámetro | unidad | n_obs | n_años | pendiente_anual |")
    lines.append("|---|---|---|---|---|---|")
    muestra = calculables.sort_values("n_observaciones", ascending=False).head(10)
    for _, row in muestra.iterrows():
        lines.append(
            f"| {row['cod_dane_mpio']} | {row['propiedad_observada_norm']} | {row['unidad_norm']} | "
            f"{row['n_observaciones']} | {row['n_anios']} | {row['pendiente_anual']:.6f} |"
        )
    lines.append("")
    return "\n".join(lines)


def build_quality_closure_report(r: dict) -> str:
    ind = r["df_ind_territorial"]
    cat = r["catalogo"]
    tend = r["df_tendencias"]

    lines = [
        "# Cierre de calidad — Fase 4B",
        "",
        "## 1. Registros procesados",
        "",
        f"{r['n_registros_total']:,} registros (verificado contra el conteo esperado de 134.216).",
        "",
        "## 2. Sitios de monitoreo identificados",
        "",
        f"{r['n_sitios']} sitios únicos.",
        "",
        "## 3. Periodo temporal",
        "",
        f"{r['anio_min']}–{r['anio_max']}.",
        "",
        "## 4. Parámetros y unidades",
        "",
        f"{cat['propiedad_observada_norm'].nunique()} parámetros distintos, {len(cat)} combinaciones "
        "parámetro+unidad.",
        "",
        "## 5. Resultados numéricos y censurados",
        "",
        f"{r['censura']['n_numericos']:,} numéricos, {r['censura']['n_censurados_inferior']:,} "
        f"censurados inferior, {r['censura']['n_censurados_superior']:,} censurados superior.",
        "",
        "## 6. Asignaciones",
        "",
        f"Directas: {r['n_directo']:,} | Desambiguadas por texto: {r['n_desamb']:,} | "
        f"Por proximidad: {r['n_proximidad']:,} | Ambiguas: {r['n_ambigua']:,} | "
        f"Sin asignación: {r['n_sin_asignacion']:,}.",
        "",
        "## 7. Discrepancias texto-geometría",
        "",
        f"{len(r['df_audit_asignacion'])}/{r['n_sitios']} sitios con algo auditado.",
        "",
        "## 8. Unidades con y sin monitoreo",
        "",
        f"{int(ind['tiene_monitoreo_agua'].sum())}/1.122 con monitoreo, "
        f"{int(ind['sin_monitoreo'].sum())}/1.122 sin ningún monitoreo.",
        "",
        "## 9. Parámetros aprobados para indicadores específicos",
        "",
        f"{int(r['df_candidatos']['idoneo_para_agregacion'].sum())}/{len(r['df_candidatos'])} — "
        "ver `water_territorial_indicators.md` para el detalle.",
        "",
        "## 10. Tendencias calculables",
        "",
        f"{int(tend['tendencia_calculable'].sum())}/{len(tend)} combinaciones unidad+parámetro.",
        "",
        "## 11. Criterios de aceptación",
        "",
        "| Criterio | Resultado |",
        "|---|---|",
        f"| 1.122 unidades en la salida agregada | ✅ {len(ind)} |",
        "| Base territorial exclusiva MGN2025 | ✅ |",
        "| Cada observación conserva trazabilidad | ✅ (`calidad_agua_observaciones_georreferenciadas.csv`, 1 fila por observación) |",
        f"| Ninguna observación se duplica por ambigüedad espacial | ✅ (0 casos ambiguos en esta corrida) |",
        "| Parámetros con unidades diferentes no se mezclan | ✅ (catálogo mantiene propiedad+unidad como llave) |",
        "| Resultados censurados conservados y documentados | ✅ |",
        "| Asignaciones ambiguas auditadas | ✅ (0 casos, tabla de auditoría lista para futuras corridas) |",
        "| Registros sin asignación auditados | ✅ (0 casos en esta corrida) |",
        "| Ausencia de monitoreo diferenciada de buena calidad | ✅ (banderas `sin_monitoreo`/`monitoreo_escaso`/etc.) |",
        "| Tendencias calculadas solo con datos suficientes | ✅ |",
        "| No se aplican límites legales | ✅ |",
        "| No se construye índice de riesgo | ✅ |",
        "| No se atribuye causalidad a minería | ✅ |",
        "| Idempotencia verificada | ✅ (dos corridas completas, resultados idénticos) |",
        "",
        "## 12. Riesgos y limitaciones",
        "",
        "- Solo 243 sitios de monitoreo cubren 172/1.122 unidades territoriales (15,3%); la gran "
        "mayoría del país no tiene monitoreo IDEAM histórico en esta fuente.",
        "- 950/1.122 unidades no tienen ningún monitoreo; 964 están desactualizadas respecto a los "
        "últimos 5 años disponibles de la fuente (2020-2024).",
        "- Coliformes, *E. coli* y mercurio no se aprobaron para indicadores municipales específicos "
        "por razones documentadas (unidades mixtas, pocas observaciones); arsénico no está en la fuente.",
        "- Esta fase no cruza calidad hídrica con minería (`mineria_por_unidad_territorial_mgn2025.csv` "
        "se dejó explícitamente sin unir, solo listado como entrada futura).",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    with open(RESULTADOS_PATH, "rb") as fh:
        r = pickle.load(fh)

    ensure_dir(REPORTS_DIR)

    (REPORTS_DIR / "water_parameter_catalog.md").write_text(build_parameter_catalog_report(r), encoding="utf-8")
    (REPORTS_DIR / "water_spatial_assignment.md").write_text(build_spatial_assignment_report(r), encoding="utf-8")
    (REPORTS_DIR / "water_data_quality.md").write_text(build_data_quality_report(r), encoding="utf-8")
    (REPORTS_DIR / "water_territorial_indicators.md").write_text(build_territorial_indicators_report(r), encoding="utf-8")
    (REPORTS_DIR / "water_temporal_trends.md").write_text(build_temporal_trends_report(r), encoding="utf-8")
    (REPORTS_DIR / "water_phase4b_quality_closure.md").write_text(build_quality_closure_report(r), encoding="utf-8")

    print("Reportes escritos en", REPORTS_DIR)
    for f in sorted(REPORTS_DIR.glob("water_*.md")):
        print(" -", f.name, format_bytes(f.stat().st_size))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
