import math

import streamlit as st

from backend.genetic.genetic_algorithm import ParametrosAG
from backend.network.balance import TipoBalance
from backend.sensitivity.scenario_simulator import ALFA, COSTO_OPERACION, DEMANDA, OFERTA
from backend.services.genetic_service import ServicioGenetico
from backend.services.sensitivity_service import ServicioSensibilidad, etiqueta_variacion
from backend.utils.exceptions import ErrorEcoResiduos
from frontend.components import charts, data_tables, header, icons, session, theme_toggle
from frontend.components import formatters as fmt
from frontend.components.auth_guard import usuario_actual

VISTAS = ["Plantas", "Empresas", "Rutas", "Simular cambios"]
PARAMETROS = {ALFA: "Costo de transporte", OFERTA: "Oferta de residuos", DEMANDA: "Capacidad de las plantas",
              COSTO_OPERACION: "Costo de operación de las plantas"}

header.mostrar("Análisis", "Análisis de sensibilidad")
escenario = session.cargar_escenario()
servicio = ServicioSensibilidad()
analisis = servicio.analizar(escenario)
empresas, plantas = escenario.empresas, escenario.plantas


# Código y nombre corto de la empresa.
def nombre_empresa(i: int) -> str:
    return f"{empresas[i].codigo} {fmt.nombre_corto(empresas[i].nombre)}"


# Código y municipio de la planta.
def nombre_planta(j: int) -> str:
    return f"{plantas[j].codigo} {plantas[j].municipio}"


# Texto de un rango de toneladas.
def rango_toneladas(minimo: float, maximo: float) -> str:
    if math.isinf(maximo):
        return f"Desde {fmt.cantidad(round(minimo, 2))} t (sin límite superior)"
    return f"Entre {fmt.cantidad(round(minimo, 2))} y {fmt.cantidad(round(maximo, 2))} t"


# Texto de un rango de costo unitario.
def rango_costo(minimo: float, maximo: float) -> str:
    if math.isinf(minimo) and math.isinf(maximo):
        return "Sin límite"
    if math.isinf(minimo):
        return f"Hasta {fmt.moneda(maximo)}"
    if math.isinf(maximo):
        return f"Desde {fmt.moneda(minimo)}"
    if abs(maximo - minimo) < 0.5:
        return "Sin margen"
    return f"{fmt.moneda(minimo)} a {fmt.moneda(maximo)}"


# Texto del efecto de un precio sombra sobre el costo total.
def efecto(valor: float, mas: str, menos: str) -> str:
    if abs(valor) < 0.5:
        return '<span class="mu">No cambia el costo</span>'
    if valor > 0:
        return f'<span class="sube">{mas} {fmt.moneda(valor)}</span>'
    return f'<span class="baja">{menos} {fmt.moneda(-valor)}</span>'


# Tarjeta que explica un concepto del análisis.
def explicacion(icono: str, titulo: str, pregunta: str, texto: str) -> str:
    return (f'<div class="concepto"><span class="mosaico-icono">{icons.icono(icono, 22)}</span>'
            f'<div><span class="concepto-nombre">{titulo}</span><strong>{pregunta}</strong>'
            f'<p>{texto}</p></div></div>')


# Lista de conclusiones del análisis.
def conclusiones(frases: list[str]) -> str:
    if not frases:
        return ""
    items = "".join(f"<li>{f}</li>" for f in frases)
    return (f'<div class="conclusiones"><div class="conclusiones-titulo">{icons.icono("visto", 16)}'
            f'Qué nos dice</div><ul>{items}</ul></div>')


st.html(
    '<div class="tarjeta sens-intro"><div class="sens-intro-texto">'
    '<h2 class="tarjeta-titulo">¿Qué tan estable es la mejor solución?</h2>'
    '<p>El método exacto encontró el plan de envíos más barato con los datos actuales. El análisis de '
    'sensibilidad muestra <strong>qué pasaría si esos datos cambian</strong>: cuánto valdría tener más '
    'capacidad o más residuo, hasta dónde pueden moverse las cantidades y los costos sin que el plan deje de '
    'ser el mejor, y cómo cambia el costo total en distintos escenarios.</p></div>'
    '<div class="conceptos">'
    + explicacion("dinero", "Precio sombra", "¿Cuánto vale una tonelada más?",
                  "Cuánto sube o baja el costo total semanal si una planta tiene 1 t más de capacidad o una "
                  "empresa entrega 1 t más.")
    + explicacion("parametros", "Rango de factibilidad", "¿Hasta dónde puede cambiar una cantidad?",
                  "Entre qué valores puede moverse la oferta de una empresa o la capacidad de una planta sin "
                  "que cambien las rutas que se usan; dentro de ese rango el precio sombra sigue siendo válido.")
    + explicacion("rutas", "Rango de optimalidad", "¿Cuánto puede cambiar el costo de una ruta?",
                  "Entre qué costos por tonelada el plan actual sigue siendo el más barato. Para las rutas sin "
                  "uso indica cuánto debería bajar su costo para que convenga usarlas.")
    + '</div></div>')

