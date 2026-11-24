"""Persistência idempotente, configuração e migração de esquema PostgreSQL (Neon / Vercel).

Este módulo centraliza:
- Validação segura das URLs de conexão (``DATABASE_URL`` pooled e
  ``DIRECT_DATABASE_URL`` direta), sem expor credenciais em logs ou exceções.
- Leitura e aplicação idempotente do DDL oficial em ``sql/schema.sql`` via
  ``psycopg`` v3.
- Verificação de conectividade com o banco PostgreSQL (Neon).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
import re
import sys
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlparse, urlunparse

import psycopg

_logger = logging.getLogger(__name__)

VALID_POSTGRES_SCHEMES: frozenset[str] = frozenset({"postgresql", "postgres"})
DEFAULT_SCHEMA_PATH = Path("sql") / "schema.sql"
DEFAULT_ENV_FILE = Path(".env")
DEFAULT_CONNECT_TIMEOUT_SECONDS = 15
METHODOLOGY_VERSION = "v1.0"
GNRA_UNIT_STATUS_DEFAULT = "pending_official_confirmation"
_STATE_CODE_PATTERN = re.compile(r"^[A-Z]{2}$")
_SHA256_PATTERN = re.compile(r"^[0-9A-Fa-f]{64}$")
_POSTGRES_URL_CREDENTIAL_PATTERN = re.compile(
    r"(?i)(postgres(?:ql)?://[^/\s:@]+:)([^@\s]+)(@)"
)
_LIBPQ_PASSWORD_PATTERN = re.compile(
    r"(?i)(\bpassword\s*=\s*)(?:'(?:\\'|[^'])*'|\"(?:\\\"|[^\"])*\"|\S+)"
)

REQUIRED_PROCESSED_COLUMNS: tuple[str, ...] = (
    "subsistema_id",
    "subsistema_nome",
    "estado_sigla",
    "estado_nome",
    "usina_nome",
    "ons_id",
    "ceg",
    "instante",
    "geracao_mwmed",
    "geracao_limitada_mwmed",
    "disponibilidade_mwmed",
    "geracao_referencia_mwmed",
    "geracao_referencia_final_mwmed",
    "restricao_razao_codigo",
    "restricao_origem_codigo",
    "restricao_descricao",
    "ponto_conexao_id",
    "ponto_conexao_nome",
    "agente_operador_nome",
    "geracao_nao_realizada_apurada",
    "minutos_restricao_rel",
    "minutos_restricao_cnf",
    "minutos_restricao_ene",
    "minutos_restricao_total",
    "elegivel_geracao_verificada",
    "elegivel_referencia_final",
    "possui_restricao_classificada",
    "elegivel_gnra",
    "elegivel_enriquecimento_aneel",
    "duracao_horas",
    "geracao_verificada_mwh",
    "geracao_referencia_final_mwh",
)

_FACT_LOAD_COLUMNS: tuple[str, ...] = (
    "ons_id",
    "instante",
    "estado_sigla",
    "usina_nome",
    "ceg",
    "duracao_horas",
    "geracao_mwmed",
    "geracao_limitada_mwmed",
    "disponibilidade_mwmed",
    "geracao_referencia_mwmed",
    "geracao_referencia_final_mwmed",
    "geracao_nao_realizada_apurada",
    "restricao_razao_codigo",
    "restricao_origem_codigo",
    "restricao_descricao",
    "minutos_restricao_rel",
    "minutos_restricao_cnf",
    "minutos_restricao_ene",
    "minutos_restricao_total",
    "geracao_verificada_mwh",
    "geracao_referencia_final_mwh",
    "elegivel_geracao_verificada",
    "elegivel_referencia_final",
    "possui_restricao_classificada",
    "elegivel_gnra",
    "elegivel_enriquecimento_aneel",
    "execucao_id",
    "metodologia_versao",
)

_INSERT_ETL_EXECUTION_SQL = """
INSERT INTO etl_execucoes (
    fonte,
    estado_sigla,
    ano_referencia,
    mes_referencia,
    arquivo_bruto_nome,
    arquivo_bruto_sha256,
    arquivo_parquet_nome,
    arquivo_parquet_sha256,
    url_origem,
    coletado_em_utc,
    processado_em_utc,
    linhas_entrada,
    linhas_saida,
    linhas_excluidas_uf,
    linhas_duplicadas_removidas,
    linhas_carregadas,
    gnra_unit_status,
    metodologia_versao,
    status,
    relatorio_qualidade_json
)
VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, 0, %s, %s, 'iniciada', %s::jsonb
)
RETURNING execucao_id
"""

_UPSERT_DIM_EMPREENDIMENTOS_SQL = """
INSERT INTO dim_empreendimentos (
    ons_id,
    usina_nome,
    estado_sigla,
    estado_nome,
    subsistema_id,
    subsistema_nome,
    ceg,
    tipo_identificador,
    elegivel_enriquecimento_aneel,
    ponto_conexao_id,
    ponto_conexao_nome,
    agente_operador_nome,
    primeira_aparicao,
    ultima_aparicao,
    atualizado_em_utc
)
VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
)
ON CONFLICT (ons_id) DO UPDATE SET
    usina_nome = CASE
        WHEN dim_empreendimentos.ultima_aparicao IS NULL
             OR EXCLUDED.ultima_aparicao >= dim_empreendimentos.ultima_aparicao
        THEN EXCLUDED.usina_nome
        ELSE dim_empreendimentos.usina_nome
    END,
    estado_sigla = CASE
        WHEN dim_empreendimentos.ultima_aparicao IS NULL
             OR EXCLUDED.ultima_aparicao >= dim_empreendimentos.ultima_aparicao
        THEN EXCLUDED.estado_sigla
        ELSE dim_empreendimentos.estado_sigla
    END,
    estado_nome = CASE
        WHEN dim_empreendimentos.ultima_aparicao IS NULL
             OR EXCLUDED.ultima_aparicao >= dim_empreendimentos.ultima_aparicao
        THEN EXCLUDED.estado_nome
        ELSE dim_empreendimentos.estado_nome
    END,
    subsistema_id = CASE
        WHEN dim_empreendimentos.ultima_aparicao IS NULL
             OR EXCLUDED.ultima_aparicao >= dim_empreendimentos.ultima_aparicao
        THEN EXCLUDED.subsistema_id
        ELSE dim_empreendimentos.subsistema_id
    END,
    subsistema_nome = CASE
        WHEN dim_empreendimentos.ultima_aparicao IS NULL
             OR EXCLUDED.ultima_aparicao >= dim_empreendimentos.ultima_aparicao
        THEN EXCLUDED.subsistema_nome
        ELSE dim_empreendimentos.subsistema_nome
    END,
    ceg = CASE
        WHEN dim_empreendimentos.ultima_aparicao IS NULL
             OR EXCLUDED.ultima_aparicao >= dim_empreendimentos.ultima_aparicao
        THEN EXCLUDED.ceg
        ELSE dim_empreendimentos.ceg
    END,
    tipo_identificador = CASE
        WHEN dim_empreendimentos.ultima_aparicao IS NULL
             OR EXCLUDED.ultima_aparicao >= dim_empreendimentos.ultima_aparicao
        THEN EXCLUDED.tipo_identificador
        ELSE dim_empreendimentos.tipo_identificador
    END,
    elegivel_enriquecimento_aneel = CASE
        WHEN dim_empreendimentos.ultima_aparicao IS NULL
             OR EXCLUDED.ultima_aparicao >= dim_empreendimentos.ultima_aparicao
        THEN EXCLUDED.elegivel_enriquecimento_aneel
        ELSE dim_empreendimentos.elegivel_enriquecimento_aneel
    END,
    ponto_conexao_id = CASE
        WHEN dim_empreendimentos.ultima_aparicao IS NULL
             OR EXCLUDED.ultima_aparicao >= dim_empreendimentos.ultima_aparicao
        THEN EXCLUDED.ponto_conexao_id
        ELSE dim_empreendimentos.ponto_conexao_id
    END,
    ponto_conexao_nome = CASE
        WHEN dim_empreendimentos.ultima_aparicao IS NULL
             OR EXCLUDED.ultima_aparicao >= dim_empreendimentos.ultima_aparicao
        THEN EXCLUDED.ponto_conexao_nome
        ELSE dim_empreendimentos.ponto_conexao_nome
    END,
    agente_operador_nome = CASE
        WHEN dim_empreendimentos.ultima_aparicao IS NULL
             OR EXCLUDED.ultima_aparicao >= dim_empreendimentos.ultima_aparicao
        THEN EXCLUDED.agente_operador_nome
        ELSE dim_empreendimentos.agente_operador_nome
    END,
    primeira_aparicao = CASE
        WHEN dim_empreendimentos.primeira_aparicao IS NULL THEN EXCLUDED.primeira_aparicao
        WHEN EXCLUDED.primeira_aparicao IS NULL THEN dim_empreendimentos.primeira_aparicao
        ELSE LEAST(dim_empreendimentos.primeira_aparicao, EXCLUDED.primeira_aparicao)
    END,
    ultima_aparicao = CASE
        WHEN dim_empreendimentos.ultima_aparicao IS NULL THEN EXCLUDED.ultima_aparicao
        WHEN EXCLUDED.ultima_aparicao IS NULL THEN dim_empreendimentos.ultima_aparicao
        ELSE GREATEST(dim_empreendimentos.ultima_aparicao, EXCLUDED.ultima_aparicao)
    END,
    atualizado_em_utc = NOW()
