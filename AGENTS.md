# AGENTS.md

## Purpose and Authority

These are the operating rules for coding agents working on Polaris.

`AGENTS.md` is primarily **prescriptive agent policy**: how an agent must work in this repository.

It is not intended to become a second authoritative copy of project architecture.

At the start of a task:

1. `CONTEXT.md` holds the project's canonical domain vocabulary. Load it on demand, not automatically at the start of every session. Load it when:

   * a domain term in the current task is ambiguous, contested, or being introduced;
   * writing or updating a `wiki/entities/` page; or
   * explicitly running `$domain-modeling`.

   A task that does not depend on domain vocabulary does not need to load it.

2. Match claims to their proper authority:

   * current source code, configuration, executable architecture checks, and relevant tests provide evidence of **implementation reality**;
   * accepted ADRs establish **active architectural decisions**;
   * `docs/current/` claims to describe **current architectural state**;
   * `wiki/entities/` is a **derived synthesis layer**, never an authority over its sources.

3. If accepted ADRs, `docs/current/`, and verified implementation evidence materially disagree, surface `[source-conflict]`. Do not silently choose whichever source makes the current task easiest.

4. Merge these repository rules with any narrower user instructions for the active task.

`AGENTS.md` is prescriptive. `CONTEXT.md` is descriptive vocabulary. Avoid duplicating content between them.

---

## Non-Negotiable Architecture

> **Migration note:** This section predates the Living Entity Wiki and still contains architectural facts that ultimately belong in accepted ADRs, `docs/current/`, and derived entity invariants.
>
> Preserve these guardrails until each architectural fact has a verified authoritative source and corresponding wiki representation. Do **not** remove one merely because the wiki system now exists.
>
> Do not add new durable architectural facts here. New decisions belong through `$to-adr-doc` or `$to-doc`, with `$wiki-sync` maintaining the derived entity knowledge.
>
> If a rule here materially conflicts with an accepted ADR, `docs/current/`, or verified implementation evidence, surface `[source-conflict]` rather than assuming this section automatically wins.

### Inside-out design

The runtime is the trunk; application, integration, intelligence, portfolio, strategy, recommendation, and interface code are branches.

* Protect stable core contracts.
* Refactor edge code directly to current contracts.
* Do not add compatibility wrappers or legacy adapters unless explicitly approved with a removal plan.
* Do not modify `core/` without user authorization. If a core change is architecturally necessary, explain why and obtain approval first.

### Runtime and workflow boundaries

* `RuntimeEngine` owns execution.
* `WorkflowFacade` is the application workflow boundary.
* `WorkflowBootstrap` is the workflow composition root.
* New workflow capabilities must use `RuntimeNode` and the canonical graph/runtime path.
* Do not create parallel runtimes or bypass the facade/bootstrap.
* `RuntimeContext` and `RuntimeNodeOutput` contain workflow evidence; do not recreate competing runtime business-state aggregates.

### Workflow control and events

* `WorkflowControlManager` owns pause, resume, and cancel state.
* The runtime checks control state cooperatively at safe boundaries.
* `WorkflowFacade` exposes control APIs.
* `EventBus` and typed `RuntimeEvent` objects are the canonical notification path.
* Telemetry maps runtime events at the boundary.
* Do not mutate runtime state directly from CLI or application code.

### Dependency injection

Use Dishka with explicit constructor dependencies.

* Long-lived infrastructure belongs in application scope.
* Each command, request, or future MCP invocation owns a request scope.
* Do not use globals, service locators, hidden dependencies, or split-brain `EventBus`, control, telemetry, persistence, or facade instances.

### Layering

External access must follow:

```text
Application service
→ provider
→ vendor-specific async client
→ external system
```

* Clients own transport, authentication, retries, pagination, rate limits, timeouts, and raw parsing.
* Providers normalize vendor data into stable platform contracts.
* Application services coordinate use cases.
* Intelligence consumes typed service results.
* Agents must never call vendor SDKs directly.
* Intelligence components must not contain transport logic.

### Persistence and projections

* PostgreSQL is the authoritative durable system of record.
* SQLAlchemy models and Alembic migrations govern schema.
* Typed repositories and application persistence services own database access.
* Qdrant, Neo4j, files, caches, and rendered reports are projections or artifacts, not competing authorities.
* Projection rebuilds must not delete canonical PostgreSQL records.
* Workflow outputs become curated records only through an explicit typed eligibility and projection policy.
* Do not promote arbitrary metadata into durable schema; add first-class typed fields when the concept is canonical.

