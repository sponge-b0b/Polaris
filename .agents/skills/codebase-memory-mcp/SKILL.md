---
name: codebase-memory-mcp
description: Default exact structural-code discovery for symbols, callers/callees, dependencies, code architecture, diff blast radius, complex graph queries, and cross-service paths. Do not use for repository health/history, implicit runtime dispatch, broad cross-document exploration, or literal and non-code searches.
---

# Codebase Knowledge Graph (codebase-memory-mcp)

This project uses codebase-memory-mcp to maintain a knowledge graph of the codebase.

## Routing Boundary

Select this skill by default when the material question requires exact structural evidence from code: symbol discovery, static callers/callees, cross-file dependencies, code architecture, change impact, or cross-service paths. Once selected, prefer its MCP graph tools over broad grep/glob/file scanning.

Use `$repowise` for behavioral location, repository health, risk, history, or dead-code triage; `$codegraph` for implicit runtime dispatch; `$graphify` for broad corpus/community exploration; and `rg` or direct reads for literals, configuration, Markdown/policy, or graph coverage gaps.

## Priority Order
1. `search_graph` — find functions, classes, routes, variables by pattern
2. `trace_path` — trace who calls a function or what it calls
3. `get_code_snippet` — read specific function/class source code
4. `query_graph` — run Cypher queries for complex patterns
5. `get_architecture` — high-level project summary

- `detect_changes` — Map git diff to affected symbols + blast radius with risk classification.
- `get_graph_schema` — Node/edge counts, relationship patterns, property definitions per label.
- `search_code` — Grep-like text search within indexed project files.
- `manage_adr` — CRUD for Architecture Decision Records.

## When to fall back to grep/glob
- Searching for string literals, error messages, config values
- Searching non-code files (Dockerfiles, shell scripts, configs)
- When MCP tools return insufficient results

## Examples
- Find a handler: `search_graph(name_pattern=".*OrderHandler.*")`
- Who calls it: `trace_path(function_name="OrderHandler", direction="inbound")`
- Read source: `get_code_snippet(qualified_name="pkg/orders.OrderHandler")`
