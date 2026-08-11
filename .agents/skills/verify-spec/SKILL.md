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

Resolve the fixed baseline from the parent Spec issue unless explicitly overridden:

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

Halt if the baseline does not resolve.

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
2. a user-supplied path or issue;
3. a matching repository Spec;
4. the user only if still unresolved.

Capture its **Architecture Impact**:

* affected entities;
* impact classification;
* governing ADR/doc references;
* unresolved architecture questions.

A Spec containing an unresolved material architecture question is not ready for verification.

## 3. Execute Verification

### Guardrails

* Explicit invocation authorizes the repository-wide Ruff and Mypy commands below.
* It does not authorize untargeted full-suite pytest, coverage, or broad live/service-backed suites.
* Read `docs/process/testing-guide.md`.
* Select tests from the Spec diff, affected boundaries, acceptance requirements, and regression risks.
* Do not weaken configuration, add pass-only suppressions, or refactor unrelated code merely to pass.
* Report unrelated pre-existing failures separately.

### Environment and Services

If a required targeted test cannot establish its acceptance criterion service-free:

* derive safe local configuration when unambiguous;
* start only the required authorized local service;
* rerun the exact targeted check.

A required test skipped only because local setup is absent remains unresolved.

Never expose secrets or authenticated connection strings.

### Ruff

```bash
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff format --check .
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff check .
```

Never use Ruff `--add-noqa` to manufacture a pass.

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

When architecture introduces a required prerequisite, update affected tests or fixtures to traverse that canonical prerequisite rather than weakening downstream expectations.

### Architecture Integrity

If the Living Entity Wiki exists, invoke `$wiki-lint`.

Evaluate Spec-relevant:

* `[source-conflict]`;
* `[code-drift]`;
* `[doc-drift]`;
* structural/citation failures affecting architectural reliability.

Unrelated pre-existing findings do not fail this Spec.

Refresh and query the architecture graph:

```bash
graphify . --update
graphify query "<affected entities, canonical concepts, and changed subsystems>"
```

Check whether implementation:

* connects to expected canonical owners;
* bypasses established boundaries;
* creates duplicate ownership or parallel canonical paths;
* violates dependency direction;
* exposes unresolved material architecture.

Before routing any `[source-conflict]`, apply the **Realization-Status Defensive Rule** below.

### Duplication

When the Spec introduces a module, helper, utility layer, service, or canonical behavior, invoke `$duplication-checks`.

A new parallel source of truth or duplicate canonical behavior fails verification.

Unrelated existing clone clusters are reported separately.

## 4. Failure Handling

For an ordinary verification failure:

1. determine whether the Spec introduced or owns it;
2. fix the narrowest authoritative point within Spec scope;
3. rerun the affected check;
4. continue verification.

This includes:

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
* broaden testing to compensate for a failed targeted check;
* modify unrelated pre-existing failures.

If a non-architecture failure cannot be safely resolved within Spec scope, stop and report it.

## 5. Architecture Finding Routing

### Realization-Status Defensive Rule

Do not accept `[source-conflict]` classification merely because an accepted ADR still describes its implementation as `pending`, `not yet realized`, or equivalent.

When all are true:

1. the ADR remains accepted;
2. its normative architectural decision is unambiguous;
3. current implementation conforms to that decision;
4. implementation clearly realizes the described capability; and
5. the only disagreement is stale realization/lifecycle wording;

then this is deterministic **ADR documentation drift**, not unresolved architecture.

Route it through `$to-adr-doc`, then rerun `$wiki-lint` and the affected architecture checks.

Do not invoke `$architecture-remediation` for this condition.

This rule applies only to stale realization/lifecycle description. If implementation contradicts the ADR's normative decision, or applicable authorities genuinely disagree about architecture, continue normal architecture routing.

### Existing Authority Determines the Fix

When current authority already establishes the correct state, repair the violation within Spec scope.

Examples:

* implementation violates an accepted ADR;
* derived wiki knowledge is stale;
* documentation or ADR realization status is stale;
* a known canonical owner or dependency direction was bypassed.

Use the owning workflow:

* implementation → correct code;
* derived entity knowledge → `$wiki-sync`;
* new non-ADR documentation → `$to-doc`;
* document classification/relocation → `$classify-doc`;
* ADR content/lifecycle/realization status → `$to-adr-doc`.

Rerun directly affected architecture checks.

Do not classify either of these as `[source-conflict]`:

* implementation has not yet realized an accepted decision and active work clearly tracks that realization;
* implementation has now realized an accepted decision but the ADR's descriptive realization status is stale.

### Architecture Decision Required

A new decision is required only when correction requires choosing or changing a durable:

* invariant;
* canonical owner/path;
* architectural boundary;
* dependency direction;
* lifecycle responsibility;

or when applicable architectural authorities genuinely disagree and existing precedence cannot resolve them.

Collect and de-duplicate every independent blocker.

Do not resolve architecture inside `$verify-spec`.

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
> 1. **<question or conflict>**
>
>    * Evidence: <concise evidence>
>    * Material consequence: <ownership/path, boundary, dependency direction, lifecycle responsibility, source conflict, or other consequence>
>    * Governing context: <entities / ADRs / docs>

Do not propose an architectural answer.

## 6. Final Verification Pass

After all verification-owned fixes are complete, rerun every applicable gate required to establish final consistency:

* repository-wide Ruff format/lint;
* repository-wide Mypy;
* targeted integration/regression tests;
* `$wiki-lint` and affected architecture queries;
* `$duplication-checks` when applicable.

Do not report success while any required gate remains failed or unresolved.

## 7. Persist Verification Fixes

If verification changed repository files:

1. verify `spec-<spec_issue_number>` remains checked out;
2. stage only verification-owned files;
3. invoke `$conventional-commits`;
4. commit;
5. push:

```bash
git push -u origin HEAD
```

Child maintenance workflows such as `$wiki-sync` and `$to-adr-doc` contribute their mutations to this verification commit rather than creating separate commits when their workflow permits parent commit ownership.

Do not use `git add .` when unrelated changes exist.

If staging, commit, or push fails, verification is incomplete.

If no repository files changed, skip commit and push.

Require a clean final worktree:

```bash
if [ -n "$(git status --porcelain)" ]; then
  echo "❌ Verification cannot attest to HEAD with an uncommitted worktree."
  exit 1
fi
```

## 8. Record the Verification Receipt

Only after:

* every required verification gate passes;
* all verification-owned changes are committed;
* required pushes succeed;
* the worktree is clean;

capture:

```bash
FINAL_HEAD=$(git rev-parse HEAD)
```

Persist a comment on the parent Spec:

```bash
gh issue comment <spec_issue_number> --body "$(printf \
'## Spec Verification Receipt\n**Status:** passed\n**Verified HEAD:** %s\n**Verified Baseline:** %s\n**Branch:** %s\n' \
"$FINAL_HEAD" "$BASELINE_COMMIT" "spec-<spec_issue_number>")"
```

The receipt attests only to that exact `Verified HEAD`.

Do not:

* write a passing receipt for failed or unresolved verification;
* reuse an older receipt after `HEAD` changes.

If receipt persistence fails, verification is incomplete because `$review-spec` cannot establish its precondition.

## 9. Reporting

Report:

* baseline and final `HEAD`;
* Spec branch;
* Ruff result;
* Mypy result;
* targeted tests and result;
* service-backed/persistence checks;
* architecture/wiki result;
* duplication result;
* failures repaired;
* architecture/documentation drift repaired under existing authority;
* unrelated pre-existing findings;
* optional checks not run;
* verification-fix commit(s), if any;
* push result, if applicable;
* final worktree state;
* verification receipt result and `Verified HEAD`.

On success:

```text
Spec verification passed.
Verified HEAD: <full SHA>
```

If any required gate or receipt persistence remains unresolved, do not report Spec verification as passed.
