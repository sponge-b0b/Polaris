---
name: verify-spec
description: Performs global codebase verification, full static analysis, repository-wide type checking, token-matching to detect duplicate code fragments and clone clusters, and strategically targeted integration testing across the spec's relevant modules.
compatibility: product=codex product=claude-code system=git system=python network=none
disable-model-invocation: true
---

# Global Specification Integration & Verification Skill

## Objective
Validate the entire project repository as a unified system to catch cross-module regressions, integration failures, and type-drift resulting from the completed specification sprint, using our project testing guide to target relevant integration test categories.

## Guardrail Constraints
- **Scope Expansion Invariant:** For formatting, linting, and typing checks, never use partial paths or git status filters. Every static analysis step must evaluate the full repository state (`.`).
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
- **Authorization Override**: If service-free tests do not meet required acceptance criteria, you are authorized to start the required Docker services yourself and run the tests.

### 3. Timeouts & Efficiency Guardrails
- Do not wait for unavailable services to time out when the test is unnecessary.
- Use timeout values that reasonably match expected command duration; if the estimate is wrong, diagnose and adjust rather than using excessive defaults.

---

## Code Quality & Suppression Guardrails

You must preserve the integrity of the project's formatting metrics. You are strictly forbidden from hiding or bypassing linting standards to make a ticket pass verification checks.

### Core Constraint
**Never generate, execute, or commit automated rule suppressions.** 
You are explicitly prohibited from running commands like `ruff check . --select E501 --add-noqa` (or any equivalent variant) to inject `# noqa: E501` comments into the codebase. 

### Compliance Rules
1. **No Automation Cheating:** Long lines must be broken up manually using Python's native syntactic elements (e.g., implicit string concatenation inside parentheses, wrapping data structures, or breaking logical blocks).
2. **Reject Inline Overrides:** If a ticket implementation generates lines exceeding the project's max-character limit, you must refactor the layout of the code until `ruff check .` passes naturally. 
3. **Escalation Exception:** The only acceptable way to change line-length constraints is by modifying the project's global `pyproject.toml` or `ruff.toml` file—and this requires explicit, manual human authorization before execution.

## Execution Steps

Execute these macro validation steps in order.

### Step 1: Global Repository Linting & Layout Audit
Verify that the entire repository—including untouched modules and newly integrated configurations—perfectly satisfies project layout standards. Do not pass file subsets:
```bash
ruff format --check .
ruff check .
```

### Step 2: Global Monolithic Type Verification
Run `mypy` over the entire repository root. This is critical for catching edge cases where a change in an individual ticket accidentally broke a type dependency in a file that was never modified during the sprint:
```bash
mypy . --explicit-package-bases
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
Invoke graphing infrastructure to check for architectural anomalies or unmapped cross-module dependencies introduced in this spec implementation:
```bash
graphify update .
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

## Verification Reporting & Remediation Check

If any step in the macro validation pipeline fails, you must compile an aggregated, highly actionable failure and remediation report. 

### Core Constraint
You are strictly forbidden from simply outputting raw stack traces or ending the execution loop on the first tool crash. You must gather the failures across all verification steps, synthesize the underlying core issues, and provide direct, actionable steps to fix them.

### Reporting Criteria
For any errors detected by `ruff`, `mypy`, `pytest`, `graphify`, or `/duplication-checks`, your final response must contain a structured **Verification Failure Summary** using the following breakdown:

1. **Aggregated Failure Inventory:** Group errors logically by the tool that caught them (e.g., Syntax/Formatting, Type Drift, Regression Failures, Architectural Drift, or Duplication Clones).
2. **Root Cause Analysis:** A brief, clear synthesis explaining *why* these failures occurred (e.g., a shared helper signature changed, breaking down-stream typing contract blocks).
3. **Remediation Roadmap:** A step-by-step, actionable checklist providing the exact file paths, lines of code, or command blocks the developer needs to modify to achieve a passing verification state.

### Example Interaction Fragment

**Agent Response (Post-Tool Failure):**
*"❌ **Specification Verification Failed.** The macro validation pipeline caught multiple cross-module integration issues. Below is the failure summary and a remediation roadmap to resolve them:

### 1. Failure Inventory
- **Type Drift (mypy):** `titan/agents/routing.py:42` — `Invalid return type (expected Dict, got Option)`
- **Regression Failures (pytest):** `tests/core/strategy/test_pipeline.py:118` — `AssertionError: Expected metric value 0.95, got 0.88`
- **Duplication Clone (/duplication-checks):** `jscpd` flagged an 85% token match between your new `utils/math_helpers.py` and the existing `titan/math/calculators.py`.

### 2. Root Cause Analysis
The model changes introduced in your specification altered the payload contract inside `routing.py`. This caused typing drift down the pipeline, which directly caused the strategy integration test to fail due to miscalculated metrics. Furthermore, the new math utility functions replicate existing codebase infrastructure.

### 3. Remediation Roadmap
- [ ] **Fix Typing:** Modify line 42 of `titan/agents/routing.py` to cleanly unpack the `Option` block before passing it down the stream.
- [ ] **Consolidate Code:** Delete `utils/math_helpers.py` entirely and refactor your new component to import the canonical wrappers from `titan/math/calculators.py`.
- [ ] **Re-verify:** Once these adjustments are complete, re-run `/verify-spec` to confirm the regression suite passes."*

## Examples

### Example 1: Pre-Review Integration Verification (Model Migration Spec)
**User:** "All individual implementation tickets for the model migration spec are closed. Let's do a final specification verification."
**Agent Response:** *"I am invoking the verify-spec skill. I will run repository-wide static analysis checks, read docs/testing_guide.md to isolate the relevant strategy and synthesis test categories, and execute those targeted integration tests."*
```bash
# 1. Run global static analysis
ruff format --check .
ruff check .
mypy . --explicit-package-bases

# 2. Read testing guidelines to extract target categories
cat docs/testing_guide.md
# [Agent determines that the 'strategy_pipeline' and 'synthesis_math' categories are required]

# 3. Execute only the relevant macro test directories
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/core/strategy/ tests/core/synthesis/
```