"""

_CREATE_STAGING_FACT_SQL = """
CREATE TEMP TABLE _stg_fact_restricoes (
    ons_id TEXT NOT NULL,
    instante TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    estado_sigla CHAR(2) NOT NULL,
    usina_nome TEXT NOT NULL,
    ceg TEXT NOT NULL,
    duracao_horas DOUBLE PRECISION NOT NULL,
    geracao_mwmed DOUBLE PRECISION,
    geracao_limitada_mwmed DOUBLE PRECISION,
    disponibilidade_mwmed DOUBLE PRECISION,
    geracao_referencia_mwmed DOUBLE PRECISION,
    geracao_referencia_final_mwmed DOUBLE PRECISION,
    geracao_nao_realizada_apurada DOUBLE PRECISION,
    restricao_razao_codigo TEXT,
    restricao_origem_codigo TEXT,
    restricao_descricao TEXT,
    minutos_restricao_rel DOUBLE PRECISION,
    minutos_restricao_cnf DOUBLE PRECISION,
    minutos_restricao_ene DOUBLE PRECISION,
    minutos_restricao_total DOUBLE PRECISION,
    geracao_verificada_mwh DOUBLE PRECISION,
    geracao_referencia_final_mwh DOUBLE PRECISION,
    elegivel_geracao_verificada BOOLEAN NOT NULL,
    elegivel_referencia_final BOOLEAN NOT NULL,
    possui_restricao_classificada BOOLEAN NOT NULL,
    elegivel_gnra BOOLEAN NOT NULL,
    elegivel_enriquecimento_aneel BOOLEAN NOT NULL,
    execucao_id BIGINT NOT NULL,
    metodologia_versao TEXT NOT NULL
) ON COMMIT DROP
"""

_COPY_STAGING_FACT_SQL = (
    f"COPY _stg_fact_restricoes ({', '.join(_FACT_LOAD_COLUMNS)}) FROM STDIN"
)

_UPSERT_FACT_FROM_STAGING_SQL = f"""
INSERT INTO fact_restricoes (
    {', '.join(_FACT_LOAD_COLUMNS)},
    atualizado_em_utc
)
SELECT
    {', '.join(_FACT_LOAD_COLUMNS)},
    NOW()
FROM _stg_fact_restricoes
ON CONFLICT (ons_id, instante) DO UPDATE SET
    estado_sigla = EXCLUDED.estado_sigla,
    usina_nome = EXCLUDED.usina_nome,
    ceg = EXCLUDED.ceg,
    duracao_horas = EXCLUDED.duracao_horas,
    geracao_mwmed = EXCLUDED.geracao_mwmed,
    geracao_limitada_mwmed = EXCLUDED.geracao_limitada_mwmed,
    disponibilidade_mwmed = EXCLUDED.disponibilidade_mwmed,
    geracao_referencia_mwmed = EXCLUDED.geracao_referencia_mwmed,
    geracao_referencia_final_mwmed = EXCLUDED.geracao_referencia_final_mwmed,
    geracao_nao_realizada_apurada = EXCLUDED.geracao_nao_realizada_apurada,
    restricao_razao_codigo = EXCLUDED.restricao_razao_codigo,
    restricao_origem_codigo = EXCLUDED.restricao_origem_codigo,
    restricao_descricao = EXCLUDED.restricao_descricao,
    minutos_restricao_rel = EXCLUDED.minutos_restricao_rel,
    minutos_restricao_cnf = EXCLUDED.minutos_restricao_cnf,
    minutos_restricao_ene = EXCLUDED.minutos_restricao_ene,
    minutos_restricao_total = EXCLUDED.minutos_restricao_total,
    geracao_verificada_mwh = EXCLUDED.geracao_verificada_mwh,
    geracao_referencia_final_mwh = EXCLUDED.geracao_referencia_final_mwh,
    elegivel_geracao_verificada = EXCLUDED.elegivel_geracao_verificada,
    elegivel_referencia_final = EXCLUDED.elegivel_referencia_final,
    possui_restricao_classificada = EXCLUDED.possui_restricao_classificada,
    elegivel_gnra = EXCLUDED.elegivel_gnra,
    elegivel_enriquecimento_aneel = EXCLUDED.elegivel_enriquecimento_aneel,
    execucao_id = EXCLUDED.execucao_id,
    metodologia_versao = EXCLUDED.metodologia_versao,
    atualizado_em_utc = NOW()
"""

_DELETE_OBSOLETE_FACT_IN_PERIOD_SQL = """
DELETE FROM fact_restricoes AS f
WHERE f.estado_sigla = %s
  AND f.instante >= %s
  AND f.instante < %s
  AND NOT EXISTS (
      SELECT 1
      FROM _stg_fact_restricoes AS s
      WHERE s.ons_id = f.ons_id
        AND s.instante = f.instante
  )
