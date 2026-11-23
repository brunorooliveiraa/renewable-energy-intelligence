# Graph Report - Projeto_eolica  (2026-11-22)

## Corpus Check
- 31 files · ~32,244 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 432 nodes · 1204 edges · 22 communities (13 shown, 9 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 51 edges (avg confidence: 0.93)
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
- Comunidade 20

## God Nodes (most connected - your core abstractions)
1. `FakeResponse` - 32 edges
2. `FakeDownloadResponse` - 31 edges
3. `download_period_range()` - 26 edges
4. `download_monthly_resource()` - 25 edges
5. `download_resource_file()` - 25 edges
6. `parse_instante_column()` - 23 edges
7. `ResourceDownloadError` - 22 edges
8. `ckan_payload()` - 22 edges
9. `SourceSchemaError` - 22 edges
10. `read_raw_ons_csv()` - 22 edges

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

## Communities (22 total, 9 thin omitted)

### Community 0 - "Testes Sintéticos CKAN, Download e CLI"
Cohesion: 0.05
Nodes (47): add_eligibility_flags(), add_energy_and_preserve_gnra(), build_processed_filepath(), build_quality_report_filepath(), ColumnNumericReport, _convert_single_numeric_series(), EligibilityReport, EmptyFilterResultError (+39 more)

### Community 1 - "Documentação, Metodologia e Arquitetura Vercel/Neon"
Cohesion: 0.05
Nodes (33): build_archived_revision_filepath(), CollectionMetadata, _commit_staged_raw_and_metadata(), compute_file_sha256(), _download_discovered_monthly_resource(), DownloadResult, _expected_content_length(), _extract_resources() (+25 more)

### Community 2 - "Testes de Estrutura, API e Referências"
Cohesion: 0.08
Nodes (40): convert_mwmed_columns(), filter_by_state(), parse_instante_column(), SourceSchemaError, TimestampConversionError, check_and_resolve_key_duplicates(), DataQualityError, DuplicateKeyError (+32 more)

### Community 3 - "Validação, Metadados e Hash SHA-256"
Cohesion: 0.08
Nodes (5): health_check(), _is_valid_postgres_url(), test_api_health_reports_database_configuration_without_exposing_secrets(), test_vercel_config_and_runtime_requirements_stay_lightweight(), test_ons_dictionary_json_has_24_unique_fields()

### Community 4 - "Descoberta, Faixa de Meses e CLI CKAN"
Cohesion: 0.14
Nodes (18): Regras para Agentes (AGENTS.md), Chave Operacional Candidata (id_ons + din_instante), Geração Não Realizada Apurada (GNRa), Reconhecimento ONS 2025-01 (Dicionário de Dados), Rotina Operacional ONS RO-AO.BR.13 (Rev. 08), Dicionário de Dados Oficial ONS - Restrição de Operação por Constrained-off de Usinas Eólicas (PDF v1.5), Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS), Registro de Coleta e Hashes dos Dicionários Oficiais ONS (+10 more)

### Community 5 - "Exceções de Extração e Revisão"
Cohesion: 0.15
Nodes (14): AmbiguousResourceError, discover_resource(), ResourceDiscoveryError, ResourceNotFoundError, ckan_payload(), FakeResponse, FakeSession, test_discovers_unique_resource_and_returns_normalized_metadata() (+6 more)

### Community 6 - "Transformação, Tipagem e Filtros CSV ONS"
Cohesion: 0.14
Nodes (8): download_period_range(), _fetch_ckan_resources(), main(), _validate_format(), _validate_max_attempts(), _validate_overwrite(), _validate_timeout(), test_download_period_range_rejects_end_year_without_end_month()

### Community 7 - "Normalização de Metadados CKAN"
Cohesion: 0.18
Nodes (10): build_raw_filename(), build_raw_filepath(), resolve_dataset_id(), _validate_dataset(), test_builds_predictable_raw_filename_for_source_and_dataset(), test_builds_predictable_raw_filepath_with_default_and_custom_dir(), test_rejects_output_dir_when_it_points_to_existing_file(), test_rejects_unsupported_or_invalid_source() (+2 more)

