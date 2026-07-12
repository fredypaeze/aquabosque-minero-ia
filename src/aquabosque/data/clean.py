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

import numpy as np
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


# ---------------------------------------------------------------------------
# Catastro Minero ANM - Títulos Vigentes (WFS, geoespacial)
# ---------------------------------------------------------------------------


def parse_catastro_fecha(series: pd.Series) -> pd.Series:
    """Parsea las fechas del catastro minero ANM, que vienen en dos formatos
    mezclados dentro de la misma columna:

    - "DD/MM/AAAA HH:MM:SS a.m./p.m." (con hora, en español)
    - "DD/MM/AAAA" (solo fecha)

    Lo que no parsea en ninguno de los dos formatos queda como NaT (nulo),
    sin inventar una fecha.
    """
    texto = series.astype(str)
    con_hora_normalizada = (
        texto.str.replace("p.m.", "PM", regex=False).str.replace("a.m.", "AM", regex=False)
    )
    dt_con_hora = pd.to_datetime(con_hora_normalizada, format="%d/%m/%Y %I:%M:%S %p", errors="coerce")
    dt_solo_fecha = pd.to_datetime(texto, format="%d/%m/%Y", errors="coerce")
    return dt_con_hora.fillna(dt_solo_fecha)


def json_safe_default(value: Any) -> Any:
    """Handler `default` para json.dumps: convierte tipos numpy/pandas que no
    son JSON-nativos. pandas.NA/NaT ya se reemplazan antes por None."""
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"Objeto de tipo {type(value)} no es serializable a JSON")


def dataframe_to_geojson(df: pd.DataFrame, geometry_col: str = "_geometry") -> dict:
    """Convierte un DataFrame con una columna de geometrías GeoJSON (dict o
    None) en un FeatureCollection GeoJSON válido; el resto de columnas se
    serializan como `properties` de cada Feature."""
    props_df = df.drop(columns=[geometry_col])
    # Reemplaza NaN/NaT/pd.NA por None ANTES de convertir a dict, para que el
    # GeoJSON resultante tenga `null` explícito en vez de "NaN" (inválido en
    # JSON estricto) o errores de serialización con tipos nulos de pandas.
    props_df = props_df.astype(object).where(props_df.notna(), None)
    records = props_df.to_dict(orient="records")
    geometries = df[geometry_col].tolist()

    features = [
        {"type": "Feature", "geometry": geom, "properties": props}
        for props, geom in zip(records, geometries)
    ]
    return {"type": "FeatureCollection", "features": features}


