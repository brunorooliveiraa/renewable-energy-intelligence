# Graph Report - Projeto_eolica  (2026-11-23)

## Corpus Check
- 97 files · ~206,554 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 17 file(s) not represented in the graph (top: (none) 8, .toml 5, .cmd 1)

## Summary
- 2102 nodes · 5055 edges · 111 communities (97 shown, 14 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 359 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e03e4fb1`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Testes Sintéticos CKAN, Download e CLI
- test_database.py
- metrics.py
- Validação, Metadados e Hash SHA-256
- transform.py
- Exceções de Extração e Revisão
- Transformação, Tipagem e Filtros CSV ONS
- FakeCursor
- FakeDownloadResponse
- extract.py
- live-browser.js
- Any
- transform_monthly_dataset
- json
- Orquestração do Pipeline (Fase 5)
- filter_by_state
- Comunidade 16
- test_api.py
- SourceSchemaError
- FakeLoadCursor
- showToast
- Comunidade 21
- run_monthly_pipeline
- Comunidade 23
- app.js
- queries.py
- database.py
- pandas
- test_database.py
- _make_phase3_synthetic_df
- iter_year_months
- Dependências Python do Projeto (requirements.txt)
- validate_source_schema
- frontend_e2e.test.mjs
- el
- Session
- modern-screenshot.umd.js
- index.py
- preserve_operational_identifiers
- handleGo
- build_argument_parser
- actOnAgentTarget
- renderDesignVisual
- captureElementToBlob
- initPageChat
- hasTextRows
- actOnAgentTarget
- new-work.md
- live.md
- resolveLiveInjectionAnchor
- adapt.md
- setLiveState
- createLiveBrowserDomHelpers
- animate.md
- onboard.md
- The Toolkit
- SKILL.md
- createLiveBrowserSessionState
- generate_basic_phase4_charts
- Path
- Diagnostic Scan
- audit.native.md
- Handle `generate`
- new-work-world.md
- New visual work
- new-work-comp.md
- optimize.md
- Impeccable Asset Producer
- Scan mode (approach C: auto-extract, then confirm descriptive language)
- critique.md
- Simplify the Design
- Hardening Dimensions
- clarify.md
- Generate Combined Critique Report
- Nielsen's 10 Heuristics
- document.md
- polish.md
- quieter.md
- resumeSession
- Cognitive Load Assessment
- Init flow
- Common Cognitive Load Violations
- iOS platform
- Operate mode depth (and Read notes)
- Shape
- Android platform
- colorize.md
- Persona-Based Design Testing
- Extract Flow
- Impeccable Finish Reviewer
- Impeccable Manual Edit Applier
- live-browser-ignores.js
- ApiDatabaseConfigError
- build_raw_filepath
- bolder.md
- $impeccable hooks
- scopeCssBlock
- interface
- Impeccable Documenter
- mountSvelteComponentVariant
- Scoring the report
- test_frontend_e2e.py
- ApiDatabaseQueryError
- CREDITS.md
- sanitize_postgres_error
- doctor.md
- adapt.native.md

## God Nodes (most connected - your core abstractions)
1. `connectSSE()` - 38 edges
2. `setLiveState()` - 34 edges
3. `showToast()` - 33 edges
4. `resumeSession()` - 33 edges
5. `FakeResponse` - 32 edges
6. `FakeDownloadResponse` - 31 edges
7. `initGlobalBar()` - 30 edges
8. `el()` - 29 edges
9. `buildInsertConfigureRow()` - 28 edges
10. `handleKeyDown()` - 28 edges

## Surprising Connections (you probably didn't know these)
- `Step 2: Act by severity` --references--> `init()`  [INFERRED]
  .agents/skills/impeccable/reference/doctor.md → .agents/skills/impeccable/scripts/live-browser.js
- `What this owns, and what it does not` --references--> `init()`  [INFERRED]
  .agents/skills/impeccable/reference/doctor.md → .agents/skills/impeccable/scripts/live-browser.js
- `Start` --references--> `init()`  [INFERRED]
  .agents/skills/impeccable/reference/live.md → .agents/skills/impeccable/scripts/live-browser.js
- `Commands` --references--> `init()`  [INFERRED]
  .agents/skills/impeccable/SKILL.md → .agents/skills/impeccable/scripts/live-browser.js
- `generate_basic_phase4_charts()` --generates--> `Grafico SVG: Geracao Verificada Diaria (MWh)`  [EXTRACTED]
  src/metrics.py → docs/imagens/fase4/geracao_diaria_mwh.svg

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Governança de Qualidade e Metodologia do Repositório** — agents_integridade_metodologica, agents_governanca_graphify, agents_contrato_frontend_sem_acesso_direto_sqlite, agents_protocolo_implementacao_autorevisao [EXTRACTED 1.00]
- **Definição Metodológica e Escopo do MVP** — plano_escopo_mvp, plano_fontes_oficiais_ons_aneel, plano_metricas_gnra_mvp, plano_riscos_decisoes [INFERRED 0.95]
- **Arquitetura e Execução do Pipeline de Dados** — plano_arquitetura_pipeline, plano_modelo_dados_sqlite, plano_contratos_execucao_cli, plano_roadmap_fases [INFERRED 0.95]

## Communities (111 total, 14 thin omitted)

### Community 0 - "Testes Sintéticos CKAN, Download e CLI"
Cohesion: 0.13
Nodes (21): discover_resource(), ResourceRevisionConflictError, ckan_payload(), FakeCombinedSession, FakeResponse, FakeSession, test_cli_main_downloads_single_month_and_prints_summary(), test_cli_main_returns_nonzero_and_prints_error_for_missing_month() (+13 more)

### Community 1 - "test_database.py"
Cohesion: 0.11
Nodes (20): apply_schema(), check_database_connection(), DatabaseConfigError, DatabaseSchemaError, load_dotenv_file(), load_schema_sql(), main(), mask_postgres_url() (+12 more)

### Community 2 - "metrics.py"
Cohesion: 0.15
Nodes (8): CoverageSummary, GnraReconciliationReport, IntervalCountsSummary, _pct(), PeakRestrictionsSummary, ReasonsAndOriginsSummary, summarize_coverage(), test_summarize_coverage_handles_reference_gaps_and_empty_dataframe()

### Community 3 - "Validação, Metadados e Hash SHA-256"
Cohesion: 0.11
Nodes (16): check_and_resolve_key_duplicates(), DataQualityError, DuplicateKeyError, DuplicateKeyReport, QualityCheckReport, run_quality_checks(), test_check_duplicates_always_rejects_conflicting_keys_even_in_drop_exact_only(), test_check_duplicates_handles_exact_duplicates_by_policy() (+8 more)

### Community 4 - "transform.py"
Cohesion: 0.11
Nodes (11): add_energy_and_preserve_gnra(), ColumnNumericReport, _convert_single_numeric_series(), EligibilityReport, EnergyCalculationReport, GranularityReport, IdentifierReport, NumericConversionError (+3 more)

### Community 5 - "Exceções de Extração e Revisão"
Cohesion: 0.15
Nodes (15): GranularityValidationError, parse_instante_column(), TimestampConversionError, validate_granularity_and_add_duration(), _sample_standardized_dataframe(), test_add_energy_and_preserve_gnra_computes_50mwh_for_100mwmed_half_hour(), test_convert_mwmed_columns_preserves_precision_and_nulls_without_rounding(), test_convert_mwmed_columns_rejects_invalid_or_non_finite_strings() (+7 more)

### Community 6 - "Transformação, Tipagem e Filtros CSV ONS"
Cohesion: 0.09
Nodes (25): Regras para Agentes (AGENTS.md), Achados Explorat?rios do MVP ? Cear? (Janeiro/2025), 1. Por que separar o ETL da API serverless, 2. Topologia do sistema, 3. Contrato de rotas planejado para a API (`api/index.py`), 4. Variáveis de ambiente e segurança, 5. Como rodar localmente antes do deploy, Arquitetura de Servidor Gratuito — Vercel + FastAPI + Neon PostgreSQL (+17 more)

### Community 7 - "FakeCursor"
Cohesion: 0.11
Nodes (9): DatabaseConnectionError, FakeConnection, FakeCursor, test_apply_schema_is_idempotent_and_masks_errors(), failing_connect(), fake_connect(), test_check_database_connection_handles_success_and_db_errors(), empty_connect() (+1 more)

### Community 8 - "FakeDownloadResponse"
Cohesion: 0.11
Nodes (11): download_period_range(), _validate_max_attempts(), _validate_overwrite(), _validate_timeout(), FakeDownloadResponse, FakeRangeSession, test_download_period_range_does_not_silence_revision_conflict_when_allow_missing_is_true(), test_download_period_range_fetches_catalog_once_and_downloads_multiple_months() (+3 more)

### Community 9 - "extract.py"
Cohesion: 0.07
Nodes (29): build_archived_revision_filepath(), build_metadata_filepath(), CollectionMetadata, _commit_staged_raw_and_metadata(), compute_file_sha256(), _download_discovered_monthly_resource(), download_monthly_resource(), DownloadResult (+21 more)

### Community 10 - "live-browser.js"
Cohesion: 0.04
Nodes (98): addManualContextText(), agentHasWorkInFlight(), applyEditing(), applyPlaceholderSizingStyles(), bindEditBadgeProxy(), buildLocatorForLeaf(), buildSteerQueueHint(), canRestoreManualEditElement() (+90 more)

### Community 11 - "Any"
Cohesion: 0.12
Nodes (9): AmbiguousResourceError, _extract_resources(), _fetch_ckan_resources(), _iter_response_chunks(), _matches_resource(), _normalize_resource_metadata(), ResourceDiscoveryError, ResourceNotFoundError (+1 more)

### Community 12 - "transform_monthly_dataset"
Cohesion: 0.14
Nodes (10): build_processed_filepath(), build_quality_report_filepath(), transform_monthly_dataset(), TransformationQualityReport, _validate_raw_csv_path(), write_processed_parquet(), write_quality_report(), test_atomic_writers_clean_part_files_on_io_failure() (+2 more)

### Community 14 - "Orquestração do Pipeline (Fase 5)"
Cohesion: 0.26
Nodes (14): RawCsvReadError, read_raw_ons_csv(), test_accepts_quoted_semicolon_inside_text_field(), test_accepts_utf8_with_bom_without_changing_first_column(), test_reads_confirmed_csv_format_without_early_type_conversion(), test_rejects_changed_or_duplicated_source_schema(), test_rejects_comma_in_numeric_source_field(), test_rejects_missing_empty_and_non_utf8_files() (+6 more)

### Community 15 - "filter_by_state"
Cohesion: 0.33
Nodes (4): EmptyFilterResultError, filter_by_state(), test_filter_by_state_handles_empty_match_explicitly(), test_filter_by_state_selects_ce_and_reports_excluded_and_nulls()

### Community 16 - "Comunidade 16"
Cohesion: 0.27
Nodes (14): dim_empreendimentos, etl_execucoes, fact_restricoes, idx_dim_empreendimentos_estado, idx_etl_execucoes_periodo, idx_etl_execucoes_status, idx_fact_restricoes_estado_instante, idx_fact_restricoes_estado_razao_origem (+6 more)

### Community 17 - "test_api.py"
Cohesion: 0.11
Nodes (7): FakeQueryConnection, FakeQueryCursor, _patch_fake_db(), test_endpoints_return_422_for_invalid_filters_and_503_without_leaking_secrets(), test_enterprises_query_applies_exact_ons_id_filter(), test_overview_endpoint_returns_metrics_and_handles_empty_filter_without_fake_zero(), test_timeseries_enterprises_reasons_and_quality_endpoints()

### Community 18 - "SourceSchemaError"
Cohesion: 0.20
Nodes (9): add_eligibility_flags(), convert_mwmed_columns(), SourceSchemaError, standardize_column_names(), test_quality_checks_and_key_uniqueness_on_verified_january_ce_subset(), test_add_eligibility_flags_classifies_all_indicators_without_dropping_rows(), test_add_eligibility_flags_rejects_untyped_or_duplicate_columns(), test_convert_mwmed_columns_rejects_missing_column() (+1 more)

### Community 20 - "showToast"
Cohesion: 0.10
Nodes (38): abandonForeignSession(), abandonSupersededGo(), abortSvelteComponentInjection(), cleanup(), cleanupAcceptedSession(), clearHandled(), clearMountErrorCard(), clearScrollY() (+30 more)

### Community 21 - "Comunidade 21"
Cohesion: 0.60
Nodes (4): Descoberta de Recurso CKAN (discover_resource), Download Seguro com Retentativas e Integridade (download_resource_file), Faixa de Meses, Recursos Ausentes e CLI (python -m src.extract), Investigação da API CKAN do ONS

### Community 22 - "run_monthly_pipeline"
Cohesion: 0.09
Nodes (11): build_argument_parser(), build_argument_parser(), main(), PipelineRunReport, run_monthly_pipeline(), _validate_pipeline_args(), test_pipeline_cli_succeeds_with_skip_load_and_fails_cleanly_on_missing_file(), test_run_monthly_pipeline_rejects_invalid_arguments_and_missing_csv() (+3 more)

### Community 23 - "Comunidade 23"
Cohesion: 0.50
Nodes (3): rewrites, $schema, version

### Community 25 - "app.js"
Cohesion: 0.22
Nodes (28): apiGet(), bindEvents(), buildQueryString(), downloadCsv(), escapeHtml(), exportEnterprisesCsv(), exportQualityCsv(), exportReasonsCsv() (+20 more)

### Community 27 - "queries.py"
Cohesion: 0.17
Nodes (15): _build_fact_where_clause(), _escape_like_pattern(), mask_postgres_url(), query_enterprises(), query_overview(), _exec(), query_quality(), query_reasons() (+7 more)

### Community 28 - "database.py"
Cohesion: 0.16
Nodes (13): DatabaseLoadReport, _is_missing_value(), load_processed_parquet(), _month_period_bounds(), _prepare_load_rows(), SchemaApplyReport, _to_optional_float(), _to_optional_str() (+5 more)

### Community 29 - "pandas"
Cohesion: 0.13
Nodes (13): build_enterprise_ranking(), build_generation_series(), identify_peak_restriction_periods(), reconcile_gnra_values(), _sum_preserving_na(), summarize_reasons_and_origins(), _aggregate_dimension(), _validate_metrics_dataframe() (+5 more)

### Community 30 - "test_database.py"
Cohesion: 0.12
Nodes (13): DatabaseLoadError, load_dataframe_to_postgres(), _sanitize_postgres_error_message(), FakeLoadConnection, FakeLoadCursor, _synthetic_processed_df(), test_dim_empreendimentos_does_not_regress_attributes_on_out_of_order_historical_load(), test_load_dataframe_is_idempotent_and_removes_obsolete_rows_on_ons_revision() (+5 more)

### Community 31 - "_make_phase3_synthetic_df"
Cohesion: 0.22
Nodes (7): summarize_interval_counts(), _make_phase3_synthetic_df(), test_generate_basic_phase4_charts_creates_valid_svg_files(), test_generate_basic_phase4_charts_distinguishes_missing_zero_positive_and_negative(), test_metrics_reject_invalid_granularity_tolerance_and_schema(), test_reconcile_gnra_exposes_negative_diff_and_divergences_without_summing_mwh(), test_summarize_interval_counts_preserves_unrestricted_rows_and_totals()

### Community 32 - "iter_year_months"
Cohesion: 0.50
Nodes (3): iter_year_months(), test_iter_year_months_handles_single_month_range_and_year_rollover(), test_iter_year_months_rejects_inverted_range()

### Community 34 - "validate_source_schema"
Cohesion: 0.22
Nodes (5): inspect_source_schema(), SourceSchemaReport, _validate_csv_structure(), validate_source_schema(), test_records_column_order_without_rejecting_a_safe_reordering()

### Community 35 - "frontend_e2e.test.mjs"
Cohesion: 0.09
Nodes (14): CdpClient, createMockServer(), enterpriseItem(), FRONTEND_ROOT, jsonResponse(), overviewPayload(), PROJECT_ROOT, qualityPayload() (+6 more)

### Community 36 - "el"
Cohesion: 0.07
Nodes (58): actionLabel(), applyConfigureBarChrome(), bindConfigureCountPillTooltip(), bindConfigureInlineControlHover(), bindConfigureModifierPillHover(), buildConfigureActionControl(), buildConfigureCountControl(), buildConfigureRow() (+50 more)

### Community 38 - "modern-screenshot.umd.js"
Cohesion: 0.09
Nodes (53): ae(), be(), bt(), Ce(), Ct(), de(), dt(), _e() (+45 more)

### Community 39 - "index.py"
Cohesion: 0.18
Nodes (7): _execute_endpoint(), get_enterprises(), get_overview(), get_quality(), get_reasons(), get_timeseries(), health_check()

### Community 40 - "preserve_operational_identifiers"
Cohesion: 0.40
Nodes (4): IdentifierNormalizationError, preserve_operational_identifiers(), test_preserve_operational_identifiers_keeps_string_dtype_and_dash_literal(), test_preserve_operational_identifiers_rejects_null_or_blank_ons_id()

### Community 41 - "handleGo"
Cohesion: 0.11
Nodes (30): applyPlaceholderDimensions(), beginEditPin(), buildAnnotationsForCapture(), buildInsertPlaceholderSnapshotFromDom(), buildPickedAnchorSnapshot(), buildPinElement(), cancelEditingPin(), captureAndEmit() (+22 more)

### Community 43 - "actOnAgentTarget"
Cohesion: 0.20
Nodes (23): fetchPendingCount(), handleManualEditActivity(), manualApplyLoadingText(), manualEditEventForCurrentPage(), numberOrNull(), onPendingKeepFixingClick(), onPendingPillClick(), onPendingRollbackClick() (+15 more)

### Community 44 - "renderDesignVisual"
Cohesion: 0.07
Nodes (41): buildCollapsible(), buildColorModels(), buildDesignHeader(), buildListHtml(), buildRadiiModels(), buildTypographyModels(), copyToClipboard(), cssSafe() (+33 more)

### Community 45 - "captureElementToBlob"
Cohesion: 0.12
Nodes (22): absolutizeUrls(), averageRgb01(), bufferToBase64(), captureChromeNodes(), captureElementFromRenderedAncestor(), captureElementToBlob(), collectFontCssText(), collectFontFaces() (+14 more)

### Community 46 - "initPageChat"
Cohesion: 0.10
Nodes (45): applyGlobalBarLabelState(), armPageChatForTyping(), attachSteerFocusDebug(), attachSteerFocusGuard(), buildSteerProcessingDots(), clearSteerAwaitTimer(), collapsePageChat(), expandPageChat() (+37 more)

### Community 48 - "actOnAgentTarget"
Cohesion: 0.19
Nodes (22): actOnAgentTarget(), agentTargetBusyReason(), agentTargetOverlayGone(), agentTargetTaken(), buildPlaceholderResizeHandles(), claimAgentTarget(), claimAndActOnAgentTarget(), cursorForPlaceholderEdge() (+14 more)

### Community 49 - "new-work.md"
Cohesion: 0.12
Nodes (15): Craft (deprecated alias), Apply, Live-mode signature params, Set the spatial thesis, Two isolated assessments, Verify, Visitor mode, Apply (+7 more)

### Community 50 - "live.md"
Cohesion: 0.07
Nodes (26): Step 1: Parse the request, Step 2: Reuse the page, then start, Step 3: Generate, Step 4: Accept and close, Cleanup, Exit, First-time setup, Handle `accept` (+18 more)

### Community 51 - "resolveLiveInjectionAnchor"
Cohesion: 0.16
Nodes (19): buildSvelteExpressionTextMap(), buildSveltePropValuesFromLiveElement(), buildSveltePropValuesV2(), cloneWithoutElements(), collectTextNodes(), collectVisibleTexts(), cssEscapeIdent(), elementMatchesOriginalMarkup() (+11 more)

### Community 52 - "adapt.md"
Cohesion: 0.08
Nodes (25): Assess Adaptation Challenge, Breakpoints: Content-Driven, Content Adaptation, Desktop Adaptation (Mobile → Desktop), Detect Input Method, Not Just Screen Size, Email Adaptation (Web → Email), Implement Adaptations, Layout Adaptation Patterns (+17 more)

### Community 53 - "setLiveState"
Cohesion: 0.08
Nodes (70): agentStatusText(), applyLiveBarPreference(), barPaletteForTheme(), beginNewLiveConfiguration(), brandMarkSvg(), cancelEditing(), cancelEditingToPicking(), cancelInsertConfigure() (+62 more)

### Community 54 - "createLiveBrowserDomHelpers"
Cohesion: 0.16
Nodes (15): createLiveBrowserDomHelpers(), activeElementDeep(), cloneWithoutChrome(), copyTextViaSelection(), cssId(), liveUiRoot(), makeFrozenAnchor(), raiseHitModal() (+7 more)

### Community 55 - "animate.md"
Cohesion: 0.09
Nodes (20): Accessibility and control, Choose material by meaning, Find the job, Hover, Implement to the runtime, Set the motion thesis, Timing and easing, Verify (+12 more)

### Community 56 - "onboard.md"
Cohesion: 0.09
Nodes (22): Assess Onboarding Needs, Context Over Ceremony, Contextual Help, Design Onboarding Experiences, Documentation & Help, Empty State Design, Feature Discovery & Adoption, Guided Tours & Walkthroughs (+14 more)

### Community 57 - "The Toolkit"
Cohesion: 0.10
Nodes (20): Animate complex properties, Assess What "Extraordinary" Means Here, For data-heavy interfaces, For functional UI, For performance-critical UI, For visual/marketing surfaces, Implement with Discipline, Interact with the device (+12 more)

### Community 58 - "SKILL.md"
Cohesion: 0.11
Nodes (14): Craft floor, Refuse, Verify, $impeccable foundations, What "done" means, With an id: fix that one item, Without an argument: the roadmap, Command guidance (+6 more)

### Community 59 - "createLiveBrowserSessionState"
Cohesion: 0.19
Nodes (17): createLiveBrowserSessionState(), clearHandled(), clearScrollY(), clearSession(), isHandled(), loadSession(), markHandled(), nextCheckpointRevision() (+9 more)

### Community 60 - "generate_basic_phase4_charts"
Cohesion: 0.22
Nodes (5): Grafico SVG: Geracao Verificada Diaria (MWh), Grafico SVG: Distribuicao Horaria das Restricoes, Grafico SVG: Intervalos Restritos por Razao Oficial, generate_basic_phase4_charts(), _svg_bar_chart()

### Community 61 - "Path"
Cohesion: 0.21
Nodes (17): download_resource_file(), ResourceDownloadError, FakeDownloadSession, test_does_not_retry_permanent_http_404_error(), test_download_monthly_resource_removes_new_csv_if_initial_metadata_write_fails(), fail_metadata_write(), test_download_monthly_resource_rolls_back_csv_if_metadata_write_fails(), fail_metadata_write() (+9 more)

### Community 62 - "Diagnostic Scan"
Cohesion: 0.33
Nodes (6): 1. Accessibility (A11y), 2. Performance, 3. Theming, 4. Responsive Design, 5. Implementation Integrity (CRITICAL), Diagnostic Scan

### Community 63 - "audit.native.md"
Cohesion: 0.08
Nodes (24): Audit Health Score, Detailed Findings by Severity, Executive Summary, Generate Report, Implementation Integrity Verdict, 1. Accessibility (VoiceOver / TalkBack), 2. Performance, 3. Appearance & Theming (+16 more)

### Community 64 - "Handle `generate`"
Cohesion: 0.12
Nodes (16): 1. Read the screenshot (if present), 2. Wrap the element, 3. Load the action's reference, 4. Plan three variants: identity first, then mode, then axes, 5. Apply the freeform prompt (if present), 6. Deliver variants, 7. Parameters (composition-sized, 0-4 per variant), 8. Signal done (+8 more)

### Community 65 - "new-work-world.md"
Cohesion: 0.13
Nodes (11): Comps, Directions, Operate, Comps, Directions, Persuade and Experience, Comps, Directions (+3 more)

### Community 66 - "New visual work"
Cohesion: 0.14
Nodes (14): 1. Decide what is already true, 2. Ask what will change the work, 3. Choose the right amount of invention, 4. Commit the world, 5. Record the decision, 6. Build with full commitment, 7. Inspect and finish, Both paths (+6 more)

### Community 67 - "new-work-comp.md"
Cohesion: 0.14
Nodes (11): Comp-led: the comp is a measured contract, New visual work: the comp-led build, Containment, Painted material, Region map, What varies independently, After approval: the comp becomes a spec, Generate three compositional options (+3 more)

### Community 68 - "optimize.md"
Cohesion: 0.14
Nodes (13): Animation Performance, Assess Performance Issues, Core Web Vitals Optimization, Cumulative Layout Shift (CLS < 0.1), Interaction to Next Paint (INP < 200ms), Largest Contentful Paint (LCP < 2.5s), Loading Performance, Network Optimization (+5 more)

### Community 69 - "Impeccable Asset Producer"
Cohesion: 0.15
Nodes (11): Act on the receipt, Assemble and review, Plan and asset review, Plan, capture, serve, Core Rule, Decision Comps, Impeccable Asset Producer, Input Contract (+3 more)

### Community 70 - "Scan mode (approach C: auto-extract, then confirm descriptive language)"
Cohesion: 0.15
Nodes (13): Component translation rules, Narrative mapping, Scan mode (approach C: auto-extract, then confirm descriptive language), Schema, Step 1: Find the design assets, Step 2: Auto-extract what can be auto-extracted, Step 2b: Stage the frontmatter, Step 3: Ask the user for qualitative language (+5 more)

### Community 71 - "critique.md"
Cohesion: 0.17
Nodes (11): Action Summary, Ask the User, Assessment A: Design Review, Assessment B: Detector + Browser Evidence, Assessment Orchestration, Deliver the Report, Hard Invariants, Persist the Snapshot (+3 more)

### Community 72 - "Simplify the Design"
Cohesion: 0.17
Nodes (11): Assess Current State, Code Simplification, Content Simplification, Document Removed Complexity, Information Architecture, Interaction Simplification, Layout Simplification, Plan Simplification (+3 more)

### Community 73 - "Hardening Dimensions"
Cohesion: 0.17
Nodes (11): Accessibility Resilience, Assess Hardening Needs, Edge Cases & Boundary Conditions, Error Handling, Hardening Dimensions, Input Validation & Sanitization, Internationalization (i18n), Performance Resilience (+3 more)

### Community 74 - "clarify.md"
Cohesion: 0.18
Nodes (10): Actions and navigation, Audit the language, Errors and permissions, Forms, Help and instructional text, Loading, empty, and success states, Rewrite by function, Set the message hierarchy (+2 more)

### Community 75 - "Generate Combined Critique Report"
Cohesion: 0.18
Nodes (11): Design Health Score, Design Specificity Verdict, Generate Combined Critique Report, Minor Observations, Overall Impression, Persona Red Flags, Priority Issues, Questions to Consider (+3 more)

### Community 76 - "Nielsen's 10 Heuristics"
Cohesion: 0.18
Nodes (11): 10. Help and Documentation, 1. Visibility of System Status, 2. Match Between System and Real World, 3. User Control and Freedom, 4. Consistency and Standards, 5. Error Prevention, 6. Recognition Rather Than Recall, 7. Flexibility and Efficiency of Use (+3 more)

### Community 77 - "document.md"
Cohesion: 0.18
Nodes (10): Pitfalls, Seed mode, Step 1: Route through new-work's workshop, Step 2: Write seed DESIGN.md, Step 3: Confirm, Style guidelines, The frontmatter: token schema, The markdown body: eight sections (canonical order) (+2 more)

### Community 78 - "polish.md"
Cohesion: 0.18
Nodes (10): 1. Establish the system, 2. Gather the evidence, 3. Triage, 4. Polish the whole path, 5. Verify and finish, Color, imagery, and icons, Content and code, Flow and hierarchy (+2 more)

### Community 79 - "quieter.md"
Cohesion: 0.18
Nodes (10): Assess Current State, Color Refinement, Composition Refinement, Motion Reduction, Plan Refinement, Refine the Design, Simplification, Verify Quality (+2 more)

### Community 81 - "resumeSession"
Cohesion: 0.06
Nodes (87): applyParamDefaults(), applyParamValue(), applySavedParamValues(), applySavedSessionMeta(), buildParamsPanel(), checkpointPayload(), clampVariantIndex(), closedClipPath() (+79 more)

### Community 82 - "Cognitive Load Assessment"
Cohesion: 0.20
Nodes (9): Cognitive Load Assessment, Cognitive Load Checklist, Critique rubric, Extraneous Load: Bad Design, Germane Load: Learning Effort, Heuristics Scoring Guide, Intrinsic Load: The Task Itself, The Working Memory Rule (+1 more)

### Community 83 - "Init flow"
Cohesion: 0.20
Nodes (10): Completion gate, Init flow, Step 1: Load current state, Step 2: Explore the project, Step 3: Interview for product truth, Step 4: Write PRODUCT.md, Step 5: Record workflow defaults, Step 6: Wrap up or resume (+2 more)

### Community 84 - "Common Cognitive Load Violations"
Cohesion: 0.22
Nodes (9): 1. The Wall of Options, 2. The Memory Bridge, 3. The Hidden Navigation, 4. The Jargon Barrier, 5. The Visual Noise Floor, 6. The Inconsistent Pattern, 7. The Multi-Task Demand, 8. The Context Switch (+1 more)

### Community 85 - "iOS platform"
Cohesion: 0.22
Nodes (9): Color & materials, Components & controls, iOS platform, Layout & structure, Motion, The iOS slop test, Touch targets, Typography (+1 more)

### Community 86 - "Operate mode depth (and Read notes)"
Cohesion: 0.22
Nodes (9): Color, Components, Layout, Motion, Operate mode depth (and Read notes), Product constraints, Product permissions, The product slop test (+1 more)

### Community 87 - "Shape"
Cohesion: 0.22
Nodes (8): Cadence, Confirm and stop, Phase 1: Discovery interview, Phase 2: Resolve the design direction, Phase 3: Write the brief, Round 1: purpose, people, and outcome, Round 2: material, behavior, and boundaries, Shape

### Community 88 - "Android platform"
Cohesion: 0.25
Nodes (8): Android platform, Color & theming, Components & motion, Layout & structure, The Android slop test, Touch targets, Typography, Verifying the build

### Community 89 - "colorize.md"
Cohesion: 0.25
Nodes (7): Apply at system scale, Audit before choosing, Choose a strategy, Contrast and perception, Live-mode signature params, Verify, Visitor mode

### Community 90 - "Persona-Based Design Testing"
Cohesion: 0.25
Nodes (8): 1. Impatient Power User: "Alex", 2. Confused First-Timer: "Jordan", 3. Accessibility-Dependent User: "Sam", 4. Deliberate Stress Tester: "Riley", 5. Distracted Mobile User: "Casey", Persona-Based Design Testing, Project-Specific Personas, Selecting Personas

### Community 91 - "Extract Flow"
Cohesion: 0.25
Nodes (7): Extract Flow, Step 1: Discover the Design System, Step 2: Identify Patterns, Step 3: Plan Extraction, Step 4: Extract & Enrich, Step 5: Migrate, Step 6: Document

### Community 92 - "Impeccable Finish Reviewer"
Cohesion: 0.29
Nodes (6): Checks, in order, Disposition, Impeccable Finish Reviewer, Input Contract, Output Contract, Verdict Pass

### Community 93 - "Impeccable Manual Edit Applier"
Cohesion: 0.29
Nodes (6): Checks, Entry Atomicity, Impeccable Manual Edit Applier, Input Contract, Output Contract, Workflow

### Community 94 - "live-browser-ignores.js"
Cohesion: 0.52
Nodes (6): globToRegex(), matchesScope(), normalizeIgnoreRule(), normalizeIgnoreValue(), pageCandidates(), resolveDetectIgnores()

### Community 95 - "ApiDatabaseConfigError"
Cohesion: 0.29
Nodes (3): ApiDatabaseConfigError, is_valid_postgres_url(), resolve_pooled_database_url()

### Community 96 - "build_raw_filepath"
Cohesion: 0.14
Nodes (10): build_raw_filename(), build_raw_filepath(), resolve_dataset_id(), _validate_dataset(), test_builds_predictable_raw_filename_for_source_and_dataset(), test_builds_predictable_raw_filepath_with_default_and_custom_dir(), test_rejects_output_dir_when_it_points_to_existing_file(), test_rejects_unsupported_or_invalid_source() (+2 more)

### Community 97 - "bolder.md"
Cohesion: 0.33
Nodes (5): Before you finish, Scope is sovereign, The amplification, The skeleton test, Why it reads flat

### Community 98 - "$impeccable hooks"
Cohesion: 0.33
Nodes (6): Constraints, Failure modes, Flow, $impeccable hooks, Routing, Triage findings

### Community 99 - "scopeCssBlock"
Cohesion: 0.33
Nodes (6): findMatchingCssBrace(), prefixCssSelectors(), scopeCssBlock(), shouldScopeNestedCssAtRule(), splitCssSelectorList(), unwrapSvelteGlobalSelector()

### Community 100 - "interface"
Cohesion: 0.40
Nodes (4): interface, default_prompt, display_name, short_description

### Community 101 - "Impeccable Documenter"
Cohesion: 0.40
Nodes (4): Impeccable Documenter, Input Contract, Output Contract, Workflow

### Community 102 - "mountSvelteComponentVariant"
Cohesion: 0.10
Nodes (31): acceptedDomAlreadyClean(), applyOriginalAttrsToSvelteAnchor(), clearHandledWrapperReloadStamp(), commitAcceptedSvelteComponentToDom(), commitAcceptedVariantToDom(), componentModuleCandidates(), deferredRecoverySuperseded(), describeMountFailure() (+23 more)

### Community 103 - "Scoring the report"
Cohesion: 0.50
Nodes (4): Issue Severity (P0–P3), Reference Material, Score Summary, Scoring the report

### Community 109 - "doctor.md"
Cohesion: 0.22
Nodes (8): Monorepo notes, Opting out of the boot check, Step 1: Run the pass, Step 2: Act by severity, Step 3: Deprecated fields are binding, Step 4: Do not overclaim on truth drift, Step 5: Compact DESIGN.md only with consent, What this owns, and what it does not

### Community 110 - "adapt.native.md"
Cohesion: 0.25
Nodes (7): Adaptation Strategies, Assess Adaptation Challenge, Implement & Verify, Orientation & foldables, Phone → Tablet (iPad / large screens), Platform → platform (iOS ↔ Android), Web → native (porting a website or web app)

## Knowledge Gaps
- **8 isolated node(s):** `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Achados Explorat?rios do MVP ? Cear? (Janeiro/2025)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS`, `Grafico SVG: Geracao Verificada Diaria (MWh)`, `Grafico SVG: Distribuicao Horaria das Restricoes` (+3 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 735 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `init()` connect `setLiveState` to `handleGo`, `live-browser.js`, `actOnAgentTarget`, `doctor.md`, `initPageChat`, `resumeSession`, `live.md`, `Init flow`, `SKILL.md`?**
  _High betweenness centrality (0.152) - this node is a cross-community bridge._
- **What connects `Taxonomia Oficial de Razão (REL, CNF, ENE, PAR) e Origem (LOC, SIS)`, `Achados Explorat?rios do MVP ? Cear? (Janeiro/2025)`, `Registro de Coleta e Hashes dos Dicionários Oficiais ONS` to the rest of the system?**
  _8 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Testes Sintéticos CKAN, Download e CLI` be split into smaller, more focused modules?**
  _Cohesion score 0.12685560053981107 - nodes in this community are weakly interconnected._
- **Why does `Commands` connect `SKILL.md` to `setLiveState`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Should `test_database.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10609756097560975 - nodes in this community are weakly interconnected._
- **Why does `Critique rubric` connect `Cognitive Load Assessment` to `Persona-Based Design Testing`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Should `Validação, Metadados e Hash SHA-256` be split into smaller, more focused modules?**
  _Cohesion score 0.11229946524064172 - nodes in this community are weakly interconnected._