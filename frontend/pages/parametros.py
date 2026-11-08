import streamlit as st

from backend.network.balance import TipoBalance, validar_datos, verificar_balance
from backend.network.cost_matrix import alfa_efectivo, factor_desde_costo
from backend.services.scenario_service import ServicioEscenarios
from backend.utils.exceptions import ErrorEcoResiduos
from frontend.components import header, session
from frontend.components import formatters as fmt
from frontend.components.kpi_cards import verificacion

escenario = session.cargar_escenario()
CLAVE_COSTO, CLAVE_FACTOR = f"par_costo_{escenario.id}", f"par_factor_{escenario.id}"
st.session_state.setdefault(CLAVE_COSTO, round(escenario.alfa_efectivo, 2))
st.session_state.setdefault(CLAVE_FACTOR, escenario.factor_transporte)
verificaciones = validar_datos(escenario.oferta, escenario.demanda, escenario.distancias,
                               escenario.costos_operacion, escenario.alfa, escenario.precios_compra,
                               escenario.habilitadas)


def guardar():
    estado = st.session_state
    try:
        ServicioEscenarios().guardar_parametros(
            escenario.id, estado.par_nombre, float(estado[CLAVE_FACTOR]),
            {e.id_vinculo: (float(estado[f"num_o_{e.id_vinculo}"]), float(estado[f"num_precio_{e.id_vinculo}"]))
             for e in escenario.empresas},
            {p.id_vinculo: (float(estado[f"num_dem_{p.id_vinculo}"]), float(estado[f"num_costo_{p.id_vinculo}"]))
             for p in escenario.plantas})
    except ErrorEcoResiduos as error:
        session.avisar(str(error), ":material/error:")
        return
    session.avisar("Escenario guardado.")


def validar():
    pendientes = [v.titulo for v in verificaciones if not v.cumple]
    if pendientes:
        session.avisar("Revisar: " + ", ".join(pendientes).lower() + ".", ":material/warning:")
    else:
        session.avisar("Los datos del escenario son válidos.")


def acciones():
    with st.container(key="barra_validar"):
        st.button("Validar datos", on_click=validar)
    with st.container(key="barra_guardar"):
        st.button("Guardar escenario", type="primary", on_click=guardar)


def costo_cambiado():
    """Al escribir el costo de transporte se recalcula el factor sobre el costo base."""
    costo = st.session_state[CLAVE_COSTO] or 0.0
    if costo > 0:
        st.session_state[CLAVE_FACTOR] = factor_desde_costo(costo, escenario.alfa)


def factor_cambiado():
    """Al cambiar el factor se recalcula el costo de transporte."""
    factor = st.session_state[CLAVE_FACTOR] or 0.0
    st.session_state[CLAVE_COSTO] = round(alfa_efectivo(escenario.alfa, factor), 2)


PROPORCION = [1.05, 0.95, 1.2]


def campo_numero(etiqueta: str, clave: str, valor: float, paso: float, caja: str) -> None:
    with st.container(key=caja):
        st.number_input(etiqueta, min_value=0.0, step=paso, format="%g", value=valor, key=clave,
                        label_visibility="collapsed")


header.mostrar("Datos de la red", "Escenario y parámetros del modelo", etiqueta_escenario=None,
               acciones=acciones)

principal, lateral = st.columns([2.05, 1], gap="medium")
with principal.container(key="tarjeta_escenario"):
    c1, c2 = st.columns(2)
    c1.text_input("Nombre del escenario", value=escenario.nombre, key="par_nombre")
    c2.selectbox("Basado en", [escenario.origen or "— Escenario original —"], disabled=True,
                 key="par_origen")
    st.html('<h2 class="tarjeta-titulo" style="margin-top:8px">Coeficientes del modelo de negocio</h2>')
    c3, c4 = st.columns(2)
    with c3:
        with st.container(key="sufijo_cop_tkm"):
            st.number_input("Costo de transporte (COP/t·km)", min_value=0.01, step=10.0, format="%.2f",
                            key=CLAVE_COSTO, on_change=costo_cambiado)
        st.html(f'<p class="pista">Flete por tonelada-kilómetro. Costo base del escenario: '
                f'{fmt.cantidad(escenario.alfa)} COP/t·km.</p>')
    with c4:
        with st.container(key="sufijo_pct_base"):
            st.number_input("Factor de costo de transporte (%)", min_value=0.01, step=5.0, format="%.2f",
                            key=CLAVE_FACTOR, on_change=factor_cambiado)
        st.html('<p class="pista">Sube o baja el costo de transporte en ese porcentaje del costo base; '
                '100 % mantiene el costo base. Ambos campos se actualizan entre sí.</p>')

