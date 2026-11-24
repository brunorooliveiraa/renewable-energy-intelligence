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

import math
from pathlib import Path
from typing import Literal, TypedDict

import numpy as np
import pandas as pd

from src.transform import (
    CEG_AGGREGATE_PLACEHOLDER,
    GNRA_UNIT_STATUS,
    SourceSchemaError,
)

OFFICIAL_REASON_CODES: tuple[str, ...] = ("REL", "CNF", "ENE", "PAR")
OFFICIAL_ORIGIN_CODES: tuple[str, ...] = ("LOC", "SIS")
_VALID_RANKING_SORT_COLUMNS: frozenset[str] = frozenset(
    {
        "intervalos_com_restricao",
        "geracao_verificada_mwh",
        "geracao_referencia_final_mwh",
        "taxa_intervalos_restricao_pct",
    }
)

_REQUIRED_BASE_COLUMNS: tuple[str, ...] = (
    "ons_id",
    "usina_nome",
    "ceg",
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
    "elegivel_enriquecimento_aneel",
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


class CoverageSummary(TypedDict):
    """Resumo auditável de cobertura dos indicadores e ausência de referências."""

    total_rows: int
    elegivel_geracao_verificada_rows: int
    cobertura_geracao_verificada_pct: float
    elegivel_referencia_final_rows: int
    sem_referencia_final_rows: int
    cobertura_referencia_final_pct: float
    referencia_base_preenchida_rows: int
    sem_referencia_base_rows: int
    cobertura_referencia_base_pct: float
    possui_restricao_classificada_rows: int
    restricao_com_referencia_final_rows: int
    restricao_sem_referencia_final_rows: int
    elegivel_gnra_rows: int
    elegivel_enriquecimento_aneel_rows: int
    sem_ceg_individual_rows: int


class ReasonsAndOriginsSummary(TypedDict):
    """Comparativo estruturado por razão oficial (REL/CNF/ENE/PAR) e origem (LOC/SIS)."""

    total_restricted_rows: int
    by_reason: pd.DataFrame
    by_origin: pd.DataFrame
    by_reason_and_origin: pd.DataFrame


class PeakRestrictionsSummary(TypedDict):
    """Dias e horários com maior concentração de intervalos restritos."""

    top_n: int
    top_days: pd.DataFrame
    top_hours: pd.DataFrame


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
        "elegivel_enriquecimento_aneel",
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
        or not math.isfinite(tolerance)
        or tolerance < 0
    ):
        raise ValueError("tolerance deve ser um número finito maior ou igual a zero.")

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


def _pct(numerator: int, denominator: int) -> float:
    """Calcula percentual arredondado a 4 casas, retornando 0.0 quando denominador == 0."""
    if denominator <= 0:
        return 0.0
    return round((numerator / float(denominator)) * 100.0, 4)


def _sum_preserving_na(series: pd.Series) -> object:
    """Soma uma série numérica retornando ``pd.NA`` se todos os valores forem nulos."""
    if series.dropna().empty:
        return pd.NA
    return float(series.sum(min_count=1))


