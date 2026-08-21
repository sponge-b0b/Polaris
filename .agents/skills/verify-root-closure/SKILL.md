---
name: verify-root-closure
description: Independently verify Root Blocker closure for a Spec Review remediation ticket in the fresh non-mutating verifier subagent dispatched by `$implement-ticket` after explicit human authorization.
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Verify Root Closure

Independently certify or reject closure of one Root Blocker for a **Spec Review remediation ticket**.

Closure certification is coverage-driven. A `PASS` must prove the complete current Root Blocker contract against the current repository state. Prior `PASS`, `satisfied`, `preserved`, or closure status is durable history and routing context, never current proof.

## Invocation Semantics

When the human explicitly invokes `$verify-root-closure` in response to the Root Closure Human Handoff from `$implement-ticket`, that invocation is an **authorization event**, not authorization for the `$implement-ticket` main agent to perform certification.

The main agent must resume `$implement-ticket` at its verifier-dispatch checkpoint and spawn exactly one fresh verifier subagent.

Only that fresh verifier executes the procedure below.

If this skill is being executed directly by the `$implement-ticket` main agent, do not perform certification or emit a root-closure verdict.

## Non-Mutating Leaf Verifier

`$verify-root-closure` is a **non-mutating leaf workflow**.

It may:

* read and search repository/tracker evidence;
* inspect Git state and history;
* run targeted checks required for current-root closure or preservation obligations.

It must not:

* edit, create, delete, move, format, or generate repository files;
* modify Git, branch, commit, or tracker state;
* run fixers or repository-mutating commands;
* perform implementation or remediation;
* invoke implementation/remediation workflows;
* delegate or spawn another agent or subagent.

A discovered implementation defect is evidence for `ROOT CLOSURE: FAIL`, never authorization to repair it.

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
* Proposed Root Closure Evidence.

Use the caller-provided `TICKET_BASELINE`.

Inspect the current implementation state:

```bash
git status --short
git diff --name-status "$TICKET_BASELINE"
```

Search before reading. Locate relevant symbols, contracts, citations, and call sites, then read the smallest useful surrounding regions.

Do not rely on the implementer's narrative to determine what changed or what must be proven.

If required durable closure state cannot be recovered, verification is invalid and must halt before the root scan.

## 2. Establish Verifier Integrity

Before substantive verification, establish that the verification run itself is valid.

Fail immediately without continuing the scan if:

* required ticket/root state cannot be recovered;
* `TICKET_BASELINE` is invalid or unavailable;
* the required repository state cannot be inspected;
* the verifier mutates repository/tracker state;
* the verifier delegates or spawns another agent;
* the repository implementation state changes during verification;
* another condition makes subsequent evidence untrustworthy.

These are **verifier-integrity failures**, not Root Blocker implementation failures.

Do not emit `ROOT CLOSURE: PASS` or `ROOT CLOSURE: FAIL` from an invalid run.

Return the invalidation reason to `$implement-ticket`, which owns recovery and fresh dispatch.

## 3. Derive Closure Obligations Independently

The stable Root Blocker invariant is authoritative over enumerated symptoms.

The cumulative acceptance contract remains required evidence and must not be silently narrowed.

Independently derive the bounded contract surface required to prove the root, including applicable:

* constructors/factories and defaults;
* producers;
* persistence/result boundaries;
* adapters/facades;
* callers and consumers;
* DI/bootstrap/composition;
* named production entrypoints;
* sibling surfaces;
* publication/release/materialization boundaries;
* negative/bypass paths;
* tests representing those paths.

Do not expand into unrelated review.

### Root Closure Coverage Manifest

Before evaluating closure, build a **Root Closure Coverage Manifest** with stable `RC-<n>` cells.

Create cells for every applicable:

* remediation obligation;
* verification obligation;
* carried acceptance cell, including cells already recorded as satisfied;
* same-root preservation obligation;
* production/composition/sibling surface independently required by the stable invariant;
* negative, bypass, fail-closed, alternate-authority, or alternate-evidence-selection path independently required by the stable invariant.

Each cell records:

```text
Coverage: RC-<n>
Kind: <remediation | verification | acceptance | preservation | invariant-sweep>
Obligation: <exact durable obligation or invariant-derived requirement>
Surfaces: <source/test/production surfaces requiring inspection>
State: <unchecked | proven | violated | unproven>
Evidence: <current evidence when dispositioned>
```

Rules:

