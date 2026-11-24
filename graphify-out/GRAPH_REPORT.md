# Graph Report - Projeto_eolica  (2026-11-23)

## Corpus Check
- 30 files · ~43,095 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: (none) 7, .example 1, .css 1)

## Summary
- 616 nodes · 1544 edges · 29 communities (23 shown, 6 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 250 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c62fe4f5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Testes Sintéticos CKAN, Download e CLI
- Documentação, Metodologia e Arquitetura Vercel/Neon
- Testes de Estrutura, API e Referências
- Validação, Metadados e Hash SHA-256
- Descoberta, Faixa de Meses e CLI CKAN
- Exceções de Extração e Revisão
- Transformação, Tipagem e Filtros CSV ONS
- Normalização de Metadados CKAN
- discover_resource
- ResourceDownloadError
- Persistência PostgreSQL Neon (Fase 5)
- Any
- Pacote Principal src
- extract.py
- Orquestração do Pipeline (Fase 5)
- Esquema SQL PostgreSQL
- Comunidade 16
- Comunidade 17
- SourceSchemaError
- Comunidade 19
- _download_discovered_monthly_resource
- Comunidade 21
- build_archived_revision_filepath
- Comunidade 23
- Comunidade 25
- Dependências Python do Projeto (requirements.txt)

## God Nodes (most connected - your core abstractions)
1. `FakeResponse` - 32 edges
2. `FakeDownloadResponse` - 31 edges
3. `download_period_range()` - 26 edges
4. `download_resource_file()` - 25 edges
5. `download_monthly_resource()` - 24 edges
6. `transform_monthly_dataset()` - 24 edges
7. `SourceSchemaError` - 23 edges
8. `parse_instante_column()` - 23 edges
9. `ckan_payload()` - 22 edges
10. `ResourceDownloadError` - 21 edges

## Surprising Connections (you probably didn't know these)
- `fail_metadata_write()` --calls--> `ResourceDownloadError`  [INFERRED]
  tests/test_extract.py → src/extract.py
- `test_builds_predictable_raw_filename_for_source_and_dataset()` --calls--> `build_raw_filename()`  [INFERRED]
  tests/test_extract.py → src/extract.py
- `test_rejects_years_with_fewer_than_four_digits_in_filename()` --calls--> `build_raw_filename()`  [INFERRED]
  tests/test_extract.py → src/extract.py
- `generate_basic_phase4_charts()` --generates--> `Grafico SVG: Geracao Verificada Diaria (MWh)`  [EXTRACTED]
  src/metrics.py → docs/imagens/fase4/geracao_diaria_mwh.svg
- `generate_basic_phase4_charts()` --generates--> `Grafico SVG: Distribuicao Horaria das Restricoes`  [EXTRACTED]
  src/metrics.py → docs/imagens/fase4/restricoes_por_hora.svg

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Governança de Qualidade e Metodologia do Repositório** — agents_integridade_metodologica, agents_governanca_graphify, agents_contrato_frontend_sem_acesso_direto_sqlite, agents_protocolo_implementacao_autorevisao [EXTRACTED 1.00]
- **Definição Metodológica e Escopo do MVP** — plano_escopo_mvp, plano_fontes_oficiais_ons_aneel, plano_metricas_gnra_mvp, plano_riscos_decisoes [INFERRED 0.95]
- **Arquitetura e Execução do Pipeline de Dados** — plano_arquitetura_pipeline, plano_modelo_dados_sqlite, plano_contratos_execucao_cli, plano_roadmap_fases [INFERRED 0.95]

## Communities (29 total, 6 thin omitted)

### Community 0 - "Testes Sintéticos CKAN, Download e CLI"
Cohesion: 0.06
Nodes (56): build_metadata_filepath(), download_monthly_resource(), download_period_range(), download_resource_file(), resolve_dataset_id(), ResourceRevisionConflictError, _validate_chunk_size(), _validate_max_attempts() (+48 more)

### Community 1 - "Documentação, Metodologia e Arquitetura Vercel/Neon"
Cohesion: 0.05
Nodes (26): health_check(), _is_valid_postgres_url(), apply_schema(), build_argument_parser(), check_database_connection(), DatabaseConfigError, DatabaseConnectionError, DatabaseSchemaError (+18 more)

### Community 2 - "Testes de Estrutura, API e Referências"
Cohesion: 0.06
Nodes (33): Grafico SVG: Geracao Verificada Diaria (MWh), Grafico SVG: Distribuicao Horaria das Restricoes, Grafico SVG: Intervalos Restritos por Razao Oficial, build_enterprise_ranking(), build_generation_series(), CoverageSummary, generate_basic_phase4_charts(), GnraReconciliationReport (+25 more)

### Community 3 - "Validação, Metadados e Hash SHA-256"
Cohesion: 0.12
Nodes (17): check_and_resolve_key_duplicates(), DataQualityError, DuplicateKeyError, DuplicateKeyReport, QualityCheckReport, run_quality_checks(), test_check_duplicates_always_rejects_conflicting_keys_even_in_drop_exact_only(), test_check_duplicates_handles_exact_duplicates_by_policy() (+9 more)

### Community 4 - "Descoberta, Faixa de Meses e CLI CKAN"
Cohesion: 0.08
Nodes (13): EligibilityReport, EnergyCalculationReport, GranularityReport, IdentifierReport, inspect_source_schema(), RawCsvReadError, SourceSchemaReport, StateFilterReport (+5 more)

### Community 5 - "Exceções de Extração e Revisão"
Cohesion: 0.16
Nodes (14): GranularityValidationError, parse_instante_column(), TimestampConversionError, validate_granularity_and_add_duration(), _sample_standardized_dataframe(), test_add_energy_and_preserve_gnra_computes_50mwh_for_100mwmed_half_hour(), test_convert_mwmed_columns_rejects_invalid_or_non_finite_strings(), test_filter_by_state_rejects_invalid_state_code() (+6 more)

### Community 6 - "Transformação, Tipagem e Filtros CSV ONS"
Cohesion: 0.09
Nodes (25): Regras para Agentes (AGENTS.md), Achados Explorat?rios do MVP ? Cear? (Janeiro/2025), 1. Por que separar o ETL da API serverless, 2. Topologia do sistema, 3. Contrato de rotas planejado para a API (`api/index.py`), 4. Variáveis de ambiente e segurança, 5. Como rodar localmente antes do deploy, Arquitetura de Servidor Gratuito — Vercel + FastAPI + Neon PostgreSQL (+17 more)

### Community 7 - "Normalização de Metadados CKAN"
Cohesion: 0.12
Nodes (7): FakeConnection, FakeCursor, failing_connect(), fake_connect(), test_check_database_connection_handles_success_and_db_errors(), empty_connect(), ok_connect()

### Community 8 - "discover_resource"
Cohesion: 0.13
Nodes (9): build_argument_parser(), discover_resource(), _extract_resources(), _fetch_ckan_resources(), main(), ResourceDiscoveryError, ResourceNotFoundError, test_raises_clear_error_when_ckan_reports_failure() (+1 more)

### Community 9 - "ResourceDownloadError"
Cohesion: 0.17
Nodes (10): CollectionMetadata, _commit_staged_raw_and_metadata(), read_collection_metadata(), ResourceDownloadError, _validate_collection_metadata_payload(), _validate_revision_history_entry(), _validate_utc_iso_timestamp(), _verify_existing_file_matches_remote_revision() (+2 more)

### Community 10 - "Persistência PostgreSQL Neon (Fase 5)"
Cohesion: 0.18
Nodes (7): build_raw_filename(), iter_year_months(), _validate_format(), _validate_month(), _validate_year(), test_iter_year_months_handles_single_month_range_and_year_rollover(), test_iter_year_months_rejects_inverted_range()

### Community 11 - "Any"
Cohesion: 0.18
Nodes (7): _expected_content_length(), _iter_response_chunks(), _matches_resource(), _normalize_resource_metadata(), ResourceMetadata, _select_unique_resource(), _stream_response_to_destination()

### Community 12 - "Pacote Principal src"
Cohesion: 0.16
Nodes (8): build_argument_parser(), build_processed_filepath(), build_quality_report_filepath(), main(), transform_monthly_dataset(), _validate_raw_csv_path(), test_build_processed_filepath_uses_relative_default_dir(), test_public_transform_functions_raise_type_error_for_invalid_argument_types()

### Community 13 - "extract.py"
Cohesion: 0.15
Nodes (6): AmbiguousResourceError, build_raw_filepath(), _validate_dataset(), _validate_destination(), _validate_download_url(), _validate_output_dir()

### Community 14 - "Orquestração do Pipeline (Fase 5)"
Cohesion: 0.29
Nodes (13): read_raw_ons_csv(), test_accepts_quoted_semicolon_inside_text_field(), test_accepts_utf8_with_bom_without_changing_first_column(), test_reads_confirmed_csv_format_without_early_type_conversion(), test_rejects_changed_or_duplicated_source_schema(), test_rejects_comma_in_numeric_source_field(), test_rejects_missing_empty_and_non_utf8_files(), test_rejects_rows_with_wrong_field_count() (+5 more)

### Community 15 - "Esquema SQL PostgreSQL"
Cohesion: 0.15
Nodes (10): EmptyFilterResultError, filter_by_state(), IdentifierNormalizationError, preserve_operational_identifiers(), standardize_column_names(), test_filter_by_state_handles_empty_match_explicitly(), test_filter_by_state_selects_ce_and_reports_excluded_and_nulls(), test_preserve_operational_identifiers_keeps_string_dtype_and_dash_literal() (+2 more)

### Community 16 - "Comunidade 16"
Cohesion: 0.27
Nodes (14): dim_empreendimentos, etl_execucoes, fact_restricoes, idx_dim_empreendimentos_estado, idx_etl_execucoes_periodo, idx_etl_execucoes_status, idx_fact_restricoes_estado_instante, idx_fact_restricoes_estado_razao_origem (+6 more)

### Community 17 - "Comunidade 17"
Cohesion: 0.21
Nodes (3): test_api_health_reports_database_configuration_without_exposing_secrets(), test_vercel_config_and_runtime_requirements_stay_lightweight(), test_ons_dictionary_json_has_24_unique_fields()

### Community 18 - "SourceSchemaError"
Cohesion: 0.14
Nodes (12): add_eligibility_flags(), add_energy_and_preserve_gnra(), ColumnNumericReport, convert_mwmed_columns(), _convert_single_numeric_series(), NumericConversionError, SourceSchemaError, test_add_eligibility_flags_classifies_all_indicators_without_dropping_rows() (+4 more)

### Community 19 - "Comunidade 19"
Cohesion: 0.29
Nodes (3): DownloadResult, MonthlyExtractionReport, RevisionHistoryEntry

### Community 20 - "_download_discovered_monthly_resource"
Cohesion: 0.17
Nodes (5): compute_file_sha256(), _download_discovered_monthly_resource(), write_processed_parquet(), write_quality_report(), test_atomic_writers_clean_part_files_on_io_failure()

### Community 21 - "Comunidade 21"
Cohesion: 0.60
Nodes (4): Descoberta de Recurso CKAN (discover_resource), Download Seguro com Retentativas e Integridade (download_resource_file), Faixa de Meses, Recursos Ausentes e CLI (python -m src.extract), Investigação da API CKAN do ONS

### Community 23 - "Comunidade 23"
Cohesion: 0.50
Nodes (3): rewrites, $schema, version

## Knowledge Gaps
- **8 isolated node(s):** `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Achados Explorat?rios do MVP ? Cear? (Janeiro/2025)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS`, `Dependências Python do Projeto (requirements.txt)`, `Chave Operacional Candidata (id_ons + din_instante)` (+3 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 225 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `FakeCursor` connect `Normalização de Metadados CKAN` to `Documentação, Metodologia e Arquitetura Vercel/Neon`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `download_period_range()` (e.g. with `test_download_period_range_does_not_silence_revision_conflict_when_allow_missing_is_true()` and `test_download_period_range_fetches_catalog_once_and_downloads_multiple_months()`) actually correct?**
  _`download_period_range()` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Achados Explorat?rios do MVP ? Cear? (Janeiro/2025)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS` to the rest of the system?**
  _8 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Testes Sintéticos CKAN, Download e CLI` be split into smaller, more focused modules?**
  _Cohesion score 0.0586340206185567 - nodes in this community are weakly interconnected._
- **Why does `FakeResponse` connect `Testes Sintéticos CKAN, Download e CLI` to `discover_resource`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Should `Documentação, Metodologia e Arquitetura Vercel/Neon` be split into smaller, more focused modules?**
  _Cohesion score 0.052943354313217325 - nodes in this community are weakly interconnected._
- **Should `Testes de Estrutura, API e Referências` be split into smaller, more focused modules?**
  _Cohesion score 0.06351236146632566 - nodes in this community are weakly interconnected._