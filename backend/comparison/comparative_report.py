"""Contenido del reporte comparativo, independiente del formato de salida."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Tabla:
    columnas: list[str]
    filas: list[list[str]]
    alineacion: list[str] | None = None   # "i" izquierda o "d" derecha por columna


@dataclass
class Seccion:
    titulo: str
    parrafos: list[str] = field(default_factory=list)
    tablas: list[Tabla] = field(default_factory=list)


@dataclass
class Reporte:
    titulo: str
    subtitulo: str
    generado_en: datetime
    secciones: list[Seccion]
