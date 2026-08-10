---
name: verify-spec
description: Perform explicitly authorized spec-wide verification, repository-wide static analysis, repository-wide type checking, duplicate-code analysis, strategically targeted integration testing, and architecture-integrity checks across the completed spec since its fixed baseline.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Global Specification Integration & Verification

Verify the completed Spec branch against its fixed baseline as a unified system.

Unlike `$verify-code`, this workflow is explicitly authorized to run the repository-wide static checks named here. It may fix verification failures within the Spec scope, rerun the affected gates, and persist those fixes.

## 1. Pin the Fixed Point

The fixed point is stored on the parent Spec issue unless explicitly overridden.

1. **Extract baseline metadata** from the Spec comments:

   ```bash
   BASELINE_COMMIT=$(gh issue view <spec_issue_number> --json comments -q '.comments[].body' \
     | grep -oP '(?<=\*\*Baseline Commit Hash:\*\* )\S+' | tail -1)
   ```

2. **Fallback:** If missing and the user supplied no explicit commit, branch, tag, or relative ref, ask for it.

3. **Verify the Spec branch:**

   ```bash
   CURRENT_BRANCH=$(git branch --show-current)
   if [ "$CURRENT_BRANCH" != "spec-<spec_issue_number>" ]; then
     echo "❌ Expected spec-<spec_issue_number> to be checked out, but current branch is $CURRENT_BRANCH."
     exit 1
   fi
   ```

4. **Validate the baseline:**

   ```bash
   git rev-parse "$BASELINE_COMMIT"
   ```

   Halt if it does not resolve.

5. **Capture the aggregate change:**

   ```bash
   git diff "$BASELINE_COMMIT"...HEAD
   git log "$BASELINE_COMMIT"..HEAD --oneline
   ```

6. The aggregate diff must be non-empty.

## 2. Identify the Spec

Resolve the originating Spec in this order:

1. issue references in commits;
2. a path or issue supplied by the user;
3. a matching Spec under `docs/`, `specs/`, or `.scratch/`;
4. ask only if it still cannot be resolved.

Capture its **Architecture Impact**:

* affected entities;
* impact classification;
* governing ADR/doc references;
* unresolved architecture questions.

A Spec that already declares a material unresolved architecture question is not ready for verification.

## Objective

Catch Spec-wide regressions, integration failures, type drift, duplication, and architecture drift across the completed implementation.

## Guardrails

* **Authorization:** Explicit invocation authorizes the repository-wide Ruff and Mypy commands defined here. It does not authorize untargeted full-suite pytest, coverage, or broad live/service-backed suites.
* **Command guard:** Set `POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number>` for authorized repository-wide Ruff and Mypy commands.
* **Static scope:** Repository-wide Ruff and Mypy operate on `.`.
* **Test scope:** Read `docs/testing_guide.md`; select tests from the Spec diff, affected boundaries, acceptance requirements, and known regression risks.
* **Safety:** Do not weaken repository configuration, create suppressions, or refactor unrelated code merely to make verification pass.
* **Pre-existing failures:** Report unrelated pre-existing failures separately. Do not make the current Spec responsible for them.

### Environment and Services

Identify required infrastructure before integration or live testing.

If a required targeted test cannot prove its acceptance criterion service-free:

* derive safe local configuration when unambiguous;
* start only the required authorized local service;
* rerun the exact targeted check.

A required test skipped solely because repository-local setup is missing is unresolved verification, not a pass.

Never expose secrets or authenticated connection strings.

### Diff Hygiene

Do not fail Spec verification for incidental whitespace outside the defined gates.

If `git diff --check` is run additionally:

* unresolved merge-conflict markers are Blocking;
* whitespace-only findings are Advisory unless an applicable repository rule explicitly makes them Blocking.

Optional patch-hygiene checks do not override the verification result.

## 3. Execute Verification

### Step 1: Repository-Wide Ruff

```bash
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff format --check .
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff check .
```

Never use Ruff `--add-noqa` to manufacture a pass.

### Step 2: Repository-Wide Mypy

```bash
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> \
  uv run mypy . --explicit-package-bases
```

### Step 3: Resolve the Testing Matrix

```bash
cat docs/testing_guide.md
```

Select integration, pipeline, regression, or macro tests that exercise:

* changed behavior;
* affected production boundaries;
* Spec acceptance requirements;
* known regression risks.

Do not blindly run the full test suite.

