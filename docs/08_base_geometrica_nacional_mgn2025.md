# 08 — Base geométrica nacional homogénea DANE MGN2025 (Fase 3D.2)

La auditoría de la Fase 4A.1 encontró que la base territorial usada hasta ahora mezclaba
dos versiones geométricas distintas del DANE: la capa ArcGIS `Divipola/Cache_DivipolaEntidadesTerritorialesCP`
(Fase 2C/3D, 1.121 unidades) y una geometría individual de Nuevo Belén de Bajirá (27493)
recuperada del Marco Geoestadístico Nacional 2025 (MGN2025) en la Fase 3D.1. Esa mezcla
producía un solape territorial de **~128.926 ha** entre 27493 y sus 5 municipios vecinos.

Esta fase reemplaza esa base mixta por una **única capa geográfica nacional**, construida
exclusivamente con la misma versión oficial del MGN2025 del DANE, y comprueba —sin
asumirlo de antemano— si eso elimina el solape.

**No integra calidad hídrica. No recalcula indicadores mineros nacionales completos (solo
una prueba con 40 títulos). No construye dataset maestro. No entrena modelos. No crea
dashboard. No elimina ni sobrescribe las capas anteriores.**

## Cómo regenerar

```powershell
.\venv\Scripts\Activate.ps1
python scripts\08_download_mgn2025_national.py
python scripts\09_build_mgn2025_national_layer.py
python scripts\10_write_mgn2025_reports.py
```

Salidas versionables (git) vs. regenerables:

- `docs/08_...md` (este documento), `scripts/08_*.py`, `scripts/09_*.py`, `scripts/10_*.py` y
  las funciones nuevas en `src/aquabosque/data/download.py`, `src/aquabosque/data/clean.py`
  quedan en git.
- `data/raw/territorio/mgn2025_unidades_territoriales_dane/`,
  `data/processed/territorio/base_geometrica_divipola_mgn2025/`,
  `data/processed/audit/mgn2025_codigos_fuera_divipola.csv`,
  `data/interim/spatial_cache/territorial_units_mgn2025_epsg9377.*` y
  `data/interim/fase3d2_resultados.pkl` quedan ignorados por git (regenerables).
- `outputs/reports/territorial_geometry/*.md` quedan ignorados por git, mismo patrón desde
  la Fase 0.

## 1. Fuente oficial y validación previa

Servicio: `geoportal.dane.gov.co/mparcgis/rest/services/MGN2025/Serv_CapasMGN_2025/FeatureServer/317`
(capa Municipio). Se re-validó la metadata real antes de descargar nada (ver
`outputs/reports/territorial_geometry/mgn2025_source_validation.md`):

- CRS nativo: EPSG:4686 (MAGNA-SIRGAS geográfico); CRS de salida solicitado: EPSG:4326.
- 1.122 features totales (`returnCountOnly`).
- Campos confirmados: `OBJECTID`, `DPTO_CCDGO`, `MPIO_CCDGO`, `MPIO_CDPMP` (código DANE
  municipal completo, 5 dígitos), `DPTO_CNMBRE`, `MPIO_CNMBRE`, `MPIO_CRSLCION`, `MPIO_TIPO`,
  `MPIO_NAREA`, `MPIO_NANO`.
- **Hallazgo crítico:** `advancedQueryCapabilities.supportsPagination=false` es real —
  `resultOffset`/`resultRecordCount` fallan siempre (HTTP 200 con cuerpo de error), incluso
  sin geometría. Se verificó esto empíricamente antes de intentar la descarga masiva. La
  descarga se hizo con el parámetro nativo `objectIds` en chunks de 40 (nueva función
  `download_arcgis_geojson_by_objectid_chunks` en `src/aquabosque/data/download.py`).

## 2. Descarga completa

