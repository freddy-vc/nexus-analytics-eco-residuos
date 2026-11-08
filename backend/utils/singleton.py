import threading


class MetaSingleton(type):
    """Metaclase que garantiza una única instancia por clase, segura entre hilos.

    Streamlit atiende cada sesión en un hilo distinto; el candado evita que dos
    sesiones creen instancias paralelas del mismo servicio. Es reentrante porque
    un singleton puede crear otro dentro de su constructor (un servicio crea la
    conexión a la base de datos y esta a su vez lee la configuración).
    """

    _instancias: dict[type, object] = {}
    _candado = threading.RLock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instancias:
            with cls._candado:
                if cls not in cls._instancias:
                    cls._instancias[cls] = super().__call__(*args, **kwargs)
        return cls._instancias[cls]
