---
name: implement-ticket
description: "Implement work based on a single ticket."
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Implement Ticket

Implement the work described by a single ticket, verify it, commit it to the ticket's declared branch, push it, and close the ticket when all required checks succeed.

---

## 1. Read the Ticket and Verify Its Branch

Before modifying any files, read the full ticket provided by the user and locate its **Ticket branch** field.

If the ticket has a `Root blocker` section or says it is part of a `Spec Review` issue, also read the parent spec and the parent Spec Review issue before editing.

Capture:

* root blocker ID;
* root invariant;
* affected sibling surfaces/reference kinds;
* acceptance-matrix cells the ticket is expected to prove.

This root context is part of the ticket scope. Do not treat it as optional background.

The ticket's `Ticket branch` value is authoritative for the branch on which this ticket must be implemented.

All tickets belonging to the same spec share the same branch.

### Branch Guard

* If **Ticket branch** contains a branch name, the currently checked-out Git branch MUST exactly match that value before implementation begins.
* Do not automatically create, switch, rename, or otherwise repair the branch here.
* `$to-tickets` owns spec-branch creation and selection.
* A mismatch is a safety failure that halts implementation.
* If **Ticket branch** is `None`, dedicated branch enforcement was explicitly disabled. Skip the exact branch comparison.
* If **Ticket branch** is missing, halt rather than guessing.
* Do not derive a branch from:

  * ticket number;
  * parent issue;
  * current branch;
  * naming convention.

For a declared branch, perform an exact check equivalent to:

```bash id="6r7elc"
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

---

## 2. Implement the Ticket

### Living Entity Wiki Guard

Use the Living Entity Wiki lifecycle defined by `AGENTS.md`, `wiki/_schema.md`, and the owning wiki/document skills.

Do not reproduce or reinterpret `$wiki-sync` internals here.

---

### Source-Code Changes

If the ticket includes a **substantive source-code change**, invoke `$wiki-sync` before editing source code.

`$wiki-sync` owns:

* routing the change through `wiki/index.md`;
* loading the relevant entity knowledge;
* evaluating authoritative-source consistency;
* checking `[source-conflict]`;
* checking applicable Strict Invariants;
* checking relevant Rejected Approaches;
* identifying unresolved entity-boundary conditions.

The ticket's existence does not exempt the change from this audit.

#### Trivial Diff

If `$wiki-sync` determines its trivial-diff exemption applies, the pre-change audit may be skipped according to that skill.

Do not reproduce the exemption criteria here.

#### Blocking Findings

If `$wiki-sync` surfaces a condition that requires resolution before implementation — including:

* `[source-conflict]`;
* a proposed change that violates an active Strict Invariant;
* a matching Rejected Approach whose reasoning still applies;
* another explicit stop condition defined by `$wiki-sync`;

halt before modifying source code.

Report the finding and do not resolve architectural authority unilaterally.

Implementation may resume only after the underlying conflict or decision has been deliberately resolved.

---

### Post-Code `$wiki-sync`

After substantive source-code implementation is complete, invoke `$wiki-sync` again for the post-change evaluation.

It owns determining whether the implementation:

* changed or established a Strict Invariant;
* realized an accepted decision previously marked `accepted, implementation pending`;
* established a qualifying Rejected Approach;
* surfaced or resolved an Open Question;
* changed entity topology or Boundary Rationale;
* produced no durable wiki knowledge.

Do not update an entity merely because its code was touched.

A successful implementation technique is not independently wiki-worthy unless it produced one of the durable outcomes defined by `$wiki-sync`.

---

### Non-ADR Document Changes

If the ticket requires creating a **new non-ADR document** under `docs/`, use `$to-doc`.

Do not manually choose a folder/name and then retrofit classification afterward.

If the ticket requires classification, reclassification, relocation, or naming correction of an **existing non-ADR document**, use `$classify-doc`.

If the ticket substantively edits an existing `docs/current/` or `docs/proposed/` document without moving it, invoke `$wiki-sync` after the edit.

`$wiki-sync` owns:

* re-evaluating existing inline `source:` citations;
* detecting newly introduced entity-level claims;
* updating affected `Strict Invariants` or `Planned` content where appropriate;
* evaluating `[source-conflict]` before ordinary drift repair.

Do not use or introduce:

```text id="cxj8e2"
Doc-Class:
doc_class:
linked_docs
```

Non-ADR classification is derived from folder placement.

---

### ADR Changes

Use `$to-adr-doc` whenever the ticket:

* creates an ADR;
* substantively edits an ADR while it remains `proposed`;
* changes an ADR lifecycle status.

Do not modify ADR lifecycle outside `$to-adr-doc`.

That skill owns:

* allowed status transitions;
* content mutability;
* historical immutability;
* supersession;
* reconsideration;
* ADR-triggered `$wiki-sync`.

Do not assume:

```text id="7ephaj"
accepted ADR = implemented architecture
```

`$wiki-sync` determines whether an accepted decision:

* is immediately effective;
* is already realized;
* remains `accepted, implementation pending`.

---

### Entity Topology Changes

If implementation reveals or deliberately causes an entity:

* creation/promotion;
* rename;
* split;
* merge;
* removal;
* material scope change;
* Boundary Rationale change;

use `$wiki-sync`.

Do not manually edit entity topology independently of that skill.

---

### Wiki Mutation Commit Ownership

Within `$implement-ticket`, `$wiki-sync` must not create a separate standalone commit.

If a substantive wiki mutation occurs:

* stage the affected entity/index changes;
* stage the matching semantic `wiki/log.md` entry;
* include both in the ticket's normal commit.

If `$wiki-sync` determines no durable wiki knowledge changed:

* do not modify `wiki/log.md`;
* do not create a wiki-only commit.

The requirement is that each substantive wiki mutation and its semantic log entry land atomically, not that `$wiki-sync` own the commit.

---

### Implementation Scope

* Implement only the work described by the ticket.
* For Spec Review remediation tickets, implement the root invariant described by the ticket, not merely the first cited symptom, hunk, or helper.
* Auditing and fixing sibling surfaces/reference kinds named by the root blocker is in scope.
* Unrelated cleanup remains out of scope.
* Respect ticket acceptance criteria and blocking assumptions.
* Use `$coding-standards` to guide implementation.
* Use `$tdd` where possible at pre-agreed seams.
* Use `$format-code` during implementation where necessary.
* Avoid unrelated cleanup or scope expansion unless required to complete the ticket correctly.

---

### Database Change Guard

If the ticket changes any database-affecting surface, invoke `$database-migrations` before treating implementation as complete.

Database-affecting surfaces include:

* SQLAlchemy model changes;
* Alembic migration changes;
* new or changed PostgreSQL-backed repositories;
* persistence serializers;
* durable persistence contracts;
* tests whose acceptance depends on a PostgreSQL schema object.

`$database-migrations` owns:

* schema strategy;
* migration-file selection;
* local database application;
* stale-revision remediation;
* database-backed migration/integration verification.

Do not skip it because the code change is otherwise small.

A DB-affecting ticket is not complete if a required targeted PostgreSQL-backed test skipped only because `POLARIS_TEST_DATABASE_URL` or equivalent local service configuration was absent.

Follow `$database-migrations` and `$verify-code` to:

* derive safe local environment from repository-local configuration;
* start only the required authorized Docker service when needed;
* rerun the exact targeted test.

---

## 3. Verify the Implementation

Once implementation is complete, but before committing or closing the ticket, invoke `$verify-code`.

Default ticket verification must be targeted.

* Run only targeted checks unless the user explicitly authorizes broad verification for the current task.

* Do not escalate from targeted tests to:

  * full-suite tests;
  * whole-repo type checks;
  * whole-repo lint checks;
  * full coverage runs;
  * service-dependent broad integration suites

  without explicit user authorization.

* Approved shell-command prefixes are execution permissions only. They are not task-specific authorization to broaden scope.

* If the Polaris command guard blocks a broad verification command, treat that refusal as final unless the owner explicitly authorizes the exact proposed broad command.

* Do not bypass the guard through:

  * executable backups;
  * absolute virtualenv paths;
  * alternate Python module entrypoints.

If broader verification seems useful after targeted verification, stop and ask:

```text id="xwn8nv"
I have completed targeted verification. Do you want me to run broader verification?
Proposed command: ...
```

Do not run the proposed broad command until the user says yes.

If targeted verification fails:

* do not commit;
* do not push;
* do not close the ticket;
* fix failures within ticket scope;
* rerun targeted verification.

### Spec Review Verification

For Spec Review remediation tickets:

* targeted verification must prove the production path named by the root blocker;
* a unit test of a helper, validator, serializer, or mapper is insufficient by itself unless that seam is demonstrably the production boundary;
* add or run at least one regression test that would have failed for:

  * the root blocker; or
  * a named child symptom.

Include missing/stale/substituted/tampered/fail-closed cases when the invariant concerns:

* reconstruction;
* provenance;
* readiness;
* persistence;
* observability.

In the final handoff, report targeted verification separately from broad verification.

State explicitly when the following were not run:

* full suite;
* whole-repo mypy/type checks;
* whole-repo lint;
* coverage.

---

## 4. Re-Verify the Ticket Branch Before Committing

Immediately before creating the ticket commit, re-read the ticket's **Ticket branch** value and verify the branch invariant again.

If **Ticket branch** is not `None`:

```bash id="1dt6a2"
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

