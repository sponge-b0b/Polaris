---
name: code-formatting
description: Formats, cleans, and structures Python files according to project-wide style guidelines. Use whenever code has been modified, new files are generated, or before passing a workspace task to the verification suite.
license: MIT
compatibility: product=codex product=claude-code system=git system=python network=none
metadata:
  version: 1.0.0
---

# Code-Formatting and Auto-Fix Style Skill

## Objective
Enforce strict syntactic consistency and layout rules across the repository by fixing auto-resolvable lint issues and aligning file code blocks with our standard coding guidelines.

## Guardrail Constraints
- **Isolation Principle:** Only perform formatting actions. Do not introduce refactors, delete feature modules, or modify logical variable assignments during this pass.
- **Safety Invariant:** If `ruff check --fix .` produces errors that cannot be solved automatically, halt immediately. Do not attempt to guess manual overrides; log the error details clearly for the developer or next workflow block.

---

## Execution Steps

Execute these formatting and correction operations sequentially to standardize your code alterations:

### Step 1: Automated Lint Correction
Execute the `ruff` lint engine using the explicit auto-fixer modifier to automatically resolve safe code violations, unused imports, and sorting invariants:
```bash
uv run ruff check --fix .
```

### Step 2: Code Layout Standardisation
Execute the native code formatter to adjust line spacing, wrapping bounds, indentation, and quote alignments to match our 88-character rule baseline:
```bash
uv run ruff format .
```

---

## Examples

### Example 1: Code Post-Generation Cleanup
**User:** "I just finished writing the new StrategyEvidenceContext data classes."
**Agent Response:** *"I am invoking the code-formatting skill to automatically resolve lint warnings and format your new Python script structures before handing the workspace off to verification."*
```bash
uv run ruff check --fix .
uv run ruff format .
```
