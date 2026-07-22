---
name: codegraph
description: Traces implicit function paths, event loops, framework decorators, and decoupled execution targets via CodeGraph tools. Use for tracing Python-specific routing (FastAPI/Django decorators), event emitters (emit/on loops), callback handlers, or abstract dispatch before tracing raw files manually.
---

# CodeGraph Analysis Skill

## Objective
Expose the dynamic edge-synthesizer engine to trace implicit Python execution flows, runtime framework routing configurations, asynchronous event loops, and string-keyed callbacks that static AST tools or raw grep queries miss.

## Context Inputs
- **Authoritative Edge Registry:** `.codegraph/` (Driven by a native, always-on SQLite backend).
- **Live File Watcher:** The underlying MCP background daemon runs an active background filesystem watcher. It automatically captures file saves and incrementally syncs the graph under a second—manual index rebuilds are completely unnecessary.

## Guardrail Constraints
- **Edge Resolution Invariant:** Only trust edges that resolve completely from end to end. 
- **Blind-Spot Rule:** If a trace yields a partial or broken path matching an interface boundary, log it explicitly as a "CodeGraph blind spot." Stop digging through files along that specific trajectory to avoid generating unnecessary file-read overhead.
- **Staleness Detection (Debounce Window):** If you make a rapid succession of edits, CodeGraph might display a minor staleness banner (⚠️) for a few milliseconds while the quiet window processes. If you see this banner, read the modified target file directly instead of over-relying on the graph query.

## Execution Steps

When investigating runtime call paths, decoupled handlers, or asynchronous routing flows, run the CodeGraph tools based on your investigative intent:

### 1. Verification of System Pathing & Readiness
Before initializing dynamic code exploration, verify that the local repository background daemon is healthy and connected:
- Run: `codegraph status` to validate the state of the active tracking databases.

### 2. High-Efficiency Single-Pass Single Symbol Exploration
Gather callers, callees, structural dependencies, and impact radii for a specific function name, class, or decorator target in one command without manual sweeps:
- Run: `codegraph_explore(query="<symbol_name>")` via the native MCP tool connector.

## Examples

### Example 1: Checking Local Index Health & Registration State
**User:** "Is CodeGraph running properly on our project?"
**Agent Response:** *"I am using the codegraph skill to check the tracking health and validation metadata of our dynamic edge registry."*
```bash
codegraph status
```

### Example 2: Tracing Framework Decorators & Route Mapping
**User:** "Find what triggers or handles requests directed at the portfolio update endpoint."
**Agent Response:** *"I am using the codegraph skill to resolve the runtime routing decorators and map out the relevant execution paths."*
```python
codegraph_explore(query="/portfolio/update")
```

### Example 3: Locating Async Event Loops & String-Keyed Emitters
**User:** "Trace how the portfolio_liquidated event is dispatched to downstream handlers."
**Agent Response:** *"I am using the codegraph skill to isolate string-keyed event emitters and track the call paths across decoupled async loops."*
```python
codegraph_explore(query="portfolio_liquidated")
```
