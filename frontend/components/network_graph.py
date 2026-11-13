import json
from pathlib import Path

import networkx as nx
import streamlit.components.v1 as componentes

from backend.network.graph_builder import kilometros_por_unidad, posiciones_geograficas

PLANTILLA = Path(__file__).resolve().parents[1] / "templates" / "red_interactiva.html"


# Grafo interactivo; una simulación de fuerzas en el navegador mantiene cada nodo cerca de su municipio.
def mostrar(grafo: nx.DiGraph, ver_flujos: bool, paleta: dict[str, str], alto: int = 600) -> None:
    posiciones = posiciones_geograficas(grafo)
    nodos = [{
        "id": nodo,
        "tipo": "empresa" if datos["bipartito"] == 0 else "planta",
        "municipio": datos["etiqueta"],
        "cantidad": datos["oferta"] if datos["bipartito"] == 0 else datos["demanda"],
        "x": posiciones[nodo][0],
        "y": posiciones[nodo][1],
    } for nodo, datos in grafo.nodes(data=True)]
    aristas = [{"u": u, "v": v, "flujo": d["flujo"], "distancia": d["distancia"], "costo": d["costo"]}
               for u, v, d in grafo.edges(data=True)]

    datos = {"nodos": nodos, "aristas": aristas, "verFlujos": ver_flujos, "paleta": paleta,
             "kmPorUnidad": kilometros_por_unidad(grafo), "alto": alto}
    html = PLANTILLA.read_text(encoding="utf-8").replace("__DATOS__", json.dumps(datos))
    componentes.html(html, height=alto + 96)