if analisis is None:
    st.html('<div class="nota wa">No hay una solución óptima para analizar en este escenario. Revisa los datos '
            'y resuelve el modelo en Método exacto.</div>')
    st.stop()

if analisis.degenerada:
    st.html('<div class="nota ag-nota">En este escenario hay empresas o rutas que podrían intercambiar envíos '
            'sin cambiar el costo total (hay más de un plan igual de barato). Por eso algunos rangos tienen '
            'margen cero y los precios sombra pueden variar un poco según el plan elegido.</div>')

with st.container(key="pestanas_sensibilidad"):
    vista = st.radio("Vista", VISTAS, horizontal=True, key="vista_sensibilidad", label_visibility="collapsed")

if vista == "Plantas":
    filas, frases = [], []
    for nodo in analisis.plantas:
        filas.append([nombre_planta(nodo.indice), fmt.toneladas(nodo.cantidad), fmt.toneladas(round(nodo.utilizado, 2)),
                      fmt.toneladas(round(nodo.holgura, 2)),
                      efecto(nodo.precio_sombra, "Cada t más de capacidad cuesta", "Cada t más de capacidad ahorra"),
                      rango_toneladas(nodo.minimo, nodo.maximo)])
    valiosas = sorted((n for n in analisis.plantas if n.precio_sombra < -0.5), key=lambda n: n.precio_sombra)
    if valiosas:
        n = valiosas[0]
        frases.append(f"<strong>Ampliar {nombre_planta(n.indice)} es lo que más ahorra:</strong> cada tonelada "
                      f"semanal adicional de capacidad reduce el costo en {fmt.moneda(-n.precio_sombra)}, mientras "
                      f"su capacidad esté {rango_toneladas(n.minimo, n.maximo).lower()}.")
    for n in analisis.plantas:
        if abs(n.precio_sombra) <= 0.5:
            libre = f" y le sobran {fmt.toneladas(round(n.holgura, 2))}" if n.holgura > 1e-6 else ""
            frases.append(f"{nombre_planta(n.indice)} no es un cuello de botella{libre}: ampliar su capacidad no "
                          f"reduce el costo.")
    if analisis.oferta_igual is False:
        frases.append("Como hay más residuo que capacidad, las plantas trabajan llenas; el valor indica cuánto "
                      "costaría que una planta tuviera que recibir 1 t más.")
    st.html(f'<div class="tarjeta sens-tarjeta"><div class="tarjeta-cabecera"><h2 class="tarjeta-titulo">'
            f'Plantas: valor de ampliar la capacidad</h2><small>Precio sombra y rango de factibilidad</small></div>'
            + data_tables.tabla([("Planta", "i"), ("Capacidad (t/sem)", "d"), ("Recibe (t/sem)", "d"),
                                 ("Capacidad libre", "d"), ("Precio sombra (por semana)", "i"),
                                 ("Rango de factibilidad", "i")], filas, ancho_minimo=760)
            + conclusiones(frases) + '</div>')

