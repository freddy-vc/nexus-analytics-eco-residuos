from datetime import datetime


# Errores de dominio con mensajes aptos para mostrar al usuario.
class ErrorEcoResiduos(Exception):
    pass


class ErrorValidacion(ErrorEcoResiduos):
    pass


class ErrorNoEncontrado(ErrorEcoResiduos):
    pass


class ErrorAutenticacion(ErrorEcoResiduos):
    # Guarda los intentos restantes y la fecha de fin del bloqueo, si aplica.
    def __init__(self, mensaje: str, intentos_restantes: int | None = None,
                 bloqueado_hasta: datetime | None = None):
        super().__init__(mensaje)
        self.intentos_restantes = intentos_restantes
        self.bloqueado_hasta = bloqueado_hasta
