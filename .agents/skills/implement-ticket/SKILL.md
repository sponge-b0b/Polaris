---
name: implement-ticket
description: "Implement work based on a single ticket."
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Implement Ticket

Implement one ticket, verify it, commit it to its declared branch, push it, and close it only when its required work is proven complete.

## Session Independence

Assume no prior conversational or agent-session state.

Recover every correctness-critical input from the explicit invocation, repository, and durable tracker artifacts before acting. Prior-session summaries or remembered conclusions are routing context only and must not substitute for required durable evidence.

If required durable state cannot be recovered, report the missing artifact rather than infer or recreate it from memory.

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

### Completion Persistence

Continue until the ticket completes all required gates or a genuine blocking condition defined by this skill prevents further progress.

Substantial remaining work, elapsed time, perceived context/token pressure, or a desire to end the current turn are **not valid stopping conditions**.

Do not voluntarily return partial work merely because the task is long. If work remains and no defined blocker exists, continue.

If execution is externally interrupted, preserve the current work and leave the ticket open for continuation; do not present partial state as completed work.

### Living Entity Wiki Guard

For substantive source changes, invoke `$wiki-sync` before editing when the Living Entity Wiki exists.

Use Architecture context only as a routing hint. `$wiki-sync` owns entity routing, source consistency, Strict Invariants, Rejected Approaches, and blocking `[source-conflict]`.

A material decision establishes or changes a durable invariant, canonical owner/path, architectural boundary, dependency direction, or lifecycle responsibility.

Choose the simplest conforming implementation for ordinary local choices.

### Architecture vs. Implementation Test

Missing implementation of accepted architecture is not an architecture blocker.

Before routing to `$architecture-remediation`, determine whether applicable accepted authority already establishes enough durable semantics to implement the requirement, including where relevant:

* canonical ownership;
* typed authority/input sources;
* identity/key semantics;
* lifecycle ordering;
* boundaries and dependency direction;
* failure behavior.

If those durable choices are already established, continue implementation.

Missing classes, methods, configuration objects, registration APIs, producers, repository methods, bootstrap wiring, or similar concrete mechanisms are implementation work unless choosing them would establish or change a durable architectural semantic.

Route to `$architecture-remediation` only when proceeding would require inventing or changing a durable owner, authority source, canonical key/path, boundary, dependency direction, lifecycle rule, or equivalent architectural semantic.

The absence of code implementing an accepted architectural responsibility is unfinished implementation, not unresolved architecture.

If `$wiki-sync` or implementation exposes genuinely unresolved architecture after this test, do not resolve it locally.

Architecture blockers include:

* unresolved material architecture decisions;
* blocking `[source-conflict]` among applicable authorities;
* current authority invalidating architecture required by the ticket;
* implementation requiring a durable architectural choice not determined by accepted authority.

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
* Do not claim an acceptance criterion is proven unless concrete source/test evidence supporting it can be identified.

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
* DI/bootstrap/composition;
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

Before closure, compare modified production paths/contracts against previously satisfied roots from the same Spec Review.

A satisfied root becomes a **protected root** when the ticket changes a surface it governs, including the same:

* production path;
* façade/service/repository;
* typed contract or evidence object;
* adapter/persistence boundary;
* canonical owner;
* explicitly named sibling surface.

Protected roots are identified by **Root Blocker ID**, not prior remediation-ticket number.

Do not protect unrelated roots merely because they belong to the same Spec Review.

For every protected root:

1. identify its applicable existing regression/acceptance proof;
2. rerun only proof affected by the current change;
3. confirm the root still satisfies its invariant.

Protected-root checks are targeted ticket verification, not optional broad verification.

If the current ticket regresses a protected root:

* keep the current ticket open;
* fix the regression within this ticket;
* rerun current-root and affected protected-root proof;
* do not defer the regression into another remediation ticket.

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

### Proposed Root Closure Evidence

For a Spec Review remediation ticket, assemble concrete proposed closure evidence before independent verification.

Record:

* Root Blocker ID and invariant;
* production path exercised;
* Root Invariant Sweep surfaces inspected and result;
* every carried acceptance cell and its concrete proof;
* every protected root checked and its proof/result;
* regression/production tests used as proof;
* required database/integration verification when applicable.

A generic test count, “targeted verification passed,” mocked lower-level seam, or unsupported assertion that the invariant was swept is insufficient.

If any required proof cannot be stated concretely, treat that obligation as `unproven` and keep the ticket open.

### Independent Root Closure Verification

For every Spec Review remediation ticket, `$implement-ticket` must invoke `$verify-root-closure` in a **fresh read-only subagent** after targeted verification and proposed closure evidence are complete, but before commit, push, closure-evidence persistence, or ticket closure.

Do not perform the independent certification yourself.

Pass enough context for the verifier to recover:

* current ticket and parent Spec;
* latest Spec Review / Root Blocker Ledger;
* `TICKET_BASELINE`;
* current uncommitted implementation state;
* proposed Root Closure Evidence;
* applicable Architecture context.

The verifier independently derives the required Root Invariant Sweep and protected roots. Do not constrain it to the implementer's claimed coverage.

#### FAIL

`ROOT CLOSURE: FAIL` is blocking.

* keep the ticket open;
* fix every implementation/proof failure within ticket scope;
* apply **Architecture vs. Implementation Test** to any architecture-blocker candidate;
* rerun affected targeted checks;
* reconcile proposed closure evidence;
* invoke a **fresh** `$verify-root-closure` subagent again.

The parent may not override or downgrade a verifier failure.

#### PASS

Only `ROOT CLOSURE: PASS` permits a Spec Review remediation ticket to proceed toward commit.

Capture the verifier's:

* `TICKET_BASELINE`;
* `ROOT_CLOSURE_STATE`;
* acceptance proof;
* invariant-sweep result;
* protected-root result;
* targeted verification result.

Any implementation change after `PASS` makes the verdict stale and requires a fresh `$verify-root-closure`.

## 4. Re-Verify Before Committing

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

Skip branch enforcement when **Ticket branch** is `None`.

On failure, do not commit, push, close, or automatically switch branches with uncommitted work.

### Root Closure State Guard

For Spec Review remediation, recompute the verifier's worktree fingerprint immediately before commit:

```bash
CURRENT_ROOT_CLOSURE_STATE=$(
  {
    git diff --binary "$TICKET_BASELINE" --
    git ls-files --others --exclude-standard -z \
      | sort -z \
      | xargs -0 -r sha256sum
  } | sha256sum | awk '{print $1}'
)
```

Require:

```bash
test "$CURRENT_ROOT_CLOSURE_STATE" = "$ROOT_CLOSURE_STATE"
```

If it differs, the independent verdict is stale.

Do not commit. Rerun `$verify-root-closure` in a fresh read-only subagent against the new state.

## 5. Commit and Push

After all required verification and closure gates succeed:

1. verify the branch;
2. for Spec Review remediation, verify `ROOT_CLOSURE_STATE`;
3. commit with `$conventional-commits`;
4. include owned wiki changes in the same commit;
5. push:

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
* every required acceptance criterion has identifiable supporting evidence;
* required targeted verification succeeded;
* for Spec Review remediation:

  * every carried Root Blocker acceptance cell is proven;
  * the Root Invariant Sweep found no remaining known in-scope violation;
  * every protected previously satisfied root remains preserved;
  * `$verify-root-closure` returned `ROOT CLOSURE: PASS`;
  * the verified `ROOT_CLOSURE_STATE` remained unchanged through commit;
* any explicitly authorized broader verification succeeded;
* the branch invariant holds;
* commit succeeded;
* push succeeded.

### Persist Root Closure Evidence

Before closing a Spec Review remediation ticket, persist the independently verified Root Closure Evidence as a ticket comment.

Use a concise structure:

```markdown
## Root Closure Evidence

**Root:** RB-<n> — <invariant>
**Production path:** <production boundary exercised>
**Independent verification:** PASS

### Acceptance proof
- <cell>: proven — <concrete source/test evidence>

### Invariant sweep
- <surface>: clean/proven — <evidence>

### Protected roots
- RB-<n>: preserved — <proof>
- or None

### Verification
- <targeted regression/production/DB checks and result>

### Commits
- <short SHA> — <subject>
```

Use the independently verified results. Do not strengthen or replace them with unsupported parent-agent claims.

Include only applicable sections.

Do not close the ticket if this comment cannot be persisted.

Never close a Spec Review remediation ticket with:

* an `unproven` carried cell;
* known root violation;
* regressed or unproven protected root;
* missing or stale independent closure `PASS`;
* missing durable closure evidence.

For ordinary tickets, do not invoke `$verify-root-closure` or require a formal Root Closure Evidence comment. Identifiable acceptance/verification evidence in the normal implementation report is sufficient.

For GitHub tickets, close only after all gates pass.

## 7. Handoff

Report:

* implementation completed;
* Architecture context and any divergence;
* acceptance criteria and supporting evidence;
* for Spec Review remediation:

  * current Root Blocker ID and invariant;
  * sibling surfaces/reference kinds audited;
  * production path exercised;
  * Root Invariant Sweep scope/result;
  * proof status for every carried acceptance cell;
  * protected roots and preservation result;
  * `$verify-root-closure` verdict;
  * verified Root Closure Evidence comment persisted;
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

Any required verification, acceptance criterion, acceptance cell, invariant sweep, protected-root preservation, independent root-closure verification, or closure-evidence persistence that remains unresolved keeps the ticket open.
