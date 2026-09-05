# Durable Persistence (Entity ID: durable-persistence)

**Boundary Rationale:** This boundary owns the durable transactional storage capability needed to preserve direct business truth, immutable history, current-state access, concurrency protection, and recovery. It is distinct because database products and physical schemas are adapter choices, while persistence guarantees are inward-owned architectural requirements.
(source: owner-approved entity boundary determination)

### Strict Invariants

* Material business facts are persisted directly under their owning semantics; workflow, job, report, model, or generic runtime event history is not the business source of truth. (source: docs/current/platform-architecture-0.2.0.md; docs/adr/0002-platform-persist-direct-business-truth-with-immutable-history.md)
* Persistence contracts express atomicity, durability, uniqueness, idempotency, historical preservation, concurrency, and reconstruction requirements without exposing PostgreSQL, ORM sessions, SQL expressions, or other adapter-native types. (source: docs/current/platform-architecture-0.2.0.md; docs/adr/0003-platform-insulate-infrastructure-behind-inward-owned-capability-ports.md)
* PostgreSQL is the initial/reference 0.2.0 persistence adapter, not the architectural identity of persistence. (source: docs/current/platform-architecture-0.2.0.md; docs/adr/0003-platform-insulate-infrastructure-behind-inward-owned-capability-ports.md)
* Greenfield Polaris uses a fresh persistence and migration lineage; current migrations must not target legacy schema objects because they already exist. (source: docs/current/platform-architecture-0.2.0.md)
