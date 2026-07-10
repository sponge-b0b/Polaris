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
  | `portfolio_state_builder` | `PortfolioAnalysisResult` -> `PortfolioStateDecision` | Generic signal envelope with `features.portfolio_state`, `features.equity_state`, `features.positions_state`, `features.risk_features` | `polaris.portfolio.state` v1 | Portfolio records via `PortfolioPersistenceService` | `PortfolioAnalysisResult` currently omits equity-history points and provider/source timeframe from the returned typed result; `PortfolioService` still reads/writes portfolio persistence directly for peak-equity/history. | Projectable after Steps 18-20 refactor the service result and remove direct service persistence. |
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
