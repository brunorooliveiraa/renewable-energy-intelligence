"""Testes da orquestração mensal do pipeline ETL (src/pipeline.py)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.pipeline import main, run_monthly_pipeline
from src.transform import EXPECTED_SOURCE_COLUMNS
from tests.test_database import FakeLoadConnection, FakeLoadCursor


def _write_synthetic_raw_csv(csv_path: Path) -> None:
    """Grava um CSV sintético no formato oficial do ONS (separador ';' e decimal '.')."""
    header = ";".join(EXPECTED_SOURCE_COLUMNS)
    rows = [
        # CE - conjunto sem CEG, sem restrição
        "NE;NORDESTE;CE;CEARA;CONJUNTO SINTETICO A;CE_CONJ_01;-;2025-01-01 00:00:00;100.0;;120.0;110.0;;;;;PC1;SE TESTE 1;AGENTE A;;;;;",
        # CE - conjunto sem CEG, com restrição ENE/SIS 30 min depois
        "NE;NORDESTE;CE;CEARA;CONJUNTO SINTETICO A;CE_CONJ_01;-;2025-01-01 00:30:00;60.0;60.0;120.0;100.0;100.0;ENE;SIS;Restricao sintetica de teste;PC1;SE TESTE 1;AGENTE A;40.0;0.0;0.0;30.0;30.0",
        # Outra UF (RN) — deve ser filtrada fora do CE
        "NE;NORDESTE;RN;RIO GRANDE DO NORTE;USINA RN;RN_USI_01;EOL.CV.RN.000001-0.01;2025-01-01 00:00:00;80.0;;90.0;85.0;;;;;PC2;SE RN;AGENTE B;;;;;",
    ]
    csv_path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8-sig")


def test_run_monthly_pipeline_transforms_and_loads_with_skip_extract(tmp_path: Path) -> None:
    raw_csv = tmp_path / "ons_eolica_2025_01.csv"
    processed_dir = tmp_path / "processed"
    _write_synthetic_raw_csv(raw_csv)

    cursor = FakeLoadCursor(execucao_id=123)
    conn = FakeLoadConnection(cursor)

    report = run_monthly_pipeline(
        year=2025,
        month=1,
        state_code="CE",
        processed_dir=processed_dir,
        input_path=raw_csv,
        skip_extract=True,
        database_url="postgresql://user:pw@db.neon.tech/neondb?sslmode=require",
        connect_fn=lambda dsn, *, connect_timeout: conn,
    )

    assert report["extracted"] is False
    assert report["loaded"] is True
    assert report["input_rows"] == 3
    assert report["output_rows"] == 2
    assert report["load_report"] is not None
    assert report["load_report"]["execucao_id"] == 123
    assert report["load_report"]["dim_rows_upserted"] == 1
    assert report["load_report"]["fact_rows_upserted"] == 2
    assert Path(report["parquet_path"]).exists()
    assert Path(report["quality_report_path"]).exists()


def test_run_monthly_pipeline_skip_load_does_not_connect_to_database(tmp_path: Path) -> None:
    raw_csv = tmp_path / "ons_eolica_2025_01.csv"
    processed_dir = tmp_path / "processed"
    _write_synthetic_raw_csv(raw_csv)

    def fail_if_called(*args: object, **kwargs: object) -> object:
        raise AssertionError("connect_fn não deve ser chamado com skip_load=True")

    report = run_monthly_pipeline(
        year=2025,
        month=1,
        state_code="CE",
        processed_dir=processed_dir,
        input_path=raw_csv,
        skip_extract=True,
        skip_load=True,
        connect_fn=fail_if_called,
    )

    assert report["loaded"] is False
    assert report["load_report"] is None
    assert report["output_rows"] == 2


def test_run_monthly_pipeline_rejects_invalid_arguments_and_missing_csv(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="year"):
        run_monthly_pipeline(year=25, month=1, skip_extract=True, skip_load=True)

    with pytest.raises(ValueError, match="month"):
        run_monthly_pipeline(year=2025, month=13, skip_extract=True, skip_load=True)

    with pytest.raises(ValueError, match="state_code"):
        run_monthly_pipeline(year=2025, month=1, state_code="CEARA", skip_extract=True, skip_load=True)

    with pytest.raises(ValueError, match="input_path só pode ser usado com skip_extract=True"):
        run_monthly_pipeline(
            year=2025,
            month=1,
            input_path=tmp_path / "qualquer.csv",
            skip_extract=False,
            skip_load=True,
        )

    with pytest.raises(FileNotFoundError, match="CSV bruto não encontrado"):
        run_monthly_pipeline(
            year=2025,
            month=1,
            input_path=tmp_path / "inexistente.csv",
            skip_extract=True,
            skip_load=True,
        )


def test_pipeline_cli_succeeds_with_skip_load_and_fails_cleanly_on_missing_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    raw_csv = tmp_path / "ons_eolica_2025_01.csv"
    processed_dir = tmp_path / "processed"
    _write_synthetic_raw_csv(raw_csv)

    exit_ok = main(
        [
            "--year",
            "2025",
            "--month",
            "1",
            "--state",
            "CE",
            "--skip-extract",
            "--skip-load",
            "--input",
            str(raw_csv),
            "--processed-dir",
            str(processed_dir),
        ]
    )
    out_ok = capsys.readouterr()
    assert exit_ok == 0
    assert "[ok] eolica CE 2025-01" in out_ok.out

    exit_err = main(
        [
            "--year",
            "2025",
            "--month",
            "1",
            "--state",
            "CE",
            "--skip-extract",
            "--skip-load",
            "--input",
            str(tmp_path / "nao_existe.csv"),
        ]
    )
    out_err = capsys.readouterr()
    assert exit_err == 1
    assert "Erro no pipeline:" in out_err.err
