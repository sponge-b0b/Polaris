# Durable Persistence (Entity ID: durable-persistence)

**Boundary Rationale:** This boundary owns the durable transactional storage capability needed to preserve direct business truth, immutable history, current-state access, concurrency/continuity protection, temporal correction, and recovery. It is distinct because database products and physical schemas are adapter choices, while persistence guarantees are inward-owned architectural requirements.
(source: owner-approved entity boundary determination)

### Strict Invariants

* Material business facts are persisted directly under their owning semantics; workflow, job, report, model, or generic runtime event history is not the business source of truth. (source: docs/current/platform-architecture-0.2.0.md; docs/adr/0002-platform-persist-direct-business-truth-with-immutable-history.md)
* Persistence contracts express atomicity, durability, uniqueness, idempotency, historical preservation, concurrency, and reconstruction requirements without exposing PostgreSQL, ORM sessions, SQL expressions, or other adapter-native types. (source: docs/current/platform-architecture-0.2.0.md; docs/adr/0003-platform-insulate-infrastructure-behind-inward-owned-capability-ports.md)
* PostgreSQL is the initial/reference 0.2.0 persistence adapter, not the architectural identity of persistence. (source: docs/current/platform-architecture-0.2.0.md; docs/adr/0003-platform-insulate-infrastructure-behind-inward-owned-capability-ports.md)
* Greenfield Polaris uses a fresh persistence and migration lineage; current migrations must not target legacy schema objects because they already exist. (source: docs/current/platform-architecture-0.2.0.md)

### Planned

* **R2 Investment Decision persistence design** — use a narrow Decisions command store plus Decision Memory reader rather than a generic repository/UoW framework; atomically preserve current projection, immutable lifecycle facts/corrections, command receipts, and relationship facts while retaining effective and recorded time. (source: docs/proposed/durable-persistence-investment-decision-history.md)
* **Continuity-safe initiation** — persistence must provide technology-neutral atomic revalidation of the bounded unresolved-candidate basis so two different operation IDs cannot silently commit duplicate Decision identities when they race over the same continuity space. (source: docs/proposed/durable-persistence-investment-decision-history.md)
* **Many-to-many Decision relationships** — R2 persists renewal/Supersession in an explicit many-to-many-capable representation; Supersession is not a replacement lifecycle state and no one-to-one uniqueness constraint is allowed by design. Later `PRIOR_DECISION_CONTEXT` can add target knowledge cutoffs without redefining the inward contract or requiring a graph database. (source: docs/proposed/durable-persistence-investment-decision-history.md; docs/proposed/investment-decisions-decision-relationship-model.md)
* **Dual temporal reconstruction and correction** — append-only lifecycle/relationship corrections preserve the original recorded history while current supported effective history may change; `as_known_at` and effective-at-under-knowledge-cutoff are distinct query semantics. (source: docs/proposed/durable-persistence-investment-decision-history.md)
* **Actor/provenance storage separation** — persistence must not collapse Actor Attribution, trigger/source provenance, and technical request/model/work provenance into one generic origin field. (source: docs/proposed/durable-persistence-investment-decision-history.md)
