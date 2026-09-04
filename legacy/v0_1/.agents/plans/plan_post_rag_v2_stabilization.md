  # Post–Platform RAG V2 Stabilization and MCP Readiness Plan

  ## Summary

  The Platform RAG Pipeline V2 implementation is functionally strong, but the review identified several architectural loose ends that should be resolved before introducing an MCP server:

  - RagOperationsService, RagRetriever, the RAG graph, and the PostgreSQL RAG repository are high-churn hotspots.
  - CLI RAG composition duplicates infrastructure construction instead of using the canonical Dishka/bootstrap composition root.
  - Backtest timestamps and important RAG query audit data are incorrectly buried in generic metadata.
  - Legacy Qdrant collections may use an incompatible unnamed-vector schema.
  - Broad package re-exports create eager imports and test/coverage fragility.
  - Existing MCP files are empty placeholders, and the current MCP plans risk creating parallel datastore clients.
  - The ordinary RAG test suite is healthy—178 tests passed—but targeted coverage exposes weak areas, particularly the PostgreSQL RAG repository at 27.6% and RagOperationsService at 58.5%.

  High churn alone will not trigger refactoring. Structurally healthy components such as the security layer, integration clients, model providers, and RagService will remain stable unless a specific defect or contract change
  requires modification.

  The user has authorized narrowly targeted core bootstrap, persistence model, and schema changes.

  ## Implementation Steps

  ### 1. Establish the stabilization baseline

  - Record current Repowise health, risk, hotspot, and coverage findings.
  - Run the deterministic RAG unit, integration, migration, CLI, graph, security, and provider suites.
  - Separate actual failures from coverage-command collection issues.
  - Treat the current 54.4% coverage result only as a selected-test diagnostic because it measured the configured project source set without running the full suite.
  - Add explicit stabilization acceptance criteria to the active plan:
      - no RAG test regressions;
      - clean Ruff and MyPy;
      - migration/model parity;
      - successful live PostgreSQL, Qdrant, Neo4j, embedding, and reranker checks;
      - no new high-risk Repowise findings.

  ### 2. Remove eager RAG package import side effects

  - Reduce broad re-exports from RAG package __init__.py files.
  - Use direct module imports internally.
  - Keep only lightweight contracts and intentional public interfaces exported at package level.
  - Ensure importing application contracts does not initialize NumPy, Qdrant, Neo4j, Ollama, or other optional infrastructure.
  - Verify pytest-cov can collect RAG tests without the NumPy “module loaded more than once” failure.

  ### 3. Promote backtest timestamps to domain fields

  Add first-class timezone-aware fields:

  - BacktestMetricRecord.recorded_at
  - BacktestArtifactRecord.generated_at

  Update the corresponding ORM models, repository mappings, structured-source adapters, and test factories.

  Migration backfill precedence:

  1. Valid legacy metadata.timestamp or metadata.created_at.
  2. The canonical parent backtest completion timestamp.
  3. The row’s database created_at.

  Do not use Unix epoch as a fabricated fallback. New records must receive a real domain timestamp before persistence.

  ### 4. Remove backtest timestamp metadata dependence

  - Make RAG structured-source timestamp extraction use the new typed timestamp fields.
  - Remove metadata probing specifically for backtest metrics and artifacts.
  - Replace generic epoch fallback behavior with an explicit “timestamp unavailable” result or validation failure.
  - Keep presentation and serialization logic separate from timestamp selection.
  - Add deterministic recency and temporal-filtering tests.

  ### 5. Promote important RAG query audit data to first-class persistence fields

  Extend the typed query-log contract and ORM schema with:

  - model_executions: ordered, bounded JSONB collection of typed model-execution records;
  - context_count: non-null integer, default 0;
  - citation_count: non-null integer, default 0;
  - grounding_score: nullable numeric value when not evaluated;
  - utility_score: nullable numeric value when not evaluated;
  - injection_detected: non-null boolean, default false;
  - reflection_scores: typed JSONB object;
  - corrective_actions: typed JSONB collection.

  Keep generic metadata only for optional or non-contractual debugging annotations. Do not introduce a normalized model-execution child table yet; the first-class JSONB column provides an appropriate persistence boundary
  without premature complexity.

  ### 6. Migrate and backfill query-log audit fields

  - Add an Alembic migration for the new query-log columns.
  - Backfill existing rows from their current metadata representation.
  - Remove migrated keys from generic metadata where doing so does not destroy unrelated information.
  - Add indexes only for fields expected to support operational queries, such as injection_detected and score-based diagnostics.
  - Verify migration upgrade, downgrade where supported, and ORM metadata parity against live PostgreSQL.

  ### 7. Create canonical RAG dependency-injection composition

  Introduce dedicated Dishka providers for:

  - RAG persistence;
  - embedding and reranking providers;
  - Qdrant and Neo4j projections;
  - routing and generation models;
  - RAG application services;
  - shared telemetry and observability dependencies.

  Wire these providers through the existing application container/bootstrap facilities. All RAG consumers must receive the same scoped resources, telemetry manager, and datastore clients.

  This is an authorized, targeted core/bootstrap change. It must not change runtime execution contracts or create RAG-specific behavior in the runtime engine.

  ### 8. Move the CLI onto canonical RAG composition

  - Remove manual infrastructure construction from the RAG CLI command service.
  - Resolve application services from the shared async Dishka container.
  - Remove the private CLI telemetry runtime and duplicate per-command infrastructure setup.
  - Ensure clients, sessions, and telemetry exporters close exactly once.
  - Keep Typer commands as thin serialization and user-interaction boundaries.
  - Establish this composition path as the one the future MCP server will reuse.

  ### 9. Split RagOperationsService by use case

  Replace the low-health god class with focused application services:

  - ingestion/source operations;
  - embedding-job operations;
  - projection lifecycle and rebuild operations;
  - RAG status and readiness operations.

  Extract source loading behind typed source-loader contracts or a registry. Remove the existing monolithic service after updating its callers; do not retain a legacy compatibility wrapper unless a concrete external consumer is
  discovered.

  Preserve transactional boundaries, telemetry, retry semantics, and canonical PostgreSQL ownership.

  ### 10. Simplify curated ingestion orchestration

  - Extract source acquisition, document construction, chunk persistence, and job creation into clearly bounded collaborators.
  - Keep the ingestion coordinator responsible for sequencing and transaction ownership rather than data transformation details.
  - Preserve typed domain objects internally.
  - Ensure retries cannot create duplicate canonical documents, chunks, or embedding jobs.
  - Add focused transaction rollback and idempotency tests.

  ### 11. Decompose RagRetriever internally

  Keep the public typed retrieval operation stable while extracting:

  - filter evaluation;
  - temporal/as-of validation;
  - dense/sparse candidate collection;
  - reciprocal-rank or hybrid fusion;
  - reranking and final context selection.

  Do not change retrieval policy or ranking semantics during this refactor. Capture current deterministic ranking behavior in tests before extraction.

  ### 12. Isolate graph routing and post-processing policy

  - Move CRAG/Self-RAG route selection and post-processing safety decisions into a pure, typed policy component.
  - Keep the RAG graph responsible for orchestration, state transitions, bounded loops, and event emission.
  - Preserve existing graph state and result contracts.
  - Add direct tests for corrective loops, maximum-loop termination, security rejection, low-quality context, web fallback, and successful synthesis.

  ### 13. Review remaining bounded complexity hotspots

  Evaluate, without automatically refactoring:

  - graph entity extraction;
  - embedding-job processing;
  - structured-source rendering;
  - graph projection extraction.

  Only extract code where Repowise findings, tests, and actual responsibility boundaries demonstrate a concrete benefit. Do not refactor healthy modules merely because they are large or recently changed.

  ### 14. Add typed projection readiness diagnostics

  Introduce a typed projection-readiness result reporting:

  - canonical PostgreSQL document, chunk, and job counts;
  - pending, retryable, and failed embedding jobs;
  - Qdrant collection existence;
  - named dense/sparse vector schema compatibility;
  - configured versus actual vector dimensions;
  - Qdrant point count and health;
  - Neo4j connectivity and projection health;
  - embedding and reranker endpoint readiness.

  Expose the result through application operations and CLI formatting. Do not place readiness information into unstructured metadata.

  ### 15. Implement the controlled Qdrant rebuild gate

  - Detect legacy unnamed-vector or dimension-incompatible collections.
  - Fail closed with clear remediation instead of silently recreating collections at startup.
  - Require explicit user confirmation for destructive projection recreation.
  - Snapshot canonical PostgreSQL document and chunk counts before rebuilding.
  - Recreate only the configured Qdrant projection.
  - Requeue canonical PostgreSQL embedding jobs.
  - Verify PostgreSQL documents and chunks were not deleted or changed.
  - Verify the rebuilt collection uses named dense and sparse vectors and reaches the expected point count.
  - Record rebuild telemetry, duration, counts, and failures.

  ### 16. Remove only verified dead or duplicate code

  - Validate the apparently unused vector_search_result_from_mapping helper with static references and tests before removal.
  - Run jscpd and the required duplicate-code checks before extracting shared helpers.
  - Treat Repowise duplication and unused-export findings as leads, not proof.
  - Do not remove local protocols solely because static export analysis reports no external callers.

  ### 17. Correct the MCP architecture plans before implementation

  Revise the MCP plans so the MCP server is a transport boundary over canonical application services, not a parallel RAG implementation.

  The MCP server must:

  - resolve services through the same Dishka composition used by the CLI;
  - reuse existing PostgreSQL, Qdrant, Neo4j, Firecrawl, embedding, reranking, routing, and security integrations;
  - expose typed request/result contracts and serialize only at the MCP boundary;
  - avoid duplicate MCP-specific datastore clients unless the MCP SDK technically requires a narrow transport adapter;
  - never become a second RAG “brain” or bypass canonical RAG security and citation behavior.

  Replace zero-byte MCP placeholders as their corresponding implementation phases begin. Their current nominal health scores are not meaningful because they contain no implementation.

  ### 18. Run the final MCP-readiness verification gate

  Run, in order:

  1. Ruff safe fixes and formatting.
  2. MyPy across the project.
  3. Full pytest suite with configured coverage.
  4. RAG-specific branch and deterministic behavior tests.
  5. Database migration contract tests against blank and upgraded PostgreSQL schemas.
  6. Live PostgreSQL, Qdrant, Neo4j, BGE-M3, BGE reranker, Firecrawl, and Ollama checks.
  7. Controlled Qdrant rebuild verification.
  8. Repowise health and blast-radius reassessment.
  9. Graphify update and scoped architecture queries.

  Acceptance criteria:

  - project coverage remains at or above the configured 75% gate;
  - refactored RAG hotspots have at least 80% targeted line coverage plus meaningful branch tests;
  - no migration/model divergence;
  - no import-time infrastructure initialization;
  - no manually composed CLI RAG stack;
  - no domain timestamps fabricated from Unix epoch;
  - no important query audit values hidden only in generic metadata;
  - no automatic destructive Qdrant recreation;
  - MCP plans contain no parallel datastore or retrieval architecture;
  - all live service readiness checks pass.

  ## Public Contract Changes

  - BacktestMetricRecord.recorded_at
  - BacktestArtifactRecord.generated_at
  - Expanded RagQueryLogRecord audit fields
  - Typed model-execution persistence representation
  - Typed RAG projection-readiness result
  - Focused RAG operations service interfaces
  - Canonical Dishka RAG infrastructure and application providers

  All new internal contracts will use frozen, slotted dataclasses or equivalent strongly typed models. Dictionaries remain limited to PostgreSQL JSONB, telemetry, MCP serialization, and other system boundaries.

  ## Assumptions and Decisions

  - Targeted core bootstrap and persistence changes are authorized.
  - PostgreSQL remains the canonical RAG system of record.
  - Qdrant and Neo4j remain rebuildable projections.
  - Model executions use a first-class JSONB column plus queryable scalar audit columns; no child table is introduced in this phase.
  - The live legacy Qdrant collection will be rebuilt through an explicit confirmation gate before MCP implementation.
  - Existing ranking, routing, CRAG, Self-RAG, security, and generation policies will not be behaviorally redesigned during stabilization.
  - Each implementation step should be completed and reviewed independently before starting the next step.

