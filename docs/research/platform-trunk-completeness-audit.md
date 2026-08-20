# Polaris Trunk Completeness Audit

## Research status and authority

This document is **research input only**. It records a cross-cutting architecture audit of the Polaris trunk and identifies areas where delaying a platform-level decision could create expensive retrofit work after additional interfaces, schedulers, workers, users, integrations, or intelligence capabilities are built.

It does **not** establish active architecture, supersede accepted ADRs, modify existing Specs, satisfy or close any `$wayfinder` work, or authorize implementation. Any concern promoted from this audit into architectural work should be independently revalidated against current repository state through the normal `$wayfinder` workflow before decisions are recorded.

Audit date: **2026-08-19**

Repository snapshot used for the final audit pass:

```text
main: 07cd6db302130a6155e2d4cbd7543ce2329554d7
```

The audit also incorporates repository evidence inspected immediately before that revision where the relevant files were unchanged. Because Polaris is actively evolving, future planning should treat every finding as a hypothesis to revalidate rather than as permanent truth.

## Purpose

Polaris has reached the point where a large amount of deep platform architecture already exists: runtime execution, persistence, replay, typed contracts, RAG, observability, governance, evaluation, provider boundaries, and external transports are no longer isolated prototypes.

That maturity creates a different architectural risk from the one faced early in the project.

The important question is no longer primarily:

> What feature should Polaris build next?

The important question is:

> What foundational semantics must exist in the trunk before outward branches multiply, so that later API, UI, scheduler, worker, plugin, multi-user, and external-integration work does not force a platform-wide retrofit?

The audit therefore evaluates **trunk completeness**, not feature completeness.

Its objective is to find concerns analogous to the risk/authority/governance retrofit represented by Spec #66: concerns that may appear optional while the platform is mostly single-process and operator-driven, but become expensive to introduce after many consumers have already invented their own assumptions.

## Trunk versus branch

For this audit, a capability belongs in the **trunk** when its semantics should be shared by many future features and when discovering the correct design late would force broad reinterpretation of existing behavior, data, APIs, or ownership.

A capability is a **branch** when it can be added later through already-correct trunk boundaries without changing the meaning of the platform underneath it.

Examples:

```text
Trunk
  identity and authorization semantics
  time and historical-knowledge semantics
  trust-boundary semantics
  execution side-effect and retry semantics
  persistence authority
  provenance
  typed contracts
  governance authority

Branches
  FastAPI routes
  dashboard pages
  scheduler UI
  new intelligence agents
  new provider adapters
  report presentation formats
```

This distinction is deliberately about **retrofit risk**, not implementation size.

A small architectural contract can be more urgent than a large production subsystem if every future subsystem would otherwise encode its own incompatible version of that contract.

## Audit method

The primary test applied to each concern was:

> If Polaris discovers the correct design only after API, UI, scheduler, worker, plugin, or multi-user branches exist, how much of the platform would have to be reinterpreted or retrofitted?

Each concern was then assessed across four dimensions:

1. **Current implementation evidence** — whether working code already establishes meaningful behavior.
2. **Architectural explicitness** — whether the behavior exists as a platform-owned contract rather than only as a local convention.
3. **Cross-cutting fan-out** — how many future subsystems are likely to depend on the concern.
4. **Late-retrofit cost** — how disruptive it would be to correct after external surfaces and durable data proliferate.

The resulting labels are intentionally qualitative:

- **Strong / trunk-grade** — platform behavior is already explicit enough that future branches can consume it without redefining the concern.
- **Partial / hardening needed** — important foundations exist, but the concern is not yet fully expressed as one platform contract.
- **Missing platform contract** — local mechanisms may exist, but the cross-cutting semantic boundary is not yet established.
- **Critical retrofit risk** — deferment is likely to create broad architectural debt.

## Evidence scope

The audit reviewed representative current implementation and architecture across:

- `core/runtime/`
- `core/storage/persistence/`
- `core/security/`
- `core/plugins/`
- `domain/authority/`
- `application/health/`
- `application/projections/`
- `application/rag/` and current RAG architecture documentation
- `config/settings.py`
- MCP transport/authentication architecture
- current data-contract semantics
- current future-platform roadmap
- active architecture/spec work related to governance, model-provider neutrality, and data-provider neutrality

Representative evidence includes:

- `core/runtime/execution/runtime_node_executor.py`
- `core/runtime/execution/runtime_wave_executor.py`
- `core/runtime/control/workflow_control_manager.py`
- `core/runtime/state/runtime_context.py`
- `core/storage/persistence/idempotency/idempotency_persistence_models.py`
- `core/storage/persistence/lineage/lineage_persistence_models.py`
- `core/storage/persistence/retention/retention_persistence_models.py`
- `core/security/sensitive_data.py`
- `core/plugins/runtime/plugin_runtime_loader.py`
- `domain/authority/contracts.py`
- `application/health/platform_readiness.py`
- `application/projections/workflow_outputs/projection_service.py`
- `docs/current/domain-contracts-data-semantics-contract-semantics.md`
- `docs/current/platform-native-rag-pipeline.md`
- `docs/current/mcp-server-transport-boundary.md`
- `docs/proposed/platform-future-architecture.md`

The audit is not intended to prove exhaustive absence from every source file. Negative findings should therefore be read as:

> no canonical platform-level contract was identified in the inspected current architecture and representative implementation evidence.

That distinction matters because a local helper or isolated implementation can exist without closing the architectural concern.

# Executive conclusion

## Overall judgment

Polaris has a **strong trunk, but not yet a complete trunk**.

