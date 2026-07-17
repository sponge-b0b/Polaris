---
name: using-graphify
description: Queries or updates the repository's structural dependency graph using the Graphify CLI tool. Use when the user asks questions about code structure/imports, or immediately following code changes and file creations to refresh the index.
compatibility: system=graphify
---

# Codebase Graph Query and Update Skill

## Objective
Leverage local repository analysis tooling to answer structural questions about the project codebase, and maintain index freshness following code modifications without exposing heavy raw data to the LLM context.

## Guardrails
- **Performance Invariant:** Do not read, open, or parse `graphify-out/` or `graphify-out/graph.json` directly using standard shell viewers during a session.
- **Tool Fallback:** If a query is requested but `graphify-out/graph.json` does not exist, you must execute Workflow B to generate the index first before performing the search.

---

## Execution Workflows

### [WORKFLOW A] Querying the Structural Graph
*Use this workflow when answering questions about file relationships, imports, or architecture invariants.*

1. Parse the user's codebase or architectural question.
2. Formulate a targeted, descriptive question string.
3. Run the canonical CLI query command:
   ```bash
   uv run graphify query "<your formulated question>"
   ```
4. Analyze the CLI tool output and present the distilled dependency or relationship layout.

### [WORKFLOW B] Updating / Refreshing the Graph Index
*Use this workflow immediately after code changes, refactors, or file creations are saved, ensuring following tasks read an accurate map.*

1. Run the local repository graph update command over the project root directory:
   ```bash
   uv run graphify update .
   ```
2. Verify that the command exits successfully with a newly refreshed `graphify-out/graph.json` layout.

---

## Examples

### Example 1: Finding Module Dependencies (Workflow A)
**User:** "Which components currently consume the WorkflowFacade?"
**Agent Response:** *"I am using the using-graphify skill to run a dependency query over our architecture graph."*
```bash
uv run graphify query "Which components currently consume the WorkflowFacade"
```

### Example 2: Refreshing after Code Changes (Workflow B)
**User:** "I finished adding the new repository layer files. What's next?"
**Agent Response:** *"I will use the using-graphify skill to update our codebase graph index so future queries recognize the new file layers."*
```bash
uv run graphify update .
```