def clean_catastro_minero_anm(
    df_raw: pd.DataFrame, geometries: list[dict | None]
) -> tuple[pd.DataFrame, dict]:
    """Limpia las propiedades del catastro minero geoespacial de la ANM.

    `geometries` es una lista paralela (mismo orden/índice que `df_raw`) de
    geometrías GeoJSON (dict) o None; se conserva intacta en una columna
    auxiliar `_geometry` para poder reconstruir el GeoJSON de salida, y NUNCA
    se imprime completa en reportes.
    """
    n_entrada = len(df_raw)
    df = normalize_column_names(df_raw)
    df["_geometry"] = list(geometries)

    # codigo_expediente a texto limpio.
    df["codigo_expediente"] = df["codigo_expediente"].astype(str).str.strip().str.upper()

    # area_ha a numérico (ya venía float en el GeoJSON origen; coerción defensiva).
    df["area_ha"] = pd.to_numeric(df["area_ha"], errors="coerce")

    # ETAPA trae el valor de texto literal "null" (no un nulo real) para
    # títulos sin etapa definida: se convierte a nulo real antes de normalizar.
    df["etapa"] = df["etapa"].replace("null", pd.NA)

    # Fechas a ISO + año auxiliar.
    fecha_inscripcion_dt = parse_catastro_fecha(df["fecha_de_inscripcion"])
    fecha_terminacion_dt = parse_catastro_fecha(df["fecha_terminacion"])
    df["fecha_de_inscripcion"] = fecha_inscripcion_dt.dt.strftime("%Y-%m-%d")
    df["fecha_terminacion"] = fecha_terminacion_dt.dt.strftime("%Y-%m-%d")
    df["anio_inscripcion"] = fecha_inscripcion_dt.dt.year.astype("Int64")
    df["anio_terminacion"] = fecha_terminacion_dt.dt.year.astype("Int64")

    # Campos normalizados con trazabilidad al original. DEPARTAMENTOS y
    # MUNICIPIOS pueden traer varios valores separados por coma (un título
    # puede cruzar más de un municipio/departamento): se normaliza la cadena
    # completa, no se separa en esta fase (ver observaciones).
    df["modalidad_norm"] = df["modalidad"].map(normalize_text)
    df["etapa_norm"] = df["etapa"].map(normalize_text)
    df["estado_norm"] = df["estado"].map(normalize_text)
    df["minerales_norm"] = df["minerales"].map(normalize_text)
    df["departamentos_norm"] = df["departamentos"].map(normalize_text)
    df["municipios_norm"] = df["municipios"].map(normalize_text)

    columnas_finales = [
        "codigo_expediente",
        "estado",
        "estado_norm",
        "modalidad",
        "modalidad_norm",
        "etapa",
        "etapa_norm",
        "area_ha",
        "minerales",
        "minerales_norm",
        "nombre_de_titular",
        "numero_identificacion",
        "tipo_de_identificacion",
        "identificacion_titulares",
        "pto_pti",
        "instrumento_ambiental",
        "departamentos",
        "departamentos_norm",
        "municipios",
        "municipios_norm",
        "grupo_de_trabajo",
        "fecha_de_inscripcion",
        "anio_inscripcion",
        "fecha_terminacion",
        "anio_terminacion",
        "objectid",
        "_geometry",
    ]
    df = df[columnas_finales].reset_index(drop=True)

    # Duplicados completos: se comparan solo las columnas no geométricas
    # (un dict de geometría no es "hashable" para duplicated()).
    columnas_sin_geom = [c for c in columnas_finales if c != "_geometry"]
    n_duplicados = int(df[columnas_sin_geom].duplicated().sum())
    if n_duplicados:
        df = df.drop_duplicates(subset=columnas_sin_geom).reset_index(drop=True)

    n_salida = len(df)

    # --- Validaciones ---
    n_codigo_vacio = int((df["codigo_expediente"].isna() | (df["codigo_expediente"].str.strip() == "")).sum())
    n_codigo_duplicado = int(df["codigo_expediente"].duplicated().sum())

    n_geom_nulas = int(df["_geometry"].isna().sum())
    try:
        from shapely.geometry import shape

        n_geom_invalidas = 0
        for g in df["_geometry"]:
            if g is None or (isinstance(g, float) and pd.isna(g)):
                continue
            try:
                if not shape(g).is_valid:
                    n_geom_invalidas += 1
            except Exception:  # noqa: BLE001
                n_geom_invalidas += 1
        validez_verificada_con = "shapely"
    except ImportError:
        n_geom_invalidas = None
        validez_verificada_con = None

    n_area_no_numerica = int(df["area_ha"].isna().sum())
    n_fecha_inscripcion_invalida = int(df["fecha_de_inscripcion"].isna().sum())
    n_fecha_terminacion_invalida = int(df["fecha_terminacion"].isna().sum())
    n_etapa_null_literal_corregido = int((df_raw["ETAPA"] == "null").sum()) if "ETAPA" in df_raw.columns else 0
    n_fecha_terminacion_null_literal = (
        int((df_raw["FECHA_TERMINACION"] == "null").sum()) if "FECHA_TERMINACION" in df_raw.columns else 0
    )
    n_fecha_terminacion_9999 = int((fecha_terminacion_dt.dt.year == 9999).sum())

    report = {
        "filas_entrada": n_entrada,
        "filas_salida": n_salida,
        "registros_eliminados": {
            "duplicados_completos_no_geometricos": n_duplicados,
        },
        "columnas_finales": columnas_finales,
        "validaciones": {
            "n_codigo_expediente_vacio": n_codigo_vacio,
            "n_codigo_expediente_duplicado": n_codigo_duplicado,
            "codigo_expediente_es_unico": n_codigo_duplicado == 0 and n_codigo_vacio == 0,
            "n_geometrias_nulas": n_geom_nulas,
            "n_geometrias_invalidas": n_geom_invalidas,
            "validez_geometrica_verificada_con": validez_verificada_con,
            "n_area_ha_no_numerica": n_area_no_numerica,
            "n_fecha_inscripcion_no_parseable": n_fecha_inscripcion_invalida,
            "n_fecha_terminacion_no_parseable": n_fecha_terminacion_invalida,
        },
        "observaciones": [
            f"{n_etapa_null_literal_corregido} filas tenían el valor de texto literal 'null' en ETAPA "
            "(no un nulo real de JSON); se reemplazó por nulo real antes de normalizar.",
            f"{n_fecha_terminacion_null_literal} filas tenían el valor de texto literal 'null' en "
            "FECHA_TERMINACION; pd.to_datetime(errors='coerce') ya las deja como nulo real (explica "
            f"la mayoría de las {n_fecha_terminacion_invalida} fechas de terminación no parseables).",
            f"{n_fecha_terminacion_9999} filas tienen FECHA_TERMINACION con año 9999 (probable valor "
            "centinela de 'sin vencimiento'); con la versión de pandas usada en este proyecto SÍ se "
            "parsean correctamente (no quedan nulas), por lo que anio_terminacion=9999 debe tratarse "
            "como caso especial en cualquier cálculo de vigencia, no como una fecha real lejana.",
            "DEPARTAMENTOS y MUNICIPIOS pueden contener varios valores separados por coma (un título "
            "minero puede cruzar más de una unidad territorial); se normalizó la cadena completa, "
            "no se separó en filas ni en listas — cualquier cruce futuro por municipio individual "
            "requerirá explotar (split) estos campos primero.",
            f"Se detectaron {n_geom_invalidas if n_geom_invalidas is not None else 'N/D'} geometrías "
            "topológicamente inválidas (autointersecciones u otros problemas) vía shapely; NO se "
            "corrigieron ni se descartaron en esta fase, solo se documentan como riesgo para análisis "
            "espacial futuro (buffer(0) u otra corrección debe decidirse explícitamente más adelante).",
            "La geometría se conserva intacta (MultiPolygon) en la salida GeoJSON; no se simplificó "
            "ni se reproyectó.",
        ],
    }
    return df, report


