---
name: verify-root-closure
description: Independently verify Root Blocker closure for a Spec Review remediation ticket in the fresh non-mutating verifier subagent dispatched by `$implement-ticket` after explicit human authorization.
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Verify Root Closure

Independently certify or reject closure of one Root Blocker for a **Spec Review remediation ticket**.

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

### Preservation Obligations

Every carried satisfied cell applicable to the current root remains a preservation obligation.

Verify preservation when the ticket changes a surface or contract that can affect it.

Do not treat satisfied cells as new remediation work.

Do not omit them merely because prior tickets or closure evidence previously established them.

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

Evaluate every applicable:

1. remediation obligation;
2. verification obligation;
3. preservation obligation;
4. carried acceptance cell;
5. material manifestation found by the independent Root Invariant Sweep.

For each:

1. inspect the actual source path;
2. verify required production composition/wiring where relevant;
3. identify concrete source/test evidence;
4. determine whether that evidence proves the invariant at the required boundary;
5. record `proven`, `violated`, or `unproven`.

A result is `proven` only when evidence establishes the required behavior.

Unless the obligation itself is lower-level, the following are insufficient:

* aggregate test counts;
* mock-only proof of production composition;
* request forwarding without proving acquisition/consumption;
* schema/read coverage without required write/lifecycle proof;
* helper-level success when the required production boundary differs;
* unsupported assertions in Proposed Root Closure Evidence.

When fail-closed behavior is required, verify applicable:

* absence;
* mismatch;
* substitution;
* malformed input;
* stale/replayed state;
* persistence failure;
* unavailable evidence;
* bypass;
* alternate authority/evidence-selection paths.

If accepted architecture already determines a responsibility but implementation is missing or incorrect, classify it as an **implementation violation**, not unresolved architecture.

If proceeding would genuinely require a new durable architectural choice, record an `architecture-blocker candidate`.

Do not resolve, route, or remediate it here.

## 5. Failure Accumulation Invariant

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

## 6. Verify Protected Roots

For every independently derived protected root:

1. recover its invariant and applicable existing acceptance/regression proof;
2. inspect the modified shared surface;
3. rerun only proof affected by the current ticket;
4. record whether the root remains preserved.

If adequate proof cannot establish preservation, mark the protected root `unproven`.

A protected root contributes to final `FAIL` when violated or unproven.

Continue verifying remaining protected roots after discovering one failure.

## 7. Verification Scope

Run only checks required to establish:

* current-root closure;
* same-root preservation obligations;
* affected protected-root preservation;
* independent Root Invariant Sweep coverage.

Targeted tests spanning production composition or sibling surfaces are required when necessary proof; they are not optional broad verification.

Do not run unrelated:

* full test suites;
* repository-wide lint/type checks;
* coverage suites;
* integration suites unrelated to the root.

Do not fix failures.

A failed targeted check is recorded and does not terminate the bounded scan unless it invalidates verifier integrity.

## 8. Worktree Fingerprint

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

## 9. Verdict

Emit a verdict only after the complete bounded scan and final fingerprint succeed.

### PASS

Return `PASS` only when:

* every remediation obligation is proven;
* every applicable verification obligation is proven;
* every carried acceptance cell is proven;
* every preservation obligation remains proven;
* the independent Root Invariant Sweep finds no remaining in-scope violation;
* required production composition and sibling surfaces are proven;
* required negative/fail-closed behavior is proven;
* every protected root is preserved;
* Proposed Root Closure Evidence contains no materially unsupported claim.

Use:

```text
ROOT CLOSURE: PASS

Root: RB-<n> — <invariant>
Production path: <path proven>

Acceptance:
- <cell>: proven — <evidence>

Preservation obligations:
- <cell>: preserved — <evidence>
- or None

Invariant sweep:
- <surface>: clean/proven — <evidence>

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

Current-root failures:
- <surface/cell>: violated|unproven — <concrete evidence>
- ...

Preservation failures:
- <cell>: violated|unproven — <concrete evidence>
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

A valid verifier execution completes with exactly one independent verdict after the bounded scan:

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