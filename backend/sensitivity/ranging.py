"""Rangos de factibilidad (lado derecho) y de optimalidad (costos) que no cambian la base óptima."""

import numpy as np

from backend.sensitivity.duals import BaseOptima

_TOL = 1e-9


def rango_lado_derecho(base: BaseOptima, fila: int) -> tuple[float, float]:
    """Valores entre los que puede moverse el lado derecho de una restricción sin cambiar la base.

    Al cambiar bₖ en Δ las variables básicas pasan a x_B + Δ·B⁻¹eₖ; la base sigue
    siendo factible (y los precios sombra válidos) mientras ninguna se vuelva negativa.
    """
    columna = base.B_inv[:, fila]
    positivos, negativos = columna > _TOL, columna < -_TOL
    bajar = np.max(-base.x_base[positivos] / columna[positivos]) if positivos.any() else -np.inf
    subir = np.min(-base.x_base[negativos] / columna[negativos]) if negativos.any() else np.inf
    actual = base.b[fila]
    return max(actual + min(bajar, 0.0), 0.0), actual + max(subir, 0.0)


def rango_costo(base: BaseOptima, columna: int) -> tuple[float, float]:
    """Costos unitarios entre los que la solución óptima (la misma base) se mantiene.

    * Ruta no básica: puede subir sin límite y bajar hasta su costo reducido.
    * Ruta básica en la fila r: al cambiar su costo en δ, el costo reducido de cada
      columna no básica k cambia en −δ·αᵣₖ (αᵣ = fila r de B⁻¹M); debe seguir ≥ 0.
    """
    costo = base.c[columna]
    filas = np.flatnonzero(base.base == columna)
    if filas.size == 0:
        return costo - base.reducidos[columna], np.inf

    alfa = base.B_inv[filas[0]] @ base.M
    no_basicas = np.setdiff1d(np.arange(base.M.shape[1]), base.base)
    a, d = alfa[no_basicas], base.reducidos[no_basicas]
    positivos, negativos = a > _TOL, a < -_TOL
    subir = np.min(d[positivos] / a[positivos]) if positivos.any() else np.inf
    bajar = np.max(d[negativos] / a[negativos]) if negativos.any() else -np.inf
    return costo + min(bajar, 0.0), costo + max(subir, 0.0)
