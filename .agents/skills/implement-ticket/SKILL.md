---
name: implement-ticket
description: "Implement work based on a single ticket using the disciplines applicable to its actual change surface."
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Implement Ticket

Implement one ticket, verify it, persist repository changes when applicable, and close it only when all required work is proven complete.

Implementation discipline is applicability-driven:

> Repository location does not determine implementation or verification discipline. Derive required work from the ticket/Spec obligations and the actual changed surfaces.

Do not force code helpers onto documentation, workflow, configuration, migration, or tracker-only work. Mixed tickets apply the union of every relevant discipline.

## Session Independence

Assume no prior session state.

Recover correctness-critical inputs from the invocation, repository, and durable tracker artifacts. Prior-session summaries are routing context only.

If required durable state cannot be recovered, report the missing artifact rather than infer it.

### Durable Root-Verification Checkpoint

For an open Spec Review remediation ticket, the root-verification Human Handoff and verifier result must survive complete conversational/session context loss.

Use exactly one machine-managed ticket comment identified by:

```text
<!-- implement-ticket-root-checkpoint:v1 -->
```

The checkpoint is routing/re-entry state only. It is not Root Closure Evidence, a verifier verdict, or workflow authority.

Persist this schema:

```markdown
<!-- implement-ticket-root-checkpoint:v1 -->
## Implement Ticket Root Checkpoint

**Version:** 1
**Stage:** awaiting-root-verification | verifier-failed | verifier-passed
**Ticket:** #<ticket>
**Ticket branch:** <branch>
**Ticket baseline:** <sha>
**Remediation parent:** #<Spec Review>
**Parent Spec:** #<Spec>
**Root:** RB-<n> — <stable invariant>
**Candidate state:** <ROOT_CLOSURE_STATE>
**Attempt:** <n>

### Proposed Root Closure Evidence
<complete current Proposed Root Closure Evidence>

### Last verifier result
<None | exact valid PASS/FAIL result, including all consolidated findings and returned state>

### Attempt history
- Attempt <n> | <candidate state> | <PASS|FAIL|invalid> | <concise result>
```

Use the existing marker comment if present; never create multiple active checkpoint comments for one ticket.

Resolve it deterministically:

```bash
REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')
CHECKPOINT_MARKER='<!-- implement-ticket-root-checkpoint:v1 -->'

CHECKPOINT_IDS=$(
  gh api --paginate --slurp \
    -H "X-GitHub-Api-Version: 2026-03-10" \
    "repos/$REPO/issues/$TICKET_NUMBER/comments?per_page=100" \
    | jq -c --arg marker "$CHECKPOINT_MARKER" \
      '[.[][] | select(.body | contains($marker)) | .id]'
)
```

Require zero or one ID. More than one is ambiguous durable state and fails closed.

Write checkpoint Markdown outside the repository, for example `/tmp/implement-ticket-root-checkpoint.md`.

If no checkpoint exists:

```bash
jq -Rs '{body: .}' /tmp/implement-ticket-root-checkpoint.md \
  | gh api -X POST \
      -H "X-GitHub-Api-Version: 2026-03-10" \
      "repos/$REPO/issues/$TICKET_NUMBER/comments" \
      --input -
```

If one exists:

```bash
CHECKPOINT_ID=<the one existing id>

jq -Rs '{body: .}' /tmp/implement-ticket-root-checkpoint.md \
  | gh api -X PATCH \
      -H "X-GitHub-Api-Version: 2026-03-10" \
      "repos/$REPO/issues/comments/$CHECKPOINT_ID" \
      --input -
```

Re-read the comment after every write and require exact `Version`, `Stage`, ticket/lineage, root, baseline, candidate state, and attempt values.

Do not use Project fields, labels, local scratch files, prior conversation, or subagent memory as a substitute for this checkpoint.

### Durable Re-entry Routing

On every human invocation concerning an open Spec Review remediation ticket, recover the latest checkpoint before choosing a root-verification continuation.

Always re-run current branch, hierarchy, baseline, parent/root-ledger, and project-delivery guards; the checkpoint never bypasses fresh authority checks.

Route by `Stage`:

* `awaiting-root-verification`
  * `$verify-root-closure` invocation → require branch/baseline/lineage/root and current candidate state to match the checkpoint, then resume at **Resume After Human Authorization**;
  * `$implement-ticket` invocation → if the candidate still matches, re-emit the existing Root Closure Human Handoff without reimplementing or self-verifying;
  * a candidate mismatch makes the checkpoint stale; resume implementation and rebuild Proposed Root Closure Evidence before another handoff.
* `verifier-failed`
  * resume `$implement-ticket` correction immediately using **all** consolidated findings stored in `Last verifier result`;
  * do not dispatch another verifier until corrective work is complete, Proposed Root Closure Evidence is rebuilt, and the checkpoint is rewritten to `awaiting-root-verification` with a new/current candidate state;
  * a candidate mismatch is allowed when it is explained by corrective edits after the recorded FAIL; the stored findings remain mandatory until re-proven.
