---
name: duplication-checks
description: Runs static code analysis and token-matching tools to detect duplicate code fragments and clone clusters. Use before extracting shared utilities, creating helper modules, or starting a refactor.
license: MIT
compatibility: product=codex product=claude-code system=pylint system=jscpd network=none
metadata:
  version: 1.0.0
---

# Code Duplication Checks

## Objective
Prevent codebase bloat and guard against split-brain logic by identifying existing equivalent code or structural patterns before introducing new helper files or utilities.

## Guardrail Constraints
- **Single Source of Truth:** Do not create a new helper function, service locator, or wrapper module until existing codebase logic has been explicitly audited and ruled out. 
- **Architectural Boundary:** Stop immediately if an analysis shows two separate components attempting to claim authoritative ownership over the same business domain or calculation rule.

## Execution Steps

Execute these duplication scanning tools over the workspace target paths before mapping out a refactor or utility extraction:

### Step 1: Python Native Structural Scan
Run `pylint` with all rule blocks disabled except for the duplicate-code signature checker to scan recursively for cloned Python blocks:
```bash
pylint --disable=all --enable=duplicate-code --recursive=y .
```

### Step 2: Multi-Language Token Sequence Scan
Run `jscpd` across the repository root to catch structural code clones, configuration layer mirroring, or copy-pasted blocks across different layers:
```bash
npx jscpd .
```

### Step 3: Analysis & Consolidation Rule
- Review the matching lines or token arrays reported by the tooling.
- If a matching helper sequence already exists in the repository, refactor the active code block to safely inherit or consume the existing canonical interface instead of creating a parallel implementation.

## Examples

### Example 1: Pre-Refactor Analysis Trigger
**User:** "I want to extract some utility functions for formatting these metrics before writing the plan."
**Agent Response:** *"I am triggering the duplication-checks skill via Pylint and jscpd to verify if equivalent metrics layout logic already exists in the codebase before we design a new helper module."*
