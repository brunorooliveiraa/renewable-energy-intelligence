"""Testes dos indicadores, séries temporais e conciliação da GNRa (Fase 4)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.metrics import (
    build_generation_series,
    reconcile_gnra_values,
    summarize_interval_counts,
)
from src.transform import (
    GNRA_UNIT_STATUS,
    SOURCE_TO_INTERNAL_COLUMNS,
    SourceSchemaError,
    add_eligibility_flags,
    add_energy_and_preserve_gnra,
    convert_mwmed_columns,
    parse_instante_column,
    validate_granularity_and_add_duration,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_JAN_CE = (
    PROJECT_ROOT / "data" / "processed" / "restricoes_eolicas_ce_2025_01.parquet"
)


def _make_phase3_synthetic_df(
    overrides: dict[str, list[object]] | None = None,
) -> pd.DataFrame:
    """Cria um DataFrame sintético processado pela Fase 3 para testes unitários."""
    row_count = 3
    if overrides:
        row_count = len(next(iter(overrides.values())))

    data: dict[str, list[object]] = {
        col: [pd.NA] * row_count for col in SOURCE_TO_INTERNAL_COLUMNS.values()
    }
    data["estado_sigla"] = ["CE"] * row_count
    data["ons_id"] = ["CE_01", "CE_01", "CE_02"][:row_count]
    data["ceg"] = ["-", "-", "EOL.CV.CE.0001-0.01"][:row_count]
    data["instante"] = [
        "2025-01-01 00:00:00",
        "2025-01-01 00:30:00",
        "2025-01-02 01:00:00",
    ][:row_count]
    data["geracao_mwmed"] = ["100.0", "100.0", "60.0"][:row_count]
    data["geracao_referencia_mwmed"] = ["120.0", "100.0", "50.0"][:row_count]
    data["geracao_referencia_final_mwmed"] = ["120.0", pd.NA, pd.NA][:row_count]
    data["restricao_razao_codigo"] = ["REL", pd.NA, "ENE"][:row_count]
    data["restricao_origem_codigo"] = ["SIS", pd.NA, "SIS"][:row_count]
    data["geracao_nao_realizada_apurada"] = ["20.0", pd.NA, "0.0"][:row_count]

    if overrides:
        data.update(overrides)

    df = pd.DataFrame(
        {col: pd.Series(vals, dtype="string") for col, vals in data.items()}
    )
    df, _ = parse_instante_column(df)
    df, _ = convert_mwmed_columns(df)
    df, _ = add_eligibility_flags(df)
    df, _ = validate_granularity_and_add_duration(df)
    df, _ = add_energy_and_preserve_gnra(df)
    return df


def test_summarize_interval_counts_preserves_unrestricted_rows_and_totals() -> None:
    df = _make_phase3_synthetic_df()

    summary = summarize_interval_counts(df)

    assert summary["total_rows"] == 3
    assert summary["restricted_rows"] == 2
    assert summary["unrestricted_rows"] == 1
    assert int(summary["by_month"]["total_intervalos"].sum()) == 3
    assert int(summary["by_day"]["total_intervalos"].sum()) == 3
    assert int(summary["by_hour"]["total_intervalos"].sum()) == 3
    # by_reason_origin deve manter a linha sem restricao (<NA>) fechando em 3.
    assert int(summary["by_reason_origin"]["total_intervalos"].sum()) == 3
    assert summary["by_reason_origin"]["restricao_razao_codigo"].isna().sum() == 1


def test_build_generation_series_sums_mwh_and_returns_na_for_zero_eligible_day() -> None:
    df = _make_phase3_synthetic_df(
        {
            "ons_id": ["CE_01", "CE_01", "CE_01"],
            "instante": [
                "2025-01-01 00:00:00",
                "2025-01-01 00:30:00",
                "2025-01-02 00:00:00",
            ],
            "geracao_mwmed": ["100.0", "100.0", pd.NA],
            "geracao_referencia_final_mwmed": ["140.0", pd.NA, pd.NA],
            "restricao_razao_codigo": ["REL", pd.NA, pd.NA],
            "restricao_origem_codigo": ["SIS", pd.NA, pd.NA],
            "geracao_nao_realizada_apurada": ["40.0", pd.NA, pd.NA],
        }
    )

    daily = build_generation_series(df, granularity="day")
    monthly = build_generation_series(df, granularity="month")

    # Dia 2025-01-01: 2 patamares de 100 MWmed * 0.5h = 100.0 MWh; ref final = 70.0 MWh.
    assert daily.loc[0, "periodo"] == "2025-01-01"
    assert daily.loc[0, "geracao_verificada_mwh"] == 100.0
    assert daily.loc[0, "geracao_referencia_final_mwh"] == 70.0
    assert daily.loc[0, "cobertura_geracao_pct"] == 100.0

    # Dia 2025-01-02 sem geracao elegivel: deve ser pd.NA, NUNCA 0.0 falso.
    assert daily.loc[1, "periodo"] == "2025-01-02"
    assert daily.loc[1, "intervalos_elegiveis_geracao"] == 0
    assert pd.isna(daily.loc[1, "geracao_verificada_mwh"])
    assert pd.isna(daily.loc[1, "geracao_referencia_final_mwh"])

    assert len(monthly) == 1
    assert monthly.loc[0, "periodo"] == "2025-01"
    assert monthly.loc[0, "geracao_verificada_mwh"] == 100.0


def test_reconcile_gnra_exposes_negative_diff_and_divergences_without_summing_mwh() -> None:
    df = _make_phase3_synthetic_df(
        {
            "ons_id": ["CE_01", "CE_02", "CE_03"],
            "instante": [
                "2025-01-01 00:00:00",
                "2025-01-01 00:30:00",
                "2025-01-01 01:00:00",
            ],
            "geracao_mwmed": ["100.0", "60.0", "80.0"],
            "geracao_referencia_mwmed": ["120.0", "50.0", "100.0"],  # linha 2: ref < ger (-10)
            "restricao_razao_codigo": ["REL", "ENE", "REL"],
            "restricao_origem_codigo": ["SIS", "SIS", "SIS"],
            "geracao_nao_realizada_apurada": ["20.0", "0.0", "25.0"],  # linha 3 diverge em 5.0
        }
    )

    report = reconcile_gnra_values(df)

    assert report["gnra_unit_status"] == GNRA_UNIT_STATUS
    assert report["energy_aggregation_allowed"] is False
    assert report["eligible_gnra_rows"] == 3
    assert report["reconciled_rows"] == 3
    assert report["exact_match_rows"] == 2
    assert report["divergent_rows"] == 1
    assert report["negative_reference_minus_generation_rows"] == 1
    assert report["max_absolute_error"] == pytest.approx(5.0)


def test_metrics_reject_invalid_granularity_tolerance_and_schema() -> None:
    df = _make_phase3_synthetic_df()

    with pytest.raises(ValueError, match="granularity inválida"):
        build_generation_series(df, granularity="week")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="tolerance"):
        reconcile_gnra_values(df, tolerance=-1.0)

    with pytest.raises(SourceSchemaError, match="Colunas obrigatórias"):
        summarize_interval_counts(df.drop(columns=["geracao_verificada_mwh"]))


@pytest.mark.skipif(
    not PROCESSED_JAN_CE.is_file(),
    reason="Parquet processado de janeiro/2025 (CE) não encontrado no ambiente.",
)
def test_phase4_metrics_on_real_january_ce_parquet() -> None:
    df = pd.read_parquet(PROCESSED_JAN_CE)

    counts = summarize_interval_counts(df)
    daily = build_generation_series(df, granularity="day")
    monthly = build_generation_series(df, granularity="month")
    gnra_report = reconcile_gnra_values(df)

    assert counts["total_rows"] == 28_272
    assert counts["restricted_rows"] == 5_692
    assert counts["unrestricted_rows"] == 22_580
    assert len(counts["by_day"]) == 31
    assert len(counts["by_month"]) == 1
    assert len(counts["by_hour"]) == 24
    assert int(counts["by_reason_origin"]["total_intervalos"].sum()) == 28_272

    assert len(daily) == 31
    assert len(monthly) == 1
    assert float(daily["geracao_verificada_mwh"].sum()) == pytest.approx(
        float(monthly.loc[0, "geracao_verificada_mwh"]), rel=1e-9
    )
    assert float(monthly.loc[0, "geracao_verificada_mwh"]) == pytest.approx(
        362_247.938, abs=1e-2
    )

    assert gnra_report["energy_aggregation_allowed"] is False
    assert gnra_report["eligible_gnra_rows"] == 5_692
    assert gnra_report["reconciled_rows"] == 5_692
    assert gnra_report["divergent_rows"] == 0
    assert gnra_report["max_absolute_error"] is not None
    assert gnra_report["max_absolute_error"] < 1e-12
