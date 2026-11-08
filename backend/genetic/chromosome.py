"""Codificación cromosómica: matriz de flujos (empresas × plantas).

Cada individuo es una matriz con las toneladas enviadas de cada empresa a cada
planta. La población completa se guarda como un arreglo (P, m, n) para operar
con NumPy sobre todos los individuos a la vez. Cada fila de un individuo suma
exactamente la oferta de su empresa, de modo que la restricción de oferta se
cumple por construcción; la de capacidad de las plantas se controla con la
penalización de la aptitud.
"""

import numpy as np


def poblacion_inicial(oferta: np.ndarray, demanda: np.ndarray, costos: np.ndarray,
                      habilitadas: np.ndarray, tamano: int, rng: np.random.Generator,
                      ficticias: np.ndarray | None = None, fraccion_heuristica: float = 0.2) -> np.ndarray:
    """Mezcla individuos aleatorios con algunos construidos por costo mínimo.

    Los aleatorios reparten la oferta de cada empresa entre sus rutas habilitadas
    con pesos al azar. Los heurísticos aplican el método del costo mínimo
    (llenar primero las rutas más baratas) con ruido en los costos para que no
    sean todos iguales; las rutas de nodos ficticios se dejan de últimas porque
    su costo cero no significa que convenga usarlas.
    """
    m, n = costos.shape
    pesos = rng.exponential(size=(tamano, m, n)) * habilitadas
    pesos /= np.maximum(pesos.sum(axis=2, keepdims=True), 1e-12)
    poblacion = pesos * oferta[None, :, None]

    orden = np.where(ficticias, costos.max() * 10 + 1, costos) if ficticias is not None else costos
    for k in range(int(tamano * fraccion_heuristica)):
        poblacion[k] = _costo_minimo(oferta, demanda, orden, habilitadas, rng)
    return poblacion


def _costo_minimo(oferta, demanda, costos, habilitadas, rng) -> np.ndarray:
    m, n = costos.shape
    individuo = np.zeros((m, n))
    pendiente, libre = oferta.astype(float).copy(), demanda.astype(float).copy()
    ruido = np.where(habilitadas, costos * rng.uniform(0.9, 1.1, size=costos.shape), np.inf)
    for celda in np.argsort(ruido, axis=None):
        i, j = divmod(int(celda), n)
        if not np.isfinite(ruido[i, j]):
            break
        envio = min(pendiente[i], libre[j])
        if envio > 1e-9:
            individuo[i, j] += envio
            pendiente[i] -= envio
            libre[j] -= envio
    for i in np.flatnonzero(pendiente > 1e-9):
        individuo[i, int(np.argmin(ruido[i]))] += pendiente[i]
    return individuo


def reparar_oferta(individuos: np.ndarray, oferta: np.ndarray, habilitadas: np.ndarray) -> np.ndarray:
    """Reescala cada fila para que sume la oferta y anula las rutas deshabilitadas."""
    individuos = np.maximum(individuos, 0.0) * habilitadas
    sumas = individuos.sum(axis=2, keepdims=True)
    vacias = sumas[..., 0] <= 1e-12
    if np.any(vacias):
        uniforme = habilitadas / np.maximum(habilitadas.sum(axis=1, keepdims=True), 1)
        individuos[vacias] = np.broadcast_to(uniforme, individuos.shape)[vacias]
        sumas = individuos.sum(axis=2, keepdims=True)
    return individuos / sumas * oferta[None, :, None]


def reparar_capacidad(individuo: np.ndarray, demanda: np.ndarray, costos: np.ndarray,
                      habilitadas: np.ndarray) -> np.ndarray:
    """Pasa el excedente de las plantas sobrecargadas a plantas con capacidad libre.

    Se aplica a la mejor solución al final de la corrida para limpiar residuos
    pequeños que dejan las transferencias parciales. Mueve primero las
    toneladas cuyo cambio de ruta encarece menos el envío; si no hay capacidad
    libre suficiente, deja el excedente (la solución se reporta no factible).
    """
    x = individuo.copy()
    for _ in range(x.size):
        exceso = x.sum(axis=0) - demanda
        j = int(np.argmax(exceso))
        if exceso[j] <= 1e-9:
            break
        libre = demanda - x.sum(axis=0)
        opciones = [(costos[i, k] - costos[i, j], i, k)
                    for i in np.flatnonzero(x[:, j] > 1e-12)
                    for k in np.flatnonzero(habilitadas[i] & (libre > 1e-9)) if k != j]
        if not opciones:
            break
        _, i, k = min(opciones)
        cantidad = min(exceso[j], x[i, j], libre[k])
        x[i, j] -= cantidad
        x[i, k] += cantidad
    return x