* construct the manifest from durable root state, the stable invariant, authoritative Spec/architecture, and current repository discovery — not from the implementer's Proposed Root Closure Evidence;
* prior closure evidence may identify useful symbols, tests, or surfaces to re-check, but it must not initialize a cell as `proven`;
* a prior `PASS`, `satisfied`, `satisfied/closed`, `preserved`, unchanged-file status, or ticket closure is never current proof;
* do not silently remove or merge materially distinct carried cells;
* if the scan discovers another material manifestation of the same stable invariant, add an `invariant-sweep` cell and evaluate it before verdict;
* only durable state that explicitly supersedes, retires, or Owner-overrides an obligation removes it from the current-root manifest.

Coverage is complete only when every manifest cell is `proven`, `violated`, or `unproven` and `unchecked = 0`.

### Preservation Obligations

Every carried satisfied cell applicable to the current root remains a current closure obligation.

Re-prove each carried same-root cell against the current repository state even when the current remediation ticket did not modify its surface.

Do not treat satisfied cells as new remediation work, but do not accept their historical status as proof.

This same-root rule is intentionally stronger than protected-root verification below: previously missed sibling or bypass defects must be discoverable before the root can close again.

### Protected Roots

From the latest Spec Review state, independently derive previously satisfied **other Root Blockers** whose governed surfaces/contracts intersect the current ticket's modified surfaces.

Relevant intersections include the same:

* production path;
* façade/service/repository;
* typed contract or evidence object;
* adapter/persistence boundary;
* canonical owner;
* explicitly named sibling surface.

Protected roots are Root Blocker IDs, not remediation-ticket numbers.

Do not trust the implementer's protected-root list.

## 4. Verify the Current Root

Evaluate every `RC-*` cell in the Root Closure Coverage Manifest.

For each:

1. inspect the actual current source path;
2. verify required production composition/wiring where relevant;
3. identify concrete current source/test evidence;
4. determine whether that evidence proves the invariant at the required boundary;
5. record `proven`, `violated`, or `unproven` with evidence.

A result is `proven` only when current evidence establishes the required behavior.

Never mark a cell `proven` solely because:

* a prior verifier passed it;
* durable state says `satisfied` or `preserved`;
* the implicated code is unchanged from an earlier reviewed HEAD;
* a previous ticket claimed the obligation was fixed;
* the implementer's Proposed Root Closure Evidence says it is covered.

Unchanged code may help bound history analysis, but current source/test evidence is still required.

Unless the obligation itself is lower-level, the following are insufficient:

* aggregate test counts;
* mock-only proof of production composition;
* request forwarding without proving acquisition/consumption;
* schema/read coverage without required write/lifecycle proof;
* helper-level success when the required production boundary differs;
* unsupported assertions in Proposed Root Closure Evidence.

When fail-closed or caller-exclusion behavior is required, verify applicable:

* absence;
* mismatch;
* substitution;
* malformed input;
* stale/replayed state;
* persistence failure;
* unavailable evidence;
* bypass;
* optional/`None` dependencies and default-success paths;
* direct-construction and compatibility paths;
* caller-selected identity/correlation/version/tier/authority/provenance;
* metadata, mapping, type-recovery, or forged-context authority/evidence paths;
* alternate authority/evidence-selection paths.

### Adversarial Root Invariant Sweep

After dispositioning explicit remediation and carried acceptance cells, independently sweep from the **stable Root Blocker invariant outward** rather than from the ticket diff inward.

Use repository/source search to locate all materially relevant current implementations, callers, sibling transports, constructors/defaults, registration/bootstrap paths, persistence/reconstruction paths, and success/failure branches that could satisfy or bypass the invariant.

For negative invariants, explicitly search for alternate ways the forbidden behavior could still occur. Do not infer root closure merely because the intended canonical path exists.

The sweep is bounded by the stable root invariant, but it may and often must inspect unchanged files outside the current ticket diff.

Add every newly discovered material same-root manifestation to the Coverage Manifest and disposition it before verdict.

If accepted architecture already determines a responsibility but implementation is missing or incorrect, classify it as an **implementation violation**, not unresolved architecture.

If proceeding would genuinely require a new durable architectural choice, record an `architecture-blocker candidate`.

Do not resolve, route, or remediate it here.

## 5. Root Closure Completeness Gate

Do not proceed to a verdict until the Root Closure Coverage Manifest is complete.

Require:

```text
Root coverage: <n> cells; proven <n>; violated <n>; unproven <n>; unchecked 0
```

The verifier must be able to account for every carried acceptance cell and every material same-root surface discovered by the invariant sweep.

A summary statement such as “prior cells preserved,” “previous closure remains valid,” or “no affected changes” cannot substitute for per-cell current evidence.

