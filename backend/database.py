from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from typing import Iterator, Optional

from sqlalchemy import (BigInteger, Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer,
                        Numeric, SmallInteger, String, Text, UniqueConstraint, create_engine,
                        func)
from sqlalchemy.orm import (DeclarativeBase, Mapped, Session, mapped_column, relationship,
                            sessionmaker)

from backend.config import Configuracion
from backend.utils.singleton import MetaSingleton


class BaseDatos(metaclass=MetaSingleton):
    """Punto único de acceso a PostgreSQL: motor de conexiones y fábrica de sesiones."""

    def __init__(self):
        self._motor = create_engine(Configuracion().url_bd, pool_pre_ping=True,
                                     pool_size=5, max_overflow=5)
        self._fabrica_sesiones = sessionmaker(bind=self._motor, expire_on_commit=False)

    @contextmanager
    def sesion(self) -> Iterator[Session]:
        sesion = self._fabrica_sesiones()
        try:
            yield sesion
            sesion.commit()
        except Exception:
            sesion.rollback()
            raise
        finally:
            sesion.close()


class ModeloBase(DeclarativeBase):
    type_annotation_map = {datetime: DateTime(timezone=True)}


def _fecha_actual():
    return mapped_column(nullable=False, server_default=func.now())


# ---------------------------------------------------------------- Seguridad

class Rol(ModeloBase):
    __tablename__ = "rol"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(30), unique=True)
    descripcion: Mapped[Optional[str]] = mapped_column(String(150))


class Usuario(ModeloBase):
    __tablename__ = "usuario"
    __table_args__ = (CheckConstraint("intentos_fallidos >= 0"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    rol_id: Mapped[int] = mapped_column(ForeignKey("rol.id"))
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(120), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    nombres: Mapped[str] = mapped_column(String(80))
    apellidos: Mapped[str] = mapped_column(String(80))
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")
    intentos_fallidos: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    bloqueado_hasta: Mapped[Optional[datetime]]
    ultimo_acceso: Mapped[Optional[datetime]]
    creado_en: Mapped[datetime] = _fecha_actual()

    rol: Mapped[Rol] = relationship()


# ---------------------------------------------------------- Datos maestros

class Departamento(ModeloBase):
    __tablename__ = "departamento"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    codigo_dane: Mapped[str] = mapped_column(String(2), unique=True)
    nombre: Mapped[str] = mapped_column(String(60), unique=True)


class Municipio(ModeloBase):
    __tablename__ = "municipio"
    __table_args__ = (UniqueConstraint("departamento_id", "nombre"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    departamento_id: Mapped[int] = mapped_column(ForeignKey("departamento.id"))
    codigo_dane: Mapped[str] = mapped_column(String(5), unique=True)
    nombre: Mapped[str] = mapped_column(String(80))
    latitud: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    longitud: Mapped[Decimal] = mapped_column(Numeric(9, 6))

    departamento: Mapped[Departamento] = relationship()


class TipoResiduo(ModeloBase):
    __tablename__ = "tipo_residuo"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True)
    descripcion: Mapped[Optional[str]] = mapped_column(String(200))


class Empresa(ModeloBase):
    __tablename__ = "empresa"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(10), unique=True)
    nombre: Mapped[str] = mapped_column(String(100))
    nit: Mapped[Optional[str]] = mapped_column(String(15), unique=True)
    municipio_id: Mapped[int] = mapped_column(ForeignKey("municipio.id"))
    tipo_residuo_id: Mapped[int] = mapped_column(ForeignKey("tipo_residuo.id"))
    activa: Mapped[bool] = mapped_column(Boolean, server_default="true")
    creado_en: Mapped[datetime] = _fecha_actual()

    municipio: Mapped[Municipio] = relationship()
    tipo_residuo: Mapped[TipoResiduo] = relationship()


class Planta(ModeloBase):
    __tablename__ = "planta"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(10), unique=True)
    nombre: Mapped[str] = mapped_column(String(100))
    municipio_id: Mapped[int] = mapped_column(ForeignKey("municipio.id"))
    activa: Mapped[bool] = mapped_column(Boolean, server_default="true")
    creado_en: Mapped[datetime] = _fecha_actual()

    municipio: Mapped[Municipio] = relationship()


# ------------------------------------------------------------- Escenarios

class Escenario(ModeloBase):
    __tablename__ = "escenario"
    __table_args__ = (UniqueConstraint("usuario_id", "nombre"),
                      CheckConstraint("alfa_cop_t_km >= 0"),
                      CheckConstraint("factor_transporte_pct > 0"))
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    escenario_origen_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("escenario.id", ondelete="SET NULL"))
    nombre: Mapped[str] = mapped_column(String(100))
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    alfa_cop_t_km: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    factor_transporte_pct: Mapped[Decimal] = mapped_column(Numeric(10, 6), server_default="100")
    es_base: Mapped[bool] = mapped_column(Boolean, server_default="false")
    creado_en: Mapped[datetime] = _fecha_actual()
    actualizado_en: Mapped[datetime] = _fecha_actual()

    origen: Mapped[Optional["Escenario"]] = relationship(remote_side=[id])
    empresas: Mapped[list["EscenarioEmpresa"]] = relationship(
        back_populates="escenario", cascade="all, delete-orphan", passive_deletes=True)
    plantas: Mapped[list["EscenarioPlanta"]] = relationship(
        back_populates="escenario", cascade="all, delete-orphan", passive_deletes=True)


