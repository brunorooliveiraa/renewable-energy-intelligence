"""Testes das regras de unicidade de chave e qualidade de dados (Fase 3)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.transform import (
    MWMED_INTERNAL_COLUMNS,
    SOURCE_TO_INTERNAL_COLUMNS,
    SourceSchemaError,
    convert_mwmed_columns,
    filter_by_state,
    parse_instante_column,
    preserve_operational_identifiers,
    read_raw_ons_csv,
    standardize_column_names,
)
from src.validate import (
    CANDIDATE_KEY_COLUMNS,
    DataQualityError,
    DuplicateKeyError,
    check_and_resolve_key_duplicates,
    run_quality_checks,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JANUARY_RAW_FILE = PROJECT_ROOT / "data" / "raw" / "RESTRICAO_COFF_EOLICA_2025_01.csv"


def _typed_synthetic_dataframe(
    overrides: dict[str, list[object]] | None = None,
) -> pd.DataFrame:
    """Cria um DataFrame sintético já padronizado e tipado para testes de qualidade."""
    row_count = 2
    if overrides:
        row_count = len(next(iter(overrides.values())))

    data: dict[str, list[object]] = {
        col: [pd.NA] * row_count for col in SOURCE_TO_INTERNAL_COLUMNS.values()
    }
    data["estado_sigla"] = ["CE"] * row_count
    data["ons_id"] = [f"CE_0{i + 1}" for i in range(row_count)]
    data["ceg"] = ["-"] * row_count
    data["instante"] = [
        f"2025-01-01 00:{30 * (i % 2):02d}:00" for i in range(row_count)
    ]
    data["geracao_mwmed"] = ["100.5"] * row_count
    data["disponibilidade_mwmed"] = ["120.0"] * row_count
    data["restricao_razao_codigo"] = ["REL"] * row_count
    data["restricao_origem_codigo"] = ["SIS"] * row_count

    if overrides:
        data.update(overrides)

    df = pd.DataFrame(
        {col: pd.Series(vals, dtype="string") for col, vals in data.items()}
    )
    df, _ = parse_instante_column(df, strict=False)
    df, _ = convert_mwmed_columns(df, strict=False)
    return df


def test_check_duplicates_passes_when_candidate_key_is_unique() -> None:
    df = _typed_synthetic_dataframe()

    result, report = check_and_resolve_key_duplicates(df, on_duplicate="raise")

    assert len(result) == 2
    assert report == {
        "key_columns": CANDIDATE_KEY_COLUMNS,
        "total_rows": 2,
        "null_key_rows": 0,
        "duplicate_key_groups": 0,
        "duplicate_key_rows": 0,
        "exact_duplicate_rows_dropped": 0,
        "conflicting_key_groups": 0,
        "conflicting_key_rows": 0,
        "resolution_policy": "raise",
        "sample_duplicate_keys": (),
    }


def test_check_duplicates_handles_exact_duplicates_by_policy() -> None:
    df = _typed_synthetic_dataframe(
        {
            "ons_id": ["CE_01", "CE_01", "CE_02"],
            "instante": [
                "2025-01-01 00:00:00",
                "2025-01-01 00:00:00",
                "2025-01-01 00:30:00",
            ],
            "geracao_mwmed": ["100.0", "100.0", "80.0"],
            "disponibilidade_mwmed": ["120.0", "120.0", "90.0"],
            "restricao_razao_codigo": ["REL", "REL", pd.NA],
            "restricao_origem_codigo": ["SIS", "SIS", pd.NA],
        }
    )

    with pytest.raises(DuplicateKeyError, match="1 grupo\\(s\\) \\(2 linha\\(s\\)\\)"):
        check_and_resolve_key_duplicates(df, on_duplicate="raise")

    reported_df, report_only = check_and_resolve_key_duplicates(
        df, on_duplicate="report"
    )
    assert len(reported_df) == 3
    assert report_only["duplicate_key_groups"] == 1
    assert report_only["conflicting_key_groups"] == 0
    assert report_only["exact_duplicate_rows_dropped"] == 0

    cleaned_df, dropped_report = check_and_resolve_key_duplicates(
        df, on_duplicate="drop_exact_only"
    )
    assert len(cleaned_df) == 2
    assert dropped_report["exact_duplicate_rows_dropped"] == 1
    assert dropped_report["conflicting_key_groups"] == 0


def test_check_duplicates_always_rejects_conflicting_keys_even_in_drop_exact_only() -> None:
    df = _typed_synthetic_dataframe(
        {
            "ons_id": ["CE_01", "CE_01"],
            "instante": ["2025-01-01 00:00:00", "2025-01-01 00:00:00"],
            "geracao_mwmed": ["100.0", "105.0"],
        }
    )

    with pytest.raises(DuplicateKeyError, match="valores divergentes"):
        check_and_resolve_key_duplicates(df, on_duplicate="drop_exact_only")

    _, report = check_and_resolve_key_duplicates(df, on_duplicate="report")
    assert report["duplicate_key_groups"] == 1
    assert report["conflicting_key_groups"] == 1
    assert report["conflicting_key_rows"] == 2


def test_check_duplicates_separates_null_keys_without_false_positive_duplicates() -> None:
    df = _typed_synthetic_dataframe(
        {
            "ons_id": [pd.NA, pd.NA, "CE_01"],
            "instante": [
                "2025-01-01 00:00:00",
                "2025-01-01 00:00:00",
                "2025-01-01 00:30:00",
            ],
        }
    )

    result, report = check_and_resolve_key_duplicates(df, on_duplicate="raise")

    assert len(result) == 3
    assert report["null_key_rows"] == 2
    assert report["duplicate_key_rows"] == 0


def test_run_quality_checks_detects_negatives_unknown_codes_and_out_of_month() -> None:
    df = _typed_synthetic_dataframe(
        {
            "ons_id": ["CE_01", "CE_02", "CE_03"],
            "instante": [
                "2025-01-01 00:00:00",
                "2025-02-01 00:00:00",
                "2025-01-15 12:00:00",
            ],
            "geracao_mwmed": ["-5.2", "10.0", pd.NA],
            "geracao_limitada_mwmed": [pd.NA, "-1.0", "50.0"],
            "restricao_razao_codigo": ["REL", "XYZ", "ENE"],
            "restricao_origem_codigo": ["SIS", "EXT", pd.NA],
        }
    )

    report = run_quality_checks(
        df, expected_year=2025, expected_month=1, strict=False
    )

    assert report["total_rows"] == 3
    assert report["negative_value_counts"]["geracao_mwmed"] == 1
    assert report["negative_value_counts"]["geracao_limitada_mwmed"] == 1
    assert report["negative_value_counts"]["disponibilidade_mwmed"] == 0
    assert report["unknown_reason_codes"] == ("XYZ",)
    assert report["unknown_reason_rows"] == 1
    assert report["unknown_origin_codes"] == ("EXT",)
    assert report["unknown_origin_rows"] == 1
    assert report["reason_without_origin_rows"] == 1
    assert report["origin_without_reason_rows"] == 0
    assert report["out_of_month_rows"] == 1
    assert report["out_of_month_samples"] == ("2025-02-01 00:00:00",)
    assert report["has_blocking_anomalies"] is True

    with pytest.raises(DataQualityError, match="Anomalias bloqueantes"):
        run_quality_checks(df, expected_year=2025, expected_month=1, strict=True)


def test_run_quality_checks_reports_mwmed_negatives_without_blocking() -> None:
    """Negativos em MWmed são evidência, não erro sem regra oficial específica."""
    df = _typed_synthetic_dataframe(
        {
            "geracao_mwmed": ["-5.2"],
            "geracao_limitada_mwmed": ["-1.0"],
        }
    )

    report = run_quality_checks(
        df, expected_year=2025, expected_month=1, strict=True
    )

    assert report["negative_value_counts"]["geracao_mwmed"] == 1
    assert report["negative_value_counts"]["geracao_limitada_mwmed"] == 1
    assert report["has_blocking_anomalies"] is False


def test_run_quality_checks_rejects_untyped_columns_and_partial_period_args() -> None:
    df = _typed_synthetic_dataframe()

    with pytest.raises(ValueError, match="expected_year e expected_month juntos"):
        run_quality_checks(df, expected_year=2025, expected_month=None)

    untyped_instante = df.copy()
    untyped_instante["instante"] = untyped_instante["instante"].astype("string")
    with pytest.raises(SourceSchemaError, match="datetime64 sem fuso"):
        run_quality_checks(untyped_instante)

    untyped_mwmed = df.copy()
    untyped_mwmed["geracao_mwmed"] = untyped_mwmed["geracao_mwmed"].astype("string")
    with pytest.raises(SourceSchemaError, match="tipo numérico"):
        run_quality_checks(untyped_mwmed)


def test_run_quality_checks_accepts_pandas3_datetime64_us_and_rejects_duplicate_columns() -> None:
    df = _typed_synthetic_dataframe()
    df["instante"] = df["instante"].astype("datetime64[us]")

    report = run_quality_checks(df, expected_year=2025, expected_month=1, strict=True)
    assert report["has_blocking_anomalies"] is False
    assert report["out_of_month_rows"] == 0

    df_dup_cols = pd.concat([df, df[["geracao_mwmed"]]], axis=1)
    with pytest.raises(SourceSchemaError, match="nomes de colunas duplicados"):
        run_quality_checks(df_dup_cols, expected_year=2025, expected_month=1)
    with pytest.raises(SourceSchemaError, match="nomes de colunas duplicados"):
        check_and_resolve_key_duplicates(df_dup_cols)


@pytest.mark.skipif(
    not JANUARY_RAW_FILE.is_file(),
    reason="CSV bruto de janeiro de 2025 não está disponível neste ambiente.",
)
def test_quality_checks_and_key_uniqueness_on_verified_january_ce_subset() -> None:
    raw_df = read_raw_ons_csv(JANUARY_RAW_FILE)
    std_df = standardize_column_names(raw_df)
    ts_df, _ = parse_instante_column(std_df)
    num_df, _ = convert_mwmed_columns(ts_df)
    ce_df, _ = filter_by_state(num_df, "CE")
    ce_df, _ = preserve_operational_identifiers(ce_df)

    checked_df, dup_report = check_and_resolve_key_duplicates(
        ce_df, on_duplicate="raise"
    )
    quality_report = run_quality_checks(
        checked_df, expected_year=2025, expected_month=1, strict=True
    )

    assert len(checked_df) == 28_272
    assert dup_report["duplicate_key_rows"] == 0
    assert dup_report["null_key_rows"] == 0
    assert quality_report["has_blocking_anomalies"] is False
    assert quality_report["out_of_month_rows"] == 0
    assert quality_report["unknown_reason_rows"] == 0
    assert quality_report["unknown_origin_rows"] == 0
    assert quality_report["reason_without_origin_rows"] == 0
    assert quality_report["origin_without_reason_rows"] == 0
    assert all(
        quality_report["negative_value_counts"][col] == 0
        for col in MWMED_INTERNAL_COLUMNS
    )
    assert quality_report["observed_min_timestamp"] == "2025-01-01 00:00:00"
    assert quality_report["observed_max_timestamp"] == "2025-01-31 23:30:00"


def test_run_quality_checks_raises_type_error_for_non_bool_strict() -> None:
    df = pd.DataFrame({"ons_id": ["CE_01"]})
    with pytest.raises(TypeError, match="strict"):
        run_quality_checks(df, strict="sim")  # type: ignore[arg-type]
