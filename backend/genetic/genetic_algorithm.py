from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from backend.exact.transport_model import ProblemaTransporte
from backend.genetic.chromosome import poblacion_inicial, reparar_capacidad, reparar_oferta
from backend.genetic.crossover import DOS_PUNTOS, cruzar
from backend.genetic.fitness import evaluar
from backend.genetic.mutation import mutar
from backend.genetic.selection import TORNEO, seleccionar
from backend.network.balance import balancear_problema
from backend.utils.timer import Cronometro


@dataclass(frozen=True)
class ParametrosAG:
    tamano_poblacion: int = 100
    num_generaciones: int = 300
    tasa_cruce: float = 0.85
    tasa_mutacion: float = 0.05
    seleccion: str = TORNEO
    tamano_torneo: int = 3
    cruce: str = DOS_PUNTOS
    elitismo: int = 2
    penalizacion: float = 1_000_000.0
    semilla: int | None = 42

    # Mensajes de error de los parámetros fuera de rango.
    def validar(self) -> list[str]:
        errores = []
        if self.tamano_poblacion < 2:
            errores.append("La población debe tener al menos 2 individuos.")
        if self.num_generaciones < 1:
            errores.append("Debe haber al menos 1 generación.")
        if not 0 <= self.tasa_cruce <= 1 or not 0 <= self.tasa_mutacion <= 1:
            errores.append("Las tasas de cruce y mutación deben estar entre 0 y 1.")
        if self.elitismo < 0 or self.elitismo >= self.tamano_poblacion:
            errores.append("El elitismo debe ser menor que el tamaño de la población.")
        if self.penalizacion <= 0:
            errores.append("La penalización debe ser mayor que 0.")
        return errores


@dataclass
class Generacion:
    numero: int
    mejor_costo: float
    costo_promedio: float
    mejor_aptitud: float
    plantas_excedidas: int


@dataclass
class ResultadoAG:
    flujos: np.ndarray
    costo: float
    exceso: float
    plantas_excedidas: int
    milisegundos: float
    semilla: int | None
    historial: list[Generacion] = field(default_factory=list)
    sin_enviar: np.ndarray | None = None
    capacidad_ociosa: np.ndarray | None = None

    # La solución es factible si no excede la capacidad de ninguna planta.
    @property
    def es_factible(self) -> bool:
        return self.exceso <= 1e-6


# Algoritmo genético para el problema de transporte.
class AlgoritmoGenetico:
    # Recibe el problema y los parámetros de la corrida.
    def __init__(self, problema: ProblemaTransporte, parametros: ParametrosAG):
        self.problema = problema
        self.parametros = parametros

    # Máscara de las celdas que pertenecen al nodo ficticio.
    @staticmethod
    def _celdas_ficticias(bal, m: int, n: int) -> np.ndarray:
        ficticias = np.zeros(bal.costos.shape, bool)
        ficticias[m:, :] = True
        ficticias[:, n:] = True
        return ficticias

    # Ejecuta una corrida completa del AG y devuelve la mejor solución y su historial.
    def ejecutar(self, al_avanzar: Callable[[int, int], None] | None = None) -> ResultadoAG:
        p = self.parametros
        m, n = self.problema.dimension
        # Mismo problema balanceado que resuelve el método exacto.
        bal = balancear_problema(self.problema.oferta, self.problema.demanda,
                                 np.nan_to_num(self.problema.costos), self.problema.habilitadas)
        oferta, demanda, costos, habilitadas = bal.oferta, bal.demanda, bal.costos, bal.habilitadas
        # Un único generador inicializado con la semilla hace reproducible la corrida.
        rng = np.random.default_rng(p.semilla)
        historial: list[Generacion] = []

        with Cronometro() as cronometro:
            poblacion = reparar_oferta(
                poblacion_inicial(oferta, demanda, costos, habilitadas, p.tamano_poblacion, rng,
                                  ficticias=self._celdas_ficticias(bal, m, n)),
                oferta, habilitadas)
            evaluacion = evaluar(poblacion, costos, demanda, p.penalizacion)
            mejor = poblacion[np.argmax(evaluacion.aptitud)].copy()
            mejor_aptitud = float(evaluacion.aptitud.max())

            for generacion in range(1, p.num_generaciones + 1):
                orden = np.argsort(-evaluacion.aptitud)
                # Elitismo: los e mejores individuos pasan intactos.
                elite = poblacion[orden[:p.elitismo]]

                faltan = p.tamano_poblacion - p.elitismo
                # q = ⌈(P − e) / 2⌉ parejas de padres.
                pares = (faltan + 1) // 2
                padres = seleccionar(evaluacion.aptitud, 2 * pares, p.seleccion, p.tamano_torneo, rng)
                hijo_a, hijo_b = cruzar(poblacion[padres[:pares]], poblacion[padres[pares:]],
                                        p.tasa_cruce, p.cruce, rng)
                hijos = np.concatenate([hijo_a, hijo_b])[:faltan]
                hijos = mutar(hijos, p.tasa_mutacion, costos, demanda, habilitadas, rng)
                # Reemplazo generacional con la oferta reparada.
                poblacion = reparar_oferta(np.concatenate([elite, hijos]), oferta, habilitadas)

                evaluacion = evaluar(poblacion, costos, demanda, p.penalizacion)
                indice = int(np.argmax(evaluacion.aptitud))
                # Se conserva la mejor solución de toda la corrida.
                if evaluacion.aptitud[indice] > mejor_aptitud:
                    mejor_aptitud = float(evaluacion.aptitud[indice])
                    mejor = poblacion[indice].copy()
                historial.append(Generacion(generacion, float(evaluacion.costo[indice]),
                                            float(evaluacion.costo.mean()), float(evaluacion.aptitud[indice]),
                                            int(evaluacion.plantas_excedidas[indice])))
                if al_avanzar and (generacion % 10 == 0 or generacion == p.num_generaciones):
                    al_avanzar(generacion, p.num_generaciones)

        # Limpieza final de los excesos residuales de capacidad.
        mejor = reparar_capacidad(mejor, demanda, costos, habilitadas)
        final = evaluar(mejor[None], costos, demanda, p.penalizacion)
        resultado = ResultadoAG(
            flujos=mejor[:m, :n], costo=float(np.sum(mejor[:m, :n] * np.nan_to_num(self.problema.costos))),
            exceso=float(final.exceso[0]), plantas_excedidas=int(final.plantas_excedidas[0]),
            milisegundos=cronometro.milisegundos, semilla=p.semilla, historial=historial)
        if bal.destino_ficticio:
            resultado.sin_enviar = mejor[:m, n]
        if bal.origen_ficticio:
            resultado.capacidad_ociosa = mejor[m, :n]
        return resultado
