from dataclasses import dataclass

import numpy as np

from backend.exact.transport_model import ProblemaTransporte
from backend.sensitivity.duals import base_optima, flujos
from backend.sensitivity.ranging import rango_costo, rango_lado_derecho


@dataclass(frozen=True)
class SensibilidadNodo:
    """Empresa (oferta) o planta (demanda)."""
    indice: int
    cantidad: float
    utilizado: float
    holgura: float
    precio_sombra: float
    minimo: float
    maximo: float


@dataclass(frozen=True)
class SensibilidadRuta:
    i: int
    j: int
    flujo: float
    costo: float
    costo_reducido: float
    costo_minimo: float
    costo_maximo: float

    @property
    def usada(self) -> bool:
        return self.flujo > 1e-6


@dataclass
class AnalisisSensibilidad:
    objetivo: float
    empresas: list[SensibilidadNodo]
    plantas: list[SensibilidadNodo]
    rutas: list[SensibilidadRuta]
    degenerada: bool
    oferta_igual: bool


def analizar(problema: ProblemaTransporte) -> AnalisisSensibilidad | None:
    """Precios sombra, holguras y rangos de factibilidad y optimalidad de la solución óptima."""
    base = base_optima(problema)
    if base is None:
        return None
    x = flujos(base)
    enviado, recibido = x.sum(axis=1), x.sum(axis=0)

    empresas = []
    for i in range(base.m):
        fila = base.fila_oferta(i)
        minimo, maximo = rango_lado_derecho(base, fila)
        empresas.append(SensibilidadNodo(i, float(problema.oferta[i]), float(enviado[i]),
                                         float(problema.oferta[i] - enviado[i]), float(base.duales[fila]),
                                         minimo, maximo))
    plantas = []
    for j in range(base.n):
        fila = base.fila_demanda(j)
        minimo, maximo = rango_lado_derecho(base, fila)
        plantas.append(SensibilidadNodo(j, float(problema.demanda[j]), float(recibido[j]),
                                        float(problema.demanda[j] - recibido[j]), float(base.duales[fila]),
                                        minimo, maximo))
    rutas = []
    for columna, (i, j) in enumerate(base.arcos):
        minimo, maximo = rango_costo(base, columna)
        rutas.append(SensibilidadRuta(int(i), int(j), float(x[i, j]), float(base.c[columna]),
                                      float(base.reducidos[columna]), minimo, maximo))
    return AnalisisSensibilidad(float(np.sum(x * np.nan_to_num(problema.costos))), empresas, plantas, rutas,
                                base.degenerada, base.oferta_igual)
