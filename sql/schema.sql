-- Esquema PostgreSQL (Neon / Vercel Storage) — Fase 5.
--
-- Este DDL é totalmente idempotente (CREATE TABLE IF NOT EXISTS,
-- CREATE INDEX IF NOT EXISTS, CREATE OR REPLACE VIEW) e segue as regras
-- metodológicas das Fases 1 a 4:
--   1. Chave operacional natural em fact_restricoes: (ons_id, instante).
--   2. instante preservado como TIMESTAMP WITHOUT TIME ZONE (horário oficial
--      naive publicado pelo ONS, sem conversão implícita para UTC).
--   3. ceg preservado como texto literal (inclusive '-' para conjuntos sem CEG),
--      sem forçar vínculo com a ANEEL.
--   4. Valores ausentes em medidas de potência, minutos e energia permanecem
--      NULL (nunca substituídos por zero com DEFAULT 0 ou COALESCE).
--   5. GNRa (geracao_nao_realizada_apurada) é preservada no grão original sem
--      agregação energética em MWh enquanto sua unidade aguardar confirmação.

-- =============================================================================
-- 1. Auditoria de execuções ETL e revisões ONS
-- =============================================================================

CREATE TABLE IF NOT EXISTS etl_execucoes (
    execucao_id BIGSERIAL PRIMARY KEY,
    fonte TEXT NOT NULL,
    estado_sigla CHAR(2) NOT NULL CHECK (estado_sigla ~ '^[A-Z]{2}$'),
    ano_referencia SMALLINT NOT NULL CHECK (ano_referencia BETWEEN 1000 AND 9999),
    mes_referencia SMALLINT NOT NULL CHECK (mes_referencia BETWEEN 1 AND 12),
    arquivo_bruto_nome TEXT NOT NULL,
    arquivo_bruto_sha256 CHAR(64) NOT NULL CHECK (arquivo_bruto_sha256 ~ '^[0-9A-Fa-f]{64}$'),
    arquivo_parquet_nome TEXT,
    arquivo_parquet_sha256 CHAR(64) CHECK (
        arquivo_parquet_sha256 IS NULL OR arquivo_parquet_sha256 ~ '^[0-9A-Fa-f]{64}$'
    ),
    url_origem TEXT,
    coletado_em_utc TIMESTAMPTZ,
    processado_em_utc TIMESTAMPTZ NOT NULL,
    carregado_em_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    linhas_entrada INTEGER NOT NULL CHECK (linhas_entrada >= 0),
    linhas_saida INTEGER NOT NULL CHECK (linhas_saida >= 0),
    linhas_excluidas_uf INTEGER NOT NULL DEFAULT 0 CHECK (linhas_excluidas_uf >= 0),
    linhas_duplicadas_removidas INTEGER NOT NULL DEFAULT 0 CHECK (linhas_duplicadas_removidas >= 0),
    linhas_carregadas INTEGER NOT NULL CHECK (linhas_carregadas >= 0),
    gnra_unit_status TEXT NOT NULL DEFAULT 'pending_official_confirmation',
    metodologia_versao TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('iniciada', 'concluida', 'falha')),
    mensagem_erro TEXT,
    relatorio_qualidade_json JSONB
);

CREATE INDEX IF NOT EXISTS idx_etl_execucoes_periodo
    ON etl_execucoes (fonte, estado_sigla, ano_referencia, mes_referencia, carregado_em_utc DESC);

CREATE INDEX IF NOT EXISTS idx_etl_execucoes_status
    ON etl_execucoes (status, carregado_em_utc DESC);

-- =============================================================================
-- 2. Dimensão de empreendimentos / conjuntos de usinas (chave operacional ONS)
-- =============================================================================

