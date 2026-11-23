# Graph Report - Projeto_eolica  (2026-11-22)

## Corpus Check
- 25 files · ~26,868 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 374 nodes · 1010 edges · 24 communities (16 shown, 8 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 48 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Testes Sintéticos CKAN, Download e CLI
- Documentação, Metodologia e Plano
- Testes de Estrutura e Referências
- Validação, Metadados e Hash SHA-256
- Descoberta, Faixa de Meses e CLI CKAN
- Exceções de Extração e Revisão
- Transformação, Tipagem e Filtros CSV ONS
- Normalização de Metadados CKAN
- Validação de Qualidade e Duplicidades (Fase 3)
- Interface Web Frontend
- Persistência SQLite (Fase 5)
- Pacote Principal src
- Métricas Analíticas (Fase 4)
- Orquestração do Pipeline (Fase 5)
- Esquema SQL
- Comunidade 15
- Comunidade 16
- Comunidade 17
- Comunidade 22

## God Nodes (most connected - your core abstractions)
1. `FakeResponse` - 32 edges
2. `FakeDownloadResponse` - 31 edges
3. `download_period_range()` - 26 edges
4. `download_monthly_resource()` - 25 edges
5. `download_resource_file()` - 25 edges
6. `ResourceDownloadError` - 22 edges
7. `ckan_payload()` - 22 edges
8. `read_raw_ons_csv()` - 21 edges
9. `discover_resource()` - 20 edges
10. `SourceSchemaError` - 18 edges

## Surprising Connections (you probably didn't know these)
- `test_download_period_range_raises_explicitly_on_missing_month_without_partial_writes()` --uses--> `ResourceNotFoundError`  [INFERRED]
  tests/test_extract.py → src/extract.py
- `test_convert_mwmed_columns_rejects_missing_column()` --uses--> `SourceSchemaError`  [INFERRED]
  tests/test_transform.py → src/transform.py
- `test_filter_by_state_handles_empty_match_explicitly()` --uses--> `EmptyFilterResultError`  [INFERRED]
  tests/test_transform.py → src/transform.py
- `test_preserve_operational_identifiers_rejects_null_or_blank_ons_id()` --uses--> `IdentifierNormalizationError`  [INFERRED]
  tests/test_transform.py → src/transform.py
- `test_rejects_changed_or_duplicated_source_schema()` --uses--> `SourceSchemaError`  [INFERRED]
  tests/test_transform.py → src/transform.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Governança de Qualidade e Metodologia do Repositório** — agents_integridade_metodologica, agents_governanca_graphify, agents_contrato_frontend_sem_acesso_direto_sqlite, agents_protocolo_implementacao_autorevisao [EXTRACTED 1.00]
- **Definição Metodológica e Escopo do MVP** — plano_escopo_mvp, plano_fontes_oficiais_ons_aneel, plano_metricas_gnra_mvp, plano_riscos_decisoes [INFERRED 0.95]
- **Arquitetura e Execução do Pipeline de Dados** — plano_arquitetura_pipeline, plano_modelo_dados_sqlite, plano_contratos_execucao_cli, plano_roadmap_fases [INFERRED 0.95]

## Communities (24 total, 8 thin omitted)

### Community 0 - "Testes Sintéticos CKAN, Download e CLI"
Cohesion: 0.07
Nodes (47): build_metadata_filepath(), build_raw_filepath(), download_monthly_resource(), download_period_range(), download_resource_file(), _fetch_ckan_resources(), main(), ResourceDownloadError (+39 more)

### Community 1 - "Documentação, Metodologia e Plano"
Cohesion: 0.13
Nodes (15): SourceSchemaError, check_and_resolve_key_duplicates(), DataQualityError, DuplicateKeyError, DuplicateKeyReport, QualityCheckReport, run_quality_checks(), test_check_duplicates_always_rejects_conflicting_keys_even_in_drop_exact_only() (+7 more)

### Community 2 - "Testes de Estrutura e Referências"
Cohesion: 0.10
Nodes (17): AmbiguousResourceError, discover_resource(), resolve_dataset_id(), ResourceDiscoveryError, ResourceNotFoundError, _validate_dataset(), _validate_timeout(), FakeSession (+9 more)

### Community 3 - "Validação, Metadados e Hash SHA-256"
Cohesion: 0.18
Nodes (17): convert_mwmed_columns(), NumericConversionError, parse_instante_column(), TimestampConversionError, _sample_standardized_dataframe(), test_column_mapping_is_complete_unique_and_reversible(), test_convert_mwmed_columns_preserves_precision_and_nulls_without_rounding(), test_convert_mwmed_columns_rejects_invalid_or_non_finite_strings() (+9 more)

### Community 4 - "Descoberta, Faixa de Meses e CLI CKAN"
Cohesion: 0.14
Nodes (18): Regras para Agentes (AGENTS.md), Chave Operacional Candidata (id_ons + din_instante), Geração Não Realizada Apurada (GNRa), Reconhecimento ONS 2025-01 (Dicionário de Dados), Rotina Operacional ONS RO-AO.BR.13 (Rev. 08), Dicionário de Dados Oficial ONS - Restrição de Operação por Constrained-off de Usinas Eólicas (PDF v1.5), Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS), Registro de Coleta e Hashes dos Dicionários Oficiais ONS (+10 more)

