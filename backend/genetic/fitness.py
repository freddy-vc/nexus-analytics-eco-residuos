from dataclasses import dataclass

import numpy as np


@dataclass
class Evaluacion:
    costo: np.ndarray
    exceso: np.ndarray
    plantas_excedidas: np.ndarray
    aptitud: np.ndarray


# Calcula costo, exceso de capacidad y aptitud penalizada de toda la población.
def evaluar(poblacion: np.ndarray, costos: np.ndarray, demanda: np.ndarray,
            penalizacion: float, tolerancia: float = 1e-6) -> Evaluacion:
    # Z = Σ_i Σ_j c_ij · x_ij para toda la población.
    costo = np.einsum("pij,ij->p", poblacion, costos)
    # E = Σ_j max(0, Σ_i x_ij − D_j)
    sobrecarga = np.maximum(poblacion.sum(axis=1) - demanda[None, :], 0.0)
    exceso = sobrecarga.sum(axis=1)
    plantas = (sobrecarga > tolerancia).sum(axis=1)
    # f = 1 / (Z + λ · E)
    aptitud = 1.0 / (costo + penalizacion * exceso)
    return Evaluacion(costo, exceso, plantas, aptitud)
