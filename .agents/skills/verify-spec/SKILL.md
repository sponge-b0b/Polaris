---
name: verify-spec
description: Perform explicitly authorized spec-wide verification, repository-wide static analysis, repository-wide type checking, token-matching to detect duplicate code fragments and clone clusters, and strategically targeted integration testing across the spec's relevant modules since a fixed point (commit, branch, tag, or merge-base).
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Global Specification Integration & Verification Skill

Verification of the diff between `HEAD` and a fixed point the user supplies:

## 1. Pin the fixed point

The fixed point is automatically stored in the parent specification issue on GitHub, unless explicitly overridden or provided by the user. Follow these steps to resolve and validate it:

1. **Extract Baseline Metadata**: `$to-tickets` posts the baseline as a **comment** on the parent spec issue (it never edits the issue body — see the Spec Branch Rule in `$to-tickets`), so fetch comments specifically, not just the body, to find and parse the **Baseline Commit Hash**:

   ```bash
   BASELINE_COMMIT=$(gh issue view <spec_issue_number> --json comments -q '.comments[].body' \
     | grep -oP '(?<=\*\*Baseline Commit Hash:\*\* )\S+' | tail -1)
   ```

2. **Fallback**: If the metadata is missing and the user did not explicitly specify a commit SHA, branch name, tag, or relative ref, ask for it directly.

3. **Verify Branch Checked Out**: Ensure `spec-<spec_issue_number>` is the currently checked-out branch:

   ```bash
   CURRENT_BRANCH=$(git branch --show-current)
   if [ "$CURRENT_BRANCH" != "spec-<spec_issue_number>" ]; then
     echo "❌ Expected spec-<spec_issue_number> to be checked out, but current branch is $CURRENT_BRANCH."
     exit 1
   fi
   ```

4. **Validate the Ref**:

   ```bash
   git rev-parse <fixed-point>
   ```

   If the ref does not resolve, halt.

5. **Capture Diff and Log**:

   * `git diff <fixed-point>...HEAD`
   * `git log <fixed-point>..HEAD --oneline`

6. **Pre-Flight Check**: The diff must be non-empty.

## 2. Identify the spec source

Look for the originating spec, in this order:

1. Issue references in commit messages — fetch via `docs/agents/issue-tracker.md`.
2. A path the user passed.
3. A matching spec under `docs/`, `specs/`, or `.scratch/`.
4. If nothing is found, ask the user where the spec is. If none exists, the **Spec** sub-agent reports "no spec available".

If the spec contains **Architecture Impact**, capture:

* affected entities;
* impact classification;
* governing ADR/doc references;
* unresolved architecture questions.

A spec with a material unresolved architecture question is not ready for aggregate verification.

## Objective

Validate the completed specification branch as a unified system to catch cross-module regressions, integration failures, type drift, duplication, and architecture drift resulting from the completed specification sprint.

## Guardrail Constraints

* **Authorization Invariant:** Explicit invocation of `$verify-spec` authorizes the repository-wide static analysis commands named here. It does not authorize untargeted full-suite pytest, coverage, or broad service-backed integration runs.
* **Command Guard Invariant:** Do not bypass the Polaris command guard. Set `POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number>` for the authorized repository-wide Ruff and Mypy commands.
* **Scope Expansion Invariant:** Repository-wide formatting, linting, and typing checks operate on `.`.
* **Testing Blueprint Invariant:** Read `docs/testing_guide.md`; do not guess integration targets or blindly run the full test suite.

## Execution Rules & Constraints

### 1. Test Targeting & Scope Identification

* Do not run a full test suite by default.
* Prefer tests tied to changed files, affected boundaries, and known regression risks.
* Report optional live validations separately.

### 2. Environment & Service Dependency Check

* Use environment variables or redacted placeholders.
* Identify required infrastructure before integration/live testing.
* If needed acceptance criteria cannot be proved service-free, start only the required authorized local Docker services.
* A targeted test skipped solely because required repo-local environment or service setup is missing is not verified.
* Never echo secrets or full connection strings.

### 3. Timeouts & Efficiency Guardrails

* Do not wait on unnecessary unavailable services.
* Use reasonable timeouts and diagnose incorrect estimates rather than applying excessive defaults.

---

## Code Quality & Suppression Guardrails

Never generate, execute, or commit automated rule suppressions merely to make verification pass.

* Do not use Ruff `--add-noqa`.
* Fix formatting and lint violations in the code.
* Changing global lint constraints requires explicit human authorization.

## Execution Steps

### Step 1: Global Repository Linting & Layout Audit

```bash
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff format --check .
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff check .
```

### Step 2: Global Monolithic Type Verification

```bash
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run mypy . --explicit-package-bases
```

### Step 3: Analyze Testing Matrix Guidelines

```bash
cat docs/testing_guide.md
```

Identify the integration, pipeline, or macro test groups matching the components introduced or modified by the spec.

### Step 4: Execute Targeted Integration and Regression Suites

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q <targeted_test_directory_or_marker>
```

### Step 5: Aggregate Architecture Integrity

If the Living Entity Wiki exists, invoke `$wiki-lint`.

Treat architecture findings introduced or left unresolved by this spec as verification failures, including applicable:

* `[source-conflict]`;
* `[code-drift]`;
* `[doc-drift]`;
* structural or citation failures that make affected architectural knowledge unreliable.

Pre-existing findings unrelated to the spec must be reported separately rather than attributed to this implementation.

Then refresh/query the architecture graph:

```bash
graphify . --update
graphify query "<affected entities, canonical concepts, and changed subsystems>"
```

Use the spec's **Architecture Impact** and actual diff to answer:

* Did changed components connect to their expected canonical owners?
* Did any layer bypass an established boundary?
* Did the implementation introduce duplicate ownership or a parallel canonical path?
* Did dependency direction violate applicable architectural constraints?
* Did the implementation introduce a material architecture decision or boundary change not resolved by the spec?

If the final question is yes, fail verification and return the issue upstream rather than resolving architecture inside `$verify-spec`.

---

## Duplication Verification Check

When the specification introduces a new module, helper, utility layer, or service, invoke `$duplication-checks`.

Fail verification when the implementation creates a parallel source of truth or duplicates existing canonical behavior. Require reuse, modification, or deliberate architectural resolution instead.

## Example

**User:** "All individual implementation tickets are closed. Let's do final specification verification."

Run:

```bash
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff format --check .
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff check .
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run mypy . --explicit-package-bases

cat docs/testing_guide.md

UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q <targeted_test_directory_or_marker>
```

Then run the aggregate architecture integrity check and `$duplication-checks` when applicable.