* `verifier-passed`
  * require exact candidate-state, baseline, branch, lineage, root, and verifier-state match;
  * if valid, resume Section 4 without re-running independent certification;
  * any candidate/root-state mismatch makes the PASS stale and returns to implementation/handoff.

A missing checkpoint is acceptable only before the first Root Closure Human Handoff. Once a root-verification attempt has begun, missing, duplicated, malformed, or contradictory checkpoint state is a hard re-entry blocker; do not infer the suspended stage from conversation history.

The same explicit command plus the same durable repository/tracker state must produce the same lifecycle continuation whether or not prior conversational context exists.

## 1. Read the Ticket and Guard the Branch

Read the full ticket and capture:

* **Ticket branch**
* **Ticket baseline**
* parent Spec
* Architecture context when present

For a Spec Review remediation ticket, also read the latest Spec Review state and capture:

* Root Blocker ID and invariant;
* affected sibling surfaces/reference kinds;
* required authoritative path/boundary obligations;
* carried acceptance-matrix cells;
* previously satisfied roots governing affected surfaces/contracts.

### Branch Guard

A declared **Ticket branch** must exactly match the current branch before any repository file mutation.

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

### Ticket Hierarchy Integrity Guard

Before persisting a pending Ticket baseline or making any other substantive tracker/repository mutation, validate the ticket's declared lineage against its native GitHub direct parent.

Determine ticket mode from durable ticket metadata:

* ordinary Implementation Ticket → require exactly one `Parent Spec: #<n>` and no remediation parent; expected native parent is Spec `#<n>`;
* Review Remediation Ticket → require exactly one `Remediation parent: Spec Review #<r>` plus exactly one `Parent Spec: #<s>` for lifecycle/branch provenance; expected native parent is Spec Review `#<r>`, never Parent Spec `#<s>`.

Re-read the ticket's native direct parent from canonical GitHub relationship state. Missing, unreadable, ambiguous, or contradictory lineage/parentage fails closed. Textual lineage is not a substitute for native decomposition hierarchy.

On failure, halt before baseline persistence, project-delivery reconciliation, implementation, verification, commit, or ticket-state mutation and report:

```text
TICKET HIERARCHY: INVALID
Ticket: #<ticket>
Declared lineage: <Parent Spec / Remediation parent values>
Expected native parent: #<n>
Actual native parent: <#n | None | unreadable>
Reason: <missing, ambiguous, or contradictory hierarchy>
```

`$implement-ticket` validates hierarchy only. It must not create, remove, or repair native parent/sub-issue relationships. Formal ticket publication/reconciliation remains owned by `$to-tickets`; `$github-issue-dependencies` remains the mechanical relationship helper for that owner.

A correctly published ticket continues through the existing guards and lifecycle unchanged.

### Project Delivery Actionability Guard

Before persisting a pending Ticket baseline or making any other tracker/repository mutation, resolve the parent Spec and determine whether it is Wayfinder-managed from durable `wayfinder-source`, `wayfinder-remediation`, and reconciled `Spec Handoff` evidence.

For a Spec Review remediation ticket, use its durable `Parent Spec` lineage for this guard. The Spec Review remains remediation provenance; it is not a substitute project-delivery governor.

An intentionally non-Wayfinder Spec keeps the existing implementation lifecycle. Do not invent a governing Wayfinder merely to enroll it into project focus.

For a Wayfinder-managed Spec:

1. require the parent Spec to be open;
2. read its complete native `blocked by` relationship set and fail closed if blocker data is truncated or unreadable;
3. stop if any direct Spec blocker is open;
4. recover every current governing Wayfinder; ambiguous governance fails closed rather than choosing one;
5. invoke `$project-delivery-management` `reconcile`;
6. invoke `$project-delivery-management` `guard <Wayfinder>` for every governor;
7. require at least one governor to return `PROJECT DELIVERY GUARD: ALLOWED`.

If no governor is allowed, stop before Ticket-baseline persistence, implementation, verification, or ticket-state mutation. Report the governing maps, their guard results, current focus, and the explicit human `$project-delivery-management` focus/switch/parallel choices. `$implement-ticket` never establishes, switches, or broadens focus.

A legitimately reopened blocker Spec makes existing tickets under the dependent Spec non-actionable again through the unchanged native dependency edge. Ticket publication, prior ticket completion, Project state, or a prior allowed invocation does not override current Spec blocker state.

Capture whether the successful entry guard returned `Mode: pre-bootstrap`.

Re-run this guard on every resumed human invocation before further substantive work. Internal child/helper workflows dispatched by an already-authorized `$implement-ticket` lifecycle inherit that parent authorization and must not introduce a redundant project-focus Human Handoff; a distinct later human lifecycle performs its own guard.

If **this same ticket lifecycle** is the atomic bootstrap/cutover operation that activates project delivery after entering with `Mode: pre-bootstrap`, preserve that captured entry authorization only through this ticket's persistence/closure as allowed by `$project-delivery-management`'s **Bootstrap Activation Boundary**. The cutover may not retroactively block the operation required to create it.

That exception:

* applies only when this ticket itself activates the canonical label + singleton cutover;
* never bypasses a direct Wayfinder blocker or reopened/open parent-Spec dependency;
* may not establish, switch, or broaden focus;
* expires when this ticket closes;
* may not authorize any downstream human lifecycle or handoff after activation.

### Ticket Baseline Guard

**Ticket baseline** is the durable per-ticket verification anchor, distinct from the Spec baseline.

It must be `Pending` or a full commit SHA.

If `Pending`:

1. require a clean worktree;
2. capture `git rev-parse HEAD`;
3. persist that full SHA into **Ticket baseline**;
4. re-read the ticket and require the value to match;
5. set `TICKET_BASELINE` to it.

Do this before repository file mutation.

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

* **Completed** — all required persistence, evidence, and closure gates completed;
* **Human Handoff** — this skill explicitly requires human authorization;
* **Hard Blocker** — a concrete external/environmental, branch, baseline, permission, required-tool, or persistence failure prevents further safe work.

Everything else is non-terminal.

In particular, partial progress, verification failure, `ROOT CLOSURE: FAIL`, corrective edits making a verdict stale, remaining actionable in-scope work, an open ticket, and `ROOT CLOSURE: PASS` before final lifecycle completion do not authorize stopping.

If none applies, continue the workflow.

### Change Surface Classification

Before selecting implementation helpers or verification, derive the ticket's complete change-surface set from the ticket/parent Spec obligations and the planned/actual mutations.

Use these classes as needed:

* **Code** — production/library/runtime source;
* **Tests** — test source, fixtures, harnesses, test configuration;
* **Documentation** — Markdown/docs/ADRs/wiki content;
* **Agent skills / workflow policy** — agent skills, lifecycle contracts, tracker/process policy;
* **Repository configuration** — package/tool/runtime configuration;
* **CI / automation** — workflows, scripts, release/qualification automation;
* **Data / schema / migrations** — models, migrations, durable serializers/contracts;
* **Tracker-only state** — issues, native relationships, labels, durable workflow state, Project projection with no repository file mutation.

`Mixed` means apply the union of all relevant classes; it is not a shortcut that collapses the ticket to one dominant class.

Record an applicability plan before substantive implementation. Every helper/check considered below must be either `applicable` or `not-applicable` with a concrete reason. Do not invoke a helper merely because it exists in the repository.

### Living Entity Wiki Guard

Invoke `$wiki-sync` before editing only when the change substantively affects a wiki-governed entity/source and the Living Entity Wiki exists.

Architecture context is routing context only. `$wiki-sync` owns entity routing, source consistency, Strict Invariants, Rejected Approaches, and blocking `[source-conflict]`.

After substantive implementation, invoke `$wiki-sync` again only when durable entity knowledge may have changed.

### Architecture vs. Implementation

Missing realization of accepted architecture is implementation work, not an architecture blocker.

Before routing to architecture remediation, determine whether accepted authority already establishes the required durable semantics, including where applicable:

* canonical ownership;
* authority/input sources;
* identity/key semantics;
* lifecycle ordering;
* boundaries/dependency direction;
* failure behavior.

Missing code, documentation, workflow policy, configuration, registration, repository operations, tracker wiring, producers, bootstrap wiring, or similar mechanisms are implementation work when those durable semantics are already resolved.

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
>    * Evidence: <concise evidence>
>    * Material consequence: <ownership/path/boundary/dependency/lifecycle/source conflict>
>    * Governing context: <entities / ADRs / docs / Wayfinder decisions>

Do not propose an architectural resolution.

### Documentation / ADRs

When the Documentation surface makes them applicable:

* `$to-doc` — new non-ADR document;
* `$classify-doc` — classify/reclassify/relocate an existing non-ADR;
* `$wiki-sync` — substantive existing `docs/current/` or `docs/proposed/` changes affecting wiki-governed knowledge;
* `$to-adr-doc` — ADR content or lifecycle.

Do not duplicate those workflows here.

### Wiki Commit Ownership

When `$implement-ticket` is parent and `$wiki-sync` changes repository files, `$wiki-sync` must not commit separately. Include its changes and matching `wiki/log.md` entry in the ticket commit.

### Scope and Applicable Helpers

* Implement only the ticket.
* For Spec Review remediation, fix the **root invariant**, not merely cited symptoms.
* Named authoritative paths and sibling surfaces are in scope.
* Any newly discovered manifestation of the same root on an in-scope surface belongs to this ticket.
* Any regression introduced against a previously satisfied root on an affected surface belongs to this ticket.
* Use `$tdd` only at applicable pre-agreed code/test seams.
* Use `$format-code` only when code/test surfaces governed by it changed.
* Use `$coding-standards` only for code surfaces it governs.
* Use documentation/workflow/configuration/CI/tracker owners and deterministic checks appropriate to those surfaces instead of substituting code helpers.
* Avoid unrelated cleanup.

### Database Guard

Invoke `$database-migrations` only for data/schema/migration-affecting work, including models, migrations, PostgreSQL repositories, durable serializers/contracts, and schema-dependent tests.

