# Platform Persistence Plan V3 — Pre-RAG Completion

## Summary

Persistence V3 completes the PostgreSQL system-of-record foundation after V2. V2 establishes typed persistence tables, repositories, serializers, and application persistence services for the major business domains. V3 finishes the pre-RAG persistence layer by adding production readiness around data quality, lineage traversal, read/query services, lifecycle management, audit trails, operational hardening, and RAG eligibility.

No full RAG ingestion, embedding workers, vector-store writes, or graph-store writes should be introduced in V3. V3’s end state is a reliable, queryable, audited PostgreSQL persistence platform from which RAG pipelines can later derive curated source documents.

Execution protocol:

- Implement one step at a time.
- Keep each step small enough for a focused 3–5 minute implementation pass where practical.
- After each step, update this file with `- [x]` and a short result.
- Run targeted validation for each step.
- Stop and prompt before beginning the next step.

## V3 Objectives

Complete pre-RAG persistence readiness for:

- canonical lineage traversal
- persistence read/query services
- historical search and filtering
- data quality validation
- deduplication and idempotency
- audit/event trails for persisted business records
- retention/export hooks
- report/recommendation/customer-facing history readiness
- RAG eligibility marking without embedding anything

PostgreSQL remains canonical.

```text
Providers / Runtime / Services / Agents
    -> Typed Application Objects
        -> PostgreSQL System-of-Record
            -> Query Services
            -> Audit / Attribution
            -> Reports / API / UI
            -> Curated RAG Eligibility
                -> Future RAG / Vector / Graph Projections
```

## Key Architecture Decisions

- V3 does not create vector embeddings.
- V3 does not write to Qdrant, Chroma, Neo4j, or any graph/vector store.
- V3 treats RAG as a downstream projection that reads only curated, eligible PostgreSQL records.
- PostgreSQL records must be queryable through typed read services, not ad hoc SQL from application code.
- Persistence repositories remain infrastructure concerns.
- Application persistence/query services coordinate use cases.
- Persisted records should preserve source lineage, timestamps, workflow context, and auditability.
- Data quality checks should fail safely and report typed validation errors.
- Raw runtime dumps, raw telemetry streams, and raw provider payloads must not become RAG sources.

## Implementation Steps

### Plan Setup

- [x] Step 1 — Create V3 plan file
  - Create `.agent/plans/plan_postgres_persistence_v3.md`.
  - Add this V3 plan as the initial content.
  - Add a `Step Results` section at the bottom.
  - Step 1 completed: created `.agent/plans/plan_postgres_persistence_v3.md` with the V3 pre-RAG persistence completion plan.

- [x] Step 2 — Review V2 completion boundary
  - Confirm V2 tables/contracts/services are complete or identify missing V2 dependencies.
  - Add a short dependency checklist to this file.
  - Do not implement V2 code in this step.
  - Step 2 completed: reviewed V2 completion state and current repository shape; V2 already provides typed domain persistence records, serializers, repositories, models, migrations, and application persistence services with read/list APIs across major domains, so V3 should not add duplicate domain query-service packages. The adjusted V3 plan below is the implementation source of truth.

#### V2 Dependency Checklist

- [x] Runtime, report, RAG source, lineage, agent signal, recommendation, portfolio, market, macro, news, sentiment, agent intelligence, attribution, workflow audit, report version/publication, and telemetry persistence foundations exist from V1/V2.
- [x] Application persistence services exist for recommendations, portfolio, market, macro, news, sentiment, agent intelligence, attribution, reports, telemetry, and workflow audit.
- [x] Existing services already expose domain read/list methods and should be hardened, not duplicated by parallel query services.
- [x] Raw workflow/telemetry records remain operational data and are excluded from canonical RAG source eligibility.
- [x] Current curated RAG builder can persist PostgreSQL RAG source records and queue embedding jobs; adjusted V3 should make embedding job creation opt-in before full RAG ingestion work.

### Shared Query and Read Layer

- [ ] Step 3 — Add shared persistence query contracts
  - Add typed query/filter objects for common fields:
    - workflow name
    - execution id
    - runtime id
    - source type/source id
    - symbol
    - account id
    - timestamp range
    - limit/offset
  - Keep these contracts generic and reusable.

- [ ] Step 4 — Add shared pagination/sort models
  - Add typed pagination and sort contracts.
  - Support stable ordering by timestamp and created time.
  - Add tests for validation and defaults.

- [ ] Step 5 — Add shared query result envelopes
  - Add typed result envelopes for list/read operations.
  - Include records, total count when available, and query metadata.
  - Add unit tests.

### Lineage Traversal

- [ ] Step 6 — Add lineage traversal contracts
  - Add typed records for lineage graph queries:
    - source node
    - target node
    - relationship type
    - depth
  - Reuse V2 lineage links.

- [ ] Step 7 — Add lineage read repository
  - Add read methods for upstream/downstream lineage traversal.
  - Support report → recommendation → signal → workflow lookups.
  - Add tests with fake or SQL statement assertions.

- [ ] Step 8 — Add lineage application query service
  - Add service methods for tracing persisted records.
  - Return typed lineage paths.
  - Keep graph/vector systems out of scope.

### Domain Read Services

- [ ] Step 9 — Add recommendation query service
  - Add read/list methods for recommendations, rationales, outcomes, setups, and watchlist items.
  - Support filters by symbol, bias, confidence range, workflow lineage, and timestamp range.

- [ ] Step 10 — Add portfolio query service
  - Add read/list methods for portfolio state, positions, exposures, risks, and allocations.
  - Support account, symbol, timestamp range, and latest/current queries.

- [ ] Step 11 — Add market query service
  - Add read/list methods for OHLCV, indicators, technical snapshots, market context, and breadth snapshots.
  - Support symbol, source, timestamp range, and technical regime filters.

- [ ] Step 12 — Add macro query service
  - Add read/list methods for macro observations, regime snapshots, and calendar events.
  - Support indicator/event name, timestamp range, and regime filters.

- [ ] Step 13 — Add news query service
  - Add read/list methods for news articles and news analysis snapshots.
  - Support source, symbol, theme, published range, importance, sentiment, and dedupe keys.

- [ ] Step 14 — Add sentiment query service
  - Add read/list methods for sentiment snapshots and sentiment sources.
  - Support source, symbol/universe, timestamp range, and composite sentiment filters.

- [ ] Step 15 — Add intelligence query service
  - Add read/list methods for agent signals, reasoning, recommendations, and risk assessments.
  - Support agent name/type, symbol, confidence range, regime, and workflow lineage filters.

- [ ] Step 16 — Add attribution query service
  - Add read/list methods for attribution records, signal attribution, and recommendation attribution.
  - Support recommendation id, signal id, agent name, contribution type, and timestamp filters.

- [ ] Step 17 — Add report query service
  - Add read/list methods for reports, sections, artifacts, versions, and publications.
  - Support report type, title, status, generated range, publication target, and workflow lineage.

- [ ] Step 18 — Add telemetry query service
  - Add read/list methods for telemetry events, metrics, traces, workflow metrics, agent metrics, and provider metrics.
  - Support source, event type, correlation id, workflow lineage, and timestamp filters.
  - Mark telemetry as non-RAG-source data.

### Data Quality and Validation

- [ ] Step 19 — Add persistence validation contracts
  - Add typed validation issue/result models.
  - Include severity, record type, record id, field name, message, and remediation hint.

- [ ] Step 20 — Add lineage completeness checks
  - Validate that persisted business records include expected lineage where available.
  - Warn rather than fail for records legitimately created outside workflows.

- [ ] Step 21 — Add timestamp quality checks
  - Validate generated/published/observed timestamps.
  - Detect missing, future, or inconsistent timestamps where inappropriate.

- [ ] Step 22 — Add score range quality checks
  - Validate confidence, sentiment, risk, directional, attribution, and setup-quality score ranges.
  - Reuse platform score semantics.

