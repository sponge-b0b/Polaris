# Intelligence & Decision Support (Entity ID: intelligence-decision-support)

**Boundary Rationale:** This boundary owns analytical reasoning over portfolio, risk, market, strategy, and recommendation outputs. It is architectural because it coordinates domain evidence, deterministic and LLM-assisted analysis, and decision-support semantics across workflows and services.
(source: owner-approved entity boundary determination)

### Strict Invariants

* Intelligence components consume typed domain evidence and produce typed outputs rather than redefining domain, persistence, or authority semantics, because decision support depends on shared contracts across the platform. (source: docs/adr/0006-domain-contracts-data-semantics-typed-internal-contracts.md)
* Analytical evidence, aggregate risk, and market context are upstream inputs to strategy synthesis and governance rather than downstream execution-risk authorities, because each decision-support stage has a distinct semantic role. (source: docs/adr/0007-strategy-synthesis-structured-hypotheses.md)
* Intelligence outputs that become durable facts must pass through owning application or persistence services, because analysis code must not create alternate systems of record. (source: docs/current/platform-architecture-ownership-ledger.md)

### Planned

* **Expanded intelligence-agent capabilities for analysis, explanation, monitoring, and portfolio decision support** — proposed, not yet accepted. (source: docs/proposed/platform-future-architecture.md)
