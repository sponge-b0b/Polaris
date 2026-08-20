# Persistence & Curated Records (Entity ID: persistence-curated-records)

**Boundary Rationale:** This is the durable system-of-record boundary: PostgreSQL schema, repositories, curated records, completed-run archives, persistence lineage, and projection queue semantics. It is meaningful because authority, durability, and rebuildability rules live here.
(source: owner-approved entity boundary determination)

### Strict Invariants

* PostgreSQL is the canonical durable system of record for platform state, completed-run archives, curated records, RAG document/chunk metadata, evaluation records, and governance audit records, because durable authority must live in one queryable store. (source: docs/adr/0004-persistence-curated-records-postgresql-system-of-record.md)
* SQLAlchemy models, Alembic migrations, typed repositories, and application persistence services own persistence contracts, because storage semantics must be explicit and migratable. (source: docs/adr/0004-persistence-curated-records-postgresql-system-of-record.md)
* Qdrant and Neo4j are rebuildable retrieval projections from PostgreSQL and not canonical stores, because derived indexes may be deleted or rebuilt without losing product authority. (source: docs/current/persistence-curated-records-postgresql-persistence.md)
* Important canonical data requires a first-class typed field and schema migration rather than living only in generic metadata or JSON, because hidden fields cannot safely support querying, governance, or projection rebuilds. (source: docs/adr/0004-persistence-curated-records-postgresql-system-of-record.md)
* Completed-run archives, curated domain records, RAG records, and observability records are distinct storage classes, because replay evidence, product facts, retrieval projections, and diagnostics have different authority. (source: docs/current/platform-architecture-ownership-ledger.md)
* One Polaris deployment is one organizational trust/data boundary, so persistence schemas, repository APIs, keys, uniqueness rules, and cache/projection identities must not acquire speculative tenant or organization dimensions; principal ownership is represented only for resource types whose semantics require it through an explicit canonical principal reference. (source: docs/adr/0022-single-tenant-resource-ownership-attribution-semantics.md)

### Planned

* **Additional persistence infrastructure such as object storage, cache policy, and operational data-store expansion** — proposed, not yet accepted. (source: docs/proposed/platform-future-architecture.md)
