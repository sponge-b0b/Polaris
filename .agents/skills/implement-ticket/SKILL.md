---
name: implement-ticket
description: "Implement work based on a single ticket."
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Implement Ticket

Implement one ticket, verify it, commit it to its declared branch, push it, and close it only when all required work is proven complete.

## Session Independence

Assume no prior session state.

Recover correctness-critical inputs from the invocation, repository, and durable tracker artifacts. Prior-session summaries are routing context only.

If required durable state cannot be recovered, report the missing artifact rather than infer it.

## 1. Read the Ticket and Guard the Branch

Read the full ticket and capture:

* **Ticket branch**
* **Ticket baseline**
* parent Spec
* Architecture context when present

For a Spec Review remediation ticket, also read the latest Spec Review state and capture:

* Root Blocker ID and invariant;
* affected sibling surfaces/reference kinds;
* production-path obligations;
* carried acceptance-matrix cells;
* previously satisfied roots governing affected surfaces/contracts.

### Branch Guard

A declared **Ticket branch** must exactly match the current branch before any file mutation.

* Do not create, switch, rename, or repair it.
* `None` skips enforcement.
* Missing field halts.
* Detached `HEAD` does not satisfy a declared branch.

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

### Ticket Baseline Guard

**Ticket baseline** is the durable per-ticket verification anchor, distinct from the Spec baseline.

It must be `Pending` or a full commit SHA.

If `Pending`:

1. require a clean worktree;
2. capture `git rev-parse HEAD`;
3. persist that full SHA into **Ticket baseline**;
4. re-read the ticket and require the value to match;
5. set `TICKET_BASELINE` to it.

Do this before file mutation.

If already a SHA:

```bash
git rev-parse "$TICKET_BASELINE^{commit}"
```

Use that exact value. Never recompute or overwrite it.

## 2. Implement

Continue until the ticket completes all required gates or reaches a defined blocker.

Elapsed time, remaining work, context pressure, task size, or partial progress are not valid stopping conditions.

**A partial implementation is not a defined blocker. If actionable in-scope work remains, continue the ticket in the current invocation.**

Whenever halting before completion, explicitly name the blocker and the workflow rule that requires or permits the halt.

### Invocation Termination

Do not emit a final response unless one of these states applies:

* **Completed** — all required commit, push, evidence, and closure gates completed;
* **Human Handoff** — this skill explicitly requires human authorization;
* **Hard Blocker** — a concrete external/environmental, branch, baseline, permission, required-tool, or persistence failure prevents further safe work.

Everything else is non-terminal.

In particular, partial progress, verification failure, `ROOT CLOSURE: FAIL`, corrective edits making a verdict stale, remaining actionable in-scope work, an open ticket, and `ROOT CLOSURE: PASS` before final lifecycle completion do not authorize stopping.

If none applies, continue the workflow.

### Living Entity Wiki Guard

For substantive source changes, invoke `$wiki-sync` before editing when the Living Entity Wiki exists.

Architecture context is routing context only. `$wiki-sync` owns entity routing, source consistency, Strict Invariants, Rejected Approaches, and blocking `[source-conflict]`.

### Architecture vs. Implementation

Missing realization of accepted architecture is implementation work, not an architecture blocker.

Before routing to architecture remediation, determine whether accepted authority already establishes the required durable semantics, including where applicable:

* canonical ownership;
* authority/input sources;
* identity/key semantics;
* lifecycle ordering;
* boundaries/dependency direction;
* failure behavior.

Missing classes, methods, configuration, registration, repository operations, producers, bootstrap wiring, or similar mechanisms are implementation work when those durable semantics are already resolved.

Route to `$architecture-remediation` only when proceeding requires inventing or changing a durable architectural semantic or applicable authorities genuinely conflict.

Collect every independent blocker and de-duplicate symptoms of the same question.

### Architecture Human Handoff Intercept

Do not invoke human-gated `$architecture-remediation` implicitly.

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
> 1. **<question/conflict>**
>
>    * Evidence: <concise evidence>
>    * Material consequence: <ownership/path/boundary/dependency/lifecycle/source conflict>
>    * Governing context: <entities / ADRs / docs>

