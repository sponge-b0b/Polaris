---
name: verify-root-closure
description: Independently verify Root Blocker closure for a Spec Review remediation ticket across the authoritative surfaces governed by the root, in the fresh non-mutating verifier subagent dispatched by `$implement-ticket` after explicit human authorization.
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Verify Root Closure

Independently certify or reject closure of one Root Blocker for a **Spec Review remediation ticket**.

Closure certification is coverage-driven and surface-neutral:

> Repository location does not determine root-closure verification discipline. Derive the required proof from the stable Root Blocker invariant, cumulative acceptance contract, and the actual authoritative surfaces governed by the root.

A root may govern code/runtime, tests, documentation/ADR, agent skills/workflow policy, repository configuration, CI/automation, data/schema/migrations, tracker-only state, or a mixed union of those surfaces.

A `PASS` must prove the complete current Root Blocker contract against current authoritative state. Prior `PASS`, `satisfied`, `preserved`, or closure status is durable history and routing context, never current proof.

## Invocation Semantics

When the human explicitly invokes `$verify-root-closure` in response to the Root Closure Human Handoff from `$implement-ticket`, that invocation is an **authorization event**, not authorization for the `$implement-ticket` main agent to perform certification.

The main agent must resume `$implement-ticket` at its verifier-dispatch checkpoint and spawn exactly one fresh verifier subagent.

Before dispatch, the main agent must recover the ticket's durable `<!-- implement-ticket-root-checkpoint:v1 -->` comment and route by its recorded stage. This requirement applies even after complete conversational/session context loss:

* `awaiting-root-verification` with matching ticket/branch/baseline/lineage/root/candidate state → the human invocation authorizes one fresh verifier dispatch;
* `verifier-failed` → do **not** dispatch the stale candidate; resume `$implement-ticket` correction from the stored consolidated FAIL;
* `verifier-passed` → do not re-certify; resume `$implement-ticket` persistence after state validation;
* missing, duplicated, malformed, or contradictory checkpoint state after an attempt began → fail closed and return control to `$implement-ticket`.

Only that fresh verifier executes the procedure below.

If this skill is being executed directly by the `$implement-ticket` main agent, do not perform certification or emit a root-closure verdict.

## Non-Mutating Leaf Verifier

`$verify-root-closure` is a **non-mutating leaf workflow**.

It may:

* read and search repository/tracker evidence;
* inspect Git state and history;
* run non-mutating targeted checks required for current-root closure or preservation obligations.

It must not:

* edit, create, delete, move, format, or generate repository files;
* modify Git, branch, commit, issue, native relationship, label, Project, or other tracker state;
* run fixers or repository-mutating commands;
* perform implementation or remediation;
* invoke implementation/remediation workflows;
* delegate or spawn another agent or subagent.

A discovered defect is evidence for `ROOT CLOSURE: FAIL`, never authorization to repair it.

A verifier that mutates or delegates has not performed valid root-closure verification.

The implementer's Proposed Root Closure Evidence is a set of claims to verify, not authority.

## 1. Recover Closure State

Read:

* the full remediation ticket;
* parent Spec;
* latest Spec Review / canonical Root Blocker Ledger;
* current stable Root Blocker invariant;
* complete carried acceptance contract;
* remediation obligations;
* verification obligations;
* preservation obligations;
* affected semantic surfaces/reference kinds;
* applicable accepted architecture referenced by the ticket;
* Proposed Root Closure Evidence;
* the durable `$implement-ticket` root checkpoint used for this dispatch, including attempt number and candidate state.

Use the caller-provided `TICKET_BASELINE`. Require the checkpoint to be `Stage: awaiting-root-verification` and its ticket/branch/baseline/lineage/root/candidate state to match the dispatch inputs. The verifier does not mutate the checkpoint.

When repository state is part of the root, inspect:

```bash
git status --short
git diff --name-status "$TICKET_BASELINE"
```

When tracker state is part of the root, independently re-read the exact canonical issues, native hierarchy/dependencies, labels, durable lifecycle fields/comments, focus singleton, or Project projection required by the root. Project state is evidence only where the governing contract makes projection itself the subject; it never becomes workflow authority.

