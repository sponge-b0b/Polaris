# Interfaces & Presentation (Entity ID: interfaces-presentation)

**Boundary Rationale:** This boundary owns human and machine presentation/transport surfaces that adapt requests into shared application commands and queries and render shared decision truth back to users or external consumers. It is distinct because no surface may create an alternate report-, protocol-, or transport-specific business model.
(source: owner-approved entity boundary determination)

### Strict Invariants

* All presentation surfaces call the same application command/query boundary and therefore share the same canonical business truth. (source: docs/current/platform-architecture-0.2.0.md)
* Interfaces must not bypass the application boundary to write business persistence directly. (source: docs/current/platform-architecture-0.2.0.md; docs/adr/0001-platform-use-modular-monolith-with-ports-and-adapters.md)
* Reports, PDFs, email, messaging, MCP, CLI, HTTP, and similar surfaces are presentation/distribution adapters rather than canonical business models. (source: docs/current/platform-architecture-0.2.0.md)
* The first human-facing slice may be deliberately small, but it must not reconstruct or persist an independent report-specific Investment Decision representation. (source: docs/current/platform-architecture-0.2.0.md)
