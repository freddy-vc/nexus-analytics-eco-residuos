from typing import Callable

import streamlit as st

from frontend.components import session, theme_toggle
from frontend.components.auth_guard import usuario_actual


def _seleccionar_escenario():
    st.session_state.escenario_activo = st.session_state.cabecera_escenario


def mostrar(seccion: str, titulo: str, *, etiqueta_escenario: str | None = "Escenario",
            acciones: Callable[[], None] | None = None) -> None:
    """Barra superior de cada página: título, escenario activo, tema y usuario."""
    usuario = usuario_actual()
    with st.container(key="cabecera_app"):
        izquierda, derecha = st.columns([1, 1.5], vertical_alignment="center")
        izquierda.html(f'<div class="titulo-pagina"><span>{seccion}</span><h1>{titulo}</h1></div>')
        with derecha.container(horizontal=True, horizontal_alignment="right",
                               vertical_alignment="center", gap="small"):
            if etiqueta_escenario:
                opciones = session.escenarios()
                if opciones:
                    nombres = {e.id: e.nombre for e in opciones}
                    ids = list(nombres)
                    activo = session.id_escenario_activo()
                    st.html(f'<span class="etiqueta-linea">{etiqueta_escenario}</span>')
                    with st.container(key="caja_escenario"):
                        st.selectbox(etiqueta_escenario, ids, index=ids.index(activo),
                                     format_func=nombres.get, key="cabecera_escenario",
                                     label_visibility="collapsed", on_change=_seleccionar_escenario)
            if acciones:
                acciones()
            theme_toggle.boton()
            if usuario:
                st.html(f'<div class="avatar"><b>{usuario.iniciales}</b><span><strong>{usuario.rol}</strong>'
                        f'<small>{usuario.usuario}</small></span></div>')