The audit found that most of the deepest work already performed is architecturally valuable and should be preserved. Runtime, persistence, typed data semantics, observability, replay, RAG source-of-truth design, and risk/authority modeling are substantive platform foundations rather than scaffolding.

The primary remaining risks are not missing intelligence features.

They are cross-cutting platform semantics that future interfaces and automation would otherwise be forced to invent independently.

The strongest audit finding is this cluster:

> **Who is acting, what are they allowed to do, what information was actually knowable at the time, what does Polaris trust, and what happens when an operation is repeated or concurrent?**

Those questions sit underneath almost every future outward branch.

The audit therefore identifies four concerns as the highest-priority new trunk-completion candidates:

1. **Identity, Access, and Ownership**
2. **Temporal Integrity, Data Freshness, and Historical Knowledge**
3. **Security and Trust Boundaries**
4. **Execution Idempotency, Concurrency, and Side-Effect Safety**

A fifth concern, **Execution Provenance, Configuration, and Version Identity**, is high priority but can follow the four critical items.

## Trunk completeness matrix

| Foundational concern | Current state | Retrofit risk | Audit judgment |
| --- | --- | --- | --- |
| Runtime and workflow execution | Strong | Low | Trunk-grade |
| Dependency composition | Strong | Low | Trunk-grade |
| PostgreSQL system of record | Strong | Medium | Trunk-grade; lifecycle work remains |
| Typed data/domain contracts | Strong | Medium | Trunk-grade |
| Risk / authority / governance | Strong but active retrofit | Critical | Finish current #66 lineage before outward expansion |
| Decision evidence / lineage | Strong | Medium | Harden execution-level provenance |
| Observability / tracing | Strong | Low–Medium | Trunk-grade |
| Backtesting / replay determinism | Strong | Medium | Trunk-grade locally |
| RAG grounding / injection controls | Strong locally | Medium | Good subsystem controls |
| Model-provider independence | Planned through #171 | High | Correct trunk work already queued |
| Data-provider independence | Planned through #176 | High | Correct trunk work already queued |
| **Identity & Access** | **Missing platform contract** | **Critical** | **Immediate Wayfinder candidate** |
| **Security & Trust Boundaries** | **Fragmented / partial** | **Critical** | **Immediate Wayfinder candidate** |
| **Temporal Integrity / known-at semantics** | **No canonical platform contract identified** | **Critical** | **Immediate Wayfinder candidate** |
| **Execution idempotency / concurrency / side-effect safety** | **Strong pieces, incomplete platform contract** | **Critical** | **Immediate Wayfinder candidate** |
| Execution provenance / configuration identity | Partial | High | Wayfinder after critical gaps |
| Schema/version evolution | Partial but deliberate | High | Targeted trunk audit |
| Secrets lifecycle | Partial | High | Likely subordinate to Security |
| Retention / deletion lifecycle | Advisory only by design | High | Needed before user-facing expansion |
| Backup / restore / disaster recovery | Future-only | High operationally | Secondary trunk work |
| Platform readiness / health | Partial and real | Medium–High | Consolidation/hardening later |
| Resource governance / quotas | Partial | Medium–High | Before scheduler/API scale |
| Failure / degradation semantics | Fairly strong | Medium | Audit rather than redesign |
| Multi-user / tenancy ownership | Implicit / undecided | Critical if multi-user | Resolve through Identity & Access |
| Scheduler/job platform | Not implemented | Low for now | Branch; can wait |

# Existing trunk foundations that are already strong

## Runtime and workflow execution

The runtime is one of Polaris's strongest platform foundations.

The implementation already separates:

```text
execution
control
lifecycle
policies
governance
checkpoints
replay
artifacts
events
telemetry
state
```

Node execution provides:

- explicit retry counts;
- optional retry backoff;
- node-level timeouts;
- lifecycle hooks;
- progress events;
- typed failure outputs;
- trace propagation.

Wave execution provides deterministic dependency-aware scheduling and cooperative cancellation boundaries. Workflow control supports pause, resume, cancel, running, completed, and failed state transitions.

These are not merely convenience helpers. They establish a reusable runtime platform that future transports can invoke rather than reimplement.

### Audit judgment

**Trunk-grade.**

The concern is not that Polaris lacks resilience primitives. The remaining question is whether the semantics of retries, concurrent mutation, and irreversible effects are strong enough for future mutating workloads. That narrower question appears later in this document.

## PostgreSQL system of record and rebuildable projections

Polaris's persistence architecture is also a strong trunk decision.

Current architecture treats PostgreSQL as authoritative while Qdrant and Neo4j are derived, rebuildable projections. The persistence layer contains explicit domains for completed runs, audit, decision evidence, evaluation, lineage, idempotency, retention, RAG, backtesting, projections, and related curated records.

This gives the platform a durable center and avoids the common failure mode where vector stores, report files, telemetry systems, or transport caches quietly become competing sources of truth.

The same architecture substantially simplifies future disaster recovery:

```text
restore PostgreSQL
    ↓
validate migration/schema state
    ↓
validate canonical records
    ↓
rebuild Qdrant
    ↓
rebuild Neo4j
    ↓
reconcile projection jobs
    ↓
verify platform readiness
```

### Audit judgment

**Trunk-grade**, with retention/deletion and backup/restore still incomplete as lifecycle/operations concerns.

## Typed domain and data-contract semantics

`docs/current/domain-contracts-data-semantics-contract-semantics.md` establishes unusually useful platform rules:

- canonical state is distinguished from reproducible derived data;
- transient runtime/presentation data is distinguished from system-of-record state;
- telemetry has its own persistence semantics;
- internal application/intelligence boundaries should use typed domain objects;
- dictionaries are permitted at genuine external/serialization/persistence boundaries;
- stable business dimensions should not disappear inside generic metadata;
- fallback/unavailable values must remain distinguishable from canonical observations;
- persisted reproducible data should retain algorithm/model version identity when needed for audit or comparison.