- [ ] Step 23 — Add source/dedupe quality checks
  - Validate dedupe fields for news, market observations, macro observations, and external source records.
  - Add tests for duplicate-safe behavior.

- [ ] Step 24 — Add validation service
  - Add `application/persistence/validation`.
  - Coordinate validation checks across domain records.
  - Return typed validation results.

### Audit Trail

- [ ] Step 25 — Add persistence audit contracts
  - Add typed records for persistence audit events.
  - Include entity type, entity id, action, actor/system source, timestamp, and metadata.

- [ ] Step 26 — Add persistence audit model and migration
  - Add `persistence_audit_events`.
  - Index by entity type/id, action, timestamp, and workflow lineage.
  - Step 16 completed: added `PersistenceAuditEventModel` for the append-only `persistence_audit_events` table, imported it into `Base.metadata`, and added Alembic migration `20260530_0017_add_persistence_audit_events.py`. The table persists audit event ids, entity type/id, action, actor/system source fields, timestamp, workflow/runtime lineage, metadata JSONB, and row timestamps, with indexes for entity lookup, action/timestamp queries, and workflow/runtime lineage. Added model and migration tests and updated the Alembic foundation metadata test. Validation passed with focused audit database pytest, full core database pytest, ruff, scoped mypy, Alembic heads/history checks, metadata import check, and graphify update.

- [ ] Step 27 — Add audit repository/service
  - Add append-only audit persistence.
  - Add application service for writing audit events.
  - Add tests.

- [ ] Step 28 — Add audit hooks to application persistence services
  - Add audit event emission at service boundaries where safe.
  - Do not mutate runtime behavior.
  - Keep audit failures non-fatal by default.

### Idempotency and Deduplication Hardening

- [ ] Step 29 — Add idempotency key helper contracts
  - Add typed idempotency key helpers for domain records.
  - Prefer deterministic keys from source, timestamp, symbol, and lineage.

- [ ] Step 30 — Review recommendation idempotency
  - Ensure recommendation, setup, watchlist, rationale, and outcome writes are duplicate-safe.

- [ ] Step 31 — Review portfolio idempotency
  - Ensure latest tables upsert and historical/snapshot tables avoid accidental duplicate primary keys.

- [ ] Step 32 — Review market/macro idempotency
  - Ensure observation and snapshot writes are deterministic by source/symbol/timestamp where appropriate.

- [ ] Step 33 — Review news/sentiment idempotency
  - Ensure news article dedupe uses source plus URL or external id.
  - Ensure sentiment snapshots are deterministic by source/timestamp/context.

### RAG Eligibility Without Ingestion

- [ ] Step 34 — Add RAG eligibility contracts
  - Add typed eligibility result records.
  - Include source table, source id, source type, eligible flag, reason, quality score, and reviewed timestamp.

- [ ] Step 35 — Add RAG eligibility model and migration
  - Add `rag_source_eligibility`.
  - Link eligibility to canonical PostgreSQL source records.
  - Do not create embeddings.

- [ ] Step 36 — Add RAG eligibility repository/service
  - Add methods to mark, unmark, and list eligible source records.
  - Add tests.

- [ ] Step 37 — Add default eligibility rules
  - Eligible by default:
    - curated reports
    - agent signals/reasoning with meaningful text
    - recommendations with rationales
    - macro/technical/news/sentiment summaries
  - Ineligible by default:
    - raw runtime events
    - raw telemetry
    - raw provider payloads
    - operational error logs

- [ ] Step 38 — Extend curated RAG source builder to require eligibility
  - Add an optional eligibility gate before building RAG documents.
  - Keep current report/signal behavior backwards-compatible unless the gate is explicitly enabled.
  - Do not write to vector stores.

### Export and API Readiness

- [ ] Step 39 — Add persistence export contracts
  - Add typed export request/result records.
  - Support domain, timestamp range, format, and destination metadata.

- [ ] Step 40 — Add JSON export service
  - Add application service for exporting curated PostgreSQL records to JSON-compatible payloads.
  - Keep exports as boundary serialization, not internal contracts.

- [ ] Step 41 — Add report-history export support
  - Support export of report history plus linked recommendations/signals/attribution.
  - Add tests with fake repositories.

- [ ] Step 42 — Add API-ready read DTO review
  - Ensure query services return typed records suitable for future FastAPI response mapping.
  - Do not add FastAPI endpoints in V3.

### Retention and Lifecycle

- [ ] Step 43 — Add persistence retention contracts
  - Add typed retention policy records.
  - Include domain, retention period, archive flag, and deletion eligibility.

- [ ] Step 44 — Add retention policy model and migration
  - Add `persistence_retention_policies`.
  - Do not delete data automatically in this step.

- [ ] Step 45 — Add retention planning service
  - Add service that reports what would be archived/deleted.
  - Keep it dry-run only for V3.

- [ ] Step 46 — Add archive marker support
  - Add typed archive marker records or reuse audit metadata where appropriate.
  - Do not physically remove canonical records in V3.

### Operational Hardening

- [ ] Step 47 — Add persistence health check contracts
  - Add typed health result records for database connectivity, migration state, and repository readiness.

- [ ] Step 48 — Add persistence health check service
  - Verify database connection, Alembic head, required tables, and metadata imports.
  - Add tests for success/failure reporting.

- [ ] Step 49 — Add persistence diagnostics CLI/service boundary
  - Add a thin application service for diagnostics.
  - CLI wiring can be deferred unless trivial and architecture-compliant.

- [ ] Step 50 — Add migration coverage test for all V3 tables
  - Confirm V3 migrations include every new table and index.
  - Confirm all V3 models are imported into `Base.metadata`.

### Documentation and Final Readiness

- [ ] Step 51 — Update PostgreSQL persistence docs for V3
  - Document query services, validation, audit, eligibility, exports, retention, and health checks.
  - Reiterate that RAG/vector writes remain out of scope.

- [ ] Step 52 — Add final pre-RAG readiness checklist
  - Document the exact conditions required before full RAG ingestion begins.
  - Include canonical source tables, eligibility rules, and excluded data types.

- [ ] Step 53 — Run final V3 validation
  - Run targeted pytest suites.
  - Run ruff.
  - Run scoped mypy with explicit package bases if needed.
  - Run Alembic heads/history checks.
  - Run SQLAlchemy metadata import checks.
  - Run `graphify update .` after code changes.

- [ ] Step 54 — Stop for review before commit/push
  - Summarize changed files.
  - Summarize validations.
  - Do not commit unless explicitly requested.

## Test Plan

Run focused tests after each domain or subsystem:

```bash
uv run pytest -q tests/unit/core/database
uv run pytest -q tests/unit/core/storage/persistence
uv run pytest -q tests/unit/application/persistence
```

Run static checks:

```bash
uv run ruff check core/database core/storage/persistence application/persistence tests/unit/core/database tests/unit/core/storage/persistence tests/unit/application/persistence
uv run mypy --explicit-package-bases core/database core/storage/persistence application/persistence tests/unit/core/database tests/unit/core/storage/persistence tests/unit/application/persistence
```

Run migration checks:

```bash
uv run alembic heads
uv run alembic history
uv run python -c "import core.database.models; from core.database.base import Base; print(sorted(Base.metadata.tables))"
```

Run guarded integration checks when available:

```bash
uv run pytest -q tests/integration/core/storage/persistence
```

## Final V3 Completion Criteria

V3 is complete when PostgreSQL supports:

- typed domain persistence from V2
- typed query/read services for persisted records
- lineage traversal across persisted records
- validation and quality checks
- audit events for persistence operations
- duplicate-safe write behavior
- RAG eligibility marking without embeddings
- JSON/export boundaries for future API/UI use
- dry-run retention planning
- persistence health checks
- documented pre-RAG readiness criteria

Only after V3 is complete should the platform begin full RAG ingestion, embedding workers, vector-store writes, graph-store writes, retrieval APIs, or RAG orchestration workflows.

