---
name: implement-ticket
description: "Implement work based on a single ticket."
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Implement Ticket

Implement one ticket, verify it, commit it to its declared branch, push it, and close it only when its required work is proven complete.

## 1. Read the Ticket and Verify Its Branch

Before modifying files, read the full ticket and locate its **Ticket branch**.

Capture the parent Spec when present.

If the ticket has **Architecture context**, capture affected entities and governing ADR/doc references as routing context. `$wiki-sync` still owns current source consistency.

If the ticket has a **Root blocker** or belongs to a `Spec Review`, also read the parent Spec and latest Spec Review state. Capture:

* Root Blocker ID and invariant;
* affected sibling surfaces/reference kinds;
* production-path obligations;
* every acceptance-matrix cell the ticket carries;
* previously satisfied Root Blockers and the surfaces/contracts they govern.

The ticket's **Ticket branch** is authoritative.

### Branch Guard

* A declared branch must exactly match the current branch.
* Do not create, switch, rename, or repair it.
* `None` skips branch enforcement.
* A missing field halts.
* Detached `HEAD` never satisfies a declared branch.

```bash
EXPECTED_TICKET_BRANCH="<Ticket branch value>"
CURRENT_BRANCH=$(git branch --show-current)

if [ "$CURRENT_BRANCH" != "$EXPECTED_TICKET_BRANCH" ]; then
  echo "❌ Wrong branch for this ticket."
  echo "Expected: $EXPECTED_TICKET_BRANCH"
  echo "Current:  ${CURRENT_BRANCH:-<detached HEAD>}"
  exit 1
fi
```

Run this before any file mutation.

Then capture:

```bash
TICKET_BASELINE=$(git rev-parse HEAD)
```

This is the ticket verification anchor only, not the Spec baseline.

## 2. Implement the Ticket

### Living Entity Wiki Guard

For substantive source changes, invoke `$wiki-sync` before editing when the Living Entity Wiki exists.

Use Architecture context only as a routing hint. `$wiki-sync` owns entity routing, source consistency, Strict Invariants, Rejected Approaches, and blocking `[source-conflict]`.

A material decision establishes or changes a durable invariant, canonical owner/path, architectural boundary, dependency direction, or lifecycle responsibility.

Choose the simplest conforming implementation for ordinary local choices.

If `$wiki-sync` or implementation exposes unresolved architecture, do not resolve it locally.

Architecture blockers include:

* unresolved material architecture decisions;
* blocking `[source-conflict]` among applicable authorities;
* current authority invalidating architecture required by the ticket.

Collect every independent blocker at the stopping point. De-duplicate symptoms of the same underlying question.

Halt with:

> ⚠️ **Implementation is blocked by unresolved architecture.**
>
> Please run:
>
> ```
> $architecture-remediation - <Current Ticket Title> (<Ticket URL>) — <concise blocker-set summary>
> ```
>
> **Architecture blockers:**
>
> 1. **<question or conflict>**
>
>    * Evidence: <concise discovery context>
>    * Material consequence: <ownership/path, boundary, dependency direction, lifecycle responsibility, source conflict, or other consequence>
>    * Governing context: <affected entities / ADRs / docs>

Do not propose an architectural resolution.

After substantive implementation, invoke `$wiki-sync` again. Update wiki entities only when durable knowledge changed.

### Documentation and ADR Changes

When applicable:

* `$to-doc` — new non-ADR document;
* `$classify-doc` — classify/reclassify/relocate an existing non-ADR;
* `$wiki-sync` — after substantive changes to `docs/current/` or `docs/proposed/`;
* `$to-adr-doc` — ADR creation, proposed-body changes, or lifecycle changes.

Do not duplicate those workflows here.

### Wiki Commit Ownership

When `$implement-ticket` is the parent, `$wiki-sync` must not commit separately.

Include substantive wiki changes and the matching semantic `wiki/log.md` entry in the ticket commit.

Do not modify `wiki/log.md` when no durable knowledge changed.

### Implementation Scope

* Implement only the ticket.
* For Spec Review remediation, implement the **root invariant**, not merely cited symptoms.
* Named sibling surfaces/reference kinds and production paths are in scope.
* Any additional manifestation of the same Root Blocker invariant discovered on an in-scope surface belongs to this ticket; fix it here.
* A regression introduced against a protected previously satisfied root also belongs to this ticket; fix it here rather than deferring it.
* Respect acceptance criteria and blocking assumptions.
* Use `$tdd` at applicable pre-agreed seams.
* Use `$format-code`.
* Use `$coding-standards`.
* Avoid unrelated cleanup.

### Database Change Guard

Invoke `$database-migrations` for database-affecting work, including:

* SQLAlchemy models;
* Alembic migrations;
* PostgreSQL repositories;
* persistence serializers/contracts;
* tests dependent on PostgreSQL schema objects.

Let `$database-migrations` own migration strategy and DB-backed verification.

A required PostgreSQL test skipped because local setup is absent remains unresolved.

## 3. Verify the Implementation

Invoke `$verify-code` with `TICKET_BASELINE`.

Default verification is targeted.

* Do not automatically run full-suite tests, repository-wide typing/lint, full coverage, or unrelated integration suites.
* Shell permission does not authorize broader verification.
* Do not bypass repository command guards.

If optional broader verification appears useful after required targeted checks, ask the user first.

If required verification fails:

* fix failures within ticket scope;
* rerun affected checks;
* do not commit, push, or close while required verification remains unresolved.

### Spec Review Root Closure Gate

For a Spec Review remediation ticket, targeted verification must prove the **entire Root Blocker obligation**, not just the changed seam or enumerated symptoms.

Required proof includes:

* the named production path;
* every carried acceptance-matrix cell;
* affected sibling surfaces/reference kinds;
* at least one regression test that would fail for the root or a named symptom;
* fail-closed cases where relevant to reconstruction, provenance, readiness, persistence, or observability.

Tests spanning the root's production path or sibling surfaces are **targeted ticket verification**, not optional broad verification.

### Root Invariant Sweep

Before declaring the Root Blocker proven, search the contract surface governed by its invariant for other ways the same violation can occur.

Inspect relevant:

* constructors/factories and defaults;
* producers and persistence/result boundaries;
* adapters/facades;
* callers and consumers;
* named sibling surfaces;
* tests representing those paths.

Use repository search first, then read only relevant surrounding code.

The sweep is bounded by the Root Blocker invariant and affected contract surface; it is not permission for unrelated cleanup.

If the sweep finds another in-scope manifestation:

* fix it within this ticket;
* extend targeted regression proof as needed;
* rerun affected checks;
* do not defer it to another remediation ticket.

The Root Blocker invariant is authoritative over the current acceptance-cell enumeration.

### Previously Satisfied Root Preservation

A Spec Review remediation ticket must not regress a previously satisfied Root Blocker.

Before closure, compare the ticket's modified production paths/contracts against previously satisfied roots from the same Spec Review.

A satisfied root becomes a **protected root** when the ticket changes a surface it governs, including the same:

* production path;
* façade/service/repository;
* typed contract or evidence object;
* adapter/persistence boundary;
* canonical owner;
* explicitly named sibling surface.

Do not protect unrelated roots merely because they belong to the same Spec Review.

For every protected root:

1. identify its applicable existing regression/acceptance proof;
2. rerun only the proof affected by the current change;
3. confirm the root still satisfies its invariant.

Protected-root checks are targeted ticket verification, not optional broad verification.

If the current ticket regresses a protected root:

* keep the current ticket open;
* fix the regression within this ticket;
* rerun the current-root and affected protected-root proof;
* do not defer the regression into a new remediation ticket.

### Closure Reconciliation

After verification, the Root Invariant Sweep, and protected-root checks:

* reconcile every carried acceptance cell as `proven` or `unproven`;
* record every protected root as `preserved` or `regressed`.

A passing local/helper test is insufficient when it does not prove the invariant at the required production boundary.

If any carried cell is `unproven`, any known manifestation remains violated, or any protected root is regressed:

* keep the ticket open;
* continue fixing within this ticket when possible;
* do not commit/push/close as completed work.

If proof cannot be completed because of an external/environmental blocker, report it and leave the ticket open.

## 4. Re-Verify the Branch Before Committing

Immediately before committing, verify **Ticket branch** again.

```bash
EXPECTED_TICKET_BRANCH="<Ticket branch value>"
CURRENT_BRANCH=$(git branch --show-current)

if [ "$CURRENT_BRANCH" != "$EXPECTED_TICKET_BRANCH" ]; then
  echo "❌ Branch changed during ticket implementation."
  echo "Expected: $EXPECTED_TICKET_BRANCH"
  echo "Current:  ${CURRENT_BRANCH:-<detached HEAD>}"
  exit 1
fi
```

Skip when **Ticket branch** is `None`.

On failure, do not commit, push, close, or automatically switch branches with uncommitted work.

## 5. Commit and Push

After required verification and any Spec Review closure gates succeed:

1. verify the branch;
2. commit with `$conventional-commits`;
3. include owned wiki changes in the same commit;
4. push:

```bash
git push -u origin HEAD
```

If commit or push fails, do not close the ticket.

After push, capture ticket commits:

```bash
git log --reverse --format='%h — %s' "$TICKET_BASELINE"..HEAD
```

Report short SHA and subject.

## 6. Close the Ticket

Close only when:

* implementation is complete;
* required targeted verification succeeded;
* for Spec Review remediation:

  * every carried Root Blocker acceptance cell is proven;
  * the Root Invariant Sweep found no remaining known in-scope violation;
  * every protected previously satisfied root remains preserved;
* any explicitly authorized broader verification succeeded;
* the branch invariant holds;
* commit succeeded;
* push succeeded.

Never close a Spec Review remediation ticket with an `unproven` carried cell, known root violation, or regressed protected root.

For GitHub tickets, close only after all gates pass.

## 7. Handoff

Report:

* implementation completed;
* Architecture context and any divergence;
* for Spec Review remediation:

  * current Root Blocker ID and invariant;
  * sibling surfaces/reference kinds audited;
  * production path exercised;
  * Root Invariant Sweep scope/result;
  * proof status for every carried acceptance cell;
  * protected roots identified and preservation result;
* ticket branch;
* `$wiki-sync` pre/post result and wiki changes;
* documentation/ADR activity;
* `$database-migrations` result when applicable;
* targeted verification;
* authorized broader verification, if any;
* broad checks not run;
* each ticket commit as `<short SHA> — <commit subject>`;
* push result;
* worktree state;
* ticket closure state.

Any required verification, acceptance cell, invariant sweep, or protected-root preservation result that remains unresolved keeps the ticket open.
