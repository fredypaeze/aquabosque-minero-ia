# 04 — Perfilamiento de datos crudos (Fase 3A)

Perfilamiento de las 3 fuentes MVP descargadas en la Fase 2A/2A.1, antes de cualquier
limpieza o transformación. Generado por `scripts/02_profile_raw_data.py`, que llama a
`src/aquabosque/data/profile.py`.

**Solo lectura:** no se limpió ni transformó ningún dato, no se guardó nada en
`data/processed/`, no se construyó dataset maestro, no se entrenó modelo ni se creó
dashboard, y no se descargó ninguna fuente nueva.

## Cómo regenerar los reportes

```powershell
.\venv\Scripts\Activate.ps1
python scripts\02_profile_raw_data.py
```

Los reportes se escriben en `outputs/reports/raw_data_profile/` (4 archivos:
`divipola_profile.md`, `mineria_anm_profile.md`, `calidad_agua_profile.md`,
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

## Problema transversal de integración territorial

Ninguna de las 3 fuentes comparte hoy una llave territorial lista para join directo:

- DIVIPOLA tiene el código DANE, pero mal tipado (numérico, sin cero inicial).
- ANM Anotaciones RMN no trae territorio en absoluto en este dataset puntual.
- Calidad de agua trae territorio como texto libre, sin código DANE.

La integración futura (Fase 3B en adelante) va a necesitar normalización de nombres de
departamento/municipio (mayúsculas, tildes, variantes como "BOGOTÁ, D.C." vs "BOGOTÁ
D.C.") y no un simple `merge` por código.

## Llaves de integración candidatas

| Fuente | Llave candidata |
|---|---|
| DIVIPOLA | `mpio_codigo` (código DANE de municipio, 5 dígitos, una vez corregido el tipo) |
| ANM Anotaciones RMN | `codigo_expediente` (llave de agrupación 1-a-muchos, no llave única de fila) |
| Calidad de agua IDEAM | coordenadas (`latitud`/`longitud`) + `szh_c_digo_rea_zona_subzona` (subzona hidrográfica) para cruzar con cuencas; `departamento`/`municipio` de texto para cruzar con DIVIPOLA tras normalización |

## Recomendación para Fase 3B

1. Documentar explícitamente, antes de escribir código de limpieza, los tipos objetivo
   por columna (códigos como texto con ceros a la izquierda, fechas en ISO 8601) y cómo
   descartar las filas basura del XLSX de DIVIPOLA.
2. Diseñar la normalización de nombres de departamento/municipio antes de intentar
   cualquier cruce entre calidad de agua/ANM y DIVIPOLA.
3. Decidir cómo tratar la relación 1-a-muchos de `codigo_expediente` en ANM (¿agregar a
   nivel de expediente antes de integrar, o mantener el detalle de anotaciones?).
4. Revisar y, si aplica, estandarizar los ~80 valores de `propiedad_observada` en calidad
   de agua.
5. Solo después de esas decisiones, avanzar a limpieza real guardando en
   `data/processed/` — seguir sin tocar RUNAP, SMByC, el catastro minero WFS completo ni
   el MGN completo.
