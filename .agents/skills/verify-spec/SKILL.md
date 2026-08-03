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

1. **Extract Baseline Metadata**: `/to-tickets` posts the baseline as a **comment** on the parent spec issue (it never edits the issue body — see the Spec Branch Rule in `/to-tickets`), so fetch comments specifically, not just the body, to find and parse the **Baseline Commit Hash**:
   ```bash
   BASELINE_COMMIT=$(gh issue view <spec_issue_number> --json comments -q '.comments[].body' \
     | grep -oP '(?<=\*\*Baseline Commit Hash:\*\* )\S+' | tail -1)
   ```
2. **Fallback**: If the metadata is missing (checked across the issue's comments) and the user did not explicitly specify a commit SHA, branch name, tag, or relative ref (e.g., `main`, `HEAD~5`), ask the user for it directly.
3. **Verify Branch Checked Out**: Ensure `spec-<spec_issue_number>` is actually the currently checked-out branch before running the diff commands below — there's no isolated worktree here to make this automatic, so it's easy to accidentally review against the wrong branch if something switched branches earlier in the session:
   ```bash
   CURRENT_BRANCH=$(git branch --show-current)
   if [ "$CURRENT_BRANCH" != "spec-<spec_issue_number>" ]; then
     echo "❌ Expected spec-<spec_issue_number> to be checked out, but current branch is $CURRENT_BRANCH. Checkout the spec branch before continuing."
     exit 1
   fi
   ```
4. **Validate the Ref**: Confirm the extracted or provided fixed point resolves locally by running:
   ```bash
   git rev-parse <fixed-point>
   ```
   *If the ref is bad or fails to resolve, halt execution immediately with a clear error message.*
5. **Capture Diff and Log**: Once validated, capture the targeted differential context since development started:
   * **The Diff**: Run `git diff <fixed-point>...HEAD` (three-dot comparison to evaluate strictly against the merge-base).
   * **The Commit Log**: Run `git log <fixed-point>..HEAD --oneline` to note the exact list of commits authored on this spec branch.
6. **Pre-Flight Check**: Verify that the generated diff is non-empty. An empty diff or unresolved ref must fail immediately here—never inside down-stream parallel sub-agents. Use this comprehensive diff as the primary source of truth to review if the aggregate changes accurately satisfy the parent specification goals.

## 2. Identify the spec source

Look for the originating spec, in this order:

1. Issue references in the commit messages (`#123`, `Closes #45`, GitLab `!67`,
   etc.) — fetch via the workflow in `docs/agents/issue-tracker.md`.
2. A path the user passed as an argument.
3. A spec file under `docs/`, `specs/`, or `.scratch/` matching the branch name
   or feature.
4. If nothing is found, ask the user where the spec is. If they say there isn't
   one, the **Spec** sub-agent will skip and report "no spec available".

## Objective
Validate the completed specification branch as a unified system to catch cross-module regressions, integration failures, and type-drift resulting from the completed specification sprint, using explicitly authorized repository-wide static analysis and the project testing guide to target relevant integration test categories.

## Guardrail Constraints
- **Authorization Invariant:** `/verify-spec` is a macro/spec-level verification workflow. Its explicit invocation by the user for the current task is the current-task authorization for the repository-wide static analysis commands named by this skill. This authorization does **not** extend to untargeted full-suite pytest, coverage, or service-backed integration runs. If this skill was not explicitly invoked, or if you are verifying an individual ticket or targeted code change, do **not** use this skill's broad static checks; defer to `/verify-code` and run changed-file/targeted verification only.
- **Command Guard Invariant:** Do not bypass the Polaris command guard with absolute paths, backup executable paths, copied binaries, subshell tricks, or renamed commands. For the guarded repository-wide `ruff` and `mypy` commands below, set `POLARIS_BROAD_VERIFY_AUTHORIZED` to a current-task label such as `verify-spec-<spec_issue_number>`. If the guard refuses a command, stop and resolve the authorization/scope issue instead of routing around it.
- **Scope Expansion Invariant:** Once `/verify-spec` has been explicitly invoked, formatting, linting, and typing checks must not use partial paths or git status filters. Every static analysis step must evaluate the full repository state (`.`) using the authorized command form shown below.
- **Testing Blueprint Invariant:** You are strictly forbidden from guessing which integration tests to execute or blindly running the entire monolithic suite of thousands of tests. You must read and follow the category filters outlined in `docs/testing_guide.md` to isolate the correct test suites.

## Execution Rules & Constraints

### 1. Test Targeting & Scope Identification
- Do not run a full test suite by default. First determine whether full-suite verification is necessary for the change scope.
- Prefer targeted tests tied directly to changed files, affected boundaries, and known regression risks.
- Report optional live validations separately from required service-free verification.

### 2. Environment & Service Dependency Check
- Ensure all tests use environment variables or redacted placeholders.
- Before running integration or live-service tests, identify required infrastructure services: `PostgreSQL`, `Qdrant`, `Neo4j`, `LiteLLM`, `Ollama`, `Langfuse`, `BGE reranker`, `Prometheus`, `Jaeger`, or `Grafana`.
- If required Docker services are not confirmed running, either notify the user before running those tests or choose service-free targeted tests instead.
- **Authorization Override**: If service-free tests do not meet required acceptance criteria, you are authorized to start only the required Docker services yourself and run the targeted tests.
- **Targeted Integration Skip Remediation**: A selected targeted integration or regression test that skips only because a repo-local environment variable or local service is missing is not verified. If a DB-backed test needs `POLARIS_TEST_DATABASE_URL`, derive a safe local value from `.env`, `.env.example`, `docker-compose.yml`, test fixtures, or typed settings when possible, start only the required local service when authorized, and rerun the exact targeted test. Never echo full connection strings or secrets. Do not broaden to untargeted full-suite, full coverage, or unrelated service-backed integration runs to compensate for the skip.

### 3. Timeouts & Efficiency Guardrails
- Do not wait for unavailable services to time out when the test is unnecessary.
- Use timeout values that reasonably match expected command duration; if the estimate is wrong, diagnose and adjust rather than using excessive defaults.

---

## Code Quality & Suppression Guardrails

You must preserve the integrity of the project's formatting metrics. You are strictly forbidden from hiding or bypassing linting standards to make a ticket pass verification checks.

### Core Constraint
**Never generate, execute, or commit automated rule suppressions.** 
You are explicitly prohibited from running commands like `ruff check . --select E501 --add-noqa` (or any equivalent variant like `C901`) to inject `# noqa: E501` or `C901` comments into the codebase. You must never use `--add-noqa` in any form to bypass or suppress project rules. All formatting must be achieved through proper code restructuring and layout adjustments.

### Compliance Rules
1. **No Automation Cheating:** Long lines must be broken up manually using Python's native syntactic elements (e.g., implicit string concatenation inside parentheses, wrapping data structures, or breaking logical blocks).
2. **Reject Inline Overrides:** If a ticket implementation generates lines exceeding the project's max-character limit, you must refactor the layout of the code until `ruff check .` passes naturally. 
3. **Escalation Exception:** The only acceptable way to change line-length constraints is by modifying the project's global `pyproject.toml` or `ruff.toml` file—and this requires explicit, manual human authorization before execution.

## Execution Steps

Execute these macro validation steps in order.

### Step 1: Global Repository Linting & Layout Audit
Verify that the entire repository—including untouched modules and newly integrated configurations—perfectly satisfies project layout standards. Do not pass file subsets:
```bash
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff format --check .
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff check .
```

### Step 2: Global Monolithic Type Verification
Run `mypy` over the entire repository root. This is critical for catching edge cases where a change in an individual ticket accidentally broke a type dependency in a file that was never modified during the sprint:
```bash
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run mypy . --explicit-package-bases
```

### Step 3: Analyze Testing Matrix Guidelines
Read the master testing blueprint file to understand the system's test categories, run constraints, and external dependencies:
```bash
cat docs/testing_guide.md
```
Identify the specific integration, pipeline, or macro test groups that match the components introduced or modified during this specification sprint. Check if the required categories dictate launching local Docker services.

### Step 4: Execute Targeted Integration and Regression Suites
Execute the specific test folders or category markers identified in Step 3:
```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q <targeted_test_directory_or_marker>
```

### Step 5: Execute Targeted Architectural Check
Invoke graphing infrastructure to check for architectural anomalies or unmapped cross-module dependencies introduced in this spec implementation. `--update` is a flag on the target path, not a subcommand — `graphify update .` is invalid syntax and will not do what's intended:
```bash
graphify . --update
graphify query "<canonical concepts and changed subsystems from the spec>"
```
Verifier is required to answer:

- Did the changed modules connect to the expected canonical owner?
- Did any edge-facing layer bypass the expected application/domain boundary?
- Did the graph reveal duplicate ownership of a durable concept?
- Did any dependency point inward/outward against the repo’s architecture rules?

---

## Duplication Verification Check

When verifying a specification, you must ensure the new requirements do not introduce structural bloat or split-brain business logic into the codebase. 

### Core Constraint
Before approving any specification that introduces a new module, helper function, utility layer, or service, you must explicitly run the `/duplication-checks` skill.

### Verification Criteria
1. **Trigger Scan:** Execute `/duplication-checks` using both `pylint` and `jscpd` over the targets outlined in the specification.
2. **Review Findings:** Examine the duplicate code outputs or structural clone blocks flagged by the scanner.
3. **Enforce Single Source of Truth:** 
   - **Fail Verification** if the specification proposes building a component that mirrors logic already present in the codebase.
   - **Require Revision** to force the specification to modify, reuse, or inherit from the existing canonical interface instead of creating a parallel implementation.

## Examples

### Example 1: Pre-Review Integration Verification (Model Migration Spec)
**User:** "All individual implementation tickets for the model migration spec are closed. Let's do a final specification verification."
**Agent Response:** *"I am invoking the verify-spec skill. I will run repository-wide static analysis checks, read docs/testing_guide.md to isolate the relevant strategy and synthesis test categories, and execute those targeted integration tests."*
```bash
# 1. Run authorized global static analysis
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff format --check .
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff check .
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run mypy . --explicit-package-bases

# 2. Read testing guidelines to extract target categories
cat docs/testing_guide.md
# [Agent determines that the 'strategy_pipeline' and 'synthesis_math' categories are required]

# 3. Execute only the relevant macro test directories
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/core/strategy/ tests/core/synthesis/
```
