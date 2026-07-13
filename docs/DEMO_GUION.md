# Guion de demo — AquaBosque Minero IA (máx. 4 minutos)

## 1. Problema (30 s)

"Colombia no tiene una vista territorial única que combine minería formal, calidad de agua,
detecciones tempranas de deforestación y cobertura forestal confirmada para priorizar revisión
técnica ambiental. AquaBosque Minero IA integra estas fuentes sobre las 1.122 unidades
DIVIPOLA vigentes."

## 2. Mapa (45 s)

Abrir la pestaña **Mapa nacional**. Mostrar el coropletico por `score_prioridad_evidencia`,
cambiar a `anomalía IA`, filtrar por un departamento minero conocido (p. ej. Antioquia o
Bolívar) para mostrar concentración territorial real.

## 3. Ranking (45 s)

Pestaña **Ranking**: mostrar el top nacional, aplicar el filtro "Sin monitoreo" en agua para
evidenciar la brecha de información, descargar el CSV filtrado.

## 4. Detalle de Puerto Rico, Meta (60 s)

Pestaña **Detalle territorial**, seleccionar Puerto Rico (preseleccionado por defecto). Mostrar
las 4 tarjetas (minería, agua, DTD, IA) y la tarjeta de **evidencia forestal confirmada**
(único municipio con bosque/deforestación real validados: 49,68 % de bosque en 2024,
2.972,71 ha de deforestación 2023-2024). Cambiar a un segundo municipio del top 20 para mostrar
el mensaje "No disponible en el MVP nacional. No equivale a cero deforestación."

## 5. IA explicable (45 s)

Volver al Ranking o Detalle y mostrar `es_perfil_atipico` y `explicacion_anomalia` de un
municipio atípico — enfatizar que es un **detector no supervisado de patrones**, no una
predicción de deforestación ni un indicador de minería ilegal.

## 6. Limitaciones (30 s)

Pestaña **Metodología y limitaciones**: leer en voz alta las 4 afirmaciones clave — no
causalidad, no detección de minería ilegal, no clasificación legal de agua, no tiempo real.

## 7. Escalabilidad (15 s)

Cerrar mencionando que la arquitectura forestal nacional (grilla de 896 tiles, colormap
validado por capa, 0 % de RGB desconocido) ya está diseñada y lista para una futura fase de
adquisición nacional — este MVP demuestra el motor de priorización con el piloto ya validado.
