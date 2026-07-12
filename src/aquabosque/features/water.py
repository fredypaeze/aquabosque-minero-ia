"""Indicadores descriptivos de calidad hídrica por unidad territorial
(Fase 4B).

Esta fase NO afirma contaminación, NO atribuye resultados a minería, NO
construye índice de riesgo, NO aplica límites legales/normativos y NO
etiqueta observaciones como "contaminadas". Todo lo que produce este módulo
son conteos, agregaciones descriptivas (mínimo/mediana/máximo/pendiente) y
banderas de disponibilidad de monitoreo.
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd

M2_PER_HA = 10_000.0

UMBRAL_MONITOREO_ESCASO_N_OBS = 5
UMBRAL_COBERTURA_TEMPORAL_LIMITADA_ANIOS = 3
UMBRAL_CATALOGO_MIN_OBS_NUMERICAS_COMPARABLE = 5
UMBRAL_CATALOGO_MIN_PCT_NUMERICO_COMPARABLE = 10.0

# Selección de parámetros candidatos a indicadores municipales específicos
# (sección K): mínimos documentados, evaluados —no asumidos— en el script
# orquestador contra el catálogo real.
UMBRAL_PARAMETRO_MIN_OBSERVACIONES = 500
UMBRAL_PARAMETRO_MIN_MUNICIPIOS = 20

# Tendencias (sección L)
UMBRAL_TENDENCIA_MIN_ANIOS = 5
UMBRAL_TENDENCIA_MIN_OBS_NUMERICAS = 10
UMBRAL_TENDENCIA_MIN_PERIODO_ANIOS = 4


# ---------------------------------------------------------------------------
# E. Resultados censurados y no numéricos
# ---------------------------------------------------------------------------

_CENSORED_RE = re.compile(r"^\s*([<>])\s*([0-9]+(?:[.,][0-9]+)?)\s*$")


def parse_censored_results(df: pd.DataFrame) -> pd.DataFrame:
    """Añade las columnas derivadas de la sección E a partir de `resultado`
    (texto original) y `resultado_numerico` (ya parseado en la Fase 3B).
    Nunca reemplaza un valor censurado por 0 ni por límite/2 en las columnas
    "oficiales" — la imputación queda en una columna aparte, explícitamente
    marcada, que no se usa por defecto en ningún indicador de esta fase."""
    out = df.copy()
    out["resultado_texto_original"] = out["resultado"]

    extraido = out["resultado"].str.extract(_CENSORED_RE)
    operador = extraido[0]
    limite_str = extraido[1].str.replace(",", ".", regex=False)
    limite = pd.to_numeric(limite_str, errors="coerce")

    out["operador_resultado"] = operador.fillna("=")
    out["limite_deteccion"] = limite
    out["resultado_es_censurado_inferior"] = operador == "<"
    out["resultado_es_censurado_superior"] = operador == ">"
    out["resultado_es_numerico"] = out["resultado_numerico"].notna()
    out["resultado_numerico_observado"] = out["resultado_numerico"]

    # Imputación opcional SOLO para censura inferior (regla explícita del
    # encargo: limite_deteccion / 2). Para censura superior (>X) no hay una
    # regla documentada equivalente en esta fase, así que se deja NaN — no
    # se inventa un factor arbitrario.
    out["resultado_imputado_ld_2"] = np.where(
        out["resultado_es_censurado_inferior"],
        out["limite_deteccion"] / 2.0,
        np.where(out["resultado_es_numerico"], out["resultado_numerico_observado"], np.nan),
    )
    return out


def summarize_censoring(df_parsed: pd.DataFrame) -> dict[str, int]:
    return {
        "n_total": len(df_parsed),
        "n_numericos": int(df_parsed["resultado_es_numerico"].sum()),
        "n_censurados_inferior": int(df_parsed["resultado_es_censurado_inferior"].sum()),
        "n_censurados_superior": int(df_parsed["resultado_es_censurado_superior"].sum()),
        "n_no_numerico_no_censurado": int(
            (~df_parsed["resultado_es_numerico"] & ~df_parsed["resultado_es_censurado_inferior"] & ~df_parsed["resultado_es_censurado_superior"]).sum()
        ),
    }


# ---------------------------------------------------------------------------
# F. Identificación de sitios de monitoreo
# ---------------------------------------------------------------------------

_CODIGO_PUNTO_RE = re.compile(r"\[([^\]]+)\]\s*$")

METODO_SITIO_CODIGO_EXTRAIDO = "codigo_estacion_extraido"
METODO_SITIO_HASH = "hash_lat_lon_municipio_nombre"
PRECISION_REDONDEO_COORDENADAS = 5  # decimales (~1.1 m en el ecuador)


def build_site_ids(df: pd.DataFrame) -> pd.DataFrame:
    """`sitio_monitoreo_id` reproducible (sección F). Prioridad:

    1. Código de estación/punto: se extrae de
       `nombre_del_punto_de_monitoreo`, que en esta fuente incluye un código
       IDEAM entre corchetes al final en 194/243 puntos (verificado: ese
       código es único por punto, y coincide 1 a 1 con pares lat/lon únicos).
    2. Código de muestra/proyecto: evaluados y DESCARTADOS como prioridad 2.
       `codigo_muestra` identifica una visita/evento de muestreo (cambia con
       cada fecha en el mismo sitio, ~19.7 filas por código en promedio), no
       un sitio estable en el tiempo. `proyecto` es demasiado agregado (8
       valores para 243 sitios). Ninguno identifica el sitio de forma
       estable, así que no se usan.
    3. Hash determinístico SHA-256 (12 hex) de latitud/longitud redondeadas
       a 5 decimales (~1,1 m de precisión en el ecuador) + `municipio_norm`
       + `nombre_del_punto_de_monitoreo`, para los 49/243 puntos sin código
       entre corchetes.
    """
    out = df.copy()
    codigos_extraidos = out["nombre_del_punto_de_monitoreo"].str.extract(_CODIGO_PUNTO_RE)[0]

    lat_r = out["latitud"].round(PRECISION_REDONDEO_COORDENADAS).astype(str)
    lon_r = out["longitud"].round(PRECISION_REDONDEO_COORDENADAS).astype(str)
    base_hash = lat_r + "|" + lon_r + "|" + out["municipio_norm"].astype(str) + "|" + out["nombre_del_punto_de_monitoreo"].astype(str)
    hashes = base_hash.map(lambda s: "hash_" + hashlib.sha256(s.encode("utf-8")).hexdigest()[:12])

    out["sitio_monitoreo_id"] = codigos_extraidos.where(codigos_extraidos.notna(), hashes)
    out["metodo_sitio_id"] = np.where(codigos_extraidos.notna(), METODO_SITIO_CODIGO_EXTRAIDO, METODO_SITIO_HASH)
    return out


# ---------------------------------------------------------------------------
# D. Catálogo de parámetros hídricos
# ---------------------------------------------------------------------------

_CLASIFICACION_POR_PARAMETRO: dict[str, str] = {
    "TEMPERATURA": "fisico",
    "TURBIDEZ": "fisico",
    "CONDUCTIVIDAD ELECTRICA": "fisico",
    "CAUDAL": "fisico",
    "SOLIDOS SUSPENDIDOS TOTALES": "fisico",
    "SOLIDOS TOTALES": "fisico",
    "SOLIDOS DISUELTOS TOTALES": "fisico",
    "PH": "quimico",
    "DUREZA TOTAL": "quimico",
    "ALCALINIDAD TOTAL": "quimico",
    "SULFATO": "quimico",
    "SULFURO": "quimico",
    "CLORURO": "quimico",
    "OXIGENO DISUELTO OD": "quimico",
    "COLIFORMES TOTALES POR SUSTRATO DEFINIDO": "microbiologico",
    "COLIFORMES TOTALES POR FILTRACION POR MEMBRANA": "microbiologico",
    "ESCHERICHIA COLI POR SUSTRATO DEFINIDO": "microbiologico",
    "ESCHERICHIA COLI POR FILTRACION POR MEMBRANA": "microbiologico",
    "ZINC TOTAL EN AGUA": "metal_metaloide",
    "ZINC POTENCIALMENTE BIODISPONIBLE": "metal_metaloide",
    "NIQUEL TOTAL EN AGUA": "metal_metaloide",
    "NIQUEL POTENCIALMENTE BIODISPONIBLE": "metal_metaloide",
    "COBRE TOTAL EN AGUA": "metal_metaloide",
    "COBRE POTENCIALMENTE BIODISPONIBLE": "metal_metaloide",
    "CROMO TOTAL EN AGUA": "metal_metaloide",
    "CROMO POTENCIALMENTE BIODISPONIBLE": "metal_metaloide",
    "CROMO HEXAVALENTE": "metal_metaloide",
    "CADMIO TOTAL EN AGUA": "metal_metaloide",
    "CADMIO POTENCIALMENTE BIODISPONIBLE": "metal_metaloide",
    "PLOMO TOTAL EN AGUA": "metal_metaloide",
    "PLOMO POTENCIALMENTE BIODISPONIBLE": "metal_metaloide",
    "MANGANESO TOTAL EN AGUA": "metal_metaloide",
    "MANGANESO POTENCIALMENTE BIODISPONIBLE": "metal_metaloide",
    "HIERRO TOTAL EN AGUA": "metal_metaloide",
    "HIERRO POTENCIALMENTE BIODISPONIBLE": "metal_metaloide",
    "ALUMINIO TOTAL EN AGUA": "metal_metaloide",
    "ALUMINIO POTENCIALMENTE BIODISPONIBLE": "metal_metaloide",
    "MERCURIO TOTAL EN AGUA": "metal_metaloide",
    "MERCURIO TOTAL EN SEDIMENTOS": "metal_metaloide",
    "CALCIO TOTAL": "metal_metaloide",
    "MAGNESIO TOTAL": "metal_metaloide",
    "FOSFORO REACTIVO DISUELTO": "nutriente",
    "FOSFORO TOTAL": "nutriente",
    "NITRATO": "nutriente",
    "NITRITO": "nutriente",
    "NITROGENO AMONIACAL": "nutriente",
    "NITROGENO KJELDAHL TOTAL": "nutriente",
    "NITROGENO TOTAL": "nutriente",
    "NITROGENO ORGANICO": "nutriente",
    "HIDROCARBUROS": "hidrocarburo_organico",
    "GRASAS Y ACEITES": "hidrocarburo_organico",
    "FENOLES": "hidrocarburo_organico",
    "HEXACLOROCICLOHEXANO HCH EN AGUA": "hidrocarburo_organico",
    "HEXACLOROCICLOHEXA HCH EN AGUA": "hidrocarburo_organico",
    "ENDOSULFAN EN AGUA": "hidrocarburo_organico",
    "ENDOSULFAN SULFATO EN AGUA": "hidrocarburo_organico",
    "ENDRIN CETONA EN AGUA": "hidrocarburo_organico",
    "ENDRIN EN AGUA": "hidrocarburo_organico",
    "ENDRIN ALDEHIDO EN AGUA": "hidrocarburo_organico",
    "P P DDD EN AGUA": "hidrocarburo_organico",
    "P P DDT EN AGUA": "hidrocarburo_organico",
    "P P DDE EN AGUA": "hidrocarburo_organico",
    "TRANS HEPTACLORO ENDO EPOXIDO ISOMERO A EN AGUA": "hidrocarburo_organico",
    "HEPTACLORO EN AGUA": "hidrocarburo_organico",
    "PROPANIL EN AGUA": "hidrocarburo_organico",
    "CLOROTALONIL EN AGUA": "hidrocarburo_organico",
    "DIELDRIN ENA AGUA": "hidrocarburo_organico",
    "ALDRIN EN AGUA": "hidrocarburo_organico",
    "METOXICLORO EN AGUA": "hidrocarburo_organico",
    "CLORPIRIFOS EN AGUA": "hidrocarburo_organico",
    "METIL PARATION EN AGUA": "hidrocarburo_organico",
    "ATRAZINA EN AGUA": "hidrocarburo_organico",
    "MALATION EN AGUA": "hidrocarburo_organico",
    "AMETRINA EN AGUA": "hidrocarburo_organico",
    "DEMANDA QUIMICA DE OXIGENO DQO": "indicador_agregado",
    "DEMANDA BIOQUIMICA DE OXIGENO DBO5": "indicador_agregado",
    "CARBONO ORGANICO TOTAL COT": "indicador_agregado",
}


def classify_parameter(propiedad_norm: str) -> str:
    """Clasifica (etiqueta de categoría), NUNCA equivale nombres distintos
    entre sí. Si un parámetro no está en la tabla explícita, devuelve
    'otro_no_clasificado' — no se inventa una categoría por analogía."""
    return _CLASIFICACION_POR_PARAMETRO.get(propiedad_norm, "otro_no_clasificado")


def normalize_unit_text(unidad: str) -> str:
    """Normalización de texto pura (espacios, capitalización de 'kg' al
    final de una fracción, capitalización de la frase 'unidades de pH') —
    NUNCA una conversión numérica entre unidades distintas. Colapsa
    variantes de la MISMA unidad literal (p. ej. 'mg Cd/Kg' y 'mg Cd/kg') sin
    tocar unidades genuinamente diferentes (mg/L sigue siendo distinto de
    µg/L)."""
    u = re.sub(r"\s+", " ", str(unidad).strip())
    u = re.sub(r"/Kg$", "/kg", u)
    if u.strip().lower() == "unidades de ph":
        return "Unidades de pH"
    return u


def build_parameter_catalog(df_parsed: pd.DataFrame) -> pd.DataFrame:
    """Sección D: una fila por combinación observada
    `propiedad_observada_norm` + `unidad_norm` (nunca se mezclan resultados
    de unidades distintas dentro de una fila)."""
    df = df_parsed.copy()
    df["unidad_norm"] = df["unidad_del_resultado"].map(normalize_unit_text)

    filas = []
    for (prop, unidad), grupo in df.groupby(["propiedad_observada_norm", "unidad_norm"]):
        numericos = grupo[grupo["resultado_es_numerico"]]
        n_num = len(numericos)
        n_obs = len(grupo)
        pct_num = round(n_num / n_obs * 100, 2) if n_obs else 0.0

        comparable = True
        razon_no_comparable = ""
        if n_num < UMBRAL_CATALOGO_MIN_OBS_NUMERICAS_COMPARABLE:
            comparable = False
            razon_no_comparable = f"menos de {UMBRAL_CATALOGO_MIN_OBS_NUMERICAS_COMPARABLE} resultados numéricos"
        elif pct_num < UMBRAL_CATALOGO_MIN_PCT_NUMERICO_COMPARABLE:
            comparable = False
            razon_no_comparable = f"menos de {UMBRAL_CATALOGO_MIN_PCT_NUMERICO_COMPARABLE}% de resultados son numéricos (mayoría censurada/no numérica)"

        filas.append(
            {
                "propiedad_observada_original": grupo["propiedad_observada"].iloc[0],
                "propiedad_observada_norm": prop,
                "unidad_original": grupo["unidad_del_resultado"].iloc[0],
                "unidad_norm": unidad,
                "n_observaciones": n_obs,
                "n_resultados_numericos": n_num,
                "n_resultados_no_numericos": n_obs - n_num,
                "pct_resultados_numericos": pct_num,
                "valor_minimo": numericos["resultado_numerico_observado"].min() if n_num else None,
                "valor_maximo": numericos["resultado_numerico_observado"].max() if n_num else None,
                "valor_mediana": numericos["resultado_numerico_observado"].median() if n_num else None,
                "anio_minimo": int(grupo["anio"].min()),
                "anio_maximo": int(grupo["anio"].max()),
                "clasificacion_parametro": classify_parameter(prop),
                "comparable_entre_registros": comparable,
                "razon_no_comparable": razon_no_comparable,
                "observaciones": (
                    f"{grupo['sitio_monitoreo_id'].nunique() if 'sitio_monitoreo_id' in grupo.columns else 'N/D'} sitios distintos."
                ),
            }
        )
    return pd.DataFrame(filas).sort_values("n_observaciones", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# I. Tabla sitio-parámetro-año
# ---------------------------------------------------------------------------


def build_site_parameter_year_table(df_assigned: pd.DataFrame) -> pd.DataFrame:
    """Sección I: una fila por sitio_monitoreo_id + propiedad_observada_norm
    + unidad_norm + anio. Nunca agrega unidades distintas en una misma fila
    (unidad_norm es parte de la llave de agrupación)."""
    grouped = df_assigned.groupby(
        ["sitio_monitoreo_id", "cod_dane_mpio_asignado", "cod_dane_dpto_asignado", "propiedad_observada_norm", "unidad_norm", "anio"],
        dropna=False,
    )

    filas = []
    for keys, grupo in grouped:
        sitio, cod_mpio, cod_dpto, prop, unidad, anio = keys
        numericos = grupo[grupo["resultado_es_numerico"]]
        n_num = len(numericos)
        n_obs = len(grupo)
        n_censurados = int((grupo["resultado_es_censurado_inferior"] | grupo["resultado_es_censurado_superior"]).sum())

        calidad = "alta" if n_num == n_obs else ("media" if n_num > 0 else "baja_solo_censurado")

        filas.append(
            {
                "sitio_monitoreo_id": sitio,
                "cod_dane_mpio": cod_mpio,
                "cod_dane_dpto": cod_dpto,
                "propiedad_observada_norm": prop,
                "unidad_norm": unidad,
                "anio": anio,
                "n_observaciones": n_obs,
                "n_resultados_numericos": n_num,
                "n_resultados_censurados": n_censurados,
                "resultado_min": numericos["resultado_numerico_observado"].min() if n_num else None,
                "resultado_mediana": numericos["resultado_numerico_observado"].median() if n_num else None,
                "resultado_media": numericos["resultado_numerico_observado"].mean() if n_num else None,
                "resultado_max": numericos["resultado_numerico_observado"].max() if n_num else None,
                "primera_fecha": grupo["fecha"].min(),
                "ultima_fecha": grupo["fecha"].max(),
                "pct_resultados_numericos": round(n_num / n_obs * 100, 2) if n_obs else 0.0,
                "calidad_agregacion": calidad,
            }
        )
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# L. Tendencias temporales (Theil-Sen manual, sin scipy)
# ---------------------------------------------------------------------------


def theil_sen_slope(x: np.ndarray, y: np.ndarray) -> float:
    """Pendiente de Theil-Sen: mediana de las pendientes de todos los pares
    (i,j) con x_i != x_j. Implementación manual (numpy puro) para no añadir
    scipy como dependencia solo para esta fase."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(x)
    pendientes = []
    for i in range(n):
        for j in range(i + 1, n):
            if x[j] != x[i]:
                pendientes.append((y[j] - y[i]) / (x[j] - x[i]))
    if not pendientes:
        return float("nan")
    return float(np.median(pendientes))


