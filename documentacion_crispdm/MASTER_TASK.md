# MASTER TASK — AQUABOSQUE

## 1. MISIÓN

Reconstruir, verificar, complementar, documentar, validar y empaquetar integralmente el ciclo de vida del producto AquaBosque Minero IA utilizando el modo DOCUMENT de la METODOLOGIA_ESTUDIOS_ESTRATEGICOS.

La ejecución debe realizarse de manera autónoma hasta alcanzar:

`APTO PARA REVISION HUMANA`

salvo aparición de un `BLOCKER_CRITICO`.

---

# 2. RESULTADO ESPERADO

No se solicita únicamente producir documentos.

Se solicita construir un expediente técnico completo, verificable, reproducible y auditable que documente:

- definición temática;
- entendimiento del negocio;
- entendimiento de datos;
- preparación de datos;
- modelamiento;
- evaluación;
- despliegue;
- seguimiento y mejora continua;
- evolución del producto;
- extensiones;
- trazabilidad;
- arquitectura;
- código;
- datos;
- modelos;
- métricas;
- visualizaciones;
- mapas;
- fuentes;
- limitaciones;
- operación;
- reproducibilidad.

---

# 3. PRINCIPIO DE RECONSTRUCCIÓN

AquaBosque ha evolucionado.

Existen evidencias de:

- diferentes configuraciones del modelo nacional;
- incorporación posterior de señales satelitales;
- Zoom Bogotá;
- incendios;
- alertas anticipatorias;
- documentación histórica;
- documentación de auditoría;
- modelos o experimentos descartados.

Está prohibido fusionar estas versiones silenciosamente.

Antes de redactar A1–A8 debe determinarse:

`ESTADO_CANONICO`

y reconstruirse la evolución del producto.

---

# 4. EVIDENCIA

Utilizar la evidencia definida en `PROJECT_CONFIG.yaml`.

La jerarquía será la establecida en:

`GOVERNANCE/JERARQUIA_EVIDENCIA.md`

La documentación histórica es un antecedente y una fuente secundaria.

No debe prevalecer automáticamente sobre:

- código;
- datos;
- configuraciones;
- tests;
- métricas;
- metadatos;
- artefactos reproducibles;
- producto desplegado.

---

# 5. DOCUMENTACIÓN PREVIA

Existen documentos A1–A8 previamente generados.

Deben:

1. leerse;
2. inventariarse;
3. contextualizarse;
4. compararse con el producto actual;
5. aprovecharse cuando sigan siendo válidos;
6. corregirse cuando existan contradicciones;
7. complementarse cuando existan vacíos.

No deben copiarse ciegamente.

La nueva documentación debe representar el estado técnico verificable del producto y su evolución.

---

# 6. PROTOCOLOS

Todos los protocolos configurados en `PROJECT_CONFIG.yaml` son obligatorios cuando corresponda.

Especialmente:

## PRD-04

Está prohibido redactar un documento sustantivo completo en una sola pasada.

Para cada A1–A8 y para el documento maestro ejecutar:

1. definición del producto;
2. inventario de evidencia;
3. arquitectura documental;
4. control de cobertura;
5. congelamiento de estructura;
6. plan de producción;
7. redacción modular;
8. control de cada parte;
9. integración;
10. auditoría.

## PEDAT

Desarrollar con profundidad suficiente sin relleno ni repetición artificial.

## Separación Narrativa-Evidencia

La narrativa final no debe convertirse en un volcado de auditoría.

La evidencia técnica, matrices, vacíos y controles deberán permanecer en las capas correspondientes.

## PGV-ACG

Aplicar a todo gráfico, tabla, figura, esquema o diagrama.

## PGV-MAPAS

Aplicar a toda cartografía o análisis territorial.

## PBF

Aplicar a toda fuente bibliográfica, técnica, institucional u oficial.

No inventar referencias.

---

# 7. PRODUCTOS A1–A8

Cada actividad debe producir un expediente, no únicamente un DOCX.

La estructura esperada es:

- control;
- evidencias;
- análisis;
- matrices/datos;
- visuales;
- documentación;
- anexos;
- validación;
- entrega.

Los workflows D05–D12 definen el contenido mínimo.

---

# 8. TAREAS TAIGA

Debe quedar correspondencia verificable con:

- #190 A1 Definición temática
- #191 A2 Entendimiento del negocio
- #192 A3 Entendimiento de los datos
- #193 A4 Preparación de los datos
- #194 A5 Modelamiento de los datos
- #195 A6 Evaluación del modelo
- #196 A7 Despliegue del modelo
- #197 Revisión integral

A8 Seguimiento y mejora continua se mantiene como expediente complementario y no debe presentarse como fase oficial CRISP-DM.

---

# 9. EXTENSIONES

Investigar y documentar de manera diferenciada:

- monitoreo satelital;
- alertas anticipatorias;
- Zoom Bogotá;
- incendios.

Para cada extensión determinar:

- origen;
- fecha aproximada;
- motivación;
- fuentes;
- datos;
- transformaciones;
- modelos/reglas;
- funcionalidades;
- validaciones;
- limitaciones;
- relación con el núcleo AquaBosque.

No asumir que fueron parte del MVP inicial.

---

# 10. PRODUCTO DESPLEGADO

Auditar:

https://streamlit.spartanit.pro/

Contrastar el producto observable con:

- código;
- datos;
- documentación;
- artefactos;
- métricas.

No documentar como funcionalidad vigente algo que no pueda verificarse.

---

# 11. PROTECCIÓN

El repositorio principal constituye evidencia.

Tratar como READ_ONLY todo lo definido en `protected_paths`.

Todo artefacto nuevo debe escribirse exclusivamente dentro de:

`/home/tuxilo/aquabosque-minero-ia/documentacion_crispdm`

salvo artefactos temporales estrictamente necesarios y seguros.

---

# 12. AUTONOMÍA

Ejecutar de manera autónoma.

No solicitar intervención humana para:

- estructura de carpetas;
- nombres de archivos;
- selección de técnicas reversibles;
- generación de scripts auxiliares;
- corrección de errores recuperables;
- reejecución de análisis;
- decisiones operativas menores.

Ante QA_FAILED:

corregir → revalidar → continuar.

Solicitar intervención únicamente ante BLOCKER_CRITICO según la gobernanza.

---

# 13. ORDEN OBLIGATORIO

Ejecutar secuencialmente:

D00
→ D01
→ D02
→ D03
→ D04
→ D05/A1
→ D06/A2
→ D07/A3
→ D08/A4
→ D09/A5
→ D10/A6
→ D11/A7
→ D12/A8
→ D13
→ D14
→ D15

No iniciar redacción de A1–A8 antes de aprobar D04.

No integrar documentos que no hayan aprobado sus gates.

---

# 14. ESTADO

Mantener actualizado:

`STATE.json`

La ejecución debe ser reanudable.

La memoria conversacional no constituye fuente suficiente de estado.

---

# 15. CRITERIO FINAL

El trabajo solo termina cuando:

- D00–D15 aplicables estén ejecutados;
- A1–A8 estén completos;
- todos los gates críticos estén PASS;
- los protocolos hayan sido auditados;
- no existan hallazgos críticos abiertos;
- el documento maestro exista;
- exista trazabilidad;
- exista manifiesto de entrega;
- STATE.json esté actualizado.

Estado final automático permitido:

`APTO PARA REVISION HUMANA`

No declarar aprobación institucional.
