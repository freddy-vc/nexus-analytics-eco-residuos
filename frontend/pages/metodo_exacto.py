import streamlit as st

from backend.network.balance import TipoBalance
from backend.services.optimization_service import ServicioOptimizacion
from backend.utils.exceptions import ErrorEcoResiduos
from frontend.components import charts, header, session
from frontend.components import formatters as fmt
from frontend.components.kpi_cards import clave_valor, dato, insignia

ETIQUETAS_ESTADO = {"OPTIMO": "Óptimo", "INFACTIBLE": "Infactible", "NO_ACOTADO": "No acotado",
                    "ERROR": "Sin solución"}
COLORES_COSTO = (("Transporte", "var(--ac)", 1), ("Operación", "var(--act)", .55), ("Compra", "var(--bd)", 1))

header.mostrar("Optimización", "Método exacto · Problema de transporte")
escenario = session.cargar_escenario()
servicio = ServicioOptimizacion()

columna_datos, columna_ejecucion = st.columns([3, 1], gap="medium")
with columna_ejecucion.container(key="tarjeta_ejecucion"):
    st.html('<h2 class="tarjeta-titulo">Ejecución</h2>')
    st.selectbox("Solucionador", ["Simplex de dos fases"], key="solucionador_exacto")
    if st.button("Resolver modelo", type="primary", width="stretch", key="resolver_exacto"):
        try:
            with st.spinner("Resolviendo con el método Simplex…"):
                servicio.resolver_exacto(escenario)
        except ErrorEcoResiduos as error:
            st.html(f'<div class="nota er">{error}</div>')
    ejecucion = servicio.ultima_exacta(escenario)
    st.html(f'<div style="display:flex;flex-direction:column;gap:6px">'
            f'<div style="display:flex;justify-content:space-between;font-size:13px;color:var(--mu)">'
            f'<span>{"Completado" if ejecucion else "Sin ejecutar"}</span>'
            f'<span>{fmt.segundos(ejecucion.milisegundos) if ejecucion else ""}</span></div>'
            f'{charts.progreso(100 if ejecucion else 0, delgada=True)}</div>')

with columna_datos:
    if ejecucion is None:
        st.html('<div class="tarjeta" style="text-align:center;padding:40px">'
                '<h2 class="tarjeta-titulo">Este escenario aún no se ha resuelto</h2>'
                '<p class="mu" style="margin:8px 0 0">Pulsa «Resolver modelo» para calcular la '
                'distribución de menor costo con el método Simplex.</p></div>')
        st.stop()

    etiqueta_estado = ETIQUETAS_ESTADO.get(ejecucion.estado, ejecucion.estado.capitalize())
    st.html('<section class="rejilla rejilla-tres">'
            + dato("Estado", etiqueta_estado,
                   f"Simplex · {ejecucion.num_variables} variables, {ejecucion.num_restricciones} restricciones",
                   resaltado=ejecucion.es_optima)
            + dato("Costo total reportado", fmt.moneda(ejecucion.costo_total),
                   "Compra, transporte y operación por semana")
            + dato("Tiempo de cómputo", fmt.segundos(ejecucion.milisegundos),
                   f"{ejecucion.iteraciones} iteraciones")
            + '</section>')

with columna_datos:
    if not ejecucion.es_optima or ejecucion.flujos is None:
        st.html(f'<div class="nota er">El modelo no tiene solución óptima ({etiqueta_estado.lower()}). '
                f'{ejecucion.mensaje or ""} Revisa oferta, demanda y rutas habilitadas.</div>')
        st.stop()

    if ejecucion.balance.tipo is not TipoBalance.BALANCEADO:
        if ejecucion.balance.tipo is TipoBalance.EXCESO_OFERTA:
            sobrante = escenario.oferta - ejecucion.flujos.sum(axis=1)
            detalle = ", ".join(f"{e.codigo}: {fmt.toneladas(v)}"
                                for e, v in zip(escenario.empresas, sobrante) if v > 1e-6)
            texto = f"{ejecucion.mensaje} Toneladas sin recolectar: {detalle}."
        else:
            ociosa = escenario.demanda - ejecucion.flujos.sum(axis=0)
            detalle = ", ".join(f"{p.codigo}: {fmt.toneladas(v)}"
                                for p, v in zip(escenario.plantas, ociosa) if v > 1e-6)
            texto = f"{ejecucion.mensaje} Capacidad sin usar: {detalle}."
        st.html(f'<div class="nota wa">{texto}</div>')

