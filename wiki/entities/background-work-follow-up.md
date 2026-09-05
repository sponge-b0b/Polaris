# Background Work & Durable Follow-Up (Entity ID: background-work-follow-up)

**Boundary Rationale:** This boundary owns technical scheduling/worker execution and the durable follow-up capability required when committed business changes must reliably trigger later work. It is distinct because background execution identity and delivery mechanics must never become Investment Decision identity or business truth.
(source: owner-approved entity boundary determination)

### Strict Invariants

* Scheduled and asynchronous workers invoke the same application use cases as interactive interfaces; technical work identity does not become business identity. (source: docs/current/platform-architecture-0.2.0.md)
* When a committed business change requires guaranteed later work, the follow-up obligation must be durably registered so it cannot be silently lost between business commit and dispatch. (source: docs/current/platform-architecture-0.2.0.md)
* Outbox, queue, broker, event bus, CDC relay, or another delivery mechanism is valid only if it satisfies inward-owned durability, atomicity, recovery, failure-visibility, and idempotent-effect guarantees. (source: docs/current/platform-architecture-0.2.0.md; docs/adr/0003-platform-insulate-infrastructure-behind-inward-owned-capability-ports.md)
* A universal event bus or replay stream must not become the organizing product spine or business source of truth. (source: docs/current/platform-architecture-0.2.0.md; docs/adr/0002-platform-persist-direct-business-truth-with-immutable-history.md)
