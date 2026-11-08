from dataclasses import dataclass

import numpy as np

from backend.exact.simplex import EstadoSolucion, Simplex
from backend.network.balance import EstadoBalance, balancear_problema, verificar_balance
from backend.utils.timer import Cronometro


@dataclass(frozen=True)
class ProblemaTransporte:
    oferta: np.ndarray
    demanda: np.ndarray
    costos: np.ndarray
    habilitadas: np.ndarray

    @property
    def dimension(self) -> tuple[int, int]:
        return self.costos.shape


@dataclass
class SolucionTransporte:
    estado: EstadoSolucion
    flujos: np.ndarray | None
    objetivo: float | None
    iteraciones: int
    milisegundos: float
    balance: EstadoBalance
    sin_enviar: np.ndarray | None
    capacidad_ociosa: np.ndarray | None
    num_variables: int
    num_restricciones: int


class ModeloTransporte:
    """Modelo de transporte de la Fase 1 resuelto con el método Simplex.

        min Z = Σᵢ Σⱼ cᵢⱼ xᵢⱼ
        s.a. Σⱼ xᵢⱼ = Oᵢ   (oferta)
             Σᵢ xᵢⱼ ≤ Dⱼ   (demanda)
             xᵢⱼ ≥ 0

    Solo se crean variables para las rutas habilitadas, de modo que el tamaño
    del programa lineal crece con los arcos reales de la red (RNF02).
    """

    def __init__(self, problema: ProblemaTransporte, simplex: Simplex | None = None):
        self.problema = problema
        self.simplex = simplex or Simplex()

    def resolver(self) -> SolucionTransporte:
        p = self.problema
        m, n = p.dimension
        balance = verificar_balance(p.oferta, p.demanda)
        balanceado = balancear_problema(p.oferta, p.demanda, p.costos, p.habilitadas)

        arcos = np.argwhere(balanceado.habilitadas)
        c, A_igual, b_igual, A_menor, b_menor = self._programa_lineal(balanceado, arcos)

        with Cronometro() as cronometro:
            resultado = self.simplex.resolver(c, A_igual, b_igual, A_menor, b_menor)

        solucion = SolucionTransporte(
            estado=resultado.estado, flujos=None, objetivo=None,
            iteraciones=resultado.iteraciones, milisegundos=cronometro.milisegundos,
            balance=balance, sin_enviar=None, capacidad_ociosa=None,
            num_variables=int(p.habilitadas.sum()), num_restricciones=m + n)
        if resultado.estado is not EstadoSolucion.OPTIMO:
            return solucion

        completo = np.zeros(balanceado.costos.shape)
        completo[arcos[:, 0], arcos[:, 1]] = resultado.x
        solucion.flujos = completo[:m, :n]
        solucion.objetivo = float(np.sum(solucion.flujos * np.nan_to_num(p.costos)))
        if balanceado.destino_ficticio:
            solucion.sin_enviar = completo[:m, n]
        if balanceado.origen_ficticio:
            solucion.capacidad_ociosa = completo[m, :n]
        return solucion

    @staticmethod
    def _programa_lineal(balanceado, arcos):
        num_arcos = len(arcos)
        filas, columnas = arcos[:, 0], arcos[:, 1]
        indice = np.arange(num_arcos)

        A_igual = np.zeros((len(balanceado.oferta), num_arcos))
        A_igual[filas, indice] = 1.0
        A_menor = np.zeros((len(balanceado.demanda), num_arcos))
        A_menor[columnas, indice] = 1.0
        c = balanceado.costos[filas, columnas]
        return c, A_igual, balanceado.oferta, A_menor, balanceado.demanda
