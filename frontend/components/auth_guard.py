"""Sesión del usuario: se guarda en session_state y se recupera tras recargar la página.

Al iniciar sesión se escribe una cookie con un token firmado; en una carga nueva
(recarga del navegador) session_state está vacío y el usuario se restaura a
partir de esa cookie mientras no haya expirado.
"""

import streamlit as st

from backend.auth import ServicioAutenticacion, UsuarioSesion
from backend.config import Configuracion
from frontend.components import session

COOKIE_SESION = "eco_sesion"


def usuario_actual() -> UsuarioSesion | None:
    if "usuario" not in st.session_state and not st.session_state.get("_sesion_cerrada"):
        st.session_state.usuario = ServicioAutenticacion().validar_token(
            session.leer_cookie(COOKIE_SESION))
    return st.session_state.get("usuario")


def esta_autenticado() -> bool:
    return usuario_actual() is not None


def iniciar_sesion(usuario: UsuarioSesion) -> None:
    st.session_state.usuario = usuario
    st.session_state.pop("_sesion_cerrada", None)
    session.programar_cookie(COOKIE_SESION, ServicioAutenticacion().emitir_token(usuario),
                             Configuracion().horas_sesion * 3600)


def cerrar_sesion() -> None:
    tema = st.session_state.get("tema")
    st.session_state.clear()
    if tema:
        st.session_state.tema = tema
    st.session_state._sesion_cerrada = True
    session.programar_cookie(COOKIE_SESION, "", 0)