## Assumptions

- V3 begins after V2 persistence foundations are implemented or nearly implemented.
- V3 completes operational readiness and queryability, not new intelligence generation.
- Existing V1/V2 tables remain stable and should be extended through additive migrations only.
- PostgreSQL remains the canonical source of truth.
- Vector and graph stores are rebuildable projections.
- RAG source eligibility is metadata only in V3; it does not trigger ingestion.
- Raw runtime events, telemetry, provider payloads, and operational logs remain excluded from RAG source creation.

---

## Codex Recommended Adjusted V3 Plan

### Adjustment Summary

This adjusted V3 plan is based on the completed V1/V2 persistence work and the current repository state.

V2 already added typed persistence records, serializers, repositories, PostgreSQL models, migrations, and application persistence services with `get_*` / `list_*` methods for the major domains. V3 should therefore avoid creating a duplicate domain query-service layer. Instead, V3 should standardize and harden the existing application persistence services so they remain the canonical application read/write boundary.

V3 remains pre-RAG completion work only:

- no vector-store writes
- no graph-store writes
- no embedding workers
- no full RAG ingestion workflows
- no FastAPI endpoints
- no destructive retention execution

### Adjusted Architecture Decisions

- Existing V2 application persistence services are the canonical read/write application boundary.
- V3 extends existing services with shared query primitives rather than creating parallel query services.
- Repositories remain infrastructure concerns under `core.storage.persistence`.
- Application services remain typed boundaries under `application.persistence`.
- PostgreSQL remains the system of record.
- RAG/vector/graph stores remain downstream rebuildable projections.
- RAG eligibility is metadata and gating only in V3.
- Embedding job creation should be opt-in during V3, not default behavior.
- Raw runtime events, telemetry, provider payloads, and operational logs remain ineligible for curated RAG sources.

### Adjusted Implementation Steps

#### V3 Boundary and Query Standardization

- [x] Step 2 — Update V3 dependency checklist and boundary audit
  - Confirm V2 persistence services are the canonical domain read/write boundaries.
  - Document that duplicate domain query-service packages are out of scope.
  - Document current RAG source persistence and curated builder behavior.
  - Do not implement V3 code in this step.
  - Step 2 completed: dependency checklist added above; adjusted V3 plan is the source of truth for subsequent steps.

- [x] Step 3 — Add shared persistence query primitives
  - Add reusable typed query primitives for pagination, sorting, time ranges, lineage filters, symbol/account/source filters, and limit/offset validation.
  - Keep these primitives generic and reusable across persistence services.
  - Add focused validation/default tests.
  - Step 3 completed: added `core.storage.persistence.query` with immutable reusable query primitives for pagination, sort direction/order, timestamp ranges, lineage filters, source filters, symbol filters, account filters, and a composable common query object; added focused contract tests covering normalization, validation, serialization helpers, immutability, and composition. Validation passed with focused pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.

- [x] Step 4 — Add shared query result envelopes
  - Add typed read/list result envelopes carrying records, optional total count, pagination metadata, and query metadata.
  - Keep envelopes generic and independent of domain repositories.
  - Add focused tests.
  - Step 4 completed: added generic typed `PersistenceReadResult[T]` and `PersistenceListResult[T]` envelopes that preserve strongly typed records while exposing read, pagination, sort, query, total-count, has-more, returned-count, and metadata summaries at the query boundary; focused tests cover found/missing read results, list pagination metadata, unknown-total paging behavior, and total-count validation. Validation passed with focused pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.

- [x] Step 5 — Retrofit one representative service with shared query primitives
  - Use one existing application persistence service as the reference implementation.
  - Preserve existing public service methods unless a direct simplification is safe.
  - Add tests proving compatibility with existing repository protocols.
  - Step 5 completed: retrofitted `NewsPersistenceService` as the representative application persistence service by mapping existing typed news filters into shared `PersistenceCommonQuery` primitives and adding typed `PersistenceListResult[T]` read-envelope methods while preserving existing sequence-returning list methods and repository protocol calls. Added focused compatibility tests and validated with focused pytest, application persistence pytest, ruff, scoped mypy, and graphify update.

- [x] Step 6 — Retrofit remaining persistence services incrementally
  - Apply shared query primitives where they reduce duplication.
  - Do not introduce duplicate domain query-service packages.
  - Keep existing V2 service boundaries intact.
  - Step 6 completed: added shared application query-result helpers and retrofitted the remaining application persistence services with typed `PersistenceListResult[T]` result methods backed by shared `PersistenceCommonQuery` primitives while preserving existing sequence-returning list APIs and repository protocol calls. Covered macro, market, portfolio, recommendations, sentiment, reports, telemetry, attribution, agent-intelligence, workflow-audit, and the Step 5 news service helper reuse. Validation passed with application persistence pytest, focused query-contract pytest, ruff, scoped mypy, and graphify update.

- [x] Step 7 — Add cross-domain service boundary tests
  - Verify application persistence exports remain service/filter/query-contract only.
  - Verify repositories are not exported from the application boundary.
  - Verify existing services remain the single domain read/write boundary.
  - Step 7 completed: strengthened application persistence boundary tests to verify each domain module exports exactly one service plus filters only, root exports do not expose repositories/infrastructure records/bundles/results/query services, and every service preserves sequence-returning list APIs while adding matching typed `PersistenceListResult[T]` result-envelope methods. Validation passed with focused boundary pytest, application persistence pytest, ruff, scoped mypy, and graphify update.

#### Lineage Traversal

- [x] Step 8 — Add lineage traversal contracts
  - Add typed lineage traversal request/result/path contracts.
  - Support bounded upstream and downstream traversal.
  - Reuse existing `persistence_lineage_links` records.
  - Step 8 completed: added typed lineage traversal contracts under `core.storage.persistence.lineage` for bounded upstream/downstream traversal over existing `PersistenceLineageLinkRecord` links, including traversal direction, request bounds and relationship filters, path segments, paths, and traversal result summaries. Added focused contract tests for normalization, immutability, request bounds, downstream source-to-target paths, upstream target-to-source paths, contiguity validation, endpoint validation, result bounds, and relationship filtering. Validation passed with lineage/query contract pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.

- [x] Step 9 — Add lineage traversal repository methods
  - Add repository methods for bounded upstream/downstream traversal over existing lineage links.
  - Keep traversal relational/PostgreSQL-backed.
  - Do not introduce graph/vector abstractions.
  - Step 9 completed: extended the lineage repository contract and PostgreSQL lineage adapter with bounded relational traversal methods for generic traversal plus upstream and downstream convenience methods. Traversal iterates over existing `persistence_lineage_links` rows with direction-specific source/target SQL filters, optional relationship-type filters, deterministic ordering, max-depth and max-edge bounds, cycle avoidance within each path, typed path construction, and typed traversal result envelopes. Added repository tests covering downstream report → recommendation → signal traversal, upstream reverse traversal, SQL boundary filters, ordering/limit use, edge-limit truncation, and typed result behavior. Validation passed with focused lineage repository/contract pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.

- [x] Step 10 — Add lineage traversal application service
  - Add service methods for tracing persisted records.
  - Return typed lineage paths.
  - Add tests for report → recommendation → signal → workflow-style lineage paths.
  - Step 10 completed: added `application.persistence.lineage.LineagePersistenceService` as the application boundary for persisted-record lineage tracing. The service delegates bounded upstream/downstream traversal to the lineage repository contract, returns typed `PersistenceLineageTraversalResult` paths, preserves sequence-returning link list APIs with `PersistenceListResult[T]` result-envelope siblings, and is exported through the application persistence boundary without exposing repositories or infrastructure types. Added service tests covering report → recommendation → signal → workflow execution downstream paths, reverse upstream paths, explicit request delegation, list API compatibility, and result metadata. Validation passed with focused lineage service/export pytest, application persistence pytest, lineage repository/contract pytest, ruff, scoped mypy, and graphify update.

