"""Regras explícitas de qualidade, unicidade de chave e detecção de anomalias.

Este módulo nunca descarta registros silenciosamente. Todas as verificações
produzem relatórios estruturados com contagens e amostras auditáveis, falhando
explicitamente quando há violação crítica sob política estrita.
"""

from __future__ import annotations

from typing import Literal, TypedDict

import pandas as pd

from src.transform import MWMED_INTERNAL_COLUMNS, SourceSchemaError


CANDIDATE_KEY_COLUMNS: tuple[str, ...] = ("ons_id", "instante")
VALID_RESTRICTION_REASON_CODES: frozenset[str] = frozenset({"REL", "CNF", "ENE", "PAR"})
VALID_RESTRICTION_ORIGIN_CODES: frozenset[str] = frozenset({"LOC", "SIS"})
NON_NEGATIVE_MWMED_COLUMNS: tuple[str, ...] = MWMED_INTERNAL_COLUMNS
_MAX_ANOMALY_SAMPLES = 5
_VALID_DUPLICATE_POLICIES: frozenset[str] = frozenset(
    {"raise", "report", "drop_exact_only"}
)


class DuplicateKeyError(ValueError):
    """Foram encontradas duplicidades ou conflitos na chave operacional."""


class DataQualityError(ValueError):
    """Foram detectadas anomalias bloqueantes de qualidade na base."""


class DuplicateKeyReport(TypedDict):
    """Diagnóstico auditável de unicidade na chave operacional (ons_id, instante)."""

    key_columns: tuple[str, ...]
    total_rows: int
    null_key_rows: int
    duplicate_key_groups: int
    duplicate_key_rows: int
    exact_duplicate_rows_dropped: int
    conflicting_key_groups: int
    conflicting_key_rows: int
    resolution_policy: Literal["raise", "report", "drop_exact_only"]
    sample_duplicate_keys: tuple[tuple[str, ...], ...]


class QualityCheckReport(TypedDict):
    """Relatório estruturado de nulos, negativos, códigos desconhecidos e datas."""

    total_rows: int
    expected_year: int | None
    expected_month: int | None
    null_counts_by_column: dict[str, int]
    null_percent_by_column: dict[str, float]
    negative_value_counts: dict[str, int]
    unknown_reason_codes: tuple[str, ...]
    unknown_reason_rows: int
    unknown_origin_codes: tuple[str, ...]
    unknown_origin_rows: int
    reason_without_origin_rows: int
    origin_without_reason_rows: int
    out_of_month_rows: int
    out_of_month_samples: tuple[str, ...]
    observed_min_timestamp: str | None
    observed_max_timestamp: str | None
    has_blocking_anomalies: bool


