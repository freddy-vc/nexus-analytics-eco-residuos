from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Tabla:
    columnas: list[str]
    filas: list[list[str]]
    # Alineación por columna: «i» izquierda o «d» derecha.
    alineacion: list[str] | None = None


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
