# 04 — Perfilamiento de datos crudos (Fase 3A / 3C / 3D)

Perfilamiento de las fuentes descargadas en la Fase 2A/2A.1/2B/2C, antes de cualquier
limpieza o transformación. Generado por `scripts/02_profile_raw_data.py`, que llama a
`src/aquabosque/data/profile.py`. La Fase 3C amplió este perfilamiento con el Catastro
Minero geoespacial de la ANM (capa `Titulo_Vigente`, descargada en la Fase 2B). La Fase
3D lo amplió con los Límites municipales DANE (capa `Municipios` vía ArcGIS REST,
descargada en la Fase 2C), incluyendo perfilamiento geométrico detallado con shapely y
validación cruzada contra DIVIPOLA limpia (Fase 3B).

**Solo lectura:** no se limpió ni transformó ningún dato, no se guardó nada en
`data/processed/`, no se construyó dataset maestro, no se entrenó modelo ni se creó
dashboard, y no se descargó ninguna fuente nueva.

## Cómo regenerar los reportes

```powershell
.\venv\Scripts\Activate.ps1
python scripts\02_profile_raw_data.py
```

Los reportes se escriben en `outputs/reports/raw_data_profile/` (6 archivos:
`divipola_profile.md`, `mineria_anm_profile.md`, `calidad_agua_profile.md`,
`catastro_minero_anm_profile.md`, `limites_municipales_dane_profile.md`,
`raw_data_profile_summary.md`). Esa carpeta está en `.gitignore` (mismo patrón que el
resto de `outputs/reports/` desde la Fase 0): son artefactos regenerables, no se
versionan. Este documento (`docs/04_...md`) sí queda en git como registro narrativo de
los hallazgos, para no depender de tener que regenerar los reportes para entender qué se
encontró.

## Fuentes perfiladas

1. `data/raw/territorio/dane_divipola_municipios.xlsx` (DIVIPOLA, DANE)
2. `data/raw/mineria/anm_titulos_anotaciones_rmn.json` (ANM Anotaciones RMN)
3. `data/raw/agua/ideam_calidad_agua_historica/manifest.json` +
   `data/raw/agua/ideam_calidad_agua_historica/*.json` (IDEAM calidad de agua, 4 partes,
   concatenadas **solo en memoria** para perfilar — no se generó ningún archivo
   concatenado en disco)
4. `data/raw/mineria/catastro_minero_anm/catastro_minero_anm_titulo_vigente_part_0001.geojson`
   + `manifest.json` (Catastro Minero ANM - Títulos Vigentes, WFS, Fase 3C). Las
   propiedades se perfilan como tabla; la geometría se perfila aparte (nulas, tipos,
   validez) y **nunca se imprime completa** en el reporte.
5. `data/raw/territorio/limites_municipales_dane/manifest.json` +
   `data/raw/territorio/limites_municipales_dane/*.geojson` (11 partes, Límites
   municipales DANE, ArcGIS REST, Fase 3D). Mismo tratamiento que el catastro minero:
   propiedades como tabla, geometría perfilada aparte (nulas, tipos, validez con
   `explain_validity`, partes/anillos, bbox, complejidad de vértices), sin imprimir
   coordenadas completas.

## Hallazgos principales por fuente

### DIVIPOLA (municipios)

- El XLSX del Geoportal DANE no es una tabla plana simple: tiene un encabezado de dos
  filas con celdas combinadas (`Departamento > Código/Nombre`, `Municipio >
  Código/Nombre`, `Tipo`, `Localización > Longitud/Latitud/Nota`) y arrastra 7 filas de
  título/notas al pie dentro del rango de datos leído por pandas.
- 1.135 filas leídas; de ellas, 1.122 son municipios/áreas no municipalizadas/isla reales
  (1.103 `Municipio` + 18 `Área no municipalizada` + 1 `Isla`), coincidiendo con el total
  de 1.122 unidades territoriales ya visto en la validación técnica de la Fase 1.5.
- **Hallazgo de calidad clave:** `mpio_codigo` se infiere como `float64` al leer con
  pandas, perdiendo el cero inicial (`05001` → `5001.0`). Debe forzarse a texto con
  relleno de ceros (`zfill(5)`) en la limpieza, no antes.
- 6 filas completamente duplicadas (en su mayoría filas vacías del pie de página).
- 33 departamentos únicos identificados.

### ANM Títulos Mineros - Anotaciones RMN

- 37.763 filas, 8 columnas, todas de tipo texto.
- `estado_juridico` es **constante** (100% `"Activo"`): el propio dataset ya viene
  filtrado a títulos activos; no aporta como variable de análisis.