def check_and_resolve_key_duplicates(
    dataframe: pd.DataFrame,
    *,
    key_columns: tuple[str, ...] = CANDIDATE_KEY_COLUMNS,
    on_duplicate: Literal["raise", "report", "drop_exact_only"] = "raise",
) -> tuple[pd.DataFrame, DuplicateKeyReport]:
    """Verifica duplicidades na chave candidata e aplica a regra de resolução explícita.

    Diferencia três situações sem nunca descartar conflitos silenciosamente:
    1. **Chaves incompletas (`null_key_rows`):** contabilizadas separadamente
       para não serem agrupadas pelo pandas como chaves duplicadas.
    2. **Duplicidade exata de linha inteira:** todas as colunas são idênticas
       (inclusive `NA == NA`).
    3. **Conflito de chave:** mesma chave `(ons_id, instante)`, mas com valores
       divergentes em alguma coluna.

    Políticas suportadas em ``on_duplicate``:
    - ``"raise"`` (padrão): lança ``DuplicateKeyError`` diante de qualquer
      duplicidade na chave (exata ou conflitante).
    - ``"report"``: não remove nenhuma linha e devolve o relatório completo.
    - ``"drop_exact_only"``: remove exclusivamente linhas 100% idênticas em
      todas as colunas, mas **ainda lança ``DuplicateKeyError``** se existir
      qualquer conflito de chave com valores divergentes.

    Args:
        dataframe: Tabela padronizada a inspecionar.
        key_columns: Colunas que compõem a chave operacional candidata.
        on_duplicate: Política de resolução (``"raise"``, ``"report"`` ou
            ``"drop_exact_only"``).

    Returns:
        Tupla ``(result_dataframe, report)``.

    Raises:
        TypeError: Quando ``dataframe`` não é ``pd.DataFrame``.
        ValueError: Quando ``key_columns`` ou ``on_duplicate`` é inválido.
        SourceSchemaError: Quando alguma coluna da chave está ausente.
        DuplicateKeyError: Quando há duplicidades incompatíveis com a política.
    """

    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe deve ser um pandas.DataFrame.")
    if not dataframe.columns.is_unique:
        duplicated_col_names = sorted(
            str(col) for col in dataframe.columns[dataframe.columns.duplicated()].unique()
        )
        raise SourceSchemaError(
            f"O DataFrame contém nomes de colunas duplicados: {duplicated_col_names}."
        )
    if not isinstance(key_columns, tuple) or not key_columns:
        raise ValueError("key_columns deve ser uma tupla não vazia de nomes de coluna.")
    if any(not isinstance(col, str) or not col.strip() for col in key_columns):
        raise ValueError("Todos os nomes em key_columns devem ser strings não vazias.")
    if len(set(key_columns)) != len(key_columns):
        raise ValueError("key_columns não pode conter colunas duplicadas.")
    if on_duplicate not in _VALID_DUPLICATE_POLICIES:
        raise ValueError(
            f"on_duplicate inválido: {on_duplicate!r}. "
            f"Valores aceitos: {sorted(_VALID_DUPLICATE_POLICIES)}."
        )

    missing_keys = [col for col in key_columns if col not in dataframe.columns]
    if missing_keys:
        raise SourceSchemaError(
            f"Colunas da chave candidata ausentes no DataFrame: {missing_keys}."
        )

    result = dataframe.copy()
    total_rows = len(result)
    key_list = list(key_columns)

    # Separa registros com chave incompleta para evitar que NA == NA gere falso positivo.
    null_key_mask = result[key_list].isna().any(axis=1)
    null_key_rows = int(null_key_mask.sum())
    complete_keys_df = result.loc[~null_key_mask]

    duplicate_key_mask = complete_keys_df.duplicated(subset=key_list, keep=False)
    duplicated_subset = complete_keys_df.loc[duplicate_key_mask]
    duplicate_key_rows = int(len(duplicated_subset))

    if duplicate_key_rows == 0:
        report: DuplicateKeyReport = {
            "key_columns": key_columns,
            "total_rows": total_rows,
            "null_key_rows": null_key_rows,
            "duplicate_key_groups": 0,
            "duplicate_key_rows": 0,
            "exact_duplicate_rows_dropped": 0,
            "conflicting_key_groups": 0,
            "conflicting_key_rows": 0,
            "resolution_policy": on_duplicate,
            "sample_duplicate_keys": (),
        }
        return result, report

    # Identifica grupos únicos de chaves duplicadas e separa duplicidades exatas de conflitos.
    unique_dup_keys = duplicated_subset[key_list].drop_duplicates()
    duplicate_key_groups = int(len(unique_dup_keys))
    sample_duplicate_keys = tuple(
        tuple(str(val) for val in row)
        for row in unique_dup_keys.iloc[:_MAX_ANOMALY_SAMPLES].itertuples(
            index=False, name=None
        )
    )

    # Após deduplicar linhas 100% idênticas em todas as colunas, qualquer chave
    # que ainda se repetir possui valores divergentes (conflito real).
    deduped_complete = complete_keys_df.drop_duplicates(keep="first")
    exact_duplicates_count = int(len(complete_keys_df) - len(deduped_complete))

    conflicting_mask = deduped_complete.duplicated(subset=key_list, keep=False)
    conflicting_subset = deduped_complete.loc[conflicting_mask]
    conflicting_key_groups = (
        int(len(conflicting_subset[key_list].drop_duplicates()))
        if not conflicting_subset.empty
        else 0
    )
    conflicting_key_rows = int(len(conflicting_subset))

    if on_duplicate == "raise":
        raise DuplicateKeyError(
            f"Encontradas duplicidades na chave {key_columns}: "
            f"{duplicate_key_groups} grupo(s) ({duplicate_key_rows} linha(s)), "
            f"sendo {conflicting_key_groups} grupo(s) conflitante(s) e "
            f"{exact_duplicates_count} linha(s) exatamente duplicada(s). "
            f"Amostras de chaves: {list(sample_duplicate_keys)}."
        )

    if on_duplicate == "drop_exact_only":
        if conflicting_key_groups > 0:
            raise DuplicateKeyError(
                f"Não é possível resolver automaticamente duplicidades na chave {key_columns}: "
                f"{conflicting_key_groups} grupo(s) possuem valores divergentes "
                f"({conflicting_key_rows} linhas distintas com a mesma chave). "
                f"Amostras: {list(sample_duplicate_keys)}."
            )
        # Mantém linhas de chave nula intactas e remove somente duplicatas exatas.
        exact_dup_mask = (~null_key_mask) & result.duplicated(keep="first")
        cleaned = result.loc[~exact_dup_mask].reset_index(drop=True).copy()
        report = {
            "key_columns": key_columns,
            "total_rows": total_rows,
            "null_key_rows": null_key_rows,
            "duplicate_key_groups": duplicate_key_groups,
            "duplicate_key_rows": duplicate_key_rows,
            "exact_duplicate_rows_dropped": int(exact_dup_mask.sum()),
            "conflicting_key_groups": 0,
            "conflicting_key_rows": 0,
            "resolution_policy": on_duplicate,
            "sample_duplicate_keys": sample_duplicate_keys,
        }
        return cleaned, report

    # Política "report": não descarta nada e devolve o diagnóstico completo.
    report = {
        "key_columns": key_columns,
        "total_rows": total_rows,
        "null_key_rows": null_key_rows,
        "duplicate_key_groups": duplicate_key_groups,
        "duplicate_key_rows": duplicate_key_rows,
        "exact_duplicate_rows_dropped": 0,
        "conflicting_key_groups": conflicting_key_groups,
        "conflicting_key_rows": conflicting_key_rows,
        "resolution_policy": on_duplicate,
        "sample_duplicate_keys": sample_duplicate_keys,
    }
    return result, report


