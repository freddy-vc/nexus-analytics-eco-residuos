import base64


# Barra de progreso en HTML.
def progreso(porcentaje: float, delgada: bool = False) -> str:
    ancho = max(0.0, min(porcentaje, 100.0))
    return f'<div class="barra{" delgada" if delgada else ""}"><div style="width:{ancho:.1f}%"></div></div>'


# Fila de utilización de una planta con su barra de progreso.
def fila_utilizacion(codigo: str, nombre: str, usado: str, capacidad: str, porcentaje: float) -> str:
    return (f'<div class="utilizacion"><div><span><strong>{codigo}</strong> · {nombre}</span>'
            f'<span class="mu">{usado} / {capacidad} t</span></div>{progreso(porcentaje)}</div>')


# Barra apilada; cada parte es (fracción, color CSS, opacidad).
def barra_apilada(partes: list[tuple[float, str, float]]) -> str:
    segmentos = "".join(
        f'<div style="width:{fraccion * 100:.1f}%;background:{color};opacity:{opacidad}"></div>'
        for fraccion, color, opacidad in partes)
    return f'<div class="barra-apilada">{segmentos}</div>'


# Esquema decorativo de la portada; se entrega como imagen porque st.html no admite SVG.
def red_portada(paleta: dict[str, str]) -> str:
    empresas = [(40, 30), (40, 70), (40, 110), (40, 150), (40, 190)]
    plantas = [(300, 50), (300, 110), (300, 170)]
    rutas = [(0, 0), (1, 0), (1, 1), (2, 2), (3, 1), (4, 2)]
    optimas = [(0, 1), (2, 0), (3, 2)]

    # Curva entre una empresa y una planta del esquema.
    def linea(i, j):
        (x1, y1), (x2, y2) = empresas[i], plantas[j]
        return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>'

    marcado = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 220">'
        f'<g stroke="{paleta["bd"]}" stroke-width="2">{"".join(linea(i, j) for i, j in rutas)}</g>'
        f'<g stroke="{paleta["ac"]}" stroke-width="3">{"".join(linea(i, j) for i, j in optimas)}</g>'
        f'<g fill="{paleta["sf"]}" stroke="{paleta["ac"]}" stroke-width="3">'
        + "".join(f'<circle cx="{x}" cy="{y}" r="10"/>' for x, y in empresas) + '</g>'
        f'<g fill="{paleta["ac"]}">'
        + "".join(f'<circle cx="{x}" cy="{y}" r="14"/>' for x, y in plantas) + '</g></svg>')
    datos = base64.b64encode(marcado.encode()).decode()
    return (f'<img src="data:image/svg+xml;base64,{datos}" width="100%" style="max-width:380px" '
            f'alt="Esquema de la red: empresas conectadas a plantas">')


# Figura de Plotly con los colores, la tipografía y los ejes del tema.
def _figura_base(paleta: dict[str, str], alto: int, titulo_x: str, titulo_y: str):
    import plotly.graph_objects as go

    figura = go.Figure()
    figura.update_layout(
        height=alto, margin=dict(l=8, r=8, t=8, b=8), paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter, system-ui, sans-serif", color=paleta["mu"], size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor=paleta["sf"], bordercolor=paleta["bd"], font_color=paleta["tx"]),
        separators=",.")
    eje = dict(gridcolor=paleta["bd"], zeroline=False, linecolor=paleta["bd"], tickfont=dict(color=paleta["mu"]))
    figura.update_xaxes(title_text=titulo_x, **eje)
    figura.update_yaxes(title_text=titulo_y, tickprefix="$", tickformat=",.3s", **eje)
    return figura


# Curva de convergencia del AG: mejor costo y costo promedio por generación.
def figura_convergencia(generaciones: list[int], mejor: list[float], promedio: list[float],
                        optimo: float | None, paleta: dict[str, str]):
    import plotly.graph_objects as go

    figura = _figura_base(paleta, 300, "Generación", "Costo semanal (COP)")
    figura.add_trace(go.Scatter(x=generaciones, y=promedio, name="Costo promedio", mode="lines",
                                line=dict(color=paleta["mu"], width=1.5, dash="dot"),
                                hovertemplate="Generación %{x}<br>Promedio $%{y:,.0f}<extra></extra>"))
    figura.add_trace(go.Scatter(x=generaciones, y=mejor, name="Mejor costo", mode="lines",
                                line=dict(color=paleta["ac"], width=3),
                                hovertemplate="Generación %{x}<br>Mejor $%{y:,.0f}<extra></extra>"))
    if optimo is not None:
        figura.add_hline(y=optimo, line=dict(color=paleta["ag"], width=1.5, dash="dash"))
        figura.add_trace(go.Scatter(x=[None], y=[None], name="Óptimo exacto", mode="lines",
                                    line=dict(color=paleta["ag"], width=1.5, dash="dash")))
        valores = [v for v in mejor if v is not None] + [optimo]
        rango = max(min(promedio[: max(len(promedio) // 10, 1)] + [max(valores)]), optimo * 1.002)
        figura.update_yaxes(range=[optimo - (rango - optimo) * 0.08, rango])
    return figura


# Costo de cada punto de la simulación; resalta dónde cambia el plan de rutas.
def figura_simulacion(etiquetas: list[str], exacto: list[float | None], genetico: list[float | None] | None,
                      cambia_plan: list[bool], paleta: dict[str, str]):
    import plotly.graph_objects as go

    figura = _figura_base(paleta, 320, "Variación del parámetro", "Costo semanal (COP)")
    colores = [paleta["wa"] if cambio else paleta["ac"] for cambio in cambia_plan]
    figura.add_trace(go.Bar(x=etiquetas, y=exacto, name="Método exacto", marker_color=colores,
                            hovertemplate="%{x}<br>Exacto $%{y:,.0f}<extra></extra>"))
    if genetico is not None:
        figura.add_trace(go.Scatter(x=etiquetas, y=genetico, name="Algoritmo genético", mode="lines+markers",
                                    line=dict(color=paleta["ag"], width=2), marker=dict(size=8),
                                    hovertemplate="%{x}<br>Genético $%{y:,.0f}<extra></extra>"))
    validos = [v for v in exacto + (genetico or []) if v is not None]
    if validos:
        minimo, maximo = min(validos), max(validos)
        margen = max((maximo - minimo) * 0.15, maximo * 0.02)
        figura.update_yaxes(range=[max(minimo - margen, 0), maximo + margen])
    return figura
