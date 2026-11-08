import numpy as np

UN_PUNTO = "UN_PUNTO"
DOS_PUNTOS = "DOS_PUNTOS"


def cruzar(padres_a: np.ndarray, padres_b: np.ndarray, tasa: float, tipo: str,
           rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Cruce por filas: los hijos intercambian el plan completo de algunas empresas.

    Los puntos de corte caen entre empresas, así que cada fila del hijo viene
    entera de uno de los padres y conserva la oferta de esa empresa.
    """
    pares, m, _ = padres_a.shape
    hijo_a, hijo_b = padres_a.copy(), padres_b.copy()
    if m < 2:
        return hijo_a, hijo_b

    cruzan = rng.random(pares) < tasa
    filas = np.arange(m)[None, :]
    if tipo == UN_PUNTO:
        corte = rng.integers(1, m, size=(pares, 1))
        segmento = filas >= corte
    else:
        cortes = np.sort(rng.integers(0, m + 1, size=(pares, 2)), axis=1)
        segmento = (filas >= cortes[:, :1]) & (filas < cortes[:, 1:])
    intercambio = (segmento & cruzan[:, None])[:, :, None]
    hijo_a = np.where(intercambio, padres_b, padres_a)
    hijo_b = np.where(intercambio, padres_a, padres_b)
    return hijo_a, hijo_b
