"""Leitura e normalização estrutural dos registros brutos do ONS.

Este módulo mantém a leitura física do CSV separada das conversões de tipos e
das regras de negócio. Nesta etapa, os valores são preservados como texto
anulável; datas e medidas numéricas serão convertidas explicitamente nas etapas
seguintes da Fase 3.
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from types import MappingProxyType
from typing import TypedDict

import numpy as np
import pandas as pd


CSV_SEPARATOR = ";"
CSV_DECIMAL_SEPARATOR = "."
CSV_ENCODING = "utf-8-sig"
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
TIMESTAMP_TIMEZONE_POLICY = "naive_ons_official_clock"
DEFAULT_MVP_STATE = "CE"
CEG_AGGREGATE_PLACEHOLDER = "-"
EXPECTED_INTERVAL_MINUTES = 30
EXPECTED_INTERVAL_HOURS = 0.5
VALID_RESTRICTION_REASON_CODES: frozenset[str] = frozenset({"REL", "CNF", "ENE", "PAR"})
_STATE_CODE_PATTERN = re.compile(r"^[A-Z]{2}$")
_STRICT_DECIMAL_PATTERN = re.compile(
    r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$"
)
_MAX_INVALID_SAMPLES = 5

EXPECTED_SOURCE_COLUMNS: tuple[str, ...] = (
    "id_subsistema",
    "nom_subsistema",
    "id_estado",
    "nom_estado",
    "nom_usina",
    "id_ons",
    "ceg",
    "din_instante",
    "val_geracao",
    "val_geracaolimitada",
    "val_disponibilidade",
    "val_geracaoreferencia",
    "val_geracaoreferenciafinal",
    "cod_razaorestricao",
    "cod_origemrestricao",
    "dsc_restricao",
    "id_pontoconexao",
    "nom_pontoconexao",
    "nom_agenteoperador",
    "val_geracaonaorealizadaapurada",
    "num_minutos_rel",
    "num_minutos_cnf",
    "num_minutos_ene",
    "num_minutos_restricao",
)

_SOURCE_TO_INTERNAL_COLUMNS = {
    "id_subsistema": "subsistema_id",
    "nom_subsistema": "subsistema_nome",
    "id_estado": "estado_sigla",
    "nom_estado": "estado_nome",
    "nom_usina": "usina_nome",
    "id_ons": "ons_id",
    "ceg": "ceg",
    "din_instante": "instante",
    "val_geracao": "geracao_mwmed",
    "val_geracaolimitada": "geracao_limitada_mwmed",
    "val_disponibilidade": "disponibilidade_mwmed",
    "val_geracaoreferencia": "geracao_referencia_mwmed",
    "val_geracaoreferenciafinal": "geracao_referencia_final_mwmed",
    "cod_razaorestricao": "restricao_razao_codigo",
    "cod_origemrestricao": "restricao_origem_codigo",
    "dsc_restricao": "restricao_descricao",
    "id_pontoconexao": "ponto_conexao_id",
    "nom_pontoconexao": "ponto_conexao_nome",
    "nom_agenteoperador": "agente_operador_nome",
    "val_geracaonaorealizadaapurada": "geracao_nao_realizada_apurada",
    "num_minutos_rel": "minutos_restricao_rel",
    "num_minutos_cnf": "minutos_restricao_cnf",
    "num_minutos_ene": "minutos_restricao_ene",
    "num_minutos_restricao": "minutos_restricao_total",
}
SOURCE_TO_INTERNAL_COLUMNS: Mapping[str, str] = MappingProxyType(
    _SOURCE_TO_INTERNAL_COLUMNS
)

INTERNAL_TO_SOURCE_COLUMNS: Mapping[str, str] = MappingProxyType(
    {
        internal_name: source_name
        for source_name, internal_name in SOURCE_TO_INTERNAL_COLUMNS.items()
    }
)

NUMERIC_SOURCE_COLUMNS: tuple[str, ...] = (
    "val_geracao",
    "val_geracaolimitada",
    "val_disponibilidade",
    "val_geracaoreferencia",
    "val_geracaoreferenciafinal",
    "val_geracaonaorealizadaapurada",
    "num_minutos_rel",
    "num_minutos_cnf",
    "num_minutos_ene",
    "num_minutos_restricao",
)

MWMED_INTERNAL_COLUMNS: tuple[str, ...] = (
    "geracao_mwmed",
    "geracao_limitada_mwmed",
    "disponibilidade_mwmed",
    "geracao_referencia_mwmed",
    "geracao_referencia_final_mwmed",
)

if len(SOURCE_TO_INTERNAL_COLUMNS) != len(INTERNAL_TO_SOURCE_COLUMNS):
    raise RuntimeError("O mapeamento de colunas internas contém nomes duplicados.")
if set(SOURCE_TO_INTERNAL_COLUMNS) != set(EXPECTED_SOURCE_COLUMNS):
    raise RuntimeError(
        "O mapeamento de colunas não corresponde ao contrato oficial esperado."
    )


class SourceSchemaReport(TypedDict):
    """Diagnóstico estrutural do cabeçalho de um CSV bruto."""

    observed: tuple[str, ...]
    missing: tuple[str, ...]
    unexpected: tuple[str, ...]
    duplicates: tuple[str, ...]
    order_matches: bool


class SourceSchemaError(ValueError):
    """O cabeçalho do arquivo bruto diverge do contrato oficial conhecido."""


class RawCsvReadError(ValueError):
    """O arquivo bruto não pôde ser lido sem perda ou interpretação ambígua."""


class TimestampConversionError(ValueError):
    """A coluna de data/hora contém valores fora do formato oficial esperado."""


class NumericConversionError(ValueError):
    """Uma ou mais colunas em MWmed contêm valores inválidos ou não finitos."""


class EmptyFilterResultError(ValueError):
    """A filtragem geográfica não encontrou nenhum registro para a UF solicitada."""


class IdentifierNormalizationError(ValueError):
    """Os identificadores operacionais (ons_id / ceg) apresentam falhas críticas."""


class GranularityValidationError(ValueError):
    """A granularidade temporal dos registros diverge do passo esperado."""


class EligibilityReport(TypedDict):
    """Resumo auditável da elegibilidade dos registros por indicador."""

    total_rows: int
    elegivel_geracao_verificada_rows: int
    elegivel_referencia_final_rows: int
    possui_restricao_classificada_rows: int
    elegivel_gnra_rows: int
    elegivel_enriquecimento_aneel_rows: int


class GranularityReport(TypedDict):
    """Diagnóstico auditável da granularidade temporal e duração do intervalo."""

    expected_step_minutes: int
    validated_duration_hours: float
    total_rows: int
    distinct_ons_ids: int
    checked_transitions: int
    exact_step_transitions: int
    gap_transitions: int
    unexpected_step_transitions: int
    off_grid_timestamp_rows: int
    observed_step_minutes: tuple[float, ...]


class StateFilterReport(TypedDict):
    """Diagnóstico auditável da filtragem geográfica por UF."""

    column: str
    source_column: str
    target_state: str
    input_rows: int
    matched_rows: int
    excluded_rows: int
    null_state_rows: int
    observed_states: tuple[str, ...]


class IdentifierReport(TypedDict):
    """Diagnóstico auditável dos identificadores operacionais (ons_id e ceg)."""

    ons_id_column: str
    ceg_column: str
    total_rows: int
    distinct_ons_ids: int
    null_ons_id_rows: int
    blank_ons_id_rows: int
    ceg_present_rows: int
    ceg_placeholder_rows: int
    ceg_null_or_blank_rows: int
    distinct_valid_cegs: int


class TimestampConversionReport(TypedDict):
    """Relatório auditável da conversão da coluna de data/hora."""

    column: str
    source_column: str
    expected_format: str
    timezone_policy: str
    total_rows: int
    original_null_count: int
    converted_count: int
    invalid_count: int
    invalid_samples: tuple[str, ...]


class ColumnNumericReport(TypedDict):
    """Relatório auditável da conversão numérica de uma coluna em MWmed."""

    column: str
    source_column: str
    total_rows: int
    original_null_count: int
    converted_count: int
    invalid_count: int
    invalid_samples: tuple[str, ...]


def inspect_source_schema(columns: Iterable[str]) -> SourceSchemaReport:
    """Compara nomes observados com as 24 colunas oficiais conhecidas.

    A ordem é registrada no relatório, mas não é tratada como erro porque a
    transformação usa nomes explícitos e não posições de coluna.
    """

    observed = tuple(columns)
    counts = Counter(observed)
    duplicates = tuple(name for name, count in counts.items() if count > 1)
    observed_set = set(observed)
    expected_set = set(EXPECTED_SOURCE_COLUMNS)

    return {
        "observed": observed,
        "missing": tuple(
            name for name in EXPECTED_SOURCE_COLUMNS if name not in observed_set
        ),
        "unexpected": tuple(name for name in observed if name not in expected_set),
        "duplicates": duplicates,
        "order_matches": observed == EXPECTED_SOURCE_COLUMNS,
    }


def validate_source_schema(columns: Iterable[str]) -> SourceSchemaReport:
    """Valida o cabeçalho e retorna seu diagnóstico quando ele é compatível."""

    report = inspect_source_schema(columns)
    problems: list[str] = []
    if report["missing"]:
        problems.append(f"colunas ausentes={list(report['missing'])}")
    if report["unexpected"]:
        problems.append(f"colunas não mapeadas={list(report['unexpected'])}")
    if report["duplicates"]:
        problems.append(f"colunas duplicadas={list(report['duplicates'])}")

    if problems:
        raise SourceSchemaError(
            "O esquema do CSV bruto não corresponde às 24 colunas oficiais "
            f"conhecidas: {'; '.join(problems)}. Consulte o dicionário oficial "
            "antes de atualizar o mapeamento."
        )
    return report


def read_raw_ons_csv(file_path: Path | str) -> pd.DataFrame:
    """Lê um CSV bruto do ONS com o formato confirmado na Fase 1.

    Os valores são carregados com ``StringDtype`` para preservar identificadores,
    casas decimais e códigos exatamente até que cada conversão seja validada em
    uma etapa própria. Como ``decimal`` não atua sobre colunas lidas como texto,
    uma validação lexical anterior rejeita vírgula nos campos numéricos e exige
    o ponto decimal confirmado na Fase 1. Apenas campos vazios são interpretados
    como ausentes. UTF-8 com ou sem BOM é aceito explicitamente.

    Raises:
        ValueError: Quando o caminho é inválido.
        FileNotFoundError: Quando o arquivo não existe.
        SourceSchemaError: Quando o cabeçalho mudou ou possui duplicidades.
        RawCsvReadError: Quando a codificação ou a estrutura CSV é inválida.
    """

    path = _validate_raw_csv_path(file_path)
    header, expected_row_count = _validate_csv_structure(path)

    try:
        dataframe = pd.read_csv(
            path,
            sep=CSV_SEPARATOR,
            encoding=CSV_ENCODING,
            dtype="string",
            keep_default_na=False,
            na_values=[""],
            index_col=False,
            low_memory=False,
        )
    except UnicodeDecodeError as error:
        raise RawCsvReadError(
            f"O arquivo {path} não usa a codificação UTF-8 confirmada na Fase 1."
        ) from error
    except (pd.errors.EmptyDataError, pd.errors.ParserError) as error:
        raise RawCsvReadError(f"Falha ao interpretar o CSV bruto {path}: {error}") from error
    except OSError as error:
        raise RawCsvReadError(f"Falha ao ler o CSV bruto {path}: {error}") from error

    # Confirma o resultado do parser, sem confiar apenas na leitura manual do cabeçalho.
    validate_source_schema(dataframe.columns)
    if len(dataframe) != expected_row_count:
        raise RawCsvReadError(
            f"O CSV bruto {path} possui {expected_row_count} registros segundo o leitor "
            f"estrutural, mas o pandas retornou {len(dataframe)}."
        )
    return dataframe


def standardize_column_names(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Retorna uma nova tabela com nomes internos e mapeamento reversível.

    A tabela recebida não é modificada. Colunas ausentes, adicionais ou
    duplicadas interrompem a transformação para impedir perdas silenciosas.
    """

    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe deve ser um pandas.DataFrame.")

    validate_source_schema(dataframe.columns)
    standardized = dataframe.rename(columns=SOURCE_TO_INTERNAL_COLUMNS).copy()

    if len(set(standardized.columns)) != len(standardized.columns):
        raise SourceSchemaError("A padronização produziu nomes internos duplicados.")
    return standardized


