"""Íconos de línea de la interfaz (trazos de 24 × 24, los mismos de los mockups).

st.html elimina las etiquetas <svg>, por eso los íconos se pintan como máscaras
CSS: toman el color del texto que los rodea y respetan el tema activo.
"""

from urllib.parse import quote

TRAZOS = {
    "hoja": "M5 19c0-8 6-14 15-14 0 9-6 15-14 15M5 19l7-7",
    "inicio": "M3 10.5 12 3l9 7.5V21h-6v-6H9v6H3z",
    "empresas": "M4 21V5l8-3v19M12 21h8V9l-8-3M8 9h.01M8 13h.01M8 17h.01M16 13h.01M16 17h.01",
    "plantas": "M3 21V10l6 4V10l6 4V6h6v15zM3 21h18",
    "rutas": "M4 17a2 2 0 1 0 4 0a2 2 0 1 0-4 0M16 7a2 2 0 1 0 4 0a2 2 0 1 0-4 0"
             "M6 15V9a4 4 0 0 1 4-4h6M18 9v6a4 4 0 0 1-4 4H8",
    "parametros": "M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M14 4v4M8 10v4M16 16v4",
    "red": "M3 6a2 2 0 1 0 4 0a2 2 0 1 0-4 0M3 18a2 2 0 1 0 4 0a2 2 0 1 0-4 0"
           "M17 12a2 2 0 1 0 4 0a2 2 0 1 0-4 0M7 6.5l10 4.5M7 17.5l10-4.5",
    "exacto": "M18 4H6l6 8-6 8h12",
    "genetico": "M7 3c0 6 10 6 10 12s-10 6-10 6M17 3c0 6-10 6-10 12M8 7h8M8 17h8",
    "sensibilidad": "M3 12h4l3-8 4 16 3-8h4",
    "escenarios": "M12 3 2 8l10 5 10-5zM2 13l10 5 10-5",
    "comparacion": "M4 20V10M10 20V4M16 20v-7M22 20H2",
    "luna": "M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z",
    "sol": "M8 12a4 4 0 1 0 8 0a4 4 0 1 0-8 0M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4"
           "M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4",
    "toneladas": "M3 7h18l-2 13H5zM8 7V4h8v3",
    "dinero": "M12 2v20M17 6H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6",
    "brecha": "M4 20 20 4M6 9a3 3 0 1 0 0-.01M18 15a3 3 0 1 0 0-.01",
    "visto": "M20 6 9 17l-5-5",
    "buscar": "M10 4a6 6 0 1 0 0 12a6 6 0 1 0 0-12M20 20l-5.6-5.6",
    "editar": "M4 20h4L19 9l-4-4L4 16zM14 6l4 4",
    "eliminar": "M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13",
    "subir": "M12 16V4M7 9l5-5 5 5M4 16v4h16v-4",
    "alerta": "M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z",
    "candado": "M6 11h12v10H6zM8 11V7a4 4 0 0 1 8 0v4",
}

_GROSOR_GRUESO = {"visto": 3.0, "alerta": 2.2}


def url_mascara(nombre: str, grosor: float | None = None) -> str:
    grosor = grosor or _GROSOR_GRUESO.get(nombre, 1.8)
    marcado = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
               f'stroke="black" stroke-width="{grosor}" stroke-linecap="round" '
               f'stroke-linejoin="round"><path d="{TRAZOS[nombre]}"/></svg>')
    return f'url("data:image/svg+xml;utf8,{quote(marcado)}")'


def icono(nombre: str, tamano: int = 18) -> str:
    return (f'<span class="ico ico-{nombre}" style="width:{tamano}px;height:{tamano}px" '
            f'aria-hidden="true"></span>')


def css_iconos() -> str:
    return "".join(f".ico-{nombre}{{--icono:{url_mascara(nombre)};}}\n" for nombre in TRAZOS)


def svg_datos(nombre: str, color: str, tamano: int = 24, grosor: float = 1.8) -> str:
    """Ícono como imagen en línea, para lugares donde no aplica la máscara CSS."""
    marcado = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{tamano}" height="{tamano}" '
               f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="{grosor}" '
               f'stroke-linecap="round" stroke-linejoin="round"><path d="{TRAZOS[nombre]}"/></svg>')
    return f"data:image/svg+xml;utf8,{quote(marcado)}"