def summarize_coverage(dataframe: pd.DataFrame) -> CoverageSummary:
    """Contabiliza a cobertura das linhas elegíveis e das linhas sem referência.

    Separa explicitamente a cobertura da referência base
    (``geracao_referencia_mwmed``) da referência final
    (``geracao_referencia_final_mwmed``, preenchida oficialmente apenas em ``REL``),
    além de distinguir restrições com e sem referência final.
    """
    _validate_metrics_dataframe(dataframe)

    total_rows = len(dataframe)
    elig_ger = dataframe["elegivel_geracao_verificada"].fillna(False).astype(bool)
    elig_ref_final = dataframe["elegivel_referencia_final"].fillna(False).astype(bool)
    restrito = dataframe["possui_restricao_classificada"].fillna(False).astype(bool)
    elig_gnra = dataframe["elegivel_gnra"].fillna(False).astype(bool)
    elig_aneel = dataframe["elegivel_enriquecimento_aneel"].fillna(False).astype(bool)
    ref_base_present = ~dataframe["geracao_referencia_mwmed"].isna()

    elig_ger_rows = int(elig_ger.sum())
    elig_ref_final_rows = int(elig_ref_final.sum())
    ref_base_rows = int(ref_base_present.sum())
    restrito_rows = int(restrito.sum())
    restrito_com_ref_final = int((restrito & elig_ref_final).sum())
    elig_aneel_rows = int(elig_aneel.sum())

    return {
        "total_rows": total_rows,
        "elegivel_geracao_verificada_rows": elig_ger_rows,
        "cobertura_geracao_verificada_pct": _pct(elig_ger_rows, total_rows),
        "elegivel_referencia_final_rows": elig_ref_final_rows,
        "sem_referencia_final_rows": total_rows - elig_ref_final_rows,
        "cobertura_referencia_final_pct": _pct(elig_ref_final_rows, total_rows),
        "referencia_base_preenchida_rows": ref_base_rows,
        "sem_referencia_base_rows": total_rows - ref_base_rows,
        "cobertura_referencia_base_pct": _pct(ref_base_rows, total_rows),
        "possui_restricao_classificada_rows": restrito_rows,
        "restricao_com_referencia_final_rows": restrito_com_ref_final,
        "restricao_sem_referencia_final_rows": restrito_rows - restrito_com_ref_final,
        "elegivel_gnra_rows": int(elig_gnra.sum()),
        "elegivel_enriquecimento_aneel_rows": elig_aneel_rows,
        "sem_ceg_individual_rows": total_rows - elig_aneel_rows,
    }