elif vista == "Empresas":
    filas, frases = [], []
    for nodo in analisis.empresas:
        filas.append([nombre_empresa(nodo.indice), fmt.toneladas(nodo.cantidad), fmt.toneladas(round(nodo.utilizado, 2)),
                      efecto(nodo.precio_sombra, "Cada t más cuesta", "Cada t más ahorra"),
                      rango_toneladas(nodo.minimo, nodo.maximo)])
    caras = sorted(analisis.empresas, key=lambda n: -n.precio_sombra)
    if caras and caras[0].precio_sombra > 0.5:
        n, b = caras[0], caras[-1]
        frases.append(f"<strong>Las toneladas de {nombre_empresa(n.indice)} son las más costosas de atender:</strong> "
                      f"cada tonelada que entrega cuesta {fmt.moneda(n.precio_sombra)} al sistema (compra, transporte "
                      f"y operación). Las de {nombre_empresa(b.indice)} son las más baratas "
                      f"({fmt.moneda(b.precio_sombra)}).")
    if analisis.oferta_igual and any(abs(n.maximo - n.cantidad) < 1e-6 for n in analisis.empresas):
        frases.append("Con oferta y capacidad iguales, ninguna empresa puede entregar más sin ampliar alguna planta; "
                      "por eso los rangos terminan en la oferta actual. El precio sombra indica cuánto bajaría el "
                      "costo si la empresa entregara 1 t menos.")
    sin_enviar = [n for n in analisis.empresas if n.holgura > 1e-6]
    if sin_enviar:
        frases.append("Quedan toneladas sin recolectar en " + ", ".join(
            f"{nombre_empresa(n.indice)} ({fmt.toneladas(round(n.holgura, 2))})" for n in sin_enviar) + ".")
    st.html(f'<div class="tarjeta sens-tarjeta"><div class="tarjeta-cabecera"><h2 class="tarjeta-titulo">'
            f'Empresas: costo de recibir más residuo</h2><small>Precio sombra y rango de factibilidad</small></div>'
            + data_tables.tabla([("Empresa", "i"), ("Oferta (t/sem)", "d"), ("Enviada (t/sem)", "d"),
                                 ("Precio sombra (por semana)", "i"), ("Rango de factibilidad", "i")],
                                filas, ancho_minimo=720)
            + conclusiones(frases) + '</div>')

elif vista == "Rutas":
    usadas = [r for r in analisis.rutas if r.usada]
    sin_uso = [r for r in analisis.rutas if not r.usada]
    filas_usadas = []
    for r in sorted(usadas, key=lambda r: (r.i, r.j)):
        filas_usadas.append([f"{nombre_empresa(r.i)} → {nombre_planta(r.j)}", fmt.toneladas(round(r.flujo, 2)),
                             fmt.moneda(r.costo), rango_costo(r.costo_minimo, r.costo_maximo),
                             "—" if math.isinf(r.costo_maximo) else fmt.moneda(max(r.costo_maximo - r.costo, 0))])
    filas_sin_uso = []
    for r in sorted(sin_uso, key=lambda r: r.costo_reducido):
        if r.costo_reducido < 0.5:
            lectura = '<span class="mu">Ya podría usarse sin cambiar el costo total</span>'
        else:
            lectura = f"Bajar {fmt.moneda(r.costo_reducido)} (a {fmt.moneda(r.costo - r.costo_reducido)})"
        filas_sin_uso.append([f"{nombre_empresa(r.i)} → {nombre_planta(r.j)}", fmt.moneda(r.costo), lectura])

    frases = []
    con_margen = [r for r in usadas if not math.isinf(r.costo_maximo) and r.costo_maximo - r.costo > 0.5]
    if con_margen:
        r = min(con_margen, key=lambda r: r.costo_maximo - r.costo)
        frases.append(f"<strong>La ruta más sensible es {nombre_empresa(r.i)} → {nombre_planta(r.j)}:</strong> si su "
                      f"costo sube más de {fmt.moneda(r.costo_maximo - r.costo)} por tonelada, deja de convenir y el "
                      f"plan de envíos cambia.")
    candidatas = [r for r in sin_uso if r.costo_reducido > 0.5]
    if candidatas:
        r = min(candidatas, key=lambda r: r.costo_reducido)
        frases.append(f"La ruta sin uso más cercana a entrar es {nombre_empresa(r.i)} → {nombre_planta(r.j)}: "
                      f"empezaría a usarse si su costo bajara {fmt.moneda(r.costo_reducido)} por tonelada.")
    sin_margen = [r for r in usadas if abs(r.costo_maximo - r.costo_minimo) < 0.5]
    if sin_margen:
        frases.append(f"{len(sin_margen)} {'ruta usada no tiene' if len(sin_margen) == 1 else 'rutas usadas no tienen'} "
                      f"margen: cualquier cambio en su costo hace que otra ruta igual de buena tome su lugar.")
    st.html(f'<div class="tarjeta sens-tarjeta"><div class="tarjeta-cabecera"><h2 class="tarjeta-titulo">'
            f'Rutas en uso: margen de cambio en el costo</h2><small>Rango de optimalidad (COP por tonelada)</small></div>'
            + data_tables.tabla([("Ruta", "i"), ("Toneladas (t/sem)", "d"), ("Costo actual (COP/t)", "d"),
                                 ("Rango de optimalidad (COP/t)", "i"), ("Puede subir hasta", "d")],
                                filas_usadas, ancho_minimo=760)
            + conclusiones(frases) + '</div>')
    st.html(f'<div class="tarjeta sens-tarjeta"><div class="tarjeta-cabecera"><h2 class="tarjeta-titulo">'
            f'Rutas sin uso: cuánto debería bajar su costo</h2><small>Costo reducido (COP por tonelada)</small></div>'
            + data_tables.tabla([("Ruta", "i"), ("Costo actual (COP/t)", "d"), ("Para empezar a usarse", "i")],
                                filas_sin_uso, ancho_minimo=620) + '</div>')

