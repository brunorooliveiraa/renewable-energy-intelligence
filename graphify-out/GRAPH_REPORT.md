# Graph Report - Projeto_eolica  (2026-11-23)

## Corpus Check
- 31 files · ~49,354 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: (none) 7, .example 1, .css 1)

## Summary
- 699 nodes · 1804 edges · 41 communities (30 shown, 11 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 261 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ea2aac69`
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
- Normalização de Metadados CKAN
- download_period_range
- Path
- Persistência PostgreSQL Neon (Fase 5)
- Any
- transform_monthly_dataset
- extract.py
- Orquestração do Pipeline (Fase 5)
- filter_by_state
- Comunidade 16
- Comunidade 17
- SourceSchemaError
- _validate_collection_metadata_payload
- FakeLoadCursor
- Comunidade 21
- run_monthly_pipeline
- Comunidade 23
- Comunidade 25
- index.py
- database.py
- pandas
- pytest
- _make_phase3_synthetic_df
- build_argument_parser
- Dependências Python do Projeto (requirements.txt)
- DatabaseConfigError
- generate_basic_phase4_charts
- argparse
- DatabaseSchemaError
- DatabaseLoadReport
- DownloadResult
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
- `test_builds_predictable_raw_filename_for_source_and_dataset()` --calls--> `build_raw_filename()`  [INFERRED]
  tests/test_extract.py → src/extract.py
- `test_rejects_years_with_fewer_than_four_digits_in_filename()` --calls--> `build_raw_filename()`  [INFERRED]
  tests/test_extract.py → src/extract.py
- `test_iter_year_months_handles_single_month_range_and_year_rollover()` --calls--> `iter_year_months()`  [INFERRED]
  tests/test_extract.py → src/extract.py
- `test_iter_year_months_rejects_inverted_range()` --calls--> `iter_year_months()`  [INFERRED]
  tests/test_extract.py → src/extract.py
- `generate_basic_phase4_charts()` --generates--> `Grafico SVG: Geracao Verificada Diaria (MWh)`  [EXTRACTED]
  src/metrics.py → docs/imagens/fase4/geracao_diaria_mwh.svg

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Governança de Qualidade e Metodologia do Repositório** — agents_integridade_metodologica, agents_governanca_graphify, agents_contrato_frontend_sem_acesso_direto_sqlite, agents_protocolo_implementacao_autorevisao [EXTRACTED 1.00]
- **Definição Metodológica e Escopo do MVP** — plano_escopo_mvp, plano_fontes_oficiais_ons_aneel, plano_metricas_gnra_mvp, plano_riscos_decisoes [INFERRED 0.95]
- **Arquitetura e Execução do Pipeline de Dados** — plano_arquitetura_pipeline, plano_modelo_dados_sqlite, plano_contratos_execucao_cli, plano_roadmap_fases [INFERRED 0.95]

## Communities (41 total, 11 thin omitted)

### Community 0 - "Testes Sintéticos CKAN, Download e CLI"
Cohesion: 0.06
Nodes (59): AmbiguousResourceError, build_metadata_filepath(), download_resource_file(), read_collection_metadata(), ResourceDiscoveryError, ResourceDownloadError, ResourceNotFoundError, ResourceRevisionConflictError (+51 more)

### Community 1 - "test_database.py"
Cohesion: 0.12
Nodes (12): apply_schema(), check_database_connection(), DatabaseConnectionError, main(), mask_postgres_url(), _sanitize_postgres_error_message(), _validate_connect_timeout(), test_apply_schema_is_idempotent_and_masks_errors() (+4 more)

### Community 2 - "metrics.py"
Cohesion: 0.13
Nodes (10): CoverageSummary, GnraReconciliationReport, identify_peak_restriction_periods(), IntervalCountsSummary, _pct(), PeakRestrictionsSummary, ReasonsAndOriginsSummary, summarize_coverage() (+2 more)

### Community 3 - "Validação, Metadados e Hash SHA-256"
Cohesion: 0.11
Nodes (17): check_and_resolve_key_duplicates(), DataQualityError, DuplicateKeyError, DuplicateKeyReport, QualityCheckReport, run_quality_checks(), test_check_duplicates_always_rejects_conflicting_keys_even_in_drop_exact_only(), test_check_duplicates_handles_exact_duplicates_by_policy() (+9 more)

### Community 4 - "transform.py"
Cohesion: 0.09
Nodes (15): ColumnNumericReport, EligibilityReport, EnergyCalculationReport, GranularityReport, IdentifierNormalizationError, IdentifierReport, inspect_source_schema(), preserve_operational_identifiers() (+7 more)

### Community 5 - "Exceções de Extração e Revisão"
Cohesion: 0.15
Nodes (19): parse_instante_column(), TimestampConversionError, validate_granularity_and_add_duration(), _sample_standardized_dataframe(), test_add_eligibility_flags_classifies_all_indicators_without_dropping_rows(), test_add_eligibility_flags_rejects_untyped_or_duplicate_columns(), test_add_energy_and_preserve_gnra_computes_50mwh_for_100mwmed_half_hour(), test_convert_mwmed_columns_preserves_precision_and_nulls_without_rounding() (+11 more)

### Community 6 - "Transformação, Tipagem e Filtros CSV ONS"
Cohesion: 0.09
Nodes (25): Regras para Agentes (AGENTS.md), Achados Explorat?rios do MVP ? Cear? (Janeiro/2025), 1. Por que separar o ETL da API serverless, 2. Topologia do sistema, 3. Contrato de rotas planejado para a API (`api/index.py`), 4. Variáveis de ambiente e segurança, 5. Como rodar localmente antes do deploy, Arquitetura de Servidor Gratuito — Vercel + FastAPI + Neon PostgreSQL (+17 more)

### Community 7 - "Normalização de Metadados CKAN"
Cohesion: 0.13
Nodes (7): FakeConnection, FakeCursor, failing_connect(), fake_connect(), test_check_database_connection_handles_success_and_db_errors(), empty_connect(), ok_connect()

### Community 8 - "download_period_range"
Cohesion: 0.14
Nodes (7): build_argument_parser(), download_period_range(), _fetch_ckan_resources(), main(), _validate_max_attempts(), _validate_overwrite(), _validate_timeout()

### Community 9 - "Path"
Cohesion: 0.23
Nodes (6): build_archived_revision_filepath(), CollectionMetadata, _commit_staged_raw_and_metadata(), _download_discovered_monthly_resource(), _verify_existing_file_matches_remote_revision(), write_collection_metadata()

### Community 10 - "Persistência PostgreSQL Neon (Fase 5)"
Cohesion: 0.16
Nodes (9): build_raw_filename(), discover_resource(), download_monthly_resource(), iter_year_months(), resolve_dataset_id(), _validate_dataset(), _validate_format(), _validate_month() (+1 more)

### Community 11 - "Any"
Cohesion: 0.15
Nodes (8): _expected_content_length(), _extract_resources(), _iter_response_chunks(), _matches_resource(), _normalize_resource_metadata(), ResourceMetadata, _select_unique_resource(), _stream_response_to_destination()

### Community 12 - "transform_monthly_dataset"
Cohesion: 0.13
Nodes (11): build_processed_filepath(), build_quality_report_filepath(), transform_monthly_dataset(), TransformationQualityReport, _validate_raw_csv_path(), write_processed_parquet(), write_quality_report(), test_atomic_writers_clean_part_files_on_io_failure() (+3 more)

### Community 13 - "extract.py"
Cohesion: 0.28
Nodes (3): compute_file_sha256(), _validate_chunk_size(), _validate_destination()

### Community 14 - "Orquestração do Pipeline (Fase 5)"
Cohesion: 0.29
Nodes (13): RawCsvReadError, read_raw_ons_csv(), test_accepts_quoted_semicolon_inside_text_field(), test_accepts_utf8_with_bom_without_changing_first_column(), test_reads_confirmed_csv_format_without_early_type_conversion(), test_rejects_changed_or_duplicated_source_schema(), test_rejects_comma_in_numeric_source_field(), test_rejects_missing_empty_and_non_utf8_files() (+5 more)

### Community 15 - "filter_by_state"
Cohesion: 0.29
Nodes (3): EmptyFilterResultError, filter_by_state(), GranularityValidationError

### Community 16 - "Comunidade 16"
Cohesion: 0.27
Nodes (14): dim_empreendimentos, etl_execucoes, fact_restricoes, idx_dim_empreendimentos_estado, idx_etl_execucoes_periodo, idx_etl_execucoes_status, idx_fact_restricoes_estado_instante, idx_fact_restricoes_estado_razao_origem (+6 more)

### Community 17 - "Comunidade 17"
Cohesion: 0.15
Nodes (3): test_api_health_reports_database_configuration_without_exposing_secrets(), test_vercel_config_and_runtime_requirements_stay_lightweight(), test_ons_dictionary_json_has_24_unique_fields()

### Community 18 - "SourceSchemaError"
Cohesion: 0.14
Nodes (10): add_eligibility_flags(), add_energy_and_preserve_gnra(), convert_mwmed_columns(), _convert_single_numeric_series(), NumericConversionError, SourceSchemaError, standardize_column_names(), test_add_energy_rejects_non_positive_duration() (+2 more)

### Community 19 - "_validate_collection_metadata_payload"
Cohesion: 0.20
Nodes (6): RevisionHistoryEntry, _validate_collection_metadata_payload(), _validate_download_url(), _validate_revision_history_entry(), _validate_sha256_hex(), _validate_utc_iso_timestamp()

### Community 21 - "Comunidade 21"
Cohesion: 0.60
Nodes (4): Descoberta de Recurso CKAN (discover_resource), Download Seguro com Retentativas e Integridade (download_resource_file), Faixa de Meses, Recursos Ausentes e CLI (python -m src.extract), Investigação da API CKAN do ONS

### Community 22 - "run_monthly_pipeline"
Cohesion: 0.12
Nodes (10): DatabaseLoadError, main(), PipelineRunReport, run_monthly_pipeline(), _validate_pipeline_args(), test_pipeline_cli_succeeds_with_skip_load_and_fails_cleanly_on_missing_file(), test_run_monthly_pipeline_rejects_invalid_arguments_and_missing_csv(), test_run_monthly_pipeline_skip_load_does_not_connect_to_database() (+2 more)

### Community 23 - "Comunidade 23"
Cohesion: 0.50
Nodes (3): rewrites, $schema, version

### Community 28 - "database.py"
Cohesion: 0.21
Nodes (12): _is_missing_value(), load_dataframe_to_postgres(), load_processed_parquet(), _month_period_bounds(), _prepare_load_rows(), _to_optional_float(), _to_optional_str(), _to_required_bool() (+4 more)

### Community 29 - "pandas"
Cohesion: 0.16
Nodes (9): build_enterprise_ranking(), build_generation_series(), _sum_preserving_na(), summarize_reasons_and_origins(), _aggregate_dimension(), test_build_enterprise_ranking_deduplicates_ons_id_and_classifies_conjuntos(), test_build_generation_series_sums_mwh_and_returns_na_for_zero_eligible_day(), test_phase4_metrics_on_real_january_ce_parquet() (+1 more)

### Community 30 - "pytest"
Cohesion: 0.15
Nodes (10): FakeLoadConnection, _synthetic_processed_df(), test_dim_empreendimentos_does_not_regress_attributes_on_out_of_order_historical_load(), test_load_dataframe_is_idempotent_and_removes_obsolete_rows_on_ons_revision(), _run_load(), test_load_dataframe_marks_etl_failed_and_hides_password_on_db_error(), test_load_dataframe_reports_secondary_error_when_mark_failed_also_fails(), test_load_dataframe_to_postgres_preserves_nulls_and_runs_idempotent_upserts() (+2 more)

### Community 31 - "_make_phase3_synthetic_df"
Cohesion: 0.20
Nodes (9): reconcile_gnra_values(), summarize_interval_counts(), _make_phase3_synthetic_df(), test_generate_basic_phase4_charts_creates_valid_svg_files(), test_generate_basic_phase4_charts_distinguishes_missing_zero_positive_and_negative(), test_metrics_reject_invalid_granularity_tolerance_and_schema(), test_reconcile_gnra_exposes_negative_diff_and_divergences_without_summing_mwh(), test_summarize_coverage_handles_reference_gaps_and_empty_dataframe() (+1 more)

### Community 34 - "DatabaseConfigError"
Cohesion: 0.24
Nodes (7): DatabaseConfigError, load_dotenv_file(), resolve_database_url(), validate_postgres_url(), test_load_dotenv_file_parses_values_and_rejects_malformed_lines(), test_resolve_database_url_respects_direct_vs_pooled_precedence(), test_validate_postgres_url_rejects_invalid_types_and_formats()

### Community 35 - "generate_basic_phase4_charts"
Cohesion: 0.22
Nodes (5): Grafico SVG: Geracao Verificada Diaria (MWh), Grafico SVG: Distribuicao Horaria das Restricoes, Grafico SVG: Intervalos Restritos por Razao Oficial, generate_basic_phase4_charts(), _svg_bar_chart()

### Community 37 - "DatabaseSchemaError"
Cohesion: 0.33
Nodes (3): DatabaseSchemaError, load_schema_sql(), test_load_schema_sql_validates_file_and_methodological_invariants()

## Knowledge Gaps
- **8 isolated node(s):** `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Achados Explorat?rios do MVP ? Cear? (Janeiro/2025)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS`, `Grafico SVG: Geracao Verificada Diaria (MWh)`, `Grafico SVG: Distribuicao Horaria das Restricoes` (+3 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 253 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `transform_monthly_dataset()` connect `transform_monthly_dataset` to `build_argument_parser`, `Validação, Metadados e Hash SHA-256`, `transform.py`, `Exceções de Extração e Revisão`, `extract.py`, `Orquestração do Pipeline (Fase 5)`, `filter_by_state`, `SourceSchemaError`, `run_monthly_pipeline`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **What connects `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Achados Explorat?rios do MVP ? Cear? (Janeiro/2025)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS` to the rest of the system?**
  _8 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Testes Sintéticos CKAN, Download e CLI` be split into smaller, more focused modules?**
  _Cohesion score 0.05785819482432148 - nodes in this community are weakly interconnected._
- **Why does `FakeLoadCursor` connect `FakeLoadCursor` to `test_database.py`, `run_monthly_pipeline`, `pytest`, `Normalização de Metadados CKAN`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Should `test_database.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1225071225071225 - nodes in this community are weakly interconnected._
- **Why does `run_monthly_pipeline()` connect `run_monthly_pipeline` to `Testes Sintéticos CKAN, Download e CLI`, `test_database.py`, `DatabaseLoadReport`, `build_raw_filepath`, `Persistência PostgreSQL Neon (Fase 5)`, `transform_monthly_dataset`, `database.py`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Should `metrics.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13043478260869565 - nodes in this community are weakly interconnected._