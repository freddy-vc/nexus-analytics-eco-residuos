from dataclasses import asdict

import streamlit as st

from backend.comparison.metrics import gap
from backend.genetic.crossover import DOS_PUNTOS, UN_PUNTO
from backend.genetic.genetic_algorithm import ParametrosAG
from backend.genetic.selection import RULETA, TORNEO
from backend.services.genetic_service import MAX_CORRIDAS, ServicioGenetico
from backend.services.optimization_service import ServicioOptimizacion
from backend.utils.exceptions import ErrorEcoResiduos
from frontend.components import charts, header, session, theme_toggle
from frontend.components import formatters as fmt
from frontend.components.kpi_cards import clave_valor, dato, rejilla_indicadores

SELECCIONES = {TORNEO: "Torneo", RULETA: "Ruleta"}
CRUCES = {UN_PUNTO: "Un punto", DOS_PUNTOS: "Dos puntos"}

header.mostrar("Optimización", "Algoritmo genético")
escenario = session.cargar_escenario()
servicio = ServicioGenetico()
lote = servicio.ultimo_lote(escenario)
exacta = ServicioOptimizacion().ultima_exacta(escenario)
optimo = exacta.objetivo if exacta and exacta.es_optima else None


def cargar_parametros(parametros: ParametrosAG, corridas: int = 30) -> None:
    for campo, valor in asdict(parametros).items():
        st.session_state[f"ag_{campo}"] = valor if valor is not None else 0
    st.session_state.ag_corridas = corridas


def restablecer():
    cargar_parametros(ParametrosAG())


def parametros_formulario() -> ParametrosAG:
    e = st.session_state
    return ParametrosAG(
        tamano_poblacion=int(e.ag_tamano_poblacion), num_generaciones=int(e.ag_num_generaciones),
        tasa_cruce=float(e.ag_tasa_cruce), tasa_mutacion=float(e.ag_tasa_mutacion), seleccion=e.ag_seleccion,
        tamano_torneo=int(e.ag_tamano_torneo), cruce=e.ag_cruce, elitismo=int(e.ag_elitismo),
        penalizacion=float(e.ag_penalizacion), semilla=int(e.ag_semilla))


if "ag_tamano_poblacion" not in st.session_state:
    previos = lote.parametros if lote else servicio.parametros_recientes()
    cargar_parametros(previos or ParametrosAG(), len(lote.corridas) if lote and len(lote.corridas) > 1 else 30)

columna_parametros, columna_resultados = st.columns([1, 2.6], gap="medium")
with columna_parametros.container(key="tarjeta_parametros_ag"):
    with st.container(horizontal=True, vertical_alignment="center"):
        st.html('<h2 class="tarjeta-titulo">Parámetros</h2>')
        st.html('<div class="espaciador"></div>')
        with st.container(key="enlace_restablecer"):
            st.button("Restablecer", type="tertiary", on_click=restablecer,
                      help="Vuelve a los valores recomendados")
    c1, c2 = st.columns(2)
    c1.number_input("Tamaño de población (individuos)", min_value=2, max_value=2000, step=10,
                    key="ag_tamano_poblacion")
    c2.number_input("Generaciones", min_value=1, max_value=5000, step=50, key="ag_num_generaciones")
    c3, c4 = st.columns(2)
    c3.number_input("Elitismo (individuos)", min_value=0, max_value=50, step=1, key="ag_elitismo",
                    help="Mejores individuos que pasan intactos a la siguiente generación.")
    c4.number_input("Penalización (COP por t excedida)", min_value=1.0, step=100000.0, format="%g",
                    key="ag_penalizacion",
                    help="Castigo por cada tonelada que supere la capacidad de una planta.")
    c5, c6 = st.columns(2)
    c5.number_input("Semilla aleatoria", min_value=0, max_value=2**31 - 1, step=1, key="ag_semilla",
                    help="Con la misma semilla se obtiene exactamente el mismo resultado.")
    c6.number_input("Corridas", min_value=1, max_value=MAX_CORRIDAS, step=1, key="ag_corridas",
                    help="Número de veces que se repite el algoritmo con semillas distintas.")
    st.slider("Tasa de cruce", 0.0, 1.0, step=0.01, key="ag_tasa_cruce",
              help="Probabilidad de que dos padres intercambien parte de su plan de envíos.")
    st.slider("Tasa de mutación", 0.0, 1.0, step=0.01, key="ag_tasa_mutacion",
              help="Probabilidad de que el plan de cada empresa cambie al azar en un hijo.")
    with st.container(key="pestanas_seleccion"):
        st.radio("Método de selección", list(SELECCIONES), format_func=SELECCIONES.get, horizontal=True,
                 key="ag_seleccion")
    if st.session_state.ag_seleccion == TORNEO:
        st.number_input("Participantes por torneo", min_value=2, max_value=20, step=1, key="ag_tamano_torneo")
    with st.container(key="pestanas_cruce"):
        st.radio("Tipo de cruce", list(CRUCES), format_func=CRUCES.get, horizontal=True, key="ag_cruce")
    una = st.button("Ejecutar 1 corrida", width="stretch", key="ag_una")
    varias = st.button(f"Ejecutar {int(st.session_state.ag_corridas)} corridas", type="primary",
                       width="stretch", key="ag_varias")

