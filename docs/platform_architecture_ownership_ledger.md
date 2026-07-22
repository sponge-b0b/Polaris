# Platform Architecture Ownership Ledger

## Purpose

This ledger defines the canonical owner, producer, runtime carrier, persistence
writer, and projection policy for Polaris platform data and responsibilities. It is
the review gate for detecting duplicate sources of truth, duplicate writers,
obsolete responsibilities, and hidden persistence paths.

The ledger is normative. Existing code that conflicts with it is an
architectural gap; current behavior does not become canonical merely because it
is implemented or tested. Strategy ownership follows
`docs/decisions/adr-007-structured-strategy-hypotheses.md`.

## Core ownership rules

1. Every durable business concept has exactly one authoritative typed model.
2. Every durable record type has exactly one canonical write boundary.
3. A producer owns the meaning of a result; a persistence service owns writing
   that result. Those are different responsibilities.
4. Analytical application services return typed results. They do not persist
   workflow-derived results unless persistence is the explicit use case.
5. Runtime evidence, canonical domain records, derived projections, telemetry,
   and presentation artifacts are different storage classes.
6. `RuntimeContext` is the canonical workflow execution snapshot. It is not a
   parallel business-domain aggregate.
7. PostgreSQL is the durable system of record. Qdrant and Neo4j are rebuildable
   projections.
8. Completed runs archive execution broadly. Workflow-output projectors curate
   eligible domain records deliberately.
9. Stable business fields must not exist only in generic `metadata`.
10. Replay, retry, resume, and reprojection must not create duplicate canonical
    records.

## Storage classes

| Class | Owner | Purpose | May contain |
| --- | --- | --- | --- |
| Runtime execution evidence | Runtime | Replay, resume, inspection, and execution audit | Workflow inputs, node outputs, checkpoints, events, artifacts, errors |
| Canonical domain records | Domain and application persistence boundaries | Durable business history and exact queries | Market facts, portfolio state, signals, risk, recommendations, reports |
| Derived projections | Projection subsystems | Search, relationship traversal, and optimized views | RAG documents, chunks, embeddings, vectors, graph relationships |
| Telemetry and diagnostics | Telemetry subsystem | Operational observability | Logs, metrics, traces, timings, retries, failures |
| Presentation artifacts | Interface/report boundaries | Human consumption and export | Console, Markdown, HTML, PDF, JSON exports |

A record must not move between these classes implicitly. Each transition requires
a typed, attributable, deterministic boundary.

## Canonical platform responsibility ownership

| Responsibility | Canonical owner | Entry point or carrier | Durable owner | Prohibited alternatives |
| --- | --- | --- | --- | --- |
| Workflow application API | `WorkflowFacade` | CLI, future API, scheduler, and MCP request scopes | Runtime/completed-run persistence as configured | Interfaces invoking `RuntimeEngine` directly or constructing parallel runtimes |
| Runtime composition | `WorkflowBootstrap` and Dishka providers | Application and request scopes | None; composition is not business state | Interface-owned containers, service locators, duplicate `EventBus` or control instances |
| Workflow execution | `RuntimeEngine` | `WorkflowGraphDefinition` and `RuntimeNode` | Runtime persistence and completed-run archive | Separate live, simulated, backtest, or MCP runtimes |
| Workflow execution snapshot | `RuntimeContext` | Workflow inputs and serialized node outputs | Checkpoints and completed-run PostgreSQL records | A second market/portfolio/risk/strategy runtime-state aggregate |
| Pause, resume, and cancel | `WorkflowControlManager` | `WorkflowFacade` control APIs | Runtime events and operational audit when configured | Direct context mutation or interface-owned control loops |
| Runtime notifications | `EventBus` and typed `RuntimeEvent` | Runtime publishers/subscribers | Runtime event and telemetry sinks | Ad hoc notification buses or telemetry-owned runtime events |
| Policy decisions | `PolicyEngine` | Canonical runtime/facade path | Runtime/audit evidence | Interface or node bypasses |
| Governance decisions | `GovernanceEngine` | Canonical runtime/facade path | Runtime/audit evidence | Local allow/deny logic that bypasses governance |
| AI risk tier and authority metadata | `domain.authority.RiskAuthorityContract` with `RiskAuthorityClassifier` | Platform-known classification input at the producing boundary | Persisted only as metadata on the owning runtime evidence, canonical record, report, RAG answer, recommendation, evaluation gate, or future tool response | Model-generated claims declaring authority, approval, production readiness, residual-risk acceptance, or lower risk |
| Trace identity | Polaris `TraceContext` and observability boundary | Runtime context, events, async tasks, providers, datastores | Telemetry traces as configured | Vendor tracing objects as internal platform contracts |
| External access | Client → provider → application service | Typed provider protocols and service requests/results | Curated records only after explicit projection | Agents calling vendor SDKs or application services containing transport code |
| Dependency lifecycle | Dishka | Application and request scopes | None | Hidden globals, manual request-scoped construction, or unclosed resources |

