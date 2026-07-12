"""Auditoría metodológica de sitios, parámetros censurados y cobertura
hídrica (Fase 4B.1).

No recalcula la asignación espacial de la Fase 4B ni construye indicadores
de contaminación o riesgo. Solo audita, clasifica y documenta la calidad
metodológica de lo que la Fase 4B ya produjo.
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd
from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry

from ..geo.intersection import reproject_geometry

M2_PER_KM = 1000.0

UMBRAL_COORD_CERCANAS_M = 100.0
UMBRAL_CENSURA_NIVEL_B = 80.0
UMBRAL_CENSURA_PRECAUCION_PCT = 20.0
UMBRAL_CENSURA_NO_RECOMENDADA_PCT = 80.0
UMBRAL_DIST_CERCA_LIMITE_KM = 2.0
UMBRAL_DIST_ERROR_COORDENADA_KM = 50.0

# Fase 4B.2 - auditoría independiente de códigos originales (sección A)
_CODIGO_PUNTO_RE = re.compile(r"\[([^\]]+)\]\s*$")

CAMPO_ORIGEN_ESTACION_PUNTO = "codigo_estacion_punto_extraido"
CAMPO_ORIGEN_MUESTRA = "codigo_muestra"
CAMPO_ORIGEN_PROYECTO = "proyecto"
CAMPO_ORIGEN_NOMBRE = "nombre_punto_texto_completo"
CAMPO_ORIGEN_NINGUNO = "sin_codigo_original"

UMBRAL_N_OBS_MIN_EVALUABLE = 3

# Parámetros candidatos a Nivel B por diseño (censura estructuralmente alta
# en química analítica de trazas): se confirma con datos reales, no se
# asume — ver classify_parameter_suitability_v2.
CANDIDATOS_NIVEL_B_INICIAL = {"PLOMO TOTAL EN AGUA", "CADMIO TOTAL EN AGUA"}


# ---------------------------------------------------------------------------
# A. Auditoría de identificación de sitios
# ---------------------------------------------------------------------------


def audit_monitoring_sites(df_assigned: pd.DataFrame, transformer) -> pd.DataFrame:
    """Sección A: una fila por `sitio_monitoreo_id` (243), con las
    estadísticas y clasificación pedidas. No fusiona ni divide sitios."""
    filas = []
    for sitio, grupo in df_assigned.groupby("sitio_monitoreo_id"):
        coords = grupo[["latitud", "longitud"]].drop_duplicates()
        n_coords = len(coords)

        dist_max_m = 0.0
        if n_coords > 1:
            pts_proj = [reproject_geometry(Point(lon, lat), transformer) for lat, lon in coords.itertuples(index=False)]
            for i in range(len(pts_proj)):
                for j in range(i + 1, len(pts_proj)):
                    dist_max_m = max(dist_max_m, pts_proj[i].distance(pts_proj[j]))

        n_municipios = grupo["cod_dane_mpio_asignado"].nunique()
        n_departamentos = grupo["cod_dane_dpto_asignado"].nunique()
        n_obs = len(grupo)
        metodo = grupo["metodo_sitio_id"].iloc[0]

        clasif = "sitio_estable"
        razon = "coordenada única, unidad territorial única, código de identificación consistente"
        if n_coords > 1 and dist_max_m <= UMBRAL_COORD_CERCANAS_M:
            clasif = "multiples_coordenadas_cercanas"
            razon = f"{n_coords} coordenadas distintas, distancia máxima {dist_max_m:.1f} m (<= {UMBRAL_COORD_CERCANAS_M} m)"
        elif n_coords > 1 and dist_max_m > UMBRAL_COORD_CERCANAS_M:
            clasif = "multiples_coordenadas_distantes"
            razon = f"{n_coords} coordenadas distintas, distancia máxima {dist_max_m:.1f} m (> {UMBRAL_COORD_CERCANAS_M} m)"
        elif n_municipios > 1:
            clasif = "multiples_unidades_territoriales"
            razon = f"{n_municipios} municipios espaciales distintos asociados al mismo sitio_monitoreo_id"
        elif n_obs < 3:
            clasif = "requiere_revision_manual"
            razon = f"solo {n_obs} observación(es): evidencia insuficiente para confirmar estabilidad"

        filas.append(
            {
                "sitio_monitoreo_id": sitio,
                "metodo_identificacion": metodo,
                "n_observaciones": n_obs,
                "n_coordenadas_distintas": n_coords,
                "distancia_maxima_entre_coordenadas_m": round(dist_max_m, 2),
                "n_municipios_espaciales": n_municipios,
                "n_departamentos_espaciales": n_departamentos,
                "n_proyectos_asociados": grupo["proyecto"].nunique(),
                "proyectos_asociados": "; ".join(sorted(grupo["proyecto"].dropna().unique().astype(str))),
                "n_codigos_muestra_asociados": grupo["codigo_muestra"].nunique(),
                "primera_fecha": grupo["fecha"].min(),
                "ultima_fecha": grupo["fecha"].max(),
                "n_parametros_observados": grupo["propiedad_observada_norm"].nunique(),
                "clasificacion": clasif,
                "razon": razon,
            }
        )
    df_out = pd.DataFrame(filas).sort_values("sitio_monitoreo_id").reset_index(drop=True)
    return df_out


def propose_composite_key_for_reused_codes(df_sitios_audit: pd.DataFrame) -> list[dict[str, Any]]:
    """Sección A: si un mismo código quedó asociado a coordenadas distantes,
    documenta el caso y propone `codigo_origen + coordenadas_redondeadas`
    como llave compuesta alternativa — sin modificar la salida canónica de
    la Fase 4B. Devuelve una lista vacía si no se encontró ningún caso real
    (no se inventa un problema que los datos no muestran)."""
    problematicos = df_sitios_audit[df_sitios_audit["clasificacion"] == "multiples_coordenadas_distantes"]
    propuestas = []
    for _, row in problematicos.iterrows():
        propuestas.append(
            {
                "sitio_monitoreo_id": row["sitio_monitoreo_id"],
                "problema": f"código reutilizado en coordenadas distantes ({row['distancia_maxima_entre_coordenadas_m']:.1f} m)",
                "llave_propuesta": f"{row['sitio_monitoreo_id']}__lat_lon_redondeados",
                "aplicada": False,
            }
        )
    return propuestas


# ---------------------------------------------------------------------------
# A (Fase 4B.2). Validación independiente de códigos originales, SIN agregar
# coordenadas a la llave de agrupación (a diferencia de sitio_monitoreo_id,
# que para los 49 sitios sin código incorpora coordenadas por construcción).
# ---------------------------------------------------------------------------


def build_source_code_column(df: pd.DataFrame) -> pd.DataFrame:
    """Sección A: construye `codigo_sitio_origen` con prioridad documentada,
    exactamente en el orden pedido por el encargo (estación/punto > muestra >
    proyecto > nombre completo del punto), sin usar latitud/longitud en
    ningún momento. `campo_origen_codigo` documenta de qué columna original
    provino cada valor. Los valores de respaldo (codigo_muestra, proyecto)
    se prefijan con el nombre del campo para que nunca colisionen por
    coincidencia textual con un código de estación real."""
    out = df.copy()
    codigo_punto = out["nombre_del_punto_de_monitoreo"].str.extract(_CODIGO_PUNTO_RE)[0]

    codigo_sitio_origen = codigo_punto.copy()
    campo_origen = pd.Series(np.where(codigo_punto.notna(), CAMPO_ORIGEN_ESTACION_PUNTO, None), index=out.index, dtype=object)

    falta = codigo_sitio_origen.isna()
    usa_muestra = falta & out["codigo_muestra"].notna()
    codigo_sitio_origen = codigo_sitio_origen.where(~usa_muestra, "muestra::" + out["codigo_muestra"].astype(str))
    campo_origen = campo_origen.where(~usa_muestra, CAMPO_ORIGEN_MUESTRA)

    falta = codigo_sitio_origen.isna()
    usa_proyecto = falta & out["proyecto"].notna()
    codigo_sitio_origen = codigo_sitio_origen.where(~usa_proyecto, "proyecto::" + out["proyecto"].astype(str))
    campo_origen = campo_origen.where(~usa_proyecto, CAMPO_ORIGEN_PROYECTO)

    falta = codigo_sitio_origen.isna()
    usa_nombre = falta & out["nombre_del_punto_de_monitoreo"].notna()
    codigo_sitio_origen = codigo_sitio_origen.where(~usa_nombre, "nombre::" + out["nombre_del_punto_de_monitoreo"].astype(str))
    campo_origen = campo_origen.where(~usa_nombre, CAMPO_ORIGEN_NOMBRE)

    campo_origen = campo_origen.fillna(CAMPO_ORIGEN_NINGUNO)

    out["codigo_sitio_origen"] = codigo_sitio_origen
    out["campo_origen_codigo"] = campo_origen
    return out


def audit_source_codes(df_with_code: pd.DataFrame, transformer) -> pd.DataFrame:
    """Sección A: agrupa SOLO por `codigo_sitio_origen` (nunca por
    sitio_monitoreo_id) y calcula evidencia real de estabilidad espacial.
    Cuando el código proviene de un campo ya sabido inestable (codigo_muestra
    o proyecto, evaluados y descartados como identificador de sitio en la
    Fase 4B.1), la clasificación lo etiqueta como tal en vez de forzarlo a
    'reutilizado en ubicaciones distantes' — no es un error de dato, es un
    campo de otra granularidad usado solo como último respaldo."""
    con_codigo = df_with_code[df_with_code["codigo_sitio_origen"].notna()]
    filas = []
    for codigo, grupo in con_codigo.groupby("codigo_sitio_origen"):
        coords = grupo[["latitud", "longitud"]].drop_duplicates()
        n_coords = len(coords)
        dist_max_m = 0.0
        if n_coords > 1:
            pts_proj = [reproject_geometry(Point(lon, lat), transformer) for lat, lon in coords.itertuples(index=False)]
            for i in range(len(pts_proj)):
                for j in range(i + 1, len(pts_proj)):
                    dist_max_m = max(dist_max_m, pts_proj[i].distance(pts_proj[j]))

        n_obs = len(grupo)
        n_sitio_ids = grupo["sitio_monitoreo_id"].nunique()
        n_mpios = grupo["cod_dane_mpio_asignado"].nunique()
        n_dptos = grupo["cod_dane_dpto_asignado"].nunique()
        campo_origen = grupo["campo_origen_codigo"].iloc[0]
        nombres_asociados = "; ".join(sorted(grupo["nombre_del_punto_de_monitoreo"].dropna().unique().astype(str)))
        proyectos_asociados = "; ".join(sorted(grupo["proyecto"].dropna().unique().astype(str)))

        if campo_origen == CAMPO_ORIGEN_MUESTRA:
            clasif = "posible_codigo_de_muestra"
            razon = (
                f"codigo_sitio_origen derivado de codigo_muestra (respaldo, no código de estación real): "
                f"{n_sitio_ids} sitio(s) de monitoreo, {n_mpios} municipio(s) espaciales bajo este código."
            )
        elif campo_origen == CAMPO_ORIGEN_PROYECTO:
            clasif = "posible_codigo_de_proyecto"
            razon = (
                f"codigo_sitio_origen derivado de proyecto (respaldo, no código de estación real): "
                f"{n_sitio_ids} sitio(s) de monitoreo, {n_mpios} municipio(s) espaciales bajo este código."
            )
        elif n_obs < UMBRAL_N_OBS_MIN_EVALUABLE:
            clasif = "requiere_revision_manual"
            razon = f"solo {n_obs} observación(es) bajo este código: evidencia insuficiente para clasificar estabilidad."
        elif n_coords == 1:
            clasif = "codigo_ubicacion_estable"
            razon = "una única coordenada asociada a este código de estación/punto, evaluada de forma independiente de sitio_monitoreo_id."
        elif dist_max_m <= UMBRAL_COORD_CERCANAS_M:
            clasif = "codigo_con_variacion_menor_100m"
            razon = f"{n_coords} coordenadas distintas, distancia máxima {dist_max_m:.1f} m (<= {UMBRAL_COORD_CERCANAS_M:.0f} m)."
        else:
            clasif = "codigo_reutilizado_en_ubicaciones_distantes"
            razon = f"{n_coords} coordenadas distintas, distancia máxima {dist_max_m:.1f} m (> {UMBRAL_COORD_CERCANAS_M:.0f} m)."

        filas.append(
            {
                "codigo_sitio_origen": codigo,
                "campo_origen_codigo": campo_origen,
                "n_observaciones": n_obs,
                "n_coordenadas_distintas": n_coords,
                "n_sitio_monitoreo_id": n_sitio_ids,
                "n_municipios_espaciales": n_mpios,
                "n_departamentos_espaciales": n_dptos,
                "distancia_maxima_entre_coordenadas_m": round(dist_max_m, 2),
                "primera_fecha": grupo["fecha"].min(),
                "ultima_fecha": grupo["fecha"].max(),
                "nombres_asociados": nombres_asociados,
                "proyectos_asociados": proyectos_asociados,
                "clasificacion": clasif,
                "razon": razon,
            }
        )
    return pd.DataFrame(filas).sort_values("codigo_sitio_origen").reset_index(drop=True)


def summarize_sites_without_original_code(df_with_code: pd.DataFrame) -> dict[str, Any]:
    """Sección A: reporta por separado los sitios construidos únicamente
    mediante hash (sin código de estación/punto real disponible en
    `nombre_del_punto_de_monitoreo`) — aunque `codigo_sitio_origen` haya
    podido resolverse con un campo de respaldo (codigo_muestra/proyecto),
    estos sitios siguen sin tener un código de estación/punto propio."""
    sin_codigo_estacion = df_with_code[df_with_code["campo_origen_codigo"] != CAMPO_ORIGEN_ESTACION_PUNTO]
    sitios = sorted(sin_codigo_estacion["sitio_monitoreo_id"].unique().tolist())
    campos_respaldo_usados = sin_codigo_estacion.groupby("sitio_monitoreo_id")["campo_origen_codigo"].agg(lambda s: sorted(s.unique().tolist())).to_dict()
    return {
        "n_sitios_sin_codigo_estacion_punto": len(sitios),
        "sitios_sin_codigo_estacion_punto": sitios,
        "campos_respaldo_por_sitio": {k: v for k, v in campos_respaldo_usados.items()},
    }


# ---------------------------------------------------------------------------
# B. Diccionario de normalización de parámetros
# ---------------------------------------------------------------------------

# Casos de fusión técnicamente dudosa encontrados en los datos reales de la
# Fase 4B (no se listan por adivinanza: se derivan programáticamente en
# build_parameter_normalization_dictionary comparando propiedad_observada
# original vs. propiedad_observada_norm).
_PALABRAS_ISOMERO_ESPECIE = ("α", "β", "γ", "ɣ", "δ", "P P", "TRANS", "ISOMERO")


def build_parameter_normalization_dictionary(df_assigned: pd.DataFrame) -> pd.DataFrame:
    """Sección B: explica exactamente qué propiedades originales terminaron
    en qué parámetro normalizado, y marca las fusiones técnicamente dudosas
    (nunca fusiones por tilde/abreviatura/signo/número/fracción/método
    analítico/estado disuelto-total/especie química sin documentarlo)."""
    combos = df_assigned.groupby(["propiedad_observada", "propiedad_observada_norm", "unidad_del_resultado", "unidad_norm"]).size().reset_index(name="n_observaciones")

    conteo_por_norm = combos.groupby("propiedad_observada_norm")["propiedad_observada"].nunique()

    filas = []
    for _, row in combos.iterrows():
        orig, norm = row["propiedad_observada"], row["propiedad_observada_norm"]
        n_originales_en_grupo = conteo_por_norm[norm]
        fue_fusionado = n_originales_en_grupo > 1

        requiere_revision = False
        observ = ""
        if fue_fusionado:
            contiene_marcador_especie = any(marcador in orig.upper() for marcador in _PALABRAS_ISOMERO_ESPECIE)
            otros_originales = combos[(combos["propiedad_observada_norm"] == norm) & (combos["propiedad_observada"] != orig)]["propiedad_observada"].unique()
            unidades_del_grupo = combos[combos["propiedad_observada_norm"] == norm]["unidad_norm"].nunique()
            if contiene_marcador_especie or unidades_del_grupo > 1:
                requiere_revision = True
                observ = (
                    f"Fusión técnicamente dudosa: '{orig}' se normalizó junto con {list(otros_originales)} bajo "
                    f"'{norm}'. La normalización de texto (Fase 3B) elimina prefijos de letra griega/isómero "
                    "(p. ej. α/β/γ/δ), colapsando nombres que en química analítica corresponden a especies "
                    "distintas (isómeros con distinto CAS y comportamiento ambiental). "
                    f"{'Las unidades SÍ difieren entre los originales fusionados (' + str(unidades_del_grupo) + ' unidades distintas), así que el catálogo de la Fase 4B (agrupado por propiedad+unidad) NO mezcló valores numéricos entre ellos.' if unidades_del_grupo > 1 else 'Las unidades no difieren, revisar manualmente si la fusión es válida.'} "
                    "Recomendación: mantener separados por `unidad_norm` en cualquier regeneración; nunca "
                    "agregar por `propiedad_observada_norm` sola para este grupo."
                )
            else:
                observ = f"Fusión con {list(otros_originales)}: no se detectó marcador de isómero/especie distinta; revisar si corresponde solo a variación de mayúsculas/tildes/espacios."
        else:
            observ = "Sin fusión: un único nombre original mapea a este parámetro normalizado."

        regla = "normalize_text: mayúsculas, sin tildes, sin signos no alfanuméricos, espacios colapsados (Fase 3B)"

        filas.append(
            {
                "propiedad_observada_original": orig,
                "propiedad_observada_norm": norm,
                "unidad_original": row["unidad_del_resultado"],
                "unidad_norm": row["unidad_norm"],
                "regla_normalizacion": regla,
                "grupo_normalizado": norm,
                "fue_fusionado_con_otro_nombre": fue_fusionado,
                "n_observaciones": row["n_observaciones"],
                "requiere_revision_tecnica": requiere_revision,
                "observaciones": observ,
            }
        )
    return pd.DataFrame(filas).sort_values(["fue_fusionado_con_otro_nombre", "propiedad_observada_norm"], ascending=[False, True]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# C. Clasificación de idoneidad de parámetros (niveles A/B/C/D)
# ---------------------------------------------------------------------------


def classify_parameter_suitability_v2(catalogo: pd.DataFrame, df_assigned: pd.DataFrame) -> pd.DataFrame:
    """Sección C: reemplaza la clasificación binaria aprobado/no aprobado de
    la Fase 4B por 4 niveles (A/B/C/D), documentados y basados en datos
    reales de cobertura, censura y homogeneidad de unidad."""
    filas = []
    for _, cat_row in catalogo.iterrows():
        prop, unidad = cat_row["propiedad_observada_norm"], cat_row["unidad_norm"]
        obs = df_assigned[
            (df_assigned["propiedad_observada_norm"] == prop)
            & (df_assigned["unidad_norm"] == unidad)
            & (df_assigned["cod_dane_mpio_asignado"].notna())
        ]
        n_obs = len(obs)
        n_mpios = obs["cod_dane_mpio_asignado"].nunique()
        n_anios = obs["anio"].nunique()
        n_num = int(obs["resultado_es_numerico"].sum())
        n_cens = int((obs["resultado_es_censurado_inferior"] | obs["resultado_es_censurado_superior"]).sum())
        pct_num = round(n_num / n_obs * 100, 2) if n_obs else 0.0
        pct_cens = round(n_cens / n_obs * 100, 2) if n_obs else 0.0
        n_ld_distintos = obs.loc[obs["resultado_es_censurado_inferior"], "limite_deteccion"].nunique()

        unidades_del_parametro = catalogo[catalogo["propiedad_observada_norm"] == prop]["unidad_norm"].nunique()
        unidad_homogenea = unidades_del_parametro == 1

        if n_obs == 0:
            nivel, permite_num, permite_det, permite_tend, razon = (
                "D", False, False, False, "0 observaciones asignadas espacialmente (ausente de la fuente o sin correspondencia territorial)",
            )
        elif pct_cens >= UMBRAL_CENSURA_NIVEL_B:
            nivel, permite_num, permite_det, permite_tend = "B", False, True, False
            razon = (
                f"{pct_cens:.1f}% censurado (>= {UMBRAL_CENSURA_NIVEL_B}%): dominado por el límite de "
                "detección. Permite indicadores de detección/censura (pct_detectados, n_detecciones, "
                "límite de detección más frecuente); NO permite promedio/mediana municipal ni tendencia "
                "numérica predeterminada ni ranking territorial por concentración."
            )
        elif not unidad_homogenea or n_obs < 500 or n_mpios < 20:
            nivel, permite_num, permite_det, permite_tend = "C", False, False, False
            razones = []
            if not unidad_homogenea:
                razones.append(f"{unidades_del_parametro} unidades distintas para este parámetro")
            if n_obs < 500:
                razones.append(f"{n_obs} observaciones (< 500)")
            if n_mpios < 20:
                razones.append(f"{n_mpios} municipios (< 20)")
            razon = "cobertura insuficiente o unidades heterogéneas: " + "; ".join(razones)
        else:
            nivel, permite_num, permite_det, permite_tend = "A", True, False, True
            razon = "unidad homogénea, cobertura suficiente, censura razonable, resultados cuantificados suficientes"

        filas.append(
            {
                "propiedad_observada_norm": prop,
                "unidad_norm": unidad,
                "n_observaciones": n_obs,
                "n_municipios": n_mpios,
                "n_anios": n_anios,
                "pct_numerico": pct_num,
                "pct_censurado": pct_cens,
                "n_limites_deteccion_distintos": int(n_ld_distintos),
                "nivel_idoneidad": nivel,
                "permite_indicador_numerico": permite_num,
                "permite_indicador_deteccion": permite_det,
                "permite_tendencia": permite_tend,
                "razon": razon,
                "requiere_revision_tecnica": bool(prop in CANDIDATOS_NIVEL_B_INICIAL and nivel != "B" and pct_cens > 50),
            }
        )
    return pd.DataFrame(filas).sort_values(["nivel_idoneidad", "n_observaciones"], ascending=[True, False]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# F (Fase 4B.2). Candidatos ausentes de la fuente.
#
# `classify_parameter_suitability_v2` clasifica por COMBINACIÓN
# propiedad_observada_norm + unidad_norm observada en el catálogo (nunca
# solo por parámetro): su Nivel D ("0 observaciones asignadas
# espacialmente") solo puede aplicar a una combinación que SÍ aparece en el
# catálogo pero perdió la asignación espacial — nunca a un parámetro que no
# aparece en la fuente en absoluto. Esta función cubre ese segundo caso por
# separado, para no mezclar "ausente de la fuente" con "presente pero sin
# asignar" bajo la misma etiqueta.
# ---------------------------------------------------------------------------


def build_absent_parameter_candidates(df_assigned: pd.DataFrame, candidatos: list[str]) -> pd.DataFrame:
    """Sección F: evalúa cada candidato de la lista `candidatos` (nombres ya
    normalizados) contra el dataset completo (no solo el catálogo) y
    confirma con datos reales cuáles están totalmente ausentes de la
    fuente."""
    filas = []
    for nombre in candidatos:
        n_obs = int((df_assigned["propiedad_observada_norm"] == nombre).sum())
        ausente = n_obs == 0
        filas.append(
            {
                "nombre_candidato_evaluado": nombre,
                "presente_en_fuente": not ausente,
                "n_observaciones_en_fuente": n_obs,
                "confirmado_ausente": ausente,
                "observaciones": (
                    "Ausente de la fuente de datos en su totalidad (0 observaciones en todo el dataset). "
                    "No corresponde a 'Nivel D' de clasificacion_idoneidad_parametros_agua.csv — ese nivel se "
                    "reserva a combinaciones que sí aparecen en el catálogo pero sin asignación espacial."
                    if ausente
                    else "Presente en la fuente; ver clasificacion_idoneidad_parametros_agua.csv para su evaluación como indicador."
                ),
            }
        )
    return pd.DataFrame(filas).sort_values(["confirmado_ausente", "nombre_candidato_evaluado"], ascending=[False, True]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# D. Auditoría de límites de detección
# ---------------------------------------------------------------------------


def audit_detection_limits(df_assigned: pd.DataFrame) -> pd.DataFrame:
    """Sección D: para cada parámetro-unidad censurado (inferior), variación
    del límite de detección — en el tiempo y por proyecto/sitio."""
    censurados = df_assigned[df_assigned["resultado_es_censurado_inferior"]]
    filas = []
    for (prop, unidad), grupo in censurados.groupby(["propiedad_observada_norm", "unidad_norm"]):
        limites = grupo["limite_deteccion"]
        n_obs = len(grupo)
        limites_distintos = sorted(limites.dropna().unique())
        moda = limites.mode()
        limite_frecuente = float(moda.iloc[0]) if len(moda) else None
        pct_limite_frecuente = round((limites == limite_frecuente).sum() / n_obs * 100, 2) if limite_frecuente is not None else None

        variacion_por_anio = grupo.groupby("anio")["limite_deteccion"].nunique()
        n_anios_con_variacion = int((variacion_por_anio > 1).sum())
        variacion_entre_anios = grupo.groupby("anio")["limite_deteccion"].apply(lambda s: s.mode().iloc[0] if len(s.mode()) else np.nan)
        limite_cambia_entre_anios = variacion_entre_anios.nunique(dropna=True) > 1

        variacion_por_sitio = grupo.groupby("sitio_monitoreo_id")["limite_deteccion"].nunique()
        n_sitios_con_variacion = int((variacion_por_sitio > 1).sum())
        variacion_por_proyecto = grupo.groupby("proyecto")["limite_deteccion"].nunique()
        n_proyectos_con_variacion = int((variacion_por_proyecto > 1).sum())

        alta_variabilidad = len(limites_distintos) >= 4 or limite_cambia_entre_anios

        filas.append(
            {
                "propiedad_observada_norm": prop,
                "unidad_norm": unidad,
                "n_observaciones_censuradas": n_obs,
                "n_limites_deteccion_distintos": len(limites_distintos),
                "limite_minimo": min(limites_distintos) if limites_distintos else None,
                "limite_maximo": max(limites_distintos) if limites_distintos else None,
                "limite_mas_frecuente": limite_frecuente,
                "pct_registros_limite_mas_frecuente": pct_limite_frecuente,
                "limite_cambia_entre_anios": bool(limite_cambia_entre_anios),
                "n_anios_con_mas_de_un_limite": n_anios_con_variacion,
                "n_sitios_con_mas_de_un_limite": n_sitios_con_variacion,
                "n_proyectos_con_mas_de_un_limite": n_proyectos_con_variacion,
                "alta_variabilidad": alta_variabilidad,
                "observaciones": (
                    "Alta variabilidad del límite de detección: puede impedir comparaciones simples entre "
                    "años o sitios (un resultado '<X' en un año no es comparable a '<Y' en otro si X≠Y)."
                    if alta_variabilidad
                    else "Variabilidad baja o nula del límite de detección para esta combinación."
                ),
            }
        )
    return pd.DataFrame(filas).sort_values("n_observaciones_censuradas", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# E. Revisión de tendencias
# ---------------------------------------------------------------------------


def audit_trends(df_tendencias: pd.DataFrame, df_assigned: pd.DataFrame) -> pd.DataFrame:
    """Sección E: audita las combinaciones con `tendencia_calculable=True`.
    Confirma que la pendiente se calculó solo con numéricos (por
    construcción de `build_trends_table`, Fase 4B) y marca precaución/no
    recomendada según % de censura del universo completo (numérico +
    censurado) de esa combinación unidad+parámetro+unidad."""
    calculables = df_tendencias[df_tendencias["tendencia_calculable"]].copy()
    asignados = df_assigned[df_assigned["cod_dane_mpio_asignado"].notna()]

    filas = []
    for _, row in calculables.iterrows():
        cod_mpio, prop, unidad = row["cod_dane_mpio"], row["propiedad_observada_norm"], row["unidad_norm"]
        universo = asignados[
            (asignados["cod_dane_mpio_asignado"] == cod_mpio)
            & (asignados["propiedad_observada_norm"] == prop)
            & (asignados["unidad_norm"] == unidad)
        ]
        n_total = len(universo)
        n_num = int(universo["resultado_es_numerico"].sum())
        n_cens = int((universo["resultado_es_censurado_inferior"] | universo["resultado_es_censurado_superior"]).sum())
        pct_cens = round(n_cens / n_total * 100, 2) if n_total else 0.0

        calculo_solo_numericos = n_num == row["n_observaciones"]

        if not calculo_solo_numericos:
            valida = False
            razon = "INCONSISTENCIA: la pendiente reportada no coincide con el conteo de resultados numéricos recalculado — requiere revisión del pipeline."
        elif pct_cens > UMBRAL_CENSURA_NO_RECOMENDADA_PCT:
            valida = True
            razon = f"no_recomendada_para_interpretacion_numerica: {pct_cens:.1f}% de las observaciones totales de esta combinación están censuradas"
        elif pct_cens > UMBRAL_CENSURA_PRECAUCION_PCT:
            valida = True
            razon = f"requiere_precaucion_por_censura: {pct_cens:.1f}% de las observaciones totales de esta combinación están censuradas"
        else:
            valida = True
            razon = f"censura baja ({pct_cens:.1f}%); pendiente calculada solo con resultados numéricos observados"

        filas.append(
            {
                "cod_dane_mpio": cod_mpio,
                "propiedad_observada_norm": prop,
                "unidad_norm": unidad,
                "n_observaciones_totales": n_total,
                "n_resultados_numericos": n_num,
                "n_resultados_censurados": n_cens,
                "pct_censurado": pct_cens,
                "anio_inicio": row["anio_inicio"],
                "anio_fin": row["anio_fin"],
                "pendiente_anual": row["pendiente_anual"],
                "tendencia_valida_metodologicamente": valida,
                "requiere_precaucion_por_censura": bool(20 < pct_cens <= 80),
                "no_recomendada_para_interpretacion_numerica": bool(pct_cens > 80),
                "razon_invalidez": "" if calculo_solo_numericos else razon,
                "observaciones": razon,
            }
        )
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# E (Fase 4B.2). Reevaluación metodológica de tendencias: separa
# reproducibilidad matemática (¿la pendiente se calculó bien?) de idoneidad
# interpretativa (¿es razonable leerla como una tendencia real?) e incorpora
# la variabilidad del límite de detección de la sección D como un motivo de
# precaución adicional, independiente de la censura.
# ---------------------------------------------------------------------------

UMBRAL_LIMITES_DISTINTOS_ALTA_VARIABILIDAD = 4


def _detection_limit_stats_for_group(grupo: pd.DataFrame) -> dict[str, Any]:
    censurados = grupo[grupo["resultado_es_censurado_inferior"]]
    if censurados.empty:
        return {
            "n_limites_deteccion_distintos": 0,
            "limite_deteccion_min": None,
            "limite_deteccion_max": None,
            "variacion_limite_deteccion": False,
            "advertencia_limite_variable": False,
        }
    limites = censurados["limite_deteccion"].dropna()
    limites_distintos = sorted(limites.unique())
    variacion_por_anio = censurados.groupby("anio")["limite_deteccion"].apply(lambda s: s.mode().iloc[0] if len(s.mode()) else np.nan)
    limite_cambia_entre_anios = variacion_por_anio.nunique(dropna=True) > 1
    alta_variabilidad = len(limites_distintos) >= UMBRAL_LIMITES_DISTINTOS_ALTA_VARIABILIDAD or limite_cambia_entre_anios
    return {
        "n_limites_deteccion_distintos": len(limites_distintos),
        "limite_deteccion_min": min(limites_distintos) if limites_distintos else None,
        "limite_deteccion_max": max(limites_distintos) if limites_distintos else None,
        "variacion_limite_deteccion": bool(limite_cambia_entre_anios),
        "advertencia_limite_variable": bool(alta_variabilidad),
    }


def audit_trends_v2(df_tendencias: pd.DataFrame, df_assigned: pd.DataFrame) -> pd.DataFrame:
    """Sección E (Fase 4B.2): reemplaza el único booleano
    `tendencia_valida_metodologicamente` de la Fase 4B.1 por cinco señales
    explícitas y no excluyentes entre sí, porque una pendiente puede estar
    matemáticamente bien calculada y, al mismo tiempo, no ser recomendable
    para interpretación:

    - `pendiente_reproducida_correctamente`: el recálculo independiente
      coincide con lo reportado por `build_trends_table` (Fase 4B).
    - `apta_para_interpretacion_descriptiva`: reproducida correctamente,
      censura baja (<=20%) y sin advertencia de límite de detección variable.
    - `requiere_precaucion_por_censura`: 20-80% de censura en el universo
      completo de esa combinación.
    - `requiere_precaucion_por_limite_deteccion_variable`: el límite de
      detección de esta combinación municipio+parámetro+unidad varió de
      forma relevante durante el periodo de la tendencia (>=4 límites
      distintos o el límite modal cambia de un año a otro).
    - `no_recomendada_para_interpretacion_numerica`: >80% de censura."""
    calculables = df_tendencias[df_tendencias["tendencia_calculable"]].copy()
    asignados = df_assigned[df_assigned["cod_dane_mpio_asignado"].notna()]

    filas = []
    for _, row in calculables.iterrows():
        cod_mpio, prop, unidad = row["cod_dane_mpio"], row["propiedad_observada_norm"], row["unidad_norm"]
        universo = asignados[
            (asignados["cod_dane_mpio_asignado"] == cod_mpio)
            & (asignados["propiedad_observada_norm"] == prop)
            & (asignados["unidad_norm"] == unidad)
        ]
        n_total = len(universo)
        n_num = int(universo["resultado_es_numerico"].sum())
        n_cens = int((universo["resultado_es_censurado_inferior"] | universo["resultado_es_censurado_superior"]).sum())
        pct_cens = round(n_cens / n_total * 100, 2) if n_total else 0.0

        pendiente_reproducida = n_num == row["n_observaciones"]
        limite_stats = _detection_limit_stats_for_group(universo)

        requiere_precaucion_censura = 20 < pct_cens <= 80
        no_recomendada = pct_cens > 80
        requiere_precaucion_limite = limite_stats["advertencia_limite_variable"] and not no_recomendada
        apta_descriptiva = pendiente_reproducida and pct_cens <= 20 and not limite_stats["advertencia_limite_variable"]

        notas = []
        if not pendiente_reproducida:
            notas.append("INCONSISTENCIA: la pendiente reportada no coincide con el conteo de resultados numéricos recalculado.")
        if no_recomendada:
            notas.append(f"no_recomendada_para_interpretacion_numerica: {pct_cens:.1f}% censurado.")
        elif requiere_precaucion_censura:
            notas.append(f"requiere_precaucion_por_censura: {pct_cens:.1f}% censurado.")
        if requiere_precaucion_limite:
            notas.append(
                f"requiere_precaucion_por_limite_deteccion_variable: {limite_stats['n_limites_deteccion_distintos']} límites "
                f"distintos observados ({limite_stats['limite_deteccion_min']}-{limite_stats['limite_deteccion_max']})."
            )
        if apta_descriptiva:
            notas.append("apta_para_interpretacion_descriptiva.")
        if not notas:
            notas.append("sin observaciones adicionales.")

        filas.append(
            {
                "cod_dane_mpio": cod_mpio,
                "propiedad_observada_norm": prop,
                "unidad_norm": unidad,
                "n_observaciones_totales": n_total,
                "n_resultados_numericos": n_num,
                "n_resultados_censurados": n_cens,
                "pct_censurado": pct_cens,
                "anio_inicio": row["anio_inicio"],
                "anio_fin": row["anio_fin"],
                "pendiente_anual": row["pendiente_anual"],
                "n_limites_deteccion_distintos": limite_stats["n_limites_deteccion_distintos"],
                "limite_deteccion_min": limite_stats["limite_deteccion_min"],
                "limite_deteccion_max": limite_stats["limite_deteccion_max"],
                "variacion_limite_deteccion": limite_stats["variacion_limite_deteccion"],
                "advertencia_limite_variable": limite_stats["advertencia_limite_variable"],
                "pendiente_reproducida_correctamente": bool(pendiente_reproducida),
                "apta_para_interpretacion_descriptiva": bool(apta_descriptiva),
                "requiere_precaucion_por_censura": bool(requiere_precaucion_censura),
                "requiere_precaucion_por_limite_deteccion_variable": bool(requiere_precaucion_limite),
                "no_recomendada_para_interpretacion_numerica": bool(no_recomendada),
                "observaciones": " ".join(notas),
            }
        )
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# G. Discrepancias texto-geometría: causa probable
# ---------------------------------------------------------------------------


def classify_discrepancy_cause(
    df_audit_asignacion: pd.DataFrame,
    df_vigente: pd.DataFrame,
    mgn_geoms_proj_by_cod: dict[str, BaseGeometry],
    transformer,
) -> pd.DataFrame:
    """Sección G: clasifica la causa probable de cada discrepancia
    municipio/departamento textual vs. geometría, con evidencia geométrica
    computada (no adivinada). No sobrescribe la asignación espacial."""
    nombre_to_cod = dict(zip(df_vigente["nombre_mpio_norm"], df_vigente["cod_dane_mpio"]))
    cod_to_nombre = dict(zip(df_vigente["cod_dane_mpio"], df_vigente["nombre_mpio_norm"]))

    filas = []
    for _, row in df_audit_asignacion.iterrows():
        texto = row["municipio_norm"]
        cod_asignado = row["cod_dane_mpio_asignado"]
        nombre_real = cod_to_nombre.get(cod_asignado)

        disc_mpio = row["coincide_municipio_texto"] == False  # noqa: E712
        disc_dpto = row["coincide_departamento_texto"] == False  # noqa: E712

        if not disc_mpio:
            causa = "sin_discrepancia_municipio"
            distancia_km = None
        elif nombre_real and (texto in nombre_real or nombre_real in texto):
            causa = "nombre_historico_o_variante"
            distancia_km = 0.0
        else:
            cod_texto = nombre_to_cod.get(texto)
            if cod_texto is None:
                causa = "requiere_revision_manual"
                distancia_km = None
            elif cod_texto not in mgn_geoms_proj_by_cod or pd.isna(row["latitud"]) or pd.isna(row["longitud"]):
                causa = "requiere_revision_manual"
                distancia_km = None
            else:
                pt_proj = reproject_geometry(Point(row["longitud"], row["latitud"]), transformer)
                distancia_km = pt_proj.distance(mgn_geoms_proj_by_cod[cod_texto]) / M2_PER_KM
                if distancia_km <= UMBRAL_DIST_CERCA_LIMITE_KM:
                    causa = "coordenada_cerca_limite"
                elif distancia_km <= UMBRAL_DIST_ERROR_COORDENADA_KM:
                    causa = "municipio_textual_incorrecto"
                else:
                    causa = "posible_error_coordenada"

        causa_dpto = "departamento_textual_incorrecto" if disc_dpto else ""

        filas.append(
            {
                "sitio_monitoreo_id": row["sitio_monitoreo_id"],
                "n_observaciones_afectadas": None,  # se completa en el script con el conteo real
                "municipio_norm": texto,
                "municipio_espacial": nombre_real,
                "cod_dane_mpio_asignado": cod_asignado,
                "distancia_a_municipio_del_texto_km": round(distancia_km, 3) if distancia_km is not None else None,
                "causa_probable_municipio": causa,
                "causa_probable_departamento": causa_dpto,
                "metodo_asignacion": row["metodo_asignacion"],
            }
        )
    return pd.DataFrame(filas)
