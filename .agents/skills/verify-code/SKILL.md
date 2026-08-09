---
name: verify-code
description: Performs syntax validation, format checks, static typing verification, and targeted testing on Python files modified in the workspace or active ticket. Use during individual ticket implementation or on demand before merging or handoff.
compatibility: product=codex product=claude-code system=git system=python network=none
---

# Targeted Codebase Verification Standards

## Objective

Verify Python changes introduced by the current workspace or active ticket without broadening into repository-wide verification.

`$coding-standards` owns coding policy. Verify applicable requirements, but do not re-invoke or duplicate that skill.

## Guardrail Constraints

* **Isolation Principle:** Verify only files changed by the current workspace or active ticket and directly affected tests.
* **Scope Extraction Invariant:** Resolve the target files before running verification.
* **Safety Invariant:** Do not refactor unrelated code, weaken configuration, or guess suppressions merely to make verification pass.
* **Authorization Invariant:** Approved shell prefixes or sandbox permissions do not authorize broad verification.
* **Command Guard Invariant:** Do not bypass the Polaris command guard through alternate executables or entrypoints.
* **Diff Hygiene:** Do not use `git diff --check` as a verification gate; patch whitespace hygiene is outside this skill.

## Verification Scope Authorization

Default verification is limited to:

1. format and lint checks on changed Python files;
2. static typing checks on changed Python files and directly affected tests;
3. targeted tests for changed behavior and nearby affected modules;
4. applicable `$coding-standards` requirements.

Do not run broad repository-wide commands unless explicitly authorized for the current task, including:

* `uv run pytest`
* `uv run pytest -q`
* `uv run mypy .`
* `uv run ruff check .`
* `uv run ruff format --check .`
* full coverage runs
* unrelated service-backed integration suites

If broader verification seems useful, stop after targeted verification and ask first, naming the exact proposed command.

Never imply full repository health unless broad verification was explicitly authorized and completed.

---

## Execution Steps

### Step 1: Identify Targeted Changes

If called from `$implement-ticket` with a ticket baseline, include committed Python changes since that baseline:

```bash
git diff --name-only --diff-filter=ACMR <ticket-baseline>...HEAD -- '*.py'
```

Also include current unstaged, staged, and untracked Python changes:

```bash
git diff --name-only --diff-filter=ACMR -- '*.py'
git diff --cached --name-only --diff-filter=ACMR -- '*.py'
git ls-files --others --exclude-standard -- '*.py'
```

If no ticket baseline applies, use only the workspace commands above.

Use the deduplicated union as the verification target list.

Do not broaden scope because no Python targets are found.

### Step 2: Verify Format and Lint

Run Ruff only against the resolved targets:

```bash
uv run ruff format --check <changed_python_paths>
uv run ruff check <changed_python_paths>
```

Do not replace the target list with `.`.

### Step 3: Targeted Static Type Verification

Run Mypy only against changed Python files and directly affected tests:

```bash
uv run mypy --explicit-package-bases <changed_python_paths_and_affected_tests>
```

Do not broaden to `mypy .`.

### Step 4: Targeted Testing

Run only tests relevant to the changed behavior and directly affected modules:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/path/to/test_relevant_module.py
```

Do not run the full suite by default.

Before targeted integration or live-service tests, identify required local services.

If a selected targeted test skips solely because required repository-local environment or services are missing:

* inspect local configuration;
* derive safe local configuration when unambiguous;
* start only an authorized required Docker service when necessary;
* rerun the exact targeted test.

Never echo secrets or full authenticated connection strings.

If required setup cannot be resolved safely, report the targeted check as unresolved or owner-deferred.

Do not compensate by broadening the test scope.

### Step 5: Coding-Standards Verification

Inspect changed code for `$coding-standards` requirements implicated by the diff.

Examples include:

* data-contract and typing boundaries;
* score semantics and precision;
* async behavior;
* observability;
* resource ownership;
* structural design rules.

Do not re-invoke `$coding-standards`.

Do not manufacture work for standards unrelated to the change.

---

## Failure Handling

When a targeted check fails:

1. determine whether the active change introduced the failure;
2. fix it at the narrowest authoritative point when within scope;
3. rerun the affected check.

Do not:

* use Ruff `--add-noqa`;
* weaken repository configuration;
* add suppressions merely to make verification pass;
* broaden verification to compensate for failure.

If a failure cannot be safely resolved within scope, report the affected file/test, failed check, concise error, and required next action.

---

## Reporting

Distinguish clearly between:

* targeted verification actually run;
* unresolved or skipped targeted checks;
* broader verification not run.

On success, use wording such as:

```text
Targeted verification passed.

- Ruff format: passed
- Ruff lint: passed
- Mypy: passed
- Targeted tests: passed
- Applicable coding standards: verified

Full repository verification was not run.
```

If any required targeted check remains unresolved, do not report targeted verification as fully passed.
