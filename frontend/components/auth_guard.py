import streamlit as st

from backend.auth import ServicioAutenticacion, UsuarioSesion
from backend.config import Configuracion
from frontend.components import session

COOKIE_SESION = "eco_sesion"


# Usuario de la sesión; tras una recarga se restaura desde la cookie firmada.
def usuario_actual() -> UsuarioSesion | None:
    if "usuario" not in st.session_state and not st.session_state.get("_sesion_cerrada"):
        st.session_state.usuario = ServicioAutenticacion().validar_token(
            session.leer_cookie(COOKIE_SESION))
    return st.session_state.get("usuario")


# Indica si hay un usuario con sesión activa.
def esta_autenticado() -> bool:
    return usuario_actual() is not None


# Guarda el usuario en la sesión y programa la cookie con su token.
def iniciar_sesion(usuario: UsuarioSesion) -> None:
    st.session_state.usuario = usuario
    st.session_state.pop("_sesion_cerrada", None)
    session.programar_cookie(COOKIE_SESION, ServicioAutenticacion().emitir_token(usuario),
                             Configuracion().horas_sesion * 3600)


# Cierra la sesión, conserva el tema elegido y elimina la cookie.
def cerrar_sesion() -> None:
    tema = st.session_state.get("tema")
    st.session_state.clear()
    if tema:
        st.session_state.tema = tema
    st.session_state._sesion_cerrada = True
    session.programar_cookie(COOKIE_SESION, "", 0)
