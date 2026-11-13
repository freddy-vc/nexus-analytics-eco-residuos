from time import perf_counter


class Cronometro:
    # Inicializa el cronómetro.
    def __init__(self):
        self._inicio = 0.0
        self.milisegundos = 0.0

    # Inicia la medición.
    def __enter__(self):
        self._inicio = perf_counter()
        return self

    # Registra el tiempo transcurrido en milisegundos.
    def __exit__(self, *excepcion):
        self.milisegundos = (perf_counter() - self._inicio) * 1000
        return False
