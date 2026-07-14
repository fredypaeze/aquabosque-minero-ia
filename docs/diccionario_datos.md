# Diccionario de datos

Dataset maestro: 1 fila por municipio.

| Variable | Definición | Fuente |
|---|---|---|
| cod_mpio | Código DANE del municipio | DANE |
| municipio | Nombre | DANE |
| departamento | Departamento | DANE |
| lat | Latitud centroide | DANE |
| lon | Longitud centroide | DANE |
| mineria_titulos | N° de explotadores mineros (RUCOM) | ANM |
| mineria_minerales | N° de minerales distintos | ANM |
| mineria_volumen | Volumen de explotación acumulado (ANM) | ANM |
| mineria_regalias | Regalías pagadas (ANM) | ANM |
| es_pdet | 1 si municipio PDET | DPS/PDET |
| deforestacion_ha | Hectáreas deforestadas (peor año, IDEAM) | IDEAM |
| agua_ica_medio | Índice de Calidad del Agua medio 0-1 (IDEAM) | IDEAM |
| agua_estaciones | N° estaciones ICA cercanas | IDEAM |
| runap_areas | N° áreas protegidas cercanas (RUNAP) | RUNAP |
| runap_hectareas | Hectáreas protegidas | RUNAP |
| idx_minero | Índice minero normalizado 0-1 | derivada |
| idx_deforestacion | Índice deforestación 0-1 | derivada |
| idx_hidrico | Índice hídrico 0-1 (1-ICA) | derivada |
| idx_sensibilidad | Índice sensibilidad 0-1 | derivada |
| riesgo_score | Score compuesto 0-1 | derivada |
| riesgo_nivel | Nivel: Bajo/Medio/Alto/Crítico | derivada |
| hidrico_sin_dato | 1 si municipio sin estación ICA | derivada |
