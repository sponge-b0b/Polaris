# AGENTS.md

## Purpose and Authority

These are the operating rules for coding agents working on Polaris.

At the start of a session:

1. Read `CONTEXT.md` for the current platform map and architectural status.
2. Read `.claude/CLAUDE.md` for the Repowise-generated system map.
3. Verify implementation claims against current source and tests; generated maps may lag the repository.
4. Merge these rules with any narrower user instruction for the active task.

`AGENTS.md` is prescriptive. `CONTEXT.md` is descriptive. Avoid duplicating detailed architecture between them.

## Behavioral Rules

* Use these behavioral guidelines to reduce common LLM coding mistakes.
* These guidelines are to be used for every prompt you receive.
* Merge with project-specific instructions as needed.

Tradeoff: These guidelines bias toward caution over speed. For trivial tasks, use judgment.

1. Think Before Coding

Don't assume. Don't hide confusion. Surface tradeoffs.

Before implementing:

    State your assumptions explicitly. If uncertain, ask.
    If multiple interpretations exist, present them - don't pick silently.
    If a simpler approach exists, say so. Push back when warranted.
    If something is unclear, stop. Name what's confusing. Ask.

2. Simplicity First

Minimum code that solves the problem. Nothing speculative.

    No features beyond what was asked.
    No abstractions for single-use code.
    No "flexibility" or "configurability" that wasn't requested.
    No error handling for impossible scenarios.
    If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

3. Surgical Changes

Touch only what you must. Clean up only your own mess.

When editing existing code:

    Don't "improve" adjacent code, comments, or formatting.
    Don't refactor things that aren't broken.
    Match existing style, even if you'd do it differently.
    If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

    Remove imports/variables/functions that YOUR changes made unused.
    Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

4. Goal-Driven Execution

Define success criteria. Loop until verified.

Transform tasks into verifiable goals:

    "Add validation" → "Write tests for invalid inputs, then make them pass"
    "Fix the bug" → "Write a test that reproduces it, then make it pass"
    "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]

OR 

1. Establish the baseline and define the success criteria.
2. Implement each bounded change and run its focused verification.
3. Run the final regression checks and review the complete diff.

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

These guidelines are working if: fewer unnecessary changes in diffs, fewer rewrites due to added complexity, and clarifying questions come before implementation rather than after mistakes.

## Architectural Investigation

Implementation scope should be surgical; investigation scope should cover the complete data lifecycle.

Before changing a state, result, schema, or persistence path, trace:

```text
producer
→ client/provider
→ application service
→ intelligence or workflow node
→ RuntimeNodeOutput and RuntimeContext
→ PostgreSQL
→ curated record or projection
→ consumer
```

Required checks:

- Identify one authoritative model, owner, and canonical writer for every durable business concept.
- Distinguish runtime evidence, canonical domain records, projections, telemetry, and presentation output.
- Stop if two components claim to be the source of truth.
- Reevaluate obsolete responsibilities when new capabilities supersede their original purpose.
- After major changes, check for duplicate writers, hidden side effects, metadata-only pseudo-fields, obsolete paths, and competing state models.
- Do not infer architectural correctness from imports, passing tests, or code-health scores alone.

Analytical services return typed results. They must not persist workflow-derived results unless persistence is the explicit use case.

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

## Repository Analysis Tools

### Graphify

Do not read or parse `graphify-out/` during routine startup.

For codebase questions when `graphify-out/graph.json` exists:

- `graphify query "<question>"` for scoped topology
- `graphify path "<A>" "<B>"` for relationships
- `graphify explain "<concept>"` for a focused concept
- use `graphify-out/wiki/index.md` for broad navigation
- read `GRAPH_REPORT.md` only when scoped commands are insufficient

Dirty generated graph files are expected and are not a reason to skip Graphify. After modifying Python code, run:

```bash
uv run graphify update .
```

### Repowise

Before editing Python:

1. Use `get_answer` or `search_codebase` to locate the behavior.
2. Use `get_context` and `get_symbol` for bounded source context.
3. Use `get_health` for target-file biomarkers.
4. Use `get_risk` for hotspots, hidden coupling, and blast radius.
5. Use `get_why` before architectural changes or pattern divergence.

Alert the user before adding code to a highly brittle or high-risk file. Trust scoped results, but verify cited paths still exist before editing.

### Duplication checks

Before extracting shared logic or performing a deep refactor, run the relevant checks:

```bash
uv run pylint --disable=all --enable=duplicate-code --recursive=y .
uv run jscpd .
```

Do not create a helper until existing equivalent logic has been ruled out.

## Verification Standards

Use `uv` for project commands and dependency management.

For meaningful Python changes, run checks in this order:

```bash
uv run ruff check . --fix
uv run ruff format .
uv run mypy . --explicit-package-bases
uv run pytest <appropriate-scope>
```

Then run broader tests when the blast radius warrants them.

- Do not suppress MyPy errors with `# type: ignore` unless explicitly instructed.
- Do not commit code that fails required MyPy validation.
- Infrastructure work normally requires unit, integration, bootstrap/provider, and telemetry coverage.
- Use reasonable command timeouts based on expected duration; investigate rather than assigning arbitrarily large timeouts.

