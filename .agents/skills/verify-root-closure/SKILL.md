---
name: verify-root-closure
description: Invoked only by `$implement-ticket` for Spec Review remediation — independently verify that the current Root Blocker is closed and affected satisfied roots remain preserved before commit and closure.
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Verify Root Closure

Invoked only by `$implement-ticket` for a **Spec Review remediation ticket**. Do not invoke as a standalone workflow.

`$implement-ticket` invokes this in a **fresh read-only subagent** after implementation, targeted verification, and proposed Root Closure Evidence are complete, but before commit, push, Root Closure Evidence persistence, or ticket closure.

Independently certify or reject closure of one Root Blocker.

Do not modify source, tests, docs, wiki, tracker state, commits, or architecture.

The implementer's proposed Root Closure Evidence is a set of claims to verify, not authority.

## 1. Recover Closure State

Read:

* the full remediation ticket;
* parent Spec;
* latest Spec Review / Root Blocker Ledger;
* current Root Blocker invariant and carried acceptance cells;
* named production paths and sibling surfaces;
* previously satisfied Root Blockers;
* applicable accepted architecture referenced by the ticket;
* proposed Root Closure Evidence.

Use the caller-provided `TICKET_BASELINE`.

Inspect the current implementation state:

```bash
git status --short
git diff --name-status "$TICKET_BASELINE"
```

Search before reading. Locate relevant symbols, contracts, citations, or call sites, then read the smallest useful surrounding regions.

Do not rely on the implementer's narrative to determine what changed or what must be proven.

## 2. Derive Closure Obligations Independently

The Root Blocker invariant is authoritative over enumerated acceptance cells.

Independently derive the contract surface required to prove the root, including applicable:

* constructors/factories and defaults;
* producers;
* persistence/result boundaries;
* adapters/facades;
* callers and consumers;
* DI/bootstrap/composition;
* named production entrypoints;
* sibling surfaces;
* negative/bypass paths;
* tests representing those paths.

Do not expand into unrelated review.

### Protected Roots

From the latest Spec Review state, independently derive previously satisfied Root Blockers whose governed surfaces/contracts intersect the current ticket's modified surfaces.

Relevant intersections include the same:

* production path;
* façade/service/repository;
* typed contract or evidence object;
* adapter/persistence boundary;
* canonical owner;
* explicitly named sibling surface.

Protected roots are **Root Blocker IDs**, not remediation-ticket numbers.

Do not trust the implementer's protected-root list.

## 3. Verify the Current Root

For every carried acceptance cell and material manifestation found by the independent Root Invariant Sweep:

1. inspect the actual source path;
2. verify required production composition/wiring where relevant;
3. identify concrete source/test evidence claimed as proof;
4. determine whether that evidence proves the invariant at the required boundary.

A result is `proven` only when its evidence establishes the required behavior.

Unless the obligation itself is lower-level, the following are insufficient:

* aggregate test counts;
* mock-only proof of production composition;
* request forwarding without proving acquisition/consumption;
* schema/read coverage without required write/lifecycle proof;
* helper-level success when the required production boundary differs;
* unsupported assertions in proposed closure evidence.

When fail-closed behavior is required, verify applicable absence, mismatch, substitution, malformed, persistence-failure, or bypass cases.

If accepted architecture already determines a responsibility but its implementation is missing or incorrect, classify it as an **implementation violation**, not unresolved architecture.

If proceeding would genuinely require a new durable architectural choice, report an `architecture-blocker candidate`. Do not resolve or route it here.

## 4. Verify Protected Roots

For every independently derived protected root:

1. recover its invariant and applicable existing acceptance/regression proof;
2. inspect the modified shared surface;
3. rerun only proof affected by the current ticket;
4. confirm the root remains satisfied.

If adequate proof cannot establish preservation, mark the root `unproven`.

A protected root fails closure when violated or unproven.

## 5. Verification Scope

Run only checks required to establish current-root closure or protected-root preservation.

Targeted tests spanning production composition or sibling surfaces are required when they are necessary proof; they are not optional broad verification.

Do not run unrelated:

* full test suites;
* repository-wide lint/type checks;
* coverage suites;
* integration suites unrelated to the root.

Do not fix failures.

## 6. Worktree Fingerprint

On `PASS`, record the exact verified implementation state:

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

Any implementation change after `PASS` makes the verdict stale and requires `$implement-ticket` to invoke a **fresh** `$verify-root-closure`.

## 7. Verdict

### PASS

Return `PASS` only when:

* every carried acceptance cell is proven;
* the independent Root Invariant Sweep finds no remaining in-scope violation;
* required production composition and sibling surfaces are proven;
* required negative/fail-closed behavior is proven;
* every protected root is preserved;
* proposed Root Closure Evidence contains no materially unsupported claim.

Use:

```text
ROOT CLOSURE: PASS

Root: RB-<n> — <invariant>
Production path: <path proven>

Acceptance:
- <cell>: proven — <evidence>

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

If any required obligation is violated or unproven, return:

```text
ROOT CLOSURE: FAIL

Root: RB-<n> — <invariant>

Current-root failures:
- <surface/cell>: violated|unproven — <concrete evidence>

Protected-root failures:
- RB-<n>: violated|unproven — <concrete evidence>
- or None

Architecture-blocker candidates:
- <candidate and evidence>
- or None

Required correction:
- <smallest concrete implementation/proof gap>
```

Do not downgrade required failures to advisory findings.

## Completion

This skill completes with exactly one independent verdict:

* `ROOT CLOSURE: PASS`; or
* `ROOT CLOSURE: FAIL`.

`FAIL` keeps the remediation ticket open.

`$implement-ticket` alone owns:

* correcting failures;
* applying its Architecture vs. Implementation Test to architecture-blocker candidates;
* rerunning affected verification;
* invoking a fresh `$verify-root-closure`;
* committing and pushing;
* persisting final Root Closure Evidence;
* closing the ticket.

This skill does not replace `$verify-code`, `$verify-spec`, or `$review-spec`.