"""

_MARK_ETL_COMPLETED_SQL = """
UPDATE etl_execucoes
SET status = 'concluida',
    linhas_carregadas = %s,
    carregado_em_utc = NOW()
WHERE execucao_id = %s
"""

_MARK_ETL_FAILED_SQL = """
UPDATE etl_execucoes
SET status = 'falha',
    mensagem_erro = %s,
    carregado_em_utc = NOW()
WHERE execucao_id = %s
"""


class DatabaseConfigError(ValueError):
    """Configuração de conexão PostgreSQL ausente ou inválida."""


class DatabaseSchemaError(ValueError):
    """Arquivo de esquema SQL ausente, inválido ou vazio."""


class DatabaseConnectionError(RuntimeError):
    """Falha de conexão ou execução DDL/SQL no PostgreSQL."""


class DatabaseLoadError(DatabaseConnectionError):
    """Falha ao carregar dados processados no PostgreSQL."""


class SchemaApplyReport(TypedDict):
    """Resumo auditável da aplicação do esquema PostgreSQL."""

    schema_path: str
    schema_sha256: str
    database_target: str
    source_env_var: str
    applied_at_utc: str


class DatabaseLoadReport(TypedDict):
    """Resumo auditável da carga idempotente de um mês no PostgreSQL."""

    execucao_id: int
    source: str
    state_code: str
    year: int
    month: int
    dim_rows_upserted: int
    fact_rows_upserted: int
    fact_rows_deleted: int
    database_target: str
    source_env_var: str
    metodologia_versao: str
    loaded_at_utc: str


def validate_postgres_url(
    raw_url: str,
    *,
    env_var_name: str = "DATABASE_URL",
) -> str:
    """Valida se a URL possui esquema PostgreSQL e host válidos.

    Args:
        raw_url: String de conexão informada.
        env_var_name: Nome da variável associada, usado apenas em mensagens de erro.

    Returns:
        URL normalizada (sem espaços nas extremidades).

    Raises:
        TypeError: Se ``raw_url`` não for ``str``.
        DatabaseConfigError: Se a URL estiver vazia, sem host ou com esquema inválido.
    """
    if not isinstance(raw_url, str):
        raise TypeError(f"{env_var_name} deve ser uma string.")

    candidate = raw_url.strip()
    if not candidate:
        raise DatabaseConfigError(f"{env_var_name} está vazia ou não foi configurada.")

    parsed = urlparse(candidate)
    if parsed.scheme.lower() not in VALID_POSTGRES_SCHEMES:
        raise DatabaseConfigError(
            f"{env_var_name} deve usar esquema 'postgresql://' ou 'postgres://'."
        )
    if not parsed.hostname:
        raise DatabaseConfigError(
            f"{env_var_name} não contém um hostname PostgreSQL válido."
        )
    return candidate


def mask_postgres_url(raw_url: str) -> str:
    """Mascara credenciais de uma URL PostgreSQL para uso seguro em logs e erros."""
    validated = validate_postgres_url(raw_url)
    parsed = urlparse(validated)

    host = parsed.hostname or ""
    if ":" in host:
        host = f"[{host}]"
    port_part = f":{parsed.port}" if parsed.port is not None else ""

    if parsed.username:
        user_part = f"{parsed.username}:***@" if parsed.password is not None else f"{parsed.username}@"
    else:
        user_part = ""

    netloc = f"{user_part}{host}{port_part}"
    safe_query = urlencode(
        [
            (key, "***" if key.casefold() == "password" else value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        ]
    )
    return urlunparse(
        (parsed.scheme, netloc, parsed.path, parsed.params, safe_query, parsed.fragment)
    )


def load_dotenv_file(env_path: Path | str = DEFAULT_ENV_FILE) -> dict[str, str]:
    """Lê pares ``CHAVE=VALOR`` de um arquivo ``.env`` local sem mutar ``os.environ``.

    Linhas em branco e comentários iniciados por ``#`` são ignorados.
    """
    if isinstance(env_path, str):
        if not env_path.strip():
            raise DatabaseConfigError("env_path não pode ser uma string vazia.")
        path = Path(env_path.strip())
    elif isinstance(env_path, Path):
        path = env_path
    else:
        raise TypeError("env_path deve ser um objeto Path ou string.")

    if not path.exists():
        raise FileNotFoundError(f"Arquivo .env não encontrado: {path}.")
    if not path.is_file():
        raise DatabaseConfigError(f"env_path não aponta para um arquivo: {path}.")

    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            raise DatabaseConfigError(
                f"Linha {line_number} inválida em {path}: esperado formato CHAVE=VALOR."
            )
        key, raw_value = line.split("=", 1)
        clean_key = key.strip()
        if not clean_key:
            raise DatabaseConfigError(
                f"Linha {line_number} inválida em {path}: nome de variável vazio."
            )
        clean_value = raw_value.strip()
        if len(clean_value) >= 2 and clean_value[0] == clean_value[-1] and clean_value[0] in {"'", '"'}:
            clean_value = clean_value[1:-1]
        values[clean_key] = clean_value

    return values


def resolve_database_url(
    *,
    prefer_direct: bool = True,
    env: Mapping[str, str] | None = None,
    env_file: Path | str | None = DEFAULT_ENV_FILE,
) -> tuple[str, str]:
    """Resolve e valida a string de conexão PostgreSQL a partir do ambiente ou ``.env``.

    Quando ``prefer_direct=True`` (migrações e ETL), prioriza ``DIRECT_DATABASE_URL``
    e usa ``DATABASE_URL`` como fallback. Quando ``prefer_direct=False`` (API pooled),
    exige ``DATABASE_URL``.

    Returns:
        Tupla ``(url_validada, nome_da_variavel)``.
    """
    if not isinstance(prefer_direct, bool):
        raise TypeError("prefer_direct deve ser um booleano.")

    source_env: Mapping[str, str] = os.environ if env is None else env
    dotenv_values: dict[str, str] = {}
    if env_file is not None:
        env_file_path = Path(env_file) if isinstance(env_file, str) else env_file
        if not isinstance(env_file_path, Path):
            raise TypeError("env_file deve ser Path, string ou None.")
        if env_file_path.exists():
            dotenv_values = load_dotenv_file(env_file_path)

    candidate_vars = (
        ("DIRECT_DATABASE_URL", "DATABASE_URL") if prefer_direct else ("DATABASE_URL",)
    )

    for var_name in candidate_vars:
        raw_value = source_env.get(var_name)
        if raw_value is None or not raw_value.strip():
            raw_value = dotenv_values.get(var_name)
        if raw_value is not None and raw_value.strip():
            return validate_postgres_url(raw_value, env_var_name=var_name), var_name

    expected = " ou ".join(candidate_vars)
    raise DatabaseConfigError(
        f"Nenhuma string de conexão configurada. Defina {expected} no ambiente ou em .env."
    )


def load_schema_sql(schema_path: Path | str = DEFAULT_SCHEMA_PATH) -> tuple[str, str, Path]:
    """Carrega o conteúdo SQL de ``sql/schema.sql`` e calcula seu hash SHA-256.

    Returns:
        Tupla ``(sql_text, sha256_uppercase, resolved_path)``.
    """
    if isinstance(schema_path, str):
        if not schema_path.strip():
            raise DatabaseSchemaError("schema_path não pode ser uma string vazia.")
        path = Path(schema_path.strip())
    elif isinstance(schema_path, Path):
        path = schema_path
    else:
        raise TypeError("schema_path deve ser um objeto Path ou string.")

    if not path.exists():
        raise DatabaseSchemaError(f"Arquivo de esquema SQL não encontrado: {path}.")
    if not path.is_file():
        raise DatabaseSchemaError(f"schema_path não aponta para um arquivo: {path}.")

    sql_text = path.read_text(encoding="utf-8")
    if not sql_text.strip():
        raise DatabaseSchemaError(f"O arquivo de esquema SQL está vazio: {path}.")

    sha256_hex = hashlib.sha256(sql_text.encode("utf-8")).hexdigest().upper()
    return sql_text, sha256_hex, path


def _validate_connect_timeout(connect_timeout: int) -> int:
    if isinstance(connect_timeout, bool) or not isinstance(connect_timeout, int):
        raise TypeError("connect_timeout deve ser um inteiro positivo.")
    if connect_timeout <= 0:
        raise ValueError("connect_timeout deve ser maior que zero.")
    return connect_timeout


def _sanitize_postgres_error_message(
    exc: BaseException,
    *,
    raw_url: str,
    masked_url: str,
) -> str:
    """Remove a DSN original e qualquer senha do texto de erro do psycopg."""
    message = str(exc)
    if not message:
        return type(exc).__name__

    sanitized = message.replace(raw_url, masked_url)
    parsed = urlparse(raw_url)
    if parsed.password:
        password_variants = {
            parsed.password,
            unquote(parsed.password),
            quote(parsed.password, safe=""),
        }
        for variant in sorted(password_variants, key=len, reverse=True):
            if variant:
                sanitized = sanitized.replace(variant, "***")

    sanitized = _POSTGRES_URL_CREDENTIAL_PATTERN.sub(r"\1***\3", sanitized)
    sanitized = _LIBPQ_PASSWORD_PATTERN.sub(r"\1***", sanitized)
    return f"{type(exc).__name__}: {sanitized}"


def apply_schema(
    *,
    database_url: str | None = None,
    schema_path: Path | str = DEFAULT_SCHEMA_PATH,
    connect_timeout: int = DEFAULT_CONNECT_TIMEOUT_SECONDS,
    connect_fn: Callable[..., Any] | None = None,
) -> SchemaApplyReport:
    """Aplica o DDL idempotente de ``sql/schema.sql`` no PostgreSQL.

    Executa todo o script dentro de uma transação: em caso de erro de banco,
    desfaz a transação e relança ``DatabaseConnectionError`` sem expor senhas.
    """
    timeout = _validate_connect_timeout(connect_timeout)

    if database_url is None:
        resolved_url, source_var = resolve_database_url(prefer_direct=True)
    else:
        resolved_url = validate_postgres_url(database_url, env_var_name="database_url")
        source_var = "explicit"

    sql_text, schema_sha256, resolved_schema_path = load_schema_sql(schema_path)
    masked_target = mask_postgres_url(resolved_url)
    connector = psycopg.connect if connect_fn is None else connect_fn

    try:
        with connector(resolved_url, connect_timeout=timeout) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql_text)
            conn.commit()
    except psycopg.Error as exc:
        safe_detail = _sanitize_postgres_error_message(
            exc,
            raw_url=resolved_url,
            masked_url=masked_target,
        )
        raise DatabaseConnectionError(
            f"Falha ao aplicar esquema '{resolved_schema_path.as_posix()}' em "
            f"{masked_target}: {safe_detail}"
        ) from None

    return {
        "schema_path": resolved_schema_path.as_posix(),
        "schema_sha256": schema_sha256,
        "database_target": masked_target,
        "source_env_var": source_var,
        "applied_at_utc": datetime.now(UTC).isoformat(),
    }


def check_database_connection(
    *,
    database_url: str | None = None,
    prefer_direct: bool = False,
    connect_timeout: int = DEFAULT_CONNECT_TIMEOUT_SECONDS,
    connect_fn: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Valida a conectividade real com o PostgreSQL executando uma consulta mínima."""
    timeout = _validate_connect_timeout(connect_timeout)

    if database_url is None:
        resolved_url, source_var = resolve_database_url(prefer_direct=prefer_direct)
    else:
        resolved_url = validate_postgres_url(database_url, env_var_name="database_url")
        source_var = "explicit"

    masked_target = mask_postgres_url(resolved_url)
    connector = psycopg.connect if connect_fn is None else connect_fn

    try:
        with (
            connector(resolved_url, connect_timeout=timeout) as conn,
            conn.cursor() as cursor,
        ):
            cursor.execute("SELECT current_database(), version()")
            row = cursor.fetchone()
    except psycopg.Error as exc:
        safe_detail = _sanitize_postgres_error_message(
            exc,
            raw_url=resolved_url,
            masked_url=masked_target,
        )
        raise DatabaseConnectionError(
            f"Falha ao conectar no PostgreSQL ({masked_target}): {safe_detail}"
        ) from None

    if not row or len(row) < 2:
        raise DatabaseConnectionError(
            f"Resposta inesperada ao verificar conexão em {masked_target}."
        )

    return {
        "status": "ok",
        "database_name": str(row[0]),
        "server_version": str(row[1]),
        "database_target": masked_target,
        "source_env_var": source_var,
        "checked_at_utc": datetime.now(UTC).isoformat(),
    }


