from typing import Callable

from sqlalchemy import select

from backend.database import (AnalisisSensibilidad as AnalisisBD, BaseDatos, Escenario, PuntoSensibilidad,
                              TipoParametro)
from backend.genetic.genetic_algorithm import ParametrosAG
from backend.sensitivity.analysis import AnalisisSensibilidad, analizar
from backend.sensitivity.scenario_simulator import (ALFA, COSTO_OPERACION, DEMANDA, OFERTA, PuntoSimulacion,
                                                    simular, variaciones)
from backend.services.genetic_service import ServicioGenetico
from backend.services.optimization_service import ServicioOptimizacion
from backend.services.scenario_service import DatosEscenario, ServicioEscenarios
from backend.utils.exceptions import ErrorValidacion
from backend.utils.singleton import MetaSingleton

NOMBRES_PARAMETRO = {ALFA: "Costo de transporte", OFERTA: "Oferta", DEMANDA: "Demanda",
                     COSTO_OPERACION: "Costo de operación"}


# Texto de una variación porcentual con su signo.
def etiqueta_variacion(variacion: float) -> str:
    if abs(variacion) < 1e-9:
        return "0 %"
    texto = f"{abs(variacion):g}".replace(".", ",")
    return f"{'+' if variacion > 0 else '−'}{texto} %"


class ServicioSensibilidad(metaclass=MetaSingleton):
    # Obtiene la instancia única de la base de datos.
    def __init__(self):
        self._bd = BaseDatos()

    # Análisis de sensibilidad del escenario; None si no tiene datos suficientes.
    def analizar(self, escenario: DatosEscenario) -> AnalisisSensibilidad | None:
        if not escenario.empresas or not escenario.plantas or not escenario.habilitadas.any():
            return None
        return analizar(escenario.problema())

    # Simula la variación de un parámetro con el método exacto y, opcionalmente, el AG.
    def simular(self, escenario: DatosEscenario, tipo: str, indice: int | None, minimo: float, maximo: float,
                paso: float, parametros_ag: ParametrosAG | None = None,
                al_avanzar: Callable[[int, int], None] | None = None) -> list[PuntoSimulacion]:
        try:
            valores = variaciones(minimo, maximo, paso)
        except ValueError as error:
            raise ErrorValidacion(str(error)) from error
        return simular(escenario.modelo(), tipo, indice, valores, parametros_ag, al_avanzar)

    # Crea y resuelve un escenario derivado por cada punto distinto de 0 %.
    def guardar_como_escenarios(self, escenario: DatosEscenario, usuario_id: int, tipo: str,
                                indice: int | None, puntos: list[PuntoSimulacion], parametros_ag: ParametrosAG | None,
                                al_avanzar: Callable[[int, int], None] | None = None) -> int:
        empresa = escenario.empresas[indice] if tipo == OFERTA and indice is not None else None
        planta = escenario.plantas[indice] if tipo in (DEMANDA, COSTO_OPERACION) and indice is not None else None
        objetivo = (f" de {empresa.codigo}" if empresa else f" de {planta.codigo}" if planta
                    else "" if tipo == ALFA else " total")
        nombre_base = f"{NOMBRES_PARAMETRO[tipo]}{objetivo}"
        valores = [p.variacion_pct for p in puntos if abs(p.variacion_pct) > 1e-9]
        if not valores:
            raise ErrorValidacion("La simulación no tiene variaciones distintas de 0 % para guardar.")

        with self._bd.sesion() as sesion:
            tipo_id = sesion.scalar(select(TipoParametro.id).where(TipoParametro.nombre == tipo))
            analisis = AnalisisBD(escenario_base_id=escenario.id, tipo_parametro_id=tipo_id,
                                  empresa_id=empresa.empresa_id if empresa else None,
                                  planta_id=planta.planta_id if planta else None,
                                  nombre=f"{nombre_base} · {escenario.nombre}"[:100],
                                  variacion_min_pct=min(p.variacion_pct for p in puntos),
                                  variacion_max_pct=max(p.variacion_pct for p in puntos),
                                  paso_pct=_paso(puntos))
            sesion.add(analisis)
            sesion.flush()
            analisis_id = analisis.id

        escenarios, optimizacion, genetico = ServicioEscenarios(), ServicioOptimizacion(), ServicioGenetico()
        for k, variacion in enumerate(valores, start=1):
            etiqueta = etiqueta_variacion(variacion)
            nuevo_id = escenarios.duplicar(
                escenario.id, usuario_id, self._nombre_libre(usuario_id, f"{nombre_base} {etiqueta}"),
                f"{nombre_base} {etiqueta} respecto a «{escenario.nombre}»")
            escenarios.aplicar_variacion(nuevo_id, tipo, empresa.empresa_id if empresa else None,
                                         planta.planta_id if planta else None, variacion)
            datos = escenarios.cargar(nuevo_id)
            optimizacion.resolver_exacto(datos)
            if parametros_ag is not None:
                genetico.resolver(datos, parametros_ag, 1)
            with self._bd.sesion() as sesion:
                sesion.add(PuntoSensibilidad(analisis_id=analisis_id, escenario_id=nuevo_id, variacion_pct=variacion))
            if al_avanzar:
                al_avanzar(k, len(valores))
        return len(valores)

    # Nombre de escenario que aún no existe para el usuario.
    def _nombre_libre(self, usuario_id: int, nombre: str) -> str:
        with self._bd.sesion() as sesion:
            existentes = set(sesion.scalars(select(Escenario.nombre).where(Escenario.usuario_id == usuario_id)))
        candidato, k = nombre[:100], 2
        while candidato in existentes:
            candidato, k = f"{nombre} ({k})"[:100], k + 1
        return candidato


# Paso de la simulación a partir de los puntos guardados.
def _paso(puntos: list[PuntoSimulacion]) -> float:
    valores = sorted(p.variacion_pct for p in puntos)
    diferencias = [b - a for a, b in zip(valores, valores[1:]) if b - a > 1e-9]
    return min(diferencias) if diferencias else 1.0
