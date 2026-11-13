import base64
from pathlib import Path

import streamlit as st

from backend.auth import ServicioAutenticacion
from backend.utils.exceptions import ErrorAutenticacion
from frontend.components import theme_toggle
from frontend.components.auth_guard import iniciar_sesion
from frontend.components.sidebar import uri_logo

RAIZ = Path(__file__).resolve().parents[2]


# Imagen de la portada como URI de datos.
@st.cache_resource
def _imagen_portada() -> str:
    datos = base64.b64encode((RAIZ / "assets/images/login.avif").read_bytes()).decode()
    return f"data:image/avif;base64,{datos}"


# Autentica al usuario e inicia la sesión, o muestra el error correspondiente.
def _enviar():
    try:
        usuario = ServicioAutenticacion().autenticar(st.session_state.acceso_usuario,
                                                     st.session_state.acceso_clave)
    except ErrorAutenticacion as error:
        st.session_state.acceso_error = str(error)
        return
    st.session_state.pop("acceso_error", None)
    iniciar_sesion(usuario)


# Pantalla de inicio de sesión.
def mostrar() -> None:
    with st.container(key="acceso_marco"):
        portada, panel = st.columns(2, gap="small")
        portada.html(f'<div class="acceso-portada" style="background-image:url({_imagen_portada()})" '
                     f'role="img" aria-label="Símbolo de reciclaje"></div>')
        with panel.container(key="acceso_panel"):
            with st.container(horizontal=True, horizontal_alignment="right"):
                theme_toggle.boton("tema_acceso")
            with st.container(key="acceso_formulario"):
                st.html(f'<img class="acceso-logo" src="{uri_logo()}" alt="EcoResiduos">'
                        '<div class="acceso-titulo"><h2>Iniciar sesión</h2>'
                        '<p>Ingresa con tu usuario institucional.</p></div>')
                with st.form("acceso", border=False, enter_to_submit=True):
                    st.text_input("Usuario o correo", key="acceso_usuario",
                                  placeholder="analista@ecoresiduos.local")
                    st.text_input("Contraseña", key="acceso_clave", type="password", placeholder="********")
                    if error := st.session_state.get("acceso_error"):
                        st.html(f'<div class="nota wa" role="alert">{error}</div>')
                    st.form_submit_button("Ingresar", type="primary", on_click=_enviar,
                                          width="stretch")
                st.html('<p class="acceso-pie">Acceso para el rol Analista.</p>')
