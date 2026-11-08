from dataclasses import dataclass

from sqlalchemy import delete, select

from backend.database import (AnalisisSensibilidad, BaseDatos, Empresa, Escenario,
                              EscenarioEmpresa, EscenarioPlanta, Municipio, Planta, Ruta,
                              TipoResiduo)
from backend.services.scenario_service import clave_natural
from backend.utils.exceptions import ErrorNoEncontrado, ErrorValidacion
from backend.utils.singleton import MetaSingleton


@dataclass(frozen=True)
class ElementoCatalogo:
    id: int
    nombre: str


@dataclass(frozen=True)
class DatosEmpresa:
    codigo: str
    nombre: str
    nit: str | None
    municipio_id: int
    tipo_residuo_id: int
    oferta: float
    precio: float


@dataclass(frozen=True)
class DatosPlanta:
    codigo: str
    municipio_id: int
    demanda: float
    costo_operacion: float


class ServicioRed(metaclass=MetaSingleton):
    """Gestión de empresas (orígenes) y plantas (destinos) de la red.

    Al crear un nodo se vincula al escenario activo y se generan sus rutas hacia
    todos los nodos del otro conjunto, deshabilitadas hasta registrar la distancia.
    """

    def __init__(self):
        self._bd = BaseDatos()

    def municipios(self) -> list[ElementoCatalogo]:
        with self._bd.sesion() as sesion:
            filas = sesion.scalars(select(Municipio).order_by(Municipio.nombre))
            return [ElementoCatalogo(m.id, m.nombre) for m in filas]

    def tipos_residuo(self) -> list[ElementoCatalogo]:
        with self._bd.sesion() as sesion:
            filas = sesion.scalars(select(TipoResiduo).order_by(TipoResiduo.nombre))
            return [ElementoCatalogo(t.id, t.nombre) for t in filas]

    def siguiente_codigo(self, prefijo: str) -> str:
        modelo = Empresa if prefijo == "E" else Planta
        with self._bd.sesion() as sesion:
            codigos = sesion.scalars(select(modelo.codigo)).all()
        numeros = [clave_natural(c)[1] for c in codigos if c.upper().startswith(prefijo)]
        return f"{prefijo}{max(numeros, default=0) + 1}"

    def crear_empresa(self, escenario_id: int, datos: DatosEmpresa) -> None:
        datos = self._limpiar_empresa(datos)
        with self._bd.sesion() as sesion:
            escenario = self._escenario(sesion, escenario_id)
            self._validar_empresa_unica(sesion, datos)
            empresa = Empresa(codigo=datos.codigo, nombre=datos.nombre, nit=datos.nit,
                              municipio_id=datos.municipio_id,
                              tipo_residuo_id=datos.tipo_residuo_id)
            vinculo = EscenarioEmpresa(empresa=empresa, oferta_t_semana=datos.oferta,
                                       precio_tonelada_cop=datos.precio)
            escenario.empresas.append(vinculo)
            for vinculo_planta in escenario.plantas:
                sesion.add(Ruta(escenario_empresa=vinculo, escenario_planta=vinculo_planta,
                                distancia_km=0, habilitada=False))

    def actualizar_empresa(self, empresa_id: int, id_vinculo: int, datos: DatosEmpresa) -> None:
        datos = self._limpiar_empresa(datos)
        with self._bd.sesion() as sesion:
            empresa = sesion.get(Empresa, empresa_id)
            vinculo = sesion.get(EscenarioEmpresa, id_vinculo)
            if empresa is None or vinculo is None:
                raise ErrorNoEncontrado("La empresa ya no existe.")
            self._validar_empresa_unica(sesion, datos, excluir_id=empresa_id)
            empresa.codigo, empresa.nombre, empresa.nit = datos.codigo, datos.nombre, datos.nit
            empresa.municipio_id, empresa.tipo_residuo_id = datos.municipio_id, datos.tipo_residuo_id
            vinculo.oferta_t_semana, vinculo.precio_tonelada_cop = datos.oferta, datos.precio

    def eliminar_empresa(self, empresa_id: int) -> None:
        """Elimina la empresa de todos los escenarios junto con sus rutas y resultados."""
        with self._bd.sesion() as sesion:
            empresa = sesion.get(Empresa, empresa_id)
            if empresa is None:
                raise ErrorNoEncontrado("La empresa ya no existe.")
            sesion.execute(delete(EscenarioEmpresa).where(
                EscenarioEmpresa.empresa_id == empresa_id))
            sesion.execute(delete(AnalisisSensibilidad).where(
                AnalisisSensibilidad.empresa_id == empresa_id))
            sesion.delete(empresa)

    def crear_planta(self, escenario_id: int, datos: DatosPlanta) -> None:
        datos = self._limpiar_planta(datos)
        with self._bd.sesion() as sesion:
            escenario = self._escenario(sesion, escenario_id)
            self._validar_planta_unica(sesion, datos.codigo)
            municipio = sesion.get(Municipio, datos.municipio_id)
            planta = Planta(codigo=datos.codigo, nombre=f"Planta {municipio.nombre}",
                            municipio_id=datos.municipio_id)
            vinculo = EscenarioPlanta(planta=planta, demanda_t_semana=datos.demanda,
                                      costo_operacion_cop_t=datos.costo_operacion)
            escenario.plantas.append(vinculo)
            for vinculo_empresa in escenario.empresas:
                sesion.add(Ruta(escenario_empresa=vinculo_empresa, escenario_planta=vinculo,
                                distancia_km=0, habilitada=False))

    def actualizar_planta(self, planta_id: int, id_vinculo: int, datos: DatosPlanta) -> None:
        datos = self._limpiar_planta(datos)
        with self._bd.sesion() as sesion:
            planta = sesion.get(Planta, planta_id)
            vinculo = sesion.get(EscenarioPlanta, id_vinculo)
            if planta is None or vinculo is None:
                raise ErrorNoEncontrado("La planta ya no existe.")
            self._validar_planta_unica(sesion, datos.codigo, excluir_id=planta_id)
            if planta.municipio_id != datos.municipio_id:
                planta.nombre = f"Planta {sesion.get(Municipio, datos.municipio_id).nombre}"
            planta.codigo, planta.municipio_id = datos.codigo, datos.municipio_id
            vinculo.demanda_t_semana, vinculo.costo_operacion_cop_t = datos.demanda, datos.costo_operacion

    def eliminar_planta(self, planta_id: int) -> None:
        """Elimina la planta de todos los escenarios junto con sus rutas y resultados."""
        with self._bd.sesion() as sesion:
            planta = sesion.get(Planta, planta_id)
            if planta is None:
                raise ErrorNoEncontrado("La planta ya no existe.")
            sesion.execute(delete(EscenarioPlanta).where(EscenarioPlanta.planta_id == planta_id))
            sesion.execute(delete(AnalisisSensibilidad).where(AnalisisSensibilidad.planta_id == planta_id))
            sesion.delete(planta)

    @staticmethod
    def _limpiar_empresa(datos: DatosEmpresa) -> DatosEmpresa:
        codigo = datos.codigo.strip().upper()
        if not codigo:
            raise ErrorValidacion("El código de la empresa es obligatorio.")
        if datos.oferta < 0 or datos.precio < 0:
            raise ErrorValidacion("La oferta y el precio deben ser mayores o iguales a 0.")
        nombre = " ".join(datos.nombre.split())
        if not nombre:
            raise ErrorValidacion("El nombre de la empresa es obligatorio.")
        nit = (datos.nit or "").strip() or None
        return DatosEmpresa(codigo, nombre, nit, datos.municipio_id, datos.tipo_residuo_id,
                            datos.oferta, datos.precio)

    @staticmethod
    def _limpiar_planta(datos: DatosPlanta) -> DatosPlanta:
        codigo = datos.codigo.strip().upper()
        if not codigo:
            raise ErrorValidacion("El código de la planta es obligatorio.")
        if datos.municipio_id is None:
            raise ErrorValidacion("Selecciona el municipio de la planta.")
        if datos.demanda < 0 or datos.costo_operacion < 0:
            raise ErrorValidacion("La demanda y el costo de operación deben ser mayores o iguales a 0.")
        return DatosPlanta(codigo, datos.municipio_id, datos.demanda, datos.costo_operacion)

    @staticmethod
    def _validar_empresa_unica(sesion, datos: DatosEmpresa, excluir_id: int | None = None):
        consulta = select(Empresa).where(Empresa.id != (excluir_id or 0))
        if sesion.scalar(consulta.where(Empresa.codigo == datos.codigo)):
            raise ErrorValidacion(f"Ya existe una empresa con el código {datos.codigo}.")
        if datos.nit and sesion.scalar(consulta.where(Empresa.nit == datos.nit)):
            raise ErrorValidacion(f"Ya existe una empresa con el NIT {datos.nit}.")

    @staticmethod
    def _validar_planta_unica(sesion, codigo: str, excluir_id: int | None = None):
        if sesion.scalar(select(Planta).where(Planta.codigo == codigo,
                                              Planta.id != (excluir_id or 0))):
            raise ErrorValidacion(f"Ya existe una planta con el código {codigo}.")

    @staticmethod
    def _escenario(sesion, escenario_id: int) -> Escenario:
        escenario = sesion.get(Escenario, escenario_id)
        if escenario is None:
            raise ErrorNoEncontrado("El escenario seleccionado no existe.")
        return escenario