## Step Results

### Step 1 — Establish the stabilization baseline — Completed 2026-06-25

- **Repository state before execution:** branch `main`; pre-existing `NOTES.md` modification was left untouched. The stabilization plan file was untracked when Step 1 began.
- **Repowise baseline:** index age was 0 days. The principal health and hotspot results were:
  - `application/rag/rag_retriever.py`: health **4.40**, hotspot **98%**, increasing/churn-heavy; high co-change scatter and filter complexity.
  - `application/rag/rag_operations.py`: health **4.68**, hotspot **96%**, increasing/churn-heavy; `RagOperationsService` remains a god class and `_load_ingestion_source` has CCN 33.
  - `core/storage/persistence/repositories/postgres_rag_persistence_repository.py`: health **5.30**, hotspot **96%**, increasing/churn-heavy; high co-change scatter.
  - `application/rag/graphs/rag_service_graph.py`: health **6.74**, hotspot **92%**; routing and post-processing policy complexity remains bounded for Step 12.
  - `application/rag/query_routing_service.py`: health **7.59**, hotspot **94%**; structurally acceptable but churn-heavy.
  - `application/rag/rag_service.py`: health **8.65**, hotspot **88%**; structurally healthy and should not receive a broad refactor.
  - `application/rag/curated_rag_document_builder.py`: health **4.65**, hotspot **99%**; critical churn and a large `persist_source` method.
- **Deterministic RAG verification:** **246 passed**, 3 dependency deprecation warnings. The suite covered application RAG services, graph, routing, retrieval, security, generation, quality, structured sources, CLI, providers, clients, persistence contracts/repository, model configuration, research node, and RAG telemetry.
- **Live integration verification:** PostgreSQL, Qdrant, Neo4j, BGE reranker, and Ollama ports were reachable. Live RAG integration tests completed with **3 passed**, 2 SWIG dependency warnings.
- **Migration verification:** PostgreSQL migration contracts completed with **4 passed**, including single-head, blank upgrade, upgrade/downgrade consistency, and ORM/DDL parity. Five Alembic `path_separator` deprecation warnings were reported; these are non-blocking configuration debt.
- **Static verification:** Ruff check passed; Ruff formatting check reported all **1,021 files** formatted; MyPy reported no issues in **1,018 source files**.
- **Targeted line coverage:** selected RAG tests produced the following hotspot coverage:
  - RAG graph: **97.06%**
  - Query routing service: **98.73%**
  - Curated document builder: **89.92%**
  - PostgreSQL RAG repository: **89.59%**
  - RAG retriever: **83.67%**
  - RAG service: **83.18%**
  - RAG operations: **58.52%**
- **Coverage interpretation:** the selected stabilization run reports **55%** across the globally configured project source set because it intentionally executed only RAG-focused tests. It is not a project-wide coverage result. The earlier **27.6%** PostgreSQL RAG repository observation was caused by a selected run that omitted its focused repository tests; the corrected targeted baseline is **89.59%**.
- **Baseline acceptance criteria locked for the remaining plan:** no RAG regressions; clean Ruff and MyPy; migration/model parity; successful live PostgreSQL, Qdrant, Neo4j, embedding/reranker readiness checks; project-wide coverage at or above the configured 75% gate at the final verification step; targeted tests for refactored hotspots; and no newly introduced high-risk Repowise findings.
- **Production changes:** none. Step 1 changed only this plan documentation.


### Step 2 — Remove eager RAG package import side effects — Completed 2026-06-25

- **Package boundary cleanup:** reduced `application.rag` from a broad implementation re-export surface to the five lightweight public domain contracts `RagRequest`, `RagResult`, `RagRetrievedContext`, `RagRetrievalFilters`, and `RagSource`.
- **Infrastructure package isolation:** removed all eager implementation exports from `integration.clients.rag` and `integration.providers.rag`. Their package initializers now contain no client/provider imports, so importing the package does not initialize vendor integrations or load their dependency trees.
- **Direct imports:** updated production and test consumers to import concrete services, clients, providers, protocols, and models from their defining modules. A repository-wide Python search confirms there are no remaining aggregate imports from the three changed package initializers.
- **Regression coverage:** added subprocess-based package-isolation tests that inspect a fresh interpreter. They verify the intentional application contract surface, verify that integration package imports load no child implementation modules, and reject import-time loading of Firecrawl, HTTPX, Neo4j, NumPy, Ollama, or Qdrant.
- **Import behavior verified:** `application.rag` now loads only its contract/model children and no forbidden infrastructure dependency. `integration.clients.rag` and `integration.providers.rag` load no package children and no forbidden dependency.
- **Pytest-cov collection regression:** the previously problematic combined RAG collection completed successfully with **169 tests collected** and did not reproduce the NumPy “module loaded more than once” failure. Remaining SWIG warnings originate from tests that intentionally import Qdrant dependencies, not package initialization.
- **Focused deterministic verification:** **248 passed**, with 3 third-party deprecation warnings.
- **Live RAG verification:** **3 passed** against the running RAG infrastructure.
- **Static verification:** Ruff check passed; Ruff formatting check reported all **1,022 files** formatted; MyPy reported no issues in **1,019 source files**; `git diff --check` passed.
- **Architecture/telemetry impact:** this step changes import topology only. It introduces no execution path, provider call, datastore access, or concurrency and therefore requires no new telemetry instrumentation.
- **Graph maintenance:** refreshed the Graphify AST graph after the import-topology changes. `graphify-out/GRAPH_REPORT.md` was regenerated; visualization generation was skipped because the graph contains 16,257 nodes, above the configured 10,000-node HTML limit.
- **Unrelated worktree state:** the pre-existing `NOTES.md` modification remains untouched.

### Step 3 — Promote backtest timestamps to domain fields — Completed 2026-06-25