def build_enterprise_ranking(
    dataframe: pd.DataFrame,
    *,
    sort_by: Literal[
        "intervalos_com_restricao",
        "geracao_verificada_mwh",
        "geracao_referencia_final_mwh",
        "taxa_intervalos_restricao_pct",
    ] = "intervalos_com_restricao",
) -> pd.DataFrame:
    """Cria ranking agregado por ``ons_id`` + nome de exibição, classificando usina vs conjunto.

    Regras metodológicas:
    - A chave de agregação é exclusivamente ``ons_id`` (se o nome de exibição mudar
      ao longo do tempo, adota o nome mais recente ordenado por ``instante`` sem
      duplicar o empreendimento).
    - Classifica ``tipo_empreendimento`` com base estrita no ``ceg``:
      ``"conjunto_sem_ceg"`` (``ceg == '-'``), ``"usina_com_ceg"`` (CEG válido)
      ou ``"nao_classificado"`` (ausente/vazio).
    - Não soma GNRa como MWh; expõe ``intervalos_elegiveis_gnra`` e, quando
      disponível, ``minutos_restricao_total_sum`` em minutos.
    """
    _validate_metrics_dataframe(dataframe)
    if sort_by not in _VALID_RANKING_SORT_COLUMNS:
        raise ValueError(
            f"sort_by inválido: {sort_by!r}. Valores aceitos: "
            f"{sorted(_VALID_RANKING_SORT_COLUMNS)}."
        )

    output_columns = [
        "ons_id",
        "usina_nome",
        "ceg",
        "tipo_empreendimento",
        "total_intervalos",
        "intervalos_com_restricao",
        "taxa_intervalos_restricao_pct",
        "geracao_verificada_mwh",
        "geracao_referencia_final_mwh",
        "intervalos_elegiveis_gnra",
        "minutos_restricao_total_sum",
    ]

    valid_ons_mask = (~dataframe["ons_id"].isna()) & (
        dataframe["ons_id"].astype("string").str.strip() != ""
    )
    if not bool(valid_ons_mask.any()):
        return pd.DataFrame(columns=output_columns)

    subset = dataframe.loc[valid_ons_mask].copy()
    subset = subset.sort_values(["ons_id", "instante"], kind="mergesort")

    elig_ger = subset["elegivel_geracao_verificada"].fillna(False).astype(bool)
    elig_ref = subset["elegivel_referencia_final"].fillna(False).astype(bool)
    restrito = subset["possui_restricao_classificada"].fillna(False).astype(bool)
    elig_gnra = subset["elegivel_gnra"].fillna(False).astype(bool)

    if "minutos_restricao_total" in subset.columns:
        minutos_total = pd.to_numeric(
            subset["minutos_restricao_total"], errors="coerce"
        ).astype("Float64")
    else:
        minutos_total = pd.Series(pd.NA, index=subset.index, dtype="Float64")

    work = pd.DataFrame(
        {
            "ons_id": subset["ons_id"].astype("string"),
            "usina_nome": subset["usina_nome"].astype("string"),
            "ceg": subset["ceg"].astype("string"),
            "restrito": restrito.astype("int64"),
            "elig_gnra": elig_gnra.astype("int64"),
            "geracao_mwh_elegivel": subset["geracao_verificada_mwh"]
            .astype("Float64")
            .where(elig_ger, pd.NA),
            "ref_final_mwh_elegivel": subset["geracao_referencia_final_mwh"]
            .astype("Float64")
            .where(elig_ref, pd.NA),
            "minutos_total": minutos_total,
        },
        index=subset.index,
    )

    def _last_non_null(series: pd.Series) -> object:
        non_null = series.dropna()
        if non_null.empty:
            return pd.NA
        return str(non_null.iloc[-1])

    grouped = work.groupby("ons_id", sort=True, as_index=False).agg(
        usina_nome=("usina_nome", _last_non_null),
        ceg=("ceg", _last_non_null),
        total_intervalos=("restrito", "size"),
        intervalos_com_restricao=("restrito", "sum"),
        geracao_verificada_mwh=("geracao_mwh_elegivel", _sum_preserving_na),
        geracao_referencia_final_mwh=("ref_final_mwh_elegivel", _sum_preserving_na),
        intervalos_elegiveis_gnra=("elig_gnra", "sum"),
        minutos_restricao_total_sum=("minutos_total", _sum_preserving_na),
    )

    def _classify_ceg(value: object) -> str:
        if pd.isna(value):
            return "nao_classificado"
        text = str(value).strip()
        if not text:
            return "nao_classificado"
        if text == CEG_AGGREGATE_PLACEHOLDER:
            return "conjunto_sem_ceg"
        return "usina_com_ceg"

    grouped["usina_nome"] = grouped["usina_nome"].astype("string")
    grouped["ceg"] = grouped["ceg"].astype("string")
    grouped["tipo_empreendimento"] = grouped["ceg"].map(_classify_ceg).astype("string")
    grouped["taxa_intervalos_restricao_pct"] = (
        (grouped["intervalos_com_restricao"] / grouped["total_intervalos"]) * 100.0
    ).round(4)
    grouped["geracao_verificada_mwh"] = grouped["geracao_verificada_mwh"].astype("Float64")
    grouped["geracao_referencia_final_mwh"] = grouped[
        "geracao_referencia_final_mwh"
    ].astype("Float64")
    grouped["minutos_restricao_total_sum"] = grouped[
        "minutos_restricao_total_sum"
    ].astype("Float64")

    sort_order = [sort_by, "geracao_verificada_mwh", "ons_id"]
    ascending = [False, False, True]
    if sort_by == "geracao_verificada_mwh":
        sort_order = ["geracao_verificada_mwh", "intervalos_com_restricao", "ons_id"]

    ranked = (
        grouped[output_columns]
        .sort_values(by=sort_order, ascending=ascending, na_position="last")
        .reset_index(drop=True)
    )
    return ranked