with columna_resultados:
    progreso = st.empty()
    if una or varias:
        corridas = 1 if una else int(st.session_state.ag_corridas)
        barra = progreso.progress(0.0, text="Preparando la población inicial…")

        def avanzar(corrida: int, total: int, generacion: int, generaciones: int):
            hecho = ((corrida - 1) + generacion / generaciones) / total
            barra.progress(min(hecho, 1.0), text=f"Corrida {corrida} de {total} · generación "
                                                 f"{generacion} / {generaciones}")

        try:
            lote = servicio.resolver(escenario, parametros_formulario(), corridas, avanzar)
            session.avisar(f"Algoritmo genético terminado: {corridas} "
                           f"{'corrida' if corridas == 1 else 'corridas'}.")
            progreso.empty()
            st.rerun()
        except ErrorEcoResiduos as error:
            progreso.html(f'<div class="nota er">{error}</div>')

    if lote is None:
        st.html('<div class="tarjeta" style="text-align:center;padding:40px">'
                '<h2 class="tarjeta-titulo">Aún no hay corridas del algoritmo genético</h2>'
                '<p class="mu" style="margin:8px 0 0">Ajusta los parámetros y pulsa «Ejecutar» para buscar '
                'una distribución de bajo costo con el algoritmo genético.</p></div>')
    else:
        e = lote.estadisticas
        p = lote.parametros
        mejor = lote.mejor
        st.html(f'<div class="ag-estado"><span>{len(lote.corridas)} '
                f'{"corrida" if len(lote.corridas) == 1 else "corridas"} · {p.num_generaciones} generaciones '
                f'· población de {p.tamano_poblacion}</span><span>Semilla {lote.corridas[0].semilla} · '
                f'reproducible</span></div>')
        diferencia = gap(e.mejor, optimo)
        st.html(rejilla_indicadores([
            dato("Mejor costo", fmt.moneda(e.mejor), f"Corrida {mejor.numero}", resaltado=True),
            dato("Gap vs. exacto", fmt.porcentaje(diferencia, 2) if diferencia is not None else "—",
                 f"Óptimo {fmt.moneda(optimo)}" if optimo else "Resuelve el método exacto"),
            dato("Tiempo promedio", fmt.segundos(e.tiempo_promedio_ms), "por corrida"),
            dato("Violaciones", "0" if mejor.factible else "Sí",
                 "Solución factible" if mejor.factible else "Supera la capacidad de alguna planta"),
        ], compacta=True))

        with st.container(key="tarjeta_convergencia"):
            st.html(f'<div class="tarjeta-cabecera"><h2 class="tarjeta-titulo">Curva de convergencia</h2>'
                    f'<small>Mejor corrida (corrida {mejor.numero})</small></div>')
            h = lote.historial_mejor
            st.plotly_chart(charts.figura_convergencia([g.numero for g in h], [g.mejor_costo for g in h],
                                                       [g.costo_promedio for g in h], optimo, theme_toggle.paleta()),
                            config={"displayModeBar": False}, theme=None, key="grafico_convergencia")

        estadisticas, diseno = st.columns(2, gap="medium")
        estadisticas.html(
            f'<div class="tarjeta" style="display:flex;flex-direction:column;gap:12px;height:100%">'
            f'<h2 class="tarjeta-titulo">Estadísticas de {e.corridas} '
            f'{"corrida" if e.corridas == 1 else "corridas"}</h2>'
            f'{clave_valor("Mejor costo", fmt.moneda(e.mejor))}'
            f'{clave_valor("Costo promedio", fmt.moneda(e.promedio))}'
            f'{clave_valor("Desviación estándar", fmt.moneda(e.desviacion))}'
            f'{clave_valor("Peor costo", fmt.moneda(e.peor))}'
            f'{clave_valor("Corridas factibles", f"{e.factibles} de {e.corridas}")}'
            f'{clave_valor("Tiempo promedio", fmt.segundos(e.tiempo_promedio_ms))}</div>')
        seleccion = (f"torneo de {p.tamano_torneo} participantes" if p.seleccion == TORNEO
                     else "ruleta (probabilidad según la aptitud)")
        diseno.html(
            f'<div class="tarjeta diseno-ag"><h2 class="tarjeta-titulo">Diseño del algoritmo</h2>'
            f'<p><strong>Cromosoma:</strong> una tabla de {len(escenario.empresas)} empresas × '
            f'{len(escenario.plantas)} plantas con las toneladas enviadas por cada ruta. Cada fila suma la oferta '
            f'de su empresa, así que la oferta siempre se cumple.</p>'
            f'<p><strong>Aptitud:</strong> inversa del costo total semanal más una penalización de '
            f'{fmt.moneda(p.penalizacion)} por cada tonelada que supere la capacidad de una planta.</p>'
            f'<p><strong>Operadores:</strong> selección por {seleccion}; cruce de '
            f'{"un punto" if p.cruce == UN_PUNTO else "dos puntos"} entre empresas (cada hijo hereda el plan '
            f'completo de cada empresa de uno de sus padres); mutación que traslada toneladas entre plantas sin '
            f'alterar la oferta; elitismo de {p.elitismo} '
            f'{"individuo" if p.elitismo == 1 else "individuos"}.</p>'
            f'<p><strong>Población inicial:</strong> planes al azar y algunos construidos llenando primero las '
            f'rutas más baratas.</p></div>')