#### Data Quality and Validation

- [x] Step 11 — Add validation issue/result contracts
  - Add typed validation issue/result models with severity, record type, record id, field name, message, and remediation hint.
  - Keep validation non-destructive.
  - Step 11 completed: added immutable non-destructive persistence validation contracts under `core.storage.persistence.validation`, including severity/status enums, scoped validation issues, per-record validation results, and batch validation summaries with boundary serialization helpers and record-identity enforcement. Added focused contract tests covering normalization, required-field validation, immutability, status aggregation, cross-record issue rejection, and batch summaries. Validation passed with focused validation pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.

- [x] Step 12 — Add timestamp and score validation checks
  - Validate generated/published/observed timestamps where applicable.
  - Validate confidence, sentiment, risk, directional, attribution, and setup-quality score ranges.
  - Add tests with representative records.
  - Step 12 completed: added non-destructive timestamp and score validation checks under `core.storage.persistence.validation`, including typed validation targets, score specs, timestamp ordering rules, canonical timestamp checks for generated/published/observed fields, future/naive timestamp warnings, required timestamp errors, ordering errors, and canonical score range validation for confidence, sentiment, risk, directional, attribution, and setup-quality scores. Added representative record tests covering valid records, missing/type/future/naive/order timestamp issues, signed and ratio score failures, custom setup-quality specs, and combined timestamp+score validation. Validation passed with focused validation pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.

- [x] Step 13 — Add lineage and source/dedupe validation checks
  - Validate expected lineage when available.
  - Warn rather than fail for records legitimately created outside workflows.
  - Validate source/dedupe keys for external-source records.
  - Step 13 completed: extended `core.storage.persistence.validation` with non-destructive lineage, source, and dedupe validation checks. Added typed expected-lineage and external-source validation specs, lineage validation that accepts expected workflow/runtime fields, warns instead of failing for records intentionally created outside workflow execution, validates canonical `PersistenceLineage` typing, and validates external-source source identity plus dedupe keys. Added combined lineage/source/dedupe validation and representative tests for matching lineage, outside-workflow warnings, required/mismatched/invalid lineage failures, stable external-source keys, missing source/dedupe keys, blank source fields, custom source specs, and merged validation results. Validation passed with focused validation pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.

- [x] Step 14 — Add persistence validation application service
  - Add `application/persistence/validation`.
  - Coordinate validation checks across representative domain records.
  - Return typed validation results.
  - Step 14 completed: added `application.persistence.validation.ValidationPersistenceService` as a thin application boundary for non-destructive persisted-record validation. The service coordinates core timestamp, score, lineage, source, and dedupe checks over typed `PersistenceRecordValidationTarget` inputs, supports direct record-object validation, batches multiple targets into typed `PersistenceValidationBatchResult`, and remains repository-free/no-mutation. Export boundaries were updated so validation is exposed as an application persistence service without leaking repositories or infrastructure types. Added application service tests for valid curated records, typed issue aggregation without mutation, outside-workflow warnings, batch aggregation, custom source specs, and export-boundary behavior. Validation passed with focused service/export pytest, application persistence pytest plus core validation pytest, ruff, scoped mypy, and graphify update.

#### Audit Trail

- [x] Step 15 — Add persistence audit contracts
  - Add typed persistence audit event records.
  - Include entity type, entity id, action, actor/system source, timestamp, lineage, and metadata.
  - Step 15 completed: added immutable persistence audit contracts under `core.storage.persistence.audit`, including typed audit actors, append-only audit event records, audit write result contracts, and a unique audit event id helper. Audit events include entity type/id, action, actor/system source, timestamp, workflow/runtime lineage, and metadata with boundary serialization helpers and typed persisted-record identity access. Added contract tests covering actor normalization, audit event serialization, immutability, required-field validation, result state validation, and unique id generation. Validation passed with focused audit pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.

- [x] Step 16 — Add persistence audit model and migration
  - Add `persistence_audit_events`.
  - Index by entity type/id, action, timestamp, and workflow lineage.

- [x] Step 17 — Add audit serializer, repository, and service
  - Add append-only audit persistence.
  - Add application service for writing/listing audit events.
  - Add tests.
  - Step 17 completed: added append-only audit persistence plumbing for `PersistenceAuditEventRecord`, including `PersistenceAuditEventSerializer`, `PersistenceAuditEventRepository`, `PostgresPersistenceAuditEventRepository`, and `application.persistence.audit.AuditPersistenceService` with typed `AuditPersistenceFilters`. The PostgreSQL adapter inserts audit events without upsert/conflict-update behavior, supports get-by-id and filtered listing by entity, action, actor/system source, timestamp range, and workflow/runtime lineage, and returns typed records through serializer boundaries. The application service preserves a sequence-returning `list_audit_events` API with a `PersistenceListResult[T]` envelope sibling and is exported through the application persistence boundary without leaking repository/infrastructure types. Added serializer, repository, service, and export-boundary tests. Validation passed with focused audit pytest, full core storage/application persistence pytest, ruff, scoped mypy, and graphify update.

- [x] Step 18 — Add optional non-fatal audit emission at service boundaries
  - Add audit emission where safe at application persistence service boundaries.
  - Keep audit failures non-fatal by default.
  - Do not mutate runtime execution behavior.

#### Idempotency and Deduplication Hardening

- [x] Step 19 — Add idempotency helper contracts only where gaps remain
  - Review V2 deterministic ID helpers and upsert semantics first.
  - Add shared helpers only for concrete gaps.

- [x] Step 20 — Add recommendation and portfolio idempotency review tests
  - Confirm recommendation/setup/watchlist/rationale/outcome writes are duplicate-safe.
  - Confirm latest portfolio tables upsert and historical/snapshot records avoid accidental duplicate primary keys.

- [x] Step 21 — Add market, macro, news, and sentiment idempotency review tests
  - Confirm observation/fact records use deterministic source keys where appropriate.
  - Confirm news article dedupe uses source plus external id or URL.
  - Confirm sentiment snapshot identity is stable for source/timestamp/context.

#### RAG Eligibility Without Ingestion

- [x] Step 22 — Add RAG eligibility contracts
  - Add typed eligibility result records with source table, source id, source type, eligible flag, reason, quality score, reviewed timestamp, and metadata.
  - Keep this as metadata only.

- [x] Step 23 — Add RAG eligibility model and migration
  - Add `rag_source_eligibility`.
  - Link eligibility to canonical PostgreSQL source records by source table/source id/source type.
  - Do not create embeddings.

- [x] Step 24 — Add RAG eligibility serializer, repository, and service
  - Add mark, unmark, get, and list eligible-source methods.
  - Add focused tests.

- [x] Step 25 — Add default RAG eligibility rules
  - Eligible by default: curated reports, meaningful agent signals/reasoning, recommendations with rationales, macro/technical/news/sentiment summaries.
  - Ineligible by default: raw runtime events, raw telemetry, raw provider payloads, operational error logs.
  - Add tests.

- [x] Step 26 — Gate curated RAG source building/persistence when eligibility is enabled
  - Add optional eligibility gate before curated RAG documents are built or persisted.
  - Preserve backwards compatibility unless the gate is explicitly enabled.
  - Do not write to vector stores.

- [x] Step 27 — Make embedding job creation opt-in for pre-RAG V3
  - Change curated RAG build defaults so embedding jobs are not queued unless explicitly requested.
  - Preserve explicit `queue_embedding_jobs=True` behavior.
  - Add/update tests.

#### Export and API Readiness

- [x] Step 28 — Add persistence export contracts
  - Add typed export request/result records.
  - Support domain, timestamp range, format, and destination metadata.

- [x] Step 29 — Add JSON export service for curated records
  - Add application service for exporting selected typed PostgreSQL records to JSON-compatible payloads.
  - Keep serialization at the boundary only.