def parse_instante_column(
    dataframe: pd.DataFrame,
    *,
    column: str = "instante",
    strict: bool = True,
) -> tuple[pd.DataFrame, TimestampConversionReport]:
    """Converte a coluna de data/hora do ONS para ``datetime64[ns]`` sem fuso.

    O ONS publica ``din_instante`` no formato exato ``YYYY-MM-DD HH:MM:SS`` sem
    sufixo de fuso horário. Por isso, a conversão preserva o carimbo como
    *timezone-naive* (política ``naive_ons_official_clock``) e **não** aplica
    ``tz_localize`` silenciosamente.

    Regras contra erros silenciosos:
    - Exige correspondência exata com ``TIMESTAMP_FORMAT`` (sem inferência livre
      de dia/mês e rejeitando sufixos ``Z`` ou deslocamentos como ``-03:00``).
    - Rejeita strings compostas apenas de espaços em branco ou datas inexistentes
      no calendário (ex.: ``2025-02-30 00:00:00``).
    - Diferencia nulos originais de valores inválidos. Com ``strict=True``,
      qualquer valor não nulo inválido lança ``TimestampConversionError``.
    - Não modifica o ``DataFrame`` de entrada.

    Args:
        dataframe: Tabela contendo a coluna de data/hora (geralmente padronizada).
        column: Nome da coluna a converter (padrão ``"instante"``).
        strict: Se ``True`` (padrão), falha explicitamente se houver qualquer
            valor inválido; se ``False``, converte inválidos para ``NaT`` e
            expõe a contagem e amostras no relatório retornado.

    Returns:
        Tupla ``(converted_dataframe, report)``.

    Raises:
        TypeError: Quando ``dataframe`` não é ``pd.DataFrame``.
        ValueError: Quando ``column`` ou ``strict`` é inválido.
        SourceSchemaError: Quando ``column`` não existe no ``DataFrame``.
        TimestampConversionError: Quando ``strict=True`` e há valores inválidos
            ou quando a coluna já contém timestamps com fuso horário inesperado.
    """

    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe deve ser um pandas.DataFrame.")
    if not isinstance(column, str) or not column.strip():
        raise ValueError("column deve ser uma string não vazia.")
    if not isinstance(strict, bool):
        raise ValueError("strict deve ser um valor booleano (True ou False).")
    if column not in dataframe.columns:
        raise SourceSchemaError(
            f"Coluna de data/hora ausente no DataFrame: {column!r}."
        )

    result = dataframe.copy()
    series = result[column]
    source_column = INTERNAL_TO_SOURCE_COLUMNS.get(column, column)

    # Caso a coluna já seja datetime, verifica a política de fuso (deve ser naive).
    if isinstance(series.dtype, pd.DatetimeTZDtype):
        raise TimestampConversionError(
            f"A coluna {column!r} já possui fuso horário ({series.dtype}), "
            f"contrariando a política explícita {TIMESTAMP_TIMEZONE_POLICY!r}."
        )

    if pd.api.types.is_datetime64_any_dtype(series.dtype):
        result[column] = series.astype("datetime64[ns]")
        null_count = int(result[column].isna().sum())
        report: TimestampConversionReport = {
            "column": column,
            "source_column": source_column,
            "expected_format": TIMESTAMP_FORMAT,
            "timezone_policy": TIMESTAMP_TIMEZONE_POLICY,
            "total_rows": len(series),
            "original_null_count": null_count,
            "converted_count": len(series) - null_count,
            "invalid_count": 0,
            "invalid_samples": (),
        }
        return result, report

    # Trata a série como texto anulável para impedir conversões silenciosas.
    raw_as_string = series.astype("string")
    original_null_mask = raw_as_string.isna()
    non_null_mask = ~original_null_mask

    # Exige formato exato YYYY-MM-DD HH:MM:SS sem espaços extras ou sufixos de fuso.
    exact_length_mask = non_null_mask & (
        raw_as_string.str.len().fillna(-1) == 19
    )
    parsed = pd.to_datetime(
        raw_as_string.where(exact_length_mask, pd.NA),
        format=TIMESTAMP_FORMAT,
        exact=True,
        errors="coerce",
    )

    invalid_mask = non_null_mask & parsed.isna()
    invalid_count = int(invalid_mask.sum())
    invalid_samples = tuple(
        str(val) for val in raw_as_string[invalid_mask].iloc[:_MAX_INVALID_SAMPLES]
    )

    if invalid_count > 0 and strict:
        raise TimestampConversionError(
            f"Falha ao converter a coluna {column!r} (origem={source_column!r}) "
            f"com o formato oficial {TIMESTAMP_FORMAT!r}: {invalid_count} registro(s) "
            f"inválido(s). Amostras: {list(invalid_samples)}."
        )

    result[column] = parsed.astype("datetime64[ns]")
    original_null_count = int(original_null_mask.sum())
    report = {
        "column": column,
        "source_column": source_column,
        "expected_format": TIMESTAMP_FORMAT,
        "timezone_policy": TIMESTAMP_TIMEZONE_POLICY,
        "total_rows": len(series),
        "original_null_count": original_null_count,
        "converted_count": int((~parsed.isna()).sum()),
        "invalid_count": invalid_count,
        "invalid_samples": invalid_samples,
    }
    return result, report