def summarize_reasons_and_origins(
    dataframe: pd.DataFrame,
    *,
    include_zero_official_codes: bool = True,
) -> ReasonsAndOriginsSummary:
    """Compara razões oficiais (REL, CNF, ENE, PAR) e origens (LOC, SIS) nos registros restritos.

    Quando ``include_zero_official_codes=True`` (padrão), códigos oficiais sem
    ocorrência no período (como ``PAR`` no Ceará em janeiro/2025) aparecem com
    ``intervalos_com_restricao = 0`` e ``geracao_verificada_mwh = pd.NA`` (nunca
    ``0.0`` falso para energia).

    Raises:
        TypeError: Quando ``dataframe`` não é ``pd.DataFrame`` ou
            ``include_zero_official_codes`` não é ``bool``.
        SourceSchemaError: Quando colunas obrigatórias da Fase 3 estão ausentes.
    """
    _validate_metrics_dataframe(dataframe)
    if not isinstance(include_zero_official_codes, bool):
        raise TypeError("include_zero_official_codes deve ser booleano (True ou False).")

    restrito_mask = (
        dataframe["possui_restricao_classificada"].fillna(False).astype(bool)
    )
    restricted = dataframe.loc[restrito_mask]
    total_restricted_rows = len(restricted)

    elig_ger = restricted["elegivel_geracao_verificada"].fillna(False).astype(bool)
    elig_ref = restricted["elegivel_referencia_final"].fillna(False).astype(bool)

    work = pd.DataFrame(
        {
            "ons_id": restricted["ons_id"].astype("string"),
            "restricao_razao_codigo": restricted["restricao_razao_codigo"].astype("string"),
            "restricao_origem_codigo": restricted["restricao_origem_codigo"].astype("string"),
            "geracao_mwh_elegivel": restricted["geracao_verificada_mwh"]
            .astype("Float64")
            .where(elig_ger, pd.NA),
            "ref_final_mwh_elegivel": restricted["geracao_referencia_final_mwh"]
            .astype("Float64")
            .where(elig_ref, pd.NA),
        },
        index=restricted.index,
    )

    def _aggregate_dimension(
        column_name: str,
        official_codes: tuple[str, ...],
    ) -> pd.DataFrame:
        cols = [
            column_name,
            "intervalos_com_restricao",
            "participacao_restricoes_pct",
            "empreendimentos_afetados",
            "geracao_verificada_mwh",
            "geracao_referencia_final_mwh",
        ]
        if work.empty:
            grouped_dim = pd.DataFrame(columns=cols)
        else:
            grouped_dim = work.groupby(
                column_name, dropna=False, sort=True, as_index=False
            ).agg(
                intervalos_com_restricao=("ons_id", "size"),
                empreendimentos_afetados=("ons_id", "nunique"),
                geracao_verificada_mwh=("geracao_mwh_elegivel", _sum_preserving_na),
                geracao_referencia_final_mwh=(
                    "ref_final_mwh_elegivel",
                    _sum_preserving_na,
                ),
            )
            grouped_dim["participacao_restricoes_pct"] = (
                (grouped_dim["intervalos_com_restricao"] / float(total_restricted_rows))
                * 100.0
            ).round(4)

        if include_zero_official_codes:
            present_codes = (
                set(grouped_dim[column_name].dropna().astype(str))
                if not grouped_dim.empty
                else set()
            )
            missing_rows = [
                {
                    column_name: code,
                    "intervalos_com_restricao": 0,
                    "participacao_restricoes_pct": 0.0,
                    "empreendimentos_afetados": 0,
                    "geracao_verificada_mwh": pd.NA,
                    "geracao_referencia_final_mwh": pd.NA,
                }
                for code in official_codes
                if code not in present_codes
            ]
            if missing_rows:
                extra_df = pd.DataFrame(missing_rows)
                grouped_dim = (
                    extra_df
                    if grouped_dim.empty
                    else pd.concat([grouped_dim, extra_df], ignore_index=True)
                )

        if grouped_dim.empty:
            return pd.DataFrame(columns=cols)

        grouped_dim[column_name] = grouped_dim[column_name].astype("string")
        grouped_dim["intervalos_com_restricao"] = grouped_dim[
            "intervalos_com_restricao"
        ].astype("int64")
        grouped_dim["empreendimentos_afetados"] = grouped_dim[
            "empreendimentos_afetados"
        ].astype("int64")
        grouped_dim["participacao_restricoes_pct"] = grouped_dim[
            "participacao_restricoes_pct"
        ].astype("float64")
        grouped_dim["geracao_verificada_mwh"] = grouped_dim[
            "geracao_verificada_mwh"
        ].astype("Float64")
        grouped_dim["geracao_referencia_final_mwh"] = grouped_dim[
            "geracao_referencia_final_mwh"
        ].astype("Float64")

        return (
            grouped_dim[cols]
            .sort_values(
                by=["intervalos_com_restricao", column_name],
                ascending=[False, True],
                na_position="last",
            )
            .reset_index(drop=True)
        )

    by_reason = _aggregate_dimension("restricao_razao_codigo", OFFICIAL_REASON_CODES)
    by_origin = _aggregate_dimension("restricao_origem_codigo", OFFICIAL_ORIGIN_CODES)

    cross_cols = [
        "restricao_razao_codigo",
        "restricao_origem_codigo",
        "intervalos_com_restricao",
        "participacao_restricoes_pct",
        "empreendimentos_afetados",
        "geracao_verificada_mwh",
        "geracao_referencia_final_mwh",
    ]
    if work.empty:
        by_reason_and_origin = pd.DataFrame(columns=cross_cols)
    else:
        by_reason_and_origin = work.groupby(
            ["restricao_razao_codigo", "restricao_origem_codigo"],
            dropna=False,
            sort=True,
            as_index=False,
        ).agg(
            intervalos_com_restricao=("ons_id", "size"),
            empreendimentos_afetados=("ons_id", "nunique"),
            geracao_verificada_mwh=("geracao_mwh_elegivel", _sum_preserving_na),
            geracao_referencia_final_mwh=("ref_final_mwh_elegivel", _sum_preserving_na),
        )
        by_reason_and_origin["participacao_restricoes_pct"] = (
            (
                by_reason_and_origin["intervalos_com_restricao"]
                / float(total_restricted_rows)
            )
            * 100.0
        ).round(4)
        by_reason_and_origin["geracao_verificada_mwh"] = by_reason_and_origin[
            "geracao_verificada_mwh"
        ].astype("Float64")
        by_reason_and_origin["geracao_referencia_final_mwh"] = by_reason_and_origin[
            "geracao_referencia_final_mwh"
        ].astype("Float64")
        by_reason_and_origin = (
            by_reason_and_origin[cross_cols]
            .sort_values(
                by=["intervalos_com_restricao", "restricao_razao_codigo"],
                ascending=[False, True],
                na_position="last",
            )
            .reset_index(drop=True)
        )

    return {
        "total_restricted_rows": total_restricted_rows,
        "by_reason": by_reason,
        "by_origin": by_origin,
        "by_reason_and_origin": by_reason_and_origin,
    }


