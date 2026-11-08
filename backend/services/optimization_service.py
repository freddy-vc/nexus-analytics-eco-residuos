from dataclasses import dataclass
from datetime import datetime

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.config import Configuracion
from backend.database import (BaseDatos, Ejecucion, EstadoEjecucion, MetodoSolucion,
                              ResultadoRuta, SensibilidadDemanda, SensibilidadOferta)
from backend.exact.simplex import EstadoSolucion
from backend.exact.solution_validator import ReporteFactibilidad, validar_solucion
from backend.exact.transport_model import ModeloTransporte
from backend.network.balance import EstadoBalance, TipoBalance, verificar_balance
from backend.network.cost_matrix import DesgloseCosto, desglose_costo
from backend.sensitivity.analysis import AnalisisSensibilidad, analizar
from backend.services.scenario_service import DatosEscenario
from backend.utils.exceptions import ErrorValidacion
from backend.utils.singleton import MetaSingleton

METODO_EXACTO = "EXACTO_SIMPLEX"

_NOMBRES_ESTADO = {
    EstadoSolucion.OPTIMO: "OPTIMO",
    EstadoSolucion.INFACTIBLE: "INFACTIBLE",
    EstadoSolucion.NO_ACOTADO: "NO_ACOTADO",
    EstadoSolucion.LIMITE_ITERACIONES: "ERROR",
}


@dataclass
class EjecucionExacta:
    ejecucion_id: int
    estado: str
    objetivo: float | None
    milisegundos: float
    iteraciones: int
    ejecutada_en: datetime
    mensaje: str | None
    flujos: np.ndarray | None
    balance: EstadoBalance
    desglose: DesgloseCosto | None
    factibilidad: ReporteFactibilidad | None
    num_variables: int
    num_restricciones: int

    @property
    def es_optima(self) -> bool:
        return self.estado == "OPTIMO"

    @property
    def costo_total(self) -> float | None:
        """El costo unitario ya incluye la compra, así que Z es el costo total."""
        return self.objetivo


@dataclass(frozen=True)
class ResumenEjecucion:
    metodo: str
    escenario: str
    estado: str
    objetivo: float | None
    milisegundos: float | None
    ejecutada_en: datetime


