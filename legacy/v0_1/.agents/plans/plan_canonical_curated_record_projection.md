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


  #### Step 1 coverage matrix and audit findings

  Step 1 audit was completed against the current source state on 2026-07-09.

  Current workflow registration findings:

  - `workflows/catalog.py` registers only `MorningReportWorkflow` as a built-in production workflow.
  - `workflows/definitions/strategies/momentum_strategy.py` and `workflows/definitions/strategies/strategy_review.py` currently exist as zero-byte placeholders and have no production nodes to project yet.
  - `core/workflow/examples/*` and `plugins/example_market_plugin/*` are examples/plugin scaffolding and should remain runtime-archive-only unless a future plan promotes them to production workflows.
  - Backtests execute canonical workflows through `BacktestService` with `mode="backtest"`; their completed-run archives are eligible for audit/replay, but live curated projection must skip them.

  Morning report node coverage:

  | Node | Source object before serialization | Current runtime output shape | Proposed contract | Target curated record types | Persistence owner | Missing fields / blockers | Eligibility |
  | --- | --- | --- | --- | --- | --- | --- |
  | `portfolio_state_builder` | `PortfolioAnalysisResult` -> `PortfolioStateDecision` | Canonical portfolio-state output with first-class state, positions, exposures, risk, allocation, equity history, provider, period, and timeframe fields | `polaris.portfolio.state` v1 | Portfolio records via workflow-output projector and `PortfolioPersistenceService` | Steps 18-20 completed the service-result refactor, portfolio projector, and direct service-persistence removal. | Projectable. |
  | `fundamental_agent` | `MacroAnalysisResult` plus deterministic scoring | Generic signal envelope (`directional_score`, `confidence`, `regime`, `signals`, `risks`, `recommendations`, `features`) | `polaris.agent.fundamental_signal` v1 | Agent signal/intelligence persistence | Needs stable timestamp/source lineage in the output contract before durable projection. Macro observations should come from macro service output, not LLM narrative. | Projectable once contract identity and decoder exist. |
  | `technical_agent` | `TechnicalAnalysisResult` plus `TechnicalSignal`-style mapping | Generic signal envelope with technical `features` including snapshot, market context, trend, volatility, breadth, raw/calibrated regime | `polaris.market.technical_analysis` v1 | `MarketPersistenceService` | Needs a typed boundary decoder and first-class observation timestamp/source fields; existing output is the best technical/market projection source. | Projectable. |
  | `news_agent` | News provider articles plus LLM analysis | Generic signal envelope; failure path returns successful degraded output with `features.error` | `polaris.news.analysis` v1 | `NewsPersistenceService` | Source articles require canonical source/vendor IDs and timestamps. LLM failure output must be skipped unless target schema has quality/status fields. | Conditionally projectable; degraded/fallback outputs must be policy-gated. |
  | `sentiment_agent` | Sentiment service/provider data plus LLM analysis | Generic signal envelope; raw typed sentiment is currently in execution metadata (`raw_sentiment_data`) rather than outputs | `polaris.sentiment.snapshot` v1 | `SentimentPersistenceService` | Persistence-relevant raw sentiment/source data must move into typed outputs; execution metadata must not be a durable data contract. | Projectable after output normalization. |
  | `drawdown_risk_agent` | `RiskSignalContract` | Risk adapter generic signal envelope | `polaris.risk.drawdown_signal` v1 | Agent signal/intelligence persistence or portfolio risk snapshots | Needs deterministic observation timestamp/account ID/source lineage. | Projectable after contract identity. |
  | `exposure_risk_agent` | `RiskSignalContract` | Risk adapter generic signal envelope | `polaris.risk.exposure_signal` v1 | Agent signal/intelligence persistence or portfolio risk snapshots | Needs deterministic observation timestamp/account ID/source lineage. | Projectable after contract identity. |
  | `volatility_risk_agent` | `VolatilityRiskDecision` -> `RiskSignalContract` | Risk adapter generic signal envelope with breadth annotations | `polaris.risk.volatility_signal` v1 | Agent signal/intelligence persistence or portfolio risk snapshots | Needs source timestamp/symbol and stable breadth annotation fields in outputs. | Projectable after contract identity. |
  | `risk_signal_builder` | Aggregated `RiskSignalContract` | Risk adapter generic signal envelope | `polaris.risk.aggregate_input_signal` v1 | Agent signal/intelligence persistence | Intermediate aggregation input; likely useful for audit but may duplicate final risk aggregator if projected blindly. | Runtime-archive-only by default; project only if an explicit risk-lineage record is needed. |
  | `risk_aggregator_agent` | Enriched `RiskSignalContract` | Risk adapter generic signal envelope with regime coupling and breadth context | `polaris.risk.aggregate_signal` v1 | Agent intelligence/risk assessment persistence and portfolio risk snapshots | Needs stable source lineage and quality status. | Projectable; preferred canonical risk projection over `risk_signal_builder`. |
  | `attribution_engine` | Contribution/attribution calculation map | Generic attribution output | `polaris.attribution.explanation` v1 | `AttributionPersistenceService` | Needs typed attribution record mapping and deterministic IDs by source signal/recommendation. | Projectable after typed decoder. |
  | `adaptive_weighting_engine` | Strategy weighting calculation | Generic weighting output | `polaris.strategy.weights` v1 | Strategy/intelligence persistence | Depends on structured-hypothesis strategy contracts; should not freeze legacy shape first. | Defer until Strategy Steps 1-20. |
  | `bull_agent` | Bull thesis calculation | Generic strategy/regime signal output | `polaris.strategy.hypothesis.bull` v1 | Future first-class strategy persistence | Must use finalized structured-hypothesis schema, not generic signal flattening. | Defer until Strategy Steps 1-20 and coordinated Step 16/17. |
  | `bear_agent` | Bear thesis calculation | Generic strategy/regime signal output | `polaris.strategy.hypothesis.bear` v1 | Future first-class strategy persistence | Must use finalized structured-hypothesis schema, not generic signal flattening. | Defer until Strategy Steps 1-20 and coordinated Step 16/17. |
  | `sideways_agent` | Sideways thesis calculation | Generic strategy/regime signal output | `polaris.strategy.hypothesis.sideways` v1 | Future first-class strategy persistence | Must use finalized structured-hypothesis schema, not generic signal flattening. | Defer until Strategy Steps 1-20 and coordinated Step 16/17. |
  | `strategy_synthesis_agent` | `StrategySynthesisDecision` plus market events | Primary path returns `decision.to_runtime_outputs()`; fallback path returns successful degraded generic output | `polaris.strategy.synthesis` v1 | Future first-class strategy persistence and recommendation persistence where appropriate | Must distinguish synthesis decision from recommendation/allocation/trade/execution decision. Fallback outputs must be quality-gated. | Defer strategy semantics until structured-hypothesis plan completes. |
  | `portfolio_manager_agent` | Portfolio management calculation | Generic recommendation/allocation-style output | `polaris.portfolio.allocation_intent` v1 | Portfolio/recommendation persistence | Must preserve allocation intent distinct from strategy recommendation and trade proposal. | Projectable after typed output normalization. |
  | `trade_packager` | Trade packaging calculation | Generic trade setup output | `polaris.trade.recommendation` v1 | `RecommendationPersistenceService` / trade setup records | Must not create outcome records without realized outcome; needs deterministic symbol/time identity. | Projectable after typed output normalization. |
  | `execution_risk_guard` | Risk guard `RiskSignalContract` | Risk adapter generic signal envelope with `features.execution_guard` | `polaris.execution.risk_decision` v1 | Recommendation/trade decision or agent risk assessment persistence | Must preserve approval/guard decision distinct from trade proposal and realized execution. | Projectable after typed output normalization. |

  Existing explicit persistence boundaries confirmed:

  - Morning report documents are assembled after workflow execution and persisted through `MorningReportPersistenceService`; they must remain excluded from generic node-output projection.
  - Backtest scenarios/runs/results are persisted through `BacktestService` / `BacktestPersistenceService`; backtest workflow outputs must not populate live curated tables.
  - Completed-run archival already persists workflow evidence in `completed_workflow_runs`, `completed_workflow_node_outputs`, and `completed_run_artifacts`; projection must use those records as input, not bypass them.
  - `PortfolioService` is the current architectural exception: it reads latest portfolio state for peak equity and writes portfolio state/equity history directly. Steps 18-20 must move that durable write responsibility to the projector after the typed service result includes all persistence-relevant portfolio data.

  Cross-cutting blockers found in Step 1:

  - `RuntimeNodeOutput` currently has no `output_contract` or `output_schema_version`; Step 3 must add the generic runtime identity before reliable projection can be implemented.
  - Completed node-output archive records currently persist outputs and metadata but do not expose explicit contract/version fields; Step 3 must preserve those fields through completed-run serialization.
  - Several nodes place persistence-relevant source data in `execution_metadata` rather than `outputs`; Step 12 must normalize those into typed output contracts where they are canonical.
  - Some nodes use successful outputs to represent degraded/fallback states. The projection policy must skip those unless the target table has first-class quality/status fields.
  - Multiple risk nodes share the same generic `RiskSignalContract` shape. The projection registry must resolve by explicit contract/version, not by fuzzy payload inspection or node name alone.
  - Strategy outputs must wait for the structured-hypothesis plan before durable semantics are finalized.

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

  ### Step 7B — Add first-class completed-run execution mode

  Add a durable first-class execution-mode field to completed-run archives before
  the projection coordinator consumes eligibility.

  Requirements:

  - Add a typed completed-run execution-mode contract with allowed values `normal`, `replay`, `backtest`, and `simulated`.
  - Add `execution_mode` to `CompletedRunRecord` and `CompletedWorkflowRunModel`.
  - Add an Alembic migration that backfills existing completed runs to `normal` and enforces allowed values.
  - Preserve execution mode through completed-run serialization, ORM mapping, and repository upserts.
  - Treat top-level runtime-context execution mode as the archival source; do not infer this value from arbitrary metadata.
  - Update projection eligibility to consume the canonical completed-run execution-mode contract instead of maintaining a competing mode definition.
  - Add focused tests for serializer mapping, model/schema metadata, upsert values, and eligibility handoff readiness.

  ### Step 8 — Implement the projection coordinator

  Implement WorkflowOutputProjectionService.project_completed_run():

  1. Load the CompletedRunBundle.
  2. Evaluate every node output through the projection policy using `CompletedRunRecord.execution_mode` as the canonical execution-mode source.
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

  ## Step Results

  ### Step 1 — Document the projection coverage matrix

  Completed on 2026-07-09.

  - Audited the registered workflow catalog and confirmed that `morning_report` is the only built-in production workflow currently registered.
  - Confirmed `momentum_strategy.py` and `strategy_review.py` are zero-byte placeholders and should not drive projection work yet.
  - Documented the current morning-report node output coverage matrix, proposed contracts, target persistence owners, blockers, and eligibility classifications.
  - Confirmed that morning report persistence and backtest persistence are explicit boundaries that must not be duplicated by generic node-output projection.
  - Identified the current portfolio persistence exception: `PortfolioService` still reads/writes portfolio persistence directly, so Steps 18-20 remain necessary to move durable workflow-derived portfolio writes into the projector.
  - Identified cross-cutting blockers for upcoming steps: missing `RuntimeNodeOutput` contract/version identity, completed-run archive contract preservation, metadata-held source data, degraded successful outputs, shared risk payload shape, and strategy-contract dependency on the structured-hypothesis plan.

  Verification:

  - Reviewed `workflows/catalog.py`, `workflows/definitions/reports/morning_report.py`, current strategy placeholder files, core completed-run archive models, `RuntimeNodeOutput`, portfolio direct persistence, report persistence, backtest workflow execution, and morning-report node implementations.
  - Documentation-only update; no Python behavior changed and no test execution was required.

