"""Aplicação serverless FastAPI na Vercel para servir indicadores validados.

A API é intencionalmente leve (sem importar pandas ou pyarrow) para respeitar
o limite de bundle (250 MB) e timeout (10 s) do plano gratuito da Vercel.
Todos os dados analíticos são consultados no PostgreSQL (Neon) via DATABASE_URL
depois de processados e validados pelo pipeline ETL Python.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI


app = FastAPI(
    title="Renewable Energy Intelligence API",
    version="0.1.0",
    description=(
        "API de leitura sobre restrições de geração eólica (constrained-off) "
        "a partir de dados abertos validados do ONS armazenados em PostgreSQL."
    ),
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


@app.get("/api/health")
def health_check() -> dict[str, Any]:
    """Verifica a disponibilidade da API serverless e se DATABASE_URL está configurada.

    Não expõe credenciais nem retorna métricas analíticas fictícias.
    """
    database_configured = bool(os.getenv("DATABASE_URL", "").strip())
    return {
        "status": "ok",
        "service": "renewable-energy-intelligence-api",
        "database_engine": "postgresql",
        "database_configured": database_configured,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