def build_trends_table(df_assigned: pd.DataFrame) -> pd.DataFrame:
    """Sección L: pendiente anual por unidad territorial + parámetro +
    unidad, calculada SOLO si hay evidencia suficiente (>=5 años distintos,
    >=10 observaciones numéricas, periodo >=4 años)."""
    numericos = df_assigned[df_assigned["resultado_es_numerico"] & df_assigned["cod_dane_mpio_asignado"].notna()]
    grouped = numericos.groupby(["cod_dane_mpio_asignado", "propiedad_observada_norm", "unidad_norm"])

    filas = []
    for (cod_mpio, prop, unidad), grupo in grouped:
        anios = sorted(grupo["anio"].unique())
        n_anios = len(anios)
        n_obs = len(grupo)
        periodo = (max(anios) - min(anios)) if anios else 0

        calculable = n_anios >= UMBRAL_TENDENCIA_MIN_ANIOS and n_obs >= UMBRAL_TENDENCIA_MIN_OBS_NUMERICAS and periodo >= UMBRAL_TENDENCIA_MIN_PERIODO_ANIOS
        razon = ""
        pendiente = None
        if not calculable:
            razones = []
            if n_anios < UMBRAL_TENDENCIA_MIN_ANIOS:
                razones.append(f"{n_anios} años distintos (< {UMBRAL_TENDENCIA_MIN_ANIOS})")
            if n_obs < UMBRAL_TENDENCIA_MIN_OBS_NUMERICAS:
                razones.append(f"{n_obs} observaciones numéricas (< {UMBRAL_TENDENCIA_MIN_OBS_NUMERICAS})")
            if periodo < UMBRAL_TENDENCIA_MIN_PERIODO_ANIOS:
                razones.append(f"periodo de {periodo} años (< {UMBRAL_TENDENCIA_MIN_PERIODO_ANIOS})")
            razon = "; ".join(razones)
        else:
            pendiente = theil_sen_slope(grupo["anio"].to_numpy(), grupo["resultado_numerico_observado"].to_numpy())

        filas.append(
            {
                "cod_dane_mpio": cod_mpio,
                "propiedad_observada_norm": prop,
                "unidad_norm": unidad,
                "n_observaciones": n_obs,
                "n_anios": n_anios,
                "anio_inicio": min(anios) if anios else None,
                "anio_fin": max(anios) if anios else None,
                "pendiente_anual": pendiente,
                "metodo_tendencia": "theil_sen" if calculable else None,
                "tendencia_calculable": calculable,
                "razon_no_calculable": razon,
            }
        )
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# J/M. Indicadores territoriales descriptivos + banderas de ausencia
# ---------------------------------------------------------------------------


