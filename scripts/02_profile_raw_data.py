"""Fase 3A: inspección y perfilamiento de datos crudos ya descargados.

Lee (sin limpiar ni transformar) las 3 fuentes MVP descargadas en la Fase 2A/2A.1:
  1. DIVIPOLA - Códigos de municipios (DANE), XLSX.
  2. ANM Títulos Mineros - Anotaciones RMN, JSON.
  3. IDEAM - Data Histórica de Calidad de Agua, JSON por lotes (4 partes + manifest).

Genera un reporte Markdown por fuente más un resumen general en
outputs/reports/raw_data_profile/. No guarda ningún dataset limpio o
procesado en data/processed/, no construye dataset maestro, no entrena
modelo, no crea dashboard y no descarga nada nuevo.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aquabosque.data.profile import (  # noqa: E402
    profile_dataframe,
    render_profile_markdown,
    value_counts_markdown,
)

DATA_RAW = PROJECT_ROOT / "data" / "raw"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports" / "raw_data_profile"

DIVIPOLA_PATH = DATA_RAW / "territorio" / "dane_divipola_municipios.xlsx"
ANM_PATH = DATA_RAW / "mineria" / "anm_titulos_anotaciones_rmn.json"
AGUA_DIR = DATA_RAW / "agua" / "ideam_calidad_agua_historica"
AGUA_MANIFEST_PATH = AGUA_DIR / "manifest.json"


# --------------------------------------------------------------------------
# Carga de datos crudos (solo lectura, sin transformar ni guardar nada)
# --------------------------------------------------------------------------


def load_divipola() -> pd.DataFrame:
    """Lee la hoja 'Municipios' del XLSX de DIVIPOLA.

    El archivo del Geoportal DANE tiene un encabezado de dos filas con celdas
    combinadas (Departamento > Código/Nombre, Municipio > Código/Nombre,
    Tipo, Localización > Longitud/Latitud/Nota) y varias filas de título
    antes de los datos. pandas resuelve el encabezado combinado con
    header=[9, 10] (0-indexado); los datos empiezan en la fila siguiente.
    """
    df = pd.read_excel(DIVIPOLA_PATH, sheet_name="Municipios", header=[9, 10])
    df.columns = [
        "depto_codigo",
        "depto_nombre",
        "mpio_codigo",
        "mpio_nombre",
        "tipo",
        "longitud",
        "latitud",
        "nota",
    ]
    return df


def load_anm_anotaciones() -> pd.DataFrame:
    return pd.read_json(ANM_PATH, encoding="utf-8")


def load_calidad_agua_por_lotes() -> tuple[pd.DataFrame, dict]:
    """Lee el manifest y concatena las 4 partes SOLO en memoria (no se
    guarda ningún archivo concatenado en esta fase)."""
    import json

    with open(AGUA_MANIFEST_PATH, encoding="utf-8") as fh:
        manifest = json.load(fh)

    frames = []
    for parte in manifest["tamano_por_parte"]:
        part_path = AGUA_DIR / parte["archivo"]
        df_parte = pd.read_json(part_path, encoding="utf-8")
        assert len(df_parte) == parte["filas"], (
            f"{parte['archivo']}: filas leídas ({len(df_parte)}) no coincide con "
            f"manifest ({parte['filas']})"
        )
        frames.append(df_parte)

    df = pd.concat(frames, ignore_index=True)
    return df, manifest


# --------------------------------------------------------------------------
# Reportes específicos por fuente
# --------------------------------------------------------------------------


def build_divipola_report() -> tuple[str, dict]:
    df = load_divipola()
    profile = profile_dataframe(
        df,
        fuente="DIVIPOLA - Códigos de municipios (DANE)",
        ruta=str(DIVIPOLA_PATH.relative_to(PROJECT_ROOT)),
        extra_key_columns=["mpio_codigo", "depto_codigo"],
    )

    # --- Validaciones específicas de DIVIPOLA (solo lectura/reporte) ---
    n_total = len(df)
    tipo_counts = df["tipo"].value_counts(dropna=False)
    n_municipios_tipo = int(tipo_counts.get("Municipio", 0))
    n_filas_totalmente_vacias = int(df.isna().all(axis=1).sum())

    # Validar longitud del código de municipio (se espera texto de 5 dígitos,
    # p. ej. "05001"). El XLSX lo entrega como número, lo que pierde el cero
    # inicial: se valida reconstruyendo el texto SOLO para el reporte, sin
    # modificar el DataFrame ni guardar nada.
    cod_no_nulo = df["mpio_codigo"].dropna()
    cod_como_texto = cod_no_nulo.astype("Int64").astype(str).str.zfill(5)
    longitudes = cod_como_texto.str.len()
    n_codigos_5_digitos = int((longitudes == 5).sum())
    n_codigos_distinto_5 = int((longitudes != 5).sum())

    depto_unicos = sorted(df["depto_nombre"].dropna().unique().tolist())

    extra = []
    extra.append("## Validaciones específicas de DIVIPOLA")
    extra.append("")
    extra.append(f"- Filas totales en la hoja `Municipios`: {n_total}")
    extra.append(f"- Filas completamente vacías (título/pie de página del XLSX): {n_filas_totalmente_vacias}")
    extra.append(f"- Filas con `tipo == 'Municipio'`: {n_municipios_tipo}")
    extra.append(f"- Distribución de `tipo`: {tipo_counts.to_dict()}")
    extra.append(
        f"- Código de municipio reconstruido a texto de 5 dígitos (solo para validar, sin "
        f"modificar el archivo): {n_codigos_5_digitos} OK / {n_codigos_distinto_5} con longitud distinta a 5"
    )
    extra.append(
        "- **Hallazgo de calidad:** `mpio_codigo` se infiere como `float64` al leer el XLSX con "
        "pandas, lo que pierde el cero inicial (p. ej. `05001` queda como `5001.0`). Debe forzarse "
        "a texto con relleno de ceros en la Fase 3B (limpieza), no antes."
    )
    extra.append(f"- Departamentos únicos ({len(depto_unicos)}): {', '.join(depto_unicos)}")
    extra.append("")

    highlights = {
        "n_filas": n_total,
        "n_filas_utiles": n_municipios_tipo + int(tipo_counts.get("Área no municipalizada", 0)) + int(tipo_counts.get("Isla", 0)),
        "n_duplicados": profile["n_duplicados"],
        "llave_candidata": "mpio_codigo (código DANE de municipio, 5 dígitos)",
        "hallazgos": [
            "mpio_codigo se lee como float64 y pierde el cero inicial (05001 -> 5001.0); "
            "se debe forzar a texto con zfill(5) en la limpieza.",
            f"{n_filas_totalmente_vacias} filas son título/notas al pie del XLSX, no datos "
            "(quedan dentro del rango leído por pandas).",
            f"{profile['n_duplicados']} filas completamente duplicadas (en su mayoría, filas vacías).",
        ],
    }

    return render_profile_markdown(profile, extra_sections="\n".join(extra)), highlights


def build_anm_report() -> tuple[str, dict]:
    df = load_anm_anotaciones()
    profile = profile_dataframe(
        df,
        fuente="ANM Títulos Mineros - Anotaciones RMN",
        ruta=str(ANM_PATH.relative_to(PROJECT_ROOT)),
        extra_key_columns=["codigo_expediente"],
    )

    # --- Validaciones/reportes específicos de ANM (solo lectura) ---
    n_expedientes_unicos = df["codigo_expediente"].nunique()

    # fecha_anotacion viene como texto MM/DD/YYYY (confirmado con muestra:
    # valores como "04/15/2003" que solo son válidos como mes/día/año).
    fechas = pd.to_datetime(df["fecha_anotacion"], format="%m/%d/%Y", errors="coerce")
    n_fechas_invalidas = int(fechas.isna().sum() - df["fecha_anotacion"].isna().sum())
    rango_fechas = (fechas.min(), fechas.max()) if fechas.notna().any() else (None, None)

    extra = []
    extra.append("## Reportes específicos de ANM Anotaciones RMN")
    extra.append("")
    extra.append(f"- Expedientes únicos (`codigo_expediente`): {n_expedientes_unicos} sobre {len(df)} filas")
    extra.append(
        f"- Rango de `fecha_anotacion` (parseada como MM/DD/AAAA): "
        f"{rango_fechas[0]} — {rango_fechas[1]}"
    )
    if n_fechas_invalidas > 0:
        extra.append(f"- **Hallazgo de calidad:** {n_fechas_invalidas} valores de `fecha_anotacion` no parsean como MM/DD/AAAA")
    extra.append("")
    extra.append(value_counts_markdown(df["estado_juridico"], title="Estados jurídicos"))
    extra.append("")
    extra.append(value_counts_markdown(df["modalidad"], top_n=30, title="Modalidades (top 30)"))
    extra.append("")
    extra.append(value_counts_markdown(df["tipo_de_anotacion"], top_n=30, title="Tipos de anotación (top 30)"))
    extra.append("")

    highlights = {
        "n_filas": len(df),
        "n_expedientes_unicos": int(n_expedientes_unicos),
        "n_duplicados": profile["n_duplicados"],
        "llave_candidata": "codigo_expediente (llave de agrupación/FK hacia el título minero; NO es única por fila, cada expediente tiene varias anotaciones)",
        "hallazgos": [
            "estado_juridico es constante ('Activo' en el 100% de las filas): no aporta como variable, "
            "es un filtro implícito del dataset (solo trae anotaciones de títulos activos).",
            f"{profile['n_duplicados']} filas completamente duplicadas.",
            "fecha_anotacion y fecha_ejecutoria vienen como texto MM/DD/AAAA, no como fecha ISO; "
            "requieren parseo explícito en la limpieza.",
        ],
    }

    return render_profile_markdown(profile, extra_sections="\n".join(extra)), highlights


def build_calidad_agua_report() -> tuple[str, dict]:
    df, manifest = load_calidad_agua_por_lotes()

    # Revalidación de completitud (además de la que ya hace el script de descarga).
    total_manifest = manifest["total_filas_descargadas"]
    assert len(df) == total_manifest, (
        f"Filas concatenadas ({len(df)}) no coinciden con el manifest ({total_manifest})"
    )

    profile = profile_dataframe(
        df,
        fuente="IDEAM - Data Histórica de Calidad de Agua (4 partes concatenadas en memoria)",
        ruta=str(AGUA_DIR.relative_to(PROJECT_ROOT)) + "/ (manifest.json + 4 partes .json)",
        extra_key_columns=["szh_c_digo_rea_zona_subzona", "codigo__muestra"],
    )

    fechas = pd.to_datetime(df["fecha"], errors="coerce", format="mixed")
    n_fechas_invalidas = int(fechas.isna().sum() - df["fecha"].isna().sum())
    anios = sorted(fechas.dropna().dt.year.unique().tolist())

    deptos = sorted(df["departamento"].dropna().unique().tolist())
    municipios_unicos = df["municipio"].dropna().nunique()

    extra = []
    extra.append("## Revalidación de completitud (concatenación en memoria)")
    extra.append("")
    extra.append(f"- `total_filas_origen` (manifest, Socrata `count(*)`): {manifest['total_filas_origen']}")
    extra.append(f"- `total_filas_descargadas` (manifest): {manifest['total_filas_descargadas']}")
    extra.append(f"- Filas tras concatenar las {manifest['numero_partes']} partes en memoria: {len(df)}")
    estado_val = "OK, coinciden" if len(df) == manifest["total_filas_origen"] else "DISCREPANCIA"
    extra.append(f"- Validación: {estado_val}")
    extra.append("- **No se guardó ningún archivo concatenado**: la unión existió solo en memoria durante el perfilamiento.")
    extra.append("")

    extra.append("## Reportes específicos de calidad hídrica")
    extra.append("")
    extra.append(f"- Años disponibles en `fecha` ({len(anios)}): {anios}")
    if n_fechas_invalidas > 0:
        extra.append(f"- **Hallazgo de calidad:** {n_fechas_invalidas} valores de `fecha` no parsean como fecha válida")
    extra.append(f"- Departamentos únicos ({len(deptos)}): {', '.join(deptos)}")
    extra.append(f"- Municipios únicos: {municipios_unicos}")
    extra.append("")
    extra.append(
        value_counts_markdown(
            df["propiedad_observada"], top_n=30, title="Propiedades observadas (top 30 de %d únicas)" % df["propiedad_observada"].nunique()
        )
    )
    extra.append("")

    highlights = {
        "n_filas": len(df),
        "n_anios": len(anios),
        "rango_anios": (anios[0], anios[-1]) if anios else (None, None),
        "n_departamentos": len(deptos),
        "n_municipios": int(municipios_unicos),
        "n_duplicados": profile["n_duplicados"],
        "llave_candidata": "coordenadas (latitud/longitud) + szh_c_digo_rea_zona_subzona (código de subzona hidrográfica) para unir con cuencas; departamento/municipio como texto para unir con DIVIPOLA (requiere normalización, no hay código DANE directo)",
        "hallazgos": [
            f"{profile['n_duplicados']} filas completamente duplicadas.",
            "departamento y municipio vienen como texto en mayúsculas, sin código DANE: "
            "el cruce con DIVIPOLA requerirá normalización de nombres, no un join directo por código.",
            f"propiedad_observada tiene {df['propiedad_observada'].nunique()} valores únicos, "
            "varios con posible redundancia de nomenclatura (mismo parámetro con distinta escritura); "
            "requiere revisión/estandarización antes de análisis agregado.",
        ],
    }

    return render_profile_markdown(profile, extra_sections="\n".join(extra)), highlights


# --------------------------------------------------------------------------
# Orquestación
# --------------------------------------------------------------------------


def main() -> int:
    print("=== AquaBosque Minero IA — Fase 3A: perfilamiento de datos crudos ===\n")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    summary_lines = [
        "# Resumen de perfilamiento de datos crudos (Fase 3A)",
        "",
        "Generado automáticamente por `scripts/02_profile_raw_data.py`. Solo lectura: no se",
        "limpió, transformó ni guardó ningún dataset procesado.",
        "",
    ]

    reports = [
        ("DIVIPOLA - Códigos de municipios (DANE)", "divipola_profile.md", build_divipola_report),
        ("ANM Títulos Mineros - Anotaciones RMN", "mineria_anm_profile.md", build_anm_report),
        ("IDEAM - Data Histórica de Calidad de Agua", "calidad_agua_profile.md", build_calidad_agua_report),
    ]

    all_highlights: dict[str, dict] = {}
    errores: list[str] = []

    for fuente, filename, builder in reports:
        print(f"-> Perfilando: {fuente} ...")
        try:
            content, highlights = builder()
        except Exception as exc:  # noqa: BLE001 - se reporta y se sigue con las demás fuentes
            print(f"   ERROR: {exc}")
            errores.append(f"{fuente}: {exc}")
            continue

        out_path = REPORTS_DIR / filename
        out_path.write_text(content, encoding="utf-8")
        print(f"   OK -> {out_path.relative_to(PROJECT_ROOT)}")
        all_highlights[fuente] = {**highlights, "filename": filename}

    # --- Tabla comparativa ---
    summary_lines.append("## Tabla comparativa")
    summary_lines.append("")
    summary_lines.append("| Fuente | Filas | Duplicados | Reporte |")
    summary_lines.append("|---|---|---|---|")
    for fuente, h in all_highlights.items():
        summary_lines.append(f"| {fuente} | {h['n_filas']} | {h['n_duplicados']} | [`{h['filename']}`](./{h['filename']}) |")
    summary_lines.append("")

    # --- Llaves de integración candidatas por fuente ---
    summary_lines.append("## Llaves de integración candidatas por fuente")
    summary_lines.append("")
    for fuente, h in all_highlights.items():
        summary_lines.append(f"- **{fuente}:** {h['llave_candidata']}")
    summary_lines.append("")

    # --- Hallazgos principales y problemas de calidad ---
    summary_lines.append("## Hallazgos principales y problemas de calidad por fuente")
    summary_lines.append("")
    for fuente, h in all_highlights.items():
        summary_lines.append(f"### {fuente}")
        summary_lines.append("")
        for hallazgo in h["hallazgos"]:
            summary_lines.append(f"- {hallazgo}")
        summary_lines.append("")

    # --- Problema transversal de integración ---
    summary_lines.append("## Problema transversal de integración territorial")
    summary_lines.append("")
    summary_lines.append(
        "Ninguna de las 3 fuentes MVP comparte una llave territorial 100% directa y lista para "
        "usar sin normalización:"
    )
    summary_lines.append("")
    summary_lines.append(
        "- DIVIPOLA tiene el código DANE de municipio limpio conceptualmente, pero el XLSX lo "
        "entrega como número (pierde ceros iniciales)."
    )
    summary_lines.append(
        "- ANM Anotaciones RMN no trae ubicación geográfica en absoluto en este dataset "
        "(el catastro minero geoespacial de la ANM, con DEPARTAMENTOS/MUNICIPIOS de texto, "
        "es una fuente distinta, pendiente de validación desde la Fase 1.5)."
    )
    summary_lines.append(
        "- IDEAM calidad de agua trae departamento/municipio como texto en mayúsculas, sin "
        "código DANE, más coordenadas propias."
    )
    summary_lines.append(
        "- **Conclusión:** integrar estas fuentes por territorio va a requerir normalización de "
        "nombres de municipio/departamento (y probablemente un paso de fuzzy-matching o "
        "diccionario de equivalencias) en vez de un join directo por código DANE."
    )
    summary_lines.append("")

    if errores:
        summary_lines.append("## Errores durante el perfilamiento")
        summary_lines.append("")
        for e in errores:
            summary_lines.append(f"- {e}")
        summary_lines.append("")

    summary_lines.append("## Recomendación para Fase 3B")
    summary_lines.append("")
    summary_lines.append(
        "1. Definir y documentar explícitamente las reglas de limpieza por fuente antes de "
        "escribir código: tipos de dato objetivo (especialmente códigos como texto con "
        "ceros a la izquierda), formato de fecha objetivo (ISO 8601), y manejo de las filas "
        "basura del XLSX de DIVIPOLA (título y notas al pie)."
    )
    summary_lines.append(
        "2. Diseñar la estrategia de normalización de nombres de departamento/municipio "
        "(mayúsculas, tildes, 'BOGOTÁ, D.C.' vs 'BOGOTÁ D.C.', etc.) antes de intentar "
        "cualquier cruce entre calidad de agua/ANM y DIVIPOLA."
    )
    summary_lines.append(
        "3. Decidir cómo tratar `codigo_expediente` de ANM Anotaciones RMN (no es llave única "
        "de fila, es una llave de agrupación 1-a-muchos) y si se necesita agregar a nivel de "
        "expediente antes de integrarlo con otras fuentes."
    )
    summary_lines.append(
        "4. Revisar y, si aplica, estandarizar los ~80 valores de `propiedad_observada` en "
        "calidad de agua antes de cualquier análisis agregado por parámetro."
    )
    summary_lines.append(
        "5. Solo después de estas decisiones, avanzar a la limpieza real (Fase 3B) guardando "
        "salidas en `data/processed/` — todavía no construir dataset maestro ni tocar RUNAP, "
        "SMByC, catastro minero WFS completo ni MGN completo."
    )
    summary_lines.append("")

    summary_path = REPORTS_DIR / "raw_data_profile_summary.md"
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")
    print(f"\nResumen -> {summary_path.relative_to(PROJECT_ROOT)}")

    if errores:
        print(f"\nAtención: {len(errores)} fuente(s) con error durante el perfilamiento.")
        return 1

    print("\nPerfilamiento completo. No se limpiaron ni transformaron datos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
