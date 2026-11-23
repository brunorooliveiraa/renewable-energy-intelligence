# Graph Report - Projeto_eolica  (2026-11-22)

## Corpus Check
- 33 files · ~36,648 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 482 nodes · 1342 edges · 32 communities (25 shown, 7 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 58 edges (avg confidence: 0.92)
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
- Comunidade 21
- Comunidade 22
- Comunidade 23
- Comunidade 24
- Comunidade 25
- Comunidade 26
- Comunidade 30

## God Nodes (most connected - your core abstractions)
1. `FakeResponse` - 32 edges
2. `FakeDownloadResponse` - 31 edges
3. `download_period_range()` - 26 edges
4. `download_monthly_resource()` - 25 edges
5. `download_resource_file()` - 25 edges
6. `parse_instante_column()` - 23 edges
7. `ResourceDownloadError` - 22 edges
8. `SourceSchemaError` - 22 edges
9. `read_raw_ons_csv()` - 22 edges
10. `ckan_payload()` - 22 edges

## Surprising Connections (you probably didn't know these)
- `test_compute_file_sha256_and_corrupted_metadata_handling()` --uses--> `ResourceDownloadError`  [INFERRED]
  tests/test_extract.py → src/extract.py
- `test_does_not_retry_permanent_http_404_error()` --uses--> `ResourceDownloadError`  [INFERRED]
  tests/test_extract.py → src/extract.py
- `test_raises_clear_error_after_exhausting_max_attempts()` --uses--> `ResourceDownloadError`  [INFERRED]
  tests/test_extract.py → src/extract.py
- `test_rejects_empty_downloaded_file()` --uses--> `ResourceDownloadError`  [INFERRED]
  tests/test_extract.py → src/extract.py
- `test_rejects_truncated_download_when_content_length_mismatches()` --uses--> `ResourceDownloadError`  [INFERRED]
  tests/test_extract.py → src/extract.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Governança de Qualidade e Metodologia do Repositório** — agents_integridade_metodologica, agents_governanca_graphify, agents_contrato_frontend_sem_acesso_direto_sqlite, agents_protocolo_implementacao_autorevisao [EXTRACTED 1.00]
- **Definição Metodológica e Escopo do MVP** — plano_escopo_mvp, plano_fontes_oficiais_ons_aneel, plano_metricas_gnra_mvp, plano_riscos_decisoes [INFERRED 0.95]
- **Arquitetura e Execução do Pipeline de Dados** — plano_arquitetura_pipeline, plano_modelo_dados_sqlite, plano_contratos_execucao_cli, plano_roadmap_fases [INFERRED 0.95]

## Communities (32 total, 7 thin omitted)

### Community 0 - "Testes Sintéticos CKAN, Download e CLI"
Cohesion: 0.08
Nodes (26): build_enterprise_ranking(), build_generation_series(), CoverageSummary, GnraReconciliationReport, identify_peak_restriction_periods(), IntervalCountsSummary, _pct(), PeakRestrictionsSummary (+18 more)

### Community 1 - "Documentação, Metodologia e Arquitetura Vercel/Neon"
Cohesion: 0.12
Nodes (16): check_and_resolve_key_duplicates(), DataQualityError, DuplicateKeyError, DuplicateKeyReport, QualityCheckReport, run_quality_checks(), test_check_duplicates_always_rejects_conflicting_keys_even_in_drop_exact_only(), test_check_duplicates_handles_exact_duplicates_by_policy() (+8 more)

### Community 2 - "Testes de Estrutura, API e Referências"
Cohesion: 0.16
Nodes (21): add_eligibility_flags(), parse_instante_column(), TimestampConversionError, validate_granularity_and_add_duration(), _sample_standardized_dataframe(), test_add_eligibility_flags_classifies_all_indicators_without_dropping_rows(), test_add_eligibility_flags_rejects_untyped_or_duplicate_columns(), test_add_energy_and_preserve_gnra_computes_50mwh_for_100mwmed_half_hour() (+13 more)

### Community 3 - "Validação, Metadados e Hash SHA-256"
Cohesion: 0.13
Nodes (19): Regras para Agentes (AGENTS.md), Achados Explorat?rios do MVP ? Cear? (Janeiro/2025), Chave Operacional Candidata (id_ons + din_instante), Geração Não Realizada Apurada (GNRa), Reconhecimento ONS 2025-01 (Dicionário de Dados), Rotina Operacional ONS RO-AO.BR.13 (Rev. 08), Dicionário de Dados Oficial ONS - Restrição de Operação por Constrained-off de Usinas Eólicas (PDF v1.5), Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS) (+11 more)

