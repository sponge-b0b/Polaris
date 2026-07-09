  # Non-RAG Platform Stabilization Plan

  ## Summary

  Stabilize the entire platform outside the RAG implementation using the same principles applied during RAG stabilization:

  - Preserve canonical core contracts and refactor higher layers around them.
  - Replace oversized orchestration classes with focused typed collaborators.
  - Promote important data out of generic metadata dictionaries into explicit domain or persistence fields.
  - Eliminate manual dependency construction, eager import side effects, duplicated implementations, and verified dead code.
  - Strengthen determinism, telemetry, replayability, migration safety, and test coverage.
  - Keep RAG source code out of scope, but run RAG regression tests whenever shared runtime, telemetry, DI, persistence, or interface infrastructure changes.

  Current Repowise findings justify a broad stabilization pass:

  - StrategySynthesisAgent: health 1.0, 1,094-line god class, 481-line _execute.
  - CLI container: health 1.64, duplicated and complex composition logic.
  - WorkflowBootstrap: health 1.69, _build_runtime CCN 37, 25 dependents.
  - YFinance client: health 1.8, 220-line get_sp500_data, top-1% churn.
  - WorkflowFacade: health 1.9, 674-line god class.
  - RuntimeEngine: health 2.39, 1,248-line god class and near-maximum hotspot score.
  - Portfolio and volatility intelligence nodes contain 254–440-line execution methods.
  - Repository-wide churn is increasing, 263 files are hotspots, and the effective bus factor is one.
  - Several critical hotspots are not governed by indexed architectural decisions.

  Repowise’s structural, health, risk, and git-history data are usable, but semantic retrieval currently reports a degraded mock embedder because the MCP process lacks GEMINI_API_KEY or GOOGLE_API_KEY. Semantic answers must not
  be treated as authoritative until that is corrected.

  Implementation should proceed one reviewed step at a time. Every step ends with focused verification and a recorded result before the next begins.

  ## Implementation Steps

  ### Step 1 — Establish the stabilization baseline

  - Configure the Repowise MCP server with its real embedding provider and restart it; confirm semantic wiki retrieval is no longer using mock vectors.
  - Capture:
      - full pytest and coverage results;
      - Ruff and MyPy results;
      - Alembic single-head, upgrade, downgrade, and metadata-divergence results;
      - Repowise health, risk, dead-code, community, and hotspot reports;
      - Graphify architecture and dependency maps;
      - current CLI, API, scheduler, backtesting, telemetry, and workflow smoke-test results.

  - Record environmental dependencies and distinguish required tests from credential-dependent live smoke tests.
  - Establish the measured baseline against which all later steps are compared.

  Verification: baseline report is reproducible and all pre-existing failures are explicitly classified.

  ### Step 2 — Add architecture governance for ungoverned hotspots

  - Document the governing decisions for:
      - runtime execution ownership;
      - WorkflowFacade as the application boundary;
      - WorkflowBootstrap as the composition root;
      - Dishka request scopes;
      - runtime event and telemetry propagation;
      - PostgreSQL system-of-record ownership;
      - deterministic backtesting;
      - typed internal contracts and boundary serialization.

  - Add concise decision records or indexed decision markers so Repowise can associate these rules with the affected modules.
  - Do not rewrite production code in this step.

  Verification: Repowise decision queries return governing decisions for the major runtime, workflow, telemetry, DI, and backtesting hotspots.

  ### Step 3 — Characterize high-risk behavior before refactoring

  Add focused characterization tests around:

  - Runtime wave scheduling, dependency resolution, node execution, cancellation, pause/resume, failure, skip, event emission, and output persistence.
  - Workflow registration, construction, execution, replay, completed-run loading, and control APIs.
  - Trace-context propagation through concurrently executing nodes.
  - Strategy synthesis, portfolio-state construction, volatility risk, technical breadth, and execution-risk behavior.
  - CLI workflow invocation, progress handling, interactive control, and complete report rendering.
  - YFinance/provider normalization and simulated-provider parity.

  Tests must validate behavior, not internal implementation details.

  Verification: targeted tests pass against the existing implementation and expose any currently untested failure branches.

  ### Step 4 — Audit package boundaries and import side effects

  - Inspect broad __init__.py re-exports and package imports across core, application, integration, intelligence, persistence, backtesting, and interfaces.
  - Remove eager imports that:
      - initialize infrastructure;
      - load settings or credentials;
      - create database engines or clients;
      - register providers globally;
      - create circular dependencies;
      - make isolated tests import unrelated subsystems.

  - Require callers to import canonical symbols from their owning modules.
  - Preserve only small, intentional package-level public APIs.

  Verification: representative packages import without opening network connections, creating DI containers, or initializing PostgreSQL, telemetry exporters, or vendor clients.

  ### Step 5 — Complete the platform data-contract inventory

  Classify every non-RAG service and intelligence output as one of:

  1. Canonical state that must be persisted as explicit fields.
  2. Reproducible derived data that does not require persistence.
  3. Transient runtime or presentation data.
  4. Telemetry or diagnostic data.

  Then:

  - Compare service results and intelligence signals with domain models, runtime serialization, ORM models, report assemblers, and backtesting fixtures.
  - Identify known values currently hidden in generic metadata, JSON blobs, or untyped dictionaries.
  - Identify duplicate, legacy, ambiguously named, fabricated, or fallback fields.
  - Verify that numeric precision is preserved internally.
  - Produce an explicit schema-change list before modifying the database.

  Verification: every important field has a documented owner, type, persistence policy, and serialization boundary.

  ### Step 6 — Approve core and destructive schema changes

  Before production changes to core/ or destructive database changes:

  - Present the exact proposed core internal decomposition, affected contracts, migration operations, blast radius, and rollback strategy.
  - Preserve these canonical public contracts unless a separately approved change is necessary:
      - WorkflowFacade;
      - WorkflowBootstrap;
      - RuntimeNode;
      - RuntimeNodeOutput;
      - WorkflowGraphDefinition;
      - runtime control and event contracts.

  - Prefer internal collaborators and typed parameter bundles over public compatibility wrappers.
  - For schema cleanup, prefer direct migration to canonical names and remove obsolete columns in the same approved migration rather than retaining permanent aliases.

  Verification: explicit approval is obtained before core production edits or destructive migrations. Without approval, core changes remain limited to tests and documentation.

  ### Step 7 — Decompose RuntimeEngine internally

  After core approval:

  - Keep RuntimeEngine as the canonical runtime entry point.
  - Extract focused internal responsibilities such as:
      - wave scheduling and dependency readiness;
      - node invocation and result normalization;
      - control-state observation;
      - node/progress event publication;
      - success, skip, failure, and cancellation finalization.

  - Introduce typed execution/event context objects where they replace repeated 7–9 argument parameter groups.
  - Preserve deterministic ordering, trace context, EventBus semantics, state transitions, and persistence behavior.
  - Do not create a second execution engine.

  Verification: characterization, replay, control, event, telemetry, and workflow integration tests remain unchanged and pass.

  ### Step 8 — Stabilize workflow composition and facade delegation

  - Reduce WorkflowBootstrap._build_runtime complexity by composing named, typed component bundles.
  - Remove duplicated composition logic between workflow bootstrap, provider modules, facade creation, and CLI bootstrap.
  - Keep WorkflowBootstrap as the only runtime composition root.
  - Keep WorkflowFacade as the stable application boundary while delegating registration, execution, control, replay, and completed-run operations to focused existing or extracted collaborators.
  - Replace parameter-heavy internal construction with typed immutable configuration objects.
  - Migrate callers directly; do not introduce legacy bootstrap adapters.

  Verification: CLI, API, scheduler, backtesting, and tests resolve the same shared runtime, control manager, EventBus, telemetry, and persistence implementations.

  ### Step 9 — Retire the unused RuntimeState aggregate and stabilize replay, checkpoints, events, and control

  Execute this step in separately reviewed slices so the runtime-context contract, persisted payload migration, and replay verification remain independently auditable.

  - Characterize current and historical `RuntimeContext` payloads before editing them. Confirm the production data flow is workflow inputs plus persisted node outputs, and prove that `MarketState`, runtime `PortfolioState`, `RiskState`, and `StrategyState` do not affect production decisions, replay, resume, or completed-run inspection.
  - Keep `RuntimeContext` as the canonical persisted execution snapshot, but move the actually used workflow input payload from `RuntimeState.shared_state` to an explicitly named `RuntimeContext.workflow_inputs` boundary field. Treat this as serialized runtime-boundary data; workflow-specific consumers must validate it into typed input contracts before business use.
  - Remove the entire unused runtime business-state aggregate when characterization confirms the current findings:
      - `RuntimeState`;
      - `MarketState`;
      - `core.runtime.state.PortfolioState`;
      - `RiskState`;
      - `StrategyState`.
  - Remove the unfinished namespace-state mechanism that exists only to populate that aggregate:
      - `RuntimeContext.merge_state()`;
      - `RuntimeNodeOutput.namespace_updates`;
      - `RuntimeNode.consumes_namespaces` and `produces_namespaces`;
      - corresponding execution-plan namespace metadata and example-only namespace workflow behavior.
  - Keep runtime-owned identity and timing directly on `RuntimeContext`. Remove duplicate `runtime_mode`, `execution_id`, `timestamp`, `step_index`, and generic runtime-state metadata rather than relocating unused fields. Rename `state_version` to `context_version`; the current counter already versions node outputs, artifacts, errors, and namespace merges rather than a separate business state.
  - Keep `domain.portfolio.models.PortfolioState` as the sole canonical portfolio business model. Do not force it into `RuntimeContext` unless a concrete node contract requires a typed portfolio result; node outputs remain execution evidence and must serialize typed domain results only at the runtime boundary.
  - Migrate canonical PostgreSQL completed-run context JSON deterministically: preserve identity, workflow inputs, node outputs, artifacts, errors, trace context, simulation time, and version; move `state.shared_state` to `workflow_inputs`; remove obsolete default state namespaces and duplicate state metadata. Do not fabricate missing business values.
  - Treat local checkpoint files as generated runtime artifacts rather than a permanent compatibility API. Update tracked fixtures and serializers to the new context schema, reject unsupported historical checkpoint schemas with an explicit version error, and do not add a permanent legacy-state adapter.
  - Audit replay and checkpoint reconstruction against the narrowed runtime-context contract. Verify that completed PostgreSQL runs remain inspectable and that checkpoints retain everything unfinished nodes actually consume.
  - Remove fabricated timestamps or nondeterministic fallback values; keep all times timezone-aware UTC and make replay-sensitive clocks and identifiers injectable.
  - Confirm pause, resume, cancellation, and progress events remain cooperative, attributable, and persisted consistently.
  - Investigate Repowise’s ReplayEngine dead-code finding before any removal; replay is an architectural capability and must not be deleted solely because static import analysis reports no importer.

  Verification: migrated completed runs load without fabricated values; unsupported old checkpoint schemas fail explicitly; deterministic replay reproduces equivalent node outputs, ordering, attribution, control outcomes, and final context using the narrowed `RuntimeContext`; no production code references the removed runtime-state or namespace contracts.

  ### Step 10 — Harden telemetry and observability

  - Add direct tests for the high-impact ObservabilityManager.
  - Replace repeated telemetry parameter lists with typed event/context objects where this simplifies the contract.
  - Verify trace propagation through:
      - runtime nodes;
      - asyncio.gather or task creation;
      - application services;
      - providers and clients;
      - PostgreSQL operations;
      - CLI/API entry points.

  - Audit logging for structured context, exception attribution, and secret leakage.
  - Audit Prometheus cardinality and prevent unbounded labels such as raw symbols, prompts, URLs, or exception messages.
  - Ensure long-running operations expose duration, success/failure, and cancellation metrics.
  - Add typed readiness diagnostics for PostgreSQL, telemetry exporters, providers, and runtime persistence without absorbing RAG readiness into this plan.

  Verification: local Prometheus, Jaeger, structured logging, and persistence tests show one correlated trace across the complete non-RAG workflow path.

  ### Step 11 — Normalize dependency injection and application entry points

  - Ensure CLI, API, scheduler, workflow, and backtesting boundaries resolve dependencies through canonical Dishka scopes.
  - Remove manual container construction from CLI code and duplicated provider registration.
  - Verify resource lifetime and shutdown for HTTP clients, database sessions, telemetry exporters, and external SDKs.
  - Ensure application services use ServiceRunner where they are canonical request/result services.
  - Do not force non-service orchestrators into ServiceRunner; give them telemetry appropriate to their actual lifecycle.

  Verification: no interface constructs application services, providers, vendor clients, repositories, or runtime infrastructure manually.

  ### Step 12 — Stabilize application services and analysis modules

  - Audit technical, macro, market-events, news, sentiment, portfolio, and backtesting services for:
      - typed request/result contracts;
      - duplicate orchestration;
      - hidden provider access;
      - internal rounding;
      - inconsistent score ranges;
      - optional-value handling;
      - swallowed provider failures;
      - generic dictionary contracts.

  - Extract complex calculations into small, deterministic, pure functions or focused analyzers.
  - Preserve service ownership of provider orchestration.
  - Confirm the canonical technical breadth fields are used consistently and remove verified legacy duplicates.
  - Investigate Repowise’s apparently unused analysis functions before deletion because callable injection and DI can evade static import analysis.

  Verification: deterministic service tests cover normal, empty, partial, stale, and provider-failure inputs.

  ### Step 13 — Stabilize integration clients and providers

  - Refactor the YFinance client behind its existing client/provider contract:
      - separate constituent retrieval, batch fetching, symbol normalization, breadth aggregation, and summary construction;
      - preserve exact canonical output semantics;
      - bound concurrency and timeouts;
      - record provider telemetry for every external call.

  - Confirm live and simulated providers return equivalent typed contracts.
  - Audit pagination, retries, rate limits, cancellation, timestamps, and partial responses across all external clients.
  - Replace parameter-heavy LLM/client calls with typed request/options/result contracts when justified.
  - Keep SDK and transport types confined to clients.

  Verification: provider contract tests run against deterministic fakes; credentialed live tests are bounded and never required for the deterministic suite.

  ### Step 14 — Decompose intelligence hotspots

  Prioritize:

  1. StrategySynthesisAgent.
  2. PortfolioStateBuilder.
  3. VolatilityRiskAgent.
  4. Other analyst, research, risk, strategy, portfolio, packaging, and execution hotspots identified by the refreshed Repowise report.

  For each hotspot:

  - Preserve RuntimeNode and RuntimeNodeOutput behavior.
  - Extract pure typed policy components for parsing, weighting, gating, uncertainty, classification, and recommendation construction.
  - Remove duplicated signal extraction and runtime-output parsing.
  - Make hidden coupling explicit through typed inputs instead of relying on co-changing modules.
  - Keep market-events access behind the application service and preserve dynamic constituent inputs.
  - Ensure telemetry remains at orchestration and significant decision boundaries rather than polluting pure calculations.
  - Retain full numeric precision.

  Verification: golden tests demonstrate that equivalent inputs produce equivalent signals, risk assessments, portfolio state, strategy posture, and recommendations before and after decomposition.

  ### Step 15 — Stabilize persistence and database mappings

  - Apply the approved contract inventory to non-RAG ORM models and repositories.
  - Promote canonical values out of generic metadata into first-class typed fields only when they are true system-of-record data.
  - Do not persist every derived service result merely because it exists.
  - Create Alembic migrations and deterministic backfills for added, renamed, converted, or removed fields.
  - Remove obsolete columns and names in the approved cleanup migration instead of preserving permanent compatibility aliases.
  - Simplify repository and serializer hotspots while retaining transaction boundaries, idempotency, and telemetry.
  - Remove eager persistence imports and hidden global engines or sessions.

  Verification: blank-database upgrade, downgrade/upgrade cycle, single-head check, pytest-alembic ORM divergence test, data-backfill tests, and live PostgreSQL integration tests pass.

  ### Step 16 — Stabilize CLI, API, scheduler, and report boundaries

  - Keep interfaces thin and async-native.
  - Delegate execution to application services or WorkflowFacade.
  - Ensure workflow output is rendered for success, partial success, cancellation, and failure.
  - Preserve complete LLM and report content; truncation or summarization is presentation-only and must be explicitly requested.
  - Keep console, Markdown, JSON, and other renderers at the serialization/presentation boundary.
  - Verify interactive pause/resume/cancel input does not create a parallel control mechanism.
  - Remove duplicated CLI container and command wiring.

  Verification: boundary tests cover exit codes, progress display, interactive control, complete output rendering, malformed input, and service failures.

  ### Step 17 — Complete deterministic backtesting verification

  - Replace the parameter-heavy backtest entry point with a typed immutable run request while preserving the application service boundary.
  - Verify simulated providers match live provider contracts exactly.
  - Add deterministic datasets with explicitly calculated expected:
      - technical indicators;
      - breadth and regime assessments;
      - portfolio state;
      - risk signals;
      - strategy synthesis;
      - trade recommendations;
      - execution-risk decisions.

  - Run simulations multiple times and assert identical outputs, ordering, timestamps from the injected clock, metrics, and persisted artifacts.
  - Ensure the ordinary runtime remains unaware of whether providers are live or simulated.

  Verification: deterministic golden scenarios independently confirm that recommendations and risk assessments are mathematically correct for the supplied data.

  ### Step 18 — Security, reliability, and governance audit

  - Verify secrets never enter logs, telemetry labels, checkpoints, runtime outputs, or persisted error messages.
  - Audit external input validation, request size limits, timeouts, retries, cancellation, and resource cleanup.
  - Confirm policy and governance checks are not bypassed by CLI, API, scheduler, replay, or backtesting paths.
  - Review destructive operations and require explicit typed confirmation gates.
  - Audit dependency vulnerabilities and unsafe serialization.
  - Confirm failures produce typed, attributable results rather than silently returning partial dictionaries.

  Verification: focused negative tests cover unauthorized operations, malformed provider data, timeouts, cancellation, persistence failures, and policy/governance denial.

  ### Step 19 — Remove verified dead and duplicate code

  - Re-run Repowise dead-code analysis, Graphify queries, exact reference searches, test discovery, plugin registration checks, and DI registration checks.
  - Treat static “unused” findings as candidates, not proof, especially for:
      - replay components;
      - DI providers;
      - telemetry sinks;
      - plugin hooks;
      - callable-injected analysis functions.

  - Run pylint duplicate-code and jscpd before extracting shared logic.
  - Remove only behavior proven unreachable or superseded.
  - Do not create generic helper modules merely to reduce a metric.
  - Request confirmation before deleting production source modules.

  Verification: full tests pass after each cleanup batch and no runtime registration, plugin, CLI, or reflection path references deleted code.

  ### Step 20 — Documentation, knowledge preservation, and final readiness gate

  - Update the Repowise wiki and platform documentation with:
      - runtime execution flow;
      - composition and DI ownership;
      - telemetry propagation;
      - service/provider/client boundaries;
      - persistence classifications;
      - operational commands and service dependencies.

  - Re-run Repowise full health, risk, dead-code, and blast-radius analyses.
  - Refresh Graphify after source changes.
  - Compare final results with the Step 1 baseline.
  - Document intentional exceptions rather than leaving unresolved critical findings unexplained.

  Verification: the final readiness report demonstrates measurable health improvement and no architectural regression.

  ## Public APIs and Contract Policy

  - Preserve WorkflowFacade, WorkflowBootstrap, RuntimeNode, RuntimeNodeOutput, and workflow graph contracts by default. The approved Step 9 removal of the unused namespace-state fields is an explicit exception; callers must migrate directly to the narrowed contracts without compatibility wrappers.
  - Core god classes may be decomposed internally, but callers continue using canonical boundaries.
  - New internal contracts should use frozen, slotted dataclasses for:
      - grouped runtime dependencies;
      - execution/event context;
      - backtest run requests;
      - provider or LLM request options;
      - readiness diagnostics.

  - Existing internal callers are migrated directly to canonical typed contracts; no permanent compatibility wrappers or dictionary adapters are added.
  - Database fields are added only for canonical system-of-record data, not arbitrary derived or presentation data.
  - RAG public and internal contracts remain unchanged unless a shared-infrastructure fix is required to prevent a regression.

  ## Test and Acceptance Criteria

  The stabilization is complete only when:

  - The full test suite passes.
  - Overall coverage is not lower than the Step 1 baseline and remains at least 80%.
  - Changed hotspot modules have at least 85% meaningful line coverage with relevant branch and failure-path tests.
  - Ruff check/fix, Ruff formatting, and MyPy pass with no new ignores.
  - Alembic has one head and migrations match SQLAlchemy metadata.
  - PostgreSQL migration and integration tests pass against a clean database.
  - CLI, API, scheduler, backtesting, replay, control, telemetry, and completed-run smoke tests pass.
  - Shared-core changes pass the existing RAG regression suite even though RAG implementation is excluded.
  - Repowise reports no unexplained critical god-class, brain-method, untested-hotspot, or architectural-governance findings in the targeted modules.
  - No important known data remains hidden exclusively in generic metadata.
  - No external call bypasses the service → provider → client layering.
  - No interface bypasses WorkflowFacade, WorkflowBootstrap, policy, or governance boundaries.
  - Deterministic backtests produce identical and independently verifiable results on repeated runs.

  ## Assumptions and Guardrails

  - RAG application, retrieval, ingestion, projection, model, and provider code is excluded from refactoring.
  - Shared runtime, telemetry, DI, persistence, and interface changes may affect RAG and therefore require RAG regression testing.
  - The user granted explicit approval on 2026-06-27 for the Step 6 core decomposition, the broadened RuntimeState retirement, and the listed persistence/schema changes. Any destructive core or schema change outside that approved package still requires a new approval.
  - Destructive database migrations and production source-file deletion require explicit review and approval.
  - Repowise semantic results are considered unreliable until its real embedder is restored; structural, health, risk, and git-history signals may still be used.
  - Health findings guide prioritization but do not justify refactoring or deletion without source inspection and behavioral tests.
  - Full numeric precision is preserved throughout internal calculations and persistence.
  - Dictionaries remain restricted to serialization and external-system boundaries.
  - Each implementation step is completed, verified, documented, and reviewed before the next step starts.
  ## Step Results

  ### Step 1 — Establish the stabilization baseline (Completed 2026-06-26)

  **Repository and tooling baseline**

  - No production source code was changed in this step.
  - Repowise was moved from the degraded Gemini/mock configuration to the local Ollama embedding provider with `bge-m3:567m`.
  - Reindex result: 200 vector pages indexed, 1 page failed, with SQL/vector drift reduced from 100% to 0.5% (`SQL=201`, `Vector=200`). `repowise doctor .` now reports all checks passed.
  - A direct semantic search through the rebuilt local index returned relevant runtime/wiki results, confirming that the stored vectors are real rather than mock vectors.
  - The Codex MCP registration now supplies `REPOWISE_EMBEDDING_MODEL=bge-m3:567m`. The already-running Repowise MCP process in this Codex session still reports its old Gemini/mock state because MCP processes cannot be hot-restarted from the active session. Restarting Codex will activate the corrected MCP registration.
  - Repowise CLI is version 0.16.0 and reports that 0.24.0 is available. The tool was not upgraded during this baseline step.

  **Static verification**

  | Check | Result |
  | --- | --- |
  | `ruff check .` | Passed: no findings |
  | `ruff format . --check` | Passed: 1,052 files already formatted |
  | `mypy . --explicit-package-bases` | Passed: no issues in 1,049 source files |

  **Non-RAG test and coverage baseline**

  - Reproducible command scope: the complete test suite excluding `tests/integration/rag`, with `POLARIS_TEST_DATABASE_URL=postgresql+asyncpg://user:pass@127.0.0.1:5432/db` so PostgreSQL migration and integration contracts execute rather than skip.
  - Result: **1 failed, 1,524 passed**, 13 warnings, in 117.43 seconds.
  - Coverage: **89.42%** (`29,270 / 32,732` statements covered; 3,462 missing).
  - The single failure is `tests/unit/core/workflow/execution/test_completed_run_archive_async.py::test_workflow_archive_failure_is_logged_and_non_fatal`.
  - Classification: **pre-existing order-dependent test isolation defect**. The test passes both alone and with its complete test module, but fails in the full ordered suite because `caplog` receives no record. The production path still calls `logger.exception("Completed workflow run archival failed.")`; an earlier test is leaking or replacing global logging configuration/handlers. This must be isolated before using full-suite logging assertions as a release gate.
  - The unscoped suite contains three live RAG integration tests. They are excluded from this non-RAG stabilization baseline because they depend on Qdrant, Neo4j, and the BGE reranker, and the live BGE check can block while the service is unavailable. Shared-core changes must still run the deterministic RAG regression suite and separately run live RAG smoke tests when those services are intentionally started.

  **Database and persistence baseline**

  - PostgreSQL connectivity passed against PostgreSQL 16.14 at `127.0.0.1:5432`, database/user `polaris`.
  - Alembic reports one head: `f6a7b8c9d0e1`.
  - `tests/database/test_migrations.py`: **6 passed** in 24.65 seconds.
  - Verified contracts include single-head history, blank-database upgrade, downgrade consistency, ORM metadata divergence, backtest timestamp backfill, and RAG query-audit metadata promotion.
  - Completed-run PostgreSQL archive/repository/workflow integrations: **3 passed**.
  - Existing warning to address later: Alembic reports that `path_separator` is absent and legacy `prepend_sys_path` splitting is in use.
  - Existing SQLAlchemy warning to investigate: a portfolio-state repository unit test compiles values named `cash_ratio` and `risk_signals` that do not match table column keys.

  **Interface, workflow, telemetry, and backtesting smoke baseline**

  | Area | Result |
  | --- | --- |
  | CLI command discovery | Passed: `polaris --help`, `polaris workflow --help`, and `polaris backtest --help` |
  | CLI runtime composition | Passed: `polaris workflow list` resolves the built-in `morning_report`; `polaris inspect runtime` resolves policy, governance, and telemetry |
  | Workflow/CLI focused tests | 50 passed |
  | Runtime control/replay/telemetry focused tests | 21 passed |
  | Deterministic backtesting/provider/CLI focused tests | 30 passed |
  | PostgreSQL completed-run integration | 3 passed |
  | API | Import succeeds, but all files under `interfaces/api/` are zero-byte placeholders; there is no runnable API behavior to smoke-test |
  | Scheduler | All files under `interfaces/scheduler/` are zero-byte placeholders; no scheduler implementation or runnable entry point exists |
  | UI | All current files under `interfaces/ui/` are zero-byte placeholders |

  - `polaris inspect runtime` reports `observability_manager: False` while telemetry is enabled. Focused observability tests pass, so the difference may be composition-path-specific; it is a concrete telemetry/composition audit item for later stabilization steps.
  - `polaris inspect runtime` also reports zero runtime nodes before a workflow request is composed. This is recorded as a baseline observation, not yet classified as a defect.

  **Repowise and architecture-risk baseline**

  - Current CLI health baseline after reindex: average health **7.72**, hotspot health **7.43**, 818 measured files, 1,468 findings, including 72 critical and 360 high-severity findings.
  - Lowest-scoring files begin with:
      1. `interfaces/cli/bootstrap/container.py` — 1.64
      2. `core/workflow/bootstrap/workflow_bootstrap.py` — 1.69
      3. `core/workflow/execution/workflow_facade.py` — 1.90
      4. `intelligence/strategy/synthesis/strategy_synthesis_agent.py` — 2.14
      5. `integration/clients/market_data/yfinance_data_client.py` — 2.24
      6. `core/runtime/execution/runtime_engine.py` — 2.39
  - Targeted structural findings confirm `RuntimeEngine` as a 1,248-line/33-method god class, `WorkflowFacade` as a 674-line/31-method god class, and `WorkflowBootstrap._build_runtime` as a 158-line method with CCN 37.
  - Targeted git-risk findings place RuntimeEngine, WorkflowFacade, and WorkflowBootstrap in approximately the 98th–100th hotspot percentiles. WorkflowBootstrap has 25 dependents and increasing churn; all three have a bus factor of one.
  - Repository git baseline: 263 hotspots, increasing churn, effective bus factor one, with the highest churn concentrated in tests/unit, core/storage, application/services, integration/providers, and core/runtime.
  - Community analysis identifies the largest low-cohesion communities around package `__init__` surfaces, storage/persistence, integration/providers, application persistence, runtime, telemetry, CLI, and technical application services. These results reinforce Steps 4, 8, 10, 13, and 16 rather than justifying immediate broad rewrites.
  - Dead-code analysis reports 166 candidates, including 54 high-confidence candidates and approximately 3,173 candidate lines. These remain unverified candidates only; no production deletion is authorized from static reachability alone.
  - Graphify confirms RuntimeEngine, WorkflowFacade, and WorkflowBootstrap as central architectural nodes tied to runtime context/state, EventBus, policy, governance, telemetry, persistence, and workflow graph contracts. Later refactors must preserve these boundaries and use blast-radius checks before edits.

  **Environment and test classification**

  - Running local service: PostgreSQL on port 5432.
  - Not running during this baseline: Qdrant 6333, Neo4j 7474/7687, BGE reranker 8080, Prometheus 9090, and Jaeger 16686.
  - Required deterministic release checks: Ruff, formatting, MyPy, non-RAG pytest/coverage, Alembic contracts, PostgreSQL integration tests, CLI composition, workflow/replay/control, telemetry, and deterministic backtesting.
  - Service-dependent checks: Prometheus and Jaeger exporter delivery; live Qdrant/Neo4j/BGE checks; external market, macro, news, sentiment, broker, Firecrawl, and LLM provider calls.
  - Credential-dependent end-to-end checks, including a live morning report, must be run only when the corresponding provider credentials and services are available. Their absence is an environmental skip, not permission to weaken deterministic fake/provider contract tests.

  **Step 1 conclusion**

  - The baseline is reproducible and sufficiently complete to begin stabilization.
  - Immediate known gates are the order-dependent logging-test contamination, missing concrete API/scheduler implementations, the CLI runtime observability composition discrepancy, and the documented high-risk core/composition hotspots.
  - No Step 2 work has begun.

  ### Step 2 — Add architecture governance for ungoverned hotspots (Completed 2026-06-27)

  **Durable architecture decision records**

  - No production source code was changed, and no external service was required.
  - Added six accepted, source-controlled ADRs under `.docs/decisions/`:
      1. `adr-001-runtime-execution-and-workflow-boundaries.md`
      2. `adr-002-dishka-composition-and-request-scopes.md`
      3. `adr-003-runtime-events-telemetry-and-trace-propagation.md`
      4. `adr-004-postgresql-system-of-record.md`
      5. `adr-005-deterministic-backtesting-through-the-canonical-runtime.md`
      6. `adr-006-typed-internal-contracts-and-boundary-serialization.md`
  - The ADRs explicitly govern runtime execution ownership, `WorkflowFacade`, `WorkflowBootstrap`, Dishka scopes, runtime events and telemetry, trace propagation, PostgreSQL authority, deterministic backtesting, typed internal contracts, boundary serialization, and full internal numeric precision.
  - Each ADR records context, the accepted decision, rationale, consequences, and the affected modules. The filenames and Nygard-style structure allow Repowise full initialization to deterministically rediscover the source-controlled records.

  **Repowise decision governance**

  - Recorded the six decisions as active Repowise decision records with explicit affected-file associations and 100% CLI confidence:
      - `27d7c698` — Runtime execution and workflow boundaries
      - `0c55dfed` — Dishka composition and request scopes
      - `4cbb10d2` — Runtime events telemetry and trace propagation
      - `d341f087` — PostgreSQL is the platform system of record
      - `41ea05f1` — Deterministic backtesting through the canonical runtime
      - `ef6d565f` — Typed internal contracts and boundary serialization
  - Decision health moved from **0 active decisions / 263 ungoverned hotspots** to **6 active decisions / 244 ungoverned hotspots**. Nineteen previously ungoverned hotspot files are now associated with a governing decision.
  - No proposed, stale, deprecated, or conflicting decision records were introduced.

  **Verification**

  - `repowise decision list . --status active` returns all six active decisions.
  - `repowise decision health .` reports six active and zero stale decisions.
  - Repowise `get_why` returns the expected active governing decision with **high alignment** for representative runtime, workflow, DI, telemetry, persistence, backtesting, and typed-contract paths.
  - Repowise `get_context(..., include=["decisions"])` returns direct decision associations for:
      - `core/runtime/execution/runtime_engine.py`
      - `core/workflow/execution/workflow_facade.py`
      - `core/workflow/bootstrap/workflow_bootstrap.py`
      - `core/bootstrap/workflow_providers.py`
      - `core/runtime/events/event_bus.py`
      - `core/database/postgres.py`
      - `application/services/backtesting/backtest_service.py`
      - `application/services/base/service_request.py`
  - This step was documentation and governance-index work only; Python static checks and tests were not rerun because no executable code changed.

  **Step 2 conclusion**

  - The major stabilization hotspots now have explicit, queryable architectural governance before behavioral characterization and refactoring begin.
  - The remaining ungoverned hotspots are intentionally deferred to the later domain-specific stabilization steps rather than being covered by overly broad decisions in this step.

  ### Step 3 — Characterize high-risk behavior before refactoring (Completed 2026-06-27)

  **Characterization coverage added**

  - No production source code was changed, and no external service was required.
  - Added `tests/unit/runtime/execution/test_runtime_engine_concurrent_trace_context.py` to prove that nodes in the same execution wave start concurrently, receive distinct child spans under one workflow trace, preserve node identity, and persist outputs under the correct node names while the final context retains the workflow root span.
  - Added `tests/unit/integration/clients/market_data/test_yfinance_data_client.py` with deterministic HTTP and constituent-table fakes. The tests freeze the canonical `SP500Data` contract, symbol normalization (`BRK.B` → `BRK-B`), market-cap ordering, breadth analytics columns, exclusion of downstream-derived legacy columns, and parity with `SimulatedDataProvider`.
  - Extended `tests/unit/application/services/technical/test_breadth_volatility_analysis.py` with a full positive breadth-analysis contract covering trend, slope, confirmation, participation, leadership, McClellan, aggregate risk/regime, strategy weights, and preservation of full internal numeric precision.
  - Extended `tests/unit/intelligence/execution/test_execution_risk_guard.py` with the single-breach scaled-execution path, including deterministic position-size adjustment and recommendation enrichment.
  - Reviewed the existing characterization suites and confirmed they already cover runtime dependency skips, disabled and missing nodes, retries, failures, cancellation, pause/resume, progress and lifecycle events, output application, workflow registration/execution/control, replay and completed-run loading, strategy breadth gating, portfolio-state construction, volatility risk, CLI workflow invocation, progress/interactive control, and complete morning-report rendering. Those behaviors were not duplicated in new tests.

  **Verification**

  | Check | Result |
  | --- | --- |
  | New and directly modified characterization tests | 9 passed |
  | Runtime, workflow, strategy, portfolio, volatility, execution-risk, and breadth characterization suite | 42 passed; targeted measured coverage 80.95% |
  | Focused intelligence/domain suite with the correct portfolio-state module target | 20 passed; targeted measured coverage 81.76% |
  | CLI workflow/progress/output and morning-report rendering suite | 27 passed |
  | YFinance normalization plus simulated-provider parity suite without coverage instrumentation | 5 passed |
  | Ruff check/fix and formatting | Passed; four changed Python test files clean and formatted |
  | MyPy with explicit package bases | Passed; no issues in 1,051 source files |
  | `git diff --check` | Passed |
  | Graphify incremental update | Completed: 17,025 nodes, 73,188 edges, 658 communities |

  **Characterization finding deferred to Step 4**

  - Combining Pandas/NumPy-dependent provider tests with coverage instrumentation can fail during collection with `ImportError: cannot load module more than once per process`. The same provider tests pass normally, and the defect was also observed during the earlier broad mixed-suite attempt. This is an import/package initialization or test-process isolation risk, not a provider behavior failure. It is deliberately left unchanged here and becomes a concrete input to Step 4 — package-boundary and import-side-effect auditing.

  **Step 3 conclusion**

  - The most consequential uncharacterized contracts now have deterministic tests before hotspot refactoring begins.
  - The added tests validate observable behavior rather than private RuntimeEngine orchestration details or vendor network availability.
  - No Step 4 implementation has begun.

  ### Step 4 — Audit package boundaries and import side effects (Completed 2026-06-27)

  **Package-boundary audit and production changes**

  - No external service was required for this step.
  - Removed broad eager re-exports from four package roots whose imports initialized unrelated implementation and infrastructure graphs:
      - `core/storage/__init__.py`
      - `integration/providers/backtesting/market_data/__init__.py`
      - `interfaces/cli/__init__.py`
      - `interfaces/cli/services/__init__.py`
  - These package roots are now side-effect-free namespaces with empty explicit export lists. Callers import contracts and implementations from their canonical owning modules instead of relying on package-root aggregation.
  - Updated affected CLI tests and the RAG DI composition test to use canonical module imports. A repository-wide exact import scan found no remaining callers using the removed package-root re-exports.
  - Preserved the intentional typed `application.persistence` package API. Its re-exports are documented application-service contracts rather than infrastructure initialization, and changing that stable API would not address the Step 4 defect.
  - Preserved the intentional `application.rag` domain-contract package API and its existing import-boundary contract. No RAG production implementation was changed.

  **Import-side-effect regression coverage**

  - Added `tests/unit/test_package_import_boundaries.py`, which imports each audited package in an isolated subprocess and verifies:
      - no package implementation children are imported;
      - no database, DI, HTTP, telemetry, numerical, CLI, or rendering frameworks are loaded;
      - no accidental package-root public exports are restored.
  - Added the reusable `tests/helpers/package_imports.py` subprocess probe and migrated the existing RAG package-import tests to it rather than duplicating the inspection logic.
  - Post-refactor isolated import measurements:

    | Package | Before | After |
    | --- | --- | --- |
    | `core.storage` | ~715 ms / 421 loaded modules | 0.215 ms / 2 loaded modules |
    | `integration.providers.backtesting.market_data` | ~1,016 ms / 1,027 loaded modules | 0.416 ms / 4 loaded modules |
    | `interfaces.cli` | ~2,751 ms / 2,440 loaded modules | 0.245 ms / 2 loaded modules |
    | `interfaces.cli.services` | ~2,279 ms / approximately 2,440 loaded modules | 0.320 ms / 3 loaded modules |

  - None of the four package imports loads `asyncpg`, Dishka, HTTP clients, NumPy, Pandas, OpenTelemetry, Prometheus, SQLAlchemy, Typer, Rich, requests, or any package child implementation.

  **Resolved characterization defect**

  - The Step 3 coverage-only failure, `ImportError: cannot load module more than once per process`, was traced to the backtesting market-data package root eagerly importing Pandas/PostgreSQL implementations while coverage resolved a dotted module target.
  - After removing the eager package imports, the combined YFinance and simulated-provider coverage run collects and passes normally: **5 passed**, **81.74%** aggregate targeted coverage, exceeding the configured 75% threshold.

  **Verification**

  | Check | Result |
  | --- | --- |
  | Infrastructure and RAG package import-boundary tests | 6 passed |
  | CLI service/rendering regression tests | 52 passed; one existing websockets deprecation warning |
  | RAG DI composition plus package-boundary regression tests | 7 passed; existing dependency warnings only |
  | Complete unit suite | 1,456 passed; 6 existing warnings |
  | Ruff check/fix and formatting | Passed; all Step 4 Python files clean and formatted |
  | MyPy with explicit package bases | Passed; no issues in 1,053 source files |
  | `git diff --check` | Passed |
  | Graphify incremental update | Completed: 17,040 nodes and 73,208 edges; the final import-only test adjustment produced no topology change |

  **Duplication and risk observations**

  - The required full JSCPD baseline reports **247 pre-existing clones**, **5.38% duplicated lines**, and therefore exceeds the configured 5% threshold. The full Pylint duplicate-code audit also exits nonzero with broad pre-existing duplication findings and a 9.72/10 score. These repository-wide findings are inputs to the later duplication-focused stabilization step, not justification for widening this package-boundary change.
  - The duplicate subprocess probe initially identified during implementation was consolidated into `tests/helpers/package_imports.py`; Step 4 leaves one implementation shared by infrastructure and RAG import tests.
  - Repowise continues to report historical co-change and hidden-coupling risk around `core/storage/__init__.py`, but the package now contains no executable imports. The complete unit suite and focused bootstrap/CLI/RAG checks cover the affected representative paths.

  **Step 4 conclusion**

  - Representative package imports no longer initialize PostgreSQL, vendor/dataframe dependencies, CLI composition, DI, telemetry exporters, or network clients.
  - The coverage-process import crash is fixed without provider behavior changes or compatibility wrappers.
  - No Step 5 work has begun.

  ### Step 5 — Complete the platform data-contract inventory (Completed 2026-06-27)

  **Inventory delivered**

  - Added `.docs/platform_data_contract_inventory.md` as the non-RAG platform data-contract and schema-change gate.
  - Classified canonical business state, reproducible derived data, transient/presentation data, and telemetry/diagnostic data with explicit persistence policies.
  - Documented ownership, required internal type, persistence policy, and serialization boundary for technical, macro, market-events, news, portfolio, and sentiment service outputs.
  - Documented the corresponding analyst, research, risk, strategy, portfolio-management, trade-packaging, execution-risk, attribution, weighting, runtime-state, report, and backtesting boundaries.
  - Confirmed that runtime outputs, checkpoints, completed-run records, telemetry attributes, reports, artifacts, vendor responses, and purpose-named PostgreSQL JSON/JSONB payloads are legitimate dictionary serialization boundaries; service and intelligence payload dictionaries are not canonical internal contracts.

  **Confirmed contract and persistence gaps**

  - Most typed service result wrappers still contain `dict[str, Any]` payloads and therefore provide only nominal rather than structural type safety.
  - Intelligence nodes commonly build raw dictionaries before `RuntimeNodeOutput` instead of constructing typed signals and serializing only at the runtime boundary.
  - `domain.portfolio.models.PortfolioState` and `core.runtime.state.PortfolioState` are competing business-state definitions with incompatible field names and nested types. The domain model is the recommended business owner; implementation is deferred to the Step 6 core-contract approval gate.
  - The current risk signal contract is mutable, weakly typed, and incorrectly owned by the integration layer. `StrategySignalResult` is also mutable and retains mutable lists, generic features, and `Any` LLM data.
  - Sentiment PostgreSQL columns are already canonical, but `SentimentSnapshotRecord` and `SentimentPersistenceSerializer` retain legacy vocabulary and fail to map canonical service fields including market bias, directional signal, momentum, stability, divergence, features, and raw payload. This is serializer data loss against the existing schema, not evidence that legacy database columns should return.
  - Portfolio equity history has no accepted persistence owner. The existing model-coverage test's missing `portfolio_history_payload` must not be closed mechanically with another opaque blob. The inventory recommends deciding between a normalized `portfolio_equity_history_points` table and explicit latest-summary fields at the Step 6 schema gate.
  - Existing backtest metric and artifact timestamps are already first-class (`recorded_at` and `generated_at`); no additional timestamp schema change is required.

  **Precision, legacy, and fallback findings**

  - Identified internal `round()` use across application-service, portfolio-domain, analyst, research, risk, strategy, attribution, weighting, trade-packaging, and portfolio-management calculation paths. These values must retain full precision until a human-presentation boundary.
  - Confirmed `ad_line_trend_score` remains the sole canonical A/D trend score; no `legacy_ad_line_trend_score` remains.
  - Identified `has_breadth` as a removable compatibility alias for canonical `has_breadth_data` after direct consumer migration.
  - Identified fabricated completed-run identity fallbacks such as `unknown_workflow` and `unknown_execution` as audit/replay risks. Missing required identity should fail validation or be represented explicitly as unavailable.
  - Confirmed deterministic `backtest_synthetic` data is intentional and valid when scenario/profile lineage prevents it from being confused with live observations.

  **Explicit change gate produced**

  - Contract-only candidates: typed service DTOs, typed intelligence signal families, typed stable backtest parameters, canonical sentiment record/serializer mapping, boundary serialization tests, fallback provenance, and removal of internal rounding.
  - Core candidates requiring Step 6 approval: portfolio-state convergence, typed stable runtime-state substructures, and direct removal of legacy ORM attribute vocabulary where practical.
  - Schema candidate requiring Step 6 approval: canonical portfolio equity-history retention and its normalized schema or explicit latest-summary alternative.
  - No new sentiment, technical, macro, market-event, news, agent-signal, recommendation, or backtest timestamp columns are justified by the current inventory.

  **Verification**

  | Check | Result |
  | --- | --- |
  | Inventory classification and ownership matrix | Completed for all non-RAG service and intelligence output families |
  | Persistence and serialization-boundary audit | Completed across service, runtime, ORM, report, telemetry, and backtesting layers |
  | Explicit schema-change candidate list | Completed; no schema was modified |
  | Referenced contract paths | Verified present |
  | Markdown structure and whitespace | Passed |
  | External services | Not required |

  **Step 5 conclusion**

  - Every important non-RAG output family now has a documented owner, required internal type, persistence policy, and serialization boundary.
  - The inventory separates confirmed serializer/contract defects from true DDL candidates so a migration is not used to encode unresolved architecture.
  - No Step 6 implementation or core/schema modification has begun.

  ### Step 6 — Core and schema change approval package (Completed and approved 2026-06-27)

  **Scope of this gate**

  - This step made no production code or database changes and required no external service.
  - Repowise reports an overall blast-radius risk score of **10.0** for the combined runtime, workflow-composition, runtime-state, sentiment-persistence, and portfolio-schema candidate set. The highest-risk files are `RuntimeEngine`, `WorkflowBootstrap`, `WorkflowFacade`, `RuntimeState`, and the portfolio-state ORM models.
  - Approval has been granted only for the exact changes below. Anything outside this documented package remains outside the approved scope.

  **A. Proposed Step 7 RuntimeEngine internal decomposition**

  Preserve `RuntimeEngine` as the only canonical runtime executor and preserve its constructor, node registration methods, and `execute()` contract. Extract private implementation responsibilities into these internal collaborators under `core/runtime/execution/`:

  1. `runtime_execution_context.py`
     - Add immutable, slotted typed parameter objects for execution location and node-invocation context.
     - Replace repeated wave/node/boundary argument groups without changing persisted or public runtime contracts.
  2. `runtime_event_publisher.py`
     - Own canonical `RuntimeEvent` construction and EventBus publication for node lifecycle, workflow progress, and control-aware location metadata.
     - Continue using the existing shared `EventBus`; do not create another event system.
  3. `runtime_node_executor.py`
     - Own one-node invocation, timeout, retry, trace-child context, and runtime execution metadata.
     - Continue invoking the existing `RuntimeNode.execute()` contract and returning `RuntimeNodeOutput`.
  4. `runtime_state_transitions.py`
     - Own pure success, skip, failure, cancellation, dependency-readiness, and output-application transitions.
     - Remove the duplicate `runtime_id` event attribute and duplicate `node_outputs` update key currently present in `RuntimeEngine`, with regression coverage proving unchanged observable behavior.
  5. `runtime_wave_executor.py`
     - Own wave scheduling, deterministic task ordering, dependency checks, disabled/missing-node handling, lifecycle hooks, artifact persistence, and cooperative pause/cancel boundaries.
     - Use `asyncio` through the existing runtime path and preserve active trace context for every task.

  `RuntimeEngine` will retain top-level workflow execution, root trace ownership, wave iteration, workflow lifecycle coordination, checkpoint policy, terminal control-state handling, and composition of these private collaborators. No second engine, public wrapper, compatibility class, or alternate runtime path will be introduced.

  **Step 7 affected contracts and likely co-changes**

  - Public contracts preserved unchanged: `RuntimeEngine`, `RuntimeNode`, `RuntimeNodeOutput`, `RuntimeContext`, `WorkflowGraphDefinition`, `RuntimeEvent`, `EventBus`, `WorkflowControlManager`, and checkpoint/replay entry points.
  - Expected production touchpoints: `core/runtime/execution/runtime_engine.py`, the five new private collaborator modules, and only the minimum export/composition files required to instantiate them.
  - Required regression surfaces: runtime execution, concurrent trace propagation, retries/timeouts, dependency skips, disabled and missing nodes, pause/resume/cancel, progress and node events, artifacts, checkpoint-on-wave, replay, runtime telemetry hooks, and workflow integration.
  - Repowise co-change review must include `core/runtime/telemetry/runtime_telemetry_hook.py`, `core/bootstrap/workflow_providers.py`, `core/workflow/bootstrap/workflow_bootstrap.py`, and `core/workflow/execution/workflow_engine.py` even if no edit is ultimately needed.

  **B. Proposed Step 8 workflow composition and facade stabilization**

  Preserve `WorkflowBootstrap` and `WorkflowFacade` public methods and signatures. Add two private composition units under `core/workflow/bootstrap/`:

  1. `workflow_runtime_components.py`
     - Define an immutable, slotted `WorkflowRuntimeComponents` bundle containing the shared runtime engine, workflow engine/service, state manager, checkpoint manager, replay engine, control manager, EventBus, telemetry/observability components, and persistence components.
  2. `workflow_runtime_assembler.py`
     - Centralize construction of the component bundle from existing configuration and already-injected infrastructure.
     - Ensure every facade, provider, CLI, and workflow path receives the same control manager, EventBus, telemetry, persistence, and runtime instances.

  `WorkflowBootstrap._build_runtime()` will become orchestration over named component-construction operations rather than directly performing all assembly. `WorkflowFacade.create()` will retain its current public signature but delegate its implementation to the same canonical assembler so it does not contain a competing composition implementation. `core/bootstrap/workflow_providers.py` and the CLI container will resolve the same canonical objects through Dishka. This preserves the public factory contract while eliminating duplicated internal assembly; it is not a compatibility shim.

  **Step 8 affected contracts and likely co-changes**

  - Public contracts preserved unchanged: `WorkflowBootstrap`, `WorkflowBootstrapConfig`, `WorkflowBootstrapResult`, `WorkflowFacade`, facade workflow/control/replay/archive methods, and Dishka request-scope behavior.
  - Expected production touchpoints: `core/workflow/bootstrap/workflow_bootstrap.py`, the two new private composition modules, `core/workflow/execution/workflow_facade.py`, `core/bootstrap/workflow_providers.py`, and potentially `interfaces/cli/bootstrap/container.py` only where duplicate assembly is confirmed.
  - Required regression surfaces: bootstrap observability, CLI runtime inspection, shared EventBus/control identity, workflow registration/execution, replay/checkpoints, completed-run persistence, policy/governance, telemetry subscribers, and backtesting composition.

  **C. Approved broadened RuntimeState aggregate retirement**

  The follow-up audit showed that the portfolio conflict is only one symptom of an unfinished alternate runtime data-flow design:

  - production intelligence nodes use `RuntimeContext.node_outputs` as their upstream execution-data bus;
  - workflow inputs are read from `RuntimeState.shared_state`;
  - no production node updates or consumes `RuntimeState.market`, `.portfolio`, `.risk`, or `.strategy`;
  - `RuntimeNodeOutput.namespace_updates` and `RuntimeContext.merge_state()` are exercised only by the example workflow;
  - `consumes_namespaces` and `produces_namespaces` are copied into execution-plan metadata but are not enforced runtime contracts;
  - `RuntimeState.runtime_mode` and `.execution_id` duplicate `RuntimeContext.mode` and `.execution_id`;
  - `RuntimeState.step_index`, `.timestamp`, and `.metadata` do not participate meaningfully in execution or replay.

  The user has now explicitly approved direct production changes under `core/` to retire this unused aggregate rather than converging only the two portfolio models. Step 9 is authorized to:

  1. Preserve `RuntimeContext` as the canonical checkpoint, replay, resume, and completed-run execution snapshot.
  2. Move the actually used workflow-input payload from `RuntimeState.shared_state` to `RuntimeContext.workflow_inputs`.
  3. Remove `RuntimeState`, `MarketState`, runtime `PortfolioState`, `RiskState`, and `StrategyState` after characterization tests confirm no production decision depends on them.
  4. Remove `RuntimeContext.merge_state()`, `RuntimeNodeOutput.namespace_updates`, runtime-node namespace declarations, and corresponding execution-plan namespace metadata rather than retaining a dead compatibility mechanism.
  5. Remove duplicated or unused runtime-state identity, timestamp, step, and metadata fields. Rename `state_version` to `context_version` because the counter already versions the complete runtime context rather than a distinct business state.
  6. Keep `domain.portfolio.models.PortfolioState` as the sole canonical portfolio business model without embedding a fabricated default portfolio into new runtime contexts.
  7. Apply a deterministic PostgreSQL completed-run JSON migration that preserves real workflow inputs and execution evidence while removing obsolete default state payloads. Missing business values must not be invented.
  8. Update checkpoint serializers and tracked fixtures to the new context schema. Unsupported historical local checkpoint schemas must fail with an explicit version error; no permanent legacy-state adapter or compatibility wrapper may be introduced.

  This supersedes the earlier portfolio-only deferral. The broader change must still be implemented in small reviewed slices with characterization, migration, replay, and RAG shared-runtime regression gates before source modules are deleted.

  **D. Approved candidate for direct sentiment persistence contract cleanup**

  The physical `sentiment_snapshots` table already uses canonical columns. Step 15 may directly align the typed record and serializer with those existing columns, without a database migration or compatibility aliases:

  - `sentiment_regime` -> `market_regime`;
  - `composite_sentiment_score` -> `composite_sentiment`;
  - `component_scores` -> `fusion_components`;
  - `inputs` -> `providers_payload`;
  - `outputs` -> `sentiment_payload`;
  - add the already-persisted first-class fields `market_bias`, `directional_signal`, `momentum`, `stability`, and `divergence`;
  - add typed-record access to `features_payload` and `raw_payload`;
  - keep `metadata` only for genuinely diagnostic/extension metadata.

  The serializer, repository, application persistence service, structured RAG source adapter, and their tests must migrate in one change. The RAG pipeline behavior must not be refactored; only its direct typed-record field access may change so the repository compiles against the canonical record.

  **E. Approved portfolio equity-history schema operation**

  Do not add the previously expected opaque `portfolio_history_payload` column to portfolio snapshot tables. The Alpaca/provider history series is semantically different from a full `PortfolioState` snapshot and cannot safely be stored in the existing non-null snapshot schema without invented values.

  Step 15 may instead add one normalized append-only `portfolio_equity_history_points` table with:

  - `portfolio_equity_history_point_id` primary key;
  - `account_id`, `source`, and `timeframe`;
  - timezone-aware `observed_at`;
  - `equity`, `profit_loss`, `profit_loss_pct`, and `base_value` using the repository's established numeric-column convention;
  - optional purpose-named `cashflow_payload` only for the provider's variable activity-series boundary;
  - `workflow_name`, `execution_id`, `runtime_id`, and `node_name` lineage;
  - `row_created_at` and `row_updated_at`;
  - uniqueness on `(account_id, source, timeframe, observed_at)` and an account/observation-time read index.

  Add matching frozen/slotted persistence records, serializer, repository contract/adapter, application persistence operation, and deterministic tests. The portfolio service must normalize provider arrays into typed points before the persistence boundary. No backfill is proposed because historical provider series were not previously stored canonically, and values must not be inferred from full portfolio snapshots.

  This migration is additive. No existing table, column, or historical row will be dropped or renamed in this approved schema package. If Step 15 discovers a justified destructive rename/drop beyond this list, it requires another explicit approval before migration code is written.

  **F. Blast radius and required verification**

  - Runtime/composition risk: `RuntimeEngine` health 2.39 at the 99.8th hotspot percentile; `WorkflowBootstrap` health 1.69 with 25 dependents; `WorkflowFacade` health 1.90. Changes must remain behavior-preserving and be split into independently reviewable slices.
  - State risk: `RuntimeState` has 15 structural dependents and is a checkpoint/completed-run serialization boundary. Retirement must therefore begin with payload characterization, direct caller migration, and deterministic completed-run migration rather than source deletion first.
  - Persistence risk: portfolio-state ORM models are in the 96th hotspot percentile; sentiment records/models affect repositories, application persistence, model exports, health checks, and curated RAG source adaptation.
  - Required deterministic gates for core changes: focused characterization tests after each extraction, complete runtime/workflow/control/replay/checkpoint/telemetry suites, complete unit suite, Ruff fix/format, MyPy, duplication checks for any new helper, `git diff --check`, and Graphify update.
  - Required database gates when Step 15 begins: PostgreSQL availability notice before execution, blank-database upgrade, single-head check, downgrade/upgrade cycle for the new revision, `pytest-alembic` ORM-divergence checks, repository integration tests, and idempotent duplicate-point tests.

  **G. Rollback strategy**

  - Runtime and workflow refactors will be kept in separate reviewable commits/slices. Rollback restores the previous private implementation while leaving all public contracts and persisted data unchanged.
  - The two currently duplicated RuntimeEngine dictionary keys will be covered by behavior tests before removal so rollback does not reintroduce silent ambiguity.
  - Sentiment cleanup is a coordinated source-contract rollback only because the physical schema is already canonical. Record, serializer, repository consumers, and tests must be reverted together.
  - The portfolio equity-history migration downgrade drops only the newly added table and its indexes. Before any production downgrade, writes must be disabled and any newly collected history exported; no existing portfolio snapshot data is touched.
  - Runtime-state retirement rollback restores the prior source contracts and deterministically reconstructs `state.shared_state` from `workflow_inputs`. The migration must abort before mutation if any historical non-default market, portfolio, risk, or strategy namespace is discovered, because those values cannot be discarded or reconstructed by assumption.

  **Approval granted**

  On 2026-06-27 the user explicitly authorized:

  1. the Step 7 internal `RuntimeEngine` decomposition in section A;
  2. the Step 8 internal workflow composition/facade stabilization in section B;
  3. the broadened Step 9 retirement of the complete unused `RuntimeState` business aggregate and namespace-state mechanism in section C;
  4. the Step 15 direct sentiment typed-record/serializer cleanup in section D;
  5. the Step 15 additive `portfolio_equity_history_points` schema and persistence path in section E;
  6. production changes under `core/` required by these approved steps and continuation through the remaining plan steps, while preserving one-step-at-a-time review and confirmation.

  **Step 6 status**

  - Documentation, risk analysis, and the broadened runtime-state architecture decision are complete.
  - The approved production work remains sequenced by the implementation plan; Step 7 is the next execution step.
  - Changes outside the exact approved core, runtime-state, sentiment, and portfolio-history package still require a new destructive-change approval where applicable.

  ### Step 7 — Decompose RuntimeEngine internally (Completed 2026-06-27)

  **Implementation**

  - Preserved `RuntimeEngine` as the sole canonical executor and kept its constructor, node registration methods, `execute()` signature, public cancellation-output constant, checkpoint behavior, and root-trace ownership unchanged.
  - Reduced `core/runtime/execution/runtime_engine.py` from 1,442 lines to 279 lines by moving private responsibilities into five focused collaborators:
      - `runtime_execution_context.py` — immutable, slotted `RuntimeExecutionLocation` and `RuntimeNodeInvocation` parameter objects;
      - `runtime_event_publisher.py` — canonical node/output/progress `RuntimeEvent` construction and publication through the existing shared `EventBus`;
      - `runtime_node_executor.py` — child trace-context creation, node invocation, timeout handling, retries, retry events, and execution metadata;
      - `runtime_state_transitions.py` — output application, dependency readiness, terminal-state classification, completed/failed/skipped-node calculation, and cancellation-output recognition;
      - `runtime_wave_executor.py` — deterministic wave scheduling, disabled/missing/dependency-failed handling, lifecycle hooks, artifact persistence, result finalization, and cooperative pause/cancel boundaries.
  - Kept top-level workflow lifecycle coordination, wave iteration, checkpoint policy, terminal workflow control transitions, and collaborator composition in `RuntimeEngine`; no second runtime engine, facade, compatibility layer, or alternate execution path was introduced.
  - Preserved result-order application after `asyncio.gather`, so parallel nodes still execute concurrently while their outputs are merged deterministically in execution-plan order.
  - Preserved workflow and per-node trace contexts across asynchronous tasks, artifact persistence, lifecycle hooks, emitted node events, progress events, checkpoints, and terminal control transitions.
  - Source inspection showed that the previously suspected duplicate `runtime_id` event attribute and duplicate `node_outputs` update entry were not present in the current working-tree implementation. The extraction nevertheless centralizes each event field and context-update key in one implementation so those duplicate-key risks cannot remain distributed across the engine.

  **Risk and architecture review**

  - Repowise preflight classified the original file as a critical god class with a **2.39 health score**, **1,248 class NLOC**, **33 methods**, **99.8th-percentile churn**, and an overall blast-radius risk score of **10.0**.
  - The active architecture decision, `Runtime execution and workflow boundaries`, explicitly allows internal decomposition while requiring `RuntimeEngine` to remain the single execution path; the implementation conforms to that decision.
  - Reviewed historical co-change and impact files including `runtime_telemetry_hook.py`, workflow providers/bootstrap, `WorkflowEngine`, workflow control/event tests, and telemetry integrations. No production co-change was required because their consumed public contracts and shared object identities remained unchanged.
  - No external service was required for this step.

  **Verification**

  | Check | Result |
  | --- | --- |
  | Focused runtime execution/control/event/trace/replay/telemetry regression set | **27 passed** |
  | Expanded runtime, artifact, checkpoint, lifecycle, workflow, plugin, Dishka, and telemetry set | **108 passed** |
  | Broader runtime/core-workflow/bootstrap/plugin/telemetry regression set | **129 passed**, 5 third-party deprecation/model warnings |
  | `ruff check . --fix` | Passed |
  | `ruff format .` | Passed; 1,061 files unchanged |
  | `mypy . --explicit-package-bases` | Passed; no issues in 1,058 source files |
  | `npx jscpd core/runtime/execution` | Passed; **0 clones / 0.00% duplication** |
  | Pylint duplicate-code check for `core/runtime/execution` | Passed; **10.00/10** |
  | `git diff --check` | Passed |
  | `graphify update .` | Passed; 1,059 files extracted, graph rebuilt with 17,133 nodes and 73,740 edges |

  **Step 7 status**

  - The approved `RuntimeEngine` decomposition is complete and behavior-preserving across the tested runtime, control, replay, checkpoint, event, telemetry, artifact, plugin, and workflow surfaces.
  - Step 8 — workflow composition and facade stabilization — has not begun and requires user confirmation.

  ### Step 8 — Stabilize workflow composition and facade delegation (Completed 2026-06-27)

  **Implementation**

  - Added `core/workflow/bootstrap/workflow_runtime_components.py` with frozen, slotted typed contracts for:
      - `WorkflowFacadeConfig`;
      - `WorkflowBootstrapConfig`;
      - `WorkflowRuntimeOverrides`;
      - `WorkflowRuntimeComponents`.
  - Added `core/workflow/bootstrap/workflow_runtime_assembler.py` as the single implementation that assembles runtime, workflow, replay, checkpoint, control, EventBus, artifact, telemetry, observability, plugin, policy, governance, archive, and optional PostgreSQL runtime-persistence components.
  - Reduced `WorkflowBootstrap._build_runtime()` from the previously reported 158-line, CCN-37 composition method to a 41-line orchestration method over the typed assembler result.
  - Reduced `WorkflowFacade.create()` from the previously reported 109-line competing composition method to a 40-line delegation into the canonical assembler while preserving its public signature and stable application-boundary role.
  - Added `WorkflowBootstrap.assemble()` for DI composition without edge workflow registration or plugin autoload, and included the canonically composed `ReplayEngine` in `WorkflowBootstrapResult`.
  - Reworked `WorkflowInfrastructureProvider` into accessors over one app-scoped `WorkflowBootstrapResult`. EventBus, control manager, archive, lifecycle, observability, telemetry, policies, governance, node factory, plugin loaders/manager, and facade are now identities from the same bootstrapped object graph rather than independently constructed provider objects.
  - Reworked CLI bootstrap to install that same `WorkflowInfrastructureProvider`, bind the completed Dishka container before lazy runtime resolution, resolve the canonical `WorkflowBootstrapResult`, and register built-in/plugin workflows through its facade. The prior separate CLI `WorkflowBootstrap` graph was removed.
  - Preserved synchronous and asynchronous CLI entry points and direct workflow factories; all production runtime construction searches now resolve through `WorkflowBootstrap`, `build_workflow_runtime`, or `WorkflowInfrastructureProvider` rather than a parallel interface-owned graph.
  - Delegated facade workflow registration to `WorkflowService.register_workflow()` after the existing facade policy and governance gates. Existing execution, control, replay, checkpoint, and completed-run behavior remains behind the stable facade boundary.
  - Corrected a final observability identity edge case: one canonical `ObservabilityManager` is always shared by `RuntimeEngine`, the facade, bootstrap result, and Dishka. `enable_observability=False` suppresses exporter/sink/plugin instrumentation while retaining the runtime tracing dependency; it no longer creates a hidden second manager.
  - No compatibility bootstrap adapter, alternate runtime engine, parallel EventBus/control manager, or interface-owned telemetry/persistence graph was introduced.

  **Architecture and risk review**

  - Repowise preflight classified `WorkflowBootstrap` and `WorkflowFacade` as approximately 98th-percentile churn hotspots with an overall blast-radius risk score of **10.0**. The implementation therefore retained their public contracts and limited changes to composition/delegation internals and required co-change tests.
  - Repowise's immediate post-edit health response still referenced the deleted 158-line `_build_runtime` at its historical line range, so that particular finding was identified as stale index data rather than accepted as a current-code measurement. Direct AST inspection reports `_build_runtime()` at 41 lines and `WorkflowFacade.create()` at 40 lines.
  - Scoped JSCPD reports 15 structural/import/delegation clones and 4.65% duplicated lines. Pylint duplicate-code remains **9.91/10**. The remaining findings are public signature forwarding, typed bundle field overlap, imports, and facade-to-service delegation; the prior duplicate runtime infrastructure construction in bootstrap/providers/facade/CLI is removed.
  - Graphify confirms the assembler and typed component bundle are connected to the existing runtime, workflow, replay, policy, governance, telemetry, plugin, persistence, and CLI communities. No external service was required.

  **Verification**

  | Check | Result |
  | --- | --- |
  | Final shared bootstrap/facade/provider/CLI/observability identity and real-node suite | **26 passed**, 1 third-party deprecation warning |
  | Broader workflow, governance, policy, plugin, telemetry, bootstrap, CLI, checkpoint, and replay regression suite | **62 passed**, 5 existing third-party warnings |
  | Backtesting CLI composition regression suite | **4 passed**, 1 existing third-party warning |
  | `ruff check . --fix` | Passed |
  | `ruff format .` | Passed; 1,063 files unchanged |
  | `mypy . --explicit-package-bases` | Passed; no issues in 1,060 source files |
  | Pylint duplicate-code audit for changed composition areas | **9.91/10**; only structural/public-delegation findings remain |
  | `git diff --check` | Passed |
  | `graphify update .` | Passed; 1,061 files extracted, graph rebuilt with 17,190 nodes and 75,091 edges |

  **Step 8 status**

  - Workflow composition now has one canonical typed assembler and one shared app-scoped runtime object graph across bootstrap, Dishka providers, facade creation, CLI, and backtesting entry paths.
  - Runtime control, EventBus, observability, telemetry, persistence, plugin, policy, governance, checkpoint, and replay identities are covered by focused regression assertions.
  - Step 9 — retire the unused `RuntimeState` aggregate and stabilize replay/checkpoint persistence around `RuntimeContext` — has not begun and requires user confirmation.

  ### Step 9 — Retire the unused RuntimeState aggregate and stabilize replay, checkpoints, events, and control (Completed 2026-06-27)

  **Implementation**

  - Replaced the unfinished dual-state design with `RuntimeContext` as the sole canonical workflow execution snapshot. The context now carries an explicit `workflow_inputs` boundary payload and no longer embeds a separate `RuntimeState` business aggregate.
  - Introduced runtime-context schema version **2** through `RUNTIME_CONTEXT_SCHEMA_VERSION`, renamed `state_version` to `context_version`, and added `UnsupportedRuntimeContextSchemaError` so unsupported local checkpoint payloads fail explicitly instead of being interpreted through a permanent compatibility adapter.
  - Removed the unused runtime business-state source contracts:
      - `BaseState`;
      - `RuntimeState`;
      - `MarketState`;
      - runtime `PortfolioState`;
      - `RiskState`;
      - `StrategyState`.
  - Preserved `domain.portfolio.models.PortfolioState` as the sole canonical portfolio business model.
  - Removed the unused namespace-state mechanism from runtime nodes, node outputs, context transitions, workflow compilation/execution-plan metadata, examples, plugins, artifacts, telemetry, replay, and tests:
      - `RuntimeContext.merge_state()`;
      - `RuntimeNodeOutput.namespace_updates`;
      - `RuntimeNode.consumes_namespaces` and `produces_namespaces`;
      - namespace update serialization and execution-plan fields.
  - Renamed the Step 7 transition collaborator to `runtime_context_transitions.py` / `RuntimeContextTransitions` so the runtime no longer describes context updates as mutations of a competing business-state aggregate.
  - Migrated workflow callers, including morning-report execution and deterministic backtesting, from `runtime_state`/`shared_state` parameters to the canonical `workflow_inputs` contract.
  - Updated checkpoint, replay, control, progress, completed-run archive/serializer/model, CLI rendering, and report paths to use the narrowed schema while preserving node outputs, artifacts, errors, trace data, simulation time, and execution attribution.
  - Removed the unused package-level `StateManager` re-export from `core.runtime.state`; direct module imports remain canonical and the change eliminates a real circular import exposed by the full regression run.

  **PostgreSQL migration**

  - Added Alembic revision `a7b8c9d0e1f2` to migrate persisted completed-run JSON to runtime-context schema 2.
  - The migration performs a complete preflight before mutating rows and aborts if it finds non-default historical market/portfolio/risk/strategy namespace data or persisted node namespace updates. This prevents silent loss of business data.
  - Successful upgrades preserve workflow identity, workflow inputs, node outputs, artifacts, errors, trace context, simulation time, and context version; deterministic backtest step/time values are retained under `workflow_inputs.backtest`.
  - The downgrade deterministically reconstructs the former default namespaces and empty namespace-update fields. It does not invent non-default business values.
  - Applied the migration to the running local PostgreSQL database. The database advanced from `f6a7b8c9d0e1` to `a7b8c9d0e1f2 (head)`. The live database contained no completed-run rows requiring conversion, and a post-migration audit found zero legacy context rows.

  **Architecture and risk review**

  - Repowise reports `RuntimeContext` as a 94th-percentile hotspot with 70 structural dependents and `StateManager` as a 96th-percentile, increasing-churn hotspot. The implementation therefore migrated direct callers and exercised the transitive runtime, checkpoint, replay, control, workflow, persistence, CLI, and intelligence surfaces rather than relying on source-level replacement alone.
  - Repowise's filename-pairing heuristic reports no paired test file for `runtime_context.py`, but direct schema tests now exist in `tests/unit/core/runtime/state/test_runtime_context_schema.py`, with additional state-manager, persistence, checkpoint, replay, workflow, and migration coverage. Its PR risk result independently reports no test gap for the runtime-context target.
  - A post-change Repowise dead-code scan found no remaining high-confidence dead code in `core/runtime/state` under the selected 0.7 confidence threshold.
  - Existing RuntimeEngine and ReplayEngine health debt remains tracked for later stabilization steps. Repowise still reports historical large-class/method and churn findings; Step 9 did not broaden into another execution-engine refactor after the completed Step 7 decomposition.
  - A final source audit found no production references to the removed runtime-state, namespace-update, namespace-declaration, merge-state, shared-state, or state-version contracts. The only non-migration match is a test assertion proving `state_version` is absent from schema-2 serialization.

  **Verification**

  | Check | Result |
  | --- | --- |
  | Focused runtime-context/state contract suite | **78 passed** |
  | Replay, checkpoint, control, and progress suite | **47 passed** |
  | State and completed-run persistence suite | **45 passed** after removing one obsolete `.state` assertion |
  | Complete non-RAG, non-database suite | **1,530 passed, 5 skipped**, 6 existing warnings |
  | Runtime-context migration tests | **3 passed** |
  | Complete database migration suite against live PostgreSQL | **9 passed**, 10 existing warnings |
  | Live PostgreSQL `alembic upgrade head` | Passed; database at `a7b8c9d0e1f2 (head)` |
  | `alembic check` | Passed; no new upgrade operations detected |
  | `ruff check . --fix` | Passed |
  | `ruff format . --check` | Passed; 1,060 files already formatted |
  | `mypy . --explicit-package-bases` | Passed; no issues in 1,057 source files |
  | Changed-file Python compilation | Passed |
  | Legacy runtime-state contract audit | Passed; no production references remain |
  | `git diff --check` | Passed |
  | `graphify update .` | Passed; 1,058 files extracted, graph rebuilt with 17,227 nodes and 75,019 edges |

  **Environmental note**

  - An unrestricted all-suite attempt reached a live Neo4j RAG integration test and waited on the unavailable external service. Step 9 excludes RAG implementation, so the authoritative broad gate was the complete non-RAG/non-database suite plus the separately executed live PostgreSQL database suite. No Qdrant, Neo4j, or BGE service was required to verify the RuntimeContext migration.

  **Step 9 status**

  - The approved `RuntimeState` aggregate and namespace-state mechanism are retired without compatibility wrappers.
  - Runtime inputs, execution evidence, checkpoints, replay, completed-run persistence, control, progress, CLI rendering, and backtesting now use the canonical runtime-context schema.
  - The schema migration is tested and applied to PostgreSQL, and all Step 9 quality gates are green.
  - Step 10 — telemetry and observability hardening — has not begun and requires user confirmation.

  ### Step 10 — Harden telemetry and observability (Completed 2026-06-29)

  **Implementation**

  - Added direct lifecycle, failure-policy, sink-isolation, trace-context, flush, shutdown, and serialization tests for `ObservabilityManager`.
  - Added recursive telemetry sanitization at the logging and OpenTelemetry boundaries. Sensitive keys such as credentials, tokens, authorization values, cookies, and secrets are redacted without discarding legitimate measurement fields such as `token_count`.
  - Replaced the application-service emitter's repeated internal parameter flow with one frozen, slotted typed event contract while preserving the public `ApplicationServiceTelemetry` API.
  - Added canonical cancellation telemetry for application services and providers. `asyncio.CancelledError` is attributed, measured, emitted as `application.service.cancelled` or `integration.provider.cancelled`, and re-raised so cooperative cancellation semantics are preserved.
  - Extended domain metrics with bounded `success`, `failure`, and `cancelled` outcomes plus cancellation duration/count measurements for long-running service and provider operations.
  - Restricted Prometheus labels to a fixed low-cardinality allowlist. Unsupported labels—including raw prompts, symbols, URLs, exception messages, request/execution IDs, and arbitrary payload keys—are rejected rather than exported as unbounded time-series dimensions.
  - Propagated canonical trace IDs, span IDs, and parent-span IDs through runtime progress, control, wave, node, output, service, provider, and intelligence telemetry events.
  - Corrected the OpenTelemetry adapter to export each short-lived `TelemetryEvent` as an independent span in Polaris's canonical trace. Logical runtime span relationships remain explicit attributes; the adapter no longer fabricates dangling or duration-invalid OpenTelemetry parents.
  - Added typed readiness contracts and a focused `PlatformReadinessService` for PostgreSQL, telemetry exporters, providers, and runtime persistence. PostgreSQL readiness requires explicit connectivity, migration, and ORM-metadata probes; RAG readiness remains outside this plan.
  - Added a live PostgreSQL integration contract proving that one canonical event/trace identity, lineage, duration, status, and attributes persist together through the real telemetry repository.

  **Architecture and risk review**

  - Repowise classified the OpenTelemetry adapter as an increasing-churn hotspot (approximately 88% hotspot score) and `DomainMetrics`/runtime telemetry as churn-heavy. Changes were therefore limited to trace correctness, cancellation coverage, cardinality, sanitization, readiness, and direct co-change tests rather than a broad telemetry redesign.
  - The OpenTelemetry boundary intentionally remains an adapter over Polaris's typed telemetry model; OpenTelemetry does not replace `TelemetryEvent`, `RuntimeEvent`, `TraceContext`, EventBus, or PostgreSQL telemetry persistence.
  - The CLI continues through `WorkflowCommandService`, canonical Dishka composition, `WorkflowFacade`, and the shared bootstrapped observability graph. API and scheduler packages currently contain no runnable workflow entry point to exercise; no speculative interface or parallel telemetry path was added.
  - PostgreSQL telemetry persistence remains optional by deployment policy rather than being silently enabled for every bootstrap. The live gate composed the existing persistence sink explicitly and verified the production repository path.
  - No RAG service was required or exercised. PostgreSQL, Prometheus, and Jaeger were the only external services needed for the live validation.

  **Live correlated-trace verification**

  - Executed a deterministic non-RAG workflow containing runtime workflow/wave/node events, an application service call, an awaited provider call, an intelligence signal, progress/control events, structured logging, Prometheus metrics, Jaeger export, and PostgreSQL telemetry persistence.
  - Jaeger received **21 spans under one canonical trace ID** and contained all required runtime, application, provider, intelligence, and terminal progress operations with **no dangling-parent or clock-skew warnings**.
  - Prometheus reported the `polaris-runtime` target **up** while the validation exporter was active and scraped both `workflow_executions_total=1` and `integration_provider_calls_total=1` using the bounded label schema.
  - PostgreSQL returned correlated trace records with the same workflow, execution, runtime, trace, root-span, and node-span identity used by the runtime and Jaeger.
  - Structured logs showed attributable runtime, application, integration, and intelligence events with workflow/execution/node context and no secret-bearing values.
  - Temporary validation rows and scripts were removed after verification; no synthetic Step 10 workflow data was left in PostgreSQL or the repository.

  **Verification**

  | Check | Result |
  | --- | --- |
  | Focused telemetry/runtime/service/provider/readiness regression set | **75 passed** |
  | Complete unit suite | **1,470 passed**, 6 existing third-party/SQLAlchemy warnings |
  | Complete non-RAG integration suite with live PostgreSQL | **76 passed**, 1 existing third-party warning |
  | Live PostgreSQL telemetry persistence contract | Passed |
  | Live Prometheus scrape and bounded workflow/provider metrics | Passed |
  | Live Jaeger canonical trace audit | Passed; 21 correlated spans, no warnings |
  | Changed telemetry-area coverage gate | **94.17%** |
  | `ruff check . --fix` | Passed |
  | `ruff format .` | Passed; 1,066 files unchanged |
  | `mypy . --explicit-package-bases` | Passed; no issues in 1,063 source files |
  | `git diff --check` | Passed |
  | `graphify update .` | Passed; 1,064 files extracted, graph rebuilt with 17,304 nodes and 75,253 edges |

  **Step 10 status**

  - Core non-RAG telemetry now has tested trace correlation, structured redaction, bounded Prometheus cardinality, cancellation attribution, typed readiness, and live Jaeger/Prometheus/PostgreSQL verification.
  - Step 11 — dependency injection and application entry-point normalization — has not begun and requires user confirmation.

  ### Step 11 — Normalize dependency injection and application entry points (Completed 2026-06-29)

  **Implementation**

  - Consolidated synchronous and asynchronous application composition in `core/bootstrap/di_providers.py`. Canonical provider selection is now shared, optional providers are explicit inputs, and both application-container variants use the same provider graph instead of allowing interface-owned registration lists to diverge.
  - Added canonical owned request-scope helpers for both runtime shapes:
      - `application_sync_request_scope()` owns the synchronous workflow-runtime container and invocation request scope;
      - `application_request_scope()` owns the asynchronous PostgreSQL/RAG application container and request scope.
  - Replaced the CLI's manual Dishka container construction, duplicated provider-profile branching, and interface-owned portfolio repository with `application_sync_request_scope()`. The CLI now supplies only boundary settings and workflow bootstrap configuration, resolves dependencies from the owned request scope, and cannot construct providers, repositories, application services, vendor clients, or runtime infrastructure directly.
  - Moved the invocation-local portfolio repository to `core/storage/persistence/portfolio/in_memory_portfolio_state_repository.py` and registered it through `InMemoryCoreStorageDIProvider`. PostgreSQL-backed portfolio storage remains request-scoped through `CoreStorageDIProvider` for asynchronous application operations.
  - Added `ApplicationPersistenceDIProvider` for request-scoped backtest and morning-report persistence services. CLI persistence commands now resolve those services through the canonical asynchronous application scope rather than constructing `AsyncSessionLocal`, PostgreSQL repositories, and services manually.
  - Registered `BacktestApplicationService` in Dishka and changed the backtest CLI path to resolve it and `ServiceRunner` from the request scope. The canonical request/result service now executes through `ServiceRunner`; report assemblers and renderers remain direct transformation/presentation collaborators rather than being forced into the service lifecycle.
  - Migrated workflow execution, workflow listing/description, completed-run inspection/cleanup, runtime inspection, morning-report persistence, and RAG command dependency resolution to the canonical scope helpers. Progress/control subscriptions remain invocation-owned and are released before the containing scope closes.
  - Preserved synchronous Dishka for workflow runtime-node resolution because `RuntimeNodeFactory.create_from_type()` is a synchronous factory contract. Asynchronous Dishka is limited to request-scoped persistence and RAG operations; no blocking bridge, parallel runtime, or compatibility container was introduced.
  - Confirmed that `interfaces/api/` and `interfaces/scheduler/` currently contain no executable Python entry points. No speculative interface implementation was added.

  **Resource lifetime and architecture review**

  - Dishka application containers and request scopes now close deterministically on success and exceptions, with direct lifecycle tests for both synchronous CLI/runtime and asynchronous application scopes.
  - PostgreSQL sessions remain request-scoped async-generator resources. Qdrant and Neo4j clients remain application-scoped async-generator resources with explicit close paths. Non-RAG HTTP clients use method-local `httpx.AsyncClient` context managers.
  - Workflow telemetry/exporter shutdown remains owned by the bootstrapped workflow infrastructure generator; existing bootstrap tests verify force-flush, shutdown, and Prometheus exporter termination.
  - Inspected the current external SDK clients used by the integration layer; the wrapped Massive, Alpaca, and NewsAPI SDK objects expose no `close`, `aclose`, or `shutdown` lifecycle API that the container could invoke.
  - Repowise confirmed the active `Dishka composition and request scopes` decision: interfaces own request-scope entry/exit while canonical providers own composition. Its post-change health response still referenced the deleted `_build_cli_container()` at historical line ranges, so those method-complexity findings are stale index data rather than current source findings. Direct source and interface-construction audits confirm that method and the duplicated provider graph are absent.
  - The async application scope intentionally does not attempt to resolve the entire synchronous workflow/intelligence graph. If a future API or scheduler executes workflows through async Dishka, runtime-node resolution needs a first-class asynchronous boundary rather than injecting request-scoped async dependencies into the existing synchronous factory.
  - No external service was required for this step.

  **Verification**

  | Check | Result |
  | --- | --- |
  | Canonical DI scope lifecycle and CLI provider-profile tests | **6 passed**, 1 existing third-party warning |
  | Expanded CLI/workflow/backtest/RAG/bootstrap/real-node regression set | **67 passed**, 1 existing third-party warning |
  | Workflow/RAG/bootstrap observability integration regression set | **16 passed**, 5 existing third-party warnings |
  | Complete unit suite | **1,474 passed**, 6 existing third-party/SQLAlchemy warnings |
  | `polaris inspect runtime --format json` | Passed; one workflow registered with policy, governance, telemetry, and observability composed |
  | Interface construction audit | Passed; no interface constructs application services, providers, vendor clients, repositories, database sessions, containers, or runtime infrastructure |
  | Resource-lifetime audit | Passed for Dishka scopes, PostgreSQL sessions, Qdrant/Neo4j clients, HTTP clients, and telemetry exporters |
  | `ruff check . --fix` | Passed |
  | `ruff format .` | Passed; 1,069 files unchanged |
  | `mypy . --explicit-package-bases` | Passed; no issues in 1,066 source files |
  | Pylint duplicate-code audit for changed DI/CLI areas | Passed; **10.00/10** |
  | Scoped JSCPD audit | 3 pre-existing CLI presentation/command clones; **1.52% duplicated lines**, no new DI composition clone |
  | `git diff --check` | Passed |
  | `graphify update .` | Passed; 1,067 files extracted, graph rebuilt with 17,386 nodes and 75,575 edges |

  **Step 11 status**

  - Runnable CLI, workflow, backtesting, persistence, and RAG boundaries now enter through canonical Dishka-owned scopes and resolve dependencies rather than constructing them.
  - Application services use `ServiceRunner` where the canonical request/result lifecycle applies; non-service orchestrators and presentation components retain lifecycle-appropriate execution.
  - Step 12 — application-service and analysis-module stabilization — has not begun and requires user confirmation.

  ### Step 12 — Stabilize application services and analysis modules (Completed 2026-06-30)

  **Implementation**

  - Replaced the generic dictionary payloads returned by technical, macro, market-events, news, sentiment, and portfolio services with frozen, slotted typed result contracts:
      - `TechnicalAnalysisResult`;
      - `MacroAnalysisResult`;
      - `MarketEventsResult`;
      - `NewsResult` and `NewsArticle`;
      - `SentimentSnapshotResult`;
      - `PortfolioAnalysisResult`.
  - Kept `to_dict()` and `to_list()` only as explicit serialization-boundary methods. Intelligence and portfolio consumers now use typed fields directly and serialize only when constructing LLM inputs or `RuntimeNodeOutput` payloads.
  - Corrected request validation in technical, market-events, news, sentiment, and portfolio services so invalid request payloads return immediately instead of falling through into provider execution.
  - Removed internal `round()` calls from the scoped application services and deterministic analyzers. Full numeric precision is now preserved through technical, macro, market-events, news, sentiment, portfolio, and backtesting calculations; presentation remains responsible for rounding.
  - Hardened provider-failure behavior for macro, news, and sentiment orchestration:
      - partial provider failures are logged with provider attribution and represented as typed partial results;
      - empty successful responses remain valid empty results;
      - total provider outages raise instead of being silently converted into successful empty data;
      - `asyncio.CancelledError` is preserved;
      - stale source timestamps are retained rather than replaced with current time.
  - Corrected the canonical macro volatility key from `vix_macro` to `vix` and prevented failed macro series from entering numeric analyzers as embedded error dictionaries.
  - Removed the synthetic empty news article previously introduced through `raw_news=[{}]`; an empty upstream response now produces zero articles.
  - Corrected sentiment score semantics: `SentimentSnapshotService` and `SentimentAgent` now consistently use the canonical `[-1.0, 1.0]` range without re-normalizing an already normalized score. Fusion and component values retain full precision.
  - Split market-event volatility into correctly typed concepts: `volatility_forecast` remains the categorical forecast, while `volatility_pressure` is the first-class numeric signal consumed by strategy synthesis. The strategy agent no longer relies on a legacy alias or numeric conversion of a categorical field.
  - Corrected `FundamentalAgent` to consume the canonical macro result and `economic_regime` field rather than querying the nonexistent `macro_regime` key. Direction and confidence now use the actual regime vocabulary.
  - Updated technical, fundamental, sentiment, portfolio-state, and strategy-synthesis consumers and their tests for the typed service contracts. No compatibility result shim was introduced.
  - Narrowed broad exception handling in deterministic sentiment and backtesting calculations to the specific conversion failures they can handle.

  **Audit findings and bounded follow-ups**

  - Confirmed that canonical breadth fields, including `ad_line_trend_score`, remain consistently owned by the technical analysis path. No `legacy_ad_line_trend_score` reference remains. Derived EMA values used internally by technical analyzers are not duplicate provider fields and were retained.
  - Repowise's unused-function findings for technical and portfolio analyzers were false positives caused by callable injection and service composition. Direct source inspection confirmed the analyzers are imported and executed, so none were deleted.
  - Repowise continues to classify portfolio, macro, technical, fundamental, sentiment, and strategy-synthesis files as high-churn or high-coupling hotspots. Step 12 kept provider orchestration in services and added direct regression coverage rather than introducing a new orchestration abstraction.
  - `MacroService` still owns an `httpx.AsyncClient`, which violates the preferred service → provider → client boundary. Correcting that requires an integration-layer provider/client contract change and is intentionally deferred to Step 13 rather than broadening this application-service step.
  - Strategy synthesis and several intelligence agents retain pre-existing method-size/complexity debt. Their typed-contract co-changes in this step were surgical; broader intelligence decomposition remains assigned to the later intelligence stabilization step.

  **Verification**

  | Check | Result |
  | --- | --- |
  | Focused deterministic service/analyzer regression set | **69 passed** |
  | Complete unit suite | **1,491 passed**, 6 existing third-party/SQLAlchemy warnings |
  | `ruff check . --fix` | Passed; 4 issues fixed |
  | `ruff format .` | Passed; 3 files reformatted |
  | Final Ruff lint and formatting checks | Passed; 1,071 files formatted |
  | `mypy . --explicit-package-bases` | Passed; no issues in 1,068 source files |
  | `git diff --check` | Passed |
  | `graphify update .` | Passed; 1,069 files extracted, graph rebuilt with 17,470 nodes and 76,303 edges |

  **Environmental note**

  - An unrestricted full-suite attempt entered live RAG/LLM integration tests. It failed because Neo4j was unavailable and then blocked on an Ollama request, so it was interrupted after **59 passed, 17 skipped, 1 external-service failure**. These live RAG services are outside Step 12; the complete unit suite and scoped deterministic service/analyzer suite are the authoritative gates for this step.

  **Step 12 status**

  - Application-service result contracts are strongly typed, internal precision is preserved, provider failures are explicit, optional/empty/partial results are deterministic, and the verified score/key mismatches are corrected.
  - Canonical breadth ownership is unchanged and no falsely reported analyzer was deleted.
  - Step 13 — integration clients and providers stabilization, including correction of the remaining macro transport-boundary violation — has not begun and requires user confirmation.

  ### Step 13 — Macro service/provider/client boundary subtask (Completed 2026-06-30)

  **Implementation**

  - Removed HTTP transport and concurrency ownership from `MacroService`. The service now performs one typed `MacroProvider.get_macro_snapshot()` call and remains responsible only for deterministic macro-analysis orchestration.
  - Replaced the parameter-level macro provider API with one stable platform-facing aggregate contract returning the new frozen, slotted `MacroDataSnapshot` domain object.
  - Moved FRED series selection and vendor-response normalization into `LiveMacroProvider`. Partial series failures are attributed through structured warning logs and `failed_fields`; a total provider outage raises instead of becoming a successful empty snapshot.
  - Moved HTTP lifecycle and concurrency into `FredMacroClient`. One method-local `httpx.AsyncClient` connection pool now executes all requested FRED series concurrently with `asyncio.gather`, preserves input order, isolates ordinary per-series failures, emits safe error descriptions that exclude credential-bearing request URLs, and propagates cancellation.
  - Kept raw historical FRED payloads confined to the vendor client boundary. SDK/transport types no longer cross the provider contract or enter the application service.
  - Updated inflation, Federal Reserve, liquidity, and yield-curve analyzers to consume the typed snapshot directly rather than generic dictionaries.
  - Updated live, backtest, and simulated macro providers to the same aggregate typed contract. The backtest path remains deterministic and is observed through the existing canonical provider telemetry wrapper.
  - Preserved the external/runtime serialization keys through `MacroDataSnapshot.to_dict()`, including the established `2y_treasury` and `10y_treasury` boundary names. No compatibility provider or legacy transport adapter was introduced.

  **Architecture and risk review**

  - Repowise preflight classified `MacroService` and the live/backtest macro providers as low-health, high-churn files. The change therefore stayed limited to the verified transport-boundary violation and its direct typed-contract consumers rather than broadening into unrelated macro algorithms.
  - The implementation follows the canonical `Application Service → Provider → Client → External System` dependency direction. `MacroService` no longer imports `httpx`, creates an HTTP client, knows FRED series identifiers, or schedules vendor calls.
  - Aggregate provider telemetry measures the complete normalized macro operation, while per-series failures retain field and FRED-series attribution in structured logs. Existing HTTP/OpenTelemetry instrumentation preserves trace context across the `asyncio.gather` tasks.
  - Scoped JSCPD found no clones. Pylint reported only expected structural similarity between the live/backtest telemetry wrappers and between the deterministic fixture and its equality assertion; extracting those lines would add an unnecessary abstraction and was not justified.
  - No external service or live FRED credential was required; deterministic `httpx.MockTransport` and fake-provider tests exercise the complete boundary behavior.

  **Verification**

  | Check | Result |
  | --- | --- |
  | Focused macro client/provider/service/intelligence regression suite | **29 passed** |
  | Complete unit suite | **1,497 passed**, 6 existing third-party/SQLAlchemy warnings |
  | Synthetic-provider morning-report real-node integration | **1 passed**, 1 existing third-party warning |
  | Shared-client and real-concurrency contract | Passed; one `AsyncClient`, all requests begin before release |
  | Partial failure, safe error, cancellation, total-outage, and telemetry contracts | Passed |
  | Live/backtest typed-contract parity | Passed through deterministic provider tests |
  | `ruff check . --fix` | Passed |
  | `ruff format .` and final format check | Passed; 1 file reformatted, then 1,076 files compliant |
  | `mypy . --explicit-package-bases` | Passed; no issues in 1,073 source files |
  | Scoped JSCPD audit | Passed; **0 clones / 0.00% duplication** |
  | `git diff --check` | Passed |
  | `graphify update .` | Passed; 1,074 files extracted, graph rebuilt with 17,550 nodes and 76,562 edges |

  **Step 13 status**

  - The MacroService transport-boundary violation identified in Step 12 is resolved and verified.
  - The broader Step 13 audit and the planned YFinance/client-provider stabilization have not begun and still require the next explicit user confirmation.

  ### Step 13 — Stabilize integration clients and providers (Completed 2026-06-30)

  **Canonical contract changes**

  - Renamed the macro treasury serialization fields from `2y_treasury` and `10y_treasury` to the canonical Python-safe names `treasury_2y` and `treasury_10y` throughout the domain model, live/backtest/simulated providers, analyzers, tests, and runtime serialization boundary.
  - Removed the old serialized names directly. No compatibility alias, duplicate field, or migration shim remains. This supersedes the earlier Step 13 macro-subtask note that said the former boundary names were preserved.
  - Moved `SP500Data` out of the vendor-specific YFinance client and into `domain.market.models`, making the live, backtest, simulated, and PostgreSQL market-data providers share one frozen, slotted platform-owned contract.

  **YFinance stabilization**

  - Decomposed the former monolithic S&P 500 operation into focused constituent retrieval, batch history fetching, summary fetching, symbol normalization, breadth aggregation, market-cap ranking, and result-construction functions.
  - Added frozen, slotted request/options and internal result contracts for history queries, price frames, breadth counts, and client execution settings.
  - Replaced local-time epoch conversion with explicit UTC conversion and moved blocking HTML table parsing to `asyncio.to_thread`.
  - Bounded connection pooling, concurrency, request timeout, and retry attempts. Retry behavior is limited to transient transport failures, HTTP 429 responses, and server errors; cancellation always propagates.
  - Reused one semaphore across history and summary fan-out, retained aggregate provider telemetry through `record_provider_call`, and kept every HTTP request within the active traced provider operation.
  - Preserved the exact canonical breadth analytics contract: market-cap index, advances, declines, unchanged/active counts, 50/200-day participation, new highs/lows, net breadth, breadth percent, advance/decline line, and advance/decline ratio.
  - Preserved deterministic partial-response behavior: isolated symbol or summary failures are attributed and omitted/defaulted, while complete market-data failure raises instead of returning fabricated successful output.

  **Broader integration audit and fixes**

  - Corrected Fed and FRED event clients so concurrent source failures support valid partial success, total outages raise, cancellation propagates, duplicate parsing is removed, and missing source timestamps are not fabricated from the current clock.
  - Corrected Alpha Vantage earnings handling by removing mutable default symbol sets and synthetic blank-event records.
  - Corrected Finnhub news handling so caller parameters are not mutated, payloads are validated, partial source success remains usable, total failure raises, and cancellation propagates.
  - Removed error dictionaries and synthetic neutral/success fallbacks from NewsAPI and Fear & Greed clients so provider telemetry and application services receive real failures.
  - Removed presentation rounding from Alpha Vantage sentiment normalization so internal sentiment values retain full precision.
  - Corrected simulated event and news providers to return canonical empty collections rather than `[{}]` placeholder records.
  - Replaced mutable symbol defaults across the market-events provider contract and its live/backtest implementations.
  - Corrected downstream application normalization to consume canonical provider fields: `published_at`, `fear_greed_index`, and market-event `timestamp`/`name`/`symbol` fields. Earnings clustering now preserves the canonical `timestamp` field.
  - Audited the Massive and Alpaca clients without adding speculative abstractions. Their SDK types remain confined to client modules, current API calls are bounded by their provider/SDK contracts, and no verified defect required a production change.
  - Did not introduce a generic retry, pagination, rate-limit, or client base-class framework. YFinance receives the bounded retry behavior justified by its fan-out workload; other clients surface throttling and transport failures through canonical provider telemetry instead of disguising them.

  **Architecture and risk review**

  - Repowise preflight identified the YFinance client as a top-1% churn hotspot with a 220-line `get_sp500_data` brain method and broad co-change scatter. Changes were therefore kept behind the existing market-data provider contract and covered through deterministic contract tests.
  - The post-change Repowise MCP health result still reported the former method names and line ranges, indicating that its wiki/health index had not incorporated the working-tree refactor. Source inspection, MyPy, tests, and the refreshed Graphify AST graph are the authoritative Step 13 verification; Repowise health should be refreshed after these changes are committed/indexed.
  - JSCPD improved from the pre-change baseline of two clones and 0.74% duplicated lines to one provider-wrapper clone and 0.30%. Pylint remained at 9.92/10 and reports expected structural similarity between thin live/backtest telemetry adapters plus pre-existing RAG similarities; extracting those adapters would add abstraction without changing behavior.
  - No PostgreSQL, Qdrant, Neo4j, Prometheus, Jaeger, vendor credentials, or other external service was required. All Step 13 behavior was verified with deterministic fakes and mocked transports.

  **Verification**

  | Check | Result |
  | --- | --- |
  | Focused Step 13 client/provider/service contract suite | **37 passed** |
  | Complete unit suite | **1,504 passed**, 6 existing third-party/SQLAlchemy warnings |
  | Canonical treasury-name audit | Passed; no `2y_treasury` or `10y_treasury` reference remains outside generated history |
  | Client-owned `SP500Data` audit | Passed; no import from the YFinance client remains |
  | Synthetic fallback/error-payload audit | Passed for the scoped non-RAG clients/providers |
  | `ruff check . --fix` | Passed |
  | `ruff format .` | Passed; 1,078 files unchanged |
  | `mypy . --explicit-package-bases` | Passed; no issues in 1,075 source files |
  | Scoped JSCPD audit | **1 clone / 0.30% duplicated lines**, improved from the Step 13 baseline |
  | Scoped Pylint duplicate-code audit | **9.92/10**, unchanged; only known adapter/RAG similarities reported |
  | `git diff --check` | Passed |
  | `graphify update .` | Passed; 1,076 files extracted, graph rebuilt with 17,628 nodes and 76,880 edges |

  **Step 13 status**

  - The MacroService transport-boundary correction, canonical treasury rename, YFinance decomposition, typed market-data contract ownership, provider parity, and broader non-RAG client/provider audit are complete.
  - Step 14 — intelligence hotspot decomposition — has not begun and requires user confirmation.

  ### Step 14 — Decompose intelligence hotspots (Completed 2026-06-30)

  **Typed policy decomposition**

  - Reduced `PortfolioStateBuilder` from 564 lines to 139 lines by moving deterministic portfolio, position, equity, risk-feature normalization, and runtime-output construction into the frozen/slotted `PortfolioStateDecision` policy in `portfolio_state_policy.py`.
  - Reduced `VolatilityRiskAgent` from 693 lines to 32 lines by introducing the frozen/slotted `VolatilityRiskInputs` and `VolatilityRiskDecision` contracts plus pure volatility, exposure, concentration, cash-buffer, breadth, classification, and recommendation policies in `volatility_risk_policy.py`.
  - Reduced `StrategySynthesisAgent` from 1,330 lines to 206 lines by introducing explicit typed synthesis inputs, typed market-event context, a typed synthesis decision, and pure weighting, gating, uncertainty, classification, breadth, event-risk, and recommendation policies in `strategy_synthesis_policy.py`.
  - Reduced `RiskAggregatorAgent` from 369 lines to 278 lines by extracting the duplicated breadth signal/risk/recommendation annotation and string deduplication behavior into `intelligence/risk/breadth_annotations.py`.
  - Kept `RuntimeNode` orchestration, `RuntimeNodeOutput` serialization, service invocation, and intelligence telemetry in the agents. Pure policy modules have no runtime, service, provider, or telemetry dependencies.

  **Contract and behavioral preservation**

  - Preserved all established runtime node names, node types, output keys, execution metadata, fallback semantics, telemetry signal names, and risk-adapter behavior.
  - Preserved `MarketEventsService` behind the application-service boundary and continued passing the normalized dynamic `top_50_constituents` set into market-event analysis. The neutral degraded-data path remains observable through canonical intelligence telemetry.
  - Made the strategy and volatility nodes' hidden runtime-output dependencies explicit through typed input parsers rather than scattering nested dictionary extraction through policy calculations.
  - Preserved the established two-stage high-event-pressure sideways-weight adjustment as characterized behavior instead of silently changing strategy posture during decomposition.
  - Retained full precision for all internal directional, confidence, uncertainty, readiness, quality, and risk values. Decimal formatting remains limited to explanatory signal strings at the runtime presentation boundary.

  **Golden characterization coverage**

  - Strengthened strategy characterization tests with exact expected posture, directional score, confidence, uncertainty, execution readiness, signal quality, and recommendation ordering for deterministic weak-breadth inputs.
  - Strengthened volatility characterization tests with exact expected market-volatility risk, base composite risk, breadth-adjusted composite risk, and stability score.
  - Retained the existing exhaustive portfolio-state contract assertions for normalized positions, equity fields, account controls, risk features, execution metadata, and telemetry payloads.
  - Verified the full real-node morning-report integration and report assembly/rendering path after the decomposition.

  **Health and duplication review**

  - Repowise preflight classified the three prioritized agents as high-churn hotspots, with `StrategySynthesisAgent` and `VolatilityRiskAgent` carrying the most severe brain-method/complexity debt. The refactor therefore kept runtime boundaries stable and moved only deterministic calculations into focused policy modules.
  - Scoped JSCPD improved from the Step 14 baseline of **20 clones / 508 duplicated lines / 7.17%** to **18 clones / 433 duplicated lines / 7.18%**. The percentage is effectively flat because the extraction substantially reduced total scoped source lines; the absolute duplicate count and duplicated lines both decreased.
  - Scoped Pylint duplicate-code improved from **9.74/10** to **9.79/10**. Remaining duplication is concentrated in the pre-existing Bull/Bear/Sideways agents and Drawdown/Exposure risk agents. It was not expanded into this step because those components require their own typed policy decomposition and golden coverage rather than a speculative shared helper.
  - No PostgreSQL, Qdrant, Neo4j, Prometheus, Jaeger, vendor API, or other external service was required. All Step 14 behavior was verified deterministically.

  **Verification**

  | Check | Result |
  | --- | --- |
  | Focused strategy/portfolio/volatility/aggregator characterization suite | **17 passed** |
  | Complete intelligence unit suite | **45 passed** |
  | Complete unit suite | **1,504 passed**, 6 existing third-party/SQLAlchemy warnings |
  | Real-node morning-report plus report unit suite | **7 passed**, 1 existing third-party warning |
  | `ruff check . --fix` | Passed |
  | `ruff format .` and final format check | Passed; 1,082 files compliant |
  | `mypy . --explicit-package-bases` | Passed; no issues in 1,079 source files |
  | Scoped JSCPD audit | **18 clones / 433 duplicated lines / 7.18%**; threshold remains exceeded by pre-existing strategy/risk clones |
  | Scoped Pylint duplicate-code audit | **9.79/10**, improved from 9.74/10 |
  | `git diff --check` | Passed |
  | `graphify update .` | Passed; 1,080 files extracted, graph rebuilt with 17,721 nodes and 77,232 edges |

  **Step 14 status**

  - The prioritized StrategySynthesisAgent, PortfolioStateBuilder, and VolatilityRiskAgent decompositions are complete and verified.
  - Shared breadth runtime annotation duplication between volatility risk and risk aggregation is removed.
  - Remaining Bull/Bear/Sideways and Drawdown/Exposure duplication is documented as bounded follow-up debt; it was not necessary to preserve or verify the Step 14 prioritized runtime contracts.
  - Step 15 — persistence and database mapping stabilization — has not begun and requires user confirmation. PostgreSQL will be required for Step 15's live migration and repository gates, so service availability will be requested before those checks run.

  ### Step 15 — Stabilize persistence and database mappings (Completed 2026-06-30)

  **Canonical sentiment persistence cleanup**

  - Replaced legacy sentiment persistence contract names with the canonical application/intelligence vocabulary: `market_regime`, `composite_sentiment`, `fusion_components`, `providers_payload`, and `sentiment_payload`.
  - Added first-class sentiment fields for `market_bias`, `directional_signal`, `momentum`, `stability`, and `divergence` rather than hiding established domain values in generic metadata.
  - Added typed `features_payload` and `raw_payload` boundaries while retaining metadata only for diagnostic/extensible attributes.
  - Updated ORM models, frozen/slotted persistence records, serializers, repository validation, application persistence tests, and the curated RAG structured-source adapter together. No compatibility aliases or duplicate legacy column names were retained.
  - Confirmed the existing physical PostgreSQL sentiment columns already used the canonical names, so no destructive sentiment migration was necessary and no RAG behavior was changed.

  **Normalized portfolio equity history**

  - Added the append-only `portfolio_equity_history_points` PostgreSQL table and `PortfolioEquityHistoryPointModel` with first-class account, source, timeframe, observation time, equity, profit/loss, profit/loss percentage, base value, optional cash-flow payload, runtime lineage, and audit timestamps.
  - Added a frozen/slotted `PortfolioEquityHistoryPointRecord`, deterministic UTC-normalized record identifiers, serializer support, repository insert/list/count operations, application persistence contracts, and Dishka composition.
  - Added the typed `normalize_portfolio_equity_history()` boundary to validate provider series lengths, timestamps, timeframes, and cash-flow alignment without rounding or silently repairing malformed data.
  - Updated live, backtest, and simulated portfolio providers with stable source identities. `PortfolioService` now normalizes history before persistence, attaches workflow/execution/runtime/node lineage from the canonical `ServiceRequest`, persists the portfolio snapshot and normalized history points, and surfaces persistence failures explicitly.
  - Added idempotent PostgreSQL insertion through the unique `(account_id, source, timeframe, observed_at)` constraint. Duplicate provider observations do not produce duplicate history rows.
  - Kept the migration additive and intentionally performed no historical backfill. PostgreSQL remains the system of record; no JSON-only or local-disk parallel store was introduced.

  **Architecture and risk review**

  - Repowise preflight identified `PortfolioService` as a high-churn hotspot. The change therefore remained limited to normalization, lineage, and persistence orchestration; its broader state-construction complexity remains documented follow-up debt.
  - Persistence models now represent established service outputs with first-class fields where stable query/replay semantics exist. Generic payloads are restricted to genuine boundary data such as provider cash-flow details, raw source payloads, and diagnostics.
  - The migration produces one Alembic head and matches current SQLAlchemy metadata. A blank database can upgrade to head, downgrade/upgrade consistency remains valid, and the repository contract was verified against live PostgreSQL.
  - Scoped duplication checks found only existing structural validation and thin repository/provider patterns. No speculative helper extraction was introduced during this schema-sensitive step.

  **Verification**

  | Check | Result |
  | --- | --- |
  | Focused sentiment and portfolio persistence/service regression suites | **151 passed** |
  | Portfolio normalization, record, and serializer contracts after UTC-ID correction | **35 passed** |
  | Complete unit suite | **1,522 passed**, 6 existing third-party/SQLAlchemy warnings |
  | Live PostgreSQL portfolio-equity-history repository integration | **1 passed**; duplicate persistence remains idempotent |
  | Dynamic Alembic/pytest-alembic migration suite | **6 passed**, 7 existing Alembic warnings |
  | `alembic heads` | Passed; single head `d9649abf672c` |
  | `alembic upgrade head` | Passed against the live Polaris PostgreSQL database |
  | `alembic check` | Passed; no new upgrade operations detected |
  | `ruff check . --fix` | Passed |
  | `ruff format .` | Passed; 1,086 files compliant |
  | `mypy . --explicit-package-bases` | Passed; no issues in 1,083 source files |
  | Scoped JSCPD audit | **9 clones / 179 duplicated lines / 4.38%**, all bounded existing structural patterns |
  | Scoped Pylint duplicate-code audit | **9.94/10** |
  | `git diff --check` | Passed |
  | `graphify update .` | Passed; 1,084 files extracted, graph rebuilt with 17,840 nodes and 77,758 edges |

  **Step 15 status**

  - Canonical sentiment persistence contracts and normalized portfolio equity-history persistence are implemented and verified.
  - The live PostgreSQL database is migrated to Alembic head `d9649abf672c`.
  - Step 16 has not begun and requires user confirmation.

  ### Step 16 — Stabilize CLI, API, scheduler, and report boundaries (Completed 2026-06-30)

  **Thin CLI boundary consolidation**

  - Added `interfaces/cli/commands/workflow_command_boundary.py` as the single CLI-owned boundary for artifact-format validation, interactive input construction, progress rendering, control notifications, renderer fallback, output emission, and stderr status messages.
  - Refactored the generic workflow and morning-report commands to use the shared boundary instead of maintaining duplicate command I/O and fallback logic.
  - Confirmed that CLI dependency resolution already uses the canonical Dishka application request scope; no duplicate container builder remained in the current source, so no speculative container rewrite was introduced.
  - Kept command execution delegated to `WorkflowCommandService` and retained `WorkflowFacade` as the only pause, resume, and cancel boundary. Interactive input does not mutate runtime state or create a parallel control loop.
  - Kept morning-report persistence behind the canonical `MorningReportPersistenceService` request scope.

  **Complete output and terminal semantics**

  - Moved shared workflow payload extraction into `interfaces/cli/formatters/workflow_payload.py` so console and Markdown formatting use one presentation-boundary interpretation of the typed render envelope.
  - Updated console and Markdown workflow renderers to include additional payload fields that are not part of the morning report or node-output sections. Partial and specialized workflow outputs are therefore no longer silently omitted.
  - Preserved complete node, LLM, report, and additional payload content. No truncation, summarization, or presentation rounding was added.
  - Ensured renderer fallback retains the actual workflow success flag and terminal status, including `partial` and `cancelled`, instead of converting renderer failures into a falsely reported workflow failure.
  - Corrected malformed `--metadata` handling so input validation occurs before service construction and returns Typer's validation exit code rather than being rendered as a runtime workflow failure.
  - Verified that success exits with code 0 and that partial success, cancellation, runtime failure, and service exceptions still render an attributable output before exiting with code 1.

  **Boundary and architecture review**

  - API and scheduler packages currently contain only zero-line scaffolding. They were intentionally left untouched rather than inventing unsupported application behavior during a CLI/report stabilization step.
  - The shared command helper remains a CLI/Typer presentation component and does not contain workflow execution, runtime control, persistence, policy, or governance logic.
  - Repowise continued to report historical method names and pre-change source measurements after the working-tree refactor. Its churn and hotspot data remain useful, but source inspection, deterministic tests, MyPy, JSCPD, Pylint, and the refreshed Graphify AST are the authoritative verification for this uncommitted step.
  - No PostgreSQL, Qdrant, Neo4j, Prometheus, Jaeger, vendor API, or other external service was required.

  **Verification**

  | Check | Result |
  | --- | --- |
  | Focused workflow/morning-report boundary suite | **71 passed**, 1 existing warning |
  | Complete CLI unit suite | **108 passed**, 1 existing warning |
  | Complete unit suite | **1,527 passed**, 6 existing third-party/SQLAlchemy warnings |
  | Malformed metadata and service-failure exit/output contracts | Passed |
  | Partial, cancelled, failed, and successful output rendering | Passed |
  | Full long-form LLM/report-content preservation | Passed with a non-truncated long-content regression case |
  | Interactive progress and pause/resume/cancel facade delegation | Passed through existing and focused boundary tests |
  | `ruff check . --fix` | Passed |
  | `ruff format .` | Passed; 1,089 files unchanged |
  | `mypy . --explicit-package-bases` | Passed; no issues in 1,086 source files |
  | Scoped JSCPD audit | **0 clones / 0 duplicated lines / 0.00%**, improved from 3 clones / 117 lines / 1.72% |
  | Scoped Pylint duplicate-code audit | **9.96/10**; the production command clone is removed and remaining findings are bounded test/PDF patterns |
  | `git diff --check` | Passed |
  | `graphify update .` | Passed; 1,087 files extracted, graph rebuilt with 17,871 nodes, 77,899 edges, and 657 communities |

  **Step 16 status**

  - CLI and report boundaries are thin, async-native at execution boundaries, and consolidated around canonical application/facade delegation.
  - Workflow output is always rendered for successful, partial, cancelled, failed, and service-exception outcomes, with complete content preserved.
  - Step 17 — deterministic backtesting verification — has not begun and requires user confirmation.

  ### Step 17 — Establish deterministic backtesting verification (Completed 2026-06-30)

  **Typed, runtime-native simulation contract**

  - Added the frozen/slotted `BacktestWorkflowStepRequest` as the immutable contract for one simulated workflow invocation. It owns the canonical workflow name, deterministic execution identifier, simulation time, persistence/checkpoint policy, and runtime input projection.
  - Propagated scenario `symbol`, `symbols`, `benchmark_symbol`, and parameter values at the canonical workflow-input boundary while retaining nested backtest metadata for attribution. Real workflow nodes therefore consume the requested deterministic scenario instead of silently falling back to live defaults.
  - Kept `WorkflowFacade` and the existing workflow graph/runtime as the only execution path. No backtest-specific runtime, graph, scheduler, checkpoint mechanism, or runtime mode branch was introduced.
  - Added injectable UTC clock and run-ID factories to the backtest application service. Production retains generated identifiers and the system UTC clock; deterministic tests can fix both without mutating runtime behavior.

  **Deterministic financial verification**

  - Added typed `BacktestOutcomeVerification` evidence and a focused verifier supporting `equals`, `approx`, `min`, `max`, `between`, and `contains` comparisons over dotted result paths.
  - Added stable financial aliases for technical analysis, canonical breadth state, portfolio state, aggregate risk, synthesized strategy, packaged trade intent, final execution-risk guard output, portfolio ledger, metrics, and explicit runtime node paths.
  - Failed expectations now fail the backtest and preserve the target, comparison, expected value, actual value, tolerance, pass/fail state, and attributable detail in typed results and console, Markdown, JSON, and persistence artifacts.
  - Added deterministic golden scenarios that independently verify the technical calculation, canonical breadth/regime assessment, portfolio equity, aggregate risk, strategy posture/score, trade direction/sizing, and execution-risk adjustment from controlled synthetic inputs.
  - Ran the real canonical `morning_report` graph through `BacktestApplicationService` with the actual synthetic provider profile and verified 13 exact/tolerance-bounded outcomes across the complete decision chain.

  **Repeatability and artifact stability**

  - Backtest step projections now deep-copy runtime node outputs in stable node-name order and omit volatile runtime `execution_metadata` such as wall-clock durations. Canonical workflow persistence remains the source for complete raw execution telemetry; the deterministic projection exists specifically for repeatable simulation evidence.
  - Repeated fixed-input simulations now produce identical typed results, verification evidence, ordering, timestamps, execution identifiers, calculated metrics, reports, and persistence bundles.
  - Updated the backtesting documentation to explain expectation aliases, failure semantics, fixed clock/run-ID use, deterministic output projection, and the separation between stable backtest evidence and raw runtime observability.

  **Provider and composition parity**

  - Made the simulated macro provider conform directly to the canonical `MacroProvider` contract and added signature/protocol parity tests across macro, market-data, market-events, news, portfolio, and sentiment simulators.
  - Real-node verification exposed a pre-existing sync-composition scope violation: application-scoped `PortfolioStateBuilder` depended transitively on request-scoped `PortfolioService` persistence. Corrected `PortfolioStateBuilder` to request scope and bound sync workflow infrastructure to the active Dishka request container.
  - Added an invocation-local in-memory implementation of `PortfolioExpansionPersistenceRepository` for sync/backtest composition, including deterministic ordering, equity-history idempotency, and latest-position upsert semantics. PostgreSQL remains the system of record for async/live composition; no disk fallback or parallel persistence architecture was introduced.
  - Moved the canonical application persistence provider into the shared base composition set and retained the PostgreSQL concrete binding in async RAG/live composition. This keeps application services dependent on the repository protocol rather than a concrete database implementation.

  **Architecture and risk review**

  - Runtime execution remains completely unaware of whether providers are live or simulated; provider selection remains a composition concern.
  - Numeric values are compared and persisted at full precision. Tolerances are explicit scenario policy, not presentation rounding.
  - No PostgreSQL, Qdrant, Neo4j, Prometheus, Jaeger, vendor API, or other external service was required. The real-node integration used deterministic synthetic providers through canonical DI and runtime boundaries.
  - Scoped duplication analysis found only existing persistence declarations and test-fixture structures. No new shared utility was extracted merely to suppress structural test duplication.

  **Verification**

  | Check | Result |
  | --- | --- |
  | Focused backtesting, simulated-provider parity, DI, and portfolio-service suites | **38 passed**, 1 existing third-party warning |
  | Runtime-native real morning-report/backtest integration | **2 passed**, 1 existing third-party warning |
  | Deterministic repeated-run result and persistence-bundle equality | Passed |
  | Full decision-chain golden expectations | Passed; all technical, breadth, portfolio, risk, strategy, trade, and execution-risk assertions verified |
  | Complete unit suite | **1,538 passed**, 6 existing third-party/SQLAlchemy warnings |
  | `ruff check . --fix` | Passed |
  | `ruff format .` | Passed; 1,094 files compliant |
  | `mypy . --explicit-package-bases` | Passed; no issues in 1,091 source files |
  | Scoped JSCPD audit | **4 existing structural clones / 97 duplicated lines / 2.39%**; no Step 17 production-logic clone identified |
  | Scoped Pylint duplicate-code audit | **9.96/10**; findings limited to existing test fixtures and the pre-existing expectation-type declaration pattern |
  | `git diff --check` | Passed |
  | `graphify update .` | Passed; 1,092 files extracted, graph rebuilt with 17,998 nodes, 78,421 edges, and 644 communities |

  **Step 17 status**

  - Deterministic backtesting can now use controlled input data to execute the canonical runtime and independently verify that technical, breadth/regime, portfolio, risk, strategy, trade-recommendation, and execution-risk calculations are correct.
  - Repeated deterministic simulations produce stable evidence while preserving complete volatile telemetry in canonical workflow persistence.
  - Step 18 has not begun and requires user confirmation.

  ### Step 18 — Security, reliability, and governance audit (Completed 2026-06-30)

  **Secret-handling and persistence-boundary hardening**

  - Added `core.security.sensitive_data` as the canonical, infrastructure-neutral redaction policy for credential-shaped keys, embedded `key=value` secrets, bearer tokens, and passwords embedded in connection URLs.
  - Refactored telemetry sanitization into a thin adapter over the shared security policy so logs, tracing exporters, checkpoints, and persistence serializers use one redaction vocabulary without making runtime or storage code depend on telemetry.
  - Sanitized `RuntimeCheckpoint.to_dict()` and completed-run PostgreSQL serialization at their explicit persistence boundaries. Canonical in-memory `RuntimeContext` and source payloads remain unchanged, while workflow inputs, node outputs, errors, metadata, and artifact payloads are redacted before persistence.
  - Added negative tests proving nested secrets and secrets embedded in error strings do not survive checkpoint, completed-run, or telemetry serialization and that source objects are not mutated.

  **Policy, governance, replay, and destructive-operation gates**

  - Added the frozen/slotted `DestructiveOperationConfirmation` contract with explicit operation, exact target, requester, and confirmed state.
  - Required typed confirmation plus policy and governance approval before workflow unregistration, completed-run deletion, or completed-run cleanup. The CLI still performs the human Typer confirmation, then translates it into the typed core contract rather than treating a presentation prompt as the authorization boundary.
  - Added policy and governance preflight checks for pause, resume, cancel, checkpoint restore, and checkpoint replay. Denial occurs before control-state mutation, registry mutation, checkpoint loading, or workflow execution.
  - Wired the bootstrap-composed policy and governance engines into `ReplayEngine`; replay continues through the existing `WorkflowEngine` and does not introduce a parallel execution or authorization path.
  - Verified backtesting and CLI execution continue to delegate through the canonical `WorkflowFacade`. API and scheduler packages remain scaffolds and contain no alternate executable path to harden.

  **Reliability, input, dependency, and serialization audit**

  - Re-audited non-RAG external client/provider paths for bounded timeouts, cancellation propagation, provider telemetry, malformed-response handling, and resource cleanup. The Step 13 service → provider → client corrections remain the canonical boundary, and the complete unit suite retains negative coverage for malformed data, provider failures, timeouts, cancellation, and persistence failures.
  - Confirmed production non-RAG code contains no `pickle`, `dill`, `cloudpickle`, `marshal`, unsafe YAML loader, `eval`, or `exec` serialization/execution path.
  - `uv lock --check` passed. `pip-audit --local --skip-editable` reported **no known vulnerabilities** in the installed environment.
  - No speculative request-size mechanism was added because the API and scheduler surfaces are not implemented. Size validation belongs at those future transport boundaries rather than inside the runtime.
  - Failures remain typed and attributable through existing workflow, replay, provider, service, and persistence result/error contracts; the new denial paths preserve their canonical policy/governance exceptions or failed `ReplayResult` evidence.

  **Risk and duplication observations**

  - Repowise continues to classify `WorkflowFacade`, `ReplayEngine`, the completed-run serializer, the checkpoint model, and the runtime assembler as churn-heavy core hotspots. Changes were therefore limited to explicit boundary checks, injected canonical engines, and serialization sanitization, with direct regression coverage for every altered behavior.
  - The required full JSCPD audit reports a pre-existing **232 clones / 6,198 duplicated lines / 5.10%** repository-wide baseline, slightly above the configured threshold. The Pylint recursive duplicate-code audit exceeded its 45-second bounded execution window without producing findings. No generic helper extraction was introduced during this security-focused step; verified duplication cleanup remains Step 19.
  - Post-change Repowise blast-radius review identified no missing historical co-change partner and no security signal. The high aggregate risk reflects the centrality and churn of the core files, not a detected policy or security regression.

  **Verification**

  | Check | Result |
  | --- | --- |
  | Focused secret-redaction, confirmation, policy/governance, replay, checkpoint, completed-run, CLI, and bootstrap suite | **31 passed**, 1 existing third-party warning |
  | Additional replay-resume, workflow-provider-control, governance-provider, and telemetry-sanitization suite | **9 passed** |
  | Complete unit suite plus focused workflow/policy/governance/replay integrations | **1,562 passed**, 6 existing third-party/SQLAlchemy warnings |
  | Full repository pytest attempt | Reached service-gated integration collection but exceeded the bounded 120-second run; no failure was reported before timeout |
  | `uv lock --check` | Passed |
  | `pip-audit --local --skip-editable` | Passed; no known vulnerabilities found |
  | Unsafe serialization/execution scan | Passed; no production non-RAG matches |
  | `ruff check . --fix` | Passed |
  | `ruff format .` | Passed; 1,101 files compliant |
  | `mypy . --explicit-package-bases` | Passed; no issues in 1,098 source files |
  | `git diff --check` | Passed |
  | `graphify update .` | Passed; 1,099 files extracted, graph rebuilt with 18,064 nodes and 78,874 edges |

  **Step 18 status**

  - Core persistence and telemetry boundaries now redact credential-shaped data consistently.
  - Replay, workflow control, checkpoint restore, workflow unregistration, and completed-run destruction are protected by the canonical policy/governance architecture, with typed confirmation for destructive actions.
  - Dependency, unsafe-serialization, reliability, and negative-path audits are complete for the current non-RAG platform surface.
  - Step 19 — verified dead- and duplicate-code removal — has not begun and requires user confirmation.

  ### Step 19 — Remove verified dead and duplicate code (Completed 2026-06-30)

  **Dead-code verification and surgical removal**

  - Re-ran Repowise dead-code/health/risk analysis, Graphify queries, exact repository references, git history searches, test discovery, and DI/plugin registration checks before removing code.
  - Confirmed that several high-confidence static findings were false positives because they are invoked through imported modules, protocols, runtime composition, tests, or callable injection. Retained the technical-analysis functions, portfolio-analysis functions, async workflow bootstrap, telemetry protocols/sinks, workflow-control protocol, report export request, persistence audit emitter, and risk runtime adapter.
  - Removed only four symbols with no production, test, plugin, DI, CLI, reflection, or serialization references:
      - `NoOpPluginLifecycleHook` from the plugin lifecycle hook contract module;
      - `top_text_items` from morning-report presentation helpers;
      - `get_db_session` and its stale public export from the PostgreSQL engine/session module;
      - the unused `EarningsCalendarEvent` dataclass from the Alpha Vantage earnings client, while correcting its stale return documentation to match the normalized mapping payload it actually returns.
  - Removed only imports and exports orphaned by those deletions. No compatibility wrapper, replacement abstraction, production module, package, or test was deleted.

  **Duplicate-code assessment**

  - The repository-wide JSCPD baseline remains **232 exact clones / 6,198 duplicated lines / 5.09%**, above the configured 5.0% threshold. Removing dead code slightly changed the percentage denominator but introduced no clone and did not increase duplicated lines.
  - Reviewed the largest non-RAG findings directly. The dominant matches are explicit SQLAlchemy model declarations, separate typed persistence-filter contracts, and the intentionally paired sync/async workflow-bootstrap boundaries. These are structural similarities with distinct schema or execution semantics; extracting generic helpers solely to lower the metric would hide contracts and violate the plan's simplicity rule.
  - A bounded recursive Pylint duplicate-code pass produced no result before timeout during preflight. A focused post-change Pylint duplicate-code pass over all four edited modules completed at **10.00/10**.
  - Whole-module candidates (`core/di.py`, `application/di.py`, `integration/di.py`, `intelligence/strategy/evolution/strategy_evolution_engine.py`, and `integration/contracts/execution/execution_decision.py`) remain unreferenced by exact search, but were not deleted because production source-module deletion requires explicit confirmation. They are documented candidates for a separately approved cleanup, not silently removed in this step.

  **Architecture and service observations**

  - Plugin lifecycle behavior continues to use the structural `PluginLifecycleHook` protocol and concrete telemetry hook; an empty hook collection already provides the canonical no-op behavior.
  - PostgreSQL composition continues to use `AsyncSessionLocal` and the canonical Dishka providers. The removed standalone async generator was not registered or consumed by current composition.
  - No PostgreSQL, Qdrant, Neo4j, Prometheus, Jaeger, vendor API, or other external service is required by the Step 19 cleanup itself.

  **Verification**

  | Check | Result |
  | --- | --- |
  | Exact post-removal reference scan | Passed; zero references to all four removed symbols |
  | Focused client, morning-report, plugin, and PostgreSQL settings suites | **21 passed** |
  | Complete repository pytest run | **1,621 passed / 18 skipped**; the sole failure was the excluded live RAG Neo4j test timing out because `localhost:7687` was unavailable |
  | `ruff check . --fix` | Passed |
  | `ruff format .` | Passed; 1,101 files unchanged |
  | `mypy . --explicit-package-bases` | Passed; no issues in 1,098 source files |
  | Focused Pylint duplicate-code audit | **10.00/10** |
  | Repository JSCPD audit | **232 existing clones / 6,198 duplicated lines / 5.09%**; no new duplicated lines |
  | `git diff --check` | Passed |
  | `graphify update .` | Passed; 1,099 files extracted, graph rebuilt with 18,066 nodes, 78,876 edges, and 681 communities |

  **Step 19 status**

  - Verified dead symbols have been removed without changing public runtime, plugin, DI, persistence, or client behavior.
  - Static-analysis false positives and intentional structural duplication have been documented rather than converted into risky abstractions.
  - Step 20 — documentation, knowledge preservation, and the final readiness gate — has not begun and requires user confirmation.

  ### Step 20 — Documentation, knowledge preservation, and final readiness gate (Completed 2026-06-30)

  **Canonical architecture and operations documentation**

  - Added `.docs/platform_architecture_and_operations.md` as the canonical non-RAG platform guide. It documents the stabilized runtime flow, `RuntimeContext` schema-version-2 ownership, facade/bootstrap/runtime responsibilities, Dishka request scopes, telemetry and trace propagation, service → provider → client boundaries, persistence classification, deterministic backtesting, operational commands, service dependencies, and safety constraints.
  - Linked the new guide and the accepted ADR directory from `README.md` so the current architecture is discoverable from the repository entry point.
  - Corrected `.docs/backtesting_system.md` to remove the obsolete `RuntimeState`/`shared_state` flow. It now documents `BacktestWorkflowStepRequest`, `RuntimeContext.workflow_inputs`, canonical node outputs, deterministic identifiers/time, and verification evidence.
  - Added a prominent post-stabilization resolution to `.docs/platform_data_contract_inventory.md`. The original Step 5 inventory remains preserved as historical audit evidence, while the new section records removal of the runtime business-state aggregate, canonical ownership by `RuntimeContext` and domain `PortfolioState`, and the checkpoint/completed-run distinction.
  - Preserved the six accepted architectural decisions under `.docs/decisions/`: runtime boundaries, Dishka scopes, events/telemetry/tracing, PostgreSQL system-of-record ownership, deterministic backtesting, and typed internal contracts.
  - The repository has no tracked Markdown wiki pages under `.repowise/`; that directory contains generated index artifacts. To avoid overwriting generated or manually maintained Repowise state, this step updated the canonical `.docs`/ADR knowledge sources that Repowise indexes rather than inventing or replacing a generated wiki tree.

  **Step 1 to Step 20 health comparison**

  | Measure | Step 1 baseline | Step 20 result | Assessment |
  | --- | ---: | ---: | --- |
  | Repowise average health | 7.72 | **7.93** | Improved |
  | Repowise hotspot health | 7.43 | **7.81** | Improved |
  | Indexed files | 818 | 833 | Expected growth from typed contracts, tests, migrations, and ADRs |
  | Open health findings | 1,468 | **1,463** | Slight improvement despite larger indexed surface |
  | CLI container health | 1.64 | **4.00** | Improved; remaining `_build_cli_container` history finding reflects the committed index rather than the current 107-line working-tree module |
  | `WorkflowBootstrap` health | 1.69 | **6.29** | Material improvement |
  | `WorkflowFacade` health | 1.90 | **7.25** | Material improvement |
  | `RuntimeEngine` health | 2.39 | **4.85** | Improved after focused execution collaborators were extracted |
  | Strategy synthesis health | 2.14 | **3.57** indexed | Improved; the working tree has already split the agent to 206 lines and policy to 755 lines, so the uncommitted source is healthier than the committed-index god-class report |
  | YFinance client health | 2.24 | 2.24 indexed | Historical churn remains; deterministic contract tests and source refactoring reduce behavioral risk but cannot erase history-based risk |
  | High-confidence dead-code candidates | 54 | 54 indexed | Candidate count unchanged; total findings fell 166 → **164** and reclaimable estimate fell about 3,173 → **2,778** lines |
  | Active architectural decisions | 0 | **6** | Canonical intent is now queryable |
  | Ungoverned hotspots | 263 | **247** | Improved |
  | Non-RAG total coverage | 89.42% | **90.63%** | Improved and above the 80% acceptance floor |

  Repowise currently reports 266 hotspots versus 263 at baseline and continues to report increasing churn and bus factor 1. This is not treated as a hidden success: the stabilization added and changed central code, so temporal hotspot counts can rise even while structural health improves. Bus factor is an organizational ownership risk that code refactoring alone cannot resolve.

  **Final risk, dead-code, and blast-radius review**

  - Re-ran Repowise dashboard, targeted biomarker, dead-code, decision-health, and changed-file blast-radius analyses.
  - The final changed-file dossier remains high risk because it includes central facade, replay, checkpoint, completed-run, and composition files. It reported no security signal. Historical co-change warnings were reviewed as broad temporal associations rather than evidence that unrelated Alpaca, sentiment, portfolio-state, script, or dependency files needed speculative edits.
  - Exact source, tests, DI/plugin registration, and Graphify remain authoritative for the uncommitted working tree. The Repowise index still lists the already removed `NoOpPluginLifecycleHook` and pre-split strategy/YFinance method shapes, demonstrating that static dead-code and health output must be verified rather than applied mechanically.
  - Remaining production-module candidates such as legacy DI modules and strategy evolution/execution contracts were not deleted. Their deletion requires separate source-level proof and explicit production-source deletion approval.
  - Repository-wide JSCPD remains at the Step 19 baseline of 232 exact clones / 6,198 duplicated lines / 5.09%. The largest reviewed non-RAG matches are explicit schema declarations, typed persistence filters, and sync/async composition structures where metric-only abstraction would obscure distinct contracts.

  **Intentional exceptions and remaining bounded debt**

  - `StrategySynthesisPolicy`, the YFinance client, the CLI composition boundary, and portions of replay/checkpoint composition remain churn-heavy. They have characterization/failure-path coverage and should be changed surgically in future work rather than expanded casually.
  - API, scheduler, and UI packages remain non-production scaffolding. No speculative transport, lifecycle, or request-size architecture was added merely to satisfy a readiness checklist.
  - External RAG service validation is excluded from this non-RAG stabilization. The Step 19 full repository run's unavailable Neo4j live test is therefore not a non-RAG regression.
  - Current Repowise history/ownership metrics report bus factor 1 across central modules. Future review ownership and contribution distribution should address that operational risk.
  - The repository's generated Repowise index should be refreshed after this working tree is committed so its method sizes and deleted-symbol inventory match the stabilized source.

  **Final verification**

  | Check | Result |
  | --- | --- |
  | Full non-RAG pytest suite with coverage | **1,621 passed / 16 skipped**, 6 existing third-party/SQLAlchemy warnings |
  | Total measured coverage | **90.63%** (33,697 statements / 3,158 missed), improved from 89.42% |
  | Changed central modules | Runtime 93%, facade 86%, bootstrap 88%, runtime assembler 99%, replay 95%, completed-run serializer 93%, strategy agent 94%, strategy policy 87%, YFinance client 82% |
  | PostgreSQL service readiness | Compose PostgreSQL confirmed running before live validation |
  | Alembic current revision | `d9649abf672c (head)` |
  | Alembic model/schema divergence check | Passed; no new upgrade operations detected |
  | Dynamic migration contract suite | **6 passed**, including blank upgrade, single head, downgrade consistency, ORM metadata match, and targeted data migrations |
  | Completed-run PostgreSQL integration suite | **3 passed** |
  | `ruff check . --fix` | Passed |
  | `ruff format .` | Passed; 1,101 files unchanged |
  | `mypy . --explicit-package-bases` | Passed; no issues in 1,098 source files |
  | Documentation local-link validation | Passed for README and all Step 20 documentation targets |
  | `git diff --check` | Passed |
  | `graphify update .` | Passed; 1,099 files extracted and no code-graph topology change was required after documentation-only Step 20 edits |

  **Step 20 and plan status**

  - Step 20 is complete.
  - The non-RAG platform stabilization plan is complete: canonical runtime and composition boundaries are preserved, runtime state ownership is singular, services/providers/clients are separated, telemetry and security boundaries are enforced, deterministic backtesting verifies the real runtime, PostgreSQL migrations and completed-run persistence pass live validation, and final health/coverage exceed the Step 1 baseline.
  - The platform is ready for the next planned implementation with the intentional exceptions above recorded as bounded technical and organizational debt rather than unexplained critical findings.