A required PostgreSQL check skipped because local setup is absent remains unresolved.

## 3. Verify

Verification is targeted and applicability-driven.

Build the verification set from the ticket acceptance criteria plus the classified change surfaces. Every required check must have identifiable supporting evidence; every omitted candidate check must have a concrete non-applicability reason.

Typical routing:

* Code/Tests → invoke `$verify-code` with `TICKET_BASELINE`, plus any ticket-required targeted production-boundary proof;
* Documentation → deterministic document/ADR/wiki validation owned by the relevant documentation workflow;
* Agent skills/workflow policy → structure/frontmatter, cross-skill contract consistency, ownership/handoff, fail-closed behavior, idempotency/re-entry, tracker relationship/projection proof as required;
* Repository configuration / CI → syntax/schema/lint/dry-run or repository-defined validation appropriate to the changed surface;
* Data/schema/migrations → `$database-migrations` and required migration/database proof;
* Tracker-only state → canonical re-read, native relationship/state verification, idempotency when required, and proof that repository files did not need mutation.

Do not automatically run full-suite tests, repository-wide lint/type checks, coverage, or unrelated integration suites.

Do not claim an acceptance criterion is proven without identifiable source/test/document/configuration/tracker evidence appropriate to that criterion.

If required verification fails, fix it within ticket scope and rerun it. Do not persist completion or close while required verification remains unresolved.

## Spec Review Root Closure

The following gates apply only to Spec Review remediation tickets.

Root closure is surface-neutral: the authoritative path/boundary may be a runtime production path, workflow/skill lifecycle, documentation/ADR contract, configuration/automation path, schema/persistence boundary, or tracker relationship/state. Existing templates may call this the **Production path**; interpret that field as the authoritative path/boundary governed by the root.

### Root Closure Gate

Targeted verification must prove the **entire carried Root Blocker obligation**, not merely the changed seam or enumerated symptoms.

Required proof includes:

* authoritative path/boundary governed by the root;
* every carried acceptance cell;
* affected sibling surfaces/reference kinds;
* regression proof that would fail for the root or a named symptom;
* relevant fail-closed behavior.

Required path and sibling-surface checks are targeted ticket verification, not optional broad verification.

### Root Invariant Sweep

Before proposing closure, search the contract surface governed by the root for other manifestations of the same violation.

Inspect only applicable surfaces, such as:

* constructors/factories/defaults, producers/consumers, adapters/facades, persistence/result boundaries, DI/bootstrap/composition;
* skills, lifecycle owners, handoffs, guards, defaults, alternate workflow paths, tracker relationships/projections;
* documentation/ADR authority and duplicate normative claims;
* configuration/CI alternate paths;
* schema/migration/persistence boundaries;
* named sibling surfaces and representative proof.

**Search first, then read only relevant surrounding material.**

The sweep is bounded by the root invariant. If another manifestation is found, fix and prove it within this ticket.

### Preserve Previously Satisfied Roots

Do not regress a previously satisfied Root Blocker.

A prior root becomes protected when this ticket changes a surface it governs, including the same authoritative path, service/repository, typed contract/evidence object, adapter/persistence boundary, workflow owner/handoff, documentation authority, tracker lifecycle state, canonical owner, or named sibling surface.

For each protected root:

1. identify applicable existing regression/acceptance proof;
2. recover and re-read the **current governing authority** for that protected contract when it derives from a Standard, repository policy, ADR/document authority, workflow policy, configuration contract, or other mutable normative source;
3. reconcile historical root wording against that current authority, including documented exceptions or explicit supersession;
4. rerun only proof affected by this change;
5. confirm the currently applicable protected contract remains satisfied.

Historical root state identifies the concern to preserve; it does not silently freeze a superseded policy forever. Current authority supersedes historical policy wording only when that authority change is explicit and durable. Implementation drift is never supersession.

For Standards/policy roots, do not treat the historical symptom alone as the violation. Cite the exact current rule and explain why any documented exception does or does not apply.

If regressed under the current applicable authority, fix it within this ticket and rerun both current-root and protected-root proof.

### Closure Reconciliation

Reconcile:

* every carried acceptance cell → `proven | unproven`;
* every protected root → `preserved | regressed`.

If any carried cell is unproven, known root violation remains, or protected root is regressed, keep the ticket open and continue fixing all actionable in-scope failures. Do not proceed to Proposed Root Closure Evidence or independent root-closure verification.

### No Partial Root Stop

Discovering additional in-scope root work is not itself a blocker. Continue until every carried root obligation is proven unless progress is actually prevented by a required Human Handoff, unresolved material architecture, an external/environmental dependency, or a branch/baseline/permission/tool/persistence failure that makes further work unsafe or impossible.

When halting for such a blocker, name the exact blocker, remaining affected obligation, and why it prevents further in-scope work.

### Proposed Root Closure Evidence

Before independent verification, assemble concrete evidence:

* Root Blocker ID and invariant;
* authoritative path/boundary exercised;
* Root Invariant Sweep surfaces/results;
* every carried acceptance cell and proof;
* protected roots and proof/results;
* applicable regression/runtime/workflow/document/configuration/tracker/DB checks used.