else:
    with st.container(key="tarjeta_simulacion"):
        st.html('<div class="tarjeta-cabecera"><h2 class="tarjeta-titulo">Simular un cambio</h2>'
                '<small>Cambios en el combustible y el transporte, en la oferta o cuellos de botella en las plantas'
                '</small></div>')
        c1, c2 = st.columns(2)
        tipo = c1.selectbox("Parámetro a variar", list(PARAMETROS), format_func=PARAMETROS.get, key="sim_tipo")
        if tipo == ALFA:
            opciones = {-1: "Toda la red"}
        elif tipo == OFERTA:
            opciones = {-1: "Todas las empresas", **{i: nombre_empresa(i) for i in range(len(empresas))}}
        else:
            opciones = {-1: "Todas las plantas", **{j: nombre_planta(j) for j in range(len(plantas))}}
        eleccion = c2.selectbox("Aplicar a", list(opciones), format_func=opciones.get, key=f"sim_indice_{tipo}",
                                disabled=tipo == ALFA)
        indice = None if eleccion == -1 else eleccion
        c3, c4, c5 = st.columns(3)
        minimo = c3.number_input("Variación mínima (%)", min_value=-95.0, max_value=500.0, value=-20.0, step=5.0,
                                 format="%g", key="sim_min")
        maximo = c4.number_input("Variación máxima (%)", min_value=-95.0, max_value=500.0, value=20.0, step=5.0,
                                 format="%g", key="sim_max")
        paso = c5.number_input("Paso (%)", min_value=0.5, max_value=100.0, value=10.0, step=5.0, format="%g",
                               key="sim_paso")
        con_ag = st.checkbox("Resolver también con el algoritmo genético (1 corrida por punto)", value=True,
                             key="sim_con_ag")
        with st.container(horizontal=True, horizontal_alignment="right"):
            simular = st.button("Simular escenarios", type="primary", key="sim_ejecutar")

    lote = ServicioGenetico().ultimo_lote(escenario)
    parametros_ag = lote.parametros if lote else ParametrosAG()
    if simular:
        barra = st.progress(0.0, text="Resolviendo los escenarios…")
        try:
            puntos = servicio.simular(escenario, tipo, indice, minimo, maximo, paso,
                                      parametros_ag if con_ag else None,
                                      lambda k, total: barra.progress(k / total, text=f"Escenario {k} de {total}"))
            st.session_state.simulacion = {"escenario": escenario.id, "tipo": tipo, "indice": indice,
                                           "objetivo": opciones[eleccion], "puntos": puntos, "con_ag": con_ag}
        except ErrorEcoResiduos as error:
            st.html(f'<div class="nota er">{error}</div>')
        barra.empty()

    resultado = st.session_state.get("simulacion")
    if resultado and resultado["escenario"] == escenario.id:
        puntos = resultado["puntos"]
        etiquetas = [etiqueta_variacion(p.variacion_pct) for p in puntos]
        base = next((p for p in puntos if abs(p.variacion_pct) < 1e-9), None)
        validos = [p for p in puntos if p.costo_exacto is not None]
        frases = []
        estables = [p for p in validos if not p.cambia_plan]
        if estables:
            frases.append(f"<strong>Entre {etiqueta_variacion(min(p.variacion_pct for p in estables))} y "
                          f"{etiqueta_variacion(max(p.variacion_pct for p in estables))} el plan de envíos no "
                          f"cambia</strong> (las mismas rutas); solo cambia el costo total.")
        cambian = [p for p in validos if p.cambia_plan]
        if cambian:
            frases.append("En " + ", ".join(etiqueta_variacion(p.variacion_pct) for p in cambian)
                          + " el plan cambia: conviene usar otras rutas (barras naranjas).")
        if len(validos) >= 2:
            extremos = sorted(validos, key=lambda p: p.variacion_pct)
            pendiente = (extremos[-1].costo_exacto - extremos[0].costo_exacto) / \
                (extremos[-1].variacion_pct - extremos[0].variacion_pct)
            frases.append(f"En promedio, cada 1 % de cambio en {PARAMETROS[resultado['tipo']].lower()} "
                          f"({resultado['objetivo'].lower()}) mueve el costo semanal en {fmt.moneda(abs(pendiente))}.")
        infactibles = [p for p in puntos if p.costo_exacto is None]
        if infactibles:
            frases.append("Sin solución en " + ", ".join(etiqueta_variacion(p.variacion_pct) for p in infactibles)
                          + ": las rutas habilitadas no alcanzan para mover toda la oferta.")
        if resultado["con_ag"]:
            gaps = [p.gap for p in puntos if p.gap is not None]
            if gaps:
                frases.append(f"El algoritmo genético quedó en promedio a {fmt.porcentaje(sum(gaps) / len(gaps), 2)} "
                              f"del óptimo exacto en estos escenarios.")

        with st.container(key="tarjeta_resultado_simulacion"):
            st.html(f'<div class="tarjeta-cabecera"><h2 class="tarjeta-titulo">Resultado: '
                    f'{PARAMETROS[resultado["tipo"]]} · {resultado["objetivo"]}</h2>'
                    f'<small>{len(puntos)} escenarios</small></div>')
            st.plotly_chart(charts.figura_simulacion(
                etiquetas, [p.costo_exacto for p in puntos],
                [p.costo_ag for p in puntos] if resultado["con_ag"] else None,
                [p.cambia_plan for p in puntos], theme_toggle.paleta()),
                config={"displayModeBar": False}, theme=None, key="grafico_simulacion")
            columnas = [("Variación", "i"), ("Costo exacto", "d")]
            if resultado["con_ag"]:
                columnas += [("Costo algoritmo genético", "d"), ("Gap", "d")]
            columnas += [("Frente al actual", "d"), ("Balance", "i"), ("Plan de envíos", "i")]
            filas = []
            for etiqueta, p in zip(etiquetas, puntos):
                cambio = "—"
                if base and base.costo_exacto and p.costo_exacto is not None:
                    cambio = fmt.porcentaje((p.costo_exacto - base.costo_exacto) / base.costo_exacto * 100, 1)
                fila = [f"<strong>{etiqueta}</strong>", fmt.moneda(p.costo_exacto)]
                if resultado["con_ag"]:
                    fila += [fmt.moneda(p.costo_ag), fmt.porcentaje(p.gap, 2) if p.gap is not None else "—"]
                balance = {TipoBalance.BALANCEADO: "Balanceado", TipoBalance.EXCESO_OFERTA: "Sobra residuo",
                           TipoBalance.EXCESO_DEMANDA: "Sobra capacidad"}[p.balance]
                plan = ('<span class="insignia wa">Cambia</span>' if p.cambia_plan
                        else '<span class="insignia ok">Igual</span>')
                filas.append(fila + [cambio, balance, plan if p.costo_exacto is not None else "Sin solución"])
            st.html(data_tables.tabla(columnas, filas, ancho_minimo=760) + conclusiones(frases))
            with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center"):
                st.html('<span class="pista">Crea un escenario derivado por cada variación (excepto 0 %) y lo '
                        'resuelve; aparecerán en Escenarios y en Comparación.</span>')
                if st.button("Guardar como escenarios", key="sim_guardar"):
                    barra = st.progress(0.0, text="Creando escenarios…")
                    try:
                        creados = servicio.guardar_como_escenarios(
                            escenario, usuario_actual().id, resultado["tipo"], resultado["indice"], puntos,
                            parametros_ag if resultado["con_ag"] else None,
                            lambda k, total: barra.progress(k / total, text=f"Escenario {k} de {total}"))
                        session.avisar(f"Se crearon {creados} escenarios derivados de «{escenario.nombre}».")
                        st.rerun()
                    except ErrorEcoResiduos as error:
                        barra.empty()
                        st.html(f'<div class="nota er">{error}</div>')