- **Typed domain contracts:** added required timezone-aware `BacktestMetricRecord.recorded_at` and `BacktestArtifactRecord.generated_at` fields. Both records reject naive datetimes instead of silently normalizing or fabricating timestamps.
- **New-record timestamp source:** the canonical backtest persistence mapper now assigns the parent `BacktestResult.completed_at` to every metric and artifact before persistence. No database default or Unix-epoch fallback is used for new records.
- **Persistence coverage:** added non-null `TIMESTAMP WITH TIME ZONE` ORM columns, serializer round-trip mappings, and PostgreSQL upsert updates for both fields.
- **RAG structured-source adoption:** backtest metric and artifact source specifications now select `recorded_at` and `generated_at` as their typed timestamp attributes. The broader generic metadata/epoch fallback remains intentionally unchanged until Step 4.
- **Schema migration:** added linear Alembic revision `e5f6a7b8c9d0`, which backfills each timestamp using the approved precedence: valid legacy `metadata.timestamp`, valid legacy `metadata.created_at`, parent `backtest_runs.completed_at`, then the row database `created_at`. The columns become non-null only after the backfill.
- **Migration safety:** invalid legacy timestamp strings are ignored using PostgreSQL input validation rather than failing the migration. The downgrade removes only the two newly introduced columns.
- **Regression coverage:** added contract tests for timezone awareness, ORM schema tests for non-null timezone columns without server defaults, mapper assertions, repository/test-factory updates, and a live migration test covering legacy timestamp, legacy created-at, invalid metadata, and parent-completion precedence for both metrics and artifacts.
- **Focused verification:** **27 passed** across backtest persistence contracts, mapper/service behavior, repository mappings, ORM definitions, and structured RAG source adapters.
- **Live PostgreSQL migration verification:** **5 passed**, covering a single migration head, blank-database upgrade, upgrade/downgrade consistency, ORM/DDL parity, and the new timestamp backfill contract. Six existing Alembic `path_separator` deprecation warnings remain non-blocking configuration debt.
- **Static verification:** final required sequence passed: Ruff safe fixes, Ruff formatting (**1,025 files unchanged**), and MyPy (**1,022 source files**, no issues). `git diff --check` also passed before documentation was appended.
- **Risk review:** Repowise reported no predicted breakages, no missing historical co-changes, and an overall changed-file risk score of **0.43**. The touched persistence files remain churn-heavy but structurally healthy; focused tests were added even though the current Repowise index still reports some new files/symbols as test gaps.
- **Telemetry review:** this step adds immutable data fields and persistence mappings but no new long-running operation, provider call, concurrency boundary, or datastore interaction path; existing repository telemetry remains the canonical instrumentation.
- **Graph maintenance:** refreshed the Graphify AST graph after the schema and contract changes: **16,274 nodes**, **66,212 edges**, and **651 communities**. HTML visualization was skipped at the configured 10,000-node limit.
- **Unrelated worktree state:** the pre-existing `NOTES.md` modification remains untouched.

### Step 4 — Remove backtest timestamp metadata dependence — Completed 2026-06-25

- **Canonical timestamp selection:** `structured_source_timestamp()` now reads only the timestamp attribute declared by the typed `StructuredSourceSpec`. It no longer probes generic `metadata.timestamp` or `metadata.created_at` values for any structured source.
- **No fabricated timestamp:** removed the Unix-epoch fallback. A missing or non-datetime domain value now raises an explicit `ValueError` identifying the record class and required field; a naive datetime raises an explicit timezone-awareness validation error.
- **Backtest isolation:** backtest metrics and artifacts continue to use the first-class `recorded_at` and `generated_at` fields introduced in Step 3. Tests deliberately supply conflicting 1970 metadata values and confirm those values cannot influence RAG document, chunk, or embedding-job timestamps.
- **Presentation/serialization separation:** structured chunk construction resolves the domain timestamp once, then serializes it independently into canonical `created_at` and `as_of_date` boundary metadata. Timestamp-selection policy remains centralized in `structured_source_timestamp()`.
- **Deterministic recency coverage:** every structured-source fixture now verifies that the RAG document `generated_at`, each chunk `created_at`/`as_of_date`, and each embedding job `queued_at` exactly preserve the source domain timestamp.
- **Temporal-filtering coverage:** added a public `RagRetriever` test with early- and late-June chunks. A bounded June 15–30 retrieval deterministically returns only the June 20 source, validating the canonical `as_of_date` boundary behavior.
- **Validation coverage:** added a corrupted-record regression test proving that absent first-class timestamp data fails validation even when legacy timestamp metadata is present; it cannot silently fall back to metadata or January 1, 1970.
- **Focused verification:** **39 passed** across structured-source construction, timestamp validation, document building, embedding-job timestamps, and temporal retrieval.
- **Broader RAG verification:** the complete `tests/unit/application/rag` suite completed with **129 passed**.
- **Static verification:** final required sequence passed: Ruff safe fixes, Ruff formatting (**1,025 files unchanged**), and MyPy (**1,022 source files**, no issues). `git diff --check` passed.
- **Risk review:** Repowise reported no predicted breakages, no missing historical co-changes, no test gaps, and an overall changed-file risk score of **0.23**. The production target remains churn-heavy but has a **9.12** health score.
- **Telemetry review:** the change tightens synchronous timestamp validation and boundary serialization only. It introduces no provider call, database operation, concurrency boundary, or long-running path requiring additional telemetry.
- **External services:** no PostgreSQL, Qdrant, Neo4j, reranker, embedding, or Ollama service was required for this deterministic unit-level step.
- **Graph maintenance:** refreshed Graphify after the timestamp-policy changes: **16,276 nodes**, **66,227 edges**, and **648 communities**. HTML visualization was skipped at the configured 10,000-node limit.
- **Unrelated worktree state:** the pre-existing `NOTES.md` modification remains untouched.

### Step 5 — Promote important RAG query audit data to first-class persistence fields — Completed 2026-06-25

- **Typed persistence contract:** introduced frozen, slotted `RagQueryModelExecutionRecord` and `RagQueryReflectionScores` value objects and extended `RagQueryLogRecord` with first-class `model_executions`, `context_count`, `citation_count`, `grounding_score`, `utility_score`, `injection_detected`, `reflection_scores`, and `corrective_actions` fields.
- **Bounded model history:** model executions preserve their input order and are limited to **32 records per query log**. Contract validation rejects invalid mappings, negative counts or durations, blank required identifiers/actions, and quality/reflection scores outside the inclusive `[0, 1]` range.
- **ORM schema definition:** added JSONB, integer, float, and boolean mappings with non-null defaults where required. Added ORM check constraints for non-negative counts and bounded quality scores. This step intentionally defines the target ORM schema without adding the Alembic migration, which is owned by Step 6.
- **Boundary serialization:** updated the RAG persistence serializer to round-trip all new typed fields through JSONB/scalar database values. An empty persisted reflection object is restored as `None`, while populated scores are reconstructed as the typed reflection value object.
- **Repository persistence:** extended PostgreSQL query-log upserts so every promoted audit field is updated on conflict rather than remaining stale in generic metadata.
- **Application mapping:** `RagService` now promotes model execution records, context/citation counts, grounding and utility scores, injection detection, reflection scores, and corrective actions into the typed query-log record. Result model executions take precedence over request metadata, with request metadata retained as a compatibility input only at this ingestion boundary.
- **Metadata policy:** removed promoted audit values from answer/query debug metadata so important operational and quality data is not duplicated or hidden in the generic metadata bag. Remaining metadata is limited to optional route, error, and sanitized debugging information.
- **Focused verification:** **58 passed** across RAG persistence contracts, ORM definitions, serializer mappings, repository upserts, and `RagService` persistence behavior.
- **Broader regression verification:** **179 passed** across the broader RAG and persistence suites.
- **Static verification:** final required sequence passed: Ruff safe fixes, Ruff formatting (**1,025 files unchanged**), and MyPy (**1,022 source files**, no issues). `git diff --check` passed before this result was appended.
- **Risk review:** Repowise confirms the changed persistence files remain high-churn hotspots (`rag_persistence_models.py` 98%, ORM model 96%, repository 96%, serializer 80%, and `RagService` 88%). No historical co-change partners or security findings were reported. The risk was contained through additive typed fields, direct serializer/repository mappings, and focused contract/round-trip tests rather than a broad hotspot refactor. Repowise's generic blast-radius warning includes package initializers and indirect CLI consumers, but the changed public behavior is confined to query-log persistence and is covered by the broader regression suite.
- **Telemetry review:** no new provider call, datastore access path, concurrency boundary, or long-running operation was introduced. Existing `RagService` persistence telemetry continues to cover the query-log writes.
- **External services:** no PostgreSQL, Qdrant, Neo4j, reranker, embedding, Firecrawl, or Ollama service was required for this contract-level step.
- **Deferred to Step 6:** create the Alembic migration, backfill existing rows with safe defaults, add approved indexes, run ORM/DDL parity, and verify the migration against live PostgreSQL.
- **Graph maintenance:** refreshed Graphify after the contract and persistence changes: **16,306 nodes**, **66,353 edges**, and **639 communities**. HTML visualization was skipped at the configured 10,000-node limit.
- **Unrelated worktree state:** the pre-existing `NOTES.md` modification remains untouched.

### Step 6 — Migrate and backfill query-log audit fields — Completed 2026-06-25

