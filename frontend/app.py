import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402

from backend.services.scenario_service import ServicioEscenarios  # noqa: E402
from frontend.components import login_form, session, sidebar, theme_toggle  # noqa: E402
from frontend.components.auth_guard import esta_autenticado  # noqa: E402
from frontend.components.sidebar import EntradaMenu  # noqa: E402

st.set_page_config(page_title="EcoResiduos · Optimizador logístico",
                   page_icon=str(RAIZ / "assets/logo/icon.svg"),
                   layout="wide", initial_sidebar_state="expanded")
theme_toggle.aplicar()

try:
    ServicioEscenarios().listar()
except OperationalError:
    st.error("No fue posible conectar con PostgreSQL. Revisa los datos de conexión del archivo "
             ".env y que la base de datos esté creada con database/ecoresiduos_db.sql.")
    st.stop()


def pagina(archivo: str, titulo: str, ruta: str, inicial: bool = False) -> st.Page:
    return st.Page(f"pages/{archivo}.py", title=titulo, url_path=ruta, default=inicial)


SECCIONES = {
    "General": [EntradaMenu("inicio", "Inicio", pagina("inicio", "Inicio", "inicio", inicial=True))],
    "Datos de la red": [
        EntradaMenu("empresas", "Empresas", pagina("empresas", "Empresas", "empresas")),
        EntradaMenu("plantas", "Plantas", pagina("plantas", "Plantas", "plantas")),
        EntradaMenu("rutas", "Rutas y costos", pagina("rutas_costos", "Rutas y costos", "rutas-costos")),
        EntradaMenu("parametros", "Parámetros", pagina("parametros", "Parámetros", "parametros")),
    ],
    "Optimización": [
        EntradaMenu("red", "Red logística", pagina("red_logistica", "Red logística", "red-logistica")),
        EntradaMenu("exacto", "Método exacto", pagina("metodo_exacto", "Método exacto", "metodo-exacto")),
        EntradaMenu("genetico", "Algoritmo genético",
                    pagina("algoritmo_genetico", "Algoritmo genético", "algoritmo-genetico")),
    ],
    "Análisis": [
        EntradaMenu("sensibilidad", "Sensibilidad", pagina("sensibilidad", "Sensibilidad", "sensibilidad")),
        EntradaMenu("escenarios", "Escenarios", pagina("escenarios", "Escenarios", "escenarios")),
        EntradaMenu("comparacion", "Comparación", pagina("comparacion", "Comparación", "comparacion")),
    ],
}
PAGINAS = [e.pagina for entradas in SECCIONES.values() for e in entradas if not e.bloqueada]

session.escribir_cookies()

if not esta_autenticado():
    # Cada ruta muestra el inicio de sesión, así una recarga con la sesión vencida
    # no termina en «Page not found».
    acceso = [st.Page(login_form.mostrar, title="Iniciar sesión", url_path="acceso", default=True)]
    acceso += [st.Page(login_form.mostrar, title="Iniciar sesión", url_path=p.url_path)
               for p in PAGINAS if p.url_path]
    st.navigation(acceso, position="hidden").run()
    st.stop()

actual = st.navigation(PAGINAS, position="hidden")
sidebar.mostrar(SECCIONES, actual)
session.mostrar_avisos()
actual.run()
