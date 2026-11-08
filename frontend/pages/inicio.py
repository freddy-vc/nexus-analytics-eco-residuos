import streamlit as st

from backend.network.balance import TipoBalance, verificar_balance
from backend.services.optimization_service import ServicioOptimizacion
from frontend.components import charts, data_tables, header, icons, session, theme_toggle
from frontend.components import formatters as fmt
from frontend.components.kpi_cards import indicador_icono, insignia, rejilla_indicadores

INSIGNIAS_ESTADO = {"OPTIMO": ("Óptimo", "ok"), "FACTIBLE": ("Factible", "ag"),
                    "INFACTIBLE": ("Infactible", "er"), "NO_ACOTADO": ("No acotado", "er"),
                    "ERROR": ("Error", "er"), "PENDIENTE": ("Pendiente", "wa")}

header.mostrar("General", "Inicio")
escenario = session.cargar_escenario()
servicio = ServicioOptimizacion()
ejecucion = servicio.ultima_exacta(escenario)
m, n = len(escenario.empresas), len(escenario.plantas)

with st.container(key="tarjeta_portada"):
    texto, arte = st.columns([1.05, 1], gap="large", vertical_alignment="center")
    with texto:
        st.html(f'<div style="display:flex;flex-direction:column;gap:16px">'
                f'{insignia(f"Escenario activo · {escenario.nombre}")}'
                f'<h2 class="portada-titulo">Distribución óptima de residuos<br>'
                f'<span style="color:var(--act)">al menor costo logístico</span></h2>'
                f'<p class="portada-texto">Red de EcoResiduos del Llano</p></div>')
        with st.container(horizontal=True, gap="small"):
            with st.container(key="enlace_primario_resolver"):
                st.page_link("pages/metodo_exacto.py", label="Ejecutar optimización")
            with st.container(key="enlace_secundario_red"):
                st.page_link("pages/red_logistica.py", label="Ver red logística")
    arte.html(f'<div class="portada-arte">{charts.red_portada(theme_toggle.paleta())}</div>')

if ejecucion and ejecucion.es_optima:
    valor_costo, nota_costo = fmt.moneda(ejecucion.costo_total), "Compra, transporte y operación por semana"
else:
    valor_costo, nota_costo = "—", "Resuelve el método exacto"
st.html(rejilla_indicadores([
    indicador_icono("Oferta total", f"{fmt.cantidad(escenario.oferta.sum())} t/sem",
                    f"{m} empresas aliadas", "toneladas"),
    indicador_icono("Demanda de plantas", f"{fmt.cantidad(escenario.demanda.sum())} t/sem",
                    f"{sum(p.activa for p in escenario.plantas)} plantas activas", "plantas"),
    indicador_icono("Costo total óptimo", valor_costo, nota_costo, "dinero"),
    indicador_icono("Gap AG vs. exacto", "—", "Sin corridas del algoritmo genético", "brecha"),
]))

balance = verificar_balance(escenario.oferta, escenario.demanda)
if balance.tipo is TipoBalance.BALANCEADO:
    tipo, mensaje = "ok", (f"<strong>Problema balanceado.</strong> Oferta total = demanda total = "
                           f"{fmt.cantidad(balance.oferta_total)} t/semana; no se requieren nodos ficticios.")
elif balance.tipo is TipoBalance.EXCESO_OFERTA:
    tipo, mensaje = "wa", (f"<strong>Problema desbalanceado.</strong> La oferta supera la demanda en "
                           f"{fmt.cantidad(balance.diferencia)} t/semana; se agregará una planta ficticia.")
else:
    tipo, mensaje = "wa", (f"<strong>Problema desbalanceado.</strong> La demanda supera la oferta en "
                           f"{fmt.cantidad(-balance.diferencia)} t/semana; se agregará una empresa ficticia.")
with st.container(key=f"aviso_{tipo}", horizontal=True, vertical_alignment="center"):
    st.html(f'<span class="aviso-texto">{icons.icono("visto" if tipo == "ok" else "alerta", 20)}'
            f'<span>{mensaje}</span></span>')
    with st.container(key="enlace_texto_validar"):
        st.page_link("pages/parametros.py", label="Validar datos")

izquierda, derecha = st.columns(2, gap="medium")
with izquierda:
    filas = []
    for j, planta in enumerate(escenario.plantas):
        usado = float(ejecucion.flujos[:, j].sum()) if ejecucion and ejecucion.flujos is not None else 0.0
        porcentaje = usado / planta.demanda * 100 if planta.demanda else 0
        filas.append(charts.fila_utilizacion(planta.codigo, planta.municipio, fmt.cantidad(usado),
                                             fmt.cantidad(planta.demanda), porcentaje))
    nota = "Solución exacta" if ejecucion and ejecucion.flujos is not None else "Sin solución"
    st.html(f'<div class="tarjeta" style="display:flex;flex-direction:column;gap:18px;height:100%">'
            f'<div class="tarjeta-cabecera"><h3>Utilización de plantas</h3><small>{nota}</small></div>'
            f'{"".join(filas)}</div>')

with derecha.container(key="tarjeta_ejecuciones"):
    with st.container(horizontal=True, vertical_alignment="center"):
        st.html('<h3 class="tarjeta-titulo">Últimas ejecuciones</h3>')
        st.html('<span class="enlace-bloqueado" aria-disabled="true" '
                'title="Disponible en una fase posterior del proyecto">Ver comparación</span>')
    recientes = servicio.ejecuciones_recientes(4)
    if recientes:
        filas_tabla = []
        for e in recientes:
            etiqueta, tipo_insignia = INSIGNIAS_ESTADO.get(e.estado, (e.estado.capitalize(), "wa"))
            filas_tabla.append([f'<span style="font-weight:500">{e.metodo}</span>',
                                insignia(etiqueta, tipo_insignia), fmt.moneda(e.objetivo),
                                f'<span class="mu">{fmt.segundos(e.milisegundos)}</span>'])
        st.html(data_tables.tabla([("Método", "i"), ("Estado", "i"), ("Costo (COP)", "d"),
                                   ("Tiempo", "d")], filas_tabla))
    else:
        st.html('<p class="pista" style="font-size:14px">Aún no hay ejecuciones registradas.</p>')

MODULOS = [
    ("Datos de la red", "Empresas, plantas, rutas, oferta, demanda y coeficientes del negocio.", "empresas"),
    ("Optimización", "Modelo exacto de transporte y algoritmo genético configurable.", "exacto"),
    ("Análisis y reportes", "Precios sombra, escenarios y reporte comparativo exportable.", "sensibilidad"),
]
tarjetas = "".join(
    f'<div class="tarjeta modulo"><span class="mosaico-icono" style="width:56px;height:56px">'
    f'{icons.icono(icono, 26)}</span><strong>{titulo}</strong><span>{texto}</span></div>'
    for titulo, texto, icono in MODULOS)
st.html(f'<section class="modulos"><div class="modulos-cabecera"><h2>Todo el flujo de optimización en '
        f'un solo sistema</h2><p>De los datos de la red al reporte comparativo exacto vs. algoritmo '
        f'genético.</p></div><div class="modulos-rejilla">{tarjetas}</div></section>')