### Step 2 — Add projection status and result models

Completed on 2026-07-09.

- Added immutable typed projection models under `application/projections/workflow_outputs/`:
  - `WorkflowOutputProjectionStatus`
  - `WorkflowOutputProjectionRequest`
  - `WorkflowOutputProjectionOutcome`
  - `CompletedRunProjectionSummary`
  - `WorkflowOutputProjectionRetryRequest`
  - `WorkflowOutputProjectionRetryResult`
  - `WorkflowOutputProjectionReconciliationRequest`
  - `WorkflowOutputProjectionReconciliationResult`
- Added package exports through `application.projections.workflow_outputs`.
- Kept these models typed and boundary-clean; no arbitrary `dict[str, Any]` metadata fields were introduced.
- Added focused unit tests covering immutability, identifier validation, status coercion, summary counts, retry validation, and reconciliation validation.

Verification:

- `uv run ruff check application/projections tests/unit/application/projections`
- `uv run ruff format application/projections tests/unit/application/projections`
- `uv run python -m mypy application/projections tests/unit/application/projections --explicit-package-bases`
- `uv run python -m pytest -q tests/unit/application/projections/test_workflow_output_projection_models.py`
- `uv run graphify update .`

Note:

- `uv run pytest ...` initially invoked a stale pytest entrypoint that referenced an old virtualenv path, so the focused test was run with the canonical interpreter form: `uv run python -m pytest ...`.

### Step 3 — Add generic runtime output contract identity

Completed on 2026-07-09.

- Added optional `output_contract` and `output_schema_version` identity fields to `RuntimeNodeOutput`.
- Added runtime validation so `output_contract` cannot be blank, `output_schema_version` must be positive when present, and a contract requires an explicit schema version.
- Added backward-compatible `RuntimeNodeOutput.from_dict()` support so legacy archived outputs without contract identity remain loadable with `None` values.
- Preserved contract identity through runtime execution metadata enrichment, artifact-enriched output replacement, and runtime-context metadata transitions.
- Preserved contract identity through completed-run serialization and PostgreSQL completed node-output records.
- Added nullable first-class completed-run node-output columns and indexes through Alembic migration `c9d0e1f2a3b4`.
- Added compatibility tests proving legacy archived node outputs without contract identity remain loadable and are not implicitly promoted into projectable records.

Verification:

- `uv run ruff check core/runtime/state/runtime_node_output.py core/runtime/contracts/runtime_node.py core/runtime/artifacts/artifact_manager.py core/runtime/execution/runtime_context_transitions.py core/storage/persistence tests/unit/core/runtime/state/test_runtime_node_output_contract.py tests/unit/core/storage/persistence/test_completed_run_serializer.py tests/unit/core/storage/persistence/test_postgres_completed_run_repository.py tests/unit/core/storage/persistence/test_completed_run_archive.py tests/integration/core/storage/persistence/test_postgres_completed_run_repository_integration.py migrations/versions/20260709_120000_c9d0e1f2a3b4_add_node_output_contract_identity.py`
- `uv run ruff format core/runtime/state/runtime_node_output.py core/runtime/contracts/runtime_node.py core/runtime/artifacts/artifact_manager.py core/runtime/execution/runtime_context_transitions.py core/storage/persistence tests/unit/core/runtime/state/test_runtime_node_output_contract.py tests/unit/core/storage/persistence/test_completed_run_serializer.py tests/unit/core/storage/persistence/test_postgres_completed_run_repository.py tests/unit/core/storage/persistence/test_completed_run_archive.py tests/integration/core/storage/persistence/test_postgres_completed_run_repository_integration.py migrations/versions/20260709_120000_c9d0e1f2a3b4_add_node_output_contract_identity.py`
- `uv run python -m mypy core/runtime/state/runtime_node_output.py core/runtime/contracts/runtime_node.py core/runtime/artifacts/artifact_manager.py core/runtime/execution/runtime_context_transitions.py core/storage/persistence tests/unit/core/runtime/state/test_runtime_node_output_contract.py tests/unit/core/storage/persistence/test_completed_run_serializer.py tests/unit/core/storage/persistence/test_postgres_completed_run_repository.py tests/unit/core/storage/persistence/test_completed_run_archive.py --explicit-package-bases`
- `uv run python -m pytest -q tests/unit/core/runtime/state/test_runtime_node_output_contract.py tests/unit/core/storage/persistence/test_completed_run_serializer.py tests/unit/core/storage/persistence/test_postgres_completed_run_repository.py tests/unit/core/storage/persistence/test_completed_run_archive.py tests/unit/core/runtime/state/test_runtime_context_schema.py tests/unit/core/runtime/checkpoints/test_runtime_checkpoint_security.py tests/database/test_migrations.py`
- `uv run graphify update .`
- `git diff --check -- <step-3-paths>`

Results:

- Focused unit/runtime/persistence tests passed: `25 passed, 6 skipped`.
- Focused MyPy passed: `Success: no issues found in 116 source files`.
- Database migration tests were discovered but skipped because no live test database URL was configured for this command.
- Graphify update completed successfully.

Notes:

- This step intentionally touched `core/` because generic output contract identity is a runtime serialization concern, not an application projection concern.
- `RuntimeNodeOutput.from_dict()` does not reconstruct `emitted_events` because `RuntimeEvent` does not currently expose a canonical `from_dict()` contract; existing `to_dict()` serialization and completed-run storage continue to preserve event payloads at the JSON boundary.

### Step 4 — Add the projection job database model and migration

Completed on 2026-07-09.

- Added `WorkflowOutputProjectionJobModel` in `core/database/models/projections.py` for durable projection job tracking.
- Added the `workflow_output_projection_jobs` Alembic migration `d0e1f2a3b4c5` chained after the runtime output contract identity migration.
- Added first-class columns for projection job identity, workflow lineage, projector identity, output contract/version, source fingerprint, status, attempts, error text, and lifecycle timestamps.
- Added idempotency through `uq_workflow_output_projection_jobs_source` across `run_id`, `projector_name`, `node_name`, and `source_fingerprint`.
- Added check constraints for valid projection statuses, non-negative attempts, and positive schema versions.
- Added indexes for status/created-at, workflow/execution, projector/node, pending/failed retrieval, and output contract/version lookup.
- Exported the model through `core.database.models` so SQLAlchemy metadata and migration tests include it.
- Added focused model tests for metadata registration, required identity fields, constraints, indexes, and idempotency.

Verification:

- `uv run ruff check core/database/models/projections.py core/database/models/__init__.py migrations/versions/20260709_130000_d0e1f2a3b4c5_add_workflow_output_projection_jobs.py tests/unit/core/database/test_workflow_output_projection_job_models.py`
- `uv run ruff format core/database/models/projections.py core/database/models/__init__.py migrations/versions/20260709_130000_d0e1f2a3b4c5_add_workflow_output_projection_jobs.py tests/unit/core/database/test_workflow_output_projection_job_models.py`
- `uv run python -m mypy core/database/models/projections.py core/database/models/__init__.py tests/unit/core/database/test_workflow_output_projection_job_models.py --explicit-package-bases`
- `uv run python -m pytest -q tests/unit/core/database/test_workflow_output_projection_job_models.py tests/database/test_migrations.py`
- `uv run graphify update .`
- `git diff --check -- <step-4-paths>`

Results:

- Focused model tests passed: `5 passed`.
- Focused MyPy passed: `Success: no issues found in 3 source files`.
- Export and operation-lifecycle MyPy passed: `Success: no issues found in 2 source files`.
- Migration tests were discovered but skipped because `POLARIS_TEST_DATABASE_URL` was not configured for this command.
- Graphify update completed successfully.

Notes:

- This step intentionally added a core database model and migration because projection job durability is a PostgreSQL system-of-record concern.
- No repository behavior or projector orchestration was added in this step; those remain Step 5 and later concerns.

### Step 5 — Implement the projection job repository

Completed on 2026-07-09.

- Added typed persistence contracts under `core/storage/persistence/projections/`:
  - `WorkflowOutputProjectionJobStatus`
  - `WorkflowOutputProjectionJobRecord`
  - `ProjectionJobClaim`
  - `MissingProjectionRunRecord`
  - `WorkflowOutputProjectionJobRepository`
- Added `PostgresWorkflowOutputProjectionJobRepository` for PostgreSQL-backed projection job execution.
- Implemented idempotent projection job creation using the projection-source unique constraint.
- Implemented atomic pending/failed job claiming with `FOR UPDATE SKIP LOCKED`, a single-row limit, running status transition, and attempt-count increment.
- Implemented terminal transitions for succeeded, failed, and skipped jobs.
- Implemented filtered job listing by run, workflow, execution, projector, and status.
- Implemented stale running-job recovery and completed-run missing-job detection.
- Exported the repository through `core.storage.persistence.repositories`.
- Added focused unit tests covering upsert, rollback, row-lock claiming, terminal transitions, filters, stale recovery, and missing-run detection.

Verification:

- `uv run ruff check core/storage/persistence/projections core/storage/persistence/repositories/postgres_workflow_output_projection_job_repository.py core/storage/persistence/repositories/__init__.py tests/unit/core/storage/persistence/test_workflow_output_projection_job_repository.py`
- `uv run ruff format core/storage/persistence/projections core/storage/persistence/repositories/postgres_workflow_output_projection_job_repository.py tests/unit/core/storage/persistence/test_workflow_output_projection_job_repository.py core/storage/persistence/repositories/__init__.py`
- `uv run python -m mypy core/storage/persistence/projections core/storage/persistence/repositories/postgres_workflow_output_projection_job_repository.py core/storage/persistence/repositories/__init__.py tests/unit/core/storage/persistence/test_workflow_output_projection_job_repository.py --explicit-package-bases`
- `uv run python -m pytest -q tests/unit/core/storage/persistence/test_workflow_output_projection_job_repository.py tests/unit/core/database/test_workflow_output_projection_job_models.py`
- `uv run graphify update .`
- `git diff --check -- <step-5-paths>`

Results:

- Repository and model tests passed: `15 passed`.
- Focused MyPy passed: `Success: no issues found in 6 source files`.
- Graphify update completed successfully.

Notes:

- No live services were required for this step; live PostgreSQL integration remains a later verification concern.
- Claiming is the canonical “mark running” path so the row lock, status transition, and attempt increment happen together.

### Step 6 — Implement the projection registry

Completed on 2026-07-09.

- Added `WorkflowOutputProjectionRegistry` under `application/projections/workflow_outputs/`.
- Added typed registry contracts:
  - `WorkflowOutputProjector`
  - `WorkflowOutputProjectorRegistration`
  - `WorkflowOutputProjectionResolution`
  - `WorkflowOutputProjectionResolutionStatus`
- Implemented exact projector resolution by `output_contract` and `output_schema_version`.
- Implemented startup-style duplicate protection for duplicate contract/schema registrations and duplicate projector names.
- Implemented unsupported-contract and unsupported-schema-version resolution results instead of exceptions during normal lookup.
- Implemented optional node-name validation as an additional guard, not as the primary matching contract.
- Exported registry types from `application.projections.workflow_outputs`.
- Added focused tests for exact resolution, duplicate rejection, unsupported contract handling, unsupported schema-version handling, node-name validation, and registration validation.

Verification:

- `uv run ruff check application/projections/workflow_outputs tests/unit/application/projections/test_workflow_output_projection_registry.py`
- `uv run ruff format application/projections/workflow_outputs/__init__.py application/projections/workflow_outputs/projection_registry.py tests/unit/application/projections/test_workflow_output_projection_registry.py`
- `uv run python -m mypy application/projections/workflow_outputs tests/unit/application/projections/test_workflow_output_projection_registry.py --explicit-package-bases`
- `uv run python -m pytest -q tests/unit/application/projections/test_workflow_output_projection_registry.py tests/unit/application/projections/test_workflow_output_projection_models.py`
- `uv run graphify update .`
- `git diff --check -- <step-6-paths>`

Results:

- Projection model and registry tests passed: `13 passed`.
- Focused MyPy passed: `Success: no issues found in 4 source files`.
- Graphify update completed successfully.

Notes:

- No live services were required for this step.
- Registry matching intentionally ignores payload shape and fuzzy node inspection; node names are only an optional validation constraint after contract/version resolution.

### Step 7 — Implement projection eligibility policy

Completed on 2026-07-09.

- Added `WorkflowOutputProjectionEligibilityPolicy` under `application/projections/workflow_outputs/`.
- Added typed eligibility contracts:
  - `WorkflowOutputProjectionEligibilityContext`
  - `WorkflowOutputProjectionEligibilityDecision`
  - `WorkflowOutputProjectionEligibilityStatus`
  - `WorkflowOutputProjectionSkipReason`
  - `WorkflowProjectionExecutionMode`
  - `WorkflowOutputQualityStatus`
- Implemented deterministic eligibility decisions using first-class policy inputs plus archived node-output fields.
- Implemented default skip rules for failed nodes, skipped nodes, backtest executions, simulated executions, unsupported contracts, unsupported schema versions, and unsupported node names.
- Allowed normal completed runs and replay/reprojection contexts when the node output is successful and registry-supported.
- Added first-class `persists_quality_status` capability to projector registrations so degraded or fallback outputs are skipped unless the target projector explicitly persists quality/status fields.
- Kept the policy free of payload-shape inspection and metadata-based execution-mode inference.
- Exported eligibility policy types from `application.projections.workflow_outputs`.
- Added focused tests for success eligibility, failed/skipped nodes, backtest/simulated skips, replay/reprojection allowance, unsupported registry resolution, node-name validation, degraded/fallback quality handling, and context validation.

Verification:

- `uv run ruff check application/projections/workflow_outputs tests/unit/application/projections/test_workflow_output_projection_eligibility.py tests/unit/application/projections/test_workflow_output_projection_registry.py`
- `uv run ruff format application/projections/workflow_outputs/projection_eligibility.py application/projections/workflow_outputs/projection_registry.py application/projections/workflow_outputs/__init__.py tests/unit/application/projections/test_workflow_output_projection_eligibility.py`
- `uv run python -m mypy application/projections/workflow_outputs tests/unit/application/projections/test_workflow_output_projection_eligibility.py tests/unit/application/projections/test_workflow_output_projection_registry.py --explicit-package-bases`
- `uv run python -m pytest -q tests/unit/application/projections/test_workflow_output_projection_eligibility.py tests/unit/application/projections/test_workflow_output_projection_registry.py tests/unit/application/projections/test_workflow_output_projection_models.py`
- `uv run graphify update .`
- `git diff --check -- <step-7-paths>`

Results:

- Projection model, registry, and eligibility tests passed: `22 passed`.
- Focused MyPy passed: `Success: no issues found in 6 source files`.
- Graphify update completed successfully.

Notes:

- No live services were required for this step.
- Because completed-run records do not yet carry a first-class execution-mode field, the policy accepts execution mode as an explicit first-class eligibility context value instead of inferring it from arbitrary run metadata. The Step 8 coordinator must supply this value from a canonical source and must not use metadata-only inference.

### Step 7B — Add first-class completed-run execution mode

Completed on 2026-07-09.

- Added canonical `CompletedRunExecutionMode` values under completed-run persistence: `normal`, `replay`, `backtest`, and `simulated`.
- Added `CompletedRunRecord.execution_mode` with boundary normalization and explicit `live` → `normal` mapping for the current runtime-context mode field.
- Added `CompletedWorkflowRunModel.execution_mode` with a first-class column, check constraint, and index.
- Added Alembic migration `20260709_140000_e1f2a3b4c5d6_add_completed_run_execution_mode.py` to backfill existing completed runs to `normal` and enforce allowed values.
- Updated completed-run serialization to promote top-level runtime context `execution_mode` or `mode` into the durable completed-run field instead of requiring projection logic to infer from arbitrary metadata.
- Updated completed-run ORM serialization and repository upserts so `execution_mode` round-trips and updates idempotently.
- Updated projection eligibility to reuse the canonical completed-run execution-mode contract instead of maintaining a competing projection-specific enum.
- Added focused tests for execution-mode normalization, serializer promotion, ORM/model constraints, repository SQL/upsert behavior, and eligibility handoff validation.

Verification:

- `uv run ruff check <step-7B-paths>`
- `uv run ruff format <step-7B-paths>`
- `uv run python -m mypy core/storage/persistence/completed_run_archive.py core/database/models/completed_runs.py core/storage/persistence/serializers/completed_run_serializer.py core/storage/persistence/repositories/postgres_completed_run_repository.py application/projections/workflow_outputs/projection_eligibility.py tests/unit/core/storage/persistence/test_completed_run_archive.py tests/unit/core/storage/persistence/test_completed_run_serializer.py tests/unit/core/storage/persistence/test_postgres_completed_run_repository.py tests/unit/core/database/test_completed_run_models.py tests/unit/application/projections/test_workflow_output_projection_eligibility.py --explicit-package-bases`
- `uv run python -m pytest -q tests/unit/core/storage/persistence/test_completed_run_archive.py tests/unit/core/storage/persistence/test_completed_run_serializer.py tests/unit/core/storage/persistence/test_postgres_completed_run_repository.py tests/unit/core/database/test_completed_run_models.py tests/unit/application/projections/test_workflow_output_projection_eligibility.py`
- `uv run alembic heads`
- `uv run graphify update .`
- `git diff --check -- <step-7B-paths>`

Results:

- Focused tests passed: `30 passed`.
- Focused MyPy passed: `Success: no issues found in 10 source files`.
- Alembic reports a single head: `e1f2a3b4c5d6`.
- Graphify update completed successfully.

Notes:

- No live services were required for this step.
- The Step 8 coordinator should now supply `CompletedRunRecord.execution_mode` directly to the eligibility context and must not infer execution mode from completed-run metadata.

### Step 8 — Implement the projection coordinator

Completed on 2026-07-09.

- Added `WorkflowOutputProjectionService.project_completed_run()` as the canonical coordinator for projecting archived completed-run node outputs into curated records.
- Added `WorkflowOutputProjectorRequest` so projectors receive a typed per-node request containing the completed run, node output, deterministic source fingerprint, and request flags.
- Extended the projector protocol with `project()` so registered projectors can be invoked through the typed registry boundary.
- Implemented deterministic source fingerprinting from completed-run/node-output identity, contract/schema, status, payload, metadata, and errors.
- Wired coordinator flow to:
  - load `CompletedRunBundle` from the completed-run archive,
  - evaluate every node through the eligibility policy,
  - use `CompletedRunRecord.execution_mode` as the canonical execution-mode source,
  - resolve projector registrations,
  - create idempotent projection jobs,
  - claim the exact projection job before projector invocation,
  - persist succeeded, skipped, and failed job outcomes,
  - return `CompletedRunProjectionSummary`.
- Added exact `claim_job()` support to the projection-job repository contract and PostgreSQL implementation so the coordinator can claim the job it just created or retrieved.
- Preserved retryability by leaving failed jobs in the durable job table with recorded error details rather than rolling back unrelated successful projections.
- Added structured logs for missing archives, skipped nodes, projector failures, and run completion.
- Added optional observability-manager integration for projection events, run/job metrics, projector failure metrics, and trace-context propagation without making telemetry failures fatal.
- Added focused coordinator tests for success, execution-mode skip behavior, projector failure recording, already-succeeded idempotency, forced reproject, missing archive handling, and deterministic fingerprinting.
- Added repository test coverage for claiming a specific projection job by ID.

Verification:

- `uv run ruff check application/projections/workflow_outputs core/storage/persistence/projections core/storage/persistence/repositories/postgres_workflow_output_projection_job_repository.py tests/unit/application/projections tests/unit/core/storage/persistence/test_workflow_output_projection_job_repository.py --fix`
- `uv run ruff format application/projections/workflow_outputs core/storage/persistence/projections core/storage/persistence/repositories/postgres_workflow_output_projection_job_repository.py tests/unit/application/projections tests/unit/core/storage/persistence/test_workflow_output_projection_job_repository.py`
- `uv run python -m mypy application/projections/workflow_outputs core/storage/persistence/projections core/storage/persistence/repositories/postgres_workflow_output_projection_job_repository.py tests/unit/application/projections tests/unit/core/storage/persistence/test_workflow_output_projection_job_repository.py --explicit-package-bases`
- `uv run python -m pytest -q tests/unit/application/projections tests/unit/core/storage/persistence/test_workflow_output_projection_job_repository.py`
- `uv run graphify update .`
- `git diff --check`

Results:

- Focused Ruff passed.
- Focused MyPy passed: `Success: no issues found in 14 source files`.
- Focused tests passed: `40 passed`.
- Graphify update completed successfully.
- `git diff --check` passed.

Notes:

- No live services were required for this step.
- The coordinator does not alter workflow execution results; projection failures are represented only in projection job state and the run-level projection summary.
- Step 9 can now add the terminal workflow-event subscriber around the coordinator boundary without creating a second projection orchestration path.

### Step 9 — Add the workflow completion subscriber

Completed on 2026-07-09.

- Added `WorkflowOutputProjectionEventSubscriber` under `application/projections/workflow_outputs/` as the application-owned terminal workflow event handler.
- Added `WorkflowOutputProjectionCoordinator` protocol so the subscriber depends on the narrow projection coordinator boundary instead of a concrete runtime or database implementation.
- Added `WorkflowOutputProjectionEventSubscriberConfig` with explicit `force_reproject` and `dry_run` controls for future DI/bootstrap wiring.
- Subscribed only to `RuntimeEventType.WORKFLOW_COMPLETED` and `RuntimeEventType.WORKFLOW_FAILED`.
- Resolved `workflow_name` deterministically from event payload, then metadata, then `event.workflow_id` fallback.
- Constructed `WorkflowOutputProjectionRequest` from the terminal runtime event and delegated projection to the coordinator.
- Left projection exceptions unhandled in the subscriber so the canonical `EventBus` non-fail-fast behavior isolates subscriber failures and emits `SYSTEM_WARNING` without changing workflow success semantics.
- Kept workflow/domain persistence logic out of `WorkflowEngine`; no runtime files were changed for this step.
- Exported the subscriber and config from `application.projections.workflow_outputs`.
- Added focused unit tests for subscription registration, completed-event projection, failed-event projection, config propagation, workflow-name fallback behavior, direct non-terminal no-op behavior, and EventBus failure isolation.

Verification:

- `uv run ruff check application/projections/workflow_outputs/projection_event_subscriber.py application/projections/workflow_outputs/__init__.py tests/unit/application/projections/test_workflow_output_projection_event_subscriber.py --fix`
- `uv run ruff format application/projections/workflow_outputs/projection_event_subscriber.py application/projections/workflow_outputs/__init__.py tests/unit/application/projections/test_workflow_output_projection_event_subscriber.py`
- `uv run python -m mypy application/projections/workflow_outputs tests/unit/application/projections/test_workflow_output_projection_event_subscriber.py --explicit-package-bases`
- `uv run python -m pytest -q tests/unit/application/projections/test_workflow_output_projection_event_subscriber.py tests/unit/application/projections/test_workflow_output_projection_service.py`
- `uv run graphify update .`
- `git diff --check`