`data/raw/territorio/mgn2025_unidades_territoriales_dane/`: 30 partes, **1.122/1.122
features descargadas**, 232,4 MB totales, ninguna parte mayor a 20 MB. Manifest con fuente,
entidad, servicio, layer_id, fecha de descarga, campos, CRS nativo/salida, tamaños, método
de paginación y estado (`completo`).

## 3. Correspondencia contra DIVIPOLA vigente

Comparación completa por código DANE contra las 1.122 unidades con
`presente_divipola_vigente==True` (`universo_territorial_divipola.csv`, Fase 3D.1):

| Métrica | Resultado |
|---|---|
| En ambas fuentes | **1.122 / 1.122** |
| Solo en MGN2025 | 0 |
| Solo en DIVIPOLA vigente (ausentes de MGN2025) | 0 |
| Códigos duplicados en MGN2025 | 0 |
| Discrepancias de departamento | 0 |
| Discrepancias de tipo de unidad territorial | 0 |
| Discrepancias de nombre (tras `normalize_text`) | 1 (`19760`: DIVIPOLA "SOTARA" vs. MGN2025 "SOTARA PAISPAMBA", variante de nombre oficial conocida) |

**Este resultado no se asumió de antemano.** El proceso estaba diseñado para detenerse si
faltaba algún código vigente sin explicación, si había duplicados, o si algún código no se
podía normalizar a 5 (municipal) o 2 (departamental) dígitos — ninguna de esas condiciones
se cumplió.

### 27493 y 94663

- **27493 (Nuevo Belén de Bajirá):** tiene geometría propia en MGN2025, en la **misma
  versión oficial que el resto del país** — a diferencia de la Fase 2C/3D.1, donde estaba
  ausente de la capa ArcGIS Divipola y requirió una descarga puntual separada de una fuente
  distinta.
- **94663 (Mapiripaná):** no está presente en MGN2025, consistente con no estar en DIVIPOLA
  vigente. No genera ninguna discrepancia adicional que reconciliar en esta fuente.

## 4. Calidad geométrica

Perfilamiento sobre los datos crudos (`outputs/reports/territorial_geometry/mgn2025_divipola_correspondence.md`,
sección D): **0 geometrías nulas, 0 vacías, 0 inválidas**, 1.113 `Polygon` + 9
`MultiPolygon` (homogeneizadas a `MultiPolygon` en la capa analítica), bbox nacional
consistente con el territorio colombiano continental e insular, 0 features con coordenadas
fuera de rango, vértices entre 538 y 78.914 (promedio 5.537). **0 geometrías necesitaron
reparación** — resultado muy distinto a la capa ArcGIS Divipola de la Fase 3D.1, que tenía
22 geometrías inválidas en el catastro minero (no en esta capa territorial, pero da
contexto de la calidad relativa de las fuentes).

## 5. Topología nacional — el hallazgo central de esta fase

Auditoría topológica completa (EPSG:9377) de las 1.122 unidades
(`outputs/reports/territorial_geometry/mgn2025_topology_audit.md`):

| | Capa mixta (Fase 3D.1/4A.1) | MGN2025 homogénea (esta fase) |
|---|---|---|
| **Solape zona Bajirá** | **128.926,00 ha** | **0,0000 ha** |
| Pares con solape (cualquier par, nacional) | 6 | **0** |
| Contenciones completas | 0 | 0 |
| Huecos relevantes (>1 ha) | 1 (coincidía con 94663) | **0** |
| Geometrías inválidas | 0 | 0 |
| Códigos duplicados | 0 | 0 |

**El solape de ~128.926 ha desaparece por completo** al usar una única fuente geométrica
homogénea. La suma de las áreas individuales de las 1.122 unidades (113.880.346,70 ha)
coincide con el área de su unión geométrica hasta la sexta cifra decimal — es decir, cero
solapes reales en todo el país, no solo en la zona de Bajirá.

## 6. Capa analítica

