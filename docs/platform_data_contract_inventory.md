# Platform Data-Contract Inventory

## Status and scope

This document records the Step 5 inventory for the non-RAG platform as of
2026-06-27. It covers application services, intelligence agents, runtime state,
PostgreSQL persistence, report assembly, and backtesting.

This is an architecture and schema-change gate. No database migration or core
contract change is applied by this inventory. Changes under `core/`, destructive
schema changes, and canonical state convergence require the explicit approval
gate in Step 6 of the platform stabilization plan.

RAG contracts are excluded because they were reviewed by the completed RAG V2
stabilization plan.

## Post-stabilization resolution (2026-06-30)

This file preserves the Step 5 point-in-time inventory and should not be read as
the current implementation status for issues resolved later in the stabilization
plan. The following decisions supersede the corresponding historical findings
below:

- `RuntimeContext` schema version 2 is the sole canonical workflow execution
  snapshot. It owns workflow inputs, node outputs, artifacts, errors, trace
  context, and runtime execution metadata.
- The unused `RuntimeState` aggregate and its `MarketState`, runtime
  `PortfolioState`, `RiskState`, and `StrategyState` namespaces were removed.
  Workflow data now enters through `RuntimeContext.workflow_inputs` and flows
  between nodes through canonical node outputs.
- `domain.portfolio.models.PortfolioState` is the sole canonical portfolio
  business-state owner. It is serialized only at explicit runtime or persistence
  boundaries.
- PostgreSQL remains the system of record for durable business state and
  completed-run history. Runtime checkpoints remain the source for resume and
  replay; completed-run records are not replay checkpoints.

The classifications and boundary rules remain valid. Tables and findings below
that use present tense describe the 2026-06-27 audit baseline unless explicitly
marked as resolved. Current architecture and operations are documented in
[`platform_architecture_and_operations.md`](platform_architecture_and_operations.md).

## Canonical classification

Every platform value belongs to one of these classes:

| Class | Meaning | Persistence policy |
| --- | --- | --- |
| 1. Canonical state | Authoritative business state, decisions, signals, inputs required for audit, or historical facts that cannot be recreated reliably | Persist with stable typed ownership. Frequently queried dimensions use explicit relational columns; complete nested source data may use purpose-named JSON payloads at the persistence boundary. |
| 2. Reproducible derived data | Values deterministically recomputable from persisted canonical inputs and a versioned algorithm | Persistence is optional. Persist when required for audit, historical model comparison, or performance; otherwise recompute. Record algorithm/model version when persisted. |
| 3. Transient runtime or presentation data | Runtime routing, renderer-only formatting, CLI state, temporary aggregation, or human-readable projection | Do not treat as system-of-record. Serialize only at runtime, report, artifact, or transport boundaries. |
| 4. Telemetry or diagnostic data | Timing, retries, trace identity, provider status, failure details, fallback provenance, and operational counters | Persist through telemetry/runtime observability stores, not business-state tables unless the value is also a business decision. |

AI-adjacent outputs also carry canonical risk and authority metadata through
`domain.authority.RiskAuthorityContract`. That contract is orthogonal to the data
class above: content type does not determine authority by itself. The contract
records the `Baseline`, `Enhanced`, `Vigilant`, or `Prohibited / Outside
Authority` tier; authority of effect; canonical owner; source-of-truth category;
intended sink; and gate profile. The deterministic classifier escalates from
platform-known facts such as capital relevance, durable authority, external
visibility, governance impact, evidence sufficiency, and sink type. Model output
or model-provided metadata must not self-declare authority, production readiness,
governance approval, residual-risk acceptance, or a lower tier.

## Boundary and precision rules

1. Application services and intelligence components must exchange typed domain
   objects. A typed wrapper whose primary payload is `dict[str, Any]` does not
   satisfy the internal contract rule.
2. Dictionaries are valid at vendor, HTTP, runtime serialization, telemetry,
   checkpoint, report, artifact, and database JSON boundaries.
3. Stable, queryable business dimensions must not be hidden only in generic
   `metadata`, `raw`, `inputs`, `outputs`, or undifferentiated JSON blobs.
4. Purpose-named JSON/JSONB columns remain appropriate for complete nested source
   payloads when the nested members are not stable query dimensions.
5. Internal calculations preserve full precision. `round()` is permitted only in
   CLI, Markdown, PDF, web, and other human-presentation renderers.
6. Fallback values must be identified as fallback or unavailable state. They must
   not be persisted or reported as indistinguishable canonical observations.

## Application-service contract inventory

### Service execution envelope

