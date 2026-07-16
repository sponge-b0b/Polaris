---
name: architectural-investigation
description: Deeply audits the data lifecycle, schema paths, and component authorities before making state, persistence, or architectural changes. Use when planning system modifications or reviewing codebase dependencies.
---

# Architectural Investigation Skill

## Objective
Trace the complete data lifecycle across Polaris to ensure surgical implementation scope, preserve single-source-of-truth invariants, and prevent state duplication.

## Initial Context Gathering
Before mapping or investigating, you must read the current platform layouts:
1. Read `CONTEXT.md` for the current platform map and descriptive architectural status.
2. Read `.claude/CLAUDE.md` for the Repowise-generated system map.
3. **Verify:** Physically cross-reference these maps against the active source code and tests, as generated maps can lag behind the repository.

## Execution Steps

### 1. Data Lifecycle Tracing
Before changing any state, calculation result, schema, or persistence path, explicitly trace the data flow through this pipeline:
```text
producer
→ client/provider
→ application service
→ intelligence or workflow node
→ RuntimeNodeOutput and RuntimeContext
→ PostgreSQL
→ curated record or projection
→ consumer
```

### 2. Guardrail Verification Checks
Ensure your plan or modification complies with these strict architectural rules:
- **Authority:** Identify exactly one authoritative model, owner, and canonical writer for every durable business concept.
- **Classification:** Distinguish cleanly between runtime evidence, canonical domain records, projections, telemetry, and presentation output.
- **Conflict Handling:** STOP immediately if two separate components claim to be the source of truth for the same data.
- **Redundancy Audit:** Evaluate if any existing responsibilities are obsolete or superseded by the new capabilities.
- **Analytical Services Boundary:** Analytical services must return typed results. They are strictly prohibited from persisting workflow-derived results unless database persistence is the explicit use case.

### 3. Post-Change Verification
After major changes are applied, run an audit to check for:
- Duplicate data writers.
- Hidden or unlogged side effects.
- Metadata-only pseudo-fields trying to bypass schema rules.
- Obsolete file paths or competing state models.
- *Note:* Do not infer architectural correctness from imports, passing tests, or high code-health scores alone.

## Examples

### Example 1: Triggering a Data Path Audit
**User:** "We need to change how the workflow node saves execution logs."
**Agent Response:** *"I am using the architectural-investigation skill to trace the state pipeline from the RuntimeNodeOutput down to PostgreSQL before writing the plan."*