* do not commit;
* do not push;
* do not close the ticket;
* do not automatically switch branches with uncommitted work present;
* report the mismatch so it can be resolved deliberately.

If **Ticket branch** is `None`, skip the exact branch comparison.

---

## 5. Commit and Push

After targeted verification succeeds and the branch invariant has been confirmed:

1. Commit the completed ticket work to the current branch using `$conventional-commits`.

   If a Living Entity Wiki mutation occurred, include:

   * entity/index changes;
   * matching `wiki/log.md` semantic entry

   in this same ticket commit.

   Do not split them into a standalone wiki commit.

2. Push the current branch to `origin` and establish its upstream if necessary:

```bash id="5ucdhk"
git push -u origin HEAD
```

Do not use a bare:

```bash id="31j4pm"
git push
```

for this workflow.

A newly created spec branch may not yet have an upstream.

If the commit or push fails, do not close the ticket.

---

## 6. Close the Ticket

Close the ticket only after all of the following are true:

* ticket implementation is complete;
* required targeted verification succeeded;
* any broader verification explicitly requested by the user succeeded, if applicable;
* ticket branch invariant is satisfied unless **Ticket branch** is `None`;
* work was successfully committed;
* commit was successfully pushed.

For a GitHub-backed ticket, use the configured GitHub tooling to close the issue only after those conditions are satisfied.

Do not close the ticket merely because implementation or verification completed locally.

---

## 7. Handoff

Report:

* what was implemented;

* for Spec Review remediation tickets:

  * root blocker ID;
  * root invariant addressed;
  * sibling surfaces/reference kinds audited;
  * root acceptance cells still unproven or intentionally deferred;

* ticket branch used, or `None` if dedicated branch enforcement was disabled;

* Living Entity Wiki status:

  * whether a source-code pre-change `$wiki-sync` audit ran or was exempt;
  * relevant entity/entities;
  * whether `[source-conflict]`, invariant conflict, or Rejected Approach was encountered;
  * result of the post-code `$wiki-sync` evaluation;
  * whether any accepted implementation-pending decision was realized;
  * whether any entity topology change occurred;
  * whether a substantive wiki mutation occurred;
  * whether that mutation and its `wiki/log.md` entry were included in the ticket commit;

* document lifecycle activity:

  * any new non-ADR document created through `$to-doc`;
  * any existing non-ADR document changed through `$classify-doc`;
  * any substantive `docs/current/` or `docs/proposed/` edit and its `$wiki-sync` result;

* ADR lifecycle activity:

  * any ADR creation;
  * proposed ADR body edit;
  * ADR status transition;
  * resulting `$wiki-sync` outcome through `$to-adr-doc`;

* commit created;

* whether push succeeded;

* for database-affecting tickets:

  * `$database-migrations` result;
  * migration-file strategy;
  * active database apply/reset status;
  * migration-contract tests;
  * DB-backed integration tests;
  * whether required DB checks passed, were owner-deferred, or remain unresolved;

* targeted verification run and result;

* any broader verification explicitly authorized by the user and its result;

* broad checks not run, including where applicable:

  * full suite;
  * whole-repo mypy/type checks;
  * whole-repo lint;
  * coverage;

* whether the ticket was successfully closed.

A test skipped solely because required local database/service setup was missing remains **unresolved verification**, not a pass.
