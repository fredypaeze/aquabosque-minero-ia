"""Decodificación reproducible del colormap RGB de los servicios ráster de
bosque del IDEAM (Fase 2D.3, secciones G/H).

Los servicios `Superficie_Bosque` y `Dinamica_Cambio_Cobertura_Bosque`
publican WCS/exportImage como imagen renderizada (RGB), no como grid de
códigos de clase (hallazgo real de la Fase 2D.1/2D.2). Este módulo centraliza
la única lógica de decodificación RGB -> código de clase que debe usar
cualquier descarga futura, para que un cambio de leyenda en el servicio se
detecte (vía hash) en vez de decodificarse silenciosamente con una paleta
vieja.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

import numpy as np

# Códigos técnicos reservados, nunca asignados por IDEAM a una clase real
# (las clases reales observadas hasta ahora son 0-5, ver forest_layer_colormaps.csv).
CLASE_DESCONOCIDA = 254
NODATA_TECNICO_MASCARA_EXTERNA = 253

TOLERANCIA_CLASE_DESCONOCIDA_DEFAULT = 0.0  # % — cualquier RGB desconocido detiene el proceso salvo config explícita


class ClaseDesconocidaExcedeTolerancia(RuntimeError):
    """Se supera la tolerancia configurada de píxeles con RGB no reconocido."""


class ColormapRegistryError(RuntimeError):
    """Error base al resolver un colormap desde el registro versionado
    (Fase 2D.4, sección E) — nunca se recurre a un diccionario global
    implícito cuando ocurre cualquiera de estos errores."""


class ColormapNoDisponible(ColormapRegistryError):
    """No existe ninguna fila validada en el registro para la combinación
    producto+periodo+layer_id solicitada."""


class HashColormapNoCoincide(ColormapRegistryError):
    """El hash recalculado del colormap cargado del registro no coincide con
    el `hash_colormap` esperado — la leyenda pudo cambiar entre la
    validación y el uso."""


class RendererInesperado(ColormapRegistryError):
    """La capa devolvió (según el registro) un tipo de renderer distinto al
    validado — no se puede asumir que la correspondencia RGB->clase se
    mantiene."""


@dataclass
class DecodeResult:
    class_array: np.ndarray
    n_pixeles_totales: int
    n_decodificados: int
    n_clase_desconocida: int
    n_nodata_mascara_externa: int
    pct_clase_desconocida: float
    rgb_desconocidos: list[tuple[int, int, int]] = field(default_factory=list)
    codigos_clase_presentes: list[int] = field(default_factory=list)


def hash_colormap(colormap: dict[tuple[int, int, int], dict[str, Any]]) -> str:
    """Hash determinístico de una leyenda/colormap — cualquier cambio en los
    colores o en las clases asociadas produce un hash distinto (sección G:
    "cada descarga futura debe quedar asociada al hash de la leyenda usada
    para decodificarla").

    Normaliza RGB y código a `int` de Python antes de calcular el hash: un
    colormap construido en memoria (claves RGB como `np.uint8`, típico al
    leer un ráster) y el mismo colormap reconstruido desde el registro CSV
    (enteros nativos de Python) deben producir el MISMO hash — de lo
    contrario `decode_layer_from_registry` (sección E) fallaría siempre por
    una diferencia de tipo, no de contenido real (bug real encontrado y
    corregido en la Fase 2D.4)."""
    items = sorted(
        (tuple(int(c) for c in rgb), int(meta["codigo"]), str(meta["clase"]))
        for rgb, meta in colormap.items()
    )
    payload = repr(items).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def decode_ideam_rgb_classes(
    rgb: np.ndarray,
    colormap: dict[tuple[int, int, int], dict[str, Any]],
    *,
    alpha: np.ndarray | None = None,
    tolerancia_pct: float = TOLERANCIA_CLASE_DESCONOCIDA_DEFAULT,
    detener_si_excede: bool = True,
) -> DecodeResult:
    """Decodifica un arreglo RGB (H, W, 3) a códigos de clase, siguiendo las
    reglas obligatorias de la sección H:

    1. Un RGB exacto conocido se transforma en su código de clase real.
    2. Un píxel con canal alfa 0 (transparencia / máscara externa) se marca
       con `NODATA_TECNICO_MASCARA_EXTERNA`, nunca con la clase 0 real.
    3. Un RGB desconocido se transforma en `CLASE_DESCONOCIDA` (254) —
       **nunca** en la clase 0 ("Sin Información"), que es una clase real de
       IDEAM y no debe confundirse con "no lo pudimos decodificar".
    4. Si el porcentaje de píxeles en `CLASE_DESCONOCIDA` supera
       `tolerancia_pct` (por defecto 0,0%), se detiene con
       `ClaseDesconocidaExcedeTolerancia` — salvo que `detener_si_excede=False`
       (uso explícito para auditoría, nunca para una descarga que se vaya a
       promover como canónica).
    """
    if rgb.ndim != 3 or rgb.shape[-1] != 3:
        raise ValueError("`rgb` debe tener forma (alto, ancho, 3)")

    h, w, _ = rgb.shape
    class_array = np.full((h, w), CLASE_DESCONOCIDA, dtype=np.uint8)
    total = h * w

    flat_rgb = rgb.reshape(-1, 3)
    flat_class = class_array.reshape(-1)

    codigos_presentes: set[int] = set()
    for color, meta in colormap.items():
        mask = np.all(flat_rgb == np.array(color, dtype=rgb.dtype), axis=-1)
        if mask.any():
            flat_class[mask] = meta["codigo"]
            codigos_presentes.add(meta["codigo"])

    n_mascara_externa = 0
    if alpha is not None:
        flat_alpha = alpha.reshape(-1)
        mask_transparente = flat_alpha == 0
        n_mascara_externa = int(mask_transparente.sum())
        flat_class[mask_transparente] = NODATA_TECNICO_MASCARA_EXTERNA

    class_array = flat_class.reshape(h, w)

    n_desconocidos = int((class_array == CLASE_DESCONOCIDA).sum())
    n_decodificados = total - n_desconocidos - n_mascara_externa
    pct_desconocido = round(n_desconocidos / total * 100, 4) if total else 0.0

    rgb_desconocidos = []
    if n_desconocidos:
        idx_desconocidos = np.where(flat_class == CLASE_DESCONOCIDA)[0]
        rgb_desconocidos = sorted({tuple(int(v) for v in flat_rgb[i]) for i in idx_desconocidos})

    if detener_si_excede and pct_desconocido > tolerancia_pct:
        raise ClaseDesconocidaExcedeTolerancia(
            f"{pct_desconocido:.4f}% de píxeles con RGB desconocido supera la tolerancia "
            f"configurada ({tolerancia_pct}%). RGB no reconocidos: {rgb_desconocidos[:10]}"
            + (" (truncado)" if len(rgb_desconocidos) > 10 else "")
        )

    return DecodeResult(
        class_array=class_array,
        n_pixeles_totales=total,
        n_decodificados=n_decodificados,
        n_clase_desconocida=n_desconocidos,
        n_nodata_mascara_externa=n_mascara_externa,
        pct_clase_desconocida=pct_desconocido,
        rgb_desconocidos=rgb_desconocidos,
        codigos_clase_presentes=sorted(codigos_presentes),
    )


# ---------------------------------------------------------------------------
# Colormaps oficiales confirmados con `identify()` real (Fase 2D.1/2D.2/2D.3).
# Cualquier capa nueva debe volver a confirmarse con `identify()` antes de
# reutilizar estos diccionarios — ver `forest_layer_colormaps.csv`.
# ---------------------------------------------------------------------------

COLORMAP_BOSQUE_NO_BOSQUE: dict[tuple[int, int, int], dict[str, Any]] = {
    (0, 0, 0): {"codigo": 0, "clase": "Sin Informacion o NoData"},
    (60, 137, 39): {"codigo": 1, "clase": "Bosque"},
    (244, 244, 215): {"codigo": 2, "clase": "No Bosque"},
}

COLORMAP_CAMBIO_BOSQUE: dict[tuple[int, int, int], dict[str, Any]] = {
    (0, 0, 0): {"codigo": 0, "clase": "Sin Informacion o NoData"},
    (60, 137, 39): {"codigo": 1, "clase": "Bosque Estable"},
    (255, 0, 0): {"codigo": 2, "clase": "Deforestacion"},
    (244, 244, 215): {"codigo": 5, "clase": "No Bosque Estable"},
}


# ---------------------------------------------------------------------------
# Fase 2D.4, sección E: registro versionado por producto+periodo+layer_id.
#
# Hallazgo real (sección B/C): el servicio NO usa el mismo renderer para
# todos los años — `identify()` devuelve atributos `Colormap.*` (con RGB
# directo) para Bosque 2024, `UniqueValue.*` + `Raster.red/green/blue` para
# Bosque 2022, y `UniqueValue.*` + una etiqueta de nombre de campo variable
# (`Raster.leyenda`, `Raster.tipo_cobertura`, `Raster.tipo_cob`...) sin RGB
# expuesto para 2013/2018/1990/2020. Por eso `decode_ideam_rgb_classes` NUNCA
# debe recibir un único diccionario global: cada capa debe resolver su propio
# colormap desde el registro real (`forest_layer_colormaps.csv`), verificado
# por hash, antes de decodificar.
# ---------------------------------------------------------------------------


def load_colormap_from_registry(
    registro: "pd.DataFrame",  # noqa: F821 - anotación solo para documentación, sin import duro de pandas
    *,
    producto: str,
    periodo: str,
    layer_id: int,
    hash_colormap: str | None = None,
) -> dict[tuple[int, int, int], dict[str, Any]]:
    """Construye el colormap real de una capa a partir del registro
    versionado, filtrando por producto+periodo+layer_id (nunca por producto
    solo). Si `hash_colormap` se provee, debe coincidir exactamente con el
    hash recalculado del colormap cargado."""
    filas = registro[
        (registro["producto"] == producto)
        & (registro["periodo"].astype(str) == str(periodo))
        & (registro["layer_id"] == layer_id)
        & (registro["rgb_r"].notna())
    ]
    if filas.empty:
        raise ColormapNoDisponible(
            f"No hay colormap validado en el registro para producto={producto!r}, periodo={periodo!r}, layer_id={layer_id!r}."
        )
    colormap: dict[tuple[int, int, int], dict[str, Any]] = {}
    for _, fila in filas.iterrows():
        rgb = (int(fila["rgb_r"]), int(fila["rgb_g"]), int(fila["rgb_b"]))
        colormap[rgb] = {"codigo": int(fila["codigo_clase"]), "clase": str(fila["nombre_clase"])}

    if hash_colormap is not None:
        hash_real = hash_colormap_(colormap)
        if hash_real != hash_colormap:
            raise HashColormapNoCoincide(
                f"Hash del colormap cargado ({hash_real}) no coincide con el esperado ({hash_colormap}) "
                f"para producto={producto!r}, periodo={periodo!r}, layer_id={layer_id!r}."
            )
    return colormap


def decode_layer_from_registry(
    rgb: np.ndarray,
    registro: "pd.DataFrame",  # noqa: F821
    *,
    producto: str,
    periodo: str,
    layer_id: int,
    hash_colormap: str | None = None,
    alpha: np.ndarray | None = None,
    tolerancia_pct: float = TOLERANCIA_CLASE_DESCONOCIDA_DEFAULT,
    detener_si_excede: bool = True,
) -> DecodeResult:
    """Punto de entrada obligatorio para decodificar una capa en producción
    (sección E): resuelve el colormap desde el registro real por
    producto+periodo+layer_id (nunca un diccionario global compartido) y
    delega en `decode_ideam_rgb_classes`. Se detiene (excepción, nunca
    decodificación silenciosa) si: no existe colormap para la capa
    (`ColormapNoDisponible`), el hash no coincide (`HashColormapNoCoincide`),
    o aparecen colores desconocidos por encima de la tolerancia
    (`ClaseDesconocidaExcedeTolerancia`, heredado de `decode_ideam_rgb_classes`)."""
    colormap = load_colormap_from_registry(
        registro, producto=producto, periodo=periodo, layer_id=layer_id, hash_colormap=hash_colormap
    )
    return decode_ideam_rgb_classes(
        rgb, colormap, alpha=alpha, tolerancia_pct=tolerancia_pct, detener_si_excede=detener_si_excede
    )


# Alias interno para evitar sombrear el parámetro `hash_colormap` de las
# funciones anteriores con la función homónima del módulo.
hash_colormap_ = hash_colormap


# ---------------------------------------------------------------------------
# Fase 2D.4, sección B: interpretación de la respuesta real de `identify()`.
#
# Evidencia real (esta fase): el campo que expone el renderer y el RGB varía
# por capa/año -
#   - Bosque 2024:        {"Colormap.Pixel Value": ..., "Colormap.Color(a,r,g,b)": "a,r,g,b", "Raster.tipo_cober": ...}
#   - Bosque 2022:        {"UniqueValue.Pixel Value": ..., "Raster.red/green/blue/opacity": ..., "Raster.tipo_cober": ...}
#   - Bosque 2013/1990:   {"UniqueValue.Pixel Value": ..., "Raster.leyenda": ...}            (sin RGB)
#   - Bosque 2018:        {"UniqueValue.Pixel Value": ..., "Raster.tipo_cobertura": ...}      (sin RGB, typo real: "No Bsque Estable")
#   - Bosque 2020:        {"UniqueValue.Pixel Value": ..., "Raster.tipo_cob": ...}             (sin RGB)
# Ningún nombre de campo se asume fijo: se busca por prefijo/patrón.
# ---------------------------------------------------------------------------

_CAMPOS_RASTER_NO_ETIQUETA = {"objectid", "count", "red", "green", "blue", "opacity"}


def parse_identify_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    """Interpreta un diccionario `attributes` de una única entrada de
    `identify()` real. Devuelve `renderer_type` ("RasterColormapRenderer",
    "UniqueValueRenderer" o "desconocido"), `pixel_value` (código de clase
    declarado por el servicio), `rgb_directo` (tupla RGB si el propio
    `identify()` la expone; `None` si no) y `etiqueta` (nombre de clase
    textual, buscado por el primer campo `Raster.*` que no sea un campo
    técnico conocido)."""
    pixel_value = None
    renderer_type = "desconocido"
    if "Colormap.Pixel Value" in attributes:
        pixel_value = attributes["Colormap.Pixel Value"]
        renderer_type = "RasterColormapRenderer"
    elif "UniqueValue.Pixel Value" in attributes:
        pixel_value = attributes["UniqueValue.Pixel Value"]
        renderer_type = "UniqueValueRenderer"

    rgb_directo = None
    alpha_directo = None
    color_key = "Colormap.Color(a,r,g,b)"
    if color_key in attributes:
        partes = [int(v) for v in str(attributes[color_key]).split(",")]
        alpha_directo, r, g, b = partes[0], partes[1], partes[2], partes[3]
        rgb_directo = (r, g, b)
    elif all(f"Raster.{c}" in attributes for c in ("red", "green", "blue")):
        rgb_directo = tuple(int(attributes[f"Raster.{c}"]) for c in ("red", "green", "blue"))
        alpha_directo = int(attributes.get("Raster.opacity", 255))

    etiqueta = None
    for clave, valor in attributes.items():
        if clave.startswith("Raster.") and clave.split(".", 1)[1] not in _CAMPOS_RASTER_NO_ETIQUETA:
            etiqueta = valor
            break

    # El servicio real devuelve literalmente el texto "NoData" (no un
    # número) para píxeles SIN valor de clase — hallazgo real: esto ocurre en
    # capas `UniqueValueRenderer` (p. ej. Bosque 2013/2018/1990/2020), donde
    # el negro (0,0,0) NO es la clase real "Sin Información" sino NoData
    # confirmado por el propio servicio. Nunca se fuerza a int, nunca se
    # asimila a la clase 0 real — pero SÍ se distingue de un valor
    # simplemente no reconocido (`es_nodata_confirmado`).
    pixel_value_int = None
    es_nodata_confirmado = False
    if pixel_value is not None:
        try:
            pixel_value_int = int(pixel_value)
        except (TypeError, ValueError):
            es_nodata_confirmado = str(pixel_value).strip().lower() == "nodata"

    return {
        "renderer_type": renderer_type,
        "pixel_value": pixel_value_int,
        "rgb_directo": rgb_directo,
        "alpha_directo": alpha_directo,
        "etiqueta": etiqueta,
        "es_nodata_confirmado": es_nodata_confirmado,
    }
