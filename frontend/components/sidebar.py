import base64
from dataclasses import dataclass
from pathlib import Path

import streamlit as st

from frontend.components import icons
from frontend.components.auth_guard import cerrar_sesion

RAIZ = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class EntradaMenu:
    clave: str
    titulo: str
    pagina: st.Page | None = None

    @property
    def bloqueada(self) -> bool:
        return self.pagina is None


@st.cache_resource
def uri_logo() -> str:
    datos = base64.b64encode((RAIZ / "assets/logo/ecoresiduos.svg").read_bytes()).decode()
    return f"data:image/svg+xml;base64,{datos}"


def mostrar(secciones: dict[str, list[EntradaMenu]], actual: st.Page) -> None:
    """Menú lateral: logo, secciones y enlaces con ícono.

    Los módulos de fases posteriores aparecen en gris y no navegan.
    """
    with st.sidebar:
        st.html(f'<div class="marca"><img src="{uri_logo()}" alt="EcoResiduos">')
        for titulo_seccion, entradas in secciones.items():
            st.html(f'<div class="nav-titulo">{titulo_seccion}</div>')
            for entrada in entradas:
                if entrada.bloqueada:
                    st.html(f'<div class="nav-bloqueado" aria-disabled="true" '
                            f'title="Disponible en una fase posterior del proyecto">'
                            f'{icons.icono(entrada.clave)}<span>{entrada.titulo}</span>'
                            f'{icons.icono("candado", 14)}</div>')
                    continue
                estado = "si" if entrada.pagina.url_path == actual.url_path else "no"
                with st.container(key=f"nav_{entrada.clave}_{estado}"):
                    st.page_link(entrada.pagina, label=entrada.titulo)
        st.html('<div style="height:16px"></div>')
        with st.container(key="salir"):
            if st.button("Cerrar sesión", key="cerrar_sesion", type="tertiary"):
                cerrar_sesion()
                st.rerun()