## Runtime evidence ownership

| Concept | Authoritative producer/model | Canonical persistence writer/store | Replay role | Curation/RAG policy | Prohibited writers |
| --- | --- | --- | --- | --- | --- |
| Workflow inputs | Invocation boundary validated into typed request contracts; serialized in `RuntimeContext.workflow_inputs` | Checkpoint and completed-run serializers | Checkpoint input for resume/replay | Not automatically curated or embedded | Nodes rewriting invocation inputs; domain tables storing the entire input bag |
| Node outputs | Runtime node constructs a typed result and serializes it into `RuntimeNodeOutput` | Runtime persistence and completed-run archive | Execution evidence and downstream node context | Eligible outputs pass through registered workflow-output projectors | Nodes writing the same result directly to canonical tables |
| Checkpoints | Checkpoint manager | Runtime checkpoint store | Canonical resume/replay source | Never a direct RAG source | Completed-run archive or domain repositories acting as checkpoints |
| Completed runs | Runtime completion/archive boundary | `completed_workflow_runs`, `completed_workflow_node_outputs`, `completed_run_artifacts` | Inspection and historical execution evidence; not resume state | Source evidence for deterministic curated projection | Local-disk archives or domain services duplicating the full run |
| Runtime events | Runtime components through `EventBus` | `workflow_events` and telemetry sinks | Execution chronology | Not directly curated or embedded | Business repositories treating operational events as domain facts |
| Workflow state audit snapshots | Explicit workflow audit use case | `WorkflowStateSnapshotPersistenceService` and `workflow_state_snapshots` | Audit only unless a separate replay contract is approved | Not a direct RAG source | Automatic duplicate capture of every context/checkpoint without a distinct audit use case |
| Runtime artifacts | Owning node/runtime boundary | Completed-run artifacts or purpose-specific artifact storage | Supporting replay/audit evidence | Curate only through a typed domain record | Treating generated files as the only system of record |

## Domain data ownership

The authoritative producer owns the semantic fact. The registered
workflow-output projector validates and converts the authoritative node result.
The application persistence service is the canonical database write boundary.