- **Linear schema migration:** added Alembic revision `f6a7b8c9d0e1`, directly following the Step 3 backtest timestamp revision `e5f6a7b8c9d0` and preserving a single migration head.
- **First-class columns:** the migration adds `model_executions`, `context_count`, `citation_count`, `grounding_score`, `utility_score`, `injection_detected`, `reflection_scores`, and `corrective_actions` to `rag_query_logs`, with the same nullability and server defaults as the canonical ORM model.
- **Safe metadata backfill:** existing contractual values are promoted from JSONB metadata with explicit JSON-type, integer-range, non-negative-count, and score-range checks. Ordered model executions are capped at the domain limit of **32** during migration. Malformed legacy values receive the canonical empty, zero, false, or null value rather than causing migration failure.
- **Metadata cleanup:** all eight promoted contractual keys are removed from generic metadata after migration while unrelated debugging annotations are preserved.
- **Database constraints:** added checks for bounded array-shaped model executions, non-negative counts, `[0, 1]` score ranges, object-shaped reflection scores, and array-shaped corrective actions. The ORM declares the same constraints for migration parity.
- **Operational indexes:** added three narrowly scoped partial indexes: injection-detected rows only, non-null grounding scores, and non-null utility scores. No JSONB-wide or low-value count indexes were introduced.
- **Downgrade contract:** the migration drops only its three indexes, seven constraints, and eight columns in dependency-safe order. The full pytest-alembic upgrade/downgrade consistency test passed.
- **Targeted migration coverage:** added a data-migration contract test that verifies ordered execution truncation, all promoted values, malformed-value defaults, unrelated metadata preservation, contractual-key removal, and creation of the three operational indexes.
- **PostgreSQL readiness:** connected successfully to PostgreSQL **16.14** as database/user `polaris` before migration execution.
- **Migration verification:** the live database began at revision `d4e5f6a7b8c9`, upgraded through `e5f6a7b8c9d0` and `f6a7b8c9d0e1`, and now reports `f6a7b8c9d0e1 (head)`. `alembic check` reports **No new upgrade operations detected**.
- **Live schema verification:** confirmed all eight columns, their nullability/defaults, and the exact partial-index predicates in the live `public.rag_query_logs` table. The live table contained zero rows, so historical-value behavior was verified deterministically in the isolated PostgreSQL migration schema.
- **Database contract tests:** **6 passed**, covering single head, blank upgrade, upgrade/downgrade consistency, ORM/DDL parity, backtest timestamp backfill, and RAG query-audit backfill. Seven existing Alembic `path_separator` deprecation warnings remain non-blocking configuration debt.
- **Focused regressions:** **10 ORM model tests passed** and the full Step 5 query-audit contract/repository/service selection completed with **58 passed**.
- **Static verification:** final required sequence passed: Ruff safe fixes, Ruff formatting (**1,026 files unchanged**), and MyPy (**1,023 source files**, no issues). `git diff --check` passed before this result was appended.
- **Risk review:** Repowise continues to classify the RAG ORM as a 96% churn hotspot, but reports no historical co-change omissions or security findings. Its generic new-file test-gap marker cannot associate an uncommitted migration with tests; the migration is directly exercised by the new live PostgreSQL data-migration contract plus the blank-upgrade, downgrade, and ORM-parity tests.
- **Telemetry review:** schema migration execution uses the existing Alembic/database operational boundary and introduces no application runtime path, provider call, or asynchronous concurrency requiring new telemetry instrumentation.
- **External services:** PostgreSQL was required and verified. Qdrant, Neo4j, BGE-M3, BGE reranker, Firecrawl, and Ollama were not required for this step.
- **Graph maintenance:** refreshed Graphify after the migration and ORM changes: **16,310 nodes**, **66,359 edges**, and **652 communities**. HTML visualization was skipped at the configured 10,000-node limit.
- **Unrelated worktree state:** the pre-existing `NOTES.md` modification remains untouched.

### Step 7 — Create canonical RAG dependency-injection composition — Completed 2026-06-25

- **Canonical async composition root:** added `get_async_di_container()` beside the existing synchronous container entry point. It composes the platform providers through the existing `build_async_app_container()` facility and registers the RAG provider stack without changing runtime-engine or runtime-node contracts.
- **Focused provider modules:** added dedicated Dishka providers for request-scoped PostgreSQL RAG persistence and application services, plus application-scoped RAG vendor clients and normalized integration providers. This keeps RAG wiring out of the already churn-heavy general integration provider module.
- **Shared scopes:** `AsyncSession`, the canonical RAG repository, structured-source repositories, `RagService`, and `RagOperationsService` are request-scoped. BGE-M3, BGE reranker, Qdrant, Neo4j, Firecrawl, Ollama-backed RAG providers, `ObservabilityManager`, application telemetry, and integration telemetry are application-scoped and shared across request scopes.
- **Lifecycle ownership:** the request-scoped SQLAlchemy session is closed by its Dishka async resource provider. The application-scoped Neo4j client is also an async resource and closes once when the root container closes. Qdrant and remaining client lifecycle cleanup stays explicitly assigned to Step 8, where the CLI manual composition is removed.
- **Application service wiring:** the canonical container now resolves the complete graph-backed `RagService` and operational `RagOperationsService`, including ingestion, embedding jobs, graph projection, hybrid retrieval, reranking, routing, quality evaluation, secure generation, structured retrieval, projection configuration, and shared telemetry.
- **Bootstrap simplification:** split provider-profile selection out of the previous low-health `get_di_container()` method into typed helpers and replaced hard-coded backtest provider strings with the canonical `Settings` constants. The synchronous application container retains its prior behavior; RAG providers are lazily imported only by the async composition path to avoid burdening non-RAG startup.
- **Container API support:** extended the existing sync and async application container builders with optional Dishka `context` and `skip_validation` arguments while preserving their defaults and existing callers.
- **Deterministic scope/lifecycle test:** added a composition test that substitutes the heavyweight BGE encoder and Neo4j driver, resolves both canonical RAG services without contacting external infrastructure, verifies one shared observability manager and datastore clients across request scopes, verifies new repositories/services per request scope, and confirms Neo4j closes exactly once.
- **Focused verification:** **151 passed** across all application RAG unit tests, the new canonical DI composition test, Dishka request/session/runtime-node scope tests, workflow DI execution, and bootstrap observability coverage.
- **Static verification:** final required sequence passed: Ruff safe fixes, Ruff formatting (**1,031 files unchanged**), and MyPy (**1,028 source files**, no issues). `git diff --check` passed.
- **Risk review:** Repowise reports no missing historical co-change partners or governance/security findings. `core/bootstrap/di_providers.py` remains a historically churn-heavy, low-health file in the current index, so the change reduced its active composition complexity through small selection/composition helpers rather than adding another monolithic branch tree. The indexed metrics do not yet reflect the uncommitted rewrite or its new direct test.
- **External services:** no PostgreSQL, Qdrant, Neo4j, BGE reranker, Firecrawl, or Ollama service was required; all composition verification was deterministic and avoided network/database operations.
- **Graph maintenance:** refreshed Graphify after the DI topology changes: **16,465 nodes**, **68,604 edges**, and **649 communities**. HTML visualization was skipped at the configured 10,000-node limit.
- **Unrelated worktree state:** the pre-existing `NOTES.md` modification remains untouched.

### Step 8 — Move RAG CLI execution onto canonical composition — Completed 2026-06-25

- **Manual composition removed:** deleted the CLI-owned construction of PostgreSQL repositories, RAG services, graph stages, Ollama providers, BGE embedding/reranking providers, Qdrant/Neo4j clients, Firecrawl fallback, projection configuration, and the one-off `_CliEmbeddingJobProcessor` from `interfaces/cli/services/rag_command_service.py`.
- **Canonical request resolution:** the default CLI service contexts now create the shared async Dishka application container from `get_async_di_container()`, enter one request scope, resolve either `RagService` or `RagOperationsService`, and close the request and root scopes in `finally`-safe order. Existing direct-service and context-factory injection seams remain available for deterministic tests.
- **Private telemetry runtime removed:** deleted `_RagTelemetryRuntime`. CLI commands now use the same application-scoped `ObservabilityManager`, `ApplicationRagTelemetry`, and integration telemetry composition as every other canonical consumer rather than creating a second telemetry stack per command.
- **Telemetry lifecycle ownership:** converted the Dishka observability provider into an application-scoped resource. Container shutdown now stops the Prometheus exporter, force-flushes telemetry, and shuts down telemetry sinks exactly once. OpenTelemetry and Prometheus provider tests verify container-owned shutdown behavior.
- **Qdrant lifecycle ownership:** added an explicit async `close()` contract to the Qdrant wrapper and changed the RAG client provider to an application-scoped async resource. The underlying `AsyncQdrantClient` now closes once when the root container closes, matching the existing Neo4j lifecycle.
- **Session lifecycle verification:** the canonical RAG composition test now substitutes tracked request-scoped sessions and proves that each request scope closes its SQLAlchemy session exactly once. The same test verifies that the shared Qdrant and Neo4j resources each close exactly once at root-container shutdown.
- **Remaining client inventory:** BGE-M3 owns an in-process encoder with no close contract; the BGE reranker uses a transient `httpx.AsyncClient` context per call when no injected client is supplied; Firecrawl's current async SDK surface exposes no lifecycle method used by this wrapper; and the Ollama wrapper uses non-persistent `requests` calls. No additional persistent RAG client lifecycle remained to transfer in this step.
- **Thin CLI boundary preserved:** Typer commands and rendering behavior were not redesigned. `polaris rag --help` succeeds and exposes the existing ask, ingest, embedding, graph, rebuild, and status commands without initializing external infrastructure merely to render help.
- **Focused lifecycle verification:** **34 passed** across RAG CLI delegation/rendering, canonical RAG composition, Qdrant wrapper lifecycle, and bootstrap observability lifecycle.
- **Broader RAG/bootstrap verification:** **199 passed** across application RAG, CLI, canonical bootstrap composition, RAG clients/providers, and bootstrap observability. A second transitive blast-radius suite covering governance, workflow provider control, Dishka workflow execution, all CLI unit tests, and bootstrap observability completed with **121 passed**.
- **Static verification:** the required sequence passed: Ruff safe fixes, Ruff formatting (**1,031 files unchanged**), and MyPy (**1,028 source files**, no issues). `git diff --check` passed.
- **Risk review:** Repowise continues to report the CLI service and workflow provider as churn-heavy historical hotspots and assigns a broad transitive risk signal to bootstrap consumers. The indexed CLI finding still references the deleted 99-line manual context, so it does not yet reflect this uncommitted simplification. No historical co-change omissions or security findings were reported; the identified governance, workflow, bootstrap, and CLI impact paths were exercised by the focused and transitive suites.
- **External services:** no PostgreSQL, Qdrant, Neo4j, BGE reranker, Firecrawl, or Ollama service was required. Lifecycle and composition behavior was verified with deterministic substitutes and without network or database operations.
- **Graph maintenance:** refreshed Graphify after the composition and lifecycle changes: **16,500 nodes**, **68,729 edges**, and **639 communities**. HTML visualization was skipped at the configured 10,000-node limit.
- **Unrelated worktree state:** the pre-existing `NOTES.md` modification remains untouched.