### Step 4: Targeted Integration and Regression Tests

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q <targeted_test_directory_or_marker>
```

A helper/unit test is not sufficient when the Spec requires proof through a higher production boundary.

When architecture introduces a new required prerequisite, update affected tests or fixtures to traverse that canonical prerequisite rather than weakening the downstream behavior being tested.

### Step 5: Aggregate Architecture Integrity

If the Living Entity Wiki exists, invoke `$wiki-lint`.

Evaluate applicable findings introduced or left unresolved by this Spec, including:

* `[source-conflict]`;
* `[code-drift]`;
* `[doc-drift]`;
* structural or citation failures that make affected architectural knowledge unreliable.

Pre-existing findings unrelated to the Spec are reported separately and do not fail this Spec.

Then refresh and query the architecture graph:

```bash
graphify . --update
graphify query "<affected entities, canonical concepts, and changed subsystems>"
```

Using the Spec's Architecture Impact and actual implementation, determine:

* Did changed components connect to their expected canonical owners?
* Did any layer bypass an established boundary?
* Did implementation create duplicate ownership or a parallel canonical path?
* Did dependency direction violate applicable architectural constraints?
* Did implementation expose a material architecture decision not resolved by the Spec?

Route findings through **Architecture Finding Routing** below before modifying anything.

### Step 6: Duplication Verification

When the Spec introduces a new module, helper, utility layer, service, or canonical behavior, invoke `$duplication-checks`.

A new parallel source of truth or duplicate canonical behavior is a verification failure.

Existing clone clusters unrelated to the Spec are reported separately.

## 4. Failure Handling

For ordinary verification failures:

1. determine whether the Spec introduced or owns the failure;
2. fix it at the narrowest authoritative point within Spec scope;
3. rerun the affected check;
4. continue verification.

This applies to failures from:

* Ruff;
* Mypy;
* targeted tests;
* integration or persistence checks selected by the testing blueprint;
* duplication introduced by the Spec;
* deterministic architecture drift described below.

Do not:

* weaken configuration;
* add suppressions merely to pass;
* change expected behavior merely because a test can no longer reach it;
* broaden testing to compensate for a failed targeted check;
* modify unrelated pre-existing failures.

If a non-architecture failure cannot be safely resolved within Spec scope, stop and report the failed gate, concise error, affected surface, and required next action.

## 5. Architecture Finding Routing

Architecture findings require classification before remediation.

### Existing Authority Determines the Fix

If the correct state is already unambiguously established by current architecture, no new architecture decision is required.

Examples:

* implementation violates an accepted ADR;
* derived wiki knowledge is stale;
* current documentation drifts from established authority;
* a known canonical owner or dependency direction was bypassed.

Fix the finding at its authoritative point within Spec scope, using the owning workflow when applicable:

* implementation → correct the code;
* derived entity knowledge → `$wiki-sync`;
* new non-ADR documentation → `$to-doc`;
* document classification or relocation → `$classify-doc`;
* ADR lifecycle or content → `$to-adr-doc`.

Then rerun `$wiki-lint` and the directly affected architecture checks.

Do not classify mere non-realization of an accepted decision as `[source-conflict]`.

### Architecture Decision Required

A new architecture decision is required when correction would require choosing or changing a durable:

* invariant;
* canonical owner or path;
* architectural boundary;
* dependency direction;
* lifecycle responsibility;

or when applicable architectural authorities genuinely disagree and no existing precedence resolves the conflict.

Collect every independent architecture blocker. De-duplicate multiple symptoms of the same underlying question.

Do not resolve them inside `$verify-spec`.

Halt with a **Human Handoff Intercept**:

> ⚠️ **Spec verification is blocked by unresolved architecture.**
>
> Please run:
>
> ```
> $architecture-remediation - <Spec Title> (<Spec URL>) — <concise blocker-set summary>
> ```
>
> **Architecture blockers:**
>
> 1. **<unresolved question or conflict>**
>
>    * Evidence: <concise evidence>
>    * Material consequence: <ownership/path, boundary, dependency direction, lifecycle responsibility, source conflict, or other consequence>
>    * Governing context: <affected entities / ADRs / docs when known>
> 2. **<unresolved question or conflict>**
>
>    * ...

Do not propose an architectural answer.

`$architecture-remediation` owns Wayfinder lineage recovery and architecture re-entry.

## 6. Final Verification Pass

After all verification-owned fixes are complete, rerun every applicable Spec gate needed to establish final consistency:

* repository-wide Ruff format/lint;
* repository-wide Mypy;
* targeted integration/regression tests;
* `$wiki-lint` and affected architecture queries;
* `$duplication-checks` when applicable.

Do not report success while any required gate remains failed or unresolved.

## 7. Persist Verification Fixes

If `$verify-spec` changed repository files while repairing failures:

1. verify `spec-<spec_issue_number>` is still checked out;
2. stage only files changed by this verification/remediation work;
3. invoke `$conventional-commits`;
4. commit the fixes;
5. push:

   ```bash
   git push -u origin HEAD
   ```

When `$verify-spec` is the parent workflow, child maintenance skills such as `$wiki-sync` contribute their mutations to this commit rather than creating separate commits.

Do not use `git add .` when unrelated working-tree changes exist.

If staging, commit, or push fails, verification is not complete.

If no repository files changed, skip commit and push.

## 8. Reporting

Report:

* baseline and final `HEAD`;
* Spec branch;
* Ruff format/lint result;
* Mypy result;
* targeted tests run and result;
* service-backed or persistence checks run;
* architecture/wiki result;
* duplication result;
* failures repaired during verification;
* architecture findings repaired under existing authority;
* unrelated pre-existing findings;
* optional checks not run;
* verification-fix commit(s), if any;
* push result, if applicable;
* final worktree state.

On success, state explicitly:

```text
Spec verification passed.
```

If a required gate remains unresolved, do not report Spec verification as passed.