Search before reading. Locate the smallest authoritative source/tracker surfaces needed to prove the root.

Do not rely on the implementer's narrative to determine what changed or what must be proven.

If required durable closure state cannot be recovered, verification is invalid and must halt before the root scan.

## 2. Establish Verifier Integrity

Before substantive verification, establish that the verification run itself is valid.

Fail immediately without continuing the scan if:

* required ticket/root state cannot be recovered;
* `TICKET_BASELINE` is invalid or unavailable when repository state is part of the candidate;
* required repository or tracker state cannot be inspected;
* the verifier mutates repository/tracker state;
* the verifier delegates or spawns another agent;
* candidate repository or root-required tracker state changes during verification;
* another condition makes subsequent evidence untrustworthy.

These are **verifier-integrity failures**, not Root Blocker implementation failures.

Do not emit `ROOT CLOSURE: PASS` or `ROOT CLOSURE: FAIL` from an invalid run.

Return the invalidation reason to `$implement-ticket`, which owns recovery and fresh dispatch.

## 3. Classify Root Surfaces and Derive Closure Obligations

The stable Root Blocker invariant is authoritative over enumerated symptoms. The cumulative acceptance contract remains required evidence and must not be silently narrowed.

Classify every surface needed to prove the root using these classes as applicable:

* **Code** — production/library/runtime source;
* **Tests** — tests, fixtures, harnesses, test configuration;
* **Documentation** — docs, ADRs, wiki content;
* **Agent skills / workflow policy** — skills, lifecycle contracts, tracker/process policy;
* **Repository configuration** — package/tool/runtime configuration;
* **CI / automation** — workflows, scripts, release/qualification automation;
* **Data / schema / migrations** — models, migrations, durable serializers/contracts;
* **Tracker-only state** — issues, native relationships, labels, durable workflow state, focus, Project projection.

`Mixed` means apply the union of all relevant classes.

Independently derive the bounded contract surface required to prove the root. Depending on the classification, that may include:

* runtime constructors/factories/defaults, producers/consumers, adapters/facades, DI/bootstrap/composition, persistence/result boundaries, entrypoints, sibling paths, negative/bypass paths, and representative tests;
* skill owners, invocation boundaries, handoffs, guard paths, default/fallback workflow behavior, re-entry/completion paths, dependency/provenance writers, and Project-projection boundaries;
* documentation/ADR normative claims, realization/lifecycle state, citations, and competing source-of-truth claims;
* configuration/CI schemas, defaults, alternate configuration paths, enabled/disabled automation, dry-run/failure behavior;
* schema/migration ordering, persistence/reconstruction contracts, and database proof where required;
* canonical tracker provenance, hierarchy, native dependencies, focus state, lifecycle transitions, idempotency/reconciliation, and exact post-mutation rereads.

Do not expand into unrelated review.

### Root Closure Coverage Manifest

Before evaluating closure, build a **Root Closure Coverage Manifest** with stable `RC-<n>` cells.

Create cells for every applicable:

* remediation obligation;
* verification obligation;
* carried acceptance cell, including cells already recorded as satisfied;
* same-root preservation obligation;
* authoritative/sibling surface independently required by the stable invariant;
* negative, bypass, fail-closed, alternate-authority, fallback, re-entry, or alternate-evidence path independently required by the invariant.

Each cell records:

```text
Coverage: RC-<n>
Kind: <remediation | verification | acceptance | preservation | invariant-sweep>
Obligation: <exact durable obligation or invariant-derived requirement>
Surfaces: <authoritative files/artifacts/tracker state requiring inspection>
State: <unchecked | proven | violated | unproven>
Evidence: <current evidence when dispositioned>
```

Rules:

* construct the manifest from durable root state, the stable invariant, authoritative Spec/architecture, and current independent discovery — not from Proposed Root Closure Evidence;
* prior closure evidence may identify useful surfaces to re-check, but must not initialize a cell as `proven`;
* prior `PASS`, `satisfied`, `preserved`, unchanged-file status, or ticket closure is never current proof;
* do not silently remove or merge materially distinct carried cells;
* if the scan discovers another material manifestation of the same stable invariant, add an `invariant-sweep` cell and evaluate it before verdict;
* only durable state that explicitly supersedes, retires, or Owner-overrides an obligation removes it from the current-root manifest.