### Step 9 — Split RAG operations by use case — Completed 2026-06-25

- **Monolith removed:** deleted the 1,389-line `application/rag/rag_operations.py` implementation after migrating every production and test caller. A repository-wide search confirms there are no remaining references to `RagOperationsService`, its old module, or its old default CLI context. No compatibility wrapper was retained.
- **Focused application services:** introduced request-scoped `RagIngestionOperationsService`, `RagEmbeddingJobOperationsService`, `RagProjectionOperationsService`, and `RagStatusOperationsService`. Each service owns one operational use case and keeps its existing PostgreSQL, processor, projection, dry-run, confirmation, retry, and result semantics.
- **Typed operation contracts:** moved the immutable operation requests, results, details, and projection configuration into `rag_operation_models.py`, preserving strongly typed internal contracts and keeping dictionary serialization at boundaries.
- **Typed source loading:** replaced the monolith's source-table branch tree with `CuratedRagSourceLoader`, `CuratedRagSourceLoaderRegistry`, and nine repository-specific loaders for reports, agent signals, recommendations, macro, market, news, sentiment, portfolio, and backtests. The registry rejects duplicate source-table ownership and returns no source for an unregistered table.
- **Telemetry preserved:** added a shared `RagOperationTelemetry` boundary used by the focused write/processing services. Existing operation names, start/completion/failure events, durations, record counts, dry-run attributes, structured logging, and repository/provider telemetry remain intact; no parallel telemetry runtime was introduced.
- **Canonical composition:** updated Dishka wiring to compose the source-loader registry and all four focused services from the existing request-scoped repositories and application-scoped providers. PostgreSQL remains the canonical source of truth, and Qdrant/Neo4j remain rebuildable projections.
- **Thin CLI delegation:** updated `RagCommandService` so each command resolves only its relevant focused request-scoped service through canonical async composition. `polaris rag --help` succeeds and still exposes `ask`, `ingest`, `process-embeddings`, `process-graph`, `rebuild`, and `status`.
- **Transactional and lifecycle boundaries:** retained the existing request-scoped SQLAlchemy session/repository ownership and root-container client lifecycle. The split does not create a second transaction manager, datastore path, runtime, or composition root.
- **Focused regression coverage:** added registry routing, missing-loader, and duplicate-registration tests and updated operation, CLI, and canonical DI tests for the focused services. The immediate focused suite completed with **26 passed**.
- **Broader regression coverage:** application RAG, RAG CLI, core bootstrap, RAG client, and RAG provider unit suites completed with **188 passed** and only five existing third-party warnings.
- **Static verification:** the required final sequence passed: Ruff safe fixes, Ruff formatting (**1,038 files unchanged**), and MyPy (**1,035 source files**, no issues). `git diff --check` passed.
- **Duplication review:** exact-clone analysis improved slightly from **80 lines / 0.68%** before the refactor to **80 lines / 0.67%** after it, so the split introduced no exact copy-paste regression. Pylint's broader similarity detector still reports pre-existing model/serialization clones and conventional operation lifecycle similarities; these were not expanded into speculative abstractions during this surgical step.
- **Risk review:** Repowise reports no predicted breakages, no missing historical co-changes, no security findings, and an overall changed-file risk score of **0.37**. The CLI service remains a 99% churn hotspot but now has a **9.65** structural health score and direct tests. Repowise's health index still cites the deleted aggregate DI provider and cannot associate uncommitted new files with their tests; the focused and broader suites directly exercise those files.
- **External services:** no PostgreSQL, Qdrant, Neo4j, BGE reranker, Firecrawl, or Ollama service was required. This step verified composition and behavior with deterministic substitutes and did not perform live projection or ingestion operations.
- **Graph maintenance:** refreshed Graphify after the service and import-topology split: **16,632 nodes**, **70,163 edges**, and **678 communities**. HTML visualization was skipped at the configured 10,000-node limit.

### Step 10 — Simplify curated ingestion orchestration — Completed 2026-06-25

- **Bounded document construction:** extracted `CuratedRagDocumentFactory` from the churn-heavy ingestion module. It now owns typed report and agent-signal `RagDocumentRecord` construction, while `CuratedRagDocumentBuilder` remains responsible for dispatching curated source types and assembling documents with the existing record-aware chunk and embedding-job collaborators.
- **Atomic persistence collaborator:** added `CuratedRagBundlePersister`, which accepts one typed `RagPersistenceBundle` and delegates the complete document/chunk/job set to one `RagPersistenceRepository.persist_document()` call. PostgreSQL remains the sole transaction owner; no parallel transaction abstraction or core persistence contract was introduced.
- **Coordinator simplification:** reduced `CuratedRagIngestionService.persist_source()` from the indexed 114-line mixed-responsibility method to a 53-line sequencing method. Eligibility resolution, bundle construction telemetry, and atomic persistence telemetry are now bounded private stages while preserving the existing operation names and result behavior.
- **Canonical composition:** updated request-scoped Dishka wiring to compose the document factory, bundle builder, bundle persister, and ingestion coordinator explicitly. The service retains direct-construction defaults for focused tests without creating hidden global dependencies.
- **Idempotency:** deterministic document, chunk, and embedding-job IDs remain unchanged. A retry regression test runs the same curated source twice, verifies identical bundle IDs, and confirms the canonical record sets contain no duplicate documents, chunks, or jobs.
- **Transaction rollback:** strengthened the PostgreSQL repository test so failure on the second write of a document/chunk/job bundle proves the partial transaction is rolled back once, never committed, and does not proceed to later writes.
- **Direct collaborator coverage:** added focused tests for typed document construction and for forwarding the complete bundle through exactly one repository persistence call. This directly covers both new collaborators in addition to the existing ingestion tests.
- **Regression verification:** **168 passed** across all application RAG tests, PostgreSQL RAG repository tests, canonical RAG DI composition, and RAG CLI tests. Five existing third-party WebSockets/SWIG/Firecrawl warnings remain non-blocking.
- **Static verification:** final required sequence passed: Ruff safe fixes, Ruff formatting (**1,041 files unchanged**), and MyPy (**1,038 source files**, no issues). `git diff --check` passed.
- **Duplication review:** Pylint duplicate-code completed at **10.00/10**. Focused jscpd analysis retained the same single pre-existing structured-source clone while the duplicated-line ratio decreased from **1.11%** to **1.05%**; this step introduced no copy-paste regression.
- **Risk review:** Repowise continues to classify the original curated ingestion module as a 99% churn hotspot and its current health index still reports the pre-refactor 114-line method because the behavioral index has not incorporated the uncommitted extraction. No historical co-change omissions or security findings were reported. The new files initially appear as generic test gaps due to absent git metadata, but both have direct focused tests and are exercised by the broader suite.
- **Telemetry review:** existing `rag.ingestion.persist_source`, `rag.ingestion.eligibility`, `rag.ingestion.build_bundle`, and `rag.ingestion.persist_bundle` telemetry was preserved. No provider call, new datastore path, or asynchronous concurrency boundary was introduced.
- **Core architecture:** no `core/` production file was modified. Existing deterministic ID generation, typed persistence contracts, and PostgreSQL transaction ownership remain intact; only the existing core rollback test was strengthened.
- **External services:** no PostgreSQL, Qdrant, Neo4j, BGE reranker, embedding, Firecrawl, or Ollama service was required for this deterministic refactor.
- **Graph maintenance:** refreshed Graphify after the extraction: **16,680 nodes**, **70,645 edges**, and **664 communities**. HTML visualization was skipped at the configured 10,000-node limit.

### Step 11 — Decompose RagRetriever internally — Completed 2026-06-25

