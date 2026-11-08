from dataclasses import dataclass
from datetime import datetime
from typing import Callable

import numpy as np
from sqlalchemy import func, insert, select
from sqlalchemy.orm import selectinload

from backend.database import (BaseDatos, Ejecucion, EstadoEjecucion, HistorialGeneracion, MetodoSeleccion,
                              MetodoSolucion, ParametrosAG as ParametrosAGBD, ResultadoRuta, TipoCruce)
from backend.genetic.genetic_algorithm import Generacion, ParametrosAG
from backend.genetic.multi_run import Estadisticas, ejecutar_corridas, estadisticas
from backend.services.scenario_service import DatosEscenario
from backend.utils.exceptions import ErrorValidacion
from backend.utils.singleton import MetaSingleton

METODO_GENETICO = "ALGORITMO_GENETICO"
MAX_CORRIDAS = 50


@dataclass
class CorridaAG:
    ejecucion_id: int
    numero: int
    semilla: int | None
    costo: float
    milisegundos: float
    factible: bool


@dataclass
class LoteAG:
    """Corridas del AG lanzadas juntas sobre un escenario (comparten la hora de inicio)."""
    escenario_id: int
    ejecutado_en: datetime
    parametros: ParametrosAG
    corridas: list[CorridaAG]
    estadisticas: Estadisticas
    historial_mejor: list[Generacion]
    flujos_mejor: np.ndarray | None

    @property
    def mejor(self) -> CorridaAG:
        return self.corridas[self.estadisticas.indice_mejor]


