---
name: verify-spec
description: Perform authorized spec-wide verification across the completed Spec branch, repair in-scope failures, and record a passing verification receipt for the exact final HEAD.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Global Specification Integration & Verification

Verify the completed Spec branch against its fixed baseline as a unified system.

Unlike `$verify-code`, this workflow is authorized to run the repository-wide checks defined here. It may repair verification failures within Spec scope, rerun affected gates, and persist those fixes.

A successful run records a **Spec Verification Receipt** for the exact final committed `HEAD`. `$review-spec` may use that receipt as its verification precondition.

## 1. Pin the Fixed Point

Resolve the fixed baseline from the parent Spec issue unless explicitly overridden:

```bash id="r3yb0x"
BASELINE_COMMIT=$(gh issue view <spec_issue_number> --json comments -q '.comments[].body' \
  | grep -oP '(?<=\*\*Baseline Commit Hash:\*\* )\S+' | tail -1)
```

If missing and no explicit ref was supplied, ask for it.

Verify the Spec branch:

```bash id="t7bcpn"
CURRENT_BRANCH=$(git branch --show-current)

if [ "$CURRENT_BRANCH" != "spec-<spec_issue_number>" ]; then
  echo "❌ Expected spec-<spec_issue_number>; current branch is $CURRENT_BRANCH."
  exit 1
fi

git rev-parse "$BASELINE_COMMIT"
```

Halt if the baseline does not resolve.

Verification must start from a clean worktree because the resulting receipt attests to an exact commit:

```bash id="e0tjdu"
if [ -n "$(git status --porcelain)" ]; then
  echo "❌ Spec verification requires a clean worktree."
  exit 1
fi
```

Capture:

```bash id="hd66kx"
git diff "$BASELINE_COMMIT"...HEAD
git log "$BASELINE_COMMIT"..HEAD --oneline
```

The aggregate diff must be non-empty.

## 2. Identify the Spec

Resolve the originating Spec from:

1. commit references;
2. a path or issue supplied by the user;
3. a matching Spec under `docs/`, `specs/`, or `.scratch/`;
4. ask only if still unresolved.

Capture its **Architecture Impact**:

* affected entities;
* impact classification;
* governing ADR/doc references;
* unresolved architecture questions.

A Spec with an unresolved material architecture question is not ready for verification.

## 3. Execute Verification

### Guardrails

* Explicit invocation authorizes the repository-wide Ruff and Mypy commands below.
* It does not authorize untargeted full-suite pytest, coverage, or broad live/service-backed suites.
* Read `docs/testing_guide.md` and select tests from the Spec diff, affected boundaries, acceptance requirements, and known regression risks.
* Do not weaken configuration, add suppressions, or refactor unrelated code merely to pass.
* Report unrelated pre-existing failures separately.

Set:

```bash id="upb7iz"
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number>
```

### Environment and Services

Identify required infrastructure before integration or live tests.

If a required targeted test cannot establish its acceptance criterion service-free:

* derive safe local configuration when unambiguous;
* start only the required authorized local service;
* rerun the exact targeted check.

A required test skipped only because local setup is absent remains unresolved.

Never expose secrets or authenticated connection strings.

### Ruff

```bash id="f2nqie"
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff format --check .
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff check .
```

Never use Ruff `--add-noqa` to manufacture a pass.

### Mypy

```bash id="1ledds"
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> \
  uv run mypy . --explicit-package-bases
```

### Testing Matrix

```bash id="p0gmsm"
cat docs/testing_guide.md
```

Select targeted integration, pipeline, regression, or macro tests exercising:

* changed behavior;
* affected production boundaries;
* Spec acceptance requirements;
* known regression risks.

Do not blindly run the full suite.

### Targeted Integration and Regression

```bash id="3ex3qu"
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

```bash id="v5f3bc"
graphify . --update
graphify query "<affected entities, canonical concepts, and changed subsystems>"
```

Check whether the implementation:

* connects to expected canonical owners;
* bypasses established boundaries;
* creates duplicate ownership or parallel canonical paths;
* violates dependency direction;
* exposes unresolved material architecture.

Route architecture findings through **Architecture Finding Routing** before modifying anything.

### Duplication

When the Spec introduces a module, helper, utility layer, service, or canonical behavior, invoke `$duplication-checks`.

A new parallel source of truth or duplicate canonical behavior fails verification.

Unrelated existing clone clusters are reported separately.

## 4. Failure Handling

For an ordinary failure:

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
* deterministic architecture drift.

Do not:

* weaken configuration;
* add pass-only suppressions;
* change expected behavior merely so a test reaches it;
* broaden testing to compensate for a failed targeted check;
* modify unrelated pre-existing failures.

If a non-architecture failure cannot be safely repaired within Spec scope, stop and report it.

## 5. Architecture Finding Routing

### Existing Authority Determines the Fix

When current authority already establishes the correct state, repair the violation within Spec scope.

Examples:

* accepted ADR violation;
* stale derived wiki knowledge;
* documentation drift;
* bypass of a known canonical owner or dependency direction.

Use the owning workflow where applicable:

* implementation → correct code;
* entity knowledge → `$wiki-sync`;
* new non-ADR document → `$to-doc`;
* document classification/relocation → `$classify-doc`;
* ADR content/lifecycle → `$to-adr-doc`.

Rerun directly affected architecture checks.

Do not classify non-realization of an accepted decision as `[source-conflict]`.

### Architecture Decision Required

A new decision is required when correction requires choosing or changing a durable:

* invariant;
* canonical owner/path;
* architectural boundary;
* dependency direction;
* lifecycle responsibility;

or when applicable authorities genuinely disagree.

Collect and de-duplicate every independent blocker. Do not resolve them here.

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

```bash id="crn0mc"
git push -u origin HEAD
```

Child maintenance workflows such as `$wiki-sync` contribute their mutations to this commit rather than committing separately.

Do not use `git add .` when unrelated changes exist.

If staging, commit, or push fails, verification is incomplete.

If no repository files changed, skip commit and push.

Require the final worktree to be clean:

```bash id="oin9la"
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

capture the exact final commit:

```bash id="3f6ufc"
FINAL_HEAD=$(git rev-parse HEAD)
```

Persist a new comment on the parent Spec issue:

```bash id="cq50u8"
gh issue comment <spec_issue_number> --body "$(printf \
'## Spec Verification Receipt\n**Status:** passed\n**Verified HEAD:** %s\n**Verified Baseline:** %s\n**Branch:** %s\n' \
"$FINAL_HEAD" "$BASELINE_COMMIT" "spec-<spec_issue_number>")"
```

A receipt attests only to that exact `Verified HEAD`.

Do not write a passing receipt for failed or unresolved verification.

Do not reuse an older receipt after `HEAD` changes.

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
* architecture findings repaired under existing authority;
* unrelated pre-existing findings;
* optional checks not run;
* verification-fix commit(s), if any;
* push result, if applicable;
* final worktree state;
* verification receipt result and `Verified HEAD`.

On success, state:

```text id="62asek"
Spec verification passed.
Verified HEAD: <full SHA>
```

If any required gate or receipt persistence remains unresolved, do not report Spec verification as passed.
