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

### Proactive Attention Duty

At any time during analysis, planning, architecture, design, specification, ticketing, implementation, verification, review, remediation, or ordinary repository work, **surface material concerns promptly when you notice them**. Do not wait for the user, a checklist, a failing test, or a later review to ask the question first.

The current task is the **immediate work surface, not the boundary of Attention**. Maintain a standing Polaris-wide meta-level Attention posture: while doing the work in front of you, continuously evaluate what the current observation implies for Polaris as a whole across materially implicated product intent, domain semantics, architecture, authority, code, persistence, APIs, tests, documentation, Living Entity Wiki knowledge, workflow skills, tracker/lifecycle/governance state, and upstream/downstream contracts.

Material concerns include, when applicable:

* likely correctness defects or missing failure boundaries;
* unresolved product, domain, architecture, identity, lifecycle, authority, temporal, persistence, or public-contract choices;
* ambiguous or misleading domain/public names;
* accidental coupling, duplicate meaning, weak typing, unnecessary complexity, or a suspicious abstraction/representation choice;
* behavior that passes current checks but appears inconsistent with authoritative intent;
* incomplete proof, hidden assumptions, source conflict, scope leakage, or workflow/process defects;
* architecture, domain language, code, persistence, APIs, docs, wiki, skills, tests, or tracker state no longer telling the same material story;
* duplicate or competing sources of truth, stale authority, or assumptions invalidated by a later decision;
* repeated local symptoms that indicate an earlier governing lifecycle, ownership, architecture, or workflow defect;
* technically valid work that is materially wrong for Polaris as a product;
* a materially better or safer approach or opportunity that the current path may be overlooking.

Use this materiality threshold:

> **Would a competent architect who understood Polaris as a whole want this brought to their attention now?**

If yes, surface it. If no, continue without distraction. Polaris-wide Attention is not a requirement to run a whole-repository audit after every edit; inspect the smallest broader surface necessary to test the material concern or consequence exposed by the current work.

Attention is **report-only authority**. Noticing or surfacing a concern does not authorize you to change product/design/architecture, expand scope, mutate repository/tracker state, override an owning workflow, or silently implement your preferred resolution.

When a concern appears:

1. state the observation and why it matters;
2. identify the governing authority when it is already known;
3. determine whether it belongs to the current obligation, invalidates the current path, or is a broader Polaris concern that requires separate routing/deferment;
4. if existing authority resolves it, follow that authority rather than redesigning it;
5. if it exposes a material unresolved choice, use the owning workflow's fail-closed/routing rule rather than choosing for convenience;
6. if it is valid but outside current scope, do not expand scope silently; use the established deferred-future-work capture policy when durable preservation is warranted.

Passing tests, satisfying an explicit checklist, or lacking authority to fix the concern does **not** excuse silence. The duty is to notice and speak up; change authority remains separate.

`$attention` is the reusable report-only skill for deliberate Attention sweeps. Every formal sweep inherits the Polaris-wide scope above; a workflow-specific checkpoint profile is an additional lens, never a boundary. The following checkpoints are prescribed internal composition even when the owning skill does not restate the global invariant:

* `$wayfinder` — before declaring the route clear or handing off downstream;
* `$to-specs` — before publishing/amending a Spec as implementation-ready;
* `$to-tickets` — before proposal-readiness certification/publication;
* `$architecture-remediation` — before bounded closure and downstream handoff;
* `$implement-ticket` — before first substantive mutation and again before freezing closure evidence;
* `$verify-ticket-closure` — during the independent adversarial sweep;
* `$verify-spec` — before integrated semantic certification is finalized;
* `$review-spec` — before review exit/handoff.

A formal Attention result does not create a new blocking authority. The owning workflow determines whether a surfaced concern is already resolved, blocking, deferred, or informational under its existing rules.

### Design-to-Implementation Boundary

Implementation executes frozen design; it is not a design phase.

Before implementation, every materially consequential product/domain/architecture/public/downstream contract must already be determined by authoritative durable sources. This includes, where applicable:

* identity representation and generation semantics;
* public domain/application type semantics and cross-component contracts;
* cardinality and ownership;
* lifecycle/state transitions and temporal interpretation;
* authority/provenance meaning;
* persistence-visible identity and reference contracts;
* externally observable failure meaning;
* any choice on which downstream components are expected to rely.