def _n_ultimos_anios(anios_disponibles: set[int], anio_max_fuente: int, ventana: int = 5) -> set[int]:
    return {a for a in anios_disponibles if a > anio_max_fuente - ventana}


def build_territorial_water_indicators(
    df_universo_vigente: pd.DataFrame,
    df_assigned: pd.DataFrame,
    df_audit: pd.DataFrame,
    catalogo: pd.DataFrame,
) -> pd.DataFrame:
    """Sección J: 1.122 filas (todo el universo DIVIPOLA vigente), incluidas
    las unidades sin ningún monitoreo. Son indicadores de DISPONIBILIDAD e
    INTENSIDAD de monitoreo, no de condición ambiental del agua."""
    anio_max_fuente = int(df_assigned["anio"].max())
    anio_min_fuente = int(df_assigned["anio"].min())
    ventana_ultimos_5 = set(range(anio_max_fuente - 4, anio_max_fuente + 1))

    asignados = df_assigned[df_assigned["cod_dane_mpio_asignado"].notna()]
    clasif_por_param = dict(zip(catalogo["propiedad_observada_norm"], catalogo["clasificacion_parametro"]))

    discrepancias_por_mpio = df_audit[df_audit["cod_dane_mpio_asignado"].notna()].groupby("cod_dane_mpio_asignado").apply(
        lambda g: int(((g["coincide_municipio_texto"] == False) | (g["coincide_departamento_texto"] == False)).sum()),  # noqa: E712
        include_groups=False,
    )
    sin_asignacion_total = int((df_assigned["cod_dane_mpio_asignado"].isna()).sum())

    filas = []
    for _, unidad in df_universo_vigente.iterrows():
        cod_mpio = unidad["cod_dane_mpio"]
        grupo = asignados[asignados["cod_dane_mpio_asignado"] == cod_mpio]
        n_obs = len(grupo)
        tiene_monitoreo = n_obs > 0

        if tiene_monitoreo:
            sitios = grupo["sitio_monitoreo_id"].unique()
            n_sitios = len(sitios)
            parametros = grupo["propiedad_observada_norm"].unique()
            n_parametros = len(parametros)
            anios = set(grupo["anio"].unique())
            n_anios = len(anios)
            anio_primera = int(grupo["anio"].min())
            anio_ultima = int(grupo["anio"].max())
            obs_ultimos5 = grupo[grupo["anio"].isin(ventana_ultimos_5)]
            n_obs_5 = len(obs_ultimos5)
            n_sitios_5 = obs_ultimos5["sitio_monitoreo_id"].nunique()

            pct_num = round(grupo["resultado_es_numerico"].sum() / n_obs * 100, 2)
            pct_cens = round((grupo["resultado_es_censurado_inferior"] | grupo["resultado_es_censurado_superior"]).sum() / n_obs * 100, 2)
            pct_con_unidad = round(grupo["unidad_norm"].notna().sum() / n_obs * 100, 2)
            pct_alta_calidad_espacial = round((grupo["calidad_asignacion"] == "alta").sum() / n_obs * 100, 2)
            n_discrepancias = int(discrepancias_por_mpio.get(cod_mpio, 0))

            cats = [clasif_por_param.get(p, "otro_no_clasificado") for p in parametros]
            n_fisicos = cats.count("fisico")
            n_quimicos = cats.count("quimico")
            n_microbiologicos = cats.count("microbiologico")
            n_metales = cats.count("metal_metaloide")
            n_nutrientes = cats.count("nutriente")
            n_organicos = cats.count("hidrocarburo_organico")
            n_agregados = cats.count("indicador_agregado")
            n_no_clasificados = cats.count("otro_no_clasificado")

            obs_por_sitio = round(n_obs / n_sitios, 2) if n_sitios else None
            obs_por_anio = round(n_obs / n_anios, 2) if n_anios else None
            param_por_sitio = round(n_parametros / n_sitios, 2) if n_sitios else None

            sin_monitoreo = False
            monitoreo_escaso = n_obs < UMBRAL_MONITOREO_ESCASO_N_OBS
            monitoreo_desactualizado = len(anios & ventana_ultimos_5) == 0
            cobertura_temporal_limitada = n_anios < UMBRAL_COBERTURA_TEMPORAL_LIMITADA_ANIOS
        else:
            n_sitios = n_parametros = n_anios = 0
            anio_primera = anio_ultima = None
            n_obs_5 = n_sitios_5 = 0
            pct_num = pct_cens = pct_con_unidad = pct_alta_calidad_espacial = None
            n_discrepancias = 0
            n_fisicos = n_quimicos = n_microbiologicos = n_metales = n_nutrientes = n_organicos = n_agregados = n_no_clasificados = 0
            obs_por_sitio = obs_por_anio = param_por_sitio = None
            sin_monitoreo = True
            monitoreo_escaso = True
            monitoreo_desactualizado = True
            cobertura_temporal_limitada = True

        filas.append(
            {
                "cod_dane_mpio": cod_mpio,
                "cod_dane_dpto": unidad["cod_dane_dpto"],
                "nombre_mpio": unidad["nombre_mpio"],
                "nombre_dpto": unidad["nombre_dpto"],
                "tipo_unidad_territorial": unidad["tipo_unidad_territorial"],
                "tiene_monitoreo_agua": tiene_monitoreo,
                "n_sitios_monitoreo": n_sitios,
                "n_observaciones_agua": n_obs,
                "n_parametros_observados": n_parametros,
                "n_anios_monitoreados": n_anios,
                "anio_primera_observacion": anio_primera,
                "anio_ultima_observacion": anio_ultima,
                "n_observaciones_ultimos_5_anios_disponibles": n_obs_5,
                "n_sitios_ultimos_5_anios_disponibles": n_sitios_5,
                "pct_resultados_numericos": pct_num,
                "pct_resultados_censurados": pct_cens,
                "pct_observaciones_con_unidad": pct_con_unidad,
                "pct_observaciones_asignacion_espacial_alta": pct_alta_calidad_espacial,
                "n_discrepancias_municipio_texto_espacial": n_discrepancias,
                "n_observaciones_sin_asignacion": 0,
                "n_parametros_fisicos": n_fisicos,
                "n_parametros_quimicos": n_quimicos,
                "n_parametros_microbiologicos": n_microbiologicos,
                "n_metales_metaloides": n_metales,
                "n_nutrientes": n_nutrientes,
                "n_compuestos_organicos": n_organicos,
                "n_parametros_agregados": n_agregados,
                "n_parametros_no_clasificados": n_no_clasificados,
                "observaciones_por_sitio": obs_por_sitio,
                "observaciones_por_anio_monitoreado": obs_por_anio,
                "parametros_por_sitio": param_por_sitio,
                "sin_monitoreo": sin_monitoreo,
                "monitoreo_escaso": monitoreo_escaso,
                "monitoreo_desactualizado": monitoreo_desactualizado,
                "cobertura_temporal_limitada": cobertura_temporal_limitada,
            }
        )

    df_ind = pd.DataFrame(filas)
    df_ind.attrs["anio_min_fuente"] = anio_min_fuente
    df_ind.attrs["anio_max_fuente"] = anio_max_fuente
    df_ind.attrs["ventana_ultimos_5_anios"] = sorted(ventana_ultimos_5)
    df_ind.attrs["n_observaciones_sin_asignacion_total"] = sin_asignacion_total
    return df_ind
