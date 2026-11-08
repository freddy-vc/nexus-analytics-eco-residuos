-- =====================================================================
--  EcoResiduos del Llano S.A.S.
--  Optimización de la red logística de residuos agropecuarios
--  Script DDL + datos del caso base (Fase 1) · PostgreSQL 14+
--  Modelo normalizado hasta 3FN (ver MER_EcoResiduos.drawio)
-- =====================================================================
--  Uso:
--    1) Crear la base de datos (una sola vez, como superusuario):
--         CREATE DATABASE ecoresiduos ENCODING 'UTF8';
--    2) Conectarse a ella y ejecutar este script:
--         psql -U postgres -d ecoresiduos -f ecoresiduos_db.sql
-- =====================================================================

BEGIN;

-- Extensión para generar el hash bcrypt de la contraseña del usuario por defecto
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------
--  Limpieza (permite volver a ejecutar el script desde cero)
-- ---------------------------------------------------------------------
DROP VIEW  IF EXISTS v_comparacion, v_costo_unitario CASCADE;
DROP TABLE IF EXISTS comparacion, punto_sensibilidad, analisis_sensibilidad,
                     historial_generacion, parametros_ag, sensibilidad_demanda,
                     sensibilidad_oferta, resultado_ruta, ejecucion, ruta,
                     escenario_planta, escenario_empresa, escenario, planta,
                     empresa, tipo_residuo, municipio, departamento, usuario, rol,
                     tipo_parametro, tipo_cruce, metodo_seleccion,
                     estado_ejecucion, metodo_solucion CASCADE;
DROP FUNCTION IF EXISTS fn_ruta_mismo_escenario() CASCADE;
DROP FUNCTION IF EXISTS fn_actualizado_en() CASCADE;

-- =====================================================================
--  1. SEGURIDAD (login básico)
-- =====================================================================
CREATE TABLE rol (
    id           SMALLSERIAL  PRIMARY KEY,
    nombre       VARCHAR(30)  NOT NULL UNIQUE,
    descripcion  VARCHAR(150)
);

CREATE TABLE usuario (
    id                 BIGSERIAL    PRIMARY KEY,
    rol_id             SMALLINT     NOT NULL REFERENCES rol(id),
    username           VARCHAR(50)  NOT NULL UNIQUE,
    email              VARCHAR(120) NOT NULL UNIQUE,
    password_hash      VARCHAR(255) NOT NULL,          -- bcrypt, nunca texto plano
    nombres            VARCHAR(80)  NOT NULL,
    apellidos          VARCHAR(80)  NOT NULL,
    activo             BOOLEAN      NOT NULL DEFAULT TRUE,
    intentos_fallidos  SMALLINT     NOT NULL DEFAULT 0,
    bloqueado_hasta    TIMESTAMPTZ,
    ultimo_acceso      TIMESTAMPTZ,
    creado_en          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT ck_usuario_intentos CHECK (intentos_fallidos >= 0)
);

-- =====================================================================
--  2. DATOS MAESTROS DE LA RED
-- =====================================================================
CREATE TABLE departamento (
    id           SMALLSERIAL PRIMARY KEY,
    codigo_dane  CHAR(2)     NOT NULL UNIQUE,
    nombre       VARCHAR(60) NOT NULL UNIQUE
);

CREATE TABLE municipio (
    id               SERIAL       PRIMARY KEY,
    departamento_id  SMALLINT     NOT NULL REFERENCES departamento(id),
    codigo_dane      CHAR(5)      NOT NULL UNIQUE,
    nombre           VARCHAR(80)  NOT NULL,
    latitud          NUMERIC(9,6) NOT NULL,
    longitud         NUMERIC(9,6) NOT NULL,
    CONSTRAINT uq_municipio_depto_nombre UNIQUE (departamento_id, nombre)
);

CREATE TABLE tipo_residuo (
    id           SMALLSERIAL  PRIMARY KEY,
    nombre       VARCHAR(80)  NOT NULL UNIQUE,
    descripcion  VARCHAR(200)
);