Results:

- Focused Ruff passed.
- Focused MyPy passed: `Success: no issues found in 7 source files`.
- Focused tests passed: `13 passed`.
- Graphify update completed successfully.
- `git diff --check` passed.

Notes:

- No live services were required for this step.
- Step 10 should wire this subscriber through the application/bootstrap DI path after the completed-run archive subscriber so terminal events trigger projection after archival.

### Step 10 — Wire projection through canonical DI and bootstrap

Completed on 2026-07-09.

- Added `WorkflowOutputProjectionDIProvider` to register the projection registry, eligibility policy, and request-scoped projection service through the canonical Dishka provider graph.
- Registered `WorkflowOutputProjectionJobRepository` through the existing PostgreSQL storage DI provider so projection jobs use the canonical SQLAlchemy session boundary.
- Added an application-owned workflow-output projection bootstrap module that builds the default PostgreSQL coordinator and subscribes the projection event subscriber exactly once per shared `EventBus`.
- Activated the projection subscriber from the CLI runtime scope and MCP application lifespan after the canonical workflow runtime has been resolved.
- Kept the runtime bootstrap and runtime assembler free of application projection imports and domain projector imports.
- Intentionally left the default domain-projector registry empty until the coordinated domain projector steps are reached; terminal workflow events can now reach projection infrastructure without freezing unsupported record mappings early.
- Updated MCP lifespan tests to verify the projection subscription happens during startup without importing live PostgreSQL settings in the unit test.
- Added focused tests for projection bootstrap idempotency, DI construction, and the runtime-bootstrap import boundary.

Verification:

- `uv run ruff check application/projections/workflow_outputs core/bootstrap/di_providers.py core/storage/rag_di.py interfaces/cli/bootstrap/container.py mcp_server/lifespan.py tests/unit/application/projections tests/unit/mcp_server/test_lifespan.py --fix`
- `uv run ruff format application/projections/workflow_outputs core/bootstrap/di_providers.py core/storage/rag_di.py interfaces/cli/bootstrap/container.py mcp_server/lifespan.py tests/unit/application/projections tests/unit/mcp_server/test_lifespan.py`
- `uv run mypy application/projections/workflow_outputs core/storage/rag_di.py interfaces/cli/bootstrap/container.py mcp_server/lifespan.py tests/unit/application/projections tests/unit/mcp_server/test_lifespan.py --explicit-package-bases`
- `uv run python -m pytest -q tests/unit/application/projections tests/unit/mcp_server/test_lifespan.py tests/unit/core/bootstrap/test_di_request_scope.py`
- `git diff --check`
- `uv run graphify update .`

Notes:

- No live services were required for this step.
- `core/storage/rag_di.py` is still the current persistence-provider module that hosts multiple PostgreSQL repositories; splitting or renaming that provider module would be a separate structural cleanup and was not included in this surgical step.
- The subscriber bootstrap opens a PostgreSQL request/session scope per terminal workflow event; projection failures remain isolated by the non-fail-fast `EventBus` behavior already verified in the event-subscriber tests.

### Step 11 — Add shared lineage and deterministic identity helpers

Completed on 2026-07-09.

- Added shared workflow-output projection identity helpers in `application/projections/workflow_outputs/projection_identity.py`.
- Added `build_workflow_output_projection_lineage()` to create canonical `PersistenceLineage` from the completed run and the producing node output.
- Added validation that a node output belongs to the completed run before lineage is built, preventing mismatched workflow/execution/run lineage from reaching projectors.
- Added deterministic projected-record identity helpers:
  - `build_projected_record_id()`
  - `build_projected_record_identity()`
  - `build_projected_record_identity_from_projector_request()`
- The deterministic record-id seed includes the record type, execution ID, node name, domain natural key, and source/observation timestamp, so replaying the same archived evidence targets the same curated record identity.
- Extended `WorkflowOutputProjectorRequest` with a first-class `PersistenceLineage` field.
- Updated `WorkflowOutputProjectionService` so every projector invocation receives canonical lineage from the completed run and node output.
- Exported the new helpers from `application.projections.workflow_outputs` for later domain projector steps.
- Added focused unit tests for lineage construction, mismatch rejection, deterministic record ID behavior, projector-request identity generation, and service-to-projector lineage propagation.

Verification:

- `uv run ruff check application/projections/workflow_outputs tests/unit/application/projections --fix`
- `uv run ruff format application/projections/workflow_outputs tests/unit/application/projections`
- `uv run mypy application/projections/workflow_outputs tests/unit/application/projections --explicit-package-bases`
- `uv run python -m pytest -q tests/unit/application/projections`
- `git diff --check`
- `uv run graphify update .`

Notes:

- No live services were required for this step.
- The helpers do not create random IDs for workflow-output-derived records; future projectors should use these helpers, or equivalent domain-specific deterministic helpers, whenever the projected record is derived from archived workflow evidence.
- Domain projectors were not implemented in this step. Step 12 remains gated by the structured-hypothesis plan as documented above.

### Step 12 — Normalize projectable node output contracts

Completed on 2026-07-10.

- Added canonical workflow-output contract constants under `domain.workflow_outputs` so projectable node outputs resolve by stable `output_contract` plus `output_schema_version` instead of legacy names or payload inspection.
- Updated morning-report projectable nodes to set explicit contract identity and schema version at the `RuntimeNodeOutput` boundary:
  - portfolio state and portfolio allocation intent
  - fundamental, technical, news, and sentiment analysis
  - drawdown, exposure, volatility, aggregate-input, aggregate, and execution-risk signals
  - attribution explanation
  - strategy evidence context, perspective weights, bull/bear/sideways hypotheses, and strategy synthesis
  - trade recommendation packaging
- Kept strategy output normalization governed by the finalized structured-hypothesis contracts; no generic legacy strategy payload was added or preserved.
- Extended the risk runtime adapter to carry explicit output contract identity and preserve it through breadth annotation wrapping.
- Added typed boundary decoding for `RiskSignalContract` and `StrategyPerspectiveWeights` and made `RiskSignalContract` immutable with `frozen=True, slots=True`.
- Moved sentiment persistence-relevant source data from execution metadata into first-class output fields (`sentiment_snapshot` and `sentiment_source_data`) while leaving execution metadata for operational context and quality state.
- Added first-class quality-state metadata for normal and degraded projectable outputs where applicable.
- Removed runtime/intelligence numeric rounding and fixed-width numeric formatting from projectable output paths so projection receives full-precision values. Presentation rounding remains a renderer concern.
- Removed persistence-oriented contract markers from serialized output payloads where they belonged on `RuntimeNodeOutput` identity fields instead.
- Added focused tests for structured strategy contract constants, risk contract decoding/immutability, and risk output contract preservation.

Verification:

- `uv run ruff check <step-12-paths> --fix`
- `uv run ruff format <step-12-paths>`
- `uv run mypy <step-12-paths> --explicit-package-bases`
- `uv run pytest -q tests/unit/integration/test_risk_signal_contract.py tests/unit/intelligence/risk/test_drawdown_risk_agent.py tests/unit/intelligence/risk/test_exposure_risk_agent.py tests/unit/intelligence/risk/test_volatility_risk_agent.py tests/unit/intelligence/strategy/test_bear_hypothesis_policy.py tests/unit/intelligence/strategy/test_bull_hypothesis_policy.py tests/unit/intelligence/strategy/test_sideways_hypothesis_policy.py tests/unit/intelligence/strategy/test_strategy_evidence_builder.py tests/unit/intelligence/strategy/test_strategy_perspective_weighting_engine.py tests/unit/intelligence/strategy/test_strategy_synthesis_contracts.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py`
- `POLARIS_POSTGRES_PASSWORD=<local-test-placeholder> uv run pytest -q tests/unit/intelligence/analysts/fundamental/test_fundamental_agent.py tests/unit/intelligence/analysts/technical/test_technical_agent.py tests/unit/intelligence/analysts/technical/test_technical_breadth_context.py tests/unit/intelligence/portfolio/test_portfolio_state_builder.py tests/unit/intelligence/portfolio/test_portfolio_manager_agent.py tests/unit/intelligence/execution/test_execution_risk_guard.py tests/unit/intelligence/execution/test_trade_packager_breadth.py tests/unit/application/reports/morning/test_morning_report_assembler.py tests/unit/application/projections`
- `git diff --check`
- `uv run graphify update .`

Results:

- Focused Ruff passed.
- Focused MyPy passed: `Success: no issues found in 36 source files`.
- Focused risk and strategy tests passed: `50 passed`.
- Focused analyst, portfolio, execution, morning-report, and projection tests passed: `64 passed`.
- `git diff --check` passed.
- Graphify update completed successfully with no code-graph topology changes after the final precision cleanup.

Notes:

- No live services were required for this step.
- Projection projectors were intentionally not implemented in this step; Step 13 remains the first domain projector step.
- Repowise flagged technical, news, sentiment, and risk aggregation files as higher-churn/hotspot areas during preflight, so the implementation stayed surgical and limited to output-contract normalization, precision preservation, and boundary decoding.

### Step 13 — Implement the technical and market projector

Completed on 2026-07-10.

- Added `TechnicalMarketWorkflowOutputProjector` under `application/projections/workflow_outputs/projectors/`.
- Registered the technical market projector against the canonical `polaris.market.technical_analysis` workflow-output contract and schema version `1`.
- Projected eligible `technical_agent` workflow evidence into typed market records through `MarketPersistenceService`:
  - `TechnicalAnalysisSnapshotRecord`
  - `MarketContextSnapshotRecord`
  - `MarketBreadthSnapshotRecord`
- Kept OHLCV, indicator, and market-event records out of this projector because the current technical node output does not contain complete canonical source data for those record types.
- Added first-class `observed_at` and `market_universe` fields to `technical_agent` output so the projector does not mine timestamps or universe identity from generic metadata.
- Wired `MarketPersistenceService` and `PostgresMarketPersistenceRepository` through the application persistence DI provider.
- Updated workflow-output projection DI and the PostgreSQL projection coordinator so a request/session-scoped market persistence service is used when projection events run.
- Deferred PostgreSQL engine creation in the persistence health service until health checks execute, avoiding import-time database settings requirements in projection unit tests.
- Added focused unit coverage for successful market projection, deterministic projected record IDs, missing first-class timestamp skip behavior, canonical projector registration, DI registry wiring, bootstrap idempotency, and technical-agent first-class output fields.

Verification:

- `uv run ruff check application/persistence/health/health_persistence_service.py application/projections/workflow_outputs/projectors application/projections/workflow_outputs/bootstrap.py application/projections/workflow_outputs/di.py application/persistence/di.py intelligence/analysts/technical/technical_agent.py tests/unit/application/projections/test_market_workflow_output_projector.py tests/unit/application/projections/test_workflow_output_projection_di.py tests/unit/application/projections/test_workflow_output_projection_bootstrap.py tests/unit/intelligence/analysts/technical/test_technical_agent.py --fix`
- `uv run ruff format application/persistence/health/health_persistence_service.py application/projections/workflow_outputs/projectors application/projections/workflow_outputs/bootstrap.py application/projections/workflow_outputs/di.py application/persistence/di.py intelligence/analysts/technical/technical_agent.py tests/unit/application/projections/test_market_workflow_output_projector.py tests/unit/application/projections/test_workflow_output_projection_di.py tests/unit/application/projections/test_workflow_output_projection_bootstrap.py tests/unit/intelligence/analysts/technical/test_technical_agent.py`
- `uv run mypy application/projections/workflow_outputs application/persistence/di.py application/persistence/health/health_persistence_service.py intelligence/analysts/technical/technical_agent.py tests/unit/application/projections/test_market_workflow_output_projector.py tests/unit/application/projections/test_workflow_output_projection_di.py tests/unit/application/projections/test_workflow_output_projection_bootstrap.py tests/unit/intelligence/analysts/technical/test_technical_agent.py --explicit-package-bases`
- `uv run pytest -q tests/unit/application/projections/test_market_workflow_output_projector.py tests/unit/application/projections/test_workflow_output_projection_di.py tests/unit/application/projections/test_workflow_output_projection_bootstrap.py tests/unit/intelligence/analysts/technical/test_technical_agent.py`
- `uv run pytest -q tests/unit/application/projections`
- `uv run graphify update .`
- `git diff --check`

