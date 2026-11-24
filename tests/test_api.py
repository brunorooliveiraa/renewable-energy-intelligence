"""Testes da camada HTTP serverless FastAPI (Vercel)."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

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