def convert_mwmed_columns(
    dataframe: pd.DataFrame,
    *,
    columns: Iterable[str] = MWMED_INTERNAL_COLUMNS,
    strict: bool = True,
) -> tuple[pd.DataFrame, dict[str, ColumnNumericReport]]:
    """Converte colunas em MWmed para ``Float64`` anulável sem arredondar precocemente.

    Por padrão converte exclusivamente as 5 colunas cuja unidade ``MWmed`` está
    confirmada no dicionário oficial do ONS (``MWMED_INTERNAL_COLUMNS``). A
    coluna ``geracao_nao_realizada_apurada`` (GNRa) não é incluída por padrão
    porque sua unidade ainda aguarda confirmação documental.

    Regras contra erros silenciosos:
    - Nunca substitui valores ausentes (``<NA>``) por ``0.0``.
    - Valida lexicalmente cada string não nula contra ponto decimal estrito
      (rejeitando vírgula decimal, espaços extras, unidades textuais e literais
      não finitos como ``"nan"``, ``"inf"`` e ``"-inf"``).
    - Preserva precisão total IEEE-754 de 64 bits (``pd.Float64Dtype``) sem
      qualquer arredondamento.
    - Com ``strict=True`` (padrão), lança ``NumericConversionError`` caso
      qualquer coluna contenha valores inválidos ou não finitos.
    - Não modifica o ``DataFrame`` de entrada.

    Args:
        dataframe: Tabela contendo as colunas em MWmed.
        columns: Iterável com os nomes das colunas a converter
            (padrão ``MWMED_INTERNAL_COLUMNS``).
        strict: Se ``True`` (padrão), falha explicitamente se houver valores
            inválidos; se ``False``, converte inválidos para ``pd.NA`` e registra
            a contagem e amostras no relatório.

    Returns:
        Tupla ``(converted_dataframe, reports_by_column)``.

    Raises:
        TypeError: Quando ``dataframe`` não é ``pd.DataFrame``.
        ValueError: Quando ``columns`` é vazio/inválido ou ``strict`` não é bool.
        SourceSchemaError: Quando alguma coluna solicitada não existe no ``DataFrame``.
        NumericConversionError: Quando ``strict=True`` e há valores inválidos,
            vírgula decimal, infinitos ou ``NaN`` literais em texto.
    """

    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe deve ser um pandas.DataFrame.")
    if not isinstance(strict, bool):
        raise ValueError("strict deve ser um valor booleano (True ou False).")

    target_columns = tuple(columns)
    if not target_columns:
        raise ValueError("columns deve conter pelo menos um nome de coluna.")
    if any(not isinstance(col, str) or not col.strip() for col in target_columns):
        raise ValueError("Todos os nomes em columns devem ser strings não vazias.")
    if len(set(target_columns)) != len(target_columns):
        raise ValueError("columns não pode conter nomes duplicados.")

    missing_columns = [col for col in target_columns if col not in dataframe.columns]
    if missing_columns:
        raise SourceSchemaError(
            f"Colunas MWmed ausentes no DataFrame: {missing_columns}."
        )

    result = dataframe.copy()
    reports: dict[str, ColumnNumericReport] = {}
    errors: list[str] = []

    for column in target_columns:
        source_column = INTERNAL_TO_SOURCE_COLUMNS.get(column, column)
        series = result[column]
        converted_series, col_report = _convert_single_numeric_series(
            series,
            column=column,
            source_column=source_column,
        )
        reports[column] = col_report
        if col_report["invalid_count"] > 0:
            errors.append(
                f"{column!r} (origem={source_column!r}): "
                f"{col_report['invalid_count']} inválido(s), "
                f"amostras={list(col_report['invalid_samples'])}"
            )
        result[column] = converted_series

    if errors and strict:
        raise NumericConversionError(
            "Falha ao converter colunas MWmed para Float64 sem arredondamento: "
            + "; ".join(errors)
        )

    return result, reports


