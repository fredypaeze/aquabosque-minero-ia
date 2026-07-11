# 05 — Limpieza y estandarización de datos (Fase 3B)

Limpieza de las 3 fuentes MVP descargadas (Fase 2A/2A.1) y perfiladas (Fase 3A), cada una
por separado. Generado por `scripts/03_clean_raw_data.py`, que usa
`src/aquabosque/data/clean.py`.

**Esta fase NO cruza fuentes ni construye dataset maestro.** Cada fuente se limpia de
forma independiente y se guarda en `data/processed/`.

## Cómo regenerar la limpieza

```powershell
.\venv\Scripts\Activate.ps1
python scripts\03_clean_raw_data.py
```

Salidas (todas ignoradas por git, igual que el resto de `data/processed/` y
`outputs/reports/` desde la Fase 0 — son artefactos regenerables):

- `data/processed/territorio/divipola_municipios_clean.csv` (+ `.metadata.json`)
- `data/processed/mineria/anm_anotaciones_rmn_clean.csv` (+ `.metadata.json`)
- `data/processed/agua/ideam_calidad_agua_clean.csv` (+ `.metadata.json`)
- `outputs/reports/cleaning/cleaning_summary.md`

## Función de normalización de texto reutilizable

`normalize_text()` en `src/aquabosque/data/clean.py`: mayúsculas, sin tildes (vía
`unicodedata`), sin signos de puntuación, sin espacios dobles, y colapsa variantes
conocidas de "Bogotá D.C." (`BOGOTÁ, D.C.`, `Bogota D.C.`, `BOGOTA D C`, `Bogotá Distrito
Capital`, etc.) a una única forma canónica `BOGOTA DC`. Se probó explícitamente con esas
4 variantes y las 4 colapsan correctamente a `BOGOTA DC`.

Esta función **nunca reemplaza el campo original**: cada columna de texto relevante
(nombre de municipio, departamento, modalidad, tipo de anotación, propiedad observada)
queda con su valor original intacto más una columna `*_norm` adicional, para mantener
trazabilidad.

## Filas antes / después por fuente

| Fuente | Filas entrada | Filas salida | Diferencia | Tamaño CSV |
|---|---|---|---|---|
| DIVIPOLA - Códigos de municipios (DANE) | 1.135 | 1.122 | -13 | 86,9 KB |
| ANM Títulos Mineros - Anotaciones RMN | 37.763 | 37.555 | -208 | 14,3 MB |
| IDEAM - Data Histórica de Calidad de Agua | 134.261 | 134.216 | -45 | 32,4 MB |

## Columnas finales por fuente

- **DIVIPOLA:** `cod_dpto`, `nombre_dpto`, `nombre_dpto_norm`, `cod_dane_mpio`,
  `nombre_mpio`, `nombre_mpio_norm`, `tipo`, `longitud`, `latitud`
- **ANM Anotaciones RMN:** `codigo_expediente`, `estado_juridico`, `modalidad`,
  `modalidad_norm`, `id_tipo_de_anotacion`, `tipo_de_anotacion`, `tipo_anotacion_norm`,
  `fecha_anotacion`, `anio_anotacion`, `fecha_ejecutoria`, `anio_ejecutoria`, `observacion`
- **Calidad de agua IDEAM:** `nombre_del_punto_de_monitoreo`, `latitud`, `longitud`,
  `elevacion_msnm`, `corriente`, `zona_hidrografica`, `codigo_subzona_hidrografica`,
  `nombre_subzona_hidrografica`, `departamento`, `departamento_norm`, `municipio`,
  `municipio_norm`, `fecha`, `anio`, `propiedad_observada`, `propiedad_observada_norm`,
  `resultado`, `resultado_numerico`, `unidad_del_resultado`, `proyecto`, `codigo_muestra`

## Registros eliminados y motivo

### DIVIPOLA
- **13 filas** descartadas por no ser registros territoriales válidos (título del
  reporte DANE y notas al pie que el XLSX arrastraba dentro del rango de datos leído).
- **0 duplicados completos** tras la limpieza (los duplicados de la Fase 3A eran, en su
  mayoría, esas mismas 13 filas basura, ya descartadas por el filtro anterior).
- Se eliminó la columna `nota` (99,6% nula, texto de nota al pie sin valor analítico).

### ANM Anotaciones RMN
- **208 filas** completamente duplicadas eliminadas.

### Calidad de agua IDEAM
- **45 filas** completamente duplicadas eliminadas.

## Calidad de fechas / coordenadas / resultados

- **DIVIPOLA:** `cod_dane_mpio` tiene longitud 5 en el 100% de las 1.122 filas finales
  (0 con longitud distinta), 0 códigos DANE duplicados.
- **ANM:** `fecha_anotacion` parseó al 100% (0 no parseables); `fecha_ejecutoria` tuvo
  **1.724 valores no parseables** (p. ej. `"N/E"`), que quedaron nulos en el CSV final —
  no se inventó ninguna fecha.
- **Calidad de agua:** `fecha` parseó al 100% (0 no parseables). `latitud`/`longitud` son
  100% numéricas y no nulas (134.216 de 134.216 filas con coordenadas completas).
  `resultado_numerico` tiene **38.440 valores nulos** de 134.216 (≈28,6%): corresponden en
  buena parte a notación de censura de límite de detección (`"<0.4"`, `"<10"`, etc.), que
  se conserva intacta en el campo original `resultado` (texto) para no perder esa
  información.

## Riesgos pendientes para integración (Fase 4+)

- Ninguna de las 3 fuentes comparte hoy una llave territorial 100% directa: DIVIPOLA
  tiene `cod_dane_mpio` (código DANE), pero ANM Anotaciones RMN no tiene territorio en
  absoluto, y calidad de agua solo tiene `departamento_norm`/`municipio_norm` de texto
  (sin código DANE).
- El cruce territorial de calidad de agua con DIVIPOLA requerirá emparejar
  `municipio_norm` contra `nombre_mpio_norm` (texto normalizado, no código), con riesgo
  de nombres compuestos o variantes de escritura no cubiertas por las equivalencias
  conocidas hoy (solo se resolvió explícitamente el caso Bogotá D.C.).
- `codigo_expediente` de ANM sigue siendo una llave 1-a-muchos (6.769 expedientes únicos
  sobre 37.555 filas): cualquier integración futura debe decidir si se agrega a nivel de
  expediente antes de cruzar con otras fuentes.
- `resultado_numerico` de calidad de agua tiene ~28,6% de nulos por censura de límite de
  detección; un análisis agregado ingenuo (promedios simples, etc.) debe decidir
  explícitamente cómo tratar esos casos en vez de ignorarlos silenciosamente.
- El catastro minero geoespacial de la ANM (WFS, con `DEPARTAMENTOS`/`MUNICIPIOS` de
  texto libre) sigue pendiente de validación desde la Fase 1.5 y sería la vía natural
  para dar ubicación geográfica a ANM Anotaciones RMN vía `codigo_expediente`.

## Próximos pasos (Fase 4+, no ejecutados aquí)

1. Diseñar la estrategia de emparejamiento de nombres de municipio/departamento
   (más allá del caso Bogotá D.C. ya resuelto) antes de cualquier cruce real.
2. Decidir el nivel de agregación de ANM Anotaciones RMN (por expediente vs. detalle de
   anotación) antes de integrarlo con otras fuentes.
3. Solo entonces, avanzar a cruces y a la construcción de un dataset maestro — todavía
   sin tocar RUNAP, SMByC, el catastro minero WFS completo ni el MGN completo.
