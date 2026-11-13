from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DesgloseCosto:
    transporte: float
    operacion: float
    compra: float

    # Costo total del plan.
    @property
    def total(self) -> float:
        return self.transporte + self.operacion + self.compra


# Costo de transporte por tonelada-kilómetro ajustado por el factor del escenario.
def alfa_efectivo(alfa: float, factor_pct: float) -> float:
    return alfa * factor_pct / 100


# Factor porcentual que produce el costo de transporte indicado.
def factor_desde_costo(costo_transporte: float, alfa_base: float) -> float:
    return round(costo_transporte / alfa_base * 100, 6)


# Matriz de costos unitarios por tonelada de cada ruta.
def costos_unitarios(alfa: float, distancias: np.ndarray, costos_operacion: np.ndarray,
                     precios_compra: np.ndarray) -> np.ndarray:
    # c_ij = α · d_ij + p_j + β_i
    return (alfa * np.asarray(distancias, float)
            + np.asarray(costos_operacion, float)[None, :]
            + np.asarray(precios_compra, float)[:, None])


# Separa el costo total en transporte, operación y compra.
def desglose_costo(alfa: float, distancias: np.ndarray, costos_operacion: np.ndarray,
                   precios_compra: np.ndarray, flujos: np.ndarray) -> DesgloseCosto:
    flujos = np.asarray(flujos, float)
    # Z = Σ α·d_ij·x_ij + Σ p_j·x_ij + Σ β_i·x_ij
    transporte = float(np.sum(alfa * np.nan_to_num(distancias) * flujos))
    operacion = float(np.sum(flujos * np.asarray(costos_operacion, float)[None, :]))
    compra = float(np.sum(flujos * np.asarray(precios_compra, float)[:, None]))
    return DesgloseCosto(transporte, operacion, compra)
