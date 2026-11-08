"""Gráficos ligeros en HTML que heredan los colores del tema."""

import base64


def progreso(porcentaje: float, delgada: bool = False) -> str:
    ancho = max(0.0, min(porcentaje, 100.0))
    return f'<div class="barra{" delgada" if delgada else ""}"><div style="width:{ancho:.1f}%"></div></div>'


def fila_utilizacion(codigo: str, nombre: str, usado: str, capacidad: str, porcentaje: float) -> str:
    return (f'<div class="utilizacion"><div><span><strong>{codigo}</strong> · {nombre}</span>'
            f'<span class="mu">{usado} / {capacidad} t</span></div>{progreso(porcentaje)}</div>')


def barra_apilada(partes: list[tuple[float, str, float]]) -> str:
    """partes: (fracción 0–1, color CSS, opacidad)."""
    segmentos = "".join(
        f'<div style="width:{fraccion * 100:.1f}%;background:{color};opacity:{opacidad}"></div>'
        for fraccion, color, opacidad in partes)
    return f'<div class="barra-apilada">{segmentos}</div>'


def red_portada(paleta: dict[str, str]) -> str:
    """Esquema decorativo de la portada: empresas conectadas a plantas.

    Se entrega como imagen porque st.html no admite SVG en línea; por eso los
    colores se toman directamente de la paleta del tema activo.
    """
    empresas = [(40, 30), (40, 70), (40, 110), (40, 150), (40, 190)]
    plantas = [(300, 50), (300, 110), (300, 170)]
    rutas = [(0, 0), (1, 0), (1, 1), (2, 2), (3, 1), (4, 2)]
    optimas = [(0, 1), (2, 0), (3, 2)]

    def linea(i, j):
        (x1, y1), (x2, y2) = empresas[i], plantas[j]
        return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>'

    marcado = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 220">'
        f'<g stroke="{paleta["bd"]}" stroke-width="2">{"".join(linea(i, j) for i, j in rutas)}</g>'
        f'<g stroke="{paleta["ac"]}" stroke-width="3">{"".join(linea(i, j) for i, j in optimas)}</g>'
        f'<g fill="{paleta["sf"]}" stroke="{paleta["ac"]}" stroke-width="3">'
        + "".join(f'<circle cx="{x}" cy="{y}" r="10"/>' for x, y in empresas) + '</g>'
        f'<g fill="{paleta["ac"]}">'
        + "".join(f'<circle cx="{x}" cy="{y}" r="14"/>' for x, y in plantas) + '</g></svg>')
    datos = base64.b64encode(marcado.encode()).decode()
    return (f'<img src="data:image/svg+xml;base64,{datos}" width="100%" style="max-width:380px" '
            f'alt="Esquema de la red: empresas conectadas a plantas">')
