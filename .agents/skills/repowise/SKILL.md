---
name: repowise
description: Locate repository behavior and assess status, health, hotspots, change risk, historical rationale, or dead-code candidates with Repowise. Do not use for exact static dependency tracing, implicit runtime dispatch, or broad cross-document exploration.
---

# Repowise Queries Skill

## Objective
Safely locate behavior, map source contexts, sweep for dead code, evaluate file brittleness, estimate change risk before modifying Python files when relevant, and recover historical rationale without reading heavy raw files into the active LLM context.

## Routing Boundary

Select Repowise when the material question is **where behavior lives** or concerns repository status, health, hotspots, change risk, historical rationale, or dead-code triage.

Use `$codebase-memory-mcp` for exact structural symbols, callers/callees, dependencies, code architecture, diff blast radius, or cross-service paths; `$codegraph` for implicit runtime dispatch; `$graphify` for broad corpus/community relationships; and `rg` or direct reads for literals and non-code authority.

## Context Inputs
- **Cached discovery map:** `.claude/CLAUDE.md` when present.
- Consult it only when its cached summaries, file-page indices, or hotspot metadata materially help choose or interpret the current query. Do not preload it merely because Repowise is being used.

## Guardrail Constraints
- **Safety Alert Invariant:** You MUST alert the user explicitly before adding code to a file flagged as highly brittle or designated as a high-risk hotspot.
- **Verification Rule:** Trust scoped context results, but physically verify that cited paths still exist on the local file system before editing them.

## Execution Steps

Choose only the Repowise operations that answer the current material question. The capabilities below are independent, not a mandatory sequence. Do not invoke one merely because another was used. Use any combination when distinct material questions require it, and broaden when the initial evidence is insufficient.

### 1. Repository Scope and Orientation
When repository/module boundaries are not already known and orientation is materially useful for locating behavior or scoping a risk inquiry:
- Run: `get_overview()` to inspect package trees, boundaries, and macro file distributions.

### 2. Behavior Location & Semantic Search
When the question is where behavior or repository responsibilities live:
- Run: `get_answer()` or `search_codebase()`.

### 3. Behavioral Context and Cleanliness Isolation
Within an already-selected Repowise inquiry, when bounded context around a behavior or risk target is needed:
- Run: `get_context()` or `get_symbol()` to isolate the relevant implementation context.
- Run: `get_dead_code()` only when whether the touched function, class, or file is abandoned/orphaned is materially relevant.

### 4. Structural Risk Assessment
When maintenance hazards, hotspot status, or change risk materially affect the planned change:
- Run: `get_health()` to evaluate target-file biomarkers.
- Run: `get_risk()` to isolate hotspots, hidden structural coupling, and change risk.

### 5. Historical-Rationale Verification
When historical rationale is materially needed to understand or challenge the current implementation choice:
- Run: `get_why()`.

## Examples

### Example 1: Repository Orientation for Behavior Location
**User:** "Orient me to the runtime areas before we locate its workflow-control behavior."
**Agent Response:** *"I am using the Repowise overview to bound the repository areas relevant to locating workflow-control behavior."*
```python
get_overview()
```

### Example 2: Semantic Behavior Search & Answer Synthesizing
**User:** "Find where we manage trace spans or log propagation."
**Agent Response:** *"I am using the repowise skill to locate where trace spans and log propagation are managed."*
```python
get_answer(query="trace spans or log propagation")
```

### Example 3: Located-Behavior Context
**User:** "After locating the workflow-control behavior, show me its bounded implementation context."
**Agent Response:** *"I am continuing the Repowise inquiry with bounded context for the located WorkflowControlManager behavior."*
```python
get_context(targets=["WorkflowControlManager"])
```

### Example 4: Change-Risk Assessment
**User:** "Let's check the stability and hotspots of the main database persistence layer before writing our migration plan."
**Agent Response:** *"I am using the repowise skill to evaluate code health signals, maintenance hazards, and change risk for the persistence module."*
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