### Community 8 - "Validação de Qualidade e Duplicidades (Fase 3)"
Cohesion: 0.18
Nodes (8): FakeDownloadResponse, FakeRangeSession, test_cli_main_downloads_single_month_and_prints_summary(), test_cli_main_returns_nonzero_and_prints_error_for_missing_month(), test_download_period_range_does_not_silence_revision_conflict_when_allow_missing_is_true(), test_download_period_range_fetches_catalog_once_and_downloads_multiple_months(), test_download_period_range_raises_explicitly_on_missing_month_without_partial_writes(), test_download_period_range_reports_missing_month_explicitly_when_allowed()

### Community 9 - "API Serverless FastAPI (Vercel)"
Cohesion: 0.19
Nodes (10): build_metadata_filepath(), download_monthly_resource(), ResourceRevisionConflictError, FakeCombinedSession, test_download_monthly_resource_detects_local_file_tampering_against_manifest(), test_download_monthly_resource_detects_remote_ckan_revision_and_blocks_overwrite(), test_download_monthly_resource_rejects_untracked_existing_file_without_overwrite(), test_download_monthly_resource_reuses_existing_file_when_version_and_hash_match() (+2 more)

### Community 10 - "Persistência PostgreSQL Neon (Fase 5)"
Cohesion: 0.32
Nodes (11): download_resource_file(), FakeDownloadSession, test_does_not_retry_permanent_http_404_error(), test_downloads_file_in_chunks_and_computes_sha256(), test_ignores_compressed_content_length_when_content_encoding_is_present(), test_raises_clear_error_after_exhausting_max_attempts(), test_refuses_to_overwrite_existing_file_by_default(), test_rejects_empty_downloaded_file() (+3 more)

### Community 11 - "Interface Web Frontend"
Cohesion: 0.48
Nodes (5): ResourceDownloadError, test_download_monthly_resource_removes_new_csv_if_initial_metadata_write_fails(), fail_metadata_write(), test_download_monthly_resource_rolls_back_csv_if_metadata_write_fails(), fail_metadata_write()

### Community 14 - "Orquestração do Pipeline (Fase 5)"
Cohesion: 0.60
Nodes (4): Descoberta de Recurso CKAN (discover_resource), Download Seguro com Retentativas e Integridade (download_resource_file), Faixa de Meses, Recursos Ausentes e CLI (python -m src.extract), Investigação da API CKAN do ONS

## Knowledge Gaps
- **4 isolated node(s):** `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS`, `Dependências Python do Projeto (requirements.txt)`, `Chave Operacional Candidata (id_ons + din_instante)`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 150 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `FakeDownloadResponse` connect `Validação de Qualidade e Duplicidades (Fase 3)` to `Documentação, Metodologia e Arquitetura Vercel/Neon`, `Normalização de Metadados CKAN`, `API Serverless FastAPI (Vercel)`, `Persistência PostgreSQL Neon (Fase 5)`, `Interface Web Frontend`, `Pacote Principal src`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **What connects `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS`, `Dependências Python do Projeto (requirements.txt)` to the rest of the system?**
  _4 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Testes Sintéticos CKAN, Download e CLI` be split into smaller, more focused modules?**
  _Cohesion score 0.05212716222533895 - nodes in this community are weakly interconnected._
- **Why does `FakeResponse` connect `Exceções de Extração e Revisão` to `Normalização de Metadados CKAN`, `Validação de Qualidade e Duplicidades (Fase 3)`, `API Serverless FastAPI (Vercel)`, `Interface Web Frontend`, `Pacote Principal src`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Should `Documentação, Metodologia e Arquitetura Vercel/Neon` be split into smaller, more focused modules?**
  _Cohesion score 0.05261261261261261 - nodes in this community are weakly interconnected._
- **Why does `ResourceDownloadError` connect `Interface Web Frontend` to `Documentação, Metodologia e Arquitetura Vercel/Neon`, `Exceções de Extração e Revisão`, `Normalização de Metadados CKAN`, `API Serverless FastAPI (Vercel)`, `Persistência PostgreSQL Neon (Fase 5)`, `Pacote Principal src`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Should `Testes de Estrutura, API e Referências` be split into smaller, more focused modules?**
  _Cohesion score 0.07553143374038897 - nodes in this community are weakly interconnected._