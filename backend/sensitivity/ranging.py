import numpy as np

from backend.sensitivity.duals import BaseOptima

_TOL = 1e-9


# Intervalo del lado derecho de una restricción en el que la base sigue siendo óptima.
def rango_lado_derecho(base: BaseOptima, fila: int) -> tuple[float, float]:
    # Al variar b_k en Δ: x_B(Δ) = x_B + Δ · B⁻¹e_k, que debe seguir siendo ≥ 0.
    columna = base.B_inv[:, fila]
    positivos, negativos = columna > _TOL, columna < -_TOL
    bajar = np.max(-base.x_base[positivos] / columna[positivos]) if positivos.any() else -np.inf
    subir = np.min(-base.x_base[negativos] / columna[negativos]) if negativos.any() else np.inf
    actual = base.b[fila]
    return max(actual + min(bajar, 0.0), 0.0), actual + max(subir, 0.0)


# Intervalo del costo de una ruta en el que la solución óptima no cambia.
def rango_costo(base: BaseOptima, columna: int) -> tuple[float, float]:
    costo = base.c[columna]
    filas = np.flatnonzero(base.base == columna)
    # Ruta no básica: puede bajar hasta su costo reducido y subir sin límite.
    if filas.size == 0:
        return costo - base.reducidos[columna], np.inf

    # Ruta básica: d_k − δ · α_rk ≥ 0 en toda columna no básica k.
    alfa = base.B_inv[filas[0]] @ base.M
    no_basicas = np.setdiff1d(np.arange(base.M.shape[1]), base.base)
    a, d = alfa[no_basicas], base.reducidos[no_basicas]
    positivos, negativos = a > _TOL, a < -_TOL
    subir = np.min(d[positivos] / a[positivos]) if positivos.any() else np.inf
    bajar = np.max(d[negativos] / a[negativos]) if negativos.any() else -np.inf
    return costo + min(bajar, 0.0), costo + max(subir, 0.0)
