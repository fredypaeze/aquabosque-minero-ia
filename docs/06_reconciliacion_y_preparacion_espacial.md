# 06 — Reconciliación territorial y preparación espacial (Fase 3D.1)

Antes de intersectar el Catastro Minero con los límites municipales (Fase 4A), esta fase
resuelve de forma documentada la discrepancia territorial encontrada en la Fase 3D,
corrige la semántica del universo territorial, prepara las geometrías del catastro
minero para intersección, y ajusta la salida GeoJSON al estándar RFC 7946. Generado por
`scripts/05_reconcile_and_prepare_spatial.py`, que usa `src/aquabosque/data/clean.py` y
el nuevo `src/aquabosque/data/spatial.py`.

**No se ejecuta ninguna intersección real ni se construyen indicadores mineros ni
dataset maestro en esta fase.**

## Cómo regenerar

```powershell
.\venv\Scripts\Activate.ps1
python scripts\05_reconcile_and_prepare_spatial.py
```

Salidas versionables (git) vs. regenerables:

- `docs/06_...md` (este documento) y el código en `src/`/`scripts/` quedan en git.
- `data/processed/territorio/universo_territorial_divipola.csv`,
  `data/processed/territorio/dane_mgn2025_nuevo_belen_bajira_27493_clean.geojson`,
  `data/processed/mineria/catastro_minero_anm_spatial_ready.geojson` y sus `.metadata.json`
  quedan ignorados por git (`data/processed/*`), igual que el resto de `data/processed/`
  desde la Fase 0 — son artefactos regenerables.
- `outputs/reports/spatial_preparation/territorial_reconciliation.md` y
  `catastro_minero_geometry_repair.md` quedan ignorados por git (`outputs/reports/*`),
  mismo patrón desde la Fase 0.

## A. Universo territorial: terminología corregida

Las 1.122 filas de DIVIPOLA **no son todas "municipios"**. Se adopta la denominación
técnica **"unidades territoriales subdepartamentales DIVIPOLA"**, que incluye:

| tipo_unidad_territorial | Conteo |
|---|---|
| Municipio | 1.103 |
| Área no municipalizada | 18 |
| Isla | 1 |

`data/processed/territorio/universo_territorial_divipola.csv` (1.123 filas: 1.122
vigentes en DIVIPOLA + 1 fuera de DIVIPOLA vigente conservada para trazabilidad) es la
tabla maestra reconciliada, con las columnas: `cod_dane_mpio`, `cod_dane_dpto`,
`nombre_mpio`, `nombre_mpio_norm`, `nombre_dpto`, `nombre_dpto_norm`,
`tipo_unidad_territorial`, `presente_divipola_vigente`, `presente_capa_geometrica`,
`tiene_geometria`, `estado_reconciliacion`, `observacion_reconciliacion`.

**DIVIPOLA tabular (Fase 3B) es la fuente de verdad administrativa.** La capa geométrica
ArcGIS (Fase 2C/3D) nunca se trató como fuente de vigencia: solo aporta (o no) geometría
para un código que DIVIPOLA ya reconoce.

## B. Discrepancia 94663 / 27493

### 94663 — Mapiripana (Guainía)

- Presente en la capa geométrica (ArcGIS REST
  `Divipola/Cache_DivipolaEntidadesTerritorialesCP`).
- **Ausente** de la DIVIPOLA tabular vigente (Fase 3B).
- **Estado:** `fuera_universo_divipola_vigente`. Se conserva en
  `universo_territorial_divipola.csv` para trazabilidad (no se borra de ningún archivo
  de datos original), pero queda excluido por defecto del universo analítico vigente
  hasta que exista evidencia oficial de su incorporación a DIVIPOLA. No se afirma aquí
  ninguna causa administrativa o legal para la discrepancia.

### 27493 — Nuevo Belén de Bajirá (Chocó)

- Presente en la DIVIPOLA tabular vigente (Fase 3B).
- **Ausente** de la capa geométrica descargada en la Fase 2C.
- **Fuente oficial consultada y encontrada:** DANE — Marco Geoestadístico Nacional 2025
  (MGN2025), servicio propio del geoportal DANE:
  `geoportal.dane.gov.co/mparcgis/rest/services/MGN2025/Serv_CapasMGN_2025/FeatureServer`,
  capa **Municipio (id 317)**. Descargada el 2026-07-12.
- **Validaciones realizadas sobre la geometría recuperada** (todas pasaron):
  - Código: `MPIO_CDPMP` = `27493` ✓
  - Departamento: `DPTO_CCDGO` = `27` = `cod_dpto` de DIVIPOLA ✓
  - Nombre (normalizado): `NUEVO BELEN DE BAJIRA` en ambas fuentes ✓
  - Geometría válida (shapely `is_valid`): ✓ (tipo original `Polygon`)
  - CRS: se solicitó `outSR=4326` explícitamente; bounding box resultante
    (lon -77.14 a -76.49, lat 7.13 a 7.78) dentro del rango esperado de Colombia ✓
