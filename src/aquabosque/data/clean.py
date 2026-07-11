"""Limpieza y estandarización de las fuentes MVP (Fase 3B).

Cada fuente se limpia por separado: estas funciones NO cruzan fuentes entre
sí ni construyen ningún dataset maestro, solo transforman un DataFrame crudo
en un DataFrame limpio, documentando cada decisión y cada pérdida de
registros en un reporte (dict) que el script orquestador vuelca a metadata
JSON y a un reporte Markdown.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

import pandas as pd

_MULTI_SPACE_RE = re.compile(r"\s+")
_NON_ALNUM_SPACE_RE = re.compile(r"[^A-Z0-9 ]")

# Variantes conocidas que deben colapsar a una sola forma canónica después de
# la normalización genérica (mayúsculas, sin tildes, sin signos).
_TEXT_EQUIVALENCES = {
    "BOGOTA D C": "BOGOTA DC",
    "BOGOTA DISTRITO CAPITAL": "BOGOTA DC",
    "SANTAFE DE BOGOTA DC": "BOGOTA DC",
    "SANTA FE DE BOGOTA DC": "BOGOTA DC",
    "BOGOTA DC": "BOGOTA DC",
}


def normalize_text(value: Any) -> str | None:
    """Normaliza un texto para comparación/cruce futuro entre fuentes:

    - mayúsculas
    - sin tildes/diacríticos
    - sin signos de puntuación (se reemplazan por espacio)
    - sin espacios dobles ni al inicio/fin
    - variantes conocidas de "Bogotá D.C." colapsadas a una forma única

    Devuelve None para valores nulos. Esta función NUNCA modifica el campo
    original: se usa para poblar un campo `*_norm` adicional, manteniendo
    trazabilidad entre el valor original y el normalizado.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().upper()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = _NON_ALNUM_SPACE_RE.sub(" ", text)
    text = _MULTI_SPACE_RE.sub(" ", text).strip()
    text = _TEXT_EQUIVALENCES.get(text, text)
    return text or None


def normalize_column_names(df: pd.DataFrame, rename_map: dict[str, str] | None = None) -> pd.DataFrame:
    """Normaliza nombres de columna (minúsculas, espacios -> guion bajo, sin
    guiones bajos repetidos) y aplica además un `rename_map` explícito de
    columnas mal nombradas por el origen (p. ej. campos Socrata que perdieron
    tildes al generar el nombre interno)."""
    df = df.copy()
    new_cols = {}
    for col in df.columns:
        c = str(col).strip().lower()
        c = re.sub(r"\s+", "_", c)
        c = re.sub(r"_+", "_", c)
        new_cols[col] = c
    df = df.rename(columns=new_cols)
    if rename_map:
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    return df


# ---------------------------------------------------------------------------
# DIVIPOLA - Códigos de municipios (DANE)
# ---------------------------------------------------------------------------