`application.services.base.service_result.ServiceResult[T]` owns the common
service execution envelope. Request identity, success, error, attempt, timing,
completion, and diagnostic metadata are class 4 values. The generic `result: T`
slot is the boundary between the runner and the use-case-specific typed result.
`metadata` is not a substitute for fields on `T`.

| Service owner | Important result fields or field families | Required internal type | Class | Persistence owner and policy | Serialization boundary | Current gap |
| --- | --- | --- | --- | --- | --- | --- |
| Technical analysis | `symbol`, `technical_score`, snapshot, market context, micro/raw/calibrated regimes, trend, volatility, breadth | `TechnicalAnalysisResult` containing typed snapshot/context/trend/volatility/breadth/regime DTOs | 1 for observations and final calibrated state; 2 for reproducible indicators/scores | Market snapshot, indicator, context, breadth, and regime persistence models. Explicit columns for stable scores/regimes; purpose-named payloads for complete nested context | Provider input and PostgreSQL/runtime serialization only | `TechnicalAnalysisResult.result` is still `dict[str, Any]`; nested service output is untyped |
| Macro analysis | Raw macro observations, inflation/Fed/liquidity/yield-curve analyses, regime fields, market bias, macro score, summary | `MacroAnalysisResult` with typed observation and component-analysis objects | 1 for sourced observations and emitted regime snapshot; 2 for derived scores | Macro observation and macro regime snapshot models | Provider input, PostgreSQL, runtime/report serialization | Wrapper contains `dict[str, Any]`; component contracts are not canonical typed DTOs |
| Market events | `symbol`, pressure score, volatility forecast, regime bias, events, high-impact events/counts, risk projection | `MarketEventsResult` with typed event and projection records | 1 for normalized events and emitted event-state snapshot; 2 for forecasts/scores | Economic/event persistence plus agent/runtime signal history where applicable | Vendor input, PostgreSQL, runtime/report serialization | Result is a dictionary; event/projection ownership is not expressed by a canonical result object |
| News | Article identity/title/summary/source/URL/publication time, headline/relevance scores, raw source payload, analysis | `NewsResult` with immutable typed article and analysis records | 1 for normalized articles and analysis snapshots; 2 for relevance/headline scores | News article and news-analysis models | Vendor input, PostgreSQL, runtime/report serialization | `NewsResult.result` is `tuple[dict[str, Any], ...]`; `raw` is acceptable only on the boundary record |
| Portfolio analysis | Portfolio/position/equity state, capital and P&L, exposures, concentration, beta, heat, constraints, risk signals, regime, history | Canonical domain `PortfolioState` plus typed position, exposure, risk, equity, and history records | 1 | Portfolio state/history/latest, position, exposure, risk, allocation, and equity-history persistence | Broker input, PostgreSQL, runtime/report serialization | Result wrapper is a dictionary; two competing `PortfolioState` definitions exist; portfolio history has no accepted persistence owner |
| Sentiment snapshot | `symbol`, providers, features, sentiment components, composite sentiment, market regime/bias, confidence, directional signal, momentum, stability, divergence | `SentimentSnapshotResult` with typed provider/features/component/state records | 1 for normalized provider snapshot and emitted state; 2 for fused scores | Sentiment snapshot persistence | Vendor input, PostgreSQL, runtime/report serialization | Result and request context are dictionaries; persistence record/serializer still uses legacy domain names and drops canonical fields |

### Application-service findings

- The service runner and `ServiceResult[T]` envelope are structurally sound. The
  use-case payload classes are the problem: most merely wrap an untyped mapping.
- Service-owned typed DTOs should be introduced at the service boundary and then
  mapped to domain objects where the value has domain meaning.
- Stable nested fields should not be promoted to standalone columns solely because
  they exist. Promotion is required when they are canonical query dimensions,
  lineage keys, state-transition inputs, or audit-critical decisions.

## Intelligence and runtime contract inventory