Generic test counts or unsupported assertions are insufficient.

### Root Closure Human Handoff Intercept

`$verify-root-closure` requires explicit human authorization.

For every Spec Review remediation ticket, after targeted verification and Proposed Root Closure Evidence are complete — but before repository persistence, closure-evidence persistence, or ticket closure:

1. compute the current candidate `ROOT_CLOSURE_STATE` using the same hash procedure used at verifier dispatch;
2. create/update the durable checkpoint with `Stage: awaiting-root-verification`, the complete Proposed Root Closure Evidence, the current candidate state, and incremented `Attempt`;
3. re-read and verify the checkpoint;
4. only then halt for human authorization.

If checkpoint persistence or verification fails, this is a hard tracker/persistence blocker. Do not emit a verifier handoff that cannot be durably resumed.

Emit this structure exactly:

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
> **Production path:** <authoritative path/boundary exercised>
> **Proposed closure:** <concise acceptance/sweep/protected-root summary>
>
> This invocation authorizes `$implement-ticket` to dispatch the independent verifier. It does **not** authorize the `$implement-ticket` main agent to perform certification itself.

Then stop.

### Resume After Human Authorization

An explicit `$verify-root-closure` invocation received at this checkpoint is an **authorization event**, not a local procedure call.

First recover the durable root checkpoint. Dispatch is authorized only when `Stage: awaiting-root-verification` and the checkpoint's ticket, branch, baseline, lineage, root, and candidate state match current durable state.

If the checkpoint says `verifier-failed`, the human invocation does **not** authorize re-verification of the stale candidate. Resume `$implement-ticket` correction instead. If it says `verifier-passed`, resume Section 4 after state validation. Missing/stale/ambiguous checkpoint state after an attempt began fails closed.

Resume `$implement-ticket` at the recovered checkpoint. Before dispatcher-only mode, re-run the **Project Delivery Actionability Guard** when the parent Spec is Wayfinder-managed.

#### Verifier Dispatch Invariant

After authorization, the `$implement-ticket` main agent enters **dispatcher-only mode**. It may only capture the exact candidate `ROOT_CLOSURE_STATE`, spawn exactly one fresh verifier subagent, receive its result, validate verifier independence/candidate-state integrity, and consume a valid `PASS` or `FAIL`.

It must not perform root-closure inspection/checks, reason to its own verdict, execute `$verify-root-closure` itself, or repair findings before the verifier returns.

Capture candidate state:

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

Require `DISPATCH_ROOT_CLOSURE_STATE` to equal the durable `awaiting-root-verification` checkpoint candidate state before spawning the verifier.

For a tracker-only remediation root with no repository mutation, also pass the exact durable tracker-state identifiers/read set required to prove the root; `$verify-root-closure` remains non-mutating and independently re-reads them.

Spawn exactly one fresh verifier subagent and pass only the explicit handoff inputs it requires: current ticket/parent Spec, latest Spec Review/Root Blocker Ledger, `TICKET_BASELINE`, current candidate state, `DISPATCH_ROOT_CLOSURE_STATE`, Proposed Root Closure Evidence, applicable Architecture context, and any root-required durable tracker identifiers.

The verifier independently derives the required Root Invariant Sweep and protected roots. Do not constrain it to the implementer's claimed coverage.

The verifier must execute `$verify-root-closure` as a **non-mutating leaf workflow**. It may read/search/inspect/run non-mutating targeted checks; a defect means `ROOT CLOSURE: FAIL`; it must not mutate repository/Git/tracker/branch state, invoke implementation/remediation workflows, or delegate.

#### Verify Verifier Integrity

After the verifier returns, recompute repository candidate state with the same hash command and re-read any root-required durable tracker state.

A verifier result is valid only when candidate state is unchanged, its `TICKET_BASELINE` and `ROOT_CLOSURE_STATE` match dispatch, required tracker state did not change unexpectedly, and no verifier mutation/delegation occurred.

If any condition fails, discard the verdict. Unauthorized verifier mutations are never automatically accepted. Each verification attempt requires fresh human authorization.

#### FAIL

`ROOT CLOSURE: FAIL` is non-terminal.

Before leaving dispatcher-only mode:

1. update the durable checkpoint to `Stage: verifier-failed`;
2. preserve the exact valid verifier verdict in `Last verifier result`, including every consolidated finding/correction and returned candidate state;
3. append the attempt/candidate/result to `Attempt history`;
4. re-read and verify the checkpoint.

Then exit dispatcher-only mode and resume implementation **in the same invocation**. Complete every actionable verifier finding, rerun affected targeted checks, rebuild Proposed Root Closure Evidence, and return to the Root Closure Human Handoff Intercept.

If context is later lost, `Stage: verifier-failed` is sufficient to resume this correction path without the human having to reconstruct the prior verifier result.

The parent may not override or downgrade a verifier failure. It may, however, determine the narrowest correct implementation response using current authoritative contracts cited by the verifier; that is implementation, not verdict override.

#### PASS