These rules substantially reduce the chance that outward features invent their own data semantics.

### Audit judgment

**Trunk-grade.**

## Risk, authority, governance, and decision evidence

Polaris no longer lacks a risk/authority architecture.

`domain.authority` already distinguishes:

- `RiskTier`;
- `AuthorityEffect`;
- `CanonicalOwner`;
- `SourceOfTruthCategory`;
- `IntendedSink`;
- `GateProfile`.

The platform, rather than model output, owns risk/authority classification.

Spec #66 then addresses the harder lifecycle issue: platform-owned invocation authority and Baseline provenance must remain distinct from claim-bearing Enhanced/Vigilant decision evidence, and authority/evidence must be reconstructed at the lifecycle boundary where authoritative inputs actually exist.

The audit treats #66 as **unfinished trunk**, not as a missing subsystem.

### Audit judgment

**Strong but still undergoing a critical trunk retrofit.** Finish that lineage before using outward expansion as the primary development direction.

## Observability and tracing

Polaris has substantial observability foundations:

- runtime events and progress events;
- trace context propagation;
- provider telemetry;
- persistence health and diagnostics;
- projection telemetry;
- AI/model observability;
- MCP sanitization rules;
- bounded approved telemetry dimensions in sensitive paths.

### Audit judgment

**Trunk-grade with future hardening.** No omitted observability architecture was identified.

## RAG grounding and injection controls

The platform-native RAG architecture already implements several security and provenance properties that should be preserved as exemplars for other future external-evidence paths:

- PostgreSQL remains canonical;
- Qdrant and Neo4j are derived projections;
- retrieved evidence is rehydrated toward canonical records;
- transient web fallback is not automatically promoted into canonical state;
- direct prompt-injection inspection occurs before model routing;
- retrieved contexts are treated as untrusted evidence;
- unsafe markup/instruction content is sanitized;
- structured model stages fail closed;
- injection resistance participates in evaluation.

### Audit judgment

**Strong subsystem-level control.** The remaining concern is making trust semantics cross-cutting rather than assuming localized RAG protections automatically define the whole-platform threat model.

# Critical finding 1: Identity, Access, and Ownership

## Finding

Polaris has authentication mechanisms, but the audit did not identify a canonical platform identity and authorization model.

For example, MCP Streamable HTTP correctly requires a bearer token and performs constant-time comparison. That proves a transport credential boundary exists.

It answers:

> Did this request present the configured MCP token?

It does not answer:

> Who is the actor?

or:

> Is this actor allowed to perform this action on this resource?

Those are separate architectural questions.

Similarly, workflow-control APIs already accept `requested_by`, but it is currently a free-form string rather than a durable typed principal.

Polaris's risk/authority architecture also does not replace authorization. `AuthorityEffect` describes what an output is permitted to affect after platform classification. Authorization asks whether a principal may perform an action against a resource under a particular policy/context.

The two must remain orthogonal.

## Why late discovery is expensive

If identity is added only at the HTTP layer later, interfaces risk becoming the owners of access semantics.

If multi-user or organizational use then appears, durable records may already lack ownership dimensions. The retrofit could reach:

```text
PostgreSQL rows
RAG filters
reports
recommendations
completed runs
governance reviews
audit records
MCP tools
future API resources
future UI queries
cache keys
scheduler jobs
```

The most expensive hidden question is therefore not login technology. It is **ownership topology**.

The platform needs an explicit answer to:

> Is one Polaris installation architecturally single-tenant, or must canonical resources support owner/tenant context?

Either answer can be correct.

Leaving the answer accidental is the risk.

## Candidate trunk contract

A future architecture investigation should consider a small provider-neutral contract such as:

```text
Principal
  ├── human
  ├── service
  ├── system/agent
  └── external client

Authorization Request
  ├── principal
  ├── action
  ├── resource
  └── context

          ↓

Authorization Policy / Service

          ↓

Authorization Decision
  ├── allow / deny
  ├── reason
  ├── policy/version
  └── audit identity
```

Authentication remains an adapter concern:

```text
local CLI identity
MCP bearer token
API key
OAuth/OIDC
session identity
service identity
        ↓
canonical Principal
```

## Questions for `$wayfinder`

A future Wayfinder map should independently decide at least:

1. What constitutes a canonical Polaris principal?
2. Are human, service, model/agent, and external-client actors distinct principal kinds?
3. Does every mutating authoritative operation require attributable principal identity?
4. Where does authentication terminate and canonical identity begin?
5. Where does authorization execute?
6. How do authorization decisions relate to governance decisions without collapsing the two?
7. Is a Polaris deployment single-tenant, owner-scoped, or organization/tenant-aware?
8. If tenancy exists, which records require tenant/owner identity at persistence time?
9. Are system/background actions represented by explicit service principals rather than magic strings?
10. What identity must survive into audit, governance, provenance, and control records?

## Audit recommendation

**Immediate Wayfinder candidate.**

The architecture contract should precede broad API/UI/admin/scheduler mutation work. Authentication implementation technology does not need to be selected immediately.

# Critical finding 2: Temporal Integrity, Data Freshness, and Historical Knowledge

## Finding

Polaris has many timestamps and strong deterministic backtesting behavior, but the audit did not identify one canonical platform semantic model for answering:

> When was this fact actually available to Polaris?

That question is stronger than:

> What timestamp does this row have?

`RuntimeContext` already distinguishes `created_at` and `simulation_time`. Historical/backtest flows deliberately use simulation time. RAG exposes temporal filters. Persistence records carry generated, observed, created, and other domain timestamps.