- **Nota de transparencia:** también se encontró un registro geométrico de este
  municipio en el catálogo ICDE (`metadatos.icde.gov.co`), a escala 1:10.000, pero la
  entidad productora de ese registro es el **IGAC**, no el DANE. Conforme a la
  instrucción explícita de esta fase ("consultar únicamente fuentes oficiales del
  DANE"), ese registro del IGAC **no se usó**, aunque probablemente sea igual de válido
  técnicamente — se documenta la decisión para que quede trazable.
- **Integración:** la geometría se guardó en
  `data/processed/territorio/dane_mgn2025_nuevo_belen_bajira_27493_clean.geojson`
  (RFC 7946, esquema de propiedades homologado al de los 11 archivos de límites
  municipales: `objectid`, `cod_dane_dpto`, `nom_dpto`, `nombre_dpto_norm`,
  `cod_dane_mpio`, `nom_mpio`, `nombre_mpio_norm`, `mpio_corrdeptal`).
  - **Decisión de diseño:** se guardó como archivo **separado**, no como una 12ª parte
    dentro de `data/processed/territorio/limites_municipales_dane/`, para no tener que
    reprocesar 158,9 MB ya generados y para que el manifest de esa carpeta (propiedad de
    la Fase 3D / `scripts/03_clean_raw_data.py`) siga siendo exactamente regenerable sin
    depender de esta fase posterior. `universo_territorial_divipola.csv` documenta
    explícitamente que ambos archivos deben usarse juntos para tener el universo
    geométrico completo de los 1.122 códigos DIVIPOLA vigentes.

## C. Métricas de correspondencia (correctamente separadas)

**Corrección respecto a la Fase 3D:** el reporte anterior presentó "99,82% de
correspondencia" como si fuera 1.121/1.122 — pero 1.121/1.122 en realidad da **99,91%**.
El 99,82% correcto correspondía a la similitud de Jaccard (1.121/1.123, dividiendo por
la **unión** de ambos conjuntos, no por el total de DIVIPOLA). Esta fase separa las tres
métricas explícitamente para que no se repita esa confusión:

| Métrica | Fórmula | Antes (capa original, 1.122 códigos) | Después (con 27493 recuperado, 1.123 códigos) |
|---|---|---|---|
| `cobertura_divipola_por_geometria` | códigos DIVIPOLA con geometría / total DIVIPOLA | 99,91% (1.121/1.122) | **100,0%** (1.122/1.122) |
| `precision_geometria_contra_divipola` | códigos geométricos vigentes / total geométricos | 99,91% (1.121/1.122) | 99,91% (1.122/1.123) |
| `similitud_jaccard` | intersección / unión | 99,82% (1.121/1.123) | 99,91% (1.122/1.123) |

Tras la reconciliación, la cobertura de DIVIPOLA por geometría llega a 100% (todo código
vigente tiene ahora una geometría disponible, propia o recuperada). La precisión se
mantiene en 99,91% porque `94663` sigue siendo un código geométrico "extra" que no está
en DIVIPOLA vigente — esa es la métrica que expone específicamente ese caso.

## D. GeoJSON RFC 7946

Se eliminó el miembro `crs` que `write_clean_geojson_with_crs` insertaba en los 11
archivos de límites municipales (Fase 3D). La función se renombró a
**`write_rfc7946_geojson`** (`scripts/03_clean_raw_data.py`) y ya no inserta ningún
objeto `crs`:

- RFC 7946 fija el CRS a WGS 84 (equivalente a `CRS84`) de forma implícita para todo
  GeoJSON y considera el miembro `crs` obsoleto (§4 de la especificación).
- Se mantiene el orden de coordenadas `[longitud, latitud]` (x, y) en todas las
  geometrías, como exige RFC 7946.
- El CRS de almacenamiento (`EPSG:4326`) se documenta en el `manifest.json` de cada
  salida procesada y en esta documentación — no dentro del propio archivo GeoJSON.
- Se regeneraron los 11 archivos de límites municipales sin el miembro `crs`
  (`scripts/03_clean_raw_data.py`), y todas las salidas nuevas de esta fase
  (`dane_mgn2025_nuevo_belen_bajira_27493_clean.geojson`,
  `catastro_minero_anm_spatial_ready.geojson`) se generan ya sin ese miembro.

## E. Catastro minero preparado para intersección (spatial_ready)

`data/processed/mineria/catastro_minero_anm_spatial_ready.geojson` — **no se modificó**
`catastro_minero_anm_clean.geojson` (Fase 3C), que conserva las 22 geometrías inválidas
originales intactas para quien necesite auditar el dato "tal cual vino".

- 6.294 → 6.294 `codigo_expediente` (0 eliminados).
- 22 geometrías inválidas (heredadas de la Fase 3C) reparadas con `shapely.make_valid`
  — **nunca `buffer(0)` como primera opción**.
- Las 22 eran autointersecciones de anillo (`Ring Self-intersection`); en los 22 casos
  `make_valid` devolvió directamente un `Polygon` válido (ningún caso produjo
  `GeometryCollection` mixta en este dataset real — la lógica de descarte documentado de
  componentes no poligonales sí se probó con casos sintéticos antes de confiar en ella,
  ver Fase 3D).
- 0 geometrías inválidas después de reparar, 0 vacías irreparables, 100% `MultiPolygon`
  homogéneo.
- Detalle completo por `codigo_expediente` (motivo, tipo original, tipo resultante,
  componentes) en `outputs/reports/spatial_preparation/catastro_minero_geometry_repair.md`.

## F. Prueba de rendimiento STRtree

Antes de plantear la intersección nacional (6.294 títulos × 1.122 unidades
territoriales ≈ 7,06 millones de pares posibles sin índice), se probó el enfoque con
índice espacial en una muestra:

- 40 títulos mineros (muestra aleatoria reproducible, `random_state=42`) contra las
  1.123 unidades territoriales del universo geométrico reconciliado.
- Ambos conjuntos reproyectados a **EPSG:9377** (MAGNA-SIRGAS 2018 / Origen-Nacional).
- Índice `shapely.strtree.STRtree` construido sobre las unidades territoriales.
- Consulta por bounding box (`tree.query`) + intersección geométrica real solo sobre
  las candidatas.

Resultado: 112 pares candidatos por bounding box, 56 confirmados como intersección real
tras el chequeo geométrico completo (44.808 pares de fuerza bruta evitados solo en esta
muestra de 40×1.123). **Hallazgo clave:** casi todo el tiempo (41,8 s de 41,9 s totales)
se fue en reproyectar y construir el índice sobre las 1.123 geometrías territoriales sin
simplificar; la consulta + intersección real tomó apenas 0,036 s. Para la Fase 4A
conviene construir el índice territorial **una sola vez** y reutilizarlo para los 6.294
títulos, no reconstruirlo por título.

## Archivos creados o modificados

- `data/raw/territorio/dane_mgn2025_nuevo_belen_bajira_27493.geojson` (+ `.metadata.json`) —
  descarga puntual, no masiva, de la geometría oficial DANE de 27493.
- `data/processed/territorio/universo_territorial_divipola.csv` — tabla maestra reconciliada.
- `data/processed/territorio/dane_mgn2025_nuevo_belen_bajira_27493_clean.geojson` (+ `.metadata.json`).
- `data/processed/mineria/catastro_minero_anm_spatial_ready.geojson` (+ `.metadata.json`).
- `data/processed/territorio/limites_municipales_dane/*.geojson` — regenerados sin el
  miembro `crs` (RFC 7946); mismo contenido de propiedades y geometría, mismo manifest.
- `src/aquabosque/data/clean.py` — `repair_invalid_geometry` generalizada
  (parámetro `feature_id` en vez de `cod_dane_mpio`, reutilizable), `geometry_to_multipolygon`
  hecha pública, `prepare_catastro_minero_spatial_ready` (nueva).
- `src/aquabosque/data/spatial.py` (nuevo) — reproyección y `STRtree` reutilizables
  para la Fase 4A.
- `scripts/03_clean_raw_data.py` — `write_clean_geojson_with_crs` renombrada a
  `write_rfc7946_geojson`, ya no inserta `crs`.
- `scripts/05_reconcile_and_prepare_spatial.py` (nuevo) — orquesta toda esta fase.
- `outputs/reports/spatial_preparation/territorial_reconciliation.md` (nuevo).
- `outputs/reports/spatial_preparation/catastro_minero_geometry_repair.md` (nuevo).

## Riesgos pendientes para la Fase 4A

- La discrepancia `94663`/`27493` queda documentada pero no "resuelta" en sentido
  absoluto: `94663` sigue sin estar en DIVIPOLA vigente y su tratamiento definitivo
  (¿ignorar?, ¿marcar como histórico?) requiere una decisión de negocio, no solo técnica.
- El archivo de Bajirá recuperado vive separado de los 11 archivos de límites
  municipales; cualquier script de la Fase 4A que consuma "todas las unidades
  territoriales con geometría" debe leer explícitamente ambos orígenes (ya lo hace
  `scripts/05_reconcile_and_prepare_spatial.py`, sirve de referencia).
- El costo dominante de cualquier operación espacial sobre estas capas es la
  reproyección/parseo de geometrías muy detalladas (promedio miles de vértices), no la
  lógica de intersección en sí — la Fase 4A debe diseñarse para reproyectar una sola vez
  y cachear, no repetir por título.
- No se determinó si conviene simplificar geometrías (con tolerancia documentada) para
  la intersección masiva; esta fase preservó fidelidad total, tal como se pidió, pero el
  costo computacional a escala nacional (6.294 × 1.122) todavía no se midió con datos
  reales completos, solo extrapolado de la muestra de 40 títulos.
