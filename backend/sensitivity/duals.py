"""Precios sombra y costos reducidos a partir de la base óptima del Simplex.

Se usa la formulación de la Fase 1 sin nodos ficticios:

* oferta igual o menor que la demanda total: Σⱼ xᵢⱼ = Oᵢ y Σᵢ xᵢⱼ ≤ Dⱼ;
* oferta mayor que la demanda: Σⱼ xᵢⱼ ≤ Oᵢ y Σᵢ xᵢⱼ = Dⱼ (las plantas se llenan).

En forma estándar cada desigualdad lleva su holgura, M = [[A_igual, 0], [A_menor, I]].
Con la base óptima B (columnas de M) se obtienen B⁻¹, los duales y = c_B B⁻¹
y los costos reducidos d = c − y M, que son la base del análisis.
"""

from dataclasses import dataclass

import numpy as np

from backend.exact.simplex import EstadoSolucion, Simplex
from backend.exact.transport_model import ProblemaTransporte
from backend.network.balance import TipoBalance, verificar_balance


@dataclass
class BaseOptima:
    M: np.ndarray
    b: np.ndarray
    c: np.ndarray                 # costos de todas las columnas (arcos y holguras)
    base: np.ndarray
    B_inv: np.ndarray
    duales: np.ndarray            # uno por restricción: primero las m de oferta, luego las n de demanda
    reducidos: np.ndarray         # uno por columna
    x_base: np.ndarray
    arcos: np.ndarray             # (i, j) de cada columna de flujo
    m: int
    n: int
    oferta_igual: bool            # True: oferta "="; False: oferta "≤" y demanda "="

    @property
    def num_arcos(self) -> int:
        return len(self.arcos)

    @property
    def degenerada(self) -> bool:
        return bool(np.any(np.abs(self.x_base) < 1e-7))

    def fila_oferta(self, i: int) -> int:
        return i

    def fila_demanda(self, j: int) -> int:
        return self.m + j


def base_optima(problema: ProblemaTransporte) -> BaseOptima | None:
    """Resuelve la formulación natural y arma B⁻¹; None si no hay óptimo o la base no es cuadrada."""
    m, n = problema.dimension
    costos = np.nan_to_num(problema.costos)
    arcos = np.argwhere(problema.habilitadas)
    k = len(arcos)
    filas, columnas, indice = arcos[:, 0], arcos[:, 1], np.arange(k)

    A_oferta = np.zeros((m, k))
    A_oferta[filas, indice] = 1.0
    A_demanda = np.zeros((n, k))
    A_demanda[columnas, indice] = 1.0
    c_arcos = costos[filas, columnas]
    exceso_oferta = verificar_balance(problema.oferta, problema.demanda).tipo is TipoBalance.EXCESO_OFERTA

    if exceso_oferta:
        A_igual, b_igual, A_menor, b_menor = A_demanda, problema.demanda, A_oferta, problema.oferta
    else:
        A_igual, b_igual, A_menor, b_menor = A_oferta, problema.oferta, A_demanda, problema.demanda
    resultado = Simplex().resolver(c_arcos, A_igual, b_igual, A_menor, b_menor)
    if resultado.estado is not EstadoSolucion.OPTIMO or resultado.base is None:
        return None

    filas_igual, filas_menor = len(b_igual), len(b_menor)
    M_simplex = np.block([[A_igual, np.zeros((filas_igual, filas_menor))],
                          [A_menor, np.eye(filas_menor)]])
    b_simplex = np.concatenate([b_igual, b_menor])
    if len(resultado.base) != M_simplex.shape[0]:
        return None

    # Reordena las filas para que siempre queden primero las de oferta y luego las de demanda.
    orden = np.r_[filas_igual:filas_igual + filas_menor, 0:filas_igual] if exceso_oferta \
        else np.arange(filas_igual + filas_menor)
    M, b = M_simplex[orden], b_simplex[orden]
    c = np.concatenate([c_arcos, np.zeros(filas_menor)])
    base = np.asarray(resultado.base)

    try:
        B_inv = np.linalg.inv(M[:, base])
    except np.linalg.LinAlgError:
        return None
    duales = c[base] @ B_inv
    reducidos = c - duales @ M
    reducidos[np.abs(reducidos) < 1e-7] = 0.0
    x_base = B_inv @ b
    return BaseOptima(M, b, c, base, B_inv, duales, reducidos, x_base, arcos, m, n,
                      oferta_igual=not exceso_oferta)


def flujos(base: BaseOptima) -> np.ndarray:
    x = np.zeros((base.m, base.n))
    for fila, columna in enumerate(base.base):
        if columna < base.num_arcos:
            i, j = base.arcos[columna]
            x[i, j] = max(base.x_base[fila], 0.0)
    return x


def costos_reducidos(base: BaseOptima) -> np.ndarray:
    """Matriz m × n; NaN en las rutas deshabilitadas."""
    d = np.full((base.m, base.n), np.nan)
    d[base.arcos[:, 0], base.arcos[:, 1]] = base.reducidos[:base.num_arcos]
    return d