class ServicioGenetico(metaclass=MetaSingleton):
    """Ejecuta el algoritmo genético, guarda cada corrida y recupera el último lote."""

    def __init__(self):
        self._bd = BaseDatos()

    def resolver(self, escenario: DatosEscenario, parametros: ParametrosAG, corridas: int,
                 al_avanzar: Callable[[int, int, int, int], None] | None = None) -> LoteAG:
        errores = parametros.validar()
        if not 1 <= corridas <= MAX_CORRIDAS:
            errores.append(f"El número de corridas debe estar entre 1 y {MAX_CORRIDAS}.")
        if not escenario.empresas or not escenario.plantas:
            errores.append("El escenario necesita al menos una empresa y una planta.")
        elif not escenario.habilitadas.any():
            errores.append("No hay rutas habilitadas: registra las distancias en Rutas y costos.")
        if errores:
            raise ErrorValidacion(" ".join(errores))

        resultados = ejecutar_corridas(escenario.problema(), parametros, corridas, al_avanzar)
        mascara = escenario.habilitadas
        with self._bd.sesion() as sesion:
            metodo = self._id(sesion, MetodoSolucion, METODO_GENETICO)
            estados = {nombre: self._id(sesion, EstadoEjecucion, nombre) for nombre in ("FACTIBLE", "INFACTIBLE")}
            seleccion = self._id(sesion, MetodoSeleccion, parametros.seleccion)
            cruce = self._id(sesion, TipoCruce, parametros.cruce)
            for k, r in enumerate(resultados, start=1):
                ejecucion = Ejecucion(
                    escenario_id=escenario.id, metodo_solucion_id=metodo,
                    estado_ejecucion_id=estados["FACTIBLE" if r.es_factible else "INFACTIBLE"],
                    tiempo_ms=round(r.milisegundos, 3), costo_objetivo_cop=round(r.costo, 2),
                    iteraciones=parametros.num_generaciones,
                    mensaje=f"Corrida {k} de {corridas}"
                            + ("" if r.es_factible else f" · {r.exceso:.2f} t sobre la capacidad"))
                sesion.add(ejecucion)
                sesion.flush()
                sesion.add(ParametrosAGBD(
                    ejecucion_id=ejecucion.id, metodo_seleccion_id=seleccion, tipo_cruce_id=cruce,
                    tamano_poblacion=parametros.tamano_poblacion, num_generaciones=parametros.num_generaciones,
                    tasa_cruce=parametros.tasa_cruce, tasa_mutacion=parametros.tasa_mutacion,
                    tamano_torneo=parametros.tamano_torneo, elitismo=parametros.elitismo,
                    factor_penalizacion=parametros.penalizacion, semilla=r.semilla))
                sesion.flush()
                sesion.execute(insert(HistorialGeneracion), [
                    {"ejecucion_id": ejecucion.id, "num_generacion": g.numero,
                     "mejor_costo": round(g.mejor_costo, 2), "costo_promedio": round(g.costo_promedio, 2),
                     "mejor_fitness": g.mejor_aptitud, "violaciones": g.plantas_excedidas}
                    for g in r.historial])
                sesion.execute(insert(ResultadoRuta), [
                    {"ejecucion_id": ejecucion.id, "ruta_id": int(ruta_id), "toneladas": round(float(t), 2)}
                    for ruta_id, t in zip(escenario.ids_rutas[mascara], r.flujos[mascara])])
        return self.ultimo_lote(escenario)

    def ultimo_lote(self, escenario: DatosEscenario) -> LoteAG | None:
        with self._bd.sesion() as sesion:
            inicio = sesion.scalar(
                select(func.max(Ejecucion.iniciada_en)).join(MetodoSolucion)
                .where(Ejecucion.escenario_id == escenario.id, MetodoSolucion.nombre == METODO_GENETICO))
            if inicio is None:
                return None
            ejecuciones = sesion.scalars(
                select(Ejecucion).join(MetodoSolucion)
                .where(Ejecucion.escenario_id == escenario.id, MetodoSolucion.nombre == METODO_GENETICO,
                       Ejecucion.iniciada_en == inicio)
                .options(selectinload(Ejecucion.estado))
                .order_by(Ejecucion.id)).all()
            corridas = [CorridaAG(e.id, k, None, float(e.costo_objetivo_cop or 0), float(e.tiempo_ms or 0),
                                  e.estado.nombre == "FACTIBLE") for k, e in enumerate(ejecuciones, start=1)]
            estad = estadisticas([c.costo for c in corridas], [c.milisegundos for c in corridas],
                                 [c.factible for c in corridas])
            mejor_id = corridas[estad.indice_mejor].ejecucion_id

            filas = sesion.execute(
                select(ParametrosAGBD, MetodoSeleccion.nombre, TipoCruce.nombre)
                .join(MetodoSeleccion).join(TipoCruce)
                .where(ParametrosAGBD.ejecucion_id.in_([c.ejecucion_id for c in corridas]))).all()
            semillas = {fila[0].ejecucion_id: fila[0].semilla for fila in filas}
            for c in corridas:
                c.semilla = semillas.get(c.ejecucion_id)
            bd, seleccion, cruce = next(f for f in filas if f[0].ejecucion_id == corridas[0].ejecucion_id)
            parametros = ParametrosAG(
                tamano_poblacion=bd.tamano_poblacion, num_generaciones=bd.num_generaciones,
                tasa_cruce=float(bd.tasa_cruce), tasa_mutacion=float(bd.tasa_mutacion), seleccion=seleccion,
                tamano_torneo=bd.tamano_torneo or 3, cruce=cruce, elitismo=bd.elitismo,
                penalizacion=float(bd.factor_penalizacion), semilla=corridas[0].semilla)

            historial = [Generacion(h.num_generacion, float(h.mejor_costo), float(h.costo_promedio),
                                    h.mejor_fitness, h.violaciones)
                         for h in sesion.scalars(select(HistorialGeneracion)
                                                 .where(HistorialGeneracion.ejecucion_id == mejor_id)
                                                 .order_by(HistorialGeneracion.num_generacion))]
            posicion = {int(rid): (i, j) for (i, j), rid in np.ndenumerate(escenario.ids_rutas) if rid}
            flujos = np.zeros(escenario.ids_rutas.shape)
            for resultado in sesion.scalars(select(ResultadoRuta).where(ResultadoRuta.ejecucion_id == mejor_id)):
                if resultado.ruta_id in posicion:
                    flujos[posicion[resultado.ruta_id]] = float(resultado.toneladas)
            return LoteAG(escenario.id, inicio, parametros, corridas, estad, historial, flujos)

    def parametros_recientes(self) -> ParametrosAG | None:
        """Parámetros de la última corrida en cualquier escenario, para precargar el formulario."""
        with self._bd.sesion() as sesion:
            fila = sesion.execute(
                select(ParametrosAGBD, MetodoSeleccion.nombre, TipoCruce.nombre)
                .join(MetodoSeleccion).join(TipoCruce)
                .order_by(ParametrosAGBD.ejecucion_id.desc()).limit(1)).first()
            if fila is None:
                return None
            bd, seleccion, cruce = fila
            return ParametrosAG(bd.tamano_poblacion, bd.num_generaciones, float(bd.tasa_cruce),
                                float(bd.tasa_mutacion), seleccion, bd.tamano_torneo or 3, cruce, bd.elitismo,
                                float(bd.factor_penalizacion), bd.semilla)

    @staticmethod
    def _id(sesion, modelo, nombre: str) -> int:
        identificador = sesion.scalar(select(modelo.id).where(modelo.nombre == nombre))
        if identificador is None:
            raise ErrorValidacion(f"Falta el valor «{nombre}» en el catálogo {modelo.__tablename__}.")
        return identificador