### RAG and MCP

* RAG orchestration belongs in canonical application services.
* PostgreSQL owns curated RAG records; Qdrant and Neo4j are rebuildable retrieval projections.
* Do not implement a second retrieval, ranking, graph, ingestion, or persistence stack in an interface.
* A future MCP server must be a thin external transport over Dishka-resolved application services. If behavior is missing, add it to the canonical service first.

### Backtesting

* Backtests use the production runtime, workflows, services, and contracts.
* Live versus simulated behavior is selected through provider composition.
* The runtime must remain unaware of execution mode.
* Deterministic scenarios require fixed inputs, time, seeds, and independently derived expected outcomes.

### Policy and governance

* Policy answers "May this happen?" with `ALLOW` or `DENY`.
* Governance answers "Should this happen?" with `ALLOW`, `WARN`, `DENY`, `REQUIRE_APPROVAL`, or `SKIP`.
* Governance operates above policy.
* Workflow and capability code must not bypass policy or governance evaluation.
* Do not claim a complete approval subsystem exists unless its contracts, persistence, interfaces, and tests are implemented.

### Architecture guardrails

* **Authority:** Ensure exactly one authoritative model, owner, and canonical writer for every durable business concept.
* **Classification:** Distinguish cleanly between runtime evidence, canonical domain records, projections, telemetry, and presentation output.
* **Conflict Handling:** Ensure that two separate components do not claim to be the source of truth for the same data.
* **Redundancy Audit:** Evaluate whether existing responsibilities become obsolete or superseded by new capabilities.
* **Analytical Services Boundary:** Analytical services must return typed results. They must not persist workflow-derived results unless database persistence is the explicit use case.
* **Architectural Correctness:** Never infer architectural correctness from imports, passing tests, or high code-health scores alone.

---

## Data Contracts

### Typed internals

Prefer immutable typed models:

```python
@dataclass(frozen=True, slots=True)
class ExampleSignal:
    ...
```

Use typed requests, results, DTOs, domain records, signals, and runtime contracts inside the platform.

`dict[str, Any]` is acceptable only at boundaries such as:

* external APIs and vendor SDKs;
* JSON and transport serialization;
* telemetry and event serialization;
* persistence, checkpoints, and replay serialization.

Serialize typed objects only when crossing a boundary.

### Numeric precision

Never use `round()` in application, intelligence, analysis, regime, calibration, or persistence logic.

Preserve full precision internally.

Round only in CLI, Markdown, PDF, web, or other human-facing renderers.

### Python conventions

* Type all public interfaces.
* Prefer `@dataclass(frozen=True, slots=True)` for immutable models.
* Workflow definitions expose `workflow_name` and `workflow_description` as `@property` methods, not class attributes.
* Use async provider/client calls consistently.
* Do not add sync/async compatibility branches without a real boundary requirement.

---

## Observability

Every meaningful operational boundary must be observable once, at its canonical owner.

Verify:

* structured logs for entry failures, retries, degradation, and caught exceptions;
* active trace spans for external calls, datastore operations, LLM flows, and long-running work;
* counters or histograms for latency, volume, success, and failure;
* trace-context propagation through `asyncio` tasks, providers, runtime events, and persistence.

Rules:

* External provider calls use the established telemetry wrapper, such as `record_provider_call()`.
* PostgreSQL, Qdrant, and Neo4j operations record latency and defensively log failures.
* Exception logs that diagnose failures include tracebacks.
* Telemetry failures remain non-fatal to valid domain results but must be visible.
* Do not emit duplicate lifecycle events from multiple layers.
* Reuse established emitter and span conventions; do not invent parallel telemetry systems.

---

## Secrets

Never place credentials, passwords, tokens, or full authenticated connection strings in source, tests, plans, or documentation.

---

## Authorized Docker Operations

These Docker operations are authorized when a required service must be managed:

```text
docker compose up -d [service ...]
docker compose stop [service ...]
docker compose restart [service ...]
docker compose down
```

Current local services may include PostgreSQL, Qdrant, Neo4j, LiteLLM, Ollama, Langfuse, BGE reranker, Prometheus, Jaeger, or Grafana.

---

## Dependencies and Shell

Use:

* `uv run`
* `uv add`
* `uv remove`
* `uv sync`

Standard read-only discovery and diagnostic shell commands are allowed.

---

## Repository Analysis Tools

Before editing files or changing code patterns, use the project's native discovery tool belt to map relevant context, enforce safety guards, and understand the likely change blast radius.