### Community 5 - "Exceções de Extração e Revisão"
Cohesion: 0.10
Nodes (9): ColumnNumericReport, _convert_single_numeric_series(), IdentifierReport, inspect_source_schema(), SourceSchemaReport, StateFilterReport, TimestampConversionReport, validate_source_schema() (+1 more)

### Community 6 - "Transformação, Tipagem e Filtros CSV ONS"
Cohesion: 0.21
Nodes (14): RawCsvReadError, read_raw_ons_csv(), _validate_csv_structure(), _validate_raw_csv_path(), test_accepts_quoted_semicolon_inside_text_field(), test_accepts_utf8_with_bom_without_changing_first_column(), test_reads_confirmed_csv_format_without_early_type_conversion(), test_rejects_changed_or_duplicated_source_schema() (+6 more)

### Community 7 - "Normalização de Metadados CKAN"
Cohesion: 0.13
Nodes (5): build_argument_parser(), compute_file_sha256(), _validate_chunk_size(), _validate_destination(), _validate_output_dir()

### Community 8 - "Validação de Qualidade e Duplicidades (Fase 3)"
Cohesion: 0.20
Nodes (7): build_archived_revision_filepath(), CollectionMetadata, _commit_staged_raw_and_metadata(), _download_discovered_monthly_resource(), read_collection_metadata(), _verify_existing_file_matches_remote_revision(), write_collection_metadata()

### Community 9 - "Interface Web Frontend"
Cohesion: 0.19
Nodes (7): EmptyFilterResultError, filter_by_state(), IdentifierNormalizationError, preserve_operational_identifiers(), standardize_column_names(), test_quality_checks_and_key_uniqueness_on_verified_january_ce_subset(), test_reads_verified_january_source_file()

### Community 10 - "Persistência SQLite (Fase 5)"
Cohesion: 0.15
Nodes (9): build_raw_filename(), iter_year_months(), _validate_format(), _validate_month(), _validate_year(), test_builds_predictable_raw_filename_for_source_and_dataset(), test_iter_year_months_handles_single_month_range_and_year_rollover(), test_iter_year_months_rejects_inverted_range() (+1 more)

### Community 11 - "Pacote Principal src"
Cohesion: 0.22
Nodes (6): _extract_resources(), _validate_collection_metadata_payload(), _validate_download_url(), _validate_revision_history_entry(), _validate_sha256_hex(), _validate_utc_iso_timestamp()

### Community 13 - "Orquestração do Pipeline (Fase 5)"
Cohesion: 0.29
Nodes (4): _matches_resource(), _normalize_resource_metadata(), ResourceMetadata, _select_unique_resource()

### Community 14 - "Esquema SQL"
Cohesion: 0.29
Nodes (3): DownloadResult, MonthlyExtractionReport, RevisionHistoryEntry

### Community 15 - "Comunidade 15"
Cohesion: 0.60
Nodes (4): Descoberta de Recurso CKAN (discover_resource), Download Seguro com Retentativas e Integridade (download_resource_file), Faixa de Meses, Recursos Ausentes e CLI (python -m src.extract), Investigação da API CKAN do ONS

### Community 16 - "Comunidade 16"
Cohesion: 0.33
Nodes (3): _expected_content_length(), _iter_response_chunks(), _stream_response_to_destination()

## Knowledge Gaps
- **4 isolated node(s):** `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS`, `Dependências Python do Projeto (requirements.txt)`, `Chave Operacional Candidata (id_ons + din_instante)`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 127 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `FakeResponse` connect `Testes Sintéticos CKAN, Download e CLI` to `Testes de Estrutura e Referências`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **What connects `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS`, `Dependências Python do Projeto (requirements.txt)` to the rest of the system?**
  _4 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Testes Sintéticos CKAN, Download e CLI` be split into smaller, more focused modules?**
  _Cohesion score 0.07113543091655267 - nodes in this community are weakly interconnected._
- **Why does `ResourceDownloadError` connect `Testes Sintéticos CKAN, Download e CLI` to `Testes de Estrutura e Referências`, `Normalização de Metadados CKAN`, `Validação de Qualidade e Duplicidades (Fase 3)`, `Pacote Principal src`, `Comunidade 16`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Should `Documentação, Metodologia e Plano` be split into smaller, more focused modules?**
  _Cohesion score 0.1310483870967742 - nodes in this community are weakly interconnected._
- **Should `Testes de Estrutura e Referências` be split into smaller, more focused modules?**
  _Cohesion score 0.09852216748768473 - nodes in this community are weakly interconnected._
- **Should `Descoberta, Faixa de Meses e CLI CKAN` be split into smaller, more focused modules?**
  _Cohesion score 0.13538461538461538 - nodes in this community are weakly interconnected._