### Database migration tests

Treat the migration timeline as a black box and validate resulting state.

Required contracts:

- one unbranched head that upgrades cleanly from a blank database
- SQLAlchemy model definitions match the upgraded DDL through `pytest-alembic`
- targeted data-state verification for complex transformations

Never count migration files, assert migration filenames, or depend on naming conventions. Use specific revision IDs only when a targeted data migration genuinely requires before/after setup.

## Secrets and Live Services

- Never place credentials, passwords, tokens, or full authenticated connection strings in source, tests, plans, or documentation.
- Tests use environment variables or redacted placeholders.
- Before running live-service tests, identify required services and notify the user.
- Do not wait for unavailable services to time out when the test is unnecessary.

Authorized Docker operations when a required service must be managed:

```text
docker compose up -d [service ...]
docker compose stop [service ...]
docker compose restart [service ...]
docker compose down
```

Current local services may include PostgreSQL, Qdrant, Neo4j, BGE reranker, Prometheus, Jaeger, and Grafana.

## Git Commit Guidelines (Conventional Commits 1.0.0)

You must structure every Git commit message in strict compliance with the **Conventional Commits 1.0.0** specification. Never write generic, conversational, or vague commit summaries (e.g., do not use "wip", "updated files", or "fixed bug").

### 1. Message Structure Blueprint
Every commit message must follow this structural schema exactly:
```text
<type>[optional scope]: <description>

[optional body describing why the change was made]
```
- **Type**: Must be entirely lowercase. Use only the approved structural types listed below.
- **Scope**: Optional but highly encouraged. Represents the specific software layer or folder module modified, wrapped in lowercase parentheses (e.g., `(reranker)`, `(api)`, `(db)`).
- **Description**: Written in the **imperative mood** (e.g., use `add` instead of `added`, `fix` instead of `fixes`). Do not capitalize the first letter and do not add a trailing period.

### 2. Approved Structural Types
Map code changes strictly to these categories:
- **`feat`**: Used when introducing a brand-new application feature or operational capability to the codebase.
- **`fix`**: Used when correcting an active bug, permission block, error log, or software crash.
- **`docs`**: Used for changes restricted entirely to documentation layout text, markdown headers, and user guides.
- **`chore`**: Used for routine maintenance operations: package/dependency management, editing configurations (`.gitignore`, `pyproject.toml`, `.graphifyignore`), or adding static asset/image files.
- **`refactor`**: Used for optimization or structural alterations to production code that do not change its runtime features or behavior.
- **`test`**: Used when generating unit tests, increasing coverage matrix setups, or altering testing suites.
- **`ci`**: Used for orchestration scripts, automated pipelines, deployment assets, or Docker Compose structures.

### 3. Handling Breaking Changes
If an engineering operation changes the system's foundational layout or breaks backward compatibility, append an exclamation point (`!`) directly to the commit type prefix and write `BREAKING CHANGE:` in the commit message body explaining the required manual migration layout steps.
*Example:* `feat(db)!: switch token storage mapping to postgresql`

### 4. Real-world Operational Examples
- `feat(api): include cross-encoder payload validation schemas`
- `fix(reranker): map container user permissions to prevent wsl lockouts`
- `chore(git): add graphify local cache paths to gitignore file`
- `docs: supplement setup documentation detailing offline launch instructions`

## Allowed Operations

### Git

Allowed without confirmation:

- `git status`
- `git add`
- `git commit`
- `git tag`
- `git push`

Require confirmation:

- checkout or switch
- branch creation
- merge, rebase, or cherry-pick
- any reset, including `reset --soft`
- other history-altering operations

### Files

Allowed:

- read, write, and create files
- delete test files, caches, temporary files, and generated artifacts
- rename, move, split, or reorganize files and packages when required by the task and architecture

Require confirmation before deleting source files, packages, modules, or production assets. Report structural changes clearly.

Ignore files excluded by `.codexignore`, including `NOTES.md`.

### Dependencies and shell

Use:

- `uv run`
- `uv add`
- `uv remove`
- `uv sync`

Standard read-only discovery and diagnostic shell commands are allowed.

## Feature Plan Protocol

Store feature plans under:

```text
.agents/plans/plan_<feature-name>.md
```

Rules:

- Never overwrite a root-level global `PLANS.md` for separate features.
- Keep the original proposal separate when appending a Codex recommendation.
- Use Markdown checkboxes for executable steps.
- Update only the active feature plan incrementally.
- During execution, treat that file as the source of truth and record completed work in its `## Step Results` section.
- Leave historical plans untouched.
- When the user requests stepwise execution, complete one step, record its result, and wait for confirmation before the next.

## Final Change Checklist

Before reporting completion:

- confirm the requested behavior and success criteria
- inspect the complete lifecycle and blast radius
- verify one source of truth and one canonical writer
- confirm typed contracts and numeric precision
- confirm telemetry at the canonical boundary without duplicate emission
- run appropriate Ruff, MyPy, tests, and migration checks
- update Graphify after Python changes
- review the diff for unrelated edits, secrets, compatibility shims, and obsolete code
- document any required live services, residual risks, or deferred work
