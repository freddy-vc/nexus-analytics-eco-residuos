from dataclasses import dataclass
from enum import Enum

import numpy as np


class EstadoSolucion(str, Enum):
    OPTIMO = "optimo"
    INFACTIBLE = "infactible"
    NO_ACOTADO = "no_acotado"
    LIMITE_ITERACIONES = "limite_iteraciones"


@dataclass
class ResultadoSimplex:
    estado: EstadoSolucion
    x: np.ndarray | None
    objetivo: float | None
    iteraciones: int
    iteraciones_fase1: int
    base: np.ndarray | None


# Método Simplex de dos fases sobre tabla densa.
class Simplex:
    # Tolerancia numérica, límite de iteraciones y racha degenerada que activa la regla de Bland.
    def __init__(self, tolerancia: float = 1e-9, max_iteraciones: int = 100_000,
                 limite_degeneracion: int = 50):
        self.tolerancia = tolerancia
        self.max_iteraciones = max_iteraciones
        self.limite_degeneracion = limite_degeneracion

    # Resuelve min c·x sujeto a igualdades, desigualdades ≤ y x ≥ 0 con el método de dos fases.
    def resolver(self, c, A_igual=None, b_igual=None, A_menor=None, b_menor=None) -> ResultadoSimplex:
        c = np.asarray(c, dtype=float)
        n = c.size
        A_igual, b_igual = self._como_sistema(A_igual, b_igual, n)
        A_menor, b_menor = self._como_sistema(A_menor, b_menor, n)

        # Lados derechos no negativos: se invierten las filas con b < 0.
        signo = np.where(b_igual < 0, -1.0, 1.0)
        A_igual, b_igual = A_igual * signo[:, None], b_igual * signo
        invertidas = b_menor < 0
        A_menor[invertidas] *= -1
        b_menor[invertidas] *= -1

        m_igual, m_menor = len(b_igual), len(b_menor)
        m = m_igual + m_menor
        # Artificiales en las igualdades y en las desigualdades invertidas; las holguras completan la base.
        filas_artificiales = list(range(m_igual)) + [m_igual + k for k in np.flatnonzero(invertidas)]
        n_holgura, n_artificial = m_menor, len(filas_artificiales)
        n_total = n + n_holgura + n_artificial

        # Tabla: m filas de restricciones y una fila de costos reducidos; la última columna es b.
        tabla = np.zeros((m + 1, n_total + 1))
        tabla[:m_igual, :n], tabla[:m_igual, -1] = A_igual, b_igual
        tabla[m_igual:m, :n], tabla[m_igual:m, -1] = A_menor, b_menor
        base = np.empty(m, dtype=int)
        for k in range(m_menor):
            tabla[m_igual + k, n + k] = -1.0 if invertidas[k] else 1.0
            if not invertidas[k]:
                base[m_igual + k] = n + k
        for a, fila in enumerate(filas_artificiales):
            tabla[fila, n + n_holgura + a] = 1.0
            base[fila] = n + n_holgura + a

        iteraciones = 0
        # Fase 1: min Σ artificiales para encontrar una base factible.
        if n_artificial:
            costo_fase1 = np.zeros(n_total)
            costo_fase1[n + n_holgura:] = 1.0
            self._fijar_objetivo(tabla, base, costo_fase1)
            estado, iteraciones = self._iterar(tabla, base, iteraciones)
            if estado is not EstadoSolucion.OPTIMO:
                return ResultadoSimplex(estado, None, None, iteraciones, iteraciones, None)
            escala = max(1.0, float(np.abs(tabla[:m, -1]).max(initial=0.0)))
            # Si la suma de artificiales no llega a cero, el problema es infactible.
            if -tabla[-1, -1] > 1e-7 * escala:
                return ResultadoSimplex(EstadoSolucion.INFACTIBLE, None, None,
                                        iteraciones, iteraciones, None)
            tabla, base = self._retirar_artificiales(tabla, base, n + n_holgura)
        iteraciones_fase1 = iteraciones

        # Fase 2: optimiza c·x con costo cero en las holguras.
        costo_fase2 = np.concatenate([c, np.zeros(n_holgura)])
        self._fijar_objetivo(tabla, base, costo_fase2)
        estado, iteraciones = self._iterar(tabla, base, iteraciones)
        if estado is not EstadoSolucion.OPTIMO:
            return ResultadoSimplex(estado, None, None, iteraciones, iteraciones_fase1, None)

        x = np.zeros(n + n_holgura)
        x[base] = tabla[:-1, -1]
        x[np.abs(x) < self.tolerancia] = 0.0
        return ResultadoSimplex(EstadoSolucion.OPTIMO, x[:n], float(c @ x[:n]),
                                iteraciones, iteraciones_fase1, base.copy())

    # Normaliza una matriz de restricciones opcional a arreglos de NumPy.
    @staticmethod
    def _como_sistema(A, b, n):
        if A is None:
            return np.zeros((0, n)), np.zeros(0)
        return np.array(A, dtype=float, ndmin=2), np.array(b, dtype=float).ravel()

    # Carga la fila de costos reducidos de la función objetivo dada.
    @staticmethod
    def _fijar_objetivo(tabla, base, costo):
        tabla[-1, :-1] = costo
        tabla[-1, -1] = 0.0
        for fila, columna in enumerate(base):
            if costo[columna] != 0.0:
                # d = c − c_B·B⁻¹A: se anulan los costos reducidos de las variables básicas.
                tabla[-1] -= costo[columna] * tabla[fila]

    # Pivotea hasta el óptimo, un problema no acotado o el límite de iteraciones.
    def _iterar(self, tabla, base, iteraciones):
        racha_degenerada = 0
        while True:
            reducidos = tabla[-1, :-1]
            # Óptimo cuando ningún costo reducido es negativo.
            candidatas = np.flatnonzero(reducidos < -self.tolerancia)
            if candidatas.size == 0:
                return EstadoSolucion.OPTIMO, iteraciones
            if iteraciones >= self.max_iteraciones:
                return EstadoSolucion.LIMITE_ITERACIONES, iteraciones

            # Regla de Dantzig (d_j más negativo); tras una racha degenerada, Bland (menor índice).
            usar_bland = racha_degenerada >= self.limite_degeneracion
            entrante = candidatas[0] if usar_bland else candidatas[np.argmin(reducidos[candidatas])]

            columna = tabla[:-1, entrante]
            filas = np.flatnonzero(columna > self.tolerancia)
            if filas.size == 0:
                return EstadoSolucion.NO_ACOTADO, iteraciones
            # Prueba de la razón mínima: θ = min b_i / a_ij con a_ij > 0.
            razones = tabla[filas, -1] / columna[filas]
            minima = razones.min()
            empates = filas[razones <= minima + self.tolerancia]
            # Los empates se rompen por el menor índice básico.
            saliente = empates[np.argmin(base[empates])]

            racha_degenerada = racha_degenerada + 1 if minima <= self.tolerancia else 0
            self._pivotear(tabla, base, saliente, entrante)
            iteraciones += 1

    # Pivote de Gauss-Jordan sobre la tabla y actualización de la base.
    @staticmethod
    def _pivotear(tabla, base, fila, columna):
        tabla[fila] /= tabla[fila, columna]
        factores = tabla[:, columna].copy()
        factores[fila] = 0.0
        # Eliminación de Gauss-Jordan en todas las filas a la vez.
        tabla -= np.outer(factores, tabla[fila])
        tabla[np.abs(tabla) < 1e-12] = 0.0
        base[fila] = columna

    # Retira de la base las artificiales nulas de la fase 1 y elimina filas redundantes.
    def _retirar_artificiales(self, tabla, base, primera_artificial):
        redundantes = []
        for fila, columna in enumerate(base):
            if columna < primera_artificial:
                continue
            no_nulos = np.flatnonzero(np.abs(tabla[fila, :primera_artificial]) > self.tolerancia)
            if no_nulos.size:
                self._pivotear(tabla, base, fila, no_nulos[0])
            else:
                # Fila sin coeficientes reales: restricción linealmente dependiente.
                redundantes.append(fila)
        if redundantes:
            tabla = np.delete(tabla, redundantes, axis=0)
            base = np.delete(base, redundantes)
        tabla = np.delete(tabla, np.s_[primera_artificial:-1], axis=1)
        return tabla, base
