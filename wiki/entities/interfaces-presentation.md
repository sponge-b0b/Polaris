# Interfaces & Presentation (Entity ID: interfaces-presentation)

**Boundary Rationale:** This boundary owns human and machine presentation/transport surfaces that adapt requests into shared application commands and queries and render shared decision truth back to users or external consumers. It is distinct because no surface may create an alternate report-, protocol-, or transport-specific business model.
(source: owner-approved entity boundary determination)

### Strict Invariants

* The first complete R3 human surface is a deliberately small interactive CLI that remains a thin adapter over shared application commands/queries and canonical decision truth; CLI transport/presentation identity never becomes business identity. (source: docs/adr/0009-governance-authority-expose-r3-human-decision-through-thin-cli.md)
* All presentation surfaces call the same application command/query boundary and therefore share the same canonical business truth. (source: docs/current/platform-architecture-0.2.0.md)
* Interfaces must not bypass the application boundary to write business persistence directly. (source: docs/current/platform-architecture-0.2.0.md; docs/adr/0001-platform-use-modular-monolith-with-ports-and-adapters.md)
* Reports, PDFs, email, messaging, MCP, CLI, HTTP, and similar surfaces are presentation/distribution adapters rather than canonical business models. (source: docs/current/platform-architecture-0.2.0.md)
* The first human-facing slice may be deliberately small, but it must not reconstruct or persist an independent report-specific Investment Decision representation. (source: docs/current/platform-architecture-0.2.0.md)


### Planned

* **R3 interactive human decision CLI** — accepted, implementation pending. The CLI will present concise-first Decision Context with inspectable Evidence, challenge, uncertainty, Portfolio/Risk consequence, Recommendation/withholding, and history, and will record Human Investment Decision only through the shared application boundary. (source: docs/adr/0009-governance-authority-expose-r3-human-decision-through-thin-cli.md)
