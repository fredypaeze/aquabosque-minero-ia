Trabaja autónomamente sobre el proyecto AquaBosque Minero IA utilizando la metodología ubicada en:

/home/tuxilo/METODOLOGIA_ESTUDIOS_ESTRATEGICOS

y el workspace del proyecto ubicado en:

/home/tuxilo/aquabosque-minero-ia/documentacion_crispdm

Antes de ejecutar cualquier tarea:

1. Lee completamente:
   - /home/tuxilo/METODOLOGIA_ESTUDIOS_ESTRATEGICOS/AGENTS.md
   - /home/tuxilo/aquabosque-minero-ia/documentacion_crispdm/PROJECT_CONFIG.yaml
   - /home/tuxilo/aquabosque-minero-ia/documentacion_crispdm/MASTER_TASK.md
   - /home/tuxilo/aquabosque-minero-ia/documentacion_crispdm/STATE.json

2. Lee y aplica toda la gobernanza ubicada en:
   /home/tuxilo/METODOLOGIA_ESTUDIOS_ESTRATEGICOS/GOVERNANCE/

3. Lee y aplica todos los protocolos vigentes ubicados en:
   /home/tuxilo/METODOLOGIA_ESTUDIOS_ESTRATEGICOS/PROTOCOLS/

4. Lee y aplica los controles de calidad ubicados en:
   /home/tuxilo/METODOLOGIA_ESTUDIOS_ESTRATEGICOS/QA/

5. Ejecuta secuencialmente el workflow DOCUMENT ubicado en:
   /home/tuxilo/METODOLOGIA_ESTUDIOS_ESTRATEGICOS/WORKFLOWS/DOCUMENT/

   siguiendo estrictamente el orden:

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

6. No inicies la redacción de A1–A8 antes de aprobar el gate maestro de D04.

7. Trata el repositorio original y toda la evidencia primaria configurada como READ_ONLY.

8. Escribe todos los artefactos nuevos únicamente dentro de:

   /home/tuxilo/aquabosque-minero-ia/documentacion_crispdm

9. Usa la documentación histórica como antecedente y evidencia secundaria, nunca como verdad automática.

10. Reconstruye primero el ESTADO_CANONICO de AquaBosque y su evolución. No mezcles silenciosamente:
    - versiones del modelo;
    - métricas;
    - fórmulas;
    - variables;
    - extensiones;
    - experimentos;
    - documentación histórica.

11. Diferencia expresamente:
    - núcleo/MVP;
    - evolución;
    - monitoreo satelital;
    - alertas anticipatorias;
    - Zoom Bogotá;
    - incendios;
    - modelos o componentes descartados.

12. Para cada actividad A1–A8 produce un expediente técnico completo, no únicamente un documento.

13. Para todo documento sustantivo aplica obligatoriamente PRD-04:
    - definir producto;
    - inventariar evidencia;
    - diseñar arquitectura documental;
    - controlar cobertura;
    - congelar estructura;
    - planificar módulos;
    - redactar por partes;
    - controlar cada parte;
    - integrar únicamente partes aprobadas;
    - auditar el documento integrado.

14. Aplica además, según corresponda:
    - PEDAT;
    - Separación Narrativa-Evidencia;
    - PGV-ACG;
    - PGV-MAPAS;
    - PBF.

15. No inventes:
    - datos;
    - fuentes;
    - métricas;
    - decisiones históricas;
    - referencias;
    - resultados;
    - funcionalidades;
    - justificaciones.

16. Clasifica la información crítica según corresponda como:
    - VERIFICADA
    - INFERIDA
    - HISTORICA
    - CONTRADICTORIA
    - NO_DETERMINADA
    - NO_APLICA

17. Si un gate falla:
    - registra el fallo;
    - corrige;
    - revalida;
    - continúa cuando obtenga PASS.

18. No solicites intervención humana por decisiones operativas menores.

19. Detente únicamente ante un BLOCKER_CRITICO definido por la gobernanza.

20. Mantén actualizado continuamente:

   /home/tuxilo/aquabosque-minero-ia/documentacion_crispdm/STATE.json

21. La memoria conversacional no debe utilizarse como único mecanismo de estado.

22. Continúa autónomamente hasta alcanzar el estado global:

   APTO PARA REVISION HUMANA

23. No declares aprobación institucional ni aceptación oficial.

24. Al finalizar, entrega un resumen ejecutivo de ejecución que indique únicamente:
    - estado final;
    - checkpoints completados;
    - gates aprobados;
    - principales hallazgos;
    - contradicciones relevantes;
    - blockers, si existieron;
    - ubicación del documento maestro;
    - ubicación de A1–A8;
    - ubicación del paquete final;
    - pendientes que requieran revisión humana.

Inicia ahora desde el valor actual de STATE.json.

No vuelvas a diseñar la metodología. Ejecútala.