| Domain concept | Authoritative typed owner | Authoritative workflow producer | Canonical PostgreSQL write boundary and records | RAG/graph policy | Status and prohibited alternatives |
| --- | --- | --- | --- | --- | --- |
| Market observations and technical context | Typed technical-analysis observation, snapshot, trend, volatility, breadth, and regime contracts | Technical analysis service result and Technical Agent for its emitted assessment | Workflow-output projector → `MarketPersistenceService` → market OHLCV, indicators, context, technical snapshot, and breadth records | Persist measurements in PostgreSQL; embed only curated explanatory technical assessments; graph lineage where useful | **Target contract.** Do not let service dictionaries, provider payloads, or strategy nodes create competing breadth/technical facts |
| Macro observations and regime | Typed macro observations, component analyses, and macro regime result | Macro service/agent authoritative output | Workflow-output projector → `MacroPersistenceService` → `macro_observations`, `macro_regime_snapshots`, `economic_calendar_events` | Embed curated summaries/regime reasoning; retain high-volume observations for SQL | **Target contract.** Provider/client responses are not canonical domain records |
| Market events | Typed normalized event and event-risk projection | Market Events service/authoritative node | Workflow-output projector → macro/market-event persistence records according to record type | Embed meaningful event analysis; graph event-to-symbol/recommendation relationships | **Target contract.** Do not persist duplicate event copies from downstream strategy nodes |
| News articles | Typed normalized article identity and source record | News provider normalization, exposed by News service/node | Workflow-output projector → `NewsPersistenceService` → `news_articles` | Article text may support RAG under content/security policy | **Target contract.** Vendor response dictionaries and report copies are not separate articles |
| News analysis | Typed news assessment referencing source articles | News Agent | Workflow-output projector → `NewsPersistenceService` → `news_analysis_snapshots` | Strong Qdrant candidate; Neo4j links analysis to articles, symbols, and decisions | **Target contract.** Report assembler must reference, not repersist, the analysis |
| Sentiment observations and assessment | Typed provider observations and canonical sentiment result | Sentiment service/agent authoritative output | Workflow-output projector → `SentimentPersistenceService` → `sentiment_sources`, `sentiment_snapshots` | Embed explanatory assessment when useful; numeric source rows remain SQL-first | **Target contract.** No legacy field vocabulary or duplicate sentiment snapshots from consumers |
| Portfolio state | `domain.portfolio.models.PortfolioState` and typed position/exposure/risk components | `PortfolioStateBuilder` | Workflow-output projector → `PortfolioPersistenceService` → portfolio state/history/latest and expansion records | Curated portfolio/risk narratives may be embedded; high-volume positions/equity points remain SQL-first; graph lineage is useful | **Implemented target.** `PortfolioService` computes and returns typed portfolio facts only; it must not write curated portfolio records directly |
| Portfolio equity history | Typed normalized equity-history point collection returned through the portfolio analysis result | Portfolio service normalizes provider history; `PortfolioStateBuilder` emits it as part of the authoritative portfolio result | Workflow-output projector → `PortfolioPersistenceService` → normalized equity-history records | PostgreSQL-only by default; summaries may contribute to a curated portfolio document | **Implemented target.** Equity history is returned through the portfolio result and projected by the workflow-output projector; do not store a duplicate opaque history blob |
| Peak equity | Derived field on the canonical portfolio result using current account equity and authoritative portfolio history | Portfolio analysis calculation | Persist only as part of the projected canonical portfolio state | May appear in curated portfolio/risk narrative; not a standalone embedding | **Implemented target.** Do not read previously persisted state solely to calculate peak equity when provider history is sufficient |
| Fundamental assessment | Immutable typed fundamental signal and supporting reasoning | Fundamental Agent | Workflow-output projector → agent signal/intelligence persistence | Strong Qdrant candidate; graph links to symbol, evidence, strategy, and recommendation | Do not persist raw LLM text as if it were the validated assessment; preserve raw response separately with lineage |
| Technical assessment | Immutable typed technical signal referencing technical source facts | Technical Agent | Workflow-output projector → agent signal/intelligence persistence | Strong Qdrant candidate; graph links to source technical records and decisions | Do not duplicate underlying market observations in the signal record |
| Sentiment assessment | Immutable typed sentiment signal referencing source sentiment records | Sentiment Agent | Workflow-output projector → agent signal/intelligence persistence | Qdrant and lineage graph when explanatory | Do not create a second canonical sentiment snapshot |
| Specialized risk assessment | Immutable risk model for drawdown, exposure, volatility, concentration, liquidity, or event risk | Corresponding specialized risk agent | Workflow-output projector → agent risk/portfolio risk persistence according to contract | Embed explanatory assessments; graph links to portfolio, inputs, and aggregate risk | Downstream aggregators reference these assessments instead of copying them as new specialized records |
| Aggregate portfolio risk | Immutable aggregate risk result | `RiskAggregatorAgent` | Workflow-output projector → canonical agent/portfolio risk record | Strong RAG and graph candidate | Specialized agents and strategy synthesis must not claim ownership of aggregate risk |
| Strategy evidence context | Immutable `StrategyEvidenceContext` built from canonical analytical node outputs | `StrategyEvidenceBuilder` | Runtime evidence only; no direct durable strategy record unless a future explicit audit use case is approved | Not directly RAG-eligible; persisted strategy records may reference its evidence fingerprint and selected evidence | Do not persist the shared evidence context as a second strategy source of truth or let downstream agents rebuild their own context |
| Pre-synthesis strategy perspective weights | Immutable `StrategyPerspectiveWeights` | `StrategyPerspectiveWeightingEngine` | Runtime evidence; projected only as lineage/evaluation attributes on persisted strategy records | Not a standalone RAG document; may appear inside curated synthesis decision context | Do not treat perspective weights as final strategy selection or compute them from Bull/Bear/Sideways outputs |
| Strategy perspective hypotheses | Immutable `StrategyHypothesis` for Bull, Bear, and Sideways perspectives | `BullAgent`, `BearAgent`, and `SidewaysAgent`, each consuming the same `StrategyEvidenceContext` | Workflow-output projector → `StrategyPersistenceService` → `StrategyHypothesisRecord` | RAG-eligible when persisted and attributable; graph links hypotheses to supporting, contradicting, and invalidating evidence | No agent-to-agent debate, voting, cross-reading, or generic strategy signal compatibility contract |
| Strategy synthesis decision | Immutable `StrategySynthesisDecision` and `StrategyHypothesisEvaluation` records | `StrategySynthesisAgent` as the only hypothesis-comparison authority | Workflow-output projector → `StrategyPersistenceService` → `StrategySynthesisDecisionRecord` and `StrategyHypothesisEvaluationRecord`; downstream recommendation mapping through `RecommendationPersistenceService` | Strong Qdrant candidate; graph links decision to evaluated/selected hypotheses, evidence, risk, portfolio, and recommendations | Reports, portfolio management, and RAG must not create parallel strategy decisions or compare hypotheses independently |
| Portfolio allocation/rebalance intent | Immutable portfolio intent | `PortfolioManagerAgent` | Workflow-output projector → portfolio allocation/recommendation persistence | RAG when rationale is useful; graph links to strategy and risk | Not an executable broker order; TradePackager must create a distinct proposal |
| Trade proposal | Immutable broker-neutral trade package | `TradePackager` | Workflow-output projector → recommendation/trade-setup records | Strong RAG and graph candidate | No broker execution or vendor-specific order ownership in this record |
| Execution decision | Immutable approve/reject/resize/defer/escalate decision | `ExecutionRiskGuard` | Workflow-output projector → recommendation outcome and audit records | RAG when rationale is useful; graph links to proposal, policy, governance, and risk | Interfaces and brokers may not bypass this decision boundary |
| Attribution | Immutable attribution and realized-outcome records | Attribution engine/approved outcome evaluator | Workflow-output projector or explicit outcome application use case → `AttributionPersistenceService` | RAG for explanatory conclusions; SQL for detailed metrics; graph links outcomes to decisions and inputs | Do not rewrite historical recommendations to add realized outcomes |
| Morning/financial report | Typed assembled report and full rendered body | Report assembler | Explicit report publication/persistence operation → `ReportPersistenceService` → report, section, artifact, version, and publication records | Strong Qdrant candidate; Neo4j links report to workflow and summarized records | Generated Markdown/PDF/HTML files are artifacts, not the sole source of truth |
| Backtest result and evidence | Typed backtest run, step, expectation, fill, metric, and artifact contracts | Backtest service using the canonical workflow runtime | `BacktestPersistenceService` → backtest tables | Embed conclusions and narratives selectively; keep detailed metrics/steps SQL-first | Backtesting may not introduce a separate runtime or compare only against prior Polaris outputs |