`ROOT CLOSURE: PASS` is non-terminal and requires verifier-integrity success.

Before proceeding:

1. update the durable checkpoint to `Stage: verifier-passed`;
2. preserve the exact valid PASS, baseline/state, acceptance proof, invariant-sweep result, protected-root result, and targeted verification result;
3. append the attempt/candidate/result to `Attempt history`;
4. re-read and verify the checkpoint.

Exit dispatcher-only mode and proceed to Section 4.

Any implementation change after `PASS` makes the verdict stale and requires another Human Handoff and fresh verifier; rewrite the checkpoint accordingly before that handoff.

## 4. Re-Verify Before Persistence

Re-run the **Ticket Hierarchy Integrity Guard** immediately before final repository persistence or ticket closure. If the native direct parent or declared lineage changed during implementation, halt under `TICKET HIERARCHY: INVALID`; do not commit or close under stale decomposition state.

Re-check **Ticket branch** immediately before repository commit when repository files changed:

```bash
EXPECTED_TICKET_BRANCH="<Ticket branch value>"
CURRENT_BRANCH=$(git branch --show-current)

if [ "$CURRENT_BRANCH" != "$EXPECTED_TICKET_BRANCH" ]; then
  echo "❌ Branch changed during ticket implementation."
  exit 1
fi
```

Skip when **Ticket branch** is `None` or the ticket is proven tracker-only with no repository mutation.

For a Wayfinder-managed parent Spec, re-run the **Project Delivery Actionability Guard** immediately before final persistence/closure unless this exact ticket entered with `Mode: pre-bootstrap` and is itself the atomic cutover operation that activated project delivery.

For that bootstrap case, validate the parent Spec/governing Wayfinder did not gain an open blocker, activation label exists, exactly one valid open singleton exists with migration-defined initial state, and the captured pre-bootstrap authorization belongs to this same still-open ticket lifecycle. Do not require newly activated empty focus to authorize the operation that created it.

For every other case, if dependency/focus authorization changed, do not commit or close under stale authorization.

### Root Closure State Guard

For Spec Review remediation, recompute repository `ROOT_CLOSURE_STATE` and required durable tracker state. Require them to match the independently verified candidate. If they differ, the PASS is stale; return to the Root Closure Human Handoff Intercept.

## 5. Commit and Push When Applicable

If repository files changed:

1. verify the branch;
2. for Spec Review remediation, verify candidate/root state;
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

If the ticket is tracker-only and no repository files changed:

* do not manufacture an empty commit;
* require `git rev-parse HEAD` still equals `TICKET_BASELINE` unless an unrelated authorized parent change is explicitly accounted for;
* require a clean worktree;
* record repository commit/push as `not-applicable — tracker-only ticket; no repository mutation`.

## 6. Close the Ticket

Close only when:

* implementation is complete;
* acceptance criteria have identifiable evidence;
* every applicable targeted verification gate succeeded;
* branch/baseline invariants hold where applicable;
* repository commit/push succeeded when repository files changed;
* tracker-only repository non-mutation was proven when no repository files changed.

For Spec Review remediation additionally require every carried acceptance cell proven, Root Invariant Sweep clean, protected roots preserved, valid independent `ROOT CLOSURE: PASS`, verified candidate state unchanged, and parent Spec Review Root Closure Reconciliation durably persisted.

### Persist Root Closure Evidence

Before closing a Spec Review remediation ticket, persist independently verified closure evidence as a ticket comment:

```markdown
## Root Closure Evidence

**Root:** RB-<n> — <invariant>
**Production path:** <authoritative path/boundary exercised>
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
- <applicable targeted checks and result>

### Commits
- <short SHA> — <subject>
- or None — tracker-only ticket; no repository mutation
```

Use the verifier's results. Do not strengthen them with unsupported parent claims. Do not close if this comment cannot be persisted.

### Persist Parent Root Closure Reconciliation

For a Spec Review remediation ticket, ticket-local Root Closure Evidence is not sufficient durable completion state.

Before closing, reconcile the independently verified `ROOT CLOSURE: PASS` into the existing parent Spec Review's canonical Root Blocker Ledger and cumulative acceptance state.

This is a closure-state projection, not another review/remediation-synthesis pass. Do not invoke `$review-spec-remediation`, perform another review, redefine Root Blockers, change acceptance obligations, strengthen verifier evidence, or rewrite historical review content.

Immediately before reconciliation, re-read latest durable Spec Review state. Require the current Root Blocker ID/invariant to match the independently verified root, every active non-satisfied cell to have been in the closure contract and proven, and no new/materially changed non-satisfied obligation to have appeared after dispatch.

If any requirement fails, the PASS is stale; keep the ticket open and return to the Root Closure Human Handoff Intercept.

Before appending, reuse an exact existing reconciliation for the same remediation ticket and candidate state; halt on conflicting reconciliation state.

Append the existing **Root Closure Reconciliation** format, changing only the current root's independently proven non-satisfied cells to `satisfied`. Previously satisfied/Owner-overridden cells and other roots remain unchanged.

If reconciliation cannot be persisted, do not close the ticket.