def _is_missing_value(value: Any) -> bool:
    """Identifica valores ausentes (None, NaN, pd.NA, pd.NaT) sem importar pandas."""
    if value is None:
        return True
    type_name = type(value).__name__
    if type_name in {"NAType", "NaTType"}:
        return True
    if isinstance(value, float):
        return math.isnan(value)
    # Trata escalares flutuantes do NumPy (ex.: numpy.float64)
    if hasattr(value, "item") and not isinstance(value, (bytes, bytearray, str)):
        try:
            scalar = value.item()
        except (TypeError, ValueError):
            return False
        if isinstance(scalar, float):
            return math.isnan(scalar)
    return False


def _to_optional_str(value: Any, *, field_name: str) -> str | None:
    if _is_missing_value(value):
        return None
    if not isinstance(value, str):
        raise TypeError(
            f"Coluna '{field_name}' esperava texto ou nulo, recebeu {type(value).__name__}."
        )
    return value


def _to_required_str(value: Any, *, field_name: str) -> str:
    text = _to_optional_str(value, field_name=field_name)
    if text is None or not text.strip():
        raise ValueError(f"Coluna obrigatória '{field_name}' contém valor nulo ou vazio.")
    return text.strip()


def _to_optional_float(value: Any, *, field_name: str) -> float | None:
    if _is_missing_value(value):
        return None
    if isinstance(value, bool):
        raise TypeError(f"Coluna numérica '{field_name}' recebeu booleano em vez de número.")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Coluna numérica '{field_name}' contém valor inválido: {value!r}."
        ) from exc
    if not math.isfinite(numeric):
        raise ValueError(
            f"Coluna numérica '{field_name}' contém valor não finito: {value!r}."
        )
    return numeric