## Persistence and projection ownership

| Record family | Canonical writer | Source requirement | Idempotency requirement | Prohibited behavior |
| --- | --- | --- | --- | --- |
| Runtime run/node/event records | Runtime persistence subscribers | Typed runtime events and context | Workflow/execution/node identities | Application services writing runtime tables |
| Completed-run records | Completed-run archive boundary | Terminal `RuntimeContext` | One archive per execution; deterministic node/artifact identities | Local-disk fallback or using completed runs as checkpoints |
| Curated business records | Domain-specific application persistence service invoked by a registered projector or explicit persistence use case | Validated typed domain record with lineage | Deterministic record identity or approved natural key/upsert | Arbitrary nodes, renderers, or clients writing repositories directly |
| RAG eligibility | `RagEligibilityPersistenceService` | Existing canonical PostgreSQL record | Source-table/source-id eligibility identity | LLM-selected eligibility or eligibility based only on node name |
| RAG documents/chunks/jobs | Curated RAG ingestion/build operations | Eligible canonical PostgreSQL record | Deterministic source/document/chunk/job identities | Provider payloads, runtime dumps, or telemetry ingested directly |
| Qdrant vectors | RAG embedding/projection operations | PostgreSQL RAG chunks and embedding jobs | Deterministic point/source identities | Qdrant as system of record or vector writes from persistence services |
| Neo4j graph | RAG graph projection operations | Canonical PostgreSQL/RAG lineage | Deterministic node and edge identities | Neo4j as source of truth or application services issuing ad hoc Cypher |
| Telemetry records | Telemetry persistence sink/service | Typed telemetry events, metrics, and traces | Event/metric/trace identities | Telemetry tables used as business-domain history |
| Audit records | `AuditPersistenceService` | Successful or attempted governed persistence/action event | Append-only audit identity | Audit failures silently redefining the primary domain result unless policy requires fail-fast |
| Lineage links | `LineagePersistenceService` or owning atomic persistence operation | Existing typed source and target identities | Deterministic relationship identity | Generic metadata used instead of relational lineage |

