# Graph Report - Projeto_eolica  (2026-11-22)

## Corpus Check
- 31 files · ~30,169 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 407 nodes · 1097 edges · 25 communities (18 shown, 7 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 50 edges (avg confidence: 0.93)
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
- Comunidade 23

## God Nodes (most connected - your core abstractions)
1. `FakeResponse` - 32 edges
2. `FakeDownloadResponse` - 31 edges
3. `download_period_range()` - 26 edges
4. `download_monthly_resource()` - 25 edges
5. `download_resource_file()` - 25 edges
6. `ResourceDownloadError` - 22 edges
7. `ckan_payload()` - 22 edges
8. `SourceSchemaError` - 21 edges
9. `read_raw_ons_csv()` - 21 edges
10. `discover_resource()` - 20 edges

## Surprising Connections (you probably didn't know these)
- `test_add_eligibility_flags_rejects_untyped_or_duplicate_columns()` --uses--> `SourceSchemaError`  [INFERRED]
  tests/test_transform.py → src/transform.py
- `test_convert_mwmed_columns_rejects_missing_column()` --uses--> `SourceSchemaError`  [INFERRED]
  tests/test_transform.py → src/transform.py
- `test_rejects_changed_or_duplicated_source_schema()` --uses--> `SourceSchemaError`  [INFERRED]
  tests/test_transform.py → src/transform.py
- `test_convert_mwmed_columns_rejects_invalid_or_non_finite_strings()` --uses--> `NumericConversionError`  [INFERRED]
  tests/test_transform.py → src/transform.py
- `test_raises_clear_error_when_resource_is_ambiguous()` --uses--> `AmbiguousResourceError`  [INFERRED]
  tests/test_extract.py → src/extract.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Governança de Qualidade e Metodologia do Repositório** — agents_integridade_metodologica, agents_governanca_graphify, agents_contrato_frontend_sem_acesso_direto_sqlite, agents_protocolo_implementacao_autorevisao [EXTRACTED 1.00]
- **Definição Metodológica e Escopo do MVP** — plano_escopo_mvp, plano_fontes_oficiais_ons_aneel, plano_metricas_gnra_mvp, plano_riscos_decisoes [INFERRED 0.95]
- **Arquitetura e Execução do Pipeline de Dados** — plano_arquitetura_pipeline, plano_modelo_dados_sqlite, plano_contratos_execucao_cli, plano_roadmap_fases [INFERRED 0.95]

## Communities (25 total, 7 thin omitted)

### Community 0 - "Testes Sintéticos CKAN, Download e CLI"
Cohesion: 0.07
Nodes (55): AmbiguousResourceError, build_metadata_filepath(), build_raw_filepath(), discover_resource(), download_monthly_resource(), download_resource_file(), read_collection_metadata(), ResourceDiscoveryError (+47 more)

### Community 1 - "Documentação, Metodologia e Arquitetura Vercel/Neon"
Cohesion: 0.15
Nodes (23): add_eligibility_flags(), convert_mwmed_columns(), GranularityValidationError, parse_instante_column(), TimestampConversionError, validate_granularity_and_add_duration(), _sample_standardized_dataframe(), test_add_eligibility_flags_classifies_all_indicators_without_dropping_rows() (+15 more)

### Community 2 - "Testes de Estrutura, API e Referências"
Cohesion: 0.12
Nodes (17): SourceSchemaError, check_and_resolve_key_duplicates(), DataQualityError, DuplicateKeyError, DuplicateKeyReport, QualityCheckReport, run_quality_checks(), test_check_duplicates_always_rejects_conflicting_keys_even_in_drop_exact_only() (+9 more)

### Community 3 - "Validação, Metadados e Hash SHA-256"
Cohesion: 0.08
Nodes (5): health_check(), _is_valid_postgres_url(), test_api_health_reports_database_configuration_without_exposing_secrets(), test_vercel_config_and_runtime_requirements_stay_lightweight(), test_ons_dictionary_json_has_24_unique_fields()

### Community 4 - "Descoberta, Faixa de Meses e CLI CKAN"
Cohesion: 0.10
Nodes (10): ColumnNumericReport, _convert_single_numeric_series(), EligibilityReport, EmptyFilterResultError, filter_by_state(), GranularityReport, IdentifierReport, StateFilterReport (+2 more)

### Community 5 - "Exceções de Extração e Revisão"
Cohesion: 0.14
Nodes (18): Regras para Agentes (AGENTS.md), Chave Operacional Candidata (id_ons + din_instante), Geração Não Realizada Apurada (GNRa), Reconhecimento ONS 2025-01 (Dicionário de Dados), Rotina Operacional ONS RO-AO.BR.13 (Rev. 08), Dicionário de Dados Oficial ONS - Restrição de Operação por Constrained-off de Usinas Eólicas (PDF v1.5), Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS), Registro de Coleta e Hashes dos Dicionários Oficiais ONS (+10 more)

