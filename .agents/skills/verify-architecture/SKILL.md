---
name: verify-architecture
description: Enforce Polaris's mechanically observable architecture invariants by running the complete architecture guard suite, repairing violations when current authority determines the correct state, and failing closed when durable architecture is unresolved.
compatibility: product=codex product=claude-code system=git system=python network=none
---

# Architecture Invariant Verification

## Objective

Keep accepted Polaris architecture continuously executable and regression-protected.

This skill owns one repository invariant gate:

> **The complete architecture suite passes with zero failures, and the live greenfield repository has zero mechanically detectable architecture violations.**

The architecture guard and its tests are executable representations of accepted architecture. They are not architecture authority themselves. Resolve architectural meaning from the current non-legacy authority ordering in `AGENTS.md`.

## Applicability

Invoke this skill when the candidate can affect a mechanically enforced architecture invariant, including when it changes:

* current Python source under `src/polaris/`;
* current tests under `tests/`;
* current Python migrations scanned by `tests/architecture_guard.py`;
* `tests/architecture_guard.py` or any architecture-guard test;
* accepted architecture authority whose mechanically enforceable rule is represented by the architecture guard.

Do not invoke it merely because unrelated documentation, tracker state, Project projection, or other non-architecture administrative state changed.

Applicability controls **whether** the gate runs. Once applicable, verification scope is the complete architecture suite; do not narrow it to changed files, one ticket, one Spec obligation, or one rule.

## Architecture Rule Admission Invariant

A rule belongs in the architecture guard only when all of the following are true:

1. current accepted authority establishes a durable architectural invariant;
2. the invariant is mechanically observable from the repository surface the guard can inspect;
3. detection can be implemented with sufficiently low false-positive risk;
4. the checker and independent falsifier tests can express both prohibited and adjacent-valid states where material.

Do not turn style preferences, speculative future architecture, subjective design taste, or ordinary code-quality concerns into architecture rules.

Do not make a new architecture rule merely because a verifier would prefer one. If current authority does not establish the durable semantic, the result is unresolved architecture.

## Complete Architecture Suite

The current suite is:

```text
tests/test_architecture_guard.py
tests/test_architecture_guard_identity_aliases.py
tests/test_architecture_guard_legacy_loaders.py
```

Before every pytest invocation, perform the mandatory test-service preflight from `AGENTS.md`. Re-derive prerequisites from the current complete suite rather than assuming they remain service-free forever. Do not use pytest startup, timeout, skip, or connection failure as the preflight.

### Non-Mutating Verification Environment

Architecture verification must not build/install Polaris, synchronize or rewrite the project environment, create/update `uv.lock`, or otherwise mutate repository state merely to execute the invariant suite.

Prefer the already-provisioned repository virtualenv when it has pytest:

```bash
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-architecture \
  .venv/bin/pytest -q \
  tests/test_architecture_guard.py \
  tests/test_architecture_guard_identity_aliases.py \
  tests/test_architecture_guard_legacy_loaders.py
```

If `.venv/bin/pytest` is unavailable, use an isolated non-project, offline uv invocation that may consume only already-cached pytest artifacts:

```bash
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-architecture \
  uv run --no-project --offline --no-python-downloads \
    --with 'pytest>=9.1.1' \
    pytest -q \
    tests/test_architecture_guard.py \
    tests/test_architecture_guard_identity_aliases.py \
    tests/test_architecture_guard_legacy_loaders.py
```

Do not use ordinary project-aware `uv run pytest ...` for this gate. Project-aware `uv run` may synchronize the environment, build/install Polaris, and create/update `uv.lock`.

If neither non-mutating execution path can run the complete suite, classify the result `environment-or-tooling-blocker`. Do not relax the invariant by allowing a project sync.

Before and after execution, require the repository's tracked/untracked `uv.lock` state to be unchanged. Never delete or rewrite a pre-existing lockfile as part of verification cleanup; unexpected lockfile mutation is itself a verification-environment defect that must be reported and corrected at the invocation mechanism.

When a parent caller has an even stricter non-mutating verification rule, preserve the stricter caller rule.

The suite is intentionally complete because it proves two distinct things together:

* the guard still detects the prohibited architecture states it claims to detect while permitting adjacent-valid states; and
* the current greenfield repository satisfies those mechanically enforced rules.

Do not replace the complete suite with only the live-repository assertion.

## Failure Classification and Repair Loop

A non-zero architecture-suite failure count is non-terminal.

For every failure, inspect current authority and classify it as exactly one of:

```text
repository-violation
guard-defect
authority-realization
unresolved-architecture
environment-or-tooling-blocker
```

### `repository-violation`

Current accepted authority already determines the correct architecture and current repository code violates it.

