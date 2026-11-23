"""Indicadores analíticos, séries temporais e conciliação auditável da GNRa (Fase 4).

Todas as funções deste módulo consomem exclusivamente tabelas já padronizadas,
tipadas e validadas pela Fase 3 (``src/transform.py`` + ``src/validate.py``).

Regras metodológicas aplicadas:
- Nunca somar ``MWmed`` diretamente como se fosse energia; as agregações
  energéticas usam exclusivamente colunas ``*_mwh`` calculadas com
  ``duracao_horas`` validada.
- Nunca converter ausência de registros elegíveis em ``0.0`` (``min_count=1``).
- Preservar linhas sem restrição (``dropna=False``) nas distribuições por
  razão/origem para que as somas fechem exatamente em ``total_rows``.
- Não agregar a GNRa oficial (``geracao_nao_realizada_apurada``) em MWh
  enquanto sua unidade não for confirmada documentalmente; manter a conciliação
  com ``max(geracao_referencia_mwmed - geracao_mwmed, 0)`` separada e auditável.
"""

from __future__ import annotations

from typing import Literal, TypedDict

import numpy as np
import pandas as pd

from src.transform import GNRA_UNIT_STATUS, SourceSchemaError


_REQUIRED_BASE_COLUMNS: tuple[str, ...] = (
    "ons_id",
    "instante",
    "geracao_mwmed",
    "geracao_referencia_mwmed",
    "geracao_referencia_final_mwmed",
    "geracao_verificada_mwh",
    "geracao_referencia_final_mwh",
    "geracao_nao_realizada_apurada",
    "restricao_razao_codigo",
    "restricao_origem_codigo",
    "elegivel_geracao_verificada",
    "elegivel_referencia_final",
    "possui_restricao_classificada",
    "elegivel_gnra",
)


class IntervalCountsSummary(TypedDict):
    """Contagens estruturadas de patamares por mês, dia, hora, razão e origem."""

    total_rows: int
    restricted_rows: int
    unrestricted_rows: int
    by_month: pd.DataFrame
    by_day: pd.DataFrame
    by_hour: pd.DataFrame
    by_reason_origin: pd.DataFrame


class GnraReconciliationReport(TypedDict):
    """Relatório separado de conciliação da GNRa oficial sem agregação energética prematura."""

    gnra_unit_status: str
    energy_aggregation_allowed: bool
    tolerance: float
    total_rows: int
    eligible_gnra_rows: int
    reconciled_rows: int
    missing_reference_or_generation_rows: int
    exact_match_rows: int
    divergent_rows: int
    negative_reference_minus_generation_rows: int
    max_absolute_error: float | None


def _validate_metrics_dataframe(dataframe: pd.DataFrame) -> None:
    """Valida esquema, unicidade de colunas e tipagem mínima exigida para métricas."""
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe deve ser um pandas.DataFrame.")
    if not dataframe.columns.is_unique:
        duplicated = sorted(
            str(col) for col in dataframe.columns[dataframe.columns.duplicated()].unique()
        )
        raise SourceSchemaError(
            f"O DataFrame contém nomes de colunas duplicados: {duplicated}."
        )

    missing = [col for col in _REQUIRED_BASE_COLUMNS if col not in dataframe.columns]
    if missing:
        raise SourceSchemaError(
            f"Colunas obrigatórias da Fase 3 ausentes para cálculo de métricas: {missing}."
        )

    if isinstance(dataframe["instante"].dtype, pd.DatetimeTZDtype) or not (
        pd.api.types.is_datetime64_any_dtype(dataframe["instante"].dtype)
    ):
        raise SourceSchemaError(
            "A coluna 'instante' deve estar convertida para datetime64 sem fuso "
            f"(naive) antes de calcular métricas (dtype atual: {dataframe['instante'].dtype})."
        )

    numeric_cols = (
        "geracao_mwmed",
        "geracao_referencia_mwmed",
        "geracao_referencia_final_mwmed",
        "geracao_verificada_mwh",
        "geracao_referencia_final_mwh",
        "geracao_nao_realizada_apurada",
    )
    for col in numeric_cols:
        if not pd.api.types.is_numeric_dtype(
            dataframe[col].dtype
        ) or pd.api.types.is_bool_dtype(dataframe[col].dtype):
            raise SourceSchemaError(
                f"A coluna numérica {col!r} precisa estar tipada antes do cálculo de métricas "
                f"(dtype atual: {dataframe[col].dtype})."
            )

    bool_cols = (
        "elegivel_geracao_verificada",
        "elegivel_referencia_final",
        "possui_restricao_classificada",
        "elegivel_gnra",
    )
    for col in bool_cols:
        if not pd.api.types.is_bool_dtype(dataframe[col].dtype):
            raise SourceSchemaError(
                f"A coluna de elegibilidade {col!r} deve ser booleana "
                f"(dtype atual: {dataframe[col].dtype})."
            )


