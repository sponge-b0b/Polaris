---
name: verify-code
description: Performs diff hygiene, contract-impact closure, syntax/format/static typing verification, targeted testing, and the complete architecture invariant gate when the active Python change can affect mechanically enforced Polaris architecture.
compatibility: product=codex product=claude-code system=git system=python network=none
---

# Targeted Codebase Verification Standards

## Objective

Verify changes introduced by the current workspace or active ticket without broadening execution into repository-wide verification **except for explicitly repository-wide delegated invariant gates such as `$verify-architecture` when applicable**.

`$coding-standards` owns coding policy. Verify applicable requirements without duplicating that skill.

Repository-wide discovery is required when necessary to prove that an authoritative contract change has no stale internal consumers. Broaden discovery, not verification indiscriminately.

## Guardrails

* Verify only the active change and directly affected tests except where an explicitly delegated invariant skill owns broader scope.
* Resolve target files before verification.
* When a shared contract changes, discover its complete affected consumer set before declaring verification scope complete.
* Do not refactor unrelated code, weaken configuration, or add pass-only suppressions.
* Shell permissions do not authorize broader verification.
* `$verify-architecture`, when applicable, is intentionally whole-suite; do not narrow that child gate to changed files merely because Ruff, Mypy, and behavioral tests are targeted.
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

### Architecture Invariant Applicability

From the same resolved change set, classify `$verify-architecture` as `applicable` when the candidate changes any Python surface that the current architecture guard can inspect or changes the guard/tests themselves. This includes current Python under `src/polaris/`, current tests under `tests/`, and current migration Python scanned by `tests/architecture_guard.py`.

If the active change is entirely outside those surfaces and does not alter accepted architecture represented by the guard, classify the architecture gate `not-applicable` with the concrete reason.

Applicability determines whether the child runs. Once applicable, `$verify-architecture` owns its complete repository-wide suite; do not reduce it to this skill's target list.

### Contract-Impact Closure

Inspect the active diff before finalizing the target set.

This gate applies when the change modifies a shared internal contract or semantic owner, including an API/call signature, protocol/interface, identity source, lifecycle responsibility, canonical representation, enum/value contract, configuration key, or other reusable boundary.

When applicable:

1. identify every material contract transition introduced by the active change;
2. close the transition universe using **Transition-Bound Contract Consumer Closure** below;
3. for every consumer-bearing transition, search the repository for every affected caller, implementation, protocol, adapter, fake, fixture, test, configuration surface, registry/bootstrap path, and other consumer;
4. inspect dynamic/indirect consumers when literal search cannot establish closure;
5. add consumers requiring migration to the affected verification set;
6. require zero unresolved transitions and zero unexplained consumers before verification may pass.

Internal source compatibility is not assumed. Apply `$coding-standards` **Authoritative Contract Changes and Compatibility** exactly; do not preserve stale consumers with ignored parameters, compatibility sinks, aliases, shims, fallback paths, or similar residue merely to keep them compiling.

If explicit authority requires genuine compatibility, verify that it is isolated at the compatibility boundary and that the canonical internal contract remains clean.

Repository-wide consumer discovery does not by itself authorize a full-suite pytest run or unrelated cleanup. Keep Ruff, Mypy, and ordinary behavioral test execution targeted to the changed contract and affected consumers. `$verify-architecture` remains the explicit whole-suite exception when applicable.

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
uv run --locked ruff format --check <changed_python_paths>
uv run --locked ruff check <changed_python_paths>
```

Do not replace targets with `.`.

## 4. Mypy

Run only against changed Python files and directly affected tests:

```bash
uv run --locked mypy --explicit-package-bases <changed_python_paths_and_affected_tests>
```

Do not broaden to `mypy .`.

## 5. Targeted Tests

Run tests relevant to the changed behavior and directly affected modules:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run --locked pytest -q tests/path/to/test_relevant_module.py
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

## 6. Architecture Invariant Gate

When **Architecture Invariant Applicability** is `applicable`, invoke `$verify-architecture` as prescribed internal composition.

The child owns:

* the complete architecture-suite scope;
* current-authority classification of architecture failures;
* narrowly bounded repair of repository architecture violations, guard defects, or already-accepted architecture realization;
* `ARCHITECTURE INVARIANT: PASS | UNRESOLVED`.

Do not substitute one architecture test, a direct `check_repository()` call, or an ad hoc import scan for the child skill.

If `$verify-architecture` repairs executable Python or tests, add those changed paths and directly affected consumers to this skill's verification set and rerun every invalidated Ruff, Mypy, targeted behavioral test, diff-hygiene, and contract-impact check before reporting success. Do not recursively call `$verify-code` from the child.

An unresolved architectural semantic is not an ordinary code-verification failure. Return the child's complete blocker set to the owning lifecycle so it can route through `$architecture-remediation`.

## 7. Coding Standards

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

`$verify-architecture` is the explicit exception to ordinary target-local repair attribution. When applicable, consume that child skill's repository-wide repair/result exactly as its contract defines. Its repair authority is limited to mechanically enforced architecture and does not authorize unrelated cleanup.

Do not:

* use Ruff `--add-noqa`;
* weaken repository configuration;
* add pass-only suppressions;
* broaden ordinary verification to compensate for failure;
* weaken or deselect architecture tests to make `$verify-architecture` pass.

If a failure cannot be safely resolved within scope, report the affected file/test, failed check, concise error, and required next action.

## Reporting

Distinguish:

* targeted verification actually run;
* contract-impact closure status when applicable;
* whitespace defects mechanically fixed;
* architecture invariant status when applicable;
* architecture repairs returned by `$verify-architecture` and the targeted checks rerun because of them;
* unresolved/skipped targeted checks;
* broader verification not run other than explicitly delegated invariant gates.

On success:

```text
Targeted verification passed.

