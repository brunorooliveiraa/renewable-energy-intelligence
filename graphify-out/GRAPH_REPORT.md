# Graph Report - Projeto_eolica  (2026-11-23)

## Corpus Check
- Corpus is ~43,001 words - fits in a single context window. You may not need a graph.

## Summary
- 619 nodes · 1539 edges · 38 communities (23 shown, 15 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 250 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 25
- Community 33

## God Nodes (most connected - your core abstractions)
1. `FakeResponse` - 32 edges
2. `FakeDownloadResponse` - 31 edges
3. `download_period_range()` - 26 edges
4. `download_resource_file()` - 25 edges
5. `download_monthly_resource()` - 24 edges
6. `transform_monthly_dataset()` - 24 edges
7. `SourceSchemaError` - 23 edges
8. `parse_instante_column()` - 23 edges
9. `ResourceDownloadError` - 22 edges
10. `ckan_payload()` - 22 edges

## Surprising Connections (you probably didn't know these)
- `test_iter_year_months_handles_single_month_range_and_year_rollover()` --calls--> `iter_year_months()`  [INFERRED]
  tests/test_extract.py → src/extract.py
- `generate_basic_phase4_charts()` --generates--> `Grafico SVG: Geracao Verificada Diaria (MWh)`  [EXTRACTED]
  src/metrics.py → docs/imagens/fase4/geracao_diaria_mwh.svg
- `generate_basic_phase4_charts()` --generates--> `Grafico SVG: Distribuicao Horaria das Restricoes`  [EXTRACTED]
  src/metrics.py → docs/imagens/fase4/restricoes_por_hora.svg
- `generate_basic_phase4_charts()` --generates--> `Grafico SVG: Intervalos Restritos por Razao Oficial`  [EXTRACTED]
  src/metrics.py → docs/imagens/fase4/restricoes_por_razao.svg
- `test_check_database_connection_handles_success_and_db_errors()` --uses--> `DatabaseConnectionError`  [INFERRED]
  tests/test_database.py → src/database.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Governança de Qualidade e Metodologia do Repositório** — agents_integridade_metodologica, agents_governanca_graphify, agents_contrato_frontend_sem_acesso_direto_sqlite, agents_protocolo_implementacao_autorevisao [EXTRACTED 1.00]
- **Definição Metodológica e Escopo do MVP** — plano_escopo_mvp, plano_fontes_oficiais_ons_aneel, plano_metricas_gnra_mvp, plano_riscos_decisoes [INFERRED 0.95]
- **Arquitetura e Execução do Pipeline de Dados** — plano_arquitetura_pipeline, plano_modelo_dados_sqlite, plano_contratos_execucao_cli, plano_roadmap_fases [INFERRED 0.95]

## Communities (38 total, 15 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.07
Nodes (49): download_resource_file(), ResourceDownloadError, ResourceRevisionConflictError, ckan_payload(), FakeCombinedSession, FakeDownloadResponse, FakeDownloadSession, FakeRangeSession (+41 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (25): health_check(), _is_valid_postgres_url(), apply_schema(), build_argument_parser(), check_database_connection(), DatabaseConfigError, DatabaseConnectionError, DatabaseSchemaError (+17 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (33): Grafico SVG: Geracao Verificada Diaria (MWh), Grafico SVG: Distribuicao Horaria das Restricoes, Grafico SVG: Intervalos Restritos por Razao Oficial, build_enterprise_ranking(), build_generation_series(), CoverageSummary, generate_basic_phase4_charts(), GnraReconciliationReport (+25 more)

### Community 3 - "Community 3"
Cohesion: 0.12
Nodes (16): check_and_resolve_key_duplicates(), DataQualityError, DuplicateKeyError, DuplicateKeyReport, QualityCheckReport, run_quality_checks(), test_check_duplicates_always_rejects_conflicting_keys_even_in_drop_exact_only(), test_check_duplicates_handles_exact_duplicates_by_policy() (+8 more)

### Community 4 - "Community 4"
Cohesion: 0.09
Nodes (12): ColumnNumericReport, EligibilityReport, EnergyCalculationReport, GranularityReport, IdentifierReport, inspect_source_schema(), SourceSchemaReport, StateFilterReport (+4 more)

### Community 5 - "Community 5"
Cohesion: 0.15
Nodes (20): parse_instante_column(), TimestampConversionError, validate_granularity_and_add_duration(), _sample_standardized_dataframe(), test_add_eligibility_flags_classifies_all_indicators_without_dropping_rows(), test_add_eligibility_flags_rejects_untyped_or_duplicate_columns(), test_add_energy_and_preserve_gnra_computes_50mwh_for_100mwmed_half_hour(), test_convert_mwmed_columns_preserves_precision_and_nulls_without_rounding() (+12 more)

### Community 6 - "Community 6"
Cohesion: 0.13
Nodes (19): Regras para Agentes (AGENTS.md), Achados Explorat?rios do MVP ? Cear? (Janeiro/2025), Chave Operacional Candidata (id_ons + din_instante), Geração Não Realizada Apurada (GNRa), Reconhecimento ONS 2025-01 (Dicionário de Dados), Rotina Operacional ONS RO-AO.BR.13 (Rev. 08), Dicionário de Dados Oficial ONS - Restrição de Operação por Constrained-off de Usinas Eólicas (PDF v1.5), Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS) (+11 more)

### Community 7 - "Community 7"
Cohesion: 0.11
Nodes (7): FakeConnection, FakeCursor, failing_connect(), fake_connect(), test_check_database_connection_handles_success_and_db_errors(), empty_connect(), ok_connect()

### Community 8 - "Community 8"
Cohesion: 0.11
Nodes (11): build_argument_parser(), build_metadata_filepath(), build_raw_filepath(), download_monthly_resource(), download_period_range(), _fetch_ckan_resources(), main(), _validate_chunk_size() (+3 more)

### Community 9 - "Community 9"
Cohesion: 0.16
Nodes (11): build_archived_revision_filepath(), CollectionMetadata, _commit_staged_raw_and_metadata(), compute_file_sha256(), _download_discovered_monthly_resource(), read_collection_metadata(), _verify_existing_file_matches_remote_revision(), write_collection_metadata() (+3 more)

### Community 10 - "Community 10"
Cohesion: 0.11
Nodes (12): build_raw_filename(), discover_resource(), iter_year_months(), resolve_dataset_id(), _validate_dataset(), _validate_format(), _validate_month(), _validate_timeout() (+4 more)

### Community 11 - "Community 11"
Cohesion: 0.15
Nodes (9): AmbiguousResourceError, _extract_resources(), _matches_resource(), _normalize_resource_metadata(), ResourceDiscoveryError, ResourceMetadata, ResourceNotFoundError, _select_unique_resource() (+1 more)

### Community 12 - "Community 12"
Cohesion: 0.15
Nodes (9): build_processed_filepath(), build_quality_report_filepath(), transform_monthly_dataset(), TransformationQualityReport, _validate_raw_csv_path(), write_quality_report(), test_atomic_writers_clean_part_files_on_io_failure(), test_build_processed_filepath_uses_relative_default_dir() (+1 more)

### Community 13 - "Community 13"
Cohesion: 0.16
Nodes (8): _expected_content_length(), _iter_response_chunks(), _stream_response_to_destination(), _validate_collection_metadata_payload(), _validate_download_url(), _validate_revision_history_entry(), _validate_sha256_hex(), _validate_utc_iso_timestamp()

### Community 14 - "Community 14"
Cohesion: 0.26
Nodes (14): RawCsvReadError, read_raw_ons_csv(), test_accepts_quoted_semicolon_inside_text_field(), test_accepts_utf8_with_bom_without_changing_first_column(), test_reads_confirmed_csv_format_without_early_type_conversion(), test_rejects_changed_or_duplicated_source_schema(), test_rejects_comma_in_numeric_source_field(), test_rejects_missing_empty_and_non_utf8_files() (+6 more)

### Community 15 - "Community 15"
Cohesion: 0.21
Nodes (8): convert_mwmed_columns(), filter_by_state(), preserve_operational_identifiers(), SourceSchemaError, standardize_column_names(), test_quality_checks_and_key_uniqueness_on_verified_january_ce_subset(), test_convert_mwmed_columns_rejects_missing_column(), test_reads_verified_january_source_file()

### Community 16 - "Community 16"
Cohesion: 0.27
Nodes (14): dim_empreendimentos, etl_execucoes, fact_restricoes, idx_dim_empreendimentos_estado, idx_etl_execucoes_periodo, idx_etl_execucoes_status, idx_fact_restricoes_estado_instante, idx_fact_restricoes_estado_razao_origem (+6 more)

### Community 17 - "Community 17"
Cohesion: 0.21
Nodes (3): test_api_health_reports_database_configuration_without_exposing_secrets(), test_vercel_config_and_runtime_requirements_stay_lightweight(), test_ons_dictionary_json_has_24_unique_fields()

### Community 18 - "Community 18"
Cohesion: 0.25
Nodes (5): add_eligibility_flags(), add_energy_and_preserve_gnra(), _convert_single_numeric_series(), NumericConversionError, test_add_energy_rejects_non_positive_duration()

### Community 19 - "Community 19"
Cohesion: 0.29
Nodes (3): DownloadResult, MonthlyExtractionReport, RevisionHistoryEntry

### Community 20 - "Community 20"
Cohesion: 0.29
Nodes (3): EmptyFilterResultError, GranularityValidationError, IdentifierNormalizationError

### Community 21 - "Community 21"
Cohesion: 0.60
Nodes (4): Descoberta de Recurso CKAN (discover_resource), Download Seguro com Retentativas e Integridade (download_resource_file), Faixa de Meses, Recursos Ausentes e CLI (python -m src.extract), Investigação da API CKAN do ONS

### Community 23 - "Community 23"
Cohesion: 0.50
Nodes (3): rewrites, $schema, version

## Knowledge Gaps
- **8 isolated node(s):** `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Achados Explorat?rios do MVP ? Cear? (Janeiro/2025)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS`, `Chave Operacional Candidata (id_ons + din_instante)`, `Dependências Python do Projeto (requirements.txt)` (+3 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 229 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `FakeCursor` connect `Community 7` to `Community 1`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `download_period_range()` (e.g. with `test_download_period_range_does_not_silence_revision_conflict_when_allow_missing_is_true()` and `test_download_period_range_fetches_catalog_once_and_downloads_multiple_months()`) actually correct?**
  _`download_period_range()` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Achados Explorat?rios do MVP ? Cear? (Janeiro/2025)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS` to the rest of the system?**
  _8 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.07111372318542462 - nodes in this community are weakly interconnected._
- **Why does `FakeDownloadResponse` connect `Community 0` to `Community 13`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.05365296803652968 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.06308610400682012 - nodes in this community are weakly interconnected._