- **Public contract preserved:** `RagRetriever`, `RagRetrieverConfig`, `RagRetrievalResult`, constructor parameters, retrieval results, route behavior, ranking policy, and all existing telemetry operation names remain unchanged.
- **Filter and temporal policy extracted:** added `RagRetrievalFilterEvaluator` to build exact PostgreSQL/Qdrant boundary filters and evaluate tuple, optional, metadata, and as-of-range constraints. Date parsing, missing-date rejection, and request-level workflow/execution fallback semantics are unchanged.
- **Candidate collection extracted:** added `RagCandidateCollector` for canonical PostgreSQL lexical candidates, BGE-M3 dense/sparse query embedding, Qdrant hybrid search requests, and PostgreSQL rehydration of vector hits. Existing stage telemetry remains owned by `RagRetriever`, so no provider or datastore operation became unobserved.
- **Hybrid fusion extracted:** added `RagRetrievalFusion` for vector-score normalization, configured lexical/vector weighting, deterministic score/vector/lexical/chunk tie breaks, and the existing bounded rerank candidate pool. No reciprocal-rank or scoring-policy change was introduced.
- **Final context selection extracted:** added `RagContextSelector` for reranker invocation, fallback top-k selection, rank assignment, rerank score replacement, and preservation of the pre-rerank retrieval score in metadata.
- **Coordinator reduced:** `application/rag/rag_retriever.py` decreased from **937 lines to 554 lines** and now coordinates the existing observed stages rather than owning filter evaluation, candidate collection, fusion, and final selection implementations.
- **Deterministic behavior locked:** the original retriever suite passed before extraction (**7 passed**). New direct tests cover exact/in-memory filter splitting, temporal matching, vector normalization, deterministic hybrid tie breaks, rerank-pool bounds, candidate collection requests, fallback selection, and reranker metadata behavior.
- **Regression verification:** **159 passed** across all application RAG unit tests, canonical RAG DI composition, the RAG research node, and RAG CLI behavior. Five existing third-party WebSockets/SWIG/Firecrawl warnings remain non-blocking.
- **Static verification:** the required final sequence passed: Ruff safe fixes, Ruff formatting (**1,049 files unchanged**), and MyPy (**1,046 source files**, no issues). `git diff --check` passed.
- **Duplication review:** Pylint duplicate-code completed at **10.00/10** and focused jscpd analysis found **0 clones / 0.00% duplicated lines** across the decomposed production modules.
- **Risk review:** Repowise reports no predicted downstream breakage, no missing historical co-changes, no security findings, and an overall changed-file risk score of **0.27**. Its health details still reference the pre-extraction 937-line indexed source and mark uncommitted files as generic test gaps; all four collaborators have direct or focused integration coverage in this step.
- **Telemetry and architecture:** existing `rag.retrieval.*` start/completion/failure events, durations, attributes, structured logging, optional graph failure behavior, and canonical PostgreSQL/Qdrant/provider boundaries were preserved. No `core/` production file, DI contract, persistence schema, or public runtime contract was changed.
- **External services:** no PostgreSQL, Qdrant, Neo4j, BGE reranker, embedding, Firecrawl, or Ollama service was required; verification used deterministic substitutes.
- **Graph maintenance:** refreshed Graphify after the decomposition and tests: **16,792 nodes**, **71,323 edges**, and **662 communities**. HTML visualization was skipped at the configured 10,000-node limit.

### Step 12 — Isolate graph routing and post-processing policy — Completed 2026-06-25

- **Pure typed policy boundary:** added `RagGraphPolicy` with typed `RagSelectionRoute`, `RagCorrectiveRoute`, and `RagPostProcessingDecision` contracts. The component has no datastore, provider, telemetry, runtime, or asynchronous dependencies and deterministically owns only route selection and final-result safety policy.
- **Graph responsibility preserved:** `RagServiceGraph` continues to own LangGraph construction, asynchronous orchestration, state transitions, bounded corrective-loop execution, security-guard calls, generation/reflection calls, and graph-stage history. Its conditional-edge adapters now delegate decisions to the policy and return the existing route strings expected by LangGraph.
- **Contracts and behavior preserved:** `RagGraphState`, `RagResult`, route values, corrective actions, grounding/utility scores, model-execution audit metadata, web-fallback audit metadata, stage history, and fail-closed answer behavior remain unchanged. No compatibility layer or alternate graph/runtime path was introduced.
- **Post-processing isolation:** final reflection safety, context-injection attribution, quality scores, corrective actions, execution metadata, web-fallback counts, and completed/failed status selection now execute through one pure typed policy method instead of the graph node's former 60-line branch-heavy implementation.
- **Complexity reduction:** `rag_service_graph.py` decreased from **576 lines to 526 lines**. The formerly complex `_post_processing_safety` and `_route_after_crag` methods are now thin orchestration adapters; the extracted policy is **150 lines** and independently testable.
- **Direct policy coverage:** added deterministic tests for corrective rewrite routing, maximum-loop termination, low-quality context with no retained evidence, permitted web fallback, unsupported/injected Self-RAG rejection, successful supported synthesis, and all initial route-selection branches.
- **Graph regression coverage:** the existing graph suite continues to verify the actual corrective loop, explicit loop bound, disabled/enabled/empty web fallback, weak-context filtering, input/context/output injection handling, supported and unsupported reflection, direct-answer behavior, deep-research/HyDE behavior, and successful grounded generation.
- **Focused verification:** the policy and graph suites completed with **27 passed**. The broader application RAG, canonical RAG DI composition, and RAG CLI regression suite completed with **164 passed** and five existing third-party WebSockets/SWIG/Firecrawl warnings.
- **Static verification:** the required final sequence passed: Ruff safe fixes, Ruff formatting (**1,051 files unchanged**), and MyPy (**1,048 source files**, no issues). `git diff --check` passed before this result was appended.
- **Duplication review:** Pylint duplicate-code completed at **10.00/10** and focused jscpd analysis found **0 clones / 0.00% duplicated lines** across the graph, policy, and direct graph/policy tests.
- **Risk review:** Repowise reported no predicted downstream breakage, no missing historical co-changes, no security findings, and an overall changed-file risk score of **0.18**. Its health index still reports the pre-extraction complex graph methods and marks the uncommitted policy as lacking tests because the behavioral index has not incorporated the new files; the new policy has direct deterministic coverage and is exercised by the broader regression suite.
- **Telemetry and architecture:** no telemetry was moved into the pure policy. Existing observed security, routing-model, retrieval, quality, generation, provider, and persistence boundaries remain unchanged. No `core/` production file, persistence schema, DI contract, public graph state, or public result contract was modified.
- **External services:** no PostgreSQL, Qdrant, Neo4j, BGE reranker, embedding, Firecrawl, or Ollama service was required; all verification used deterministic substitutes.
- **Graph maintenance:** refreshed Graphify after the extraction and tests: **16,838 nodes**, **71,714 edges**, and **672 communities**. HTML visualization was skipped at the configured 10,000-node limit.

### Step 13 — Review remaining bounded complexity hotspots — Completed 2026-06-25

- **Disposition:** no production refactor was performed. The review found bounded complexity and recent churn, but not a responsibility or correctness failure strong enough to justify another extraction before readiness and end-to-end verification. This preserves the plan's rule not to refactor healthy modules merely because they are large or recently changed.
- **Graph entity extraction:** `RagGraphEntityExtractor.extract()` is the clearest remaining method-level hotspot at 133 NLOC and CCN 10. It nevertheless remains a pure, deterministic policy boundary with no provider, persistence, telemetry, runtime, or concurrency responsibility. Direct tests cover deterministic master entities, news themes, and risk constraints, and the graph-projection module reached **90%** focused line coverage. Retain it as-is for now. Reconsider decomposition only when another entity family is added, when source-specific branches require independent policy tests, or when the method exceeds the current bounded complexity without equivalent coverage.
- **Graph projection module organization:** `graph_projection.py` contains three related but distinct public responsibilities: deterministic entity extraction, projection-job orchestration, and graph retrieval. Repowise reports health **8.15**, hotspot **91%**, increasing/churn-heavy, with the extractor as its only high-severity size finding. Because the responsibilities already have explicit class boundaries and tests, a file-only split would improve navigation but not behavior, testability, coupling, or operational safety. Defer that organizational split until one of those classes requires substantive change; do not create compatibility modules.
- **Embedding-job processing:** `embedding_job_processor.py` has health **8.97**, maximum CCN **6**, and **90%** focused line coverage. Its 89-line `process_job()` method is a cohesive transaction-like application sequence: persist processing state, load the canonical PostgreSQL chunk, request the embedding, validate dimensions, upsert Qdrant, persist completion/retry state, and emit lifecycle telemetry. Splitting this sequence now would distribute one invariant across more collaborators without reducing policy complexity. Retain it intact; reassess only if batching becomes concurrent, retry policy becomes independently configurable, or another vector target needs a distinct projection strategy.
- **Structured-source rendering:** `curated_rag_rendering.py` has health **9.47**, maximum CCN **3**, and **95%** focused line coverage. Its renderer is long because it emits a complete human-readable signal document, not because it mixes infrastructure responsibilities. It preserves the full LLM response and performs only presentation-boundary formatting. Retain it as a focused renderer. Repowise's test-gap flag is contradicted by direct execution through the curated document-builder suite.
- **Structured-source registry and rendering:** `curated_rag_structured_sources.py` is large and churn-heavy, but remains structurally healthy at **9.12**, maximum CCN **8**, and **86%** focused line coverage. Most size comes from the typed, declarative `StructuredSourceSpec` registry for supported persistence records. The generic renderer is 76 NLOC with CCN 4 and operates only on those typed specifications. A future split into a source-spec registry and rendering module is reasonable only when independent ownership, plugin registration, or materially different rendering policies emerge; performing it now would be a navigation-only move across a newly stabilized contract.
- **Duplication validation:** Repowise's broad DRY biomarkers reported implausible 100% file duplication for several targets while identifying only 16–30-line worst clones. Independent exact-clone analysis is the controlling evidence: jscpd found **1 clone / 24 duplicated lines / 0.68%** across 3,542 lines in the six relevant RAG modules. The clone is the intentional overlap between `_render_value()` and `_stringify_value()` inside the structured-source renderer; their dictionary/dataclass behavior differs, so extracting a shared helper would add branching without a meaningful maintenance benefit. Pylint identified only the shared six-key regime vocabulary between graph projection and retrieval. That small declarative tuple does not justify a new cross-module utility or dependency.
- **Focused deterministic verification:** **41 passed** across embedding-job processing, graph projection/retrieval, structured-source construction, and curated document building.
- **Focused coverage:** the four reviewed modules achieved **88.90%** combined line coverage: curated rendering **95%**, embedding-job processing **90%**, graph projection **90%**, and structured sources **86%**. The configured 75% coverage threshold was satisfied.
- **Telemetry review:** embedding and graph job processors retain structured logging plus application RAG operation start/completion/failure telemetry around provider and datastore work. Entity extraction and rendering remain pure synchronous transformations and correctly do not create spans or metrics of their own. No unobserved external call, database query, or asynchronous fan-out was found.
- **Risk interpretation:** the principal risk is concentrated recent churn and single-owner history, not current structural failure. Repowise reported hotspot scores of **91%** for graph projection, **90%** for embedding jobs, **86%** for structured sources, and **57%** for curated rendering, with no security signals or historical co-change partners. Additional refactoring during the same stabilization window would increase rather than reduce near-term change risk.
- **External services:** no PostgreSQL, Qdrant, Neo4j, reranker, embedding, Firecrawl, or Ollama service was required for this deterministic review.
- **Production changes:** none. Step 13 changed only this plan documentation and intentionally leaves the reviewed production contracts unchanged.

