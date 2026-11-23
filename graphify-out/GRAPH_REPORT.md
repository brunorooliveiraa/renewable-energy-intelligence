# Graph Report - Projeto_eolica  (2026-11-22)

## Corpus Check
- 17 files · ~28,565 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 397 nodes · 1014 edges · 23 communities (16 shown, 7 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 40 edges (avg confidence: 0.93)
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
- Comunidade 17

## God Nodes (most connected - your core abstractions)
1. `FakeResponse` - 32 edges
2. `FakeDownloadResponse` - 31 edges
3. `download_period_range()` - 26 edges
4. `download_monthly_resource()` - 25 edges
5. `download_resource_file()` - 25 edges
6. `ResourceDownloadError` - 22 edges
7. `ckan_payload()` - 22 edges
8. `discover_resource()` - 20 edges
9. `read_raw_ons_csv()` - 19 edges
10. `_validate_collection_metadata_payload()` - 16 edges

## Surprising Connections (you probably didn't know these)
- `test_compute_file_sha256_and_corrupted_metadata_handling()` --uses--> `ResourceDownloadError`  [INFERRED]
  tests/test_extract.py → src/extract.py
- `test_download_monthly_resource_detects_local_file_tampering_against_manifest()` --uses--> `ResourceRevisionConflictError`  [INFERRED]
  tests/test_extract.py → src/extract.py
- `test_download_monthly_resource_detects_remote_ckan_revision_and_blocks_overwrite()` --uses--> `ResourceRevisionConflictError`  [INFERRED]
  tests/test_extract.py → src/extract.py
- `test_download_monthly_resource_rejects_untracked_existing_file_without_overwrite()` --uses--> `ResourceRevisionConflictError`  [INFERRED]
  tests/test_extract.py → src/extract.py
- `test_download_period_range_does_not_silence_revision_conflict_when_allow_missing_is_true()` --uses--> `ResourceRevisionConflictError`  [INFERRED]
  tests/test_extract.py → src/extract.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Governança de Qualidade, Metodologia e Arquitetura do Repositório** — agents_integridade_metodologica, agents_governanca_graphify, agents_contrato_api_serverless_frontend, agents_protocolo_implementacao_autorevisao [EXTRACTED 1.00]
- **Stack de Produção Gratuita Vercel + FastAPI + Neon PostgreSQL** — docs_arquitetura_vercel_serverless_fastapi_neon, requirements_runtime_vercel_leve, requirements_etl_dependencias_pipeline, plano_modelo_dados_postgresql [INFERRED 0.95]
- **Definição Metodológica e Escopo do MVP** — plano_escopo_mvp, plano_fontes_oficiais_ons_aneel, plano_metricas_gnra_mvp, plano_riscos_decisoes [INFERRED 0.95]

## Communities (23 total, 7 thin omitted)

### Community 0 - "Testes Sintéticos CKAN, Download e CLI"
Cohesion: 0.06
Nodes (47): ColumnNumericReport, convert_mwmed_columns(), _convert_single_numeric_series(), EmptyFilterResultError, filter_by_state(), IdentifierNormalizationError, IdentifierReport, inspect_source_schema() (+39 more)

### Community 1 - "Documentação, Metodologia e Arquitetura Vercel/Neon"
Cohesion: 0.07
Nodes (49): AmbiguousResourceError, build_metadata_filepath(), discover_resource(), download_monthly_resource(), download_resource_file(), ResourceDiscoveryError, ResourceDownloadError, ResourceNotFoundError (+41 more)

### Community 2 - "Testes de Estrutura, API e Referências"
Cohesion: 0.12
Nodes (16): check_and_resolve_key_duplicates(), DataQualityError, DuplicateKeyError, DuplicateKeyReport, QualityCheckReport, run_quality_checks(), test_check_duplicates_always_rejects_conflicting_keys_even_in_drop_exact_only(), test_check_duplicates_handles_exact_duplicates_by_policy() (+8 more)

### Community 3 - "Validação, Metadados e Hash SHA-256"
Cohesion: 0.12
Nodes (20): Regras para Agentes (AGENTS.md), Contrato de Rotas JSON da API FastAPI (/api/*), Arquitetura Serverless Vercel + FastAPI + Neon PostgreSQL, Variáveis de Ambiente PostgreSQL Neon (DATABASE_URL vs DIRECT_DATABASE_URL), Diagnóstico do Ceará e Conciliação Inicial da GNRa (5.692 observações), Contrato de Leitura CSV ONS e Mapeamento Reversível de 24 Colunas, Dicionário e Reconhecimento dos Dados ONS (2025-01), Metodologia, Premissas e Conciliação da GNRa (+12 more)

### Community 4 - "Descoberta, Faixa de Meses e CLI CKAN"
Cohesion: 0.10
Nodes (4): health_check(), test_api_health_reports_database_configuration_without_exposing_secrets(), test_vercel_config_and_runtime_requirements_stay_lightweight(), test_ons_dictionary_json_has_24_unique_fields()

### Community 5 - "Exceções de Extração e Revisão"
Cohesion: 0.20
Nodes (8): build_archived_revision_filepath(), CollectionMetadata, _commit_staged_raw_and_metadata(), _download_discovered_monthly_resource(), read_collection_metadata(), _verify_existing_file_matches_remote_revision(), write_collection_metadata(), test_compute_file_sha256_and_corrupted_metadata_handling()

### Community 6 - "Transformação, Tipagem e Filtros CSV ONS"
Cohesion: 0.14
Nodes (8): download_period_range(), _fetch_ckan_resources(), main(), _validate_max_attempts(), _validate_output_dir(), _validate_overwrite(), _validate_timeout(), test_download_period_range_rejects_end_year_without_end_month()

### Community 7 - "Normalização de Metadados CKAN"
Cohesion: 0.16
Nodes (7): _expected_content_length(), _extract_resources(), _iter_response_chunks(), _stream_response_to_destination(), _validate_revision_history_entry(), _validate_sha256_hex(), _validate_utc_iso_timestamp()

### Community 8 - "Validação de Qualidade e Duplicidades (Fase 3)"
Cohesion: 0.16
Nodes (4): build_argument_parser(), compute_file_sha256(), _validate_chunk_size(), _validate_destination()

### Community 9 - "API Serverless FastAPI (Vercel)"
Cohesion: 0.14
Nodes (10): build_raw_filename(), build_raw_filepath(), resolve_dataset_id(), _validate_dataset(), test_builds_predictable_raw_filename_for_source_and_dataset(), test_builds_predictable_raw_filepath_with_default_and_custom_dir(), test_rejects_output_dir_when_it_points_to_existing_file(), test_rejects_unsupported_or_invalid_source() (+2 more)

### Community 10 - "Persistência PostgreSQL Neon (Fase 5)"
Cohesion: 0.15
Nodes (8): iter_year_months(), _validate_collection_metadata_payload(), _validate_download_url(), _validate_format(), _validate_month(), _validate_year(), test_iter_year_months_handles_single_month_range_and_year_rollover(), test_iter_year_months_rejects_inverted_range()

### Community 11 - "Interface Web Frontend"
Cohesion: 0.29
Nodes (4): _matches_resource(), _normalize_resource_metadata(), ResourceMetadata, _select_unique_resource()

### Community 12 - "Pacote Principal src"
Cohesion: 0.29
Nodes (3): DownloadResult, MonthlyExtractionReport, RevisionHistoryEntry

### Community 13 - "Métricas Analíticas (Fase 4)"
Cohesion: 0.60
Nodes (4): Descoberta de Recurso CKAN (discover_resource), Download Seguro com Retentativas e Integridade (download_resource_file), Faixa de Meses, Recursos Ausentes e CLI (python -m src.extract), Investigação da API CKAN do ONS

### Community 14 - "Orquestração do Pipeline (Fase 5)"
Cohesion: 0.50
Nodes (3): rewrites, $schema, version

### Community 15 - "Esquema SQL PostgreSQL"
Cohesion: 0.67
Nodes (3): Dicionário de Dados Oficial ONS - Restrição de Operação por Constrained-off de Usinas Eólicas (PDF v1.5), Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS), Registro de Coleta e Hashes dos Dicionários Oficiais ONS

## Knowledge Gaps
- **7 isolated node(s):** `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS`, `Interface Web Inicial (frontend/index.html)`, `Variáveis de Ambiente PostgreSQL Neon (DATABASE_URL vs DIRECT_DATABASE_URL)`, `Contrato de Leitura CSV ONS e Mapeamento Reversível de 24 Colunas` (+2 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 146 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `FakeDownloadResponse` connect `Documentação, Metodologia e Arquitetura Vercel/Neon` to `Normalização de Metadados CKAN`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **What connects `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS`, `Interface Web Inicial (frontend/index.html)` to the rest of the system?**
  _7 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Testes Sintéticos CKAN, Download e CLI` be split into smaller, more focused modules?**
  _Cohesion score 0.05982905982905983 - nodes in this community are weakly interconnected._
- **Why does `ResourceDownloadError` connect `Documentação, Metodologia e Arquitetura Vercel/Neon` to `Validação de Qualidade e Duplicidades (Fase 3)`, `Persistência PostgreSQL Neon (Fase 5)`, `Exceções de Extração e Revisão`, `Normalização de Metadados CKAN`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Should `Documentação, Metodologia e Arquitetura Vercel/Neon` be split into smaller, more focused modules?**
  _Cohesion score 0.07217321571772253 - nodes in this community are weakly interconnected._
- **Should `Testes de Estrutura, API e Referências` be split into smaller, more focused modules?**
  _Cohesion score 0.12310606060606061 - nodes in this community are weakly interconnected._
- **Should `Validação, Metadados e Hash SHA-256` be split into smaller, more focused modules?**
  _Cohesion score 0.12 - nodes in this community are weakly interconnected._