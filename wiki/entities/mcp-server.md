# MCP Server (Entity ID: mcp-server)

**Boundary Rationale:** MCP deserves promotion because it is a distinct external transport for LLM hosts with read-only/tool-catalog constraints and delegation rules into workflow/RAG services.
(source: owner-approved entity promotion)

### Strict Invariants

* The MCP request path is strict request model, FastMCP handler, Dishka request scope, canonical application service or `WorkflowFacade`, and strict response, because MCP is a transport adapter rather than an authority boundary. (source: docs/current/mcp-server-transport-boundary.md)
* MCP handlers must not directly query or import internal Postgres, Qdrant, Neo4j, provider, RAG, or runtime internals; missing behavior must be implemented in the canonical service first, because transport-specific shortcuts create alternate APIs. (source: docs/current/mcp-server-transport-boundary.md)
* MCP governance and release capabilities must delegate through the request scope and must not create local approval queues, caches, tables, gates, direct repository writers, audit stores, or RAG approval stacks, because approval state belongs to governance services. (source: docs/current/mcp-server-transport-boundary.md)
* The MCP approval-state surface is read-only and delegates to `AutomatedDecisionAuditService` through a request scope; MCP may list canonical review state but cannot approve, deny, override, accept residual risk, mutate review state, or bypass review. (source: docs/current/mcp-server-transport-boundary.md)

### Planned

* **Future MCP tool namespace for ingest, processing, rebuild, and reporting workflows** — proposed, not yet accepted. (source: docs/proposed/platform-future-architecture.md)
