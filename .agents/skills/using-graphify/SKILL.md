---
name: using-graphify
description: Queries the repository's structural dependency graph using the Graphify CLI tool. Use when the user asks questions about code structure, imports, or file relationships.
compatibility: system=graphify
---

# Codebase Graph Query Skill

## Objective
Leverage local repository analysis tooling to answer structural questions about the Polaris codebase without reading heavy raw files into the active LLM context.

## Guardrails
- **Performance Invariant:** Do not read, open, or parse `graphify-out/` or `graphify-out/graph.json` directly during routine execution or startup. 
- **Tool Selection:** Only execute graph queries if `graphify-out/graph.json` exists in the environment workspace.

## Execution Steps
1. Parse the user's codebase or architectural question.
2. Formulate a targeted, descriptive question string.
3. Run the canonical CLI command using the exact pattern:
   ```bash
   uv run graphify query "<your formulated question>"
   ```
4. Analyze the CLI output and present the distilled dependency or relationship structure back to the user.

## Examples

### Example 1: Finding Module Dependencies
**User:** "Which components currently consume the WorkflowFacade?"
**Agent Response:** *Detects structural query, verifies graph.json exists, and runs the tool:*
```bash
uv run graphify query "Which components currently consume the WorkflowFacade"
```
