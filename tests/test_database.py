"""Testes da camada de configuração, esquema SQL e conectividade PostgreSQL (Fase 5)."""

from __future__ import annotations

import json
import re
import traceback
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Any, Self

import pandas as pd
import psycopg
import pytest

from src.database import (
    DatabaseConfigError,
    DatabaseConnectionError,
    DatabaseLoadError,
    DatabaseSchemaError,
    apply_schema,
    check_database_connection,
    load_dataframe_to_postgres,
    load_dotenv_file,
    load_processed_parquet,
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


class FakeCopyWriter:
    """Context manager falso para simular ``cursor.copy(...)`` do psycopg v3."""

    def __init__(
        self,
        captured_rows: list[tuple[Any, ...]],
        *,
        fail_on_write: Exception | None = None,
    ) -> None:
        self._captured_rows = captured_rows
        self._fail_on_write = fail_on_write

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    def write_row(self, row: tuple[Any, ...]) -> None:
        if self._fail_on_write is not None:
            raise self._fail_on_write
        self._captured_rows.append(row)


class FakeLoadCursor:
    """Cursor falso com estado em memória para simular UPSERT, DELETE de revisões e falhas."""

    def __init__(
        self,
        *,
        execucao_id: int = 42,
        fail_on_copy: Exception | None = None,
        fail_on_mark_failed: Exception | None = None,
        dim_store: dict[str, dict[str, Any]] | None = None,
        fact_store: dict[tuple[str, datetime], tuple[Any, ...]] | None = None,
    ) -> None:
        self.execucao_id = execucao_id
        self.fail_on_copy = fail_on_copy
        self.fail_on_mark_failed = fail_on_mark_failed
        self.dim_store: dict[str, dict[str, Any]] = {} if dim_store is None else dim_store
        self.fact_store: dict[tuple[str, datetime], tuple[Any, ...]] = (
            {} if fact_store is None else fact_store
        )
        self.executed: list[tuple[str, Any]] = []
        self.dim_rows: list[tuple[Any, ...]] = []
        self.copied_fact_rows: list[tuple[Any, ...]] = []
        self._staging_rows: list[tuple[Any, ...]] = []
        self.rowcount = 0
        self._last_sql = ""

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    def execute(self, sql: str, params: Any = None) -> None:
        self._last_sql = sql
        self.executed.append((sql, params))
        self.rowcount = 0

        if "SET status = 'falha'" in sql and self.fail_on_mark_failed is not None:
            raise self.fail_on_mark_failed

        if "CREATE TEMP TABLE _stg_fact_restricoes" in sql:
            self._staging_rows = []
            return

        if "INSERT INTO fact_restricoes" in sql and "FROM _stg_fact_restricoes" in sql:
            for row in self._staging_rows:
                self.fact_store[(row[0], row[1])] = row
            self.rowcount = len(self._staging_rows)
            return

        if "DELETE FROM fact_restricoes" in sql and params is not None:
            state_code, period_start, period_end = params
            staging_keys = {(row[0], row[1]) for row in self._staging_rows}
            obsolete_keys = [
                key
                for key, row in self.fact_store.items()
                if row[2] == state_code
                and period_start <= key[1] < period_end
                and key not in staging_keys
            ]
            for key in obsolete_keys:
                del self.fact_store[key]
            self.rowcount = len(obsolete_keys)

    def executemany(self, sql: str, seq: list[tuple[Any, ...]]) -> None:
        self._last_sql = sql
        self.executed.append((sql, seq))
        self.dim_rows.extend(seq)
        if "INSERT INTO dim_empreendimentos" in sql:
            for row in seq:
                (
                    ons_id,
                    usina_nome,
                    estado_sigla,
                    estado_nome,
                    subsistema_id,
                    subsistema_nome,
                    ceg,
                    tipo_identificador,
                    elegivel_aneel,
                    ponto_id,
                    ponto_nome,
                    agente,
                    primeira,
                    ultima,
                ) = row
                existing = self.dim_store.get(ons_id)
                if existing is None:
                    self.dim_store[ons_id] = {
                        "ons_id": ons_id,
                        "usina_nome": usina_nome,
                        "estado_sigla": estado_sigla,
                        "estado_nome": estado_nome,
                        "subsistema_id": subsistema_id,
                        "subsistema_nome": subsistema_nome,
                        "ceg": ceg,
                        "tipo_identificador": tipo_identificador,
                        "elegivel_enriquecimento_aneel": elegivel_aneel,
                        "ponto_conexao_id": ponto_id,
                        "ponto_conexao_nome": ponto_nome,
                        "agente_operador_nome": agente,
                        "primeira_aparicao": primeira,
                        "ultima_aparicao": ultima,
                    }
                else:
                    existing_ultima = existing["ultima_aparicao"]
                    is_newer_or_equal = (
                        existing_ultima is None or ultima >= existing_ultima
                    )
                    if is_newer_or_equal:
                        existing["usina_nome"] = usina_nome
                        existing["estado_sigla"] = estado_sigla
                        existing["estado_nome"] = estado_nome
                        existing["subsistema_id"] = subsistema_id
                        existing["subsistema_nome"] = subsistema_nome
                        existing["ceg"] = ceg
                        existing["tipo_identificador"] = tipo_identificador
                        existing["elegivel_enriquecimento_aneel"] = elegivel_aneel
                        existing["ponto_conexao_id"] = ponto_id
                        existing["ponto_conexao_nome"] = ponto_nome
                        existing["agente_operador_nome"] = agente
                    existing["primeira_aparicao"] = min(
                        existing["primeira_aparicao"], primeira
                    )
                    existing["ultima_aparicao"] = max(
                        existing["ultima_aparicao"], ultima
                    )

    def copy(self, sql: str) -> FakeCopyWriter:
        self._last_sql = sql
        self.executed.append((sql, None))
        self._staging_rows = []
        self.copied_fact_rows = self._staging_rows
        return FakeCopyWriter(self._staging_rows, fail_on_write=self.fail_on_copy)

    def fetchone(self) -> tuple[Any, ...] | None:
        if "RETURNING execucao_id" in self._last_sql:
            return (self.execucao_id,)
        return None


class FakeLoadConnection:
    """Conexão falsa com contagem de commits e rollbacks para testes de carga."""

    def __init__(self, cursor: FakeLoadCursor) -> None:
        self.cursor_obj = cursor
        self.commit_count = 0
        self.rollback_count = 0
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

    def cursor(self) -> FakeLoadCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1


def _synthetic_processed_df() -> pd.DataFrame:
    """Cria DataFrame sintético compatível com o contrato da Fase 3 (com NULLs preservados)."""
    return pd.DataFrame(
        {
            "subsistema_id": pd.Series(["NE", "NE"], dtype="string"),
            "subsistema_nome": pd.Series(["NORDESTE", "NORDESTE"], dtype="string"),
            "estado_sigla": pd.Series(["CE", "CE"], dtype="string"),
            "estado_nome": pd.Series(["CEARA", "CEARA"], dtype="string"),
            "usina_nome": pd.Series(["CONJUNTO TESTE A", "USINA TESTE B"], dtype="string"),
            "ons_id": pd.Series(["CE_CONJ_01", "CE_USI_02"], dtype="string"),
            "ceg": pd.Series(["-", "EOL.CV.CE.000001-0.01"], dtype="string"),
            "instante": pd.to_datetime(["2025-01-01 00:00:00", "2025-01-01 00:30:00"]),
            "geracao_mwmed": pd.Series([100.0, 50.0], dtype="Float64"),
            "geracao_limitada_mwmed": pd.Series([pd.NA, 40.0], dtype="Float64"),
            "disponibilidade_mwmed": pd.Series([120.0, 60.0], dtype="Float64"),
            "geracao_referencia_mwmed": pd.Series([110.0, 55.0], dtype="Float64"),
            "geracao_referencia_final_mwmed": pd.Series([pd.NA, 55.0], dtype="Float64"),
            "restricao_razao_codigo": pd.Series([pd.NA, "ENE"], dtype="string"),
            "restricao_origem_codigo": pd.Series([pd.NA, "SIS"], dtype="string"),
            "restricao_descricao": pd.Series([pd.NA, "Restrição sintética"], dtype="string"),
            "ponto_conexao_id": pd.Series(["PC1", "PC2"], dtype="string"),
            "ponto_conexao_nome": pd.Series(["SE TESTE 1", "SE TESTE 2"], dtype="string"),
            "agente_operador_nome": pd.Series(["AGENTE A", "AGENTE B"], dtype="string"),
            "geracao_nao_realizada_apurada": pd.Series([pd.NA, 5.0], dtype="Float64"),
            "minutos_restricao_rel": pd.Series([pd.NA, 0.0], dtype="Float64"),
            "minutos_restricao_cnf": pd.Series([pd.NA, 0.0], dtype="Float64"),
            "minutos_restricao_ene": pd.Series([pd.NA, 30.0], dtype="Float64"),
            "minutos_restricao_total": pd.Series([pd.NA, 30.0], dtype="Float64"),
            "elegivel_geracao_verificada": pd.Series([True, True], dtype="boolean"),
            "elegivel_referencia_final": pd.Series([False, True], dtype="boolean"),
            "possui_restricao_classificada": pd.Series([False, True], dtype="boolean"),
            "elegivel_gnra": pd.Series([False, True], dtype="boolean"),
            "elegivel_enriquecimento_aneel": pd.Series([False, True], dtype="boolean"),
            "duracao_horas": pd.Series([0.5, 0.5], dtype="Float64"),
            "geracao_verificada_mwh": pd.Series([50.0, 25.0], dtype="Float64"),
            "geracao_referencia_final_mwh": pd.Series([pd.NA, 27.5], dtype="Float64"),
        }
    )


def test_load_dataframe_to_postgres_preserves_nulls_and_runs_idempotent_upserts() -> None:
    df = _synthetic_processed_df()
    cursor = FakeLoadCursor(execucao_id=99)
    conn = FakeLoadConnection(cursor)

    report = load_dataframe_to_postgres(
        df,
        source="eolica",
        state_code="CE",
        year=2025,
        month=1,
        raw_file_name="ons_eolica_2025_01.csv",
        raw_file_sha256="A" * 64,
        parquet_file_name="restricoes_eolicas_ce_2025_01.parquet",
        parquet_file_sha256="B" * 64,
        processed_at_utc="2025-02-01T12:00:00+00:00",
        input_rows=10,
        output_rows=2,
        excluded_by_state_rows=8,
        dropped_duplicate_rows=0,
        database_url="postgresql://user:segredo@db.neon.tech/neondb?sslmode=require",
        connect_fn=lambda dsn, *, connect_timeout: conn,
    )

    assert report["execucao_id"] == 99
    assert report["dim_rows_upserted"] == 2
    assert report["fact_rows_upserted"] == 2
    assert "segredo" not in report["database_target"]
    assert conn.commit_count == 2
    assert conn.rollback_count == 0

    # Verifica classificação de CEG na dimensão (ceg '-' preservado como conjunto_sem_ceg)
    dim_by_id = {row[0]: row for row in cursor.dim_rows}
    assert dim_by_id["CE_CONJ_01"][6] == "-"
    assert dim_by_id["CE_CONJ_01"][7] == "conjunto_sem_ceg"
    assert dim_by_id["CE_CONJ_01"][8] is False
    assert dim_by_id["CE_USI_02"][6] == "EOL.CV.CE.000001-0.01"
    assert dim_by_id["CE_USI_02"][7] == "usina_com_ceg"
    assert dim_by_id["CE_USI_02"][8] is True

    # Verifica preservação rigorosa de NULL (None) em vez de 0 na primeira linha do COPY
    row0 = cursor.copied_fact_rows[0]
    assert row0[0] == "CE_CONJ_01"
    assert row0[7] is None  # geracao_limitada_mwmed
    assert row0[10] is None  # geracao_referencia_final_mwmed
    assert row0[11] is None  # geracao_nao_realizada_apurada
    assert row0[12] is None  # restricao_razao_codigo
    assert row0[20] is None  # geracao_referencia_final_mwh
    assert row0[19] == 50.0  # geracao_verificada_mwh (100 MWmed * 0.5h)

    # Verifica uso explícito de ON CONFLICT DO UPDATE e remoção de obsoletos no período
    sql_statements = [sql for sql, _ in cursor.executed]
    assert any("ON CONFLICT (ons_id) DO UPDATE" in sql for sql in sql_statements)
    assert any("EXCLUDED.ultima_aparicao >= dim_empreendimentos.ultima_aparicao" in sql for sql in sql_statements)
    assert any("ON CONFLICT (ons_id, instante) DO UPDATE" in sql for sql in sql_statements)
    assert any("DELETE FROM fact_restricoes" in sql for sql in sql_statements)
    assert any("SET status = 'concluida'" in sql for sql in sql_statements)
    assert report["fact_rows_deleted"] == 0
    assert len(cursor.fact_store) == 2


def test_load_dataframe_is_idempotent_and_removes_obsolete_rows_on_ons_revision() -> None:
    dim_store: dict[str, dict[str, Any]] = {}
    fact_store: dict[tuple[str, datetime], tuple[Any, ...]] = {}
    url = "postgresql://user:pw@db.neon.tech/neondb?sslmode=require"

    def _run_load(df_to_load: pd.DataFrame, *, year: int, month: int, exec_id: int) -> dict[str, Any]:
        cursor = FakeLoadCursor(execucao_id=exec_id, dim_store=dim_store, fact_store=fact_store)
        conn = FakeLoadConnection(cursor)
        return load_dataframe_to_postgres(
            df_to_load,
            source="eolica",
            state_code="CE",
            year=year,
            month=month,
            raw_file_name=f"ons_eolica_{year}_{month:02d}.csv",
            raw_file_sha256="A" * 64,
            processed_at_utc="2025-02-01T12:00:00+00:00",
            input_rows=len(df_to_load),
            output_rows=len(df_to_load),
            database_url=url,
            connect_fn=lambda dsn, *, connect_timeout: conn,
        )

    # 1) Carga inicial de jan/2025 com 2 linhas
    df_jan_v1 = _synthetic_processed_df()
    r1 = _run_load(df_jan_v1, year=2025, month=1, exec_id=1)
    assert r1["fact_rows_upserted"] == 2
    assert r1["fact_rows_deleted"] == 0
    assert len(fact_store) == 2

    # 2) Carga de fev/2025 com 1 linha (não pode ser apagada por revisão de janeiro)
    df_fev = _synthetic_processed_df().iloc[[0]].copy()
    df_fev["instante"] = pd.to_datetime(["2025-02-01 00:00:00"])
    _run_load(df_fev, year=2025, month=2, exec_id=2)
    assert len(fact_store) == 3

    # 3) Reexecução idêntica de jan/2025: mantém exatamente 3 linhas no total (2 jan + 1 fev)
    r2 = _run_load(df_jan_v1, year=2025, month=1, exec_id=3)
    assert r2["fact_rows_deleted"] == 0
    assert len(fact_store) == 3

    # 4) Revisão oficial de jan/2025 removendo a 2ª linha (CE_USI_02 em 00:30)
    df_jan_v2 = df_jan_v1.iloc[[0]].copy()
    r3 = _run_load(df_jan_v2, year=2025, month=1, exec_id=4)
    assert r3["fact_rows_upserted"] == 1
    assert r3["fact_rows_deleted"] == 1
    assert ("CE_USI_02", datetime(2025, 1, 1, 0, 30)) not in fact_store
    assert ("CE_CONJ_01", datetime(2025, 1, 1, 0, 0)) in fact_store
    assert ("CE_CONJ_01", datetime(2025, 2, 1, 0, 0)) in fact_store
    assert len(fact_store) == 2


def test_dim_empreendimentos_does_not_regress_attributes_on_out_of_order_historical_load() -> None:
    dim_store: dict[str, dict[str, Any]] = {}
    fact_store: dict[tuple[str, datetime], tuple[Any, ...]] = {}
    url = "postgresql://user:pw@db.neon.tech/neondb?sslmode=require"

    # Primeiro carrega março/2025 com nome e CEG atualizados
    df_mar = _synthetic_processed_df().iloc[[0]].copy()
    df_mar["instante"] = pd.to_datetime(["2025-03-15 12:00:00"])
    df_mar["usina_nome"] = pd.Series(["CONJUNTO NOME NOVO MARCO"], dtype="string")
    df_mar["ceg"] = pd.Series(["EOL.CV.CE.999999-0.01"], dtype="string")
    df_mar["elegivel_enriquecimento_aneel"] = pd.Series([True], dtype="boolean")

    c_mar = FakeLoadCursor(execucao_id=10, dim_store=dim_store, fact_store=fact_store)
    load_dataframe_to_postgres(
        df_mar,
        source="eolica",
        state_code="CE",
        year=2025,
        month=3,
        raw_file_name="ons_eolica_2025_03.csv",
        raw_file_sha256="A" * 64,
        processed_at_utc="2025-04-01T12:00:00+00:00",
        input_rows=1,
        output_rows=1,
        database_url=url,
        connect_fn=lambda dsn, *, connect_timeout: FakeLoadConnection(c_mar),
    )

    # Depois carrega janeiro/2025 (histórico mais antigo) com nome e CEG antigos
    df_jan = _synthetic_processed_df().iloc[[0]].copy()
    df_jan["instante"] = pd.to_datetime(["2025-01-01 00:00:00"])
    df_jan["usina_nome"] = pd.Series(["CONJUNTO NOME ANTIGO JAN"], dtype="string")
    df_jan["ceg"] = pd.Series(["-"], dtype="string")
    df_jan["elegivel_enriquecimento_aneel"] = pd.Series([False], dtype="boolean")

    c_jan = FakeLoadCursor(execucao_id=11, dim_store=dim_store, fact_store=fact_store)
    load_dataframe_to_postgres(
        df_jan,
        source="eolica",
        state_code="CE",
        year=2025,
        month=1,
        raw_file_name="ons_eolica_2025_01.csv",
        raw_file_sha256="B" * 64,
        processed_at_utc="2025-04-01T12:05:00+00:00",
        input_rows=1,
        output_rows=1,
        database_url=url,
        connect_fn=lambda dsn, *, connect_timeout: FakeLoadConnection(c_jan),
    )

    dim_entry = dim_store["CE_CONJ_01"]
    assert dim_entry["primeira_aparicao"] == datetime(2025, 1, 1, 0, 0)
    assert dim_entry["ultima_aparicao"] == datetime(2025, 3, 15, 12, 0)
    # Atributos descritivos devem permanecer os de março (sem regressão para janeiro)
    assert dim_entry["usina_nome"] == "CONJUNTO NOME NOVO MARCO"
    assert dim_entry["ceg"] == "EOL.CV.CE.999999-0.01"
    assert dim_entry["tipo_identificador"] == "usina_com_ceg"


def test_load_dataframe_to_postgres_rejects_invalid_inputs_and_edge_cases() -> None:
    valid_kwargs: dict[str, Any] = {
        "source": "eolica",
        "state_code": "CE",
        "year": 2025,
        "month": 1,
        "raw_file_name": "ons_eolica_2025_01.csv",
        "raw_file_sha256": "A" * 64,
        "processed_at_utc": "2025-02-01T12:00:00+00:00",
        "input_rows": 2,
        "output_rows": 2,
        "database_url": "postgresql://user:pw@db.neon.tech/neondb",
    }

    with pytest.raises(TypeError):
        load_dataframe_to_postgres(None, **valid_kwargs)

    # DataFrame vazio
    empty_df = _synthetic_processed_df().iloc[0:0]
    with pytest.raises(ValueError, match="vazio"):
        load_dataframe_to_postgres(empty_df, **valid_kwargs)

    # Chave duplicada no mesmo lote
    dup_df = pd.concat([_synthetic_processed_df().iloc[[0]], _synthetic_processed_df().iloc[[0]]])
    with pytest.raises(ValueError, match="Chave duplicada"):
        load_dataframe_to_postgres(dup_df, **valid_kwargs)

    # Estado divergente do solicitado
    wrong_state_df = _synthetic_processed_df()
    wrong_state_df.loc[0, "estado_sigla"] = "RN"
    with pytest.raises(ValueError, match="diverge do estado esperado"):
        load_dataframe_to_postgres(wrong_state_df, **valid_kwargs)

    # Instante fora do mês solicitado (protege DELETE escopado ao período)
    wrong_period_df = _synthetic_processed_df()
    wrong_period_df.loc[0, "instante"] = pd.Timestamp("2025-02-01 00:00:00")
    with pytest.raises(ValueError, match="fora do período esperado"):
        load_dataframe_to_postgres(wrong_period_df, **valid_kwargs)

    # Timestamp com timezone (viola política naive oficial do ONS)
    tz_df = _synthetic_processed_df()
    tz_df["instante"] = pd.to_datetime(tz_df["instante"]).dt.tz_localize(UTC)
    with pytest.raises(ValueError, match="naive"):
        load_dataframe_to_postgres(tz_df, **valid_kwargs)

    # Valor numérico não finito (inf)
    inf_df = _synthetic_processed_df()
    inf_df.loc[0, "geracao_mwmed"] = float("inf")
    with pytest.raises(ValueError, match="não finito"):
        load_dataframe_to_postgres(inf_df, **valid_kwargs)

    # SHA-256 inválido
    with pytest.raises(ValueError, match="SHA-256"):
        load_dataframe_to_postgres(
            _synthetic_processed_df(),
            **{**valid_kwargs, "raw_file_sha256": "curto"},
        )


def test_load_dataframe_marks_etl_failed_and_hides_password_on_db_error() -> None:
    secret = "S3nhaSuperSecreta!"
    url = f"postgresql://neondb_owner:{secret}@ep-demo.neon.tech/neondb?sslmode=require"
    cursor = FakeLoadCursor(
        execucao_id=77,
        fail_on_copy=psycopg.OperationalError(f"copy failed for {url}"),
    )
    conn = FakeLoadConnection(cursor)

    with pytest.raises(DatabaseLoadError) as exc_info:
        load_dataframe_to_postgres(
            _synthetic_processed_df(),
            source="eolica",
            state_code="CE",
            year=2025,
            month=1,
            raw_file_name="ons_eolica_2025_01.csv",
            raw_file_sha256="A" * 64,
            processed_at_utc=datetime(2025, 2, 1, 12, 0, tzinfo=UTC),
            input_rows=2,
            output_rows=2,
            database_url=url,
            connect_fn=lambda dsn, *, connect_timeout: conn,
        )

    assert secret not in str(exc_info.value)
    assert "execucao_id=77" in str(exc_info.value)
    assert conn.rollback_count == 1
    assert any("SET status = 'falha'" in sql for sql, _ in cursor.executed)


def test_load_dataframe_reports_secondary_error_when_mark_failed_also_fails() -> None:
    secret = "S3nhaSuperSecreta!"
    url = f"postgresql://neondb_owner:{secret}@ep-demo.neon.tech/neondb?sslmode=require"
    cursor = FakeLoadCursor(
        execucao_id=88,
        fail_on_copy=psycopg.OperationalError(f"copy failed for {url}"),
        fail_on_mark_failed=psycopg.OperationalError(f"status update failed for {url}"),
    )
    conn = FakeLoadConnection(cursor)

    with pytest.raises(DatabaseLoadError) as exc_info:
        load_dataframe_to_postgres(
            _synthetic_processed_df(),
            source="eolica",
            state_code="CE",
            year=2025,
            month=1,
            raw_file_name="ons_eolica_2025_01.csv",
            raw_file_sha256="A" * 64,
            processed_at_utc=datetime(2025, 2, 1, 12, 0, tzinfo=UTC),
            input_rows=2,
            output_rows=2,
            database_url=url,
            connect_fn=lambda dsn, *, connect_timeout: conn,
        )

    message = str(exc_info.value)
    assert secret not in message
    assert "execucao_id=88" in message
    assert "copy failed" in message
    assert "status update failed" in message
    assert "permanece como 'iniciada'" in message
    assert conn.rollback_count == 2


def test_load_processed_parquet_reads_files_and_validates_missing_artifacts(
    tmp_path: Path,
) -> None:
    parquet_path = tmp_path / "restricoes_eolicas_ce_2025_01.parquet"
    report_path = Path(f"{parquet_path}.quality_report.json")
    _synthetic_processed_df().to_parquet(parquet_path, index=False)

    # Sem relatório de qualidade deve falhar explicitamente
    with pytest.raises(FileNotFoundError, match="Relatório de qualidade"):
        load_processed_parquet(parquet_path)

    report_path.write_text(
        json.dumps(
            {
                "source_file": "data/raw/ons_eolica_2025_01.csv",
                "source_sha256": "C" * 64,
                "output_parquet_sha256": "D" * 64,
                "processed_at_utc": "2025-02-01T12:00:00+00:00",
                "target_state": "CE",
                "expected_year": 2025,
                "expected_month": 1,
                "input_rows": 2,
                "output_rows": 2,
                "excluded_by_state_rows": 0,
                "dropped_exact_duplicate_rows": 0,
            }
        ),
        encoding="utf-8",
    )

    cursor = FakeLoadCursor(execucao_id=55)
    conn = FakeLoadConnection(cursor)
    result = load_processed_parquet(
        parquet_path,
        database_url="postgresql://user:pw@db.neon.tech/neondb",
        connect_fn=lambda dsn, *, connect_timeout: conn,
    )
    assert result["execucao_id"] == 55
    assert result["fact_rows_upserted"] == 2

    # Parquet inexistente
    with pytest.raises(FileNotFoundError, match="Parquet"):
        load_processed_parquet(tmp_path / "inexistente.parquet")