## Workflow-output projection contract

Workflow-output projection is the canonical bridge from completed workflow
evidence to curated PostgreSQL domain records. It is not part of runtime
execution, not RAG ingestion, and not report rendering.

The canonical target flow for workflow-produced business facts is:

```text
Provider/client boundary data
    → typed application service result
    → typed intelligence/domain result
    → RuntimeNodeOutput serialization
    → completed RuntimeContext archive
    → registered workflow-output projector
    → typed curated domain record
    → domain application persistence service
    → PostgreSQL
    → optional RAG document, vector projection, and graph projection
```

### Persistence tiers

| Tier | What it is | Canonical owner/writer | Stored in | May feed | Must not be |
| --- | --- | --- | --- | --- | --- |
| Runtime node output | Serialized workflow evidence produced by a runtime node for downstream nodes, replay inspection, and audit | Producing `RuntimeNode` through `RuntimeNodeOutput` and runtime persistence subscribers | Runtime context, checkpoints, completed-run node-output rows | Completed-run archive and registered projectors | A direct domain-table writer, RAG document, or long-lived business aggregate |
| Completed-run archive | Immutable terminal execution evidence after a workflow finishes | Runtime completion/archive boundary | `completed_workflow_runs`, `completed_workflow_node_outputs`, `completed_run_artifacts` | Deterministic projection, inspection, diagnostics, and report history | A replay checkpoint, mutable business record, or query-optimized domain store |
| Curated domain record | Validated first-class business fact with typed fields, lineage, deterministic identity, and business timestamp | Registered projector invoking the owning domain application persistence service | Domain PostgreSQL tables | SQL queries, reports, attribution, RAG eligibility, graph/vector projections | A raw runtime dump, metadata-only pseudo-schema, or duplicate writer output |
| RAG document | Retrieval-ready representation derived from an eligible curated PostgreSQL record | RAG ingestion/build operations | PostgreSQL RAG document and chunk tables | Embedding jobs, reranking, answer citations, graph projection | Raw node output, telemetry, provider payload, or arbitrary LLM-selected content |
| Vector projection | Dense/sparse retrieval projection generated from RAG chunks and embedding jobs | RAG embedding/projection operations | Qdrant collections | Semantic retrieval and hybrid fusion | A system of record, canonical document store, or source for domain writes |
| Graph projection | Relationship projection generated from canonical lineage and RAG/domain records | RAG graph projection operations | Neo4j | Multi-hop retrieval, provenance traversal, relationship explanation | A system of record, ad hoc Cypher write path, or substitute for PostgreSQL lineage |

