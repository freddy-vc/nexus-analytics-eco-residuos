import math
from datetime import datetime

import streamlit as st

from backend.comparison.comparative_report import Reporte, Seccion, Tabla
from backend.comparison.metrics import gap, medir_escalabilidad
from backend.genetic.genetic_algorithm import ParametrosAG
from backend.services.comparison_service import ServicioComparacion
from backend.services.genetic_service import ServicioGenetico
from backend.services.optimization_service import ServicioOptimizacion
from backend.services.sensitivity_service import ServicioSensibilidad
from frontend.components import data_tables, header, session
from frontend.components import formatters as fmt
from frontend.components.kpi_cards import clave_valor, insignia

TAMANOS = [(10, 4), (50, 10), (100, 20)]

header.mostrar("Análisis", "Comparación exacto vs. algoritmo genético")
escenario = session.cargar_escenario()
exacta = ServicioOptimizacion().ultima_exacta(escenario)
lote = ServicioGenetico().ultimo_lote(escenario)
seleccion = st.session_state.get("comparar_escenarios")
filas = ServicioComparacion().por_escenarios(seleccion)

costo_exacto = exacta.objetivo if exacta and exacta.es_optima else None
diferencia = gap(lote.estadisticas.mejor, costo_exacto) if lote else None

izquierda, centro, derecha = st.columns([1, 0.9, 1], gap="medium")
if exacta:
    izquierda.html(
        f'<div class="tarjeta comp-tarjeta"><div class="tarjeta-cabecera"><h2 class="tarjeta-titulo">Método exacto</h2>'
        f'{insignia("Óptimo") if exacta.es_optima else insignia("Sin óptimo", "er")}</div>'
        f'<strong class="comp-costo">{fmt.moneda(costo_exacto)}</strong>'
        f'{clave_valor("Tiempo", fmt.segundos(exacta.milisegundos))}'
        f'{clave_valor("Violaciones", str(exacta.factibilidad.violaciones) if exacta.factibilidad else "—")}'
        f'{clave_valor("Solucionador", "Simplex de dos fases")}</div>')
else:
    izquierda.html('<div class="tarjeta comp-tarjeta"><h2 class="tarjeta-titulo">Método exacto</h2>'
                   '<p class="mu">Sin resolver. Ejecútalo en Método exacto.</p></div>')

if lote:
    e = lote.estadisticas
    derecha.html(
        f'<div class="tarjeta comp-tarjeta"><div class="tarjeta-cabecera"><h2 class="tarjeta-titulo">Algoritmo genético</h2>'
        f'{insignia("Factible") if lote.mejor.factible else insignia("No factible", "er")}</div>'
        f'<strong class="comp-costo">{fmt.moneda(e.mejor)}</strong>'
        f'{clave_valor("Tiempo promedio", fmt.segundos(e.tiempo_promedio_ms))}'
        f'{clave_valor("Promedio y desviación", f"{fmt.moneda(e.promedio)} ± {fmt.moneda(e.desviacion)}")}'
        f'{clave_valor("Corridas", str(e.corridas))}</div>')
else:
    derecha.html('<div class="tarjeta comp-tarjeta"><h2 class="tarjeta-titulo">Algoritmo genético</h2>'
                 '<p class="mu">Sin corridas. Ejecútalo en Algoritmo genético.</p></div>')

if diferencia is not None:
    veces = lote.estadisticas.tiempo_promedio_ms / max(exacta.milisegundos, 0.001)
    lectura = ("El algoritmo genético encontró el mismo costo que el óptimo exacto." if abs(diferencia) < 0.005
               else f"El algoritmo genético cuesta {fmt.moneda(lote.estadisticas.mejor - costo_exacto)} más por semana "
                    f"que el óptimo.")
    centro.html(f'<div class="tarjeta comp-tarjeta comp-gap"><span>Gap del algoritmo genético frente al óptimo</span>'
                f'<strong>{fmt.porcentaje(diferencia, 2)}</strong><p>{lectura}</p>'
                f'<p class="mu">El algoritmo genético tarda unas {fmt.numero(veces, 0)} veces más que el método '
                f'exacto en este escenario.</p></div>')
else:
    centro.html('<div class="tarjeta comp-tarjeta comp-gap"><span>Gap del algoritmo genético frente al óptimo</span>'
                '<strong>—</strong><p class="mu">Se necesita una solución de cada método para calcularlo.</p></div>')

