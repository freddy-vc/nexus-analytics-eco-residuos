import streamlit as st

from backend.services.network_service import DatosEmpresa, ServicioRed
from backend.services.scenario_service import DatosEscenario, FilaEmpresa
from backend.utils.exceptions import ErrorEcoResiduos
from frontend.components import header, session
from frontend.components import formatters as fmt
from frontend.components.kpi_cards import insignia

COLUMNAS = [0.75, 2.0, 1.45, 1.9, 0.95, 0.95]
servicio = ServicioRed()

header.mostrar("Datos de la red", "Empresas agropecuarias (fuentes)")
escenario: DatosEscenario = session.cargar_escenario()
nombres_municipio = {m.id: m.nombre for m in servicio.municipios()}
nombres_tipo = {t.id: t.nombre for t in servicio.tipos_residuo()}


def campos_empresa(prefijo: str, fila: FilaEmpresa | None, codigo: str) -> DatosEmpresa:
    """Campos comunes del formulario de empresa; devuelve los valores capturados."""
    c1, c2 = st.columns(2)
    codigo = c1.text_input("Código", value=codigo, key=f"{prefijo}_codigo")
    nit = c2.text_input("NIT", value=(fila.nit or "") if fila else "", placeholder="Opcional",
                        key=f"{prefijo}_nit")
    nombre = st.text_input("Nombre de la empresa", value=fila.nombre if fila else "",
                           key=f"{prefijo}_nombre")
    ids_municipio = list(nombres_municipio)
    municipio = st.selectbox("Municipio", ids_municipio, format_func=nombres_municipio.get,
                             index=ids_municipio.index(fila.municipio_id) if fila else 0,
                             key=f"{prefijo}_municipio")
    ids_tipo = list(nombres_tipo)
    tipo = st.selectbox("Tipo de residuo", ids_tipo, format_func=nombres_tipo.get,
                        index=ids_tipo.index(fila.tipo_residuo_id) if fila else 0, key=f"{prefijo}_tipo")
    c3, c4 = st.columns(2)
    oferta = c3.number_input("Oferta (t/sem)", min_value=0.0, step=1.0, format="%g",
                             value=fila.oferta if fila else 0.0, key=f"{prefijo}_oferta")
    precio = c4.number_input("Precio (COP/t)", min_value=0.0, step=500.0, format="%g",
                             value=fila.precio if fila else 12000.0, key=f"{prefijo}_precio")
    return DatosEmpresa(codigo, nombre, nit, municipio, tipo, oferta, precio)


@st.dialog("Nueva empresa")
def dialogo_crear():
    datos = campos_empresa("nueva", None, servicio.siguiente_codigo("E"))
    st.html('<p class="pista">Se crearán sus rutas hacia todas las plantas; registra las distancias '
            'en Rutas y costos.</p>')
    if st.button("Crear empresa", type="primary", width="stretch"):
        try:
            servicio.crear_empresa(escenario.id, datos)
        except ErrorEcoResiduos as error:
            st.error(str(error))
            return
        session.avisar(f"Empresa {datos.codigo.upper()} creada.")
        st.rerun()


@st.dialog("Eliminar empresa")
def dialogo_eliminar(fila: FilaEmpresa):
    st.html(f'<p style="font-size:14px">¿Eliminar la empresa <strong>{fila.codigo} · {fila.nombre}</strong> '
            f'({fila.municipio})? Se borrarán sus rutas y resultados en todos los escenarios. '
            f'Esta acción no se puede deshacer.</p>')
    cancelar, confirmar = st.columns(2)
    if cancelar.button("Cancelar", width="stretch"):
        st.rerun()
    if confirmar.button("Eliminar", type="primary", width="stretch"):
        servicio.eliminar_empresa(fila.empresa_id)
        session.avisar(f"Empresa {fila.codigo} eliminada.")
        st.rerun()


