"""Consultas SQL parametrizadas e leves para a API serverless FastAPI (Vercel).

Este módulo usa apenas biblioteca padrão + ``psycopg`` v3 (nunca ``pandas`` ou
``pyarrow``) e consulta o PostgreSQL Neon exclusivamente via ``DATABASE_URL``
(pooled). Todos os parâmetros de filtro são passados como bind parameters ``%s``
e qualquer erro de banco tem credenciais mascaradas antes de ser relançado.
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any, Literal
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlparse, urlunparse

import psycopg

VALID_POSTGRES_SCHEMES: frozenset[str] = frozenset({"postgresql", "postgres"})
OFFICIAL_REASON_CODES: tuple[str, ...] = ("REL", "CNF", "ENE", "PAR")
OFFICIAL_ORIGIN_CODES: tuple[str, ...] = ("LOC", "SIS")
VALID_REASON_CODES: frozenset[str] = frozenset(OFFICIAL_REASON_CODES)
VALID_ORIGIN_CODES: frozenset[str] = frozenset(OFFICIAL_ORIGIN_CODES)
VALID_GRANULARITIES: frozenset[str] = frozenset({"daily", "monthly"})
DEFAULT_CONNECT_TIMEOUT_SECONDS = 10
DEFAULT_STATE_CODE = "CE"
METHODOLOGY_VERSION = "v1.0"
GNRA_UNIT_STATUS = "pending_official_confirmation"

_STATE_CODE_PATTERN = re.compile(r"^[A-Z]{2}$")
_POSTGRES_URL_CREDENTIAL_PATTERN = re.compile(
    r"(?i)(postgres(?:ql)?://[^/\s:@]+:)([^@\s]+)(@)"
)
_LIBPQ_PASSWORD_PATTERN = re.compile(
    r"(?i)(\bpassword\s*=\s*)(?:'(?:\\'|[^'])*'|\"(?:\\\"|[^\"])*\"|\S+)"
)

STANDARD_UNITS: dict[str, str] = {
    "geracao_verificada_mwh": "MWh",
    "geracao_referencia_final_mwh": "MWh",
    "minutos_restricao_total": "minutos",
    "taxa_intervalos_restricao_pct": "%",
    "intervalos": "contagem_intervalos_30min",
}

STANDARD_METHODOLOGY: dict[str, Any] = {
    "version": METHODOLOGY_VERSION,
    "gnra_unit_status": GNRA_UNIT_STATUS,
    "timezone_policy": "naive_ons_official_clock",
    "revision_notice": (
        "Dados abertos históricos do ONS estão sujeitos a revisão oficial; "
        "ausência de registro nunca é convertida em zero."
    ),
    "source_attribution": "ONS — Dados Abertos (CC BY 4.0). Este projeto não é produto oficial do ONS/ANEEL.",
}


class ApiDatabaseConfigError(ValueError):
    """DATABASE_URL ausente ou inválida na camada serverless."""


class ApiDatabaseQueryError(RuntimeError):
    """Erro de conexão ou consulta PostgreSQL com mensagem sanitizada."""


def is_valid_postgres_url(raw_url: str) -> bool:
    """Valida se a string de conexão possui esquema PostgreSQL e host válidos."""
    if not isinstance(raw_url, str):
        return False
    candidate = raw_url.strip()
    if not candidate:
        return False
    parsed = urlparse(candidate)
    return parsed.scheme.lower() in VALID_POSTGRES_SCHEMES and bool(parsed.hostname)


def mask_postgres_url(raw_url: str) -> str:
    """Mascara credenciais de uma URL PostgreSQL para uso seguro em erros."""
    parsed = urlparse(raw_url.strip())
    host = parsed.hostname or ""
    if ":" in host:
        host = f"[{host}]"
    port_part = f":{parsed.port}" if parsed.port is not None else ""
    if parsed.username:
        user_part = (
            f"{parsed.username}:***@"
            if parsed.password is not None
            else f"{parsed.username}@"
        )
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


def sanitize_postgres_error(
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
        variants = {
            parsed.password,
            unquote(parsed.password),
            quote(parsed.password, safe=""),
        }
        for variant in sorted(variants, key=len, reverse=True):
            if variant:
                sanitized = sanitized.replace(variant, "***")

    sanitized = _POSTGRES_URL_CREDENTIAL_PATTERN.sub(r"\1***\3", sanitized)
    sanitized = _LIBPQ_PASSWORD_PATTERN.sub(r"\1***", sanitized)
    return f"{type(exc).__name__}: {sanitized}"


def resolve_pooled_database_url(database_url: str | None = None) -> str:
    """Resolve e valida ``DATABASE_URL`` pooled para uso pela API serverless."""
    raw = os.getenv("DATABASE_URL", "") if database_url is None else database_url
    if not isinstance(raw, str) or not is_valid_postgres_url(raw):
        raise ApiDatabaseConfigError(
            "DATABASE_URL não está configurada ou não é uma URL PostgreSQL válida."
        )
    return raw.strip()


def validate_filters(
    *,
    state: str = DEFAULT_STATE_CODE,
    start_date: date | None = None,
    end_date: date | None = None,
    ons_id: str | None = None,
    reason: str | None = None,
    origin: str | None = None,
) -> dict[str, Any]:
    """Valida e normaliza filtros analíticos antes de montar consultas SQL."""
    if not isinstance(state, str):
        raise TypeError("state deve ser uma sigla de UF com 2 letras (ex.: 'CE').")
    clean_state = state.strip().upper()
    if not _STATE_CODE_PATTERN.fullmatch(clean_state):
        raise ValueError("state deve ser uma sigla de UF com 2 letras (ex.: 'CE').")

    if end_date is not None and end_date == date.max:
        raise ValueError(
            "end_date não pode ser 9999-12-31; informe uma data anterior a 9999-12-31."
        )

    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValueError("start_date não pode ser posterior a end_date.")

    clean_ons_id: str | None = None
    if ons_id is not None:
        stripped = ons_id.strip()
        if not stripped:
            raise ValueError("ons_id não pode ser uma string vazia.")
        clean_ons_id = stripped

    clean_reason: str | None = None
    if reason is not None:
        normalized_reason = reason.strip().upper()
        if normalized_reason not in VALID_REASON_CODES:
            allowed = ", ".join(sorted(VALID_REASON_CODES))
            raise ValueError(f"reason inválido: {reason!r}. Valores aceitos: {allowed}.")
        clean_reason = normalized_reason

    clean_origin: str | None = None
    if origin is not None:
        normalized_origin = origin.strip().upper()
        if normalized_origin not in VALID_ORIGIN_CODES:
            allowed = ", ".join(sorted(VALID_ORIGIN_CODES))
            raise ValueError(f"origin inválido: {origin!r}. Valores aceitos: {allowed}.")
        clean_origin = normalized_origin

    return {
        "state": clean_state,
        "start_date": start_date,
        "end_date": end_date,
        "ons_id": clean_ons_id,
        "reason": clean_reason,
        "origin": clean_origin,
    }


def _build_fact_where_clause(
    filters: dict[str, Any],
    *,
    table_alias: str = "f",
    restricted_only: bool = False,
) -> tuple[str, list[Any]]:
    clauses = [f"{table_alias}.estado_sigla = %s"]
    params: list[Any] = [filters["state"]]

    if filters["start_date"] is not None:
        start_dt = datetime.combine(filters["start_date"], datetime.min.time())
        clauses.append(f"{table_alias}.instante >= %s")
        params.append(start_dt)

    if filters["end_date"] is not None:
        end_exclusive = datetime.combine(
            filters["end_date"] + timedelta(days=1),
            datetime.min.time(),
        )
        clauses.append(f"{table_alias}.instante < %s")
        params.append(end_exclusive)

    if filters["ons_id"] is not None:
        clauses.append(f"{table_alias}.ons_id = %s")
        params.append(filters["ons_id"])

    if filters["reason"] is not None:
        clauses.append(f"{table_alias}.restricao_razao_codigo = %s")
        params.append(filters["reason"])

    if filters["origin"] is not None:
        clauses.append(f"{table_alias}.restricao_origem_codigo = %s")
        params.append(filters["origin"])

    if restricted_only:
        clauses.append(f"{table_alias}.possui_restricao_classificada = TRUE")

    return " AND ".join(clauses), params


def _serialize_filters(filters: dict[str, Any]) -> dict[str, Any]:
    return {
        "state": filters["state"],
        "start_date": None if filters["start_date"] is None else filters["start_date"].isoformat(),
        "end_date": None if filters["end_date"] is None else filters["end_date"].isoformat(),
        "ons_id": filters["ons_id"],
        "reason": filters["reason"],
        "origin": filters["origin"],
    }


def _to_optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _to_optional_iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _escape_like_pattern(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _run_read_query(
    callback: Callable[[Any], Any],
    *,
    database_url: str | None = None,
    connect_timeout: int = DEFAULT_CONNECT_TIMEOUT_SECONDS,
    connect_fn: Callable[..., Any] | None = None,
) -> Any:
    resolved_url = resolve_pooled_database_url(database_url)
    masked_target = mask_postgres_url(resolved_url)
    connector = psycopg.connect if connect_fn is None else connect_fn

    try:
        with (
            connector(resolved_url, connect_timeout=connect_timeout) as conn,
            conn.cursor() as cursor,
        ):
            return callback(cursor)
    except psycopg.Error as exc:
        safe_detail = sanitize_postgres_error(
            exc,
            raw_url=resolved_url,
            masked_url=masked_target,
        )
        raise ApiDatabaseQueryError(
            f"Falha ao consultar PostgreSQL ({masked_target}): {safe_detail}"
        ) from None


def query_overview(
    *,
    state: str = DEFAULT_STATE_CODE,
    start_date: date | None = None,
    end_date: date | None = None,
    ons_id: str | None = None,
    reason: str | None = None,
    origin: str | None = None,
    database_url: str | None = None,
    connect_fn: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Retorna indicadores consolidados do recorte sem converter ausência em zero."""
    filters = validate_filters(
        state=state,
        start_date=start_date,
        end_date=end_date,
        ons_id=ons_id,
        reason=reason,
        origin=origin,
    )
    where_sql, params = _build_fact_where_clause(filters, table_alias="f")

    sql = f"""
    SELECT
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
        SUM(f.minutos_restricao_total) FILTER (WHERE f.possui_restricao_classificada) AS minutos_restricao_total,
        MIN(f.instante) AS primeiro_instante,
        MAX(f.instante) AS ultimo_instante
    FROM fact_restricoes AS f
    WHERE {where_sql}
    """

    def _exec(cursor: Any) -> tuple[Any, ...] | None:
        cursor.execute(sql, params)
        return cursor.fetchone()

    row = _run_read_query(_exec, database_url=database_url, connect_fn=connect_fn)
    total_intervalos = int(row[0]) if row and row[0] is not None else 0
    has_data = total_intervalos > 0

    if not has_data:
        summary: dict[str, Any] = {
            "total_intervalos": 0,
            "intervalos_com_restricao": None,
            "intervalos_sem_restricao": None,
            "taxa_intervalos_restricao_pct": None,
            "empreendimentos_observados": 0,
            "empreendimentos_com_restricao": None,
            "intervalos_elegiveis_geracao": None,
            "intervalos_elegiveis_referencia_final": None,
            "intervalos_elegiveis_gnra": None,
            "geracao_verificada_mwh": None,
            "geracao_referencia_final_mwh": None,
            "minutos_restricao_total": None,
            "primeiro_instante": None,
            "ultimo_instante": None,
        }
    else:
        assert row is not None
        summary = {
            "total_intervalos": total_intervalos,
            "intervalos_com_restricao": int(row[1]),
            "intervalos_sem_restricao": int(row[2]),
            "taxa_intervalos_restricao_pct": _to_optional_float(row[3]),
            "empreendimentos_observados": int(row[4]),
            "empreendimentos_com_restricao": int(row[5]),
            "intervalos_elegiveis_geracao": int(row[6]),
            "intervalos_elegiveis_referencia_final": int(row[7]),
            "intervalos_elegiveis_gnra": int(row[8]),
            "geracao_verificada_mwh": _to_optional_float(row[9]),
            "geracao_referencia_final_mwh": _to_optional_float(row[10]),
            "minutos_restricao_total": _to_optional_float(row[11]),
            "primeiro_instante": _to_optional_iso(row[12]),
            "ultimo_instante": _to_optional_iso(row[13]),
        }

    return {
        "has_data": has_data,
        "filters": _serialize_filters(filters),
        "units": STANDARD_UNITS,
        "methodology": STANDARD_METHODOLOGY,
        "summary": summary,
    }