### Community 4 - "Descoberta, Faixa de Meses e CLI CKAN"
Cohesion: 0.10
Nodes (10): EligibilityReport, EnergyCalculationReport, GranularityReport, IdentifierReport, inspect_source_schema(), SourceSchemaReport, StateFilterReport, TimestampConversionReport (+2 more)

### Community 5 - "Exceções de Extração e Revisão"
Cohesion: 0.16
Nodes (13): AmbiguousResourceError, discover_resource(), ResourceDiscoveryError, ResourceNotFoundError, FakeResponse, FakeSession, test_discovers_unique_resource_and_returns_normalized_metadata(), test_raises_clear_error_when_ckan_reports_failure() (+5 more)

### Community 6 - "Transformação, Tipagem e Filtros CSV ONS"
Cohesion: 0.15
Nodes (11): build_metadata_filepath(), download_monthly_resource(), ResourceRevisionConflictError, FakeCombinedSession, FakeDownloadResponse, test_download_monthly_resource_detects_local_file_tampering_against_manifest(), test_download_monthly_resource_detects_remote_ckan_revision_and_blocks_overwrite(), test_download_monthly_resource_rejects_untracked_existing_file_without_overwrite() (+3 more)

### Community 7 - "Normalização de Metadados CKAN"
Cohesion: 0.28
Nodes (14): RawCsvReadError, read_raw_ons_csv(), _validate_csv_structure(), test_accepts_quoted_semicolon_inside_text_field(), test_accepts_utf8_with_bom_without_changing_first_column(), test_reads_confirmed_csv_format_without_early_type_conversion(), test_rejects_changed_or_duplicated_source_schema(), test_rejects_comma_in_numeric_source_field() (+6 more)

### Community 8 - "Validação de Qualidade e Duplicidades (Fase 3)"
Cohesion: 0.18
Nodes (9): CollectionMetadata, _commit_staged_raw_and_metadata(), compute_file_sha256(), _download_discovered_monthly_resource(), read_collection_metadata(), _stream_response_to_destination(), _verify_existing_file_matches_remote_revision(), write_collection_metadata() (+1 more)

### Community 9 - "API Serverless FastAPI (Vercel)"
Cohesion: 0.18
Nodes (14): download_resource_file(), _validate_max_attempts(), _validate_overwrite(), _validate_timeout(), FakeDownloadSession, test_does_not_retry_permanent_http_404_error(), test_downloads_file_in_chunks_and_computes_sha256(), test_ignores_compressed_content_length_when_content_encoding_is_present() (+6 more)

### Community 10 - "Persistência PostgreSQL Neon (Fase 5)"
Cohesion: 0.14
Nodes (10): build_processed_filepath(), build_quality_report_filepath(), standardize_column_names(), transform_monthly_dataset(), TransformationQualityReport, _validate_raw_csv_path(), write_processed_parquet(), write_quality_report() (+2 more)

### Community 11 - "Interface Web Frontend"
Cohesion: 0.19
Nodes (11): download_period_range(), _fetch_ckan_resources(), main(), ckan_payload(), FakeRangeSession, test_cli_main_downloads_single_month_and_prints_summary(), test_cli_main_returns_nonzero_and_prints_error_for_missing_month(), test_download_period_range_does_not_silence_revision_conflict_when_allow_missing_is_true() (+3 more)

### Community 12 - "Pacote Principal src"
Cohesion: 0.15
Nodes (12): build_raw_filename(), build_raw_filepath(), iter_year_months(), _validate_format(), _validate_year(), test_builds_predictable_raw_filename_for_source_and_dataset(), test_builds_predictable_raw_filepath_with_default_and_custom_dir(), test_download_period_range_rejects_end_year_without_end_month() (+4 more)

### Community 13 - "Métricas Analíticas (Fase 4)"
Cohesion: 0.16
Nodes (3): test_api_health_reports_database_configuration_without_exposing_secrets(), test_vercel_config_and_runtime_requirements_stay_lightweight(), test_ons_dictionary_json_has_24_unique_fields()

### Community 14 - "Orquestração do Pipeline (Fase 5)"
Cohesion: 0.15
Nodes (7): _expected_content_length(), _extract_resources(), _iter_response_chunks(), _matches_resource(), _normalize_resource_metadata(), ResourceMetadata, _select_unique_resource()

