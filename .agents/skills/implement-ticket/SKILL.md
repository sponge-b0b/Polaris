---
name: implement-ticket
description: "Implement work based on a single ticket."
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Implement Ticket

Implement the work described by a single ticket, verify it, commit it to the ticket's declared branch, push it, and close the ticket when all required checks succeed.

## 1. Read the ticket and verify its branch

Before modifying any files, read the full ticket provided by the user and locate its **Ticket branch** field.

If the ticket has a `Root blocker` section or says it is part of a `Spec Review`
issue, also read the parent spec and the parent Spec Review issue before editing.
Capture the root blocker ID, invariant, affected sibling surfaces/reference
kinds, and acceptance-matrix cells the ticket is expected to prove. This root
context is part of the ticket scope; do not treat it as optional background.

The ticket's `Ticket branch` value is authoritative for the branch on which this ticket must be implemented. All tickets belonging to the same spec share the same branch.

### Branch guard

* If **Ticket branch** contains a branch name, the currently checked-out Git branch MUST exactly match that value before any implementation work begins.
* Do NOT automatically create, switch, rename, or otherwise repair the branch here. `/to-tickets` owns spec-branch creation and selection. A mismatch is a safety failure that must halt implementation.
* If **Ticket branch** is `None`, dedicated branch enforcement was explicitly disabled for this ticket. Skip the exact branch comparison.
* If the **Ticket branch** field is missing, halt rather than guessing the intended branch. Do not fall back to deriving a branch from the ticket number, parent issue, current branch, or naming conventions.

For a declared branch, perform an exact check equivalent to:

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

A detached `HEAD` does not satisfy a declared ticket branch.

This check MUST happen before editing, formatting, generating, deleting, or otherwise modifying project files.

## 2. Implement the ticket

* Implement only the work described by the provided ticket.
* For Spec Review remediation tickets, implement the root invariant described by
  the ticket, not merely the first cited symptom, hunk, or helper. Auditing and
  fixing sibling surfaces/reference kinds named by the root blocker is in scope;
  unrelated cleanup remains out of scope.
* Use the identified standards source `CODING_STANDARDS.md` to guide implementation.
* Respect the ticket's acceptance criteria and blocking assumptions.
* Use the `/tdd` skill where possible, at pre-agreed seams.
* Use the `/format-code` skill during implementation where necessary.
* Avoid unrelated cleanup or scope expansion unless it is necessary to complete the ticket correctly.

### Database change guard

If the ticket changes any database-affecting surface, invoke the
`/database-migrations` skill before treating implementation as complete.
Database-affecting surfaces include:

* SQLAlchemy model changes.
* Alembic migration changes.
* New or changed PostgreSQL-backed repositories, persistence serializers, or
  durable persistence contracts.
* Tests whose acceptance depends on a PostgreSQL schema object.

The database migration workflow owns the schema strategy, the migration file
selection, local database application, stale-revision remediation, and
DB-backed migration/integration verification. Do not skip it because the code
changes are otherwise small.

## 3. Verify the implementation

Once the implementation is complete, but before committing or closing the ticket, invoke the `/verify-code` skill to verify the implementation of the ticket.

Default ticket verification must be targeted.

* Run only targeted checks unless the user explicitly authorizes broad verification for the current task.
* Do not escalate from targeted tests to full-suite tests, whole-repo type checks, whole-repo lint checks, full coverage runs, or service-dependent integration suites without explicit user authorization, even if those commands are already approved by the shell permission system.
* Approved shell command prefixes are execution permissions only. They are not task-specific authorization to broaden scope.
* If broader verification seems useful after targeted verification, stop and ask:

  `I have completed targeted verification. Do you want me to run broader verification? Proposed command: ...`

  Do not run the proposed broad command until the user says yes.
* If targeted verification fails, do not commit, push, or close the ticket. Fix failures that are within the ticket's scope and re-run the targeted verification.
* For Spec Review remediation tickets, targeted verification must prove the
  production path named by the root blocker. A unit test of a helper, validator,
  serializer, or mapper is not sufficient by itself unless the production path is
  also exercised or there is a documented reason that seam is the production
  boundary.
* For Spec Review remediation tickets, add or run at least one regression test
  that would have failed for the root blocker or a named child symptom. Include
  missing/stale/substituted/tampered or fail-closed cases when the root invariant
  concerns reconstruction, provenance, readiness, persistence, or observability.
* In the final handoff, report targeted verification separately from any broad verification. State when the full suite, whole-repo mypy, whole-repo lint, or coverage were not run.

## 4. Re-verify the ticket branch before committing

Immediately before creating the ticket's commit, re-read the ticket's **Ticket branch** value and verify the branch invariant again.

If **Ticket branch** is not `None`:

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

If this check fails:

* Do not commit.
* Do not push.
* Do not close the ticket.
* Do not automatically switch branches with uncommitted work present.
* Report the mismatch so it can be resolved deliberately.

If **Ticket branch** is `None`, skip the exact branch comparison.

## 5. Commit and push

After targeted verification succeeds and the branch invariant has been confirmed:

1. Commit the completed ticket work to the current branch using the `/conventional-commits` skill.
2. Push the current branch to `origin` and establish its upstream if necessary:

   ```bash
   git push -u origin HEAD
   ```

Do not use a bare `git push` for this workflow. A newly created spec branch may not have an upstream yet, and the first push must establish one.

If the commit or push fails, do not close the ticket.

## 6. Close the ticket

Close the ticket only after all of the following are true:

* The ticket implementation is complete.
* Required targeted verification succeeded.
* Any broader verification explicitly requested by the user succeeded, if applicable.
* The ticket branch invariant is satisfied, unless **Ticket branch** is `None`.
* The work was successfully committed.
* The commit was successfully pushed to the remote.

For a GitHub-backed ticket, use the configured GitHub tooling to close the issue only after those conditions are satisfied.

Do not close the ticket merely because implementation or verification completed locally.

## 7. Handoff

Report:

* What was implemented.
* For Spec Review remediation tickets: the root blocker ID, the root invariant
  addressed, sibling surfaces/reference kinds audited, and any root acceptance
  cells still unproven or intentionally deferred.
* The ticket branch used, or `None` if dedicated branch enforcement was disabled.
* The commit created.
* Whether the push succeeded.
* For database-affecting tickets: the `/database-migrations` result, migration
  file strategy, active database apply/reset status, migration-contract tests,
  and DB-backed integration tests. State explicitly if any required DB check
  skipped or could not run.
* The targeted verification that was run and its result.
* Any broader verification that the user explicitly authorized and its result.
* Which broad checks were not run, including full-suite tests, whole-repo mypy, whole-repo lint, or coverage when applicable.
* Whether the ticket was successfully closed.
