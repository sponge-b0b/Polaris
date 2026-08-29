---
name: verify-code
description: Performs diff hygiene, contract-impact closure, syntax/format/static typing verification, and targeted testing on Python files modified in the workspace or active ticket.
compatibility: product=codex product=claude-code system=git system=python network=none
---

# Targeted Codebase Verification Standards

## Objective

Verify changes introduced by the current workspace or active ticket without broadening execution into repository-wide verification.

`$coding-standards` owns coding policy. Verify applicable requirements without duplicating that skill.

Repository-wide discovery is required when necessary to prove that an authoritative contract change has no stale internal consumers. Broaden discovery, not verification indiscriminately.

## Guardrails

* Verify only the active change and directly affected tests.
* Resolve target files before verification.
* When a shared contract changes, discover its complete affected consumer set before declaring verification scope complete.
* Do not refactor unrelated code, weaken configuration, or add pass-only suppressions.
* Shell permissions do not authorize broader verification.
* Do not bypass repository command guards.
* Deterministic whitespace defects owned by the active change are mechanical fixes: fix them, rerun the check, and continue without asking.
* Do not modify semantic content while fixing whitespace.
* Unrelated pre-existing whitespace remains report-only.

## 1. Identify Targets

If called by `$implement-ticket` with a ticket baseline, include committed Python changes since that baseline:

```bash
git diff --name-only --diff-filter=ACMR <ticket-baseline>...HEAD -- '*.py'
```

Also include unstaged, staged, and untracked Python changes:

```bash
git diff --name-only --diff-filter=ACMR -- '*.py'
git diff --cached --name-only --diff-filter=ACMR -- '*.py'
git ls-files --others --exclude-standard -- '*.py'
```

Use the deduplicated union as Python verification targets.

If no ticket baseline applies, use workspace changes only.

Do not broaden scope because no Python targets exist.

### Contract-Impact Closure

Inspect the active diff before finalizing the target set.

This gate applies when the change modifies a shared internal contract or semantic owner, including an API/call signature, protocol/interface, identity source, lifecycle responsibility, canonical representation, enum/value contract, configuration key, or other reusable boundary.

When applicable:

1. identify the superseded contract or ownership rule;
2. search the repository for every affected caller, implementation, protocol, adapter, fake, fixture, test, configuration surface, registry/bootstrap path, and other consumer;
3. inspect dynamic/indirect consumers when literal search cannot establish closure;
4. add consumers requiring migration to the affected verification set;
5. require zero unexplained consumers of the superseded contract before verification may pass.

Internal source compatibility is not assumed. Apply `$coding-standards` **Authoritative Contract Changes and Compatibility** exactly; do not preserve stale consumers with ignored parameters, compatibility sinks, aliases, shims, fallback paths, or similar residue merely to keep them compiling.

If explicit authority requires genuine compatibility, verify that it is isolated at the compatibility boundary and that the canonical internal contract remains clean.

Repository-wide consumer discovery does not by itself authorize a full-suite pytest run or unrelated cleanup. Keep Ruff, Mypy, and test execution targeted to the changed contract and affected consumers.

## 2. Diff Hygiene

When a ticket baseline exists, check the complete active ticket patch including current working-tree fixes:

```bash
git diff --check <ticket-baseline>
```

Without a ticket baseline:

```bash
git diff --check
git diff --cached --check
```

For findings owned by the active change:

* trailing whitespace, space-before-tab, or whitespace-only line defects → fix mechanically and rerun `git diff --check`;
* unresolved conflict markers → Blocking; investigate rather than treating them as whitespace cleanup.

Do not ask for confirmation for deterministic whitespace-only fixes.

Do not alter unrelated pre-existing files merely to make this check clean.

## 3. Ruff

Run only against resolved Python targets:

```bash
uv run ruff format --check <changed_python_paths>
uv run ruff check <changed_python_paths>
```

Do not replace targets with `.`.

## 4. Mypy

Run only against changed Python files and directly affected tests:

```bash
uv run mypy --explicit-package-bases <changed_python_paths_and_affected_tests>
```

