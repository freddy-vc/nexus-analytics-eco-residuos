"""Tablas HTML con el estilo de la aplicación."""

Columna = tuple[str, str]  # (título, alineación: "i" izquierda | "d" derecha)


def tabla(columnas: list[Columna], filas: list[list[str]], pie: list[str] | None = None,
          clase: str = "", ancho_minimo: int = 420) -> str:
    def celda(etiqueta: str, valor: str, alineacion: str) -> str:
        return f'<{etiqueta} class="{"num" if alineacion == "d" else ""}">{valor}</{etiqueta}>'

    cabecera = "".join(celda("th", titulo, alineacion) for titulo, alineacion in columnas)
    cuerpo = "".join("<tr>" + "".join(celda("td", valor, columnas[k][1])
                                      for k, valor in enumerate(fila)) + "</tr>" for fila in filas)
    final = ""
    if pie:
        final = "<tfoot><tr>" + "".join(celda("td", valor, columnas[k][1])
                                        for k, valor in enumerate(pie)) + "</tr></tfoot>"
    return (f'<div class="tabla-marco"><table class="tabla {clase}" style="min-width:{ancho_minimo}px">'
            f'<thead><tr>{cabecera}</tr></thead><tbody>{cuerpo}</tbody>{final}</table></div>')
