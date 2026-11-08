import re
from dataclasses import dataclass

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from backend.database import (BaseDatos, Ejecucion, Empresa, Escenario, EscenarioEmpresa,
                              EscenarioPlanta, MetodoSolucion, Municipio, Planta, Ruta)
from backend.exact.transport_model import ProblemaTransporte
from backend.network.balance import TipoBalance, verificar_balance
from backend.network.cost_matrix import alfa_efectivo, costos_unitarios, factor_desde_costo
from backend.utils.exceptions import ErrorNoEncontrado, ErrorValidacion
from backend.utils.singleton import MetaSingleton


def clave_natural(codigo: str):
    """Ordena E2 antes que E10."""
    coincidencia = re.match(r"([A-Za-z]*)(\d*)", codigo)
    prefijo, numero = coincidencia.groups() if coincidencia else (codigo, "")
    return prefijo, int(numero) if numero else 0


@dataclass(frozen=True)
class ResumenEscenario:
    id: int
    nombre: str
    es_base: bool


@dataclass(frozen=True)
class TarjetaEscenario:
    id: int
    nombre: str
    descripcion: str | None
    es_base: bool
    origen: str | None
    empresas: int
    plantas: int
    alfa: float
    factor_transporte: float
    balanceado: bool
    costo_exacto: float | None


@dataclass(frozen=True)
class FilaEmpresa:
    id_vinculo: int
    empresa_id: int
    codigo: str
    nombre: str
    nit: str | None
    municipio_id: int
    municipio: str
    latitud: float
    longitud: float
    tipo_residuo_id: int
    tipo_residuo: str
    activa: bool
    oferta: float
    precio: float


@dataclass(frozen=True)
class FilaPlanta:
    id_vinculo: int
    planta_id: int
    codigo: str
    nombre: str
    municipio_id: int
    municipio: str
    latitud: float
    longitud: float
    departamento: str
    activa: bool
    demanda: float
    costo_operacion: float


@dataclass
class DatosEscenario:
    id: int
    nombre: str
    alfa: float
    factor_transporte: float
    es_base: bool
    origen: str | None
    empresas: list[FilaEmpresa]
    plantas: list[FilaPlanta]
    distancias: np.ndarray
    ids_rutas: np.ndarray
    habilitadas: np.ndarray

    @property
    def oferta(self) -> np.ndarray:
        return np.array([e.oferta for e in self.empresas], float)

    @property
    def demanda(self) -> np.ndarray:
        return np.array([p.demanda for p in self.plantas], float)

    @property
    def costos_operacion(self) -> np.ndarray:
        return np.array([p.costo_operacion for p in self.plantas], float)

    @property
    def precios_compra(self) -> np.ndarray:
        return np.array([e.precio for e in self.empresas], float)

    @property
    def alfa_efectivo(self) -> float:
        return alfa_efectivo(self.alfa, self.factor_transporte)

    @property
    def costos_unitarios(self) -> np.ndarray:
        return costos_unitarios(self.alfa_efectivo, np.nan_to_num(self.distancias),
                                self.costos_operacion, self.precios_compra)

    def problema(self) -> ProblemaTransporte:
        return ProblemaTransporte(self.oferta, self.demanda, self.costos_unitarios,
                                  self.habilitadas.copy())


