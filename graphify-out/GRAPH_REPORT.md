# Graph Report - Projeto_eolica  (2026-11-22)

## Corpus Check
- 32 files · ~33,926 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 456 nodes · 1272 edges · 26 communities (18 shown, 8 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 52 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Testes Sintéticos CKAN, Download e CLI
- Documentação, Metodologia e Arquitetura Vercel/Neon
- Testes de Estrutura, API e Referências
- Validação, Metadados e Hash SHA-256
- Descoberta, Faixa de Meses e CLI CKAN
- Exceções de Extração e Revisão
- Transformação, Tipagem e Filtros CSV ONS
- Normalização de Metadados CKAN
- Validação de Qualidade e Duplicidades (Fase 3)
- API Serverless FastAPI (Vercel)
- Persistência PostgreSQL Neon (Fase 5)
- Interface Web Frontend
- Pacote Principal src
- Métricas Analíticas (Fase 4)
- Orquestração do Pipeline (Fase 5)
- Esquema SQL PostgreSQL
- Comunidade 16
- Comunidade 17
- Comunidade 18
- Comunidade 19
- Comunidade 20
- Comunidade 24

## God Nodes (most connected - your core abstractions)
1. `FakeResponse` - 32 edges
2. `FakeDownloadResponse` - 31 edges
3. `download_period_range()` - 26 edges
4. `download_resource_file()` - 25 edges
5. `download_monthly_resource()` - 25 edges
6. `parse_instante_column()` - 23 edges
7. `ResourceDownloadError` - 22 edges
8. `SourceSchemaError` - 22 edges
9. `read_raw_ons_csv()` - 22 edges
10. `transform_monthly_dataset()` - 22 edges

## Surprising Connections (you probably didn't know these)
- `test_preserve_operational_identifiers_rejects_null_or_blank_ons_id()` --uses--> `IdentifierNormalizationError`  [INFERRED]
  tests/test_transform.py → src/transform.py
- `test_compute_file_sha256_and_corrupted_metadata_handling()` --uses--> `ResourceDownloadError`  [INFERRED]
  tests/test_extract.py → src/extract.py
- `test_run_quality_checks_accepts_pandas3_datetime64_us_and_rejects_duplicate_columns()` --uses--> `SourceSchemaError`  [INFERRED]
  tests/test_quality.py → src/transform.py
- `test_run_quality_checks_rejects_untyped_columns_and_partial_period_args()` --uses--> `SourceSchemaError`  [INFERRED]
  tests/test_quality.py → src/transform.py
- `test_rejects_changed_or_duplicated_source_schema()` --uses--> `SourceSchemaError`  [INFERRED]
  tests/test_transform.py → src/transform.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Governança de Qualidade e Metodologia do Repositório** — agents_integridade_metodologica, agents_governanca_graphify, agents_contrato_frontend_sem_acesso_direto_sqlite, agents_protocolo_implementacao_autorevisao [EXTRACTED 1.00]
- **Definição Metodológica e Escopo do MVP** — plano_escopo_mvp, plano_fontes_oficiais_ons_aneel, plano_metricas_gnra_mvp, plano_riscos_decisoes [INFERRED 0.95]
- **Arquitetura e Execução do Pipeline de Dados** — plano_arquitetura_pipeline, plano_modelo_dados_sqlite, plano_contratos_execucao_cli, plano_roadmap_fases [INFERRED 0.95]

## Communities (26 total, 8 thin omitted)

### Community 0 - "Testes Sintéticos CKAN, Download e CLI"
Cohesion: 0.07
Nodes (51): AmbiguousResourceError, main(), ResourceDiscoveryError, ResourceDownloadError, ResourceNotFoundError, ResourceRevisionConflictError, ckan_payload(), FakeCombinedSession (+43 more)

### Community 1 - "Documentação, Metodologia e Arquitetura Vercel/Neon"
Cohesion: 0.13
Nodes (25): add_energy_and_preserve_gnra(), convert_mwmed_columns(), GranularityValidationError, NumericConversionError, parse_instante_column(), SourceSchemaError, TimestampConversionError, validate_granularity_and_add_duration() (+17 more)

### Community 2 - "Testes de Estrutura, API e Referências"
Cohesion: 0.09
Nodes (14): add_eligibility_flags(), ColumnNumericReport, _convert_single_numeric_series(), EligibilityReport, EnergyCalculationReport, GranularityReport, IdentifierReport, inspect_source_schema() (+6 more)

### Community 3 - "Validação, Metadados e Hash SHA-256"
Cohesion: 0.12
Nodes (16): check_and_resolve_key_duplicates(), DataQualityError, DuplicateKeyError, DuplicateKeyReport, QualityCheckReport, run_quality_checks(), test_check_duplicates_always_rejects_conflicting_keys_even_in_drop_exact_only(), test_check_duplicates_handles_exact_duplicates_by_policy() (+8 more)

### Community 4 - "Descoberta, Faixa de Meses e CLI CKAN"
Cohesion: 0.08
Nodes (5): health_check(), _is_valid_postgres_url(), test_api_health_reports_database_configuration_without_exposing_secrets(), test_vercel_config_and_runtime_requirements_stay_lightweight(), test_ons_dictionary_json_has_24_unique_fields()

### Community 5 - "Exceções de Extração e Revisão"
Cohesion: 0.14
Nodes (12): build_generation_series(), GnraReconciliationReport, IntervalCountsSummary, reconcile_gnra_values(), summarize_interval_counts(), _validate_metrics_dataframe(), _make_phase3_synthetic_df(), test_build_generation_series_sums_mwh_and_returns_na_for_zero_eligible_day() (+4 more)

### Community 6 - "Transformação, Tipagem e Filtros CSV ONS"
Cohesion: 0.14
Nodes (18): Regras para Agentes (AGENTS.md), Chave Operacional Candidata (id_ons + din_instante), Geração Não Realizada Apurada (GNRa), Reconhecimento ONS 2025-01 (Dicionário de Dados), Rotina Operacional ONS RO-AO.BR.13 (Rev. 08), Dicionário de Dados Oficial ONS - Restrição de Operação por Constrained-off de Usinas Eólicas (PDF v1.5), Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS), Registro de Coleta e Hashes dos Dicionários Oficiais ONS (+10 more)