Coverage is complete only when every manifest cell is `proven`, `violated`, or `unproven` and `unchecked = 0`.

### Preservation Obligations

Every carried satisfied cell applicable to the current root remains a current closure obligation.

Re-prove each carried same-root cell against current authoritative state even when the remediation ticket did not modify its surface.

Do not treat satisfied cells as new remediation work, but do not accept historical status as proof.

### Protected Roots

From the latest Spec Review state, independently derive previously satisfied **other Root Blockers** whose governed surfaces/contracts intersect the current ticket's modified surfaces.

Relevant intersections may include the same runtime path/service/repository, typed contract/evidence object, adapter/persistence boundary, workflow owner/handoff/guard, documentation authority, configuration/CI path, schema/migration boundary, tracker lifecycle/relationship/projection, canonical owner, or named sibling surface.

Protected roots are Root Blocker IDs, not remediation-ticket numbers. Do not trust the implementer's protected-root list.

For each protected root, distinguish durable historical remediation state from its **current governing authority**.

* Recover the historical root invariant and acceptance/regression evidence.
* Identify and re-read the current authoritative Standard, repository policy, ADR/document authority, workflow policy, configuration contract, schema contract, or other normative source that governs the intersecting surface.
* Historical root wording does not silently become a permanent shadow policy when the governing authority has been explicitly and durably changed.
* Current implementation behavior never counts as supersession by itself.
* A current authority change supersedes historical policy wording only when that authority relationship/change is explicit and durable.
* Preserve every unsuperseded part of the historical root contract.

For Standards/policy-derived roots, evaluate the candidate against the **exact current rule**, including documented exceptions. Do not convert the old symptom into an automatic violation.

A Standards/policy protected-root failure must cite:

1. protected Root Blocker ID and historical concern;
2. current governing authority;
3. exact current rule violated;
4. why any documented exception or explicit supersession does not apply.

If current authority expressly permits the candidate under a documented exception, that fact may prove preservation; no owner override is required merely because the historical symptom is present.

If the current authority relationship is ambiguous or cannot be recovered, mark the protected root `unproven`; do not invent a stricter historical rule or silently waive it.

## 4. Verify the Current Root

Evaluate every `RC-*` cell in the Root Closure Coverage Manifest.

For each:

1. inspect the actual current authoritative surface;
2. verify required composition/wiring/lifecycle/state transition where relevant;
3. identify concrete current evidence appropriate to that surface;
4. determine whether the evidence proves the invariant at the required boundary;
5. record `proven`, `violated`, or `unproven` with evidence.

A result is `proven` only when current evidence establishes the required behavior/state.

Never mark a cell `proven` solely because a prior verifier passed it, durable state labels it satisfied/preserved, the implicated file is unchanged, a previous ticket claimed it fixed, or Proposed Root Closure Evidence says it is covered.

Proof must match the surface. Examples:

* runtime behavior may require source plus targeted production-boundary tests;
* workflow policy may require skill contracts plus canonical tracker-state/re-entry/idempotency evidence;
* documentation/ADR obligations may require exact normative text, lifecycle state, and source consistency;
* configuration/CI obligations may require schema/syntax/dry-run/effective-state proof;
* migrations may require migration/database proof;
* tracker-only obligations may require exact canonical re-reads of native relationships and durable lifecycle/focus/projection state.

Do not manufacture code tests for non-code obligations.

For negative or fail-closed invariants, inspect the bypass forms appropriate to the surface. This may include runtime defaults/direct construction/fallbacks, alternate workflow entry/handoff paths, inferred tracker authority, stale/replayed lifecycle state, conflicting documentation authority, alternate configuration/defaults, partial-mutation recovery, unavailable dependencies, or other routes by which the forbidden condition could still occur.

### Adversarial Root Invariant Sweep

After dispositioning explicit remediation and carried acceptance cells, independently sweep from the **stable Root Blocker invariant outward** rather than from the ticket diff inward.