The problem is that these local timestamps do not yet appear to compose into one cross-cutting **known-at / as-of** contract.

## Financial example: economic release

Consider CPI:

```text
period represented               → effective/reference time
official agency publishes value  → publication/release time
provider makes value available   → provider-availability time
Polaris retrieves value          → observed time
Polaris persists normalized row  → ingestion/persistence time
workflow consumes row            → decision/as-of time
```

These timestamps are not interchangeable.

## Financial example: market event

Likewise:

```text
exchange/event time
provider timestamp
Polaris observed_at
persisted_at
decision_as_of
```

A historical system that uses the correct value but the wrong availability time can still exhibit look-ahead bias.

## Why this belongs in the trunk

This concern cuts through:

```text
vendor providers
→ normalization
→ canonical records
→ historical providers
→ backtesting
→ replay
→ RAG
→ strategy
→ risk
→ reports
→ decision evidence
→ audit
```

If the meaning of `timestamp`, `date`, `observed_at`, `generated_at`, and `created_at` is allowed to diverge independently across those branches, correcting historical truth later becomes difficult.

Retention already exposes the ambiguity indirectly: its candidate record intentionally allows its aging timestamp to represent different domain meanings such as generated, published, observed, or created time. That flexibility is useful for retention policy, but it demonstrates why those meanings should be explicit rather than inferred.

## Candidate trunk invariant

A future architecture investigation should consider whether Polaris needs a small shared temporal vocabulary such as:

```text
effective_at / event_at
published_at
source_at / provider_at
observed_at
known_at / available_at
ingested_at / persisted_at
decision_as_of
```

Not every record needs every field.

The key requirement is that every timestamp which affects historical truth has one unambiguous semantic role.

A particularly valuable historical invariant would be:

> **A historical/replay decision may consume only evidence whose canonical known/available time is less than or equal to the decision's as-of time.**

The exact vocabulary and enforcement boundary require Wayfinder analysis rather than adoption from this research document.

## Freshness is the complementary concern

Temporal integrity is also the right place to decide stale-data semantics.

Historical knowledge asks:

> Could Polaris know this yet?

Freshness asks:

> Is this observation still sufficiently current to support this decision?

Without a common contract, providers and application services may independently invent concepts such as stale, delayed, unavailable, old, cached, or fallback.

## Questions for `$wayfinder`

1. Which temporal concepts require platform-wide names?
2. Which data families need `known_at`/availability semantics rather than only event time?
3. Where is provider publication/availability metadata normalized?
4. Does `simulation_time` represent decision/as-of time or a broader simulated clock?
5. What invariant prevents historical providers from returning future-known evidence?
6. How are data revisions represented when a provider revises a previously published economic value?
7. How is stale-data policy expressed and surfaced to decision evidence?
8. Which timestamps are canonical business state versus ingestion/telemetry metadata?
9. What temporal evidence must be preserved for recommendations, reports, and governance review?
10. How should RAG temporal filtering distinguish source/event time from known-at time?

## Audit recommendation

**Immediate Wayfinder candidate.**

This is especially important because Polaris is a financial analysis platform: time semantics affect look-ahead bias, replay fidelity, stale-data decisions, evidence integrity, and auditability simultaneously.

# Critical finding 3: Security and Trust Boundaries

## Finding

Polaris already contains significant security controls, but they are localized rather than expressed as one platform trust model.

Examples of existing controls include:

- centralized sensitive-value redaction in `core/security/sensitive_data.py`;
- MCP bearer-token protection for remote transport;
- safe MCP sanitization and telemetry limits;
- RAG prompt-injection inspection;
- treating retrieved/web contexts as untrusted evidence;
- removal of executable/instructional content before model stages;
- fail-closed structured model operations;
- prompt-injection resistance as an evaluation concern.

Those are meaningful foundations.

The missing question is:

> What does Polaris trust, and where does trust change?

## Plugin example

The runtime plugin loader currently imports configured Python modules with `importlib.import_module()` and registers discovered `RuntimeNode` classes.

That can be completely correct if plugins are defined as **trusted first-party code**.

It would be insufficient if Polaris later presents plugins as arbitrary third-party extensions.

The plugin tree already reserves `sandbox` and `versioning` boundaries, but those areas are not yet substantive. That makes plugin trust a design decision that should be made before a plugin ecosystem is encouraged.

## Cross-cutting trust classes

Potential trust boundaries include:

```text
operator configuration
secrets
local CLI input
remote MCP requests
future HTTP requests
provider responses
market/news/web content
RAG retrieved evidence
LLM/model output
generated artifacts
plugin code
persisted database content
external URLs
telemetry and logs
```

A platform can apply different protections to each class. The important thing is that the classification is deliberate.

## Candidate trunk concerns

A future security architecture should likely decide:

- trusted versus untrusted input classes;
- where validation/sanitization occurs;
- which evidence can influence prompts;
- network egress ownership;
- secret access boundaries;
- code-execution boundaries;
- logging/telemetry data classification;
- safe error propagation;
- plugin trust model;
- transport authentication boundaries;
- relationship to the separate authorization architecture.

Security should **consume** canonical identity. It should not become a second identity system.

## Questions for `$wayfinder`

1. What are Polaris's canonical trust zones?
2. Which inputs are always untrusted regardless of source reputation?
3. Which components may perform network egress?
4. Which components may access secret material?
5. Which values are prohibited from logs, traces, events, or persistence metadata?
6. Are runtime plugins trusted repository/deployment code or untrusted extensions?
7. If plugins may be untrusted, is in-process Python import fundamentally incompatible with that goal?
8. What validation belongs at transport boundaries versus typed application boundaries?
9. How are external URLs, downloaded content, and provider payloads classified?
10. How are LLM outputs prevented from being interpreted as platform authority, code, configuration, or credentials?
11. Does local stdio imply a trusted parent-process boundary, and what does it not imply?
12. How does the security model intersect with governance without duplicating governance?

