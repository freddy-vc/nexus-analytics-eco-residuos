"""Formato numérico colombiano: punto para miles y coma para decimales."""

import math


def numero(valor: float | None, decimales: int = 0) -> str:
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "—"
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


def cantidad(valor: float | None, max_decimales: int = 2) -> str:
    """Entero sin decimales; con decimales solo si los tiene (12,5)."""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "—"
    if float(valor).is_integer():
        return numero(valor)
    return numero(valor, max_decimales).rstrip("0").rstrip(",")


def moneda(valor: float | None) -> str:
    if valor is None:
        return "—"
    signo = "−" if valor < 0 else ""
    return f"{signo}${numero(abs(valor))}"


def toneladas(valor: float | None, unidad: str = "t") -> str:
    return f"{cantidad(valor)} {unidad}" if valor is not None else "—"


def segundos(milisegundos: float | None) -> str:
    if milisegundos is None:
        return "—"
    valor = milisegundos / 1000
    return f"{numero(valor, 2 if valor < 10 else 1)} s"


def porcentaje(valor: float | None, decimales: int = 0) -> str:
    return f"{numero(valor, decimales)} %" if valor is not None else "—"


def nombre_corto(nombre: str) -> str:
    """Nombre comercial sin la razón social (S.A.S., S.A.) para listas y matrices."""
    for sufijo in (" S.A.S.", " S.A.S", " S.A.", " S.A"):
        if nombre.endswith(sufijo):
            return nombre[: -len(sufijo)]
    return nombre
