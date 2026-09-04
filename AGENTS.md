# AGENTS.md

## Purpose and Authority

These are the operating rules for coding agents working on Polaris.

`AGENTS.md` is primarily **prescriptive agent policy**: how an agent must work in this repository. It is not a second authoritative copy of project architecture.

At the start of a task:

1. Match claims to the correct authority:

   * code, configuration, executable checks, and relevant tests outside `legacy/` → current implementation reality;
   * accepted ADRs outside `legacy/` → active architectural decisions;
   * active architecture documents outside `legacy/` → current architectural description;
   * an active root `wiki/entities/`, when present → derived architectural knowledge;
   * `legacy/v0_1/` → historical donor/reference material only, never current product, architecture, implementation, or workflow authority.

2. If applicable authorities materially disagree, surface `[source-conflict]`. Do not silently choose whichever source makes the task easiest.

3. Merge these repository rules with narrower user instructions for the active task.

### Domain Vocabulary

Do not preload `CONTEXT.md`.

Read `CONTEXT.md` only when:

* a domain term is ambiguous, contested, or new;
* canonical domain vocabulary is required for the current work;
* writing/updating an entity page where domain terminology is relevant;
* running `$domain-modeling`.

Context compaction, conversation continuation, or task-state recovery does not by itself require re-reading `CONTEXT.md`.

If the required vocabulary is already established in the current task context, do not re-read `CONTEXT.md` unless it needs to be verified or refreshed.

`CONTEXT.md` is canonical domain vocabulary. Avoid duplicating it here.

### Greenfield / Legacy Boundary

The canonical greenfield implementation lives under `src/polaris/`.

`legacy/v0_1/` preserves the pre-greenfield Polaris platform as donor/reference material. New Polaris code, tests, configuration, migrations, tools, and runtime paths must not import, wrap, extend, execute through, or otherwise depend on `legacy/`.

Nothing survives because it already existed. A dependency, schema, migration, abstraction, workflow, runtime mechanism, architecture document, test, or implementation pattern from `legacy/` may be reused only after the current product need and architectural owner are independently established. Reuse means deliberately copying or transplanting the useful implementation into the current greenfield boundary; it never means creating a runtime dependency on `legacy/`.

Do not treat ADRs, `docs/current/`, wiki pages, manifests, tests, or code under `legacy/v0_1/` as current authority. When current greenfield architecture has not yet established an answer, surface the gap and use the applicable requirements/architecture process rather than inheriting the legacy answer by default.

---

## Coding Conduct

When changing source code, use `$coding-standards`.

Its requirements are mandatory, including project-specific data-contract, scoring, precision, async, observability, and related implementation practices.

When a coding rule depends on project-specific semantics or architecture, follow the applicable current non-legacy ADR or architecture source referenced by `$coding-standards`. Do not infer architectural or data-contract semantics from field names, legacy implementation, existing implementation accidents, `CONTEXT.md`, or this file.

Do not duplicate coding-standard policy in `AGENTS.md`.

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

## Pytest Service Preflight

No pytest command may launch until the exact selected test scope's external-service prerequisites have been identified and, when applicable, verified ready.

Before every pytest invocation, identify the exact selected greenfield test scope and inspect its active root configuration, tests, and fixtures to classify the complete scope as service-free or requiring one or more external services. For multi-file or directory scopes, use the union of all prerequisites. Identify required environment/configuration prerequisites, and for service-backed tests verify required services are ready before pytest starts. The v0.1 testing guide under `legacy/v0_1/docs/process/` is historical reference only and must not be treated as current greenfield test authority.

Do not use pytest startup, a client timeout, a connection exception, or a skip as the readiness probe. If prerequisites cannot be verified, do not launch pytest; report the verification as unresolved.

`POLARIS_BROAD_VERIFY_AUTHORIZED` must be supplied only for the individual command requiring authorization, for example `POLARIS_BROAD_VERIFY_AUTHORIZED=<task-specific-value> uv run pytest ...`. Never export it globally or persist it into a shell/session environment.

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

For current greenfield analysis, exclude `legacy/` unless the task explicitly requires donor/reference inspection.

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

Classification/naming policy lives in the active root `wiki/_schema.md` when a greenfield Living Entity Wiki is established. Do not use the legacy wiki schema as current authority.

Do not:

* store `doc_class` or `Doc-Class:` metadata;
* leave new project-owned documents loose under `docs/`;
* manually move classified documents without updating references and authority consequences.

---

## Living Entity Wiki

The pre-greenfield Living Entity Wiki is preserved under `legacy/v0_1/wiki/`. No legacy wiki page is current architectural authority.

When a greenfield Living Entity Wiki is intentionally established at root `wiki/`, it is the machine-oriented architectural knowledge layer and preserves durable knowledge that is not cheaply reconstructable from current code, especially:

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

When an active root wiki exists, use `$wiki-sync` for:

* substantive source changes, before and after;
* substantive current/proposed architecture-document changes;
* ADR creation, proposed-body edits, or lifecycle changes;
* entity topology/boundary changes.

Do not reproduce `$wiki-sync` procedure here.

Start entity routing from `wiki/index.md`; use `$codegraph` or `$codebase-memory-mcp` when routing is ambiguous.

Entity pages:

* have no YAML frontmatter;
* preserve causal **why**;
* use canonical domain terminology; consult `CONTEXT.md` only when that terminology is not already established;
* do not store Category, Implementation, Routing Anchors, `last_updated`, `linked_docs`, file inventories, call chains, or dependency lists.

Use inline `source:` citations for entity-document relationships.

Do not claim stronger implementation certainty than the evidence supports.

Use `$wiki-lint` for whole-wiki health/conflict/drift auditing.

Use `$wiki-synthesize` manually for higher-inference recurring-pattern analysis; it is report-only.

---

## Agent Skills

### Internal Skill Composition

When a skill prescribes another repository skill as internal composition:

1. Do not use the session skill list or tool registry to determine whether the child exists.
2. Resolve the child directly from `.agents/skills/<skill-name>/SKILL.md`.
3. Read that `SKILL.md` and execute its procedure as prescribed internal composition.
4. `disable-model-invocation: true` and `allow_implicit_invocation: false` do not prohibit prescribed parent → child composition.
5. Report the child unavailable only when its repository `SKILL.md` is absent or unreadable.

### Workflow Project tracking

The public Polaris GitHub Project is an operational projection, not workflow authority.

Every formal lifecycle owner must carry an explicit **Project Reconciliation** step in its own `SKILL.md`. That local step identifies the artifacts affected by the transition, supplies their desired base lifecycle projection, and invokes `$project-tracking` as prescribed internal composition **after** the authoritative tracker/repository transition succeeds and **before** Human Handoff or ordinary return.

This applies to `$wayfinder`, `$to-specs`, `$to-tickets`, `$implement-ticket`, `$verify-spec`, `$review-spec`, `$spec-merge-cleanup`, and `$architecture-remediation`.

This section establishes the global invariant; it is not a substitute for the lifecycle owner's local call-site instruction. If one transition changes multiple artifacts, the owning skill must synchronize every affected artifact in one reconciliation set.

Follow `.agents/skills/project-tracking/WIRING.md` for the cross-skill call contract and `$project-tracking` for projection mechanics. Internal helpers return their result to the lifecycle owner; independent verifiers do not synchronize Project state. Project synchronization failure is projection drift and must never roll back or rewrite the authoritative workflow transition or suppress an otherwise-authorized downstream handoff.

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
