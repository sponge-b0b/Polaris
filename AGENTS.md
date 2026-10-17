# AGENTS.md

## Purpose and Authority

These are the operating rules for coding agents working on Polaris.

`AGENTS.md` is primarily **prescriptive agent policy**: how an agent must work in this
repository. It is not a second authoritative copy of project architecture.

At the start of a task:

1. Match claims to the correct authority:
   * code, configuration, executable checks, and relevant tests outside `legacy/` →
     current implementation reality;
   * accepted CCL contracts → canonical material delivery semantics where a CCL contract
     exists;
   * accepted ADRs outside `legacy/` → active architectural rationale/decisions not
     superseded by a canonical CCL field;
   * active architecture documents outside `legacy/` → current architectural description;
   * an active root `wiki/entities/`, when present → derived architectural knowledge;
   * `legacy/v0_1/` → historical donor/reference material only.
2. If applicable authorities materially disagree, surface `[source-conflict]`. Do not
   silently choose whichever source makes the task easiest.
3. Merge these repository rules with narrower user instructions for the active task.

Where a material semantic coordinate is represented by CCL, downstream prose may explain
or project it but may not override it.

### Proactive Attention Duty

At any time during analysis, planning, architecture, design, specification, ticketing,
implementation, verification, review, remediation, or ordinary repository work,
**surface material concerns promptly when you notice them**.

The current task is the immediate work surface, not the boundary of Attention. Maintain a
Polaris-wide meta-level Attention posture across materially implicated product intent,
domain semantics, architecture, authority, code, persistence, APIs, tests, docs/wiki,
workflow state, and upstream/downstream contracts.

Use this materiality threshold:

> **Would a competent architect who understood Polaris as a whole want this brought to
> their attention now?**

Material concerns include correctness defects, unresolved semantic/design choices,
misleading vocabulary, weak/duplicated abstractions, hidden assumptions, source conflicts,
workflow defects, stale/competing truth, scope leakage, missing proof, or a materially
better/safer approach.

Attention is **report-only authority**. It does not authorize mutation, scope expansion,
architecture changes, or lifecycle-owner override.

When a concern appears:

1. state the observation and material consequence;
2. identify governing authority when known;
3. determine whether it belongs to the current obligation, invalidates the current path,
   or requires separate routing/deferment;
4. follow existing authority when it resolves the question;
5. if a material choice remains unresolved, use the owning workflow's fail-closed route;
6. do not silently expand scope to fix unrelated concerns.

Formal `$attention` checkpoints remain required at the boundaries named by their owning
skills, including `$wayfinder`, `$to-specs`, `$to-tickets`, `$architecture-remediation`,
`$implement-ticket`, `$verify-ticket-closure`, `$verify-spec`, and `$review-spec`.

### Collaborative Judgment

Polaris agents contribute substantive engineering judgment rather than merely executing
instructions mechanically:

```text
think broadly → speak broadly → discuss material choices → act within the agreed mandate
```

The mandate boundary governs mutation, not thought or recommendation.

### Mandate Boundary and Structural Mutation Guard

An instruction authorizes the smallest correct change necessary to satisfy it. It does
not implicitly authorize adjacent cleanup, refactoring, generalization, reorganization, or
architecture work.

Before broadening a repository mutation ask:

> **Can the explicit requirement be satisfied correctly without this additional structural
> or design change?**

If yes, the additional change needs explicit owner authorization.

Material structural changes include creating/deleting/renaming/moving/splitting/merging
canonical policy/process/architecture artifacts; introducing wrappers/base files/helper
architectures or new organization conventions; or relocating authority/responsibility.

Before persisting repository-wide workflow/process/governance changes reconcile:

```text
Authorized files/surfaces: <n>
Actual changed files/surfaces: <n>
Unauthorized structural additions/deletions/renames: 0
Optional design changes performed without approval: 0
```

Required participation in an already-authoritative shared invariant is necessary
correctness work, not scope expansion. If the shared invariant itself is unresolved,
fail closed rather than invent it.

### Design-to-Implementation Boundary

Implementation executes frozen design; it is not a design phase.

Before implementation, every materially consequential product/domain/architecture/public/
persistence/temporal/authority/failure/downstream contract must already be determined.
Use this test:

> Could two reasonable implementations satisfy the written requirement while establishing
> materially different material behavior/contracts?

If yes, work is not implementation-ready.