CREATE TABLE empresa (
    id               SERIAL      PRIMARY KEY,
    codigo           VARCHAR(10) NOT NULL UNIQUE,      -- E1, E2, ...
    nombre           VARCHAR(100) NOT NULL,
    nit              VARCHAR(15) UNIQUE,               -- opcional
    municipio_id     INTEGER     NOT NULL REFERENCES municipio(id),
    tipo_residuo_id  SMALLINT    NOT NULL REFERENCES tipo_residuo(id),
    activa           BOOLEAN     NOT NULL DEFAULT TRUE,
    creado_en        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE planta (
    id            SERIAL       PRIMARY KEY,
    codigo        VARCHAR(10)  NOT NULL UNIQUE,        -- P1, P2, ...
    nombre        VARCHAR(100) NOT NULL,
    municipio_id  INTEGER      NOT NULL REFERENCES municipio(id),
    activa        BOOLEAN      NOT NULL DEFAULT TRUE,
    creado_en     TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- =====================================================================
--  3. ESCENARIOS Y PARÁMETROS DEL MODELO (O_i, D_j, d_ij, α, β_i, p_j)
-- =====================================================================
CREATE TABLE escenario (
    id                   BIGSERIAL     PRIMARY KEY,
    usuario_id           BIGINT        NOT NULL REFERENCES usuario(id),
    escenario_origen_id  BIGINT        REFERENCES escenario(id) ON DELETE SET NULL,
    nombre               VARCHAR(100)  NOT NULL,
    descripcion          TEXT,
    alfa_cop_t_km        NUMERIC(12,2) NOT NULL,                    -- α
    factor_transporte_pct NUMERIC(10,6) NOT NULL DEFAULT 100,       -- % sobre α; costo usado = α · factor / 100
    es_base              BOOLEAN       NOT NULL DEFAULT FALSE,
    creado_en            TIMESTAMPTZ   NOT NULL DEFAULT now(),
    actualizado_en       TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT uq_escenario_usuario_nombre UNIQUE (usuario_id, nombre),
    CONSTRAINT ck_escenario_alfa CHECK (alfa_cop_t_km >= 0),
    CONSTRAINT ck_escenario_factor CHECK (factor_transporte_pct > 0)
);

CREATE TABLE escenario_empresa (
    id                   BIGSERIAL     PRIMARY KEY,
    escenario_id         BIGINT        NOT NULL REFERENCES escenario(id) ON DELETE CASCADE,
    empresa_id           INTEGER       NOT NULL REFERENCES empresa(id),
    oferta_t_semana      NUMERIC(12,2) NOT NULL,                    -- O_i
    precio_tonelada_cop  NUMERIC(12,2) NOT NULL DEFAULT 0,          -- β_i
    CONSTRAINT uq_esc_empresa UNIQUE (escenario_id, empresa_id),
    CONSTRAINT ck_esc_empresa_oferta CHECK (oferta_t_semana >= 0),
    CONSTRAINT ck_esc_empresa_precio CHECK (precio_tonelada_cop >= 0)
);

CREATE TABLE escenario_planta (
    id                     BIGSERIAL     PRIMARY KEY,
    escenario_id           BIGINT        NOT NULL REFERENCES escenario(id) ON DELETE CASCADE,
    planta_id              INTEGER       NOT NULL REFERENCES planta(id),
    demanda_t_semana       NUMERIC(12,2) NOT NULL,                  -- D_j
    costo_operacion_cop_t  NUMERIC(12,2) NOT NULL,                  -- p_j
    CONSTRAINT uq_esc_planta UNIQUE (escenario_id, planta_id),
    CONSTRAINT ck_esc_planta_demanda CHECK (demanda_t_semana >= 0),
    CONSTRAINT ck_esc_planta_costo CHECK (costo_operacion_cop_t >= 0)
);

CREATE TABLE ruta (
    id                    BIGSERIAL    PRIMARY KEY,
    escenario_empresa_id  BIGINT       NOT NULL REFERENCES escenario_empresa(id) ON DELETE CASCADE,
    escenario_planta_id   BIGINT       NOT NULL REFERENCES escenario_planta(id)  ON DELETE CASCADE,
    distancia_km          NUMERIC(8,2) NOT NULL,                    -- d_ij
    habilitada            BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_ruta UNIQUE (escenario_empresa_id, escenario_planta_id),
    CONSTRAINT ck_ruta_distancia CHECK (distancia_km >= 0)
);

-- =====================================================================
--  4. CATÁLOGOS
-- =====================================================================
CREATE TABLE metodo_solucion (
    id           SMALLSERIAL  PRIMARY KEY,
    nombre       VARCHAR(40)  NOT NULL UNIQUE,
    descripcion  VARCHAR(150)
);

CREATE TABLE estado_ejecucion (
    id      SMALLSERIAL PRIMARY KEY,
    nombre  VARCHAR(30) NOT NULL UNIQUE
);

CREATE TABLE metodo_seleccion (
    id      SMALLSERIAL PRIMARY KEY,
    nombre  VARCHAR(30) NOT NULL UNIQUE
);

CREATE TABLE tipo_cruce (
    id      SMALLSERIAL PRIMARY KEY,
    nombre  VARCHAR(30) NOT NULL UNIQUE
);

CREATE TABLE tipo_parametro (
    id           SMALLSERIAL  PRIMARY KEY,
    nombre       VARCHAR(40)  NOT NULL UNIQUE,
    descripcion  VARCHAR(150)
);

-- =====================================================================
--  5. EJECUCIONES Y RESULTADOS (modelo exacto HiGHS / AG)
-- =====================================================================
CREATE TABLE ejecucion (
    id                   BIGSERIAL     PRIMARY KEY,
    escenario_id         BIGINT        NOT NULL REFERENCES escenario(id) ON DELETE CASCADE,
    metodo_solucion_id   SMALLINT      NOT NULL REFERENCES metodo_solucion(id),
    estado_ejecucion_id  SMALLINT      NOT NULL REFERENCES estado_ejecucion(id),
    iniciada_en          TIMESTAMPTZ   NOT NULL DEFAULT now(),
    tiempo_ms            NUMERIC(12,3),
    costo_objetivo_cop   NUMERIC(16,2),                             -- Z
    iteraciones          INTEGER,
    mensaje              TEXT,
    CONSTRAINT ck_ejecucion_tiempo CHECK (tiempo_ms IS NULL OR tiempo_ms >= 0)
);

CREATE TABLE resultado_ruta (
    id                     BIGSERIAL     PRIMARY KEY,
    ejecucion_id           BIGINT        NOT NULL REFERENCES ejecucion(id) ON DELETE CASCADE,
    ruta_id                BIGINT        NOT NULL REFERENCES ruta(id) ON DELETE CASCADE,
    toneladas              NUMERIC(12,2) NOT NULL,                  -- x_ij
    costo_reducido         NUMERIC(14,2),
    costo_min_optimalidad  NUMERIC(14,2),
    costo_max_optimalidad  NUMERIC(14,2),
    CONSTRAINT uq_resultado_ruta UNIQUE (ejecucion_id, ruta_id),
    CONSTRAINT ck_resultado_toneladas CHECK (toneladas >= 0)
);

-- =====================================================================
--  6. ANÁLISIS DE SENSIBILIDAD
-- =====================================================================
CREATE TABLE sensibilidad_oferta (
    id                    BIGSERIAL     PRIMARY KEY,
    ejecucion_id          BIGINT        NOT NULL REFERENCES ejecucion(id) ON DELETE CASCADE,
    escenario_empresa_id  BIGINT        NOT NULL REFERENCES escenario_empresa(id) ON DELETE CASCADE,
    precio_sombra         NUMERIC(14,2) NOT NULL,
    holgura               NUMERIC(12,2) NOT NULL,
    oferta_min            NUMERIC(12,2),
    oferta_max            NUMERIC(12,2),
    CONSTRAINT uq_sens_oferta UNIQUE (ejecucion_id, escenario_empresa_id)
);

CREATE TABLE sensibilidad_demanda (
    id                   BIGSERIAL     PRIMARY KEY,
    ejecucion_id         BIGINT        NOT NULL REFERENCES ejecucion(id) ON DELETE CASCADE,
    escenario_planta_id  BIGINT        NOT NULL REFERENCES escenario_planta(id) ON DELETE CASCADE,
    precio_sombra        NUMERIC(14,2) NOT NULL,
    holgura              NUMERIC(12,2) NOT NULL,
    demanda_min          NUMERIC(12,2),
    demanda_max          NUMERIC(12,2),
    CONSTRAINT uq_sens_demanda UNIQUE (ejecucion_id, escenario_planta_id)
);

CREATE TABLE analisis_sensibilidad (
    id                 BIGSERIAL    PRIMARY KEY,
    escenario_base_id  BIGINT       NOT NULL REFERENCES escenario(id) ON DELETE CASCADE,
    tipo_parametro_id  SMALLINT     NOT NULL REFERENCES tipo_parametro(id),
    empresa_id         INTEGER      REFERENCES empresa(id),          -- si el parámetro es de una empresa
    planta_id          INTEGER      REFERENCES planta(id),           -- si el parámetro es de una planta
    nombre             VARCHAR(100) NOT NULL,
    variacion_min_pct  NUMERIC(6,2) NOT NULL,
    variacion_max_pct  NUMERIC(6,2) NOT NULL,
    paso_pct           NUMERIC(6,2) NOT NULL,
    creado_en          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT ck_analisis_rango CHECK (variacion_min_pct < variacion_max_pct),
    CONSTRAINT ck_analisis_paso  CHECK (paso_pct > 0)
);

CREATE TABLE punto_sensibilidad (
    id             BIGSERIAL    PRIMARY KEY,
    analisis_id    BIGINT       NOT NULL REFERENCES analisis_sensibilidad(id) ON DELETE CASCADE,
    escenario_id   BIGINT       NOT NULL REFERENCES escenario(id) ON DELETE CASCADE,  -- escenario derivado
    variacion_pct  NUMERIC(6,2) NOT NULL,
    CONSTRAINT uq_punto_sens UNIQUE (analisis_id, variacion_pct)
);

-- =====================================================================
--  7. ALGORITMO GENÉTICO
-- =====================================================================
CREATE TABLE parametros_ag (
    ejecucion_id         BIGINT        PRIMARY KEY REFERENCES ejecucion(id) ON DELETE CASCADE,
    metodo_seleccion_id  SMALLINT      NOT NULL REFERENCES metodo_seleccion(id),
    tipo_cruce_id        SMALLINT      NOT NULL REFERENCES tipo_cruce(id),
    tamano_poblacion     INTEGER       NOT NULL,
    num_generaciones     INTEGER       NOT NULL,
    tasa_cruce           NUMERIC(4,3)  NOT NULL,
    tasa_mutacion        NUMERIC(4,3)  NOT NULL,
    tamano_torneo        SMALLINT,
    elitismo             SMALLINT      NOT NULL DEFAULT 0,
    factor_penalizacion  NUMERIC(16,2) NOT NULL,
    semilla              INTEGER,
    CONSTRAINT ck_ag_poblacion   CHECK (tamano_poblacion > 1),
    CONSTRAINT ck_ag_generaciones CHECK (num_generaciones > 0),
    CONSTRAINT ck_ag_tasa_cruce  CHECK (tasa_cruce BETWEEN 0 AND 1),
    CONSTRAINT ck_ag_tasa_mut    CHECK (tasa_mutacion BETWEEN 0 AND 1),
    CONSTRAINT ck_ag_elitismo    CHECK (elitismo >= 0)
);

CREATE TABLE historial_generacion (
    id              BIGSERIAL        PRIMARY KEY,
    ejecucion_id    BIGINT           NOT NULL REFERENCES parametros_ag(ejecucion_id) ON DELETE CASCADE,
    num_generacion  INTEGER          NOT NULL,
    mejor_costo     NUMERIC(16,2)    NOT NULL,
    costo_promedio  NUMERIC(16,2)    NOT NULL,
    mejor_fitness   DOUBLE PRECISION NOT NULL,
    violaciones     INTEGER          NOT NULL DEFAULT 0,
    CONSTRAINT uq_historial_gen UNIQUE (ejecucion_id, num_generacion)
);

-- =====================================================================
--  8. COMPARACIÓN EXACTO vs. AG
-- =====================================================================
CREATE TABLE comparacion (
    id                   BIGSERIAL   PRIMARY KEY,
    ejecucion_exacta_id  BIGINT      NOT NULL REFERENCES ejecucion(id) ON DELETE CASCADE,
    ejecucion_ag_id      BIGINT      NOT NULL REFERENCES ejecucion(id) ON DELETE CASCADE,
    observaciones        TEXT,
    creada_en            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_comparacion UNIQUE (ejecucion_exacta_id, ejecucion_ag_id),
    CONSTRAINT ck_comparacion_distintas CHECK (ejecucion_exacta_id <> ejecucion_ag_id)
);

-- =====================================================================
--  9. ÍNDICES SOBRE CLAVES FORÁNEAS (consultas frecuentes)
-- =====================================================================
CREATE INDEX ix_usuario_rol            ON usuario(rol_id);
CREATE INDEX ix_municipio_depto        ON municipio(departamento_id);
CREATE INDEX ix_empresa_municipio      ON empresa(municipio_id);
CREATE INDEX ix_empresa_tipo_residuo   ON empresa(tipo_residuo_id);
CREATE INDEX ix_planta_municipio       ON planta(municipio_id);
CREATE INDEX ix_escenario_usuario      ON escenario(usuario_id);
CREATE INDEX ix_escenario_origen       ON escenario(escenario_origen_id);
CREATE INDEX ix_esc_empresa_empresa    ON escenario_empresa(empresa_id);
CREATE INDEX ix_esc_planta_planta      ON escenario_planta(planta_id);
CREATE INDEX ix_ruta_esc_planta        ON ruta(escenario_planta_id);
CREATE INDEX ix_ejecucion_escenario    ON ejecucion(escenario_id);
CREATE INDEX ix_ejecucion_metodo       ON ejecucion(metodo_solucion_id);
CREATE INDEX ix_resultado_ruta_ruta    ON resultado_ruta(ruta_id);
CREATE INDEX ix_sens_oferta_esc_emp    ON sensibilidad_oferta(escenario_empresa_id);
CREATE INDEX ix_sens_demanda_esc_pla   ON sensibilidad_demanda(escenario_planta_id);
CREATE INDEX ix_analisis_escenario     ON analisis_sensibilidad(escenario_base_id);
CREATE INDEX ix_punto_escenario        ON punto_sensibilidad(escenario_id);
CREATE INDEX ix_comparacion_ag         ON comparacion(ejecucion_ag_id);

-- =====================================================================
--  10. TRIGGERS
-- =====================================================================
-- 10.1 Una ruta solo puede unir una empresa y una planta del MISMO escenario
CREATE FUNCTION fn_ruta_mismo_escenario() RETURNS trigger AS $$
DECLARE
    esc_emp BIGINT;
    esc_pla BIGINT;
BEGIN
    SELECT escenario_id INTO esc_emp FROM escenario_empresa WHERE id = NEW.escenario_empresa_id;
    SELECT escenario_id INTO esc_pla FROM escenario_planta  WHERE id = NEW.escenario_planta_id;
    IF esc_emp IS DISTINCT FROM esc_pla THEN
        RAISE EXCEPTION 'La ruta une una empresa (escenario %) y una planta (escenario %) de escenarios distintos',
                        esc_emp, esc_pla;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tg_ruta_mismo_escenario
    BEFORE INSERT OR UPDATE ON ruta
    FOR EACH ROW EXECUTE FUNCTION fn_ruta_mismo_escenario();

-- 10.2 Mantener actualizado_en del escenario
CREATE FUNCTION fn_actualizado_en() RETURNS trigger AS $$
BEGIN
    NEW.actualizado_en := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tg_escenario_actualizado
    BEFORE UPDATE ON escenario
    FOR EACH ROW EXECUTE FUNCTION fn_actualizado_en();

-- =====================================================================
--  11. VISTAS (valores derivados que NO se almacenan, por 3FN)
-- =====================================================================
-- c_ij = α · (factor/100) · d_ij + p_j + β_i   (matriz de costos unitarios por escenario)
CREATE VIEW v_costo_unitario AS
SELECT  e.id                    AS escenario_id,
        e.nombre                AS escenario,
        r.id                    AS ruta_id,
        em.codigo               AS empresa,
        pl.codigo               AS planta,
        ee.oferta_t_semana      AS oferta,
        ep.demanda_t_semana     AS demanda,
        r.distancia_km,
        e.alfa_cop_t_km         AS alfa,
        e.factor_transporte_pct AS factor_transporte,
        ep.costo_operacion_cop_t AS costo_operacion,
        ee.precio_tonelada_cop  AS precio_compra,
        (e.alfa_cop_t_km * e.factor_transporte_pct / 100 * r.distancia_km
         + ep.costo_operacion_cop_t + ee.precio_tonelada_cop)::NUMERIC(14,2) AS costo_unitario_cop_t,
        r.habilitada
FROM ruta r
JOIN escenario_empresa ee ON ee.id = r.escenario_empresa_id
JOIN escenario_planta  ep ON ep.id = r.escenario_planta_id
JOIN escenario         e  ON e.id  = ee.escenario_id
JOIN empresa           em ON em.id = ee.empresa_id
JOIN planta            pl ON pl.id = ep.planta_id;

-- Comparación exacto vs. AG: gap % y tiempos
CREATE VIEW v_comparacion AS
SELECT  c.id                         AS comparacion_id,
        ex.escenario_id,
        ex.costo_objetivo_cop        AS z_exacto,
        ag.costo_objetivo_cop        AS z_ag,
        ROUND((ag.costo_objetivo_cop - ex.costo_objetivo_cop)
              / NULLIF(ex.costo_objetivo_cop, 0) * 100, 4) AS gap_pct,
        ex.tiempo_ms                 AS tiempo_exacto_ms,
        ag.tiempo_ms                 AS tiempo_ag_ms,
        c.creada_en
FROM comparacion c
JOIN ejecucion ex ON ex.id = c.ejecucion_exacta_id
JOIN ejecucion ag ON ag.id = c.ejecucion_ag_id;

-- =====================================================================
--  12. DATOS INICIALES
-- =====================================================================
-- 12.1 Catálogos
INSERT INTO rol (nombre, descripcion) VALUES
  ('ANALISTA', 'Gestiona escenarios, ejecuta el modelo exacto y el AG, y realiza el análisis de sensibilidad');

INSERT INTO metodo_solucion (nombre, descripcion) VALUES
  ('EXACTO_SIMPLEX',     'Método Simplex de dos fases'),
  ('ALGORITMO_GENETICO', 'Metaheurística: Algoritmo Genético');

INSERT INTO estado_ejecucion (nombre) VALUES
  ('PENDIENTE'), ('OPTIMO'), ('FACTIBLE'), ('INFACTIBLE'), ('NO_ACOTADO'), ('ERROR');

INSERT INTO metodo_seleccion (nombre) VALUES ('RULETA'), ('TORNEO');

INSERT INTO tipo_cruce (nombre) VALUES ('UN_PUNTO'), ('DOS_PUNTOS');

INSERT INTO tipo_parametro (nombre, descripcion) VALUES
  ('ALFA',            'Costo de transporte por tonelada-kilómetro (α)'),
  ('OFERTA',          'Oferta semanal de una empresa (O_i)'),
  ('DEMANDA',         'Demanda semanal de una planta (D_j)'),
  ('COSTO_OPERACION', 'Costo de operación por tonelada de una planta (p_j)'),
  ('DISTANCIA',       'Distancia de una ruta (d_ij)');

-- 12.2 Usuario analista por defecto
--      usuario: analista   ·   contraseña: Analista2026*   (cambiarla tras el primer ingreso)
INSERT INTO usuario (rol_id, username, email, password_hash, nombres, apellidos)
SELECT r.id, 'analista', 'analista@ecoresiduos.local',
       crypt('Analista2026*', gen_salt('bf', 10)), 'Analista', 'EcoResiduos'
FROM rol r WHERE r.nombre = 'ANALISTA';

-- 12.3 Geografía (códigos DANE)
INSERT INTO departamento (codigo_dane, nombre) VALUES ('50', 'Meta');

INSERT INTO municipio (departamento_id, codigo_dane, nombre, latitud, longitud)
SELECT d.id, v.codigo, v.nombre, v.lat, v.lon
FROM departamento d
CROSS JOIN (VALUES
  ('50001', 'Villavicencio',        4.142000, -73.627000),
  ('50606', 'Restrepo',             4.258000, -73.562000),
  ('50313', 'Granada',              3.546000, -73.707000),
  ('50568', 'Puerto Gaitán',        4.314000, -72.083000),
  ('50226', 'Cumaral',              4.271000, -73.487000),
  ('50573', 'Puerto López',         4.085000, -72.956000),
  ('50680', 'San Carlos de Guaroa', 3.711000, -73.243000)
) AS v(codigo, nombre, lat, lon)
WHERE d.codigo_dane = '50';

-- 12.4 Tipos de residuo (Tabla 2.1 del documento de la Fase 1)
INSERT INTO tipo_residuo (nombre) VALUES
  ('Raquis y fibra de palma'),
  ('Cuesco y raquis de palma'),
  ('Biomasa de poda foliar'),
  ('Fibra y residuos de prensado'),
  ('Tamo y cascarilla de arroz'),
  ('Cascarilla de arroz'),
  ('Estiércol porcino/bovino'),
  ('Biomasa maderable'),
  ('Bagazo de caña de azúcar'),
  ('Estiércol de bovinos');

-- 12.5 Empresas (orígenes)
INSERT INTO empresa (codigo, nombre, municipio_id, tipo_residuo_id)
SELECT v.codigo, v.nombre, m.id, t.id
FROM (VALUES
  ('E1', 'Palmeras del Llano S.A.S.',  'San Carlos de Guaroa', 'Raquis y fibra de palma'),
  ('E2', 'Unipalma de Los Llanos S.A.',  'Cumaral',              'Cuesco y raquis de palma'),
  ('E3', 'Poligrow Colombia S.A.S.',  'Puerto Gaitán',        'Biomasa de poda foliar'),
  ('E4', 'Aceites Cumaral S.A.S.',  'Cumaral',              'Fibra y residuos de prensado'),
  ('E5', 'Comercializadora del Llano S.A.',  'Villavicencio',        'Tamo y cascarilla de arroz'),
  ('E6', 'Molinos Roa S.A.',  'Villavicencio',        'Cascarilla de arroz'),
  ('E7', 'Agropecuaria Aliar S.A.',  'Puerto López',         'Estiércol porcino/bovino'),
  ('E8', 'Refocosta S.A.',  'Puerto López',         'Biomasa maderable'),
  ('E9', 'Bioenergy S.A.S.',  'Puerto López',         'Bagazo de caña de azúcar'),
  ('E10', 'Frigollano S.A.', 'Villavicencio',        'Estiércol de bovinos')
) AS v(codigo, nombre, municipio, residuo)
JOIN municipio    m ON m.nombre = v.municipio
JOIN tipo_residuo t ON t.nombre = v.residuo
ORDER BY length(v.codigo), v.codigo;

-- 12.6 Plantas (destinos)
INSERT INTO planta (codigo, nombre, municipio_id)
SELECT v.codigo, v.nombre, m.id
FROM (VALUES
  ('P1', 'Planta Villavicencio', 'Villavicencio'),
  ('P2', 'Planta Restrepo',      'Restrepo'),
  ('P3', 'Planta Granada',       'Granada'),
  ('P4', 'Planta Puerto Gaitán', 'Puerto Gaitán')
) AS v(codigo, nombre, municipio)
JOIN municipio m ON m.nombre = v.municipio
ORDER BY v.codigo;

-- 12.7 Escenario "Caso base" (α = 750 COP/(t·km))
INSERT INTO escenario (usuario_id, nombre, descripcion, alfa_cop_t_km, es_base)
SELECT u.id, 'Caso base', NULL, 750, TRUE
FROM usuario u WHERE u.username = 'analista';

-- 12.8 Oferta O_i y precio β_i por empresa
INSERT INTO escenario_empresa (escenario_id, empresa_id, oferta_t_semana, precio_tonelada_cop)
SELECT e.id, em.id, v.oferta, 12000
FROM escenario e
CROSS JOIN (VALUES
  ('E1', 150), ('E2', 120), ('E3', 110), ('E4', 140), ('E5', 100),
  ('E6', 100), ('E7', 150), ('E8', 120), ('E9', 120), ('E10', 140)
) AS v(codigo, oferta)
JOIN empresa em ON em.codigo = v.codigo
WHERE e.nombre = 'Caso base';

-- 12.9 Demanda D_j y costo de operación p_j por planta
INSERT INTO escenario_planta (escenario_id, planta_id, demanda_t_semana, costo_operacion_cop_t)
SELECT e.id, p.id, v.demanda, v.costo
FROM escenario e
CROSS JOIN (VALUES
  ('P1', 400, 42000), ('P2', 250, 48000), ('P3', 300, 45000), ('P4', 300, 38000)
) AS v(codigo, demanda, costo)
JOIN planta p ON p.codigo = v.codigo
WHERE e.nombre = 'Caso base';

-- 12.10 Distancias d_ij (km) – Matriz 3.3 del documento de la Fase 1
INSERT INTO ruta (escenario_empresa_id, escenario_planta_id, distancia_km)
SELECT ee.id, ep.id, v.km
FROM escenario e
CROSS JOIN (VALUES
  ('E1','P1', 85), ('E1','P2',102), ('E1','P3', 92), ('E1','P4',275),
  ('E2','P1', 28), ('E2','P2', 15), ('E2','P3',113), ('E2','P4',218),
  ('E3','P1',190), ('E3','P2',207), ('E3','P3',275), ('E3','P4',  5),
  ('E4','P1', 28), ('E4','P2', 15), ('E4','P3',113), ('E4','P4',218),
  ('E5','P1',  5), ('E5','P2', 22), ('E5','P3', 85), ('E5','P4',190),
  ('E6','P1',  5), ('E6','P2', 22), ('E6','P3', 85), ('E6','P4',190),
  ('E7','P1', 85), ('E7','P2',102), ('E7','P3',170), ('E7','P4',105),
  ('E8','P1', 85), ('E8','P2',102), ('E8','P3',170), ('E8','P4',105),
  ('E9','P1', 85), ('E9','P2',102), ('E9','P3',170), ('E9','P4',105),
  ('E10','P1', 5), ('E10','P2',22), ('E10','P3', 85), ('E10','P4',190)
) AS v(emp, pla, km)
JOIN empresa em            ON em.codigo = v.emp
JOIN planta  pl            ON pl.codigo = v.pla
JOIN escenario_empresa ee  ON ee.escenario_id = e.id AND ee.empresa_id = em.id
JOIN escenario_planta  ep  ON ep.escenario_id = e.id AND ep.planta_id  = pl.id
WHERE e.nombre = 'Caso base';

COMMIT;

-- =====================================================================
--  Consultas de verificación (opcionales)
-- =====================================================================
-- Matriz de costos unitarios del caso base (debe coincidir con la Tabla 4.3):
--   SELECT empresa, planta, distancia_km, costo_unitario_cop_t
--   FROM v_costo_unitario WHERE escenario = 'Caso base' ORDER BY ruta_id;
--
-- Condición de balanceo:
--   SELECT (SELECT SUM(oferta_t_semana)  FROM escenario_empresa WHERE escenario_id = 1) AS oferta_total,
--          (SELECT SUM(demanda_t_semana) FROM escenario_planta  WHERE escenario_id = 1) AS demanda_total;
--
-- Login (desde la app se compara con bcrypt; en SQL sería):
--   SELECT id FROM usuario
--   WHERE username = 'analista' AND activo
--     AND password_hash = crypt('Analista2026*', password_hash);
