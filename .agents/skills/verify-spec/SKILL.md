---
name: verify-spec
description: Perform authorized spec-wide verification across the completed Spec branch, repair in-scope failures, and record a passing verification receipt for the exact final HEAD.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Global Specification Integration & Verification

Verify the completed Spec branch against its fixed baseline as a unified system.

Unlike `$verify-code`, this workflow is authorized to run the repository-wide checks defined here. It may repair verification failures within Spec scope, rerun affected gates, and persist those fixes.

A successful run records a **Spec Verification Receipt** for the exact final committed `HEAD`. `$review-spec` requires that receipt.

## 1. Pin the Fixed Point

Resolve the baseline from the parent Spec unless explicitly overridden:

```bash
BASELINE_COMMIT=$(gh issue view <spec_issue_number> --json comments -q '.comments[].body' \
  | grep -oP '(?<=\*\*Baseline Commit Hash:\*\* )\S+' | tail -1)
```

If missing and no explicit ref was supplied, ask for it.

Verify the Spec branch:

```bash
CURRENT_BRANCH=$(git branch --show-current)

if [ "$CURRENT_BRANCH" != "spec-<spec_issue_number>" ]; then
  echo "❌ Expected spec-<spec_issue_number>; current branch is $CURRENT_BRANCH."
  exit 1
fi

git rev-parse "$BASELINE_COMMIT"
```

Verification must begin from a clean worktree:

```bash
if [ -n "$(git status --porcelain)" ]; then
  echo "❌ Spec verification requires a clean worktree."
  exit 1
fi
```

Capture:

```bash
git diff "$BASELINE_COMMIT"...HEAD
git log "$BASELINE_COMMIT"..HEAD --oneline
```

The aggregate diff must be non-empty.

## 2. Identify the Spec

Resolve the originating Spec from:

1. commit references;
2. user-supplied path or issue;
3. matching repository Spec;
4. user only if still unresolved.

Capture its **Architecture Impact**:

* affected entities;
* impact classification;
* governing ADR/doc references;
* unresolved architecture questions.

A Spec containing unresolved material architecture is not ready for verification.

## 3. Execute Verification

### Guardrails

* Invocation authorizes the repository-wide Ruff and Mypy commands below.
* It does not authorize untargeted full-suite pytest, coverage, or broad live/service-backed suites.
* Read `docs/process/testing-guide.md`.
* Select tests from the Spec diff, affected boundaries, acceptance requirements, and regression risks.
* Do not weaken configuration, add pass-only suppressions, or refactor unrelated code merely to pass.
* Report unrelated pre-existing failures separately.

### Diff Hygiene

Check the complete Spec change against its baseline:

```bash
git diff --check "$BASELINE_COMMIT"
```

For findings introduced or carried by this Spec:

* deterministic whitespace-only defects → fix mechanically, rerun `git diff --check`, and continue;
* unresolved conflict markers → Blocking; investigate rather than treating them as whitespace cleanup.

Do not ask for confirmation for whitespace-only fixes.

Do not alter document/code meaning while fixing whitespace.

Unrelated pre-existing whitespace outside the Spec remains report-only.

### Environment and Services

If a required targeted test cannot establish its criterion service-free:

* derive safe local configuration when unambiguous;
* start only the required authorized local service;
* rerun the exact targeted check.

A required test skipped solely because local setup is absent remains unresolved.

Never expose secrets or authenticated connection strings.

### Ruff

```bash
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff format --check .
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff check .
```

Never use Ruff `--add-noqa`.

### Mypy

```bash
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> \
  uv run mypy . --explicit-package-bases
```

### Testing Matrix

```bash
cat docs/process/testing-guide.md
```

Select targeted integration, pipeline, regression, or macro tests exercising:

* changed behavior;
* affected production boundaries;
* Spec acceptance requirements;
* known regression risks.

Do not blindly run the full suite.