## Audit recommendation

**Immediate Wayfinder candidate.**

Do not frame this as “add security features.” The valuable work is defining the trust architecture so future security mechanisms have stable ownership.

# Critical finding 4: Execution Idempotency, Concurrency, and Side-Effect Safety

## Finding

Polaris already has strong local idempotency and concurrency mechanisms.

Persistence provides a typed deterministic `PersistenceIdempotencyKey` contract.

Workflow-output projection provides:

- source fingerprints;
- persistent projection jobs;
- already-succeeded detection;
- claimable job states;
- explicit durable job claiming.

The runtime provides retries and retry backoff.

The remaining gap is the relationship among those mechanisms when runtime nodes or application operations perform meaningful mutations or external effects.

## Retry hazard

Consider a future operation:

```text
1. node performs external or durable side effect
2. effect succeeds remotely
3. response/connection fails before Polaris records success
4. runtime sees failure
5. runtime retries
6. effect occurs twice
```

Today many Polaris nodes are analytical and this problem may be limited.

Future surfaces are more likely to introduce mutation:

```text
governance submissions
publication
RAG ingestion
projection rebuild operations
alerts and notifications
scheduler jobs
API writes
administrative actions
retention/deletion operations
external integrations
```

At that point, retry behavior becomes architectural rather than incidental.

## Process-local versus durable coordination

`WorkflowControlManager` explicitly describes itself as an in-memory cooperative workflow-control state manager and protects local state transitions with an `asyncio.Lock`.

That is appropriate for its current ownership.

It should not silently become the implied answer to distributed concurrency when multiple API workers or scheduler processes exist.

The platform eventually needs to know where:

```text
process-local coordination ends
and
durable cross-process coordination begins
```

## Candidate execution-effect contract

A future Wayfinder should investigate whether runtime/application operations need a small effect classification such as:

```text
pure/read-only
idempotent mutation
non-idempotent mutation
externally irreversible effect
```

and therefore rules such as:

```text
may retry automatically?
requires deterministic idempotency key?
requires DB transaction?
requires durable claim/lease?
requires optimistic concurrency/version check?
requires reconciliation after uncertain outcome?
requires explicit operator recovery?
```

The exact model should remain lean. The audit does not recommend building a distributed workflow engine or universal transaction manager without evidence.

## Questions for `$wayfinder`

1. Which runtime/application effects may be retried automatically?
2. How does a node declare or inherit effect semantics?
3. When must an idempotency key exist before mutation?
4. Which mutations require durable claim/lease semantics?
5. How are duplicate submissions from API/MCP/scheduler surfaces reconciled?
6. What happens after an uncertain external effect where Polaris cannot prove success or failure?
7. Where are optimistic concurrency/version checks required for authoritative records?
8. Which operations must never be executed concurrently for the same logical resource?
9. How do replay and resume avoid re-performing effects that were already committed?
10. Are external notifications/publications treated differently from internal database writes?

## Audit recommendation

**Immediate Wayfinder candidate.**

The best time to establish these semantics is before API and scheduler paths create multiple invocation sources for the same application operations.

# High-priority finding: Execution Provenance, Configuration, and Version Identity

## Finding

Polaris already has substantial lineage and versioning evidence, but the audit did not identify one canonical execution identity that can answer:

> Exactly what Polaris configuration and implementation produced this decision?

Current evidence already includes pieces such as:

- workflow name;
- execution ID;
- runtime ID;
- node name;
- trace context;
- runtime-context schema version;
- model/provider metadata in model paths;
- source fingerprints in projection paths;
- content hashes in RAG paths;
- source references and cross-record lineage links;
- algorithm/model-version expectations in the data-contract architecture.

Those are strong foundations.

The missing concern is their top-level composition into a reproducibility contract.

## Candidate provenance identity

A future design may need to preserve, where relevant:

```text
code/build revision
workflow definition identity/version
runtime context schema version
configuration/profile fingerprint
model capability allocation
concrete provider/model binding evidence
prompt/template identity
policy/governance version
algorithm version
data/provider source identity
```

The goal is not to dump every environment variable into every record.

The goal is to preserve the minimum durable identity necessary to distinguish:

> Replay the run under the configuration it originally used.

from:

> Replay the same historical evidence under today's configuration.

Those are distinct operations and should remain distinguishable.

## Audit recommendation

**High-priority Wayfinder after the four critical concerns.**

Temporal semantics and identity/security may influence what provenance must contain, so sequencing it afterward is sensible.

# Schema evolution and historical compatibility

## Finding

Schema evolution is not absent.

`RuntimeContext` explicitly carries a schema version and fails reconstruction when persisted context uses an unsupported schema. The failure instructs callers that historical local checkpoints must be regenerated and completed PostgreSQL runs must be migrated.

That is a healthy fail-fast posture.

What the audit did not identify is one cross-cutting policy governing the compatibility lifecycle of all durable/external contracts, including:

```text
runtime context
workflow outputs
events
decision evidence
RAG records
MCP schemas
future HTTP schemas
```

## Candidate policy questions

A focused audit or small Wayfinder should eventually decide:

- who owns each schema version;
- what compatibility windows are supported;
- which readers must accept prior versions;
- where migration occurs;
- how unsupported historical artifacts fail;
- when replay requires historical schema adapters;
- how external transports deprecate contracts.