def filter_by_state(
    dataframe: pd.DataFrame,
    state_code: str = DEFAULT_MVP_STATE,
    *,
    column: str = "estado_sigla",
    allow_empty: bool = False,
) -> tuple[pd.DataFrame, StateFilterReport]:
    """Filtra a tabela para uma UF específica (padrão ``'CE'`` no MVP) com auditoria.

    Regras contra erros silenciosos:
    - Valida ``state_code`` exigindo exatamente 2 letras ASCII (normalizadas para
      maiúsculas, ex.: ``"ce"`` -> ``"CE"``).
    - Preserva o ``DataFrame`` de entrada sem mutação e reseta o índice da saída.
    - Contabiliza explicitamente linhas com UF nula (``null_state_rows``) e lista
      todas as siglas observadas (``observed_states``) no relatório retornado.
    - Com ``allow_empty=False`` (padrão), lança ``EmptyFilterResultError`` se
      nenhum registro corresponder à UF solicitada.

    Args:
        dataframe: Tabela contendo a coluna de sigla da UF.
        state_code: Sigla da UF desejada com 2 letras (padrão ``"CE"``).
        column: Nome da coluna de UF (padrão ``"estado_sigla"``).
        allow_empty: Se ``True``, permite retorno com 0 linhas preservando o esquema.

    Returns:
        Tupla ``(filtered_dataframe, report)``.

    Raises:
        TypeError: Quando ``dataframe`` não é ``pd.DataFrame``.
        ValueError: Quando ``state_code``, ``column`` ou ``allow_empty`` é inválido.
        SourceSchemaError: Quando ``column`` não existe no ``DataFrame``.
        EmptyFilterResultError: Quando ``matched_rows == 0`` e ``allow_empty=False``.
    """

    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe deve ser um pandas.DataFrame.")
    if not isinstance(state_code, str) or not state_code:
        raise ValueError("state_code deve ser uma sigla de UF com 2 letras.")
    normalized_state = state_code.upper()
    if not _STATE_CODE_PATTERN.fullmatch(normalized_state):
        raise ValueError(
            f"state_code inválido: {state_code!r}. Informe exatamente 2 letras ASCII (ex.: 'CE')."
        )
    if not isinstance(column, str) or not column.strip():
        raise ValueError("column deve ser uma string não vazia.")
    if not isinstance(allow_empty, bool):
        raise ValueError("allow_empty deve ser um valor booleano (True ou False).")
    if column not in dataframe.columns:
        raise SourceSchemaError(f"Coluna de UF ausente no DataFrame: {column!r}.")

    series = dataframe[column].astype("string")
    null_mask = series.isna()
    matched_mask = series.eq(normalized_state).fillna(False)

    observed_states = tuple(sorted(str(val) for val in series.dropna().unique()))
    input_rows = len(dataframe)
    matched_rows = int(matched_mask.sum())
    null_state_rows = int(null_mask.sum())
    excluded_rows = input_rows - matched_rows

    if matched_rows == 0 and not allow_empty:
        raise EmptyFilterResultError(
            f"Nenhum registro encontrado para {column}={normalized_state!r}. "
            f"Estados observados na base: {list(observed_states)} "
            f"(linhas com UF nula: {null_state_rows})."
        )

    filtered = dataframe.loc[matched_mask].reset_index(drop=True).copy()
    report: StateFilterReport = {
        "column": column,
        "source_column": INTERNAL_TO_SOURCE_COLUMNS.get(column, column),
        "target_state": normalized_state,
        "input_rows": input_rows,
        "matched_rows": matched_rows,
        "excluded_rows": excluded_rows,
        "null_state_rows": null_state_rows,
        "observed_states": observed_states,
    }
    return filtered, report