### Output contracts and schema versioning

AI-adjacent output boundaries use `domain.authority.RiskAuthorityContract` to
carry risk tier, authority effect, content type, canonical owner, source-of-truth
category, intended sink, and gate profile. This authority contract classifies the
output boundary; it does not make a raw node output projectable by itself and does
not replace the owning typed result contract. Model-provided text or metadata is
never an authority source for downgrading tier, declaring governance approval,
declaring production readiness, accepting residual risk, or converting advisory
content into a canonical decision.

A projectable runtime output must expose a stable `output_contract` and
`output_schema_version`. A projector supports explicit contract/version pairs
only. Unsupported versions are rejected, quarantined, or left archive-only; they
must not be coerced through best-effort dictionary parsing.

Schema evolution is deliberate:

- add or rename canonical fields through typed models and Alembic migrations;
- keep backward compatibility only when explicitly approved with a removal path;
- never hide stable business fields in generic `metadata` because a migration is
  inconvenient;
- preserve full numeric precision and full LLM/report text at persistence
  boundaries.

### Projector registration and eligibility

Each projector must be registered through the workflow-output projection catalog
and declare:

- supported output contract and schema version;
- authoritative source node or producer family;
- target record type and owning application persistence service;
- required fields and quality policy;
- deterministic identity and business timestamp strategy;
- workflow, execution, node, provider, model, source, and parent-record lineage;
- supported live, replay, simulated, and backtest modes;
- PostgreSQL, RAG-document, Qdrant, and Neo4j eligibility;
- retry, rejection, quarantine, reconciliation, and idempotency behavior.

Projection eligibility is a typed platform policy. A generic serializer, report
renderer, LLM, arbitrary node-name condition, or interface command may not decide
curation ownership.

### Live, simulated, replay, and backtest isolation

Execution mode is first-class lineage. Live operational records, replayed
records, simulated records, and deterministic backtest records must not become
indistinguishable in PostgreSQL, RAG documents, Qdrant, or Neo4j.

A projector must either:

1. explicitly support the incoming execution mode and persist the mode on the
   curated record or lineage; or
2. reject/quarantine the output as ineligible for that record family.

Backtest and simulated outputs may use the same runtime and service contracts as
live workflows, but their curated records and projections must remain filterable
so they do not pollute live operational history or customer-facing retrieval.

### Retry, reconciliation, idempotency, and lineage

Projection may run after workflow completion, during repair, or during explicit
reconciliation. Therefore every projector must be idempotent.

Required behavior:

- calculate deterministic record identities from stable workflow, node, source,
  domain, timestamp, and schema-version fields;
- use repository/application persistence upserts only at the canonical writer;
- record lineage from curated records back to workflow execution, node output,
  source provider/model, and parent domain records;
- treat missing required identity, timestamp, or lineage fields as quality
  failures rather than inventing fallbacks;
- allow safe reprocessing without duplicate domain records, duplicate RAG
  documents, duplicate vector points, or duplicate graph edges;
- expose rejections and failures through telemetry, audit, and operator-visible
  diagnostics.

### Why services and nodes do not persist directly

Analytical services and intelligence nodes produce typed facts. They do not own
workflow completion, retry timing, replay/reprojection semantics, cross-record
lineage, or duplicate-writer prevention.

Direct persistence from services or nodes is prohibited for workflow-derived
business facts because it:

- creates competing writers for the same durable concept;
- can persist partial results from failed or canceled workflows;
- bypasses execution-mode isolation and projection eligibility;
- couples analysis code to database schema evolution;
- makes retry/reconciliation non-deterministic;
- encourages metadata-only persistence instead of first-class fields;
- duplicates data that already exists in the completed-run archive.

