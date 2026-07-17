# ADR-004: PostgreSQL Is the Platform System of Record

## Status

Accepted

## Context

The platform persists workflow history, completed runs, market and portfolio facts, signals, recommendations, reports, telemetry, backtests, lineage, and curated RAG records. Treating caches, local files, vector stores, or graph projections as authoritative would create inconsistent recovery, replay, retention, and audit behavior.

## Decision

PostgreSQL is the canonical system of record for durable platform state. SQLAlchemy models and Alembic migrations define the relational schema. Application persistence services coordinate use cases; typed repositories own persistence contracts; PostgreSQL repository implementations perform database access.

Qdrant and Neo4j are rebuildable projections of curated PostgreSQL records. Local files are presentation artifacts or explicitly bounded exports, not an alternate authoritative database. Important canonical data receives a first-class typed field and schema migration rather than being stored only in generic metadata.

## Rationale

A single relational authority provides transactional integrity, migration governance, deterministic rebuilds, retention enforcement, auditability, and recovery. Projection stores can be recreated without loss of canonical records.

## Consequences

- Schema changes require Alembic migrations and metadata-divergence tests.
- Persistence access follows application service to repository boundaries.
- Projection rebuilds never delete canonical PostgreSQL records.
- Generic metadata is reserved for non-canonical extension data, not planned core fields.

## Affected Modules

- `core/database/postgres.py`
- `core/database/models/`
- `core/storage/persistence/`
- `application/persistence/`
- `migrations/`
