import streamlit as st

from backend.services.network_service import DatosPlanta, ServicioRed
from backend.services.optimization_service import ServicioOptimizacion
from backend.services.scenario_service import FilaPlanta
from backend.utils.exceptions import ErrorEcoResiduos
from frontend.components import charts, header, icons, session
from frontend.components import formatters as fmt
from frontend.components.kpi_cards import insignia

POR_FILA = 4
servicio = ServicioRed()

header.mostrar("Datos de la red", "Plantas de recepción y transformación")
escenario = session.cargar_escenario()
ejecucion = ServicioOptimizacion().ultima_exacta(escenario)
municipios = {m.id: m.nombre for m in servicio.municipios()}
ids_municipio = list(municipios)


def campos_planta(prefijo: str, fila: FilaPlanta | None, codigo: str) -> DatosPlanta:
    celdas = st.columns(2)
    codigo = celdas[0].text_input("Código", value=codigo, key=f"{prefijo}_codigo")
    municipio = celdas[1].selectbox(
        "Municipio", ids_municipio, format_func=municipios.get, key=f"{prefijo}_municipio",
        index=ids_municipio.index(fila.municipio_id) if fila else None, placeholder="Seleccionar…")
    celdas = st.columns(2)
    demanda = celdas[-2].number_input("Demanda (t/semana)", min_value=0.0, step=1.0, format="%g",
                                      value=fila.demanda if fila else 0.0, key=f"{prefijo}_demanda")
    costo = celdas[-1].number_input("Costo operación (COP/t)", min_value=0.0, step=500.0, format="%g",
                                    value=fila.costo_operacion if fila else 0.0, key=f"{prefijo}_costo")
    return DatosPlanta(codigo, municipio, demanda, costo)


def crear(datos: DatosPlanta) -> bool:
    try:
        servicio.crear_planta(escenario.id, datos)
    except ErrorEcoResiduos as error:
        st.error(str(error))
        return False
    session.avisar(f"Planta {datos.codigo.strip().upper()} creada.")
    return True


@st.dialog("Nueva planta")
def dialogo_crear():
    datos = campos_planta("dialogo_nueva", None, servicio.siguiente_codigo("P"))
    st.html('<p class="pista">Al crear la sede se generan sus rutas desde todas las empresas; '
            'complete las distancias en Rutas y costos.</p>')
    if st.button("Crear planta", type="primary", width="stretch") and crear(datos):
        st.rerun()


@st.dialog("Editar planta")
def dialogo_editar(fila: FilaPlanta):
    datos = campos_planta(f"editar{fila.planta_id}", fila, fila.codigo)
    if st.button("Guardar cambios", type="primary", width="stretch"):
        try:
            servicio.actualizar_planta(fila.planta_id, fila.id_vinculo, datos)
        except ErrorEcoResiduos as error:
            st.error(str(error))
            return
        session.avisar(f"Planta {datos.codigo.strip().upper()} actualizada.")
        st.rerun()


@st.dialog("Eliminar planta")
def dialogo_eliminar(fila: FilaPlanta):
    st.html(f'<p style="font-size:14px">¿Eliminar la planta <strong>{fila.codigo} · {fila.municipio}</strong>? '
            f'Se borrarán sus rutas y resultados en todos los escenarios. '
            f'Esta acción no se puede deshacer.</p>')
    cancelar, confirmar = st.columns(2)
    if cancelar.button("Cancelar", width="stretch"):
        st.rerun()
    if confirmar.button("Eliminar", type="primary", width="stretch"):
        servicio.eliminar_planta(fila.planta_id)
        session.avisar(f"Planta {fila.codigo} eliminada.")
        st.rerun()


with st.container(horizontal=True):
    with st.container(key="barra_nueva_planta"):
        if st.button("+ Nueva planta", type="primary"):
            dialogo_crear()

for inicio in range(0, len(escenario.plantas), POR_FILA):
    columnas = st.columns(POR_FILA, gap="medium")
    for columna, (j, planta) in zip(columnas, list(enumerate(escenario.plantas))[inicio:inicio + POR_FILA]):
        recibido = float(ejecucion.flujos[:, j].sum()) if ejecucion and ejecucion.flujos is not None else None
        porcentaje = recibido / planta.demanda * 100 if recibido is not None and planta.demanda else 0.0
        with columna.container(key=f"tarjeta_planta_{planta.planta_id}"):
            with st.container(horizontal=True, vertical_alignment="top"):
                st.html(f'<span class="mosaico-icono">{icons.icono("plantas", 26)}</span>')
                st.html('<div class="espaciador"></div>')
                with st.container(key=f"esquina_planta_{planta.planta_id}"):
                    st.html(insignia("Activa") if planta.activa else insignia("Inactiva", "wa"))
                    if st.button(" ", key=f"accion_eliminar_planta_{planta.planta_id}",
                                 help=f"Eliminar {planta.codigo}"):
                        dialogo_eliminar(planta)
            st.html(
                f'<div class="planta-tarjeta">'
                f'<div style="display:flex;flex-direction:column;gap:4px">'
                f'<span class="codigo" style="font-size:13px">{planta.codigo}</span>'
                f'<h2 style="margin:0;font-size:20px">{planta.municipio}</h2>'
                f'<span class="mu" style="font-size:13px">Destino · {planta.departamento}</span></div>'
                f'<dl class="planta-datos"><div><dt>Demanda</dt><dd>{fmt.toneladas(planta.demanda)}</dd></div>'
                f'<div><dt>Costo operación</dt><dd>{fmt.moneda(planta.costo_operacion)}<small> /t</small></dd></div></dl>'
                f'<div style="display:flex;flex-direction:column;gap:6px">'
                f'<div style="display:flex;justify-content:space-between;font-size:13px;color:var(--mu)">'
                f'<span>Utilización (exacto)</span>'
                f'<span>{fmt.porcentaje(porcentaje) if recibido is not None else "—"}</span></div>'
                f'{charts.progreso(porcentaje, delgada=True)}</div></div>')
            with st.container(key=f"acento_editar_{planta.planta_id}"):
                if st.button("Editar planta", key=f"editar_planta_{planta.planta_id}", width="stretch"):
                    dialogo_editar(planta)