### Community 7 - "Normalização de Metadados CKAN"
Cohesion: 0.13
Nodes (11): build_metadata_filepath(), discover_resource(), download_monthly_resource(), download_period_range(), _fetch_ckan_resources(), resolve_dataset_id(), _select_unique_resource(), _validate_dataset() (+3 more)

### Community 8 - "Validação de Qualidade e Duplicidades (Fase 3)"
Cohesion: 0.25
Nodes (15): main(), RawCsvReadError, read_raw_ons_csv(), _validate_csv_structure(), test_accepts_quoted_semicolon_inside_text_field(), test_accepts_utf8_with_bom_without_changing_first_column(), test_reads_confirmed_csv_format_without_early_type_conversion(), test_rejects_changed_or_duplicated_source_schema() (+7 more)

### Community 9 - "API Serverless FastAPI (Vercel)"
Cohesion: 0.14
Nodes (9): _expected_content_length(), _extract_resources(), _iter_response_chunks(), _matches_resource(), _stream_response_to_destination(), _validate_collection_metadata_payload(), _validate_revision_history_entry(), _validate_sha256_hex() (+1 more)

### Community 10 - "Persistência PostgreSQL Neon (Fase 5)"
Cohesion: 0.15
Nodes (6): compute_file_sha256(), download_resource_file(), _validate_chunk_size(), _validate_destination(), _validate_download_url(), _validate_max_attempts()

### Community 11 - "Interface Web Frontend"
Cohesion: 0.20
Nodes (8): build_archived_revision_filepath(), CollectionMetadata, _commit_staged_raw_and_metadata(), _download_discovered_monthly_resource(), read_collection_metadata(), _verify_existing_file_matches_remote_revision(), write_collection_metadata(), test_compute_file_sha256_and_corrupted_metadata_handling()

### Community 12 - "Pacote Principal src"
Cohesion: 0.17
Nodes (8): build_processed_filepath(), build_quality_report_filepath(), transform_monthly_dataset(), _validate_raw_csv_path(), write_processed_parquet(), write_quality_report(), test_build_processed_filepath_uses_relative_default_dir(), test_write_processed_parquet_rejects_directory_destination()

### Community 13 - "Métricas Analíticas (Fase 4)"
Cohesion: 0.18
Nodes (8): build_raw_filename(), iter_year_months(), _validate_month(), _validate_year(), test_builds_predictable_raw_filename_for_source_and_dataset(), test_iter_year_months_handles_single_month_range_and_year_rollover(), test_iter_year_months_rejects_inverted_range(), test_rejects_years_with_fewer_than_four_digits_in_filename()

### Community 14 - "Orquestração do Pipeline (Fase 5)"
Cohesion: 0.18
Nodes (5): DownloadResult, MonthlyExtractionReport, _normalize_resource_metadata(), ResourceMetadata, RevisionHistoryEntry

### Community 15 - "Esquema SQL PostgreSQL"
Cohesion: 0.25
Nodes (5): IdentifierNormalizationError, preserve_operational_identifiers(), standardize_column_names(), test_preserve_operational_identifiers_keeps_string_dtype_and_dash_literal(), test_reads_verified_january_source_file()

### Community 17 - "Comunidade 17"
Cohesion: 0.60
Nodes (4): Descoberta de Recurso CKAN (discover_resource), Download Seguro com Retentativas e Integridade (download_resource_file), Faixa de Meses, Recursos Ausentes e CLI (python -m src.extract), Investigação da API CKAN do ONS

### Community 18 - "Comunidade 18"
Cohesion: 0.40
Nodes (4): EmptyFilterResultError, filter_by_state(), test_filter_by_state_handles_empty_match_explicitly(), test_filter_by_state_selects_ce_and_reports_excluded_and_nulls()

## Knowledge Gaps
- **4 isolated node(s):** `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS`, `Dependências Python do Projeto (requirements.txt)`, `Chave Operacional Candidata (id_ons + din_instante)`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 158 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `FakeDownloadResponse` connect `Testes Sintéticos CKAN, Download e CLI` to `API Serverless FastAPI (Vercel)`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **What connects `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS`, `Dependências Python do Projeto (requirements.txt)` to the rest of the system?**
  _4 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Testes Sintéticos CKAN, Download e CLI` be split into smaller, more focused modules?**
  _Cohesion score 0.06682705159048383 - nodes in this community are weakly interconnected._
- **Why does `ResourceDownloadError` connect `Testes Sintéticos CKAN, Download e CLI` to `API Serverless FastAPI (Vercel)`, `Persistência PostgreSQL Neon (Fase 5)`, `Interface Web Frontend`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Should `Documentação, Metodologia e Arquitetura Vercel/Neon` be split into smaller, more focused modules?**
  _Cohesion score 0.12685560053981107 - nodes in this community are weakly interconnected._
- **Should `Testes de Estrutura, API e Referências` be split into smaller, more focused modules?**
  _Cohesion score 0.0873440285204991 - nodes in this community are weakly interconnected._
- **Should `Validação, Metadados e Hash SHA-256` be split into smaller, more focused modules?**
  _Cohesion score 0.12310606060606061 - nodes in this community are weakly interconnected._