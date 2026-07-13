"""Identificación canónica, semántica de duplicados y metodología de
asignación territorial de las Detecciones Tempranas de Deforestación (DTD)
del IDEAM (Fase 2D.3, secciones I/J/K).

`cod_dtd` NO es un identificador único de fila (Fase 2D.2: 32.062 registros,
12,8% del histórico, comparten un `cod_dtd` placeholder dentro de su propio
trimestre). Este módulo define `dtd_registro_id`, un hash determinístico que
no depende de `cod_dtd` en solitario, y clasifica la semántica real de cada
posible duplicado en vez de asumir que compartir `cod_dtd` implica error.
"""

from __future__ import annotations

import hashlib
from typing import Any

import pandas as pd

PRECISION_COORDENADA = 5  # decimales (~1,1 m en el ecuador), mismo criterio que Fase 4B

# Umbral empírico (Fase 2D.2): un `cod_dtd` con más de este número de
# apariciones DENTRO del mismo trimestre se considera un valor placeholder,
# no un identificador individual genuino (los casos reales encontrados van
# de 1.120 a 13.593 apariciones; un duplicado legítimo aislado no debería
# superar unas pocas unidades).
UMBRAL_APARICIONES_PLACEHOLDER = 10


def build_dtd_registro_id(row: dict[str, Any]) -> str:
    """`dtd_registro_id`: hash determinístico SHA-256 (16 hex) de los
    atributos estables de un registro DTD. Deliberadamente NO incluye la
    fecha de descarga (para que el mismo registro produzca siempre el mismo
    id, sin importar cuándo se descargue) y NO usa `cod_dtd` en solitario
    (por la Fase 2D.2: no es único dentro de 5 trimestres)."""
    x = row.get("x")
    y = row.get("y")
    x_norm = round(float(x), PRECISION_COORDENADA) if x is not None else None
    y_norm = round(float(y), PRECISION_COORDENADA) if y is not None else None
    partes = [
        str(row.get("anio")), str(row.get("periodo")), str(x_norm), str(y_norm),
        str(row.get("cod_mpio")), str(row.get("cod_depto")), str(row.get("nucleo_tri")),
        str(row.get("cod_dtd")),
    ]
    payload = "|".join(partes).encode("utf-8")
    return "dtd_" + hashlib.sha256(payload).hexdigest()[:16]