Do not propose an architectural resolution.

After substantive implementation, invoke `$wiki-sync` again. Update wiki entities only when durable knowledge changed.

### Documentation / ADRs

When applicable:

* `$to-doc` — new non-ADR document;
* `$classify-doc` — classify/reclassify/relocate an existing non-ADR;
* `$wiki-sync` — substantive existing `docs/current/` or `docs/proposed/` changes;
* `$to-adr-doc` — ADR content or lifecycle.

Do not duplicate those workflows here.

### Wiki Commit Ownership

When `$implement-ticket` is parent, `$wiki-sync` must not commit separately.

Include substantive wiki changes and the matching `wiki/log.md` entry in the ticket commit.

### Scope

* Implement only the ticket.
* For Spec Review remediation, fix the **root invariant**, not merely cited symptoms.
* Named production paths and sibling surfaces are in scope.
* Any newly discovered manifestation of the same root on an in-scope surface belongs to this ticket.
* Any regression introduced against a previously satisfied root on an affected surface belongs to this ticket.
* Use `$tdd` at applicable pre-agreed seams.
* Use `$format-code`.
* Use `$coding-standards`.
* Avoid unrelated cleanup.

### Database Guard

Invoke `$database-migrations` for database-affecting work, including models, migrations, PostgreSQL repositories, durable serializers/contracts, and schema-dependent tests.

A required PostgreSQL check skipped because local setup is absent remains unresolved.

## 3. Verify

Invoke `$verify-code` with `TICKET_BASELINE`.

Verification is targeted by default.

Do not automatically run full-suite tests, repository-wide lint/type checks, coverage, or unrelated integration suites.

Do not claim an acceptance criterion is proven without identifiable supporting source/test evidence.

If required verification fails, fix it within ticket scope and rerun it. Do not commit, push, or close while required verification remains unresolved.

## Spec Review Root Closure

The following gates apply only to Spec Review remediation tickets.

### Root Closure Gate

Targeted verification must prove the **entire carried Root Blocker obligation**, not merely the changed seam or enumerated symptoms.

Required proof includes:

* named production path;
* every carried acceptance cell;
* affected sibling surfaces/reference kinds;
* regression proof that would fail for the root or a named symptom;
* relevant fail-closed behavior.

Production-path and sibling-surface checks required by the root are targeted ticket verification, not optional broad verification.

### Root Invariant Sweep

Before proposing closure, search the contract surface governed by the root for other manifestations of the same violation.

Inspect relevant:

* constructors/factories/defaults;
* producers and persistence/result boundaries;
* adapters/facades;
* callers/consumers;
* DI/bootstrap/composition;
* named sibling surfaces;
* representative tests.

**Search first, then read only relevant surrounding code.**

The sweep is bounded by the root invariant.

If another manifestation is found, fix and prove it within this ticket.

### Preserve Previously Satisfied Roots

Do not regress a previously satisfied Root Blocker.

A prior root becomes protected when this ticket changes a surface it governs, such as the same:

* production path;
* façade/service/repository;
* typed contract/evidence object;
* adapter/persistence boundary;
* canonical owner;
* named sibling surface.

For each protected root:

1. identify applicable existing regression/acceptance proof;
2. rerun only proof affected by this change;
3. confirm its invariant remains satisfied.

If regressed, fix it within this ticket and rerun both current-root and protected-root proof.

### Closure Reconciliation

Reconcile:

* every carried acceptance cell → `proven | unproven`;
* every protected root → `preserved | regressed`.

If any carried cell is unproven, known root violation remains, or protected root is regressed:

* keep the ticket open;
* continue fixing all actionable in-scope failures in the current invocation;
* do not return control merely to report partial remediation;
* do not proceed to Proposed Root Closure Evidence or root-closure verification.

### No Partial Root Stop

For a Spec Review remediation ticket, discovering additional in-scope root work during implementation, verification, reconciliation, or the Root Invariant Sweep means **continue the ticket**.