def clean_divipola(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Limpia el DataFrame crudo de DIVIPOLA (leído del XLSX con columnas
    depto_codigo, depto_nombre, mpio_codigo, mpio_nombre, tipo, longitud,
    latitud, nota)."""
    n_entrada = len(df_raw)
    df = df_raw.copy()

    # 1. Eliminar filas de título/notas al pie/completamente vacías: se
    #    consideran registros territoriales válidos solo los que tienen
    #    código y nombre de municipio y de departamento.
    mask_validos = df["mpio_codigo"].notna() & df["mpio_nombre"].notna() & df["depto_codigo"].notna()
    n_no_territoriales = int((~mask_validos).sum())
    df = df[mask_validos].copy()

    # 2. Código de departamento a texto de 2 dígitos.
    df["cod_dpto"] = df["depto_codigo"].astype(str).str.strip().str.zfill(2)

    # 3. Código de municipio a texto de 5 dígitos -> cod_dane_mpio.
    df["cod_dane_mpio"] = df["mpio_codigo"].astype("Int64").astype(str).str.zfill(5)

    # 4/5. Campos normalizados de nombre, con trazabilidad al original.
    df["nombre_dpto"] = df["depto_nombre"]
    df["nombre_dpto_norm"] = df["nombre_dpto"].map(normalize_text)
    df["nombre_mpio"] = df["mpio_nombre"]
    df["nombre_mpio_norm"] = df["nombre_mpio"].map(normalize_text)

    columnas_finales = [
        "cod_dpto",
        "nombre_dpto",
        "nombre_dpto_norm",
        "cod_dane_mpio",
        "nombre_mpio",
        "nombre_mpio_norm",
        "tipo",
        "longitud",
        "latitud",
    ]
    df = df[columnas_finales].reset_index(drop=True)

    # Duplicados completos (tras limpiar, no antes: las filas basura del
    # pie de página sí eran duplicados entre sí, pero ya se descartaron
    # arriba por no ser registros territoriales).
    n_duplicados = int(df.duplicated().sum())
    if n_duplicados:
        df = df.drop_duplicates().reset_index(drop=True)

    # --- Validaciones ---
    longitudes_ok = (df["cod_dane_mpio"].str.len() == 5).all()
    n_cod_dane_no5 = int((df["cod_dane_mpio"].str.len() != 5).sum())
    n_duplicados_cod_dane = int(df["cod_dane_mpio"].duplicated().sum())

    n_salida = len(df)

    report = {
        "filas_entrada": n_entrada,
        "filas_salida": n_salida,
        "registros_eliminados": {
            "filas_no_territoriales_titulo_notas_vacias": n_no_territoriales,
            "duplicados_completos_tras_limpieza": n_duplicados,
        },
        "columnas_finales": columnas_finales,
        "validaciones": {
            "cod_dane_mpio_longitud_5_para_todas_las_filas": bool(longitudes_ok),
            "n_filas_con_cod_dane_mpio_longitud_distinta_de_5": n_cod_dane_no5,
            "n_codigos_dane_duplicados": n_duplicados_cod_dane,
            "n_municipios_unidades_territoriales_final": n_salida,
        },
        "observaciones": [
            f"Se descartaron {n_no_territoriales} filas sin código/nombre de municipio "
            "(título del reporte DANE y notas al pie que arrastraba el XLSX dentro del rango de datos).",
            "Se eliminó la columna 'nota' del archivo original (99.6% nula, texto de nota al pie sin valor analítico).",
            "cod_dane_mpio se construyó forzando el código de municipio a texto con relleno de "
            "ceros a la izquierda (5 dígitos), corrigiendo la pérdida de cero inicial del XLSX original.",
        ],
    }
    return df, report


# ---------------------------------------------------------------------------
# ANM Títulos Mineros - Anotaciones RMN
# ---------------------------------------------------------------------------


def clean_anm_anotaciones(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    n_entrada = len(df_raw)
    df = normalize_column_names(df_raw)

    # codigo_expediente a texto limpio (sin espacios, mayúsculas por
    # consistencia con los prefijos alfabéticos ya presentes, p. ej. ABQ-101).
    df["codigo_expediente"] = df["codigo_expediente"].astype(str).str.strip().str.upper()

    # Fechas: vienen como texto MM/DD/AAAA (confirmado en Fase 3A: valores
    # como "04/15/2003" solo son válidos como mes/día/año). Se parsean a
    # datetime y se guardan en formato ISO YYYY-MM-DD; lo que no parsee
    # (p. ej. "N/E") queda como nulo, documentado, no se inventa una fecha.
    fecha_anotacion_dt = pd.to_datetime(df["fecha_anotacion"], format="%m/%d/%Y", errors="coerce")
    fecha_ejecutoria_dt = pd.to_datetime(df["fecha_ejecutoria"], format="%m/%d/%Y", errors="coerce")

    df["fecha_anotacion"] = fecha_anotacion_dt.dt.strftime("%Y-%m-%d")
    df["fecha_ejecutoria"] = fecha_ejecutoria_dt.dt.strftime("%Y-%m-%d")
    df["anio_anotacion"] = fecha_anotacion_dt.dt.year.astype("Int64")
    df["anio_ejecutoria"] = fecha_ejecutoria_dt.dt.year.astype("Int64")

    # Variables auxiliares normalizadas, con trazabilidad al original.
    df["tipo_anotacion_norm"] = df["tipo_de_anotacion"].map(normalize_text)
    df["modalidad_norm"] = df["modalidad"].map(normalize_text)

    columnas_finales = [
        "codigo_expediente",
        "estado_juridico",
        "modalidad",
        "modalidad_norm",
        "id_tipo_de_anotacion",
        "tipo_de_anotacion",
        "tipo_anotacion_norm",
        "fecha_anotacion",
        "anio_anotacion",
        "fecha_ejecutoria",
        "anio_ejecutoria",
        "observacion",
    ]
    df = df[columnas_finales].reset_index(drop=True)

    n_duplicados = int(df.duplicated().sum())
    if n_duplicados:
        df = df.drop_duplicates().reset_index(drop=True)

    n_salida = len(df)
    n_expedientes_unicos = int(df["codigo_expediente"].nunique())

    # Conteos de fechas no parseables sobre el DataFrame final (después de
    # deduplicar), para que coincidan exactamente con lo que queda en el CSV.
    n_fecha_anotacion_invalida = int(df["fecha_anotacion"].isna().sum())
    n_fecha_ejecutoria_invalida = int(df["fecha_ejecutoria"].isna().sum())

    report = {
        "filas_entrada": n_entrada,
        "filas_salida": n_salida,
        "registros_eliminados": {
            "duplicados_completos": n_duplicados,
        },
        "columnas_finales": columnas_finales,
        "validaciones": {
            "n_expedientes_unicos": n_expedientes_unicos,
            "expediente_es_llave_1_a_muchos_no_llave_unica_de_fila": n_expedientes_unicos < n_salida,
            "n_fecha_anotacion_no_parseable": n_fecha_anotacion_invalida,
            "n_fecha_ejecutoria_no_parseable": n_fecha_ejecutoria_invalida,
        },
        "observaciones": [
            "Esta fuente NO tiene ubicación geográfica (sin coordenadas ni departamento/municipio): "
            "cualquier cruce territorial futuro requiere el catastro minero geoespacial de la ANM "
            "(fuente distinta, WFS, pendiente de validación desde la Fase 1.5).",
            "codigo_expediente es una llave de agrupación 1-a-muchos (varias anotaciones por "
            "expediente), no una llave única de fila.",
            "estado_juridico es constante ('Activo' en el 100% de las filas de este dataset).",
            f"{n_fecha_anotacion_invalida} valores de fecha_anotacion y {n_fecha_ejecutoria_invalida} "
            "de fecha_ejecutoria no parsearon como MM/DD/AAAA (p. ej. 'N/E') y quedaron nulos, sin inventar fecha.",
        ],
    }
    return df, report


# ---------------------------------------------------------------------------
# IDEAM - Data Histórica de Calidad de Agua
# ---------------------------------------------------------------------------

_AGUA_COLUMN_RENAME = {
    "elevaci_n_m_s_n_m": "elevacion_msnm",
    "zona_hidrogr_fica_zh": "zona_hidrografica",
    "szh_c_digo_rea_zona_subzona": "codigo_subzona_hidrografica",
    "nombre_subzona_hidrogr_fica": "nombre_subzona_hidrografica",
    "codigo__muestra": "codigo_muestra",
}


def clean_calidad_agua(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    n_entrada = len(df_raw)
    df = normalize_column_names(df_raw, rename_map=_AGUA_COLUMN_RENAME)

    # Fecha: viene como texto ISO con hora (p. ej. "2007-03-09T00:00:00.000").
    # Se parsea y se guarda como fecha ISO (solo fecha, sin hora: la hora
    # observada en la muestra es siempre 00:00:00, no aporta información).
    fecha_dt = pd.to_datetime(df["fecha"], errors="coerce", format="mixed")
    df["fecha"] = fecha_dt.dt.strftime("%Y-%m-%d")
    df["anio"] = fecha_dt.dt.year.astype("Int64")

    # Coordenadas a numérico (defensivo: ya venían float en el JSON, pero se
    # fuerza la coerción explícita para no asumir el tipo de origen).
    df["latitud"] = pd.to_numeric(df["latitud"], errors="coerce")
    df["longitud"] = pd.to_numeric(df["longitud"], errors="coerce")

    # Resultado: se conserva el texto original (algunos valores son censura
    # de límite de detección, p. ej. "<0.4", "<10") y se agrega una versión
    # numérica aparte; lo que no convierte a número queda nulo en
    # resultado_numerico, no se inventa un valor.
    df["resultado_numerico"] = pd.to_numeric(df["resultado"], errors="coerce")

    # Campos normalizados con trazabilidad al original.
    df["departamento_norm"] = df["departamento"].map(normalize_text)
    df["municipio_norm"] = df["municipio"].map(normalize_text)
    df["propiedad_observada_norm"] = df["propiedad_observada"].map(normalize_text)

    columnas_finales = [
        "nombre_del_punto_de_monitoreo",
        "latitud",
        "longitud",
        "elevacion_msnm",
        "corriente",
        "zona_hidrografica",
        "codigo_subzona_hidrografica",
        "nombre_subzona_hidrografica",
        "departamento",
        "departamento_norm",
        "municipio",
        "municipio_norm",
        "fecha",
        "anio",
        "propiedad_observada",
        "propiedad_observada_norm",
        "resultado",
        "resultado_numerico",
        "unidad_del_resultado",
        "proyecto",
        "codigo_muestra",
    ]
    df = df[columnas_finales].reset_index(drop=True)

    n_duplicados = int(df.duplicated().sum())
    if n_duplicados:
        df = df.drop_duplicates().reset_index(drop=True)

    n_salida = len(df)
    anios_validos = df["anio"].dropna()
    rango_anios = (int(anios_validos.min()), int(anios_validos.max())) if len(anios_validos) else (None, None)
    n_departamentos = int(df["departamento_norm"].dropna().nunique())
    n_municipios = int(df["municipio_norm"].dropna().nunique())
    n_coords_no_nulas = int((df["latitud"].notna() & df["longitud"].notna()).sum())

    # Conteos de calidad recalculados SOBRE EL DATAFRAME FINAL (después de
    # deduplicar), para que coincidan exactamente con lo que queda en el CSV.
    n_fecha_invalida = int(df["fecha"].isna().sum())
    n_lat_invalida = int(df["latitud"].isna().sum())
    n_lon_invalida = int(df["longitud"].isna().sum())
    n_resultado_no_numerico = int(df["resultado_numerico"].isna().sum() - df["resultado"].isna().sum())

    report = {
        "filas_entrada": n_entrada,
        "filas_salida": n_salida,
        "registros_eliminados": {
            "duplicados_completos": n_duplicados,
        },
        "columnas_finales": columnas_finales,
        "validaciones": {
            "rango_anios": rango_anios,
            "n_departamentos_unicos_norm": n_departamentos,
            "n_municipios_unicos_norm": n_municipios,
            "n_filas_con_coordenadas_no_nulas": n_coords_no_nulas,
            "pct_filas_con_coordenadas_no_nulas": round(n_coords_no_nulas / n_salida * 100, 2) if n_salida else 0.0,
            "n_fecha_no_parseable": n_fecha_invalida,
            "n_latitud_no_numerica": n_lat_invalida,
            "n_longitud_no_numerica": n_lon_invalida,
            "n_resultado_no_numerico": n_resultado_no_numerico,
        },
        "observaciones": [
            "Se renombraron columnas con nombres truncados por el origen (Socrata pierde tildes al "
            "generar el nombre interno del campo), p. ej. elevaci_n_m_s_n_m -> elevacion_msnm, "
            "szh_c_digo_rea_zona_subzona -> codigo_subzona_hidrografica.",
            f"{n_resultado_no_numerico} valores de 'resultado' no son numéricos (incluye censura de "
            "límite de detección tipo '<0.4', '<10'); se conservan en el campo original 'resultado' "
            "como texto y quedan nulos en 'resultado_numerico', no se inventa un valor.",
            "departamento/municipio se conservan como texto original + versión *_norm; no hay código "
            "DANE en esta fuente, el cruce futuro con DIVIPOLA requerirá emparejar por nombre normalizado.",
        ],
    }
    return df, report