def _to_required_positive_float(value: Any, *, field_name: str) -> float:
    numeric = _to_optional_float(value, field_name=field_name)
    if numeric is None or numeric <= 0:
        raise ValueError(
            f"Coluna '{field_name}' deve ser um número estritamente positivo; recebido {value!r}."
        )
    return numeric


def _to_required_bool(value: Any, *, field_name: str) -> bool:
    if _is_missing_value(value):
        raise ValueError(f"Coluna booleana obrigatória '{field_name}' contém valor nulo.")
    if isinstance(value, bool):
        return value
    if hasattr(value, "item") and not isinstance(value, (bytes, bytearray, str)):
        scalar = value.item()
        if isinstance(scalar, bool):
            return scalar
    raise TypeError(
        f"Coluna booleana '{field_name}' esperava bool, recebeu {type(value).__name__}."
    )


def _to_required_naive_datetime(value: Any, *, field_name: str) -> datetime:
    if _is_missing_value(value):
        raise ValueError(f"Coluna temporal obrigatória '{field_name}' contém valor nulo.")
    if hasattr(value, "to_pydatetime"):
        dt_value = value.to_pydatetime()
    elif isinstance(value, datetime):
        dt_value = value
    elif isinstance(value, str):
        try:
            dt_value = datetime.fromisoformat(value.strip())
        except ValueError as exc:
            raise ValueError(
                f"Coluna temporal '{field_name}' contém texto inválido: {value!r}."
            ) from exc
    else:
        raise ValueError(
            f"Coluna temporal '{field_name}' esperava datetime, recebeu {type(value).__name__}."
        )
    if dt_value.tzinfo is not None:
        raise ValueError(
            f"Coluna '{field_name}' deve preservar horário naive oficial do ONS (sem tzinfo)."
        )
    return dt_value


def _validate_load_metadata(
    *,
    source: str,
    state_code: str,
    year: int,
    month: int,
    raw_file_name: str,
    raw_file_sha256: str,
    parquet_file_name: str | None,
    parquet_file_sha256: str | None,
    processed_at_utc: str | datetime,
    collected_at_utc: str | datetime | None,
    input_rows: int,
    output_rows: int,
    excluded_by_state_rows: int,
    dropped_duplicate_rows: int,
    metodologia_versao: str,
) -> dict[str, Any]:
    if not isinstance(source, str) or not source.strip():
        raise ValueError("source deve ser uma string não vazia (ex.: 'eolica').")
    if not isinstance(state_code, str) or not _STATE_CODE_PATTERN.fullmatch(
        state_code.strip().upper()
    ):
        raise ValueError("state_code deve ser uma sigla de UF com 2 letras (ex.: 'CE').")
    if isinstance(year, bool) or not isinstance(year, int) or not (1000 <= year <= 9999):
        raise ValueError("year deve ser um inteiro de 4 dígitos (1000 a 9999).")
    if isinstance(month, bool) or not isinstance(month, int) or not (1 <= month <= 12):
        raise ValueError("month deve ser um inteiro entre 1 e 12.")
    if not isinstance(raw_file_name, str) or not raw_file_name.strip():
        raise ValueError("raw_file_name deve ser uma string não vazia.")
    if not isinstance(raw_file_sha256, str) or not _SHA256_PATTERN.fullmatch(
        raw_file_sha256.strip()
    ):
        raise ValueError("raw_file_sha256 deve ser um hash SHA-256 hexadecimal de 64 caracteres.")
    if parquet_file_sha256 is not None and (
        not isinstance(parquet_file_sha256, str)
        or not _SHA256_PATTERN.fullmatch(parquet_file_sha256.strip())
    ):
        raise ValueError(
            "parquet_file_sha256 deve ser None ou um hash SHA-256 hexadecimal de 64 caracteres."
        )
    if not isinstance(metodologia_versao, str) or not metodologia_versao.strip():
        raise ValueError("metodologia_versao deve ser uma string não vazia.")

    for count_name, count_value in (
        ("input_rows", input_rows),
        ("output_rows", output_rows),
        ("excluded_by_state_rows", excluded_by_state_rows),
        ("dropped_duplicate_rows", dropped_duplicate_rows),
    ):
        if isinstance(count_value, bool) or not isinstance(count_value, int) or count_value < 0:
            raise ValueError(f"{count_name} deve ser um inteiro não negativo.")

    def _parse_utc_ts(raw_ts: str | datetime, name: str) -> datetime:
        if isinstance(raw_ts, datetime):
            parsed = raw_ts
        elif isinstance(raw_ts, str) and raw_ts.strip():
            normalized = raw_ts.strip().replace("Z", "+00:00")
            try:
                parsed = datetime.fromisoformat(normalized)
            except ValueError as exc:
                raise ValueError(f"{name} não é um timestamp ISO válido: {raw_ts!r}.") from exc
        else:
            raise ValueError(f"{name} deve ser datetime ou string ISO não vazia.")
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed

    parsed_processed_at = _parse_utc_ts(processed_at_utc, "processed_at_utc")
    parsed_collected_at = (
        None if collected_at_utc is None else _parse_utc_ts(collected_at_utc, "collected_at_utc")
    )

    return {
        "source": source.strip().lower(),
        "state_code": state_code.strip().upper(),
        "year": year,
        "month": month,
        "raw_file_name": raw_file_name.strip(),
        "raw_file_sha256": raw_file_sha256.strip().upper(),
        "parquet_file_name": None if parquet_file_name is None else parquet_file_name.strip(),
        "parquet_file_sha256": (
            None if parquet_file_sha256 is None else parquet_file_sha256.strip().upper()
        ),
        "processed_at_utc": parsed_processed_at,
        "collected_at_utc": parsed_collected_at,
        "metodologia_versao": metodologia_versao.strip(),
    }


def _month_period_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    """Retorna o intervalo semiaberto ``[início_do_mês, início_do_mês_seguinte)`` naive."""
    period_start = datetime(year, month, 1)
    if month == 12:
        period_end = datetime(year + 1, 1, 1)
    else:
        period_end = datetime(year, month + 1, 1)
    return period_start, period_end