def query_timeseries(
    *,
    state: str = DEFAULT_STATE_CODE,
    granularity: Literal["daily", "monthly"] = "daily",
    start_date: date | None = None,
    end_date: date | None = None,
    ons_id: str | None = None,
    reason: str | None = None,
    origin: str | None = None,
    database_url: str | None = None,
    connect_fn: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Retorna série temporal diária ou mensal pré-agregada no PostgreSQL."""
    if granularity not in VALID_GRANULARITIES:
        raise ValueError("granularity deve ser 'daily' ou 'monthly'.")

    filters = validate_filters(
        state=state,
        start_date=start_date,
        end_date=end_date,
        ons_id=ons_id,
        reason=reason,
        origin=origin,
    )
    where_sql, params = _build_fact_where_clause(filters, table_alias="f")

    bucket_expr = (
        "DATE(f.instante)"
        if granularity == "daily"
        else "DATE_TRUNC('month', f.instante)::DATE"
    )

    sql = f"""
    SELECT
        {bucket_expr} AS periodo_referencia,
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
        SUM(f.geracao_verificada_mwh) FILTER (WHERE f.elegivel_geracao_verificada) AS geracao_verificada_mwh,
        SUM(f.geracao_referencia_final_mwh) FILTER (WHERE f.elegivel_referencia_final) AS geracao_referencia_final_mwh,
        SUM(f.minutos_restricao_total) FILTER (WHERE f.possui_restricao_classificada) AS minutos_restricao_total
    FROM fact_restricoes AS f
    WHERE {where_sql}
    GROUP BY {bucket_expr}
    ORDER BY periodo_referencia ASC
    """

    def _exec(cursor: Any) -> list[tuple[Any, ...]]:
        cursor.execute(sql, params)
        return list(cursor.fetchall())

    rows = _run_read_query(_exec, database_url=database_url, connect_fn=connect_fn)
    items = [
        {
            "periodo_referencia": _to_optional_iso(row[0]),
            "total_intervalos": int(row[1]),
            "intervalos_com_restricao": int(row[2]),
            "intervalos_sem_restricao": int(row[3]),
            "taxa_intervalos_restricao_pct": _to_optional_float(row[4]),
            "empreendimentos_observados": int(row[5]),
            "empreendimentos_com_restricao": int(row[6]),
            "intervalos_elegiveis_geracao": int(row[7]),
            "intervalos_elegiveis_referencia_final": int(row[8]),
            "geracao_verificada_mwh": _to_optional_float(row[9]),
            "geracao_referencia_final_mwh": _to_optional_float(row[10]),
            "minutos_restricao_total": _to_optional_float(row[11]),
        }
        for row in rows
    ]

    return {
        "has_data": len(items) > 0,
        "granularity": granularity,
        "filters": _serialize_filters(filters),
        "units": STANDARD_UNITS,
        "methodology": STANDARD_METHODOLOGY,
        "items": items,
    }


def query_enterprises(
    *,
    state: str = DEFAULT_STATE_CODE,
    start_date: date | None = None,
    end_date: date | None = None,
    reason: str | None = None,
    origin: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    database_url: str | None = None,
    connect_fn: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Retorna ranking paginado de empreendimentos/conjuntos por ``ons_id``."""
    if isinstance(limit, bool) or not isinstance(limit, int) or not (1 <= limit <= 200):
        raise ValueError("limit deve ser um inteiro entre 1 e 200.")
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise ValueError("offset deve ser um inteiro maior ou igual a zero.")

    filters = validate_filters(
        state=state,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        origin=origin,
    )
    where_sql, params = _build_fact_where_clause(filters, table_alias="f")

    clean_search: str | None = None
    if search is not None and search.strip():
        clean_search = search.strip()
        like_param = _escape_like_pattern(clean_search)
        where_sql += " AND (d.usina_nome ILIKE %s ESCAPE '\\' OR f.ons_id ILIKE %s ESCAPE '\\')"
        params.extend([like_param, like_param])

    count_sql = f"""
    SELECT COUNT(DISTINCT f.ons_id) AS total_enterprises
    FROM fact_restricoes AS f
    INNER JOIN dim_empreendimentos AS d
        ON d.ons_id = f.ons_id
    WHERE {where_sql}
    """

    sql = f"""
    SELECT
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
    WHERE {where_sql}
    GROUP BY
        f.ons_id,
        d.usina_nome,
        d.ceg,
        d.tipo_identificador,
        d.elegivel_enriquecimento_aneel
    ORDER BY
        intervalos_com_restricao DESC,
        geracao_verificada_mwh DESC NULLS LAST,
        f.ons_id ASC
    LIMIT %s OFFSET %s
    """
    query_params = [*params, limit, offset]

    def _exec(cursor: Any) -> tuple[int, list[tuple[Any, ...]]]:
        cursor.execute(count_sql, params)
        count_row = cursor.fetchone()
        total = int(count_row[0]) if count_row and count_row[0] is not None else 0
        if total == 0 or offset >= total:
            return total, []
        cursor.execute(sql, query_params)
        return total, list(cursor.fetchall())

    total_enterprises, rows = _run_read_query(
        _exec,
        database_url=database_url,
        connect_fn=connect_fn,
    )
    items = [
        {
            "ons_id": str(row[0]),
            "usina_nome": str(row[1]),
            "ceg": str(row[2]),
            "tipo_identificador": str(row[3]),
            "elegivel_enriquecimento_aneel": bool(row[4]),
            "total_intervalos": int(row[5]),
            "intervalos_com_restricao": int(row[6]),
            "taxa_intervalos_restricao_pct": _to_optional_float(row[7]),
            "intervalos_elegiveis_geracao": int(row[8]),
            "intervalos_elegiveis_referencia_final": int(row[9]),
            "geracao_verificada_mwh": _to_optional_float(row[10]),
            "geracao_referencia_final_mwh": _to_optional_float(row[11]),
            "minutos_restricao_total": _to_optional_float(row[12]),
        }
        for row in rows
    ]

    serialized_filters = _serialize_filters(filters)
    serialized_filters["search"] = clean_search

    return {
        "has_data": total_enterprises > 0,
        "filters": serialized_filters,
        "pagination": {
            "total": total_enterprises,
            "limit": limit,
            "offset": offset,
        },
        "units": STANDARD_UNITS,
        "methodology": STANDARD_METHODOLOGY,
        "items": items,
    }


def query_reasons(
    *,
    state: str = DEFAULT_STATE_CODE,
    start_date: date | None = None,
    end_date: date | None = None,
    ons_id: str | None = None,
    include_descriptions: bool = True,
    include_zero_official_codes: bool = True,
    database_url: str | None = None,
    connect_fn: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Retorna distribuição de intervalos restritos por razão (REL/CNF/ENE/PAR) e origem (LOC/SIS).

    Quando ``include_zero_official_codes=True`` (padrão), espelha o contrato do
    Pandas em ``src.metrics.summarize_reasons_and_origins``: códigos oficiais sem
    ocorrência (como ``PAR`` no Ceará em janeiro/2025) são incluídos com
    ``intervalos_com_restricao = 0`` e energia/minutos como ``None`` (nunca ``0.0``).
    """
    filters = validate_filters(
        state=state,
        start_date=start_date,
        end_date=end_date,
        ons_id=ons_id,
    )
    where_sql, params = _build_fact_where_clause(
        filters,
        table_alias="f",
        restricted_only=True,
    )

    reasons_sql = f"""
    SELECT
        f.restricao_razao_codigo,
        f.restricao_origem_codigo,
        COUNT(*) AS intervalos_com_restricao,
        COUNT(DISTINCT f.ons_id) AS empreendimentos_afetados,
        COUNT(*) FILTER (WHERE f.elegivel_geracao_verificada) AS intervalos_elegiveis_geracao,
        COUNT(*) FILTER (WHERE f.elegivel_referencia_final) AS intervalos_elegiveis_referencia_final,
        SUM(f.geracao_verificada_mwh) FILTER (WHERE f.elegivel_geracao_verificada) AS geracao_verificada_mwh,
        SUM(f.geracao_referencia_final_mwh) FILTER (WHERE f.elegivel_referencia_final) AS geracao_referencia_final_mwh,
        SUM(f.minutos_restricao_total) AS minutos_restricao_total
    FROM fact_restricoes AS f
    WHERE {where_sql}
    GROUP BY
        f.restricao_razao_codigo,
        f.restricao_origem_codigo
    ORDER BY
        intervalos_com_restricao DESC,
        f.restricao_razao_codigo ASC,
        f.restricao_origem_codigo ASC NULLS LAST
    """

    by_reason_sql = f"""
    SELECT
        f.restricao_razao_codigo,
        COUNT(*) AS intervalos_com_restricao,
        COUNT(DISTINCT f.ons_id) AS empreendimentos_afetados,
        SUM(f.geracao_verificada_mwh) FILTER (WHERE f.elegivel_geracao_verificada) AS geracao_verificada_mwh,
        SUM(f.geracao_referencia_final_mwh) FILTER (WHERE f.elegivel_referencia_final) AS geracao_referencia_final_mwh,
        SUM(f.minutos_restricao_total) AS minutos_restricao_total
    FROM fact_restricoes AS f
    WHERE {where_sql}
    GROUP BY f.restricao_razao_codigo
    ORDER BY intervalos_com_restricao DESC, f.restricao_razao_codigo ASC
    """

    by_origin_sql = f"""
    SELECT
        f.restricao_origem_codigo,
        COUNT(*) AS intervalos_com_restricao,
        COUNT(DISTINCT f.ons_id) AS empreendimentos_afetados,
        SUM(f.geracao_verificada_mwh) FILTER (WHERE f.elegivel_geracao_verificada) AS geracao_verificada_mwh,
        SUM(f.geracao_referencia_final_mwh) FILTER (WHERE f.elegivel_referencia_final) AS geracao_referencia_final_mwh,
        SUM(f.minutos_restricao_total) AS minutos_restricao_total
    FROM fact_restricoes AS f
    WHERE {where_sql}
    GROUP BY f.restricao_origem_codigo
    ORDER BY intervalos_com_restricao DESC, f.restricao_origem_codigo ASC NULLS LAST
    """

    descriptions_sql = f"""
    SELECT
        f.restricao_razao_codigo,
        f.restricao_origem_codigo,
        f.restricao_descricao,
        COUNT(*) AS intervalos_com_restricao
    FROM fact_restricoes AS f
    WHERE {where_sql}
      AND f.restricao_descricao IS NOT NULL
      AND BTRIM(f.restricao_descricao) <> ''
    GROUP BY
        f.restricao_razao_codigo,
        f.restricao_origem_codigo,
        f.restricao_descricao
    ORDER BY intervalos_com_restricao DESC
    LIMIT 10
    """

    def _exec(
        cursor: Any,
    ) -> tuple[
        list[tuple[Any, ...]],
        list[tuple[Any, ...]],
        list[tuple[Any, ...]],
        list[tuple[Any, ...]],
    ]:
        cursor.execute(reasons_sql, params)
        reason_rows = list(cursor.fetchall())
        cursor.execute(by_reason_sql, params)
        by_reason_rows = list(cursor.fetchall())
        cursor.execute(by_origin_sql, params)
        by_origin_rows = list(cursor.fetchall())
        desc_rows: list[tuple[Any, ...]] = []
        if include_descriptions:
            cursor.execute(descriptions_sql, params)
            desc_rows = list(cursor.fetchall())
        return reason_rows, by_reason_rows, by_origin_rows, desc_rows

    reason_rows, by_reason_rows, by_origin_rows, desc_rows = _run_read_query(
        _exec,
        database_url=database_url,
        connect_fn=connect_fn,
    )
    total_restricted = sum(int(row[2]) for row in reason_rows)
    has_observed_restrictions = total_restricted > 0

    items = [
        {
            "restricao_razao_codigo": row[0],
            "restricao_origem_codigo": row[1],
            "intervalos_com_restricao": int(row[2]),
            "participacao_restricoes_pct": (
                round(100.0 * int(row[2]) / total_restricted, 4)
                if total_restricted > 0
                else None
            ),
            "empreendimentos_afetados": int(row[3]),
            "intervalos_elegiveis_geracao": int(row[4]),
            "intervalos_elegiveis_referencia_final": int(row[5]),
            "geracao_verificada_mwh": _to_optional_float(row[6]),
            "geracao_referencia_final_mwh": _to_optional_float(row[7]),
            "minutos_restricao_total": _to_optional_float(row[8]),
        }
        for row in reason_rows
    ]

    if include_zero_official_codes:
        present_item_reasons = {
            str(item["restricao_razao_codigo"])
            for item in items
            if item["restricao_razao_codigo"] is not None
        }
        for code in OFFICIAL_REASON_CODES:
            if code not in present_item_reasons:
                items.append(
                    {
                        "restricao_razao_codigo": code,
                        "restricao_origem_codigo": None,
                        "intervalos_com_restricao": 0,
                        "participacao_restricoes_pct": (
                            0.0 if has_observed_restrictions else None
                        ),
                        "empreendimentos_afetados": 0,
                        "intervalos_elegiveis_geracao": 0,
                        "intervalos_elegiveis_referencia_final": 0,
                        "geracao_verificada_mwh": None,
                        "geracao_referencia_final_mwh": None,
                        "minutos_restricao_total": None,
                    }
                )

    def _build_dimension_list(
        rows: list[tuple[Any, ...]],
        *,
        code_key: str,
        official_codes: tuple[str, ...],
    ) -> list[dict[str, Any]]:
        result = [
            {
                code_key: row[0],
                "intervalos_com_restricao": int(row[1]),
                "participacao_restricoes_pct": (
                    round(100.0 * int(row[1]) / total_restricted, 4)
                    if total_restricted > 0
                    else None
                ),
                "empreendimentos_afetados": int(row[2]),
                "geracao_verificada_mwh": _to_optional_float(row[3]),
                "geracao_referencia_final_mwh": _to_optional_float(row[4]),
                "minutos_restricao_total": _to_optional_float(row[5]),
            }
            for row in rows
        ]
        if include_zero_official_codes:
            present = {
                str(entry[code_key]) for entry in result if entry[code_key] is not None
            }
            for code in official_codes:
                if code not in present:
                    result.append(
                        {
                            code_key: code,
                            "intervalos_com_restricao": 0,
                            "participacao_restricoes_pct": (
                                0.0 if has_observed_restrictions else None
                            ),
                            "empreendimentos_afetados": 0,
                            "geracao_verificada_mwh": None,
                            "geracao_referencia_final_mwh": None,
                            "minutos_restricao_total": None,
                        }
                    )
        result.sort(
            key=lambda entry: (
                -entry["intervalos_com_restricao"],
                "" if entry[code_key] is None else str(entry[code_key]),
            )
        )
        return result

    by_reason = _build_dimension_list(
        by_reason_rows,
        code_key="restricao_razao_codigo",
        official_codes=OFFICIAL_REASON_CODES,
    )
    by_origin = _build_dimension_list(
        by_origin_rows,
        code_key="restricao_origem_codigo",
        official_codes=OFFICIAL_ORIGIN_CODES,
    )

    top_descriptions = [
        {
            "restricao_razao_codigo": row[0],
            "restricao_origem_codigo": row[1],
            "restricao_descricao": str(row[2]),
            "intervalos_com_restricao": int(row[3]),
        }
        for row in desc_rows
    ]

    return {
        "has_data": has_observed_restrictions,
        "filters": _serialize_filters(filters),
        "units": STANDARD_UNITS,
        "methodology": STANDARD_METHODOLOGY,
        "total_intervalos_com_restricao": (
            total_restricted if has_observed_restrictions else None
        ),
        "by_reason": by_reason,
        "by_origin": by_origin,
        "items": items,
        "top_descriptions": top_descriptions,
    }


def query_quality(
    *,
    state: str = DEFAULT_STATE_CODE,
    start_date: date | None = None,
    end_date: date | None = None,
    database_url: str | None = None,
    connect_fn: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Retorna cobertura, elegibilidade, nulos e histórico recente de execuções ETL."""
    filters = validate_filters(
        state=state,
        start_date=start_date,
        end_date=end_date,
    )
    where_sql, params = _build_fact_where_clause(filters, table_alias="f")

    coverage_sql = f"""
    SELECT
        COUNT(*) AS total_intervalos,
        COUNT(*) FILTER (WHERE f.elegivel_geracao_verificada) AS elegivel_geracao_verificada,
        COUNT(*) FILTER (WHERE f.elegivel_referencia_final) AS elegivel_referencia_final,
        COUNT(*) FILTER (WHERE NOT f.elegivel_referencia_final) AS sem_referencia_final,
        COUNT(*) FILTER (WHERE f.elegivel_gnra) AS elegivel_gnra,
        COUNT(*) FILTER (WHERE f.possui_restricao_classificada) AS possui_restricao_classificada,
        COUNT(DISTINCT f.ons_id) AS total_empreendimentos,
        COUNT(DISTINCT f.ons_id) FILTER (WHERE f.elegivel_enriquecimento_aneel) AS empreendimentos_com_ceg,
        COUNT(DISTINCT f.ons_id) FILTER (WHERE NOT f.elegivel_enriquecimento_aneel) AS conjuntos_sem_ceg,
        MIN(f.instante) AS primeiro_instante,
        MAX(f.instante) AS ultimo_instante
    FROM fact_restricoes AS f
    WHERE {where_sql}
    """

    executions_sql = """
    SELECT
        execucao_id,
        fonte,
        estado_sigla,
        ano_referencia,
        mes_referencia,
        arquivo_bruto_nome,
        arquivo_bruto_sha256,
        coletado_em_utc,
        processado_em_utc,
        carregado_em_utc,
        linhas_entrada,
        linhas_saida,
        linhas_carregadas,
        gnra_unit_status,
        metodologia_versao
    FROM etl_execucoes
    WHERE estado_sigla = %s
      AND status = 'concluida'
    ORDER BY ano_referencia DESC, mes_referencia DESC, carregado_em_utc DESC
    LIMIT 24
    """

    latest_timestamps_sql = """
    SELECT
        MAX(carregado_em_utc) AS last_loaded_at_utc,
        MAX(coletado_em_utc) AS last_collected_at_utc
    FROM etl_execucoes
    WHERE estado_sigla = %s
      AND status = 'concluida'
    """

    def _exec(
        cursor: Any,
    ) -> tuple[
        tuple[Any, ...] | None,
        tuple[Any, ...] | None,
        list[tuple[Any, ...]],
    ]:
        cursor.execute(coverage_sql, params)
        cov_row = cursor.fetchone()
        cursor.execute(latest_timestamps_sql, [filters["state"]])
        latest_row = cursor.fetchone()
        cursor.execute(executions_sql, [filters["state"]])
        exec_rows = list(cursor.fetchall())
        return cov_row, latest_row, exec_rows

    cov_row, latest_row, exec_rows = _run_read_query(
        _exec,
        database_url=database_url,
        connect_fn=connect_fn,
    )

    total_intervalos = int(cov_row[0]) if cov_row and cov_row[0] is not None else 0
    has_data = total_intervalos > 0

    if not has_data:
        coverage: dict[str, Any] = {
            "total_intervalos": 0,
            "elegivel_geracao_verificada": None,
            "elegivel_referencia_final": None,
            "sem_referencia_final": None,
            "elegivel_gnra": None,
            "possui_restricao_classificada": None,
            "taxa_cobertura_referencia_final_pct": None,
            "taxa_cobertura_gnra_pct": None,
            "total_empreendimentos": 0,
            "empreendimentos_com_ceg": None,
            "conjuntos_sem_ceg": None,
            "primeiro_instante": None,
            "ultimo_instante": None,
        }
    else:
        assert cov_row is not None
        elig_ref = int(cov_row[2])
        elig_gnra = int(cov_row[4])
        coverage = {
            "total_intervalos": total_intervalos,
            "elegivel_geracao_verificada": int(cov_row[1]),
            "elegivel_referencia_final": elig_ref,
            "sem_referencia_final": int(cov_row[3]),
            "elegivel_gnra": elig_gnra,
            "possui_restricao_classificada": int(cov_row[5]),
            "taxa_cobertura_referencia_final_pct": round(
                100.0 * elig_ref / total_intervalos,
                4,
            ),
            "taxa_cobertura_gnra_pct": round(
                100.0 * elig_gnra / total_intervalos,
                4,
            ),
            "total_empreendimentos": int(cov_row[6]),
            "empreendimentos_com_ceg": int(cov_row[7]),
            "conjuntos_sem_ceg": int(cov_row[8]),
            "primeiro_instante": _to_optional_iso(cov_row[9]),
            "ultimo_instante": _to_optional_iso(cov_row[10]),
        }

    executions = [
        {
            "execucao_id": int(r[0]),
            "fonte": str(r[1]),
            "estado_sigla": str(r[2]),
            "ano_referencia": int(r[3]),
            "mes_referencia": int(r[4]),
            "arquivo_bruto_nome": str(r[5]),
            "arquivo_bruto_sha256": str(r[6]),
            "coletado_em_utc": _to_optional_iso(r[7]),
            "processado_em_utc": _to_optional_iso(r[8]),
            "carregado_em_utc": _to_optional_iso(r[9]),
            "linhas_entrada": int(r[10]),
            "linhas_saida": int(r[11]),
            "linhas_carregadas": int(r[12]),
            "gnra_unit_status": str(r[13]),
            "metodologia_versao": str(r[14]),
        }
        for r in exec_rows
    ]

    last_loaded_at = _to_optional_iso(latest_row[0]) if latest_row else None
    last_collected_at = _to_optional_iso(latest_row[1]) if latest_row else None

    return {
        "has_data": has_data,
        "filters": _serialize_filters(filters),
        "units": STANDARD_UNITS,
        "methodology": STANDARD_METHODOLOGY,
        "last_loaded_at_utc": last_loaded_at,
        "last_collected_at_utc": last_collected_at,
        "coverage": coverage,
        "executions": executions,
    }