- [x] Step 30 — Add report-history export support
  - Support report history export with linked recommendations, signals, and attribution where lineage exists.
  - Add tests with fake repositories/services.

- [x] Step 31 — Add API-readiness DTO review tests
  - Verify query/export services return typed records suitable for future FastAPI response mapping.
  - Do not add FastAPI endpoints in V3.

#### Retention and Lifecycle

- [x] Step 32 — Add retention policy contracts
  - Add typed retention policy records with domain, retention period, archive flag, and deletion eligibility.

- [x] Step 33 — Add retention policy model and migration
  - Add `persistence_retention_policies`.
  - Do not delete or archive data automatically in this step.

- [x] Step 34 — Add dry-run retention planning service
  - Add service that reports archive/delete candidates.
  - Keep retention execution dry-run only in V3.

- [x] Step 35 — Add archive marker support
  - Add typed archive marker records or reuse audit metadata where appropriate.
  - Do not physically remove canonical records in V3.

#### Operational Hardening

- [x] Step 36 — Add persistence health-check contracts
  - Add typed health result records for database connectivity, migration state, metadata/table availability, and repository/service readiness.

- [x] Step 37 — Add persistence health-check service
  - Verify database connectivity, Alembic head, required tables, and metadata imports.
  - Add tests for success and failure reporting.

- [x] Step 38 — Add persistence diagnostics service boundary
  - Add a thin application service for diagnostics.
  - CLI wiring is deferred unless trivial and architecture-compliant.

- [x] Step 39 — Add migration coverage tests for all V3 tables
  - Confirm V3 migrations include every new table and index.
  - Confirm all V3 models are imported into `Base.metadata`.

#### Documentation and Final Readiness

- [x] Step 40 — Update PostgreSQL persistence docs for V3
  - Document query primitives, validation, audit, eligibility, exports, retention, and health checks.
  - Reiterate that RAG/vector/graph writes remain out of scope.

- [x] Step 41 — Add final pre-RAG readiness checklist
  - Document exact conditions required before full RAG ingestion begins.
  - Include canonical source tables, eligibility rules, excluded data types, and no-vector/no-graph constraints.

- [x] Step 42 — Run final V3 validation
  - Run targeted pytest suites.
  - Run ruff.
  - Run scoped mypy with explicit package bases if needed.
  - Run Alembic heads/history checks.
  - Run SQLAlchemy metadata import checks.
  - Run `graphify update .` after code changes.

- [x] Step 43 — Stop for review before commit/push
  - Summarize changed files.
  - Summarize validations.
  - Do not commit unless explicitly requested.

### Adjusted Test Plan

Run focused tests after each domain or subsystem:

```bash
uv run pytest -q tests/unit/core/database
uv run pytest -q tests/unit/core/storage/persistence
uv run pytest -q tests/unit/application/persistence
```

Run static checks after meaningful changes:

```bash
uv run ruff check core/database core/storage/persistence application/persistence tests/unit/core/database tests/unit/core/storage/persistence tests/unit/application/persistence
uv run mypy --explicit-package-bases core/database core/storage/persistence application/persistence tests/unit/core/database tests/unit/core/storage/persistence tests/unit/application/persistence
```

Run migration checks after every migration:

```bash
uv run alembic heads
uv run alembic history
uv run python -c "import core.database.models; from core.database.base import Base; print(sorted(Base.metadata.tables))"
```

Run guarded integration checks when available:

```bash
uv run pytest -q tests/integration/core/storage/persistence
uv run pytest -q tests/integration/application/persistence
```

### Adjusted Completion Criteria

V3 is complete when PostgreSQL persistence has:

- standardized shared query primitives and result envelopes
- existing V2 services hardened as canonical read/write boundaries
- lineage traversal over persisted record links
- validation and quality checks
- append-only persistence audit events
- duplicate-safe write behavior verified by tests
- RAG eligibility marking and optional gating without embeddings
- JSON/export boundaries for future API/UI use
- dry-run retention planning
- persistence health checks
- documented pre-RAG readiness criteria

Only after adjusted V3 is complete should the platform begin full RAG ingestion, embedding workers, vector-store writes, graph-store writes, retrieval APIs, or RAG orchestration workflows.

### Adjusted Assumptions

- V2 is complete and validated.
- Existing V2 application persistence services are canonical.
- V3 extends existing boundaries rather than creating duplicate domain query services.
- PostgreSQL remains the canonical source of truth.
- RAG/vector/graph stores remain rebuildable projections.
- RAG eligibility in V3 is metadata and gating only.
- Embedding job creation is opt-in during V3.
- Raw runtime events, telemetry, provider payloads, and operational logs remain excluded from RAG source creation.

## Step Results

