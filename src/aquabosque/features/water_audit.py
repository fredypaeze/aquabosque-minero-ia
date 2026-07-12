"""Auditoría metodológica de sitios, parámetros censurados y cobertura
hídrica (Fase 4B.1).

No recalcula la asignación espacial de la Fase 4B ni construye indicadores
de contaminación o riesgo. Solo audita, clasifica y documenta la calidad
metodológica de lo que la Fase 4B ya produjo.
"""

from __future__ import annotations

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