`data/processed/territorio/base_geometrica_divipola_mgn2025/` — 17 partes GeoJSON (RFC
7946, sin miembro `crs`, coordenadas lon/lat), **1.122 features (una por código DANE
vigente)**, 232,4 MB, ninguna parte mayor a 20 MB. **0 códigos excluidos** (correspondencia
1:1 exacta con DIVIPOLA vigente, así que no hubo necesidad de excluir ningún código de
MGN2025). `data/processed/audit/mgn2025_codigos_fuera_divipola.csv` existe (con encabezados)
pero **0 filas** — se documenta la ausencia de casos, no se omite el archivo.

## 7. Sustitución metodológica

**No se borró ni sobrescribió ninguna capa anterior.** Se marcan explícitamente como:

- `data/processed/territorio/limites_municipales_dane/` (Fase 3D, ArcGIS Divipola) — **insumo
  histórico**, fuente usada para diagnóstico y para entender el origen del problema de la
  Fase 4A.1. **No recomendada para nuevas integraciones espaciales nacionales** por mezclar,
  junto con el archivo siguiente, dos versiones geométricas distintas.
- `data/processed/territorio/dane_mgn2025_nuevo_belen_bajira_27493_clean.geojson` (Fase
  3D.1) — **insumo histórico**, documenta cómo se detectó y resolvió puntualmente la
  ausencia de 27493 antes de esta fase. **No recomendado para nuevas integraciones**: su
  propósito quedó cubierto por la nueva capa completa.

**La fuente analítica recomendada para toda integración espacial nacional futura (Fase 4B
en adelante) es exclusivamente `base_geometrica_divipola_mgn2025`.**

## 8. CRS

- CRS nativo del servicio: EPSG:4686 (MAGNA-SIRGAS geográfico).
- CRS de descarga y almacenamiento: EPSG:4326 (`outSR=4326` explícito, RFC 7946).
- CRS de cálculo (reproyección, topología, intersecciones): EPSG:9377 (MAGNA-SIRGAS 2018 /
  Origen-Nacional), mismo estándar que las Fases 3D.1 y 4A.

## 9. Caché espacial

`data/interim/spatial_cache/territorial_units_mgn2025_epsg9377.pkl` (+ `.metadata.json`) —
**nombre y huella de invalidación completamente independientes** del caché anterior
(`territorial_units_epsg9377.pkl`, que sigue existiendo, ligado a los archivos de la capa
mixta, y no se reutilizó en ningún momento de esta fase).

## 10. Prueba espacial (40 títulos de la Fase 3D.1)

`outputs/reports/territorial_geometry/mgn2025_spatial_test.md`: misma muestra reproducible
(`random_state=42`, 40 títulos) contra la nueva base. 115 pares candidatos, 55
intersecciones con área positiva, 0 contactos sin área, 0 títulos sin asignación, **0
títulos sobreasignados** (consistente con 0 solapes territoriales), 0,069 s, 0,09 MB pico.
Ningún título de esta muestra pequeña cayó en la zona de Bajirá, así que esta prueba puntual
no reproduce directamente el efecto sobre los 5 títulos de la Fase 4A.1 — esa evidencia
viene de la auditoría topológica completa (sección 5), no de esta muestra. **No se ejecutó
la intersección minera nacional completa.**

## 11. Limitaciones

- Solo se comparó por código DANE, nombre, departamento y tipo de unidad — no se comparó
  vértice a vértice el trazado exacto de cada límite municipal contra la capa ArcGIS
  Divipola (fuera de alcance de esta fase).
- La prueba espacial de la sección 10 usa una muestra de 40/6.294 títulos; no garantiza que
  no aparezcan casos nuevos de "hueco entre límites" (como los 22 de la Fase 4A.1, causa
  `hueco_entre_limites_territoriales`) al ejecutar la intersección nacional completa con
  esta nueva base — eso requiere repetir la Fase 4A con `base_geometrica_divipola_mgn2025`
  como fuente territorial, que queda fuera de alcance de esta fase.