Use the smallest tool sufficient for the question rather than performing broad manual source scans by default.

### `repowise`

This project maintains a codebase status registry and documentation layout inside `.repowise/`, tracking synchronization state, file health, and system hotspots.

For behavioral location, mapping source contexts, code-health overview, or file-risk auditing, prefer the installed `$repowise` skill before tracing raw files manually.

### `graphify`

This project maintains a knowledge graph under `graphify-out/` containing community structure and cross-file relationships.

For structural dependency lookups or broad codebase architecture questions, prefer the installed `$graphify` skill before tracing raw files manually.

### `codegraph`

The project uses an edge-synthesizer capable of connecting dynamic runtime call flows, framework decorators, and decoupled execution targets.

For tracing implicit function paths, event loops, or dynamic string-keyed dispatch in Python, prefer the installed `$codegraph` skill before tracing raw files manually.

### `codebase-memory-mcp`

This project uses `codebase-memory-mcp` to maintain a knowledge graph of the codebase.

Prefer the installed `$codebase-memory-mcp` skill over raw grep/glob/file-search for code discovery, architecture exploration, impact analysis, targeted index-coverage checks, Cypher queries, dead-code analysis, cross-service HTTP linking, and related graph-backed investigation.

Exact literal reference checks remain appropriate where graph analysis provides no advantage.

---

## Development Strategy and Versioning

Project version resolution and database migration lifecycle policy — including pre-1.0 squashing, 1.0 release handling, and post-1.0 immutability — are owned by the `$database-migrations` skill.

Read `$database-migrations` before creating or modifying migration files.

Do not duplicate migration lifecycle rules here.

---

## Architectural Decision Records

The `$to-adr-doc` skill is the single source of truth for:

* ADR format;
* mandatory status metadata;
* numbering and naming;
* when an ADR is warranted;
* allowed lifecycle transitions;
* body mutability and historical immutability;
* reconsideration and supersession; and
* Living Entity Wiki synchronization triggered by ADR changes.

Use `$to-adr-doc` whenever:

* creating an ADR;
* substantively editing a proposed ADR; or
* changing an ADR lifecycle status.

Do not manually invent an ADR lifecycle outside that skill.

---

## Non-ADR Documents Under `docs/`

For a **new** non-ADR document, use `$to-doc`.

It owns creation-time classification, canonical placement, naming, and relevant Living Entity Wiki follow-through.

For an **existing** non-ADR document that needs classification, reclassification, relocation, or naming correction, use `$classify-doc`.

Document classification and naming policy itself is defined in `wiki/_schema.md`.

Do not:

* store an independent `doc_class` or `Doc-Class:` field in non-ADR documents;
* place new project-owned documents loose under `docs/`;
* manually move an existing classified document without accounting for its inbound references and possible change in wiki authority.

---

## Living Entity Wiki

The project maintains a machine-oriented architecture knowledge layer under `wiki/`.

Its purpose is to preserve durable architectural knowledge that cannot be cheaply and reliably reconstructed from current code structure alone.

This includes:

* why an entity boundary exists;
* active architectural invariants and their causal reasoning;
* meaningful rejected approaches;
* unresolved architectural questions;
* accepted decisions whose implementation is still pending;
* proposed future direction worth preserving.

The wiki must complement live repository analysis, not duplicate it.

### Authority model

The entity wiki is always derived.

```text
accepted ADRs + current docs + implementation evidence
                         ↓
                  wiki/entities/
```

An entity page never overrides its sources.

When authoritative sources materially disagree, surface `[source-conflict]` before attempting ordinary drift repair.

### Wiki structure

* `wiki/index.md` — authoritative registry of active entities and their Category, Implementation state, Routing Anchors, and concise Summary. It also provides discovery links for genuinely cross-cutting platform documents where required by `wiki/_schema.md`.
* `wiki/entities/` — active derived entity pages containing architectural knowledge defined by `wiki/_template.md`.
* `wiki/log.md` — concise semantic history of **substantive wiki mutations**, not tool executions.
* `wiki/_schema.md` — structural rules for document classification, source authority, entity boundaries, index structure, naming, and topology.
* `wiki/_template.md` — required entity-page structure and claim provenance rules.

### When to invoke `$wiki-sync`

Use `$wiki-sync` for these triggers:

1. **Source code**
   Before and after a substantive source-code change.

2. **Current or proposed non-ADR documents**
   After substantive creation, editing, or authority-changing reclassification involving `docs/current/` or `docs/proposed/`.

