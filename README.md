<div align="center">

<img src="assets/logo/logo-hoja.svg" alt="Nexus Analytics · EcoResiduos" width="90"/>

# Nexus Analytics · EcoResiduos

**Sistema web de optimización de la red logística de recepción y procesamiento de residuos agropecuarios**

Modelos de redes · Problema de transporte · Simplex propio · Algoritmos genéticos · Análisis de sensibilidad

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-web%20app-FF4B4B?logo=streamlit&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14%2B-4169E1?logo=postgresql&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-cálculo-013243?logo=numpy&logoColor=white)
![Licencia](https://img.shields.io/badge/licencia-MIT-green)
![Estado](https://img.shields.io/badge/estado-en%20desarrollo-orange)

*Universidad de los Llanos · Facultad de Ciencias Básicas e Ingeniería · Ingeniería de Sistemas*
*Asignatura: Optimización · Periodo académico 2026-II*

</div>

---

## Tabla de contenido

1. [Descripción](#1-descripción)
2. [Contexto del problema](#2-contexto-del-problema)
3. [Objetivos](#3-objetivos)
4. [Funcionalidades](#4-funcionalidades)
5. [Arquitectura](#5-arquitectura)
6. [Stack tecnológico](#6-stack-tecnológico)
7. [Estructura del proyecto](#7-estructura-del-proyecto)
8. [Descripción de los módulos](#8-descripción-de-los-módulos)
9. [Modelo matemático](#9-modelo-matemático)
10. [Base de datos](#10-base-de-datos)
11. [Instalación y configuración](#11-instalación-y-configuración)
12. [Ejecución](#12-ejecución)
13. [Requerimientos no funcionales clave](#13-requerimientos-no-funcionales-clave)
14. [Hoja de ruta](#14-hoja-de-ruta)
15. [Equipo y roles](#15-equipo-y-roles)
16. [Flujo de trabajo con Git](#16-flujo-de-trabajo-con-git)
17. [Documentación](#17-documentación)
18. [Licencia](#18-licencia)

---

## 1. Descripción

**Nexus Analytics · EcoResiduos** es una aplicación web que permite a **EcoResiduos del Llano S.A.S.** minimizar el costo logístico de recolectar los residuos orgánicos generados por sus empresas agropecuarias aliadas y llevarlos a sus plantas de transformación en el departamento del Meta.

El sistema modela la red como un grafo dirigido, resuelve el **problema de transporte** con un **método exacto (Simplex implementado desde cero)** y con un **Algoritmo Genético**, realiza el **análisis de sensibilidad** (precios sombra y rangos de variación) y genera un **reporte comparativo** entre ambos enfoques. Toda la lógica de optimización se construye **sin librerías de optimización**, usando únicamente **NumPy** para el cálculo matricial.

## 2. Contexto del problema

EcoResiduos del Llano S.A.S. valoriza residuos agropecuarios (biomasa, subproductos de palma, arroz, ganadería y plantaciones forestales) y los transforma en abonos orgánicos, biocombustibles y suplementos para nutrición animal.

| Elemento | Caso base |
|---|---|
| Empresas agropecuarias aliadas (orígenes) | 10 (E1 … E10) |
| Plantas de recepción y transformación (destinos) | 4: Villavicencio, Restrepo, Granada y Puerto Gaitán |
| Oferta total semanal | 1.250 t |
| Demanda total semanal | 1.250 t (problema balanceado) |
| Costo de transporte | α = 750 COP por tonelada-kilómetro |
| Arcos de la red | 40 rutas empresa → planta |

La asignación empírica de rutas genera sobrecostos operativos. El sistema determina la distribución óptima de los flujos de residuos y permite **ampliar empresas y sedes**, **modificar los coeficientes del negocio** y **simular escenarios** de variación en oferta, demanda y costos.

## 3. Objetivos

**General.** Diseñar y desarrollar una solución computacional basada en modelos de optimización de redes, métodos de transporte y algoritmos genéticos para minimizar el costo logístico de la red de recepción de residuos agropecuarios.

**Específicos.**

- Estructurar y parametrizar el problema de transporte y flujo en redes con las ofertas de las 10 empresas y las demandas de las 4 plantas.
- Implementar el modelo matemático exacto para hallar la solución óptima global.
- Diseñar e implementar un Algoritmo Genético para encontrar soluciones cuasi-óptimas.
- Realizar el análisis de sensibilidad ante variaciones de costos unitarios, ofertas y demandas.
- Comparar el método exacto y el Algoritmo Genético en calidad de la función objetivo, tiempo de cómputo, escalabilidad y respuesta ante escenarios.

## 4. Funcionalidades

| Módulo | Funcionalidad | Requerimientos |
|---|---|---|
| Autenticación | Inicio de sesión con usuario y contraseña (rol **analista**) | — |
| Datos de la red | Gestión de empresas, plantas, rutas, distancias, ofertas y demandas | RF01 – RF04 |
| Parámetros | Coeficientes del negocio: α, precio de la tonelada (β), costo de operación (p<sub>j</sub>) | RF05 |
| Importar / exportar | Carga y descarga de datos en CSV, XLSX y JSON | RF06 |
| Red logística | Construcción y visualización del grafo G = (V, A) | RF07 |
| Validación | Consistencia de datos y balance oferta–demanda con nodo ficticio | RF08 |
| Método exacto | Resolución con Simplex propio, verificación de factibilidad | RF09, RF10 |
| Algoritmo Genético | Parámetros configurables, ejecución, múltiples corridas y estadísticas | RF11 – RF13 |
| Resultados | Flujos por arco, costo total y utilización de las plantas | RF14 |
| Sensibilidad | Precios sombra, costos reducidos y rangos de variación | RF15 |
| Escenarios | Simulación de variaciones, guardado y recuperación de escenarios | RF16, RF17 |
| Comparación | Reporte exacto vs. AG: costo, tiempo y gap % | RF18 |
| Reportes | Exportación a PDF, CSV y XLSX | RF19 |

## 5. Arquitectura

La aplicación sigue una arquitectura en capas con separación estricta entre **frontend** (presentación) y **backend** (lógica de negocio, optimización y persistencia).

```mermaid
flowchart LR
    U([Analista]) --> FE

    subgraph FE[frontend · Streamlit]
        APP[app.py<br/>login y navegación] --> PAGES[pages/]
        PAGES --> COMP[components/]
    end

    FE --> SRV

    subgraph BE[backend]
        SRV[services/<br/>orquestación] --> NET[network/]
        SRV --> EXA[exact/]
        SRV --> GEN[genetic/]
        SRV --> SEN[sensitivity/]
        SRV --> CMP[comparison/]
        SRV --> DIO[data_io/]
        SRV --> AUTH[auth.py]
        SRV --> DB[database.py<br/>conexión + ORM]
    end

    DB --> PG[(PostgreSQL)]
```

**Principios de diseño**

- **Bajo acoplamiento:** los módulos de optimización (`network`, `exact`, `genetic`, `sensitivity`, `comparison`) no conocen la base de datos ni la interfaz; reciben y devuelven estructuras NumPy. Así cada integrante trabaja su módulo sin afectar los demás (RNF04).
- **Capa de servicios:** `services/` conecta la interfaz con los algoritmos y con la persistencia.
- **Persistencia con ORM:** `database.py` centraliza la conexión y los modelos ORM; ningún módulo escribe SQL directamente.
- **Escenarios inmutables:** las simulaciones crean escenarios nuevos y nunca alteran los datos originales (RNF10).

## 6. Stack tecnológico

| Capa | Tecnología | Uso |
|---|---|---|
| Lenguaje | Python 3.11+ | Todo el sistema |
| Interfaz web | Streamlit | Páginas, formularios, tablas y gráficas |
| Cálculo | NumPy | Matrices, vectores y operaciones del Simplex, el AG y la sensibilidad |
| Grafos | NetworkX | Construcción y visualización de la red G = (V, A) |
| Visualización | Matplotlib · Plotly | Grafo, convergencia del AG, sensibilidad y comparación |
| Base de datos | PostgreSQL | Persistencia de datos, escenarios y resultados |
| ORM | SQLAlchemy 2 | Mapeo objeto-relacional en `database.py` |
| Seguridad | bcrypt | Hash de contraseñas |
| Archivos | pandas · openpyxl · fpdf2 | Lectura/escritura CSV y XLSX, reportes PDF |

> **Restricción de diseño:** el método Simplex, el método de transporte, el Algoritmo Genético y el análisis de sensibilidad se implementan **desde cero**. No se utilizan librerías de optimización (SciPy, PuLP, HiGHS, OR-Tools, DEAP, etc.); NumPy se usa solo como soporte de cálculo matricial. pandas se limita a la lectura y escritura de archivos.

## 7. Estructura del proyecto

```text
nexus-analytics-eco-residuos/
├── .streamlit/
│   └── config.toml                  # Tema y configuración de Streamlit
├── assets/
│   ├── icons/                       # Iconos SVG de navegación, KPIs, acciones y tema
│   ├── images/                      # Imágenes de la aplicación
│   └── logo/                        # Logotipo
├── backend/
│   ├── __init__.py
│   ├── config.py                    # Carga de variables de entorno y constantes globales
│   ├── database.py                  # Conexión a PostgreSQL y modelos ORM (SQLAlchemy)
│   ├── auth.py                      # Login: verificación de credenciales con bcrypt
│   ├── network/                     # Fase 1 · Modelado de la red
│   │   ├── __init__.py
│   │   ├── graph_builder.py         # Grafo dirigido G = (V, A) con NetworkX
│   │   ├── cost_matrix.py           # Matriz de costos c_ij = α·d_ij + p_j
│   │   └── balance.py               # Validación de datos, balance y nodos ficticios
│   ├── exact/                       # Fase 2 · Solución exacta
│   │   ├── __init__.py
│   │   ├── transport_model.py       # Formulación del PL: vector c, matriz A, vector b
│   │   ├── simplex.py               # Algoritmo Simplex propio (NumPy)
│   │   └── solution_validator.py    # Verificación de factibilidad (tolerancia 1e-6)
│   ├── genetic/                     # Fase 3 · Algoritmo Genético
│   │   ├── __init__.py
│   │   ├── chromosome.py            # Codificación cromosómica de la asignación de flujos
│   │   ├── fitness.py               # Aptitud: inversa del costo penalizado
│   │   ├── selection.py             # Selección por ruleta y por torneo
│   │   ├── crossover.py             # Cruce de uno y de dos puntos
│   │   ├── mutation.py              # Operador de mutación
│   │   ├── genetic_algorithm.py     # Motor evolutivo y curva de convergencia
│   │   └── multi_run.py             # N corridas independientes y estadísticas
│   ├── sensitivity/                 # Fase 4 · Análisis de sensibilidad
│   │   ├── __init__.py
│   │   ├── duals.py                 # Precios sombra y costos reducidos
│   │   ├── ranging.py               # Rangos de optimalidad y de factibilidad
│   │   └── scenario_simulator.py    # Simulación de variaciones porcentuales
│   ├── comparison/                  # Fase 4 · Comparación exacto vs. AG
│   │   ├── __init__.py
│   │   ├── metrics.py               # Gap %, tiempos y estadísticas
│   │   └── comparative_report.py    # Construcción del reporte comparativo
│   ├── data_io/                     # Importación y exportación
│   │   ├── __init__.py
│   │   ├── importer.py              # Carga desde CSV, XLSX y JSON
│   │   ├── exporter.py              # Descarga de datos en CSV, XLSX y JSON
│   │   └── report_exporter.py       # Reportes en PDF, CSV y XLSX
│   ├── services/                    # Orquestación entre interfaz, algoritmos y BD
│   │   ├── __init__.py
│   │   ├── network_service.py       # Empresas, plantas, rutas y catálogos
│   │   ├── scenario_service.py      # Crear, copiar, guardar y recuperar escenarios
│   │   ├── optimization_service.py  # Ejecución del método exacto y del AG
│   │   ├── sensitivity_service.py   # Análisis de sensibilidad y simulaciones
│   │   └── comparison_service.py    # Comparaciones y reportes
│   └── utils/
│       ├── __init__.py
│       ├── exceptions.py            # Excepciones del dominio (infactible, no acotado…)
│       ├── timer.py                 # Medición de tiempos de ejecución
│       └── logger.py                # Registro de eventos
├── frontend/
│   ├── __init__.py
│   ├── app.py                       # Punto de entrada: login y navegación
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── inicio.py                # Panel con KPIs del escenario activo
│   │   ├── empresas.py              # Gestión de empresas (orígenes)
│   │   ├── plantas.py               # Gestión de plantas (destinos)
│   │   ├── rutas_costos.py          # Distancias y matriz de costos
│   │   ├── parametros.py            # α, β, p_j, ofertas y demandas
│   │   ├── red_logistica.py         # Visualización del grafo
│   │   ├── escenarios.py            # Escenarios guardados e importación/exportación
│   │   ├── metodo_exacto.py         # Ejecución y resultados del Simplex
│   │   ├── algoritmo_genetico.py    # Parámetros, ejecución y convergencia del AG
│   │   ├── sensibilidad.py          # Precios sombra, rangos y simulaciones
│   │   └── comparacion.py           # Reporte comparativo exacto vs. AG
│   ├── components/
│   │   ├── __init__.py
│   │   ├── login_form.py            # Formulario de inicio de sesión
│   │   ├── auth_guard.py            # Protección de páginas sin sesión
│   │   ├── sidebar.py               # Menú lateral con iconos
│   │   ├── theme_toggle.py          # Cambio de tema claro / oscuro
│   │   ├── kpi_cards.py             # Tarjetas de indicadores
│   │   ├── network_graph.py         # Render del grafo y de los flujos
│   │   ├── charts.py                # Gráficas de convergencia, sensibilidad y comparación
│   │   └── data_tables.py           # Tablas editables y de resultados
│   └── styles/
│       └── main.css                 # Estilos personalizados
├── database/
│   └── ecoresiduos_db.sql           # Script DDL + datos del caso base
├── data/
│   └── samples/                     # Datos de prueba regionales (CSV, XLSX, JSON)
├── docs/                            # Enunciado, requerimientos, Fase 1 y MER
├── .env.example                     # Plantilla de variables de entorno
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

## 8. Descripción de los módulos

### 8.1 Backend

| Paquete / archivo | Responsabilidad | Fase |
|---|---|---|
| `config.py` | Lee `.env` (conexión a la BD, entorno) y define constantes como la tolerancia numérica (1e-6). | — |
| `database.py` | Crea el *engine* y la sesión de SQLAlchemy y declara los modelos ORM que mapean las 25 tablas del MER. El resto del sistema manipula la BD a través de estos objetos, sin escribir consultas SQL. | — |
| `auth.py` | Valida usuario y contraseña contra `usuario.password_hash` (bcrypt). Solo login básico: sin registro ni recuperación de contraseña. | — |
| `network/` | Construye el grafo bipartito dirigido con NetworkX, calcula la matriz c<sub>ij</sub> y valida el balance; si ΣO<sub>i</sub> ≠ ΣD<sub>j</sub> agrega la empresa o planta ficticia. | 1 |
| `exact/` | Traduce la red a un modelo de PL en forma matricial y lo resuelve con un **Simplex propio** sobre NumPy; entrega el estado (óptimo, infactible, no acotado), x<sub>ij</sub>, Z, el tiempo y la base óptima. `solution_validator.py` comprueba oferta, demanda y no negatividad. | 2 |
| `genetic/` | AG con cromosoma de asignación de flujos, aptitud = 1 / (costo + penalización por violación de capacidad), selección por ruleta o torneo, cruce de uno o dos puntos, mutación, semilla reproducible y múltiples corridas. | 3 |
| `sensitivity/` | A partir de la tabla final del Simplex calcula precios sombra, costos reducidos y rangos de variación de c<sub>ij</sub>, O<sub>i</sub> y D<sub>j</sub> que no alteran la base óptima; simula escenarios porcentuales. | 4 |
| `comparison/` | Calcula costo, tiempo y gap % = (Z<sub>AG</sub> − Z<sub>exacto</sub>) / Z<sub>exacto</sub> × 100 y arma el reporte comparativo. | 4 |
| `data_io/` | Importa y exporta los datos de entrada (CSV, XLSX, JSON) y los reportes (PDF, CSV, XLSX) en UTF-8. | 4 |
| `services/` | Casos de uso que combinan algoritmos y persistencia: crear escenarios, ejecutar métodos, guardar resultados y comparar. | — |
| `utils/` | Excepciones del dominio, cronómetro y registro de eventos. | — |

### 8.2 Frontend

| Página | Contenido | HU |
|---|---|---|
| Inicio | KPIs del escenario activo: costo total, toneladas, gap | — |
| Empresas / Plantas | CRUD de orígenes y destinos | HU-01 |
| Rutas y costos | Matriz de distancias y de costos unitarios | HU-02 |
| Parámetros | α, β, p<sub>j</sub>, ofertas, demandas y balance | HU-02, HU-03 |
| Red logística | Grafo interactivo de la red | HU-05 |
| Escenarios | Guardar, recuperar, importar y exportar | HU-04, HU-10 |
| Método exacto | Ejecución del Simplex y resultados | HU-06, HU-08 |
| Algoritmo genético | Parámetros, ejecución, convergencia y estadísticas | HU-07, HU-08 |
| Sensibilidad | Precios sombra, rangos y simulación de escenarios | HU-09, HU-10 |
| Comparación | Reporte exacto vs. AG exportable | HU-11 |

## 9. Modelo matemático

Grafo bipartito dirigido $G = (V, A)$ con $V = V_O \cup V_D$ (empresas y plantas) y $A = V_O \times V_D$.

**Parámetros:** oferta $O_i$, demanda $D_j$, distancia $d_{ij}$, costo de transporte $\alpha$, costo de operación $p_j$ y costo unitario $c_{ij} = \alpha\, d_{ij} + p_j$.

**Variables:** $x_{ij} \ge 0$, toneladas semanales enviadas de la empresa $i$ a la planta $j$.

$$
\begin{aligned}
\min \quad & Z = \sum_{i \in V_O} \sum_{j \in V_D} c_{ij}\, x_{ij} \\
\text{s.a.} \quad & \sum_{j \in V_D} x_{ij} = O_i, && \forall\, i \in V_O \\
& \sum_{i \in V_O} x_{ij} \le D_j, && \forall\, j \in V_D \\
& x_{ij} \ge 0, && \forall\, i, j
\end{aligned}
$$

Si el problema no está balanceado se agrega una empresa ficticia $E_{m+1}$ o una planta ficticia $P_{n+1}$ con costo cero. El desarrollo completo está en `docs/Fase1_Modelado_Red_Logistica.docx`.

## 10. Base de datos

Modelo entidad-relación normalizado hasta **tercera forma normal** (`docs/MER_EcoResiduos.drawio`), con 25 tablas agrupadas en módulos:

| Módulo | Tablas |
|---|---|
| Seguridad | `rol`, `usuario` |
| Datos maestros | `departamento`, `municipio`, `tipo_residuo`, `empresa`, `planta` |
| Escenarios | `escenario`, `escenario_empresa`, `escenario_planta`, `ruta` |
| Ejecuciones | `ejecucion`, `resultado_ruta` |
| Algoritmo Genético | `parametros_ag`, `historial_generacion` |
| Sensibilidad | `sensibilidad_oferta`, `sensibilidad_demanda`, `analisis_sensibilidad`, `punto_sensibilidad` |
| Comparación | `comparacion` |
| Catálogos | `metodo_solucion`, `estado_ejecucion`, `metodo_seleccion`, `tipo_cruce`, `tipo_parametro` |

**Vistas:** `v_costo_unitario` (c<sub>ij</sub> por escenario) y `v_comparacion` (Z exacto, Z AG, gap % y tiempos). Los valores derivados no se almacenan.

**Datos iniciales:** el script `database/ecoresiduos_db.sql` carga los catálogos, el escenario **Caso base** de la Fase 1 (10 empresas, 4 plantas y 40 rutas) y un usuario analista por defecto.

## 11. Instalación y configuración

### 11.1 Requisitos previos

- Python 3.11 o superior
- PostgreSQL 14 o superior
- Git

### 11.2 Clonar el repositorio y crear el entorno virtual

```bash
git clone https://github.com/freddy-vc/nexus-analytics-eco-residuos.git
cd nexus-analytics-eco-residuos

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 11.3 Crear la base de datos

```bash
psql -U postgres -c "CREATE DATABASE ecoresiduos ENCODING 'UTF8';"
psql -U postgres -d ecoresiduos -f database/ecoresiduos_db.sql
```

El script es reejecutable: elimina y vuelve a crear todos los objetos.

### 11.4 Variables de entorno

Copiar la plantilla y completar los datos de conexión:

```bash
cp .env.example .env
```

| Variable | Descripción | Ejemplo |
|---|---|---|
| `DB_HOST` | Servidor de PostgreSQL | `localhost` |
| `DB_PORT` | Puerto | `5432` |
| `DB_NAME` | Nombre de la base de datos | `ecoresiduos` |
| `DB_USER` | Usuario de la base de datos | `postgres` |
| `DB_PASSWORD` | Contraseña de la base de datos | — |
| `APP_ENV` | Entorno de ejecución | `development` |

## 12. Ejecución

Desde la raíz del proyecto:

```bash
streamlit run frontend/app.py
```

La aplicación se abre en `http://localhost:8501`.

| Usuario | Contraseña | Rol |
|---|---|---|
| `analista` | `Analista2026*` | Analista |

> Cambiar la contraseña por defecto antes de cualquier despliegue.

**Flujo de uso sugerido**

1. Iniciar sesión como analista.
2. Revisar o ajustar empresas, plantas, rutas y parámetros del **Caso base**.
3. Visualizar la red logística y validar el balance.
4. Resolver con el **método exacto**.
5. Configurar y ejecutar el **Algoritmo Genético** (una o varias corridas).
6. Realizar el **análisis de sensibilidad** y simular escenarios.
7. Generar y exportar el **reporte comparativo**.

## 13. Requerimientos no funcionales clave

| Id | Requerimiento | Criterio |
|---|---|---|
| RNF01 | Rendimiento | Método exacto < 5 s en la instancia base; AG < 60 s con parámetros por defecto; interfaz < 2 s |
| RNF02 | Escalabilidad | Al menos 100 empresas y 20 plantas sin modificar el código |
| RNF04 | Modularidad | Módulos independientes: exacto, genético, interfaz y sensibilidad |
| RNF05 | Tecnología | Simplex de construcción propia, entorno web, PostgreSQL y `requirements.txt` |
| RNF06 | Exactitud | Restricciones satisfechas con tolerancia ≤ 1e-6 |
| RNF07 | Reproducibilidad | Semilla configurable y parámetros del AG registrados |
| RNF10 | Integridad | Las simulaciones no alteran los datos originales |
| RNF12 | Demostración | Ejecución local sin internet con casos precargados |
| RNF13 | Interoperabilidad | CSV, XLSX, JSON y PDF en UTF-8 |

## 14. Hoja de ruta

- [x] **Fase 1 · Modelado de la red:** grafo G = (V, A), parámetros y modelo de programación lineal.
- [x] Modelo entidad-relación (3FN) y script de base de datos.
- [x] Estructura del proyecto.
- [ ] **Fase 2 · Solución exacta:** Simplex propio y validación de factibilidad.
- [ ] **Fase 3 · Metaheurística:** Algoritmo Genético y múltiples corridas.
- [ ] **Fase 4 · Interfaz, sensibilidad y comparación:** páginas de Streamlit, precios sombra, rangos, escenarios y reporte comparativo.
- [ ] Informe técnico en formato IEEE y sustentación.

## 15. Equipo y roles

| Rol | Responsabilidades | Integrante |
|---|---|---|
| Líder de proyecto / Analista de negocio | Coordinación, cronograma, informe IEEE y validación de restricciones del negocio | *Por definir* |
| Ingeniero de modelado y optimización | Formulación matemática y módulo exacto (`network/`, `exact/`) | *Por definir* |
| Desarrollador de metaheurísticas | Diseño y ajuste del Algoritmo Genético (`genetic/`) | *Por definir* |
| Desarrollador de software e interfaz | Arquitectura, interfaz y módulos de sensibilidad y reportes (`frontend/`, `sensitivity/`, `comparison/`) | *Por definir* |

## 16. Flujo de trabajo con Git

Se trabaja con ramas por módulo, como exige el proyecto:

| Rama | Propósito |
|---|---|
| `main` | Versión estable y entregable |
| `develop` | Integración de los módulos |
| `feature/network` | Modelado de la red |
| `feature/exact` | Simplex y método exacto |
| `feature/genetic` | Algoritmo Genético |
| `feature/sensitivity` | Análisis de sensibilidad |
| `feature/frontend` | Interfaz en Streamlit |
| `feature/database` | ORM y persistencia |

**Convención de commits:** `feat:`, `fix:`, `docs:`, `refactor:`, `chore:` seguidos de una descripción breve en español. Ejemplo: `feat(exact): implementa la fase 1 del Simplex`.

## 17. Documentación

| Archivo | Contenido |
|---|---|
| `docs/ProyectoFinal_Optimizacion_2026-2.pdf` | Enunciado del proyecto |
| `docs/Requerimientos.docx` | Requerimientos funcionales, no funcionales e historias de usuario |
| `docs/Fase1_Modelado_Red_Logistica.docx` | Modelado de la red y modelo de programación lineal |
| `docs/MER_EcoResiduos.drawio` | Modelo entidad-relación (abrir con [draw.io](https://app.diagrams.net)) |
| `database/ecoresiduos_db.sql` | Script DDL y datos del caso base |

## 18. Licencia

Distribuido bajo la licencia **MIT**. Ver [`LICENSE`](LICENSE).

---

<div align="center">

Proyecto académico · Optimización 2026-II · Universidad de los Llanos

</div>