Results:

- Focused Ruff passed.
- Focused MyPy passed: `Success: no issues found in 18 source files`.
- Focused projector/DI/bootstrap/technical-agent tests passed: `10 passed`.
- Projection test suite passed: `49 passed`.
- Graphify update completed successfully.
- `git diff --check` passed.

Notes:

- No live services were required for this step.
- The projector skips archived outputs that lack first-class `observed_at`, `market_universe`, or symbol identity rather than reconstructing provider facts from metadata.
- Step 14 can now implement macro projection using the same pattern: typed output contract eligibility, first-class source fields, deterministic projected IDs, and the canonical application persistence service for the target durable records.

### Step 14 — Implement macro projection

Completed on 2026-07-10.

- Added `MacroAnalysisWorkflowOutputProjector` under `application/projections/workflow_outputs/projectors/`.
- Registered the macro projector against the canonical `polaris.macro.analysis` workflow-output contract and schema version `1`.
- Projected eligible `fundamental_agent` macro workflow evidence into typed macro records through `MacroPersistenceService`:
  - `MacroObservationRecord`
  - `MacroRegimeSnapshotRecord`
  - `EconomicCalendarEventRecord`, only when first-class calendar events are present in the output.
- Added first-class macro output fields to the fundamental agent output boundary:
  - `observed_at`
  - `macro_source`
  - `macro_region`
  - `macro_analysis`
- Added `MacroIndicatorObservation` to the typed macro domain snapshot so provider observations can flow through the service and node output without reconstructing facts from scalar summaries or narrative LLM text.
- Updated the FRED macro client/provider path to preserve source observation timestamps and emit typed macro observations when a vendor observation has both a value and timestamp.
- Wired `MacroPersistenceService` and `PostgresMacroPersistenceRepository` through application persistence DI and the PostgreSQL workflow-output projection coordinator.
- Kept macro observation projection limited to explicit typed observations under `macro_analysis.macro_data.observations`; scalar macro snapshot fields are not converted into observations by inference.
- Added focused tests for macro projection success, deterministic projected record IDs, missing timestamp skip behavior, canonical registration, DI wiring, and fundamental-agent macro output fields.

Verification:

- `uv run ruff check domain/macro/models domain/workflow_outputs application/projections/workflow_outputs/projectors application/projections/workflow_outputs/bootstrap.py application/projections/workflow_outputs/di.py application/persistence/di.py integration/clients/macro/fred_macro_client.py integration/providers/macro/live_macro_provider.py intelligence/analysts/fundamental/fundamental_agent.py tests/unit/application/projections/test_macro_workflow_output_projector.py tests/unit/application/projections/test_workflow_output_projection_di.py tests/unit/application/projections/test_workflow_output_projection_bootstrap.py tests/unit/intelligence/analysts/fundamental/test_fundamental_agent.py --fix`
- `uv run ruff format domain/macro/models domain/workflow_outputs application/projections/workflow_outputs/projectors application/projections/workflow_outputs/bootstrap.py application/projections/workflow_outputs/di.py application/persistence/di.py integration/clients/macro/fred_macro_client.py integration/providers/macro/live_macro_provider.py intelligence/analysts/fundamental/fundamental_agent.py tests/unit/application/projections/test_macro_workflow_output_projector.py tests/unit/application/projections/test_workflow_output_projection_di.py tests/unit/application/projections/test_workflow_output_projection_bootstrap.py tests/unit/intelligence/analysts/fundamental/test_fundamental_agent.py`
- `uv run mypy domain/macro/models domain/workflow_outputs application/projections/workflow_outputs application/persistence/di.py integration/clients/macro/fred_macro_client.py integration/providers/macro/live_macro_provider.py intelligence/analysts/fundamental/fundamental_agent.py tests/unit/application/projections/test_macro_workflow_output_projector.py tests/unit/application/projections/test_workflow_output_projection_di.py tests/unit/application/projections/test_workflow_output_projection_bootstrap.py tests/unit/intelligence/analysts/fundamental/test_fundamental_agent.py --explicit-package-bases`
- `uv run pytest -q tests/unit/application/projections/test_macro_workflow_output_projector.py tests/unit/application/projections/test_workflow_output_projection_di.py tests/unit/application/projections/test_workflow_output_projection_bootstrap.py tests/unit/intelligence/analysts/fundamental/test_fundamental_agent.py tests/unit/integration/providers/macro/test_macro_providers.py tests/unit/integration/clients/macro/test_fred_macro_client.py`
- `uv run pytest -q tests/unit/application/projections`
- `uv run pytest -q tests/unit/application/persistence/macro tests/unit/core/database/test_macro_persistence_models.py tests/unit/core/storage/persistence/test_macro_persistence_contracts.py tests/unit/core/storage/persistence/test_macro_persistence_serializer.py tests/unit/core/storage/persistence/test_postgres_macro_persistence_repository.py tests/unit/integration/providers/macro/test_macro_providers.py tests/unit/integration/clients/macro/test_fred_macro_client.py`
- `uv run graphify update .`
- `git diff --check`

Results:

- Focused Ruff passed.
- Focused MyPy passed: `Success: no issues found in 24 source files`.
- Focused macro/projector/fundamental-agent tests passed: `16 passed`.
- Projection test suite passed: `53 passed`.
- Macro persistence/provider/client contract tests passed: `51 passed`.
- Graphify update completed successfully.
- `git diff --check` passed.

Notes:

- No live services were required for this step.
- Plain `pytest` is not available on the shell PATH in this environment, so verification used `uv run pytest`.
- Economic calendar events are projected only from explicit `economic_calendar_events` output entries. The current production fundamental agent does not synthesize those events, so none are fabricated from macro analysis text.
- Macro observation records are sourced from typed provider observations only; the projector does not derive observations from scalar macro fields, summaries, or LLM narrative content.

### Step 15 — Implement news and sentiment projectors

Completed on 2026-07-10.

- Added `NewsAnalysisWorkflowOutputProjector` and registered it against `polaris.news.analysis` schema version `1`.
- Projected eligible `news_agent` workflow evidence through `NewsPersistenceService` into:
  - `NewsArticleRecord`, only when the source article has canonical source identity, title, published timestamp, and `id` or `url`
  - `NewsAnalysisSnapshotRecord`, when the analysis output is not degraded
- Added `SentimentSnapshotWorkflowOutputProjector` and registered it against `polaris.sentiment.snapshot` schema version `1`.
- Projected eligible `sentiment_agent` workflow evidence through `SentimentPersistenceService` into:
  - `SentimentSnapshotRecord`
  - `SentimentSourceRecord`, only when a provider/source entry has source identity and timestamp
- Updated `news_agent` output boundaries with first-class `observed_at`, `news_source`, `symbol`, `query`, and `news_articles` fields so the projector does not mine canonical identity or timestamps from generic metadata.
- Updated `sentiment_agent` output boundaries with first-class `observed_at`, `sentiment_source`, `sentiment_universe`, and `symbol` fields.
- Wired `NewsPersistenceService`, `SentimentPersistenceService`, `PostgresNewsPersistenceRepository`, and `PostgresSentimentPersistenceRepository` through application persistence DI and the PostgreSQL workflow-output projection coordinator.
- Extended projection DI registry wiring for news and sentiment projector registrations.
- Added focused projector tests for success, deterministic eligibility behavior, snapshot-only/source-only edge cases, missing timestamp skips, and canonical registrations.
- Added output-boundary tests for news and sentiment agents' first-class projection fields.

Verification:

- `uv run ruff check <step-15-paths> --fix`
- `uv run ruff format <step-15-paths>`
- `uv run mypy <step-15-paths> --explicit-package-bases`
- `uv run pytest -q tests/unit/application/projections/test_news_workflow_output_projector.py tests/unit/application/projections/test_sentiment_workflow_output_projector.py tests/unit/application/projections/test_workflow_output_projection_di.py tests/unit/application/projections/test_workflow_output_projection_bootstrap.py tests/unit/application/projections/test_macro_workflow_output_projector.py tests/unit/application/projections/test_market_workflow_output_projector.py tests/unit/intelligence/research/test_news_sentiment_output_contracts.py`
- `uv run pytest -q tests/unit/application/projections tests/unit/intelligence/research/test_news_sentiment_output_contracts.py`
- `uv run graphify update .`
- `git diff --check`

Results:

- Focused Ruff passed.
- Focused MyPy passed: `Success: no issues found in 12 source files`.
- Focused projector/DI/bootstrap/output-boundary tests passed: `23 passed`.
- Projection suite plus news/sentiment output-boundary tests passed: `64 passed`.
- Graphify update completed successfully.
- `git diff --check` passed.

Notes:

- No live services were required for this step.
- Repowise flagged the news persistence service, sentiment persistence service, news agent, and sentiment agent as churn-heavy/hotspot areas, so the change stayed surgical and used narrow projector/DI/test additions instead of broad service rewrites.
- Degraded news outputs do not create analysis snapshots; they can still persist eligible source article records. Sentiment source records are persisted only when source identity and timestamp are present; otherwise the sentiment snapshot is persisted without source records.

### Steps 16–17 — Coordinated strategy/recommendation projection stage

Completed on 2026-07-10.

Checked off as one coordinated implementation stage with Strategy Step 21.

- Added canonical workflow-output projectors for risk/agent signals and execution-risk decisions.
- Added strategy-specific projection for Bull, Bear, Sideways, and strategy synthesis outputs through first-class strategy persistence records instead of generic legacy signal payloads.
- Added downstream recommendation projection mappings while preserving distinct meanings:
  - strategy synthesis maps to `strategy_recommendation`;
  - portfolio allocation intent maps to `allocation_intent`;
  - trade packaging maps to `trade_proposal` and `TradeSetupRecord`;
  - execution-risk guard output remains an execution/risk decision signal, not a recommendation or realized outcome.
- Extended projector requests with the completed-run bundle so synthesis projection can relate sibling hypothesis node outputs without creating a parallel strategy projector coordinator or legacy payload merger.
- Added `AgentSignalPersistenceService` and wired agent-signal, strategy, and recommendation persistence services through application persistence DI and the PostgreSQL projection bootstrap.
- Kept projection as a completed-run workflow-output concern; runtime nodes and analytical services do not write curated strategy or recommendation records directly.

Verification:

- `uv run ruff check application/persistence/agent_signals application/persistence/di.py application/persistence/strategy/strategy_persistence_service.py application/projections/workflow_outputs core/storage/persistence/strategy core/storage/persistence/repositories/postgres_strategy_persistence_repository.py tests/unit/application/projections --fix`
- `uv run ruff format application/persistence/agent_signals application/persistence/di.py application/persistence/strategy/strategy_persistence_service.py application/projections/workflow_outputs core/storage/persistence/strategy core/storage/persistence/repositories/postgres_strategy_persistence_repository.py tests/unit/application/projections`
- `uv run pytest -q tests/unit/application/projections`
- `uv run mypy application/projections/workflow_outputs application/persistence/agent_signals application/persistence/di.py application/persistence/strategy/strategy_persistence_service.py core/storage/persistence/strategy core/storage/persistence/repositories/postgres_strategy_persistence_repository.py tests/unit/application/projections --explicit-package-bases`
- `timeout 90s uv run graphify update .`