Use this test:

> Could two reasonable implementations satisfy the written requirement while establishing materially different public, product, domain, architecture, persistence, or downstream behavior/contracts?

If **yes**, the work is not implementation-ready. The choice must be resolved upstream; an implementation agent must not select one merely because it is convenient or conventional.

Semantically equivalent private mechanics remain implementation-owned, including ordinary helper decomposition, local algorithms/data structures with no contract consequence, local variable names, formatting, and equivalent test mechanics.

Workflow consequences:

* `$wayfinder` must not declare a route clear while a material architecture/design choice remains unresolved;
* `$to-specs` must require material design completeness, not merely architecture consistency or obligation coverage;
* `$to-tickets` decomposes frozen design and must not delegate material design choices to implementation;
* `$implement-ticket` must classify any material choice it encounters as `authorized contract`, `semantically equivalent mechanic`, or `design gap`; a `design gap` fails closed before that choice is implemented;
* `$verify-ticket-closure` must reject a candidate that introduces an unowned material design/public contract even when explicit tests pass;
* later integrated verification/review must surface cross-ticket design gaps that only become visible after composition.

### Spec Governance Mode

Spec governance is **orthogonal to Spec validity and lifecycle state**. Every Spec, and every downstream artifact whose delivery governance derives from that Spec, must resolve exactly one governance mode from durable tracker evidence before any Wayfinder- or project-delivery-dependent step:

```text
Wayfinder-managed
Independent
```

A Spec is **Wayfinder-managed** only when current durable evidence establishes one or more governing Wayfinders through canonical `wayfinder-source`, `wayfinder-remediation`, or reconciled `Spec Handoff` provenance.

A Spec is **Independent** only when exhaustive governance recovery establishes no Wayfinder governor and no evidence suggests missing, contradictory, or ambiguous Wayfinder provenance. Missing expected provenance is governance drift, not proof of independence.

This section is a repository-wide workflow hardening rule and **supersedes any narrower skill wording that unconditionally assumes a Spec has a governing Wayfinder**. In particular:

* any instruction to recover a governing Wayfinder, invoke `$project-delivery-management` `guard`/`reconcile`, require Wayfinder focus, or reconcile/close governing Wayfinders for a Spec or Spec-derived artifact applies **only** after that artifact's parent Spec is proven Wayfinder-managed, even if the local skill later omits the qualifier;
* an Independent Spec and its descendants never acquire, infer, or require a Wayfinder merely because they enter ticketing, implementation, verification, review, remediation, dependency handling, merge/cleanup, or Project reconciliation;
* Independent Specs do not participate in Wayfinder focus. Their authoritative Project Delivery State is `independent` while open, subject to their ordinary lifecycle and native blockers;
* if `$project-delivery-management` is invoked with an Independent Spec or a descendant whose only governing Spec is Independent, it must return `PROJECT DELIVERY: OUTSIDE OWNER` without mutation rather than treating the missing Wayfinder as ambiguous or creating one;
* `$to-remediation-specs` is intentionally Wayfinder-only. It is not the remediation path for an Independent Spec. Independent architecture remediation is owned by `$architecture-remediation`, which amends the existing Spec in place and then returns through `$to-tickets` for ticket reconciliation;
* native GitHub `blocked by` relationships remain the dependency truth for both governance modes. A closed blocker satisfies the existing edge; reopening it makes the edge blocking again.

Spec dependency semantic ownership is:

| Consumer Spec | Blocker Spec | Semantic owner |
| --- | --- | --- |
| Wayfinder-managed | Wayfinder-managed, same governing lineage | `$to-specs` |
| Wayfinder-managed | Wayfinder-managed, different governing lineages | `$project-delivery-management` |
| Independent | Independent | `$to-specs` |
| Independent | Wayfinder-managed | `$to-specs` |
| Wayfinder-managed | Independent | `$to-specs` |

`$github-issue-dependencies` owns only the authorized native relationship mechanics. When either endpoint is Independent, `$to-specs` validates the exact Spec-level semantic prerequisite, lowest accurate placement, cycle safety, and complete native blocker graph before delegating the mutation. Never promote an Independent-involved Spec dependency to a synthetic Wayfinder dependency.