class ServicioOptimizacion(metaclass=MetaSingleton):
    """Ejecuta el modelo exacto, guarda la ejecución y recupera sus resultados."""

    def __init__(self):
        self._bd = BaseDatos()
        self._tolerancia = Configuracion().tolerancia_factibilidad

    def resolver_exacto(self, escenario: DatosEscenario) -> EjecucionExacta:
        if not escenario.empresas or not escenario.plantas:
            raise ErrorValidacion("El escenario necesita al menos una empresa y una planta.")
        if not escenario.habilitadas.any():
            raise ErrorValidacion("No hay rutas habilitadas: registra las distancias en Rutas y costos.")

        solucion = ModeloTransporte(escenario.problema()).resolver()
        mensaje = self._mensaje_balance(solucion.balance, escenario)

        with self._bd.sesion() as sesion:
            ejecucion = Ejecucion(
                escenario_id=escenario.id,
                metodo_solucion_id=self._id_catalogo(sesion, MetodoSolucion, METODO_EXACTO),
                estado_ejecucion_id=self._id_catalogo(sesion, EstadoEjecucion,
                                                      _NOMBRES_ESTADO[solucion.estado]),
                tiempo_ms=round(solucion.milisegundos, 3),
                costo_objetivo_cop=solucion.objetivo,
                iteraciones=solucion.iteraciones,
                mensaje=mensaje)
            sesion.add(ejecucion)
            sesion.flush()
            if solucion.flujos is not None:
                self._guardar_resultados(sesion, ejecucion.id, escenario, solucion.flujos,
                                         analizar(escenario.problema()))
            ejecucion_id = ejecucion.id

        return self.ultima_exacta(escenario, ejecucion_id)

    @staticmethod
    def _guardar_resultados(sesion, ejecucion_id: int, escenario: DatosEscenario, flujos: np.ndarray,
                            analisis: AnalisisSensibilidad | None) -> None:
        """Flujos por ruta y, si hay análisis, costos reducidos, rangos y precios sombra."""
        mascara = escenario.habilitadas
        rutas = analisis.rutas if analisis else [None] * int(mascara.sum())
        sesion.add_all(
            ResultadoRuta(ejecucion_id=ejecucion_id, ruta_id=int(ruta_id), toneladas=round(float(toneladas), 2),
                          costo_reducido=_decimal(r.costo_reducido) if r else None,
                          costo_min_optimalidad=_decimal(r.costo_minimo) if r else None,
                          costo_max_optimalidad=_decimal(r.costo_maximo) if r else None)
            for ruta_id, toneladas, r in zip(escenario.ids_rutas[mascara], flujos[mascara], rutas))
        if analisis is None:
            return
        sesion.add_all(
            SensibilidadOferta(ejecucion_id=ejecucion_id, escenario_empresa_id=empresa.id_vinculo,
                               precio_sombra=round(nodo.precio_sombra, 2), holgura=round(nodo.holgura, 2),
                               oferta_min=_decimal(nodo.minimo), oferta_max=_decimal(nodo.maximo))
            for empresa, nodo in zip(escenario.empresas, analisis.empresas))
        sesion.add_all(
            SensibilidadDemanda(ejecucion_id=ejecucion_id, escenario_planta_id=planta.id_vinculo,
                                precio_sombra=round(nodo.precio_sombra, 2), holgura=round(nodo.holgura, 2),
                                demanda_min=_decimal(nodo.minimo), demanda_max=_decimal(nodo.maximo))
            for planta, nodo in zip(escenario.plantas, analisis.plantas))

    def ultima_exacta(self, escenario: DatosEscenario,
                      ejecucion_id: int | None = None) -> EjecucionExacta | None:
        with self._bd.sesion() as sesion:
            consulta = (select(Ejecucion)
                        .join(MetodoSolucion)
                        .where(Ejecucion.escenario_id == escenario.id,
                               MetodoSolucion.nombre == METODO_EXACTO)
                        .options(selectinload(Ejecucion.estado), selectinload(Ejecucion.resultados))
                        .order_by(Ejecucion.iniciada_en.desc(), Ejecucion.id.desc()))
            if ejecucion_id is not None:
                consulta = consulta.where(Ejecucion.id == ejecucion_id)
            ejecucion = sesion.scalars(consulta.limit(1)).first()
            if ejecucion is None:
                return None
            return self._a_ejecucion(ejecucion, escenario)

    def ejecuciones_recientes(self, limite: int = 4) -> list[ResumenEjecucion]:
        """Últimas ejecuciones; las corridas de un mismo lote del AG se muestran como una sola (la mejor)."""
        with self._bd.sesion() as sesion:
            candidatas = sesion.scalars(
                select(Ejecucion)
                .options(selectinload(Ejecucion.metodo), selectinload(Ejecucion.estado),
                         selectinload(Ejecucion.escenario))
                .order_by(Ejecucion.iniciada_en.desc(), Ejecucion.id.desc())
                .limit(limite * 60)).all()
            lotes: dict[tuple, Ejecucion] = {}
            for e in candidatas:
                clave = (e.escenario_id, e.metodo_solucion_id, e.iniciada_en) \
                    if e.metodo.nombre != METODO_EXACTO else ("exacta", e.id)
                actual = lotes.get(clave)
                if actual is None or _mejor_que(e, actual):
                    lotes[clave] = e
            filas = sorted(lotes.values(), key=lambda e: (e.iniciada_en, e.id), reverse=True)[:limite]
            return [ResumenEjecucion(
                metodo=self._etiqueta(e.metodo.nombre, e.escenario),
                escenario=e.escenario.nombre, estado=e.estado.nombre,
                objetivo=float(e.costo_objetivo_cop) if e.costo_objetivo_cop is not None else None,
                milisegundos=float(e.tiempo_ms) if e.tiempo_ms is not None else None,
                ejecutada_en=e.iniciada_en) for e in filas]

    def _a_ejecucion(self, ejecucion: Ejecucion, escenario: DatosEscenario) -> EjecucionExacta:
        balance = verificar_balance(escenario.oferta, escenario.demanda)
        flujos = desglose = factibilidad = None
        if ejecucion.resultados:
            posicion = {int(rid): (i, j) for (i, j), rid in np.ndenumerate(escenario.ids_rutas) if rid}
            flujos = np.zeros(escenario.ids_rutas.shape)
            for resultado in ejecucion.resultados:
                if resultado.ruta_id in posicion:
                    flujos[posicion[resultado.ruta_id]] = float(resultado.toneladas)
            desglose = desglose_costo(escenario.alfa_efectivo, escenario.distancias,
                                      escenario.costos_operacion, escenario.precios_compra, flujos)
            factibilidad = validar_solucion(
                flujos, escenario.oferta, escenario.demanda, escenario.habilitadas,
                self._tolerancia, permitir_sin_enviar=balance.tipo is TipoBalance.EXCESO_OFERTA)

        return EjecucionExacta(
            ejecucion_id=ejecucion.id, estado=ejecucion.estado.nombre,
            objetivo=float(ejecucion.costo_objetivo_cop) if ejecucion.costo_objetivo_cop is not None else None,
            milisegundos=float(ejecucion.tiempo_ms or 0), iteraciones=ejecucion.iteraciones or 0,
            ejecutada_en=ejecucion.iniciada_en, mensaje=ejecucion.mensaje, flujos=flujos,
            balance=balance, desglose=desglose, factibilidad=factibilidad,
            num_variables=int(escenario.habilitadas.sum()),
            num_restricciones=len(escenario.empresas) + len(escenario.plantas))

    @staticmethod
    def _etiqueta(metodo: str, escenario) -> str:
        if escenario.es_base:
            return "Exacto" if metodo == METODO_EXACTO else "Algoritmo genético"
        return f"{'Exacto' if metodo == METODO_EXACTO else 'AG'} · {escenario.nombre}"

    @staticmethod
    def _mensaje_balance(balance: EstadoBalance, escenario: DatosEscenario) -> str:
        if balance.tipo is TipoBalance.EXCESO_OFERTA:
            return (f"Oferta mayor que la demanda en {balance.diferencia:g} t: "
                    f"se agregó la planta ficticia P{len(escenario.plantas) + 1}.")
        if balance.tipo is TipoBalance.EXCESO_DEMANDA:
            return (f"Demanda mayor que la oferta en {-balance.diferencia:g} t: "
                    f"se agregó la empresa ficticia E{len(escenario.empresas) + 1}.")
        return "Problema balanceado: no se requieren nodos ficticios."

    @staticmethod
    def _id_catalogo(sesion, modelo, nombre: str) -> int:
        id_catalogo = sesion.scalar(select(modelo.id).where(modelo.nombre == nombre))
        if id_catalogo is None:
            raise ErrorValidacion(f"Falta el valor «{nombre}» en el catálogo {modelo.__tablename__}.")
        return id_catalogo


def _decimal(valor: float) -> float | None:
    """Los rangos infinitos se guardan como NULL (sin límite)."""
    return round(float(valor), 2) if np.isfinite(valor) else None


def _mejor_que(a: Ejecucion, b: Ejecucion) -> bool:
    factible_a, factible_b = a.estado.nombre in ("OPTIMO", "FACTIBLE"), b.estado.nombre in ("OPTIMO", "FACTIBLE")
    if factible_a != factible_b:
        return factible_a
    costo_a = float(a.costo_objetivo_cop) if a.costo_objetivo_cop is not None else float("inf")
    costo_b = float(b.costo_objetivo_cop) if b.costo_objetivo_cop is not None else float("inf")
    return costo_a < costo_b