Result:

- Focused Ruff passed after one automatic fix.
- Projection unit suite passed: `66 passed`.
- Focused MyPy passed: `Success: no issues found in 40 source files`.
- Graphify update completed successfully after Python changes.

Notes:

- No live external services were required for this coordinated stage.
- The implementation intentionally does not create `RecommendationOutcomeRecord` or `WatchlistItemRecord` without explicit realized outcome/watchlist evidence in workflow outputs.

### Step 18 — Refactor the portfolio analysis result

Completed on 2026-07-11.

- Expanded `PortfolioAnalysisResult` so the portfolio workflow output now carries the persistence-relevant portfolio facts needed by the upcoming projector:
  - canonical `PortfolioState`
  - normalized positions
  - exposure summary
  - risk metrics
  - allocation data
  - current equity
  - equity-history point records
  - peak equity and drawdown values
  - provider source, history period, and history timeframe
- Updated `PortfolioService` to request an explicit `1A` / `1D` portfolio-history window instead of relying on the provider default.
- Changed peak-equity calculation to derive from authoritative provider history plus current account equity. The service no longer reads the latest persisted portfolio state for that calculation.
- Kept direct portfolio persistence in place for now because Step 20 removes it only after the Step 19 projector is implemented and verified.
- Updated the portfolio provider protocol and live/backtest/simulated provider implementations to accept explicit portfolio-history `period` and `timeframe` parameters.
- Updated the Alpaca portfolio client to pass an explicit `GetPortfolioHistoryRequest` to Alpaca when fetching portfolio history.
- Extended focused tests to verify explicit history-window propagation, provider/client behavior, serialization of the expanded result, and provider-history-derived peak equity.

Verification:

- `uv run ruff check application/services/portfolio/portfolio_result.py application/services/portfolio/portfolio_service.py integration/clients/portfolio/alpaca_portfolio_client.py integration/providers/backtesting/portfolio/simulated_portfolio_provider.py integration/providers/portfolio/backtest_portfolio_provider.py integration/providers/portfolio/live_portfolio_provider.py integration/providers/portfolio/portfolio_provider.py tests/unit/application/services/portfolio/test_portfolio_service.py tests/unit/application/services/test_canonical_service_entrypoints.py tests/unit/integration/clients/portfolio/test_alpaca_portfolio_client.py tests/unit/integration/providers/portfolio/test_backtest_portfolio_provider.py --fix`
- `uv run ruff format application/services/portfolio/portfolio_result.py application/services/portfolio/portfolio_service.py integration/clients/portfolio/alpaca_portfolio_client.py integration/providers/backtesting/portfolio/simulated_portfolio_provider.py integration/providers/portfolio/backtest_portfolio_provider.py integration/providers/portfolio/live_portfolio_provider.py integration/providers/portfolio/portfolio_provider.py tests/unit/application/services/portfolio/test_portfolio_service.py tests/unit/application/services/test_canonical_service_entrypoints.py tests/unit/integration/clients/portfolio/test_alpaca_portfolio_client.py tests/unit/integration/providers/portfolio/test_backtest_portfolio_provider.py`
- `uv run mypy application/services/portfolio integration/providers/portfolio integration/providers/backtesting/portfolio integration/clients/portfolio tests/unit/application/services/portfolio/test_portfolio_service.py tests/unit/application/services/test_canonical_service_entrypoints.py tests/unit/integration/clients/portfolio/test_alpaca_portfolio_client.py tests/unit/integration/providers/portfolio/test_backtest_portfolio_provider.py --explicit-package-bases`
- `uv run pytest -q tests/unit/application/services/portfolio/test_portfolio_service.py tests/unit/application/services/test_canonical_service_entrypoints.py tests/unit/intelligence/portfolio/test_portfolio_state_builder.py tests/unit/integration/clients/portfolio/test_alpaca_portfolio_client.py tests/unit/integration/providers/portfolio/test_backtest_portfolio_provider.py tests/unit/integration/providers/backtesting/portfolio/test_simulated_portfolio_provider.py`
- `uv run graphify update .`
- `git diff --check`

Results:

- Focused Ruff passed.
- Focused MyPy passed: `Success: no issues found in 20 source files`.
- Focused portfolio service/provider/client tests passed: `18 passed`.
- Graphify update completed successfully.
- `git diff --check` passed.

Notes:

- No live services were required for this step.
- Repowise health/risk checks flagged `PortfolioService` as a churn-heavy hotspot, so the implementation stayed scoped to the Step 18 service-result and provider-history contract. The direct persistence removal remains deferred to Step 20 after the portfolio projector exists.

### Step 19 — Implement the portfolio projector

Completed on 2026-07-11.

- Added `PortfolioStateWorkflowOutputProjector` under `application/projections/workflow_outputs/projectors/`.
- Registered the portfolio projector against the canonical `polaris.portfolio.state` workflow-output contract and schema version `1`.
- Projected eligible `portfolio_state_builder` workflow evidence through `PortfolioPersistenceService` into:
  - canonical portfolio state snapshot/latest state
  - position history records
  - latest position records
  - equity history point records
  - exposure snapshot records
  - risk snapshot records
  - allocation snapshot records
- Updated `PortfolioStateDecision` so the portfolio-state builder emits the Step 18 expanded portfolio result fields at the runtime output boundary for explicit projector consumption.
- Wired `PortfolioPersistenceService`, `PostgresPortfolioExpansionPersistenceRepository`, and `PostgresPortfolioStateRepository` through workflow-output projection DI and the PostgreSQL projection bootstrap.
- Added focused tests for successful portfolio projection, deterministic projected IDs, missing canonical-state skip behavior, canonical projector registration, DI registry wiring, and portfolio-state-builder projection payload output.

Verification:

- `uv run ruff check application/projections/workflow_outputs/projectors/portfolio.py application/projections/workflow_outputs/projectors/__init__.py application/projections/workflow_outputs/di.py application/projections/workflow_outputs/bootstrap.py intelligence/portfolio/management/portfolio_state_policy.py tests/unit/application/projections/test_portfolio_workflow_output_projector.py tests/unit/application/projections/test_workflow_output_projection_di.py tests/unit/intelligence/portfolio/test_portfolio_state_builder.py --fix`
- `uv run ruff format application/projections/workflow_outputs/projectors/portfolio.py application/projections/workflow_outputs/projectors/__init__.py application/projections/workflow_outputs/di.py application/projections/workflow_outputs/bootstrap.py intelligence/portfolio/management/portfolio_state_policy.py tests/unit/application/projections/test_portfolio_workflow_output_projector.py tests/unit/application/projections/test_workflow_output_projection_di.py tests/unit/intelligence/portfolio/test_portfolio_state_builder.py`
- `uv run ruff check application/projections/workflow_outputs/projectors/portfolio.py application/projections/workflow_outputs/projectors/__init__.py application/projections/workflow_outputs/di.py application/projections/workflow_outputs/bootstrap.py intelligence/portfolio/management/portfolio_state_policy.py tests/unit/application/projections/test_portfolio_workflow_output_projector.py tests/unit/application/projections/test_workflow_output_projection_di.py tests/unit/intelligence/portfolio/test_portfolio_state_builder.py`
- `uv run ruff format --check application/projections/workflow_outputs/projectors/portfolio.py application/projections/workflow_outputs/projectors/__init__.py application/projections/workflow_outputs/di.py application/projections/workflow_outputs/bootstrap.py intelligence/portfolio/management/portfolio_state_policy.py tests/unit/application/projections/test_portfolio_workflow_output_projector.py tests/unit/application/projections/test_workflow_output_projection_di.py tests/unit/intelligence/portfolio/test_portfolio_state_builder.py`
- `uv run mypy application/projections/workflow_outputs/projectors/portfolio.py application/projections/workflow_outputs/projectors/__init__.py application/projections/workflow_outputs/di.py application/projections/workflow_outputs/bootstrap.py intelligence/portfolio/management/portfolio_state_policy.py tests/unit/application/projections/test_portfolio_workflow_output_projector.py tests/unit/application/projections/test_workflow_output_projection_di.py tests/unit/intelligence/portfolio/test_portfolio_state_builder.py --explicit-package-bases`
- `uv run pytest -q tests/unit/application/projections/test_portfolio_workflow_output_projector.py tests/unit/application/projections/test_workflow_output_projection_di.py tests/unit/intelligence/portfolio/test_portfolio_state_builder.py`
- `uv run pytest -q tests/unit/application/projections tests/unit/intelligence/portfolio/test_portfolio_state_builder.py`
- `uv run graphify update .`
- `git diff --check`

Results:

- Focused Ruff passed and the focused files are formatted.
- Focused MyPy passed: `Success: no issues found in 8 source files`.
- Focused portfolio projector/DI/builder tests passed: `6 passed`.
- Projection suite plus portfolio-state-builder tests passed: `71 passed`.
- Graphify update completed successfully.
- `git diff --check` passed.

Notes:

- No live services were required for this step.
- Direct `PortfolioService` persistence intentionally remains in place until Step 20, now that the portfolio projector exists and is verified.
- The projector uses deterministic projected IDs keyed by completed-run lineage, account identity, source timestamp, and stable portfolio sub-record keys so one workflow run produces one repeatable curated portfolio record set.

### Step 20 — Remove direct persistence from PortfolioService

Completed on 2026-07-11.

- Removed `PortfolioPersistenceService` from `PortfolioService` construction and request execution.
- Removed direct portfolio-state snapshot writes from `PortfolioService`.
- Removed direct equity-history expansion writes from `PortfolioService`.
- Confirmed the service no longer reads persisted portfolio state for peak-equity calculation; peak equity remains derived from current account equity plus authoritative provider portfolio history.
- Kept `PortfolioService` focused on provider orchestration, normalization, deterministic calculation, and returning the expanded typed `PortfolioAnalysisResult` for the `PortfolioStateBuilder` node output.
- Updated application service DI so `PortfolioService` depends only on the portfolio provider.
- Updated service tests and canonical service-entrypoint tests to instantiate and verify `PortfolioService` without persistence dependencies.
- Updated the architecture ownership ledger to reflect that portfolio state/equity history are now written through workflow-output projection, not directly by the service.

Verification:

- `uv run ruff check application/services/portfolio/portfolio_service.py application/services/di.py tests/unit/application/services/portfolio/test_portfolio_service.py tests/unit/application/services/test_canonical_service_entrypoints.py tests/unit/application/services/test_service_stabilization.py application/projections/workflow_outputs/projectors/portfolio.py application/projections/workflow_outputs/di.py application/projections/workflow_outputs/bootstrap.py --fix`
- `uv run ruff format application/services/portfolio/portfolio_service.py application/services/di.py tests/unit/application/services/portfolio/test_portfolio_service.py tests/unit/application/services/test_canonical_service_entrypoints.py tests/unit/application/services/test_service_stabilization.py application/projections/workflow_outputs/projectors/portfolio.py application/projections/workflow_outputs/di.py application/projections/workflow_outputs/bootstrap.py`
- `uv run mypy application/services/portfolio application/services/di.py tests/unit/application/services/portfolio/test_portfolio_service.py tests/unit/application/services/test_canonical_service_entrypoints.py tests/unit/application/services/test_service_stabilization.py --explicit-package-bases`
- `uv run pytest -q tests/unit/application/services/portfolio/test_portfolio_service.py tests/unit/application/services/test_canonical_service_entrypoints.py tests/unit/application/services/test_service_stabilization.py tests/unit/intelligence/portfolio/test_portfolio_state_builder.py tests/unit/application/projections/test_portfolio_workflow_output_projector.py tests/unit/application/projections/test_workflow_output_projection_di.py`
- `uv run graphify update .`
- `git diff --check`
- `rg "portfolio_persistence_service|PortfolioPersistenceService|persist_state_snapshot|persist_expansion_records|get_latest_state" application/services/portfolio application/services/di.py tests/unit/application/services --glob '!**/__pycache__/**'`