with columna_datos.container(key="tarjeta_flujos"):
    with st.container(horizontal=True, vertical_alignment="center"):
        st.html('<h2 class="tarjeta-titulo">Flujos óptimos (t/semana)</h2>')
        st.html('<div class="espaciador"></div>')
        with st.container(key="enlace_contorno_red"):
            st.page_link("pages/red_logistica.py", label="Ver en la red")

    costos = escenario.costos_unitarios
    cabecera = "".join(f'<th class="num">{p.codigo}</th>' for p in escenario.plantas)
    cuerpo = ""
    for i, empresa in enumerate(escenario.empresas):
        celdas = "".join(
            f'<td class="celda"><span class="{"flujo-si" if v > 1e-9 else "flujo-no"}">'
            f'{fmt.cantidad(v)}</span></td>' for v in ejecucion.flujos[i])
        costo_fila = float((ejecucion.flujos[i] * costos[i]).sum())
        cuerpo += (f'<tr><td style="white-space:nowrap"><strong class="act">{empresa.codigo}</strong> '
                   f'{fmt.nombre_corto(empresa.nombre)}</td>{celdas}'
                   f'<td class="num">{fmt.moneda(costo_fila)}</td></tr>')
    recibido = ejecucion.flujos.sum(axis=0)
    pie = "".join(f'<td class="num">{fmt.cantidad(r)}/{fmt.cantidad(p.demanda)}</td>'
                  for r, p in zip(recibido, escenario.plantas))
    st.html(f'<div class="tabla-marco"><table class="tabla flujos" style="min-width:620px">'
            f'<thead><tr><th>Empresa</th>{cabecera}<th class="num">Costo (COP)</th></tr></thead>'
            f'<tbody>{cuerpo}</tbody><tfoot><tr><td>Recibido / Demanda</td>{pie}'
            f'<td class="num">{fmt.moneda(ejecucion.costo_total)}</td></tr></tfoot></table></div>')

with columna_ejecucion:
    reporte = ejecucion.factibilidad
    factible = insignia("Factible") if reporte.es_factible else insignia("No factible", "er")
    st.html(f'<div class="tarjeta" style="display:flex;flex-direction:column;gap:12px">'
            f'<div class="tarjeta-cabecera"><h2 class="tarjeta-titulo">Verificación de factibilidad</h2>'
            f'{factible}</div>'
            f'{clave_valor("Restricciones de oferta", f"{reporte.oferta_cumplida} / {reporte.oferta_total}")}'
            f'{clave_valor("Restricciones de demanda", f"{reporte.demanda_cumplida} / {reporte.demanda_total}")}'
            f'{clave_valor("No negatividad", f"{reporte.no_negatividad_cumplida} / {reporte.no_negatividad_total}")}'
            f'{clave_valor("Violaciones", str(reporte.violaciones))}'
            f'</div>')

    d = ejecucion.desglose
    total = d.total or 1
    valores = (d.transporte, d.operacion, d.compra)
    leyenda = "".join(
        f'<div class="fila-cv simple"><span><i class="muestra-color" style="background:{color};opacity:{opacidad}">'
        f'</i>{nombre}</span><strong>{fmt.moneda(valor)}</strong></div>'
        for (nombre, color, opacidad), valor in zip(COLORES_COSTO, valores))
    st.html(f'<div class="tarjeta" style="display:flex;flex-direction:column;gap:14px">'
            f'<h2 class="tarjeta-titulo">Composición del costo</h2>'
            f'{charts.barra_apilada([(v / total, c, o) for (_, c, o), v in zip(COLORES_COSTO, valores)])}'
            f'{leyenda}</div>')
