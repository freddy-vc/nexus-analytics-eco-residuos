from dataclasses import dataclass
from enum import Enum

import numpy as np


class TipoBalance(str, Enum):
    BALANCEADO = "balanceado"
    EXCESO_OFERTA = "exceso_oferta"
    EXCESO_DEMANDA = "exceso_demanda"


@dataclass(frozen=True)
class EstadoBalance:
    oferta_total: float
    demanda_total: float
    tipo: TipoBalance

    @property
    def diferencia(self) -> float:
        return self.oferta_total - self.demanda_total

    @property
    def esta_balanceado(self) -> bool:
        return self.tipo is TipoBalance.BALANCEADO


@dataclass(frozen=True)
class Verificacion:
    titulo: str
    detalle: str
    cumple: bool


@dataclass(frozen=True)
class ProblemaBalanceado:
    oferta: np.ndarray
    demanda: np.ndarray
    costos: np.ndarray
    habilitadas: np.ndarray
    origen_ficticio: bool
    destino_ficticio: bool


def verificar_balance(oferta: np.ndarray, demanda: np.ndarray, tolerancia: float = 1e-6) -> EstadoBalance:
    oferta_total, demanda_total = float(np.sum(oferta)), float(np.sum(demanda))
    diferencia = oferta_total - demanda_total
    if abs(diferencia) <= tolerancia:
        tipo = TipoBalance.BALANCEADO
    elif diferencia > 0:
        tipo = TipoBalance.EXCESO_OFERTA
    else:
        tipo = TipoBalance.EXCESO_DEMANDA
    return EstadoBalance(oferta_total, demanda_total, tipo)


def balancear_problema(oferta, demanda, costos, habilitadas, tolerancia: float = 1e-6) -> ProblemaBalanceado:
    """Agrega un nodo ficticio de costo cero cuando ΣOᵢ ≠ ΣDⱼ (RF08).

    Con oferta mayor se agrega una planta ficticia que recibe el excedente;
    con oferta menor, una empresa ficticia que representa la capacidad ociosa.
    """
    estado = verificar_balance(oferta, demanda, tolerancia)
    oferta, demanda = np.asarray(oferta, float), np.asarray(demanda, float)
    costos, habilitadas = np.asarray(costos, float), np.asarray(habilitadas, bool)

    if estado.tipo is TipoBalance.EXCESO_OFERTA:
        return ProblemaBalanceado(
            oferta, np.append(demanda, estado.diferencia),
            np.hstack([costos, np.zeros((len(oferta), 1))]),
            np.hstack([habilitadas, np.ones((len(oferta), 1), bool)]),
            origen_ficticio=False, destino_ficticio=True)

    if estado.tipo is TipoBalance.EXCESO_DEMANDA:
        return ProblemaBalanceado(
            np.append(oferta, -estado.diferencia), demanda,
            np.vstack([costos, np.zeros((1, len(demanda)))]),
            np.vstack([habilitadas, np.ones((1, len(demanda)), bool)]),
            origen_ficticio=True, destino_ficticio=False)

    return ProblemaBalanceado(oferta, demanda, costos, habilitadas, False, False)


def validar_datos(oferta, demanda, distancias, costos_operacion, alfa, precios_compra,
                  habilitadas) -> list[Verificacion]:
    oferta, demanda = np.asarray(oferta, float), np.asarray(demanda, float)
    distancias = np.asarray(distancias, float)
    m, n = distancias.shape

    no_negativos = (alfa > 0 and np.all(oferta >= 0) and np.all(demanda >= 0)
                    and np.all(np.nan_to_num(distancias, nan=0) >= 0)
                    and np.all(np.asarray(costos_operacion) >= 0)
                    and np.all(np.asarray(precios_compra) >= 0))
    con_distancia = int(np.sum(np.asarray(habilitadas) & (np.nan_to_num(distancias, nan=0) > 0)))
    completos = m > 0 and n > 0 and con_distancia == m * n
    estado = verificar_balance(oferta, demanda)

    if estado.esta_balanceado:
        detalle_balance = "No se requiere nodo ficticio."
    elif estado.tipo is TipoBalance.EXCESO_OFERTA:
        detalle_balance = f"La oferta es mayor: se agregará una planta ficticia P{n + 1}."
    else:
        detalle_balance = f"La oferta es menor: se agregará una empresa ficticia E{m + 1}."

    return [
        Verificacion("Valores no negativos",
                     "Oferta, demanda, distancias y costos mayores o iguales a 0; "
                     "costo de transporte mayor que 0.", bool(no_negativos)),
        Verificacion("Datos completos",
                     f"{m} empresas, {n} plantas y {con_distancia}/{m * n} rutas con distancia.",
                     bool(completos)),
        Verificacion("Oferta y demanda balanceadas", detalle_balance, estado.esta_balanceado),
    ]