def preserve_operational_identifiers(
    dataframe: pd.DataFrame,
    *,
    ons_id_column: str = "ons_id",
    ceg_column: str = "ceg",
    strict_ons_id: bool = True,
) -> tuple[pd.DataFrame, IdentifierReport]:
    """Garante ``ons_id`` e ``ceg`` em ``StringDtype``, preservando literalmente ``'-'``.

    O ONS publica ``ceg == '-'`` para conjuntos de usinas. Esta função **nunca**
    converte ``'-'`` em ``pd.NA`` nem força vínculo com a ANEEL; em vez disso,
    preserva o texto exato e contabiliza separadamente linhas com CEG individual,
    linhas de conjuntos (``'-'``) e linhas sem CEG.

    Regras contra erros silenciosos:
    - Mantém ambas as colunas em ``pd.StringDtype`` para preservar zeros à
      esquerda e códigos alfanuméricos.
    - Detecta ``ons_id`` nulo ou composto apenas por espaços em branco. Com
      ``strict_ons_id=True`` (padrão), lança ``IdentifierNormalizationError``
      pois ``ons_id`` integra a chave operacional candidata.
    - Não modifica o ``DataFrame`` de entrada.

    Args:
        dataframe: Tabela contendo as colunas de identificadores operacionais.
        ons_id_column: Nome da coluna do identificador ONS (padrão ``"ons_id"``).
        ceg_column: Nome da coluna do código CEG (padrão ``"ceg"``).
        strict_ons_id: Se ``True`` (padrão), falha quando houver ``ons_id`` nulo
            ou em branco.

    Returns:
        Tupla ``(normalized_dataframe, report)``.

    Raises:
        TypeError: Quando ``dataframe`` não é ``pd.DataFrame``.
        ValueError: Quando nomes de coluna ou ``strict_ons_id`` são inválidos.
        SourceSchemaError: Quando ``ons_id_column`` ou ``ceg_column`` está ausente.
        IdentifierNormalizationError: Quando ``strict_ons_id=True`` e há registros
            com ``ons_id`` nulo ou em branco.
    """

    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe deve ser um pandas.DataFrame.")
    if not isinstance(ons_id_column, str) or not ons_id_column.strip():
        raise ValueError("ons_id_column deve ser uma string não vazia.")
    if not isinstance(ceg_column, str) or not ceg_column.strip():
        raise ValueError("ceg_column deve ser uma string não vazia.")
    if ons_id_column == ceg_column:
        raise ValueError("ons_id_column e ceg_column devem ser colunas distintas.")
    if not isinstance(strict_ons_id, bool):
        raise ValueError("strict_ons_id deve ser um valor booleano (True ou False).")

    missing_columns = [
        col for col in (ons_id_column, ceg_column) if col not in dataframe.columns
    ]
    if missing_columns:
        raise SourceSchemaError(
            f"Colunas de identificadores ausentes no DataFrame: {missing_columns}."
        )

    result = dataframe.copy()
    ons_series = result[ons_id_column].astype("string")
    ceg_series = result[ceg_column].astype("string")

    null_ons_mask = ons_series.isna()
    blank_ons_mask = (~null_ons_mask) & (ons_series.str.strip() == "")
    null_ons_count = int(null_ons_mask.sum())
    blank_ons_count = int(blank_ons_mask.sum())

    if strict_ons_id and (null_ons_count > 0 or blank_ons_count > 0):
        raise IdentifierNormalizationError(
            f"Identificador operacional {ons_id_column!r} inválido: "
            f"{null_ons_count} nulo(s) e {blank_ons_count} em branco."
        )

    ceg_null_mask = ceg_series.isna()
    ceg_blank_mask = (~ceg_null_mask) & (ceg_series.str.strip() == "")
    ceg_null_or_blank_mask = ceg_null_mask | ceg_blank_mask
    ceg_placeholder_mask = (~ceg_null_or_blank_mask) & (
        ceg_series == CEG_AGGREGATE_PLACEHOLDER
    )
    ceg_present_mask = (~ceg_null_or_blank_mask) & (~ceg_placeholder_mask)

    valid_ons_series = ons_series[~(null_ons_mask | blank_ons_mask)]
    valid_ceg_series = ceg_series[ceg_present_mask]

    result[ons_id_column] = ons_series
    result[ceg_column] = ceg_series

    report: IdentifierReport = {
        "ons_id_column": ons_id_column,
        "ceg_column": ceg_column,
        "total_rows": len(result),
        "distinct_ons_ids": int(valid_ons_series.nunique()),
        "null_ons_id_rows": null_ons_count,
        "blank_ons_id_rows": blank_ons_count,
        "ceg_present_rows": int(ceg_present_mask.sum()),
        "ceg_placeholder_rows": int(ceg_placeholder_mask.sum()),
        "ceg_null_or_blank_rows": int(ceg_null_or_blank_mask.sum()),
        "distinct_valid_cegs": int(valid_ceg_series.nunique()),
    }
    return result, report


