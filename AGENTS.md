# AGENTS.md

## Purpose and Authority

These are the operating rules for coding agents working on Polaris.

At the start of a session:

1. `CONTEXT.md` holds the project's canonical vocabulary. Load it on
   demand, not automatically at the start of every session — this
   mirrors how `wiki/entities/` is lazily loaded rather than scanned
   in full. Load it when: a domain term in the current task is
   ambiguous, contested, or being introduced; writing or updating a
   `wiki/entities/` page, per the canonical-terms rule under
   Formatting; or when explicitly running `/domain-modeling`. A task
   that never touches domain vocabulary has no reason to load it.
2. Verify implementation claims directly against current source files
   and unit tests. Entity pages in `wiki/entities/`, if present,
   describe architecture and rationale but can lag real code — see
   `/wiki-lint`'s `[code-drift]` check rather than trusting an entity
   page's claim at face value.
3. Merge these prescriptive rules with any narrower user instructions provided for the active task.

`AGENTS.md` is prescriptive. `CONTEXT.md` is descriptive. Avoid duplicating content between them.

---

## Non-Negotiable Architecture

### Inside-out design

The runtime is the trunk; application, integration, intelligence, portfolio, strategy, recommendation, and interface code are branches.

- Protect stable core contracts.
- Refactor edge code directly to current contracts.
- Do not add compatibility wrappers or legacy adapters unless explicitly approved with a removal plan.
- Do not modify `core/` without user authorization. If a core change is architecturally necessary, explain why and obtain approval first.

### Runtime and workflow boundaries

- `RuntimeEngine` owns execution.
- `WorkflowFacade` is the application workflow boundary.
- `WorkflowBootstrap` is the workflow composition root.
- New workflow capabilities must use `RuntimeNode` and the canonical graph/runtime path.
- Do not create parallel runtimes or bypass the facade/bootstrap.
- `RuntimeContext` and `RuntimeNodeOutput` contain workflow evidence; do not recreate competing runtime business-state aggregates.

### Workflow control and events

- `WorkflowControlManager` owns pause, resume, and cancel state.
- The runtime checks control state cooperatively at safe boundaries.
- `WorkflowFacade` exposes control APIs.
- `EventBus` and typed `RuntimeEvent` objects are the canonical notification path.
- Telemetry maps runtime events at the boundary.
- Do not mutate runtime state directly from CLI or application code.

### Dependency injection

Use Dishka with explicit constructor dependencies.

- Long-lived infrastructure belongs in application scope.
- Each command, request, or future MCP invocation owns a request scope.
- Do not use globals, service locators, hidden dependencies, or split-brain `EventBus`, control, telemetry, persistence, or facade instances.

### Layering

External access must follow:

```text
Application service
→ provider
→ vendor-specific async client
→ external system
```

- Clients own transport, authentication, retries, pagination, rate limits, timeouts, and raw parsing.
- Providers normalize vendor data into stable platform contracts.
- Application services coordinate use cases.
- Intelligence consumes typed service results.
- Agents must never call vendor SDKs directly.
- Intelligence components must not contain transport logic.

### Persistence and projections

- PostgreSQL is the authoritative durable system of record.
- SQLAlchemy models and Alembic migrations govern schema.
- Typed repositories and application persistence services own database access.
- Qdrant, Neo4j, files, caches, and rendered reports are projections or artifacts, not competing authorities.
- Projection rebuilds must not delete canonical PostgreSQL records.
- Workflow outputs become curated records only through an explicit typed eligibility and projection policy.
- Do not promote arbitrary metadata into durable schema; add first-class typed fields when the concept is canonical.

### RAG and MCP

- RAG orchestration belongs in canonical application services.
- PostgreSQL owns curated RAG records; Qdrant and Neo4j are rebuildable retrieval projections.
- Do not implement a second retrieval, ranking, graph, ingestion, or persistence stack in an interface.
- A future MCP server must be a thin external transport over Dishka-resolved application services. If behavior is missing, add it to the canonical service first.

### Backtesting

- Backtests use the production runtime, workflows, services, and contracts.
- Live versus simulated behavior is selected through provider composition.
- The runtime must remain unaware of execution mode.
- Deterministic scenarios require fixed inputs, time, seeds, and independently derived expected outcomes.

### Policy and governance

