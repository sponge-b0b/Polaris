---
name: using-repowise
description: Queries local repository code, structural overviews, dead code references, and file risk markers via Repowise tools. Use before editing python files or when exploring existing codebase implementations or when the user asks questions about architecture, code structure, imports, or file relationships.
---

# Repowise Queries Skill

## Objective
Safely locate behavior, map source contexts, sweep for dead code, evaluate file brittleness, estimate change blast radiuses before modifying any Python files, and to answer structural questions about the project codebase without reading heavy raw files into the active LLM context.

## Context Inputs
- **Authoritative Cache Map:** `.claude/CLAUDE.md`.
- Before executing any lookup tool, reference this cached markdown segment to evaluate system summaries, file page indices, and pre-calculated hotspots.

## Guardrail Constraints
- **Safety Alert Invariant:** You MUST alert the user explicitly before adding code to a file flagged as highly brittle or designated as a high-risk hotspot.
- **Verification Rule:** Trust scoped context results, but physically verify that cited paths still exist on the local file system before editing them.

## Execution Steps

When investigating existing Python functionality or assessing change risks, run the Repowise tools sequentially based on your investigative intent:

### 1. Repository Scopes & High-Level Architecture
Before diving into code blocks, establish the high-level boundaries of the module or repository layer:
- Run: `get_overview()` to inspect package trees, boundaries, and macro file distributions.

### 2. Behavior Location & Semantic Search
Locate specific code strings, definitions, or architectural concepts across the repository:
- Run: `get_answer()` or `search_codebase()`

### 3. Context & Structural Cleanliness Isolation
Extract exact, bounded code blocks and symbol trees while ensuring you are not adding code to abandoned or orphaned logic branches:
- Run: `get_context()` and `get_symbol()` to isolate active implementation code.
- Run: `get_dead_code()` to verify that the functions, classes, or files you are touching are actively used and have not been abandoned.

### 4. Structural Risk Assessment
Check the target destination for maintenance hazards and unexpected system coupling to ensure safe modification:
- Run: `get_health` to evaluate target-file biomarkers.
- Run: `get_risk()` to isolate hotspots, hidden structural coupling, and change blast radius.

### 5. Intent & Architecture Verification
Verify the historical rationale or architectural choice behind the file layout before deviating from established repo patterns:
- Run: `get_why()`

## Examples

### Example 1: High-Level Module Distribution & Layout
**User:** "Give me an overview of how the runtime package is structured."
**Agent Response:** *"I am using the repowise-queries skill to map the package trees and layout distribution of the runtime components."*
```python
get_overview()
```

### Example 2: Semantic Behavior Search & Answer Synthesizing
**User:** "Find where we manage trace spans or log propagation."
**Agent Response:** *"I am using the repowise-queries skill to locate trace logs, check for semantic answers, and find related source modules."*
```python
get_answer(query="trace spans or log propagation")
search_codebase(query="trace spans or log propagation")
```

### Example 3: Context and Source Isolation
**User:** "Show me the context and methods inside the WorkflowControlManager class."
**Agent Response:** *"I am using the repowise-queries skill to pull bounded context and structural targets specifically for WorkflowControlManager."*
```python
get_context(targets=["WorkflowControlManager"])
```

### Example 4: Risk and Blast Radius Assessment
**User:** "Let's check the stability and hotspots of the main database persistence layer before writing our migration plan."
**Agent Response:** *"I am using the repowise-queries skill to evaluate code health signals, maintenance hazards, and architectural blast radius for the persistence module."*
```python
get_health(targets=["core/storage/persistence/"])
get_risk(targets=["core/storage/persistence/"])
```

### Example 5: Sweeping for Orphaned Logic Branches
**User:** "Are there any unused methods or dead code blocks inside the telemetry engine?"
**Agent Response:** *"I am using the repowise-queries skill to check for dead or unreachable code blocks within the telemetry paths."*
```python
get_dead_code(targets=["core/telemetry/"])
```