| Owner | Important values | Required internal type | Class | Persistence policy | Serialization boundary | Current gap |
| --- | --- | --- | --- | --- | --- | --- |
| Fundamental, technical, news, and sentiment agents | Directional score, confidence, regime, signals, risks, recommendations, features, optional full LLM response | Immutable agent-family signal model with typed component collections | 1 for emitted signal/decision; 2 for derived features | Agent signal history, including complete reasoning and LLM text when emitted | `RuntimeNodeOutput.outputs`, PostgreSQL, telemetry/report projections | Agents commonly construct raw dictionaries first instead of serializing typed signals at the runtime boundary |
| Drawdown, exposure, and volatility risk agents | Risk score/severity, confidence, risk regime, breaches, mitigations, sizing guidance, features | Immutable risk signal hierarchy | 1 | Agent/risk signal history and portfolio risk snapshots | Runtime and persistence serialization | `integration.contracts.risk.RiskSignalContract` is mutable, weakly typed, and owned by the wrong layer |
| Risk signal builder and aggregator | Normalized risk packets, aggregate risk, constraints, recommendations | Typed risk packet and aggregate result | 1 | Risk signal and portfolio risk persistence | Runtime/persistence boundary | Generic mappings and lists conceal stable component types |
| Regime agents and strategy synthesis | Shared evidence context, perspective hypotheses, strategy weights, directional result, confidence, risks, recommendations, fallback provenance | Immutable `StrategyEvidenceContext`, `StrategyHypothesis`, `StrategyPerspectiveWeights`, and `StrategySynthesisDecision` records | 1; weighting calculations are class 2 but emitted decision is class 1 | Strategy hypothesis, synthesis decision, evaluation, and recommendation history | Runtime/persistence/report boundary | Legacy generic strategy signal contract has been removed; remaining boundary mappings should stay limited to runtime serialization and persistence projection |
| Portfolio manager | Allocation intent, target weights, rebalance intent, constraints, risk context | Typed allocation/portfolio intent | 1 | Allocation/recommendation/portfolio state history | Runtime/persistence boundary | Dictionary-first node output and overlap with competing portfolio state contracts |
| Trade packager | Trade package, sizing, order proposal, rationale, risk annotations | Immutable broker-agnostic trade package and proposal records | 1 | Recommendation/trade setup history | Runtime/persistence/external broker boundary | Internal dictionaries and internal rounding reduce contract safety and precision |
| Execution risk guard | Approval outcome, rejection/resize/defer reason, validated package, breaches | Typed execution-risk decision | 1 | Recommendation outcome/audit history | Runtime/persistence/execution boundary | Result serialization is valid at the node edge, but the internal package and decision path must remain typed |
| Attribution and adaptive weighting | Contributors, realized outcomes, strategy performance, selected weights | Typed attribution and weighting results | 1 for observed outcomes; 2 for derived attribution/weights | Attribution/outcome and strategy-weight history when used to alter future decisions | Runtime/persistence/report boundary | Generic feature mappings and internal rounding obscure reproducibility |
| Runtime state | Workflow/node state, portfolio/risk/strategy/market state, execution metadata | Immutable typed state and typed stable nested records | 1 for checkpoint/replay state; 3 for transient scheduling; 4 for execution diagnostics | Runtime persistence, checkpoints, completed-run archive | Runtime serializers are valid dictionary boundaries | Stable nested structures remain dictionaries; duplicate portfolio-state ownership is unresolved |

`RuntimeNodeOutput.outputs` and `execution_metadata` are legitimate serialization
boundaries. The node should nevertheless create and validate a typed signal or
decision before converting it to a mapping. `execution_metadata` should contain
operational provenance such as node identity, source, trace/fallback status, and
counts; business values belong in the typed output.

## Canonical state ownership conflicts

### Duplicate portfolio state

Two classes currently claim the `PortfolioState` name:

- `domain/portfolio/models/portfolio_state.py` is the richer immutable domain
  state and should be the canonical business owner.
- `core/runtime/state/portfolio_state.py` is an older runtime state with different
  names and untyped positions/orders/metadata.

These definitions must not continue evolving independently. The recommended
resolution is for runtime state to reference or serialize the canonical domain
portfolio state rather than maintain a second business schema. Because this
changes a core runtime contract, implementation requires the Step 6 approval
gate and migration/serialization compatibility analysis.

### Risk and strategy ownership

- Move or replace the mutable risk contract currently under
  `integration/contracts/risk/` with an immutable domain risk model. Integration
  must not own intelligence-domain output contracts.
- Keep strategy ownership on the structured-hypothesis contracts: shared evidence
  context, perspective hypotheses, pre-synthesis perspective weights, synthesis
  decisions, and persistence/projected records. Do not reintroduce a generic
  strategy signal result as a compatibility contract.

## Persistence coverage audit

### Coverage already represented

The current PostgreSQL model set has explicit relational coverage for the main
query dimensions of:

- technical snapshots, indicators, market context, market breadth, and regimes;
- macro observations and macro regime snapshots;
- news articles and news analysis;
- portfolio state, positions, exposure, risk, allocation, and equity state;
- agent signals and recommendations;
- runtime runs, node runs, events, completed runs, reports, artifacts, and
  telemetry;
- backtest runs, steps, fills, metrics, artifacts, scenarios, and expected
  outcomes.

