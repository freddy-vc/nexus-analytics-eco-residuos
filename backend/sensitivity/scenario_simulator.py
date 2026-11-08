"""Simulación de variaciones porcentuales de un parámetro del modelo."""

from dataclasses import dataclass
from typing import Callable

import numpy as np

from backend.exact.simplex import EstadoSolucion
from backend.exact.transport_model import ModeloTransporte, ProblemaTransporte
from backend.genetic.genetic_algorithm import AlgoritmoGenetico, ParametrosAG
from backend.network.balance import TipoBalance, verificar_balance
from backend.network.cost_matrix import costos_unitarios

ALFA = "ALFA"
OFERTA = "OFERTA"
DEMANDA = "DEMANDA"
COSTO_OPERACION = "COSTO_OPERACION"
MAX_PUNTOS = 21


@dataclass(frozen=True)
class DatosModelo:
    """Datos de entrada del modelo, independientes de la base de datos."""
    oferta: np.ndarray
    demanda: np.ndarray
    distancias: np.ndarray
    costos_operacion: np.ndarray
    precios_compra: np.ndarray
    alfa: float
    habilitadas: np.ndarray


@dataclass
class PuntoSimulacion:
    variacion_pct: float
    costo_exacto: float | None
    milisegundos_exacto: float
    costo_ag: float | None
    milisegundos_ag: float | None
    ag_factible: bool | None
    balance: TipoBalance
    cambia_plan: bool

    @property
    def gap(self) -> float | None:
        if self.costo_exacto and self.costo_ag is not None:
            return (self.costo_ag - self.costo_exacto) / self.costo_exacto * 100
        return None


def variaciones(minimo: float, maximo: float, paso: float) -> list[float]:
    if paso <= 0 or minimo >= maximo:
        raise ValueError("La variación mínima debe ser menor que la máxima y el paso mayor que 0.")
    valores = np.round(np.arange(minimo, maximo + paso / 2, paso), 6)
    if valores.size > MAX_PUNTOS:
        raise ValueError(f"La simulación admite hasta {MAX_PUNTOS} puntos; aumente el paso.")
    return [float(v) for v in valores if v > -100]


def problema_variado(datos: DatosModelo, tipo: str, indice: int | None, variacion_pct: float) -> ProblemaTransporte:
    """Problema de transporte con el parámetro elegido multiplicado por (1 + variación %)."""
    factor = 1 + variacion_pct / 100
    oferta, demanda = datos.oferta.astype(float).copy(), datos.demanda.astype(float).copy()
    operacion, alfa = datos.costos_operacion.astype(float).copy(), datos.alfa
    if tipo == ALFA:
        alfa *= factor
    elif tipo == OFERTA:
        oferta[slice(None) if indice is None else indice] *= factor
    elif tipo == DEMANDA:
        demanda[slice(None) if indice is None else indice] *= factor
    elif tipo == COSTO_OPERACION:
        operacion[slice(None) if indice is None else indice] *= factor
    costos = costos_unitarios(alfa, np.nan_to_num(datos.distancias), operacion, datos.precios_compra)
    return ProblemaTransporte(oferta, demanda, costos, datos.habilitadas.copy())


def simular(datos: DatosModelo, tipo: str, indice: int | None, valores: list[float],
            parametros_ag: ParametrosAG | None = None,
            al_avanzar: Callable[[int, int], None] | None = None) -> list[PuntoSimulacion]:
    """Resuelve el método exacto (y opcionalmente el AG) en cada punto de la variación.

    `cambia_plan` indica si el conjunto de rutas usadas difiere del de la
    solución sin variación: allí la solución deja de tener la misma estructura.
    """
    referencia = _rutas_usadas(ModeloTransporte(problema_variado(datos, tipo, indice, 0.0)).resolver())
    puntos = []
    for k, variacion in enumerate(valores, start=1):
        problema = problema_variado(datos, tipo, indice, variacion)
        exacta = ModeloTransporte(problema).resolver()
        optima = exacta.estado is EstadoSolucion.OPTIMO
        punto = PuntoSimulacion(
            variacion_pct=variacion, costo_exacto=exacta.objetivo if optima else None,
            milisegundos_exacto=exacta.milisegundos, costo_ag=None, milisegundos_ag=None, ag_factible=None,
            balance=verificar_balance(problema.oferta, problema.demanda).tipo,
            cambia_plan=optima and referencia is not None and _rutas_usadas(exacta) != referencia)
        if parametros_ag is not None and optima:
            ag = AlgoritmoGenetico(problema, parametros_ag).ejecutar()
            punto.costo_ag, punto.milisegundos_ag, punto.ag_factible = ag.costo, ag.milisegundos, ag.es_factible
        puntos.append(punto)
        if al_avanzar:
            al_avanzar(k, len(valores))
    return puntos


def _rutas_usadas(solucion) -> frozenset | None:
    if solucion.flujos is None:
        return None
    return frozenset(map(tuple, np.argwhere(solucion.flujos > 1e-6)))
