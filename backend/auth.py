import hashlib
import hmac
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import func, or_, select

from backend.config import Configuracion
from backend.database import BaseDatos, Usuario
from backend.utils.exceptions import ErrorAutenticacion
from backend.utils.singleton import MetaSingleton


@dataclass(frozen=True)
class UsuarioSesion:
    id: int
    usuario: str
    nombres: str
    apellidos: str
    rol: str

    # Iniciales del usuario para el avatar de la barra superior.
    @property
    def iniciales(self) -> str:
        return (self.nombres[:1] + self.apellidos[:1]).upper()


# Autenticación con contraseña cifrada con bcrypt y sesión con token firmado.
class ServicioAutenticacion(metaclass=MetaSingleton):
    MAX_INTENTOS = 3
    MINUTOS_BLOQUEO = 60

    # Obtiene las instancias únicas de la base de datos y de la configuración.
    def __init__(self):
        self._bd = BaseDatos()
        self._configuracion = Configuracion()

    # Valida usuario o correo y contraseña, controlando intentos fallidos y bloqueo temporal.
    def autenticar(self, identificador: str, clave: str) -> UsuarioSesion:
        identificador = identificador.strip().lower()
        if not identificador or not clave:
            raise ErrorAutenticacion("Ingresa tu usuario y contraseña.")

        ahora = datetime.now(timezone.utc)
        with self._bd.sesion() as sesion:
            usuario = sesion.scalar(select(Usuario).where(or_(
                func.lower(Usuario.username) == identificador,
                func.lower(Usuario.email) == identificador)))

            if usuario is None or not usuario.activo:
                raise ErrorAutenticacion("Usuario o contraseña incorrectos.")
            if usuario.bloqueado_hasta and usuario.bloqueado_hasta > ahora:
                raise ErrorAutenticacion("Cuenta bloqueada temporalmente por intentos fallidos.",
                                         bloqueado_hasta=usuario.bloqueado_hasta)

            # Contraseña incorrecta: suma un intento y bloquea la cuenta al llegar al máximo.
            if not bcrypt.checkpw(clave.encode(), usuario.password_hash.encode()):
                usuario.intentos_fallidos += 1
                restantes = self.MAX_INTENTOS - usuario.intentos_fallidos
                if restantes <= 0:
                    usuario.intentos_fallidos = 0
                    usuario.bloqueado_hasta = ahora + timedelta(minutes=self.MINUTOS_BLOQUEO)
                    sesion.commit()
                    raise ErrorAutenticacion(
                        f"Credenciales incorrectas. La cuenta quedó bloqueada "
                        f"{self._duracion_bloqueo()}.", bloqueado_hasta=usuario.bloqueado_hasta)
                sesion.commit()
                raise ErrorAutenticacion(
                    f"Credenciales incorrectas. Te quedan {restantes} "
                    f"{'intento' if restantes == 1 else 'intentos'} antes de un bloqueo "
                    f"temporal de {self._duracion_bloqueo()}.", intentos_restantes=restantes)

            usuario.intentos_fallidos = 0
            usuario.bloqueado_hasta = None
            usuario.ultimo_acceso = ahora
            return self._a_sesion(usuario)

    # Texto legible de la duración del bloqueo.
    def _duracion_bloqueo(self) -> str:
        horas, minutos = divmod(self.MINUTOS_BLOQUEO, 60)
        if minutos:
            return f"{self.MINUTOS_BLOQUEO} minutos"
        return "1 hora" if horas == 1 else f"{horas} horas"

    # Genera el token firmado que conserva la sesión entre recargas.
    def emitir_token(self, usuario: UsuarioSesion) -> str:
        expira = int(time.time() + self._configuracion.horas_sesion * 3600)
        # Formato del token: id.expiración.firma.
        contenido = f"{usuario.id}.{expira}"
        return f"{contenido}.{self._firmar(contenido)}"

    # Restaura el usuario a partir de un token válido y vigente; None en otro caso.
    def validar_token(self, token: str | None) -> UsuarioSesion | None:
        try:
            id_usuario, expira, firma = (token or "").split(".")
            contenido = f"{id_usuario}.{expira}"
            # Comparación de la firma en tiempo constante y control de expiración.
            if not hmac.compare_digest(firma, self._firmar(contenido)) or int(expira) < time.time():
                return None
            id_usuario = int(id_usuario)
        except ValueError:
            return None

        with self._bd.sesion() as sesion:
            usuario = sesion.get(Usuario, id_usuario)
            return self._a_sesion(usuario) if usuario and usuario.activo else None

    # Firma HMAC-SHA256 con el secreto de sesión.
    def _firmar(self, contenido: str) -> str:
        return hmac.new(self._configuracion.secreto_sesion.encode(), contenido.encode(),
                        hashlib.sha256).hexdigest()

    # Convierte la entidad Usuario en los datos de sesión.
    @staticmethod
    def _a_sesion(usuario: Usuario) -> UsuarioSesion:
        return UsuarioSesion(usuario.id, usuario.username, usuario.nombres, usuario.apellidos,
                             usuario.rol.nombre.capitalize())
