---
name: repowise-queries
description: Queries local repository code, structural overviews, dead code references, and file risk markers via Repowise tools. Use before editing python files or when exploring existing codebase implementations.
---

# Repowise Queries Skill

## Objective
Safely locate behavior, map source contexts, sweep for dead code, evaluate file brittleness, and estimate change blast radiuses before modifying any Python files.

## Guardrail Constraints
- **Safety Alert Invariant:** You MUST alert the user explicitly before adding code to a file flagged as highly brittle or designated as a high-risk hotspot.
- **Verification Rule:** Trust scoped context results, but physically verify that cited paths still exist on the local file system before editing them.

## Execution Steps

When investigating existing Python functionality or assessing change risks, run the Repowise tools sequentially based on your investigative intent:

### 1. Repository Scopes & High-Level Architecture
Before diving into code blocks, establish the high-level boundaries of the module or repository layer:
- Run: `get_overview` to inspect package trees, boundaries, and macro file distributions.

### 2. Behavior Location & Semantic Search
Locate specific code strings, definitions, or architectural concepts across the repository:
- Run: `get_answer` or `search_codebase`

### 3. Context & Structural Cleanliness Isolation
Extract exact, bounded code blocks and symbol trees while ensuring you are not adding code to abandoned or orphaned logic branches:
- Run: `get_context` and `get_symbol` to isolate active implementation code.
- Run: `get_dead_code()` to verify that the functions, classes, or files you are touching are actively used and have not been abandoned.

### 4. Structural Risk Assessment
Check the target destination for maintenance hazards and unexpected system coupling to ensure safe modification:
- Run: `get_health` to evaluate target-file biomarkers.
- Run: `get_risk` to isolate hotspots, hidden structural coupling, and change blast radius.

### 5. Intent & Architecture Verification
Verify the historical rationale or architectural choice behind the file layout before deviating from established repo patterns:
- Run: `get_why`

## Examples

### Example 1: Large-Scale Exploration & Dead Code Audit
**User:** "Give me an overview of the RAG pipeline module and see if there is any code we can safely remove before adding the reranker."
**Agent Response:** *"I am running the repowise-queries skill via get_overview and get_dead_code() to map out the RAG package boundaries and isolate orphan blocks before writing our implementation plan."*
