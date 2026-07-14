"""Fase 2 — descarga de fuentes geoespaciales (ArcGIS FeatureServer):
deforestación por municipio y RUNAP (áreas protegidas).
Nota: la calidad de agua (IDEAM DHIME) se entrega ya en data/raw/agua/ica_ideam.csv."""
import _bootstrap  # noqa: F401
from aquabosque.data.download_arcgis import run

if __name__ == "__main__":
    run()
