  # Canonical Workflow-Output-to-Curated-Record Projection Plan

  ## Summary

  Introduce an application-owned projection layer that converts selected, successful workflow node outputs into strongly typed curated PostgreSQL records.

  The canonical flow will become:

  Application service
      → typed result
      → intelligence node
      → typed signal/decision
      → RuntimeNodeOutput
      → completed-run archive
      → workflow-output projection layer
      → typed curated persistence record
      → PostgreSQL
      → optional downstream RAG ingestion

  The projection layer will:

  - Keep domain persistence out of analysis services and intelligence nodes.
  - Keep the runtime unaware of application domains and curated tables.
  - Preserve completed-run archival as a separate concern.
  - Populate curated PostgreSQL tables through existing application persistence services.
  - Use deterministic identities and workflow lineage for idempotent reprocessing.
  - Prevent backtest, simulated, failed, or unsupported outputs from contaminating live curated records.
  - Never use generic metadata as a substitute for missing first-class fields.
  - Not trigger RAG ingestion directly; RAG remains a downstream projection of curated PostgreSQL records.

  ## Cross-Plan Execution Coordination

  This plan is the infrastructure foundation for `.agents/plans/plan_strategy_structured_hypothesis_implementation.md`. Execute the plans in this order:

  1. **Execute this plan through Step 11, then pause.** Do not begin projectable-node normalization or domain projectors yet.
  2. **Switch to the structured-hypothesis plan and execute Strategy Steps 1–20.** This establishes the final strategy output contracts and database schema.
  3. **Return here and execute Steps 12–15.** Do not normalize strategy outputs into the obsolete generic strategy shape.
  4. **Execute Steps 16–17 together with Strategy Step 21.** The coordinated stage registers and implements strategy projectors once through this plan's canonical projection infrastructure.
  5. **Switch to the structured-hypothesis plan for Steps 22–25.** Complete strategy RAG/graph projections, cleanup, and architecture documentation.
  6. **Return here and execute Steps 18–28.** Complete portfolio projection, operations, integration coverage, RAG compatibility, quality gates, and persistence documentation.
  7. **Finish with Strategy Steps 26–27.** Those steps are the final strategy-specific regression and architecture-health gate.

  Ownership rules:

  - This plan exclusively owns projection jobs, registry, eligibility, orchestration, retries, workflow-completion subscription, generic lineage, and idempotency.
  - The structured-hypothesis plan exclusively owns strategy domain contracts, strategy database records, and strategy-specific mapping semantics.
  - No strategy step may introduce parallel projection infrastructure.
  - No projector in this plan may freeze the current generic Bull/Bear/Sideways payload before the structured-hypothesis contracts are complete.

  ## Architecture and Public Contracts

  ### Runtime output contract identification

  Extend RuntimeNodeOutput with generic, persistence-agnostic serialization identity:

  output_contract: str | None
  output_schema_version: int

  These fields describe the serialized output contract for replay, validation, and projection. They do not reference PostgreSQL, RAG, or application persistence.

  Every projectable node will declare a stable contract such as:

  polaris.portfolio.state
  polaris.market.technical_analysis
  polaris.agent.fundamental_signal
  polaris.agent.news_signal
  polaris.agent.sentiment_signal
  polaris.portfolio.risk
  polaris.strategy.synthesis
  polaris.portfolio.allocation_intent
  polaris.trade.recommendation

  ### Projection contracts

  Add an application-layer projection package with these typed contracts:

  @dataclass(frozen=True, slots=True)
  class WorkflowOutputProjectionRequest:
      run: CompletedRunRecord
      node_output: CompletedNodeOutputRecord
      source_fingerprint: str

  @dataclass(frozen=True, slots=True)
  class WorkflowOutputProjectionOutcome:
      projector_name: str
      node_name: str
      status: ProjectionStatus
      persisted_record_ids: tuple[str, ...]
      error: str | None = None

  class WorkflowOutputProjector(Protocol):
      @property
      def projector_name(self) -> str: ...

      @property
      def output_contract(self) -> str: ...

      @property
      def supported_schema_versions(self) -> frozenset[int]: ...

      async def project(
          self,
          request: WorkflowOutputProjectionRequest,
      ) -> WorkflowOutputProjectionOutcome: ...

  Add:

  - WorkflowOutputProjectionRegistry for contract/version resolution.
  - WorkflowOutputProjectionService for projection orchestration.
  - WorkflowOutputProjectionEventSubscriber for runtime-event integration.
  - WorkflowOutputProjectionPolicy for execution-mode and output eligibility.
  - WorkflowOutputProjectionTelemetry for persistence-specific telemetry.

  ### Durable projection jobs

  Create workflow_output_projection_jobs with first-class columns:

  - projection_job_id
  - run_id
  - workflow_name
  - execution_id
  - node_name
  - projector_name
  - output_contract
  - output_schema_version
  - source_fingerprint
  - status
  - attempt_count
  - last_error
  - created_at
  - started_at
  - completed_at
  - updated_at

  Add a unique constraint across:

  run_id
  projector_name
  node_name
  source_fingerprint

  Supported statuses:

  pending
  running
  succeeded
  failed
  skipped

  The job table provides retry, reconciliation, idempotency, and operational visibility without changing workflow success semantics.

  ## Implementation Steps

  ### Step 1 — Document the projection coverage matrix

  Audit every production workflow node and record:

  - Node name.
  - Typed source object produced before serialization.
  - Current runtime output shape.
  - Proposed output contract and schema version.
  - Target curated record types.
  - Existing persistence service and repository.
  - Missing first-class database fields.
  - Projection eligibility rules.

  Explicitly classify outputs as:

  projectable
  runtime-archive-only
  backtest-only
  report-orchestrated
  unsupported-until-schema-exists

  Verify that morning reports and backtests remain on their existing explicit persistence paths and are not accidentally duplicated.

  ### Step 2 — Add projection status and result models

  Create immutable typed models for:

  - Projection status.
  - Projection request.
  - Per-projector outcome.
  - Completed-run projection summary.
  - Retry and reconciliation requests/results.

  Keep JSON dictionaries confined to the completed-run serialization input boundary.

  ### Step 3 — Add generic runtime output contract identity

  Add output_contract and output_schema_version to RuntimeNodeOutput.

  Requirements:

  - Existing non-projectable nodes may leave output_contract=None.
  - The schema version must be positive.
  - Serialization, checkpoint, replay, and completed-run archival must preserve both fields.
  - No runtime code may contain knowledge of projectors or curated database tables.

  Add compatibility tests for old archived outputs that lack these fields; they remain loadable but are not automatically projected unless a deterministic legacy decoder is explicitly registered.

  ### Step 4 — Add the projection job database model and migration

  Create the SQLAlchemy model, indexes, enum/check constraints, and Alembic migration for workflow_output_projection_jobs.

  Add indexes for:

  - Status and creation time.
  - Workflow and execution ID.
  - Projector and node name.
  - Failed or pending job retrieval.

  Run migration metadata-divergence and blank-database upgrade tests.

  ### Step 5 — Implement the projection job repository

  Add a typed PostgreSQL repository supporting:

  - Idempotent job creation.
  - Claiming a pending or failed job.
  - Marking running, succeeded, failed, or skipped.
  - Incrementing attempt counts.
  - Listing jobs by run, status, workflow, or projector.
  - Recovering stale running jobs.
  - Detecting archived runs with missing projection jobs.

  Use database transactions and row locking where necessary to prevent concurrent duplicate execution.

  ### Step 6 — Implement the projection registry

  Implement exact projector resolution by:

  output_contract + output_schema_version

  Rules:

  - Duplicate projector registrations fail at startup.
  - Unknown contracts are reported as unsupported, not treated as errors.
  - Unsupported schema versions produce a visible skipped or failed result.
  - Matching must never depend on fuzzy payload inspection.
  - Node names may be used as an additional validation constraint, but not as the sole schema contract.

  ### Step 7 — Implement projection eligibility policy

  The policy will make deterministic decisions based on first-class run and node fields.

  Default rules:

  - Project only archived node outputs with success=True.
  - Skip failed and skipped nodes.
  - Skip backtest and simulated executions from live curated tables.
  - Keep backtest persistence in the existing backtest tables.
  - Skip unsupported output contracts.
  - Allow explicit reprojection of normal completed runs.
  - Treat replay/resume safely through deterministic identities.
  - Persist degraded or fallback outputs only when the target schema has first-class quality/status fields; otherwise skip them with an explicit reason.
  - Do not infer execution mode from arbitrary metadata if a first-class run field is required; add the field and migration instead.

  ### Step 8 — Implement the projection coordinator

  Implement WorkflowOutputProjectionService.project_completed_run():

  1. Load the CompletedRunBundle.
  2. Evaluate every node output through the projection policy.
  3. Resolve the matching projector.
  4. Calculate a deterministic source fingerprint.
  5. create or retrieve the projection job.
  6. Claim the job.
  7. Invoke the projector.
  8. Persist job outcome.
  9. Return a typed run-level summary.

  Projection failures must:

  - Not change the workflow execution result.
  - Be recorded in the projection job.
  - Emit structured logs, metrics, and traces.
  - Remain retryable.
  - Not roll back successfully committed projections from unrelated nodes.

  ### Step 9 — Add the workflow completion subscriber

  Subscribe an application-owned handler to:

  WORKFLOW_COMPLETED
  WORKFLOW_FAILED

  The handler will:

  - Run after completed-run archival.
  - Load the archived run using workflow name and execution ID.
  - Invoke the projection coordinator.
  - Project successful eligible nodes even when a later node caused the workflow to fail.
  - Report a missing completed-run archive as an observable projection failure.
  - Rely on the EventBus non-fail-fast behavior so projection failure cannot convert a successful workflow into a failed workflow.

  Do not add domain persistence logic to WorkflowEngine.

  ### Step 10 — Wire projection through canonical DI and bootstrap

  Register through Dishka:

  - Projection job repository.
  - Registry.
  - Policy.
  - Coordinator.
  - Telemetry emitter.
  - Event subscriber.
  - Domain projectors.

  Activate the subscriber once at application startup against the shared canonical EventBus.

  Verify:

  - No duplicate subscribers.
  - Request/session ownership is deterministic.
  - CLI, backtesting, future MCP, and other interfaces use the same shared projection infrastructure.
  - The runtime bootstrap does not import domain projectors.

  ### Step 11 — Add shared lineage and deterministic identity helpers

  Use PersistenceLineage for every projected record:

  workflow_name
  execution_id
  runtime_id
  node_name

  Generate deterministic record IDs from:

  record type
  execution ID
  node name
  domain natural key
  source timestamp or observation timestamp

  Do not use random UUIDs for records derived deterministically from a completed workflow output.

  Reprojecting the same archived output must update or no-op against the same record identity rather than create duplicates.

  ### Step 12 — Normalize projectable node output contracts

  **Execution switch:** Begin this step only after Strategy Steps 1–20 are complete. For strategy nodes, use the finalized structured-hypothesis contracts; do not normalize or preserve the previous generic strategy payload.

  For each projectable node:

  - Build a typed result/signal internally.
  - Serialize only when creating RuntimeNodeOutput.
  - Set its stable output contract and schema version.
  - Add or complete typed from_dict() boundary decoding.
  - Preserve full numeric precision.
  - Remove persistence-oriented payload construction from node logic.
  - Ensure required timestamps, symbols, account IDs, source identities, and quality states are first-class fields.

  Do not add missing values to generic features or metadata dictionaries merely to support projection.

  ### Step 13 — Implement the technical and market projector

  Project technical_agent output into applicable typed records:

  - TechnicalAnalysisSnapshotRecord
  - MarketContextSnapshotRecord
  - MarketBreadthSnapshotRecord
  - Other market records only when the output contains the complete canonical source data.

  Use MarketPersistenceService.

  Do not reconstruct provider facts that were not included in the node output. If required canonical fields are absent, update the typed node output contract first.

  ### Step 14 — Implement macro projection

  Expose the complete typed macro result through the appropriate projectable node output.

  Project into:

  - MacroObservationRecord
  - MacroRegimeSnapshotRecord
  - EconomicCalendarEventRecord, when actually present.

  Use MacroPersistenceService.

  Do not derive macro observations from narrative LLM text.

  ### Step 15 — Implement news and sentiment projectors

  Project eligible outputs into:

  - NewsArticleRecord
  - NewsAnalysisSnapshotRecord
  - SentimentSnapshotRecord
  - SentimentSourceRecord

  Use the existing news and sentiment persistence services.

  Persist source articles or sentiment sources only when their canonical vendor/source identity and timestamps are available. Otherwise persist only the analysis snapshot.

  ### Step 16 — Implement generic intelligence-signal projection

  **Coordinated strategy stage:** Execute the strategy portion of this step together with Strategy Step 21. Bull, Bear, Sideways, and synthesis outputs must use the finalized structured-hypothesis contracts and dedicated strategy persistence records. They must not be flattened into the legacy generic signal payload merely for reuse of an existing table.

  Project typed signals from:

  - Fundamental analysis.
  - Technical analysis.
  - News analysis.
  - Sentiment analysis.
  - Individual risk agents.
  - Risk aggregation.
  - Bull, bear, and sideways regime agents.
  - Strategy synthesis.

  Use existing agent signal/intelligence records for analytical signals whose canonical schema fits those records:

  - Signal score and confidence.
  - Regime.
  - Reasoning.
  - Recommendations.
  - Risk assessments.
  - Source lineage.

  Structured strategy hypotheses and synthesis decisions are excluded from the generic agent-signal table. Persist them through the first-class strategy models created by Strategy Steps 19–20.

  Do not put an entire serialized node output into a metadata column.

  ### Step 17 — Implement recommendation and trade projection

  **Coordinated strategy stage:** Execute strategy-synthesis mapping in this step together with Strategy Step 21. The persisted `StrategySynthesisDecision` remains distinct from a recommendation, allocation intent, trade proposal, execution decision, and realized outcome.

  Project appropriate outputs from:

  - strategy_synthesis_agent
  - portfolio_manager_agent
  - trade_packager
  - execution_risk_guard

  Into:

  - RecommendationRecord
  - RecommendationRationaleRecord
  - TradeSetupRecord
  - RecommendationOutcomeRecord only when an actual outcome exists.
  - WatchlistItemRecord only when explicitly produced.

  Preserve the distinction between:

  strategy recommendation
  allocation intent
  trade proposal
  execution approval decision
  realized outcome

  Do not collapse them into one generic recommendation payload.

  ### Step 18 — Refactor the portfolio analysis result

  Update PortfolioAnalysisResult to return all persistence-relevant typed data:

  - Current canonical portfolio state.
  - Positions.
  - Exposures.
  - Risk metrics.
  - Allocation data.
  - Current equity.
  - Historical equity points.
  - Peak equity and drawdown calculations.
  - Provider source and timeframe.

  Calculate peak equity from authoritative provider history plus current equity.

  Ensure the provider requests a sufficiently complete history window rather than relying on a short vendor default period.

  ### Step 19 — Implement the portfolio projector

  Project portfolio_state_builder and related eligible outputs into:

  - Canonical portfolio state snapshot/latest state.
  - Position history.
  - Latest positions.
  - Equity history points.
  - Exposure snapshots.
  - Risk snapshots.
  - Allocation snapshots.

  Use PortfolioPersistenceService from the projector rather than from PortfolioService.

  Ensure one workflow run produces one deterministic set of portfolio records.

  ### Step 20 — Remove direct persistence from PortfolioService

  After the portfolio projector passes integration tests:

  - Remove PortfolioPersistenceService from PortfolioService.
  - Remove previous-state database reads used only for peak-equity calculation.
  - Remove direct state and equity-history writes.
  - Keep portfolio analysis focused on provider orchestration and calculation.
  - Update Dishka providers and service tests.
  - Confirm that completed-run archival and curated portfolio persistence remain separate and non-duplicating.

  Do not remove portfolio repositories or tables; they remain the curated system-of-record targets used by the projector.

  ### Step 21 — Preserve report and backtest persistence boundaries

  Explicitly exclude:

  - Morning report documents from generic node-output projection because they are assembled after workflow execution and already use MorningReportPersistenceService.
  - Backtest result bundles from live curated projection because they already use BacktestPersistenceService.

  Add duplicate-prevention tests demonstrating that enabling workflow projection does not create a second report or backtest record.

  ### Step 22 — Add projection telemetry

  Create persistence-specific telemetry rather than reusing ApplicationServiceTelemetry or ApplicationRagTelemetry.

  Emit:

  - Projection run started/completed/failed.
  - Projector started/completed/failed/skipped.
  - Projection latency.
  - Records persisted per record type.
  - Retry count.
  - Unsupported contract/version count.
  - Missing archive count.
  - Stale job recovery count.

  Preserve trace context from the workflow completion event through repository writes and concurrent projector tasks.

  ### Step 23 — Add operational commands

  Extend completed-run CLI operations with:

  polaris completed-runs projection-status
  polaris completed-runs project
  polaris completed-runs retry-projection
  polaris completed-runs reconcile-projections

  Capabilities:

  - Inspect projection jobs by workflow/execution.
  - Reproject one archived run.
  - Retry failed jobs.
  - Requeue stale running jobs.
  - Find archived runs with missing projection jobs.
  - Run in dry-run mode where appropriate.

  All CLI commands must remain thin async boundaries and resolve services through Dishka request scope.

  ### Step 24 — Add unit coverage

  Test:

  - Runtime output contract serialization and backward compatibility.
  - Registry registration and resolution.
  - Unsupported contract and version handling.
  - Policy decisions for live, failed, skipped, backtest, simulated, replay, and fallback outputs.
  - Deterministic fingerprints and record IDs.
  - Job state transitions.
  - Projector decoding and mapping.
  - Individual persistence-service calls.
  - Projection failure isolation.
  - Portfolio peak-equity calculation from provider history.
  - Removal of direct portfolio persistence.

  ### Step 25 — Add PostgreSQL integration coverage

  Using a live test PostgreSQL database, verify:

  - Alembic upgrade from blank database.
  - ORM metadata matches the migrated schema.
  - Workflow completion creates projection jobs.
  - Successful node outputs populate curated tables.
  - Failed downstream workflows still project valid successful upstream outputs.
  - Backtest runs do not populate live curated tables.
  - Reprocessing a run produces no duplicate records.
  - Failed jobs can be retried.
  - Stale jobs can be recovered.
  - Portfolio state and history are persisted exactly once.
  - Workflow success is unaffected by projector failure.

  ### Step 26 — Verify RAG compatibility

  Run curated RAG source loading against the newly populated tables.

  Confirm:

  - Newly projected records satisfy existing eligibility rules.
  - Raw completed-run outputs remain ineligible.
  - RAG ingestion still begins from curated PostgreSQL records.
  - Projection does not call Qdrant, Neo4j, embedding, reranking, or RAG services.
  - A projection retry does not automatically duplicate RAG documents.

  ### Step 27 — Run full quality gates

  Run in the required order:

  ruff check --fix
  ruff format
  mypy . --explicit-package-bases
  pytest
  database migration tests
  live projection integration tests
  graphify update .

  Run Repowise health and blast-radius checks for:

  - Runtime output changes.
  - Workflow completion subscription.
  - PortfolioService.
  - Projection coordinator.
  - Persistence DI.
  - Database models and repositories.

  Resolve all regressions introduced by the projection implementation.

  ### Step 28 — Document the canonical persistence architecture

  Update architecture documentation to distinguish:

  runtime node output
  completed-run archive
  curated domain record
  RAG document
  vector projection
  graph projection

  Document:

  - Output contracts and schema versioning.
  - Projector registration.
  - Projection eligibility.
  - Live versus backtest isolation.
  - Retry and reconciliation.
  - Idempotency and lineage.
  - Why application services and intelligence nodes do not persist directly.
  - How to add a new projectable node safely.

  ## Acceptance Criteria

  The implementation is complete when:

  1. Normal workflow execution automatically produces eligible curated records.
  2. Runtime core contains no application-domain persistence logic.
  3. Application services and intelligence nodes do not directly write curated records.
  4. PortfolioService no longer reads or writes persistence solely for peak equity.
  5. Every projected record has deterministic identity and workflow lineage.
  6. Reprojecting an archived run creates no duplicates.
  7. Backtest and simulated outputs cannot contaminate live curated tables.
  8. Projection failures are observable and retryable but do not alter workflow success.
  9. Missing domain fields result in typed schema/model changes, not metadata dumping.
  10. RAG continues to ingest only explicitly eligible curated PostgreSQL records.
  11. Morning report and backtest persistence are not duplicated.
  12. Migration, unit, integration, Ruff, MyPy, and full test suites pass.

  ## Assumptions and Defaults

  - PostgreSQL remains the authoritative system of record.
  - Completed-run archival occurs before the workflow completion event is emitted.
  - Projection is synchronous with completion-event handling initially, but failures remain non-fatal. Durable jobs make later asynchronous worker extraction possible without changing projector contracts.
  - Successfully completed upstream nodes may be projected even if the overall workflow later fails.
  - Backtest and simulated runs remain isolated in dedicated backtesting persistence.
  - Existing curated tables and persistence services will be reused wherever their schemas are complete.
  - Schema migrations are permitted when canonical node outputs contain important data without first-class columns.
  - No compatibility wrappers will preserve direct service persistence after the canonical projector is operational.
  - Automatic RAG ingestion is outside this plan; this plan only ensures RAG-eligible curated records exist in PostgreSQL.