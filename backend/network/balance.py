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

    # Oferta total menos demanda total.
    @property
    def diferencia(self) -> float:
        return self.oferta_total - self.demanda_total

    # Indica si la oferta y la demanda totales coinciden.
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


# Clasifica el problema como balanceado, con exceso de oferta o con exceso de demanda.
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


# Agrega una planta o empresa ficticia de costo cero cuando el problema no está balanceado.
def balancear_problema(oferta, demanda, costos, habilitadas, tolerancia: float = 1e-6) -> ProblemaBalanceado:
    estado = verificar_balance(oferta, demanda, tolerancia)
    oferta, demanda = np.asarray(oferta, float), np.asarray(demanda, float)
    costos, habilitadas = np.asarray(costos, float), np.asarray(habilitadas, bool)

    # Oferta mayor: planta ficticia con D = Σ O_i − Σ D_j y costo cero.
    if estado.tipo is TipoBalance.EXCESO_OFERTA:
        return ProblemaBalanceado(
            oferta, np.append(demanda, estado.diferencia),
            np.hstack([costos, np.zeros((len(oferta), 1))]),
            np.hstack([habilitadas, np.ones((len(oferta), 1), bool)]),
            origen_ficticio=False, destino_ficticio=True)

    # Oferta menor: empresa ficticia con O = Σ D_j − Σ O_i y costo cero.
    if estado.tipo is TipoBalance.EXCESO_DEMANDA:
        return ProblemaBalanceado(
            np.append(oferta, -estado.diferencia), demanda,
            np.vstack([costos, np.zeros((1, len(demanda)))]),
            np.vstack([habilitadas, np.ones((1, len(demanda)), bool)]),
            origen_ficticio=True, destino_ficticio=False)

    return ProblemaBalanceado(oferta, demanda, costos, habilitadas, False, False)


# Verificaciones previas a resolver: valores no negativos, datos completos y balance.
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