def add_registro_id(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["dtd_registro_id"] = out.apply(lambda r: build_dtd_registro_id(r.to_dict()), axis=1)
    return out


# ---------------------------------------------------------------------------
# J. Semántica de duplicados
# ---------------------------------------------------------------------------


def audit_duplicate_semantics(df: pd.DataFrame) -> pd.DataFrame:
    """Sección J: clasifica cada `cod_dtd` (no cada fila) según su
    comportamiento real. Nunca elimina registros — solo etiqueta."""
    df = df.copy()
    df["coord_redondeada"] = list(zip(df["x"].round(PRECISION_COORDENADA), df["y"].round(PRECISION_COORDENADA)))
    df["fila_hash"] = df.apply(lambda r: build_dtd_registro_id(r.to_dict()), axis=1)

    filas = []
    for cod_dtd, grupo in df.groupby("cod_dtd", dropna=False):
        n_apariciones = len(grupo)
        n_coords = grupo["coord_redondeada"].nunique()
        n_registro_id = grupo["fila_hash"].nunique()

        if n_apariciones == 1:
            clasif = "observacion_legitima_independiente"
            razon = "código aparece exactamente una vez"
        elif n_apariciones > UMBRAL_APARICIONES_PLACEHOLDER and n_coords > 1:
            clasif = "codigo_placeholder_repetido"
            razon = f"{n_apariciones} apariciones con {n_coords} coordenadas distintas — supera el umbral empírico ({UMBRAL_APARICIONES_PLACEHOLDER}) de un identificador genuino"
        elif n_registro_id < n_apariciones and n_coords == 1:
            clasif = "duplicado_exacto_atributos_geometria"
            razon = f"{n_apariciones} filas, misma coordenada y mismos atributos estables (dtd_registro_id repetido)"
        elif n_coords == 1 and n_apariciones > 1:
            clasif = "coordenada_repetida_bajo_mismo_codigo"
            razon = f"{n_apariciones} apariciones, misma coordenada — posible reenvío o reproceso del mismo evento"
        else:
            clasif = "mismo_codigo_puntos_distintos"
            razon = f"{n_apariciones} apariciones con {n_coords} coordenadas distintas (por debajo del umbral de placeholder) — requiere revisión manual"

        filas.append({
            "cod_dtd": cod_dtd, "n_apariciones": n_apariciones, "n_coordenadas_distintas": n_coords,
            "n_dtd_registro_id_distintos": n_registro_id, "clasificacion": clasif, "razon": razon,
        })

    df_cod = pd.DataFrame(filas)

    # Coordenada repetida bajo códigos DISTINTOS (el caso complementario: un
    # mismo punto físico reportado con más de un `cod_dtd`).
    por_coord = df.groupby("coord_redondeada")["cod_dtd"].nunique()
    coords_multi_codigo = por_coord[por_coord > 1]
    df_coord_multi = pd.DataFrame({
        "coordenada": [str(c) for c in coords_multi_codigo.index],
        "n_codigos_distintos_en_misma_coordenada": coords_multi_codigo.values,
    })

    resumen = pd.concat([
        df_cod.assign(tipo_analisis="por_cod_dtd"),
        df_coord_multi.rename(columns={"coordenada": "cod_dtd"}).assign(
            tipo_analisis="por_coordenada", n_apariciones=None, n_coordenadas_distintas=None,
            n_dtd_registro_id_distintos=None, clasificacion="punto_repetido_con_multiples_codigos",
            razon=lambda d: "misma coordenada asociada a " + d["n_codigos_distintos_en_misma_coordenada"].astype(str) + " cod_dtd distintos",
        ).drop(columns=["n_codigos_distintos_en_misma_coordenada"]),
    ], ignore_index=True)
    return resumen


def summarize_dtd_metrics(df: pd.DataFrame) -> dict[str, int]:
    """Sección J: tres métricas distintas, NUNCA presentadas como
    equivalentes entre sí."""
    return {
        "n_registros_dtd": len(df),
        "n_coordenadas_dtd_unicas": df.assign(c=list(zip(df["x"].round(PRECISION_COORDENADA), df["y"].round(PRECISION_COORDENADA))))["c"].nunique(),
        "n_nucleos_dtd": df["nucleo_tri"].nunique(dropna=True),
    }


# ---------------------------------------------------------------------------
# K. Metodología de asignación territorial futura (definición, sin construir
# todavía la tabla final de 1.122 unidades)
# ---------------------------------------------------------------------------


def assign_dtd_points_to_mgn2025(df: pd.DataFrame, territorial_index, assign_point_fn) -> pd.DataFrame:
    """Implementa la metodología de la sección K sobre una muestra —no el
    universo completo—, para dejarla lista y validada:

    1. Los puntos ya vienen en EPSG:4326 (columnas `x`, `y` reales del
       servicio) — no se requiere transformación de CRS.
    2. Asignación mediante `covers()` sobre MGN2025 (reutiliza
       `aquabosque.geo.point_assignment.assign_point`, mismo patrón que la
       Fase 4B para calidad de agua).
    3. Se audita el código municipal de la fuente (`cod_mpio`, `nom_depto`)
       contra el municipio/departamento espacial resultante — nunca se usa
       el código de la fuente para sobrescribir la asignación espacial.
    4. No se convierte ningún punto en hectáreas.
    """
    filas = []
    for _, row in df.iterrows():
        resultado = assign_point_fn(row["x"], row["y"], territorial_index)
        filas.append({
            "dtd_registro_id": row.get("dtd_registro_id"), "cod_mpio_fuente": row.get("cod_mpio"),
            "nom_depto_fuente": row.get("cod_depto"),
            "cod_mpio_espacial_mgn2025": resultado.cod_dane_mpio_asignado,
            "metodo_asignacion": resultado.metodo_asignacion,
            "coincide_municipio_fuente_vs_espacial": (row.get("cod_mpio") == resultado.cod_dane_mpio_asignado) if resultado.cod_dane_mpio_asignado else None,
        })
    return pd.DataFrame(filas)
