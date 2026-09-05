# Application Use Cases (Entity ID: application-use-cases)

**Boundary Rationale:** This boundary owns commands, queries, cross-entity use-case coordination, application transaction semantics, idempotency, continuity arbitration, concurrency protection, and inward-owned capability ports. It is distinct because interfaces and infrastructure must reach business truth through one application boundary rather than establishing alternate write paths.
(source: owner-approved entity boundary determination)

### Strict Invariants

* Application commands may establish durable business facts; queries assemble current or historical views without becoming authoritative business writers. (source: docs/current/platform-architecture-0.2.0.md)
* Application use cases own business transaction boundaries, expected-version checks, idempotency, and atomic registration of required durable follow-up where the originating use case requires it. (source: docs/current/platform-architecture-0.2.0.md)
* Long-running model or external calls must not hold durable-store transactions open; state and governing preconditions are re-checked before committing resulting judgments. (source: docs/current/platform-architecture-0.2.0.md)
* Application contracts depend inward on domain semantics and must not import concrete infrastructure or interface implementations. (source: docs/current/platform-architecture-0.2.0.md; docs/adr/0001-platform-use-modular-monolith-with-ports-and-adapters.md)

### Planned

* **R2 Investment Decision application contract** — coordinate initiation, partial/complete Scope refinement, Decisions-side human-Deferral and substantive-resolution consequences, work withdrawal/resumption, Decision Need External Resolution/retraction, renewal, Supersession, lifecycle correction, and Decision Memory queries through technology-neutral application contracts. (source: docs/proposed/application-use-cases-investment-decision-lifecycle.md)
* **Continuity arbitration beyond idempotency** — initial R2 may inspect all unresolved non-superseded Decisions rather than inventing a semantic matching heuristic; before a distinct new Decision commits, the candidate universe is revalidated atomically so different operation IDs cannot silently create duplicate Decision identity. (source: docs/proposed/application-use-cases-investment-decision-lifecycle.md)
* **Cross-owner human-judgment seams** — Deferral and substantive resolution require trusted Governance-owned Human Investment Decision/resolution bases; R2 exercises only the Decisions-side consequences with deterministic trusted fixtures and does not fabricate authority facts. (source: docs/proposed/application-use-cases-investment-decision-lifecycle.md; docs/proposed/platform-domain-interaction-map.md)
* **Independent Need/judgment/work semantics** — External Resolution changes Decision Need status rather than creating substantive judgment; unsupported-Need retraction may occur after other historical acts and uses explicit lifecycle correction where an earlier Decisions-side interpretation becomes unsupported. (source: docs/proposed/application-use-cases-investment-decision-lifecycle.md)
* **Dual temporal query semantics** — distinguish `as_known_at` from effective-at-under-a-knowledge-cutoff, with append-only correction preserving the originally recorded history. (source: docs/proposed/application-use-cases-investment-decision-lifecycle.md)
* **Decision relationship coordination** — application establishes renewal/Supersession edges and later contextual bindings; the Decision aggregate does not discover graph neighbors. Future `PRIOR_DECISION_CONTEXT` is created only after attributable material use and preserves the target Decision historical state actually used. (source: docs/proposed/investment-decisions-decision-relationship-model.md)