Repair the narrowest authoritative implementation point, then rerun the complete architecture suite.

Examples include an inward layer importing an outward layer, current code depending on `legacy/`, or a vendor-native representation crossing a boundary that accepted architecture already forbids.

### `guard-defect`

Current accepted authority is clear, but the checker or its falsifier tests encode it incorrectly or incompletely.

Repair the checker/test representation from current authority. Keep independent expectation matrices independent of checker implementation constants; do not make tests self-confirming merely to restore green.

Then rerun the complete architecture suite.

### `authority-realization`

Accepted architecture intentionally changed and current checker/tests have not yet been updated to represent that already-authorized rule.

Update the checker and its independent acceptance/falsifier coverage together. Do not treat stale executable architecture as higher authority than the accepted decision.

Then rerun the complete architecture suite.

### `unresolved-architecture`

Proceeding would require inventing, changing, or choosing a durable architectural owner, boundary, dependency direction, identity/key semantic, lifecycle rule, failure semantic, or other architectural invariant not determined by current authority.

Do not repair toward whichever state makes pytest pass. Return the complete blocker set to the owning lifecycle so it can route through `$architecture-remediation`.

### `environment-or-tooling-blocker`

The complete suite cannot be executed or interpreted reliably because a required tool/environment prerequisite is unavailable or broken.

Report the exact blocker. Do not claim PASS from partial execution.

## Repair Authority

When delegated by another workflow, this skill owns only the repository mutations required to restore **already-determined mechanically enforced architecture**:

* fixing a repository architecture violation;
* fixing the guard/tests to match current accepted authority;
* realizing an already-accepted architecture change in the guard/tests.

This is explicit repository-wide architecture-gate repair authority. It does not authorize unrelated cleanup or new architectural decisions.

Return every changed path and failure disposition to the caller. The caller remains responsible for rerunning any non-architecture verification invalidated by those repairs, such as Ruff, Mypy, targeted behavioral tests, migration lifecycle proof, exact-HEAD certification, or candidate-state checks.

Do not recursively invoke `$verify-code` when `$verify-code` is the caller.

## Forbidden Pass-Only Repairs

Do not make the architecture gate green by:

* deleting or weakening a valid architecture rule without current authority;
* changing an independent expected matrix to derive from the checker implementation it is supposed to challenge;
* adding `skip`, `xfail`, marker filtering, test deselection, or path exclusions merely to hide a failing invariant;
* treating tests as a fifth product layer or inventing another scope category unless current authority establishes it;
* excluding a current source/test/migration path because it now violates the guard;
* preserving a forbidden dependency behind a wrapper, alias, loader indirection, compatibility shim, or other concealment;
* changing architecture authority inside this verification skill merely to fit implementation reality.

If a mechanically enforced rule has become wrong, first establish the authoritative architecture change through the owning architecture lifecycle. Then update its executable representation.

## Parent Workflow Composition

### `$verify-code`

When applicable, `$verify-code` invokes this gate in addition to its targeted Ruff, Mypy, and behavioral-test verification. Architecture remains whole-suite even though those other checks stay targeted.

If this skill repairs executable source/tests, return the changed paths so `$verify-code` expands/re-runs its affected target verification before reporting success.

### `$database-migrations`

When current migration Python changes, `$database-migrations` invokes this gate because current migrations are part of the architecture guard's scan universe. If this skill repairs a migration, the migration owner reruns every invalidated migration lifecycle proof.

### `$verify-spec`

When the integrated Spec contains architecture-capable changes, `$verify-spec` invokes this gate as an explicit repository-wide delegated invariant. Architecture repairs are authorized by this child gate even when the repaired surface is outside the ordinary Spec semantic repair scope; that exception applies only to mechanically enforced architecture repair under this skill.

Any repair changes the candidate and invalidates prior exact-HEAD semantic certification normally.

## Terminal Result

Report PASS only after the complete suite actually passes and the live-repository assertion establishes zero violations:

```text
ARCHITECTURE INVARIANT: PASS

Architecture suite: <passed>/<collected>
Architecture suite failures: 0
Live repository architecture violations: 0
Unresolved architecture questions: 0
Environment/tooling blockers: 0
Repairs:
- Repository violations repaired: <n>
- Guard defects repaired: <n>
- Accepted-authority realizations repaired: <n>
```

When unresolved architecture remains, return:

```text
ARCHITECTURE INVARIANT: UNRESOLVED

Architecture suite failures: <n>
Unresolved architecture questions: <n>
Blockers:
- <question/conflict + current authority evidence + material consequence>
```

Do not report PASS with a non-zero suite failure count, a non-zero live repository violation count, incomplete suite execution, unresolved architectural semantics, or verification-environment mutation.
