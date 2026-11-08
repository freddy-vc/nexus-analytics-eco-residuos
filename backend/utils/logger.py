import logging

_FORMATO = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
logging.basicConfig(level=logging.INFO, format=_FORMATO)


def obtener_registrador(nombre: str) -> logging.Logger:
    return logging.getLogger(f"ecoresiduos.{nombre}")