def add_eligibility_flags(
    dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, EligibilityReport]:
    """Cria sinalizadores booleanos explícitos de elegibilidade para cada indicador.

    Nenhuma linha é descartada. Em vez disso, adiciona cinco colunas
    ``pd.BooleanDtype`` que permitem às camadas de métricas e SQL calcular
    indicadores e taxas de cobertura com rastreabilidade:
    - ``elegivel_geracao_verificada``: ``instante`` válido, ``ons_id`` válido e
      ``geracao_mwmed`` finito ``>= 0``.
    - ``elegivel_referencia_final``: ``instante`` válido, ``ons_id`` válido e
      ``geracao_referencia_final_mwmed`` finito ``>= 0``.
    - ``possui_restricao_classificada``: ``restricao_razao_codigo`` pertence ao
      domínio oficial ``{REL, CNF, ENE, PAR}``.
    - ``elegivel_gnra``: ``possui_restricao_classificada`` e
      ``geracao_nao_realizada_apurada`` preenchida com número decimal finito
      ``>= 0`` (preservando o valor bruto da GNRa sem converter para MWh).
    - ``elegivel_enriquecimento_aneel``: ``ceg`` preenchido, não vazio e
      diferente de ``'-'`` (conjuntos de usinas não são elegíveis).

    Args:
        dataframe: Tabela padronizada e tipada (com ``instante`` datetime naive
            e colunas MWmed numéricas).

    Returns:
        Tupla ``(enriched_dataframe, report)``.

    Raises:
        TypeError: Quando ``dataframe`` não é ``pd.DataFrame``.
        SourceSchemaError: Quando há colunas duplicadas, colunas obrigatórias
            ausentes ou colunas ainda sem a tipagem esperada.
    """

    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe deve ser um pandas.DataFrame.")
    if not dataframe.columns.is_unique:
        duplicated = sorted(
            str(col) for col in dataframe.columns[dataframe.columns.duplicated()].unique()
        )
        raise SourceSchemaError(
            f"O DataFrame contém nomes de colunas duplicados: {duplicated}."
        )

    required_columns = (
        "ons_id",
        "ceg",
        "instante",
        "geracao_mwmed",
        "geracao_referencia_final_mwmed",
        "restricao_razao_codigo",
        "geracao_nao_realizada_apurada",
    )
    missing = [col for col in required_columns if col not in dataframe.columns]
    if missing:
        raise SourceSchemaError(
            f"Colunas obrigatórias ausentes para criar sinalizadores de elegibilidade: {missing}."
        )

    if isinstance(dataframe["instante"].dtype, pd.DatetimeTZDtype) or not (
        pd.api.types.is_datetime64_any_dtype(dataframe["instante"].dtype)
    ):
        raise SourceSchemaError(
            "A coluna 'instante' deve estar convertida para datetime64 sem fuso "
            f"(naive) antes de criar sinalizadores (dtype atual: {dataframe['instante'].dtype})."
        )

    for num_col in ("geracao_mwmed", "geracao_referencia_final_mwmed"):
        if not pd.api.types.is_numeric_dtype(
            dataframe[num_col].dtype
        ) or pd.api.types.is_bool_dtype(dataframe[num_col].dtype):
            raise SourceSchemaError(
                f"A coluna {num_col!r} deve estar convertida para tipo numérico "
                f"antes de criar sinalizadores (dtype atual: {dataframe[num_col].dtype})."
            )

    result = dataframe.copy()

    ons_series = result["ons_id"].astype("string")
    valid_ons = (~ons_series.isna()) & (ons_series.str.strip() != "")
    valid_instante = ~result["instante"].isna()
    valid_key = valid_ons & valid_instante

    geracao = pd.to_numeric(result["geracao_mwmed"], errors="coerce")
    geracao_finite = pd.Series(
        np.isfinite(geracao.fillna(0.0).to_numpy(dtype="float64")),
        index=result.index,
    )
    elegivel_geracao_verificada = (
        valid_key & (~geracao.isna()) & geracao_finite & (geracao >= 0).fillna(False)
    )

    ref_final = pd.to_numeric(result["geracao_referencia_final_mwmed"], errors="coerce")
    ref_final_finite = pd.Series(
        np.isfinite(ref_final.fillna(0.0).to_numpy(dtype="float64")),
        index=result.index,
    )
    elegivel_referencia_final = (
        valid_key
        & (~ref_final.isna())
        & ref_final_finite
        & (ref_final >= 0).fillna(False)
    )

    reason_series = result["restricao_razao_codigo"].astype("string")
    possui_restricao_classificada = (~reason_series.isna()) & (
        reason_series.isin(VALID_RESTRICTION_REASON_CODES)
    )

    # Valida GNRa sem alterar sua coluna original nem converter para MWh.
    gnra_numeric, _ = _convert_single_numeric_series(
        result["geracao_nao_realizada_apurada"],
        column="geracao_nao_realizada_apurada",
        source_column="val_geracaonaorealizadaapurada",
    )
    elegivel_gnra = (
        valid_key
        & possui_restricao_classificada
        & (~gnra_numeric.isna())
        & (gnra_numeric >= 0).fillna(False)
    )

    ceg_series = result["ceg"].astype("string")
    elegivel_enriquecimento_aneel = (
        (~ceg_series.isna())
        & (ceg_series.str.strip() != "")
        & (ceg_series != CEG_AGGREGATE_PLACEHOLDER)
    )

    result["elegivel_geracao_verificada"] = elegivel_geracao_verificada.astype("boolean")
    result["elegivel_referencia_final"] = elegivel_referencia_final.astype("boolean")
    result["possui_restricao_classificada"] = possui_restricao_classificada.astype(
        "boolean"
    )
    result["elegivel_gnra"] = elegivel_gnra.astype("boolean")
    result["elegivel_enriquecimento_aneel"] = elegivel_enriquecimento_aneel.astype(
        "boolean"
    )

    report: EligibilityReport = {
        "total_rows": len(result),
        "elegivel_geracao_verificada_rows": int(elegivel_geracao_verificada.sum()),
        "elegivel_referencia_final_rows": int(elegivel_referencia_final.sum()),
        "possui_restricao_classificada_rows": int(possui_restricao_classificada.sum()),
        "elegivel_gnra_rows": int(elegivel_gnra.sum()),
        "elegivel_enriquecimento_aneel_rows": int(elegivel_enriquecimento_aneel.sum()),
    }
    return result, report