A Wayfinder-managed Spec blocked by an Independent Spec remains governed by its existing Wayfinder; the narrower open Spec blocker makes the Spec non-actionable without making the Wayfinder itself dependent on or governed by the Independent Spec. If the map otherwise remains frontier-eligible, it may remain focused-but-stalled.

Governance mode is revalidated at every fresh human lifecycle entry and whenever durable provenance changes. It is never inferred from GitHub Project fields, labels other than canonical provenance mechanisms, issue age/order, branch names, conversation state, or the fact that a prior workflow happened to use or not use Wayfinder.

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

`POLARIS_BROAD_VERIFY_AUTHORIZED` must be supplied only for the individual command requiring authorization, for example `POLARIS_BROAD_VERIFY_AUTHORIZED=<task-specific-value> uv run --locked pytest ...`. Never export it globally or persist it into a shell/session environment.

---

## Dependencies and Shell

`uv.lock` is committed project state and is the resolved dependency source of truth for Polaris. Keep it synchronized with `pyproject.toml` when dependency declarations intentionally change.

For canonical Polaris Python development, verification, and runtime commands whose tools or dependencies are declared by the project, use:

```text
uv run --locked <command>
```

`--locked` is mandatory for ordinary execution because it verifies that `uv.lock` is current and fails rather than rewriting dependency state. `uv` may synchronize `.venv` or build/install Polaris as normal generated local environment state; `.venv` is not repository state.

Every canonical Python tool invoked this way must be declared in the applicable project dependency group and therefore represented in `uv.lock`. Do not rely on a same-named executable from ambient `PATH` as a substitute for locked project tooling.

Use `uv add`, `uv remove`, `uv lock`, or an intentional unlocked `uv sync` only for authorized dependency-management work. Commit the resulting `pyproject.toml` and `uv.lock` changes together when both change.

Use `uvx` only for genuinely one-off external Python tools that are not part of the Polaris development/runtime contract. Use plain `python` for repository helper scripts that are intentionally standard-library-only and do not require the Polaris environment.

Missing or stale `uv.lock` is a dependency-state defect for ordinary locked execution; do not delete, ignore, regenerate, or rewrite it as incidental verification cleanup.

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

The public Polaris GitHub Project is an operational projection, not workflow authority. **Authoritative repository/tracker state is immediate; Project projection is intentionally eventually consistent.**

Routine lifecycle transitions do **not** invoke `$project-tracking`. This repository-wide cadence rule explicitly supersedes narrower existing skill wording that still requires automatic Project synchronization after ordinary `$wayfinder`, `$to-specs`, `$to-tickets`, `$implement-ticket`, `$verify-spec`, `$review-spec`, `$architecture-remediation`, or internal `$project-delivery-management` transitions.

Project projection is authorized only at:

1. **Spec completion** — `$spec-merge-cleanup` reconstructs the complete completed-Spec lineage from current durable authority and invokes `$project-tracking` once for the whole reconciliation set before successful cleanup return;
2. **explicit human-requested board reconciliation** — the active workflow independently reconstructs the requested authoritative artifact universe and refreshes it in one batch;
3. **separately authorized bootstrap/migration** — one-time Project/schema setup may synchronize state under its own contract.

Do not create a pending-Project-update queue, flag, comment ledger, label, or other shadow registry. Missing Project membership or stale Project fields during active Spec work are expected projection lag and never substitute for or alter authoritative workflow state.

`$project-delivery-management` continues to persist canonical focus/dependency truth immediately. Focus, switch, parallel-focus, dependency mutation, guard, and deterministic reconciliation do not imply a board refresh unless the human explicitly requested one. A board refresh is a separate projection operation.

At the mandatory Spec boundary, `$spec-merge-cleanup` must not assume earlier skills kept the board current. It reconstructs the complete lineage from hierarchy, dependencies, receipts/checkpoints, issue state, provenance, and canonical project-delivery state, then lets `$project-tracking` add missing Project members and apply one batch of field deltas. Reconstruction is working state only; do not persist another projection registry.

Follow `.agents/skills/project-tracking/WIRING.md` for this cadence and `$project-tracking` for projection mechanics. Independent verifiers never synchronize Project state. `PROJECT TRACKING: DRIFT` never rolls back or rewrites authoritative workflow state or suppresses an otherwise-authorized downstream handoff.

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