Purpose-named JSON/JSONB payload columns in these models are valid persistence
boundaries when they retain complete nested source or signal data and are not the
only representation of stable query dimensions.

### Confirmed sentiment persistence drift

The physical sentiment schema already uses the approved canonical column names:

- `market_regime`
- `composite_sentiment`
- `providers_payload`
- `features_payload`
- `sentiment_payload`
- `fusion_components_payload`
- `raw_payload`
- explicit `market_bias`, `directional_signal`, `momentum`, `stability`, and
  `divergence`

`SentimentSnapshotRecord` and `SentimentPersistenceSerializer` still expose the
older concepts `sentiment_regime`, `composite_sentiment_score`, `component_scores`,
`inputs`, `outputs`, and generic `metadata`. They do not map all canonical service
fields to the existing ORM columns. This is contract drift and data loss, not a
missing-column problem.

Recommended correction after Step 6:

1. Rename the typed persistence record fields directly to the canonical physical
   and service vocabulary.
2. Add the missing canonical fields and purpose-named provider, feature,
   sentiment, fusion, and raw payload fields.
3. Update the serializer and round-trip tests to prove that no service field is
   silently dropped.
4. Remove legacy record/serializer names rather than add compatibility aliases.
5. Do not create a database migration unless ORM metadata comparison proves an
   actual DDL difference.

### Confirmed portfolio-history gap

`PortfolioAnalysisService` receives a historical equity series but currently
reduces it to a latest summary containing timestamp, equity, profit/loss,
profit/loss percentage, base value, timeframe, cashflow, and `has_history`.
Neither the reduced history state nor the source point series has an accepted
persistence owner. The structural model-coverage test currently reports a
missing `portfolio_history_payload`.

A payload column would close the test mechanically but would make an important
historical series opaque. The recommended schema candidate is a normalized
`portfolio_equity_history_points` table with:

- platform/account identifier;
- provider/source and timeframe;
- observation timestamp;
- equity;
- profit/loss and profit/loss percentage;
- base value;
- cashflow represented by typed child values or a purpose-named payload when its
  vendor shape is genuinely variable;
- source/run lineage and record timestamps.

Before implementation, Step 6 must decide whether the source series is canonical
state that the platform will retain. If only the latest summary is a platform
requirement, add explicit summary fields to the appropriate portfolio state
record instead. Do not add both a repeated blob and a normalized table without a
separate use case.

### Backtesting timestamps

Backtest metric and artifact records already have first-class timestamps
(`recorded_at` and `generated_at`). The earlier concern about deterministic epoch
fallbacks does not require another schema change in the current model. Adapters
must populate these canonical fields rather than hiding timestamps in metadata.

## Generic mapping and JSON audit

### Valid boundary mappings

The following mapping uses are architectural boundaries and should remain:

- vendor/client raw responses before provider normalization;
- runtime output, checkpoint, replay, event, and completed-run serialization;
- telemetry attributes and diagnostic metadata;
- PostgreSQL purpose-named JSON/JSONB payloads;
- report structured-content and artifact serialization;
- backtest node outputs and artifacts;
- CLI/web/external transport serialization.

### Mappings that require typed promotion

- all service `result` payloads listed above;
- sentiment request `previous_snapshot` and `risk_state` when consumed internally;
- intelligence signal component collections;
- risk packet and strategy perspective/weight structures;
- stable runtime market/risk/strategy/portfolio substructures;
- known backtest scenario parameters such as missing-data policy and benchmark
  return when they are part of the deterministic verification contract.

Truly extension-only backtest scenario parameters may remain in a typed
`Mapping[str, object]` boundary field. Known parameters must not remain hidden in
that extension bag after their semantics stabilize.

## Numeric precision audit

Internal `round()` calls were found in these non-presentation modules:

- `application/services/market_events/market_events_service.py`
- `application/services/news/headline_filtering.py`
- `application/services/news/news_service.py`
- `application/services/sentiment/sentiment_analysis.py`
- `application/services/sentiment/sentiment_fusion.py`
- `domain/portfolio/portfolio_decision_engine.py`
- fundamental and technical analyst agents;
- attribution and adaptive weighting;
- trade packaging and portfolio management;
- news and sentiment intelligence agents;
- risk signal building and volatility risk;
- strategy synthesis.

These calls violate the platform precision rule when they alter stored,
transmitted, scored, or persisted values. They must be removed from calculation
and contract construction paths. Human-readable strings should receive formatted
values from presentation helpers at report/CLI boundaries; internal numeric
fields must retain the original precision.

## Duplicate, legacy, fabricated, and fallback audit

