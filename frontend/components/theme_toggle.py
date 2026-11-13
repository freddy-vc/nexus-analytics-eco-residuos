import base64
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as componentes

from frontend.components import icons, session

RAIZ = Path(__file__).resolve().parents[2]
HOJA_ESTILOS = RAIZ / "frontend/styles/main.css"
COOKIE_TEMA = "eco_tema"

# Variable CSS de la interfaz y su opción equivalente en config.toml.
COLORES = {
    "bg": "backgroundColor", "sf": "secondaryBackgroundColor", "sf2": "dataframeHeaderBackgroundColor",
    "tx": "textColor", "mu": "grayTextColor", "bd": "borderColor", "ac": "primaryColor",
    "acs": "greenBackgroundColor", "act": "greenTextColor", "ag": "blueTextColor",
    "ags": "blueBackgroundColor", "wa": "orangeTextColor", "was": "orangeBackgroundColor",
    "er": "redTextColor", "ers": "redBackgroundColor",
}
MODOS = {"claro": "light", "oscuro": "dark"}
RUTAS = ["", "acceso"] + sorted(p.stem.replace("_", "-") for p in (RAIZ / "frontend/pages").glob("[!_]*.py"))


# Luminancia relativa de un color según WCAG.
def _luminancia(color: str) -> float:
    canales = [int(color.lstrip("#")[k:k + 2], 16) / 255 for k in (0, 2, 4)]
    # Linealización sRGB y L = 0,2126 R + 0,7152 G + 0,0722 B
    r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canales]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# Color con transparencia en formato rgba.
def _rgba(color: str, alfa: float) -> str:
    r, g, b = (int(color.lstrip("#")[k:k + 2], 16) for k in (0, 2, 4))
    return f"rgba({r},{g},{b},{alfa})"


# Paleta del modo leída de config.toml, con el color de texto sobre el acento y la sombra derivados.
def colores(nombre_modo: str) -> dict[str, str]:
    seccion = MODOS[nombre_modo]
    valores = {}
    for clave, opcion in COLORES.items():
        valor = st.get_option(f"theme.{seccion}.{opcion}")
        if not valor:
            raise RuntimeError(f"Falta theme.{seccion}.{opcion} en .streamlit/config.toml")
        valores[clave] = valor
    fondos = [valores[k] for k in ("bg", "sf", "sf2", "tx")]
    # El texto sobre el acento usa el fondo de mayor contraste con él.
    valores["on"] = (min if _luminancia(valores["ac"]) >= 0.5 else max)(fondos, key=_luminancia)
    claro = _luminancia(valores["bg"]) > 0.5
    valores["sh"] = (f"0 1px 2px {_rgba(valores['tx'], .04)}, 0 6px 20px {_rgba(valores['tx'], .04)}"
                     if claro else "none")
    return valores


# Modo activo; por defecto el guardado en la cookie o el del navegador.
def modo() -> str:
    if "tema" not in st.session_state:
        guardado = session.leer_cookie(COOKIE_TEMA)
        nativo = "oscuro" if st.context.theme.type == "dark" else "claro"
        st.session_state.tema = guardado if guardado in MODOS else nativo
    return st.session_state.tema


# Paleta del modo activo.
def paleta() -> dict[str, str]:
    return colores(modo())


# Cambia entre el modo claro y el oscuro.
def alternar() -> None:
    st.session_state.tema = "oscuro" if modo() == "claro" else "claro"
    session.programar_cookie(COOKIE_TEMA, st.session_state.tema, 365 * 24 * 3600)


# Hoja de estilos con las fuentes embebidas; se vuelve a leer cuando cambia su versión.
@st.cache_resource
def _css_estatico(version: float) -> str:
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
                       "genetico", "sensibilidad", "escenarios", "comparacion"))
    iconos_accion = (f'[class*="st-key-accion_editar"]{{--icono:{icons.url_mascara("editar")};}}\n'
                     f'[class*="st-key-accion_eliminar"]{{--icono:{icons.url_mascara("eliminar")};}}\n'
                     f':root{{--icono-buscar:{icons.url_mascara("buscar")};}}\n')
    estilos = HOJA_ESTILOS.read_text(encoding="utf-8")
    return fuentes + icons.css_iconos() + iconos_nav + iconos_accion + estilos


# Aplica las variables de color del modo activo y la hoja de estilos.
def aplicar() -> None:
    variables = ";".join(f"--{clave}:{valor}" for clave, valor in paleta().items())
    icono_tema = icons.url_mascara("sol" if modo() == "oscuro" else "luna")
    esquema = "dark" if modo() == "oscuro" else "light"
    st.html(f"<style>:root{{{variables};--icono-tema:{icono_tema};color-scheme:{esquema}}}\n"
            f"{_css_estatico(HOJA_ESTILOS.stat().st_mtime)}</style>")
    _sincronizar_streamlit()


# Sincroniza el tema de los componentes nativos de Streamlit con el modo activo.
def _sincronizar_streamlit() -> None:
    tema = json.dumps("Dark" if modo() == "oscuro" else "Light")
    with st.container(key="cookies_tema"):
        componentes.html(
            f"<script>const p = window.parent, tema = {json.dumps(tema)};"
            f"const clave = r => `stActiveTheme-${{r}}-v2`;"
            f"if (p.localStorage.getItem(clave(p.location.pathname)) !== tema) {{"
            f"for (const r of {json.dumps(['/' + r for r in RUTAS])}.concat([p.location.pathname]))"
            f" p.localStorage.setItem(clave(r), tema);"
            f"p.document.cookie = '{COOKIE_TEMA}={modo()}; path=/; max-age=31536000; SameSite=Lax';"
            f"const ultima = Number(p.sessionStorage.getItem('eco_recarga_tema') || 0);"
            f"if (Date.now() - ultima > 10000) {{ p.sessionStorage.setItem('eco_recarga_tema', Date.now());"
            f" p.location.reload(); }} }}</script>", height=0)


# Botón que alterna el tema.
def boton(clave: str = "boton_tema") -> None:
    ayuda = "Cambiar a tema claro" if modo() == "oscuro" else "Cambiar a tema oscuro"
    with st.container(key=f"botontema_{clave}"):
        st.button(" ", key=clave, on_click=alternar, help=ayuda)
