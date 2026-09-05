# Application Use Cases (Entity ID: application-use-cases)

**Boundary Rationale:** This boundary owns commands, queries, use-case coordination, application transaction semantics, idempotency, concurrency protection, and inward-owned capability ports. It is distinct because interfaces and infrastructure must reach business truth through one application boundary rather than establishing alternate write paths.
(source: owner-approved entity boundary determination)

### Strict Invariants

* Application commands may establish durable business facts; queries assemble current or historical views without becoming authoritative business writers. (source: docs/current/platform-architecture-0.2.0.md)
* Application use cases own business transaction boundaries, expected-version checks, idempotency, and atomic registration of required durable follow-up where the originating use case requires it. (source: docs/current/platform-architecture-0.2.0.md)
* Long-running model or external calls must not hold durable-store transactions open; state and governing preconditions are re-checked before committing resulting judgments. (source: docs/current/platform-architecture-0.2.0.md)
* Application contracts depend inward on domain semantics and must not import concrete infrastructure or interface implementations. (source: docs/current/platform-architecture-0.2.0.md; docs/adr/0001-platform-use-modular-monolith-with-ports-and-adapters.md)

### Planned

* **R2 Investment Decision application contract** — define explicit lifecycle commands and Decision Memory queries with operation-scoped idempotency, expected-version concurrency protection, semantic transaction boundaries, and an internal substantive-resolution seam that can later coordinate with Governance without fabricating Governance-owned authority facts. (source: docs/proposed/application-use-cases-investment-decision-lifecycle.md)
