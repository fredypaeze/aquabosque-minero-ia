"""Fase 3-5 — integración municipal (dataset maestro) + 4 índices y etiqueta técnica."""
import _bootstrap  # noqa: F401
from aquabosque.features.build_master import run as build_master
from aquabosque.features.build_target import run as build_target

if __name__ == "__main__":
    build_master()
    build_target()
