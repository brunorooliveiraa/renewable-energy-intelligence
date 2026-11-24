"""Testes da camada HTTP serverless FastAPI (Vercel)."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from types import TracebackType
from typing import Any, Self

import psycopg
import pytest
from fastapi.testclient import TestClient

import api.queries as api_queries
from api.index import app

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_api_health_reports_database_configuration_without_exposing_secrets(
    monkeypatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    client = TestClient(app)

    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database_engine"] == "postgresql"
    assert payload["database_configured"] is False
    assert "timestamp_utc" in payload

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:secret@ep-demo-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require",
    )
    response_configured = client.get("/api/health")
    assert response_configured.status_code == 200
    payload_configured = response_configured.json()
    assert payload_configured["database_configured"] is True
    assert "secret" not in json.dumps(payload_configured)


def test_api_health_rejects_invalid_or_non_postgres_database_url(monkeypatch) -> None:
    client = TestClient(app)

    for invalid_url in ("   ", "sqlite:///local.db", "postgresql://", "valor-invalido"):
        monkeypatch.setenv("DATABASE_URL", invalid_url)
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["database_configured"] is False


def test_vercel_config_and_runtime_requirements_stay_lightweight() -> None:
    vercel_config = json.loads(
        (PROJECT_ROOT / "vercel.json").read_text(encoding="utf-8")
    )
    rewrites = vercel_config["rewrites"]
    assert {"source": "/api/(.*)", "destination": "/api/index.py"} in rewrites
    assert {"source": "/", "destination": "/frontend/index.html"} in rewrites

    runtime_reqs = (
        (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    )
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "fastapi" in runtime_reqs
    assert "psycopg[binary]" in runtime_reqs
    assert "pandas" not in runtime_reqs
    assert "pyarrow" not in runtime_reqs
    assert "`psycopg[binary]` será adicionado" not in readme

    # Garante que nenhum módulo Python em api/ importa pandas ou pyarrow
    for py_file in (PROJECT_ROOT / "api").glob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        assert "import pandas" not in source
        assert "from pandas" not in source
        assert "import pyarrow" not in source
        assert "from pyarrow" not in source


class FakeQueryCursor:
    """Cursor falso parametrizável para testar endpoints FastAPI sem banco real."""

    def __init__(
        self,
        *,
        fetchone_queue: list[tuple[Any, ...] | None] | None = None,
        fetchall_queue: list[list[tuple[Any, ...]]] | None = None,
        fail_with: Exception | None = None,
    ) -> None:
        self._fetchone_queue = list(fetchone_queue or [])
        self._fetchall_queue = list(fetchall_queue or [])
        self._fail_with = fail_with
        self.executed: list[tuple[str, Any]] = []

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
        self.executed.append((sql, params))
        if self._fail_with is not None:
            raise self._fail_with

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._fetchone_queue.pop(0) if self._fetchone_queue else None

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._fetchall_queue.pop(0) if self._fetchall_queue else []


class FakeQueryConnection:
    """Conexão falsa compatível com context manager do psycopg v3."""

    def __init__(self, cursor: FakeQueryCursor) -> None:
        self.cursor_obj = cursor

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    def cursor(self) -> FakeQueryCursor:
        return self.cursor_obj


def _patch_fake_db(
    monkeypatch: pytest.MonkeyPatch,
    cursor: FakeQueryCursor,
    *,
    dsn: str = "postgresql://user:segredo@ep-demo-pooler.neon.tech/neondb?sslmode=require",
) -> None:
    monkeypatch.setenv("DATABASE_URL", dsn)
    monkeypatch.setattr(
        api_queries.psycopg,
        "connect",
        lambda url, *, connect_timeout: FakeQueryConnection(cursor),
    )


def test_enterprises_query_applies_exact_ons_id_filter() -> None:
    """O ranking deve respeitar o mesmo ``ons_id`` do restante da Visão Geral."""
    cursor = FakeQueryCursor(fetchone_queue=[(0,)])

    result = api_queries.query_enterprises(
        ons_id="CJU_CEPTM",
        connect_fn=lambda url, *, connect_timeout: FakeQueryConnection(cursor),
        database_url=(
            "postgresql://user:segredo@ep-demo-pooler.neon.tech/neondb?sslmode=require"
        ),
    )

    assert result["pagination"]["total"] == 0
    count_sql, count_params = cursor.executed[0]
    assert "f.ons_id = %s" in count_sql
    assert "CJU_CEPTM" in count_params

    with pytest.raises(TypeError, match="ons_id deve ser uma string"):
        api_queries.query_enterprises(
            ons_id=123,  # type: ignore[arg-type]
            connect_fn=lambda url, *, connect_timeout: FakeQueryConnection(cursor),
            database_url=(
                "postgresql://user:segredo@ep-demo-pooler.neon.tech/neondb?sslmode=require"
            ),
        )

    with pytest.raises(ValueError, match="ons_id não pode ser uma string vazia"):
        api_queries.query_enterprises(
            ons_id="   ",
            connect_fn=lambda url, *, connect_timeout: FakeQueryConnection(cursor),
            database_url=(
                "postgresql://user:segredo@ep-demo-pooler.neon.tech/neondb?sslmode=require"
            ),
        )


def test_overview_endpoint_returns_metrics_and_handles_empty_filter_without_fake_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TestClient(app)

    # Caso com dados
    cursor_with_data = FakeQueryCursor(
        fetchone_queue=[
            (
                28272,
                5692,
                22580,
                20.133,
                19,
                18,
                28272,
                5692,
                5692,
                362247.938,
                30619.1855,
                148200.0,
                datetime(2025, 1, 1, 0, 0),
                datetime(2025, 1, 31, 23, 30),
            )
        ]
    )
    _patch_fake_db(monkeypatch, cursor_with_data)
    resp = client.get("/api/overview?state=CE&start_date=2025-01-01&end_date=2025-01-31")
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_data"] is True
    assert body["units"]["geracao_verificada_mwh"] == "MWh"
    assert body["methodology"]["gnra_unit_status"] == "pending_official_confirmation"
    assert body["summary"]["total_intervalos"] == 28272
    assert body["summary"]["geracao_verificada_mwh"] == 362247.938

    # Caso sem dados: nunca retorna zero falso para métricas ausentes
    cursor_empty = FakeQueryCursor(
        fetchone_queue=[(0, 0, 0, None, 0, 0, 0, 0, 0, None, None, None, None, None)]
    )
    _patch_fake_db(monkeypatch, cursor_empty)
    resp_empty = client.get("/api/overview?state=CE&start_date=2026-01-01&end_date=2026-01-31")
    assert resp_empty.status_code == 200
    empty_body = resp_empty.json()
    assert empty_body["has_data"] is False
    assert empty_body["summary"]["total_intervalos"] == 0
    assert empty_body["summary"]["geracao_verificada_mwh"] is None
    assert empty_body["summary"]["intervalos_com_restricao"] is None
    assert empty_body["summary"]["taxa_intervalos_restricao_pct"] is None


def test_timeseries_enterprises_reasons_and_quality_endpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TestClient(app)

    # /api/timeseries
    ts_cursor = FakeQueryCursor(
        fetchall_queue=[
            [
                (date(2025, 1, 1), 912, 120, 792, 13.1579, 19, 12, 912, 120, 12345.5, 2500.0, 3600.0)
            ]
        ]
    )
    _patch_fake_db(monkeypatch, ts_cursor)
    resp_ts = client.get("/api/timeseries?state=CE&granularity=daily")
    assert resp_ts.status_code == 200
    ts_body = resp_ts.json()
    assert ts_body["has_data"] is True
    assert ts_body["granularity"] == "daily"
    assert ts_body["items"][0]["periodo_referencia"] == "2025-01-01"
    assert ts_body["items"][0]["geracao_verificada_mwh"] == 12345.5

    # /api/enterprises com busca contendo caractere curinga (%) escapado
    ent_cursor = FakeQueryCursor(
        fetchone_queue=[(1,)],
        fetchall_queue=[
            [
                (
                    "CE_CONJ_01",
                    "CONJUNTO TESTE 100%",
                    "-",
                    "conjunto_sem_ceg",
                    False,
                    1488,
                    400,
                    26.8817,
                    1488,
                    400,
                    21000.0,
                    6500.0,
                    12000.0,
                )
            ]
        ],
    )
    _patch_fake_db(monkeypatch, ent_cursor)
    resp_ent = client.get("/api/enterprises?state=CE&search=100%25&limit=10&offset=0")
    assert resp_ent.status_code == 200
    ent_body = resp_ent.json()
    assert ent_body["has_data"] is True
    assert ent_body["pagination"] == {"total": 1, "limit": 10, "offset": 0}
    assert ent_body["items"][0]["tipo_identificador"] == "conjunto_sem_ceg"
    # Confirma escape do '%' no parâmetro ILIKE
    _, ent_params = ent_cursor.executed[0]
    assert "%100\\%%" in ent_params

    # /api/enterprises com offset >= total deve preservar pagination.total=19
    ent_past_end_cursor = FakeQueryCursor(fetchone_queue=[(19,)], fetchall_queue=[])
    _patch_fake_db(monkeypatch, ent_past_end_cursor)
    resp_past_end = client.get("/api/enterprises?state=CE&limit=10&offset=19")
    assert resp_past_end.status_code == 200
    past_end_body = resp_past_end.json()
    assert past_end_body["has_data"] is True
    assert past_end_body["items"] == []
    assert past_end_body["pagination"] == {"total": 19, "limit": 10, "offset": 19}

    # /api/reasons inclui códigos oficiais ausentes (ex.: PAR e LOC) com 0 intervalos e energia None
    reasons_cursor = FakeQueryCursor(
        fetchall_queue=[
            [("ENE", "SIS", 400, 15, 400, 400, 5000.0, 9000.0, 12000.0)],
            [("ENE", 400, 15, 5000.0, 9000.0, 12000.0)],
            [("SIS", 400, 15, 5000.0, 9000.0, 12000.0)],
            [("ENE", "SIS", "Restrição energética sistêmica", 400)],
        ]
    )
    _patch_fake_db(monkeypatch, reasons_cursor)
    resp_reasons = client.get("/api/reasons?state=CE")
    assert resp_reasons.status_code == 200
    reasons_body = resp_reasons.json()
    assert reasons_body["has_data"] is True
    assert reasons_body["total_intervalos_com_restricao"] == 400
    by_reason_map = {
        entry["restricao_razao_codigo"]: entry for entry in reasons_body["by_reason"]
    }
    assert set(by_reason_map) == {"REL", "CNF", "ENE", "PAR"}
    assert by_reason_map["PAR"]["intervalos_com_restricao"] == 0
    assert by_reason_map["PAR"]["geracao_verificada_mwh"] is None
    assert by_reason_map["PAR"]["minutos_restricao_total"] is None
    by_origin_map = {
        entry["restricao_origem_codigo"]: entry for entry in reasons_body["by_origin"]
    }
    assert set(by_origin_map) == {"LOC", "SIS"}
    assert by_origin_map["LOC"]["intervalos_com_restricao"] == 0
    assert by_origin_map["LOC"]["geracao_verificada_mwh"] is None
    assert reasons_body["top_descriptions"][0]["restricao_descricao"] == "Restrição energética sistêmica"

    # /api/quality usa MAX(carregado_em_utc) e MAX(coletado_em_utc) mesmo se revisão de jan for mais recente que mar
    jan_loaded = datetime(2026, 11, 24, 15, 0, tzinfo=UTC)
    jan_collected = datetime(2026, 11, 24, 14, 30, tzinfo=UTC)
    mar_loaded = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
    mar_collected = datetime(2026, 11, 20, 9, 30, tzinfo=UTC)
    quality_cursor = FakeQueryCursor(
        fetchone_queue=[
            (
                28272,
                28272,
                5692,
                22580,
                5692,
                5692,
                19,
                4,
                15,
                datetime(2025, 1, 1, 0, 0),
                datetime(2025, 1, 31, 23, 30),
            ),
            (jan_loaded, jan_collected),
        ],
        fetchall_queue=[
            [
                # Março aparece primeiro na lista por ano/mês de referência, mas janeiro foi carregado depois
                (
                    2,
                    "eolica",
                    "CE",
                    2025,
                    3,
                    "ons_eolica_2025_03.csv",
                    "B" * 64,
                    mar_collected,
                    mar_loaded,
                    mar_loaded,
                    232128,
                    28272,
                    28272,
                    "pending_official_confirmation",
                    "v1.0",
                ),
                (
                    3,
                    "eolica",
                    "CE",
                    2025,
                    1,
                    "RESTRICAO_COFF_EOLICA_2025_01.csv",
                    "A" * 64,
                    jan_collected,
                    jan_loaded,
                    jan_loaded,
                    232128,
                    28272,
                    28272,
                    "pending_official_confirmation",
                    "v1.0",
                ),
            ]
        ],
    )
    _patch_fake_db(monkeypatch, quality_cursor)
    resp_quality = client.get("/api/quality?state=CE")
    assert resp_quality.status_code == 200
    q_body = resp_quality.json()
    assert q_body["has_data"] is True
    assert q_body["coverage"]["empreendimentos_com_ceg"] == 4
    assert q_body["coverage"]["conjuntos_sem_ceg"] == 15
    assert q_body["last_loaded_at_utc"] == jan_loaded.isoformat()
    assert q_body["last_collected_at_utc"] == jan_collected.isoformat()
    assert q_body["executions"][0]["mes_referencia"] == 3


def test_endpoints_return_422_for_invalid_filters_and_503_without_leaking_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TestClient(app)

    # Validação de parâmetros (422) sem precisar de banco
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pw@db.neon.tech/neondb")
    assert client.get("/api/overview?state=CEARA").status_code == 422
    assert (
        client.get("/api/overview?state=CE&start_date=2025-02-01&end_date=2025-01-01").status_code
        == 422
    )
    assert client.get("/api/overview?state=CE&end_date=9999-12-31").status_code == 422
    assert client.get("/api/overview?state=CE&reason=INVALIDO").status_code == 422
    assert client.get("/api/overview?state=CE&origin=EXT").status_code == 422
    assert client.get("/api/timeseries?state=CE&granularity=hourly").status_code == 422
    assert client.get("/api/enterprises?state=CE&limit=500").status_code == 422

    # DATABASE_URL ausente → 503
    monkeypatch.delenv("DATABASE_URL", raising=False)
    resp_missing = client.get("/api/overview?state=CE")
    assert resp_missing.status_code == 503
    assert "DATABASE_URL" in resp_missing.json()["detail"]

    # Erro do PostgreSQL com senha → 503 com senha mascarada
    secret = "S3nhaSuperSecretaApi!"
    dsn = f"postgresql://neondb_owner:{secret}@ep-demo-pooler.neon.tech/neondb?sslmode=require"
    failing_cursor = FakeQueryCursor(
        fail_with=psycopg.OperationalError(f"connection failed for {dsn}")
    )
    _patch_fake_db(monkeypatch, failing_cursor, dsn=dsn)
    resp_err = client.get("/api/overview?state=CE")
    assert resp_err.status_code == 503
    detail = resp_err.json()["detail"]
    assert secret not in detail
    assert "OperationalError" in detail
