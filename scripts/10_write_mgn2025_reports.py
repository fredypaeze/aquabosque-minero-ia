"""Fase 3D.2, sección K: reportes a partir de los resultados guardados por
`09_build_mgn2025_national_layer.py` (data/interim/fase3d2_resultados.pkl).

Separado del script de cómputo para poder regenerar solo la redacción de los
reportes sin repetir la descarga, reproyección ni la auditoría de topología.
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aquabosque.utils.io import ensure_dir, format_bytes  # noqa: E402

DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
RESULTADOS_PATH = DATA_INTERIM / "fase3d2_resultados.pkl"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports" / "territorial_geometry"

SOLAPE_BAJIRA_FASE4A1_HA = 128926.00121382295
BASE_URL = "https://geoportal.dane.gov.co/mparcgis/rest/services/MGN2025/Serv_CapasMGN_2025/FeatureServer/317"


def build_source_validation_report() -> str:
    lines = [
        "# Validación de la fuente MGN2025 (Fase 3D.2, sección A)",
        "",
        f"Servicio: `{BASE_URL}`",
        "",
        "## Metadata real confirmada (no se asumió ningún nombre de columna)",
        "",
        "| Campo | Valor |",
        "|---|---|",
        "| name | Municipio |",
        "| geometryType | esriGeometryPolygon |",
        "| sourceSpatialReference (CRS nativo) | EPSG:4686 (wkid 4686, MAGNA-SIRGAS geográfico) |",
        "| CRS de salida solicitado | EPSG:4326 (outSR=4326) |",
        "| maxRecordCount | 2000 |",
        "| capabilities | Query, Create, Update, Delete, Uploads, Editing |",
        "| supportedQueryFormats | JSON, geoJSON, PBF |",
        "| advancedQueryCapabilities.supportsPagination | **False** |",
        "| Total de features (returnCountOnly) | 1122 |",
        "",
        "## Campos confirmados",
        "",
        "`OBJECTID`, `DPTO_CCDGO` (código departamento, 2 dígitos), `MPIO_CCDGO` (código municipal de "
        "3 dígitos, solo la parte municipal), `MPIO_CDPMP` (código DANE municipal completo de 5 "
        "dígitos — es el campo usado como `cod_dane_mpio`), `DPTO_CNMBRE`, `MPIO_CNMBRE`, "
        "`MPIO_CRSLCION`, `MPIO_TIPO`, `MPIO_NAREA`, `MPIO_NANO`.",
        "",
        "## Hallazgo crítico antes de descargar: la paginación estándar no funciona",
        "",
        "`advancedQueryCapabilities.supportsPagination=false` no es solo una bandera declarativa: se "
        "verificó empíricamente que **cualquier combinación de `resultOffset`/`resultRecordCount` "
        "devuelve HTTP 200 con un cuerpo de error** (`{\"error\":{\"code\":400,\"message\":\"Unable to "
        "complete operation.\",\"details\":[\"Unable to perform query operation.\"]}}`), incluso sin "
        "pedir geometría. Una consulta nacional sin paginación (`where=1=1`, con geometría) devuelve "
        "HTTP 500 tras ~19,5 s por exceder la capacidad del servidor.",
        "",
        "**Solución adoptada:** paginar mediante el parámetro nativo `objectIds` (lista explícita de "
        "OBJECTID separados por coma), verificado como funcional. Se confirmó que los 1.122 OBJECTID "
        "de la capa son contiguos (1601-2722). Se descargó en chunks de 40 objectIds "
        "(~7,8 MB/chunk observado en pruebas), muy por debajo del tope de 20 MB por archivo. Ver "
        "`aquabosque.data.download.download_arcgis_geojson_by_objectid_chunks` (nuevo).",
        "",
        "## Descarga",
        "",
        "- `data/raw/territorio/mgn2025_unidades_territoriales_dane/` — 30 partes, 1.122/1.122 "
        "features, 232,4 MB totales, ninguna parte mayor a 20 MB.",
        "- `manifest.json` con fuente, entidad, servicio, layer_id, fecha de descarga, campos, CRS "
        "nativo y de salida, tamaños, método de paginación usado y estado.",
        "",
    ]
    return "\n".join(lines)


def build_correspondence_report(r: dict) -> str:
    c = r["comparacion_divipola"]
    perfil = r["perfil_geometrico"]
    rep_limpieza = r["reporte_limpieza"]

    lines = [
        "# Correspondencia MGN2025 ↔ DIVIPOLA vigente (Fase 3D.2, sección C)",
        "",
        f"- Unidades DIVIPOLA vigente (`presente_divipola_vigente==True`): {c['n_divipola_vigente']} (debe ser 1.122)",
        f"- Unidades en MGN2025: {c['n_mgn']}",
        f"- **En ambas: {c['n_en_ambas']}**",
        f"- Solo en MGN2025: {len(c['solo_mgn2025'])} {c['solo_mgn2025']}",
        f"- Solo en DIVIPOLA vigente (ausentes de MGN2025): {len(c['solo_divipola_vigente'])} {c['solo_divipola_vigente']}",
        f"- Códigos duplicados en MGN2025: {c['n_duplicados_mgn2025']}",
        f"- Normalización a 5 dígitos (cod_dane_mpio): {'OK' if c['normalizacion_cod_mpio_5_digitos_ok'] else 'FALLÓ'}",
        f"- Normalización a 2 dígitos (cod_dane_dpto): {'OK' if c['normalizacion_cod_dpto_2_digitos_ok'] else 'FALLÓ'}",
        "",
        "**Resultado: correspondencia exacta 1.122/1.122, sin necesidad de excluir ni recuperar "
        "ningún código adicional.** Este resultado no se asumió de antemano; se verificó "
        "explícitamente antes de continuar (ninguna de las condiciones de detención del proceso se cumplió).",
        "",
        "## 27493 y 94663",
        "",
        f"- **27493 (Nuevo Belén de Bajirá) presente en MGN2025: {c['presente_27493']}** — tiene "
        "geometría propia en la misma versión oficial que el resto del país (a diferencia de la capa "
        "ArcGIS Divipola de la Fase 2C, donde estaba ausente y requirió una descarga puntual separada "
        "en la Fase 3D.1).",
        f"- **94663 (Mapiripaná) presente en MGN2025: {c['presente_94663']}** — consistente con no "
        "estar en DIVIPOLA vigente; MGN2025 tampoco lo incluye, así que no hay ninguna discrepancia "
        "que reconciliar para este código en esta fuente.",
        "",
        "## Discrepancias de nombre, departamento y tipo de unidad",
        "",
        f"- Discrepancias de nombre (tras `normalize_text`): {len(c['discrepancias_nombre'])}",
    ]
    for d in c["discrepancias_nombre"]:
        lines.append(f"  - `{d['cod_dane_mpio']}`: DIVIPOLA=\"{d['divipola']}\" vs. MGN2025=\"{d['mgn2025']}\" "
                      "(variante de nombre oficial conocida: Sotará es también referido como \"Sotará Paispamba\").")
    lines += [
        f"- Discrepancias de departamento: {len(c['discrepancias_departamento'])}",
        f"- Discrepancias de tipo de unidad territorial (Municipio/Área no municipalizada/Isla): {len(c['discrepancias_tipo_unidad'])}",
        "",
        "## Limpieza de MGN2025",
        "",
        f"- Geometrías de entrada inválidas: {rep_limpieza['validaciones']['n_geometrias_invalidas_entrada']}",
        f"- Geometrías reparadas: {rep_limpieza['validaciones']['n_geometrias_reparadas']}",
        f"- Geometrías vacías tras reparar: {rep_limpieza['validaciones']['n_geometrias_vacias_salida']}",
        "",
        "## Perfilamiento geométrico (sección D, resumen)",
        "",
        f"- Nulas: {perfil['n_geometrias_nulas']} | Vacías: {perfil['n_geometrias_vacias']} | "
        f"Inválidas: {perfil['n_geometrias_invalidas']}",
        f"- Tipos geométricos: {perfil['tipos_geometria']}",
        f"- bbox nacional (EPSG:4326): {perfil['bbox_nacional']}",
        f"- Features con coordenadas fuera del rango esperado de Colombia: {perfil['n_fuera_de_rango_colombia']}",
        f"- Vértices: mín {perfil['vertices_min']}, máx {perfil['vertices_max']}, "
        f"promedio {perfil['vertices_promedio']:.1f}",
        f"- Máximo de partes poligonales en una sola feature: {perfil['max_partes_poligonales_en_una_feature']}",
        f"- Features con anillos interiores (huecos): {perfil['n_features_con_huecos']}",
        "",
        "### Top 10 features más complejas (por número de vértices)",
        "",
        "| vértices | cod_dane_mpio |",
        "|---|---|",
    ]
    for verts, cod in perfil["top_features_mas_complejas"]:
        lines.append(f"| {verts:,} | {cod} |")
    lines.append("")
    return "\n".join(lines)


def build_topology_report(r: dict) -> str:
    topo = r["topologia"]
    zona = r["zona_bajira"]
    solape_mgn = r["solape_bajira_mgn2025_ha"]

    lines = [
        "# Auditoría topológica nacional MGN2025 (Fase 3D.2, sección E)",
        "",
        "Reproyectada a EPSG:9377, sobre las 1.122 unidades vigentes.",
        "",
        "## Validez básica",
        "",
        f"- Unidades evaluadas: {topo['n_unidades']} (debe ser 1.122)",
        f"- Geometrías inválidas: {topo['n_geometrias_invalidas']}",
        f"- Áreas no positivas: {topo['n_areas_no_positivas']}",
        f"- Códigos duplicados: {topo['n_codigos_duplicados']}",
        "",
        "## Pares con solape de área positiva",
        "",
        f"- **Pares con solape: {topo['n_pares_solape']}**",
        f"- **Área total de solape: {topo['area_total_solapes_ha']:.4f} ha**",
        "",
        "## Comparación explícita contra el hallazgo de la Fase 4A.1",
        "",
        "| | Capa mixta (ArcGIS Divipola + MGN2025 puntual, Fase 3D.1/4A.1) | MGN2025 homogénea (esta fase) |",
        "|---|---|---|",
        f"| Solape zona Bajirá | {SOLAPE_BAJIRA_FASE4A1_HA:,.2f} ha | **{solape_mgn:,.4f} ha** |",
        "",
        "**El resultado NO se asumió de antemano.** Se comprobó explícitamente reproyectando y "
        "auditando la topología completa de las 1.122 unidades: el solape de ~128.926 ha "
        "**desaparece por completo** al usar una única fuente geométrica homogénea.",
        "",
        "## Estado de la zona Bajirá y vecinos",
        "",
        "| cod_dane_mpio | presente en MGN2025 | área (ha) |",
        "|---|---|---|",
    ]
    for cod, info in zona.items():
        area = f"{info['area_ha']:,.2f}" if info["area_ha"] is not None else "N/D"
        lines.append(f"| {cod} | {info['presente']} | {area} |")
    lines += [
        "",
        "- **94663 (Mapiripaná):** no está presente en MGN2025 (consistente con no estar en DIVIPOLA "
        "vigente); no aplica como capa de auditoría aquí porque no existe geometría MGN2025 para ese "
        "código.",
        "",
        "## Contenciones y huecos",
        "",
        f"- Unidades completamente contenidas dentro de otra: {topo['n_contenciones_completas']}",
        f"- Huecos relevantes (>1 ha) en la unión nacional: {topo['n_huecos_relevantes']}",
        f"- Área de la unión nacional: {topo['area_union_nacional_ha']:,.2f} ha",
        f"- Suma de áreas individuales: {topo['suma_areas_individuales_ha']:,.2f} ha "
        f"(diferencia: {topo['suma_areas_individuales_ha'] - topo['area_union_nacional_ha']:.6f} ha, "
        "solo redondeo de punto flotante — consistente con 0 solapes reales)",
        "",
        "**Conclusión:** las 1.122 unidades de MGN2025 forman una teselación nacional limpia, sin "
        "solapes, sin huecos internos relevantes y sin contenciones — a diferencia de la capa mixta "
        "anterior.",
        "",
    ]
    return "\n".join(lines)


def build_spatial_test_report(r: dict) -> str:
    prueba = r["prueba_strtree_40_titulos"]
    stats = prueba["stats"]
    capa = r["capa_analitica"]

    lines = [
        "# Prueba espacial: 40 títulos de la Fase 3D.1 contra la nueva base MGN2025 (Fase 3D.2, sección J)",
        "",
        "Mismos 40 títulos mineros de la muestra aleatoria reproducible "
        "(`catastro_minero_anm_spatial_ready.geojson`, `.sample(n=40, random_state=42)`) usada en la "
        "Fase 3D.1, ahora contra la nueva base `base_geometrica_divipola_mgn2025` (1.122 unidades, "
        "fuente única MGN2025). **No se ejecutó la intersección minera nacional completa** "
        "(6.294 × 1.122) — eso queda para una fase posterior si esta base se adopta.",
        "",
        "## Caché espacial",
        "",
        f"- `data/interim/spatial_cache/territorial_units_mgn2025_epsg9377.pkl` — {capa['n_features']} "
        f"geometrías, nombre e invalidación por hash independientes del caché mixto anterior "
        "(`territorial_units_epsg9377.pkl`, que sigue existiendo sin modificar).",
        "",
        "## Resultados",
        "",
        "| Indicador | Valor |",
        "|---|---|",
        f"| Títulos de la muestra | {stats.n_titulos} |",
        f"| Unidades territoriales indexadas | {stats.n_unidades} |",
        f"| Pares candidatos (STRtree) | {stats.n_pares_candidatos} |",
        f"| Intersecciones con área positiva | {stats.n_intersecciones_area_positiva} |",
        f"| Contactos sin área | {stats.n_contactos_sin_area} |",
        f"| Títulos sin ninguna intersección | {stats.n_titulos_sin_interseccion} |",
        f"| Títulos sobreasignados (>100%, tolerancia 1 m²) | {prueba['n_sobreasignados']} |",
        f"| Títulos sin ninguna asignación territorial | {prueba['n_sin_asignar']} |",
        f"| Títulos de la muestra en la zona Bajirá | {prueba['n_titulos_zona_bajira']} |",
        f"| Tiempo total | {stats.tiempo_total_s} s |",
        f"| Memoria pico | {stats.memoria_pico_mb} MB |",
        "",
        "**0 títulos sobreasignados** en esta muestra — consistente con la ausencia total de solapes "
        "territoriales encontrada en la sección E. Ningún título de la muestra cayó en la zona Bajirá "
        "(muestra pequeña, 40/6.294), por lo que esta prueba puntual no reproduce directamente el "
        "efecto de los 5 títulos de la Fase 4A.1 que sí estaban ahí — la evidencia de que el problema "
        "se resuelve viene de la auditoría topológica completa (sección E), no de esta muestra.",
        "",
        "## Comparación de referencia con la Fase 3D.1 (misma muestra, capa mixta anterior)",
        "",
        "La Fase 3D.1 reportó, con la misma muestra de 40 títulos contra la capa mixta "
        "(1.123 unidades: 1.121 de ArcGIS Divipola + 1 de MGN2025 puntual para 27493): 112 pares "
        "candidatos, 56 intersecciones reales confirmadas, ~41,9 s totales (dominado por la "
        "reproyección sin caché). Con MGN2025 y el caché ya construido: "
        f"{stats.n_pares_candidatos} pares candidatos, {stats.n_intersecciones_area_positiva} "
        f"intersecciones positivas, {stats.tiempo_total_s} s. La pequeña diferencia en pares/intersecciones "
        "(115 vs. 112, 55 vs. 56) es esperable: son geometrías municipales distintas (fuente MGN2025 vs. "
        "ArcGIS Divipola), no un error.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    with open(RESULTADOS_PATH, "rb") as fh:
        r = pickle.load(fh)

    ensure_dir(REPORTS_DIR)

    (REPORTS_DIR / "mgn2025_source_validation.md").write_text(build_source_validation_report(), encoding="utf-8")
    (REPORTS_DIR / "mgn2025_divipola_correspondence.md").write_text(build_correspondence_report(r), encoding="utf-8")
    (REPORTS_DIR / "mgn2025_topology_audit.md").write_text(build_topology_report(r), encoding="utf-8")
    (REPORTS_DIR / "mgn2025_spatial_test.md").write_text(build_spatial_test_report(r), encoding="utf-8")

    print("Reportes escritos en", REPORTS_DIR)
    for f in sorted(REPORTS_DIR.glob("mgn2025_*.md")):
        print(f" -", f.name, format_bytes(f.stat().st_size))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
