from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.comparison.metrics import gap
from backend.database import BaseDatos, Comparacion, Ejecucion, Escenario
from backend.services.genetic_service import METODO_GENETICO
from backend.services.optimization_service import METODO_EXACTO
from backend.utils.singleton import MetaSingleton


@dataclass(frozen=True)
class FilaComparacion:
    escenario_id: int
    escenario: str
    es_base: bool
    exacta_id: int | None
    costo_exacto: float | None
    milisegundos_exacto: float | None
    ag_id: int | None
    costo_ag: float | None
    milisegundos_ag: float | None
    corridas_ag: int

    @property
    def gap(self) -> float | None:
        return gap(self.costo_ag, self.costo_exacto)


class ServicioComparacion(metaclass=MetaSingleton):
    """Resultados del método exacto y del AG por escenario, y registro de comparaciones."""

    def __init__(self):
        self._bd = BaseDatos()

    def por_escenarios(self, ids: list[int] | None = None) -> list[FilaComparacion]:
        """Por escenario: la última solución exacta y la mejor corrida del último lote del AG."""
        with self._bd.sesion() as sesion:
            consulta = select(Escenario).order_by(Escenario.es_base.desc(), Escenario.creado_en)
            if ids:
                consulta = consulta.where(Escenario.id.in_(ids))
            escenarios = sesion.scalars(consulta).all()
            ejecuciones = sesion.scalars(
                select(Ejecucion).where(Ejecucion.escenario_id.in_([e.id for e in escenarios]))
                .options(selectinload(Ejecucion.metodo), selectinload(Ejecucion.estado))
                .order_by(Ejecucion.iniciada_en.desc(), Ejecucion.id.desc())).all()

            filas = []
            for escenario in escenarios:
                propias = [e for e in ejecuciones if e.escenario_id == escenario.id]
                exacta = next((e for e in propias if e.metodo.nombre == METODO_EXACTO), None)
                ag = [e for e in propias if e.metodo.nombre == METODO_GENETICO]
                lote = [e for e in ag if e.iniciada_en == ag[0].iniciada_en] if ag else []
                factibles = [e for e in lote if e.estado.nombre == "FACTIBLE"] or lote
                mejor = min(factibles, key=lambda e: float(e.costo_objetivo_cop)) if factibles else None
                filas.append(FilaComparacion(
                    escenario.id, escenario.nombre, escenario.es_base,
                    exacta.id if exacta else None,
                    float(exacta.costo_objetivo_cop) if exacta and exacta.costo_objetivo_cop is not None else None,
                    float(exacta.tiempo_ms) if exacta and exacta.tiempo_ms is not None else None,
                    mejor.id if mejor else None,
                    float(mejor.costo_objetivo_cop) if mejor else None,
                    sum(float(e.tiempo_ms or 0) for e in lote) / len(lote) if lote else None,
                    len(lote)))
            return filas

    def registrar(self, exacta_id: int, ag_id: int, observaciones: str | None = None) -> None:
        """Guarda la pareja comparada (una sola vez por pareja)."""
        with self._bd.sesion() as sesion:
            existe = sesion.scalar(select(Comparacion.id).where(Comparacion.ejecucion_exacta_id == exacta_id,
                                                                Comparacion.ejecucion_ag_id == ag_id))
            if not existe:
                sesion.add(Comparacion(ejecucion_exacta_id=exacta_id, ejecucion_ag_id=ag_id,
                                       observaciones=observaciones))
