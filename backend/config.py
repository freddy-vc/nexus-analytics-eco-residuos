import hashlib
import os
from pathlib import Path

from dotenv import load_dotenv

from backend.utils.singleton import MetaSingleton

DIRECTORIO_RAIZ = Path(__file__).resolve().parents[1]


class Configuracion(metaclass=MetaSingleton):
    # Carga la configuración desde el archivo .env con valores por defecto.
    def __init__(self):
        load_dotenv(DIRECTORIO_RAIZ / ".env")
        self.host_bd = os.getenv("DB_HOST", "localhost")
        self.puerto_bd = int(os.getenv("DB_PORT", "5432"))
        self.nombre_bd = os.getenv("DB_NAME", "ecoresiduos")
        self.usuario_bd = os.getenv("DB_USER", "postgres")
        self.clave_bd = os.getenv("DB_PASSWORD", "")

        # Clave de firma de la cookie de sesión; si no se define se deriva de la conexión.
        self.secreto_sesion = os.getenv("APP_SECRET") or hashlib.sha256(
            f"{self.usuario_bd}:{self.clave_bd}@{self.host_bd}/{self.nombre_bd}".encode()).hexdigest()
        self.horas_sesion = 8

        # Tolerancia de factibilidad exigida por RNF06.
        self.tolerancia_factibilidad = 1e-6

    # Cadena de conexión a PostgreSQL.
    @property
    def url_bd(self) -> str:
        return (f"postgresql+psycopg2://{self.usuario_bd}:{self.clave_bd}"
                f"@{self.host_bd}:{self.puerto_bd}/{self.nombre_bd}")
