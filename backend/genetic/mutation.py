import numpy as np


# Mutación por transferencia o por intercambio en ciclo; ambos movimientos conservan la oferta.
def mutar(poblacion: np.ndarray, tasa: float, costos: np.ndarray, demanda: np.ndarray,
          habilitadas: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    poblacion = poblacion.copy()
    # Cada empresa de cada hijo muta con probabilidad p_m.
    individuos, filas = np.nonzero(rng.random(poblacion.shape[:2]) < tasa)
    if individuos.size == 0:
        return poblacion
    # σ: escala de la softmax, desviación estándar de los costos habilitados.
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

        # Transferencia: mover δ toneladas de la planta a hacia una planta b con capacidad libre.
        con_espacio = destinos[libre[destinos] > 1e-9]
        if con_espacio.size and rng.random() < 0.5:
            b = _elegir(rng, costos[i, con_espacio] - costos[i, a], escala, con_espacio)
            # δ es el máximo posible con probabilidad 0,7; en otro caso, una fracción aleatoria.
            cantidad = min(x[i, a], libre[b]) * (1.0 if rng.random() < 0.7 else rng.random())
            x[i, a] -= cantidad
            x[i, b] += cantidad
            continue

        b = rng.choice(destinos)
        # Ciclo: la empresa k hace el movimiento inverso y lo que recibe cada planta no cambia.
        companeras = np.flatnonzero((x[:, b] > 1e-9) & habilitadas[:, a] & (np.arange(x.shape[0]) != i))
        if companeras.size == 0:
            continue
        # Δ = (c_ib − c_ia) + (c_ka − c_kb)
        ahorro = (costos[i, b] - costos[i, a]) + (costos[companeras, a] - costos[companeras, b])
        k = _elegir(rng, ahorro, escala, companeras)
        cantidad = min(x[i, a], x[k, b]) * (1.0 if rng.random() < 0.7 else rng.random())
        x[i, a] -= cantidad
        x[i, b] += cantidad
        x[k, b] -= cantidad
        x[k, a] += cantidad
    return poblacion


# Elige una opción favoreciendo las que reducen el costo.
def _elegir(rng: np.random.Generator, cambio_costo: np.ndarray, escala: float, opciones: np.ndarray):
    # P ∝ exp(−Δ/σ), con el exponente acotado a [−30, 30] para evitar desbordamientos.
    peso = np.exp(-np.clip(cambio_costo / escala, -30, 30))
    return opciones[rng.choice(opciones.size, p=peso / peso.sum())]