Results:

- Focused Ruff passed and the focused files are formatted.
- Focused MyPy passed: `Success: no issues found in 12 source files`.
- Focused service, portfolio-state-builder, and portfolio-projection tests passed: `35 passed`.
- Graphify update completed successfully.
- `git diff --check` passed.
- Source scan found no remaining direct portfolio persistence dependency or write/read call in `PortfolioService`, service DI, or application-service unit tests.

Notes:

- No live services were required for this step.
- Portfolio repositories and tables remain intact because they are now the curated portfolio projection targets used by `PortfolioStateWorkflowOutputProjector`.
- Completed-run archival remains separate from curated portfolio persistence: the workflow archive stores runtime evidence, and the projector converts eligible `portfolio_state_builder` evidence into deterministic portfolio records.

### Step 21 — Preserve report and backtest persistence boundaries

Completed on 2026-07-11.

- Added explicit workflow-output projection skip reasons for existing persistence-owner boundaries:
  - `REPORT_PERSISTENCE_BOUNDARY` for `polaris.report.*` contracts owned by `MorningReportPersistenceService`.
  - `BACKTEST_PERSISTENCE_BOUNDARY` for `polaris.backtest.*` contracts owned by `BacktestPersistenceService`.
- Updated the projection eligibility policy so report documents and backtest result bundles are skipped before registry/projector resolution, preventing accidental duplicate projection even if a future generic projector registration is added.
- Preserved the existing non-production execution-mode gate for `backtest` and `simulated` completed runs.
- Added eligibility-policy coverage proving report and backtest contracts are explicitly excluded with ownership-aware messages.
- Added projection-service duplicate-prevention coverage proving enabled workflow projection creates no projection jobs and invokes no report/backtest projectors for report/backtest boundary contracts.

Verification:

- `uv run ruff check application/projections/workflow_outputs/projection_eligibility.py tests/unit/application/projections/test_workflow_output_projection_eligibility.py tests/unit/application/projections/test_workflow_output_projection_service.py --fix`
- `uv run ruff format application/projections/workflow_outputs/projection_eligibility.py tests/unit/application/projections/test_workflow_output_projection_eligibility.py tests/unit/application/projections/test_workflow_output_projection_service.py`
- `uv run mypy application/projections/workflow_outputs/projection_eligibility.py tests/unit/application/projections/test_workflow_output_projection_eligibility.py tests/unit/application/projections/test_workflow_output_projection_service.py --explicit-package-bases`
- `uv run pytest -q tests/unit/application/projections/test_workflow_output_projection_eligibility.py tests/unit/application/projections/test_workflow_output_projection_service.py`
- `uv run pytest -q tests/unit/application/projections`
- `uv run graphify update .`
- `git diff --check`

Results:

- Focused Ruff passed and the focused files are formatted.
- Focused MyPy passed: `Success: no issues found in 3 source files`.
- Focused eligibility/service tests passed: `18 passed`.
- Full unit projection suite passed: `72 passed`.
- Graphify update completed successfully.
- `git diff --check` passed.

Notes:

- No live services were required for this step.
- This step intentionally did not add report or backtest projectors. Morning reports and backtest bundles remain owned by their dedicated persistence services, while workflow-output projection only handles eligible curated domain records.

### Step 22 — Add projection telemetry

Completed on 2026-07-11.

- Added `WorkflowOutputProjectionTelemetry` as a projection-specific telemetry boundary instead of reusing application-service or RAG telemetry emitters.
- Wired `WorkflowOutputProjectionService` to emit projection run lifecycle events:
  - `workflow_output_projection.completed_run_started`
  - `workflow_output_projection.completed_run_finished`
  - `workflow_output_projection.completed_run_failed`
  - `workflow_output_projection.completed_run_not_found`
- Wired projector lifecycle telemetry for eligible and skipped node outputs:
  - `workflow_output_projection.projector_started`
  - `workflow_output_projection.projector_completed`
  - `workflow_output_projection.projector_skipped`
  - `workflow_output_projection.projector_failed`
- Added projection metrics for run count, run latency, projector latency, persisted record counts by record type, retry count, unsupported contracts/schema versions, missing archives, and stale-job recovery count.
- Preserved workflow run trace context by creating child projector trace contexts for per-node projection work.
- Updated OpenTelemetry operation lifecycle mapping so workflow-output projection events resolve to valid completed-run and projector operation spans.
- Added focused unit coverage for successful telemetry emission, failed projection-run telemetry, unsupported-contract skip telemetry, missing archive telemetry, and stale-job recovery metrics.

Verification:

- `uv run ruff check application/projections/workflow_outputs/projection_telemetry.py application/projections/workflow_outputs/projection_service.py application/projections/workflow_outputs/__init__.py core/telemetry/tracing/operation_lifecycle.py tests/unit/application/projections/test_workflow_output_projection_service.py --fix`
- `uv run ruff format application/projections/workflow_outputs/projection_telemetry.py application/projections/workflow_outputs/projection_service.py application/projections/workflow_outputs/__init__.py core/telemetry/tracing/operation_lifecycle.py tests/unit/application/projections/test_workflow_output_projection_service.py`
- `uv run mypy application/projections/workflow_outputs/projection_telemetry.py application/projections/workflow_outputs/projection_service.py tests/unit/application/projections/test_workflow_output_projection_service.py --explicit-package-bases`
- `uv run mypy application/projections/workflow_outputs/__init__.py core/telemetry/tracing/operation_lifecycle.py --explicit-package-bases`
- `uv run pytest -q tests/unit/application/projections/test_workflow_output_projection_service.py tests/unit/application/projections/test_workflow_output_projection_di.py`
- `uv run pytest -q tests/unit/application/projections`
- `uv run graphify update .`
- `git diff --check`

Results:

- Focused Ruff passed and the focused files are formatted.
- Focused MyPy passed: `Success: no issues found in 3 source files`.
- Export and operation-lifecycle MyPy passed: `Success: no issues found in 2 source files`.
- Focused projection service/DI tests passed: `12 passed`.
- Full unit projection suite passed: `75 passed`.
- Graphify update completed successfully.
- `git diff --check` passed.

Notes:

- No live services were required for this step.
- Stale-job recovery telemetry is exposed on the projection telemetry boundary for upcoming operational commands; no stale-job recovery orchestration was added in this step.

### Step 23 — Add operational commands

Completed on 2026-07-11.

- Added `WorkflowOutputProjectionOperationsService` as the canonical application boundary for completed-run projection operations instead of putting repository orchestration directly in the CLI.
- Added typed operation requests/results for projection status, one-run projection, failed/stale retry, and missing-projection reconciliation.
- Added `polaris completed-runs` as a CLI alias for the existing completed-run command group while preserving the existing `polaris runs` command path.
- Added completed-run projection commands:
  - `polaris completed-runs projection-status`
  - `polaris completed-runs project`
  - `polaris completed-runs retry-projection`
  - `polaris completed-runs reconcile-projections`
- Kept CLI commands as thin async boundaries using `run_cli_async()` and Dishka request scopes through `application_request_scope()`.
- Supported dry-run behavior for one-run projection, retry, and reconciliation operations.
- Supported stale running projection-job recovery through the operations service and projection-job repository.
- Added unit coverage for projection operation orchestration and CLI command wiring.

Verification:

- `uv run ruff check application/projections/workflow_outputs/projection_operations.py application/projections/workflow_outputs/projection_models.py application/projections/workflow_outputs/__init__.py application/projections/workflow_outputs/di.py interfaces/cli/commands/completed_runs_command.py interfaces/cli/app.py tests/unit/application/projections/test_workflow_output_projection_operations.py tests/unit/application/projections/test_workflow_output_projection_models.py tests/unit/interfaces/cli/test_completed_runs_command.py`
- `POLARIS_POSTGRES_PASSWORD=dummy uv run mypy application/projections/workflow_outputs/projection_operations.py application/projections/workflow_outputs/projection_models.py application/projections/workflow_outputs/__init__.py application/projections/workflow_outputs/di.py interfaces/cli/commands/completed_runs_command.py interfaces/cli/app.py tests/unit/application/projections/test_workflow_output_projection_operations.py tests/unit/application/projections/test_workflow_output_projection_models.py tests/unit/interfaces/cli/test_completed_runs_command.py --explicit-package-bases`
- `POLARIS_POSTGRES_PASSWORD=dummy uv run pytest -q tests/unit/application/projections/test_workflow_output_projection_operations.py tests/unit/application/projections/test_workflow_output_projection_models.py tests/unit/application/projections/test_workflow_output_projection_di.py tests/unit/interfaces/cli/test_completed_runs_command.py tests/unit/interfaces/cli/test_cli.py`
- `uv run graphify update .`
- `git diff --check`

Results:

- Focused Ruff passed.
- Focused MyPy passed: `Success: no issues found in 9 source files`.
- Focused projection-operation and CLI tests passed: `26 passed`.
- Graphify update completed successfully with no code-graph topology changes detected.
- `git diff --check` passed.

Notes:

- No live external services were required for this step.
- The first focused pytest collection without a placeholder PostgreSQL password hit the expected settings import guard. The verification rerun used `POLARIS_POSTGRES_PASSWORD=dummy`; no live database connection was used and no secret was written to source.
- Reconciliation currently treats the repository's missing-run result set as the scanned candidate set, keeping the implementation surgical and avoiding new completed-run repository query surface in this step.

### Step 24 — Add unit coverage

Completed on 2026-07-11.

- Strengthened runtime-output contract tests to verify success, failure, and skipped factory outputs all serialize and deserialize canonical output contract identity and schema versions.
- Added explicit projection-service failure-isolation coverage proving one failing projector records a failed outcome/job while a later eligible node output still invokes its projector, succeeds, and reports its persisted record count.
- Expanded projection-operations coverage for dry-run retry behavior so dry runs inspect matching jobs without recovering stale jobs or invoking projection.
- Expanded reconciliation coverage for since/until window filtering and enqueue-enabled projection of missing completed runs.
- Added request validation coverage for invalid projection status, non-positive operation limits, and invalid reconciliation windows.
- Added CLI alias coverage proving the `completed-runs` command group exposes the projection operations alongside the existing `runs` path.
- Re-ran the broader existing Step 24-relevant suites covering registry registration/resolution, unsupported contracts and schema versions, eligibility policy decisions, deterministic fingerprints and record IDs, projection job state transitions, portfolio projector mapping, individual persistence-service calls, portfolio peak-equity calculation from provider history, and direct portfolio persistence removal.

Verification:

- `uv run ruff check tests/unit/core/runtime/state/test_runtime_node_output_contract.py tests/unit/application/projections/test_workflow_output_projection_service.py tests/unit/application/projections/test_workflow_output_projection_operations.py tests/unit/interfaces/cli/test_cli.py --fix`
- `uv run ruff format tests/unit/core/runtime/state/test_runtime_node_output_contract.py tests/unit/application/projections/test_workflow_output_projection_service.py tests/unit/application/projections/test_workflow_output_projection_operations.py tests/unit/interfaces/cli/test_cli.py`
- `POLARIS_POSTGRES_PASSWORD=dummy uv run mypy tests/unit/core/runtime/state/test_runtime_node_output_contract.py tests/unit/application/projections/test_workflow_output_projection_service.py tests/unit/application/projections/test_workflow_output_projection_operations.py tests/unit/interfaces/cli/test_cli.py --explicit-package-bases`
- `POLARIS_POSTGRES_PASSWORD=dummy uv run pytest -q tests/unit/core/runtime/state/test_runtime_node_output_contract.py tests/unit/core/storage/persistence/test_completed_run_serializer.py tests/unit/core/storage/persistence/test_workflow_output_projection_job_repository.py tests/unit/application/projections tests/unit/application/services/portfolio/test_portfolio_service.py tests/unit/application/services/test_canonical_service_entrypoints.py tests/unit/application/services/test_service_stabilization.py tests/unit/interfaces/cli/test_completed_runs_command.py tests/unit/interfaces/cli/test_cli.py`
- `uv run graphify update .`
- `git diff --check`

Results:

- Focused Ruff passed and the changed test files are formatted.
- Focused MyPy passed: `Success: no issues found in 4 source files`.
- Focused Step 24 unit coverage suite passed: `151 passed, 1 warning`.
- Graphify update completed successfully.
- `git diff --check` passed.

Notes:

- No live services were required for this step.
- The pytest warning is from the installed `websockets.legacy` package deprecation path and is unrelated to workflow-output projection behavior.
- The placeholder `POLARIS_POSTGRES_PASSWORD=dummy` was used only to satisfy settings import validation during unit-test collection; no database connection was opened and no secret was written to source.

### Step 25 — Add PostgreSQL integration coverage

Completed on 2026-07-11.

- Added live PostgreSQL integration coverage for the workflow-output projection boundary in `tests/integration/core/storage/persistence/test_postgres_workflow_output_projection_integration.py`.
- Covered normal completed-run projection from persisted workflow evidence into curated portfolio tables.
- Verified projection-job creation and terminal success status for successful eligible node outputs.
- Verified reprocessing the same completed run without `force_reproject` skips the already-succeeded projection job and does not duplicate portfolio state, position, exposure, risk, allocation, or equity-history rows.
- Verified backtest completed runs are treated as non-production workflow evidence and do not create projection jobs or populate live curated portfolio tables.
- Verified projector failure isolation: a failing downstream projector records a failed job/outcome while valid successful upstream portfolio output still persists curated records.
- Verified failed projection jobs can be retried through the operations service and transition to succeeded without creating extra jobs.
- Verified stale running jobs can be recovered to failed, retried, and completed successfully through the operations service.
- Reused the canonical PostgreSQL completed-run archive, projection-job repository, workflow-output projection service, projection operations service, and portfolio persistence repositories; no parallel test-only persistence path was introduced.

Verification:

- `uv run ruff check tests/integration/core/storage/persistence/test_postgres_workflow_output_projection_integration.py --fix`
- `uv run ruff format tests/integration/core/storage/persistence/test_postgres_workflow_output_projection_integration.py`
- `POLARIS_POSTGRES_PASSWORD=dummy uv run mypy tests/integration/core/storage/persistence/test_postgres_workflow_output_projection_integration.py --explicit-package-bases`
- `POLARIS_POSTGRES_PASSWORD=dummy timeout 30s uv run pytest -q tests/integration/core/storage/persistence/test_postgres_workflow_output_projection_integration.py`
- `POLARIS_POSTGRES_PASSWORD=dummy timeout 30s uv run pytest -q tests/database/test_migrations.py`
- `timeout 120s uv run graphify update .`
- `git diff --check`

Results:

- Focused Ruff passed and the new integration test file is formatted.
- Focused MyPy passed: `Success: no issues found in 1 source file`.
- PostgreSQL workflow-output projection integration test collection passed with expected live-test skips: `3 skipped` because `POLARIS_TEST_DATABASE_URL` is not set in the current Codex environment.
- Migration contract test collection passed with expected live-test skips: `7 skipped` because `POLARIS_TEST_DATABASE_URL` is not set in the current Codex environment.
- Graphify update completed successfully.
- `git diff --check` passed.

Notes:

- No secret or authenticated PostgreSQL connection string was written to source, tests, plans, or documentation.
- I confirmed `POLARIS_TEST_DATABASE_URL` is not available in this shell, and the configured application settings do not currently expose a usable PostgreSQL URL to derive the test URL without a password. To run this coverage live, export `POLARIS_TEST_DATABASE_URL` in the shell and rerun the two pytest commands above.
- The migration coverage for blank upgrade and ORM metadata matching remains in `tests/database/test_migrations.py`; Step 25 added projection-specific PostgreSQL coverage rather than duplicating pytest-alembic migration assertions.

### Step 26 — Verify RAG compatibility

Completed on 2026-07-11.

- Added focused RAG compatibility coverage in `tests/unit/application/rag/test_workflow_output_projection_rag_compatibility.py`.
- Verified newly projected portfolio risk and allocation records become typed structured curated RAG sources and satisfy the existing default eligibility rule as curated analytical summaries.
- Verified raw completed-run node-output/runtime records remain ineligible under the raw-runtime eligibility rule and cannot be passed to the curated RAG document builder as arbitrary payloads.
- Verified the portfolio RAG ingestion operation starts from eligible canonical PostgreSQL source records, resolves typed portfolio records through the curated source-loader registry, and passes `require_source_eligibility=True` into the ingestion boundary.
- Verified the projection package and projection-job repository do not import or call RAG services, Qdrant, Neo4j, embedding, or reranking concerns.
- Verified projection retry replays only the canonical projection operation and does not trigger RAG ingestion or projection side effects.

Verification:

- `uv run ruff check tests/unit/application/rag/test_workflow_output_projection_rag_compatibility.py --fix`
- `uv run ruff format tests/unit/application/rag/test_workflow_output_projection_rag_compatibility.py`
- `timeout 60s uv run mypy tests/unit/application/rag/test_workflow_output_projection_rag_compatibility.py --explicit-package-bases`
- `timeout 60s uv run pytest -q tests/unit/application/rag/test_workflow_output_projection_rag_compatibility.py`
- `timeout 60s uv run pytest -q tests/unit/application/rag/test_workflow_output_projection_rag_compatibility.py tests/unit/application/rag/test_curated_rag_structured_sources.py tests/unit/application/projections/test_workflow_output_projection_operations.py`
- `timeout 120s uv run graphify update .`
- `git diff --check`

Results:

- Focused Ruff passed and the new test file is formatted.
- Focused MyPy passed: `Success: no issues found in 1 source file`.
- New Step 26 unit tests passed: `6 passed`.
- Broader RAG/projection compatibility suite passed: `30 passed`.
- Graphify update completed successfully.
- `git diff --check` passed.

Notes:

- No live services were required for this step.
- This step intentionally added compatibility coverage only; no production RAG or projection code changes were needed.

### Step 27 — Run full quality gates

Completed on 2026-07-11.

- Ran Repowise health and blast-radius checks for the projection/runtime/persistence surface touched by the workflow-output projection plan.
- Ran the required quality gates in order and resolved projection-plan regressions discovered by the gates.
- Updated morning-report integration expectations for the canonical `strategy_evidence_builder` node and the structured-hypothesis strategy outputs now produced by the workflow.
- Updated the CLI runtime-scope failure test so the projection subscription boundary is isolated from the scope-closing assertion.
- Documented the new projection telemetry/logging boundary in the observability architecture allowlist.
- Updated migration contract tests after the migration squash so they validate the upgraded schema as a black-box final state instead of referencing removed historical revision IDs.
- Fixed `PostgresPortfolioStateRepository` latest-state upserts to use actual database column keys for renamed ORM attributes, preventing invalid `cash_ratio` and `risk_signals` insert/update columns while preserving the typed domain attribute names.

Verification:

- `uv run ruff check . --fix`
- `uv run ruff format .`
- `uv run mypy . --explicit-package-bases`
- `POLARIS_POSTGRES_PASSWORD=dummy uv run pytest -q`
- `source .env; POLARIS_TEST_DATABASE_URL=<derived from POLARIS_DATABASE_URL> uv run pytest -q tests/database/test_migrations.py`
- `source .env; POLARIS_TEST_DATABASE_URL=<derived from POLARIS_DATABASE_URL> uv run pytest -q tests/integration/core/storage/persistence/test_postgres_workflow_output_projection_integration.py`
- `uv run graphify update .`
- `git diff --check`

Results:

- Ruff check passed: `All checks passed!`.
- Ruff format passed; final run reported `1221 files left unchanged`.
- MyPy passed: `Success: no issues found in 1218 source files`.
- Full pytest passed: `2102 passed, 22 skipped, 5 warnings`.
- Live PostgreSQL migration tests passed: `7 passed, 8 warnings`.
- Live PostgreSQL workflow-output projection integration tests passed: `3 passed`.
- Graphify update completed successfully: `17568 nodes, 83041 edges, 562 communities`.
- `git diff --check` passed.

Repowise notes:

- Projection service and repository surfaces remain feature-active/churn-aware, so follow-on work should stay surgical.
- `core/storage/persistence/repositories/postgres_portfolio_state_repository.py` reports high health with a small import-block duplication signal and no downstream blast-radius warnings.
- `tests/database/test_migrations.py` and `tests/integration/workflow/test_morning_report_real_nodes.py` remain churn-heavy test hotspots, but the Step 27 changes are test-contract updates required by the current architecture and migration squash.

Notes:

- PostgreSQL was required for the live migration and projection integration checks; no database password or authenticated connection string was written to source, tests, plans, or documentation.
- The placeholder `POLARIS_POSTGRES_PASSWORD=dummy` was used only for non-live unit/full-suite settings import validation. Live PostgreSQL tests derived their test URL from the local `.env` at command execution time without printing the secret.
- The full pytest warnings are from third-party deprecations/user warnings and are unrelated to the projection implementation.

### Step 28 — Document the canonical persistence architecture

Completed on 2026-07-11.

- Expanded `docs/platform_architecture_ownership_ledger.md` with a canonical workflow-output projection contract that distinguishes runtime node output, completed-run archive records, curated domain records, RAG documents, Qdrant vector projections, and Neo4j graph projections.
- Documented output contract and schema-version requirements, projector registration, projection eligibility, live/replay/simulated/backtest isolation, retry/reconciliation behavior, idempotency, lineage, and safe projectable-node onboarding.
- Replaced stale ownership-ledger architectural-gap language with current watch items that reflect the implemented workflow-output projection route and remaining audit concerns.
- Added `docs/postgres_persistence.md` guidance explaining how completed-run evidence becomes curated PostgreSQL records and why RAG documents, Qdrant, and Neo4j remain downstream projections.
- Updated `docs/workflow_output_curation.md` so the canonical data flow explicitly includes the completed-run archive before projector-driven curation.

Verification:

- `rg -n "not yet|Future vector/graph|PortfolioService currently reads|Peak-equity calculation still|persisted by the service" docs/platform_architecture_ownership_ledger.md docs/postgres_persistence.md docs/workflow_output_curation.md || true`
- `git diff --check`
- `git status --short`

Results:

- Stale architecture-gap references for the completed projection work were removed from the ownership ledger and PostgreSQL persistence docs.
- `git diff --check` passed.
- No Python files were changed for this documentation-only step, so Ruff, MyPy, pytest, live services, and Graphify were not required.

Notes:

- Existing uncommitted production and test changes from prior projection-plan steps remain in the worktree and were not committed as part of this step.
