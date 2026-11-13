import math
from collections import defaultdict
from dataclasses import dataclass

import networkx as nx
import numpy as np


@dataclass(frozen=True)
class NodoRed:
    codigo: str
    etiqueta: str
    cantidad: float
    municipio: str
    latitud: float
    longitud: float


@dataclass(frozen=True)
class ResumenGrafo:
    origenes: int
    destinos: int
    arcos: int
    arcos_con_flujo: int


# Grafo bipartito dirigido de empresas a plantas con distancia, costo y flujo por arco.
def construir_red(origenes: list[NodoRed], destinos: list[NodoRed], distancias: np.ndarray,
                  costos: np.ndarray, habilitadas: np.ndarray,
                  flujos: np.ndarray | None = None) -> nx.DiGraph:
    grafo = nx.DiGraph()
    for nodo in origenes:
        grafo.add_node(nodo.codigo, bipartito=0, etiqueta=nodo.etiqueta, oferta=nodo.cantidad,
                       municipio=nodo.municipio, latitud=nodo.latitud, longitud=nodo.longitud)
    for nodo in destinos:
        grafo.add_node(nodo.codigo, bipartito=1, etiqueta=nodo.etiqueta, demanda=nodo.cantidad,
                       municipio=nodo.municipio, latitud=nodo.latitud, longitud=nodo.longitud)

    for i, origen in enumerate(origenes):
        for j, destino in enumerate(destinos):
            if habilitadas[i, j]:
                grafo.add_edge(origen.codigo, destino.codigo,
                               distancia=float(distancias[i, j]),
                               costo=float(costos[i, j]),
                               flujo=float(flujos[i, j]) if flujos is not None else 0.0)
    return grafo


KM_POR_GRADO = 111.32


# Proyecta las coordenadas geográficas al cuadrado unitario y calcula la escala en kilómetros.
def _proyeccion(grafo: nx.DiGraph):
    nodos = list(grafo.nodes)
    lon = np.array([grafo.nodes[n]["longitud"] for n in nodos], float)
    lat = np.array([grafo.nodes[n]["latitud"] for n in nodos], float)
    # Proyección equirectangular: la longitud se corrige por el coseno de la latitud media.
    x = (lon - lon.min()) * math.cos(math.radians(float(lat.mean())))
    y = lat.max() - lat
    escala = max(x.max(), y.max()) or 0.1
    x, y = x / escala, y / escala
    x += (1 - x.max()) / 2
    y += (1 - y.max()) / 2
    return nodos, x, y, escala * KM_POR_GRADO


# Kilómetros que representa una unidad del dibujo.
def kilometros_por_unidad(grafo: nx.DiGraph) -> float:
    return _proyeccion(grafo)[3] if grafo.number_of_nodes() else 0.0


# Posición inicial de cada nodo según la ubicación de su municipio.
def posiciones_geograficas(grafo: nx.DiGraph, radio_grupo: float = 0.07) -> dict[str, tuple[float, float]]:
    if grafo.number_of_nodes() == 0:
        return {}
    nodos, x, y, _ = _proyeccion(grafo)

    grupos: dict[tuple[float, float], list[int]] = defaultdict(list)
    for k in range(len(nodos)):
        grupos[(round(x[k], 4), round(y[k], 4))].append(k)

    posiciones = {}
    for indices in grupos.values():
        for orden, k in enumerate(indices):
            if len(indices) == 1:
                posiciones[nodos[k]] = (float(x[k]), float(y[k]))
                continue
            # Los nodos de un mismo municipio se reparten en un círculo para no superponerse.
            angulo = 2 * math.pi * orden / len(indices) - math.pi / 2
            posiciones[nodos[k]] = (float(x[k] + radio_grupo * math.cos(angulo)),
                                    float(y[k] + radio_grupo * math.sin(angulo)))
    return posiciones


# Conteo de orígenes, destinos, arcos y arcos con flujo.
def resumir(grafo: nx.DiGraph) -> ResumenGrafo:
    origenes = sum(1 for _, d in grafo.nodes(data=True) if d["bipartito"] == 0)
    con_flujo = sum(1 for *_, d in grafo.edges(data=True) if d["flujo"] > 1e-9)
    return ResumenGrafo(origenes, grafo.number_of_nodes() - origenes,
                        grafo.number_of_edges(), con_flujo)
