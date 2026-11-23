# Graph Report - Projeto_eolica  (2026-11-22)

## Corpus Check
- Corpus is ~38,733 words - fits in a single context window. You may not need a graph.

## Summary
- 514 nodes · 1329 edges · 37 communities (19 shown, 18 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 26 edges (avg confidence: 0.88)
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
- Community 22
- Community 31

## God Nodes (most connected - your core abstractions)
1. `FakeResponse` - 32 edges
2. `FakeDownloadResponse` - 31 edges
3. `download_period_range()` - 26 edges
4. `download_resource_file()` - 25 edges
5. `download_monthly_resource()` - 25 edges
6. `parse_instante_column()` - 25 edges
7. `transform_monthly_dataset()` - 25 edges
8. `read_raw_ons_csv()` - 22 edges
9. `convert_mwmed_columns()` - 22 edges
10. `ckan_payload()` - 22 edges

## Surprising Connections (you probably didn't know these)
- `generate_basic_phase4_charts()` --generates--> `Grafico SVG: Geracao Verificada Diaria (MWh)`  [EXTRACTED]
  src/metrics.py → docs/imagens/fase4/geracao_diaria_mwh.svg
- `generate_basic_phase4_charts()` --generates--> `Grafico SVG: Distribuicao Horaria das Restricoes`  [EXTRACTED]
  src/metrics.py → docs/imagens/fase4/restricoes_por_hora.svg
- `generate_basic_phase4_charts()` --generates--> `Grafico SVG: Intervalos Restritos por Razao Oficial`  [EXTRACTED]
  src/metrics.py → docs/imagens/fase4/restricoes_por_razao.svg
- `test_parse_instante_rejects_tz_aware_series()` --calls--> `parse_instante_column()`  [EXTRACTED]
  tests/test_transform.py → src/transform.py
- `test_convert_mwmed_columns_rejects_missing_column()` --calls--> `convert_mwmed_columns()`  [EXTRACTED]
  tests/test_transform.py → src/transform.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Governança de Qualidade e Metodologia do Repositório** — agents_integridade_metodologica, agents_governanca_graphify, agents_contrato_frontend_sem_acesso_direto_sqlite, agents_protocolo_implementacao_autorevisao [EXTRACTED 1.00]
- **Definição Metodológica e Escopo do MVP** — plano_escopo_mvp, plano_fontes_oficiais_ons_aneel, plano_metricas_gnra_mvp, plano_riscos_decisoes [INFERRED 0.95]
- **Arquitetura e Execução do Pipeline de Dados** — plano_arquitetura_pipeline, plano_modelo_dados_sqlite, plano_contratos_execucao_cli, plano_roadmap_fases [INFERRED 0.95]

## Communities (37 total, 18 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (57): build_metadata_filepath(), build_raw_filename(), discover_resource(), download_monthly_resource(), iter_year_months(), resolve_dataset_id(), _validate_dataset(), _validate_month() (+49 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (34): Grafico SVG: Geracao Verificada Diaria (MWh), Grafico SVG: Distribuicao Horaria das Restricoes, Grafico SVG: Intervalos Restritos por Razao Oficial, build_enterprise_ranking(), build_generation_series(), CoverageSummary, generate_basic_phase4_charts(), GnraReconciliationReport (+26 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (34): add_eligibility_flags(), convert_mwmed_columns(), parse_instante_column(), SourceSchemaError, validate_granularity_and_add_duration(), check_and_resolve_key_duplicates(), DataQualityError, DuplicateKeyError (+26 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (5): health_check(), _is_valid_postgres_url(), test_api_health_reports_database_configuration_without_exposing_secrets(), test_vercel_config_and_runtime_requirements_stay_lightweight(), test_ons_dictionary_json_has_24_unique_fields()

### Community 4 - "Community 4"
Cohesion: 0.13
Nodes (19): Regras para Agentes (AGENTS.md), Achados Explorat?rios do MVP ? Cear? (Janeiro/2025), Chave Operacional Candidata (id_ons + din_instante), Geração Não Realizada Apurada (GNRa), Reconhecimento ONS 2025-01 (Dicionário de Dados), Rotina Operacional ONS RO-AO.BR.13 (Rev. 08), Dicionário de Dados Oficial ONS - Restrição de Operação por Constrained-off de Usinas Eólicas (PDF v1.5), Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS) (+11 more)

### Community 5 - "Community 5"
Cohesion: 0.12
Nodes (7): ColumnNumericReport, EligibilityReport, EnergyCalculationReport, GranularityReport, IdentifierReport, StateFilterReport, TimestampConversionReport