### Community 15 - "Esquema SQL PostgreSQL"
Cohesion: 0.18
Nodes (7): add_energy_and_preserve_gnra(), ColumnNumericReport, convert_mwmed_columns(), _convert_single_numeric_series(), NumericConversionError, SourceSchemaError, test_convert_mwmed_columns_rejects_missing_column()

### Community 16 - "Comunidade 16"
Cohesion: 0.16
Nodes (3): _validate_chunk_size(), _validate_destination(), _validate_output_dir()

### Community 17 - "Comunidade 17"
Cohesion: 0.15
Nodes (5): resolve_dataset_id(), _validate_dataset(), test_rejects_unsupported_or_invalid_source(), test_resolves_supported_source_and_dataset_identifiers(), test_strict_validation_of_collection_metadata_fields()

### Community 18 - "Comunidade 18"
Cohesion: 0.16
Nodes (7): build_archived_revision_filepath(), _validate_collection_metadata_payload(), _validate_download_url(), _validate_month(), _validate_revision_history_entry(), _validate_sha256_hex(), _validate_utc_iso_timestamp()

### Community 19 - "Comunidade 19"
Cohesion: 0.29
Nodes (3): build_argument_parser(), build_argument_parser(), main()

### Community 20 - "Comunidade 20"
Cohesion: 0.29
Nodes (4): GranularityValidationError, IdentifierNormalizationError, preserve_operational_identifiers(), test_preserve_operational_identifiers_rejects_null_or_blank_ons_id()

### Community 21 - "Comunidade 21"
Cohesion: 0.48
Nodes (5): ResourceDownloadError, test_download_monthly_resource_removes_new_csv_if_initial_metadata_write_fails(), fail_metadata_write(), test_download_monthly_resource_rolls_back_csv_if_metadata_write_fails(), fail_metadata_write()

### Community 22 - "Comunidade 22"
Cohesion: 0.29
Nodes (3): DownloadResult, MonthlyExtractionReport, RevisionHistoryEntry

### Community 24 - "Comunidade 24"
Cohesion: 0.60
Nodes (4): Descoberta de Recurso CKAN (discover_resource), Download Seguro com Retentativas e Integridade (download_resource_file), Faixa de Meses, Recursos Ausentes e CLI (python -m src.extract), Investigação da API CKAN do ONS

### Community 25 - "Comunidade 25"
Cohesion: 0.40
Nodes (4): EmptyFilterResultError, filter_by_state(), test_filter_by_state_handles_empty_match_explicitly(), test_filter_by_state_selects_ce_and_reports_excluded_and_nulls()

## Knowledge Gaps
- **5 isolated node(s):** `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS`, `Dependências Python do Projeto (requirements.txt)`, `Chave Operacional Candidata (id_ons + din_instante)`, `Achados Explorat?rios do MVP ? Cear? (Janeiro/2025)`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 169 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `FakeDownloadResponse` connect `Transformação, Tipagem e Filtros CSV ONS` to `API Serverless FastAPI (Vercel)`, `Interface Web Frontend`, `Pacote Principal src`, `Orquestração do Pipeline (Fase 5)`, `Comunidade 17`, `Comunidade 21`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **What connects `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS`, `Dependências Python do Projeto (requirements.txt)` to the rest of the system?**
  _5 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Testes Sintéticos CKAN, Download e CLI` be split into smaller, more focused modules?**
  _Cohesion score 0.08144796380090498 - nodes in this community are weakly interconnected._
- **Why does `FakeResponse` connect `Exceções de Extração e Revisão` to `Transformação, Tipagem e Filtros CSV ONS`, `Interface Web Frontend`, `Pacote Principal src`, `Comunidade 17`, `Comunidade 21`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Should `Documentação, Metodologia e Arquitetura Vercel/Neon` be split into smaller, more focused modules?**
  _Cohesion score 0.12310606060606061 - nodes in this community are weakly interconnected._
- **Why does `ResourceDownloadError` connect `Comunidade 21` to `Exceções de Extração e Revisão`, `Transformação, Tipagem e Filtros CSV ONS`, `Validação de Qualidade e Duplicidades (Fase 3)`, `API Serverless FastAPI (Vercel)`, `Pacote Principal src`, `Orquestração do Pipeline (Fase 5)`, `Comunidade 16`, `Comunidade 17`, `Comunidade 18`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Should `Validação, Metadados e Hash SHA-256` be split into smaller, more focused modules?**
  _Cohesion score 0.1282051282051282 - nodes in this community are weakly interconnected._