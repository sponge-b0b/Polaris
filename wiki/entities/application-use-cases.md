# Application Use Cases (Entity ID: application-use-cases)

**Boundary Rationale:** This boundary owns commands, queries, cross-entity use-case coordination, application transaction semantics, idempotency, continuity arbitration, concurrency protection, and inward-owned capability ports. It is distinct because interfaces and infrastructure must reach business truth through one application boundary rather than establishing alternate write paths.
(source: owner-approved entity boundary determination)

### Strict Invariants

* Application commands may establish durable business facts; queries assemble current or historical views without becoming authoritative business writers. (source: docs/current/platform-architecture-0.2.0.md)
* Application use cases own business transaction boundaries, expected-version checks, idempotency, and atomic registration of required durable follow-up where the originating use case requires it. (source: docs/current/platform-architecture-0.2.0.md)
* Long-running model or external calls must not hold durable-store transactions open; state and governing preconditions are re-checked before committing resulting judgments. (source: docs/current/platform-architecture-0.2.0.md)
* Application contracts depend inward on domain semantics and must not import concrete infrastructure or interface implementations. (source: docs/current/platform-architecture-0.2.0.md; docs/adr/0001-platform-use-modular-monolith-with-ports-and-adapters.md)

### Planned

* **R2 Investment Decision application contract** — coordinate initiation, Scope establishment/revision, Decisions-side Deferral/resolution consequences, work withdrawal/resumption, External Resolution, unsupported-Need retraction, renewal, Supersession, lifecycle correction, and current/historical queries through one technology-neutral application boundary. (source: docs/proposed/application-use-cases-investment-decision-lifecycle.md)
* **Continuity arbitration beyond idempotency** — before a distinct new Decision commits, revalidate the bounded unresolved-candidate basis used for same/new continuity; different operation IDs cannot silently create duplicate Decision identity when continuity overlaps, and ambiguity fails closed. (source: docs/proposed/application-use-cases-investment-decision-lifecycle.md)
* **Cross-owner human-judgment seams** — Deferral and substantive resolution require trusted Governance-owned Human Investment Decision/resolution bases; R2 may test the Decisions-side consequences with fixtures but must not fabricate authority facts. (source: docs/proposed/application-use-cases-investment-decision-lifecycle.md; docs/proposed/platform-domain-interaction-map.md)
* **Dual temporal query semantics** — distinguish `as_known_at` from effective-at-under-a-knowledge-cutoff, with explicit non-destructive lifecycle correction when late facts change supported effective interpretation. (source: docs/proposed/application-use-cases-investment-decision-lifecycle.md)
* **Decision relationship coordination** — application use cases establish renewal/Supersession edges and later contextual bindings; the Decision aggregate does not discover graph neighbors. Future `PRIOR_DECISION_CONTEXT` is created only after attributable material use and preserves the target Decision historical knowledge boundary actually used. (source: docs/proposed/investment-decisions-decision-relationship-model.md)
