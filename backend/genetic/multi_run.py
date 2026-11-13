from dataclasses import dataclass, replace
from typing import Callable

import numpy as np

from backend.exact.transport_model import ProblemaTransporte
from backend.genetic.genetic_algorithm import AlgoritmoGenetico, ParametrosAG, ResultadoAG


@dataclass
class Estadisticas:
    corridas: int
    mejor: float
    promedio: float
    desviacion: float
    peor: float
    tiempo_promedio_ms: float
    indice_mejor: int
    factibles: int


# Ejecuta N corridas independientes con semillas consecutivas.
def ejecutar_corridas(problema: ProblemaTransporte, parametros: ParametrosAG, corridas: int,
                      al_avanzar: Callable[[int, int, int, int], None] | None = None) -> list[ResultadoAG]:
    resultados = []
    # Las corridas usan las semillas s, s + 1, …, s + N − 1.
    base = parametros.semilla if parametros.semilla is not None else int(np.random.SeedSequence().entropy % 2**31)
    for k in range(corridas):
        avance = (lambda g, total, k=k: al_avanzar(k + 1, corridas, g, total)) if al_avanzar else None
        resultados.append(AlgoritmoGenetico(problema, replace(parametros, semilla=base + k)).ejecutar(avance))
    return resultados


# Mejor, promedio, desviación, peor y tiempo medio de un lote de corridas.
def estadisticas(costos: list[float], tiempos_ms: list[float], factibles: list[bool]) -> Estadisticas:
    valores = np.array(costos, float)
    candidatos = np.flatnonzero(factibles) if any(factibles) else np.arange(valores.size)
    indice = int(candidatos[np.argmin(valores[candidatos])])
    # Desviación estándar muestral (ddof = 1).
    return Estadisticas(
        corridas=valores.size, mejor=float(valores[indice]), promedio=float(valores.mean()),
        desviacion=float(valores.std(ddof=1)) if valores.size > 1 else 0.0, peor=float(valores.max()),
        tiempo_promedio_ms=float(np.mean(tiempos_ms)), indice_mejor=indice, factibles=int(sum(factibles)))