def run_quality_checks(
    dataframe: pd.DataFrame,
    *,
    expected_year: int | None = None,
    expected_month: int | None = None,
    strict: bool = False,
) -> QualityCheckReport:
    """Executa auditoria de qualidade sem descartar nem alterar nenhum registro.

    Inspeciona:
    - contagem e percentual de nulos em todas as colunas;
    - valores negativos indevidos nas 5 colunas MWmed (exigindo tipagem numérica);
    - códigos desconhecidos de razão (fora de ``REL/CNF/ENE/PAR``) e origem
      (fora de ``LOC/SIS``), além de inconsistências cruzadas entre razão e origem;
    - datas fora do mês/ano esperado (quando ``expected_year`` e ``expected_month``
      são informados), exigindo ``instante`` já convertido para ``datetime64[ns]``.

    Args:
        dataframe: Tabela padronizada com ``instante`` e colunas MWmed tipadas.
        expected_year: Ano esperado do lote (exige ``expected_month``).
        expected_month: Mês esperado do lote, de 1 a 12 (exige ``expected_year``).
        strict: Se ``True``, lança ``DataQualityError`` caso
            ``has_blocking_anomalies`` seja ``True``.

    Returns:
        Relatório ``QualityCheckReport`` completo.

    Raises:
        TypeError: Quando ``dataframe`` não é ``pd.DataFrame``.
        ValueError: Quando ``expected_year``/``expected_month`` são inválidos ou
            fornecidos parcialmente, ou quando ``strict`` não é booleano.
        SourceSchemaError: Quando colunas obrigatórias para auditoria estão
            ausentes ou ainda não foram convertidas para o tipo esperado.
        DataQualityError: Quando ``strict=True`` e há anomalias bloqueantes.
    """

    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe deve ser um pandas.DataFrame.")
    if not dataframe.columns.is_unique:
        duplicated_col_names = sorted(
            str(col) for col in dataframe.columns[dataframe.columns.duplicated()].unique()
        )
        raise SourceSchemaError(
            f"O DataFrame contém nomes de colunas duplicados: {duplicated_col_names}."
        )
    if not isinstance(strict, bool):
        raise ValueError("strict deve ser um valor booleano (True ou False).")

    if (expected_year is None) != (expected_month is None):
        raise ValueError(
            "Informe expected_year e expected_month juntos para validar datas fora do mês."
        )
    if expected_year is not None and expected_month is not None:
        if (
            isinstance(expected_year, bool)
            or not isinstance(expected_year, int)
            or not 1000 <= expected_year <= 9999
        ):
            raise ValueError("expected_year deve ser um inteiro de 4 dígitos (1000 a 9999).")
        if (
            isinstance(expected_month, bool)
            or not isinstance(expected_month, int)
            or not 1 <= expected_month <= 12
        ):
            raise ValueError("expected_month deve ser um inteiro entre 1 e 12.")

    required_columns = (
        "instante",
        "restricao_razao_codigo",
        "restricao_origem_codigo",
        *NON_NEGATIVE_MWMED_COLUMNS,
    )
    missing_cols = [col for col in required_columns if col not in dataframe.columns]
    if missing_cols:
        raise SourceSchemaError(
            f"Colunas obrigatórias ausentes para verificação de qualidade: {missing_cols}."
        )

    if isinstance(dataframe["instante"].dtype, pd.DatetimeTZDtype) or not (
        pd.api.types.is_datetime64_any_dtype(dataframe["instante"].dtype)
    ):
        raise SourceSchemaError(
            "A coluna 'instante' deve estar convertida para datetime64 sem fuso "
            f"(naive) antes da validação (dtype atual: {dataframe['instante'].dtype})."
        )

    for col in NON_NEGATIVE_MWMED_COLUMNS:
        if not pd.api.types.is_numeric_dtype(
            dataframe[col].dtype
        ) or pd.api.types.is_bool_dtype(dataframe[col].dtype):
            raise SourceSchemaError(
                f"A coluna MWmed {col!r} deve estar convertida para tipo numérico "
                f"antes da verificação de valores negativos (dtype atual: {dataframe[col].dtype})."
            )

    total_rows = len(dataframe)

    # 1) Nulos por coluna (contagem e percentual).
    null_counts: dict[str, int] = {}
    null_percent: dict[str, float] = {}
    for col in dataframe.columns:
        count = int(dataframe[col].isna().sum())
        null_counts[str(col)] = count
        null_percent[str(col)] = (
            round((count / total_rows) * 100.0, 4) if total_rows > 0 else 0.0
        )

    # 2) Valores negativos indevidos nas colunas MWmed (ignorando NA).
    negative_counts: dict[str, int] = {}
    for col in NON_NEGATIVE_MWMED_COLUMNS:
        neg_mask = (dataframe[col] < 0).fillna(False)
        negative_counts[col] = int(neg_mask.sum())

    # 3) Códigos desconhecidos e inconsistência cruzada razão x origem.
    reason_series = dataframe["restricao_razao_codigo"].astype("string")
    origin_series = dataframe["restricao_origem_codigo"].astype("string")

    unknown_reason_mask = (~reason_series.isna()) & (
        ~reason_series.isin(VALID_RESTRICTION_REASON_CODES)
    )
    unknown_reason_codes = tuple(
        sorted(str(val) for val in reason_series[unknown_reason_mask].unique())
    )
    unknown_reason_rows = int(unknown_reason_mask.sum())

    unknown_origin_mask = (~origin_series.isna()) & (
        ~origin_series.isin(VALID_RESTRICTION_ORIGIN_CODES)
    )
    unknown_origin_codes = tuple(
        sorted(str(val) for val in origin_series[unknown_origin_mask].unique())
    )
    unknown_origin_rows = int(unknown_origin_mask.sum())

    reason_without_origin_rows = int(
        ((~reason_series.isna()) & origin_series.isna()).sum()
    )
    origin_without_reason_rows = int(
        (reason_series.isna() & (~origin_series.isna())).sum()
    )

    # 4) Cobertura temporal e datas fora do mês esperado.
    instante_series = dataframe["instante"]
    valid_timestamps = instante_series.dropna()
    observed_min = (
        valid_timestamps.min().strftime("%Y-%m-%d %H:%M:%S")
        if not valid_timestamps.empty
        else None
    )
    observed_max = (
        valid_timestamps.max().strftime("%Y-%m-%d %H:%M:%S")
        if not valid_timestamps.empty
        else None
    )

    out_of_month_rows = 0
    out_of_month_samples: tuple[str, ...] = ()
    if expected_year is not None and expected_month is not None:
        out_mask = (~instante_series.isna()) & (
            (instante_series.dt.year != expected_year)
            | (instante_series.dt.month != expected_month)
        )
        out_of_month_rows = int(out_mask.sum())
        if out_of_month_rows > 0:
            out_of_month_samples = tuple(
                ts.strftime("%Y-%m-%d %H:%M:%S")
                for ts in instante_series[out_mask].iloc[:_MAX_ANOMALY_SAMPLES]
            )

    total_negatives = sum(negative_counts.values())
    has_blocking_anomalies = (
        total_negatives > 0
        or unknown_reason_rows > 0
        or unknown_origin_rows > 0
        or out_of_month_rows > 0
    )

    report: QualityCheckReport = {
        "total_rows": total_rows,
        "expected_year": expected_year,
        "expected_month": expected_month,
        "null_counts_by_column": null_counts,
        "null_percent_by_column": null_percent,
        "negative_value_counts": negative_counts,
        "unknown_reason_codes": unknown_reason_codes,
        "unknown_reason_rows": unknown_reason_rows,
        "unknown_origin_codes": unknown_origin_codes,
        "unknown_origin_rows": unknown_origin_rows,
        "reason_without_origin_rows": reason_without_origin_rows,
        "origin_without_reason_rows": origin_without_reason_rows,
        "out_of_month_rows": out_of_month_rows,
        "out_of_month_samples": out_of_month_samples,
        "observed_min_timestamp": observed_min,
        "observed_max_timestamp": observed_max,
        "has_blocking_anomalies": has_blocking_anomalies,
    }

    if strict and has_blocking_anomalies:
        details: list[str] = []
        if total_negatives > 0:
            neg_detail = {k: v for k, v in negative_counts.items() if v > 0}
            details.append(f"valores negativos={neg_detail}")
        if unknown_reason_rows > 0:
            details.append(
                f"códigos de razão desconhecidos={list(unknown_reason_codes)} "
                f"({unknown_reason_rows} linha(s))"
            )
        if unknown_origin_rows > 0:
            details.append(
                f"códigos de origem desconhecidos={list(unknown_origin_codes)} "
                f"({unknown_origin_rows} linha(s))"
            )
        if out_of_month_rows > 0:
            details.append(
                f"datas fora de {expected_year:04d}-{expected_month:02d}="
                f"{out_of_month_rows} linha(s), amostras={list(out_of_month_samples)}"
            )
        raise DataQualityError(
            "Anomalias bloqueantes detectadas na verificação de qualidade: "
            + "; ".join(details)
        )

    return report
