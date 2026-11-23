# Graph Report - Projeto_eolica  (2026-11-22)

## Corpus Check
- Corpus is ~39,666 words - fits in a single context window. You may not need a graph.

## Summary
- 518 nodes · 1397 edges · 44 communities (24 shown, 20 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 61 edges (avg confidence: 0.92)
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
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 29
- Community 38

## God Nodes (most connected - your core abstractions)
1. `FakeResponse` - 32 edges
2. `FakeDownloadResponse` - 31 edges
3. `download_period_range()` - 27 edges
4. `download_resource_file()` - 26 edges
5. `SourceSchemaError` - 26 edges
6. `parse_instante_column()` - 26 edges
7. `download_monthly_resource()` - 25 edges
8. `transform_monthly_dataset()` - 25 edges
9. `read_raw_ons_csv()` - 23 edges
10. `convert_mwmed_columns()` - 23 edges

## Surprising Connections (you probably didn't know these)
- `generate_basic_phase4_charts()` --generates--> `Grafico SVG: Geracao Verificada Diaria (MWh)`  [EXTRACTED]
  src/metrics.py → docs/imagens/fase4/geracao_diaria_mwh.svg
- `generate_basic_phase4_charts()` --generates--> `Grafico SVG: Distribuicao Horaria das Restricoes`  [EXTRACTED]
  src/metrics.py → docs/imagens/fase4/restricoes_por_hora.svg
- `generate_basic_phase4_charts()` --generates--> `Grafico SVG: Intervalos Restritos por Razao Oficial`  [EXTRACTED]
  src/metrics.py → docs/imagens/fase4/restricoes_por_razao.svg
- `test_raises_clear_error_when_ckan_reports_failure()` --uses--> `ResourceDiscoveryError`  [INFERRED]
  tests/test_extract.py → src/extract.py
- `test_rejects_resource_with_invalid_url()` --uses--> `ResourceDiscoveryError`  [INFERRED]
  tests/test_extract.py → src/extract.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Governança de Qualidade e Metodologia do Repositório** — agents_integridade_metodologica, agents_governanca_graphify, agents_contrato_frontend_sem_acesso_direto_sqlite, agents_protocolo_implementacao_autorevisao [EXTRACTED 1.00]
- **Definição Metodológica e Escopo do MVP** — plano_escopo_mvp, plano_fontes_oficiais_ons_aneel, plano_metricas_gnra_mvp, plano_riscos_decisoes [INFERRED 0.95]
- **Arquitetura e Execução do Pipeline de Dados** — plano_arquitetura_pipeline, plano_modelo_dados_sqlite, plano_contratos_execucao_cli, plano_roadmap_fases [INFERRED 0.95]

## Communities (44 total, 20 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.07
Nodes (33): Grafico SVG: Geracao Verificada Diaria (MWh), Grafico SVG: Distribuicao Horaria das Restricoes, Grafico SVG: Intervalos Restritos por Razao Oficial, build_enterprise_ranking(), build_generation_series(), CoverageSummary, generate_basic_phase4_charts(), GnraReconciliationReport (+25 more)

### Community 1 - "Community 1"
Cohesion: 0.11
Nodes (20): SourceSchemaError, standardize_column_names(), validate_source_schema(), check_and_resolve_key_duplicates(), DataQualityError, DuplicateKeyError, DuplicateKeyReport, QualityCheckReport (+12 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (10): EligibilityReport, EnergyCalculationReport, GranularityReport, IdentifierReport, inspect_source_schema(), SourceSchemaReport, StateFilterReport, TimestampConversionReport (+2 more)

### Community 3 - "Community 3"
Cohesion: 0.13
Nodes (19): Regras para Agentes (AGENTS.md), Achados Explorat?rios do MVP ? Cear? (Janeiro/2025), Chave Operacional Candidata (id_ons + din_instante), Geração Não Realizada Apurada (GNRa), Reconhecimento ONS 2025-01 (Dicionário de Dados), Rotina Operacional ONS RO-AO.BR.13 (Rev. 08), Dicionário de Dados Oficial ONS - Restrição de Operação por Constrained-off de Usinas Eólicas (PDF v1.5), Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS) (+11 more)

### Community 4 - "Community 4"
Cohesion: 0.17
Nodes (11): discover_resource(), ckan_payload(), FakeResponse, FakeSession, test_discovers_unique_resource_and_returns_normalized_metadata(), test_raises_clear_error_when_ckan_reports_failure(), test_raises_clear_error_when_resource_is_ambiguous(), test_raises_clear_error_when_resource_is_missing() (+3 more)

### Community 5 - "Community 5"
Cohesion: 0.23
Nodes (15): main(), RawCsvReadError, read_raw_ons_csv(), test_accepts_quoted_semicolon_inside_text_field(), test_accepts_utf8_with_bom_without_changing_first_column(), test_reads_confirmed_csv_format_without_early_type_conversion(), test_rejects_changed_or_duplicated_source_schema(), test_rejects_comma_in_numeric_source_field() (+7 more)

### Community 6 - "Community 6"
Cohesion: 0.21
Nodes (13): download_resource_file(), FakeDownloadResponse, FakeDownloadSession, test_does_not_retry_permanent_http_404_error(), test_downloads_file_in_chunks_and_computes_sha256(), test_ignores_compressed_content_length_when_content_encoding_is_present(), test_public_extract_functions_raise_type_error_for_invalid_argument_types(), test_raises_clear_error_after_exhausting_max_attempts() (+5 more)

### Community 7 - "Community 7"
Cohesion: 0.14
Nodes (10): build_processed_filepath(), build_quality_report_filepath(), transform_monthly_dataset(), TransformationQualityReport, _validate_raw_csv_path(), write_processed_parquet(), write_quality_report(), test_atomic_writers_clean_part_files_on_io_failure() (+2 more)

### Community 8 - "Community 8"
Cohesion: 0.13
Nodes (12): download_period_range(), main(), _validate_max_attempts(), _validate_timeout(), FakeRangeSession, test_cli_main_downloads_single_month_and_prints_summary(), test_cli_main_returns_nonzero_and_prints_error_for_missing_month(), test_download_period_range_does_not_silence_revision_conflict_when_allow_missing_is_true() (+4 more)

### Community 9 - "Community 9"
Cohesion: 0.16
Nodes (13): GranularityValidationError, parse_instante_column(), TimestampConversionError, validate_granularity_and_add_duration(), _sample_standardized_dataframe(), test_convert_mwmed_columns_rejects_invalid_or_non_finite_strings(), test_filter_by_state_rejects_invalid_state_code(), test_parse_instante_converts_official_format_and_preserves_original_nulls() (+5 more)

### Community 10 - "Community 10"
Cohesion: 0.16
Nodes (12): add_eligibility_flags(), add_energy_and_preserve_gnra(), ColumnNumericReport, convert_mwmed_columns(), _convert_single_numeric_series(), NumericConversionError, test_add_eligibility_flags_classifies_all_indicators_without_dropping_rows(), test_add_eligibility_flags_rejects_untyped_or_duplicate_columns() (+4 more)

### Community 11 - "Community 11"
Cohesion: 0.16
Nodes (3): test_api_health_reports_database_configuration_without_exposing_secrets(), test_vercel_config_and_runtime_requirements_stay_lightweight(), test_ons_dictionary_json_has_24_unique_fields()

### Community 12 - "Community 12"
Cohesion: 0.16
Nodes (9): EmptyFilterResultError, filter_by_state(), IdentifierNormalizationError, preserve_operational_identifiers(), test_filter_by_state_handles_empty_match_explicitly(), test_filter_by_state_selects_ce_and_reports_excluded_and_nulls(), test_preserve_operational_identifiers_keeps_string_dtype_and_dash_literal(), test_preserve_operational_identifiers_rejects_null_or_blank_ons_id() (+1 more)

### Community 13 - "Community 13"
Cohesion: 0.19
Nodes (10): compute_file_sha256(), read_collection_metadata(), ResourceDownloadError, _validate_chunk_size(), test_compute_file_sha256_and_corrupted_metadata_handling(), test_download_monthly_resource_removes_new_csv_if_initial_metadata_write_fails(), fail_metadata_write(), test_download_monthly_resource_rolls_back_csv_if_metadata_write_fails() (+2 more)

### Community 14 - "Community 14"
Cohesion: 0.16
Nodes (8): build_archived_revision_filepath(), build_metadata_filepath(), build_raw_filepath(), _validate_destination(), _validate_output_dir(), test_builds_predictable_raw_filepath_with_default_and_custom_dir(), test_download_monthly_resource_with_overwrite_preserves_multi_revision_history_and_archived_files(), test_rejects_output_dir_when_it_points_to_existing_file()

### Community 15 - "Community 15"
Cohesion: 0.15
Nodes (9): build_raw_filename(), iter_year_months(), _validate_format(), _validate_month(), _validate_year(), test_builds_predictable_raw_filename_for_source_and_dataset(), test_iter_year_months_handles_single_month_range_and_year_rollover(), test_iter_year_months_rejects_inverted_range() (+1 more)

### Community 16 - "Community 16"
Cohesion: 0.20
Nodes (8): download_monthly_resource(), ResourceRevisionConflictError, _validate_overwrite(), FakeCombinedSession, test_download_monthly_resource_detects_local_file_tampering_against_manifest(), test_download_monthly_resource_detects_remote_ckan_revision_and_blocks_overwrite(), test_download_monthly_resource_rejects_untracked_existing_file_without_overwrite(), test_download_monthly_resource_reuses_existing_file_when_version_and_hash_match()

### Community 17 - "Community 17"
Cohesion: 0.17
Nodes (5): AmbiguousResourceError, _extract_resources(), _fetch_ckan_resources(), ResourceDiscoveryError, ResourceNotFoundError

### Community 18 - "Community 18"
Cohesion: 0.26
Nodes (5): CollectionMetadata, _commit_staged_raw_and_metadata(), _download_discovered_monthly_resource(), _verify_existing_file_matches_remote_revision(), write_collection_metadata()

### Community 19 - "Community 19"
Cohesion: 0.20
Nodes (6): RevisionHistoryEntry, _validate_collection_metadata_payload(), _validate_download_url(), _validate_revision_history_entry(), _validate_sha256_hex(), _validate_utc_iso_timestamp()

### Community 20 - "Community 20"
Cohesion: 0.29
Nodes (5): resolve_dataset_id(), _validate_dataset(), test_rejects_unsupported_or_invalid_source(), test_resolves_supported_source_and_dataset_identifiers(), test_strict_validation_of_collection_metadata_fields()

### Community 21 - "Community 21"
Cohesion: 0.28
Nodes (3): _expected_content_length(), _iter_response_chunks(), _stream_response_to_destination()

### Community 23 - "Community 23"
Cohesion: 0.29
Nodes (4): _matches_resource(), _normalize_resource_metadata(), ResourceMetadata, _select_unique_resource()

### Community 26 - "Community 26"
Cohesion: 0.60
Nodes (4): Descoberta de Recurso CKAN (discover_resource), Download Seguro com Retentativas e Integridade (download_resource_file), Faixa de Meses, Recursos Ausentes e CLI (python -m src.extract), Investigação da API CKAN do ONS

## Knowledge Gaps
- **8 isolated node(s):** `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Achados Explorat?rios do MVP ? Cear? (Janeiro/2025)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS`, `Dependências Python do Projeto (requirements.txt)`, `Chave Operacional Candidata (id_ons + din_instante)` (+3 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 198 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `FakeDownloadResponse` connect `Community 6` to `Community 4`, `Community 8`, `Community 13`, `Community 14`, `Community 16`, `Community 20`, `Community 21`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **What connects `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Achados Explorat?rios do MVP ? Cear? (Janeiro/2025)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS` to the rest of the system?**
  _8 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06734867860187553 - nodes in this community are weakly interconnected._
- **Why does `compute_file_sha256()` connect `Community 13` to `Community 2`, `Community 6`, `Community 7`, `Community 14`, `Community 18`, `Community 20`, `Community 21`, `Community 22`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.1073170731707317 - nodes in this community are weakly interconnected._
- **Why does `FakeResponse` connect `Community 4` to `Community 8`, `Community 13`, `Community 14`, `Community 16`, `Community 20`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.09259259259259259 - nodes in this community are weakly interconnected._