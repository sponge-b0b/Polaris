---
name: verify-ticket
description: Performs syntax validation, format checks, static typing verification, and targeted testing *only* on the specific files modified or generated as part of the current active issue ticket. Use whenever work is being performed on an individual ticket using the /implement-ticket skill, or when a ticket is ready for verification before merging or handing off to a human reviewer.
license: MIT
compatibility: product=codex product=claude-code system=git system=python network=none
metadata:
  version: 1.0.0
---

# Targeted Ticket Codebase Verification Standards

## Objective
Enforce consistent formatting, catch hidden type exceptions, and maintain test coverage *strictly* for code alterations introduced by the active issue ticket, ensuring stability before changes are merged or handed off.

## Guardrail Constraints
- **Explicit Exclusions:** Never use `round()` in application, intelligence, analysis, regime, calibration, or persistence logic. Keep numeric precision full internally; rounding is permitted only inside human-facing renderers or CLI displays.
- **Python Invariants:** Type all public interfaces. Prefer `@dataclass(frozen=True, slots=True)` for immutable models. 
- **Scope Extraction Invariant:** Before running any verification checks, you must explicitly isolate the modified file paths using local version control records. Never run global repository-wide check commands inside an isolated ticket lifecycle.

---

## Execution Steps

Execute these four validation steps in order. Stop immediately if any step reports a failure.

### Step 1: Identify Targeted Changes
Locate and isolate the precise file paths modified or created as part of the current ticket scope. Use `git status` or internal session tracking to extract the explicit target list:
```bash
git status --porcelain | awk '{print $2}' | grep '\.py$'
```

### Step 2: Verify Format
Run `ruff` to ensure layout consistency over **only** those space-separated file targets. Do not use a trailing dot (`.`):
```bash
uv run ruff format --check <path_to_modified_file_1> <path_to_modified_file_2>
uv run ruff check <path_to_modified_file_1> <path_to_modified_file_2>
```

### Step 3: Targeted Static Type Verification
Run `mypy` using explicit package base routing, checking **only** the identified target files to keep type-checking rapid and isolate scope regressions:
```bash
uv run mypy --explicit-package-bases <path_to_modified_file_1> <path_to_modified_file_2>
```

### Step 4: Targeted Testing
Run only the tests relevant to modified ticket files using isolated cache directories.
**Identify Required Services:** Before running integration or live-service tests, identify required services such as PostgreSQL, Qdrant, Neo4j, LiteLLM, Ollama, Langfuse, BGE reranker, Prometheus, Jaeger, or Grafana. If required Docker services are not confirmed running, either notify the user before running those tests or choose service-free targeted tests instead. If service-free tests do not meet required acceptance criteria then you are authorized to start the services yourself and run the tests.
```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/path/to/test_relevant_module.py
```

### Step 5: Trace & Observability Audit
Verify that newly introduced boundaries implement established telemetry structures within the modified files:
- Ensure structured logs record exceptions, retries, and caught failures with full tracebacks.
- Confirm active trace spans accompany new data operations.
- **Constraint:** Telemetry failures must remain non-fatal to valid domain results but must be visible in logs. Do not emit duplicate lifecycle events from multiple layers.

---

## Examples

### Example 1: Isolated Ticket Post-Implementation Verification
**User:** "Verify ticket changes for runtime engine updates."
**Agent Response:** *"I am invoking the verify-ticket skill to identify the specific files modified, check their layout with Ruff, run isolated MyPy type verification over those files, and execute targeted Pytest scripts."*
```bash
# 1. Agent identifies targeted changes (e.g., core/runtime/execution/runtime_engine.py)
# 2. Agent runs targeted lint/format checks
uv run ruff format --check core/runtime/execution/runtime_engine.py
uv run ruff check core/runtime/execution/runtime_engine.py

# 3. Agent runs targeted type checks
uv run mypy --explicit-package-bases core/runtime/execution/runtime_engine.py

# 4. Agent runs targeted tests
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/core/runtime/test_runtime_engine.py
```
