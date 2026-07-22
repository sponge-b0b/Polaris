---
name: verification-standards
description: Coordinates codebase syntax validation, format checks, static typing verification, and suite testing. Use whenever checking for regressions, reviewing a diff, or running a workspace audit.
license: MIT
compatibility: product=codex product=claude-code system=git system=python network=none
metadata:
  version: 1.0.0
---

# Codebase Verification Standards

## Objective
Enforce consistent formatting, catch hidden type exceptions, and maintain test coverage before code modifications are merged or handed off to a human reviewer.

## Guardrail Constraints
- **Explicit Exclusions:** Never use `round()` in application, intelligence, analysis, regime, calibration, or persistence logic. Keep numeric precision full internally; rounding is permitted only inside human-facing renderers or CLI displays.
- **Python Invariants:** Type all public interfaces. Prefer `@dataclass(frozen=True, slots=True)` for immutable models. 

## Execution Steps

Execute these four validation steps in order. Stop immediately if any step reports a failure.

### Step 1: Automated Lint and Code Formatting
Run `ruff` to ensure layout consistency:
```bash
ruff format --check .
ruff check .
```

### Step 2: Strict Static Type Verification
Run `mypy` using explicit package base routing. Do not assume passing application tests guarantee type cleanliness:
```bash
mypy . --explicit-package-bases
```

### Step 3: Run the Regression Suite
Run your unit tests using isolated cache directories to ensure local changes do not rely on toxic side-effects or state pollution:
```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q
```

### Step 4: Trace & Observability Audit
Verify that newly introduced boundaries implement established telemetry structures:
- Ensure structured logs record exceptions, retries, and caught failures with full tracebacks.
- Confirm active trace spans accompany new data operations.
- **Constraint:** Telemetry failures must remain non-fatal to valid domain results but must be visible in logs. Do not emit duplicate lifecycle events from multiple layers.

## Examples

### Example 1: Post-Implementation Verification
**User:** "Check if my changes are good to go."
**Agent Response:** *"I am running the verification-standards suite (Ruff format checks, MyPy typing verification, and isolated Pytest execution) to validate your changes against project constraints."*
```bash
ruff format --check .
ruff check .
```
```bash
mypy . --explicit-package-bases
```
```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q
```