- [x] Step 1 completed: created `.agent/plans/plan_postgres_persistence_v3.md` with the V3 pre-RAG persistence completion plan.
- [x] Step 2 completed: reviewed V2 completion boundary and current repository state; appended the Codex adjusted V3 plan that avoids duplicate domain query services, preserves existing V2 application persistence services as canonical read/write boundaries, narrows V3 to query standardization, lineage traversal, validation, audit, idempotency hardening, RAG eligibility metadata/gating, export readiness, retention dry-run planning, health checks, documentation, and final validation.
- [x] Step 3 completed: added `core.storage.persistence.query` with immutable reusable query primitives for pagination, sorting, timestamp ranges, lineage/source/symbol/account filters, and composable common queries; added focused contract tests and validated with focused pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 4 completed: added generic typed `PersistenceReadResult[T]` and `PersistenceListResult[T]` envelopes under `core.storage.persistence.query`; envelopes preserve typed records and expose query/pagination/sort/metadata summaries plus found, returned-count, total-count, and has-more semantics. Focused tests and full core storage persistence tests passed, along with ruff, scoped mypy, and graphify update.
- [x] Step 5 completed: retrofitted `NewsPersistenceService` as the representative application persistence service by mapping existing typed news filters into shared `PersistenceCommonQuery` primitives and adding typed `PersistenceListResult[T]` read-envelope methods while preserving existing sequence-returning list methods and repository protocol calls. Added focused compatibility tests and validated with focused pytest, application persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 6 completed: added shared application query-result helpers and retrofitted the remaining application persistence services with typed `PersistenceListResult[T]` result methods backed by shared `PersistenceCommonQuery` primitives while preserving existing sequence-returning list APIs and repository protocol calls. Covered macro, market, portfolio, recommendations, sentiment, reports, telemetry, attribution, agent-intelligence, workflow-audit, and the Step 5 news service helper reuse. Validation passed with application persistence pytest, focused query-contract pytest, ruff, scoped mypy, and graphify update.
- [x] Step 7 completed: strengthened application persistence boundary tests to verify each domain module exports exactly one service plus filters only, root exports do not expose repositories/infrastructure records/bundles/results/query services, and every service preserves sequence-returning list APIs while adding matching typed `PersistenceListResult[T]` result-envelope methods. Validation passed with focused boundary pytest, application persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 8 completed: added typed lineage traversal contracts under `core.storage.persistence.lineage` for bounded upstream/downstream traversal over existing `PersistenceLineageLinkRecord` links, including traversal direction, request bounds and relationship filters, path segments, paths, and traversal result summaries. Added focused contract tests for normalization, immutability, request bounds, downstream source-to-target paths, upstream target-to-source paths, contiguity validation, endpoint validation, result bounds, and relationship filtering. Validation passed with lineage/query contract pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 9 completed: extended the lineage repository contract and PostgreSQL lineage adapter with bounded relational traversal methods for generic traversal plus upstream and downstream convenience methods. Traversal iterates over existing `persistence_lineage_links` rows with direction-specific source/target SQL filters, optional relationship-type filters, deterministic ordering, max-depth and max-edge bounds, cycle avoidance within each path, typed path construction, and typed traversal result envelopes. Added repository tests covering downstream report → recommendation → signal traversal, upstream reverse traversal, SQL boundary filters, ordering/limit use, edge-limit truncation, and typed result behavior. Validation passed with focused lineage repository/contract pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 10 completed: added `application.persistence.lineage.LineagePersistenceService` as the application boundary for persisted-record lineage tracing. The service delegates bounded upstream/downstream traversal to the lineage repository contract, returns typed `PersistenceLineageTraversalResult` paths, preserves sequence-returning link list APIs with `PersistenceListResult[T]` result-envelope siblings, and is exported through the application persistence boundary without exposing repositories or infrastructure types. Added service tests covering report → recommendation → signal → workflow execution downstream paths, reverse upstream paths, explicit request delegation, list API compatibility, and result metadata. Validation passed with focused lineage service/export pytest, application persistence pytest, lineage repository/contract pytest, ruff, scoped mypy, and graphify update.
- [x] Step 11 completed: added immutable non-destructive persistence validation contracts under `core.storage.persistence.validation`, including severity/status enums, scoped validation issues, per-record validation results, and batch validation summaries with boundary serialization helpers and record-identity enforcement. Added focused contract tests covering normalization, required-field validation, immutability, status aggregation, cross-record issue rejection, and batch summaries. Validation passed with focused validation pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 12 completed: added non-destructive timestamp and score validation checks under `core.storage.persistence.validation`, including typed validation targets, score specs, timestamp ordering rules, canonical timestamp checks for generated/published/observed fields, future/naive timestamp warnings, required timestamp errors, ordering errors, and canonical score range validation for confidence, sentiment, risk, directional, attribution, and setup-quality scores. Added representative record tests covering valid records, missing/type/future/naive/order timestamp issues, signed and ratio score failures, custom setup-quality specs, and combined timestamp+score validation. Validation passed with focused validation pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 13 completed: extended `core.storage.persistence.validation` with non-destructive lineage, source, and dedupe validation checks. Added typed expected-lineage and external-source validation specs, lineage validation that accepts expected workflow/runtime fields, warns instead of failing for records intentionally created outside workflow execution, validates canonical `PersistenceLineage` typing, and validates external-source source identity plus dedupe keys. Added combined lineage/source/dedupe validation and representative tests for matching lineage, outside-workflow warnings, required/mismatched/invalid lineage failures, stable external-source keys, missing source/dedupe keys, blank source fields, custom source specs, and merged validation results. Validation passed with focused validation pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 14 completed: added `application.persistence.validation.ValidationPersistenceService` as a thin application boundary for non-destructive persisted-record validation. The service coordinates core timestamp, score, lineage, source, and dedupe checks over typed `PersistenceRecordValidationTarget` inputs, supports direct record-object validation, batches multiple targets into typed `PersistenceValidationBatchResult`, and remains repository-free/no-mutation. Export boundaries were updated so validation is exposed as an application persistence service without leaking repositories or infrastructure types. Added application service tests for valid curated records, typed issue aggregation without mutation, outside-workflow warnings, batch aggregation, custom source specs, and export-boundary behavior. Validation passed with focused service/export pytest, application persistence pytest plus core validation pytest, ruff, scoped mypy, and graphify update.
- [x] Step 15 completed: added immutable persistence audit contracts under `core.storage.persistence.audit`, including typed audit actors, append-only audit event records, audit write result contracts, and a unique audit event id helper. Audit events include entity type/id, action, actor/system source, timestamp, workflow/runtime lineage, and metadata with boundary serialization helpers and typed persisted-record identity access. Added contract tests covering actor normalization, audit event serialization, immutability, required-field validation, result state validation, and unique id generation. Validation passed with focused audit pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 16 completed: added `PersistenceAuditEventModel` for the append-only `persistence_audit_events` table, imported it into `Base.metadata`, and added Alembic migration `20260530_0017_add_persistence_audit_events.py`. The table persists audit event ids, entity type/id, action, actor/system source fields, timestamp, workflow/runtime lineage, metadata JSONB, and row timestamps, with indexes for entity lookup, action/timestamp queries, and workflow/runtime lineage. Added model and migration tests and updated the Alembic foundation metadata test. Validation passed with focused audit database pytest, full core database pytest, ruff, scoped mypy, Alembic heads/history checks, metadata import check, and graphify update.
- [x] Step 17 completed: added append-only audit persistence plumbing for `PersistenceAuditEventRecord`, including `PersistenceAuditEventSerializer`, `PersistenceAuditEventRepository`, `PostgresPersistenceAuditEventRepository`, and `application.persistence.audit.AuditPersistenceService` with typed `AuditPersistenceFilters`. The PostgreSQL adapter inserts audit events without upsert/conflict-update behavior, supports get-by-id and filtered listing by entity, action, actor/system source, timestamp range, and workflow/runtime lineage, and returns typed records through serializer boundaries. The application service preserves a sequence-returning `list_audit_events` API with a `PersistenceListResult[T]` envelope sibling and is exported through the application persistence boundary without leaking repository/infrastructure types. Added serializer, repository, service, and export-boundary tests. Validation passed with focused audit pytest, full core storage/application persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 18 completed: added optional non-fatal persistence audit emission at safe application persistence service boundaries. Introduced `PersistenceAuditEmission`, `PersistenceAuditEmitter`, `NonFatalPersistenceAuditEmitter`, and `emit_persistence_audit_events_non_fatal` under `application.persistence.audit.audit_emission` so services can describe typed audit events after primary persistence succeeds without making audit storage part of the business write path. Wired representative curated write services (`NewsPersistenceService` and `RecommendationPersistenceService`) to accept an optional audit emitter and emit append-only `persist` audit requests for news articles, news analysis snapshots, recommendations, rationales, outcomes, trade setups, and watchlist items. Audit emission remains disabled unless an emitter is injected, catches emitter failures, does not change runtime execution behavior, and preserves existing constructor compatibility. Added tests for typed emission, disabled emission, audit exception conversion, ordered batch emission, service-boundary audit metadata, and non-fatal primary writes when audit emission fails. Validation passed with focused audit/news/recommendation/export pytest, full application/core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 19 completed: reviewed existing V2 deterministic ID helpers and repository upsert semantics across recommendations, portfolio, market, macro, news, sentiment, reports, runtime, lineage, telemetry, and RAG persistence. Added a small shared idempotency contract package under `core.storage.persistence.idempotency` only for the remaining cross-domain gap: reusable typed construction of stable natural-key strings for future persistence domains. The new contracts include immutable `PersistenceIdempotencyKey`, `build_persistence_idempotency_key`, `symbol_idempotency_component`, and `timestamp_idempotency_component`, with required-component validation, optional-component omission, namespace/version support, ISO timestamp normalization, symbol normalization, and boundary serialization. No existing domain ID helpers or repository behavior were rewritten in this step. Added focused idempotency contract tests and validated with focused pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 20 completed: added recommendation and portfolio idempotency review tests confirming recommendation parent, rationale, outcome, setup, and watchlist writes are duplicate-safe PostgreSQL upserts by stable identifiers; latest portfolio positions upsert by account/symbol; and portfolio history, exposure, risk, and allocation snapshots remain insert-only while ID helpers avoid accidental duplicate primary keys when execution lineage is absent. No production repository behavior was changed. Validation passed with focused recommendation/portfolio pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 21 completed: added market, macro, news, and sentiment idempotency review tests confirming market OHLCV/indicator and macro observation/calendar fact records use deterministic source-key identities and duplicate-safe PostgreSQL upserts; news articles dedupe by source plus external id or URL while analysis snapshots remain append-only; and sentiment snapshot identity is stable when source, timestamp, execution lineage, and context are provided while sentiment records remain append-only. Added a backwards-compatible optional `source` component to `new_sentiment_snapshot_id` to close the source-aware identity gap without changing existing call sites. Validation passed with focused market/macro/news/sentiment pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 22 completed: added metadata-only RAG source eligibility contracts under `core.storage.persistence.rag`, including `RagSourceEligibilityRecord`, `RagSourceEligibilityResult`, and stable `new_rag_source_eligibility_id` helper. Eligibility records identify canonical PostgreSQL sources by source table, source id, and source type; carry eligible flag, reason, quality score, reviewed timestamp, and metadata; expose boundary serialization through `as_dict`; and explicitly do not create documents, chunks, embedding jobs, vector writes, graph writes, or ingestion behavior. Validation passed with focused RAG eligibility pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 23 completed: added PostgreSQL schema support for metadata-only RAG eligibility through `RagSourceEligibilityModel` and Alembic migration `20260530_0018_add_rag_source_eligibility.py`. The new `rag_source_eligibility` table stores eligibility id, canonical source table/id/type, eligible flag, reason, quality score, reviewed timestamp, metadata JSONB, and row timestamps; enforces one eligibility record per canonical source via `uq_rag_source_eligibility_source`; validates quality score with `ck_rag_source_eligibility_quality_score_range`; and adds source/eligibility lookup indexes. The model is imported into `Base.metadata`, and tests verify the migration stays metadata-only without document, chunk, embedding, vector, graph, or ingestion relationships. Validation passed with focused database tests, full core database pytest, full core storage persistence pytest, ruff, scoped mypy, Alembic heads/history/metadata checks, and graphify update.
- [x] Step 24 completed: added metadata-only RAG eligibility persistence plumbing across the serializer, repository, PostgreSQL adapter, and application service boundary. `RagPersistenceSerializer` now maps `RagSourceEligibilityRecord` to/from `RagSourceEligibilityModel`; `RagPersistenceRepository` and `PostgresRagPersistenceRepository` now support mark, unmark, get, and filtered list operations for canonical source eligibility records; and `application.persistence.rag.RagEligibilityPersistenceService` exposes typed mark/unmark/get/list methods plus `PersistenceListResult[T]` envelopes through `RagEligibilityPersistenceFilters`. Focused tests cover serializer round-trips, metadata-only repository upserts/deletes/queries, typed application service delegation, result envelopes, export boundaries, and RAG readiness method scope. No RAG document building, chunking, ingestion jobs, embeddings, vector writes, or graph writes were added. Validation passed with focused RAG persistence/application tests, full core storage persistence plus application persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 25 completed: added metadata-only default RAG eligibility rules under `core.storage.persistence.rag`, including typed `RagEligibilitySourceCandidate`, `DefaultRagEligibilityRules`, and `evaluate_default_rag_source_eligibility`. The rules mark curated reports, meaningful agent signals/reasoning, recommendation rationales or recommendations with rationales, and macro/technical/news/sentiment summaries eligible by default, while raw runtime records, raw telemetry, raw provider payload/fact tables, operational error logs, sources without meaningful curated content, and unknown sources remain ineligible by default. Rule outputs are `RagSourceEligibilityRecord` metadata only and do not build documents, chunks, embedding jobs, vector writes, graph writes, or ingestion workflows. Validation passed with focused RAG eligibility/readiness pytest, full core storage persistence plus application persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 26 completed: added an optional curated RAG eligibility gate to `application.rag`. `CuratedRagBuildOptions` now includes `require_source_eligibility=False` so existing builder and ingestion flows remain backward compatible by default. When explicitly enabled, `CuratedRagDocumentBuilder` evaluates default typed eligibility before building documents and raises `CuratedRagSourceNotEligibleError` for ineligible sources; `CuratedRagIngestionService` checks persisted `rag_source_eligibility` metadata first, falls back to default eligibility rules when no persisted marker exists, passes the resolved eligibility decision into the builder, and returns a failed `RagPersistenceResult` without persisting documents/chunks/jobs when a source is ineligible. Added tests for default legacy persistence, default eligibility-gated persistence, persisted ineligible-source blocking before build/persist, persisted eligible manual overrides, and builder-level meaningful-content gating. No vector stores, graph stores, or full ingestion workflows were added. Validation passed with 37 focused application RAG/RAG eligibility/readiness tests, 635 full application RAG plus core storage/application persistence tests, ruff, scoped mypy, `git diff --check`, and graphify update.
- [x] Step 27 completed: made curated RAG embedding job creation opt-in for pre-RAG V3 by changing `CuratedRagBuildOptions.queue_embedding_jobs` to default to `False`. Existing explicit `queue_embedding_jobs=True` behavior is preserved and still queues one embedding job per chunk through the PostgreSQL persistence bundle only. Added a focused builder test proving default curated RAG builds create documents/chunks without embedding jobs, while existing explicit-true tests continue to cover queued jobs. No vector stores, graph stores, embedding execution, or full ingestion workflows were added. Validation passed with 38 focused application RAG/RAG eligibility/readiness tests, 636 full application RAG plus core storage/application persistence tests, ruff, scoped mypy, `git diff --check`, and graphify update.
- [x] Step 28 completed: added typed persistence export contracts under `core.storage.persistence.export`, including `PersistenceExportFormat`, `PersistenceExportDestinationType`, `PersistenceExportDestination`, `PersistenceExportRequest`, and `PersistenceExportResult`. The contracts support normalized export domains, timestamp ranges via `PersistenceTimeRange`, export format selection, destination type/URI/metadata, request metadata, result record counts by domain, artifact URI, and success/failure validation. These are metadata/request/result contracts only and do not serialize records, write files, create embeddings, write vector stores, write graph stores, or add export execution services. Added focused contract tests for destination normalization, domain deduplication, timestamp/format validation, single-domain convenience, result success/failure state, immutability, and boundary dictionaries. Validation passed with 15 focused export/query tests, 519 full core storage persistence tests, ruff, scoped mypy, `git diff --check`, and graphify update.
- [x] Step 29 completed: added `application.persistence.export.JsonPersistenceExportService` as the application boundary for JSON-compatible persistence exports. The service accepts selected typed PostgreSQL persistence records from upstream application services, serializes dataclass or `as_dict()` records only at the explicit export boundary, supports requested-domain selection while ignoring extra supplied domains, returns typed `JsonPersistenceExportResult`/payload internals, reports unsupported formats or unserializable records as failed `PersistenceExportResult`s without raising, and is exported through the application persistence boundary without exposing repository/infrastructure types. Added focused JSON export service tests and updated application persistence boundary tests. No repositories were queried, no files were written, no embeddings were created, and no vector/graph/RAG ingestion behavior was added. Validation passed with 16 focused export/application tests, 635 full application plus core storage persistence tests, ruff, scoped mypy, `git diff --check`, and graphify update.
- [x] Step 30 completed: extended `application.persistence.export.JsonPersistenceExportService` with typed report-history export support through `ReportHistoryExportRequest`. The new `export_report_history` method coordinates existing application services, loads the curated report bundle, optionally traces downstream persisted lineage from the report, and includes linked recommendation bundles, agent signals, enriched agent-intelligence records, attribution records, and lineage paths where lineage/service data exists before delegating final JSON serialization to the Step 29 boundary serializer. Missing reports and invalid report bundle shapes return failed typed export results without raising. Added fake-service tests covering report bundle export, lineage-linked recommendations/signals/attribution export, no-lineage behavior, missing report failure, and export-boundary stability. No repositories are queried directly, no files are written, no embeddings are created, and no vector/graph/RAG ingestion behavior was added. Validation passed with 19 focused export/application tests, 638 full application plus core storage persistence tests, ruff, scoped mypy, `git diff --check`, and graphify update.
- [x] Step 31 completed: added API-readiness DTO review tests proving persistence query/read result envelopes preserve typed records internally while exposing JSON-compatible metadata dictionaries for future API mapping, JSON export results serialize typed records only at the application export boundary, report-history export results are JSON-compatible without adding FastAPI, and persistence source layers do not introduce FastAPI endpoint dependencies in V3. No FastAPI endpoints, repository behavior, embeddings, vector writes, graph writes, or RAG ingestion behavior were added. Validation passed with 18 focused export/API-readiness tests, 643 full application plus core storage persistence tests, ruff, scoped mypy, `git diff --check`, and graphify update.
- [x] Step 32 completed: added typed retention policy contracts under `core.storage.persistence.retention`, including immutable `PersistenceRetentionPeriod`, `PersistenceRetentionPolicyRecord`, and stable `new_persistence_retention_policy_id` helper. Policies carry normalized domain, typed retention duration, archive-before-delete flag, deletion eligibility flag, enabled state, optional description, and metadata, with JSON-compatible boundary dictionaries and non-mutating lifecycle convenience properties. This step added contracts only; no database model, migration, archive execution, deletion execution, or automatic lifecycle behavior was introduced. Validation passed with 27 focused retention/export/RAG eligibility contract tests, 528 full core storage persistence tests, ruff, scoped mypy, `git diff --check`, and graphify update.
- [x] Step 33 completed: added `PersistenceRetentionPolicyModel` and Alembic migration `20260530_0019_add_persistence_retention_policies.py` for the `persistence_retention_policies` table. The table stores retention policy metadata by unique domain with typed retention-period days, archive-before-delete flag, deletion eligibility flag, enabled state, optional description, metadata JSONB, row timestamps, positive-period check constraint, and lifecycle lookup indexes. Added model, migration, and metadata import tests. This step created schema support only; no archive execution, deletion execution, automatic lifecycle job, or canonical-record mutation behavior was added. Validation passed with 19 focused retention/database tests, 723 full core database plus core storage persistence tests, ruff, scoped mypy, Alembic heads/history checks, metadata import check, `git diff --check`, and graphify update.
- [x] Step 34 completed: added a dry-run retention planning boundary under `application.persistence.retention`, including `RetentionPersistenceService` and `RetentionPlanningFilters`, plus typed retention planning records/actions/results under `core.storage.persistence.retention`. The service evaluates typed retention policies against typed candidate records, reports archive/delete/retain/skip candidates, supports domain filtering, rejects duplicate policy domains, and returns JSON-compatible dry-run plan summaries. This step remains advisory only: it does not persist plans, schedule jobs, archive records, delete records, mutate canonical PostgreSQL records, or perform RAG/vector/graph work. Validation passed with 21 focused retention/application/export tests, 658 full application plus core storage persistence tests, ruff, scoped mypy, `git diff --check`, and graphify update.
- [x] Step 35 completed: added typed dry-run archive marker support under `core.storage.persistence.retention`, including `PersistenceArchiveMarkerRecord` and `new_persistence_archive_marker_id`, plus `RetentionPersistenceService.build_archive_markers` to derive advisory archive markers from archive candidates only. Archive markers are JSON-compatible and audit-metadata-ready, remain dry-run lifecycle metadata, and do not persist plans, schedule jobs, archive records, delete records, mutate canonical PostgreSQL records, or perform RAG/vector/graph work. Validation passed with 26 focused retention/application/export tests, 663 full application plus core storage persistence tests, ruff, scoped mypy, `git diff --check`, and graphify update.
- [x] Step 36 completed: added typed persistence health-check contracts under `core.storage.persistence.health`, including `PersistenceHealthStatus`, `PersistenceHealthCheckCategory`, `PersistenceHealthCheckResult`, and `PersistenceHealthReport` for database connectivity, migration state, metadata/table availability, repository readiness, and service readiness diagnostics. The contracts are immutable, JSON-compatible, aggregate health status without opening database connections, and remain diagnostic contracts only; no health-check execution service, CLI wiring, repository probing, database mutation, RAG/vector/graph work, or migration behavior was added. Validation passed with 18 focused health/retention contract tests, 537 full core storage persistence tests, 668 full application plus core storage persistence tests, ruff, scoped mypy, `git diff --check`, and graphify update.
- [x] Step 37 completed: added `application.persistence.health.HealthPersistenceService` with typed `HealthPersistenceFilters` to produce non-mutating persistence health reports for PostgreSQL connectivity, Alembic head/current revision state, SQLAlchemy metadata imports, required database table availability, and optional repository/service readiness components. The service uses injectable probes for testability and default runtime probes for database connectivity, table inspection, Alembic revision lookup, and metadata import checks; it reports success, degraded/unknown state, and failures through the Step 36 health contracts without mutating database state. Validation passed with 15 focused health/export/contract tests, 672 full application plus core storage persistence tests, ruff, scoped mypy, `git diff --check`, and graphify update.
- [x] Step 38 completed: added `application.persistence.diagnostics.DiagnosticsPersistenceService` with typed `DiagnosticsPersistenceFilters` as a thin diagnostics application boundary that delegates to the canonical `HealthPersistenceService` and returns typed `PersistenceHealthReport` diagnostics. The boundary is exported through `application.persistence` without exposing repositories, serializers, models, records, bundles, or result types, and no CLI/API rendering or wiring was added. Validation passed with 19 focused diagnostics/health/export/contract tests, 676 full application plus core storage persistence tests, ruff, scoped mypy, `git diff --check`, and graphify update.
- [x] Step 39 completed: added aggregate V3 migration coverage tests for `persistence_audit_events`, `rag_source_eligibility`, and `persistence_retention_policies`, confirming migration file presence, linear Alembic revision chain, create/drop table coverage, expected columns, primary keys, indexes, constraints, and SQLAlchemy `Base.metadata` model imports/index/constraint coverage. Tests are read-only and do not execute migrations, connect to PostgreSQL, mutate database state, or add RAG/vector/graph behavior. Validation passed with 6 focused V3 migration coverage tests, 877 full core database/core storage/application persistence tests, ruff, scoped mypy, and `git diff --check`; graphify update also completed.
- [x] Step 40 completed: updated `docs/postgres_persistence.md` for V3 by adding migration inventory entries for audit events, RAG eligibility, and retention policies; documenting canonical application persistence service boundaries; adding V3 pre-RAG architecture scope; documenting query primitives/result envelopes, lineage traversal, validation/data quality, append-only audit events, idempotency guidance, JSON export boundaries, dry-run retention planning, health/diagnostics, and metadata-only RAG eligibility with opt-in embedding job creation. The docs explicitly reiterate that V3 does not add vector writes, graph writes, embedding workers, full RAG ingestion workflows, FastAPI endpoints, or destructive retention execution. Validation passed with focused V3 migration coverage pytest and `git diff --check`.
- [x] Step 41 completed: added the final pre-RAG readiness checklist to `docs/postgres_persistence.md`, covering required PostgreSQL foundation checks, canonical eligible source tables, metadata-only eligibility and quality rules, explicitly excluded data types, and pre-ingestion gates that preserve no-vector/no-graph/no-embedding-worker/no-full-ingestion constraints until a dedicated RAG plan begins. Validation passed with focused V3 migration coverage pytest and `git diff --check`.
- [x] Step 42 completed: ran final V3 validation across the PostgreSQL persistence boundary. Validation passed with `uv run pytest -q tests/unit/core/database tests/unit/core/storage/persistence tests/unit/application/persistence tests/integration/application/persistence` (878 passed), `uv run ruff check ...` (all checks passed), `uv run mypy --explicit-package-bases ...` (no issues in 281 source files), `uv run alembic heads` (`20260530_0019 (head)`), `uv run alembic history` (linear migration chain through V3), SQLAlchemy metadata import check (53 tables with V3 audit/RAG eligibility/retention tables present), `git diff --check`, and `graphify update .`.
- [x] Step 43 completed: stopped for review before commit/push. Current V3-related changes include the adjusted V3 plan, PostgreSQL persistence documentation, application persistence exports plus diagnostics/health/retention services, retention database model and migration `20260530_0019`, health and retention core persistence contracts, V3 migration/alembic/export/API-readiness tests, and updated graphify outputs. Final validation from Step 42 passed with 878 persistence tests, ruff, mypy, Alembic heads/history checks, SQLAlchemy metadata import check, `git diff --check`, and `graphify update .`. No commit or push was performed.