with st.container(key="tarjeta_comparacion_escenarios"):
    with st.container(horizontal=True, vertical_alignment="center"):
        st.html('<div class="tarjeta-cabecera" style="flex:1"><h2 class="tarjeta-titulo">Comportamiento ante '
                'escenarios de sensibilidad</h2><small>Última solución exacta y mejor corrida del último lote del '
                'algoritmo genético de cada escenario</small></div>')
        if seleccion:
            with st.container(key="barra_ver_todos"):
                if st.button("Ver todos los escenarios", type="tertiary"):
                    st.session_state.pop("comparar_escenarios", None)
                    st.rerun()
    tabla_escenarios = [[f"<strong>{f.escenario}</strong>" + (" <span class='mu'>(base)</span>" if f.es_base else ""),
                         fmt.moneda(f.costo_exacto), fmt.moneda(f.costo_ag),
                         fmt.porcentaje(f.gap, 2) if f.gap is not None else "—",
                         fmt.segundos(f.milisegundos_exacto), fmt.segundos(f.milisegundos_ag),
                         str(f.corridas_ag) if f.corridas_ag else "—"] for f in filas]
    st.html(data_tables.tabla([("Escenario", "i"), ("Costo exacto", "d"), ("Costo algoritmo genético", "d"),
                               ("Gap", "d"), ("Tiempo exacto", "d"), ("Tiempo algoritmo genético", "d"),
                               ("Corridas", "d")], tabla_escenarios, ancho_minimo=820))
    pendientes = [f.escenario for f in filas if f.costo_exacto is None or f.costo_ag is None]
    if pendientes:
        st.html(f'<p class="pista">Para completar la tabla, resuelve con ambos métodos: {", ".join(pendientes)}.</p>')

escala, exportar = st.columns([1.6, 1], gap="medium")
with escala.container(key="tarjeta_escalabilidad"):
    with st.container(horizontal=True, vertical_alignment="center"):
        st.html('<div class="tarjeta-cabecera" style="flex:1"><h2 class="tarjeta-titulo">Escalabilidad</h2>'
                '<small>Tiempo de cómputo por tamaño de instancia (empresas × plantas)</small></div>')
        with st.container(key="barra_medir"):
            medir = st.button("Medir escalabilidad", key="medir_escalabilidad")
    parametros_ag = lote.parametros if lote else ParametrosAG()
    if medir:
        with st.spinner("Resolviendo instancias de prueba de 10 × 4, 50 × 10 y 100 × 20…"):
            st.session_state.escalabilidad = medir_escalabilidad(TAMANOS, parametros_ag)
    mediciones = st.session_state.get("escalabilidad")
    if mediciones:
        st.html(data_tables.tabla(
            [("Instancia", "i"), ("Tiempo exacto", "d"), ("Tiempo algoritmo genético", "d"), ("Gap", "d")],
            [[f"{m.empresas} × {m.plantas}", fmt.segundos(m.milisegundos_exacto), fmt.segundos(m.milisegundos_ag),
              fmt.porcentaje(m.gap, 2) if m.gap is not None else "—"] for m in mediciones]))
        st.html('<p class="pista">Instancias balanceadas generadas al azar (semilla fija) con costos del mismo orden '
                'que el caso base; el algoritmo genético usa los parámetros de su última corrida.</p>')
    else:
        st.html('<p class="pista">Pulsa «Medir escalabilidad» para resolver instancias de 10 × 4, 50 × 10 y 100 × 20 '
                'con ambos métodos y comparar cómo crece el tiempo.</p>')