## Audit recommendation

**Targeted trunk audit after execution provenance.**

Do not create a large generic schema framework unless the audit demonstrates real duplication.

# Retention, deletion, and data lifecycle

## Finding

Retention has not been accidentally forgotten. It is intentionally incomplete.

The current retention contracts explicitly describe lifecycle policy only. They do not archive, delete, mutate, or physically remove canonical PostgreSQL records. Archive markers and planning results are constrained to dry-run behavior.

That is a good safety posture while authority and user/ownership semantics are still evolving.

## Why it still becomes trunk work

Before Polaris accepts user-specific data, external mutation, or privacy-sensitive workflows, it will need explicit lifecycle semantics for:

```text
retain
archive
delete
audit/legal hold
projection deletion
projection rebuild
reference preservation
cascade behavior
authorization to delete
proof/audit of deletion
```

Deletion is especially dependent on Identity & Access: before deciding who may delete data, Polaris needs a canonical actor/ownership model.

## Audit recommendation

**High-priority secondary Wayfinder after Identity & Access.**

# Backup, restore, and disaster recovery

## Finding

The future architecture explicitly lists backup/restore, but the current audit did not identify an implemented backup/restore contract for PostgreSQL and related projection recovery.

This is a real gap, but its architectural retrofit risk is lower than Identity or Temporal Integrity because the current source-of-truth architecture already constrains the solution strongly.

A likely recovery shape is:

```text
restore PostgreSQL authority
    ↓
validate migrations/schema
    ↓
verify canonical record integrity
    ↓
rebuild derived vector projection
    ↓
rebuild derived graph projection
    ↓
reconcile durable jobs
    ↓
run readiness checks
```

## Questions for future work

- What recovery point objective and recovery time objective, if any, does Polaris target?
- Which local-development backup behavior belongs in the open-source repository?
- Which production backup mechanisms remain deployment-specific?
- How are projection jobs reconciled after restore?
- How is successful recovery verified?
- Which secrets/configuration must be restored separately from data?

## Audit recommendation

**Secondary trunk operations work.** Important before serious production deployment, but not ahead of the four critical semantic gaps.

# Platform readiness and health

## Finding

Readiness is stronger than initially expected.

`PlatformReadinessService` already defines typed non-RAG readiness checks and currently distinguishes categories such as PostgreSQL, telemetry exporter, provider, and runtime persistence. PostgreSQL readiness checks include connectivity, migration state, and metadata-table availability. Additional probes are injectable.

RAG has its own richer dependency/projection readiness.

Evaluation/readiness work is also tracked separately through the risk-tiered readiness lineage.

## Remaining concern

Future consolidation should preserve the distinction among different questions:

```text
Is the process alive?
Is infrastructure ready?
Is capability X operational?
Is capability X governance/evaluation-ready?
```

Those are not equivalent health checks.

## Audit recommendation

**Do not build another readiness subsystem now.** Revisit after current readiness/evaluation work lands and consolidate only if duplicated semantics are demonstrated.

# Secrets lifecycle

## Finding

Secrets handling is partial but not absent.

Polaris already uses typed environment/configuration settings, avoids exposing database passwords through repr in core DB settings, and centralizes sensitive-data redaction for keys, credentials, bearer tokens, passwords, private keys, and credential-bearing URLs.

What is not yet established is a platform abstraction for secret rotation, revocation, or external secret-manager integrations.

## Audit recommendation

Do **not** add Vault, cloud secret managers, or Kubernetes-secret abstractions speculatively.

Instead, the Security Wayfinder should preserve a narrow invariant such as:

> Application/runtime semantics consume secret values or secret references through composition and must not treat environment variables as a permanent architectural storage mechanism.

Specific secret stores can then remain deployment adapters.

# Resource governance and budgets

## Finding

Polaris already bounds many expensive resources locally:

- model concurrency;
- request token budgets;
- RAG stage token limits;
- MCP query/page/retrieval bounds;
- provider timeouts;
- runtime node timeouts;
- retry counts.

These are good foundations.

The future concern is aggregate budget ownership when one externally initiated request can trigger many model/provider operations or when several users/scheduler jobs compete for limited resources.

Potential future budget dimensions include:

```text
elapsed runtime
model tokens
provider calls
network calls
parallelism
queue depth
optional monetary cost
```

## Audit recommendation

**Before API/scheduler scale, but after the critical semantic gaps.** Avoid creating a universal quota platform before real multi-request competition exists.

# Failure and degradation semantics

## Finding

Polaris generally exposes rather than hides failure:

- node failures produce typed outputs;
- retries are observable;
- provider degradation is often explicit;
- RAG has rejected/failed/empty outcomes;
- readiness returns typed not-ready states;
- model fallback rejection is explicit;
- projection jobs record failed/skipped/succeeded outcomes.

The audit did not identify a need to redesign failure semantics from scratch.

## Audit recommendation

Perform a later cross-cutting audit for consistency of terms such as unavailable, degraded, stale, skipped, rejected, blocked, failed, and not-ready. Promote a shared abstraction only if inconsistency creates real consumer burden.

# Multi-user and tenancy implications

## Finding

No canonical `tenant_id`-style platform contract was identified during the audit.

This is not automatically a defect.

A self-hosted Polaris deployment may intentionally be single-tenant and operator-owned.

The risk is allowing that assumption to remain implicit until resource ownership is already embedded across API, persistence, RAG, audit, and governance surfaces.

## Audit recommendation

Resolve this as part of **Identity, Access, and Ownership**, not as a separate speculative multi-tenancy project.

A valid Wayfinder outcome could explicitly declare:

> Polaris installations are single-tenant; resource-level tenant isolation is outside platform scope.

