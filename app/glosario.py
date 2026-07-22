"""Glosario en lenguaje sencillo para tooltips (hover) en la app.

Cada dato del tablero se explica al pasar el cursor: st.metric(help=...) y
st.dataframe(column_config={col: st.column_config.Column(help=...)}).
"""
import streamlit as st

G = {
    "score": ("Puntaje de priorización de 0 a 1. Combina minería, deforestación, fuego satelital, "
              "agua y sensibilidad del territorio. Mayor puntaje = revisar primero. No mide daño probado."),
    "nivel": ("Nivel de prioridad según el puntaje: Bajo, Medio, Alto o Crítico. Orienta la revisión; "
              "no prueba causalidad ni ilegalidad."),
    "critico": ("Municipios en el 5% más alto de prioridad. Señala dónde mirar primero, no que exista un delito."),
    "alto": "Municipios en el siguiente tramo de mayor prioridad (después de Crítico).",
    "prediccion": "Nivel que asigna el modelo de IA. Puede coincidir o no con el puntaje técnico.",
    "confianza": "Qué tan seguro está el modelo de esa clasificación (de 0 a 100%).",
    "idx_minero": "Presión minera formal: títulos y volumen de explotación, en escala de 0 a 1.",
    "idx_deforestacion": "Deforestación registrada en el municipio, en escala de 0 a 1.",
    "idx_fuego": ("Señal de satélite: focos de calor activos (proxy de quema y deforestación reciente), 0 a 1."),
    "idx_hidrico": "Afectación del agua donde hay estación de medición (1 menos el índice de calidad ICA), 0 a 1.",
    "idx_sensibilidad": "Valor ambiental del territorio: áreas protegidas y municipios PDET, en escala de 0 a 1.",
    "focos": "Focos de calor activos detectados por satélite (NASA FIRMS) en los últimos 7 días.",
    "frp": "Intensidad del fuego: potencia radiativa acumulada de los focos (a mayor valor, quema más fuerte).",
    "prioridad_max": "Municipios que el modelo prioriza (Alto/Crítico) y que además tienen fuego activo hoy.",
    "actividad_nueva": ("Fuego intenso en municipios que el índice histórico no marcaba: lo que el dato viejo no veía."),
    "accuracy": ("Aciertos del modelo en la prueba. Es alto por construcción (la etiqueta es una fórmula); "
                 "el valor real de la herramienta es priorizar y explicar, no el porcentaje."),
    "baseline": "Qué acertaría un modelo trivial que siempre dice la clase más común. Sirve para comparar con honestidad.",
    "f1": "Medida de calidad que equilibra los aciertos entre las 4 clases (0 a 1).",
    "municipios_vista": "Cantidad de municipios que se están mostrando con los filtros actuales.",
    "municipios_fuego": "Municipios del país con al menos un foco de calor activo en los últimos 7 días.",
}


def cc(mapping: dict):
    """Construye column_config con tooltips. mapping: {nombre_columna: clave_glosario}."""
    return {col: st.column_config.Column(help=G[k]) for col, k in mapping.items()}
