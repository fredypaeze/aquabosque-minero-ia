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
    para decodificarla")."""
    items = sorted((rgb, meta["codigo"], meta["clase"]) for rgb, meta in colormap.items())
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