CREATE TABLE IF NOT EXISTS dim_empreendimentos (
    ons_id TEXT PRIMARY KEY CHECK (BTRIM(ons_id) <> ''),
    usina_nome TEXT NOT NULL CHECK (BTRIM(usina_nome) <> ''),
    estado_sigla CHAR(2) NOT NULL CHECK (estado_sigla ~ '^[A-Z]{2}$'),
    estado_nome TEXT,
    subsistema_id TEXT,
    subsistema_nome TEXT,
    ceg TEXT NOT NULL CHECK (BTRIM(ceg) <> ''),
    tipo_identificador TEXT NOT NULL CHECK (
        tipo_identificador IN ('usina_com_ceg', 'conjunto_sem_ceg')
    ),
    elegivel_enriquecimento_aneel BOOLEAN NOT NULL,
    ponto_conexao_id TEXT,
    ponto_conexao_nome TEXT,
    agente_operador_nome TEXT,
    primeira_aparicao TIMESTAMP WITHOUT TIME ZONE,
    ultima_aparicao TIMESTAMP WITHOUT TIME ZONE,
    atualizado_em_utc TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dim_empreendimentos_estado
    ON dim_empreendimentos (estado_sigla, usina_nome);

-- =============================================================================
-- 3. Tabela fato semi-horária de geração e restrições (constrained-off)
-- =============================================================================

CREATE TABLE IF NOT EXISTS fact_restricoes (
    ons_id TEXT NOT NULL REFERENCES dim_empreendimentos (ons_id),
    instante TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    estado_sigla CHAR(2) NOT NULL CHECK (estado_sigla ~ '^[A-Z]{2}$'),
    usina_nome TEXT NOT NULL CHECK (BTRIM(usina_nome) <> ''),
    ceg TEXT NOT NULL CHECK (BTRIM(ceg) <> ''),
    duracao_horas DOUBLE PRECISION NOT NULL CHECK (duracao_horas > 0),

    -- Potências médias no patamar (MWmed) — nulos preservados como NULL
    geracao_mwmed DOUBLE PRECISION,
    geracao_limitada_mwmed DOUBLE PRECISION,
    disponibilidade_mwmed DOUBLE PRECISION,
    geracao_referencia_mwmed DOUBLE PRECISION,
    geracao_referencia_final_mwmed DOUBLE PRECISION,

    -- GNRa oficial preservada sem conversão energética prematura
    geracao_nao_realizada_apurada DOUBLE PRECISION,

    -- Classificação e minutos de restrição no patamar
    restricao_razao_codigo TEXT,
    restricao_origem_codigo TEXT,
    restricao_descricao TEXT,
    minutos_restricao_rel DOUBLE PRECISION CHECK (
        minutos_restricao_rel IS NULL OR (minutos_restricao_rel >= 0 AND minutos_restricao_rel <= 30)
    ),
    minutos_restricao_cnf DOUBLE PRECISION CHECK (
        minutos_restricao_cnf IS NULL OR (minutos_restricao_cnf >= 0 AND minutos_restricao_cnf <= 30)
    ),
    minutos_restricao_ene DOUBLE PRECISION CHECK (
        minutos_restricao_ene IS NULL OR (minutos_restricao_ene >= 0 AND minutos_restricao_ene <= 30)
    ),
    minutos_restricao_total DOUBLE PRECISION CHECK (
        minutos_restricao_total IS NULL OR (minutos_restricao_total >= 0 AND minutos_restricao_total <= 30)
    ),

    -- Energia validada (MWh = MWmed * duracao_horas) — nulos preservados como NULL
    geracao_verificada_mwh DOUBLE PRECISION,
    geracao_referencia_final_mwh DOUBLE PRECISION,

    -- Sinalizadores explícitos de elegibilidade da Fase 3
    elegivel_geracao_verificada BOOLEAN NOT NULL,
    elegivel_referencia_final BOOLEAN NOT NULL,
    possui_restricao_classificada BOOLEAN NOT NULL,
    elegivel_gnra BOOLEAN NOT NULL,
    elegivel_enriquecimento_aneel BOOLEAN NOT NULL,

    -- Linhagem e versionamento metodológico
    execucao_id BIGINT NOT NULL REFERENCES etl_execucoes (execucao_id),
    metodologia_versao TEXT NOT NULL,
    atualizado_em_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (ons_id, instante)
);

CREATE INDEX IF NOT EXISTS idx_fact_restricoes_estado_instante
    ON fact_restricoes (estado_sigla, instante);

CREATE INDEX IF NOT EXISTS idx_fact_restricoes_estado_razao_origem
    ON fact_restricoes (estado_sigla, restricao_razao_codigo, restricao_origem_codigo);

CREATE INDEX IF NOT EXISTS idx_fact_restricoes_restritas
    ON fact_restricoes (estado_sigla, instante)
    WHERE possui_restricao_classificada = TRUE;

CREATE INDEX IF NOT EXISTS idx_fact_restricoes_execucao
    ON fact_restricoes (execucao_id);

-- =============================================================================
-- 4. Views analíticas pré-agregadas (sempre sincronizadas, sem NULL -> 0)
-- =============================================================================

CREATE OR REPLACE VIEW vw_serie_diaria AS
SELECT
    f.estado_sigla,
    DATE(f.instante) AS data_referencia,
    COUNT(*) AS total_intervalos,
    COUNT(*) FILTER (WHERE f.possui_restricao_classificada) AS intervalos_com_restricao,
    COUNT(*) FILTER (WHERE NOT f.possui_restricao_classificada) AS intervalos_sem_restricao,
    CASE
        WHEN COUNT(*) > 0 THEN ROUND(
            (100.0 * COUNT(*) FILTER (WHERE f.possui_restricao_classificada))::NUMERIC / COUNT(*),
            4
        )::DOUBLE PRECISION
        ELSE NULL
    END AS taxa_intervalos_restricao_pct,
    COUNT(DISTINCT f.ons_id) AS empreendimentos_observados,
    COUNT(DISTINCT f.ons_id) FILTER (WHERE f.possui_restricao_classificada) AS empreendimentos_com_restricao,
    COUNT(*) FILTER (WHERE f.elegivel_geracao_verificada) AS intervalos_elegiveis_geracao,
    COUNT(*) FILTER (WHERE f.elegivel_referencia_final) AS intervalos_elegiveis_referencia_final,
    COUNT(*) FILTER (WHERE f.elegivel_gnra) AS intervalos_elegiveis_gnra,
    SUM(f.geracao_verificada_mwh) FILTER (WHERE f.elegivel_geracao_verificada) AS geracao_verificada_mwh,
    SUM(f.geracao_referencia_final_mwh) FILTER (WHERE f.elegivel_referencia_final) AS geracao_referencia_final_mwh,
    SUM(f.minutos_restricao_total) FILTER (WHERE f.possui_restricao_classificada) AS minutos_restricao_total
FROM fact_restricoes AS f
GROUP BY f.estado_sigla, DATE(f.instante);

CREATE OR REPLACE VIEW vw_serie_mensal AS
SELECT
    f.estado_sigla,
    DATE_TRUNC('month', f.instante)::DATE AS mes_referencia,
    COUNT(*) AS total_intervalos,
    COUNT(*) FILTER (WHERE f.possui_restricao_classificada) AS intervalos_com_restricao,
    COUNT(*) FILTER (WHERE NOT f.possui_restricao_classificada) AS intervalos_sem_restricao,
    CASE
        WHEN COUNT(*) > 0 THEN ROUND(
            (100.0 * COUNT(*) FILTER (WHERE f.possui_restricao_classificada))::NUMERIC / COUNT(*),
            4
        )::DOUBLE PRECISION
        ELSE NULL
    END AS taxa_intervalos_restricao_pct,
    COUNT(DISTINCT f.ons_id) AS empreendimentos_observados,
    COUNT(DISTINCT f.ons_id) FILTER (WHERE f.possui_restricao_classificada) AS empreendimentos_com_restricao,
    COUNT(*) FILTER (WHERE f.elegivel_geracao_verificada) AS intervalos_elegiveis_geracao,
    COUNT(*) FILTER (WHERE f.elegivel_referencia_final) AS intervalos_elegiveis_referencia_final,
    COUNT(*) FILTER (WHERE f.elegivel_gnra) AS intervalos_elegiveis_gnra,
    SUM(f.geracao_verificada_mwh) FILTER (WHERE f.elegivel_geracao_verificada) AS geracao_verificada_mwh,
    SUM(f.geracao_referencia_final_mwh) FILTER (WHERE f.elegivel_referencia_final) AS geracao_referencia_final_mwh,
    SUM(f.minutos_restricao_total) FILTER (WHERE f.possui_restricao_classificada) AS minutos_restricao_total
FROM fact_restricoes AS f
GROUP BY f.estado_sigla, DATE_TRUNC('month', f.instante)::DATE;

CREATE OR REPLACE VIEW vw_ranking_empreendimentos AS
SELECT
    f.estado_sigla,
    f.ons_id,
    d.usina_nome,
    d.ceg,
    d.tipo_identificador,
    d.elegivel_enriquecimento_aneel,
    COUNT(*) AS total_intervalos,
    COUNT(*) FILTER (WHERE f.possui_restricao_classificada) AS intervalos_com_restricao,
    CASE
        WHEN COUNT(*) > 0 THEN ROUND(
            (100.0 * COUNT(*) FILTER (WHERE f.possui_restricao_classificada))::NUMERIC / COUNT(*),
            4
        )::DOUBLE PRECISION
        ELSE NULL
    END AS taxa_intervalos_restricao_pct,
    COUNT(*) FILTER (WHERE f.elegivel_geracao_verificada) AS intervalos_elegiveis_geracao,
    COUNT(*) FILTER (WHERE f.elegivel_referencia_final) AS intervalos_elegiveis_referencia_final,
    SUM(f.geracao_verificada_mwh) FILTER (WHERE f.elegivel_geracao_verificada) AS geracao_verificada_mwh,
    SUM(f.geracao_referencia_final_mwh) FILTER (WHERE f.elegivel_referencia_final) AS geracao_referencia_final_mwh,
    SUM(f.minutos_restricao_total) FILTER (WHERE f.possui_restricao_classificada) AS minutos_restricao_total
FROM fact_restricoes AS f
INNER JOIN dim_empreendimentos AS d
    ON d.ons_id = f.ons_id
GROUP BY
    f.estado_sigla,
    f.ons_id,
    d.usina_nome,
    d.ceg,
    d.tipo_identificador,
    d.elegivel_enriquecimento_aneel;

CREATE OR REPLACE VIEW vw_resumo_razoes_origens AS
SELECT
    f.estado_sigla,
    f.restricao_razao_codigo,
    f.restricao_origem_codigo,
    COUNT(*) AS total_intervalos,
    COUNT(*) FILTER (WHERE f.possui_restricao_classificada) AS intervalos_com_restricao,
    COUNT(DISTINCT f.ons_id) AS empreendimentos_observados,
    COUNT(*) FILTER (WHERE f.elegivel_geracao_verificada) AS intervalos_elegiveis_geracao,
    COUNT(*) FILTER (WHERE f.elegivel_referencia_final) AS intervalos_elegiveis_referencia_final,
    SUM(f.geracao_verificada_mwh) FILTER (WHERE f.elegivel_geracao_verificada) AS geracao_verificada_mwh,
    SUM(f.geracao_referencia_final_mwh) FILTER (WHERE f.elegivel_referencia_final) AS geracao_referencia_final_mwh,
    SUM(f.minutos_restricao_total) FILTER (WHERE f.possui_restricao_classificada) AS minutos_restricao_total
FROM fact_restricoes AS f
GROUP BY
    f.estado_sigla,
    f.restricao_razao_codigo,
    f.restricao_origem_codigo;