def construir_reporte(secciones: list[str]) -> Reporte:
    contenido = []
    if "Resultados de optimización" in secciones:
        s = Seccion("Resultados de optimización", [f"Escenario: {escenario.nombre}. {len(escenario.empresas)} empresas, "
                                                   f"{len(escenario.plantas)} plantas, costo de transporte "
                                                   f"{fmt.cantidad(escenario.alfa_efectivo)} COP/t·km."])
        if exacta and exacta.flujos is not None:
            s.parrafos.append(f"Método exacto (Simplex de dos fases): costo total semanal {fmt.moneda(costo_exacto)}, "
                              f"tiempo {fmt.segundos(exacta.milisegundos)}, {exacta.iteraciones} iteraciones.")
            s.tablas.append(Tabla(["Empresa"] + [p.codigo for p in escenario.plantas] + ["Enviado (t)"],
                                  [[e.codigo] + [fmt.cantidad(round(v, 2)) for v in exacta.flujos[i]]
                                   + [fmt.cantidad(round(exacta.flujos[i].sum(), 2))]
                                   for i, e in enumerate(escenario.empresas)]))
        if lote:
            e = lote.estadisticas
            s.parrafos.append(f"Algoritmo genético: {e.corridas} corridas; mejor costo {fmt.moneda(e.mejor)}, promedio "
                              f"{fmt.moneda(e.promedio)}, desviación {fmt.moneda(e.desviacion)}, tiempo promedio "
                              f"{fmt.segundos(e.tiempo_promedio_ms)}.")
        contenido.append(s)
    if "Análisis de sensibilidad" in secciones:
        analisis = ServicioSensibilidad().analizar(escenario)
        s = Seccion("Análisis de sensibilidad")
        if analisis:
            def rango(a, b):
                return f"{fmt.cantidad(round(a, 2))} a {'sin límite' if math.isinf(b) else fmt.cantidad(round(b, 2))}"
            s.parrafos.append("Precio sombra: cambio en el costo semanal por 1 t más de capacidad o de oferta. Rango de "
                              "factibilidad: valores entre los que ese precio sigue siendo válido.")
            s.tablas.append(Tabla(["Planta", "Capacidad (t)", "Recibe (t)", "Precio sombra", "Rango (t)"],
                                  [[f"{escenario.plantas[n.indice].codigo} {escenario.plantas[n.indice].municipio}",
                                    fmt.cantidad(n.cantidad), fmt.cantidad(round(n.utilizado, 2)),
                                    fmt.moneda(n.precio_sombra), rango(n.minimo, n.maximo)] for n in analisis.plantas]))
            s.tablas.append(Tabla(["Empresa", "Oferta (t)", "Precio sombra", "Rango (t)"],
                                  [[escenario.empresas[n.indice].codigo, fmt.cantidad(n.cantidad),
                                    fmt.moneda(n.precio_sombra), rango(n.minimo, n.maximo)] for n in analisis.empresas]))
            s.parrafos.append("Rango de optimalidad: costos por tonelada entre los que el plan de envíos se mantiene.")
            s.tablas.append(Tabla(["Ruta", "Toneladas", "Costo (COP/t)", "Desde", "Hasta"],
                                  [[f"{escenario.empresas[r.i].codigo} -> {escenario.plantas[r.j].codigo}",
                                    fmt.cantidad(round(r.flujo, 2)), fmt.moneda(r.costo),
                                    "sin límite" if math.isinf(r.costo_minimo) else fmt.moneda(r.costo_minimo),
                                    "sin límite" if math.isinf(r.costo_maximo) else fmt.moneda(r.costo_maximo)]
                                   for r in analisis.rutas if r.usada]))
        else:
            s.parrafos.append("No hay una solución óptima para analizar.")
        contenido.append(s)
    if "Reporte comparativo" in secciones:
        s = Seccion("Reporte comparativo exacto vs. algoritmo genético")
        if diferencia is not None:
            s.parrafos.append(f"Gap del algoritmo genético frente al óptimo: {fmt.porcentaje(diferencia, 2)}. "
                              f"Tiempo exacto {fmt.segundos(exacta.milisegundos)}; tiempo promedio del algoritmo genético "
                              f"{fmt.segundos(lote.estadisticas.tiempo_promedio_ms)}.")
        s.tablas.append(Tabla(["Escenario", "Costo exacto", "Costo AG", "Gap", "T. exacto", "T. AG"],
                              [[f.escenario, fmt.moneda(f.costo_exacto), fmt.moneda(f.costo_ag),
                                fmt.porcentaje(f.gap, 2) if f.gap is not None else "-",
                                fmt.segundos(f.milisegundos_exacto), fmt.segundos(f.milisegundos_ag)] for f in filas]))
        if mediciones:
            s.parrafos.append("Escalabilidad (instancias de prueba):")
            s.tablas.append(Tabla(["Instancia", "Tiempo exacto", "Tiempo AG", "Gap"],
                                  [[f"{m.empresas} x {m.plantas}", fmt.segundos(m.milisegundos_exacto),
                                    fmt.segundos(m.milisegundos_ag),
                                    fmt.porcentaje(m.gap, 2) if m.gap is not None else "-"] for m in mediciones]))
        contenido.append(s)
    return Reporte("Reporte de optimización", f"Escenario {escenario.nombre}", datetime.now(), contenido)


def registrar_comparacion():
    if exacta and lote:
        ServicioComparacion().registrar(exacta.ejecucion_id, lote.mejor.ejecucion_id,
                                        f"Gap {fmt.porcentaje(diferencia, 2)}" if diferencia is not None else None)


with exportar.container(key="tarjeta_exportar"):
    st.html('<h2 class="tarjeta-titulo">Exportar reporte</h2><span class="mu" style="font-size:13px">Contenido</span>')
    elegidas = [s for s in ("Resultados de optimización", "Análisis de sensibilidad", "Reporte comparativo")
                if st.checkbox(s, value=True, key=f"reporte_{s}")]
    st.html('<span class="insignia ag">PDF</span>')
    if elegidas:
        try:
            from backend.data_io.report_exporter import generar_pdf
            datos = generar_pdf(construir_reporte(elegidas))
            st.download_button("Descargar reporte", datos, file_name=f"reporte_{escenario.nombre}.pdf".replace(" ", "_"),
                               mime="application/pdf", type="primary", width="stretch", on_click=registrar_comparacion)
        except ImportError:
            st.html('<div class="nota wa">Falta la librería fpdf2: ejecute <code>pip install -r requirements.txt</code>.</div>')
    else:
        st.html('<p class="pista">Elige al menos una sección.</p>')
