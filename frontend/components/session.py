"""Estado compartido entre páginas: escenario activo, avisos diferidos y cookies."""

import json

import streamlit as st
import streamlit.components.v1 as componentes

from backend.services.scenario_service import DatosEscenario, ResumenEscenario, ServicioEscenarios
from backend.utils.exceptions import ErrorEcoResiduos


def escenarios() -> list[ResumenEscenario]:
    return ServicioEscenarios().listar()


def id_escenario_activo() -> int | None:
    ids = [e.id for e in escenarios()]
    if st.session_state.get("escenario_activo") not in ids:
        st.session_state.escenario_activo = ids[0] if ids else None
    return st.session_state.escenario_activo


def cargar_escenario() -> DatosEscenario:
    escenario_id = id_escenario_activo()
    if escenario_id is None:
        st.warning("No hay escenarios registrados. Ejecuta el script de la base de datos.")
        st.stop()
    try:
        return ServicioEscenarios().cargar(escenario_id)
    except ErrorEcoResiduos as error:
        st.error(str(error))
        st.stop()


def avisar(mensaje: str, icono: str = ":material/check_circle:") -> None:
    """Muestra un aviso en la siguiente ejecución (sobrevive a st.rerun)."""
    st.session_state.setdefault("_avisos", []).append((mensaje, icono))


def mostrar_avisos() -> None:
    for mensaje, icono in st.session_state.pop("_avisos", []):
        st.toast(mensaje, icon=icono)


def leer_cookie(nombre: str) -> str | None:
    return st.context.cookies.get(nombre)


def programar_cookie(nombre: str, valor: str, segundos_vida: int) -> None:
    """Deja una cookie pendiente; se escribe en el navegador en la siguiente ejecución.

    Streamlit no permite fijar cookies desde el servidor, así que se escriben con
    un componente HTML que comparte origen con la aplicación. Con segundos_vida = 0
    la cookie se elimina.
    """
    st.session_state.setdefault("_cookies", {})[nombre] = (valor, segundos_vida)


def escribir_cookies() -> None:
    pendientes = st.session_state.pop("_cookies", None)
    if not pendientes:
        return
    asignaciones = [f"{nombre}={valor}; path=/; max-age={vida}; SameSite=Lax"
                    for nombre, (valor, vida) in pendientes.items()]
    with st.container(key="cookies"):
        componentes.html(
            f"<script>for (const c of {json.dumps(asignaciones)}) "
            f"window.parent.document.cookie = c;</script>", height=0)