Ordinary tickets do not use `$verify-root-closure`, formal Root Closure Evidence, or Root Closure Reconciliation.

## 7. Handoff

Enter this section only when **Invocation Termination** permits returning control.

Report:

* classified change surfaces and applicability plan;
* implementation and acceptance evidence;
* Architecture context/divergence;
* ticket branch and baseline;
* applicable wiki/document/database/tooling activity;
* applicable targeted verification and non-applicable checks with reasons;
* repository commit(s)/push, or tracker-only non-mutation proof;
* final worktree/repository state;
* closure state.

For Spec Review remediation also report Root Blocker ID/invariant, authoritative path/boundary, sibling surfaces audited, Root Invariant Sweep, carried acceptance proof, protected-root preservation, `$verify-root-closure` verdict, Root Closure Evidence persistence, and Root Closure Reconciliation persistence.

After successful ticket closure, if the parent Spec is Wayfinder-managed, invoke `$project-delivery-management` `reconcile` after closure is durable. Ticket closure remains authoritative even if reconciliation fails; report projection/coordination drift and do not present a downstream lifecycle handoff that depends on stale project-delivery state.

### Deterministic Post-Closure Frontier

After successful ticket closure and any required project-delivery reconciliation, derive the downstream ticket frontier **before** post-transition Project reconciliation. The same recovered frontier must drive both affected parent/frontier projections and the final Human Handoff.

Use the already recovered repository and decomposition parent:

* ordinary Implementation Ticket → frontier parent is its native parent Spec;
* Review Remediation Ticket → frontier parent is its native parent Spec Review; the durable `Parent Spec` remains the lifecycle provenance owner and downstream verification target.

Do not infer the frontier from Project fields, labels, prior conversation, or prose in issue comments.

Use the native REST sub-issue endpoint exactly once to read all direct children:

```bash
REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')
FRONTIER_PARENT=<native parent issue number>

FRONTIER_PAGES=$(
  gh api --paginate --slurp \
    -H "X-GitHub-Api-Version: 2026-03-10" \
    "repos/$REPO/issues/$FRONTIER_PARENT/sub_issues?per_page=100"
)

OPEN_CHILDREN=$(
  printf '%s\n' "$FRONTIER_PAGES" \
    | jq -c '[.[][] | select(.state == "open") | {number, title, url: .html_url}]'
)
```

For each open direct child, use the native dependency endpoint exactly once to recover its complete `blocked by` set:

```bash
BLOCKER_PAGES=$(
  gh api --paginate --slurp \
    -H "X-GitHub-Api-Version: 2026-03-10" \
    "repos/$REPO/issues/$CHILD_NUMBER/dependencies/blocked_by?per_page=100"
)

OPEN_BLOCKERS=$(
  printf '%s\n' "$BLOCKER_PAGES" \
    | jq -c '[.[][] | select(.state == "open") | {number, title, url: .html_url}]'
)
```

A child is executable only when `OPEN_BLOCKERS` is empty.

Execution rules:

* use these prescribed REST reads; do not probe `gh issue view --json subIssues`, alternate JSON shapes, GraphQL relationship queries, or help output;
* capture raw paginated payloads locally and inspect only the reduced `jq` results required by this workflow; do not print raw page payloads merely for model inspection;
* a successful prescribed `gh api --paginate --slurp` command plus successful local `jq` reduction is authoritative for this read; UI, harness, or tool-rendering truncation of an otherwise successful raw payload is **not** pagination failure and must not make the frontier unreadable;
* treat the frontier as unreadable only when a prescribed command fails, pagination itself fails, local reduction fails, or required relationship data is otherwise proven incomplete;
* do not retry a failed frontier/dependency read through another interface;
* do not narrate successful frontier discovery, per-child blocker reads, intermediate counts, or retries;
* preserve native hierarchy as the decomposition authority and native `blocked by` relationships as dependency authority.

### Parent / Frontier Lifecycle Reconciliation

Derive parent/frontier lifecycle state from this same post-closure snapshot before Project reconciliation.

For an ordinary Implementation Ticket:

* if one or more implementation-ticket children remain open, preserve the parent Spec's current implementation lifecycle unless another durable lifecycle transition independently changed it;
* if no implementation-ticket children remain open, advance the parent Spec to base `Workflow State = Ready to Verify`, `Work Status = Ready`, `Next Skill = $verify-spec`.

For a Review Remediation Ticket:

* re-read the latest durable Spec Review Root Blocker Ledger after ticket-local Root Closure Reconciliation;
* if remediation children remain open or the ledger still establishes `open` / `regressed` implementation remediation, preserve the parent Spec's `Review Remediation` lifecycle and derive the Spec Review projection from that durable remediation state;
* if no remediation child remains open and the ledger establishes no remaining `open` / `regressed` implementation remediation, advance the durable `Parent Spec` to base `Workflow State = Ready to Verify`, `Work Status = Ready`, `Next Skill = $verify-spec`;
* include the Spec Review itself as an affected artifact only when its own durable remediation state changes. Never infer `Spec Review = Complete` merely because its child count reached zero.