def identify_peak_restriction_periods(
    dataframe: pd.DataFrame,
    *,
    top_n: int = 5,
) -> PeakRestrictionsSummary:
    """Identifica os ``top_n`` dias e horários com maior concentração de restrições.

    Utiliza exclusivamente grandezas validadas (contagem e taxa de intervalos
    restritos, empreendimentos afetados, geração verificada/referência final em
    MWh e minutos de restrição), sem somar GNRa em MWh.

    Args:
        dataframe: Tabela tratada pela Fase 3.
        top_n: Quantidade máxima de dias e horários a retornar (inteiro >= 1).

    Returns:
        ``PeakRestrictionsSummary`` contendo ``top_days`` e ``top_hours``.
    """
    _validate_metrics_dataframe(dataframe)
    if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n < 1:
        raise ValueError("top_n deve ser um número inteiro maior ou igual a 1.")

    day_columns = [
        "data",
        "total_intervalos",
        "intervalos_com_restricao",
        "taxa_restricao_pct",
        "empreendimentos_afetados",
        "geracao_verificada_mwh",
        "geracao_referencia_final_mwh",
        "minutos_restricao_total_sum",
    ]
    hour_columns = [
        "hora",
        "total_intervalos",
        "intervalos_com_restricao",
        "taxa_restricao_pct",
        "empreendimentos_afetados",
        "geracao_verificada_mwh",
        "minutos_restricao_total_sum",
    ]

    valid_time = dataframe.dropna(subset=["instante"])
    if valid_time.empty:
        return {
            "top_n": top_n,
            "top_days": pd.DataFrame(columns=day_columns),
            "top_hours": pd.DataFrame(columns=hour_columns),
        }

    elig_ger = valid_time["elegivel_geracao_verificada"].fillna(False).astype(bool)
    elig_ref = valid_time["elegivel_referencia_final"].fillna(False).astype(bool)
    restrito = valid_time["possui_restricao_classificada"].fillna(False).astype(bool)

    if "minutos_restricao_total" in valid_time.columns:
        minutos_total = pd.to_numeric(
            valid_time["minutos_restricao_total"], errors="coerce"
        ).astype("Float64")
    else:
        minutos_total = pd.Series(pd.NA, index=valid_time.index, dtype="Float64")

    work = pd.DataFrame(
        {
            "data": valid_time["instante"].dt.strftime("%Y-%m-%d"),
            "hora": valid_time["instante"].dt.hour.astype("int64"),
            "ons_id_restrito": valid_time["ons_id"]
            .astype("string")
            .where(restrito, pd.NA),
            "restrito": restrito.astype("int64"),
            "geracao_mwh_elegivel": valid_time["geracao_verificada_mwh"]
            .astype("Float64")
            .where(elig_ger, pd.NA),
            "ref_final_mwh_elegivel": valid_time["geracao_referencia_final_mwh"]
            .astype("Float64")
            .where(elig_ref, pd.NA),
            "minutos_total": minutos_total,
        },
        index=valid_time.index,
    )

    days_df = work.groupby("data", sort=True, as_index=False).agg(
        total_intervalos=("restrito", "size"),
        intervalos_com_restricao=("restrito", "sum"),
        empreendimentos_afetados=("ons_id_restrito", "nunique"),
        geracao_verificada_mwh=("geracao_mwh_elegivel", _sum_preserving_na),
        geracao_referencia_final_mwh=("ref_final_mwh_elegivel", _sum_preserving_na),
        minutos_restricao_total_sum=("minutos_total", _sum_preserving_na),
    )
    days_df["taxa_restricao_pct"] = (
        (days_df["intervalos_com_restricao"] / days_df["total_intervalos"]) * 100.0
    ).round(4)
    days_df["geracao_verificada_mwh"] = days_df["geracao_verificada_mwh"].astype("Float64")
    days_df["geracao_referencia_final_mwh"] = days_df[
        "geracao_referencia_final_mwh"
    ].astype("Float64")
    days_df["minutos_restricao_total_sum"] = days_df[
        "minutos_restricao_total_sum"
    ].astype("Float64")
    top_days = (
        days_df[day_columns]
        .sort_values(
            by=["intervalos_com_restricao", "taxa_restricao_pct", "data"],
            ascending=[False, False, True],
        )
        .head(top_n)
        .reset_index(drop=True)
    )

    hours_df = work.groupby("hora", sort=True, as_index=False).agg(
        total_intervalos=("restrito", "size"),
        intervalos_com_restricao=("restrito", "sum"),
        empreendimentos_afetados=("ons_id_restrito", "nunique"),
        geracao_verificada_mwh=("geracao_mwh_elegivel", _sum_preserving_na),
        minutos_restricao_total_sum=("minutos_total", _sum_preserving_na),
    )
    hours_df["taxa_restricao_pct"] = (
        (hours_df["intervalos_com_restricao"] / hours_df["total_intervalos"]) * 100.0
    ).round(4)
    hours_df["geracao_verificada_mwh"] = hours_df["geracao_verificada_mwh"].astype("Float64")
    hours_df["minutos_restricao_total_sum"] = hours_df[
        "minutos_restricao_total_sum"
    ].astype("Float64")
    top_hours = (
        hours_df[hour_columns]
        .sort_values(
            by=["intervalos_com_restricao", "taxa_restricao_pct", "hora"],
            ascending=[False, False, True],
        )
        .head(top_n)
        .reset_index(drop=True)
    )

    return {
        "top_n": top_n,
        "top_days": top_days,
        "top_hours": top_hours,
    }