### Community 6 - "Community 6"
Cohesion: 0.14
Nodes (12): filter_by_state(), IdentifierNormalizationError, preserve_operational_identifiers(), standardize_column_names(), test_build_processed_filepath_uses_relative_default_dir(), test_convert_mwmed_columns_rejects_missing_column(), test_filter_by_state_handles_empty_match_explicitly(), test_filter_by_state_selects_ce_and_reports_excluded_and_nulls() (+4 more)

### Community 7 - "Community 7"
Cohesion: 0.20
Nodes (8): build_archived_revision_filepath(), CollectionMetadata, _commit_staged_raw_and_metadata(), _download_discovered_monthly_resource(), read_collection_metadata(), _verify_existing_file_matches_remote_revision(), write_collection_metadata(), test_compute_file_sha256_and_corrupted_metadata_handling()

### Community 8 - "Community 8"
Cohesion: 0.14
Nodes (8): build_raw_filepath(), download_period_range(), _fetch_ckan_resources(), main(), _validate_max_attempts(), _validate_output_dir(), _validate_overwrite(), _validate_timeout()

### Community 9 - "Community 9"
Cohesion: 0.15
Nodes (8): AmbiguousResourceError, _extract_resources(), _matches_resource(), _normalize_resource_metadata(), ResourceDiscoveryError, ResourceMetadata, ResourceNotFoundError, _select_unique_resource()

### Community 10 - "Community 10"
Cohesion: 0.16
Nodes (8): build_processed_filepath(), build_quality_report_filepath(), main(), transform_monthly_dataset(), TransformationQualityReport, _validate_raw_csv_path(), write_quality_report(), test_transform_monthly_dataset_writes_parquet_and_quality_report_and_cli_runs()

### Community 11 - "Community 11"
Cohesion: 0.15
Nodes (8): download_resource_file(), _expected_content_length(), _iter_response_chunks(), ResourceDownloadError, ResourceRevisionConflictError, _stream_response_to_destination(), _validate_destination(), fail_metadata_write()

### Community 12 - "Community 12"
Cohesion: 0.40
Nodes (11): read_raw_ons_csv(), test_accepts_quoted_semicolon_inside_text_field(), test_accepts_utf8_with_bom_without_changing_first_column(), test_reads_confirmed_csv_format_without_early_type_conversion(), test_rejects_changed_or_duplicated_source_schema(), test_rejects_comma_in_numeric_source_field(), test_rejects_missing_empty_and_non_utf8_files(), test_rejects_rows_with_wrong_field_count() (+3 more)

### Community 13 - "Community 13"
Cohesion: 0.18
Nodes (6): inspect_source_schema(), RawCsvReadError, SourceSchemaReport, _validate_csv_structure(), validate_source_schema(), test_records_column_order_without_rejecting_a_safe_reordering()

### Community 14 - "Community 14"
Cohesion: 0.20
Nodes (6): _validate_collection_metadata_payload(), _validate_download_url(), _validate_format(), _validate_revision_history_entry(), _validate_sha256_hex(), _validate_utc_iso_timestamp()

### Community 15 - "Community 15"
Cohesion: 0.22
Nodes (4): EmptyFilterResultError, GranularityValidationError, NumericConversionError, TimestampConversionError

### Community 18 - "Community 18"
Cohesion: 0.29
Nodes (3): DownloadResult, MonthlyExtractionReport, RevisionHistoryEntry

### Community 19 - "Community 19"
Cohesion: 0.29
Nodes (3): write_processed_parquet(), test_atomic_writers_clean_part_files_on_io_failure(), test_write_processed_parquet_rejects_directory_destination()

### Community 20 - "Community 20"
Cohesion: 0.60
Nodes (4): Descoberta de Recurso CKAN (discover_resource), Download Seguro com Retentativas e Integridade (download_resource_file), Faixa de Meses, Recursos Ausentes e CLI (python -m src.extract), Investigação da API CKAN do ONS

## Knowledge Gaps
- **8 isolated node(s):** `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Achados Explorat?rios do MVP ? Cear? (Janeiro/2025)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS`, `Chave Operacional Candidata (id_ons + din_instante)`, `Dependências Python do Projeto (requirements.txt)` (+3 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 199 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `FakeDownloadResponse` connect `Community 0` to `Community 11`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **What connects `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Achados Explorat?rios do MVP ? Cear? (Janeiro/2025)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS` to the rest of the system?**
  _8 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.05979843225083987 - nodes in this community are weakly interconnected._
- **Why does `compute_file_sha256()` connect `Community 17` to `Community 0`, `Community 5`, `Community 7`, `Community 10`, `Community 19`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.06202435312024353 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.07231638418079096 - nodes in this community are weakly interconnected._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.08465608465608465 - nodes in this community are weakly interconnected._