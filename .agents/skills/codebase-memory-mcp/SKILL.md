---
name: codebase-memory-mcp
description: Optimizes local code intelligence and discovery using a high-performance, Tree-sitter-backed structural knowledge graph instead of expensive token-heavy file searches. Use for understanding code architecture, tracing function call chains, finding cross-file dependencies, analyzing git diff blast radiuses, running complex graph queries, or discovering specific functions, classes, or routes within the repository without scanning full files.
---

# Codebase Knowledge Graph (codebase-memory-mcp)

This project uses codebase-memory-mcp to maintain a knowledge graph of the codebase.
ALWAYS prefer MCP graph tools over grep/glob/file-search for code discovery.

## Priority Order
1. `search_graph` — find functions, classes, routes, variables by pattern
2. `trace_path` — trace who calls a function or what it calls
3. `get_code_snippet` — read specific function/class source code
4. `query_graph` — run Cypher queries for complex patterns
5. `get_architecture` — high-level project summary

- `detect_changes` — Map git diff to affected symbols + blast radius with risk classification.
- `get_graph_schema` — Node/edge counts, relationship patterns, property definitions per label.
- `search_code` — Grep-like text search within indexed project files.

## When to fall back to grep/glob
- Searching for string literals, error messages, config values
- Searching non-code files (Dockerfiles, shell scripts, configs)
- When MCP tools return insufficient results

## Examples
- Find a handler: `search_graph(name_pattern=".*OrderHandler.*")`
- Who calls it: `trace_path(function_name="OrderHandler", direction="inbound")`
- Read source: `get_code_snippet(qualified_name="pkg/orders.OrderHandler")`