def _svg_bar_chart(
    *,
    title: str,
    subtitle: str,
    unit_label: str,
    labels: list[str],
    values: list[float | None],
    bar_color: str = "#1f6feb",
    negative_bar_color: str = "#dc2626",
) -> str:
    """Gera um gráfico de barras horizontal em SVG puro (sem dependências extras).

    Diferencia visualmente os quatro estados possíveis de cada categoria:
    - ``missing`` (``None`` ou não finito): sem barra, rótulo explícito ``Sem dados``;
    - ``zero`` (``0.0``): marcador fino sobre o eixo zero e rótulo ``0.00``;
    - ``positive`` (``> 0``): barra à direita do eixo zero na cor principal;
    - ``negative`` (``< 0``): barra à esquerda do eixo zero em cor distinta (vermelha).
    """
    width = 960
    margin_left = 190
    margin_right = 120
    margin_top = 75
    row_height = 28
    chart_height = max(len(labels), 1) * row_height
    height = margin_top + chart_height + 45

    finite_values = [v for v in values if v is not None and math.isfinite(v)]
    max_pos = max((v for v in finite_values if v > 0), default=0.0)
    min_neg = min((v for v in finite_values if v < 0), default=0.0)
    has_negatives = min_neg < 0.0

    # Reserva folga à esquerda quando há negativos para o rótulo numérico caber.
    plot_left = margin_left + (70.0 if has_negatives else 0.0)
    usable_width = width - plot_left - margin_right
    span = max_pos + abs(min_neg)
    if span <= 0.0:
        span = 1.0
    zero_x = plot_left + (abs(min_neg) / span) * usable_width

    def _escape(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    lines = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="{_escape(title)}">'
        ),
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="20" y="30" font-family="sans-serif" font-size="18" font-weight="bold" fill="#111827">{_escape(title)}</text>',
        f'<text x="20" y="52" font-family="sans-serif" font-size="12" fill="#4b5563">{_escape(subtitle)} | Unidade: {_escape(unit_label)}</text>',
        (
            f'<line x1="{zero_x:.2f}" y1="{margin_top - 4}" '
            f'x2="{zero_x:.2f}" y2="{margin_top + chart_height + 4}" '
            'stroke="#9ca3af" stroke-width="1"/>'
        ),
    ]
    for idx, (label, val) in enumerate(zip(labels, values, strict=True)):
        y = margin_top + idx * row_height
        lines.append(
            f'<text x="{margin_left - 10}" y="{y + 16}" text-anchor="end" '
            f'font-family="sans-serif" font-size="12" fill="#1f2937">{_escape(label)}</text>'
        )
        if val is None or not math.isfinite(val):
            lines.append(
                f'<text x="{zero_x + 8:.2f}" y="{y + 16}" data-state="missing" '
                'font-family="sans-serif" font-size="11" font-style="italic" '
                'fill="#6b7280">Sem dados</text>'
            )
        elif val == 0.0:
            lines.append(
                f'<rect x="{zero_x - 1.0:.2f}" y="{y + 3}" width="2.00" height="18" '
                'rx="1" fill="#6b7280" data-state="zero"/>'
            )
            lines.append(
                f'<text x="{zero_x + 8:.2f}" y="{y + 16}" data-state="zero" '
                'font-family="sans-serif" font-size="11" fill="#374151">0.00</text>'
            )
        elif val > 0.0:
            bar_w = (val / span) * usable_width
            lines.append(
                f'<rect x="{zero_x:.2f}" y="{y + 3}" width="{bar_w:.2f}" height="18" '
                f'rx="3" fill="{bar_color}" data-state="positive"/>'
            )
            lines.append(
                f'<text x="{zero_x + bar_w + 8:.2f}" y="{y + 16}" data-state="positive" '
                f'font-family="sans-serif" font-size="11" fill="#111827">{val:,.2f}</text>'
            )
        else:
            bar_w = (abs(val) / span) * usable_width
            bar_x = zero_x - bar_w
            lines.append(
                f'<rect x="{bar_x:.2f}" y="{y + 3}" width="{bar_w:.2f}" height="18" '
                f'rx="3" fill="{negative_bar_color}" data-state="negative"/>'
            )
            lines.append(
                f'<text x="{bar_x - 6:.2f}" y="{y + 16}" text-anchor="end" data-state="negative" '
                f'font-family="sans-serif" font-size="11" fill="#991b1b">{val:,.2f}</text>'
            )

    lines.append("</svg>\n")
    return "\n".join(lines)