class EscenarioEmpresa(ModeloBase):
    __tablename__ = "escenario_empresa"
    __table_args__ = (UniqueConstraint("escenario_id", "empresa_id"),
                      CheckConstraint("oferta_t_semana >= 0"),
                      CheckConstraint("precio_tonelada_cop >= 0"))
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    escenario_id: Mapped[int] = mapped_column(ForeignKey("escenario.id", ondelete="CASCADE"))
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id"))
    oferta_t_semana: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    precio_tonelada_cop: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")

    escenario: Mapped[Escenario] = relationship(back_populates="empresas")
    empresa: Mapped[Empresa] = relationship()
    rutas: Mapped[list["Ruta"]] = relationship(
        back_populates="escenario_empresa", cascade="all, delete-orphan", passive_deletes=True)


class EscenarioPlanta(ModeloBase):
    __tablename__ = "escenario_planta"
    __table_args__ = (UniqueConstraint("escenario_id", "planta_id"),
                      CheckConstraint("demanda_t_semana >= 0"),
                      CheckConstraint("costo_operacion_cop_t >= 0"))
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    escenario_id: Mapped[int] = mapped_column(ForeignKey("escenario.id", ondelete="CASCADE"))
    planta_id: Mapped[int] = mapped_column(ForeignKey("planta.id"))
    demanda_t_semana: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    costo_operacion_cop_t: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    escenario: Mapped[Escenario] = relationship(back_populates="plantas")
    planta: Mapped[Planta] = relationship()
    rutas: Mapped[list["Ruta"]] = relationship(
        back_populates="escenario_planta", cascade="all, delete-orphan", passive_deletes=True)


class Ruta(ModeloBase):
    __tablename__ = "ruta"
    __table_args__ = (UniqueConstraint("escenario_empresa_id", "escenario_planta_id"),
                      CheckConstraint("distancia_km >= 0"))
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    escenario_empresa_id: Mapped[int] = mapped_column(
        ForeignKey("escenario_empresa.id", ondelete="CASCADE"))
    escenario_planta_id: Mapped[int] = mapped_column(
        ForeignKey("escenario_planta.id", ondelete="CASCADE"))
    distancia_km: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    habilitada: Mapped[bool] = mapped_column(Boolean, server_default="true")

    escenario_empresa: Mapped[EscenarioEmpresa] = relationship(back_populates="rutas")
    escenario_planta: Mapped[EscenarioPlanta] = relationship(back_populates="rutas")


