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

## Coding Conduct

When changing Python source, use `$coding-standards` and follow the repository's
configured Ruff, formatting, typing, and verification practices.

Architectural decisions and current architectural descriptions live in
`docs/adr/` and `docs/current/`; consult the applicable source instead of using
`AGENTS.md` as an architecture reference. When changing scoring code, consult
the score semantics in `docs/current/platform-data-contract-inventory.md` rather
than relying on `CONTEXT.md` or inferred field names.

Agent-facing coding rules:

* Type public interfaces.
* Prefer `@dataclass(frozen=True, slots=True)` for immutable internal models.
* Do not use `round()` in application, intelligence, analysis, regime,
  calibration, or persistence logic; preserve full precision internally and
  round only in human-facing renderers.
* Use async provider/client calls consistently.
* Do not add sync/async compatibility branches without a real boundary
  requirement and an applicable architecture source.

## Observability Practice

When changing an operational boundary, consult the current observability and
platform architecture documents before implementing telemetry behavior.

Verify appropriate structured logs, trace spans, metrics, trace propagation, and
failure visibility using established repository conventions. Do not create
parallel telemetry systems or duplicate lifecycle emission paths.

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