That would be substantially better than accidental single-tenancy.

# Scheduler and job platform

## Finding

The future architecture describes scheduler/automation capabilities, but the scheduler itself is not currently a trunk-completeness blocker.

A scheduler can be added later **if** it invokes the same canonical application/runtime boundaries and inherits identity, temporal, trust, idempotency, governance, and provenance semantics from the trunk.

Without those semantics, the scheduler would become another place that invents them.

## Audit recommendation

**Treat scheduler as a branch for now.** Complete the underlying trunk contracts first.

# Architecture the audit explicitly does not recommend

The purpose of a trunk audit is not to justify building every possible platform abstraction.

Several tempting responses would increase complexity without closing demonstrated risk.

## Do not build a universal policy engine preemptively

Risk classification, governance, authorization, readiness, provider eligibility, release controls, and retention all contain policy-like decisions.

That does not prove they should be collapsed into one generic rules engine.

Continue to prefer narrowly typed owners until real duplication demonstrates a common abstraction.

## Do not build distributed infrastructure before the semantics require it

The execution-safety finding does not automatically require Redis, Kafka, Temporal, Celery, a distributed lock service, or a transaction coordinator.

First define effect/idempotency/concurrency semantics.

Then use the smallest mechanism that satisfies actual deployment needs.

## Do not equate authentication with identity architecture

Adding JWTs or OAuth to FastAPI would not by itself solve principal identity, resource ownership, service actors, or authorization policy.

The core contract should be technology-neutral.

## Do not equate more timestamps with temporal integrity

Adding `created_at` fields everywhere would make the problem worse if their meanings differ.

The missing work is semantic classification, not timestamp quantity.

## Do not turn provider abstraction into magical fallback

The provider-neutral model/data-source work should continue to prohibit silent substitution. Provider neutrality means bindings are operator/composition choices; it does not mean the platform can silently change source identity and preserve the same evidence semantics.

# Relationship to active and queued trunk work

## Spec #66 — Risk-tiered governance approval and contestability

The audit reinforces the importance of completing the current governance/authority/evidence lifecycle before broad outward expansion.

The same failure pattern appears throughout this audit: a local mechanism can exist while the true authority boundary remains ambiguous. Spec #66 is already correcting that class of problem for governed invocation and claim-bearing output evidence.

The new audit findings should not be implemented inside #66 or used to broaden its existing scope. They are separate future planning inputs.

## Spec #171 — Provider-neutral LLM capability aliases

Provider-neutral model capability naming is trunk work because application semantics should express required capability rather than deployment location or concrete model/provider identity.

That direction is consistent with this audit's broader principle:

> Stable trunk semantics should describe platform meaning; replaceable deployment choices belong at composition/integration boundaries.

## Spec #176 — Provider-neutral data-source selection and free-first operation

The same principle applies to market/news/macro/provider sources. Current #176 work correctly separates execution mode and capability requirements from concrete vendor binding while preserving source identity in telemetry and operator-visible configuration.

Temporal Integrity will eventually need to compose with this work because provider substitution cannot erase publication/availability/freshness semantics.

# Proposed trunk model

The audit suggests the following conceptual structure:

```text
                         POLARIS TRUNK

                    ┌──────────────────┐
                    │ Domain Semantics │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ Identity & Access│   ← missing platform contract
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ Security / Trust │   ← partial/localized
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ Temporal Truth   │   ← missing platform contract
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ Runtime / Effects│   ← runtime strong;
                    │ / Concurrency    │      effect semantics partial
                    └────────┬─────────┘
                             │
          ┌──────────────────┼───────────────────┐
          ▼                  ▼                   ▼
    Persistence         Observability       Governance
        strong              strong          active retrofit
          │                  │                   │
          └──────────────────┼───────────────────┘
                             ▼
                     Evidence / Lineage
                           strong
                             │
                    Provider Capabilities
                     model / data binding
                             │
                       Application
                         Services
                             │
                      Intelligence
                             │
                  Strategy / Portfolio / Risk
                             │
                   ───── branches ─────
                             │
                     CLI / MCP / API
                             │
                  Scheduler / Web UI / etc.
```

This is a research model, not adopted architecture. Its value is to illustrate why Identity, Trust, Time, and Effect semantics should be decided deeper than individual interface branches.

# Recommended trunk-completion sequence

Subject to independent `$wayfinder` validation, the audit recommends this ordering:

1. **Finish the active risk/governance trunk work represented by #66 and its review/remediation lineage.**
2. **Identity, Access & Ownership Wayfinder.**
3. **Temporal Integrity, Data Freshness & Historical Knowledge Wayfinder.**
4. **Security & Trust Boundary Wayfinder.**
5. **Execution Idempotency, Concurrency & Side-Effect Safety Wayfinder.**
6. **Execution Provenance, Configuration & Version Identity Wayfinder.**
7. **Schema Evolution / Historical Compatibility audit and, only if needed, Wayfinder.**
8. **Retention, Deletion & Data Lifecycle Wayfinder.**
9. **Backup, Restore & Projection-Recovery Wayfinder.**
10. **Readiness/resource-governance consolidation after current evaluation/readiness work and before external API/scheduler scale.**

The sequence is based on dependency direction rather than feature value.

For example:

- deletion authorization depends on identity;
- security consumes identity;
- provenance may need temporal/configuration semantics;
- scheduler safety depends on idempotency/concurrency;
- API mutation should consume authorization rather than define it;
- historical evaluation depends on known-at semantics.

# Candidate Wayfinder maps

The audit should not automatically create all of these maps. They are candidate planning entries to use sequentially after current trunk work allows it.

