# AGENTS.md

## Purpose and Authority

These are the operating rules for coding agents working on Polaris.

`AGENTS.md` is primarily **prescriptive agent policy**: how an agent must work in this repository. It is not a second authoritative copy of project architecture.

At the start of a task:

1. Load `CONTEXT.md` only when domain vocabulary matters, including when:

   * a domain term is ambiguous, contested, or new;
   * writing/updating an entity page;
   * running `$domain-modeling`.

2. Match claims to the correct authority:

   * code, configuration, executable checks, and relevant tests → implementation reality;
   * accepted ADRs → active architectural decisions;
   * `docs/current/` → current architectural description;
   * `wiki/entities/` → derived architectural knowledge.

3. If applicable authorities materially disagree, surface `[source-conflict]`. Do not silently choose whichever source makes the task easiest.

4. Merge these repository rules with narrower user instructions for the active task.

`CONTEXT.md` is canonical domain vocabulary. Avoid duplicating it here.

---

## Non-Negotiable Architecture

> **Migration note:** This section predates the Living Entity Wiki and still contains architectural facts that should eventually live in accepted ADRs, `docs/current/`, and derived entity invariants.
>
> Preserve each rule until it has verified authoritative coverage and corresponding wiki representation.
>
> Do not add new durable architectural facts here. Use `$to-adr-doc` or `$to-doc`, with `$wiki-sync` maintaining derived entity knowledge.
>
> If a rule here conflicts materially with accepted ADRs, `docs/current/`, or verified implementation, surface `[source-conflict]`.

### Inside-out design

The runtime is the trunk; application, integration, intelligence, portfolio, strategy, recommendation, and interface code are branches.

* Protect stable core contracts.
* Refactor edge code directly to current contracts.
* Do not add compatibility wrappers or legacy adapters unless explicitly approved with a removal plan.
* Do not modify `core/` without user authorization. If necessary, explain why and obtain approval first.

### Runtime and workflow boundaries

* `RuntimeEngine` owns execution.
* `WorkflowFacade` is the application workflow boundary.
* `WorkflowBootstrap` is the workflow composition root.
* New workflow capabilities use `RuntimeNode` and the canonical graph/runtime path.
* Do not create parallel runtimes or bypass the facade/bootstrap.
* `RuntimeContext` and `RuntimeNodeOutput` contain workflow evidence; do not recreate competing runtime business-state aggregates.

### Workflow control and events

* `WorkflowControlManager` owns pause/resume/cancel state.
* Runtime checks control state cooperatively at safe boundaries.
* `WorkflowFacade` exposes control APIs.
* `EventBus` and typed `RuntimeEvent` objects are the canonical notification path.
* Telemetry maps runtime events at the boundary.
* CLI/application code must not mutate runtime state directly.

### Dependency injection

Use Dishka with explicit constructor dependencies.

* Long-lived infrastructure belongs in application scope.
* Each command/request/future MCP invocation owns a request scope.
* Do not use globals, service locators, hidden dependencies, or split-brain infrastructure instances.

### Layering

External access follows:

```text
Application service
→ provider
→ vendor-specific async client
→ external system
```

* Clients own transport, authentication, retries, pagination, rate limits, timeouts, and raw parsing.
* Providers normalize vendor data into stable contracts.
* Application services coordinate use cases.
* Intelligence consumes typed service results.
* Agents never call vendor SDKs directly.
* Intelligence must not contain transport logic.

### Persistence and projections

* PostgreSQL is the authoritative durable system of record.
* SQLAlchemy models and Alembic migrations govern schema.
* Typed repositories and application persistence services own database access.
* Qdrant, Neo4j, files, caches, and rendered reports are projections/artifacts, not competing authorities.
* Projection rebuilds must not delete canonical PostgreSQL records.
* Workflow outputs become curated records only through explicit typed eligibility/projection policy.
* Canonical concepts get first-class typed fields rather than arbitrary metadata.

### RAG and MCP

* RAG orchestration belongs in canonical application services.
* PostgreSQL owns curated RAG records; Qdrant and Neo4j are rebuildable projections.
* Do not create a second retrieval, ranking, graph, ingestion, or persistence stack in an interface.
* A future MCP server is a thin transport over Dishka-resolved application services.

### Backtesting

* Backtests use production runtime, workflows, services, and contracts.
* Live vs simulated behavior is selected through provider composition.
* Runtime remains unaware of execution mode.
* Deterministic scenarios require fixed inputs, time, seeds, and independently derived expected outcomes.

### Policy and governance

* Policy answers **May this happen?** with `ALLOW` or `DENY`.
* Governance answers **Should this happen?** with `ALLOW`, `WARN`, `DENY`, `REQUIRE_APPROVAL`, or `SKIP`.
* Governance operates above policy.
* Workflow/capability code must not bypass either.
* Do not claim a complete approval subsystem exists until its contracts, persistence, interfaces, and tests exist.

### Architecture guardrails

* **Authority:** one authoritative model, owner, and canonical writer per durable business concept.
* **Classification:** distinguish runtime evidence, canonical records, projections, telemetry, and presentation.
* **Conflict:** two components must not claim authority over the same durable data.
* **Redundancy:** new capabilities should retire superseded responsibilities where appropriate.
* **Analytical services:** return typed results; persist workflow-derived results only when persistence is the explicit use case.
* **Correctness:** do not infer architectural correctness from imports, passing tests, or code-health scores alone.

---

## Data Contracts

### Typed internals

Prefer immutable typed models:

```python
@dataclass(frozen=True, slots=True)
class ExampleSignal:
    ...
```

Use typed requests, results, DTOs, domain records, signals, and runtime contracts internally.

`dict[str, Any]` is acceptable at serialization/transport boundaries such as:

* external APIs/vendor SDKs;
* JSON transport;
* telemetry/events;
* persistence/checkpoints/replay.

Serialize typed objects only when crossing a boundary.

### Numeric precision

Never use `round()` in application, intelligence, analysis, regime, calibration, or persistence logic.

Preserve full precision internally. Round only in human-facing renderers.

### Python conventions

* Type public interfaces.
* Prefer `@dataclass(frozen=True, slots=True)` for immutable models.
* Workflow definitions expose `workflow_name` and `workflow_description` as properties.
* Use async provider/client calls consistently.
* Do not add sync/async compatibility branches without a real boundary requirement.

---

## Observability

Every meaningful operational boundary is observable once at its canonical owner.

Verify appropriate:

* structured failure/retry/degradation logs;
* trace spans for external calls, datastore operations, LLM flows, and long work;
* latency/volume/success/failure metrics;
* trace propagation through async tasks, providers, runtime events, and persistence.

Rules:

* use established telemetry wrappers/emitter/span conventions;
* datastore operations record latency and defensively log failures;
* diagnostic exception logs include tracebacks;
* telemetry failure must not invalidate a valid domain result, but must remain visible;
* do not emit duplicate lifecycle events or create parallel telemetry systems.

---

## Secrets

Never place credentials, passwords, tokens, or full authenticated connection strings in source, tests, plans, or documentation.

---

## Authorized Docker Operations

When required and otherwise safe:

```text
docker compose up -d [service ...]
docker compose stop [service ...]
docker compose restart [service ...]
docker compose down
```

Manage only services needed for the active task.

---

## Dependencies and Shell

Use:

* `uv run`
* `uv add`
* `uv remove`
* `uv sync`

Standard read-only discovery and diagnostic shell commands are allowed.

---

## Repository Analysis

Use the smallest discovery tool sufficient for the question rather than broad manual scanning.

* `$repowise` — repository status, hot spots, health, and behavioral location.
* `$graphify` — broad structural/dependency relationships.
* `$codegraph` — implicit/dynamic call paths and dispatch.
* `$codebase-memory-mcp` — graph-backed discovery, architecture, impact, dead-code, and cross-service analysis.

Exact literal searches remain appropriate when graph analysis provides no advantage.

---

## Database Migrations

Migration lifecycle policy is owned by `$database-migrations`.

Read and use it before creating or modifying migration files.

Do not duplicate migration policy here.

---

## ADRs

`$to-adr-doc` is the single source of truth for ADR creation and lifecycle.

Use it when:

* creating an ADR;
* substantively editing a proposed ADR;
* changing ADR status.

Do not invent ADR lifecycle behavior independently.

---

## Non-ADR Documents

Use:

* `$to-doc` for a new non-ADR document;
* `$classify-doc` for classification, reclassification, relocation, or naming correction of an existing non-ADR document.

Classification/naming policy lives in `wiki/_schema.md`.

Do not:

* store `doc_class` or `Doc-Class:` metadata;
* leave new project-owned documents loose under `docs/`;
* manually move classified documents without updating references and authority consequences.

---

## Living Entity Wiki

The project maintains a machine-oriented architectural knowledge layer under `wiki/`.

It preserves durable knowledge that is not cheaply reconstructable from current code, especially:

* boundary rationale;
* active invariants and causal reasoning;
* meaningful rejected approaches;
* unresolved questions;
* future architectural direction.

### Structure

* `wiki/index.md` — active entity registry and routing metadata.
* `wiki/entities/` — derived entity knowledge.
* `wiki/log.md` — semantic wiki mutation history.
* `wiki/_schema.md` — structural policy.
* `wiki/_template.md` — entity-page format/provenance.

### Lifecycle

Use `$wiki-sync` for:

* substantive source changes, before and after;
* substantive `docs/current/` / `docs/proposed/` changes;
* ADR creation, proposed-body edits, or lifecycle changes;
* entity topology/boundary changes.

Do not reproduce `$wiki-sync` procedure here.

Start entity routing from `wiki/index.md`; use `$codegraph` or `$codebase-memory-mcp` when routing is ambiguous.

Entity pages:

* have no YAML frontmatter;
* preserve causal **why**;
* use canonical `CONTEXT.md` terminology where relevant;
* do not store Category, Implementation, Routing Anchors, `last_updated`, `linked_docs`, file inventories, call chains, or dependency lists.

Use inline `source:` citations for entity-document relationships.

Do not claim stronger implementation certainty than the evidence supports.

Use `$wiki-lint` for whole-wiki health/conflict/drift auditing.

Use `$wiki-synthesize` manually for higher-inference recurring-pattern analysis; it is report-only.

---

## Migrating Architecture Facts Out of `AGENTS.md`

The facts under **Non-Negotiable Architecture** are transitional.

For each one:

1. verify an authoritative accepted ADR or `docs/current/` source exists;
2. create the appropriate source through `$to-adr-doc` or `$to-doc` only when genuinely needed;
3. use `$classify-doc` for existing documents where necessary;
4. derive/verify corresponding wiki knowledge;
5. remove the duplicate from `AGENTS.md` only after authoritative coverage is established.

Do not create ADRs merely to empty this section.

True agent-behavior policy remains here.

---

## Agent Skills

### Issue tracker

Issues and PRDs are tracked in GitHub Issues for `sponge-b0b/Polaris`.

See `docs/agents/issue-tracker.md`.

### Triage labels

Default labels:

* `needs-triage`
* `needs-info`
* `ready-for-agent`
* `ready-for-human`
* `wontfix`

See `docs/agents/triage-labels.md`.

### Domain docs

This repository uses a single-context domain-doc layout with root `CONTEXT.md` and optional root `docs/adr/`.

See `docs/agents/domain.md`.