Remaining in-scope implementation or proof work is not itself a blocker.

Do not halt merely because:

* some root obligations are already proven;
* targeted tests pass for the implemented subset;
* substantial progress has been made;
* remaining root work is larger than expected;
* another in-scope manifestation was discovered;
* the ticket would remain open.

Halt before root completion only when further progress is actually prevented by:

* a required Human Handoff defined by this skill;
* unresolved material architecture requiring the Architecture Human Handoff;
* an external/environmental dependency that cannot be safely resolved here;
* a branch, baseline, permission, tool, or persistence failure that makes further work unsafe or impossible.

When halting for such a blocker, name the **exact blocker**, the remaining affected obligation, and why it prevents further in-scope work.

Absent such a blocker, continue until every carried root obligation is proven and Proposed Root Closure Evidence can be assembled.

### Proposed Root Closure Evidence

Before independent verification, assemble concrete evidence:

* Root Blocker ID and invariant;
* production path exercised;
* Root Invariant Sweep surfaces/results;
* every carried acceptance cell and proof;
* protected roots and proof/results;
* regression/production/DB checks used.

Generic test counts, mocked lower-level seams, or unsupported assertions are insufficient.

If required proof cannot be stated concretely because implementation or proof work remains actionable, continue the ticket under **No Partial Root Stop**.

If proof cannot be completed because of a permitted blocker, keep the ticket open and report that blocker explicitly.

### Root Closure Human Handoff Intercept

`$verify-root-closure` requires explicit human authorization.

For every Spec Review remediation ticket, after targeted verification and Proposed Root Closure Evidence are complete — but before commit, push, closure-evidence persistence, or ticket closure — halt.

Before halting, confirm the handoff explicitly contains:

* current ticket title and URL;
* Root Blocker ID and invariant;
* `TICKET_BASELINE`;
* production boundary/path exercised;
* concise Proposed Root Closure Evidence summary covering acceptance, invariant sweep, and protected-root/preservation state;
* the explicit verifier-dispatch authorization statement below.

Do not rely on preceding prose to satisfy these required handoff fields.

Emit the following handoff structure exactly. An implementation summary or verification summary may precede it, but none of the required fields or final authorization statement may be omitted, merged, paraphrased away, or left implicit:

> ⚠️ **Implementation is ready for independent Root Blocker closure verification.**
>
> Explicit human authorization is required before `$verify-root-closure` can run.
>
> Please run:
>
> ```
> $verify-root-closure - <Current Ticket Title> (<Ticket URL>)
> ```
>
> **Root:** <RB-n — invariant>
> **Ticket baseline:** <TICKET_BASELINE>
> **Production path:** <production boundary exercised>
> **Proposed closure:** <concise acceptance/sweep/protected-root summary>
>
> This invocation authorizes `$implement-ticket` to dispatch the independent verifier. It does **not** authorize the `$implement-ticket` main agent to perform certification itself.

The surrounding implementation report may contain additional evidence, test results, or changed surfaces, but it does not replace this lifecycle handoff.

Do not substitute a shorter or free-form request to run `$verify-root-closure`.

Then stop.

### Resume After Human Authorization

An explicit `$verify-root-closure` invocation received at this checkpoint is an **authorization event**, not a local procedure call.

Resume `$implement-ticket` at this checkpoint rather than restarting implementation discovery or executing `$verify-root-closure` in the main agent.

#### Verifier Dispatch Invariant

After authorization, the `$implement-ticket` main agent enters **dispatcher-only mode**.

It may only:

1. capture the exact candidate `ROOT_CLOSURE_STATE`;
2. spawn exactly one fresh verifier subagent;
3. wait for and receive its result;
4. validate verifier independence and candidate-state integrity;
5. consume a valid `PASS` or `FAIL`.

While in dispatcher-only mode, the main agent must not:

* perform root-closure source inspection or tracker recovery;
* run root-closure tests or checks;
* reason to or emit its own closure verdict;
* execute the `$verify-root-closure` procedure itself;
* repair findings before the verifier returns.

