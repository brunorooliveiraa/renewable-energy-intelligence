"""Testes dos indicadores, séries temporais e conciliação da GNRa (Fase 4)."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

from src.metrics import (
    build_enterprise_ranking,
    build_generation_series,
    generate_basic_phase4_charts,
    identify_peak_restriction_periods,
    reconcile_gnra_values,
    summarize_coverage,
    summarize_interval_counts,
    summarize_reasons_and_origins,
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

    for non_finite in (math.nan, math.inf, -math.inf):
        with pytest.raises(ValueError, match="finito"):
            reconcile_gnra_values(df, tolerance=non_finite)

    with pytest.raises(SourceSchemaError, match="Colunas obrigatórias"):
        summarize_interval_counts(df.drop(columns=["geracao_verificada_mwh"]))


def test_generate_basic_phase4_charts_creates_valid_svg_files(tmp_path: Path) -> None:
    df = _make_phase3_synthetic_df()
    charts = generate_basic_phase4_charts(df, tmp_path)

    assert set(charts) == {
        "geracao_diaria_mwh",
        "restricoes_por_razao",
        "restricoes_por_hora",
    }
    for chart_path in charts.values():
        assert chart_path.is_file()
        content = chart_path.read_text(encoding="utf-8")
        assert content.startswith("<svg ")
        assert "</svg>" in content


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

    coverage = summarize_coverage(df)
    assert coverage["total_rows"] == 28_272
    assert coverage["elegivel_geracao_verificada_rows"] == 28_272
    assert coverage["elegivel_referencia_final_rows"] == 2_772
    assert coverage["restricao_com_referencia_final_rows"] == 2_772
    assert coverage["restricao_sem_referencia_final_rows"] == 2_920
    assert coverage["elegivel_enriquecimento_aneel_rows"] == 5_952
    assert coverage["sem_ceg_individual_rows"] == 22_320

    ranking = build_enterprise_ranking(df)
    assert len(ranking) == 19
    assert int((ranking["tipo_empreendimento"] == "conjunto_sem_ceg").sum()) == 15
    assert int((ranking["tipo_empreendimento"] == "usina_com_ceg").sum()) == 4
    assert int(ranking["intervalos_com_restricao"].sum()) == 5_692

    reasons_summary = summarize_reasons_and_origins(df)
    assert reasons_summary["total_restricted_rows"] == 5_692
    by_reason = reasons_summary["by_reason"].set_index("restricao_razao_codigo")
    assert int(by_reason.loc["ENE", "intervalos_com_restricao"]) == 2_913
    assert int(by_reason.loc["REL", "intervalos_com_restricao"]) == 2_772
    assert int(by_reason.loc["CNF", "intervalos_com_restricao"]) == 7
    assert int(by_reason.loc["PAR", "intervalos_com_restricao"]) == 0
    assert pd.isna(by_reason.loc["PAR", "geracao_verificada_mwh"])
    assert pd.isna(by_reason.loc["ENE", "geracao_referencia_final_mwh"])
    by_origin = reasons_summary["by_origin"].set_index("restricao_origem_codigo")
    assert int(by_origin.loc["SIS", "intervalos_com_restricao"]) == 5_685
    assert int(by_origin.loc["LOC", "intervalos_com_restricao"]) == 7

    peaks = identify_peak_restriction_periods(df, top_n=5)
    assert len(peaks["top_days"]) == 5
    assert peaks["top_days"].loc[0, "data"] == "2025-01-23"
    assert int(peaks["top_days"].loc[0, "intervalos_com_restricao"]) == 636
    assert len(peaks["top_hours"]) == 5
    assert int(peaks["top_hours"].loc[0, "hora"]) == 9
    assert int(peaks["top_hours"].loc[0, "intervalos_com_restricao"]) == 518


def test_summarize_coverage_handles_reference_gaps_and_empty_dataframe() -> None:
    df = _make_phase3_synthetic_df()
    cov = summarize_coverage(df)

    assert cov["total_rows"] == 3
    assert cov["elegivel_referencia_final_rows"] == 1
    assert cov["sem_referencia_final_rows"] == 2
    assert cov["restricao_com_referencia_final_rows"] == 1
    assert cov["restricao_sem_referencia_final_rows"] == 1
    assert cov["elegivel_enriquecimento_aneel_rows"] == 1
    assert cov["sem_ceg_individual_rows"] == 2

    empty_cov = summarize_coverage(df.iloc[0:0])
    assert empty_cov["total_rows"] == 0
    assert empty_cov["cobertura_geracao_verificada_pct"] == 0.0


def test_build_enterprise_ranking_deduplicates_ons_id_and_classifies_conjuntos() -> None:
    df = _make_phase3_synthetic_df(
        {
            "ons_id": ["CE_01", "CE_01", "CE_02"],
            "usina_nome": ["Conjunto Antigo", "Conjunto Novo", "Usina Individual"],
            "ceg": ["-", "-", "EOL.CV.CE.0001-0.01"],
            "instante": [
                "2025-01-01 00:00:00",
                "2025-01-01 00:30:00",
                "2025-01-01 00:00:00",
            ],
            "geracao_mwmed": ["100.0", "100.0", "80.0"],
            "geracao_referencia_final_mwmed": ["120.0", pd.NA, pd.NA],
            "restricao_razao_codigo": ["REL", "ENE", pd.NA],
            "restricao_origem_codigo": ["SIS", "SIS", pd.NA],
            "geracao_nao_realizada_apurada": ["20.0", "5.0", pd.NA],
        }
    )

    ranking = build_enterprise_ranking(df, sort_by="intervalos_com_restricao")
    assert len(ranking) == 2
    assert ranking.loc[0, "ons_id"] == "CE_01"
    assert ranking.loc[0, "usina_nome"] == "Conjunto Novo"
    assert ranking.loc[0, "tipo_empreendimento"] == "conjunto_sem_ceg"
    assert ranking.loc[0, "intervalos_com_restricao"] == 2
    assert ranking.loc[0, "geracao_verificada_mwh"] == 100.0
    assert ranking.loc[1, "ons_id"] == "CE_02"
    assert ranking.loc[1, "tipo_empreendimento"] == "usina_com_ceg"
    assert pd.isna(ranking.loc[1, "geracao_referencia_final_mwh"])

    with pytest.raises(ValueError, match="sort_by inválido"):
        build_enterprise_ranking(df, sort_by="invalido")  # type: ignore[arg-type]


def test_summarize_reasons_and_origins_includes_zero_official_codes_with_na_energy() -> None:
    df = _make_phase3_synthetic_df()

    summary = summarize_reasons_and_origins(df, include_zero_official_codes=True)
    by_reason = summary["by_reason"].set_index("restricao_razao_codigo")
    assert set(by_reason.index) == {"REL", "CNF", "ENE", "PAR"}
    assert int(by_reason.loc["PAR", "intervalos_com_restricao"]) == 0
    assert pd.isna(by_reason.loc["PAR", "geracao_verificada_mwh"])
    assert pd.isna(by_reason.loc["ENE", "geracao_referencia_final_mwh"])

    by_origin = summary["by_origin"].set_index("restricao_origem_codigo")
    assert set(by_origin.index) == {"LOC", "SIS"}
    assert int(by_origin.loc["LOC", "intervalos_com_restricao"]) == 0
    assert pd.isna(by_origin.loc["LOC", "geracao_verificada_mwh"])


def test_identify_peak_restriction_periods_orders_days_and_hours_and_validates_top_n() -> None:
    df = _make_phase3_synthetic_df(
        {
            "ons_id": ["CE_01", "CE_02", "CE_01"],
            "instante": [
                "2025-01-01 09:00:00",
                "2025-01-01 09:30:00",
                "2025-01-02 10:00:00",
            ],
            "geracao_mwmed": ["100.0", "80.0", "50.0"],
            "restricao_razao_codigo": ["REL", "ENE", pd.NA],
            "restricao_origem_codigo": ["SIS", "SIS", pd.NA],
            "geracao_nao_realizada_apurada": ["20.0", "10.0", pd.NA],
        }
    )

    peaks = identify_peak_restriction_periods(df, top_n=2)
    assert peaks["top_n"] == 2
    assert peaks["top_days"].loc[0, "data"] == "2025-01-01"
    assert int(peaks["top_days"].loc[0, "intervalos_com_restricao"]) == 2
    assert int(peaks["top_days"].loc[0, "empreendimentos_afetados"]) == 2
    assert int(peaks["top_hours"].loc[0, "hora"]) == 9
    assert int(peaks["top_hours"].loc[0, "intervalos_com_restricao"]) == 2

    empty_peaks = identify_peak_restriction_periods(df.iloc[0:0], top_n=3)
    assert empty_peaks["top_days"].empty
    assert empty_peaks["top_hours"].empty

    for bad_top_n in (0, -1, True):
        with pytest.raises(ValueError, match="top_n"):
            identify_peak_restriction_periods(df, top_n=bad_top_n)  # type: ignore[arg-type]