## Candidate A — Identity, Access, and Ownership

Destination:

> Establish a decision-complete platform identity and authorization architecture that works across CLI, MCP, future HTTP, scheduler/background work, governance, audit, and durable resources without coupling canonical principals to one authentication technology.

Key decisions:

- principal kinds;
- authentication-to-principal boundary;
- authorization ownership;
- resource/action model;
- service/system identity;
- single-tenant versus owner/tenant semantics;
- persistence/audit identity requirements;
- relationship to governance.

## Candidate B — Temporal Integrity and Historical Knowledge

Destination:

> Establish canonical temporal semantics for event/effective time, publication/source availability, Polaris observation/known-at time, persistence time, decision/as-of time, freshness, revisions, and historical consumption so replay/backtesting cannot silently consume future-known or stale evidence.

Key decisions:

- temporal vocabulary;
- known-at invariant;
- provider normalization ownership;
- revision handling;
- freshness policy;
- RAG/backtest/replay integration;
- evidence persistence requirements.

## Candidate C — Security and Trust Boundaries

Destination:

> Establish a cross-cutting trust model that classifies external inputs, code, models, configuration, secrets, transports, provider data, web/RAG evidence, logging, and plugin execution, while consuming rather than duplicating canonical identity/authorization.

Key decisions:

- trust zones;
- input validation/sanitization ownership;
- egress ownership;
- secret access;
- plugin trust model;
- code execution;
- telemetry/logging restrictions;
- transport trust assumptions.

## Candidate D — Execution Idempotency, Concurrency, and Side Effects

Destination:

> Establish platform semantics for retries, idempotency, durable claims, concurrent mutation, irreversible effects, uncertain outcomes, replay/resume, and cross-process coordination so future API/scheduler/worker invocation cannot duplicate or race authoritative side effects.

Key decisions:

- effect classes;
- retry eligibility;
- idempotency-key requirements;
- transaction/claim ownership;
- optimistic concurrency;
- external-effect reconciliation;
- replay/resume behavior;
- process-local versus durable coordination.

## Candidate E — Execution Provenance and Configuration Identity

Destination:

> Establish the minimum canonical execution provenance required to reconstruct which code, workflow definition, configuration/profile, model/provider binding, prompt/policy/algorithm versions, and source evidence produced an authoritative run or output.

Key decisions:

- execution/build identity;
- configuration fingerprinting;
- historical-versus-current replay semantics;
- prompt/model/provider identity;
- provenance retention boundaries;
- sensitive-value exclusion.

# Criteria for deciding whether a future concern belongs in the trunk

The audit produced a reusable test for future architecture discussions.

Before adding a new concern to the trunk, ask:

1. **Semantic fan-out:** Will several unrelated future features need the same answer?
2. **Persistence fan-out:** Would discovering the answer later require changing durable record shape or meaning?
3. **Authority fan-out:** Would different interfaces otherwise become competing authorities?
4. **Historical fan-out:** Could a late change invalidate replay/audit interpretation?
5. **Security fan-out:** Could different transports/providers/plugins invent incompatible trust assumptions?
6. **Concurrency fan-out:** Could multiple invocation sources race or duplicate effects?
7. **Replacement cost:** Can this be cleanly added later behind existing boundaries, or would consumers need reinterpretation?

A concern that fails most of these tests is probably a branch, not trunk work.

# Audit limitations

This research intentionally has limits.

## It is not an implementation review

The audit did not attempt to prove every existing class is bug-free or every production path has complete tests.

Its target is architectural omission and retrofit risk.

## Absence conclusions are bounded

Polaris is a large repository. A specialized local helper may exist outside the representative surfaces reviewed. Therefore findings such as “no canonical contract identified” are stronger than “no code exists anywhere.”

Future `$wayfinder` work must independently search the current repository before deciding that a subsystem is truly missing.

## It does not replace active review workflows

Nothing in this document should be used to bypass the durable branch/baseline/review/verification workflow for existing Specs such as #66.

## It does not authorize speculative abstraction

The audit deliberately recommends contracts before infrastructure and semantic ownership before frameworks.

If a Wayfinder can satisfy a concern with a small typed contract and existing primitives, that is preferable to inventing a large generic subsystem.

# Final audit conclusion

Polaris's architecture is mature enough that the next major risks are less visible than missing feature directories.

The platform already has strong answers to:

```text
How are workflows executed?
Where is canonical state stored?
How are derived projections separated?
How are typed values represented?
How are runs observed and replayed?
How are AI-adjacent outputs assigned risk and authority?
How is grounded RAG assembled?
How are model and data-provider boundaries becoming replaceable?
```

The audit found that the next trunk questions are deeper:

```text
Who is acting?
What may that actor do?
What did Polaris actually know at decision time?
What does Polaris trust?
What happens if an effect is retried, duplicated, raced, or only partially observed?
What exact configuration produced the result?
```

Answering those questions before outward branches multiply should make later API, UI, scheduler, plugin, automation, and multi-user work **adapters over the trunk**.

Deferring them risks turning those branches into the accidental owners of platform semantics.

That is the principal conclusion of the Polaris Trunk Completeness Audit.

## Handoff

This document should be supplied as research input when each relevant `$wayfinder` effort is intentionally started.

The authoritative workflow should:

1. re-read current repository state;
2. revalidate the audit finding against current implementation and accepted architecture;
3. reject, narrow, combine, or expand the candidate concern as evidence requires;
4. record actual architecture decisions in Wayfinder/ADR artifacts rather than treating this research as authority;
5. derive Specs and implementation tickets only after those decisions are resolved.

This document must not be cited as proof that a proposed architecture was accepted merely because the audit recommended investigating it.