- `has_breadth` is a compatibility alias for canonical `has_breadth_data` in the
  technical breadth context. Migrate direct consumers and remove the alias rather
  than retain two names.
- No `legacy_ad_line_trend_score` remains. `ad_line_trend_score` is the canonical
  breadth field and must remain the sole contract name.
- The sentiment persistence record names are legacy relative to the already
  canonicalized physical schema and must be replaced directly.
- Completed-run serializer fallbacks such as `unknown_workflow` and
  `unknown_execution` can fabricate replay/audit identity. Missing required
  identity should fail validation or be represented explicitly as unavailable;
  it must not become canonical history under a fabricated identifier.
- Technical, fundamental, and strategy fallbacks are valid resilience behavior
  only when typed status, reason, source, and confidence/provenance distinguish
  them from canonical model/provider results.
- `backtest_synthetic` is an intentional deterministic provider profile, not a
  fabricated live observation. Backtest records must retain scenario/profile
  lineage so synthetic state cannot be confused with live state.

## Explicit implementation and schema-change list

### A. Edge contract changes without a database migration

1. Replace dictionary payloads in technical, macro, market-events, news,
   portfolio, and sentiment result wrappers with immutable typed DTOs.
2. Type stable nested request context, beginning with sentiment previous-state and
   risk-state inputs.
3. Introduce or complete immutable domain signal families for analyst, research,
   risk, strategy, portfolio intent, trade package, execution decision,
   attribution, and weighting outputs.
4. Make agents construct typed results before runtime serialization.
5. Move risk output ownership from integration to the domain layer.
6. Attach `RiskAuthorityContract` metadata at AI-adjacent output boundaries
   that feed durable records, reports, recommendations, RAG answers, strategy
   synthesis, evaluation gates, or future tool responses.
7. Make strategy signal results immutable and remove `Any`/mutable collections.
8. Update the sentiment persistence record and serializer to the existing
   canonical schema and service vocabulary; add lossless service-to-record-to-ORM
   round-trip tests.
9. Promote stable deterministic backtest parameters to typed scenario/config
   fields.
10. Remove internal rounding and leave formatting to presentation boundaries.
11. Remove compatibility aliases and fabricated identity fallbacks after direct
    consumers and tests are migrated.

### B. Core contract candidates requiring Step 6 approval

1. Converge the duplicate domain and runtime `PortfolioState` definitions, with
   the domain model owning business state and runtime owning serialization and
   execution state only.
2. Replace stable dictionary members in runtime portfolio, market, risk, and
   strategy state with immutable typed records.
3. Validate checkpoint, replay, completed-run, event, and telemetry serializers
   against the converged state contracts.
4. Evaluate direct canonical ORM attribute names where Python attributes still
   preserve legacy vocabulary over canonical physical columns. Do not add another
   alias layer.

### C. Database schema candidate requiring Step 6 approval

1. Decide the canonical retention contract for portfolio equity history.
2. If the point series is canonical, add normalized
   `portfolio_equity_history_points` ORM and Alembic schema with lineage and
   timestamps.
3. If only the latest summary is canonical, add explicit summary fields to the
   owning portfolio state model instead.
4. Update migration state tests through `pytest-alembic`; do not assert migration
   filenames or counts.

No new sentiment, technical, macro, market-event, news, agent-signal,
recommendation, or backtest timestamp columns are currently justified by this
inventory. The sentiment issue is serializer drift against an existing schema.

### D. Verification contracts

1. Add service-result construction tests that reject missing or malformed typed
   component data.
2. Add service-to-domain-to-persistence round-trip tests for each canonical
   persisted output family.
3. Extend model-output coverage beyond column presence so serializers must prove
   every canonical field is mapped.
4. Add boundary tests proving mappings are introduced only by approved runtime,
   persistence, telemetry, report, artifact, and transport serializers.
5. Add precision tests using values that would visibly change under rounding.
6. Add fallback provenance tests and deterministic backtest expected-outcome
   tests.
7. Run ORM metadata divergence, migration, unit, integration, Ruff, MyPy, and
   Graphify verification after each approved implementation slice.

## Sequencing recommendation

After the Step 6 approval gate:

1. Fix edge-owned service DTOs and sentiment record/serializer drift first.
2. Add lossless round-trip and precision tests.
3. Converge intelligence signal contracts and node-boundary serialization.
4. Approve and perform the core runtime/domain portfolio-state convergence.
5. Decide and implement the portfolio-history schema, if canonical retention is
   approved.
6. Complete migration and live PostgreSQL verification.

This order protects the core while allowing direct edge conformance and prevents
a database migration from encoding contracts that are still ambiguous.
