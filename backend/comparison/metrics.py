"""Métricas de la comparación entre el método exacto y el algoritmo genético."""

from dataclasses import dataclass

import numpy as np

from backend.exact.transport_model import ModeloTransporte, ProblemaTransporte
from backend.genetic.genetic_algorithm import AlgoritmoGenetico, ParametrosAG


def gap(costo_ag: float | None, costo_exacto: float | None) -> float | None:
    """Desviación porcentual del AG frente al óptimo exacto."""
    if costo_ag is None or not costo_exacto:
        return None
    return (costo_ag - costo_exacto) / costo_exacto * 100


@dataclass(frozen=True)
class MedicionEscala:
    empresas: int
    plantas: int
    milisegundos_exacto: float
    milisegundos_ag: float
    gap: float | None
    ag_factible: bool


def instancia_aleatoria(empresas: int, plantas: int, semilla: int) -> ProblemaTransporte:
    """Problema balanceado de prueba con costos del mismo orden que el caso base (COP/t)."""
    rng = np.random.default_rng(semilla)
    oferta = rng.integers(50, 200, empresas).astype(float)
    demanda = rng.multinomial(int(oferta.sum()), np.ones(plantas) / plantas).astype(float)
    costos = rng.uniform(50_000, 270_000, (empresas, plantas))
    return ProblemaTransporte(oferta, demanda, costos, np.ones((empresas, plantas), bool))


def medir_escalabilidad(tamanos: list[tuple[int, int]], parametros: ParametrosAG,
                        semilla: int = 2026) -> list[MedicionEscala]:
    mediciones = []
    for k, (empresas, plantas) in enumerate(tamanos):
        problema = instancia_aleatoria(empresas, plantas, semilla + k)
        exacta = ModeloTransporte(problema).resolver()
        ag = AlgoritmoGenetico(problema, parametros).ejecutar()
        mediciones.append(MedicionEscala(empresas, plantas, exacta.milisegundos, ag.milisegundos,
                                         gap(ag.costo, exacta.objetivo), ag.es_factible))
    return mediciones