Capture the candidate state before spawning:

```bash
DISPATCH_ROOT_CLOSURE_STATE=$(
  {
    git diff --binary "$TICKET_BASELINE" --
    git ls-files --others --exclude-standard -z \
      | sort -z \
      | xargs -0 -r sha256sum
  } | sha256sum | awk '{print $1}'
)
```

Spawn exactly one **fresh verifier subagent** and pass only the explicit handoff inputs it requires:

* current ticket and parent Spec;
* latest Spec Review / Root Blocker Ledger;
* `TICKET_BASELINE`;
* current candidate implementation state;
* `DISPATCH_ROOT_CLOSURE_STATE`;
* Proposed Root Closure Evidence;
* applicable Architecture context.

The verifier independently derives the required Root Invariant Sweep and protected roots. Do not constrain it to the implementer's claimed coverage.

The verifier must execute `$verify-root-closure` as a **non-mutating leaf workflow**:

* it may read, search, inspect, and run non-mutating targeted checks;
* a discovered defect means `ROOT CLOSURE: FAIL`, never authorization to repair it;
* it must not modify repository, Git, tracker, or branch state;
* it must not invoke implementation/remediation workflows;
* it must not delegate or spawn another agent or subagent.

The main agent only consumes the verifier result; it never independently certifies root closure.

#### Verify Verifier Integrity

After the verifier returns, recompute:

```bash
POST_VERIFIER_ROOT_CLOSURE_STATE=$(
  {
    git diff --binary "$TICKET_BASELINE" --
    git ls-files --others --exclude-standard -z \
      | sort -z \
      | xargs -0 -r sha256sum
  } | sha256sum | awk '{print $1}'
)
```

A verifier result is valid only when:

* `POST_VERIFIER_ROOT_CLOSURE_STATE` equals `DISPATCH_ROOT_CLOSURE_STATE`;
* the verifier's `TICKET_BASELINE` equals the current `TICKET_BASELINE`;
* the verifier's `ROOT_CLOSURE_STATE` equals `DISPATCH_ROOT_CLOSURE_STATE`;
* no verifier mutation or delegation is reported or otherwise observed.

If any condition fails, discard the verdict. Do not treat it as `PASS` or `FAIL`.

A verifier that mutates or delegates has not performed valid root-closure verification.

Unauthorized verifier mutations are never automatically accepted as ticket implementation. They must either be safely reverted or explicitly adopted by the `$implement-ticket` implementation flow. If adopted, rerun applicable targeted verification, rebuild Proposed Root Closure Evidence, and return to the Root Closure Human Handoff Intercept for fresh authorization and a fresh verifier.

If the candidate state remains unchanged but the verifier delegated or otherwise violated independence, return directly to the Root Closure Human Handoff Intercept.

Each verification attempt requires fresh human authorization.

#### FAIL

`ROOT CLOSURE: FAIL` is non-terminal.

Exit dispatcher-only mode and resume implementation immediately.

Complete every actionable verifier finding before returning to the Root Closure Human Handoff Intercept.

Corrective edits making the failed verdict stale are expected and are not a stopping condition.

* keep the ticket open;
* fix every implementation/proof failure within ticket scope;
* apply **Architecture vs. Implementation** to architecture-blocker candidates;
* rerun affected targeted checks;
* rebuild Proposed Root Closure Evidence;
* halt at the **Root Closure Human Handoff Intercept** again.

Do not stop after a verifier `FAIL` merely to report the failures while actionable in-scope remediation remains.

Each new verification attempt requires fresh human authorization and a fresh verifier subagent.

The parent may not override or downgrade a verifier failure.

#### PASS

`ROOT CLOSURE: PASS` is non-terminal.

A valid `PASS` requires the **Verify Verifier Integrity** gate above to succeed.

Exit dispatcher-only mode and proceed directly to Section 4.

Do not report `PASS` as completion; the ticket is not complete until commit, push, Root Closure Evidence persistence, parent Root Closure Reconciliation persistence, and closure succeed.