Semantically equivalent private mechanics remain implementation-owned.

Workflow consequences:

* `$wayfinder` may not declare route clear with unresolved material semantics;
* `$to-specs` projects material semantics from exact CCL and owns stable private/test/
  exclusion planning cells;
* `$to-tickets` decomposes the frozen Spec contract and does not design semantics;
* `$implement-ticket` must classify material questions as authorized contract,
  implementation-equivalent mechanic, or design gap;
* verifiers/reviewers may falsify implementation against frozen contracts but may not
  redefine the contract universe.

### Spec Governance Mode

Spec governance is orthogonal to Spec validity/lifecycle. Every Spec resolves exactly one
mode from one bounded read of the parent Spec:

```text
Wayfinder-managed
Independent
```

This is a repository-wide supersession rule.

* valid `wayfinder-source` or `wayfinder-remediation` marker(s) → Wayfinder-managed with
  exactly those governing maps;
* neither marker → Independent;
* malformed/contradictory/ambiguous Spec-local provenance → governance drift, fail closed.

`$to-specs` owns keeping Spec-local governance provenance correct. The temporary
`$to-remediation-specs` helper may repair only unambiguous forward/local provenance; it
is not a semantic owner.

Downstream workflows must not reverse-search unrelated Wayfinders/Project history merely
to prove an unmarked Spec Independent. Independent Specs never acquire a Wayfinder simply
because they enter ticketing, implementation, verification, review, remediation, or
completion.

Native GitHub `blocked by` relationships remain dependency truth. For Spec dependencies:

| Consumer | Blocker | Semantic owner |
| --- | --- | --- |
| Wayfinder-managed | same-lineage Wayfinder-managed | `$to-specs` |
| Wayfinder-managed | different-lineage Wayfinder-managed | `$project-delivery-management` |
| either endpoint Independent | any Spec | `$to-specs` |

`$github-issue-dependencies` owns only native relationship mechanics.

### Candidate-Bound Verification Evidence Reuse

Deterministic/technical proof is reusable while exact candidate inputs, check scope/config,
and material external prerequisites remain unchanged. Phase transitions alone do not
invalidate a passing result.

After mutation rerun only checks whose input universe may have changed. When uncertain,
run the smallest check that resolves the uncertainty.

A helper returning a still-valid passing result must return that evidence to its parent;
the parent does not rerun it merely to satisfy duplicate phase wording.

### Canonical Contract Consumption

This is the repository-wide supersession rule for `$spec-contract`, `$to-tickets`,
`$verify-spec`, `$verify-spec-closure`, `$review-spec`, and downstream consumers of a
CCL-backed software Spec.

The material semantic chain is:

```text
accepted CCL assertion
        ↓
Spec OBL-* projection
        ↓
Ticket/implementation/verification/review consumption
```

`$spec-contract` is deterministic. Its complete contract-cell universe is:

* `OBL-*` — material semantics; payload is exact CCL address set;
* `IMP-*` — stable private/mechanical planning obligation;
* `TEST-*` — stable proof/test obligation;
* `EXC-*` — stable exclusion/guardrail.

Problem/Solution/User Story/Architecture Impact/Further Notes prose is human context and
never creates a hidden acceptance cell. If that prose reveals a missing material semantic
requirement, route it to `$to-specs` / the semantic owner rather than interpreting it
locally.

Do not rebuild Source Unit Inventories, classify arbitrary prose as normative/non-
normative, invent `NORM-*` cells, or reconstruct architecture obligation universes from
ADR/wiki/code prose.

Every contract cell has deterministic identity/hash. Narrative-only changes may alter the
Spec Body Hash without changing the Spec Contract Hash.

`$to-tickets` routes every executable cell exactly once and preserves every exclusion in
`ticket-coverage-manifest:v2`. Exact deterministic coverage replaces independent semantic
decomposition certification for ordinary CCL-backed Specs.

`$verify-spec` and `$verify-spec-closure` independently prove implementation conformance
to the same frozen cells. Independence means independent falsifiers/evidence, not a new
interpretation of contract membership.

`$review-spec` independently challenges Standards, Spec conformance, and Architecture
realization against the same frozen cells. It may surface:

* an in-contract implementation/test/standards defect;
* an exact cell-routing defect owned by `$to-tickets`;
* a contract/planning gap owned upstream by `$to-specs` / semantic authority.