### Targeted Integration and Regression

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q <targeted_test_directory_or_marker>
```

A helper/unit test is insufficient when the Spec requires proof through a higher production boundary.

When architecture introduces a required prerequisite, update tests/fixtures to traverse that canonical prerequisite rather than weakening downstream expectations.

### Architecture Integrity

If the Living Entity Wiki exists, invoke the `$wiki-lint` skill.

Evaluate Spec-relevant:

* `[source-conflict]`;
* `[code-drift]`;
* `[doc-drift]`;
* structural/citation failures affecting architectural reliability.

Unrelated pre-existing findings do not fail the Spec.

Refresh/query architecture:

```bash
graphify . --update
graphify query "<affected entities, canonical concepts, and changed subsystems>"
```

Check whether implementation:

* connects to canonical owners;
* bypasses boundaries;
* creates duplicate ownership/canonical paths;
* violates dependency direction;
* exposes unresolved material architecture.

Apply the **Realization-Status Defensive Rule** before routing `[source-conflict]`.

### Duplication

When the Spec introduces a module, helper, utility layer, service, or canonical behavior, invoke `$duplication-checks`.

New duplicate canonical behavior fails verification.

Unrelated existing clone clusters are report-only.

## 4. Failure Handling

For an ordinary verification failure:

1. determine whether the Spec introduced or owns it;
2. fix the narrowest authoritative point within Spec scope;
3. rerun the affected check;
4. continue verification.

This includes:

* deterministic whitespace defects;
* Ruff;
* Mypy;
* targeted tests;
* integration/persistence checks;
* Spec-introduced duplication;
* deterministic architecture/documentation drift.

Do not:

* weaken configuration;
* add pass-only suppressions;
* change expected behavior merely so a test reaches it;
* broaden testing to compensate for failure;
* modify unrelated pre-existing failures.

Deterministic whitespace-only fixes require no owner confirmation.

If a non-architecture failure cannot be safely repaired within Spec scope, stop and report it.

## 5. Architecture Finding Routing

### Realization-Status Defensive Rule

Do not accept `[source-conflict]` merely because an accepted ADR still says implementation is `pending`, `not yet realized`, or equivalent.

When:

1. the ADR remains accepted;
2. its normative decision is unambiguous;
3. implementation conforms to that decision;
4. implementation clearly realizes it; and
5. only realization/lifecycle wording is stale;

treat this as deterministic ADR documentation drift.

Route through `$to-adr-doc`, then rerun the `$wiki-lint` skill and affected architecture checks.

Do not invoke `$architecture-remediation`.

If implementation contradicts the normative decision or authorities genuinely disagree, use normal architecture routing.

### Existing Authority Determines the Fix

When current authority establishes the correct state, repair within Spec scope.

Examples:

* accepted ADR violation;
* stale derived wiki knowledge;
* stale documentation/ADR realization state;
* bypassed canonical owner/dependency direction.

Use the owner:

* implementation → correct code;
* entity knowledge → `$wiki-sync`;
* new non-ADR documentation → `$to-doc`;
* classification/relocation → `$classify-doc`;
* ADR lifecycle/realization → `$to-adr-doc`.

Rerun affected architecture checks.

### Architecture Decision Required

A new decision is required only when correction requires choosing/changing a durable:

* invariant;
* canonical owner/path;
* architectural boundary;
* dependency direction;
* lifecycle responsibility;

or applicable authorities genuinely disagree.

Collect/de-duplicate all independent blockers.

Do not resolve architecture here.

Halt with:

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
> 1. **<question/conflict>**
>
>    * Evidence: <evidence>
>    * Material consequence: <ownership/path/boundary/dependency/lifecycle/conflict>
>    * Governing context: <entities / ADRs / docs>

Do not propose an architectural answer.

## 6. Final Verification Pass

After all verification-owned fixes, rerun every applicable gate needed for final consistency:

* `git diff --check "$BASELINE_COMMIT"`;
* repository-wide Ruff;
* repository-wide Mypy;
* targeted integration/regression tests;
* invoke the `$wiki-lint` skill and affected architecture queries;
* invoke the `$duplication-checks` skill when applicable.

If final `git diff --check` finds a deterministic Spec-owned whitespace defect, fix it mechanically and rerun the affected final gates as needed.

Do not report success while any required gate remains failed or unresolved.

## 7. Persist Verification Fixes

If verification changed files:

1. verify `spec-<spec_issue_number>` remains checked out;
2. stage only verification-owned files;
3. invoke `$conventional-commits`;
4. commit;
5. push:

```bash
git push -u origin HEAD
```

Child workflows such as `$wiki-sync` and `$to-adr-doc` contribute their mutations to this verification commit when parent commit ownership applies.

Do not use `git add .` with unrelated changes.

If staging, commit, or push fails, verification is incomplete.

If no files changed, skip commit/push.

Require a clean final worktree:

```bash
if [ -n "$(git status --porcelain)" ]; then
  echo "❌ Verification cannot attest to HEAD with an uncommitted worktree."
  exit 1
fi
```

## 8. Record the Verification Receipt

Only after all required gates pass, fixes are committed/pushed, and the worktree is clean:

```bash
FINAL_HEAD=$(git rev-parse HEAD)
```

Persist:

```bash
gh issue comment <spec_issue_number> --body "$(printf \
'## Spec Verification Receipt\n**Status:** passed\n**Verified HEAD:** %s\n**Verified Baseline:** %s\n**Branch:** %s\n' \
"$FINAL_HEAD" "$BASELINE_COMMIT" "spec-<spec_issue_number>")"
```

The receipt attests only to that exact `HEAD`.

Do not write a passing receipt for failed/unresolved verification or reuse a stale receipt.

Receipt persistence failure means verification is incomplete.

## 9. Reporting

Report:

* baseline and final `HEAD`;
* Spec branch;
* diff hygiene result and any mechanical fixes;
* Ruff result;
* Mypy result;
* targeted tests;
* service-backed/persistence checks;
* architecture/wiki result;
* duplication result;
* failures repaired;
* unrelated pre-existing findings;
* optional checks not run;
* verification-fix commits;
* push result;
* final worktree state;
* verification receipt and `Verified HEAD`.

On success:

```text
Spec verification passed.
Verified HEAD: <full SHA>
```

If any required gate or receipt remains unresolved, do not report a pass.
