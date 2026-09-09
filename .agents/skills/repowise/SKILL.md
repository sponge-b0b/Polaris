---
name: repowise
description: Queries local repository code, structural overviews, dead-code references, file risk markers, and historical rationale via Repowise tools when those questions are materially useful.
---

# Repowise Queries Skill

## Objective
Safely locate behavior, map source contexts, sweep for dead code, evaluate file brittleness, estimate change blast radiuses before modifying Python files when relevant, and answer structural questions about the project codebase without reading heavy raw files into the active LLM context.

## Context Inputs
- **Cached discovery map:** `.claude/CLAUDE.md` when present.
- Consult it only when its cached summaries, file-page indices, or hotspot metadata materially help choose or interpret the current query. Do not preload it merely because Repowise is being used.

## Guardrail Constraints
- **Safety Alert Invariant:** You MUST alert the user explicitly before adding code to a file flagged as highly brittle or designated as a high-risk hotspot.
- **Verification Rule:** Trust scoped context results, but physically verify that cited paths still exist on the local file system before editing them.

## Execution Steps

Choose only the Repowise operations that answer the current material question. The capabilities below are independent, not a mandatory sequence. Do not invoke one merely because another was used. Use any combination when distinct material questions require it, and broaden when the initial evidence is insufficient.

### 1. Repository Scopes & High-Level Architecture
When repository/module boundaries are not already known and high-level orientation is materially useful:
- Run: `get_overview()` to inspect package trees, boundaries, and macro file distributions.

### 2. Behavior Location & Semantic Search
When the question is where behavior, definitions, or architectural concepts live:
- Run: `get_answer()` or `search_codebase()`.

### 3. Context & Structural Cleanliness Isolation
When exact bounded code or symbol structure is needed:
- Run: `get_context()` or `get_symbol()` to isolate active implementation code.
- Run: `get_dead_code()` only when whether the touched function, class, or file is abandoned/orphaned is materially relevant.

### 4. Structural Risk Assessment
When maintenance hazards, hotspot status, or blast radius materially affect the planned change:
- Run: `get_health()` to evaluate target-file biomarkers.
- Run: `get_risk()` to isolate hotspots, hidden structural coupling, and change blast radius.

### 5. Intent & Architecture Verification
When historical rationale is materially needed to understand or challenge the current implementation choice:
- Run: `get_why()`.

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