class ServicioEscenarios(metaclass=MetaSingleton):
    """Lectura y actualización de los parámetros del modelo por escenario."""

    def __init__(self):
        self._bd = BaseDatos()

    def listar(self) -> list[ResumenEscenario]:
        with self._bd.sesion() as sesion:
            escenarios = sesion.scalars(select(Escenario).order_by(
                Escenario.es_base.desc(), Escenario.creado_en)).all()
            return [ResumenEscenario(e.id, e.nombre, e.es_base) for e in escenarios]

    def cargar(self, escenario_id: int) -> DatosEscenario:
        with self._bd.sesion() as sesion:
            empresa = selectinload(Escenario.empresas).selectinload(EscenarioEmpresa.empresa)
            escenario = sesion.scalar(
                select(Escenario).where(Escenario.id == escenario_id).options(
                    selectinload(Escenario.origen),
                    empresa.selectinload(Empresa.municipio),
                    empresa.selectinload(Empresa.tipo_residuo),
                    selectinload(Escenario.empresas).selectinload(EscenarioEmpresa.rutas),
                    selectinload(Escenario.plantas).selectinload(EscenarioPlanta.planta)
                    .selectinload(Planta.municipio).selectinload(Municipio.departamento)))
            if escenario is None:
                raise ErrorNoEncontrado("El escenario seleccionado no existe.")

            vinculos_e = sorted(escenario.empresas, key=lambda v: clave_natural(v.empresa.codigo))
            vinculos_p = sorted(escenario.plantas, key=lambda v: clave_natural(v.planta.codigo))
            empresas = [FilaEmpresa(
                v.id, v.empresa.id, v.empresa.codigo, v.empresa.nombre, v.empresa.nit,
                v.empresa.municipio_id,
                v.empresa.municipio.nombre, float(v.empresa.municipio.latitud),
                float(v.empresa.municipio.longitud), v.empresa.tipo_residuo_id,
                v.empresa.tipo_residuo.nombre, v.empresa.activa,
                float(v.oferta_t_semana), float(v.precio_tonelada_cop)) for v in vinculos_e]
            plantas = [FilaPlanta(
                v.id, v.planta.id, v.planta.codigo, v.planta.nombre, v.planta.municipio_id,
                v.planta.municipio.nombre, float(v.planta.municipio.latitud),
                float(v.planta.municipio.longitud), v.planta.municipio.departamento.nombre,
                v.planta.activa, float(v.demanda_t_semana),
                float(v.costo_operacion_cop_t)) for v in vinculos_p]

            m, n = len(empresas), len(plantas)
            fila_de = {v.id: i for i, v in enumerate(vinculos_e)}
            columna_de = {v.id: j for j, v in enumerate(vinculos_p)}
            distancias = np.full((m, n), np.nan)
            ids_rutas = np.zeros((m, n), dtype=np.int64)
            habilitadas = np.zeros((m, n), dtype=bool)
            for vinculo in vinculos_e:
                for ruta in vinculo.rutas:
                    i, j = fila_de[ruta.escenario_empresa_id], columna_de[ruta.escenario_planta_id]
                    distancias[i, j] = float(ruta.distancia_km)
                    ids_rutas[i, j] = ruta.id
                    habilitadas[i, j] = ruta.habilitada

            return DatosEscenario(escenario.id, escenario.nombre, float(escenario.alfa_cop_t_km),
                                  float(escenario.factor_transporte_pct), escenario.es_base,
                                  escenario.origen.nombre if escenario.origen else None,
                                  empresas, plantas, distancias, ids_rutas, habilitadas)

    def guardar_alfa(self, escenario_id: int, costo_transporte: float) -> None:
        """Fija el costo de transporte usado en el modelo ajustando el factor sobre el costo base."""
        if costo_transporte <= 0:
            raise ErrorValidacion("El costo de transporte debe ser mayor que 0.")
        with self._bd.sesion() as sesion:
            escenario = self._obtener(sesion, escenario_id)
            escenario.factor_transporte_pct = factor_desde_costo(costo_transporte,
                                                                 float(escenario.alfa_cop_t_km))

    def guardar_distancias(self, distancias: dict[int, float]) -> None:
        """Actualiza dᵢⱼ por ruta; una ruta queda habilitada cuando su distancia es positiva."""
        if any(km < 0 for km in distancias.values()):
            raise ErrorValidacion("Las distancias deben ser mayores o iguales a 0.")
        with self._bd.sesion() as sesion:
            for ruta in sesion.scalars(select(Ruta).where(Ruta.id.in_(distancias))):
                ruta.distancia_km = distancias[ruta.id]
                ruta.habilitada = distancias[ruta.id] > 0

    def guardar_parametros(self, escenario_id: int, nombre: str, factor: float,
                           empresas: dict[int, tuple[float, float]],
                           plantas: dict[int, tuple[float, float]]) -> None:
        """empresas: {vínculo: (oferta, precio por tonelada)}; plantas: {vínculo: (demanda, costo)}."""
        nombre = nombre.strip()
        if not nombre:
            raise ErrorValidacion("El escenario debe tener un nombre.")
        if factor <= 0:
            raise ErrorValidacion("El factor de costo de transporte debe ser mayor que 0 %.")
        valores = [v for par in (*empresas.values(), *plantas.values()) for v in par]
        if any(v < 0 for v in valores):
            raise ErrorValidacion("Oferta, demanda, precios y costos deben ser mayores o iguales a 0.")

        with self._bd.sesion() as sesion:
            escenario = self._obtener(sesion, escenario_id)
            self._validar_nombre_libre(sesion, escenario.usuario_id, nombre, escenario_id)
            escenario.nombre = nombre
            escenario.factor_transporte_pct = factor
            escenario.actualizado_en = func.now()
            for vinculo in escenario.empresas:
                if vinculo.id in empresas:
                    vinculo.oferta_t_semana, vinculo.precio_tonelada_cop = empresas[vinculo.id]
            for vinculo in escenario.plantas:
                if vinculo.id in plantas:
                    vinculo.demanda_t_semana, vinculo.costo_operacion_cop_t = plantas[vinculo.id]

    def resumenes(self, metodo: str) -> list[TarjetaEscenario]:
        """Datos de las tarjetas de la página Escenarios, con el último costo del método dado."""
        with self._bd.sesion() as sesion:
            escenarios = sesion.scalars(
                select(Escenario).options(selectinload(Escenario.origen),
                                          selectinload(Escenario.empresas),
                                          selectinload(Escenario.plantas))
                .order_by(Escenario.es_base.desc(), Escenario.creado_en)).all()
            ultimo = (select(Ejecucion.escenario_id, func.max(Ejecucion.id).label("id"))
                      .join(MetodoSolucion).where(MetodoSolucion.nombre == metodo)
                      .group_by(Ejecucion.escenario_id).subquery())
            costos = dict(sesion.execute(
                select(Ejecucion.escenario_id, Ejecucion.costo_objetivo_cop)
                .join(ultimo, Ejecucion.id == ultimo.c.id)).all())

            tarjetas = []
            for e in escenarios:
                oferta = sum(float(v.oferta_t_semana) for v in e.empresas)
                demanda = sum(float(v.demanda_t_semana) for v in e.plantas)
                costo = costos.get(e.id)
                tarjetas.append(TarjetaEscenario(
                    id=e.id, nombre=e.nombre, descripcion=e.descripcion, es_base=e.es_base,
                    origen=e.origen.nombre if e.origen else None,
                    empresas=len(e.empresas), plantas=len(e.plantas),
                    alfa=float(e.alfa_cop_t_km), factor_transporte=float(e.factor_transporte_pct),
                    balanceado=verificar_balance(np.array([oferta]), np.array([demanda])).tipo
                    is TipoBalance.BALANCEADO,
                    costo_exacto=float(costo) if costo is not None else None))
            return tarjetas

    def duplicar(self, escenario_id: int, usuario_id: int, nombre: str | None = None,
                 descripcion: str | None = None) -> int:
        """Copia oferta, precios, demanda, costos y rutas en un escenario derivado del original."""
        with self._bd.sesion() as sesion:
            original = sesion.scalar(
                select(Escenario).where(Escenario.id == escenario_id).options(
                    selectinload(Escenario.empresas).selectinload(EscenarioEmpresa.rutas),
                    selectinload(Escenario.plantas)))
            if original is None:
                raise ErrorNoEncontrado("El escenario seleccionado no existe.")
            nombre = (nombre or "").strip() or self._nombre_copia(sesion, usuario_id, original.nombre)
            self._validar_nombre_libre(sesion, usuario_id, nombre)

            copia = Escenario(usuario_id=usuario_id, origen=original, nombre=nombre,
                              descripcion=(descripcion or "").strip() or original.descripcion,
                              alfa_cop_t_km=original.alfa_cop_t_km,
                              factor_transporte_pct=original.factor_transporte_pct, es_base=False)
            plantas = {}
            for v in original.plantas:
                plantas[v.id] = EscenarioPlanta(planta_id=v.planta_id, demanda_t_semana=v.demanda_t_semana,
                                                costo_operacion_cop_t=v.costo_operacion_cop_t)
                copia.plantas.append(plantas[v.id])
            for v in original.empresas:
                vinculo = EscenarioEmpresa(empresa_id=v.empresa_id, oferta_t_semana=v.oferta_t_semana,
                                           precio_tonelada_cop=v.precio_tonelada_cop)
                copia.empresas.append(vinculo)
                for ruta in v.rutas:
                    sesion.add(Ruta(escenario_empresa=vinculo,
                                    escenario_planta=plantas[ruta.escenario_planta_id],
                                    distancia_km=ruta.distancia_km, habilitada=ruta.habilitada))
            sesion.add(copia)
            sesion.flush()
            return copia.id

    @staticmethod
    def _nombre_copia(sesion, usuario_id: int, base: str) -> str:
        existentes = set(sesion.scalars(select(Escenario.nombre).where(Escenario.usuario_id == usuario_id)))
        nombre, k = f"{base} (copia)", 2
        while nombre in existentes:
            nombre, k = f"{base} (copia {k})", k + 1
        return nombre

    @staticmethod
    def _validar_nombre_libre(sesion, usuario_id: int, nombre: str, excluir_id: int | None = None):
        duplicado = sesion.scalar(select(Escenario.id).where(
            Escenario.usuario_id == usuario_id, Escenario.nombre == nombre,
            Escenario.id != (excluir_id or 0)))
        if duplicado:
            raise ErrorValidacion(f"Ya existe un escenario llamado «{nombre}».")

    @staticmethod
    def _obtener(sesion, escenario_id: int) -> Escenario:
        escenario = sesion.get(Escenario, escenario_id)
        if escenario is None:
            raise ErrorNoEncontrado("El escenario seleccionado no existe.")
        return escenario
