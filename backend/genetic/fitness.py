from dataclasses import dataclass

import numpy as np


@dataclass
class Evaluacion:
    costo: np.ndarray            # costo de compra, transporte y operación de cada individuo
    exceso: np.ndarray           # toneladas que superan la capacidad de las plantas
    plantas_excedidas: np.ndarray
    aptitud: np.ndarray


def evaluar(poblacion: np.ndarray, costos: np.ndarray, demanda: np.ndarray,
            penalizacion: float, tolerancia: float = 1e-6) -> Evaluacion:
    """Aptitud = 1 / (costo total + penalización × toneladas sobre la capacidad).

    Un individuo que respeta todas las capacidades tiene exceso cero y su
    aptitud es simplemente el inverso de su costo.
    """
    costo = np.einsum("pij,ij->p", poblacion, costos)
    sobrecarga = np.maximum(poblacion.sum(axis=1) - demanda[None, :], 0.0)
    exceso = sobrecarga.sum(axis=1)
    plantas = (sobrecarga > tolerancia).sum(axis=1)
    aptitud = 1.0 / (costo + penalizacion * exceso)
    return Evaluacion(costo, exceso, plantas, aptitud)