Capture the verifier's:

* `TICKET_BASELINE`;
* `ROOT_CLOSURE_STATE`;
* acceptance proof;
* invariant-sweep result;
* protected-root result;
* targeted verification result.

Any implementation change after `PASS` makes the verdict stale and requires another Root Closure Human Handoff and fresh verifier subagent.

## 4. Re-Verify Before Commit

Re-check **Ticket branch** immediately before commit.

```bash
EXPECTED_TICKET_BRANCH="<Ticket branch value>"
CURRENT_BRANCH=$(git branch --show-current)

if [ "$CURRENT_BRANCH" != "$EXPECTED_TICKET_BRANCH" ]; then
  echo "❌ Branch changed during ticket implementation."
  exit 1
fi
```

Skip when **Ticket branch** is `None`.

### Root Closure State Guard

For Spec Review remediation, recompute:

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

If it differs, the PASS is stale.

Do not commit. Perform the `$verify-root-closure` Human Handoff again against the new state.

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

Capture ticket commits:

```bash
git log --reverse --format='%h — %s' "$TICKET_BASELINE"..HEAD
```

## 6. Close the Ticket

Close only when:

* implementation is complete;
* acceptance criteria have identifiable evidence;
* required targeted verification succeeded;
* any authorized broader verification succeeded;
* branch invariant holds;
* commit and push succeeded.

For Spec Review remediation additionally require:

* every carried acceptance cell is proven;
* Root Invariant Sweep has no known remaining violation;
* every protected root remains preserved;
* `$verify-root-closure` returned a valid `ROOT CLOSURE: PASS`;
* verified `ROOT_CLOSURE_STATE` remained unchanged through commit;
* parent Spec Review Root Closure Reconciliation is durably persisted.

### Persist Root Closure Evidence

Before closing a Spec Review remediation ticket, persist the independently verified closure evidence as a ticket comment:

```markdown
## Root Closure Evidence

**Root:** RB-<n> — <invariant>
**Production path:** <boundary exercised>
**Independent verification:** PASS
**Ticket baseline:** <TICKET_BASELINE>
**ROOT_CLOSURE_STATE:** <ROOT_CLOSURE_STATE>

### Acceptance proof
- <cell>: proven — <evidence>

### Invariant sweep
- <surface>: clean/proven — <evidence>

### Protected roots
- RB-<n>: preserved — <evidence>
- or None

### Verification
- <targeted checks and result>

### Commits
- <short SHA> — <subject>
```

Use the verifier's results. Do not strengthen them with unsupported parent claims.

Do not close if this comment cannot be persisted.

### Persist Parent Root Closure Reconciliation

For a Spec Review remediation ticket, ticket-local Root Closure Evidence is not sufficient durable completion state.

Before closing the ticket, reconcile the independently verified `ROOT CLOSURE: PASS` into the existing parent Spec Review's canonical Root Blocker Ledger and cumulative acceptance state.

This is a closure-state projection, not a review or remediation-synthesis pass.

Do not:

* invoke `$review-spec-remediation`;
* perform another Standards, Spec, or Architecture review;
* create, split, renumber, broaden, or redefine a Root Blocker;
* add, remove, replace, or reinterpret acceptance obligations;
* strengthen verifier evidence;
* rewrite historical Spec Review content.

Immediately before reconciliation, re-read the latest durable Spec Review state, including later ledger normalization and Root Closure Reconciliation updates.

Require that:

* the current Root Blocker ID equals the independently verified root;
* the current stable invariant materially matches the independently verified invariant;
* every currently active `open`, `regressed`, or `unproven` acceptance cell for that root was included in the verifier's closure contract and was proven;
* no new or materially changed non-satisfied obligation for that root appeared after verifier dispatch.

If any requirement fails, the PASS is stale relative to the canonical ledger.

Keep the ticket open and return to the Root Closure Human Handoff Intercept for fresh authorization and independent verification against the current root contract. A previously completed commit/push does not waive this gate.

