import numpy as np
import streamlit as st

from backend.services.scenario_service import ServicioEscenarios
from backend.utils.exceptions import ErrorEcoResiduos
from frontend.components import header, session
from frontend.components import formatters as fmt

header.mostrar("Datos de la red", "Rutas, distancias y costos")
escenario = session.cargar_escenario()
m, n = len(escenario.empresas), len(escenario.plantas)
costos = escenario.costos_unitarios


def recalcular():
    distancias = {
        int(ruta_id): float(st.session_state.get(f"num_d_{ruta_id}", escenario.distancias[i, j]))
        for (i, j), ruta_id in np.ndenumerate(escenario.ids_rutas) if ruta_id}
    try:
        ServicioEscenarios().guardar_alfa(escenario.id, float(st.session_state[f"grande_alfa_{escenario.id}"]))
        ServicioEscenarios().guardar_distancias(distancias)
    except ErrorEcoResiduos as error:
        session.avisar(str(error), ":material/error:")
        return
    session.avisar("Distancias y costos unitarios actualizados.")


superior = st.columns([1, 1, 1.25], gap="medium")
with superior[0].container(key="tarjeta_alfa"):
    st.html('<span class="mu" style="font-size:13px">Costo de transporte (COP/t·km)</span>')
    with st.container(key="grande_alfa_caja"):
        st.number_input("Costo de transporte", min_value=0.01, step=10.0, format="%g",
                        value=round(escenario.alfa_efectivo, 2), key=f"grande_alfa_{escenario.id}",
                        label_visibility="collapsed")

superior[1].html(f'<div class="tarjeta mini-tarjeta"><span>Arcos de la red</span>'
                 f'<strong>{int(escenario.habilitadas.sum())} rutas habilitadas</strong>'
                 f'<small>{m} fuentes × {n} plantas · grafo bipartito</small></div>')

with st.container(key="tarjeta_matriz"):
    with st.container(horizontal=True, vertical_alignment="center"):
        with st.container(key="pestanas_matriz"):
            vista = st.radio("Matriz", ["Distancias (km)", "Costos unitarios (COP/t)"],
                             horizontal=True, key="vista_matriz", label_visibility="collapsed")
        st.html('<div class="espaciador"></div>')
        with st.container(key="barra_recalcular"):
            st.button("Recalcular costos", type="primary", on_click=recalcular)

    ver_distancias = vista.startswith("Distancias")
    anchos = [2.3] + [1.0] * n + [0.6]
    cabecera = st.columns(anchos, vertical_alignment="bottom", gap="small")
    cabecera[0].html('<div class="th">Empresa</div>')
    for j, planta in enumerate(escenario.plantas):
        cabecera[j + 1].html(f'<div class="th" style="text-align:right">{planta.codigo} {planta.municipio}</div>')
    cabecera[-1].html('<div class="th" style="text-align:right">Oferta (t/sem)</div>')

    for i, empresa in enumerate(escenario.empresas):
        fila = st.columns(anchos, vertical_alignment="center", gap="small")
        fila[0].html(f'<div class="matriz-etiqueta"><strong class="act">{empresa.codigo}</strong> '
                     f'<span>{fmt.nombre_corto(empresa.nombre)}</span></div>')
        mejor = np.nanargmin(np.where(escenario.habilitadas[i], costos[i], np.nan)) \
            if escenario.habilitadas[i].any() else -1
        for j in range(n):
            ruta_id = int(escenario.ids_rutas[i, j])
            with fila[j + 1]:
                if not ruta_id:
                    st.html('<div class="celda-caja tenue">—</div>')
                elif ver_distancias:
                    with st.container(key=f"num_celda_{ruta_id}"):
                        st.number_input(f"{empresa.codigo} a {escenario.plantas[j].codigo}", min_value=0.0,
                                        step=1.0, format="%g", value=float(escenario.distancias[i, j]),
                                        key=f"num_d_{ruta_id}", label_visibility="collapsed")
                else:
                    clase = "mejor" if j == mejor else ("tenue" if not escenario.habilitadas[i, j] else "")
                    valor = fmt.moneda(costos[i, j]) if escenario.habilitadas[i, j] else "Sin distancia"
                    st.html(f'<div class="celda-caja {clase}">{valor}</div>')
        fila[-1].html(f'<div class="celda-num">{fmt.cantidad(empresa.oferta)}</div>')

    pie = st.columns(anchos, gap="small")
    pie[0].html('<div style="font-weight:700;padding:10px 0">Demanda (t/sem)</div>')
    for j, planta in enumerate(escenario.plantas):
        pie[j + 1].html(f'<div class="celda-num" style="font-weight:700;padding:10px 12px 10px 0">'
                        f'{fmt.cantidad(planta.demanda)}</div>')
    pie[-1].html(f'<div class="celda-num" style="font-weight:700;padding:10px 0">'
                 f'{fmt.cantidad(escenario.demanda.sum())}</div>')

    pista = ("Distancias viales estimadas en kilómetros. Una ruta con distancia 0 queda deshabilitada. "
             "Edite una celda y pulse Recalcular costos para actualizar los costos unitarios."
             if ver_distancias else
             f"Costo por tonelada enviada: transporte ({fmt.cantidad(escenario.alfa_efectivo)} COP/t·km) "
             f"más costo de operación de la planta y precio pagado a la empresa. "
             f"En verde, la planta más económica para cada empresa.")
    st.html(f'<p class="pista" style="font-size:13px">{pista}</p>')