balance = verificar_balance(escenario.oferta, escenario.demanda)
color = "var(--act)" if balance.tipo is TipoBalance.BALANCEADO else "var(--wa)"
lateral.html(
    f'<div class="tarjeta" style="display:flex;flex-direction:column;gap:14px">'
    f'<h2 class="tarjeta-titulo">Validación del problema</h2>'
    f'{"".join(verificacion(v.titulo, v.detalle, v.cumple) for v in verificaciones)}'
    f'<div style="display:flex;flex-direction:column;gap:8px;background:var(--sf2);border-radius:12px;padding:14px">'
    f'<div style="display:flex;justify-content:space-between;font-size:13px"><span class="mu">Oferta total</span>'
    f'<strong>{fmt.toneladas(balance.oferta_total)}</strong></div>'
    f'<div style="display:flex;justify-content:space-between;font-size:13px"><span class="mu">Demanda total</span>'
    f'<strong>{fmt.toneladas(balance.demanda_total)}</strong></div>'
    f'<div style="display:flex;justify-content:space-between;font-size:13px"><span class="mu">Diferencia</span>'
    f'<strong style="color:{color}">{fmt.toneladas(abs(balance.diferencia))}</strong></div></div></div>')


def cabecera_tabla(titulo: str, columnas: tuple[tuple[str, str], ...]) -> list:
    """Título de la tarjeta y encabezado de cada columna con su unidad debajo."""
    st.html(f'<h2 class="tarjeta-titulo">{titulo}</h2>')
    celdas = st.columns(PROPORCION, vertical_alignment="bottom")
    for celda, (texto, unidad) in zip(celdas[1:], columnas):
        celda.html(f'<div class="th th-una-linea">{texto}<span class="th-unidad">{unidad.replace("/", "/<wbr>")}</span></div>')
    return celdas


with principal:
    columna_oferta, columna_plantas = st.columns(2, gap="medium")
    with columna_oferta.container(key="tarjeta_oferta"):
        cabecera_tabla("Oferta semanal", (("Oferta", "t/semana"), ("Costo por tonelada", "COP/t")))
        for empresa in escenario.empresas:
            etiqueta, oferta, precio = st.columns(PROPORCION, vertical_alignment="center")
            etiqueta.html(f'<span class="fila-etiqueta"><strong class="act">{empresa.codigo}</strong> '
                          f'{fmt.nombre_corto(empresa.nombre)}</span>')
            with oferta:
                campo_numero(f"Oferta {empresa.codigo}", f"num_o_{empresa.id_vinculo}", empresa.oferta, 1.0,
                             f"num_ocaja_{empresa.id_vinculo}")
            with precio:
                campo_numero(f"Precio {empresa.codigo}", f"num_precio_{empresa.id_vinculo}", empresa.precio,
                             500.0, f"num_pcaja_{empresa.id_vinculo}")

    with columna_plantas.container(key="tarjeta_plantas"):
        cabecera_tabla("Plantas", (("Demanda", "t/semana"), ("Costo de operación", "COP/t")))
        for planta in escenario.plantas:
            nombre, demanda, costo = st.columns(PROPORCION, vertical_alignment="center")
            nombre.html(f'<span class="fila-etiqueta"><strong class="act">{planta.codigo}</strong> '
                        f'{planta.municipio}</span>')
            with demanda:
                campo_numero(f"Demanda {planta.codigo}", f"num_dem_{planta.id_vinculo}", planta.demanda, 1.0,
                             f"num_dcaja_{planta.id_vinculo}")
            with costo:
                campo_numero(f"Costo {planta.codigo}", f"num_costo_{planta.id_vinculo}", planta.costo_operacion,
                             500.0, f"num_ccaja_{planta.id_vinculo}")