# --------------------------------------------------------------- Catálogos

class MetodoSolucion(ModeloBase):
    __tablename__ = "metodo_solucion"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(40), unique=True)
    descripcion: Mapped[Optional[str]] = mapped_column(String(150))


class EstadoEjecucion(ModeloBase):
    __tablename__ = "estado_ejecucion"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(30), unique=True)


class MetodoSeleccion(ModeloBase):
    __tablename__ = "metodo_seleccion"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(30), unique=True)


class TipoCruce(ModeloBase):
    __tablename__ = "tipo_cruce"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(30), unique=True)


class TipoParametro(ModeloBase):
    __tablename__ = "tipo_parametro"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(40), unique=True)
    descripcion: Mapped[Optional[str]] = mapped_column(String(150))


# --------------------------------------------------- Ejecuciones y resultados

class Ejecucion(ModeloBase):
    __tablename__ = "ejecucion"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    escenario_id: Mapped[int] = mapped_column(ForeignKey("escenario.id", ondelete="CASCADE"))
    metodo_solucion_id: Mapped[int] = mapped_column(ForeignKey("metodo_solucion.id"))
    estado_ejecucion_id: Mapped[int] = mapped_column(ForeignKey("estado_ejecucion.id"))
    iniciada_en: Mapped[datetime] = _fecha_actual()
    tiempo_ms: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))
    costo_objetivo_cop: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 2))
    iteraciones: Mapped[Optional[int]] = mapped_column(Integer)
    mensaje: Mapped[Optional[str]] = mapped_column(Text)

    escenario: Mapped[Escenario] = relationship()
    metodo: Mapped[MetodoSolucion] = relationship()
    estado: Mapped[EstadoEjecucion] = relationship()
    resultados: Mapped[list["ResultadoRuta"]] = relationship(
        back_populates="ejecucion", cascade="all, delete-orphan", passive_deletes=True)


class ResultadoRuta(ModeloBase):
    __tablename__ = "resultado_ruta"
    __table_args__ = (UniqueConstraint("ejecucion_id", "ruta_id"),
                      CheckConstraint("toneladas >= 0"))
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ejecucion_id: Mapped[int] = mapped_column(ForeignKey("ejecucion.id", ondelete="CASCADE"))
    ruta_id: Mapped[int] = mapped_column(ForeignKey("ruta.id", ondelete="CASCADE"))
    toneladas: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    costo_reducido: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))
    costo_min_optimalidad: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))
    costo_max_optimalidad: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))

    ejecucion: Mapped[Ejecucion] = relationship(back_populates="resultados")
    ruta: Mapped[Ruta] = relationship()


# ------------------------------------------------- Análisis de sensibilidad

class SensibilidadOferta(ModeloBase):
    __tablename__ = "sensibilidad_oferta"
    __table_args__ = (UniqueConstraint("ejecucion_id", "escenario_empresa_id"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ejecucion_id: Mapped[int] = mapped_column(ForeignKey("ejecucion.id", ondelete="CASCADE"))
    escenario_empresa_id: Mapped[int] = mapped_column(
        ForeignKey("escenario_empresa.id", ondelete="CASCADE"))
    precio_sombra: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    holgura: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    oferta_min: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    oferta_max: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))


class SensibilidadDemanda(ModeloBase):
    __tablename__ = "sensibilidad_demanda"
    __table_args__ = (UniqueConstraint("ejecucion_id", "escenario_planta_id"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ejecucion_id: Mapped[int] = mapped_column(ForeignKey("ejecucion.id", ondelete="CASCADE"))
    escenario_planta_id: Mapped[int] = mapped_column(
        ForeignKey("escenario_planta.id", ondelete="CASCADE"))
    precio_sombra: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    holgura: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    demanda_min: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    demanda_max: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))