- Policy answers “May this happen?” with `ALLOW` or `DENY`.
- Governance answers “Should this happen?” with `ALLOW`, `WARN`, `DENY`, `REQUIRE_APPROVAL`, or `SKIP`.
- Governance operates above policy.
- Workflow and capability code must not bypass policy or governance evaluation.
- Do not claim a complete approval subsystem exists unless its contracts, persistence, interfaces, and tests are implemented.

### Architecture Guardrails

- **Authority:** Ensure exactly one authoritative model, owner, and canonical writer for every durable business concept.
- **Classification:** Distinguish cleanly between runtime evidence, canonical domain records, projections, telemetry, and presentation output.
- **Conflict Handling:** Ensure that two separate components do not claim to be the source of truth for the same data.
- **Redundancy Audit:** Evaluate if any existing responsibilities are obsolete or superseded by the new capabilities.
- **Analytical Services Boundary:** Analytical services must return typed results. They are strictly prohibited from persisting workflow-derived results unless database persistence is the explicit use case.
- **Architectural Correctness:** Never infer architectural correctness from imports, passing tests, or high code-health scores alone.

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

- external APIs and vendor SDKs
- JSON and transport serialization
- telemetry and event serialization
- persistence, checkpoints, and replay serialization

Serialize typed objects only when crossing a boundary.

### Numeric precision

Never use `round()` in application, intelligence, analysis, regime, calibration, or persistence logic. Preserve full precision internally. Round only in CLI, Markdown, PDF, web, or other human-facing renderers.

### Python conventions

- Type all public interfaces.
- Prefer `@dataclass(frozen=True, slots=True)` for immutable models.
- Workflow definitions expose `workflow_name` and `workflow_description` as `@property` methods, not class attributes.
- Use async provider/client calls consistently; do not add sync/async compatibility branches without a real boundary requirement.

---

## Observability

Every meaningful operational boundary must be observable once, at its canonical owner.

Verify:

- structured logs for entry failures, retries, degradation, and caught exceptions
- active trace spans for external calls, datastore operations, LLM flows, and long-running work
- counters or histograms for latency, volume, success, and failure
- trace-context propagation through `asyncio` tasks, providers, runtime events, and persistence

Rules:

- External provider calls use the established telemetry wrapper, such as `record_provider_call()`.
- PostgreSQL, Qdrant, and Neo4j operations record latency and defensively log failures.
- Exception logs that diagnose failures include tracebacks.
- Telemetry failures remain non-fatal to valid domain results but must be visible.
- Do not emit duplicate lifecycle events from multiple layers.
- Reuse established emitter and span conventions; do not invent parallel telemetry systems.

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

Current local services may include PostgreSQL, Qdrant, Neo4j, LiteLLM, Ollama, Langfuse, BGE reranker, Prometheus, Jaeger, or Grafana et-all.

---

## Dependencies and shell

Use:

- `uv run`
- `uv add`
- `uv remove`
- `uv sync`

Standard read-only discovery and diagnostic shell commands are allowed.

---

## Repository Analysis Tools

Before editing any files or changing code patterns, you must leverage the project's native discovery tool belt to map context, enforce safety guards, and isolate change blast radiuses.

### repowise

This project maintains a codebase status registry and documentation layout inside the `.repowise/` directory tracking synchronization state, file health, and system hotspots.

For behavioral location, mapping source contexts, code health overview, or file risk auditing, use the installed `/repowise` skill or instructions before tracing raw files manually.

### graphify

This project has a knowledge graph at `graphify-out/` with god nodes, community structure, and cross-file relationships.

For structural dependency lookups or codebase architecture questions, use the installed `/graphify` skill or instructions before tracing raw files manually.

### codegraph

This project leverages an active edge-synthesizer engine to bridge dynamic runtime call flows, framework decorators, and decoupled execution targets.

For tracing implicit function paths, event loops, or dynamic string-keyed dispatches in Python, use the installed `/codegraph` skill before tracing raw files manually.

### codebase-memory-mcp

This project uses codebase-memory-mcp to maintain a knowledge graph of the codebase. ALWAYS prefer MCP graph tools over grep/glob/file-search for code discovery.

For search, trace, architecture, code discovery, impact analysis, targeted index-coverage checks, Cypher queries, dead code detection, cross-service HTTP linking, or ADR management, use the installed `/codebase-memory-mcp` skill before tracing raw files manually.

