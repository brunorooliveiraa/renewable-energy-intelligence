"""Aplicação serverless FastAPI na Vercel para servir indicadores validados.

A API é intencionalmente leve (sem importar pandas ou pyarrow) para respeitar
o limite de bundle (250 MB) e timeout (300 s) do plano gratuito da Vercel.
Todos os dados analíticos são consultados no PostgreSQL (Neon) via DATABASE_URL
depois de processados e validados pelo pipeline ETL Python.
"""

from __future__ import annotations

import os
from datetime import UTC, date, datetime
from typing import Annotated, Any, Literal

from fastapi import FastAPI, HTTPException, Query

from api.queries import (
    DEFAULT_STATE_CODE,
    ApiDatabaseConfigError,
    ApiDatabaseQueryError,
    is_valid_postgres_url,
    query_enterprises,
    query_overview,
    query_quality,
    query_reasons,
    query_timeseries,
)

app = FastAPI(
    title="Renewable Energy Intelligence API",
    version="0.2.0",
    description=(
        "API de leitura sobre restrições de geração eólica (constrained-off) "
        "a partir de dados abertos validados do ONS armazenados em PostgreSQL."
    ),
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


def _execute_endpoint(fn: Any, **kwargs: Any) -> dict[str, Any]:
    """Executa consulta parametrizada traduzindo erros para status HTTP semânticos."""
    try:
        return fn(**kwargs)
    except (ApiDatabaseConfigError, ApiDatabaseQueryError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@app.get("/api/health")
def health_check() -> dict[str, Any]:
    """Verifica a disponibilidade da API serverless e se DATABASE_URL é uma URL PostgreSQL válida.

    Não expõe credenciais nem retorna métricas analíticas fictícias.
    """
    database_configured = is_valid_postgres_url(os.getenv("DATABASE_URL", ""))
    return {
        "status": "ok",
        "service": "renewable-energy-intelligence-api",
        "database_engine": "postgresql",
        "database_configured": database_configured,
        "timestamp_utc": datetime.now(UTC).isoformat(),
    }


@app.get("/api/overview")
def get_overview(
    state: Annotated[str, Query(description="Sigla da UF (ex.: CE).")] = DEFAULT_STATE_CODE,
    start_date: Annotated[
        date | None, Query(description="Data inicial inclusiva (YYYY-MM-DD).")
    ] = None,
    end_date: Annotated[
        date | None, Query(description="Data final inclusiva (YYYY-MM-DD).")
    ] = None,
    ons_id: Annotated[
        str | None, Query(description="Identificador ONS da usina ou conjunto.")
    ] = None,
    reason: Annotated[
        str | None, Query(description="Código oficial de razão (REL, CNF, ENE, PAR).")
    ] = None,
    origin: Annotated[
        str | None, Query(description="Código oficial de origem (LOC, SIS).")
    ] = None,
) -> dict[str, Any]:
    """Retorna cartões consolidados de geração verificada (MWh), cobertura e restrições."""
    return _execute_endpoint(
        query_overview,
        state=state,
        start_date=start_date,
        end_date=end_date,
        ons_id=ons_id,
        reason=reason,
        origin=origin,
    )


@app.get("/api/timeseries")
def get_timeseries(
    state: Annotated[str, Query(description="Sigla da UF (ex.: CE).")] = DEFAULT_STATE_CODE,
    granularity: Annotated[
        Literal["daily", "monthly"],
        Query(description="Granularidade temporal: daily ou monthly."),
    ] = "daily",
    start_date: Annotated[
        date | None, Query(description="Data inicial inclusiva (YYYY-MM-DD).")
    ] = None,
    end_date: Annotated[
        date | None, Query(description="Data final inclusiva (YYYY-MM-DD).")
    ] = None,
    ons_id: Annotated[
        str | None, Query(description="Identificador ONS da usina ou conjunto.")
    ] = None,
    reason: Annotated[
        str | None, Query(description="Código oficial de razão (REL, CNF, ENE, PAR).")
    ] = None,
    origin: Annotated[
        str | None, Query(description="Código oficial de origem (LOC, SIS).")
    ] = None,
) -> dict[str, Any]:
    """Retorna série temporal diária ou mensal pré-agregada no PostgreSQL."""
    return _execute_endpoint(
        query_timeseries,
        state=state,
        granularity=granularity,
        start_date=start_date,
        end_date=end_date,
        ons_id=ons_id,
        reason=reason,
        origin=origin,
    )


@app.get("/api/enterprises")
def get_enterprises(
    state: Annotated[str, Query(description="Sigla da UF (ex.: CE).")] = DEFAULT_STATE_CODE,
    start_date: Annotated[
        date | None, Query(description="Data inicial inclusiva (YYYY-MM-DD).")
    ] = None,
    end_date: Annotated[
        date | None, Query(description="Data final inclusiva (YYYY-MM-DD).")
    ] = None,
    reason: Annotated[
        str | None, Query(description="Código oficial de razão (REL, CNF, ENE, PAR).")
    ] = None,
    origin: Annotated[
        str | None, Query(description="Código oficial de origem (LOC, SIS).")
    ] = None,
    search: Annotated[
        str | None, Query(description="Busca parcial por nome ou ons_id.")
    ] = None,
    limit: Annotated[
        int, Query(ge=1, le=200, description="Máximo de registros retornados (1 a 200).")
    ] = 50,
    offset: Annotated[
        int, Query(ge=0, description="Deslocamento para paginação.")
    ] = 0,
) -> dict[str, Any]:
    """Retorna ranking paginado de empreendimentos/conjuntos por ons_id."""
    return _execute_endpoint(
        query_enterprises,
        state=state,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        origin=origin,
        search=search,
        limit=limit,
        offset=offset,
    )


@app.get("/api/reasons")
def get_reasons(
    state: Annotated[str, Query(description="Sigla da UF (ex.: CE).")] = DEFAULT_STATE_CODE,
    start_date: Annotated[
        date | None, Query(description="Data inicial inclusiva (YYYY-MM-DD).")
    ] = None,
    end_date: Annotated[
        date | None, Query(description="Data final inclusiva (YYYY-MM-DD).")
    ] = None,
    ons_id: Annotated[
        str | None, Query(description="Identificador ONS da usina ou conjunto.")
    ] = None,
    include_descriptions: Annotated[
        bool, Query(description="Inclui top 10 descrições qualitativas (dsc_restricao).")
    ] = True,
    include_zero_official_codes: Annotated[
        bool,
        Query(
            description=(
                "Inclui códigos oficiais sem ocorrência (ex.: PAR) com 0 intervalos "
                "e energia nula, espelhando o contrato do Pandas."
            )
        ),
    ] = True,
) -> dict[str, Any]:
    """Retorna distribuição de restrições por razão (REL/CNF/ENE/PAR) e origem (LOC/SIS)."""
    return _execute_endpoint(
        query_reasons,
        state=state,
        start_date=start_date,
        end_date=end_date,
        ons_id=ons_id,
        include_descriptions=include_descriptions,
        include_zero_official_codes=include_zero_official_codes,
    )


@app.get("/api/quality")
def get_quality(
    state: Annotated[str, Query(description="Sigla da UF (ex.: CE).")] = DEFAULT_STATE_CODE,
    start_date: Annotated[
        date | None, Query(description="Data inicial inclusiva (YYYY-MM-DD).")
    ] = None,
    end_date: Annotated[
        date | None, Query(description="Data final inclusiva (YYYY-MM-DD).")
    ] = None,
) -> dict[str, Any]:
    """Retorna cobertura, elegibilidade, última coleta e histórico de execuções ETL."""
    return _execute_endpoint(
        query_quality,
        state=state,
        start_date=start_date,
        end_date=end_date,
    )
