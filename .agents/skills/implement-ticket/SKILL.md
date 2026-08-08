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

### Entity wiki guard

Before making any file edits in this step, invoke the `/wiki-sync`
skill's audit (steps 1-4): map the change to its entity, load the
target and any referenced entities, and check for invariant
conflicts. This satisfies AGENTS.md's rule that source code
modification is always preceded by a `/wiki-sync` audit — do not treat
this as optional because the ticket already describes the intended
change; the audit still runs.

* If `/wiki-sync`'s trivial-diff exemption applies (the ticket is
  formatting/comment-only, or a pure rename with no cited anchor
  path), the audit may be skipped per that exemption.
* If the audit finds no conflict, or finds no entity coverage for
  this boundary, proceed with implementation.
* If the audit finds a conflict between the ticket's intended change
  and a stated invariant, halt before editing any files. Treat this
  with the same severity as a branch-guard mismatch: report the
  conflicting invariant, the entity page it lives on, and do not
  resolve it unilaterally. Implementation resumes only once the
  conflict has been deliberately resolved — either the invariant is
  confirmed outdated, or the ticket's approach is adjusted.

After implementation is complete, apply `/wiki-sync`'s step 6: update
the relevant entity page if the change altered a structural boundary
or invariant (not on every edit).

If the ticket's changes include creating, editing, or reclassifying
any non-ADR file under `docs/` — not just source code — also apply
`/wiki-sync`'s "Docs-change trigger" after that change: an edit to an
existing `doc_class: current` file triggers the staleness check; a
newly created `doc_class: current` or `doc_class: proposed` file, or
a document promoted to `doc_class: current`, triggers the
invariant/Planned check instead. This is distinct from the pre-edit
audit above — a ticket can trigger any combination of these depending
on what it touches.

If the ticket's changes include creating a new ADR, or changing an
existing ADR's `status` field, also apply `/wiki-sync`'s "ADR-change
trigger" after that change — checking whether the new or changed
decision belongs on an entity page as an invariant, a Planned entry,
or a signal that an existing citation is now stale. This is
independent of the docs-change trigger above, since ADR lifecycle
(`status`) uses a different mechanism than `doc_class`.

Within this workflow, do not let `/wiki-sync` perform its own separate
commit for any of these triggers — stage any resulting entity page
diff and the corresponding `wiki/log.md` line, and let step 5 below
include them in the single ticket commit. The "never write one
without the other" pairing invariant still holds; it is satisfied by
both landing in the same commit as the change that motivated them,
not by a standalone wiki commit.

### Implementation scope

* Implement only the work described by the provided ticket.
* For Spec Review remediation tickets, implement the root invariant described by
  the ticket, not merely the first cited symptom, hunk, or helper. Auditing and
  fixing sibling surfaces/reference kinds named by the root blocker is in scope;
  unrelated cleanup remains out of scope.
* Respect the ticket's acceptance criteria and blocking assumptions.
* Use the `/coding-standards` skill to guide implementation.
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

A DB-affecting ticket is not complete if a required targeted PostgreSQL-backed
test skipped only because `POLARIS_TEST_DATABASE_URL` or an equivalent local
service setting was absent. Follow `/database-migrations` and `/verify-code` to
derive safe local env from repo-local configuration, start only the required
authorized Docker service when needed, and rerun the exact targeted test.

## 3. Verify the implementation

Once the implementation is complete, but before committing or closing the ticket, invoke the `/verify-code` skill to verify the implementation of the ticket.

Default ticket verification must be targeted.

* Run only targeted checks unless the user explicitly authorizes broad verification for the current task.
* Do not escalate from targeted tests to full-suite tests, whole-repo type checks, whole-repo lint checks, full coverage runs, or service-dependent integration suites without explicit user authorization, even if those commands are already approved by the shell permission system.
* Approved shell command prefixes are execution permissions only. They are not task-specific authorization to broaden scope.
* If the Polaris command guard blocks a broad verification command, treat that refusal as final for the ticket unless the owner explicitly authorizes the exact proposed broad command in the current task. Do not bypass the guard through real executable backups, absolute virtualenv paths, or alternate Python module entrypoints.
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

1. Commit the completed ticket work to the current branch using the `/conventional-commits` skill. If the entity wiki guard staged an entity page update and `wiki/log.md` line, include them in this same commit — do not split them into a separate commit.
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
* Entity wiki status: whether the pre-edit `/wiki-sync` audit found a
  conflict (and how it was resolved); whether any non-ADR `docs/`
  file was created, edited, or reclassified and, if so, which
  docs-change check applied (staleness, or invariant/Planned) and its
  result; whether any ADR was created or had its `status` changed
  and, if so, the ADR-change trigger's result; which entity or
  entities (if any) were updated for any of these reasons; and
  whether the update was included in the ticket commit.
* The commit created.
* Whether the push succeeded.
* For database-affecting tickets: the `/database-migrations` result, migration
  file strategy, active database apply/reset status, migration-contract tests,
  and DB-backed integration tests. State explicitly whether required DB checks
  passed, were owner-deferred, or remain unresolved. A skip caused only by
  missing local env/service setup is unresolved verification, not a pass.
* The targeted verification that was run and its result.
* Any broader verification that the user explicitly authorized and its result.
* Which broad checks were not run, including full-suite tests, whole-repo mypy, whole-repo lint, or coverage when applicable.
* Whether the ticket was successfully closed.
