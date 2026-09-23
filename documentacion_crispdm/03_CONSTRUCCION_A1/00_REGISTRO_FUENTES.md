# REGISTRO COMPARTIDO DE FUENTES Y EVIDENCIAS

## 1. Fuentes del documento histórico

### Documento: AquaBosque_A1_Definicion_Tematica.docx
- **Ruta**: /home/tuxilo/AquaBosque_A1_Definicion_Tematica.docx
- **Tipo**: Documento Word (.docx)
- **Descripción**: Documento histórico de definición temática del proyecto AquaBosque

## 2. Fuentes técnicas del proyecto

### Repositorio principal del proyecto
- **Ruta**: /home/tuxilo/aquabosque-minero-ia
- **Tipo**: Directorio de proyecto Git
- **Descripción**: Repositorio principal del proyecto AquaBosque Minero IA

### Código fuente relevante
- **Ruta**: /home/tuxilo/aquabosque-minero-ia/src/aquabosque/features/build_target.py
- **Tipo**: Archivo Python
- **Descripción**: Código fuente relacionado con construcción del target (objetivo del proyecto)

- **Ruta**: /home/tuxilo/aquabosque-minero-ia/src/aquabosque/models/train.py
- **Tipo**: Archivo Python
- **Descripción**: Código fuente relacionado con entrenamiento de modelos

- **Ruta**: /home/tuxilo/aquabosque-minero-ia/src/aquabosque/satelital/firms_signal.py
- **Tipo**: Archivo Python
- **Descripción**: Código fuente relacionado con señales satelitales

### Documentación técnica
- **Ruta**: /home/tuxilo/aquabosque-minero-ia/README.md
- **Tipo**: Archivo Markdown
- **Descripción**: Documentación general del proyecto

- **Ruta**: /home/tuxilo/aquabosque-minero-ia/docs
- **Tipo**: Directorio
- **Descripción**: Documentación específica del proyecto

## 3. Fuentes de datos oficiales

### Fuentes oficiales mencionadas en el documento histórico
- **ANM**: Agencia Nacional de Minería
- **IDEAM**: Instituto de Hidrología, Meteorología y Estudios Ambientales
- **NASA**: National Aeronautics and Space Administration
- **IDIGER**: Instituto de Geografía

## 4. Fuentes del framework DOCUMENT

### Protocolos del framework
- **Protocolo PRD-04**: Pipeline de redacción documental
- **Protocolo PEDAT**: Profundidad en el tratamiento de datos
- **Protocolo PGV-ACG**: Separación entre narrativa y evidencia
- **Protocolo PBF**: Uso de bibliografía en documentos

## 5. Fuentes de datos del proyecto específico

### Datos geoespaciales
- **Ruta**: /home/tuxilo/aquabosque-minero-ia/data/municipios.geojson
- **Tipo**: Archivo GeoJSON
- **Descripción**: Datos geoespaciales de municipios colombianos

### Archivos de configuración
- **Ruta**: /home/tuxilo/aquabosque-minero-ia/config
- **Tipo**: Directorio
- **Descripción**: Configuración del proyecto

## 6. Fuentes del modelo de riesgo

### Modelo de riesgo de suspensión
- **Ruta**: /home/tuxilo/modelo-riesgo-suspension
- **Tipo**: Directorio de proyecto
- **Descripción**: Proyecto específico del modelo de riesgo de suspensión

### Archivos clave del modelo de riesgo
- **Ruta**: /home/tuxilo/modelo-riesgo-suspension/6. modelo_riesgo_apagon_montecarlo.py
- **Tipo**: Archivo Python
- **Descripción**: Script principal del modelo de riesgo de suspensión

- **Ruta**: /home/tuxilo/modelo-riesgo-suspension/DOCUMENTACION_PROYECTO_MODELO_RIESGO_APAGON.md
- **Tipo**: Archivo Markdown
- **Descripción**: Documentación del proyecto de modelo de riesgo

- **Ruta**: /home/tuxilo/modelo-riesgo-suspension/README_modelo_riesgo_apagon.md
- **Tipo**: Archivo Markdown
- **Descripción**: README del proyecto de modelo de riesgo

## 7. Evidencia técnica específica

### Evidencia de funcionamiento del sistema
- **Servicio**: /home/tuxilo/.config/systemd/user/visor-riesgo-apagon.service
- **Tipo**: Archivo de servicio systemd
- **Descripción**: Servicio de visualización del riesgo de apagón

### Evidencia de datos del modelo de riesgo
- **Ruta**: /home/tuxilo/.openclaw/workspace/tmp/tuxilo/modelo_apagon/curated/indice_riesgo_dashboard.json
- **Tipo**: Archivo JSON
- **Descripción**: Índice de riesgo del dashboard

## 8. Clasificación de evidencia

| Tipo | Estado | Descripción |
|------|--------|-------------|
| Documento histórico | CONFIRMED | AquaBosque_A1_Definicion_Tematica.docx |
| Código fuente del proyecto | CONFIRMED | src/aquabosque/features/build_target.py |
| Código fuente del modelo de riesgo | CONFIRMED | modelo-riesgo-suspension/6. modelo_riesgo_apagon_montecarlo.py |
| Configuración del proyecto | CONFIRMED | config/ |
| Datos geoespaciales | CONFIRMED | data/municipios.geojson |
| Servicio del sistema | CONFIRMED | visor-riesgo-apagon.service |
| Documentación técnica | CONFIRMED | README.md, docs/ |
| Fuentes oficiales | PARTIAL | ANM, IDEAM, NASA, IDIGER |
| Evidencia de funcionamiento | CONFIRMED | índice_riesgo_dashboard.json |

## 9. Evidencia de componentes complementarios

### Componente de incendios
- **Fuente**: Documento histórico menciona "capa de incendios (medición de área quemada por dNBR en municipios seleccionados)"
- **Estado**: PARTIAL - Solo se menciona en el documento histórico, no se encuentra evidencia específica en el workspace

### Componente de alerta urbana de Bogotá
- **Fuente**: Documento histórico menciona "capa de alerta temprana urbana para Bogotá"
- **Estado**: PARTIAL - Solo se menciona en el documento histórico, no se encuentra evidencia específica en el workspace

## 10. Pendientes de verificación

### Pendientes de confirmación
1. **Fuentes oficiales**: Verificar disponibilidad y uso de ANM, IDEAM, NASA, IDIGER
2. **Componentes complementarios**: Verificar existencia de datos específicos para incendios y alerta urbana de Bogotá
3. **Datos históricos**: Verificar disponibilidad de datos desde 2010 (para el nuevo enfoque temporal)
4. **Datos en tiempo real**: Verificar si existen datos que puedan considerarse cercanos al tiempo real

### Pendientes de investigación
1. **Evidencia de funcionamiento**: Verificar el funcionamiento completo del sistema
2. **Código fuente**: Revisar completamente el código fuente para validar afirmaciones técnicas
3. **Documentación**: Revisar documentación técnica adicional del proyecto