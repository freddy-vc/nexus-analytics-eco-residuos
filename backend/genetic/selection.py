import numpy as np

TORNEO = "TORNEO"
RULETA = "RULETA"


def seleccionar(aptitud: np.ndarray, cantidad: int, metodo: str, tamano_torneo: int,
                rng: np.random.Generator) -> np.ndarray:
    """Índices de los padres elegidos."""
    if metodo == TORNEO:
        return torneo(aptitud, cantidad, tamano_torneo, rng)
    return ruleta(aptitud, cantidad, rng)


def torneo(aptitud: np.ndarray, cantidad: int, tamano: int, rng: np.random.Generator) -> np.ndarray:
    """Cada padre es el más apto entre `tamano` individuos tomados al azar."""
    competidores = rng.integers(0, aptitud.size, size=(cantidad, max(tamano, 1)))
    ganadores = np.argmax(aptitud[competidores], axis=1)
    return competidores[np.arange(cantidad), ganadores]


def ruleta(aptitud: np.ndarray, cantidad: int, rng: np.random.Generator) -> np.ndarray:
    """Probabilidad proporcional a la aptitud por encima de la del peor individuo.

    Como las aptitudes son inversos de costos muy parecidos, restar la mínima
    (escalado por ventana) evita que la ruleta elija casi al azar.
    """
    ajustada = aptitud - aptitud.min()
    total = ajustada.sum()
    if total <= 0:
        return rng.integers(0, aptitud.size, size=cantidad)
    return rng.choice(aptitud.size, size=cantidad, p=ajustada / total)
