from dataclasses import dataclass

import numpy as np

from backend.exact.simplex import EstadoSolucion, Simplex
from backend.exact.transport_model import ProblemaTransporte
from backend.network.balance import TipoBalance, verificar_balance


@dataclass
class BaseOptima:
    M: np.ndarray
    b: np.ndarray
    c: np.ndarray
    base: np.ndarray
    B_inv: np.ndarray
    # Precios sombra: primero los de oferta y luego los de demanda.
    duales: np.ndarray
    reducidos: np.ndarray
    x_base: np.ndarray
    arcos: np.ndarray
    m: int
    n: int
    # True si la igualdad está en la oferta; False si está en la demanda.
    oferta_igual: bool

    # Número de columnas de flujo del programa lineal.
    @property
    def num_arcos(self) -> int:
        return len(self.arcos)

    # La solución es degenerada si alguna variable básica vale cero.
    @property
    def degenerada(self) -> bool:
        return bool(np.any(np.abs(self.x_base) < 1e-7))

    # Fila de la restricción de oferta de la empresa i.
    def fila_oferta(self, i: int) -> int:
        return i

    # Fila de la restricción de demanda de la planta j.
    def fila_demanda(self, j: int) -> int:
        return self.m + j


# Resuelve la formulación sin nodos ficticios y obtiene la base óptima con su inversa.
def base_optima(problema: ProblemaTransporte) -> BaseOptima | None:
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

    # Con exceso de oferta la igualdad pasa a la demanda: Σ_i x_ij = D_j y Σ_j x_ij ≤ O_i.
    if exceso_oferta:
        A_igual, b_igual, A_menor, b_menor = A_demanda, problema.demanda, A_oferta, problema.oferta
    else:
        A_igual, b_igual, A_menor, b_menor = A_oferta, problema.oferta, A_demanda, problema.demanda
    resultado = Simplex().resolver(c_arcos, A_igual, b_igual, A_menor, b_menor)
    if resultado.estado is not EstadoSolucion.OPTIMO or resultado.base is None:
        return None

    filas_igual, filas_menor = len(b_igual), len(b_menor)
    # Forma estándar: M = [A_igual 0; A_menor I], con una holgura por desigualdad.
    M_simplex = np.block([[A_igual, np.zeros((filas_igual, filas_menor))],
                          [A_menor, np.eye(filas_menor)]])
    b_simplex = np.concatenate([b_igual, b_menor])
    if len(resultado.base) != M_simplex.shape[0]:
        return None

    # Las filas quedan siempre en el orden oferta y luego demanda.
    orden = np.r_[filas_igual:filas_igual + filas_menor, 0:filas_igual] if exceso_oferta \
        else np.arange(filas_igual + filas_menor)
    M, b = M_simplex[orden], b_simplex[orden]
    c = np.concatenate([c_arcos, np.zeros(filas_menor)])
    base = np.asarray(resultado.base)

    try:
        B_inv = np.linalg.inv(M[:, base])
    except np.linalg.LinAlgError:
        return None
    # Precios sombra: y = c_B · B⁻¹
    duales = c[base] @ B_inv
    # Costos reducidos: d = c − y · M
    reducidos = c - duales @ M
    reducidos[np.abs(reducidos) < 1e-7] = 0.0
    x_base = B_inv @ b
    return BaseOptima(M, b, c, base, B_inv, duales, reducidos, x_base, arcos, m, n,
                      oferta_igual=not exceso_oferta)


# Matriz de flujos a partir de las variables básicas.
def flujos(base: BaseOptima) -> np.ndarray:
    x = np.zeros((base.m, base.n))
    for fila, columna in enumerate(base.base):
        if columna < base.num_arcos:
            i, j = base.arcos[columna]
            x[i, j] = max(base.x_base[fila], 0.0)
    return x
