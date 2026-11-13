import math


# Número con punto de miles y coma decimal.
def numero(valor: float | None, decimales: int = 0) -> str:
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "—"
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


# Cantidad con decimales solo cuando el valor los tiene.
def cantidad(valor: float | None, max_decimales: int = 2) -> str:
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "—"
    if float(valor).is_integer():
        return numero(valor)
    return numero(valor, max_decimales).rstrip("0").rstrip(",")


# Valor en pesos colombianos.
def moneda(valor: float | None) -> str:
    if valor is None:
        return "—"
    signo = "−" if valor < 0 else ""
    return f"{signo}${numero(abs(valor))}"


# Cantidad con su unidad de masa.
def toneladas(valor: float | None, unidad: str = "t") -> str:
    return f"{cantidad(valor)} {unidad}" if valor is not None else "—"


# Tiempo en milisegundos o segundos según su magnitud.
def segundos(milisegundos: float | None) -> str:
    if milisegundos is None:
        return "—"
    valor = milisegundos / 1000
    return f"{numero(valor, 2 if valor < 10 else 1)} s"


# Valor porcentual.
def porcentaje(valor: float | None, decimales: int = 0) -> str:
    return f"{numero(valor, decimales)} %" if valor is not None else "—"


# Nombre comercial sin la razón social.
def nombre_corto(nombre: str) -> str:
    for sufijo in (" S.A.S.", " S.A.S", " S.A.", " S.A"):
        if nombre.endswith(sufijo):
            return nombre[: -len(sufijo)]
    return nombre