### Step 14 — Add typed projection readiness diagnostics — Completed 2026-06-25

- **Typed readiness contract:** added frozen, slotted application models for canonical PostgreSQL readiness, Qdrant projection readiness, Neo4j projection readiness, embedding/reranker model readiness, configuration, and the aggregate result. Readiness data is carried in explicit fields rather than generic metadata.
- **Canonical PostgreSQL counts:** added `RagCanonicalRecordCounts` and a repository contract/implementation that reports document, chunk, embedding-job, and graph-job counts directly from PostgreSQL. The status service also reports pending, retryable, and failed embedding jobs using the canonical typed job records.
- **Non-mutating Qdrant inspection:** added client and provider inspection contracts that report collection existence, named dense/sparse vector compatibility, configured and actual dense-vector dimensions, point count, collection status, and health without creating, deleting, or rebuilding a collection.
- **Neo4j and model readiness:** the application status operation now checks the existing telemetry-wrapped Neo4j projection status, performs a bounded embedding probe with dimension validation, and performs a bounded reranker probe. Each dependency is evaluated independently so one unavailable projection or model does not hide the remaining diagnostics.
- **Fail-visible status behavior:** dependency failures are captured as typed error fields and produce a complete `degraded` result instead of suppressing output or aborting the command. The aggregate result is `ready` only when PostgreSQL, Qdrant, Neo4j, embedding, and reranking dependencies all satisfy their explicit readiness contracts.
- **Canonical composition:** updated request-scoped RAG DI wiring to inject the repository, projection providers, model providers, configured collection/vector dimensions, configured model names, and shared `ApplicationRagTelemetry` into the focused status operation. No parallel composition root or telemetry runtime was introduced.
- **Professional CLI output:** `polaris rag status` now renders sectioned PostgreSQL, Qdrant, Neo4j, and model-dependency diagnostics plus a summary. A degraded result remains fully rendered and exits nonzero so both humans and automation can detect the failure.
- **Telemetry:** the status operation emits the existing application RAG start/completion lifecycle telemetry. Qdrant, Neo4j, embedding, and reranker calls continue through their canonical telemetry-wrapped provider boundaries; caught failures are logged with dependency context.
- **Core contract rationale:** the only core production change is the narrowly required read-only PostgreSQL count contract and typed count value object. This is necessary because canonical record counts belong to the persistence boundary and must not be reconstructed through application-side list loading or raw SQL outside the repository.
- **Deterministic coverage:** added direct status-service tests for a fully ready platform and partial/degraded dependency failure, plus client/provider tests proving Qdrant inspection is observational. Repository, DI, CLI rendering, and protocol-fake coverage were updated for the typed contracts.
- **Regression verification:** **208 passed** across application RAG, persistence eligibility, PostgreSQL RAG repository/readiness, Qdrant client/provider, RAG CLI, and canonical RAG DI composition. Five existing third-party WebSockets/SWIG/Firecrawl warnings remain non-blocking.
- **Static verification:** the required final sequence passed: Ruff safe fixes, Ruff formatting (**1,052 files unchanged**), and MyPy (**1,049 source files**, no issues). `git diff --check` passed.
- **Risk review:** Repowise reports no predicted breakage, missing historical co-changes, governance findings, or security findings, with an overall changed-file risk score of **0.40**. The CLI service remains a 99% churn hotspot and RAG DI remains a 77% churn hotspot; the change was kept surgical and both paths are exercised by direct CLI/status and composition tests. Repowise's generic uncommitted-file test-gap markers are contradicted by those direct tests.
- **External services:** no live PostgreSQL, Qdrant, Neo4j, embedding, reranker, Firecrawl, or Ollama service was required for this deterministic implementation step. Running `polaris rag status` against the real platform requires PostgreSQL, Qdrant, Neo4j, the configured embedding model, and the configured BGE reranker to be available.
- **Graph maintenance:** refreshed Graphify after the readiness changes; all **1,050** indexed code files were processed and no additional code-graph topology changes were detected.

### Step 15 — Implement the controlled Qdrant rebuild gate — Completed 2026-06-25

- **Fail-closed preflight:** the Qdrant rebuild operation now verifies canonical PostgreSQL document/chunk counts, one unique Qdrant embedding-job source per canonical chunk, referenced chunk existence, job/chunk document consistency, referenced document existence, and complete document reachability before any destructive projection action is permitted.
- **Typed canonical snapshot:** preflight captures the full immutable `RagDocumentRecord` and `RagChunkRecord` sets reachable from canonical embedding jobs, not only aggregate counts. After rebuilding, the operation reloads and compares those typed records exactly, so deleted or content-mutated PostgreSQL documents/chunks fail the rebuild even when row counts remain unchanged.
- **Explicit destructive gate:** a normal or dry-run request performs inspection only and returns concrete remediation for an absent collection, legacy unnamed/incomplete vectors, incompatible dimensions, or an existing compatible projection. Destructive recreation requires the existing explicit `--confirm-delete` CLI flag; no startup path silently deletes or recreates Qdrant state.
- **Scoped projection recreation:** execution recreates only the configured Qdrant collection and immediately verifies that it exists, is healthy and empty, uses the required named dense and sparse vector schema, and has the configured dense-vector dimension before repopulation begins.
- **Canonical repopulation:** the operation deterministically requeues exactly one current-model Qdrant embedding job per canonical PostgreSQL chunk and processes those jobs through the existing canonical `EmbeddingJobProcessor`; no parallel embedding or datastore path was introduced.
- **Post-rebuild verification:** success requires unchanged PostgreSQL document/chunk counts, exact equality of the captured typed documents/chunks, zero failed embedding jobs, a healthy named-vector collection with compatible dimensions, and a Qdrant point count equal to the canonical PostgreSQL chunk count.
- **Clear client remediation:** Qdrant collection validation now reports that legacy unnamed vectors, missing named dense/sparse vectors, and dimension mismatches require an explicit projection rebuild rather than implying automatic startup repair.
- **Telemetry:** rebuild start/completion/failure events include projection and collection identity, duration, PostgreSQL before/after counts, requeued/completed/failed job counts, expected/actual Qdrant points, named-vector readiness, vector compatibility, and PostgreSQL source-of-truth attribution. Failure telemetry now accepts the same typed operation details as successful lifecycle events.
- **Canonical DI:** request-scoped RAG composition injects the existing `EmbeddingJobProcessor` into `RagProjectionOperationsService`; no alternate composition root, runtime, or telemetry stack was created.
- **Deterministic coverage:** added tests for legacy-schema dry runs, incomplete canonical job coverage, successful recreate/requeue/process/verify behavior, canonical chunk mutation detection, incomplete projection population, fail-closed Qdrant startup validation, telemetry details/duration, and CLI confirmation forwarding.
- **Regression verification:** **218 passed** across all application RAG unit tests, RAG clients/providers, RAG CLI command behavior, and canonical RAG DI composition. Five existing third-party WebSockets/SWIG/Firecrawl warnings remain non-blocking.
- **Static verification:** the required final sequence passed: Ruff safe fixes, Ruff formatting (**1,052 files unchanged**), and MyPy (**1,049 source files**, no issues). `git diff --check` passed before this result was appended.
- **Risk review:** Repowise reports no predicted breakages, no missing historical co-changes, no security findings, and an overall changed-file risk score of **0.23**. Qdrant client, RAG DI, and related tests remain churn-heavy but structurally healthy. Its generic test-gap markers for the uncommitted projection and telemetry modules are contradicted by direct operation/telemetry tests and the broader 218-test regression suite.
- **External services:** no live PostgreSQL, Qdrant, Neo4j, embedding, reranker, Firecrawl, or Ollama service was required. A destructive live Qdrant rebuild was intentionally not executed; the gate was verified with deterministic fakes that model schema, recreation, job processing, point counts, and canonical-record mutation.
- **Graph maintenance:** refreshed Graphify after the final rebuild-gate changes: **16,991 nodes**, **73,042 edges**, and **656 communities**. HTML visualization was skipped at the configured 10,000-node limit.

### Step 16 — Remove only verified dead or duplicate code — Completed 2026-06-25

