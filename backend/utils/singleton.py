import threading


# Metaclase que garantiza una única instancia por clase, segura entre hilos.
class MetaSingleton(type):
    _instancias: dict[type, object] = {}
    _candado = threading.RLock()

    # Devuelve la instancia existente de la clase o la crea una sola vez.
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instancias:
            # Doble verificación con candado reentrante: cada sesión de Streamlit corre en su propio hilo.
            with cls._candado:
                if cls not in cls._instancias:
                    cls._instancias[cls] = super().__call__(*args, **kwargs)
        return cls._instancias[cls]