3. **ADRs**
   After:

   * creating an ADR;
   * substantively editing an ADR while it remains `proposed`; or
   * changing an ADR lifecycle status.

4. **Entity topology**
   When an entity is created/promoted, renamed, split, merged, removed, or materially changes scope/boundary rationale.

Do not inline the `$wiki-sync` procedure here.

`$wiki-sync` is the single source of truth for per-change wiki maintenance.

Other implementation skills must invoke it explicitly when their work meets one of these triggers.

### Entity routing

Begin with `wiki/index.md`.

Routing Anchors are coarse, non-exhaustive starting hints only.

If routing is ambiguous, cross-boundary, or unmatched, use repository analysis such as `$codegraph` or `$codebase-memory-mcp` rather than guessing entity ownership.

Do not maintain a second dependency graph inside entity pages.

### Entity-page formatting

Entity pages are optimized for reliable machine ingestion.

Keep them:

* concise;
* claim-oriented;
* causally explicit;
* source-backed where required;
* honest about uncertainty.

Preserve the **why** behind architectural constraints. That causal reasoning is the durable information that code structure usually cannot recover.

When domain terminology matters, use canonical terms from `CONTEXT.md`.

Entity pages have no YAML frontmatter.

Do not add:

* `category`;
* `implementation`;
* Routing Anchors;
* `last_updated`;
* `linked_docs`;
* full file inventories;
* module listings;
* call chains;
* manually maintained upstream/downstream dependency lists.

Category, Implementation, and Routing Anchors belong only in `wiki/index.md`.

Inline `source:` citations are the sole representation of entity-to-document relationships.

### Evidence strength

Do not claim more certainty than the evidence supports.

A mechanically observable invariant may be positively verified against implementation.

An architectural or intent-level invariant may be audited for concrete contradictory evidence, but failure to find a violation does not prove compliance.

Use:

> no contrary implementation evidence found

when that is the strongest conclusion available.

Do not convert inference into architectural fact.

### Wiki health

Run `$wiki-lint` on demand, after broad multi-entity work, or whenever wiki trustworthiness is in doubt.

`$wiki-lint` owns:

* `[source-conflict]`;
* `[code-drift]`;
* `[doc-drift]`;
* citation validity and lifecycle;
* document-classification hygiene;
* Open Question review;
* entity/index structural integrity;
* direct cross-entity contradictions.

A clean `$wiki-lint` run produces a report only.

It does not modify `wiki/log.md` or create a commit merely to record that lint ran.

Run `$wiki-synthesize` manually when accumulated Rejected Approaches and Open Questions may reveal a broader recurring pattern.

`$wiki-synthesize` is higher-inference and strictly report-only.

It never:

* creates architectural authority;
* mutates the wiki;
* edits docs;
* edits code;
* writes `wiki/log.md`; or
* creates a commit.

A synthesis finding becomes durable knowledge only after human review and action through the normal owning workflow such as `$to-adr-doc` or `$wiki-sync`.

---

## Migration of Architecture Facts Out of `AGENTS.md`

The architectural facts still present under **Non-Negotiable Architecture** are transitional.

Migrate them incrementally rather than deleting them wholesale.

For each architectural fact:

1. determine whether an accepted ADR or `docs/current/` document already authoritatively supports it;
2. if no authoritative source exists, create the appropriate decision/current-state documentation through `$to-adr-doc` or `$to-doc`;
3. classify or reclassify existing documents through `$classify-doc` where necessary;
4. allow the bootstrap or `$wiki-sync` process to derive the corresponding entity knowledge;
5. verify the entity representation and source consistency;
6. only then remove the duplicate architectural fact from `AGENTS.md`.

Do not create ADRs merely to empty this section.

Use an ADR only when the `$to-adr-doc` decision criteria are actually met.

Current-state facts that do not warrant an ADR may belong in `docs/current/`.

True agent-behavior rules remain in `AGENTS.md`.

---

## Agent Skills

### Issue tracker

Issues and PRDs are tracked in GitHub Issues for `sponge-b0b/Polaris`.

See `docs/agents/issue-tracker.md`.

### Triage labels

The default triage labels are:

* `needs-triage`
* `needs-info`
* `ready-for-agent`
* `ready-for-human`
* `wontfix`

See `docs/agents/triage-labels.md`.

### Domain docs

This repository uses a single-context domain-doc layout with root `CONTEXT.md` and optional root `docs/adr/`.

See `docs/agents/domain.md`.