Persistence is valid inside a service only when the service's explicit use case
is persistence, publication, ingestion, reconciliation, retention, audit, or
projection.

### Adding a projectable node safely

Before adding a new projectable node or promoting a new field to durable memory:

1. Define the authoritative typed output model and owner.
2. Set a stable `output_contract` and `output_schema_version` on the
   `RuntimeNodeOutput`.
3. Ensure the completed-run archive preserves the full source evidence.
4. Add or extend first-class PostgreSQL fields through SQLAlchemy and Alembic
   when the concept is canonical.
5. Register a projector with explicit required fields, identity, timestamp,
   lineage, quality policy, and execution-mode eligibility.
6. Route writes through the owning application persistence service; do not write
   repositories directly from the node.
7. Add unit tests for eligibility, rejection, idempotency, and lineage.
8. Add integration coverage when PostgreSQL records, RAG documents, Qdrant
   points, or Neo4j relationships are produced.
9. Declare RAG, vector, and graph eligibility only after the curated PostgreSQL
   record exists.
10. Update this ledger and the relevant architecture documentation.

## Approved direct-persistence use cases

Direct application persistence is valid only when persistence is the explicit
operation, including:

- ingestion of externally sourced canonical records;
- report publication and artifact registration;
- curated workflow-output projection;
- RAG document, embedding-job, and graph/vector projection processing;
- retention, audit, lineage, health, diagnostics, and export operations;
- explicit realized-outcome or reconciliation operations;
- runtime, checkpoint, completed-run, and telemetry persistence owned by their
  respective infrastructure boundaries.

Analytical services invoked as workflow dependencies are not direct-persistence
use cases merely because their result should eventually be durable.

## Change review checklist

Before changing a model, service, node, repository, schema, or projector, answer:

1. What durable concept is affected?
2. Which typed model is authoritative?
3. Which component authoritatively produces it?
4. Which runtime output carries it?
5. Which component is the single canonical writer?
6. Is the destination runtime evidence, a domain record, telemetry, an artifact,
   or a derived projection?
7. What is the deterministic identity and business timestamp?
8. How are workflow, node, provider, model, and source lineage preserved?
9. Does an existing responsibility become obsolete?
10. Does this create a duplicate source, writer, schema, payload, or projection?
11. Are stable fields being hidden in metadata?
12. Can retry, replay, resume, or reprojection create duplicates?
13. If AI-adjacent content is emitted, which `RiskAuthorityContract` tier,
    authority effect, owner, source-of-truth category, intended sink, and gate
    profile apply?

If ownership is ambiguous or two components claim to be authoritative, stop and
resolve the ledger before implementation.

## Known architectural watch items

The following watch items remain intentionally visible and must not be
normalized into new architectural patterns:

1. The workflow-output-to-curated-record projection layer is the required route
   for workflow-produced domain facts. New workflow-derived persistence must add
   a registered projector instead of writing from analytical services or nodes.
2. Several older application service result wrappers and intelligence results may
   still carry dictionary-first internal payloads rather than complete immutable
   typed contracts. Convert them directly when touched for feature work.
3. Some curated persistence paths predate this ledger and require a
   writer-by-writer audit before they can be declared compliant.
4. New stable business fields must become typed model fields and schema columns;
   generic `metadata` may only hold incidental boundary context.
5. Projection and RAG expansion must preserve execution-mode isolation so
   simulated, replay, and backtest records cannot contaminate live history.

These items should be resolved through direct conformance, not compatibility
wrappers or additional duplicate persistence paths.

## Ledger maintenance rule

Update this ledger whenever a change introduces or alters:

- a durable domain concept;
- an authoritative typed model;
- a workflow producer or node-output contract;
- a persistence writer, table, or repository;
- a checkpoint, replay, or completed-run responsibility;
- a curated-record projector;
- RAG eligibility, Qdrant projection, or Neo4j projection;
- a new metadata field that may have stable business meaning.

A feature is not architecturally complete until its ledger row has one owner,
one writer, explicit lineage, and a tested lifecycle.
