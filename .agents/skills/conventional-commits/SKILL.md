---
name: conventional-commits
description: Enforces strict adherence to the Conventional Commits 1.0.0 specification for staging and saving changes. Use when a user asks to commit files, draft a git message, or finalize code tasks.
license: MIT
compatibility: product=claude-code product=codex system=git network=none
metadata:
  version: 1.0.0
  specification: conventional-commits-1.0.0
---

# Git Commit Guidelines

## Objective
Structure every Git commit message in strict compliance with the Conventional Commits 1.0.0 specification. Never write generic, conversational, or vague commit summaries (e.g., do not use "wip", "updated files", or "fixed bug").

## Message Structure Blueprint
Every commit message must follow this structural schema exactly:
```text
<type>[optional scope]: <description>

[optional body describing why the change was made]
```
- **Type**: Must be entirely lowercase. Use only the approved structural types listed below.
- **Scope**: Optional but highly encouraged. Represents the specific software layer or folder module modified, wrapped in lowercase parentheses (e.g., `(reranker)`, `(api)`, `(db)`).
- **Description**: Written in the **imperative mood** (e.g., use `add` instead of `added`, `fix` instead of `fixes`). Do not capitalize the first letter and do not add a trailing period.

## Approved Structural Types
Map code changes strictly to these categories:
- **`feat(scope)`**: Used when introducing a brand-new application feature or operational capability to the codebase.
- **`fix(scope)`**: Used when correcting an active bug, permission block, error log, or software crash.
- **`docs(scope)`**: Used for changes restricted entirely to documentation layout text, markdown headers, and user guides.
- **`chore(scope)`**: Used for routine maintenance operations: package/dependency management, editing configurations (`.gitignore`, `pyproject.toml`, `.graphifyignore`), or adding static asset/image files.
- **`refactor(scope)`**: Used for optimization or structural alterations to production code that do not change its runtime features or behavior.
- **`test(scope)`**: Used when generating unit tests, increasing coverage matrix setups, or altering testing suites.
- **`ci(scope)`**: Used for orchestration scripts, automated pipelines, deployment assets, or Docker Compose structures.

## Handling Breaking Changes
If an engineering operation changes the system's foundational layout or breaks backward compatibility, append an exclamation point (`!`) directly to the commit type prefix and write `BREAKING CHANGE:` in the commit message body explaining the required manual migration layout steps.
*Example:* `feat(db)!: switch token storage mapping to postgresql`

## Examples

### Example 1: Standard Staging & Commit Flow
**User:** "Commit my backend updates."
**Agent Response:** *Runs `git diff --cached` to evaluate the staging area, determines that a new validation routine was added to an API component, and structures the commit message:*
```bash
git commit -m "feat(api): include cross-encoder payload validation schemas"
```

### Example 2: Bug Fix Flow
**User:** "Save the changes that fixed the permission crash."
**Agent Response:** *Evaluates changes and structures the commit:*
```bash
git commit -m "fix(reranker): map container user permissions to prevent wsl lockouts"
```

### Example 3: Infrastructure and Documentation Tasks
*   `chore(git): add graphify local cache paths to gitignore file`
*   `docs(deployment): supplement setup documentation detailing offline launch instructions`