# ---------------------------------------------------------------------------
# Límites municipales DANE (ArcGIS REST, capa Municipios) — Fase 3D
# ---------------------------------------------------------------------------


def _geometry_to_multipolygon(geom) -> Any:
    """Convierte una geometría shapely Polygon/MultiPolygon a MultiPolygon de
    forma consistente. No acepta otros tipos (deben filtrarse antes)."""
    from shapely.geometry import MultiPolygon, Polygon

    if isinstance(geom, MultiPolygon):
        return geom
    if isinstance(geom, Polygon):
        return MultiPolygon([geom])
    raise ValueError(f"Se esperaba Polygon o MultiPolygon, llegó {geom.geom_type}")


def repair_invalid_geometry(geom_dict: dict, *, cod_dane_mpio: str) -> tuple[dict | None, dict]:
    """Repara UNA geometría GeoJSON inválida con `shapely.make_valid` (no
    `buffer(0)`). Devuelve (geometría GeoJSON final o None si quedó vacía,
    registro de la reparación con trazabilidad completa).

    Si `make_valid` produce una `GeometryCollection` (mezcla de tipos), se
    conservan únicamente los componentes `Polygon`/`MultiPolygon`; los demás
    (líneas, puntos) se cuentan y se listan en el registro, nunca se
    descartan en silencio.
    """
    from shapely import make_valid
    from shapely.geometry import MultiPolygon, Polygon, mapping, shape
    from shapely.validation import explain_validity

    s = shape(geom_dict)
    motivo = explain_validity(s)
    tipo_original = s.geom_type

    repaired = make_valid(s)
    tipo_resultante = repaired.geom_type

    componentes_poligonales: list[Any] = []
    componentes_descartados: list[str] = []

    if repaired.geom_type == "GeometryCollection":
        for g in repaired.geoms:
            if g.geom_type == "Polygon":
                componentes_poligonales.append(g)
            elif g.geom_type == "MultiPolygon":
                componentes_poligonales.extend(list(g.geoms))
            else:
                componentes_descartados.append(g.geom_type)
    elif repaired.geom_type == "Polygon":
        componentes_poligonales.append(repaired)
    elif repaired.geom_type == "MultiPolygon":
        componentes_poligonales.extend(list(repaired.geoms))
    else:
        componentes_descartados.append(repaired.geom_type)

    final = MultiPolygon(componentes_poligonales) if componentes_poligonales else MultiPolygon([])

    registro = {
        "cod_dane_mpio": cod_dane_mpio,
        "motivo_invalidez": motivo,
        "tipo_original": tipo_original,
        "tipo_resultante_make_valid": tipo_resultante,
        "paso_a_geometrycollection": repaired.geom_type == "GeometryCollection",
        "quedo_vacia": final.is_empty,
        "n_componentes_poligonales_finales": len(final.geoms) if not final.is_empty else 0,
        "componentes_no_poligonales_descartados": componentes_descartados,
    }

    return (None if final.is_empty else mapping(final)), registro