Do not broaden to `mypy .`.

## 5. Targeted Tests

Run tests relevant to the changed behavior and directly affected modules:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/path/to/test_relevant_module.py
```

Do not run the full suite by default.

Before any pytest invocation, follow the mandatory test-service preflight in
`AGENTS.md` and `docs/process/testing-guide.md`. Determine the selected scope's
complete external prerequisites and verify them before pytest starts. Missing
prerequisites leave required verification unresolved.

If a required targeted test skips solely because repository-local setup is absent:

* inspect repository configuration;
* derive safe local configuration when unambiguous;
* start only an authorized required service;
* rerun the exact test.

Never print secrets or authenticated connection strings.

If setup cannot be safely resolved, report the check as unresolved.

Do not broaden testing to compensate.

## 6. Coding Standards

Inspect changed code for `$coding-standards` requirements implicated by the diff, such as:

* data-contract and typing boundaries;
* score semantics and precision;
* async behavior;
* observability;
* resource ownership;
* authoritative contract changes and compatibility;
* structural design rules.

Do not manufacture work for unrelated standards.

## Failure Handling

When a targeted check fails:

1. determine whether the active change owns it;
2. fix the narrowest authoritative point within scope;
3. rerun the affected check.

A stale or unexplained consumer found by Contract-Impact Closure is Blocking for the active contract change. Fix the consumer or identify explicit compatibility authority; do not weaken the authoritative contract to make the stale consumer pass.

For deterministic whitespace-only failures, fix mechanically without confirmation.

Do not:

* use Ruff `--add-noqa`;
* weaken repository configuration;
* add pass-only suppressions;
* broaden verification to compensate for failure.

If a failure cannot be safely resolved within scope, report the affected file/test, failed check, concise error, and required next action.

## Reporting

Distinguish:

* targeted verification actually run;
* contract-impact closure status when applicable;
* whitespace defects mechanically fixed;
* unresolved/skipped targeted checks;
* broader verification not run.

On success:

```text
Targeted verification passed.

- Contract-impact closure: passed | not applicable
- Diff hygiene: passed
- Ruff format: passed
- Ruff lint: passed
- Mypy: passed
- Targeted tests: passed
- Applicable coding standards: verified

Full repository verification was not run.
```

If any required contract-impact discovery or targeted check remains unresolved, do not report targeted verification as passed.

## Transition-Bound Contract Consumer Closure

Whenever Contract Migration Proof applies, `Contract-impact closure: passed` requires an explicit working **Consumer Closure Manifest**. Searching for known obsolete symbols or broad sinks is supporting evidence; it does not define the consumer universe.

Derive candidate consumers from the authoritative contract and repository relationships/callers/composition/test substitutions/configuration surfaces that can exercise or model that contract. Every discovered candidate receives exactly one row:

```text
Consumer: CC-<n>
Surface: <path/symbol/config/test seam>
Role: <caller | implementation | protocol | adapter | fake/fixture | bootstrap/composition | configuration | other>
Authoritative contract: <exact contract/source>
Disposition: <conforming | migrated | retained-by-authority | unresolved>
Evidence: <direct current evidence>
```

Rules:

* `conforming` means the current consumer directly satisfies the authoritative contract;
* `migrated` means an old contract use was found and current state proves migration;
* `retained-by-authority` requires explicit current authority for compatibility; convenience or a passing test is insufficient;
* `unresolved` prevents contract-impact closure;
* a candidate may not disappear because it is unchanged, inherited, test-only, indirect, already searched by name, or outside the changed-file list.

Before `Contract-impact closure: passed` require:

```text
Contract consumer candidates: <n>
Consumer closure rows: <n>
Unclassified candidates: 0
Unresolved consumers: 0
Retained compatibility without authority: 0
```

Then apply the general counterexample-survivability question to the closure claim: could every cited check pass while an authoritative consumer still accepts, emits, models, or depends on the obsolete contract? If yes, closure remains unresolved.

The final verification report must include the consumer-closure counts whenever Contract Migration Proof applies. This requirement is contract-neutral and must not be reduced to a catalog of previously seen migration defects.
