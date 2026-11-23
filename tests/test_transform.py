"""Testes da leitura e padronização estrutural dos dados brutos do ONS."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import pandas as pd
import pytest

from src.transform import (
    CEG_AGGREGATE_PLACEHOLDER,
    EXPECTED_SOURCE_COLUMNS,
    INTERNAL_TO_SOURCE_COLUMNS,
    MWMED_INTERNAL_COLUMNS,
    SOURCE_TO_INTERNAL_COLUMNS,
    TIMESTAMP_TIMEZONE_POLICY,
    EmptyFilterResultError,
    IdentifierNormalizationError,
    NumericConversionError,
    RawCsvReadError,
    SourceSchemaError,
    TimestampConversionError,
    convert_mwmed_columns,
    filter_by_state,
    inspect_source_schema,
    parse_instante_column,
    preserve_operational_identifiers,
    read_raw_ons_csv,
    standardize_column_names,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
JANUARY_RAW_FILE = PROJECT_ROOT / "data" / "raw" / "RESTRICAO_COFF_EOLICA_2025_01.csv"
JANUARY_RAW_SHA256 = "2DBE2C4232126CC03BE12CD96977B58EBAD8FD0E07E4431F618A4696D17C02AC"


def _valid_csv_row() -> list[str]:
    values = {name: "" for name in EXPECTED_SOURCE_COLUMNS}
    values.update(
        {
            "id_subsistema": "NE",
            "nom_subsistema": "Nordeste",
            "id_estado": "CE",
            "nom_estado": "Ceará",
            "nom_usina": "Conjunto de teste",
            "id_ons": "TESTE_01",
            "ceg": "-",
            "din_instante": "2025-01-01 00:00:00",
            "val_geracao": "404.073",
        }
    )
    return [values[name] for name in EXPECTED_SOURCE_COLUMNS]


def _write_csv(
    path: Path,
    header: tuple[str, ...],
    row: list[str],
    *,
    encoding: str = "utf-8",
) -> None:
    with path.open("w", encoding=encoding, newline="") as handle:
        writer = csv.writer(handle, delimiter=";", lineterminator="\n")
        writer.writerow(header)
        writer.writerow(row)


def test_reads_confirmed_csv_format_without_early_type_conversion(tmp_path: Path) -> None:
    csv_path = tmp_path / "ons.csv"
    _write_csv(csv_path, EXPECTED_SOURCE_COLUMNS, _valid_csv_row())

    dataframe = read_raw_ons_csv(csv_path)

    assert dataframe.shape == (1, 24)
    assert dataframe.loc[0, "nom_estado"] == "Ceará"
    assert dataframe.loc[0, "val_geracao"] == "404.073"
    assert dataframe.loc[0, "ceg"] == "-"
    assert pd.isna(dataframe.loc[0, "val_geracaolimitada"])
    assert all(isinstance(dtype, pd.StringDtype) for dtype in dataframe.dtypes)


def test_column_mapping_is_complete_unique_and_reversible() -> None:
    assert len(EXPECTED_SOURCE_COLUMNS) == 24
    assert set(SOURCE_TO_INTERNAL_COLUMNS) == set(EXPECTED_SOURCE_COLUMNS)
    assert len(set(SOURCE_TO_INTERNAL_COLUMNS.values())) == 24
    assert {
        INTERNAL_TO_SOURCE_COLUMNS[internal]: source
        for source, internal in SOURCE_TO_INTERNAL_COLUMNS.items()
    } == {source: source for source in EXPECTED_SOURCE_COLUMNS}
    assert SOURCE_TO_INTERNAL_COLUMNS["val_geracao"] == "geracao_mwmed"
    assert (
        SOURCE_TO_INTERNAL_COLUMNS["val_geracaonaorealizadaapurada"]
        == "geracao_nao_realizada_apurada"
    )

    with pytest.raises(TypeError):
        SOURCE_TO_INTERNAL_COLUMNS["id_estado"] = "mutacao_proibida"  # type: ignore[index]
    with pytest.raises(TypeError):
        INTERNAL_TO_SOURCE_COLUMNS["estado_sigla"] = "mutacao_proibida"  # type: ignore[index]


def test_standardizes_columns_without_modifying_source_dataframe(tmp_path: Path) -> None:
    csv_path = tmp_path / "ons.csv"
    _write_csv(csv_path, EXPECTED_SOURCE_COLUMNS, _valid_csv_row())
    source = read_raw_ons_csv(csv_path)
    original_columns = tuple(source.columns)

    standardized = standardize_column_names(source)

    assert tuple(source.columns) == original_columns
    assert tuple(standardized.columns) == tuple(SOURCE_TO_INTERNAL_COLUMNS.values())
    assert standardized.loc[0, "estado_nome"] == "Ceará"
    assert standardized.loc[0, "geracao_mwmed"] == "404.073"


@pytest.mark.parametrize(
    ("header", "expected_message"),
    [
        (EXPECTED_SOURCE_COLUMNS[:-1], "colunas ausentes"),
        (EXPECTED_SOURCE_COLUMNS + ("campo_novo",), "colunas não mapeadas"),
        (
            EXPECTED_SOURCE_COLUMNS + (EXPECTED_SOURCE_COLUMNS[0],),
            "colunas duplicadas",
        ),
    ],
)
def test_rejects_changed_or_duplicated_source_schema(
    tmp_path: Path,
    header: tuple[str, ...],
    expected_message: str,
) -> None:
    csv_path = tmp_path / "schema_invalido.csv"
    row = [""] * len(header)
    _write_csv(csv_path, header, row)

    with pytest.raises(SourceSchemaError, match=expected_message):
        read_raw_ons_csv(csv_path)


def test_records_column_order_without_rejecting_a_safe_reordering() -> None:
    reversed_columns = tuple(reversed(EXPECTED_SOURCE_COLUMNS))

    report = inspect_source_schema(reversed_columns)

    assert report["missing"] == ()
    assert report["unexpected"] == ()
    assert report["duplicates"] == ()
    assert report["order_matches"] is False


def test_rejects_missing_empty_and_non_utf8_files(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="CSV bruto não encontrado"):
        read_raw_ons_csv(tmp_path / "ausente.csv")

    empty_file = tmp_path / "vazio.csv"
    empty_file.write_bytes(b"")
    with pytest.raises(RawCsvReadError, match="vazio ou não possui cabeçalho"):
        read_raw_ons_csv(empty_file)

    invalid_encoding = tmp_path / "latin1.csv"
    invalid_encoding.write_bytes("id_subsistema;descrição\n".encode("latin-1"))
    with pytest.raises(RawCsvReadError, match="não usa codificação UTF-8 válida"):
        read_raw_ons_csv(invalid_encoding)


def test_accepts_utf8_with_bom_without_changing_first_column(tmp_path: Path) -> None:
    csv_path = tmp_path / "ons_com_bom.csv"
    _write_csv(
        csv_path,
        EXPECTED_SOURCE_COLUMNS,
        _valid_csv_row(),
        encoding="utf-8-sig",
    )

    dataframe = read_raw_ons_csv(csv_path)

    assert tuple(dataframe.columns) == EXPECTED_SOURCE_COLUMNS
    assert dataframe.loc[0, "id_subsistema"] == "NE"


def test_rejects_comma_in_numeric_source_field(tmp_path: Path) -> None:
    csv_path = tmp_path / "decimal_com_virgula.csv"
    row = _valid_csv_row()
    row[EXPECTED_SOURCE_COLUMNS.index("val_geracao")] = "404,073"
    _write_csv(csv_path, EXPECTED_SOURCE_COLUMNS, row)

    with pytest.raises(RawCsvReadError, match="separador decimal confirmado"):
        read_raw_ons_csv(csv_path)


@pytest.mark.parametrize("width_delta", [-1, 1])
def test_rejects_rows_with_wrong_field_count(
    tmp_path: Path,
    width_delta: int,
) -> None:
    csv_path = tmp_path / f"largura_{width_delta}.csv"
    row = _valid_csv_row()
    malformed_row = row[:-1] if width_delta < 0 else row + ["EXTRA"]
    _write_csv(csv_path, EXPECTED_SOURCE_COLUMNS, malformed_row)

    with pytest.raises(RawCsvReadError, match=r"possui (23|25) campos; eram esperados 24"):
        read_raw_ons_csv(csv_path)


def test_accepts_quoted_semicolon_inside_text_field(tmp_path: Path) -> None:
    csv_path = tmp_path / "texto_com_ponto_e_virgula.csv"
    row = _valid_csv_row()
    row[EXPECTED_SOURCE_COLUMNS.index("dsc_restricao")] = "Motivo; detalhado"
    _write_csv(csv_path, EXPECTED_SOURCE_COLUMNS, row)

    dataframe = read_raw_ons_csv(csv_path)

    assert dataframe.loc[0, "dsc_restricao"] == "Motivo; detalhado"


@pytest.mark.skipif(
    not JANUARY_RAW_FILE.is_file(),
    reason="CSV bruto de janeiro de 2025 não está disponível neste ambiente.",
)
def test_reads_verified_january_source_file() -> None:
    digest = hashlib.sha256(JANUARY_RAW_FILE.read_bytes()).hexdigest().upper()
    assert digest == JANUARY_RAW_SHA256

    dataframe = read_raw_ons_csv(JANUARY_RAW_FILE)

    assert dataframe.shape == (232_128, 24)
    assert tuple(dataframe.columns) == EXPECTED_SOURCE_COLUMNS
    assert dataframe.loc[0, "din_instante"] == "2025-01-01 00:00:00"

    standardized = standardize_column_names(dataframe)
    with_timestamps, ts_report = parse_instante_column(standardized)
    typed_df, mwmed_reports = convert_mwmed_columns(with_timestamps)

    assert ts_report["invalid_count"] == 0
    assert ts_report["original_null_count"] == 0
    assert ts_report["timezone_policy"] == TIMESTAMP_TIMEZONE_POLICY
    assert pd.api.types.is_datetime64_ns_dtype(typed_df["instante"].dtype)
    assert all(rep["invalid_count"] == 0 for rep in mwmed_reports.values())
    assert all(
        isinstance(typed_df[col].dtype, pd.Float64Dtype)
        for col in MWMED_INTERNAL_COLUMNS
    )

    ce_df, state_report = filter_by_state(typed_df, "CE")
    ce_id_df, id_report = preserve_operational_identifiers(ce_df)

    assert state_report["input_rows"] == 232_128
    assert state_report["matched_rows"] == 28_272
    assert state_report["null_state_rows"] == 0
    assert len(ce_id_df) == 28_272
    assert id_report["distinct_ons_ids"] == 19
    assert id_report["ceg_placeholder_rows"] == 22_320
    assert id_report["ceg_present_rows"] == 5_952
    assert id_report["ceg_null_or_blank_rows"] == 0
    assert id_report["distinct_valid_cegs"] == 4
    assert isinstance(ce_id_df["ons_id"].dtype, pd.StringDtype)
    assert isinstance(ce_id_df["ceg"].dtype, pd.StringDtype)


def _sample_standardized_dataframe(
    overrides: dict[str, list[object]] | None = None,
) -> pd.DataFrame:
    """Cria um DataFrame sintético padronizado para testar tipagem sem I/O."""
    row_count = 2
    if overrides:
        row_count = len(next(iter(overrides.values())))

    data: dict[str, list[object]] = {
        internal: [pd.NA] * row_count
        for internal in SOURCE_TO_INTERNAL_COLUMNS.values()
    }
    data["estado_sigla"] = ["CE"] * row_count
    data["ons_id"] = ["TESTE_01"] * row_count
    data["instante"] = ["2025-01-01 00:00:00", "2025-01-01 00:30:00"][:row_count]
    data["geracao_mwmed"] = ["404.073125987", "0.0"][:row_count]
    data["disponibilidade_mwmed"] = ["500.25", pd.NA][:row_count]
    data["geracao_nao_realizada_apurada"] = ["12.345", pd.NA][:row_count]

    if overrides:
        data.update(overrides)

    return pd.DataFrame({col: pd.Series(vals, dtype="string") for col, vals in data.items()})


def test_parse_instante_converts_official_format_and_preserves_original_nulls() -> None:
    source = _sample_standardized_dataframe(
        {"instante": ["2025-01-01 00:00:00", pd.NA, "2025-01-31 23:30:00"]}
    )

    converted, report = parse_instante_column(source)

    assert isinstance(source["instante"].dtype, pd.StringDtype)
    assert pd.api.types.is_datetime64_ns_dtype(converted["instante"].dtype)
    assert converted["instante"].dt.tz is None
    assert converted.loc[0, "instante"] == pd.Timestamp("2025-01-01 00:00:00")
    assert pd.isna(converted.loc[1, "instante"])
    assert converted.loc[2, "instante"] == pd.Timestamp("2025-01-31 23:30:00")
    assert report == {
        "column": "instante",
        "source_column": "din_instante",
        "expected_format": "%Y-%m-%d %H:%M:%S",
        "timezone_policy": TIMESTAMP_TIMEZONE_POLICY,
        "total_rows": 3,
        "original_null_count": 1,
        "converted_count": 2,
        "invalid_count": 0,
        "invalid_samples": (),
    }


@pytest.mark.parametrize(
    "bad_timestamp",
    [
        "01/01/2025 00:00:00",
        "2025-02-30 00:00:00",
        "2025-01-01T00:00:00Z",
        "2025-01-01 00:00:00-03:00",
        " 2025-01-01 00:00:00 ",
        "   ",
        "invalido",
    ],
)
def test_parse_instante_rejects_invalid_or_ambiguous_timestamps(
    bad_timestamp: str,
) -> None:
    source = _sample_standardized_dataframe(
        {"instante": ["2025-01-01 00:00:00", bad_timestamp]}
    )

    with pytest.raises(TimestampConversionError, match="1 registro\\(s\\) inválido\\(s\\)"):
        parse_instante_column(source, strict=True)

    converted, report = parse_instante_column(source, strict=False)
    assert pd.isna(converted.loc[1, "instante"])
    assert report["invalid_count"] == 1
    assert report["invalid_samples"] == (bad_timestamp,)


def test_parse_instante_rejects_tz_aware_series() -> None:
    df = pd.DataFrame(
        {"instante": pd.to_datetime(["2025-01-01 00:00:00"], utc=True)}
    )

    with pytest.raises(TimestampConversionError, match="já possui fuso horário"):
        parse_instante_column(df)


def test_convert_mwmed_columns_preserves_precision_and_nulls_without_rounding() -> None:
    source = _sample_standardized_dataframe(
        {
            "geracao_mwmed": ["404.073125987", pd.NA],
            "geracao_limitada_mwmed": [pd.NA, "120.5"],
            "disponibilidade_mwmed": ["500.123456789", "0"],
            "geracao_referencia_mwmed": ["410.000001", pd.NA],
            "geracao_referencia_final_mwmed": [pd.NA, pd.NA],
            "geracao_nao_realizada_apurada": ["9.999", pd.NA],
        }
    )

    converted, reports = convert_mwmed_columns(source)

    # Tabela original permanece intacta como texto.
    assert isinstance(source["geracao_mwmed"].dtype, pd.StringDtype)
    # Coluna GNRa não é convertida por padrão (unidade pendente de confirmação).
    assert isinstance(converted["geracao_nao_realizada_apurada"].dtype, pd.StringDtype)

    for col in MWMED_INTERNAL_COLUMNS:
        assert isinstance(converted[col].dtype, pd.Float64Dtype)
        assert reports[col]["invalid_count"] == 0

    assert converted.loc[0, "geracao_mwmed"] == 404.073125987
    assert pd.isna(converted.loc[1, "geracao_mwmed"])
    assert converted.loc[0, "disponibilidade_mwmed"] == 500.123456789
    assert converted.loc[1, "disponibilidade_mwmed"] == 0.0
    assert reports["geracao_mwmed"]["original_null_count"] == 1
    assert reports["geracao_mwmed"]["converted_count"] == 1
    assert reports["geracao_referencia_final_mwmed"]["original_null_count"] == 2
    assert reports["geracao_referencia_final_mwmed"]["converted_count"] == 0


@pytest.mark.parametrize(
    "bad_numeric",
    ["404,073", "nan", "NaN", "inf", "-inf", "Infinity", "100 MW", " 10.5 ", "   "],
)
def test_convert_mwmed_columns_rejects_invalid_or_non_finite_strings(
    bad_numeric: str,
) -> None:
    source = _sample_standardized_dataframe(
        {"geracao_mwmed": ["10.5", bad_numeric]}
    )

    with pytest.raises(NumericConversionError, match="geracao_mwmed"):
        convert_mwmed_columns(source, strict=True)

    converted, reports = convert_mwmed_columns(source, strict=False)
    assert pd.isna(converted.loc[1, "geracao_mwmed"])
    assert reports["geracao_mwmed"]["invalid_count"] == 1
    assert reports["geracao_mwmed"]["invalid_samples"] == (bad_numeric,)


def test_convert_mwmed_columns_rejects_missing_column() -> None:
    df = pd.DataFrame({"geracao_mwmed": pd.Series(["10.0"], dtype="string")})

    with pytest.raises(SourceSchemaError, match="Colunas MWmed ausentes"):
        convert_mwmed_columns(df)


def test_filter_by_state_selects_ce_and_reports_excluded_and_nulls() -> None:
    source = _sample_standardized_dataframe(
        {
            "estado_sigla": ["CE", "RN", pd.NA, "CE"],
            "ons_id": ["CE_01", "RN_01", "XX_01", "CE_02"],
            "instante": [
                "2025-01-01 00:00:00",
                "2025-01-01 00:00:00",
                "2025-01-01 00:00:00",
                "2025-01-01 00:30:00",
            ],
        }
    )

    filtered, report = filter_by_state(source, "ce")

    assert len(source) == 4
    assert len(filtered) == 2
    assert list(filtered.index) == [0, 1]
    assert list(filtered["ons_id"]) == ["CE_01", "CE_02"]
    assert report == {
        "column": "estado_sigla",
        "source_column": "id_estado",
        "target_state": "CE",
        "input_rows": 4,
        "matched_rows": 2,
        "excluded_rows": 2,
        "null_state_rows": 1,
        "observed_states": ("CE", "RN"),
    }


@pytest.mark.parametrize("bad_state", ["", "Ceará", "C1", "CE ", "12"])
def test_filter_by_state_rejects_invalid_state_code(bad_state: str) -> None:
    source = _sample_standardized_dataframe()

    with pytest.raises(ValueError, match="state_code"):
        filter_by_state(source, bad_state)


def test_filter_by_state_handles_empty_match_explicitly() -> None:
    source = _sample_standardized_dataframe({"estado_sigla": ["RN", "BA"]})

    with pytest.raises(EmptyFilterResultError, match="estado_sigla='CE'"):
        filter_by_state(source, "CE", allow_empty=False)

    empty_df, report = filter_by_state(source, "CE", allow_empty=True)
    assert empty_df.empty
    assert list(empty_df.columns) == list(source.columns)
    assert report["matched_rows"] == 0
    assert report["observed_states"] == ("BA", "RN")


def test_preserve_operational_identifiers_keeps_string_dtype_and_dash_literal() -> None:
    source = _sample_standardized_dataframe(
        {
            "ons_id": ["001_CONJ", "002_USINA", "001_CONJ", "003_SEM_CEG"],
            "ceg": [
                CEG_AGGREGATE_PLACEHOLDER,
                "EOL.CV.CE.031234-5.01",
                CEG_AGGREGATE_PLACEHOLDER,
                pd.NA,
            ],
            "instante": [
                "2025-01-01 00:00:00",
                "2025-01-01 00:00:00",
                "2025-01-01 00:30:00",
                "2025-01-01 00:30:00",
            ],
        }
    )

    normalized, report = preserve_operational_identifiers(source)

    assert isinstance(normalized["ons_id"].dtype, pd.StringDtype)
    assert isinstance(normalized["ceg"].dtype, pd.StringDtype)
    assert normalized.loc[0, "ons_id"] == "001_CONJ"
    assert normalized.loc[0, "ceg"] == "-"
    assert normalized.loc[1, "ceg"] == "EOL.CV.CE.031234-5.01"
    assert pd.isna(normalized.loc[3, "ceg"])
    assert report == {
        "ons_id_column": "ons_id",
        "ceg_column": "ceg",
        "total_rows": 4,
        "distinct_ons_ids": 3,
        "null_ons_id_rows": 0,
        "blank_ons_id_rows": 0,
        "ceg_present_rows": 1,
        "ceg_placeholder_rows": 2,
        "ceg_null_or_blank_rows": 1,
        "distinct_valid_cegs": 1,
    }


def test_preserve_operational_identifiers_rejects_null_or_blank_ons_id() -> None:
    source = _sample_standardized_dataframe(
        {
            "ons_id": ["CE_01", pd.NA, "   "],
            "ceg": ["-", "-", "-"],
            "instante": [
                "2025-01-01 00:00:00",
                "2025-01-01 00:30:00",
                "2025-01-01 01:00:00",
            ],
        }
    )

    with pytest.raises(
        IdentifierNormalizationError, match="1 nulo\\(s\\) e 1 em branco"
    ):
        preserve_operational_identifiers(source, strict_ons_id=True)

    normalized, report = preserve_operational_identifiers(source, strict_ons_id=False)
    assert len(normalized) == 3
    assert report["null_ons_id_rows"] == 1
    assert report["blank_ons_id_rows"] == 1
    assert report["distinct_ons_ids"] == 1
