---
name: implement-ticket
description: "Implement work based on a single ticket."
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Implement Ticket

Implement the work described by a single ticket, verify it, commit it to the ticket's declared branch, push it, and close the ticket when all required checks succeed.

## 1. Read the Ticket and Verify Its Branch

Before modifying any files, read the full ticket and locate its **Ticket branch** field.

Capture the parent spec reference from the ticket when present.

If the ticket has an **Architecture context** section, capture its affected entities and governing ADR/doc references. Treat these as routing context, not duplicated architectural authority; `$wiki-sync` must still evaluate the current sources.

If the ticket has a `Root blocker` section or belongs to a `Spec Review` issue, also read the parent spec and parent Spec Review issue. Capture the root blocker ID, invariant, affected sibling surfaces/reference kinds, and acceptance-matrix cells the ticket is expected to prove.

The ticket's `Ticket branch` is authoritative. All tickets belonging to the same spec share the same branch.

### Branch Guard

* If **Ticket branch** contains a branch name, the currently checked-out branch MUST exactly match it before implementation begins.
* Do not automatically create, switch, rename, or repair the branch. `$to-tickets` owns spec-branch creation and selection.
* If **Ticket branch** is `None`, skip dedicated branch enforcement.
* If the field is missing, halt rather than deriving a branch from the ticket, parent issue, current branch, or naming convention.
* A detached `HEAD` never satisfies a declared branch.

For a declared branch:

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

This check MUST occur before editing, formatting, generating, deleting, or otherwise modifying project files.

After the branch guard succeeds and before modifying files, capture the ticket verification baseline:

```bash
TICKET_BASELINE=$(git rev-parse HEAD)
```

Keep this baseline for the current ticket implementation. It is a verification anchor only; do not write it to the ticket or treat it as the spec baseline.

## 2. Implement the Ticket

### Living Entity Wiki Guard

If the ticket includes substantive source-code changes and the Living Entity Wiki exists, invoke `$wiki-sync` before editing.

Use any ticket **Architecture context** as a routing hint, but let `$wiki-sync` own entity routing, source consistency, Strict Invariant checks, Rejected Approaches, and any blocking `[source-conflict]`.

A decision is material when it establishes or changes a durable invariant, canonical owner or path, architectural boundary, dependency direction, or lifecycle responsibility.

Ordinary local implementation choices where the viable options conform to current architectural authority are not material. Choose the simplest conforming option and continue.

If `$wiki-sync` or implementation exposes one or more unresolved architecture blockers, do not resolve them locally.

This includes:

* an unresolved material architectural decision;
* a blocking `[source-conflict]` among applicable authorities;
* current architectural authority invalidating architecture the ticket depends on.

Collect every independent blocker discovered at the stopping point. Preserve distinct questions/conflicts rather than collapsing them into one, but do not split multiple evidence examples of the same underlying blocker.

Halt with a **Human Handoff Intercept** instructing the user to invoke `$architecture-remediation`.

Preserve the discovery context so the next workflow does not have to rediscover it. For each blocker include:

* concise unresolved question or conflict;
* evidence establishing it;
* why it blocks architecture or implementation;
* affected entities and governing ADR/doc references already known.

Do not propose or imply an architectural resolution.

Use:

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
>    * Material consequence: <ownership/path, boundary, dependency direction, lifecycle responsibility, source conflict, or other blocking consequence>
>    * Governing context: <affected entities / ADRs / docs when known>
> 2. **<question or conflict>**
>
>    * ...

After substantive implementation, invoke `$wiki-sync` again and let it determine whether any durable entity knowledge changed.

Do not update the wiki merely because code was touched or an implementation technique succeeded.

### Documentation and ADR Changes

If the ticket also changes repository documentation:

* use `$to-doc` for a new non-ADR document;
* use `$classify-doc` for classification, reclassification, or relocation of an existing non-ADR document;
* invoke `$wiki-sync` after substantive edits to existing `docs/current/` or `docs/proposed/` documents;
* use `$to-adr-doc` for ADR creation, proposed ADR body edits, or ADR lifecycle changes.

Do not manually reproduce document classification, ADR lifecycle, or wiki synchronization logic inside this workflow.

### Wiki Commit Ownership

When `$implement-ticket` is the parent workflow, `$wiki-sync` must not create a separate commit.

