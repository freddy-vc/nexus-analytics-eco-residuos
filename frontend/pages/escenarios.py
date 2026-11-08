import streamlit as st

from backend.services.optimization_service import METODO_EXACTO
from backend.services.scenario_service import ServicioEscenarios, TarjetaEscenario
from backend.utils.exceptions import ErrorEcoResiduos
from frontend.components import header, session
from frontend.components import formatters as fmt
from frontend.components.auth_guard import usuario_actual
from frontend.components.kpi_cards import insignia

POR_FILA = 3
servicio = ServicioEscenarios()

header.mostrar("Análisis", "Escenarios guardados")
tarjetas = servicio.resumenes(METODO_EXACTO)
costo_base = next((t.costo_exacto for t in tarjetas if t.es_base), None)


def descripcion(t: TarjetaEscenario) -> str:
    if t.descripcion:
        return t.descripcion
    factor = "" if t.factor_transporte == 100 else f" ({fmt.numero(t.factor_transporte, 1)} % del base)"
    return (f"{t.empresas} empresas, {t.plantas} plantas, costo de transporte = "
            f"{fmt.cantidad(round(t.alfa * t.factor_transporte / 100, 2))} COP/t·km{factor}")


def variacion(t: TarjetaEscenario) -> str:
    if t.es_base or t.costo_exacto is None or not costo_base:
        return "—"
    cambio = (t.costo_exacto - costo_base) / costo_base * 100
    signo = "+" if cambio > 0 else ("−" if cambio < 0 else "")
    return f"{signo}{fmt.numero(abs(cambio), 1)} %"


def abrir(escenario_id: int):
    st.session_state.escenario_activo = escenario_id
    st.session_state._abrir_parametros = True


def duplicar(t: TarjetaEscenario):
    try:
        servicio.duplicar(t.id, usuario_actual().id)
    except ErrorEcoResiduos as error:
        session.avisar(str(error), ":material/error:")
        return
    session.avisar(f"Se creó una copia de «{t.nombre}».")


@st.dialog("Nuevo escenario")
def dialogo_nuevo():
    nombres = {t.id: t.nombre for t in tarjetas}
    ids = list(nombres)
    activo = session.id_escenario_activo()
    nombre = st.text_input("Nombre del escenario", placeholder="Ej. Transporte +20 %")
    descripcion_nueva = st.text_input("Descripción (opcional)",
                                      placeholder="Ej. 900 COP/t·km o E7: 150 → 250 t")
    origen = st.selectbox("Basado en", ids, format_func=nombres.get,
                          index=ids.index(activo) if activo in ids else 0)
    st.html('<p class="pista">El nuevo escenario copia empresas, plantas, rutas y costos del escenario '
            'de origen; luego puedes modificarlos en Parámetros.</p>')
    if st.button("Crear escenario", type="primary", width="stretch"):
        try:
            nuevo_id = servicio.duplicar(origen, usuario_actual().id, nombre, descripcion_nueva)
        except ErrorEcoResiduos as error:
            st.error(str(error))
            return
        st.session_state.escenario_activo = nuevo_id
        session.avisar(f"Escenario «{nombre.strip() or 'copia'}» creado.")
        st.rerun()


if st.session_state.pop("_abrir_parametros", False):
    st.switch_page("pages/parametros.py")

seleccionados = [t.id for t in tarjetas if st.session_state.get(f"sel_esc_{t.id}")]
with st.container(horizontal=True, vertical_alignment="center"):
    with st.container(key="barra_buscar"):
        consulta = st.text_input("Buscar escenario", placeholder="Buscar escenario",
                                 label_visibility="collapsed", key="buscar_escenario")
    st.html('<div class="espaciador"></div>')
    with st.container(key="barra_comparar"):
        if st.button(f"Comparar seleccionados ({len(seleccionados)})", disabled=len(seleccionados) < 2,
                     help="Marca al menos dos escenarios para compararlos."):
            st.session_state.comparar_escenarios = seleccionados
            st.switch_page("pages/comparacion.py")
    with st.container(key="barra_nuevo_escenario"):
        if st.button("+ Nuevo escenario", type="primary"):
            dialogo_nuevo()

visibles = [t for t in tarjetas if not consulta or consulta.lower() in
            f"{t.nombre} {t.descripcion or ''}".lower()]
if not visibles:
    st.html('<p class="pista" style="font-size:14px">No hay escenarios que coincidan con la búsqueda.</p>')

for inicio in range(0, len(visibles), POR_FILA):
    columnas = st.columns(POR_FILA, gap="medium")
    for columna, t in zip(columnas, visibles[inicio:inicio + POR_FILA]):
        if t.es_base:
            estado = insignia("Base")
        elif t.balanceado:
            estado = insignia("Balanceado")
        else:
            estado = insignia("Desbalanceado", "wa")
        with columna.container(key=f"tarjeta_escenario_{t.id}"):
            with st.container(horizontal=True, vertical_alignment="top", gap="small"):
                with st.container(key=f"seleccion_{t.id}"):
                    st.checkbox(f"Seleccionar {t.nombre}", key=f"sel_esc_{t.id}", label_visibility="collapsed")
                st.html(f'<div class="escenario-titulo"><strong>{t.nombre}</strong>'
                        f'<span>{descripcion(t)}</span></div>')
                st.html(estado)
            costo = fmt.moneda(t.costo_exacto) if t.costo_exacto is not None else "Sin resolver"
            st.html(f'<div class="escenario-datos"><div><span>Costo exacto</span><strong>{costo}</strong></div>'
                    f'<div><span>vs. caso base</span><strong>{variacion(t)}</strong></div></div>')
            with st.container(horizontal=True, vertical_alignment="center", gap="small"):
                origen = "Escenario original" if not t.origen else f"Derivado de {t.origen}"
                st.html(f'<span class="escenario-origen">{origen}</span>')
                st.html('<div class="espaciador"></div>')
                with st.container(key=f"enlace_abrir_{t.id}"):
                    st.button("Abrir", key=f"abrir_{t.id}", type="tertiary", on_click=abrir, args=(t.id,))
                with st.container(key=f"enlace_duplicar_{t.id}"):
                    st.button("Duplicar", key=f"duplicar_{t.id}", type="tertiary", on_click=duplicar, args=(t,))