- `codigo_expediente` **no es una llave única por fila**: 6.769 expedientes únicos sobre
  37.763 filas (relación 1 expediente → muchas anotaciones). Es una llave de agrupación
  o llave foránea, no una llave primaria de esta tabla.
- `fecha_anotacion`/`fecha_ejecutoria` vienen como texto `MM/DD/AAAA` (confirmado con
  valores como `04/15/2003`, que solo son válidos como mes/día/año), no como fecha ISO.
  Rango observado: 1990-01-31 a 2025-11-21.
- 208 filas completamente duplicadas.
- Esta tabla **no trae ubicación geográfica**: ni coordenadas ni departamento/municipio.
  Cualquier cruce territorial requeriría el catastro minero geoespacial de la ANM (WFS,
  fuente distinta, con `DEPARTAMENTOS`/`MUNICIPIOS` de texto libre — ver Fase 1.5).

### IDEAM - Data Histórica de Calidad de Agua

- 134.261 filas confirmadas de nuevo tras concatenar las 4 partes en memoria (coincide
  exactamente con `total_filas_origen` del manifest y con el conteo de origen de
  Socrata).
- Datos entre 2005 y 2024 (20 años con al menos un registro).
- 28 departamentos y 170 municipios únicos.
- `propiedad_observada` tiene 80 valores únicos; varios son posibles variantes de un
  mismo parámetro con distinta escritura (p. ej. variantes de "biodisponible" vs "total
  en agua" para el mismo metal) — requiere revisión antes de cualquier agregación por
  parámetro.
- `departamento`/`municipio` vienen como texto en mayúsculas, sin código DANE: el cruce
  con DIVIPOLA no puede ser un join directo por código, necesita normalización de
  nombres.
- 45 filas completamente duplicadas.

### Catastro Minero ANM - Títulos Vigentes (WFS)

- 6.294 features, 19 columnas de propiedades, **0 filas completamente duplicadas**.
- `CODIGO_EXPEDIENTE` es **único** por feature (0 duplicados) — a diferencia de ANM
  Anotaciones RMN, aquí sí sirve como llave primaria de fila.
- Geometría: 100% `MultiPolygon`, 0 nulas, pero **22 topológicamente inválidas**
  (verificado con `shapely.geometry.shape(...).is_valid`).
- `AREA_HA` ya viene numérica (float64); rango de 0,0138 a 206.040,39 ha.
- `FECHA_DE_INSCRIPCION`/`FECHA_TERMINACION` vienen en dos formatos mezclados dentro de
  la misma columna: `'DD/MM/AAAA HH:MM:SS a.m./p.m.'` y `'DD/MM/AAAA'` (solo fecha).
- **Hallazgo de calidad:** `ETAPA` tiene el valor de texto literal `'null'` en 138
  features (no un nulo real de JSON). `FECHA_TERMINACION` tiene el mismo problema en 91
  features.
- **Hallazgo de calidad:** 3 features tienen `FECHA_TERMINACION` en el año 9999 (p. ej.
  `9999-12-31`), casi con certeza un valor centinela de "sin vencimiento", no una fecha
  real.
- `MINERALES` trae varios minerales separados por coma en una sola cadena (121 minerales
  individuales distintos tras separar); `DEPARTAMENTOS`/`MUNICIPIOS` igual: 246 features
  cruzan más de un departamento y 1.676 más de un municipio.
- El geoservicio de origen sigue declarando "actualizado el 22/03/2023" en su
  `GetCapabilities Abstract` (mismo hallazgo de la Fase 1.5/2B).

### Límites municipales DANE (ArcGIS REST)

- 1.122 features, 6 columnas de propiedades, **0 filas completamente duplicadas**.
- `COD_MPIO` es **único**, sin vacíos, y viene ya como texto de 5 dígitos (1.122 de
  1.122) — a diferencia del XLSX de DIVIPOLA, este servicio no pierde el cero inicial.
- `MPIO_CORRDEPTAL` está 98,2% vacío (solo 20 features lo tienen, p. ej. municipios con
  corregimientos departamentales adscritos como Vaupés).
- Geometría: 1.114 `Polygon` + 8 `MultiPolygon`, **0 nulas, 0 vacías, 0 topológicamente
  inválidas** (verificado con `shapely`, incluyendo `explain_validity`).
- **Hallazgo relevante:** dataset con geometría muy detallada, sin simplificar —
  promedio de 3.776 vértices por feature, máximo 126.304 (San Vicente del Caguán). El
  peso real (166 MB para 1.122 features) es mucho mayor de lo que sugería la validación
  superficial de la Fase 1.5.
- Bounding box nacional confirmado dentro del rango geográfico esperado de Colombia
  (incluye territorio insular): lon [-81,74, -66,85], lat [-4,23, 13,39]. 0 features con
  bbox fuera de rango.
- Máximo de 19 partes poligonales en una sola feature (archipiélagos/municipios con
  islas); 1 feature con anillos internos (hueco).
- **Validación cruzada contra DIVIPOLA limpia (por código DANE, no por nombre):**
  1.121/1.122 códigos coinciden (99,82% de correspondencia sobre la unión de ambos
  conjuntos). La única diferencia es real, no de formato: código `94663` (MAPIRIPANA,
  Guainía) solo está en la capa geométrica; código `27493` (NUEVO BELÉN DE BAJIRÁ,
  Chocó) solo está en DIVIPOLA — son municipios distintos, sin inferir aquí ninguna causa
  administrativa o legal.
- 10 nombres de municipio difieren tras normalizar, todos variantes oficiales conocidas
  (p. ej. "MOMPÓS" vs "SANTA CRUZ DE MOMPOX", "CALI" vs "SANTIAGO DE CALI", "CÚCUTA" vs
  "SAN JOSÉ DE CÚCUTA"). 0 departamentos distintos para los códigos coincidentes.

## Problema transversal de integración territorial

De las 5 fuentes, **Límites municipales DANE es la única que trae código DANE de
municipio limpio y listo para join directo** (texto, 5 dígitos, sin vacíos, único):

- DIVIPOLA tiene el código DANE, pero mal tipado en el XLSX (numérico, sin cero inicial).
- ANM Anotaciones RMN no trae territorio en absoluto en este dataset puntual.
- Calidad de agua trae territorio como texto libre, sin código DANE.
- Catastro Minero ANM trae geometría (cruzable espacialmente) y territorio como texto
  libre, a veces con varias unidades territoriales en una sola cadena.
- Límites municipales DANE trae `COD_MPIO` como código DANE directo, y corresponde en un
  99,82% con DIVIPOLA (única discrepancia real, no de formato).

La integración de calidad de agua/ANM/catastro minero seguirá necesitando normalización
de nombres o cruce espacial por geometría; el cruce DIVIPOLA ↔ Límites municipales, en
cambio, puede hacerse por código DANE directo.

## Llaves de integración candidatas

| Fuente | Llave candidata |
|---|---|
| DIVIPOLA | `mpio_codigo` (código DANE de municipio, 5 dígitos, una vez corregido el tipo) |
| ANM Anotaciones RMN | `codigo_expediente` (llave de agrupación 1-a-muchos, no llave única de fila) |
| Calidad de agua IDEAM | coordenadas (`latitud`/`longitud`) + `szh_c_digo_rea_zona_subzona` (subzona hidrográfica) para cruzar con cuencas; `departamento`/`municipio` de texto para cruzar con DIVIPOLA tras normalización |
| Catastro Minero ANM | `CODIGO_EXPEDIENTE` (único por feature) + geometría para cruce espacial directo con otras capas geoespaciales |
| Límites municipales DANE | `COD_MPIO` (código DANE de municipio, único, listo para join directo con DIVIPOLA) + geometría para cruce espacial con catastro minero |

## Recomendación

1. Documentar explícitamente, antes de escribir código de limpieza, los tipos objetivo
   por columna (códigos como texto con ceros a la izquierda, fechas en ISO 8601) y cómo
   descartar las filas basura del XLSX de DIVIPOLA.
2. Diseñar la normalización de nombres de departamento/municipio antes de intentar
   cualquier cruce entre calidad de agua/ANM/catastro minero y DIVIPOLA.
3. Decidir cómo tratar la relación 1-a-muchos de `codigo_expediente` en ANM Anotaciones
   RMN (¿agregar a nivel de expediente antes de integrar, o mantener el detalle de
   anotaciones?).
4. Revisar y, si aplica, estandarizar los ~80 valores de `propiedad_observada` en calidad
   de agua.
5. Para el catastro minero: decidir si corregir (p. ej. `make_valid`) o descartar las 22
   geometrías inválidas antes de análisis espacial, y cómo tratar el valor centinela
   `FECHA_TERMINACION = 9999-12-31`.
6. Para los límites municipales: decidir cómo tratar el municipio `94663` (Mapiripana),
   presente solo en la capa geométrica, antes de usar Límites municipales como base
   territorial para cruces con DIVIPOLA.
7. Solo después de esas decisiones, avanzar a cruces reales entre fuentes (incluida la
   intersección espacial Límites municipales ↔ Catastro Minero) y a la construcción de
   un dataset maestro — seguir sin tocar RUNAP, SMByC, el MGN completo por otras vías,
   Global Forest Watch, MapBiomas, Sentinel ni Landsat.
