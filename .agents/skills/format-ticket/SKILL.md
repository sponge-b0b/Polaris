---
name: format-ticket
description: Formats, cleans, and structures only the specific files modified or generated as part of the current active issue ticket. Use whenever work is being performed on an individual ticket using the /implement-ticket skill, or when a ticket is ready for formatting before running local verification checks.
license: MIT
compatibility: product=codex product=claude-code system=git system=python network=none
metadata:
  version: 1.0.0
---

# Targeted Ticket Code-Formatting and Auto-Fix Style Skill

## Objective
Enforce strict syntactic consistency and layout rules strictly across files altered or introduced by the active issue ticket, fixing auto-resolvable lint issues and aligning modified blocks with standard project coding guidelines.

## Guardrail Constraints
- **Isolation Principle:** Only perform formatting actions on files touched by the current ticket. Do not introduce refactors, delete unrelated feature modules, or modify logical variable assignments. Never run global repository-wide formatting commands inside an isolated ticket lifecycle.
- **Scope Extraction Invariant:** Before running any style checks, you must explicitly identify the modified file paths using local version control records or active workspace diffs.
- **Safety Invariant:** If targeted lint fixes produce errors that cannot be solved automatically, halt immediately. Do not attempt to guess manual overrides; log the file paths and error details clearly for the developer or next workflow block.

---

## Execution Steps

Execute these formatting and correction operations sequentially to standardize your targeted code alterations:

### Step 1: Identify Targeted Changes
Locate and isolate the precise file paths modified or created as part of the current ticket scope. Use `git status` or internal session tracking to extract the explicit target list:
```bash
git status --porcelain | awk '{print $2}' | grep '\.py$'

```

### Step 2: Targeted Automated Lint Correction
Execute the `ruff` lint engine using the explicit auto-fixer modifier, targeting **only** the space-separated list of file paths extracted in Step 1. Do not use a trailing dot (`.`):
```bash
ruff check --fix <path_to_modified_file_1> <path_to_modified_file_2>
```

### Step 3: Targeted Code Layout Standardisation
Execute the native code formatter over **only** the identified target file paths to adjust line spacing, wrapping bounds, indentation, and quote alignments to match our 88-character rule baseline:
```bash
ruff format <path_to_modified_file_1> <path_to_modified_file_2>
```

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

## Examples

### Example 1: Isolated Ticket Code Cleanup
**User:** "I just finished writing the code modifications for ticket #4."
**Agent Response:** *"I am invoking the format-ticket skill to identify the specific files changed under ticket #4, automatically resolve targeted lint warnings, and format those exact Python structures before triggering validation."*
```bash
# 1. Agent identifies targeted changes (e.g., core/runtime/execution/runtime_engine.py)
# 2. Agent runs targeted lint correction
ruff check --fix core/runtime/execution/runtime_engine.py

# 3. Agent runs targeted code formatting
ruff format core/runtime/execution/runtime_engine.py
```