def _prepare_load_rows(
    df: Any,
    *,
    expected_state_code: str,
    period_start: datetime,
    period_end: datetime,
    execucao_id: int,
    metodologia_versao: str,
) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]]]:
    """Valida o DataFrame tratado e prepara tuplas de dimensão e fato preservando NULL."""
    if not hasattr(df, "columns") or not hasattr(df, "itertuples"):
        raise TypeError("df deve ser um DataFrame tabular com colunas e itertuples().")

    columns = set(df.columns)
    missing_cols = [col for col in REQUIRED_PROCESSED_COLUMNS if col not in columns]
    if missing_cols:
        raise ValueError(
            "DataFrame processado sem colunas obrigatórias para carga: "
            + ", ".join(missing_cols)
        )

    if len(df) == 0:
        raise ValueError("DataFrame processado está vazio; não há registros para carregar.")

    selected = df.loc[:, list(REQUIRED_PROCESSED_COLUMNS)]

    seen_keys: set[tuple[str, datetime]] = set()
    dim_by_ons_id: dict[str, dict[str, Any]] = {}
    fact_rows: list[tuple[Any, ...]] = []

    for row in selected.itertuples(index=False, name=None):
        (
            subsistema_id,
            subsistema_nome,
            estado_sigla,
            estado_nome,
            usina_nome,
            ons_id,
            ceg,
            instante,
            geracao_mwmed,
            geracao_limitada_mwmed,
            disponibilidade_mwmed,
            geracao_referencia_mwmed,
            geracao_referencia_final_mwmed,
            restricao_razao_codigo,
            restricao_origem_codigo,
            restricao_descricao,
            ponto_conexao_id,
            ponto_conexao_nome,
            agente_operador_nome,
            geracao_nao_realizada_apurada,
            minutos_restricao_rel,
            minutos_restricao_cnf,
            minutos_restricao_ene,
            minutos_restricao_total,
            elegivel_geracao_verificada,
            elegivel_referencia_final,
            possui_restricao_classificada,
            elegivel_gnra,
            elegivel_enriquecimento_aneel,
            duracao_horas,
            geracao_verificada_mwh,
            geracao_referencia_final_mwh,
        ) = row

        clean_ons_id = _to_required_str(ons_id, field_name="ons_id")
        clean_instante = _to_required_naive_datetime(instante, field_name="instante")
        if not (period_start <= clean_instante < period_end):
            raise ValueError(
                f"Registro com instante={clean_instante.isoformat()} está fora do período "
                f"esperado [{period_start.isoformat()}, {period_end.isoformat()}) para "
                f"ons_id={clean_ons_id!r}."
            )
        clean_estado = _to_required_str(estado_sigla, field_name="estado_sigla").upper()
        if clean_estado != expected_state_code:
            raise ValueError(
                f"Registro com estado_sigla={clean_estado!r} diverge do estado esperado "
                f"{expected_state_code!r} para ons_id={clean_ons_id!r}."
            )

        key = (clean_ons_id, clean_instante)
        if key in seen_keys:
            raise ValueError(
                f"Chave duplicada (ons_id={clean_ons_id!r}, instante={clean_instante.isoformat()}) "
                "encontrada no lote antes da carga no PostgreSQL."
            )
        seen_keys.add(key)

        clean_usina = _to_required_str(usina_nome, field_name="usina_nome")
        clean_ceg = _to_required_str(ceg, field_name="ceg")
        clean_elegivel_aneel = _to_required_bool(
            elegivel_enriquecimento_aneel,
            field_name="elegivel_enriquecimento_aneel",
        )
        tipo_identificador = (
            "usina_com_ceg" if clean_elegivel_aneel else "conjunto_sem_ceg"
        )

        clean_subsistema_id = _to_optional_str(subsistema_id, field_name="subsistema_id")
        clean_subsistema_nome = _to_optional_str(subsistema_nome, field_name="subsistema_nome")
        clean_estado_nome = _to_optional_str(estado_nome, field_name="estado_nome")
        clean_ponto_id = _to_optional_str(ponto_conexao_id, field_name="ponto_conexao_id")
        clean_ponto_nome = _to_optional_str(ponto_conexao_nome, field_name="ponto_conexao_nome")
        clean_agente = _to_optional_str(agente_operador_nome, field_name="agente_operador_nome")

        dim_entry = dim_by_ons_id.get(clean_ons_id)
        if dim_entry is None:
            dim_by_ons_id[clean_ons_id] = {
                "ons_id": clean_ons_id,
                "usina_nome": clean_usina,
                "estado_sigla": clean_estado,
                "estado_nome": clean_estado_nome,
                "subsistema_id": clean_subsistema_id,
                "subsistema_nome": clean_subsistema_nome,
                "ceg": clean_ceg,
                "tipo_identificador": tipo_identificador,
                "elegivel_enriquecimento_aneel": clean_elegivel_aneel,
                "ponto_conexao_id": clean_ponto_id,
                "ponto_conexao_nome": clean_ponto_nome,
                "agente_operador_nome": clean_agente,
                "primeira_aparicao": clean_instante,
                "ultima_aparicao": clean_instante,
            }
        else:
            dim_entry["primeira_aparicao"] = min(
                dim_entry["primeira_aparicao"],
                clean_instante,
            )
            if clean_instante >= dim_entry["ultima_aparicao"]:
                dim_entry["ultima_aparicao"] = clean_instante
                dim_entry["usina_nome"] = clean_usina
                dim_entry["estado_nome"] = clean_estado_nome
                dim_entry["subsistema_id"] = clean_subsistema_id
                dim_entry["subsistema_nome"] = clean_subsistema_nome
                dim_entry["ceg"] = clean_ceg
                dim_entry["tipo_identificador"] = tipo_identificador
                dim_entry["elegivel_enriquecimento_aneel"] = clean_elegivel_aneel
                dim_entry["ponto_conexao_id"] = clean_ponto_id
                dim_entry["ponto_conexao_nome"] = clean_ponto_nome
                dim_entry["agente_operador_nome"] = clean_agente

        fact_rows.append(
            (
                clean_ons_id,
                clean_instante,
                clean_estado,
                clean_usina,
                clean_ceg,
                _to_required_positive_float(duracao_horas, field_name="duracao_horas"),
                _to_optional_float(geracao_mwmed, field_name="geracao_mwmed"),
                _to_optional_float(geracao_limitada_mwmed, field_name="geracao_limitada_mwmed"),
                _to_optional_float(disponibilidade_mwmed, field_name="disponibilidade_mwmed"),
                _to_optional_float(
                    geracao_referencia_mwmed, field_name="geracao_referencia_mwmed"
                ),
                _to_optional_float(
                    geracao_referencia_final_mwmed,
                    field_name="geracao_referencia_final_mwmed",
                ),
                _to_optional_float(
                    geracao_nao_realizada_apurada,
                    field_name="geracao_nao_realizada_apurada",
                ),
                _to_optional_str(
                    restricao_razao_codigo, field_name="restricao_razao_codigo"
                ),
                _to_optional_str(
                    restricao_origem_codigo, field_name="restricao_origem_codigo"
                ),
                _to_optional_str(restricao_descricao, field_name="restricao_descricao"),
                _to_optional_float(
                    minutos_restricao_rel, field_name="minutos_restricao_rel"
                ),
                _to_optional_float(
                    minutos_restricao_cnf, field_name="minutos_restricao_cnf"
                ),
                _to_optional_float(
                    minutos_restricao_ene, field_name="minutos_restricao_ene"
                ),
                _to_optional_float(
                    minutos_restricao_total, field_name="minutos_restricao_total"
                ),
                _to_optional_float(
                    geracao_verificada_mwh, field_name="geracao_verificada_mwh"
                ),
                _to_optional_float(
                    geracao_referencia_final_mwh,
                    field_name="geracao_referencia_final_mwh",
                ),
                _to_required_bool(
                    elegivel_geracao_verificada,
                    field_name="elegivel_geracao_verificada",
                ),
                _to_required_bool(
                    elegivel_referencia_final,
                    field_name="elegivel_referencia_final",
                ),
                _to_required_bool(
                    possui_restricao_classificada,
                    field_name="possui_restricao_classificada",
                ),
                _to_required_bool(elegivel_gnra, field_name="elegivel_gnra"),
                clean_elegivel_aneel,
                execucao_id,
                metodologia_versao,
            )
        )

    dim_rows = [
        (
            entry["ons_id"],
            entry["usina_nome"],
            entry["estado_sigla"],
            entry["estado_nome"],
            entry["subsistema_id"],
            entry["subsistema_nome"],
            entry["ceg"],
            entry["tipo_identificador"],
            entry["elegivel_enriquecimento_aneel"],
            entry["ponto_conexao_id"],
            entry["ponto_conexao_nome"],
            entry["agente_operador_nome"],
            entry["primeira_aparicao"],
            entry["ultima_aparicao"],
        )
        for entry in sorted(dim_by_ons_id.values(), key=lambda item: item["ons_id"])
    ]

    return dim_rows, fact_rows