- Contract-impact closure: passed | not applicable
- Diff hygiene: passed
- Ruff format: passed
- Ruff lint: passed
- Mypy: passed
- Targeted tests: passed
- Architecture invariant: passed | not applicable
- Applicable coding standards: verified

Full repository verification was not run except for explicitly applicable repository-wide invariant gates.
```

If any required contract-impact discovery, targeted check, or applicable architecture invariant remains unresolved, do not report targeted verification as passed.

## Transition-Bound Contract Consumer Closure

Whenever Contract Migration Proof applies, `Contract-impact closure: passed` requires two nested working universes: a **Contract Transition Manifest** and, for every consumer-bearing transition, a **Consumer Closure Manifest**.

A search for known obsolete symbols, new contract names, or broad sinks is supporting evidence only. It does not define either universe.

### Contract Transition Manifest

Materialize the complete set of shared internal contract or semantic-owner transitions introduced by the active change before deriving consumers. Derive candidates from the authoritative baseline-to-candidate diff and the affected reusable boundaries, not from the subset of transitions already suspected.

Every transition candidate receives exactly one row:

```text
Transition: CT-<n>
Authoritative boundary: <exact contract/semantic owner>
Baseline contract: <prior observable contract/semantic>
Candidate contract: <current observable contract/semantic>
Transition kind: <signature | representation | ownership | lifecycle | behavior | configuration | protocol | other>
Disposition: <consumer-bearing | no-consumer-impact | unresolved>
Evidence/reason: <direct evidence or exact reason no consumer can observe the transition>
```

Rules:

* `consumer-bearing` means at least one caller, implementation, protocol, adapter, fake/fixture, test, bootstrap/composition path, configuration surface, or other consumer can observe or model the changed contract;
* `no-consumer-impact` requires evidence that the change cannot alter any consumer-observable contract; omission, file locality, or absence of a known symbol reference is insufficient;
* `unresolved` prevents contract-impact closure;
* a material transition may not disappear because the symbol name is unchanged, the old symbol was removed, the change is semantic rather than syntactic, or the transition was discovered indirectly;
* transition-universe completeness must be established by an independently checkable exhaustive mechanism when mechanically decidable; when semantic judgment is required to decide whether the transition universe itself is complete, `Contract-impact closure` remains unresolved without fresh non-mutating semantic certification of that bounded transition manifest.

Before deriving consumer closure require:

```text
Contract transition candidates: <n>
Transition rows: <n>
Unclassified transitions: 0
Unresolved transitions: 0
Consumer-bearing transitions without consumer closure: 0
```

### Consumer Closure Manifest

For every `consumer-bearing` transition, derive candidate consumers from that transition's authoritative contract and repository relationships/callers/composition/test substitutions/configuration surfaces that can exercise or model it. Every discovered candidate receives exactly one row:

```text
Consumer: CC-<n>
Transition: CT-<n>
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
* a candidate may not disappear because it is unchanged, inherited, test-only, indirect, already searched by name, or outside the changed-file list;
* each `consumer-bearing` transition must have a closed consumer universe; one transition's consumer search does not prove another transition complete.

Before `Contract-impact closure: passed` require:

```text
Contract consumer candidates: <n>
Consumer closure rows: <n>
Unclassified candidates: 0
Unresolved consumers: 0
Retained compatibility without authority: 0
```

Then apply the general counterexample-survivability question to both universes: could every cited check pass while a material contract transition was omitted, or while an authoritative consumer still accepts, emits, models, or depends on the obsolete contract? If yes, closure remains unresolved.

The final verification report must include both transition-closure and consumer-closure counts whenever Contract Migration Proof applies. This requirement is contract-neutral and must not be reduced to a catalog of previously seen migration defects.