Search all materially relevant current surfaces—changed or unchanged—that could satisfy or bypass the invariant. For workflow/tracker roots, explicitly inspect ownership, guards, handoffs, re-entry, idempotency, native relationship semantics, and projection-authority boundaries. For code/runtime roots, inspect the relevant construction/composition/persistence/alternate paths. Use analogous authoritative surfaces for docs/config/migrations.

For negative invariants, explicitly search for alternate ways the forbidden behavior could still occur. Do not infer closure merely because the intended canonical path exists.

The sweep is bounded by the stable root invariant but may inspect unchanged surfaces outside the current ticket diff.

Add every newly discovered material same-root manifestation to the Coverage Manifest and disposition it before verdict.

If accepted architecture already determines a responsibility but realization is missing or incorrect, classify it as an **implementation violation**, not unresolved architecture.

If proceeding would genuinely require a new durable architectural choice, record an `architecture-blocker candidate`. Do not resolve, route, or remediate it here.

## 5. Root Closure Completeness Gate

Do not proceed to a verdict until the Root Closure Coverage Manifest is complete.

Require:

```text
Root coverage: <n> cells; proven <n>; violated <n>; unproven <n>; unchecked 0
```

The verifier must account for every carried acceptance cell and every material same-root surface discovered by the invariant sweep.

A summary such as “prior cells preserved,” “previous closure remains valid,” or “no affected changes” cannot substitute for per-cell current evidence.

A root with any `violated` or `unproven` cell cannot pass.

## 6. Failure Accumulation Invariant

Once a valid verification scan begins, **do not fail fast on implementation or proof defects**.

When any current-root, preservation, protected-root, negative-path, authoritative-surface, or proof obligation fails:

1. record the failure with concrete evidence;
2. continue the remaining bounded closure scan;
3. evaluate every other applicable obligation and invariant-sweep surface;
4. return one consolidated verdict after the scan completes.

A discovered defect must not prevent discovery of other independently observable defects in the same bounded closure domain.

Do not repeatedly exercise a path when one failure makes its downstream result impossible and no independent evidence can be gained. Record the blocked obligation as `unproven` with the causal failure and continue elsewhere.

Do not broaden the scan merely because failures were found.

Fail immediately only for a **verifier-integrity failure** that makes continued results untrustworthy.

## 7. Verify Protected Roots

For every independently derived protected root:

1. recover its historical invariant and applicable existing acceptance/regression proof;
2. recover the current governing authority for the intersecting contract and reconcile any explicit durable policy change or documented exception;
3. inspect the modified shared surface;
4. rerun only proof affected by the current ticket;
5. record whether the **currently applicable protected contract** remains preserved.

For Standards/policy roots, a broad pattern match or old symptom is insufficient. The evidence must show why the current authoritative rule actually forbids the candidate at this boundary.

If adequate current proof cannot establish preservation, mark the protected root `unproven`.

A protected root contributes to final `FAIL` when violated or unproven. Continue verifying remaining protected roots after discovering one failure.

## 8. Verification Scope

Run only checks required to establish complete current-root coverage, carried acceptance/preservation obligations, affected protected-root preservation, and independent Root Invariant Sweep coverage.

The current-root boundary is the stable Root Blocker invariant, not the current ticket diff.

Inspecting unchanged sibling/source/tracker paths required to prove that invariant is targeted root verification, not unrelated broad review.

Run targeted tests only when tests are necessary proof for the applicable root surface. Do not run unrelated full test suites, repository-wide lint/type checks, coverage suites, or integration suites unrelated to the root.

Before any pytest invocation, follow the mandatory test-service preflight in
`AGENTS.md` and `docs/process/testing-guide.md`. Determine the selected scope's
complete external prerequisites and verify them before pytest starts. Missing
prerequisites leave required verification unresolved.

Do not fix failures. A failed targeted check is recorded and does not terminate the bounded scan unless it invalidates verifier integrity.

## 9. Candidate-State Integrity

After the bounded scan, confirm and record the exact verified repository candidate state:

```bash
ROOT_CLOSURE_STATE=$(
  {
    git diff --binary "$TICKET_BASELINE" --
    git ls-files --others --exclude-standard -z \
      | sort -z \
      | xargs -0 -r sha256sum
  } | sha256sum | awk '{print $1}'
)
```

Return:

* `TICKET_BASELINE`;
* `ROOT_CLOSURE_STATE`;
* the exact root-required durable tracker-state evidence/read set, or `Tracker state: not-applicable`.

The caller-provided candidate repository state and returned `ROOT_CLOSURE_STATE` must match. Root-required tracker state must also remain unchanged during the verifier run.

If candidate repository or tracker state changed during verification, invalidate the run rather than reconcile it.

`$implement-ticket` owns candidate-state integrity and verdict invalidation. Any implementation/tracker change after a valid `PASS` makes that verdict stale when it affects the verified root state.

## 10. Verdict

Emit a verdict only after the complete bounded scan, Root Closure Completeness Gate, and candidate-state integrity checks succeed.

### PASS

Return `PASS` only when:

* Root Closure Coverage Manifest has `unchecked 0`;
* every remediation obligation is proven;
* every applicable verification obligation is proven;
* every carried acceptance cell has current proof;
* every same-root preservation obligation has current proof;
* the adversarial Root Invariant Sweep finds no remaining in-scope violation;
* every required authoritative and sibling surface is proven;
* required negative/fail-closed behavior is proven;
* every protected root is preserved;
* Proposed Root Closure Evidence contains no materially unsupported claim.

Use:

```text
ROOT CLOSURE: PASS

Root: RB-<n> — <invariant>
Production path: <authoritative path/boundary proven>
Root surfaces: <classified surfaces>
Root coverage: <n> cells; proven <n>; violated 0; unproven 0; unchecked 0

Acceptance:
- RC-<n> <cell>: proven — <current evidence>

Preservation obligations:
- RC-<n> <cell>: proven — <current evidence>
- or None

Invariant sweep:
- RC-<n> <surface>: clean/proven — <current evidence>

Protected roots:
- RB-<n>: preserved — <evidence>
- or None

Targeted verification:
- <check>: passed

Tracker state:
- <canonical root-required state/evidence>
- or not-applicable

TICKET_BASELINE: <sha>
ROOT_CLOSURE_STATE: <sha256>
```

Do not emit `PASS` with qualifications.

### FAIL

If one or more required obligations are violated or unproven, return **all independently supported failures discovered during the completed bounded scan**:

```text
ROOT CLOSURE: FAIL

Root: RB-<n> — <invariant>
Root surfaces: <classified surfaces>
Root coverage: <n> cells; proven <n>; violated <n>; unproven <n>; unchecked 0

Current-root failures:
- RC-<n> <surface/cell>: violated|unproven — <concrete evidence>
- ...

Preservation failures:
- RC-<n> <cell>: violated|unproven — <concrete evidence>
- or None

Protected-root failures:
- RB-<n>: violated|unproven — <concrete evidence>; current authority: <source/rule>; exception/supersession analysis: <why it does not apply>
- or None

Architecture-blocker candidates:
- <candidate and evidence>
- or None

Blocked proof:
- <obligation>: unproven because <causal failure>
- or None

Required corrections:
- <smallest concrete implementation/proof gap>
- ...

Targeted verification:
- <check>: passed|failed — <relevant evidence>

Tracker state:
- <canonical root-required state/evidence>
- or not-applicable

TICKET_BASELINE: <sha>
ROOT_CLOSURE_STATE: <sha256>
```

Do not stop after the first failure. Do not duplicate one underlying failure as several corrections unless independently actionable. Do not downgrade required failures to advisory findings. Do not repair any failure before returning the verdict.

## Completion

A valid verifier execution completes with exactly one independent verdict after the complete bounded coverage scan:

* `ROOT CLOSURE: PASS`; or
* `ROOT CLOSURE: FAIL`.

A verifier-integrity failure produces no closure verdict and requires fresh dispatch. `FAIL` keeps the remediation ticket open.

`$implement-ticket` alone owns correcting consolidated failures, applying Architecture vs. Implementation to architecture-blocker candidates, rerunning affected implementation verification, rebuilding Proposed Root Closure Evidence, requesting fresh human authorization, dispatching a fresh verifier, committing/pushing when applicable, persisting final Root Closure Evidence/Reconciliation, and closing the ticket.

This skill does not replace `$verify-code`, `$verify-spec`, or `$review-spec`.