def generate_basic_phase4_charts(
    dataframe: pd.DataFrame,
    output_dir: Path | str,
) -> dict[str, Path]:
    """Gera gráficos básicos exploratórios em SVG a partir da base validada da Fase 3.

    Produz três gráficos autoexplicativos com unidades visíveis (sem dependências
    externas além do Python padrão e Pandas):
    - ``geracao_diaria_mwh.svg``: série diária de geração verificada (MWh);
    - ``restricoes_por_razao.svg``: contagem de intervalos por razão oficial (REL/CNF/ENE/PAR);
    - ``restricoes_por_hora.svg``: incidência horária de restrições (00h–23h).

    Raises:
        TypeError: Quando ``dataframe`` não é ``pd.DataFrame`` ou ``output_dir``
            não é ``Path`` nem ``str``.
        ValueError: Quando ``output_dir`` é vazio ou aponta para um arquivo existente.
        SourceSchemaError: Quando colunas obrigatórias da Fase 3 estão ausentes.
    """
    _validate_metrics_dataframe(dataframe)
    if isinstance(output_dir, str):
        if not output_dir.strip():
            raise ValueError("output_dir não pode ser uma string vazia.")
        target_dir = Path(output_dir.strip())
    elif isinstance(output_dir, Path):
        target_dir = output_dir
    else:
        raise TypeError("output_dir deve ser um objeto Path ou string não vazia.")

    if target_dir.exists() and not target_dir.is_dir():
        raise ValueError(f"output_dir aponta para um arquivo existente: {target_dir}.")
    target_dir.mkdir(parents=True, exist_ok=True)

    daily = build_generation_series(dataframe, granularity="day")
    reasons = summarize_reasons_and_origins(dataframe)["by_reason"]
    counts = summarize_interval_counts(dataframe)

    daily_path = target_dir / "geracao_diaria_mwh.svg"
    daily_svg = _svg_bar_chart(
        title="Geração Verificada Diária — Ceará (ONS)",
        subtitle="Apenas patamares elegíveis (MWmed × 0,5 h)",
        unit_label="MWh",
        labels=daily["periodo"].astype(str).tolist(),
        values=[
            None if pd.isna(v) else float(v) for v in daily["geracao_verificada_mwh"]
        ],
        bar_color="#0f766e",
    )
    daily_path.write_text(daily_svg, encoding="utf-8")

    reason_path = target_dir / "restricoes_por_razao.svg"
    reason_svg = _svg_bar_chart(
        title="Intervalos com Restrição por Razão Oficial (ONS)",
        subtitle="Distribuição completa do domínio oficial (REL, CNF, ENE, PAR)",
        unit_label="intervalos semi-horários",
        labels=reasons["restricao_razao_codigo"].astype(str).tolist(),
        values=[float(v) for v in reasons["intervalos_com_restricao"]],
        bar_color="#b45309",
    )
    reason_path.write_text(reason_svg, encoding="utf-8")

    hour_path = target_dir / "restricoes_por_hora.svg"
    by_hour = counts["by_hour"]
    hour_svg = _svg_bar_chart(
        title="Perfil Horário de Intervalos com Restrição (00h–23h)",
        subtitle="Horário oficial publicado pelo ONS (timezone-naive)",
        unit_label="intervalos semi-horários",
        labels=[f"{int(h):02d}h" for h in by_hour["hora"]],
        values=[float(v) for v in by_hour["intervalos_com_restricao"]],
        bar_color="#1d4ed8",
    )
    hour_path.write_text(hour_svg, encoding="utf-8")

    return {
        "geracao_diaria_mwh": daily_path,
        "restricoes_por_razao": reason_path,
        "restricoes_por_hora": hour_path,
    }