def summarize_interval_counts(dataframe: pd.DataFrame) -> IntervalCountsSummary:
    """Conta linhas por mês, dia, hora, razão e origem de restrição sem perdas silenciosas.

    Em ``by_reason_origin``, ``dropna=False`` garante que intervalos sem código de
    restrição apareçam explicitamente com ``<NA>`` e que a soma feche em ``total_rows``.
    """
    _validate_metrics_dataframe(dataframe)

    total_rows = len(dataframe)
    restricted_flag = (
        dataframe["possui_restricao_classificada"].fillna(False).astype(bool)
    )
    restricted_rows = int(restricted_flag.sum())
    unrestricted_rows = total_rows - restricted_rows

    work = pd.DataFrame(
        {
            "ons_id": dataframe["ons_id"].astype("string"),
            "instante": dataframe["instante"],
            "restrito": restricted_flag.astype("int64"),
            "restricao_razao_codigo": dataframe["restricao_razao_codigo"].astype("string"),
            "restricao_origem_codigo": dataframe["restricao_origem_codigo"].astype("string"),
        },
        index=dataframe.index,
    )

    valid_time = work.dropna(subset=["instante"]).copy()
    if valid_time.empty:
        by_month = pd.DataFrame(
            columns=[
                "ano_mes",
                "total_intervalos",
                "intervalos_com_restricao",
                "empreendimentos_distintos",
            ]
        )
        by_day = pd.DataFrame(
            columns=[
                "data",
                "total_intervalos",
                "intervalos_com_restricao",
                "empreendimentos_distintos",
            ]
        )
        by_hour = pd.DataFrame(
            columns=["hora", "total_intervalos", "intervalos_com_restricao"]
        )
    else:
        valid_time["ano_mes"] = valid_time["instante"].dt.strftime("%Y-%m")
        valid_time["data"] = valid_time["instante"].dt.strftime("%Y-%m-%d")
        valid_time["hora"] = valid_time["instante"].dt.hour.astype("int64")

        by_month = (
            valid_time.groupby("ano_mes", sort=True, as_index=False)
            .agg(
                total_intervalos=("restrito", "size"),
                intervalos_com_restricao=("restrito", "sum"),
                empreendimentos_distintos=("ons_id", "nunique"),
            )
        )
        by_day = (
            valid_time.groupby("data", sort=True, as_index=False)
            .agg(
                total_intervalos=("restrito", "size"),
                intervalos_com_restricao=("restrito", "sum"),
                empreendimentos_distintos=("ons_id", "nunique"),
            )
        )
        by_hour = (
            valid_time.groupby("hora", sort=True, as_index=False)
            .agg(
                total_intervalos=("restrito", "size"),
                intervalos_com_restricao=("restrito", "sum"),
            )
        )

    if work.empty:
        by_reason_origin = pd.DataFrame(
            columns=[
                "restricao_razao_codigo",
                "restricao_origem_codigo",
                "total_intervalos",
                "percentual_total",
            ]
        )
    else:
        by_reason_origin = (
            work.groupby(
                ["restricao_razao_codigo", "restricao_origem_codigo"],
                dropna=False,
                sort=True,
                as_index=False,
            )
            .agg(total_intervalos=("restrito", "size"))
            .sort_values(
                by=["total_intervalos", "restricao_razao_codigo"],
                ascending=[False, True],
                na_position="last",
            )
            .reset_index(drop=True)
        )
        by_reason_origin["percentual_total"] = (
            (by_reason_origin["total_intervalos"] / float(total_rows)) * 100.0
        ).round(4)

    return {
        "total_rows": total_rows,
        "restricted_rows": restricted_rows,
        "unrestricted_rows": unrestricted_rows,
        "by_month": by_month,
        "by_day": by_day,
        "by_hour": by_hour,
        "by_reason_origin": by_reason_origin,
    }