def load_dataframe_to_postgres(
    df: Any,
    *,
    source: str,
    state_code: str,
    year: int,
    month: int,
    raw_file_name: str,
    raw_file_sha256: str,
    processed_at_utc: str | datetime,
    input_rows: int,
    output_rows: int,
    excluded_by_state_rows: int = 0,
    dropped_duplicate_rows: int = 0,
    parquet_file_name: str | None = None,
    parquet_file_sha256: str | None = None,
    source_url: str | None = None,
    collected_at_utc: str | datetime | None = None,
    gnra_unit_status: str = GNRA_UNIT_STATUS_DEFAULT,
    metodologia_versao: str = METHODOLOGY_VERSION,
    quality_report: Mapping[str, Any] | None = None,
    database_url: str | None = None,
    connect_timeout: int = DEFAULT_CONNECT_TIMEOUT_SECONDS,
    connect_fn: Callable[..., Any] | None = None,
) -> DatabaseLoadReport:
    """Carrega um DataFrame mensal tratado no PostgreSQL de forma idempotente e auditável.

    Executa UPSERT em ``dim_empreendimentos`` e ``fact_restricoes`` (via tabela
    temporária + ``COPY`` + ``ON CONFLICT (ons_id, instante) DO UPDATE``),
    registrando linhagem e status em ``etl_execucoes``. Reexecutar o mesmo mês
    atualiza os registros existentes sem duplicar linhas.
    """
    timeout = _validate_connect_timeout(connect_timeout)
    meta = _validate_load_metadata(
        source=source,
        state_code=state_code,
        year=year,
        month=month,
        raw_file_name=raw_file_name,
        raw_file_sha256=raw_file_sha256,
        parquet_file_name=parquet_file_name,
        parquet_file_sha256=parquet_file_sha256,
        processed_at_utc=processed_at_utc,
        collected_at_utc=collected_at_utc,
        input_rows=input_rows,
        output_rows=output_rows,
        excluded_by_state_rows=excluded_by_state_rows,
        dropped_duplicate_rows=dropped_duplicate_rows,
        metodologia_versao=metodologia_versao,
    )

    period_start, period_end = _month_period_bounds(meta["year"], meta["month"])

    # Valida estrutura do DataFrame antes de abrir conexão ou gravar etl_execucoes.
    dim_rows, preliminary_fact_rows = _prepare_load_rows(
        df,
        expected_state_code=meta["state_code"],
        period_start=period_start,
        period_end=period_end,
        execucao_id=0,
        metodologia_versao=meta["metodologia_versao"],
    )

    if database_url is None:
        resolved_url, source_var = resolve_database_url(prefer_direct=True)
    else:
        resolved_url = validate_postgres_url(database_url, env_var_name="database_url")
        source_var = "explicit"

    masked_target = mask_postgres_url(resolved_url)
    connector = psycopg.connect if connect_fn is None else connect_fn
    quality_json = (
        None
        if quality_report is None
        else json.dumps(dict(quality_report), ensure_ascii=False)
    )

    execucao_id: int | None = None
    try:
        with connector(resolved_url, connect_timeout=timeout) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    _INSERT_ETL_EXECUTION_SQL,
                    (
                        meta["source"],
                        meta["state_code"],
                        meta["year"],
                        meta["month"],
                        meta["raw_file_name"],
                        meta["raw_file_sha256"],
                        meta["parquet_file_name"],
                        meta["parquet_file_sha256"],
                        source_url,
                        meta["collected_at_utc"],
                        meta["processed_at_utc"],
                        input_rows,
                        output_rows,
                        excluded_by_state_rows,
                        dropped_duplicate_rows,
                        gnra_unit_status,
                        meta["metodologia_versao"],
                        quality_json,
                    ),
                )
                inserted = cursor.fetchone()
                if not inserted or inserted[0] is None:
                    raise DatabaseLoadError(
                        "PostgreSQL não retornou execucao_id ao registrar início em etl_execucoes."
                    )
                execucao_id = int(inserted[0])
            conn.commit()

            fact_rows = [
                (*row[:-2], execucao_id, meta["metodologia_versao"])
                for row in preliminary_fact_rows
            ]

            fact_rows_deleted = 0
            try:
                with conn.cursor() as cursor:
                    cursor.executemany(_UPSERT_DIM_EMPREENDIMENTOS_SQL, dim_rows)
                    cursor.execute(_CREATE_STAGING_FACT_SQL)
                    with cursor.copy(_COPY_STAGING_FACT_SQL) as copy:
                        for fact_row in fact_rows:
                            copy.write_row(fact_row)
                    cursor.execute(_UPSERT_FACT_FROM_STAGING_SQL)
                    cursor.execute(
                        _DELETE_OBSOLETE_FACT_IN_PERIOD_SQL,
                        (meta["state_code"], period_start, period_end),
                    )
                    raw_rowcount = getattr(cursor, "rowcount", 0)
                    fact_rows_deleted = (
                        raw_rowcount
                        if isinstance(raw_rowcount, int) and raw_rowcount > 0
                        else 0
                    )
                    cursor.execute(
                        _MARK_ETL_COMPLETED_SQL,
                        (len(fact_rows), execucao_id),
                    )
                conn.commit()
            except psycopg.Error as exc:
                conn.rollback()
                safe_detail = _sanitize_postgres_error_message(
                    exc,
                    raw_url=resolved_url,
                    masked_url=masked_target,
                )
                status_update_note = ""
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            _MARK_ETL_FAILED_SQL,
                            (safe_detail[:2000], execucao_id),
                        )
                    conn.commit()
                except psycopg.Error as status_exc:
                    safe_status_detail = _sanitize_postgres_error_message(
                        status_exc,
                        raw_url=resolved_url,
                        masked_url=masked_target,
                    )
                    rollback_note = ""
                    try:
                        conn.rollback()
                    except psycopg.Error as rollback_exc:
                        safe_rollback_detail = _sanitize_postgres_error_message(
                            rollback_exc,
                            raw_url=resolved_url,
                            masked_url=masked_target,
                        )
                        rollback_note = f" (rollback também falhou: {safe_rollback_detail})"
                    _logger.error(
                        "Falha ao atualizar status='falha' em etl_execucoes (execucao_id=%s): %s%s",
                        execucao_id,
                        safe_status_detail,
                        rollback_note,
                    )
                    status_update_note = (
                        " Adicionalmente, não foi possível atualizar status='falha' em "
                        f"etl_execucoes (registro permanece como 'iniciada'): "
                        f"{safe_status_detail}{rollback_note}"
                    )
                raise DatabaseLoadError(
                    f"Falha ao carregar {meta['state_code']} {meta['year']:04d}-{meta['month']:02d} "
                    f"em {masked_target} (execucao_id={execucao_id}): "
                    f"{safe_detail}{status_update_note}"
                ) from None
    except DatabaseLoadError:
        raise
    except psycopg.Error as exc:
        safe_detail = _sanitize_postgres_error_message(
            exc,
            raw_url=resolved_url,
            masked_url=masked_target,
        )
        raise DatabaseLoadError(
            f"Falha de conexão/registro em etl_execucoes para {masked_target}: {safe_detail}"
        ) from None

    return {
        "execucao_id": execucao_id,
        "source": meta["source"],
        "state_code": meta["state_code"],
        "year": meta["year"],
        "month": meta["month"],
        "dim_rows_upserted": len(dim_rows),
        "fact_rows_upserted": len(preliminary_fact_rows),
        "fact_rows_deleted": fact_rows_deleted,
        "database_target": masked_target,
        "source_env_var": source_var,
        "metodologia_versao": meta["metodologia_versao"],
        "loaded_at_utc": datetime.now(UTC).isoformat(),
    }


