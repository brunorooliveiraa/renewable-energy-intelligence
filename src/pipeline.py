"""Orquestração do pipeline ETL mensal (Extração → Transformação → PostgreSQL).

Integra as etapas validadas das Fases 2, 3 e 5:
1. Extração oficial via API CKAN do ONS (``src.extract``) ou leitura de CSV bruto já coletado.
2. Transformação, validação de qualidade e persistência em Parquet (``src.transform``).
3. Carga idempotente em ``dim_empreendimentos``, ``fact_restricoes`` e ``etl_execucoes``
   no PostgreSQL Neon via ``psycopg`` v3 (``src.database``).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Literal, TypedDict

from src.database import (
    DEFAULT_CONNECT_TIMEOUT_SECONDS,
    DEFAULT_SCHEMA_PATH,
    GNRA_UNIT_STATUS_DEFAULT,
    METHODOLOGY_VERSION,
    DatabaseConfigError,
    DatabaseConnectionError,
    DatabaseLoadError,
    DatabaseLoadReport,
    DatabaseSchemaError,
    apply_schema,
    load_dataframe_to_postgres,
)
from src.extract import (
    DEFAULT_RAW_DIR,
    ResourceDiscoveryError,
    ResourceDownloadError,
    build_metadata_filepath,
    build_raw_filepath,
    download_monthly_resource,
    read_collection_metadata,
)
from src.transform import (
    DEFAULT_MVP_STATE,
    DEFAULT_PROCESSED_DIR,
    transform_monthly_dataset,
)


class PipelineRunReport(TypedDict):
    """Resumo auditável de uma execução mensal completa do pipeline ETL."""

    source: str
    state_code: str
    year: int
    month: int
    raw_csv_path: str
    parquet_path: str
    quality_report_path: str
    extracted: bool
    loaded: bool
    input_rows: int
    output_rows: int
    load_report: DatabaseLoadReport | None


def _validate_pipeline_args(
    *,
    year: int,
    month: int,
    state_code: str,
    source: str,
    skip_extract: bool,
    skip_load: bool,
    init_schema: bool,
    overwrite_raw: bool,
) -> tuple[int, int, str, str]:
    if isinstance(year, bool) or not isinstance(year, int) or not (1000 <= year <= 9999):
        raise ValueError("year deve ser um inteiro de 4 dígitos (ex.: 2025).")
    if isinstance(month, bool) or not isinstance(month, int) or not (1 <= month <= 12):
        raise ValueError("month deve ser um inteiro entre 1 e 12.")
    if not isinstance(state_code, str) or len(state_code.strip()) != 2 or not state_code.strip().isalpha():
        raise ValueError("state_code deve ser uma sigla de UF com 2 letras (ex.: 'CE').")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("source deve ser uma string não vazia (ex.: 'eolica').")

    for flag_name, flag_value in (
        ("skip_extract", skip_extract),
        ("skip_load", skip_load),
        ("init_schema", init_schema),
        ("overwrite_raw", overwrite_raw),
    ):
        if not isinstance(flag_value, bool):
            raise TypeError(f"{flag_name} deve ser um valor booleano.")

    return year, month, state_code.strip().upper(), source.strip().lower()


def run_monthly_pipeline(
    *,
    year: int,
    month: int,
    state_code: str = DEFAULT_MVP_STATE,
    source: str = "eolica",
    raw_dir: Path | str = DEFAULT_RAW_DIR,
    processed_dir: Path | str = DEFAULT_PROCESSED_DIR,
    input_path: Path | str | None = None,
    skip_extract: bool = False,
    skip_load: bool = False,
    init_schema: bool = False,
    overwrite_raw: bool = False,
    on_duplicate: Literal["raise", "report", "drop_exact_only"] = "raise",
    database_url: str | None = None,
    schema_path: Path | str = DEFAULT_SCHEMA_PATH,
    connect_timeout: int = DEFAULT_CONNECT_TIMEOUT_SECONDS,
    connect_fn: Callable[..., Any] | None = None,
) -> PipelineRunReport:
    """Executa o pipeline ETL mensal de ponta a ponta (Extração → Transformação → Carga).

    Args:
        year: Ano de referência com 4 dígitos.
        month: Mês de referência entre 1 e 12.
        state_code: Sigla da UF (padrão ``'CE'``).
        source: Fonte configurada em ``src.extract`` (padrão ``'eolica'``).
        raw_dir: Diretório para arquivos brutos baixados.
        processed_dir: Diretório para arquivos Parquet e relatórios de qualidade.
        input_path: Caminho opcional para um CSV bruto já existente (requer ``skip_extract=True``).
        skip_extract: Quando ``True``, pula o download CKAN e usa o CSV bruto local.
        skip_load: Quando ``True``, executa apenas até a geração do Parquet/relatório.
        init_schema: Quando ``True``, aplica ``sql/schema.sql`` de forma idempotente antes da carga.
        overwrite_raw: Permite substituir revisão local caso o ONS tenha publicado nova versão.
        on_duplicate: Política de duplicidade na chave ``(ons_id, instante)``.
        database_url: String de conexão opcional (se omitida, usa ``DIRECT_DATABASE_URL``/``DATABASE_URL``).
        schema_path: Caminho do DDL PostgreSQL usado quando ``init_schema=True``.
        connect_timeout: Timeout de conexão PostgreSQL em segundos.
        connect_fn: Função de conexão injetável para testes unitários.
    """
    valid_year, valid_month, valid_state, valid_source = _validate_pipeline_args(
        year=year,
        month=month,
        state_code=state_code,
        source=source,
        skip_extract=skip_extract,
        skip_load=skip_load,
        init_schema=init_schema,
        overwrite_raw=overwrite_raw,
    )

    if input_path is not None and not skip_extract:
        raise ValueError(
            "input_path só pode ser usado com skip_extract=True para evitar ambiguidade "
            "entre arquivo local explícito e download CKAN."
        )

    source_url: str | None = None
    collected_at_utc: str | None = None

    if skip_extract:
        if input_path is not None:
            raw_csv_path = Path(input_path)
        else:
            raw_csv_path = build_raw_filepath(
                valid_source,
                valid_year,
                valid_month,
                "csv",
                output_dir=raw_dir,
            )
        if not raw_csv_path.exists() or not raw_csv_path.is_file():
            raise FileNotFoundError(
                f"CSV bruto não encontrado para skip_extract=True: {raw_csv_path}."
            )
        extracted = False
    else:
        download_result = download_monthly_resource(
            source=valid_source,
            year=valid_year,
            month=valid_month,
            file_format="csv",
            output_dir=raw_dir,
            overwrite=overwrite_raw,
        )
        raw_csv_path = download_result["destination_path"]
        source_url = download_result["url"]
        extracted = True

    metadata_path = build_metadata_filepath(raw_csv_path)
    collection_metadata = read_collection_metadata(metadata_path)
    if collection_metadata is not None:
        source_url = source_url or collection_metadata.get("source_url")
        collected_at_utc = collection_metadata.get("collected_at_utc")

    final_df, parquet_path, report_path, consolidated_report = transform_monthly_dataset(
        raw_csv_path,
        year=valid_year,
        month=valid_month,
        state_code=valid_state,
        output_dir=processed_dir,
        on_duplicate=on_duplicate,
        strict_quality=True,
    )

    load_report: DatabaseLoadReport | None = None
    loaded = False

    if not skip_load:
        if init_schema:
            apply_schema(
                database_url=database_url,
                schema_path=schema_path,
                connect_timeout=connect_timeout,
                connect_fn=connect_fn,
            )

        energy_report = consolidated_report.get("energy_report")
        gnra_status = (
            energy_report.get("gnra_unit_status", GNRA_UNIT_STATUS_DEFAULT)
            if isinstance(energy_report, dict)
            else GNRA_UNIT_STATUS_DEFAULT
        )

        load_report = load_dataframe_to_postgres(
            final_df,
            source=valid_source,
            state_code=valid_state,
            year=valid_year,
            month=valid_month,
            raw_file_name=raw_csv_path.name,
            raw_file_sha256=str(consolidated_report["source_sha256"]),
            parquet_file_name=parquet_path.name,
            parquet_file_sha256=consolidated_report.get("output_parquet_sha256"),
            source_url=source_url,
            collected_at_utc=collected_at_utc,
            processed_at_utc=str(consolidated_report["processed_at_utc"]),
            input_rows=int(consolidated_report["input_rows"]),
            output_rows=int(consolidated_report["output_rows"]),
            excluded_by_state_rows=int(
                consolidated_report.get("excluded_by_state_rows", 0)
            ),
            dropped_duplicate_rows=int(
                consolidated_report.get("dropped_exact_duplicate_rows", 0)
            ),
            gnra_unit_status=str(gnra_status),
            metodologia_versao=METHODOLOGY_VERSION,
            quality_report=consolidated_report,
            database_url=database_url,
            connect_timeout=connect_timeout,
            connect_fn=connect_fn,
        )
        loaded = True

    return {
        "source": valid_source,
        "state_code": valid_state,
        "year": valid_year,
        "month": valid_month,
        "raw_csv_path": raw_csv_path.as_posix(),
        "parquet_path": parquet_path.as_posix(),
        "quality_report_path": report_path.as_posix(),
        "extracted": extracted,
        "loaded": loaded,
        "input_rows": int(consolidated_report["input_rows"]),
        "output_rows": int(consolidated_report["output_rows"]),
        "load_report": load_report,
    }


def build_argument_parser() -> argparse.ArgumentParser:
    """Constrói o parser CLI para ``python -m src.pipeline``."""
    parser = argparse.ArgumentParser(
        prog="python -m src.pipeline",
        description=(
            "Executa o pipeline ETL mensal completo (extração CKAN, transformação/"
            "validação Parquet e carga idempotente no PostgreSQL)."
        ),
    )
    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Ano de referência com 4 dígitos (ex.: 2025).",
    )
    parser.add_argument(
        "--month",
        type=int,
        required=True,
        help="Mês de referência entre 1 e 12 (ex.: 1).",
    )
    parser.add_argument(
        "--state",
        type=str,
        default=DEFAULT_MVP_STATE,
        help=f"Sigla da UF com 2 letras (padrão: {DEFAULT_MVP_STATE}).",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="eolica",
        help="Fonte de dados configurada em src.extract (padrão: eolica).",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=DEFAULT_RAW_DIR,
        help=f"Diretório de CSVs brutos (padrão: {DEFAULT_RAW_DIR.as_posix()}).",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=DEFAULT_PROCESSED_DIR,
        help=f"Diretório de Parquets tratados (padrão: {DEFAULT_PROCESSED_DIR.as_posix()}).",
    )
    parser.add_argument(
        "--input",
        dest="input_path",
        type=Path,
        default=None,
        help="Caminho explícito para CSV bruto local (usar junto com --skip-extract).",
    )
    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="Pula a etapa CKAN e transforma/carrega o CSV bruto já presente em disco.",
    )
    parser.add_argument(
        "--skip-load",
        action="store_true",
        help="Executa extração e transformação, sem gravar no PostgreSQL.",
    )
    parser.add_argument(
        "--init-schema",
        action="store_true",
        help="Aplica sql/schema.sql de forma idempotente antes da carga no PostgreSQL.",
    )
    parser.add_argument(
        "--overwrite-raw",
        action="store_true",
        help="Permite atualizar o CSV bruto local caso o ONS tenha publicado revisão.",
    )
    parser.add_argument(
        "--on-duplicate",
        choices=("raise", "report", "drop_exact_only"),
        default="raise",
        help="Política para duplicidades na chave (ons_id, instante).",
    )
    parser.add_argument(
        "--connect-timeout",
        type=int,
        default=DEFAULT_CONNECT_TIMEOUT_SECONDS,
        help=f"Timeout de conexão PostgreSQL em segundos (padrão: {DEFAULT_CONNECT_TIMEOUT_SECONDS}).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Ponto de entrada CLI para execução mensal do pipeline ETL."""
    parser = build_argument_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1

    try:
        report = run_monthly_pipeline(
            year=args.year,
            month=args.month,
            state_code=args.state,
            source=args.source,
            raw_dir=args.raw_dir,
            processed_dir=args.processed_dir,
            input_path=args.input_path,
            skip_extract=args.skip_extract,
            skip_load=args.skip_load,
            init_schema=args.init_schema,
            overwrite_raw=args.overwrite_raw,
            on_duplicate=args.on_duplicate,
            connect_timeout=args.connect_timeout,
        )
    except (
        ValueError,
        TypeError,
        FileNotFoundError,
        OSError,
        ResourceDiscoveryError,
        ResourceDownloadError,
        DatabaseConfigError,
        DatabaseSchemaError,
        DatabaseConnectionError,
        DatabaseLoadError,
    ) as exc:
        print(f"Erro no pipeline: {exc}", file=sys.stderr)
        return 1

    load_summary = (
        f"execucao_id={report['load_report']['execucao_id']} "
        f"dim={report['load_report']['dim_rows_upserted']} "
        f"fact={report['load_report']['fact_rows_upserted']}"
        if report["load_report"] is not None
        else "carga=ignorada (--skip-load)"
    )
    print(
        f"[ok] {report['source']} {report['state_code']} {report['year']:04d}-{report['month']:02d}: "
        f"{report['input_rows']} -> {report['output_rows']} linhas | "
        f"parquet={report['parquet_path']} | {load_summary}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