- No se investigó por qué 27615, 05480, 05837, 27150 y 05234 tienen áreas distintas en
  MGN2025 frente a la capa ArcGIS Divipola (más allá de que ya no se solapan con 27493) —
  se documenta el hallazgo geométrico, no se afirma ninguna causa administrativa.

## 12. Decisión de adopción

**Se adopta MGN2025 (`base_geometrica_divipola_mgn2025`) como la nueva base geométrica
territorial analítica recomendada.** Cumple los 10 criterios de aceptación de la Fase 3D.2:

| Criterio | Resultado |
|---|---|
| Cubre las 1.122 unidades DIVIPOLA vigentes | ✅ 1.122/1.122 exacto |
| 27493 tiene geometría | ✅ |
| No existen códigos duplicados | ✅ 0 |
| Todas las geometrías finales son válidas | ✅ 0 inválidas |
| No existen solapes territoriales grandes sin explicación | ✅ 0 pares de solape |
| No reproduce el solape de ~128.926 ha de Bajirá | ✅ 0,0000 ha |
| El caché espacial corresponde exclusivamente a MGN2025 | ✅ nombre/huella independientes |
| La prueba STRtree funciona | ✅ 115 candidatos, 55 intersecciones, 0,069 s |
| No se integró calidad hídrica | ✅ |
| No se recalcularon indicadores mineros nacionales completos | ✅ solo prueba de 40 títulos |

No se forzó ninguna adopción: los 10 criterios se cumplieron con evidencia real, verificada
paso a paso, sin asumir el resultado de antemano.

## Archivos creados o modificados

- `src/aquabosque/data/download.py` — nuevas `get_arcgis_all_object_ids` y
  `download_arcgis_geojson_by_objectid_chunks` (paginación por `objectIds` para servidores
  que rechazan `resultOffset`/`resultRecordCount`).
- `src/aquabosque/data/clean.py` — nueva `clean_mgn2025_municipios`.
- `scripts/08_download_mgn2025_national.py` (nuevo) — secciones A/B.
- `scripts/09_build_mgn2025_national_layer.py` (nuevo) — secciones C-J.
- `scripts/10_write_mgn2025_reports.py` (nuevo) — sección K (reportes).
- `data/raw/territorio/mgn2025_unidades_territoriales_dane/` (nuevo, 30 partes + manifest).
- `data/processed/territorio/base_geometrica_divipola_mgn2025/` (nuevo, 17 partes + manifest).
- `data/processed/audit/mgn2025_codigos_fuera_divipola.csv` (nuevo, 0 filas).
- `data/interim/spatial_cache/territorial_units_mgn2025_epsg9377.pkl` (+ `.metadata.json`, nuevo).
- `outputs/reports/territorial_geometry/mgn2025_source_validation.md`,
  `mgn2025_divipola_correspondence.md`, `mgn2025_topology_audit.md`,
  `mgn2025_spatial_test.md` (nuevos).
- `docs/08_base_geometrica_nacional_mgn2025.md` (este documento).

## Riesgos pendientes

- La intersección minera nacional completa (6.294 × 1.122) no se ha repetido con la nueva
  base; los indicadores de la Fase 4A siguen calculados sobre la capa mixta hasta que se
  ejecute esa fase de nuevo explícitamente.
- No se determinó el tratamiento definitivo de 94663 (Mapiripaná): sigue sin tener
  geometría en ninguna fuente DANE vigente disponible para este proyecto.
- El pequeño desajuste de nombre en 19760 (Sotará/Sotará Paispamba) no se corrigió en
  `universo_territorial_divipola.csv`; queda documentado aquí para una futura fase de
  reconciliación de nombres si se considera necesario.
- No se comparó el trazado geométrico exacto de cada límite entre MGN2025 y la capa ArcGIS
  Divipola más allá de las 6 unidades de la zona de Bajirá y las validaciones topológicas
  agregadas.
