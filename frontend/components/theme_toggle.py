import base64
from pathlib import Path

import streamlit as st

from frontend.components import icons, session

RAIZ = Path(__file__).resolve().parents[2]
HOJA_ESTILOS = RAIZ / "frontend/styles/main.css"
COOKIE_TEMA = "eco_tema"

PALETAS = {
    "claro": {
        "bg": "#F5F7FA", "sf": "#FFFFFF", "sf2": "#F0F3F6", "tx": "#1F2A30", "mu": "#5B6770",
        "bd": "#E3E7EC", "ac": "#6CC51D", "on": "#FFFFFF", "acs": "#EEF8E4", "act": "#3B820E",
        "ag": "#1D4ED8", "ags": "#E6EEFD", "wa": "#92400E", "was": "#FEF3C7", "er": "#B42318",
        "ers": "#FDECEA",
        "sh": "0 1px 2px rgba(16,24,40,.04), 0 6px 20px rgba(16,24,40,.04)",
    },
    "oscuro": {
        "bg": "#141517", "sf": "#1E1F22", "sf2": "#121315", "tx": "#F2F3F5", "mu": "#8F949A",
        "bd": "#2C2E33", "ac": "#C8F135", "on": "#121315", "acs": "#2A3312", "act": "#C8F135",
        "ag": "#7AA7FF", "ags": "#1A2438", "wa": "#FBBF24", "was": "#33270F", "er": "#F87171",
        "ers": "#3A1717", "sh": "none",
    },
}


def modo() -> str:
    if "tema" not in st.session_state:
        guardado = session.leer_cookie(COOKIE_TEMA)
        st.session_state.tema = guardado if guardado in PALETAS else "claro"
    return st.session_state.tema


def paleta() -> dict[str, str]:
    return PALETAS[modo()]


def alternar() -> None:
    st.session_state.tema = "oscuro" if modo() == "claro" else "claro"
    session.programar_cookie(COOKIE_TEMA, st.session_state.tema, 365 * 24 * 3600)


@st.cache_resource
def _css_estatico(version: float) -> str:
    """version es la fecha de modificación de la hoja: al editarla se vuelve a leer."""
    fuentes = ""
    for nombre, rango in (
            ("Inter-latin.woff2", "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, "
                                  "U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, "
                                  "U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD"),
            ("Inter-latin-ext.woff2", "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, "
                                      "U+02DD-02FF, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, "
                                      "U+2020, U+20A0-20AB, U+20AD-20C4, U+2113, U+2C60-2C7F, "
                                      "U+A720-A7FF")):
        datos = base64.b64encode((RAIZ / "assets/fonts" / nombre).read_bytes()).decode()
        fuentes += (f"@font-face{{font-family:'Inter';font-style:normal;font-weight:100 900;"
                    f"font-display:swap;src:url(data:font/woff2;base64,{datos}) format('woff2');"
                    f"unicode-range:{rango};}}\n")
    iconos_nav = "".join(
        f'[class*="st-key-nav_{nombre}_"]{{--icono:{icons.url_mascara(nombre)};}}\n'
        for nombre in ("inicio", "empresas", "plantas", "rutas", "parametros", "red", "exacto",
                       "escenarios"))
    iconos_accion = (f'[class*="st-key-accion_editar"]{{--icono:{icons.url_mascara("editar")};}}\n'
                     f'[class*="st-key-accion_eliminar"]{{--icono:{icons.url_mascara("eliminar")};}}\n'
                     f':root{{--icono-buscar:{icons.url_mascara("buscar")};}}\n')
    estilos = HOJA_ESTILOS.read_text(encoding="utf-8")
    return fuentes + icons.css_iconos() + iconos_nav + iconos_accion + estilos


def aplicar() -> None:
    variables = ";".join(f"--{clave}:{valor}" for clave, valor in paleta().items())
    icono_tema = icons.url_mascara("sol" if modo() == "oscuro" else "luna")
    esquema = "dark" if modo() == "oscuro" else "light"
    st.html(f"<style>:root{{{variables};--icono-tema:{icono_tema};color-scheme:{esquema}}}\n"
            f"{_css_estatico(HOJA_ESTILOS.stat().st_mtime)}</style>")


def boton(clave: str = "boton_tema") -> None:
    ayuda = "Cambiar a tema claro" if modo() == "oscuro" else "Cambiar a tema oscuro"
    with st.container(key=f"botontema_{clave}"):
        st.button(" ", key=clave, on_click=alternar, help=ayuda)