def load_processed_parquet(
    parquet_path: Path | str,
    *,
    quality_report_path: Path | str | None = None,
    source: str = "eolica",
    source_url: str | None = None,
    collected_at_utc: str | datetime | None = None,
    database_url: str | None = None,
    connect_timeout: int = DEFAULT_CONNECT_TIMEOUT_SECONDS,
    connect_fn: Callable[..., Any] | None = None,
) -> DatabaseLoadReport:
    """Lê um Parquet tratado e seu ``.quality_report.json`` e carrega no PostgreSQL."""
    if isinstance(parquet_path, str):
        if not parquet_path.strip():
            raise ValueError("parquet_path não pode ser uma string vazia.")
        resolved_parquet = Path(parquet_path.strip())
    elif isinstance(parquet_path, Path):
        resolved_parquet = parquet_path
    else:
        raise TypeError("parquet_path deve ser Path ou string.")

    if not resolved_parquet.exists() or not resolved_parquet.is_file():
        raise FileNotFoundError(f"Arquivo Parquet tratado não encontrado: {resolved_parquet}.")

    if quality_report_path is None:
        resolved_report_path = Path(f"{resolved_parquet}.quality_report.json")
    elif isinstance(quality_report_path, str):
        if not quality_report_path.strip():
            raise ValueError("quality_report_path não pode ser uma string vazia.")
        resolved_report_path = Path(quality_report_path.strip())
    elif isinstance(quality_report_path, Path):
        resolved_report_path = quality_report_path
    else:
        raise TypeError("quality_report_path deve ser Path, string ou None.")

    if not resolved_report_path.exists() or not resolved_report_path.is_file():
        raise FileNotFoundError(
            f"Relatório de qualidade associado não encontrado: {resolved_report_path}."
        )

    try:
        quality_report = json.loads(resolved_report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Relatório de qualidade JSON inválido em {resolved_report_path}: {exc}"
        ) from exc

    if not isinstance(quality_report, dict):
        raise TypeError(
            f"Relatório de qualidade em {resolved_report_path} deve ser um objeto JSON."
        )

    required_report_keys = (
        "source_file",
        "source_sha256",
        "target_state",
        "expected_year",
        "expected_month",
        "processed_at_utc",
        "input_rows",
        "output_rows",
    )
    missing_keys = [key for key in required_report_keys if key not in quality_report]
    if missing_keys:
        raise ValueError(
            f"Relatório de qualidade em {resolved_report_path} sem campos obrigatórios: "
            + ", ".join(missing_keys)
        )

    import pandas as pd

    df = pd.read_parquet(resolved_parquet)
    energy_report = quality_report.get("energy_report")
    gnra_status = (
        energy_report.get("gnra_unit_status", GNRA_UNIT_STATUS_DEFAULT)
        if isinstance(energy_report, dict)
        else GNRA_UNIT_STATUS_DEFAULT
    )

    return load_dataframe_to_postgres(
        df,
        source=source,
        state_code=str(quality_report["target_state"]),
        year=int(quality_report["expected_year"]),
        month=int(quality_report["expected_month"]),
        raw_file_name=Path(str(quality_report["source_file"])).name,
        raw_file_sha256=str(quality_report["source_sha256"]),
        parquet_file_name=resolved_parquet.name,
        parquet_file_sha256=quality_report.get("output_parquet_sha256"),
        source_url=source_url,
        collected_at_utc=collected_at_utc,
        processed_at_utc=str(quality_report["processed_at_utc"]),
        input_rows=int(quality_report["input_rows"]),
        output_rows=int(quality_report["output_rows"]),
        excluded_by_state_rows=int(quality_report.get("excluded_by_state_rows", 0)),
        dropped_duplicate_rows=int(quality_report.get("dropped_exact_duplicate_rows", 0)),
        gnra_unit_status=str(gnra_status),
        quality_report=quality_report,
        database_url=database_url,
        connect_timeout=connect_timeout,
        connect_fn=connect_fn,
    )


def build_argument_parser() -> argparse.ArgumentParser:
    """Constrói o parser CLI para ``python -m src.database``."""
    parser = argparse.ArgumentParser(
        prog="python -m src.database",
        description=(
            "Gerencia verificação de conexão e aplicação idempotente do esquema "
            "PostgreSQL (Neon / Vercel Storage)."
        ),
    )
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        "--init-schema",
        action="store_true",
        help="Aplica sql/schema.sql de forma idempotente usando DIRECT_DATABASE_URL/DATABASE_URL.",
    )
    action_group.add_argument(
        "--check-connection",
        action="store_true",
        help="Testa conectividade real com o PostgreSQL usando DATABASE_URL.",
    )
    parser.add_argument(
        "--schema-path",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help=f"Caminho para o arquivo SQL de esquema (padrão: {DEFAULT_SCHEMA_PATH.as_posix()}).",
    )
    parser.add_argument(
        "--connect-timeout",
        type=int,
        default=DEFAULT_CONNECT_TIMEOUT_SECONDS,
        help=f"Timeout de conexão em segundos (padrão: {DEFAULT_CONNECT_TIMEOUT_SECONDS}).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada CLI para administração inicial do PostgreSQL."""
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        if args.init_schema:
            report = apply_schema(
                schema_path=args.schema_path,
                connect_timeout=args.connect_timeout,
            )
            print(
                f"Esquema aplicado com sucesso em {report['database_target']} "
                f"(variável={report['source_env_var']}, sha256={report['schema_sha256'][:12]}...)."
            )
            return 0

        status = check_database_connection(
            prefer_direct=False,
            connect_timeout=args.connect_timeout,
        )
        print(
            f"Conexão PostgreSQL validada: banco={status['database_name']} "
            f"({status['database_target']}, variável={status['source_env_var']})."
        )
        return 0
    except (
        DatabaseConfigError,
        DatabaseSchemaError,
        DatabaseConnectionError,
        FileNotFoundError,
        ValueError,
        TypeError,
    ) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