- **Verified dead-code removal:** removed `vector_search_result_from_mapping()` from `integration/providers/rag/vector_index_models.py` only after exact repository search, Graphify topology, git-history inspection, and Repowise analysis found no production or test caller. The helper had been introduced with the initial RAG vector models but was never adopted by a downstream boundary.
- **Private orphan cleanup:** removed the helper's now-unreachable `_float_from_payload()`, `_required_str()`, and `_json_object_from_payload()` functions plus the unused `Mapping` import. The production change is a net deletion of **65 lines** and introduces no replacement abstraction or compatibility layer.
- **Conservative unused-export review:** retained the RAG-local protocol classes reported by static export analysis because exact source references show they remain active constructor and typing contracts inside their defining modules. Also retained other public helpers, including `build_chunks()`, because an unused-export signal alone is insufficient proof that a public contract is safe to delete.
- **Duplicate-code review:** ran both required detectors before considering extraction. Pylint completed at **9.93/10**. jscpd reported **14 clones / 217 duplicated lines / 1.55%** across 14,005 RAG production lines, compared with the pre-removal **14 clones / 217 lines / 1.54%** across 14,070 lines. The unchanged clone count confirms the deleted helper was dead code rather than a meaningful shared implementation; the small remaining clones are bounded request/result serialization, lifecycle, provider, and source-vocabulary patterns whose extraction would increase coupling without solving a demonstrated defect.
- **No speculative refactor:** no shared helper was extracted, no local protocol was removed, and no adjacent RAG production module was modified. Repowise findings were treated as investigation leads rather than deletion authority, as required by the plan.
- **Focused verification:** **18 passed** across Qdrant vector-provider behavior, candidate collection, retrieval fusion, retriever orchestration, and embedding-job processing.
- **Broader regression verification:** **218 passed** across all application RAG tests, RAG clients/providers, canonical RAG DI composition, and RAG CLI behavior. Five existing third-party SWIG/WebSockets/Firecrawl warnings remain non-blocking.
- **Static verification:** the required sequence passed: Ruff safe fixes, Ruff formatting (**1,052 files unchanged**), and MyPy (**1,049 source files**, no issues). `git diff --check` passed before this result was appended.
- **Risk review:** Repowise reports no predicted breakages, no transitive affected files, no historical co-change omissions, and no security findings. It assigns the file a **0.51** risk score because its index labels the churn-heavy file as untested; direct vector-provider, retrieval, and embedding-processing regressions exercised every remaining live vector-model path during this step.
- **Telemetry and architecture:** the removed code was an unreachable pure mapping helper with no provider call, datastore operation, asynchronous work, or telemetry boundary. No telemetry instrumentation, core contract, persistence schema, DI wiring, or public runtime behavior changed.
- **External services:** no PostgreSQL, Qdrant, Neo4j, embedding, reranker, Firecrawl, or Ollama service was required; all verification was deterministic and local.
- **Graph maintenance:** refreshed Graphify after the deletion: **16,995 nodes**, **73,046 edges**, and **649 communities**. HTML visualization was skipped at the configured 10,000-node limit.

### Step 17 — Correct the MCP architecture plans before implementation — Completed 2026-06-25

- **Architecture correction applied:** updated `.agent/plans/plan_platform_mcp_server_master.md` with a superseding Codex Step 17 architecture section that defines the MCP server as a thin external transport boundary over canonical Polaris application services, not a datastore gateway or second RAG implementation.
- **Canonical composition rule:** the corrected MCP plan now requires every non-health MCP tool to resolve services through `get_async_di_container()` and a request scope, mirroring `interfaces/cli/services/rag_command_service.py`, before delegating to `RagService` or the focused RAG operation services.
- **Canonical service surface:** the corrected plan explicitly exposes only existing typed service capabilities: `RagService.run()`, `RagStatusOperationsService.status()`, `RagIngestionOperationsService.ingest()`, `RagEmbeddingJobOperationsService.process_embeddings()`, `RagProjectionOperationsService.process_graph()`, and `RagProjectionOperationsService.rebuild()`.
- **Parallel implementation blocked:** the master plan now forbids MCP-owned PostgreSQL, Qdrant, Neo4j, Firecrawl, embedding, reranking, SQL/Cypher, vector retrieval, fusion/ranking, CRAG, Self-RAG, security-brain, answer-generation, and LangGraph implementations. If a future MCP tool needs missing behavior, the behavior must first be implemented as a canonical application service and then exposed through MCP.
- **Phase plans corrected:** prepended superseding corrected sections to all ten MCP phase plans. Each phase now states its corrected role and marks the older direct-client/retrieval/graph/web/LangGraph content below as historical legacy draft material that must not be implemented where it conflicts with the corrected architecture.
- **Corrected phase map:** Phase 1 is transport skeleton and service context; Phase 2 wraps `RagService`; Phase 3 wraps readiness/status; Phase 4 wraps ingestion/embedding/graph operations; Phase 5 wraps the controlled projection rebuild gate; Phase 6 formalizes boundary serialization/tool catalog; Phase 7 adds transport validation/security hooks; Phase 8 adds MCP boundary observability; Phase 9 adds canonical-service integration/live tests; Phase 10 performs the final readiness gate and placeholder cleanup.
- **Legacy placeholder handling:** documented that zero-byte `mcp_server/clients/*` placeholders are legacy scaffolding and should not be populated. They may be removed when their corresponding corrected implementation phase begins.
- **Verification:** Graphify scoped query confirmed the canonical RAG topology is centered on `RagService`, focused RAG operation services, `RagServiceGraph`, `RagRetriever`, existing providers, and `ApplicationRagTelemetry`. Exact source inspection confirmed the CLI resolves RAG services through canonical Dishka request scopes. `git diff --check` passed after the documentation changes.
- **Code changes:** none. Step 17 modified only MCP planning documents and this stabilization plan. No tests, Ruff, MyPy, or Graphify update were required because no Python source changed in this step.

### Step 18 — Execute final stabilization readiness gate — Completed 2026-06-25

- **Scope completed:** ran the final post-RAG-v2 stabilization readiness gate across static analysis, deterministic RAG/unit coverage, full repository tests, live database migration checks, and live dependency readiness checks. This step also fixed one integration-wiring issue exposed by the full test suite rather than leaving the readiness gate red.
- **Integration fix:** added the missing `AlphaVantageEarningsClient` factory to `IntegrationClientsDIProvider`. `LiveEventsDIProvider` already required that client, and full pytest exposed the missing Dishka factory as a `NoFactoryError`. This is a canonical DI wiring fix, not a new runtime path.
- **Real-node workflow test fix:** updated `tests/integration/workflow/test_morning_report_real_nodes.py` to set `PROVIDER_PROFILE=backtest_synthetic` for the test environment. Without this, `build_cli_runtime_async()` applied the default/live provider profile and overwrote the individual backtest provider environment variables.
- **Static verification:** final required sequence passed after the fixes: Ruff safe fixes, Ruff formatting (**1,052 files unchanged**), and MyPy (**1,049 source files**, no issues). `git diff --check` passed before this result was appended.
- **Targeted workflow verification:** `tests/integration/workflow/test_morning_report_real_nodes.py` passed with **1 passed**. The test is slower than a small unit test because it exercises the real workflow composition path, but it now completes successfully.
- **Full repository verification:** the full pytest/coverage gate passed with **1,517 passed**, **11 skipped**, and **6 warnings**. Total coverage reported **89.45%**, above the configured **75%** threshold.
- **RAG deterministic regression:** the RAG unit/integration subset covering application RAG, RAG providers/clients, canonical RAG DI composition, and RAG CLI behavior passed with **218 passed**.
- **Database verification:** live PostgreSQL migration tests passed with **6 passed**. `alembic upgrade head` completed successfully and `alembic check` reported **No new upgrade operations detected**.
- **Live service readiness:** a bounded 30-second readiness probe confirmed PostgreSQL, Qdrant, Ollama, BGE reranker, Neo4j, and Firecrawl were reachable. The probe completed in about three seconds and returned ready status for each checked service.
- **Live BGE reranker verification:** the direct BGE reranker integration test passed with **1 passed** in under one second.
- **Live projection dependency verification:** live Qdrant collection lifecycle and Neo4j graph projection integration tests passed with **2 passed**.
- **BGE-M3 readiness gap:** the local BGE-M3 embedding provider did not become ready inside the requested 30-second cap. The process began fetching/cache-warming model files and timed out at 30 seconds. This is no longer a Codex sandbox restriction; it is a local model cache/download/warm-up readiness issue.
- **CLI live readiness impact:** `polaris rag status` and `polaris rag rebuild --projection qdrant` both timed out at 30 seconds for the same BGE-M3 initialization reason. The controlled Qdrant rebuild behavior remains covered by deterministic tests, but the live CLI readiness path should be rerun after BGE-M3 is fully cached/warmed.
- **Graphify maintenance:** a scoped Graphify query completed but returned low-signal results for this specific stabilization question. A 30-second `graphify update .` reached the end of AST extraction but timed out before final graph persistence/report completion. The timeout respected the local-service command cap and should be rerun with a longer allowance only if the user approves an exception.
- **Risk and health review:** Repowise shows the most relevant remaining RAG hotspots are `RagProjectionOperationsService` and `RagCommandService`; the CLI service is structurally healthy while projection operations retain bounded complexity around the controlled Qdrant rebuild gate. Repowise also flags `integration/clients/di.py` for hidden coupling with `integration/providers/di.py`, which matches the DI-wiring bug found and fixed in this step. No security findings or missing historical co-change requirements were reported.
- **Recommendation before MCP implementation:** pre-warm or fully cache the configured BGE-M3 model (`bge-m3:567m`) before treating live `polaris rag status` or live Qdrant rebuild as operationally ready under the 30-second local command policy. If this remains inconvenient, a future small plan should consider making `polaris rag status` capable of reporting embedding-model readiness without forcing a full model download on every status invocation.
- **External services:** PostgreSQL, Qdrant, Neo4j, BGE reranker, Ollama, and Firecrawl were available. BGE-M3 was reachable only as an initializing local model dependency and did not satisfy the 30-second readiness budget.
