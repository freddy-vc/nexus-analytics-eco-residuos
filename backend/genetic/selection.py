import numpy as np

TORNEO = "TORNEO"
RULETA = "RULETA"


# Índices de los padres según el método de selección configurado.
def seleccionar(aptitud: np.ndarray, cantidad: int, metodo: str, tamano_torneo: int,
                rng: np.random.Generator) -> np.ndarray:
    if metodo == TORNEO:
        return torneo(aptitud, cantidad, tamano_torneo, rng)
    return ruleta(aptitud, cantidad, rng)


# Selección por torneo: cada padre es el más apto de un grupo tomado al azar.
def torneo(aptitud: np.ndarray, cantidad: int, tamano: int, rng: np.random.Generator) -> np.ndarray:
    competidores = rng.integers(0, aptitud.size, size=(cantidad, max(tamano, 1)))
    ganadores = np.argmax(aptitud[competidores], axis=1)
    return competidores[np.arange(cantidad), ganadores]


# Selección por ruleta con escalado por ventana.
def ruleta(aptitud: np.ndarray, cantidad: int, rng: np.random.Generator) -> np.ndarray:
    # p_r = (f_r − f_min) / Σ_s (f_s − f_min)
    ajustada = aptitud - aptitud.min()
    total = ajustada.sum()
    if total <= 0:
        return rng.integers(0, aptitud.size, size=cantidad)
    return rng.choice(aptitud.size, size=cantidad, p=ajustada / total)