def build_generation_series(
    dataframe: pd.DataFrame,
    *,
    granularity: Literal["day", "month"] = "day",
) -> pd.DataFrame:
    """Constrói série diária ou mensal da geração verificada e referência final em MWh.

    Soma exclusivamente registros elegíveis (``elegivel_geracao_verificada`` e
    ``elegivel_referencia_final``) usando ``min_count=1`` para que períodos sem
    nenhum registro elegível retornem ``pd.NA`` em vez de ``0.0`` falso.

    Args:
        dataframe: Tabela tratada pela Fase 3.
        granularity: ``"day"`` (``YYYY-MM-DD``) ou ``"month"`` (``YYYY-MM``).

    Returns:
        ``DataFrame`` ordenado cronologicamente com unidades explícitas (``MWh`` e ``%``).
    """
    _validate_metrics_dataframe(dataframe)
    if granularity not in {"day", "month"}:
        raise ValueError(
            f"granularity inválida: {granularity!r}. Use 'day' ou 'month'."
        )

    output_columns = [
        "periodo",
        "total_intervalos",
        "intervalos_elegiveis_geracao",
        "cobertura_geracao_pct",
        "geracao_verificada_mwh",
        "intervalos_elegiveis_referencia_final",
        "geracao_referencia_final_mwh",
        "intervalos_com_restricao",
        "empreendimentos_distintos",
    ]

    valid_time_mask = ~dataframe["instante"].isna()
    if not bool(valid_time_mask.any()):
        return pd.DataFrame(columns=output_columns)

    subset = dataframe.loc[valid_time_mask]
    date_format = "%Y-%m-%d" if granularity == "day" else "%Y-%m"

    elig_ger = subset["elegivel_geracao_verificada"].fillna(False).astype(bool)
    elig_ref = subset["elegivel_referencia_final"].fillna(False).astype(bool)
    restrito = subset["possui_restricao_classificada"].fillna(False).astype(bool)

    work = pd.DataFrame(
        {
            "periodo": subset["instante"].dt.strftime(date_format),
            "ons_id": subset["ons_id"].astype("string"),
            "elig_ger": elig_ger.astype("int64"),
            "elig_ref": elig_ref.astype("int64"),
            "restrito": restrito.astype("int64"),
            "geracao_mwh_elegivel": subset["geracao_verificada_mwh"]
            .astype("Float64")
            .where(elig_ger, pd.NA),
            "ref_final_mwh_elegivel": subset["geracao_referencia_final_mwh"]
            .astype("Float64")
            .where(elig_ref, pd.NA),
        },
        index=subset.index,
    )

    def _sum_preserving_na(series: pd.Series) -> object:
        if series.dropna().empty:
            return pd.NA
        return float(series.sum(min_count=1))

    grouped = work.groupby("periodo", sort=True, as_index=False).agg(
        total_intervalos=("elig_ger", "size"),
        intervalos_elegiveis_geracao=("elig_ger", "sum"),
        geracao_verificada_mwh=("geracao_mwh_elegivel", _sum_preserving_na),
        intervalos_elegiveis_referencia_final=("elig_ref", "sum"),
        geracao_referencia_final_mwh=("ref_final_mwh_elegivel", _sum_preserving_na),
        intervalos_com_restricao=("restrito", "sum"),
        empreendimentos_distintos=("ons_id", "nunique"),
    )

    grouped["cobertura_geracao_pct"] = (
        (grouped["intervalos_elegiveis_geracao"] / grouped["total_intervalos"]) * 100.0
    ).round(4)
    grouped["geracao_verificada_mwh"] = grouped["geracao_verificada_mwh"].astype("Float64")
    grouped["geracao_referencia_final_mwh"] = grouped[
        "geracao_referencia_final_mwh"
    ].astype("Float64")

    return grouped[output_columns]


