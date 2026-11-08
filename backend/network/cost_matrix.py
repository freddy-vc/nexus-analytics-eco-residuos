from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DesgloseCosto:
    transporte: float
    operacion: float
    compra: float

    @property
    def total(self) -> float:
        return self.transporte + self.operacion + self.compra


def alfa_efectivo(alfa: float, factor_pct: float) -> float:
    """Costo de transporte por t·km escalado por el factor del escenario (100 % = sin cambio)."""
    return alfa * factor_pct / 100


def factor_desde_costo(costo_transporte: float, alfa_base: float) -> float:
    """Porcentaje del costo base que produce el costo de transporte indicado."""
    return round(costo_transporte / alfa_base * 100, 6)


def costos_unitarios(alfa: float, distancias: np.ndarray, costos_operacion: np.ndarray,
                     precios_compra: np.ndarray) -> np.ndarray:
    """cᵢⱼ = α · dᵢⱼ + pⱼ + βᵢ"""
    return (alfa * np.asarray(distancias, float)
            + np.asarray(costos_operacion, float)[None, :]
            + np.asarray(precios_compra, float)[:, None])


def desglose_costo(alfa: float, distancias: np.ndarray, costos_operacion: np.ndarray,
                   precios_compra: np.ndarray, flujos: np.ndarray) -> DesgloseCosto:
    """Separa Z en transporte (α·d·x), operación (p·x) y compra (β·x)."""
    flujos = np.asarray(flujos, float)
    transporte = float(np.sum(alfa * np.nan_to_num(distancias) * flujos))
    operacion = float(np.sum(flujos * np.asarray(costos_operacion, float)[None, :]))
    compra = float(np.sum(flujos * np.asarray(precios_compra, float)[:, None]))
    return DesgloseCosto(transporte, operacion, compra)