---

## Development Strategy & Versioning Policies

Project version resolution and database migration lifecycle policy —
pre-1.0 squashing, 1.0 release squashing, and post-1.0 immutability —
are defined in full in the `/database-migrations` skill,
the single source of truth. Read it before creating or modifying any
migration file. Do not duplicate its rules here.

---

## Architectural Decision Records (ADRs) Rules

ADR format, the `status` field, numbering, and when an ADR is
warranted are all defined in `/to-adr-doc` — the single source of
truth for ADR creation. Read it before creating or modifying any file
in `docs/adr/`. Do not duplicate its rules here.

---

## Non-ADR Documents in docs/ Rules

Folder placement, classification, and the entity-prefixed naming
convention for any file created inside `docs/` outside of `docs/adr/`
— which follows `/to-adr-doc` instead — are defined in `/to-doc`, the
single source of truth for non-ADR document creation. Read it before
creating any file under `docs/current/`, `docs/proposed/`,
`docs/reference/`, `docs/process/`, or `docs/research/`. Do not
duplicate its rules here.

---

## Living Entity Wiki

The project maintains a machine-optimized architecture wiki at
`wiki/`. See `wiki/_schema.md` for entity boundaries and document
classification rules, and `wiki/_template.md` for the entity page
format.

### Purpose

`wiki/entities/` is not a second copy of the codebase index. It exists
to hold the one category of knowledge that codebase-memory-mcp,
codegraph, and any other structural tool cannot produce, no matter how
good they get: things that are true about this project but are not
*derivable by parsing the code*.

Those tools answer "what does the code look like right now" — call
chains, module membership, function signatures — by reading the code
directly. That answer is always available on demand and never goes
stale in a way that matters, because it's regenerated from source
every time. Writing that same information into a markdown page would
only add a second, worse copy that silently drifts the moment
something is renamed. Entity pages must never attempt this — see
"What entity pages do *not* contain" below.

What those tools structurally cannot answer, because it was never in
the code to begin with:

- **Why a boundary was drawn where it was** — not what the boundary
  is, which codegraph can show, but the reasoning that made it the
  right boundary and not a different one.
- **What was tried and rejected**, and why — the failed approaches
  that will otherwise get silently retried by a future session that
  has no memory of the last one.
- **What the product actually needs to do next**, and what it must
  never do — for this project specifically, that includes constraints
  like "recommendation-oriented, not autonomous trading": nothing in
  the source code of a well-implemented recommendation engine and a
  poorly-scoped autonomous trading system looks structurally
  different at the function-signature level. That distinction lives
  entirely in intent, and intent is exactly what a parser cannot
  recover. An agent implementing a new feature needs this *before*
  deciding how to build it, not as a retrospective check after.
- **What an earlier session already decided, and why** — so that
  decision doesn't get silently re-litigated or reversed by a later
  session working from the code alone, with no visibility into the
  reasoning that produced it.

This is judgment and synthesis, not structure. It is also,
concretely, the difference between an agent that writes code
consistent with this project's architecture and constraints, and one
that writes code that merely compiles. Consulting the entity wiki
before making a structural change is not a formality — treat a
missed or skipped `/wiki-sync` check with the same seriousness as
shipping code that breaks an existing invariant, because in practice
that is usually what it produces, just discovered later and by
someone else.

### Layers

- `docs/` — authored source layer, human (and human-directed agent)
  maintained.
    - `docs/adr/` — write-once by convention. Content is immutable
      once an ADR's own `status` field is `accepted`; the `status`
      field itself is the one recognized transition (proposed →
      accepted, rejected, deprecated, or superseded by a later ADR),
      changed directly by ADR authors as part of normal ADR lifecycle
      — never by `/wiki-sync`. See `/to-adr-doc` for the full field
      format. The wiki's `doc_class` for these mirrors that `status`
      directly: proposed → proposed, accepted → accepted, rejected →
      rejected, deprecated → deprecated, superseded by ADR-NNNN →
      superseded.
    - Everything else in `docs/` — living documents (`doc_class:
      current`, `proposed`, `process`, `research`, or `reference`),
      edited as the project evolves. Editing itself is ordinary dev
      work, with no pre-edit gate — but editing a `doc_class: current`
      document also triggers `/wiki-sync`'s post-edit staleness check,
      since that class is the only one (besides accepted ADRs)
      permitted to back an entity invariant. Edits to `proposed`,
      `process`, `research`, or `reference` docs remain fully
      independent of the `/wiki-sync` workflow, since none of those
      classes can ever be cited by an invariant.