def reconcile_gnra_values(
    dataframe: pd.DataFrame,
    *,
    tolerance: float = 1e-9,
) -> GnraReconciliationReport:
    """Concilia a GNRa oficial com ``max(geracao_referencia_mwmed - geracao_mwmed, 0)``.

    Esta função **não** soma a GNRa como MWh e **não** substitui o valor oficial
    publicado pelo ONS. Serve exclusivamente para auditar consistência numérica
    e expor divergências ou casos em que a geração verificada excede a referência.

    Args:
        dataframe: Tabela tratada pela Fase 3.
        tolerance: Tolerância absoluta máxima para considerar coincidência numérica.

    Returns:
        Relatório ``GnraReconciliationReport`` com contagens e erro máximo observado.
    """
    _validate_metrics_dataframe(dataframe)
    if (
        isinstance(tolerance, bool)
        or not isinstance(tolerance, (int, float))
        or tolerance < 0
    ):
        raise ValueError("tolerance deve ser um número maior ou igual a zero.")

    total_rows = len(dataframe)
    elig_gnra = dataframe["elegivel_gnra"].fillna(False).astype(bool)
    eligible_df = dataframe.loc[elig_gnra]
    eligible_gnra_rows = len(eligible_df)

    if eligible_gnra_rows == 0:
        return {
            "gnra_unit_status": GNRA_UNIT_STATUS,
            "energy_aggregation_allowed": False,
            "tolerance": float(tolerance),
            "total_rows": total_rows,
            "eligible_gnra_rows": 0,
            "reconciled_rows": 0,
            "missing_reference_or_generation_rows": 0,
            "exact_match_rows": 0,
            "divergent_rows": 0,
            "negative_reference_minus_generation_rows": 0,
            "max_absolute_error": None,
        }

    ref_vals = eligible_df["geracao_referencia_mwmed"].astype("Float64")
    ger_vals = eligible_df["geracao_mwmed"].astype("Float64")
    gnra_vals = eligible_df["geracao_nao_realizada_apurada"].astype("Float64")

    can_reconcile = (~ref_vals.isna()) & (~ger_vals.isna()) & (~gnra_vals.isna())
    reconciled_rows = int(can_reconcile.sum())
    missing_inputs = eligible_gnra_rows - reconciled_rows

    if reconciled_rows == 0:
        return {
            "gnra_unit_status": GNRA_UNIT_STATUS,
            "energy_aggregation_allowed": False,
            "tolerance": float(tolerance),
            "total_rows": total_rows,
            "eligible_gnra_rows": eligible_gnra_rows,
            "reconciled_rows": 0,
            "missing_reference_or_generation_rows": missing_inputs,
            "exact_match_rows": 0,
            "divergent_rows": 0,
            "negative_reference_minus_generation_rows": 0,
            "max_absolute_error": None,
        }

    ref_arr = ref_vals.loc[can_reconcile].to_numpy(dtype="float64")
    ger_arr = ger_vals.loc[can_reconcile].to_numpy(dtype="float64")
    gnra_arr = gnra_vals.loc[can_reconcile].to_numpy(dtype="float64")

    raw_diff = ref_arr - ger_arr
    negative_diff_rows = int(np.sum(raw_diff < 0.0))
    recalculated = np.maximum(raw_diff, 0.0)
    abs_errors = np.abs(gnra_arr - recalculated)

    exact_match_rows = int(np.sum(abs_errors <= float(tolerance)))
    divergent_rows = reconciled_rows - exact_match_rows
    max_abs_error = float(np.max(abs_errors))

    return {
        "gnra_unit_status": GNRA_UNIT_STATUS,
        "energy_aggregation_allowed": False,
        "tolerance": float(tolerance),
        "total_rows": total_rows,
        "eligible_gnra_rows": eligible_gnra_rows,
        "reconciled_rows": reconciled_rows,
        "missing_reference_or_generation_rows": missing_inputs,
        "exact_match_rows": exact_match_rows,
        "divergent_rows": divergent_rows,
        "negative_reference_minus_generation_rows": negative_diff_rows,
        "max_absolute_error": max_abs_error,
    }