class AnalisisSensibilidad(ModeloBase):
    __tablename__ = "analisis_sensibilidad"
    __table_args__ = (CheckConstraint("variacion_min_pct < variacion_max_pct"),
                      CheckConstraint("paso_pct > 0"))
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    escenario_base_id: Mapped[int] = mapped_column(ForeignKey("escenario.id", ondelete="CASCADE"))
    tipo_parametro_id: Mapped[int] = mapped_column(ForeignKey("tipo_parametro.id"))
    empresa_id: Mapped[Optional[int]] = mapped_column(ForeignKey("empresa.id"))
    planta_id: Mapped[Optional[int]] = mapped_column(ForeignKey("planta.id"))
    nombre: Mapped[str] = mapped_column(String(100))
    variacion_min_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    variacion_max_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    paso_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    creado_en: Mapped[datetime] = _fecha_actual()


class PuntoSensibilidad(ModeloBase):
    __tablename__ = "punto_sensibilidad"
    __table_args__ = (UniqueConstraint("analisis_id", "variacion_pct"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    analisis_id: Mapped[int] = mapped_column(
        ForeignKey("analisis_sensibilidad.id", ondelete="CASCADE"))
    escenario_id: Mapped[int] = mapped_column(ForeignKey("escenario.id", ondelete="CASCADE"))
    variacion_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2))


# ------------------------------------------------------ Algoritmo genético

class ParametrosAG(ModeloBase):
    __tablename__ = "parametros_ag"
    __table_args__ = (CheckConstraint("tasa_cruce BETWEEN 0 AND 1"),
                      CheckConstraint("tasa_mutacion BETWEEN 0 AND 1"))
    ejecucion_id: Mapped[int] = mapped_column(
        ForeignKey("ejecucion.id", ondelete="CASCADE"), primary_key=True)
    metodo_seleccion_id: Mapped[int] = mapped_column(ForeignKey("metodo_seleccion.id"))
    tipo_cruce_id: Mapped[int] = mapped_column(ForeignKey("tipo_cruce.id"))
    tamano_poblacion: Mapped[int] = mapped_column(Integer)
    num_generaciones: Mapped[int] = mapped_column(Integer)
    tasa_cruce: Mapped[Decimal] = mapped_column(Numeric(4, 3))
    tasa_mutacion: Mapped[Decimal] = mapped_column(Numeric(4, 3))
    tamano_torneo: Mapped[Optional[int]] = mapped_column(SmallInteger)
    elitismo: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    factor_penalizacion: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    semilla: Mapped[Optional[int]] = mapped_column(Integer)


class HistorialGeneracion(ModeloBase):
    __tablename__ = "historial_generacion"
    __table_args__ = (UniqueConstraint("ejecucion_id", "num_generacion"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ejecucion_id: Mapped[int] = mapped_column(
        ForeignKey("parametros_ag.ejecucion_id", ondelete="CASCADE"))
    num_generacion: Mapped[int] = mapped_column(Integer)
    mejor_costo: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    costo_promedio: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    mejor_fitness: Mapped[float] = mapped_column(Float)
    violaciones: Mapped[int] = mapped_column(Integer, server_default="0")


# ---------------------------------------------------------------- Comparación

class Comparacion(ModeloBase):
    __tablename__ = "comparacion"
    __table_args__ = (UniqueConstraint("ejecucion_exacta_id", "ejecucion_ag_id"),
                      CheckConstraint("ejecucion_exacta_id <> ejecucion_ag_id"))
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ejecucion_exacta_id: Mapped[int] = mapped_column(ForeignKey("ejecucion.id", ondelete="CASCADE"))
    ejecucion_ag_id: Mapped[int] = mapped_column(ForeignKey("ejecucion.id", ondelete="CASCADE"))
    observaciones: Mapped[Optional[str]] = mapped_column(Text)
    creada_en: Mapped[datetime] = _fecha_actual()
