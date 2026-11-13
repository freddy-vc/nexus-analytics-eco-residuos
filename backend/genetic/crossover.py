import numpy as np

UN_PUNTO = "UN_PUNTO"
DOS_PUNTOS = "DOS_PUNTOS"


# Cruce por filas de uno o dos puntos; cada hijo conserva la oferta de cada empresa.
def cruzar(padres_a: np.ndarray, padres_b: np.ndarray, tasa: float, tipo: str,
           rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    pares, m, _ = padres_a.shape
    hijo_a, hijo_b = padres_a.copy(), padres_b.copy()
    if m < 2:
        return hijo_a, hijo_b

    # Cada pareja se cruza con probabilidad p_c.
    cruzan = rng.random(pares) < tasa
    filas = np.arange(m)[None, :]
    if tipo == UN_PUNTO:
        # Un punto: se intercambian las filas i ≥ c.
        corte = rng.integers(1, m, size=(pares, 1))
        segmento = filas >= corte
    else:
        # Dos puntos: se intercambian las filas c1 ≤ i < c2.
        cortes = np.sort(rng.integers(0, m + 1, size=(pares, 2)), axis=1)
        segmento = (filas >= cortes[:, :1]) & (filas < cortes[:, 1:])
    intercambio = (segmento & cruzan[:, None])[:, :, None]
    hijo_a = np.where(intercambio, padres_b, padres_a)
    hijo_b = np.where(intercambio, padres_a, padres_b)
    return hijo_a, hijo_b