def clean_limites_municipales_dane(features: list[dict]) -> tuple[pd.DataFrame, dict]:
    """Limpia la capa de límites municipales DANE (ArcGIS REST).

    `features` es la lista completa de Features GeoJSON crudas (properties +
    geometry). Devuelve un DataFrame con las propiedades limpias más una
    columna auxiliar `_geometry` (geometría final, siempre Polygon/MultiPolygon
    homogéneo como MultiPolygon, o None si quedó irremediablemente vacía tras
    reparar) y un reporte detallado de la limpieza, incluida la reparación de
    geometrías inválidas.

    No se elimina ninguna fila por invalidez de geometría: toda feature de
    entrada conserva su registro de propiedades en la salida, con la
    geometría reparada o documentada como vacía si no se pudo recuperar.
    """
    from shapely.geometry import mapping, shape

    n_entrada = len(features)
    props_list = [f.get("properties", {}) for f in features]
    df = normalize_column_names(pd.DataFrame(props_list))

    df["cod_dane_mpio"] = df["cod_mpio"].astype(str).str.strip().str.zfill(5)
    df["cod_dane_dpto"] = df["cod_dpto"].astype(str).str.strip().str.zfill(2)
    df["nombre_mpio_norm"] = df["nom_mpio"].map(normalize_text)
    df["nombre_dpto_norm"] = df["nom_dpto"].map(normalize_text)

    n_geometrias_nulas_entrada = 0
    n_geometrias_invalidas_entrada = 0
    n_geometrias_invalidas_salida = 0
    n_geometrias_vacias_salida = 0
    tipos_finales: dict[str, int] = {}
    reparaciones: list[dict] = []
    geometries_out: list[dict | None] = []

    codigos = df["cod_dane_mpio"].tolist()
    for feat, cod in zip(features, codigos):
        geom_dict = feat.get("geometry")
        if not geom_dict:
            n_geometrias_nulas_entrada += 1
            geometries_out.append(None)
            continue

        s = shape(geom_dict)
        if s.is_valid:
            geom_out = mapping(_geometry_to_multipolygon(s))
        else:
            n_geometrias_invalidas_entrada += 1
            geom_out, registro = repair_invalid_geometry(geom_dict, cod_dane_mpio=cod)
            reparaciones.append(registro)

        if geom_out is None:
            n_geometrias_vacias_salida += 1
            tipos_finales["(vacía)"] = tipos_finales.get("(vacía)", 0) + 1
        else:
            # Verificación dura: la geometría de salida (original ya válida,
            # o recién reparada) debe quedar válida; si no, se documenta,
            # nunca se asume silenciosamente que la reparación funcionó.
            if not shape(geom_out).is_valid:
                n_geometrias_invalidas_salida += 1
            tipos_finales[geom_out["type"]] = tipos_finales.get(geom_out["type"], 0) + 1
        geometries_out.append(geom_out)

    df["_geometry"] = geometries_out

    columnas_finales = [
        "objectid",
        "cod_dane_dpto",
        "nom_dpto",
        "nombre_dpto_norm",
        "cod_dane_mpio",
        "nom_mpio",
        "nombre_mpio_norm",
        "mpio_corrdeptal",
        "_geometry",
    ]
    df = df[columnas_finales].reset_index(drop=True)

    n_salida = len(df)
    n_cod_vacios = int((df["cod_dane_mpio"].isna() | (df["cod_dane_mpio"].str.strip() == "")).sum())
    n_cod_duplicados = int(df["cod_dane_mpio"].duplicated().sum())
    longitudes_ok = bool((df["cod_dane_mpio"].str.len() == 5).all())

    report = {
        "filas_entrada": n_entrada,
        "filas_salida": n_salida,
        "registros_eliminados": {
            "filas_eliminadas_por_invalidez_de_geometria": 0,
        },
        "columnas_finales": columnas_finales,
        "validaciones": {
            "n_cod_dane_mpio_vacios": n_cod_vacios,
            "n_cod_dane_mpio_duplicados": n_cod_duplicados,
            "cod_dane_mpio_es_unico": n_cod_duplicados == 0 and n_cod_vacios == 0,
            "cod_dane_mpio_longitud_5_para_todas_las_filas": longitudes_ok,
            "n_geometrias_nulas_entrada": n_geometrias_nulas_entrada,
            "n_geometrias_invalidas_entrada": n_geometrias_invalidas_entrada,
            "n_geometrias_reparadas": len(reparaciones),
            "n_geometrias_invalidas_salida": n_geometrias_invalidas_salida,
            "n_geometrias_vacias_salida": n_geometrias_vacias_salida,
            "tipos_geometricos_finales": tipos_finales,
        },
        "reparaciones_detalle": reparaciones,
        "observaciones": [
            "No se eliminó ninguna fila por invalidez de geometría: toda feature de entrada "
            "conserva su registro de propiedades en la salida.",
            f"{n_geometrias_invalidas_entrada} geometrías de entrada eran inválidas; se repararon "
            "con shapely.make_valid (no buffer(0) como primera opción).",
            "La salida geométrica final se normalizó siempre a MultiPolygon, incluso cuando el "
            "Polygon original o reparado era simple.",
            "Si make_valid devolvió una GeometryCollection mixta, se conservaron solo los "
            "componentes Polygon/MultiPolygon; los componentes de línea/punto se cuentan y quedan "
            "listados en 'reparaciones_detalle', nunca se descartan en silencio.",
            "CRS de la geometría: EPSG:4326 (mismo sistema de origen del servicio ArcGIS REST; no "
            "se reproyectó ni se simplificó ninguna coordenada).",
        ],
    }
    return df, report
