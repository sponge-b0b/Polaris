---
name: using-graphify
description: Queries the repository's structural dependency graph using the Graphify CLI tool. Use to answer questions about architecture, file dependencies, code paths, and component logic.
compatibility: system=graphify>=0.9.20
---

# Codebase Graph Query, Navigation, and Analysis Skill

## Objective
Leverage local repository graph tooling (`graphify`) to analyze codebase structure, trace execution paths, and explain relationships between modules.

## Guardrails
- **Performance Invariant:** Never attempt to read, open, or parse files inside the `graphify-out/` directory (e.g., `graphify-out/graph.json`) using standard shell commands (`cat`, `grep`, `jq`). Always interface via the CLI.
- **Index Lifecycle:** If a command returns an error or if `graphify-out/graph.json` is missing, you must run the full-stack extraction and clustering routine sequentially to ensure both Python syntax and Markdown documentation nodes are preserved:
  ```bash
  uv run graphify extract . --max-concurrency 1
  uv run graphify cluster-only . --max-concurrency 1
  ```
- **Fallback Execution:** If `uv` is not present or configured in the project root, drop the prefix and execute the tool directly: `graphify <command>`.

---

## Capabilities & Workflows

### 1. General Structural Queries
*Use when the user asks broad conceptual or architectural questions about file relationships or architectural boundaries.*
- **Action**: Pass a descriptive natural language prompt directly to the query router.
- **Command**:
  ```bash
  uv run graphify query "<your architectural or structural question>"
  ```

### 2. Component and Logic Explanations
*Use when you need a deep, context-aware explanation of a specific module, class, function, or file without manually reading hundreds of lines of code.*
- **Action**: Targeted extraction of functional logic using the code semantics engine.
- **Command**:
  ```bash
  uv run graphify explain "<target component, file path, or feature logic>"
  ```

### 3. Dependency Path Tracing
*Use when evaluating the impact of a refactor, tracing how an error propagates, or figuring out how file A is connected to file B.*
- **Action**: Trace the directional path/bridge between two explicit codebase targets.
- **Command**:
  ```bash
  uv run graphify path "<source_file_or_symbol>" "<target_file_or_symbol>"
  ```

---

## Examples

### Example 1: Finding Module Dependencies (Query)
**User:** "Which components currently consume the WorkflowFacade?"
**Agent Response:** *"I will use the using-graphify skill to query the structural graph for consumers of the WorkflowFacade."*
```bash
uv run graphify query "Which components currently consume the WorkflowFacade"
```

### Example 2: Analyzing Complex Logic (Explain)
**User:** "Can you explain how the data ingestion pipeline handles backpressure?"
**Agent Response:** *"I will leverage Graphify to extract and explain the system logic managing ingestion backpressure."*
```bash
uv run graphify explain "data ingestion pipeline backpressure handling"
```

### Example 3: Tracing Code Couplings (Path)
**User:** "Is the database service tightly coupled to our API router layer?"
**Agent Response:** *"I will trace the dependency path between the database service and the API router to assess structural coupling."*
```bash
uv run graphify path "src/services/database.py" "src/api/router.py"
```