If a substantive wiki mutation occurs, include the affected wiki files and matching semantic `wiki/log.md` entry in the ticket commit.

If no durable wiki knowledge changed, do not modify `wiki/log.md`.

### Implementation Scope

* Implement only the work described by the ticket.
* For Spec Review remediation tickets, fix the root invariant, not merely the first cited symptom.
* Auditing and fixing named sibling surfaces/reference kinds is in scope; unrelated cleanup is not.
* Respect acceptance criteria and blocking assumptions.
* Use `$tdd` where appropriate at pre-agreed seams.
* Use `$format-code`.
* Use `$coding-standards`.
* Avoid unrelated cleanup or scope expansion unless required for correctness.

### Database Change Guard

If the ticket changes a database-affecting surface, invoke `$database-migrations` before treating implementation as complete.

This includes:

* SQLAlchemy models;
* Alembic migrations;
* PostgreSQL-backed repositories;
* persistence serializers or durable persistence contracts;
* tests that depend on PostgreSQL schema objects.

Let `$database-migrations` own migration strategy, local database application, stale-revision handling, and DB-backed verification.

A required PostgreSQL-backed test skipped solely because local environment or service setup was absent is unresolved verification, not a pass.

## 3. Verify the Implementation

After implementation, but before committing or closing the ticket, invoke `$verify-code` with `TICKET_BASELINE` as the ticket verification baseline.

Default ticket verification is targeted.

* Run only targeted checks unless the user explicitly authorizes broader verification.
* Do not escalate automatically to full-suite tests, whole-repo type checks, whole-repo lint, full coverage, or broad service-dependent integration suites.
* Shell-command permission does not imply task-specific authorization to broaden verification.
* Do not bypass repository command guards using alternate executable paths or module entrypoints.

If broader verification appears useful after targeted checks, ask:

> I have completed targeted verification. Do you want me to run broader verification? Proposed command: ...

Do not run it without approval.

If targeted verification fails:

* do not commit;
* do not push;
* do not close the ticket;
* fix failures within ticket scope and rerun the targeted checks.

### Spec Review Verification

For Spec Review remediation tickets:

* targeted verification must exercise the production path named by the root blocker;
* a helper/unit test alone is insufficient unless that seam is the actual production boundary;
* add or run at least one regression test that would have failed for the root blocker or a named child symptom;
* include fail-closed cases where relevant to reconstruction, provenance, readiness, persistence, or observability.

In the handoff, distinguish targeted checks from any broader verification and state which broad checks were not run.

## 4. Re-Verify the Branch Before Committing

Immediately before committing, re-read **Ticket branch** and verify it again.

If it is not `None`:

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

If this fails:

* do not commit;
* do not push;
* do not close the ticket;
* do not automatically switch branches with uncommitted work present;
* report the mismatch.

## 5. Commit and Push

After targeted verification succeeds and the branch invariant is confirmed:

1. Commit the completed ticket work using `$conventional-commits`.
2. Include any substantive wiki mutation and matching `wiki/log.md` entry in that same commit.
3. Push and establish upstream if necessary:

```bash
git push -u origin HEAD
```

Do not use bare `git push` for this workflow.

If commit or push fails, do not close the ticket.

## 6. Close the Ticket

Close the ticket only when:

* implementation is complete;
* required targeted verification succeeded;
* any explicitly authorized broader verification succeeded;
* the branch invariant is satisfied unless **Ticket branch** is `None`;
* the commit succeeded;
* the push succeeded.

For GitHub-backed tickets, use the configured GitHub tooling only after all conditions are satisfied.

## 7. Handoff

Report:

* what was implemented;
* architecture context used and any divergence found;
* for Spec Review work:

  * root blocker ID;
  * root invariant addressed;
  * sibling surfaces/reference kinds audited;
  * acceptance cells still unproven or deliberately deferred;
* ticket branch used;
* `$wiki-sync` pre/post result and any wiki mutation;
* any `$to-doc`, `$classify-doc`, or `$to-adr-doc` activity;
* `$database-migrations` result when applicable;
* targeted verification and result;
* broader verification explicitly authorized, if any;
* broad checks not run;
* commit created;
* push result;
* whether the ticket was closed.

Any required DB check skipped solely because local setup was missing remains unresolved verification.