def validate_granularity_and_add_duration(
    dataframe: pd.DataFrame,
    *,
    expected_step_minutes: int = EXPECTED_INTERVAL_MINUTES,
    strict: bool = True,
) -> tuple[pd.DataFrame, GranularityReport]:
    """Valida a granularidade temporal por ``ons_id`` e cria ``duracao_horas``.

    Só preenche ``duracao_horas`` (em ``Float64``, padrão ``0.5`` h para 30 min)
    após verificar que:
    - todos os timestamps não nulos estão alinhados à grade do passo esperado
      (para 30 min: minutos múltiplos de 30, segundos == 0, microssegundos == 0);
    - todas as transições consecutivas por ``ons_id`` (ordenado por ``instante``)
      são múltiplos positivos exatos de ``expected_step_minutes`` (transições de
      60, 90 min etc. são contabilizadas como lacunas em ``gap_transitions``, sem
      alterar a duração nominal do patamar para 1,0 h).

    Transições de 0 min (duplicatas) ou fora da grade (ex.: 15 min) são
    sinalizadas em ``unexpected_step_transitions`` e bloqueiam a criação de
    ``duracao_horas`` sob ``strict=True`` lançando ``GranularityValidationError``.

    Args:
        dataframe: Tabela contendo ``ons_id`` e ``instante`` (datetime64 naive).
        expected_step_minutes: Granularidade esperada em minutos (padrão 30;
            deve ser divisor positivo de 60).
        strict: Se ``True`` (padrão), falha com ``GranularityValidationError``
            caso haja timestamps fora da grade ou passos incompatíveis.

    Returns:
        Tupla ``(dataframe_with_duration, report)``.

    Raises:
        TypeError: Quando ``dataframe`` não é ``pd.DataFrame``.
        ValueError: Quando ``expected_step_minutes`` ou ``strict`` é inválido.
        SourceSchemaError: Quando ``ons_id``/``instante`` estão ausentes,
            duplicados ou não tipados.
        GranularityValidationError: Quando ``strict=True`` e a granularidade
            observada não é compatível com ``expected_step_minutes``.
    """

    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe deve ser um pandas.DataFrame.")
    if not dataframe.columns.is_unique:
        duplicated = sorted(
            str(col) for col in dataframe.columns[dataframe.columns.duplicated()].unique()
        )
        raise SourceSchemaError(
            f"O DataFrame contém nomes de colunas duplicados: {duplicated}."
        )
    if (
        isinstance(expected_step_minutes, bool)
        or not isinstance(expected_step_minutes, int)
        or expected_step_minutes <= 0
        or 60 % expected_step_minutes != 0
    ):
        raise ValueError(
            "expected_step_minutes deve ser um inteiro positivo divisor de 60 (ex.: 30)."
        )
    if not isinstance(strict, bool):
        raise ValueError("strict deve ser um valor booleano (True ou False).")

    missing = [col for col in ("ons_id", "instante") if col not in dataframe.columns]
    if missing:
        raise SourceSchemaError(
            f"Colunas obrigatórias ausentes para validação de granularidade: {missing}."
        )

    if isinstance(dataframe["instante"].dtype, pd.DatetimeTZDtype) or not (
        pd.api.types.is_datetime64_any_dtype(dataframe["instante"].dtype)
    ):
        raise SourceSchemaError(
            "A coluna 'instante' deve estar convertida para datetime64 sem fuso "
            f"(naive) antes de validar granularidade (dtype atual: {dataframe['instante'].dtype})."
        )

    result = dataframe.copy()
    instante = result["instante"]
    ons_id = result["ons_id"].astype("string")

    non_null_ts_mask = ~instante.isna()
    off_grid_mask = non_null_ts_mask & (
        ((instante.dt.minute % expected_step_minutes) != 0)
        | (instante.dt.second != 0)
        | (instante.dt.microsecond != 0)
    )
    off_grid_rows = int(off_grid_mask.sum())

    # Calcula transições consecutivas por ons_id válido sem alterar a ordem original de result.
    valid_for_diff = pd.DataFrame(
        {"ons_id": ons_id, "instante": instante}, index=result.index
    ).dropna(subset=["ons_id", "instante"])
    valid_for_diff = valid_for_diff[valid_for_diff["ons_id"].str.strip() != ""]

    distinct_ons_ids = int(valid_for_diff["ons_id"].nunique())
    checked_transitions = 0
    exact_step_transitions = 0
    gap_transitions = 0
    unexpected_step_transitions = 0
    observed_steps: set[float] = set()

    if not valid_for_diff.empty:
        sorted_pairs = valid_for_diff.sort_values(["ons_id", "instante"], kind="mergesort")
        diffs_seconds = (
            sorted_pairs.groupby("ons_id", sort=False)["instante"]
            .diff()
            .dt.total_seconds()
            .dropna()
        )
        checked_transitions = int(len(diffs_seconds))
        expected_seconds = float(expected_step_minutes * 60)

        for step_sec in diffs_seconds.unique():
            observed_steps.add(round(float(step_sec) / 60.0, 6))

        exact_mask = diffs_seconds == expected_seconds
        gap_mask = (diffs_seconds > expected_seconds) & (
            (diffs_seconds % expected_seconds) == 0.0
        )
        unexpected_mask = ~(exact_mask | gap_mask)

        exact_step_transitions = int(exact_mask.sum())
        gap_transitions = int(gap_mask.sum())
        unexpected_step_transitions = int(unexpected_mask.sum())

    duration_hours = expected_step_minutes / 60.0

    if strict and (off_grid_rows > 0 or unexpected_step_transitions > 0):
        raise GranularityValidationError(
            f"Granularidade incompatível com passo de {expected_step_minutes} minuto(s): "
            f"{off_grid_rows} timestamp(s) fora da grade, "
            f"{unexpected_step_transitions} transição(ões) inesperada(s). "
            f"Passos observados (min): {sorted(observed_steps)}."
        )

    duration_series = pd.Series(pd.NA, index=result.index, dtype="Float64")
    if off_grid_rows == 0 and unexpected_step_transitions == 0:
        duration_series.loc[non_null_ts_mask] = duration_hours
    else:
        # Em modo strict=False, atribui duração apenas aos timestamps alinhados à grade.
        duration_series.loc[non_null_ts_mask & (~off_grid_mask)] = duration_hours

    result["duracao_horas"] = duration_series

    report: GranularityReport = {
        "expected_step_minutes": expected_step_minutes,
        "validated_duration_hours": duration_hours,
        "total_rows": len(result),
        "distinct_ons_ids": distinct_ons_ids,
        "checked_transitions": checked_transitions,
        "exact_step_transitions": exact_step_transitions,
        "gap_transitions": gap_transitions,
        "unexpected_step_transitions": unexpected_step_transitions,
        "off_grid_timestamp_rows": off_grid_rows,
        "observed_step_minutes": tuple(sorted(observed_steps)),
    }
    return result, report


