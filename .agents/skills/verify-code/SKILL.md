---
name: verify-code
description: Performs diff hygiene, syntax/format/static typing verification, and targeted testing on Python files modified in the workspace or active ticket.
compatibility: product=codex product=claude-code system=git system=python network=none
---

# Targeted Codebase Verification Standards

## Objective

Verify changes introduced by the current workspace or active ticket without broadening into repository-wide verification.

`$coding-standards` owns coding policy. Verify applicable requirements without duplicating that skill.

## Guardrails

* Verify only the active change and directly affected tests.
* Resolve target files before verification.
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

Before targeted integration/live-service tests, identify required local services.

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
* structural design rules.

Do not manufacture work for unrelated standards.

## Failure Handling

When a targeted check fails:

1. determine whether the active change owns it;
2. fix the narrowest authoritative point within scope;
3. rerun the affected check.

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
* whitespace defects mechanically fixed;
* unresolved/skipped targeted checks;
* broader verification not run.

On success:

```text
Targeted verification passed.

- Diff hygiene: passed
- Ruff format: passed
- Ruff lint: passed
- Mypy: passed
- Targeted tests: passed
- Applicable coding standards: verified

Full repository verification was not run.
```

If any required targeted check remains unresolved, do not report targeted verification as passed.