@st.dialog("Editar empresa")
def dialogo_editar(fila: FilaEmpresa):
    estado = insignia("Activa") if fila.activa else insignia("Inactiva", "wa")
    st.html(f'<div class="tarjeta-cabecera"><span class="mu" style="font-size:14px">{fila.codigo} · '
            f'{fila.nombre}</span>{estado}</div>')
    datos = campos_empresa(f"editar{fila.empresa_id}", fila, fila.codigo)
    st.html('<p class="pista">Los valores deben ser mayores o iguales a 0. Al guardar se revalida '
            'el balance oferta–demanda.</p>')
    cancelar, guardar = st.columns(2)
    if cancelar.button("Cancelar", width="stretch"):
        st.rerun()
    if guardar.button("Guardar cambios", type="primary", width="stretch"):
        try:
            servicio.actualizar_empresa(fila.empresa_id, fila.id_vinculo, datos)
        except ErrorEcoResiduos as error:
            st.error(str(error))
            return
        session.avisar(f"Empresa {datos.codigo.strip().upper()} actualizada.")
        st.rerun()


with st.container(horizontal=True, vertical_alignment="center"):
    with st.container(key="barra_buscar"):
        consulta = st.text_input("Buscar empresa", placeholder="Buscar empresa",
                                 label_visibility="collapsed", key="buscar_empresa")
    st.html('<span class="etiqueta-linea">Municipio</span>')
    with st.container(key="barra_municipio"):
        filtro_municipio = st.selectbox("Municipio", ["Todos", *nombres_municipio.values()],
                                        label_visibility="collapsed", key="filtro_municipio")
    st.html('<div class="espaciador"></div>')
    with st.container(key="barra_nueva"):
        if st.button("+ Nueva empresa", type="primary"):
            dialogo_crear()

filas = [f for f in escenario.empresas
         if (filtro_municipio == "Todos" or f.municipio == filtro_municipio)
         and (not consulta or consulta.lower() in f"{f.codigo} {f.nombre} {f.municipio} {f.nit or ''} "
                                                  f"{f.tipo_residuo}".lower())]
with st.container(key="tarjeta_empresas"):
    with st.container(key="cabeceraemp"):
        cabecera = st.columns(COLUMNAS, vertical_alignment="center")
    for columna, (titulo, alineacion) in zip(cabecera, [
            ("Código", "c"), ("Empresa", "i"), ("Municipio", "i"), ("Tipo de residuo", "i"),
            ("Oferta (t/sem)", "c"), ("Acciones", "c")]):
        columna.html(f'<div class="th" style="text-align:{"center" if alineacion == "c" else "left"}">'
                     f'{titulo}</div>')
    for fila in filas:
        with st.container(key=f"filaemp_{fila.empresa_id}"):
            celdas = st.columns(COLUMNAS, vertical_alignment="center")
            celdas[0].html(f'<div class="celda-codigo" style="text-align:center">{fila.codigo}</div>')
            celdas[1].html(f'<span>{fila.nombre}</span>')
            celdas[2].html(f'<span class="celda-tenue">{fila.municipio}</span>')
            celdas[3].html(f'<span class="celda-tenue">{fila.tipo_residuo}</span>')
            celdas[4].html(f'<div class="celda-num" style="text-align:center">{fmt.cantidad(fila.oferta)}</div>')
            with celdas[5].container(horizontal=True, horizontal_alignment="center", gap="small"):
                if st.button(" ", key=f"accion_editar_{fila.empresa_id}", help=f"Editar {fila.codigo}"):
                    dialogo_editar(fila)
                if st.button(" ", key=f"accion_eliminar_{fila.empresa_id}", help=f"Eliminar {fila.codigo}"):
                    dialogo_eliminar(fila)
    if not filas:
        st.html('<p class="pista" style="padding:16px">No hay empresas que coincidan con la búsqueda.</p>')
    st.html(f'<div class="pie-emp"><span>Total oferta semanal · {len(escenario.empresas)} empresas'
            f'</span><span>{fmt.cantidad(escenario.oferta.sum())} t</span></div>')
