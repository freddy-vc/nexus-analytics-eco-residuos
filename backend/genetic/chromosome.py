import numpy as np


# Población inicial: individuos aleatorios y una fracción construida por costo mínimo.
def poblacion_inicial(oferta: np.ndarray, demanda: np.ndarray, costos: np.ndarray,
                      habilitadas: np.ndarray, tamano: int, rng: np.random.Generator,
                      ficticias: np.ndarray | None = None, fraccion_heuristica: float = 0.2) -> np.ndarray:
    m, n = costos.shape
    # Individuos aleatorios: x_ij = O_i · w_ij / Σ_k w_ik, con w ~ Exp(1).
    pesos = rng.exponential(size=(tamano, m, n)) * habilitadas
    pesos /= np.maximum(pesos.sum(axis=2, keepdims=True), 1e-12)
    poblacion = pesos * oferta[None, :, None]

    # Las rutas ficticias se ordenan al final, con un costo mayor que el de cualquier ruta real.
    orden = np.where(ficticias, costos.max() * 10 + 1, costos) if ficticias is not None else costos
    for k in range(int(tamano * fraccion_heuristica)):
        poblacion[k] = _costo_minimo(oferta, demanda, orden, habilitadas, rng)
    return poblacion


# Individuo construido con el método del costo mínimo sobre costos perturbados.
def _costo_minimo(oferta, demanda, costos, habilitadas, rng) -> np.ndarray:
    m, n = costos.shape
    individuo = np.zeros((m, n))
    pendiente, libre = oferta.astype(float).copy(), demanda.astype(float).copy()
    # Costos perturbados ±10 % para que los individuos heurísticos no sean idénticos.
    ruido = np.where(habilitadas, costos * rng.uniform(0.9, 1.1, size=costos.shape), np.inf)
    for celda in np.argsort(ruido, axis=None):
        i, j = divmod(int(celda), n)
        if not np.isfinite(ruido[i, j]):
            break
        # Costo mínimo: se envía lo máximo que permiten la oferta pendiente y la capacidad libre.
        envio = min(pendiente[i], libre[j])
        if envio > 1e-9:
            individuo[i, j] += envio
            pendiente[i] -= envio
            libre[j] -= envio
    # La oferta sobrante se asigna a la ruta más barata de la empresa.
    for i in np.flatnonzero(pendiente > 1e-9):
        individuo[i, int(np.argmin(ruido[i]))] += pendiente[i]
    return individuo


# Anula valores negativos y rutas deshabilitadas, y reescala cada fila a su oferta.
def reparar_oferta(individuos: np.ndarray, oferta: np.ndarray, habilitadas: np.ndarray) -> np.ndarray:
    individuos = np.maximum(individuos, 0.0) * habilitadas
    sumas = individuos.sum(axis=2, keepdims=True)
    vacias = sumas[..., 0] <= 1e-12
    if np.any(vacias):
        # Una fila vacía reparte la oferta en partes iguales entre sus rutas habilitadas.
        uniforme = habilitadas / np.maximum(habilitadas.sum(axis=1, keepdims=True), 1)
        individuos[vacias] = np.broadcast_to(uniforme, individuos.shape)[vacias]
        sumas = individuos.sum(axis=2, keepdims=True)
    # x_ij ← O_i · x_ij / Σ_k x_ik
    return individuos / sumas * oferta[None, :, None]


# Mueve el excedente de las plantas sobrecargadas hacia los cambios de ruta más baratos.
def reparar_capacidad(individuo: np.ndarray, demanda: np.ndarray, costos: np.ndarray,
                      habilitadas: np.ndarray) -> np.ndarray:
    x = individuo.copy()
    for _ in range(x.size):
        exceso = x.sum(axis=0) - demanda
        j = int(np.argmax(exceso))
        if exceso[j] <= 1e-9:
            break
        libre = demanda - x.sum(axis=0)
        # Mover de la planta excedida j a una planta k con espacio cuesta c_ik − c_ij.
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
