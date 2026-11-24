# Graph Report - Projeto_eolica  (2026-11-23)

## Corpus Check
- 32 files · ~53,938 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: (none) 7, .example 1, .css 1)

## Summary
- 779 nodes · 2011 edges · 44 communities (35 shown, 9 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 273 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c229eaf6`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Testes Sintéticos CKAN, Download e CLI
- test_database.py
- metrics.py
- Validação, Metadados e Hash SHA-256
- transform.py
- Exceções de Extração e Revisão
- Transformação, Tipagem e Filtros CSV ONS
- FakeCursor
- download_monthly_resource
- Path
- extract.py
- Any
- transform_monthly_dataset
- json
- Orquestração do Pipeline (Fase 5)
- filter_by_state
- Comunidade 16
- test_api.py
- SourceSchemaError
- FakeLoadCursor
- apply_schema
- Comunidade 21
- run_monthly_pipeline
- Comunidade 23
- Comunidade 25
- queries.py
- database.py
- pandas
- load_dataframe_to_postgres
- _make_phase3_synthetic_df
- build_raw_filename
- Dependências Python do Projeto (requirements.txt)
- validate_source_schema
- generate_basic_phase4_charts
- pipeline.py
- main
- DownloadResult
- preserve_operational_identifiers
- FakeLoadConnection
- build_argument_parser
- build_raw_filepath

## God Nodes (most connected - your core abstractions)
1. `FakeResponse` - 32 edges
2. `FakeDownloadResponse` - 31 edges
3. `load_dataframe_to_postgres()` - 26 edges
4. `download_monthly_resource()` - 26 edges
5. `download_period_range()` - 26 edges
6. `transform_monthly_dataset()` - 26 edges
7. `download_resource_file()` - 25 edges
8. `ResourceDownloadError` - 23 edges
9. `SourceSchemaError` - 23 edges
10. `parse_instante_column()` - 23 edges

## Surprising Connections (you probably didn't know these)
- `generate_basic_phase4_charts()` --generates--> `Grafico SVG: Geracao Verificada Diaria (MWh)`  [EXTRACTED]
  src/metrics.py → docs/imagens/fase4/geracao_diaria_mwh.svg
- `generate_basic_phase4_charts()` --generates--> `Grafico SVG: Distribuicao Horaria das Restricoes`  [EXTRACTED]
  src/metrics.py → docs/imagens/fase4/restricoes_por_hora.svg
- `generate_basic_phase4_charts()` --generates--> `Grafico SVG: Intervalos Restritos por Razao Oficial`  [EXTRACTED]
  src/metrics.py → docs/imagens/fase4/restricoes_por_razao.svg
- `test_check_database_connection_handles_success_and_db_errors()` --uses--> `DatabaseConnectionError`  [INFERRED]
  tests/test_database.py → src/database.py
- `test_raises_clear_error_when_ckan_reports_failure()` --uses--> `ResourceDiscoveryError`  [INFERRED]
  tests/test_extract.py → src/extract.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Governança de Qualidade e Metodologia do Repositório** — agents_integridade_metodologica, agents_governanca_graphify, agents_contrato_frontend_sem_acesso_direto_sqlite, agents_protocolo_implementacao_autorevisao [EXTRACTED 1.00]
- **Definição Metodológica e Escopo do MVP** — plano_escopo_mvp, plano_fontes_oficiais_ons_aneel, plano_metricas_gnra_mvp, plano_riscos_decisoes [INFERRED 0.95]
- **Arquitetura e Execução do Pipeline de Dados** — plano_arquitetura_pipeline, plano_modelo_dados_sqlite, plano_contratos_execucao_cli, plano_roadmap_fases [INFERRED 0.95]

## Communities (44 total, 9 thin omitted)

### Community 0 - "Testes Sintéticos CKAN, Download e CLI"
Cohesion: 0.07
Nodes (52): download_resource_file(), _expected_content_length(), _iter_response_chunks(), ResourceDownloadError, ResourceRevisionConflictError, _stream_response_to_destination(), ckan_payload(), FakeCombinedSession (+44 more)

### Community 1 - "test_database.py"
Cohesion: 0.15
Nodes (13): DatabaseConfigError, DatabaseSchemaError, load_dotenv_file(), load_schema_sql(), mask_postgres_url(), resolve_database_url(), validate_postgres_url(), test_load_dotenv_file_parses_values_and_rejects_malformed_lines() (+5 more)

### Community 2 - "metrics.py"
Cohesion: 0.13
Nodes (10): CoverageSummary, GnraReconciliationReport, identify_peak_restriction_periods(), IntervalCountsSummary, _pct(), PeakRestrictionsSummary, ReasonsAndOriginsSummary, summarize_coverage() (+2 more)

### Community 3 - "Validação, Metadados e Hash SHA-256"
Cohesion: 0.12
Nodes (16): check_and_resolve_key_duplicates(), DataQualityError, DuplicateKeyError, DuplicateKeyReport, QualityCheckReport, run_quality_checks(), test_check_duplicates_always_rejects_conflicting_keys_even_in_drop_exact_only(), test_check_duplicates_handles_exact_duplicates_by_policy() (+8 more)

### Community 4 - "transform.py"
Cohesion: 0.11
Nodes (11): add_energy_and_preserve_gnra(), ColumnNumericReport, _convert_single_numeric_series(), EligibilityReport, EnergyCalculationReport, GranularityReport, IdentifierReport, NumericConversionError (+3 more)

### Community 5 - "Exceções de Extração e Revisão"
Cohesion: 0.15
Nodes (15): GranularityValidationError, parse_instante_column(), TimestampConversionError, validate_granularity_and_add_duration(), _sample_standardized_dataframe(), test_add_energy_and_preserve_gnra_computes_50mwh_for_100mwmed_half_hour(), test_convert_mwmed_columns_preserves_precision_and_nulls_without_rounding(), test_convert_mwmed_columns_rejects_invalid_or_non_finite_strings() (+7 more)

### Community 6 - "Transformação, Tipagem e Filtros CSV ONS"
Cohesion: 0.09
Nodes (25): Regras para Agentes (AGENTS.md), Achados Explorat?rios do MVP ? Cear? (Janeiro/2025), 1. Por que separar o ETL da API serverless, 2. Topologia do sistema, 3. Contrato de rotas planejado para a API (`api/index.py`), 4. Variáveis de ambiente e segurança, 5. Como rodar localmente antes do deploy, Arquitetura de Servidor Gratuito — Vercel + FastAPI + Neon PostgreSQL (+17 more)

### Community 7 - "FakeCursor"
Cohesion: 0.17
Nodes (7): FakeConnection, FakeCursor, failing_connect(), fake_connect(), test_check_database_connection_handles_success_and_db_errors(), empty_connect(), ok_connect()

### Community 8 - "download_monthly_resource"
Cohesion: 0.13
Nodes (11): build_metadata_filepath(), discover_resource(), download_monthly_resource(), download_period_range(), _fetch_ckan_resources(), main(), resolve_dataset_id(), _validate_dataset() (+3 more)

### Community 9 - "Path"
Cohesion: 0.19
Nodes (9): build_archived_revision_filepath(), CollectionMetadata, _commit_staged_raw_and_metadata(), _download_discovered_monthly_resource(), read_collection_metadata(), _validate_collection_metadata_payload(), _verify_existing_file_matches_remote_revision(), write_collection_metadata() (+1 more)

### Community 10 - "extract.py"
Cohesion: 0.14
Nodes (6): build_argument_parser(), compute_file_sha256(), _validate_chunk_size(), _validate_destination(), _validate_download_url(), _validate_max_attempts()

### Community 11 - "Any"
Cohesion: 0.15
Nodes (8): AmbiguousResourceError, _extract_resources(), _matches_resource(), _normalize_resource_metadata(), ResourceDiscoveryError, ResourceMetadata, ResourceNotFoundError, _select_unique_resource()

### Community 12 - "transform_monthly_dataset"
Cohesion: 0.14
Nodes (10): build_processed_filepath(), build_quality_report_filepath(), transform_monthly_dataset(), TransformationQualityReport, _validate_raw_csv_path(), write_processed_parquet(), write_quality_report(), test_atomic_writers_clean_part_files_on_io_failure() (+2 more)

### Community 13 - "json"
Cohesion: 0.18
Nodes (3): load_processed_parquet(), test_load_processed_parquet_reads_files_and_validates_missing_artifacts(), test_ons_dictionary_json_has_24_unique_fields()

### Community 14 - "Orquestração do Pipeline (Fase 5)"
Cohesion: 0.26
Nodes (14): RawCsvReadError, read_raw_ons_csv(), test_accepts_quoted_semicolon_inside_text_field(), test_accepts_utf8_with_bom_without_changing_first_column(), test_reads_confirmed_csv_format_without_early_type_conversion(), test_rejects_changed_or_duplicated_source_schema(), test_rejects_comma_in_numeric_source_field(), test_rejects_missing_empty_and_non_utf8_files() (+6 more)

### Community 15 - "filter_by_state"
Cohesion: 0.33
Nodes (4): EmptyFilterResultError, filter_by_state(), test_filter_by_state_handles_empty_match_explicitly(), test_filter_by_state_selects_ce_and_reports_excluded_and_nulls()

### Community 16 - "Comunidade 16"
Cohesion: 0.27
Nodes (14): dim_empreendimentos, etl_execucoes, fact_restricoes, idx_dim_empreendimentos_estado, idx_etl_execucoes_periodo, idx_etl_execucoes_status, idx_fact_restricoes_estado_instante, idx_fact_restricoes_estado_razao_origem (+6 more)

### Community 17 - "test_api.py"
Cohesion: 0.11
Nodes (6): FakeQueryConnection, FakeQueryCursor, _patch_fake_db(), test_endpoints_return_422_for_invalid_filters_and_503_without_leaking_secrets(), test_overview_endpoint_returns_metrics_and_handles_empty_filter_without_fake_zero(), test_timeseries_enterprises_reasons_and_quality_endpoints()

### Community 18 - "SourceSchemaError"
Cohesion: 0.20
Nodes (9): add_eligibility_flags(), convert_mwmed_columns(), SourceSchemaError, standardize_column_names(), test_quality_checks_and_key_uniqueness_on_verified_january_ce_subset(), test_add_eligibility_flags_classifies_all_indicators_without_dropping_rows(), test_add_eligibility_flags_rejects_untyped_or_duplicate_columns(), test_convert_mwmed_columns_rejects_missing_column() (+1 more)

### Community 20 - "apply_schema"
Cohesion: 0.18
Nodes (7): apply_schema(), check_database_connection(), DatabaseConnectionError, _sanitize_postgres_error_message(), _validate_connect_timeout(), test_apply_schema_is_idempotent_and_masks_errors(), test_database_errors_never_leak_password_from_psycopg_exception()

### Community 21 - "Comunidade 21"
Cohesion: 0.60
Nodes (4): Descoberta de Recurso CKAN (discover_resource), Download Seguro com Retentativas e Integridade (download_resource_file), Faixa de Meses, Recursos Ausentes e CLI (python -m src.extract), Investigação da API CKAN do ONS

### Community 22 - "run_monthly_pipeline"
Cohesion: 0.21
Nodes (7): main(), run_monthly_pipeline(), test_pipeline_cli_succeeds_with_skip_load_and_fails_cleanly_on_missing_file(), test_run_monthly_pipeline_rejects_invalid_arguments_and_missing_csv(), test_run_monthly_pipeline_skip_load_does_not_connect_to_database(), test_run_monthly_pipeline_transforms_and_loads_with_skip_extract(), _write_synthetic_raw_csv()

### Community 23 - "Comunidade 23"
Cohesion: 0.50
Nodes (3): rewrites, $schema, version

### Community 27 - "queries.py"
Cohesion: 0.07
Nodes (27): _execute_endpoint(), get_enterprises(), get_overview(), get_quality(), get_reasons(), get_timeseries(), health_check(), ApiDatabaseConfigError (+19 more)

### Community 28 - "database.py"
Cohesion: 0.22
Nodes (10): _is_missing_value(), _month_period_bounds(), _prepare_load_rows(), _to_optional_float(), _to_optional_str(), _to_required_bool(), _to_required_naive_datetime(), _to_required_positive_float() (+2 more)

### Community 29 - "pandas"
Cohesion: 0.15
Nodes (10): build_enterprise_ranking(), build_generation_series(), _sum_preserving_na(), summarize_reasons_and_origins(), _aggregate_dimension(), test_load_dataframe_to_postgres_rejects_invalid_inputs_and_edge_cases(), test_build_enterprise_ranking_deduplicates_ons_id_and_classifies_conjuntos(), test_build_generation_series_sums_mwh_and_returns_na_for_zero_eligible_day() (+2 more)

### Community 30 - "load_dataframe_to_postgres"
Cohesion: 0.23
Nodes (9): DatabaseLoadError, load_dataframe_to_postgres(), _synthetic_processed_df(), test_dim_empreendimentos_does_not_regress_attributes_on_out_of_order_historical_load(), test_load_dataframe_is_idempotent_and_removes_obsolete_rows_on_ons_revision(), _run_load(), test_load_dataframe_marks_etl_failed_and_hides_password_on_db_error(), test_load_dataframe_reports_secondary_error_when_mark_failed_also_fails() (+1 more)

### Community 31 - "_make_phase3_synthetic_df"
Cohesion: 0.18
Nodes (9): reconcile_gnra_values(), summarize_interval_counts(), _make_phase3_synthetic_df(), test_generate_basic_phase4_charts_creates_valid_svg_files(), test_generate_basic_phase4_charts_distinguishes_missing_zero_positive_and_negative(), test_metrics_reject_invalid_granularity_tolerance_and_schema(), test_reconcile_gnra_exposes_negative_diff_and_divergences_without_summing_mwh(), test_summarize_coverage_handles_reference_gaps_and_empty_dataframe() (+1 more)

### Community 32 - "build_raw_filename"
Cohesion: 0.18
Nodes (8): build_raw_filename(), iter_year_months(), _validate_month(), _validate_year(), test_builds_predictable_raw_filename_for_source_and_dataset(), test_iter_year_months_handles_single_month_range_and_year_rollover(), test_iter_year_months_rejects_inverted_range(), test_rejects_years_with_fewer_than_four_digits_in_filename()

### Community 34 - "validate_source_schema"
Cohesion: 0.22
Nodes (5): inspect_source_schema(), SourceSchemaReport, _validate_csv_structure(), validate_source_schema(), test_records_column_order_without_rejecting_a_safe_reordering()

### Community 35 - "generate_basic_phase4_charts"
Cohesion: 0.22
Nodes (5): Grafico SVG: Geracao Verificada Diaria (MWh), Grafico SVG: Distribuicao Horaria das Restricoes, Grafico SVG: Intervalos Restritos por Razao Oficial, generate_basic_phase4_charts(), _svg_bar_chart()

### Community 36 - "pipeline.py"
Cohesion: 0.12
Nodes (5): DatabaseLoadReport, SchemaApplyReport, build_argument_parser(), PipelineRunReport, _validate_pipeline_args()

### Community 37 - "main"
Cohesion: 0.25
Nodes (3): build_argument_parser(), main(), test_cli_returns_nonzero_when_database_url_is_missing()

### Community 39 - "DownloadResult"
Cohesion: 0.15
Nodes (6): DownloadResult, MonthlyExtractionReport, RevisionHistoryEntry, _validate_revision_history_entry(), _validate_sha256_hex(), _validate_utc_iso_timestamp()

### Community 40 - "preserve_operational_identifiers"
Cohesion: 0.40
Nodes (4): IdentifierNormalizationError, preserve_operational_identifiers(), test_preserve_operational_identifiers_keeps_string_dtype_and_dash_literal(), test_preserve_operational_identifiers_rejects_null_or_blank_ons_id()

## Knowledge Gaps
- **8 isolated node(s):** `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Achados Explorat?rios do MVP ? Cear? (Janeiro/2025)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS`, `Dependências Python do Projeto (requirements.txt)`, `Grafico SVG: Geracao Verificada Diaria (MWh)` (+3 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 284 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `transform_monthly_dataset()` connect `transform_monthly_dataset` to `Validação, Metadados e Hash SHA-256`, `pipeline.py`, `transform.py`, `Exceções de Extração e Revisão`, `preserve_operational_identifiers`, `build_argument_parser`, `extract.py`, `Orquestração do Pipeline (Fase 5)`, `filter_by_state`, `SourceSchemaError`, `run_monthly_pipeline`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **What connects `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Achados Explorat?rios do MVP ? Cear? (Janeiro/2025)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS` to the rest of the system?**
  _8 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Testes Sintéticos CKAN, Download e CLI` be split into smaller, more focused modules?**
  _Cohesion score 0.06609195402298851 - nodes in this community are weakly interconnected._
- **Why does `FakeLoadCursor` connect `FakeLoadCursor` to `test_database.py`, `BaseException`, `FakeLoadConnection`, `json`, `run_monthly_pipeline`, `load_dataframe_to_postgres`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Should `metrics.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13043478260869565 - nodes in this community are weakly interconnected._
- **Should `Validação, Metadados e Hash SHA-256` be split into smaller, more focused modules?**
  _Cohesion score 0.11764705882352941 - nodes in this community are weakly interconnected._
- **Should `transform.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1111111111111111 - nodes in this community are weakly interconnected._