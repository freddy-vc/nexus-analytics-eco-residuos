from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ReporteFactibilidad:
    oferta_cumplida: int
    oferta_total: int
    demanda_cumplida: int
    demanda_total: int
    no_negatividad_cumplida: int
    no_negatividad_total: int
    violacion_maxima: float

    @property
    def violaciones(self) -> int:
        return ((self.oferta_total - self.oferta_cumplida)
                + (self.demanda_total - self.demanda_cumplida)
                + (self.no_negatividad_total - self.no_negatividad_cumplida))

    @property
    def es_factible(self) -> bool:
        return self.violaciones == 0


def validar_solucion(flujos: np.ndarray, oferta: np.ndarray, demanda: np.ndarray,
                     habilitadas: np.ndarray, tolerancia: float = 1e-6,
                     permitir_sin_enviar: bool = False) -> ReporteFactibilidad:
    """Verifica oferta, demanda y no negatividad (RF10, RNF06).

    Con oferta mayor que la demanda la oferta no puede salir completa, así que
    la restricción se evalúa como Σⱼ xᵢⱼ ≤ Oᵢ.
    """
    flujos = np.asarray(flujos, float)
    habilitadas = np.asarray(habilitadas, bool)
    enviado = flujos.sum(axis=1)
    recibido = flujos.sum(axis=0)

    brecha_oferta = enviado - oferta if permitir_sin_enviar else np.abs(enviado - oferta)
    brecha_oferta = np.maximum(brecha_oferta, 0.0)
    brecha_demanda = np.maximum(recibido - demanda, 0.0)
    flujos_arcos = flujos[habilitadas]
    brecha_negativa = np.maximum(-flujos_arcos, 0.0)
    flujo_deshabilitado = np.abs(flujos[~habilitadas])

    violacion_maxima = float(max(brecha_oferta.max(initial=0), brecha_demanda.max(initial=0),
                                 brecha_negativa.max(initial=0), flujo_deshabilitado.max(initial=0)))
    return ReporteFactibilidad(
        oferta_cumplida=int(np.sum(brecha_oferta <= tolerancia)), oferta_total=len(oferta),
        demanda_cumplida=int(np.sum(brecha_demanda <= tolerancia)), demanda_total=len(demanda),
        no_negatividad_cumplida=int(np.sum(brecha_negativa <= tolerancia)),
        no_negatividad_total=flujos_arcos.size, violacion_maxima=violacion_maxima)
