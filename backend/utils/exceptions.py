from datetime import datetime


class ErrorEcoResiduos(Exception):
    """Error de dominio con un mensaje apto para mostrar al usuario."""


class ErrorValidacion(ErrorEcoResiduos):
    pass


class ErrorNoEncontrado(ErrorEcoResiduos):
    pass


class ErrorAutenticacion(ErrorEcoResiduos):
    def __init__(self, mensaje: str, intentos_restantes: int | None = None,
                 bloqueado_hasta: datetime | None = None):
        super().__init__(mensaje)
        self.intentos_restantes = intentos_restantes
        self.bloqueado_hasta = bloqueado_hasta