Child absence is frontier evidence, not sufficient authority to erase Architecture Remediation, unresolved durable remediation state, or another independently owned lifecycle state.

### Downstream Dependency Reconciliation

After every successful ticket closure, re-read direct native dependents because closure may change their actionability without changing the dependency relationship itself.

Use the native REST dependency endpoint exactly once to read every direct dependent:

```bash
DEPENDENT_PAGES=$(
  gh api --paginate --slurp \
    -H "X-GitHub-Api-Version: 2026-03-10" \
    "repos/$REPO/issues/$TICKET_NUMBER/dependencies/blocking?per_page=100"
)

OPEN_DEPENDENTS=$(
  printf '%s\n' "$DEPENDENT_PAGES" \
    | jq -c '[.[][] | select(.state == "open") | {number, title, url: .html_url, parent_issue_url}]'
)
```

For each open direct dependent, read its complete native `blocked by` set exactly once and keep only open blockers:

```bash
DEPENDENT_BLOCKER_PAGES=$(
  gh api --paginate --slurp \
    -H "X-GitHub-Api-Version: 2026-03-10" \
    "repos/$REPO/issues/$DEPENDENT_NUMBER/dependencies/blocked_by?per_page=100"
)

DEPENDENT_OPEN_BLOCKERS=$(
  printf '%s\n' "$DEPENDENT_BLOCKER_PAGES" \
    | jq -c '[.[][] | select(.state == "open") | {number, title, url: .html_url}]'
)
```

The native dependency edge remains authoritative history. Do **not** remove it merely because the blocker closed, and do not rewrite the dependent ticket's `## Blocked by` prose to erase the relationship.

For an open direct dependent that is durably an ordinary Implementation Ticket or Review Remediation Ticket and whose current `Blocked` lifecycle state is dependency-derived:

* one or more open native blockers → keep base `Workflow State = Blocked`, `Work Status = Blocked`, `Next Skill = None`;
* zero open native blockers → advance the base ticket route to `Workflow State = Ready to Implement`, `Work Status = Ready`, `Next Skill = $implement-ticket`.

Do not overwrite another durable lifecycle state such as Architecture Remediation or Awaiting Root Verification. Require the dependent's native parent and declared lineage to establish its ticket type and current lifecycle ownership before changing its base route; ambiguous state fails closed.

### Post-Closure Project Reconciliation

After frontier and dependent state are recovered, assemble one post-transition Project reconciliation set containing every affected artifact:

* the completed ticket;
* every direct dependent whose base projection changed;
* every parent/frontier artifact whose lifecycle projection changed from the recovered post-closure frontier;
* for remediation, the Spec Review when its durable remediation projection changed and the durable Parent Spec when its lifecycle changed.

Recover current project-delivery context before submitting that set. Do not synchronize the completed ticket first and derive its affected parent/frontier afterward. Project reconciliation consumes the already-recovered dependency/frontier truth; it must not discover dependents or infer lifecycle transitions from Project fields.

If authoritative frontier, blocker, lineage, or remediation-ledger reads cannot be completed, the completed ticket remains authoritatively closed. Report the exact unreadable state and do not advertise a downstream lifecycle handoff whose actionability cannot be proven.

Project synchronization failure by itself is projection drift: it never rolls back authoritative ticket closure or changes the recovered native frontier. Report the drift; do not suppress an otherwise-proven downstream handoff solely because the non-authoritative Project projection failed to update.

Before presenting any next `$implement-ticket` or `$verify-spec` handoff for a Wayfinder-managed Spec, evaluate current project-delivery authorization again. If no governing Wayfinder is currently allowed, do not advertise downstream lifecycle as actionable. Report the governing Wayfinder set and explicit human `$project-delivery-management` focus/switch/parallel action required.

### Handoff From the Recovered Frontier

Emit the normal frontier handoff from the **same** recovered post-closure snapshot used for parent/frontier Project reconciliation. Do not perform a second frontier read for handoff selection.

* exactly one open unblocked ticket → emit exactly one copy-ready line:

  ```text
  $implement-ticket - <Ticket Title> (<Ticket URL>)
  ```

* multiple open unblocked tickets → emit one copy-ready line per ticket in stable issue-number order and let the user choose;
* no open implementation/remediation tickets and the parent Spec is durably `Ready to Verify` → emit exactly one copy-ready line:

  ```text
  $verify-spec - <Spec Title> (<Spec URL>)
  ```

  For Review Remediation Ticket mode, use the durable `Parent Spec` title and URL, not the Spec Review title/URL.
* open tickets but all blocked → report the open blockers and stop.

A prose sentence that merely names the next artifact does **not** satisfy the handoff requirement. The required copy-ready `$implement-ticket` or `$verify-spec` command must be present in the final response when that lifecycle is actionable.

Do not invoke the next `$implement-ticket` or `$verify-spec` lifecycle stage implicitly.

An unresolved required gate keeps the ticket open, but does not by itself authorize stopping. If actionable in-scope work remains, continue; a pre-completion handoff must identify the concrete blocker that requires the halt.