### Community 6 - "Transformação, Tipagem e Filtros CSV ONS"
Cohesion: 0.22
Nodes (14): RawCsvReadError, read_raw_ons_csv(), _validate_csv_structure(), _validate_raw_csv_path(), test_accepts_quoted_semicolon_inside_text_field(), test_accepts_utf8_with_bom_without_changing_first_column(), test_reads_confirmed_csv_format_without_early_type_conversion(), test_rejects_changed_or_duplicated_source_schema() (+6 more)

### Community 7 - "Normalização de Metadados CKAN"
Cohesion: 0.14
Nodes (8): _expected_content_length(), _extract_resources(), _iter_response_chunks(), _matches_resource(), _normalize_resource_metadata(), ResourceMetadata, _select_unique_resource(), _stream_response_to_destination()

### Community 8 - "Validação de Qualidade e Duplicidades (Fase 3)"
Cohesion: 0.15
Nodes (7): download_period_range(), _fetch_ckan_resources(), main(), _validate_max_attempts(), _validate_output_dir(), _validate_overwrite(), _validate_timeout()

### Community 9 - "API Serverless FastAPI (Vercel)"
Cohesion: 0.23
Nodes (6): build_archived_revision_filepath(), CollectionMetadata, _commit_staged_raw_and_metadata(), _download_discovered_monthly_resource(), _verify_existing_file_matches_remote_revision(), write_collection_metadata()

### Community 10 - "Persistência PostgreSQL Neon (Fase 5)"
Cohesion: 0.18
Nodes (4): build_argument_parser(), compute_file_sha256(), _validate_chunk_size(), _validate_destination()

### Community 11 - "Interface Web Frontend"
Cohesion: 0.15
Nodes (9): build_raw_filename(), iter_year_months(), _validate_format(), _validate_month(), _validate_year(), test_builds_predictable_raw_filename_for_source_and_dataset(), test_iter_year_months_handles_single_month_range_and_year_rollover(), test_iter_year_months_rejects_inverted_range() (+1 more)

### Community 12 - "Pacote Principal src"
Cohesion: 0.24
Nodes (5): _validate_collection_metadata_payload(), _validate_download_url(), _validate_revision_history_entry(), _validate_sha256_hex(), _validate_utc_iso_timestamp()

### Community 13 - "Métricas Analíticas (Fase 4)"
Cohesion: 0.22
Nodes (5): inspect_source_schema(), SourceSchemaReport, standardize_column_names(), validate_source_schema(), test_records_column_order_without_rejecting_a_safe_reordering()

### Community 14 - "Orquestração do Pipeline (Fase 5)"
Cohesion: 0.29
Nodes (4): IdentifierNormalizationError, NumericConversionError, preserve_operational_identifiers(), test_preserve_operational_identifiers_rejects_null_or_blank_ons_id()

### Community 15 - "Esquema SQL PostgreSQL"
Cohesion: 0.29
Nodes (3): DownloadResult, MonthlyExtractionReport, RevisionHistoryEntry

### Community 16 - "Comunidade 16"
Cohesion: 0.33
Nodes (4): resolve_dataset_id(), _validate_dataset(), test_rejects_unsupported_or_invalid_source(), test_resolves_supported_source_and_dataset_identifiers()

### Community 17 - "Comunidade 17"
Cohesion: 0.60
Nodes (4): Descoberta de Recurso CKAN (discover_resource), Download Seguro com Retentativas e Integridade (download_resource_file), Faixa de Meses, Recursos Ausentes e CLI (python -m src.extract), Investigação da API CKAN do ONS

## Knowledge Gaps
- **4 isolated node(s):** `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS`, `Dependências Python do Projeto (requirements.txt)`, `Chave Operacional Candidata (id_ons + din_instante)`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 142 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `FakeDownloadResponse` connect `Testes Sintéticos CKAN, Download e CLI` to `Normalização de Metadados CKAN`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **What connects `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS`, `Dependências Python do Projeto (requirements.txt)` to the rest of the system?**
  _4 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Testes Sintéticos CKAN, Download e CLI` be split into smaller, more focused modules?**
  _Cohesion score 0.06517357222844344 - nodes in this community are weakly interconnected._
- **Why does `ResourceDownloadError` connect `Testes Sintéticos CKAN, Download e CLI` to `Persistência PostgreSQL Neon (Fase 5)`, `Pacote Principal src`, `Normalização de Metadados CKAN`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Should `Testes de Estrutura, API e Referências` be split into smaller, more focused modules?**
  _Cohesion score 0.12100840336134454 - nodes in this community are weakly interconnected._
- **Should `Validação, Metadados e Hash SHA-256` be split into smaller, more focused modules?**
  _Cohesion score 0.08465608465608465 - nodes in this community are weakly interconnected._
- **Should `Descoberta, Faixa de Meses e CLI CKAN` be split into smaller, more focused modules?**
  _Cohesion score 0.09788359788359788 - nodes in this community are weakly interconnected._