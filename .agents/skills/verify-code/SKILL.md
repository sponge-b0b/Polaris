---
name: verify-code
description: Performs syntax validation, format checks, static typing verification, and targeted testing on modified or newly generated files in the workspace. Use whenever work is being performed on an individual ticket (e.g., using the /implement-ticket skill) OR, on-demand anytime current working files require verification before merging or handing off to a human reviewer.
license: MIT
compatibility: product=codex product=claude-code system=git system=python network=none
metadata:
  version: 1.0.0
---

# Targeted Codebase Verification Standards

## Objective
Enforce consistent formatting, catch hidden type exceptions, and maintain test coverage *strictly* for code alterations introduced in the workspace OR by the active issue ticket, ensuring stability before changes are merged or handed off.

## Guardrail Constraints
- **Explicit Exclusions:** Never use `round()` in application, intelligence, analysis, regime, calibration, or persistence logic. Keep numeric precision full internally; rounding is permitted only inside human-facing renderers or CLI displays.
- **Python Invariants:** Type all public interfaces. Prefer `@dataclass(frozen=True, slots=True)` for immutable models. 
- **Isolation Principle:** Only perform verification actions on files touched in the workspace OR by the current ticket. Do not introduce refactors, delete unrelated feature modules, or modify logical variable assignments. Never run global repository-wide verification commands inside an isolated workspace OR ticket lifecycle.
- **Scope Extraction Invariant:** Before running any verification checks, you must explicitly isolate the modified file paths using local version control records or active workspace diffs.
- **Safety Invariant:** If targeted verification checks produce errors that cannot be solved automatically, do not attempt to guess manual overrides; log the file paths and error details clearly for the developer or next workflow block and report when completed.

---

## Execution Steps

Execute these four validation operations sequentially to standardize your targeted code verifications:

### Step 1: Identify Targeted Changes
Locate and isolate the precise file paths modified or created in the workspace OR as part of the current ticket scope. Use `git status` or internal session tracking to extract the explicit target list:
```bash
git status --porcelain | awk '{print $2}' | grep '\.py$'
```

### Step 2: Verify Format
Run `ruff` to ensure layout consistency over **only** those space-separated file targets. Do not use a trailing dot (`.`):
```bash
ruff format --check <path_to_modified_file_1> <path_to_modified_file_2>
ruff check <path_to_modified_file_1> <path_to_modified_file_2>
```

### Step 3: Targeted Static Type Verification
Run `mypy` using explicit package base routing, checking **only** the identified target files to keep type-checking rapid and isolate scope regressions:
```bash
mypy --explicit-package-bases <path_to_modified_file_1> <path_to_modified_file_2>
```

### Step 4: Targeted Testing
Run only the tests relevant to modified or created files in the workspace OR as part of the current ticket scope, using isolated cache directories.
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

### Example 1: Isolated Post-Implementation Verification
**User:** "Verify ticket changes for runtime engine updates."
**Agent Response:** *"I am invoking the verify-code skill to identify the specific files modified, check their layout with Ruff, run isolated MyPy type verification over those files, and execute targeted Pytest scripts."*
```bash
# 1. Agent identifies targeted changes
git status --porcelain | awk '{print $2}' | grep '\.py$'

# 2. Agent runs targeted lint/format checks
ruff format --check core/runtime/execution/runtime_engine.py
ruff check core/runtime/execution/runtime_engine.py

# 3. Agent runs targeted type checks
mypy --explicit-package-bases core/runtime/execution/runtime_engine.py

# 4. Agent runs targeted tests
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/core/runtime/test_runtime_engine.py
```

### Example 2: Workspace Code Verification
**User:** "Can you verify the files I've been working on before I push my changes?"
**Agent Response:** *"I am invoking the verify-code skill to identify the specific files you worked on, check their layout with Ruff, run isolated MyPy type verification over those files, and execute targeted Pytest scripts."*
```bash
# 1. Agent identifies targeted changes
```bash
git status --porcelain | awk '{print $2}' | grep '\.py$'

# 2. Agent runs targeted lint/format checks
ruff format --check core/auth/login.py tests/test_login.py
ruff check core/auth/login.py tests/test_login.py

# 3. Agent runs targeted type checks
mypy --explicit-package-bases core/auth/login.py tests/test_login.py

# 4. Agent runs targeted tests
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q core/auth/login.py tests/test_login.py
```