A root with any `violated` or `unproven` cell cannot pass.

## 6. Failure Accumulation Invariant

Once a valid verification scan begins, **do not fail fast on implementation or proof defects**.

When any current-root, preservation, protected-root, negative-path, production-composition, or proof obligation fails:

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

1. recover its invariant and applicable existing acceptance/regression proof;
2. inspect the modified shared surface;
3. rerun only proof affected by the current ticket;
4. record whether the root remains preserved.

If adequate proof cannot establish preservation, mark the protected root `unproven`.

A protected root contributes to final `FAIL` when violated or unproven.

Continue verifying remaining protected roots after discovering one failure.

## 8. Verification Scope

Run only checks required to establish:

* complete current-root coverage;
* same-root carried acceptance and preservation obligations;
* affected protected-root preservation;
* independent Root Invariant Sweep coverage.

The current-root boundary is the stable Root Blocker invariant, not the current ticket diff.

Inspecting unchanged sibling/source paths required to prove that invariant is targeted root verification, not unrelated broad review.

Targeted tests spanning production composition or sibling surfaces are required when necessary proof; they are not optional broad verification.

Do not run unrelated:

* full test suites;
* repository-wide lint/type checks;
* coverage suites;
* integration suites unrelated to the root.

Do not fix failures.

A failed targeted check is recorded and does not terminate the bounded scan unless it invalidates verifier integrity.

## 9. Worktree Fingerprint

After the bounded scan, confirm and record the exact verified implementation state:

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

Return both:

* `TICKET_BASELINE`;
* `ROOT_CLOSURE_STATE`.

The caller-provided candidate state and returned `ROOT_CLOSURE_STATE` must describe the same state.

If the implementation state changed during verification, invalidate the run rather than reconcile it.

`$implement-ticket` owns candidate-state integrity and verdict invalidation.

Any implementation change after a valid `PASS` makes that verdict stale.

## 10. Verdict

Emit a verdict only after the complete bounded scan, Root Closure Completeness Gate, and final fingerprint succeed.

### PASS

Return `PASS` only when:

* Root Closure Coverage Manifest has `unchecked 0`;
* every remediation obligation is proven;
* every applicable verification obligation is proven;
* every carried acceptance cell has current proof;
* every same-root preservation obligation has current proof;
* the adversarial Root Invariant Sweep finds no remaining in-scope violation;
* required production composition and sibling surfaces are proven;
* required negative/fail-closed behavior is proven;
* every protected root is preserved;
* Proposed Root Closure Evidence contains no materially unsupported claim.

Use:

```text
ROOT CLOSURE: PASS

Root: RB-<n> — <invariant>
Production path: <path proven>
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

TICKET_BASELINE: <sha>
ROOT_CLOSURE_STATE: <sha256>
```

Do not emit `PASS` with qualifications.

### FAIL

If one or more required obligations are violated or unproven, return **all independently supported failures discovered during the completed bounded scan**:

```text
ROOT CLOSURE: FAIL

Root: RB-<n> — <invariant>
Root coverage: <n> cells; proven <n>; violated <n>; unproven <n>; unchecked 0

Current-root failures:
- RC-<n> <surface/cell>: violated|unproven — <concrete evidence>
- ...

Preservation failures:
- RC-<n> <cell>: violated|unproven — <concrete evidence>
- or None

Protected-root failures:
- RB-<n>: violated|unproven — <concrete evidence>
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

TICKET_BASELINE: <sha>
ROOT_CLOSURE_STATE: <sha256>
```

Do not stop after the first failure.

Do not duplicate one underlying failure as several corrections unless the failures are independently actionable.

Do not downgrade required failures to advisory findings.

Do not repair any failure before returning the verdict.

## Completion

A valid verifier execution completes with exactly one independent verdict after the complete bounded coverage scan:

* `ROOT CLOSURE: PASS`; or
* `ROOT CLOSURE: FAIL`.

A verifier-integrity failure produces no closure verdict and requires fresh dispatch.

`FAIL` keeps the remediation ticket open.

`$implement-ticket` alone owns:

* correcting consolidated failures;
* applying its Architecture vs. Implementation rule to architecture-blocker candidates;
* rerunning affected implementation verification;
* rebuilding Proposed Root Closure Evidence;
* requesting fresh human authorization;
* dispatching a fresh `$verify-root-closure` verifier;
* committing and pushing;
* persisting final Root Closure Evidence;
* closing the ticket.

This skill does not replace `$verify-code`, `$verify-spec`, or `$review-spec`.