A verifier/reviewer must never repair a gap by adding a new semantic obligation itself.

Legacy Spec Review remediation may temporarily retain Root Blocker compatibility state,
but every executable remediation obligation must map to exact current Spec cells and the
frozen finding falsifier. Compatibility state does not create semantics.

### Non-Semantic Workflow-Policy Synchronization

A verified/reviewed semantic candidate anchor may remain valid when its branch later
receives a non-semantic workflow-policy synchronization from default branch only when all
of these are proven fail-closed:

1. semantic anchor is an ancestor of current Spec branch tip;
2. anchor→tip paths are workflow/process authority surfaces only (`.agents/skills/`,
   `docs/process/`, or root `AGENTS.md`);
3. each changed branch blob equals current default-branch policy;
4. no product/test/migration/config/architecture/Spec/CCL/TCM/ticket/review-semantic
   surface changed;
5. policy delta changes workflow mechanics only, not product/acceptance semantics;
6. mutable external authorities used by the prior receipt remain valid.

When policy changes `$spec-contract` or related construction rules, current deterministic
validation must reproduce the receipt-bound Spec Body Hash and Spec Contract Hash.

If all predicates pass, the old receipt HEAD remains semantic anchor and the current tip
is the authorized delivery tip. Otherwise ordinary exact-candidate invalidation applies.

### `$implement-ticket` Parent / Independent Verifier Boundary

`$implement-ticket` implements and technically validates a ticket candidate;
`$verify-ticket-closure` independently certifies closure. The parent must not perform a
second semantic-certification workflow merely to dispatch the verifier.

Before dispatch carry a concise Implementation Evidence Index:

```text
Candidate state: <identity>
Changed/implemented surfaces: <compact groups>
Evidence: <ticket cell/criterion group -> implementation/evidence pointer>
Applicable technical checks: <check -> PASS + candidate identity>
Known unresolved implementation failures: 0
Known unresolved design/architecture blockers: 0
```

For ordinary CCL-backed tickets, exact assigned Spec cells/CCL addresses are the ticket
semantic contract. Remediation tickets may additionally carry current compatibility Root
Blocker/finding preservation state. A verifier may independently prove those contracts;
it may not invent a broader architecture universe.

### Domain Vocabulary

Do not preload `CONTEXT.md`. Read it only when a domain term is ambiguous/contested/new,
canonical vocabulary is required, an entity page needs terminology, or `$domain-modeling`
is running. Context compaction alone is not a reason to reread it.

`CONTEXT.md` is canonical domain vocabulary; avoid duplicating it here.

### Greenfield / Legacy Boundary

Canonical greenfield implementation lives under `src/polaris/`.

`legacy/v0_1/` is donor/reference material only. New Polaris code/tests/config/migrations/
tools/runtime must not import, wrap, execute through, or otherwise depend on `legacy/`.
Reuse requires independently established current need/authority and deliberate transplant
into the greenfield boundary.

Do not treat legacy ADR/docs/wiki/manifests/tests/code as current authority.

---

## Coding Conduct

When changing source code use `$coding-standards`. Its requirements are mandatory.
Project-specific semantic/architecture rules come from current authoritative contracts/
architecture, not names, legacy implementation, or implementation accidents.

Do not duplicate coding-standard policy here.

## Secrets

Never place credentials, passwords, tokens, or full authenticated connection strings in
source, tests, plans, or documentation.

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

No pytest command may launch until the selected test scope's external-service prerequisites
have been identified and, when applicable, verified ready.

Classify the exact selected greenfield scope from current root configuration/tests/
fixtures. For multi-file/directory scope use the union of prerequisites. Verify required
services/environment before pytest; do not use pytest startup/timeouts/skips as readiness
probes.

The classification may be reused while selected scope/configuration/fixtures/service
topology remain unchanged. A lightweight readiness check may refresh service state.

`POLARIS_BROAD_VERIFY_AUTHORIZED` must be supplied only to the individual command that
requires it; never export/persist it globally.

---

## Dependencies and Shell

`uv.lock` is committed resolved dependency authority. Keep it synchronized with
`pyproject.toml` for intentional dependency changes.

For canonical project-declared Python tooling/runtime use:

```text
uv run --locked <command>
```

Do not substitute ambient same-named tools. Use `uv add/remove/lock` or intentional
unlocked sync only for authorized dependency management. `uvx` is for genuinely one-off
external tools. Plain `python` is allowed for intentionally standard-library-only repo
helpers.

