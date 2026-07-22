---
name: verify-spec
description: Performs global codebase verification, full static analysis, repository-wide type checking, and strategically targeted integration testing across the spec's relevant modules.
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

## Execution Steps

Execute these macro validation steps in order. Stop immediately if any step reports a failure.

### Step 1: Global Repository Linting & Layout Audit
Verify that the entire repository—including untouched modules and newly integrated configurations—perfectly satisfies project layout standards. Do not pass file subsets:
```bash
uv run ruff format --check .
uv run ruff check .
```

### Step 2: Global Monolithic Type Verification
Run `mypy` over the entire repository root. This is critical for catching edge cases where a change in an individual ticket accidentally broke a type dependency in a file that was never modified during the sprint:
```bash
uv run mypy . --explicit-package-bases
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

### Step 5: Structural Graph Drift Analysis
Invoke your local repository graphing infrastructure to check for architectural boundary violations, dangling nodes, or unmapped dependency breaks against your project ADRs:
```bash
uv run graphify update .
uv run graphify query "Identify any new architectural anomalies or unmapped cross-module dependencies introduced in this sprint."
```

---

## Examples

### Example 1: Pre-Review Integration Verification (Model Migration Spec)
**User:** "All individual implementation tickets for the model migration spec are closed. Let's do a final specification verification."
**Agent Response:** *"I am invoking the verify-spec skill. I will run repository-wide static analysis checks, read docs/testing_guide.md to isolate the relevant strategy and synthesis test categories, and execute those targeted integration tests."*
```bash
# 1. Run global static analysis
uv run ruff format --check .
uv run ruff check .
uv run mypy . --explicit-package-bases

# 2. Read testing guidelines to extract target categories
cat docs/testing_guide.md
# [Agent determines that the 'strategy_pipeline' and 'synthesis_math' categories are required]

# 3. Execute only the relevant macro test directories
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/core/strategy/ tests/core/synthesis/