- `wiki/entities/` — derived layer, owned exclusively by the agent.
  Contains only real entity pages — no template, no schema, no
  exceptions list. Always downstream of `docs/`: the agent may update
  an entity page to reflect a docs/ change, but never edits docs/ to
  match what an entity page currently says. Direction of truth is
  one-way.
- `wiki/index.md` — high-density catalog: one line per entity, link,
  one-sentence summary, category. Also links `reference` and
  `research` docs directly, since neither decomposes into a single
  entity.
- `wiki/log.md` — chronological record of wiki activity: entity
  creations/updates and lint runs, in one append-only file. Written as
  part of the same operation as its corresponding commit, using a
  matching label, so the two can't silently drift apart.
- `wiki/_schema.md` — document classification rules (`doc_class`
  values and how they're assigned) and the entity promotion test.
- `wiki/_template.md` — the mandatory entity page structure.

### When to consult or update the wiki

Before modifying source code, after editing a `doc_class: current`
document under `docs/`, and after an ADR is created or its `status`
changes, follow the `/wiki-sync` skill. It governs three triggers: a
pre-change audit for source code (reading the relevant entity page
before changes, checking compliance against stated invariants and
Rejected Approaches, updating the entity page afterward if the change
alters a structural boundary or invariant), a post-edit staleness
check for living `docs/` content (checking whether any entity page's
invariant, now potentially outdated, cites the just-edited doc), and
an ADR-change check (checking whether a new or changed decision
belongs on an entity page). None run on every edit — see `/wiki-sync`
for the exact conditions. Do not inline any of the three procedures
here; `/wiki-sync` is the single source of truth for all of them, and
other skills (e.g. `/implement-ticket`, `/domain-modeling`) invoke it
explicitly rather than assuming it happens implicitly.

### Formatting

Entity pages are written for AI ingestion, not human reading: strip
narrative scaffolding, use tables/bullets/exact identifiers, use
absolute confidence only in things that are actually structural facts.
Never strip the causal justification behind an invariant — "why" is
the content that makes an invariant worth respecting instead of
"fixing" later. Where `CONTEXT.md` exists, use its canonical domain
terms rather than ad hoc names for the same concept — no dedicated
sync mechanism enforces this going forward, so a stale term simply
gets corrected the next time `/wiki-sync` touches that entity for an
unrelated reason.

### What entity pages do *not* contain

Full file-path enumeration, module contents, or call chains — that's
what codebase-memory-mcp / codegraph already give you live, and it
never drifts because it's derived, not authored. Entity pages hold
what those tools structurally cannot: invariants, rationale, and
cross-component contracts. An entity page with more than 1-2 anchor
paths is a sign it's duplicating the code graph rather than
complementing it.

### Wiki health checks

Periodically, or on-demand, run the `/wiki-lint` skill to audit the
wiki as a whole — contradictions between entities, drift against code
or docs, stale or invalid citations, and structural hygiene. See
`/wiki-lint` for the full list of checks, severity categories, and the
`wiki/log.md` entry format. Do not inline that procedure here;
`/wiki-lint` is the single source of truth for it.

Separately, the user can explicitly run `/wiki-synthesize` periodically as Rejected Approaches
and Open Questions entries accumulate across entities, to surface
recurring cross-entity patterns that no single entity page states on
its own and that `/wiki-lint`'s direct-contradiction check cannot
catch. Unlike `/wiki-lint`, `/wiki-synthesize` never writes to the
wiki — it produces a report for human review only. See
`/wiki-synthesize` for cadence guidance and report format.

---

## Agent skills

### Issue tracker

Issues and PRDs are tracked in GitHub Issues for `sponge-b0b/Polaris`. See `docs/agents/issue-tracker.md`.

### Triage labels

The default triage labels are used: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

This repo uses a single-context domain-doc layout with root `CONTEXT.md` and optional root `docs/adr/`. See `docs/agents/domain.md`.
