import streamlit as st

from backend.network.graph_builder import NodoRed, construir_red, resumir
from backend.services.genetic_service import ServicioGenetico
from backend.services.optimization_service import ServicioOptimizacion
from frontend.components import header, network_graph, session, theme_toggle
from frontend.components import formatters as fmt
from frontend.components.kpi_cards import clave_valor, insignia

header.mostrar("Optimización", "Red logística G = (V, A)")
escenario = session.cargar_escenario()
ejecucion = ServicioOptimizacion().ultima_exacta(escenario)
lote = ServicioGenetico().ultimo_lote(escenario)
SOLUCIONES = ["Exacto (Simplex)"] + (["Algoritmo genético (mejor corrida)"] if lote else [])
if st.session_state.get("solucion_grafo") not in SOLUCIONES:
    st.session_state.solucion_grafo = SOLUCIONES[0]
if st.session_state.solucion_grafo == SOLUCIONES[0]:
    flujos = ejecucion.flujos if ejecucion and ejecucion.flujos is not None else None
else:
    flujos = lote.flujos_mejor

origenes = [NodoRed(e.codigo, e.municipio, e.oferta, e.municipio, e.latitud, e.longitud)
            for e in escenario.empresas]
destinos = [NodoRed(p.codigo, p.municipio, p.demanda, p.municipio, p.latitud, p.longitud)
            for p in escenario.plantas]
grafo = construir_red(origenes, destinos, escenario.distancias, escenario.costos_unitarios,
                      escenario.habilitadas, flujos)
resumen = resumir(grafo)

columna_grafo, columna_detalle = st.columns([2.6, 1], gap="medium")
with columna_grafo.container(key="tarjeta_grafo"):
    with st.container(horizontal=True, vertical_alignment="center"):
        with st.container(key="pestanas_grafo"):
            vista = st.radio("Vista", ["Todas las rutas", "Flujos óptimos"], index=1, horizontal=True,
                             key="vista_grafo", label_visibility="collapsed")
        st.html('<div class="espaciador"></div>')
        st.html('<span class="etiqueta-linea">Solución</span>')
        with st.container(key="caja_solucion"):
            st.selectbox("Solución", SOLUCIONES, key="solucion_grafo", label_visibility="collapsed")
    ver_flujos = vista == "Flujos óptimos"
    if ver_flujos and flujos is None:
        st.html('<div class="nota wa">Aún no hay una solución para este escenario; '
                'resuélvela en Método exacto para ver los flujos óptimos.</div>')
    if grafo.number_of_nodes():
        network_graph.mostrar(grafo, ver_flujos and flujos is not None, theme_toggle.paleta())
    else:
        st.html('<div class="nota wa">El grafo necesita al menos una empresa y una planta.</div>')

with columna_detalle:
    st.html(f'<div class="tarjeta" style="display:flex;flex-direction:column;gap:12px">'
            f'<h2 class="tarjeta-titulo">Resumen del grafo</h2>'
            f'{clave_valor("Nodos fuente |V<sub>O</sub>|", str(resumen.origenes), simple=True)}'
            f'{clave_valor("Nodos destino |V<sub>D</sub>|", str(resumen.destinos), simple=True)}'
            f'{clave_valor("Arcos |A|", str(resumen.arcos), simple=True)}'
            f'{clave_valor("Arcos con flujo &gt; 0", str(resumen.arcos_con_flujo) if flujos is not None else "—", simple=True)}'
            f'</div>')

    with st.container(key="tarjeta_arco"):
        if escenario.empresas and escenario.plantas:
            indice_origen = {e.codigo: i for i, e in enumerate(escenario.empresas)}
            indice_destino = {p.codigo: j for j, p in enumerate(escenario.plantas)}
            elegir_origen, elegir_destino = st.columns(2)
            codigo_origen = elegir_origen.selectbox("Origen", list(indice_origen), key="arco_origen")
            codigo_destino = elegir_destino.selectbox("Destino", list(indice_destino), key="arco_destino")
            i, j = indice_origen[codigo_origen], indice_destino[codigo_destino]
            activo = bool(escenario.habilitadas[i, j])
            flujo = float(flujos[i, j]) if flujos is not None else None
            costo = float(escenario.costos_unitarios[i, j])
            st.html(
                f'<div style="display:flex;flex-direction:column;gap:12px">'
                f'<div class="tarjeta-cabecera"><h2 class="tarjeta-titulo">Arco seleccionado</h2>'
                f'{insignia("Activo") if activo else insignia("Deshabilitado", "wa")}</div>'
                f'<strong style="font-size:22px">{codigo_origen} → {codigo_destino}</strong>'
                f'<span class="mu" style="font-size:13px">{escenario.empresas[i].municipio} → '
                f'{escenario.plantas[j].municipio}</span>'
                f'{clave_valor("Distancia dᵢⱼ", fmt.toneladas(escenario.distancias[i, j], "km"))}'
                f'{clave_valor("Costo unitario cᵢⱼ", fmt.moneda(costo) + " /t" if activo else "—")}'
                f'{clave_valor("Flujo óptimo xᵢⱼ", fmt.toneladas(flujo) if flujo is not None else "—")}'
                f'{clave_valor("Costo del arco", fmt.moneda(costo * flujo) if flujo is not None and activo else "—")}'
                f'</div>')
