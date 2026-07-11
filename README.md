# AquaBosque Minero IA

Proyecto de análisis de datos aplicado a recursos hídricos, cobertura boscosa y actividad minera, mediante herramientas de IA.

## Estado del proyecto

Fase actual: **Fase 0 — estructura base del repositorio**. Aún no se ha descargado ni cargado ningún dato, ni se ha entrenado ningún modelo, ni existe dashboard final.

## Estructura del repositorio

```
.
├── config/
│   ├── config.example.yaml # Configuración de ejemplo (copiar como config.yaml, no versionado)
│   └── .gitkeep
├── data/
│   ├── raw/                # Datos originales, sin modificar (no versionados en git)
│   ├── processed/          # Datos limpios/transformados (no versionados en git)
│   └── external/            # Datos de fuentes externas de referencia (no versionados en git)
├── docs/                   # Documentación del proyecto
├── notebooks/               # Notebooks de exploración y análisis
├── outputs/
│   ├── figures/             # Gráficos y visualizaciones generadas
│   └── reports/             # Reportes generados
├── scripts/                 # Scripts placeholder (aún no implementados)
│   ├── 01_download_data.py
│   ├── 02_process_data.py
│   ├── 03_train_model.py
│   └── 04_generate_report.py
├── src/aquabosque/          # Código fuente del paquete Python del proyecto
├── tests/                   # Pruebas automatizadas
├── venv/                    # Entorno virtual local (no versionado)
├── .env.example             # Variables de entorno de ejemplo (copiar como .env, no versionado)
├── .gitignore
├── README.md
└── requirements.txt
```

## Reglas de trabajo

1. Trabajo restringido a esta carpeta del repositorio.
2. No se leen, borran, mueven ni modifican archivos fuera de esta carpeta.
3. No se instalan paquetes globales; todo el trabajo usa el entorno virtual local `venv`.
4. No se ejecutan comandos destructivos.
5. No se hace push a repositorios remotos.
6. No se usan servicios pagos.
7. No se descargan archivos pesados sin avisar previamente.
8. No se inventan datos.
9. No se afirma causalidad ambiental ni minería ilegal; los análisis se limitan a lo que los datos permiten sustentar.

## Entorno virtual

El entorno virtual ya existe en `venv/`. Para activarlo (PowerShell):

```powershell
.\venv\Scripts\Activate.ps1
```

## Próximos pasos

- Definir fuentes de datos a utilizar (pendiente de aprobación antes de descargar).
- Ampliar `requirements.txt` con librerías geoespaciales/de modelado cuando se definan las fuentes y el alcance.
- Documentar en `docs/` el alcance y la metodología del proyecto.
- Implementar `scripts/01_download_data.py` una vez aprobadas las fuentes de datos (Fase 1).
