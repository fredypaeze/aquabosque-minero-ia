"""Perfilado de calidad de datos con ydata-profiling (sucesor de pandas-profiling).

Genera un informe HTML por dataset clave del proyecto y un resumen JSON
compacto (alertas, faltantes, duplicados) apto para versionar.

Uso (requiere un entorno con ydata-profiling; NO está en requirements.txt
del producto porque es herramienta de auditoría, no de runtime):

    python scripts/12_perfilado_datos.py [--minimal]

Salidas en outputs/perfilado/ (los HTML no se versionan por tamaño; el
resumen JSON sí).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "perfilado"

# (ruta, título, minimal) — minimal=True acelera datasets grandes
DATASETS = [
    ("data/processed/master_municipal.csv",
     "AquaBosque · Tabla maestra municipal (insumo, 1.122 municipios)", False),
    ("data/processed/master_con_etiqueta.csv",
     "AquaBosque · Tabla de modelado (insumo + etiqueta compuesta)", False),
    ("outputs/tables/predicciones.csv",
     "AquaBosque · Predicciones del modelo nacional", False),
    ("data/processed/fuego_municipal.csv",
     "AquaBosque · Señal de fuego NASA FIRMS (NRT, 7 días)", False),
    ("data/processed/area_quemada_municipal.csv",
     "AquaBosque · Área quemada medida (Sentinel-2 dNBR)", False),
    ("outputs/rc_v1/gold_localidad_dia.csv",
     "Zoom Bogotá · Dataset dorado localidad-día", True),
]


def perfilar(path: str, titulo: str, minimal: bool) -> dict:
    from ydata_profiling import ProfileReport

    f = ROOT / path
    if not f.exists():
        return {"dataset": path, "estado": "NO_ENCONTRADO"}
    df = pd.read_csv(f)
    rep = ProfileReport(df, title=titulo, minimal=minimal, progress_bar=False)
    html = OUT / (Path(path).stem + "_perfil.html")
    rep.to_file(html)

    d = rep.description_set
    tabla = d.table if isinstance(d.table, dict) else {}
    alertas = [str(a) for a in getattr(d, "alerts", [])]
    return {
        "dataset": path,
        "titulo": titulo,
        "estado": "OK",
        "filas": int(tabla.get("n", len(df))),
        "variables": int(tabla.get("n_var", df.shape[1])),
        "celdas_faltantes_pct": round(100 * float(tabla.get("p_cells_missing", 0.0)), 2),
        "filas_duplicadas": int(tabla.get("n_duplicates", 0)),
        "n_alertas": len(alertas),
        "alertas": alertas,
        "informe_html": html.name,
        "modo": "minimal" if minimal else "completo",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--minimal", action="store_true",
                    help="fuerza modo minimal en todos los datasets")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    resumen = []
    for path, titulo, minimal in DATASETS:
        print(f"→ {path}")
        resumen.append(perfilar(path, titulo, minimal or args.minimal))

    salida = OUT / "resumen_perfilado.json"
    salida.write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nResumen: {salida}")
    for r in resumen:
        if r["estado"] == "OK":
            print(f"  {r['dataset']}: {r['filas']} filas · {r['variables']} vars · "
                  f"faltantes {r['celdas_faltantes_pct']}% · dup {r['filas_duplicadas']} · "
                  f"alertas {r['n_alertas']}")


if __name__ == "__main__":
    main()
