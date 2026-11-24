"""Testes da camada de configuração, esquema SQL e conectividade PostgreSQL (Fase 5)."""

from __future__ import annotations

import re
import traceback
from pathlib import Path
from types import TracebackType
from typing import Any, Self

import psycopg
import pytest

from src.database import (
    DatabaseConfigError,
    DatabaseConnectionError,
    DatabaseSchemaError,
    apply_schema,
    check_database_connection,
    load_dotenv_file,
    load_schema_sql,
    main,
    mask_postgres_url,
    resolve_database_url,
    validate_postgres_url,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_FILE = PROJECT_ROOT / "sql" / "schema.sql"


class FakeCursor:
    """Cursor falso para simular execução DDL e consultas sem banco real."""

    def __init__(
        self,
        *,
        fetchone_result: tuple[Any, ...] | None = ("neondb", "PostgreSQL 16.4"),
        fail_on_execute: Exception | None = None,
    ) -> None:
        self.executed_sql: list[str] = []
        self._fetchone_result = fetchone_result
        self._fail_on_execute = fail_on_execute

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    def execute(self, sql: str) -> None:
        self.executed_sql.append(sql)
        if self._fail_on_execute is not None:
            raise self._fail_on_execute

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._fetchone_result


class FakeConnection:
    """Conexão falsa compatível com o protocolo context manager do psycopg v3."""

    def __init__(self, cursor: FakeCursor) -> None:
        self.cursor_obj = cursor
        self.committed = False
        self.closed = False

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.closed = True

    def cursor(self) -> FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.committed = True


def test_validate_and_mask_postgres_url_accept_valid_urls_and_hide_password() -> None:
    raw = "  postgresql://neondb_owner:super_secret_pw@ep-demo-pooler.us-east-1.aws.neon.tech:5432/neondb?sslmode=require  "
    validated = validate_postgres_url(raw)
    assert validated == raw.strip()

    masked = mask_postgres_url(raw)
    assert "super_secret_pw" not in masked
    assert "neondb_owner:***@" in masked
    assert "ep-demo-pooler.us-east-1.aws.neon.tech:5432/neondb?sslmode=require" in masked


def test_mask_postgres_url_hides_password_from_query_parameters() -> None:
    raw = (
        "postgresql://neondb_owner@ep-demo-pooler.us-east-1.aws.neon.tech/neondb"
        "?password=s3nh4%40secreta%21&sslmode=require"
    )

    masked = mask_postgres_url(raw)

    assert "s3nh4" not in masked
    assert "secreta" not in masked
    assert "password=%2A%2A%2A" in masked
    assert "sslmode=require" in masked


def test_validate_postgres_url_rejects_invalid_types_and_formats() -> None:
    with pytest.raises(TypeError):
        validate_postgres_url(None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        validate_postgres_url(12345)  # type: ignore[arg-type]

    for bad_url in ("", "   ", "sqlite:///local.db", "http://localhost:5432/db", "postgresql://"):
        with pytest.raises(DatabaseConfigError):
            validate_postgres_url(bad_url)


def test_load_dotenv_file_parses_values_and_rejects_malformed_lines(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# Comentário\n"
        "\n"
        'DATABASE_URL="postgresql://u:p@ep-pooler.neon.tech/neondb?sslmode=require"\n'
        "export DIRECT_DATABASE_URL='postgresql://u:p@ep-direct.neon.tech/neondb?sslmode=require'\n",
        encoding="utf-8",
    )

    parsed = load_dotenv_file(env_file)
    assert parsed["DATABASE_URL"].startswith("postgresql://u:p@ep-pooler")
    assert parsed["DIRECT_DATABASE_URL"].startswith("postgresql://u:p@ep-direct")

    bad_env = tmp_path / "bad.env"
    bad_env.write_text("LINHA_SEM_IGUAL\n", encoding="utf-8")
    with pytest.raises(DatabaseConfigError):
        load_dotenv_file(bad_env)

    with pytest.raises(FileNotFoundError):
        load_dotenv_file(tmp_path / "nao_existe.env")

    with pytest.raises(DatabaseConfigError):
        load_dotenv_file(tmp_path)

    with pytest.raises(TypeError):
        load_dotenv_file(123)  # type: ignore[arg-type]


def test_resolve_database_url_respects_direct_vs_pooled_precedence(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgresql://u:p@ep-pooler.neon.tech/neondb?sslmode=require\n"
        "DIRECT_DATABASE_URL=postgresql://u:p@ep-direct.neon.tech/neondb?sslmode=require\n",
        encoding="utf-8",
    )

    direct_url, direct_var = resolve_database_url(prefer_direct=True, env={}, env_file=env_file)
    assert direct_var == "DIRECT_DATABASE_URL"
    assert "ep-direct" in direct_url

    pooled_url, pooled_var = resolve_database_url(prefer_direct=False, env={}, env_file=env_file)
    assert pooled_var == "DATABASE_URL"
    assert "ep-pooler" in pooled_url

    # Quando só DIRECT_DATABASE_URL existe, prefer_direct=False NÃO deve usá-la silenciosamente.
    only_direct_env = {
        "DIRECT_DATABASE_URL": "postgresql://u:p@ep-direct.neon.tech/neondb?sslmode=require"
    }
    with pytest.raises(DatabaseConfigError):
        resolve_database_url(prefer_direct=False, env=only_direct_env, env_file=None)

    with pytest.raises(TypeError):
        resolve_database_url(prefer_direct="yes", env={}, env_file=None)  # type: ignore[arg-type]


def test_load_schema_sql_validates_file_and_methodological_invariants(tmp_path: Path) -> None:
    sql_text, sha256_hex, resolved_path = load_schema_sql(SCHEMA_FILE)
    assert resolved_path == SCHEMA_FILE
    assert len(sha256_hex) == 64

    # Tabelas e views obrigatórias com cláusulas idempotentes
    for table_name in ("etl_execucoes", "dim_empreendimentos", "fact_restricoes"):
        assert f"CREATE TABLE IF NOT EXISTS {table_name}" in sql_text
    for view_name in (
        "vw_serie_diaria",
        "vw_serie_mensal",
        "vw_ranking_empreendimentos",
        "vw_resumo_razoes_origens",
    ):
        assert f"CREATE OR REPLACE VIEW {view_name}" in sql_text

    # Regras metodológicas críticas das Fases 1-4
    assert "PRIMARY KEY (ons_id, instante)" in sql_text
    assert "instante TIMESTAMP WITHOUT TIME ZONE NOT NULL" in sql_text
    assert "COALESCE(" not in sql_text.upper()
    assert re.search(r"SUM\s*\([^)]*geracao_nao_realizada_apurada", sql_text, re.IGNORECASE) is None
    reasons_view = sql_text.split("CREATE OR REPLACE VIEW vw_resumo_razoes_origens AS", 1)[1]
    assert re.search(
        r"FROM\s+fact_restricoes\s+AS\s+f\s+WHERE\s+f\.possui_restricao_classificada\s*=\s*TRUE",
        reasons_view,
        re.IGNORECASE,
    )

    empty_sql = tmp_path / "empty.sql"
    empty_sql.write_text("   \n", encoding="utf-8")
    with pytest.raises(DatabaseSchemaError):
        load_schema_sql(empty_sql)
    with pytest.raises(DatabaseSchemaError):
        load_schema_sql(tmp_path / "missing.sql")
    with pytest.raises(DatabaseSchemaError):
        load_schema_sql(tmp_path)
    with pytest.raises(TypeError):
        load_schema_sql(None)  # type: ignore[arg-type]


def test_apply_schema_is_idempotent_and_masks_errors() -> None:
    url = "postgresql://owner:segredo123@ep-direct.neon.tech/neondb?sslmode=require"
    connections: list[FakeConnection] = []

    def fake_connect(dsn: str, *, connect_timeout: int) -> FakeConnection:
        assert dsn == url
        assert connect_timeout == 10
        conn = FakeConnection(FakeCursor())
        connections.append(conn)
        return conn

    report_1 = apply_schema(
        database_url=url,
        schema_path=SCHEMA_FILE,
        connect_timeout=10,
        connect_fn=fake_connect,
    )
    report_2 = apply_schema(
        database_url=url,
        schema_path=SCHEMA_FILE,
        connect_timeout=10,
        connect_fn=fake_connect,
    )

    assert len(connections) == 2
    assert all(conn.committed and conn.closed for conn in connections)
    assert report_1["schema_sha256"] == report_2["schema_sha256"]
    assert "segredo123" not in report_1["database_target"]

    # Erro de banco nunca é silenciado e nunca vaza senha
    def failing_connect(dsn: str, *, connect_timeout: int) -> FakeConnection:
        return FakeConnection(
            FakeCursor(fail_on_execute=psycopg.OperationalError("connection refused"))
        )

    with pytest.raises(DatabaseConnectionError) as exc_info:
        apply_schema(
            database_url=url,
            schema_path=SCHEMA_FILE,
            connect_fn=failing_connect,
        )
    assert "segredo123" not in str(exc_info.value)
    assert "connection refused" in str(exc_info.value)

    with pytest.raises(TypeError):
        apply_schema(database_url=url, connect_timeout=True)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        apply_schema(database_url=url, connect_timeout=0)


def test_check_database_connection_handles_success_and_db_errors() -> None:
    url = "postgresql://owner:senha_oculta@ep-pooler.neon.tech/neondb?sslmode=require"

    def ok_connect(dsn: str, *, connect_timeout: int) -> FakeConnection:
        return FakeConnection(FakeCursor(fetchone_result=("neondb", "PostgreSQL 16.4")))

    result = check_database_connection(database_url=url, connect_fn=ok_connect)
    assert result["status"] == "ok"
    assert result["database_name"] == "neondb"
    assert "senha_oculta" not in result["database_target"]

    def empty_connect(dsn: str, *, connect_timeout: int) -> FakeConnection:
        return FakeConnection(FakeCursor(fetchone_result=None))

    with pytest.raises(DatabaseConnectionError):
        check_database_connection(database_url=url, connect_fn=empty_connect)

    def error_connect(dsn: str, *, connect_timeout: int) -> FakeConnection:
        raise psycopg.OperationalError("timeout expired")

    with pytest.raises(DatabaseConnectionError) as exc_info:
        check_database_connection(database_url=url, connect_fn=error_connect)
    assert "senha_oculta" not in str(exc_info.value)


def test_database_errors_never_leak_password_from_psycopg_exception() -> None:
    encoded_secret = "s3nh4%40secreta!"
    decoded_secret = "s3nh4@secreta!"
    url = (
        f"postgresql://neondb_owner:{encoded_secret}"
        "@ep-direct.us-east-1.aws.neon.tech/neondb?sslmode=require"
    )
    leaky_messages = (
        f"connection failed for {url}: server closed the connection unexpectedly",
        f"failed to connect: host=ep-direct.us-east-1.aws.neon.tech user=neondb_owner password='{decoded_secret}'",
        f"auth failed with password={decoded_secret} on {url}",
    )

    for raw_error_message in leaky_messages:

        def leaky_connect(
            dsn: str,
            *,
            connect_timeout: int,
            msg: str = raw_error_message,
        ) -> FakeConnection:
            raise psycopg.OperationalError(msg)

        with pytest.raises(DatabaseConnectionError) as apply_exc:
            apply_schema(
                database_url=url,
                schema_path=SCHEMA_FILE,
                connect_fn=leaky_connect,
            )
        apply_rendered = "".join(traceback.format_exception(apply_exc.value))
        assert encoded_secret not in str(apply_exc.value)
        assert decoded_secret not in str(apply_exc.value)
        assert encoded_secret not in apply_rendered
        assert decoded_secret not in apply_rendered
        assert "OperationalError" in str(apply_exc.value)

        with pytest.raises(DatabaseConnectionError) as check_exc:
            check_database_connection(
                database_url=url,
                connect_fn=leaky_connect,
            )
        check_rendered = "".join(traceback.format_exception(check_exc.value))
        assert encoded_secret not in str(check_exc.value)
        assert decoded_secret not in str(check_exc.value)
        assert encoded_secret not in check_rendered
        assert decoded_secret not in check_rendered
        assert "OperationalError" in str(check_exc.value)


def test_cli_returns_nonzero_when_database_url_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DIRECT_DATABASE_URL", raising=False)

    exit_code = main(["--check-connection"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Erro:" in captured.err