def _convert_single_numeric_series(
    series: pd.Series,
    *,
    column: str,
    source_column: str,
) -> tuple[pd.Series, ColumnNumericReport]:
    """Converte uma única série para ``Float64`` anulável rejeitando formatos inválidos."""

    # Se a série já é numérica (não booleana), valida finitude e converte para Float64.
    if pd.api.types.is_numeric_dtype(series.dtype) and not pd.api.types.is_bool_dtype(
        series.dtype
    ):
        numeric_float = pd.to_numeric(series, errors="coerce")
        original_null_mask = series.isna()
        non_null_mask = ~original_null_mask
        finite_mask = pd.Series(
            np.isfinite(numeric_float.fillna(0.0).to_numpy(dtype="float64")),
            index=series.index,
        )
        invalid_mask = non_null_mask & (~finite_mask)
        invalid_count = int(invalid_mask.sum())
        invalid_samples = tuple(
            str(val) for val in series[invalid_mask].iloc[:_MAX_INVALID_SAMPLES]
        )
        cleaned = numeric_float.mask(invalid_mask, pd.NA).astype("Float64")
        return cleaned, {
            "column": column,
            "source_column": source_column,
            "total_rows": len(series),
            "original_null_count": int(original_null_mask.sum()),
            "converted_count": int((~cleaned.isna()).sum()),
            "invalid_count": invalid_count,
            "invalid_samples": invalid_samples,
        }

    # Caso padrão (StringDtype / object): valida padrão decimal estrito antes do cast.
    raw_as_string = series.astype("string")
    original_null_mask = raw_as_string.isna()
    non_null_mask = ~original_null_mask

    matches_decimal = raw_as_string.str.fullmatch(_STRICT_DECIMAL_PATTERN).fillna(False)
    valid_text_mask = non_null_mask & matches_decimal

    parsed_float = pd.to_numeric(
        raw_as_string.where(valid_text_mask, pd.NA),
        errors="coerce",
    )
    finite_mask = pd.Series(
        np.isfinite(parsed_float.fillna(0.0).to_numpy(dtype="float64")),
        index=series.index,
    )
    invalid_mask = non_null_mask & (parsed_float.isna() | (~finite_mask))
    invalid_count = int(invalid_mask.sum())
    invalid_samples = tuple(
        str(val) for val in raw_as_string[invalid_mask].iloc[:_MAX_INVALID_SAMPLES]
    )

    cleaned = parsed_float.mask(invalid_mask, pd.NA).astype("Float64")
    return cleaned, {
        "column": column,
        "source_column": source_column,
        "total_rows": len(series),
        "original_null_count": int(original_null_mask.sum()),
        "converted_count": int((~cleaned.isna()).sum()),
        "invalid_count": invalid_count,
        "invalid_samples": invalid_samples,
    }


def _validate_raw_csv_path(file_path: Path | str) -> Path:
    """Valida o caminho do CSV antes de abrir o arquivo."""

    if isinstance(file_path, str):
        if not file_path.strip():
            raise ValueError("file_path não pode ser uma string vazia.")
        path = Path(file_path.strip())
    elif isinstance(file_path, Path):
        path = file_path
    else:
        raise ValueError("file_path deve ser um objeto Path ou uma string não vazia.")

    if not path.exists():
        raise FileNotFoundError(f"CSV bruto não encontrado: {path}.")
    if not path.is_file():
        raise ValueError(f"file_path não aponta para um arquivo: {path}.")
    return path


def _validate_csv_structure(path: Path) -> tuple[tuple[str, ...], int]:
    """Valida cabeçalho, largura e pontuação decimal de todos os registros.

    A leitura com :mod:`csv` respeita campos entre aspas, inclusive textos que
    contenham ``;``. Cada registro deve possuir exatamente a mesma quantidade de
    campos do cabeçalho; assim, o pandas não pode completar linhas truncadas nem
    inferir silenciosamente a primeira coluna como índice em linhas excedentes.
    """

    try:
        with path.open("r", encoding=CSV_ENCODING, newline="") as handle:
            reader = csv.reader(handle, delimiter=CSV_SEPARATOR, strict=True)
            header = next(reader, None)
            if not header or not any(name.strip() for name in header):
                raise RawCsvReadError(
                    f"O CSV bruto {path} está vazio ou não possui cabeçalho."
                )

            normalized_header = tuple(header)
            validate_source_schema(normalized_header)
            numeric_positions = {
                column: normalized_header.index(column)
                for column in NUMERIC_SOURCE_COLUMNS
            }
            row_count = 0
            for row_count, row in enumerate(reader, start=1):
                if len(row) != len(normalized_header):
                    raise RawCsvReadError(
                        f"Registro {row_count} do CSV bruto {path} possui {len(row)} "
                        f"campos; eram esperados {len(normalized_header)} "
                        f"(linha física terminada em {reader.line_num})."
                    )
                for column, position in numeric_positions.items():
                    value = row[position]
                    if "," in value:
                        raise RawCsvReadError(
                            f"Registro {row_count} do CSV bruto {path}, coluna {column!r}, "
                            f"usa vírgula em {value!r}. O separador decimal confirmado é "
                            f"{CSV_DECIMAL_SEPARATOR!r}."
                        )
    except UnicodeDecodeError as error:
        raise RawCsvReadError(
            f"O arquivo {path} não usa codificação UTF-8 válida (com ou sem BOM)."
        ) from error
    except RawCsvReadError:
        raise
    except (csv.Error, OSError) as error:
        raise RawCsvReadError(
            f"Falha ao validar a estrutura do CSV bruto {path}: {error}"
        ) from error

    return normalized_header, row_count