Before appending reconciliation, inspect the parent Spec Review for an existing Root Closure Reconciliation for the same remediation ticket and `ROOT_CLOSURE_STATE`.

* exact matching reconciliation → reuse it and treat the persistence gate as satisfied;
* no matching reconciliation → append it;
* same remediation ticket with conflicting root, invariant, ticket baseline, or `ROOT_CLOSURE_STATE` → halt with a durable-state error and do not close the ticket.

Append:

```markdown
## Root Closure Reconciliation [YYYY-MM-DD HH:MM]

This is a durable-state reconciliation only. It does not rewrite or invalidate historical review findings or prior ledger updates.

**Root:** RB-<n> — <invariant>
**Remediation ticket:** #<ticket>
**Root Closure Evidence:** <ticket closure-evidence comment URL>
**Independent verification:** `ROOT CLOSURE: PASS`
**Ticket baseline:** `<TICKET_BASELINE>`
**ROOT_CLOSURE_STATE:** `<ROOT_CLOSURE_STATE>`

### Acceptance state changes

- <previously non-satisfied cell>: `satisfied` — <verifier evidence>

### Preserved acceptance state

- All previously `satisfied` active cells remain `satisfied`.
- All `owner-overridden` cells remain `owner-overridden`.
- Other Root Blockers and their acceptance cells are unchanged.

### Root status

- RB-<n>: `satisfied`
```

Use only the independently verified results.

Change only the current root's proven non-satisfied cells to `satisfied`. A root becomes `satisfied` only when every active required cell is `satisfied` or `owner-overridden`.

Do not change the status of protected other Root Blockers merely because the verifier proved they were preserved.

If the reconciliation comment cannot be persisted, do not close the ticket.

Never close a Spec Review remediation ticket with:

* unproven carried cells;
* known root violations;
* regressed/unproven protected roots;
* missing, invalid, or stale independent PASS;
* missing durable closure evidence;
* missing durable parent Root Closure Reconciliation.

Ordinary tickets do not use `$verify-root-closure`, formal Root Closure Evidence, or Root Closure Reconciliation.

## 7. Handoff

Enter this section only when **Invocation Termination** permits returning control.

Do not use a progress report as a substitute for continuing actionable work.

Report:

* implementation and acceptance evidence;
* Architecture context/divergence;
* ticket branch and baseline;
* `$wiki-sync` result and wiki changes;
* documentation/ADR activity;
* `$database-migrations` result when applicable;
* targeted verification;
* authorized broader verification, if any;
* broad checks not run;
* ticket commits as `<short SHA> — <subject>`;
* push result;
* worktree state;
* closure state.

For Spec Review remediation also report:

* Root Blocker ID/invariant;
* production path;
* sibling surfaces audited;
* Root Invariant Sweep;
* carried acceptance-cell proof;
* protected-root preservation;
* `$verify-root-closure` verdict;
* Root Closure Evidence persistence;
* Root Closure Reconciliation persistence.

After successful ticket closure, inspect the parent Spec's implementation-ticket state.

* If one open, unblocked frontier ticket remains, halt with:

  > ✅ **Ticket completed.**
  >
  > Please continue with:
  >
  > ```
  > $implement-ticket - <Frontier Ticket Title> (<Ticket URL>)
  > ```

* If multiple open, unblocked frontier tickets remain, output one copy-ready `$implement-ticket` line per ticket and let the user choose the next fresh implementation session.
* If no open implementation tickets remain, halt with:

  > ✅ **Spec implementation tickets are complete.**
  >
  > Please run:
  >
  > ```
  > $verify-spec - <Spec Title> (<Spec URL>)
  > ```

* If open tickets remain but all are blocked, report the blocking relationships and stop. Do not begin `$verify-spec`.

Do not invoke the next `$implement-ticket` or `$verify-spec` lifecycle stage implicitly.

An unresolved required gate keeps the ticket open, but **does not by itself authorize stopping**. If actionable in-scope work remains, continue. A pre-completion handoff must identify the concrete blocker that requires the halt.