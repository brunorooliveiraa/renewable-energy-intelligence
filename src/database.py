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
import os
import re
import sys
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict
from urllib.parse import quote, unquote, urlparse, urlunparse

import psycopg

VALID_POSTGRES_SCHEMES: frozenset[str] = frozenset({"postgresql", "postgres"})
DEFAULT_SCHEMA_PATH = Path("sql") / "schema.sql"
DEFAULT_ENV_FILE = Path(".env")
DEFAULT_CONNECT_TIMEOUT_SECONDS = 15
METHODOLOGY_VERSION = "v1.0"
_POSTGRES_URL_CREDENTIAL_PATTERN = re.compile(
    r"(?i)(postgres(?:ql)?://[^/\s:@]+:)([^@\s]+)(@)"
)
_LIBPQ_PASSWORD_PATTERN = re.compile(
    r"(?i)(\bpassword\s*=\s*)(?:'(?:\\'|[^'])*'|\"(?:\\\"|[^\"])*\"|\S+)"
)


class DatabaseConfigError(ValueError):
    """Configuração de conexão PostgreSQL ausente ou inválida."""


class DatabaseSchemaError(ValueError):
    """Arquivo de esquema SQL ausente, inválido ou vazio."""


class DatabaseConnectionError(RuntimeError):
    """Falha de conexão ou execução DDL/SQL no PostgreSQL."""


class SchemaApplyReport(TypedDict):
    """Resumo auditável da aplicação do esquema PostgreSQL."""

    schema_path: str
    schema_sha256: str
    database_target: str
    source_env_var: str
    applied_at_utc: str


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
    return urlunparse(
        (parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
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
