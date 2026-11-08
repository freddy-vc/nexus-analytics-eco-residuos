import numpy as np


def mutar(poblacion: np.ndarray, tasa: float, costos: np.ndarray, demanda: np.ndarray,
          habilitadas: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Mutación por transferencia de toneladas; cada empresa de cada hijo muta con probabilidad `tasa`.

    Hay dos movimientos y ambos conservan la oferta de cada empresa:

    * Transferencia: si alguna planta tiene capacidad libre, la empresa pasa
      toneladas de una de sus rutas a esa planta.
    * Intercambio en ciclo: si no hay capacidad libre (problema balanceado), la
      empresa i pasa toneladas de la planta a a la planta b y otra empresa k
      hace lo contrario (de b hacia a). Así tampoco cambia lo que recibe cada
      planta. Es el movimiento clásico del método de transporte.

    El destino o la empresa compañera se eligen al azar, pero con mayor
    probabilidad cuando el cambio abarata el envío.
    """
    poblacion = poblacion.copy()
    individuos, filas = np.nonzero(rng.random(poblacion.shape[:2]) < tasa)
    if individuos.size == 0:
        return poblacion
    escala = max(float(np.std(costos[habilitadas])), 1.0)

    for p, i in zip(individuos, filas):
        x = poblacion[p]
        con_flujo = np.flatnonzero(x[i] > 1e-9)
        if con_flujo.size == 0:
            continue
        a = rng.choice(con_flujo)
        libre = demanda - x.sum(axis=0)
        destinos = np.flatnonzero(habilitadas[i] & (np.arange(x.shape[1]) != a))
        if destinos.size == 0:
            continue

        con_espacio = destinos[libre[destinos] > 1e-9]
        if con_espacio.size and rng.random() < 0.5:
            b = _elegir(rng, costos[i, con_espacio] - costos[i, a], escala, con_espacio)
            cantidad = min(x[i, a], libre[b]) * (1.0 if rng.random() < 0.7 else rng.random())
            x[i, a] -= cantidad
            x[i, b] += cantidad
            continue

        b = rng.choice(destinos)
        companeras = np.flatnonzero((x[:, b] > 1e-9) & habilitadas[:, a] & (np.arange(x.shape[0]) != i))
        if companeras.size == 0:
            continue
        ahorro = (costos[i, b] - costos[i, a]) + (costos[companeras, a] - costos[companeras, b])
        k = _elegir(rng, ahorro, escala, companeras)
        cantidad = min(x[i, a], x[k, b]) * (1.0 if rng.random() < 0.7 else rng.random())
        x[i, a] -= cantidad
        x[i, b] += cantidad
        x[k, b] -= cantidad
        x[k, a] += cantidad
    return poblacion


def _elegir(rng: np.random.Generator, cambio_costo: np.ndarray, escala: float, opciones: np.ndarray):
    """Elige una opción con probabilidad mayor cuanto más baje el costo (softmax)."""
    peso = np.exp(-np.clip(cambio_costo / escala, -30, 30))
    return opciones[rng.choice(opciones.size, p=peso / peso.sum())]