Missing/stale `uv.lock` is a dependency-state defect; do not casually regenerate/delete
it.

Standard read-only shell discovery/diagnostics are allowed.

---

## Context and Discovery Efficiency

Treat context/discovery as engineering resources. Use the smallest authoritative context
and smallest discovery operation sufficient for the current material question; broaden
when evidence remains ambiguous/incomplete.

Efficiency never authorizes skipping correctness/closure evidence. Durable manifests,
receipts, known IDs/markers, CCL addresses, and exact cell mappings are recovery indexes;
use them instead of lifecycle archaeology.

Avoid dumping broad raw histories/payloads when exact sections/IDs/hashes or deterministic
reduction suffice. Reuse still-valid discovery while its target/authority remains current.

---

## Repository Analysis

Select discovery tools by question, not mandatory sequence:

* `$repowise` — behavioral location/status/hotspots/history/dead-code triage;
* `$codebase-memory-mcp` — exact structural symbol/caller/dependency analysis;
* `$codegraph` — implicit/dynamic runtime paths;
* `$graphify` — broad exploratory relationships across code/docs/decisions;
* `rg` / direct reads — exact literals/config/Markdown/policy/ground truth.

Combine only when distinct material questions require it. Exclude `legacy/` from current
greenfield analysis unless donor/reference inspection is explicitly needed.

---

## Database Migrations

Migration lifecycle policy is owned by `$database-migrations`. Use it before creating or
modifying migrations. Do not duplicate it here.

---

## ADRs

`$to-adr-doc` owns ADR creation/lifecycle. In CCL-backed decisions, the ADR Decision
projection may not override the accepted CCL contract.

Use `$to-adr-doc` for ADR creation, proposed-body substantive edits, and status changes.

---

## Non-ADR Documents

Use `$to-doc` for new non-ADR documents and `$classify-doc` for classification,
reclassification, relocation, or naming correction. Active root `wiki/_schema.md`, when
present, owns classification/naming policy.

Do not store `doc_class`/`Doc-Class:` metadata, leave project-owned docs loose under
`docs/`, or manually move classified docs without reference/authority reconciliation.

---

## Living Entity Wiki

Legacy wiki under `legacy/v0_1/wiki/` is historical only.

When active root wiki exists, `$wiki-sync` owns substantive source/architecture/ADR/entity
synchronization. Start routing from `wiki/index.md`; use code graph tools only when needed.
Entity pages preserve causal why, canonical vocabulary, and inline `source:` citations;
they do not become a second implementation/file inventory.

Use `$wiki-lint` for whole-wiki health/conflict/drift and `$wiki-synthesize` manually for
higher-inference report-only analysis.

---

## Agent Skills

### Internal Skill Composition

When a skill prescribes another repository skill as internal composition:

1. resolve `.agents/skills/<skill-name>/SKILL.md` directly;
2. read and execute it as prescribed;
3. `disable-model-invocation: true` / `allow_implicit_invocation: false` do not prohibit
   prescribed parent→child composition;
4. report unavailable only when its repository `SKILL.md` is absent/unreadable.

### Independent Semantic Child Result Admission

Dispatch is not a verdict. Before consuming a fresh independent verifier/reviewer result,
require the actual terminal payload, exact frozen candidate/contract identity match,
required witness fields, current immutability/freshness, and no parent-substituted verdict.

Pending/missing/malformed/contradictory/identity-mismatched results are unresolved/invalid,
never PASS/FAIL. Use only the owning workflow's explicit replacement rule if the original
child context is unavailable.

### Workflow Project Tracking

The public Polaris GitHub Project is an eventually consistent operational projection, not
workflow authority.

Routine lifecycle transitions do **not** invoke `$project-tracking`. Authorized projection
boundaries are:

1. Spec completion — `$spec-merge-cleanup` reconstructs and batch-syncs the completed
   lineage;
2. explicit human-requested board reconciliation;
3. separately authorized bootstrap/migration.

Do not create pending-update shadow state. `$project-delivery-management` persists
canonical focus/dependency truth immediately but does not imply board refresh.

Project drift never rewrites authoritative repository/tracker state or suppresses an
otherwise-authorized lifecycle handoff.

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

This repository uses root `CONTEXT.md` and optional root `docs/adr/` for the current
single-context domain-doc layout. See `docs/agents/domain.md`.
