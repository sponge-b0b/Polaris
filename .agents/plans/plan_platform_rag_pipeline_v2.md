  # Platform RAG Pipeline Plan V2 — Remaining Completion Work

  ## Summary

  V2 completes the internal Platform RAG Pipeline after the completed V1 foundation. V1 already provides PostgreSQL-backed curated ingestion for reports/agent signals, deterministic chunks, embedding jobs, Qdrant dense
  projection, hybrid lexical/vector retrieval, secure generation, query/answer logging, CLI polaris rag ask, optional runtime node access, telemetry, and documentation.

  V2 should complete the remaining pipeline capabilities using staged gates:

  1. Operational RAG ingestion/rebuild commands.
  2. Broader curated source coverage.
  3. Retrieval quality improvements: BM25, reranking, parent expansion, structured retrieval.
  4. Adaptive routing, HyDE, CRAG, Self-RAG, and query rewriting through LangGraph.
  5. Firecrawl web fallback and Neo4j graph projection/retrieval.
  6. Security hardening, observability, deterministic quality gates, and updated documentation.

  Per the selected scope, V2 is pipeline-only: do not add FastAPI or MCP exposure in this plan. Leave those for a later interface plan after the internal pipeline is complete.

  ## Key Implementation Changes

  ### 1. V2 plan initialization and quality unblockers

  - Create .agent/plans/plan_platform_rag_pipeline_v2.md and add a ## Step Results section.
  - Record the completed V1 baseline and the V2 scope boundary.
  - Fix the known non-RAG mypy blocker in interfaces/cli/commands/completed_runs_command.py only if needed to allow final full-project quality gates.
  - Verification:
      - focused RAG tests still pass;
      - focused mypy for current RAG files passes;
      - known unrelated type errors are either fixed or explicitly isolated before final gates.

  ### 2. RAG operations CLI

  Add operational commands under the existing polaris rag command group:

  - polaris rag ingest --source reports
  - polaris rag ingest --source agent-signals
  - polaris rag ingest --source recommendations
  - polaris rag ingest --source market
  - polaris rag ingest --source macro
  - polaris rag ingest --source news
  - polaris rag ingest --source sentiment
  - polaris rag process-embeddings
  - polaris rag process-graph
  - polaris rag rebuild --projection qdrant
  - polaris rag rebuild --projection neo4j
  - polaris rag status

  Behavior:

  - CLI remains thin and delegates to application services.
  - PostgreSQL remains canonical.
  - Rebuild commands never treat Qdrant or Neo4j as source-of-truth.
  - Rebuild supports dry-run by default where destructive projection cleanup is involved; require an explicit confirmation flag for projection deletion.
  - Verification:
      - CLI tests for command parsing, renderable output, failures, and dry-run behavior.

  ### 3. Broaden curated source ingestion

  Extend curated RAG source builders beyond V1 reports and agent signals.

  Add typed source adapters for:

  - recommendations and rationales;
  - macro regime snapshots;
  - technical analysis snapshots;
  - market breadth/volatility summaries;
  - risk snapshots;
  - news analysis summaries;
  - sentiment summaries;
  - portfolio/backtest summaries where curated persistence records exist.

  Rules:

  - Do not ingest raw provider payloads, runtime dumps, telemetry, or arbitrary JSON.
  - Convert numeric/structured records into human-readable narrative summaries before chunking.
  - Preserve source lineage, workflow/execution lineage, symbol metadata, timestamps, and confidence/risk metadata.
  - Verification:
      - deterministic chunk tests for every new source type;
      - eligibility tests proving raw operational tables remain rejected.

  ### 4. Embedding and Qdrant projection hardening

  Complete operational Qdrant projection support.

  Changes:

  - Add Qdrant collection lifecycle support through the integration client/provider:
      - ensure collection;
      - delete/recreate collection for rebuild;
      - validate vector size and collection health.

  - Align embedding model defaults through settings instead of scattered hardcoded defaults.
  - Add idempotent embedding job requeue support for rebuilds.
  - Add batch-level failure summaries and retry visibility.
  - Verification:
      - unit tests with fake Qdrant client;
      - guarded live Qdrant integration test when Qdrant is running.

  ### 5. Retrieval quality V2

  Upgrade retrieval from V1 lexical/vector fusion to the final internal retrieval path.

  Changes:

  - Add a deterministic BM25 lexical retriever over PostgreSQL chunks.
  - Keep dense Qdrant retrieval and PostgreSQL rehydration.
  - Add parent document expansion after child chunk retrieval.
  - Add deduplication across lexical/vector/graph/web contexts.
  - Add BGE reranker provider using the existing bge-reranker compose service.
  - Add structured read-only retrieval for known facts through typed persistence repositories, not arbitrary SQL.
  - Verification:
      - fixed test corpus proves BM25, dense, and reranker ordering;
      - parent expansion returns the correct parent context without duplicate citations;
      - structured retrieval only uses approved repository-backed query paths.

  ### 6. Memory, query rewriting, adaptive routing, and HyDE

  Build the internal routing layer under application/rag.

  Add typed contracts for:

  - query context;
  - conversation memory;
  - standalone query rewrite;
  - complexity classification;
  - retrieval route;
  - HyDE expansion.

  Behavior:

  - Follow-up questions are rewritten into standalone queries when context is provided.
  - Adaptive classifier selects:
      - direct answer;
      - retrieval;
      - deep research.

  - Deep research can generate HyDE text before retrieval.
  - All classifier/router outputs use strict enums and structured parsing.
  - Verification:
      - deterministic fake model tests for each routing outcome;
      - invalid model output fails closed.

  ### 7. Unified LangGraph RAG graph

  Replace the current one-node LangGraph wrapper with the full internal graph.

  Graph stages:

  1. memory/context node;
  2. adaptive classifier node;
  3. route selection node;
  4. optional HyDE node;
  5. branched retrieval node;
  6. context fusion/reranking node;
  7. CRAG evaluator node;
  8. optional query rewrite loop;
  9. secure generation node;
  10. Self-RAG reflection node;
  11. post-processing safety node.

  Rules:

  - LangGraph remains inside application/rag/graphs/.
  - It must not own or modify the core platform workflow runtime.
  - Max loop count must be explicit and bounded.
  - Verification:
      - graph tests cover each route and loop exit condition;
      - service output remains compatible with RagResult.

  ### 8. CRAG and Self-RAG

  Add corrective and reflective quality gates.

  CRAG outcomes:

  - correct
  - incorrect
  - ambiguous
  - missing

  Corrective actions:

  - proceed;
  - discard weak context;
  - rewrite query;
  - trigger web fallback when allowed;
  - fail closed when no grounded answer can be produced.

  Self-RAG scores:

  - retrieval necessity;
  - source relevance;
  - answer support;
  - usefulness.

  Expose typed result fields on RagResult:

  - grounding_score;
  - utility_score;
  - injection_detected;
  - reflection_scores;
  - corrective_actions.

  Persist these fields in query/answer log metadata unless relational columns are explicitly needed later.

  Verification:

  - tests for missing context, unsupported answer, ambiguous context, and successful correction loop;
  - no infinite loops;
  - failed grounding returns a safe, renderable response.

  ### 9. Firecrawl web fallback

  Add Firecrawl as an optional fallback retriever.

  Rules:

  - Firecrawl is only used when RagRequest.allow_web=True or route policy explicitly permits it.
  - Web content is never automatically persisted as canonical corpus.
  - Web results are treated as untrusted transient context unless separately curated later.
  - HTML/script content is sanitized before prompt packaging.
  - Web fallback is mainly triggered by CRAG missing or ambiguous outcomes.
  - Verification:
      - provider tests with fake Firecrawl client;
      - sanitization tests for HTML/script/prompt-injection content;
      - no-web tests prove external fetches are not called by default.

  ### 10. Neo4j graph projection and graph retrieval

  Add graph projection as a rebuildable PostgreSQL-derived projection.

  Changes:

  - Add Neo4j client/provider boundaries.
  - Implement deterministic graph entity extraction first:
      - symbols;
      - reports;
      - agent signals;
      - recommendations;
      - risks;
      - regimes;
      - news themes;
      - portfolio snapshots.

  - Process existing rag_graph_jobs.
  - Upsert nodes and relationships into Neo4j idempotently.
  - Add graph retrieval branch that returns typed graph contexts and merges them with lexical/vector/web contexts.
  - Verification:
      - unit tests for entity extraction and Cypher payload construction;
      - guarded live Neo4j integration test when Neo4j is running;
      - rebuild test proves Neo4j can be recreated from PostgreSQL jobs.

  ### 11. Security hardening

  Extend existing secure prompt packaging.

  Changes:

  - Add input guardrails for direct prompt injection.
  - Sanitize retrieved context from all branches.
  - Keep retrieved context isolated as untrusted evidence.
  - Require structured JSON outputs for classifier, CRAG evaluator, router, and Self-RAG reflection.
  - Add post-generation suspicious phrase detection.
  - Emit security telemetry for injection detection, unsafe retrieved context, and failed grounding.
  - Verification:
      - direct injection tests;
      - retrieved-context injection tests;
      - web HTML/script injection tests;
      - post-generation unsafe phrase tests.

  ### 12. Observability and persistence

  Add telemetry for all V2 stages.

  Events/metrics should cover:

  - ingestion source selection;
  - embedding requeue/rebuild;
  - Qdrant collection lifecycle;
  - BGE-M3 retrieval;
  - structured retrieval;
  - reranking;
  - parent expansion;
  - adaptive routing;
  - HyDE;
  - CRAG decisions;
  - query rewrites;
  - Firecrawl fallback;
  - Neo4j graph projection/retrieval;
  - Self-RAG reflection;
  - security failures.

  Rules:

  - Provider calls remain behind integration providers and record_provider_call.
  - PostgreSQL query and answer logs remain persisted for all outcomes.
  - Do not persist raw web/provider payloads as canonical RAG source records.
  - Verification:
      - telemetry tests assert expected operations and failure events.

  ### 13. Documentation and final quality gates

  Update .docs/platform_rag_pipeline.md with V2 operations.

  Document:

  - new CLI commands;
  - source ingestion matrix;
  - Qdrant rebuild;
  - Neo4j rebuild;
  - Firecrawl fallback rules;
  - routing and corrective loop behavior;
  - security guarantees;
  - local service startup for PostgreSQL, Qdrant, Neo4j, Ollama, and reranker.

  Final verification:

  - targeted RAG unit tests;
  - CLI tests;
  - guarded live PostgreSQL/Qdrant/Neo4j tests when services are running;
  - security tests;
  - telemetry tests;
  - focused mypy for RAG and touched CLI/integration areas;
  - full-project mypy only after known unrelated blockers are resolved;
  - git diff --check;
  - graphify update ..

  ## Test Plan

  - Unit:
      - all new typed contracts;
      - source-specific ingestion builders;
      - BGE-M3 scoring;
      - reranking;
      - parent expansion;
      - adaptive routing;
      - HyDE;
      - CRAG;
      - Self-RAG reflection;
      - Firecrawl sanitation;
      - Neo4j entity extraction;
      - CLI command rendering.

  - Integration:
      - PostgreSQL RAG repository lifecycle;
      - Qdrant collection lifecycle and vector search;
      - Neo4j graph projection/retrieval;
      - optional Firecrawl provider with mocked network boundary;
      - full RagService graph execution.

  - Security:
      - direct prompt injection;
      - indirect retrieved-context injection;
      - malicious web content;
      - unsupported answer fail-closed behavior;
      - citation integrity.

  - Determinism:
      - fixed curated records produce stable chunks;
      - fixed embeddings/retrieval inputs produce stable fused order;
      - fixed graph projection input produces stable node/relationship IDs;
      - fixed CRAG/Self-RAG fake outputs produce stable loop behavior.

  ## Assumptions and Defaults

  - V2 is pipeline-only: FastAPI and MCP exposure are deferred.
  - Implementation should be staged and reviewed step-by-step.
  - PostgreSQL remains the only system-of-record.
  - Qdrant and Neo4j are rebuildable projections.
  - Firecrawl is off by default and only used when explicitly allowed.
  - Neo4j starts with deterministic extraction before LLM-based extraction.
  - BGE-M3 is the V2 dense-sparse retrieval mechanism.
  - Existing runtime architecture must not be changed for RAG.
  - LangGraph remains internal to the RAG application subsystem.
  - No autonomous trading or execution behavior is introduced.

## Step Results

### Step 1 — V2 Plan Initialization and Quality Unblockers

Status: Completed.

Files changed:

- `.agent/plans/plan_platform_rag_pipeline_v2.md`

Summary:

- Confirmed the V2 plan is present and scoped as pipeline-only: no FastAPI or MCP exposure in this plan.
- Added the `## Step Results` section at the bottom of this plan file.
- Confirmed PostgreSQL is reachable for later guarded RAG persistence work.
- Verified the current V1 RAG baseline before starting Step 2.
- Confirmed the previously known completed-runs CLI MyPy blocker is no longer present; no Python code changes were needed in Step 1.

Verification:

- PostgreSQL connectivity check succeeded:
  - `POLARIS_TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db UV_CACHE_DIR=/tmp/uv-cache timeout 60s uv run python ...`
  - Result: `database=polaris user=polaris`.
- Focused RAG tests passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/rag tests/unit/application/persistence/rag tests/unit/core/storage/persistence/test_rag_persistence_contracts.py tests/unit/core/storage/persistence/test_rag_persistence_serializer.py tests/unit/core/storage/persistence/test_rag_eligibility_rules.py tests/unit/core/storage/persistence/test_rag_eligibility_persistence_contracts.py tests/unit/core/storage/persistence/test_rag_readiness.py tests/unit/core/storage/persistence/test_postgres_rag_persistence_repository.py tests/unit/core/database/test_rag_persistence_models.py tests/unit/integration/clients/rag tests/unit/integration/providers/rag tests/unit/interfaces/cli/test_rag_command.py tests/unit/intelligence/research/test_rag_research_node.py tests/unit/telemetry/test_application_rag_telemetry.py`
  - Result: `154 passed, 1 warning`.
- Focused RAG MyPy passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run mypy application/rag application/persistence/rag core/storage/persistence/rag core/storage/persistence/repositories/postgres_rag_persistence_repository.py core/storage/persistence/serializers/rag_persistence_serializer.py integration/clients/rag integration/providers/rag interfaces/cli/commands/rag_command.py intelligence/research tests/unit/application/rag tests/unit/application/persistence/rag tests/unit/core/storage/persistence/test_rag_persistence_contracts.py tests/unit/core/storage/persistence/test_rag_persistence_serializer.py tests/unit/core/storage/persistence/test_rag_eligibility_rules.py tests/unit/core/storage/persistence/test_rag_eligibility_persistence_contracts.py tests/unit/core/storage/persistence/test_rag_readiness.py tests/unit/core/storage/persistence/test_postgres_rag_persistence_repository.py tests/unit/core/database/test_rag_persistence_models.py tests/unit/integration/clients/rag tests/unit/integration/providers/rag tests/unit/interfaces/cli/test_rag_command.py tests/unit/intelligence/research/test_rag_research_node.py tests/unit/telemetry/test_application_rag_telemetry.py --explicit-package-bases`
  - Result: `Success: no issues found in 67 source files`.
- Focused RAG Ruff check passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check <focused RAG paths>`
  - Result: `All checks passed!`.
- Full-project MyPy passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run mypy . --explicit-package-bases`
  - Result: `Success: no issues found in 967 source files`.

Known issues / deferred work:

- The focused test run emitted the existing `websockets.legacy` deprecation warning only.
- No RAG V2 implementation code was changed in Step 1; Step 2 begins the operational RAG CLI work.

### Step 2 — RAG Operations CLI

Status: Completed.

Files changed:

- `application/rag/rag_operations.py`
- `application/rag/__init__.py`
- `interfaces/cli/services/rag_command_service.py`
- `interfaces/cli/commands/rag_command.py`
- `tests/unit/application/rag/test_rag_operations.py`
- `tests/unit/interfaces/cli/test_rag_command.py`
- `graphify-out/GRAPH_REPORT.md`

Summary:

- Added typed application-layer RAG operation contracts and `RagOperationsService` for CLI-backed RAG operations.
- Added `polaris rag` operational commands:
  - `ingest --source ...`
  - `process-embeddings`
  - `process-graph`
  - `rebuild --projection ...`
  - `status`
- Kept the CLI thin: commands construct typed operation requests, delegate to `RagCommandService`, and render typed operation results.
- Kept PostgreSQL as canonical source-of-truth for status, ingestion eligibility, embedding jobs, and graph jobs.
- Implemented report and agent-signal ingestion entrypoints over existing curated eligibility records; newer source adapters remain explicit Step 3 work.
- Added safe dry-run behavior for projection rebuilds and graph processing. `rebuild` requires `--confirm-delete` before destructive projection cleanup can be attempted.
- Avoided eager Qdrant/Ollama client construction for non-embedding operations so `status`, `rebuild --projection qdrant`, and ingestion dry-runs do not require projection services.

Verification:

- CLI dry-run verification passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run polaris rag rebuild --projection qdrant`
  - Result: rendered a successful dry-run operation and did not delete or rebuild a projection.
- Live PostgreSQL status verification passed with escalation for local database access:
  - `POLARIS_DATABASE_URL=postgresql+asyncpg://user:pass@127.0.0.1:5432/db UV_CACHE_DIR=/tmp/uv-cache timeout 30s uv run polaris rag status`
  - Result: rendered RAG status from PostgreSQL successfully.
- Focused RAG/CLI tests passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/rag tests/unit/interfaces/cli/test_rag_command.py`
  - Result: `58 passed, 1 warning`.
- Focused MyPy passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run mypy application/rag/rag_operations.py application/rag/__init__.py interfaces/cli/services/rag_command_service.py interfaces/cli/commands/rag_command.py tests/unit/interfaces/cli/test_rag_command.py tests/unit/application/rag/test_rag_operations.py --explicit-package-bases`
  - Result: `Success: no issues found in 6 source files`.
- Focused Ruff and formatting checks passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check <step-2 files>`
  - Result: `All checks passed!`.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check <step-2 files>`
  - Result: `6 files already formatted`.
- Graphify was updated:
  - `GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .`
  - Result: graph rebuilt successfully; HTML visualization skipped because the graph exceeds the configured node limit.

Known issues / deferred work:

- `ingest --source recommendations|market|macro|news|sentiment` is intentionally exposed but returns an explicit not-yet-implemented operation failure until Step 3 adds those curated source adapters.
- `process-graph --execute` and `rebuild --confirm-delete` are guarded until Neo4j/Qdrant projection lifecycle processors are implemented in later V2 steps.
- The focused test run emitted the existing `websockets.legacy` deprecation warning only.

### Step 3 — Broaden Curated Source Ingestion

Status: Completed.

Files changed:

- `application/rag/curated_rag_structured_sources.py`
- `application/rag/curated_rag_document_builder.py`
- `application/rag/curated_rag_metadata.py`
- `application/rag/curated_rag_models.py`
- `application/rag/rag_operations.py`
- `core/storage/persistence/rag/rag_eligibility_rules.py`
- `interfaces/cli/services/rag_command_service.py`
- `interfaces/cli/commands/rag_command.py`
- `tests/unit/application/rag/test_curated_rag_structured_sources.py`
- `tests/unit/application/rag/test_rag_operations.py`
- `tests/unit/core/storage/persistence/test_rag_eligibility_rules.py`
- `tests/unit/interfaces/cli/test_rag_command.py`
- `graphify-out/GRAPH_REPORT.md`

Summary:

- Added typed structured curated RAG source adapters for recommendations, recommendation rationales, macro regime snapshots, technical snapshots, market context summaries, market breadth summaries, portfolio risk/allocation snapshots, news analysis snapshots, sentiment snapshots, and curated backtest summaries/artifacts.
- Kept PostgreSQL as the canonical source-of-truth and preserved the boundary rule: raw provider payloads, runtime records, telemetry, operational errors, and arbitrary JSON are not RAG ingestion sources.
- Converted structured/numeric records into deterministic human-readable source documents before chunking.
- Preserved source lineage metadata, workflow/execution/runtime/node metadata where present, source table/type/id metadata, symbols/universe/account ids, timestamps, confidence, regime, and risk metadata.
- Extended RAG eligibility rules so curated analytical summary tables are eligible while raw operational/provider tables remain rejected.
- Updated `RagOperationsService` so `ingest --source recommendations|market|macro|news|sentiment|portfolio|backtests` can enumerate eligible curated PostgreSQL records and load them through typed repositories before persisting canonical RAG documents.
- Wired the CLI operations service with the corresponding PostgreSQL repositories for the broadened curated sources.
- Added deterministic chunk tests for every new structured source type and dry-run coverage proving market ingestion counts only curated market summary tables.

Verification:

- Focused Ruff check and formatting passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check application/rag/curated_rag_structured_sources.py application/rag/curated_rag_document_builder.py application/rag/curated_rag_metadata.py application/rag/curated_rag_models.py application/rag/rag_operations.py core/storage/persistence/rag/rag_eligibility_rules.py interfaces/cli/services/rag_command_service.py interfaces/cli/commands/rag_command.py tests/unit/application/rag/test_curated_rag_structured_sources.py tests/unit/application/rag/test_rag_operations.py tests/unit/core/storage/persistence/test_rag_eligibility_rules.py tests/unit/interfaces/cli/test_rag_command.py --fix`
  - Result: `All checks passed!`.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format <same focused files>`
  - Result: files formatted successfully.
- Focused RAG/CLI tests passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/rag/test_curated_rag_structured_sources.py tests/unit/application/rag/test_rag_operations.py tests/unit/core/storage/persistence/test_rag_eligibility_rules.py tests/unit/interfaces/cli/test_rag_command.py`
  - Result: `67 passed, 1 warning`.
- Broader RAG regression tests passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/rag tests/unit/application/persistence/rag tests/unit/core/storage/persistence/test_rag_eligibility_persistence_contracts.py tests/unit/core/storage/persistence/test_rag_persistence_contracts.py tests/unit/core/storage/persistence/test_rag_persistence_serializer.py tests/unit/core/storage/persistence/test_rag_readiness.py`
  - Result: `101 passed`.
- Focused MyPy passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run mypy application/rag/curated_rag_structured_sources.py application/rag/curated_rag_document_builder.py application/rag/curated_rag_metadata.py application/rag/curated_rag_models.py application/rag/rag_operations.py interfaces/cli/services/rag_command_service.py interfaces/cli/commands/rag_command.py tests/unit/application/rag/test_curated_rag_structured_sources.py tests/unit/application/rag/test_rag_operations.py tests/unit/core/storage/persistence/test_rag_eligibility_rules.py tests/unit/interfaces/cli/test_rag_command.py --explicit-package-bases`
  - Result: `Success: no issues found in 11 source files`.
- Graphify was updated:
  - `GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .`
  - Result: graph rebuilt successfully; HTML visualization skipped because the graph exceeds the configured node limit.

Known issues / deferred work:

- Backtest metric and artifact records do not currently have first-class timestamp fields; the structured adapter preserves `metadata.timestamp` or `metadata.created_at` when present and otherwise uses a deterministic epoch fallback.
- Qdrant lifecycle hardening, embedding requeue behavior, and projection rebuild execution remain Step 4 work.
- The focused test run emitted the existing `websockets.legacy` deprecation warning only.

### Step 4 — Embedding and Qdrant Projection Hardening

Status: Completed.

Files changed:

- `config/settings.py`
- `application/rag/__init__.py`
- `application/rag/curated_rag_models.py`
- `application/rag/embedding_job_processor.py`
- `application/rag/rag_operations.py`
- `application/rag/rag_retriever.py`
- `integration/clients/rag/__init__.py`
- `integration/clients/rag/qdrant_rag_client.py`
- `integration/providers/rag/__init__.py`
- `integration/providers/rag/qdrant_vector_index_provider.py`
- `integration/providers/rag/vector_index_models.py`
- `integration/providers/rag/vector_index_provider.py`
- `interfaces/cli/services/rag_command_service.py`
- `tests/unit/application/rag/test_embedding_job_processor.py`
- `tests/unit/application/rag/test_rag_operations.py`
- `tests/unit/integration/clients/rag/test_qdrant_rag_client.py`
- `tests/unit/integration/providers/rag/test_qdrant_vector_index_provider.py`
- `tests/integration/rag/test_qdrant_collection_lifecycle.py`
- `graphify-out/GRAPH_REPORT.md`

Summary:

- Added typed Qdrant collection lifecycle contracts and provider models for collection creation, recreation, vector-size validation, health validation, and point-count reporting.
- Implemented `ensure_collection` and destructive `recreate_collection` through the Qdrant client/provider boundary, with provider-call telemetry around both operations.
- Centralized the canonical Qdrant collection, embedding model, and vector-size defaults in `config/settings.py`; ingestion, retrieval, embedding processing, and CLI composition now use those settings instead of independent hardcoded production defaults.
- Hardened embedding processing so queued batches ensure the target collection exists, validate returned embedding dimensions before upsert, honor the requested batch size, and expose retryable job ids, terminal failure job ids, and human-readable failure summaries.
- Implemented confirmed Qdrant rebuild execution in `RagOperationsService`: recreate the configured projection, then idempotently upsert deterministic queued embedding jobs from canonical PostgreSQL job records without deleting or treating Qdrant as authoritative.
- Preserved PostgreSQL as the system-of-record. Repeated rebuilds reuse deterministic current-model job ids and reset retry lifecycle state rather than creating duplicate jobs.
- Wired CLI retrieval, ingestion, embedding processing, and rebuild operations to the same settings-derived projection configuration.
- Added fake-client unit coverage for missing collections, collection recreation, vector-size mismatch, unhealthy collection rejection, provider lifecycle translation, embedding collection validation, retry summaries, and idempotent rebuild requeue behavior.
- Added a guarded live Qdrant lifecycle integration test that creates a uniquely named test collection and cleans it up when Qdrant is available.

Verification:

- Focused Ruff fix/format workflow passed for all Step 4 Python files:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check <step-4 files> --fix`
  - Result: `All checks passed!`.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format <step-4 files>`
  - Result: `18 files left unchanged` in the final verification run.
- Full-project MyPy passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run mypy . --explicit-package-bases`
  - Result: `Success: no issues found in 972 source files`.
- Broader RAG regression suite passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/rag tests/unit/application/persistence/rag tests/unit/core/storage/persistence/test_rag_persistence_contracts.py tests/unit/core/storage/persistence/test_rag_persistence_serializer.py tests/unit/core/storage/persistence/test_rag_eligibility_rules.py tests/unit/core/storage/persistence/test_rag_eligibility_persistence_contracts.py tests/unit/core/storage/persistence/test_rag_readiness.py tests/unit/core/storage/persistence/test_postgres_rag_persistence_repository.py tests/unit/core/database/test_rag_persistence_models.py tests/unit/integration/clients/rag tests/unit/integration/providers/rag tests/unit/interfaces/cli/test_rag_command.py tests/unit/intelligence/research/test_rag_research_node.py tests/unit/telemetry/test_application_rag_telemetry.py tests/integration/rag/test_qdrant_collection_lifecycle.py`
  - Result: `200 passed, 1 skipped, 1 warning`.
- The guarded live Qdrant test skipped cleanly because Qdrant was not available at `http://localhost:6333` during Step 4 execution.
- CLI rebuild safety check passed:
  - `POLARIS_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db UV_CACHE_DIR=/tmp/uv-cache timeout 30s uv run polaris rag rebuild --projection qdrant`
  - Result: successful dry-run output; no projection was deleted.
- `git diff --check` passed.
- Graphify was updated:
  - `GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .`
  - Result: graph rebuilt successfully; HTML visualization skipped because the graph exceeds the configured node limit.

Known issues / deferred work:

- Qdrant was not running during final verification, so the live lifecycle test was skipped rather than executed against an external service. Fake-client lifecycle coverage passed.
- Neo4j projection rebuild remains intentionally unimplemented and is handled by later RAG V2 steps.
- The broader test run emitted only the existing `websockets.legacy` deprecation warning.

### Step 5 — Retrieval Quality V2

Status: Completed. Live Qdrant, PostgreSQL, and BGE reranker verification passed.

Files changed:

- `application/rag/__init__.py`
- `application/rag/rag_retriever.py`
- `application/rag/retrieval_quality.py`
- `application/rag/structured_retrieval.py`
- `config/settings.py`
- `integration/clients/rag/__init__.py`
- `integration/clients/rag/bge_reranker_client.py`
- `integration/providers/rag/__init__.py`
- `integration/providers/rag/bge_reranking_provider.py`
- `integration/providers/rag/reranking_provider.py`
- `interfaces/cli/services/rag_command_service.py`
- `tests/integration/rag/test_bge_reranker.py`
- `tests/unit/application/rag/test_rag_retriever.py`
- `tests/unit/application/rag/test_retrieval_quality.py`
- `tests/unit/application/rag/test_structured_retrieval.py`
- `tests/unit/integration/clients/rag/test_bge_reranker_client.py`
- `tests/unit/integration/providers/rag/test_bge_reranking_provider.py`
- `graphify-out/GRAPH_REPORT.md`

Summary:

- Added deterministic BM25 lexical ranking over canonical PostgreSQL RAG chunks and fused it with dense Qdrant candidates only after PostgreSQL rehydration.
- Added parent-document expansion after child-chunk fusion. Expansion groups matching children by canonical document, reloads the document and its ordered chunks from PostgreSQL, and emits one citation-bearing context per parent document.
- Added canonical context deduplication across lexical, vector, graph, web, and structured routes using source lineage and normalized evidence text, preventing duplicate citations without treating a projection-specific document id as authoritative.
- Added typed BGE reranking contracts, an async BGE Text Embeddings Inference client, and a provider wrapper with provider-call telemetry. Final reranker ordering is deterministic for score ties and preserves the pre-rerank retrieval score in metadata.
- Added a typed, read-only structured retrieval boundary. The initial market implementation permits only approved technical-analysis snapshot retrieval through `MarketPersistenceRepository`; it does not expose arbitrary SQL or unrestricted table access.
- Added retrieval-stage latency telemetry for candidate loading, BM25, embedding, vector lookup, PostgreSQL rehydration, parent expansion, structured retrieval, deduplication, and reranking.
- Wired the default CLI RAG composition to the configured BGE endpoint and the approved typed PostgreSQL structured retriever.

Verification:

- Required static verification order passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check <Step 5 files> --fix`
  - Result: `All checks passed!`.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format <Step 5 files>`
  - Result: all focused files formatted successfully.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run mypy . --explicit-package-bases`
  - Result: `Success: no issues found in 982 source files`.
- Broad RAG regression and live integration suite passed:
  - Result: `211 passed, 1 skipped, 1 warning in 3.81s`.
  - The guarded live Qdrant collection lifecycle test passed against the running service.
  - The guarded live BGE test was the single skip because the service accepted the TCP connection but reset HTTP requests before returning a response.
  - The warning was the existing `websockets.legacy` deprecation warning.
- Fixed-corpus unit tests prove deterministic BM25 ordering, dense retrieval followed by PostgreSQL rehydration, parent expansion, duplicate-citation removal, and final BGE reranker ordering.
- Structured retrieval tests prove that only the approved typed repository path is used, unsupported source tables are rejected, and supported lineage/filter fields are honored.
- PostgreSQL connectivity passed against the running service:
  - Result: `('polaris', 'polaris')` for `current_database(), current_user`.
- Final BGE endpoint probe:
  - `POST http://localhost:8080/rerank`
  - Result: `curl: (56) Recv failure: Connection reset by peer`.
- `git diff --check` passed after removing trailing whitespace from the plan.
- Graphify was updated:
  - `GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .`
  - Result: graph rebuilt successfully with `15392 nodes`, `58977 edges`, and `637 communities`; HTML visualization was skipped because the graph exceeds the configured node limit.

Known issues / deferred work:

- Follow-up live BGE verification passed after the Docker volume correction and model warm-up:
  - `GET http://localhost:8080/health` returned HTTP 200.
  - Direct `/rerank` evaluation ranked the relevant market-breadth passage first.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/integration/rag/test_bge_reranker.py -rs` returned `1 passed in 1.99s`.
- Neo4j was not required for Step 5; graph projection and graph retrieval remain later-plan work.

### Step 6 — Memory, Query Rewriting, Adaptive Routing, and HyDE

Status: Completed.

Files changed:

- `application/rag/__init__.py`
- `application/rag/query_routing_models.py`
- `application/rag/query_routing_service.py`
- `integration/providers/rag/__init__.py`
- `integration/providers/rag/query_routing_provider.py`
- `integration/providers/rag/ollama_query_routing_provider.py`
- `tests/unit/application/rag/test_query_routing_service.py`
- `tests/unit/integration/providers/rag/test_ollama_query_routing_provider.py`
- `graphify-out/GRAPH_REPORT.md`

Summary:

- Added immutable, slotted typed contracts for conversation turns, conversation memory, query context, standalone rewrites, complexity classifications, retrieval routes, HyDE expansions, and complete routing decisions.
- Added strict enums for conversation roles, query complexity (`low`, `moderate`, `high`), and adaptive routes (`direct_answer`, `retrieval`, `deep_research`).
- Added `RagQueryRoutingService` as the isolated application-layer routing boundary rather than increasing the complexity of the existing churn-heavy `RagService` or `RagRetriever` modules.
- Context-free questions bypass rewriting; follow-up questions with conversation memory are rewritten into standalone queries before classification.
- Added adaptive classification for direct answers, evidence retrieval, and deep research. Only deep-research decisions generate a hypothetical retrieval document.
- Added exact-key, non-empty text, operation, and enum validation for every model response. Missing keys, extra keys, malformed values, unsupported enums, and invalid rewrite/HyDE payloads raise `RagRoutingModelOutputError` and therefore fail closed.
- Added a typed async query-model provider contract and an Ollama-backed implementation using the canonical `OllamaClient` through `asyncio.to_thread` and `record_provider_call` telemetry.
- Added application RAG telemetry for routing start, completion, failure, selected complexity/route, rewrite use, HyDE generation, and duration. Provider calls retain integration telemetry.
- Kept this step independent of the current one-node LangGraph wrapper; Step 7 will compose these routing contracts into the unified graph.

Verification:

- Deterministic routing tests passed for every routing outcome:
  - direct answer without rewriting;
  - contextual follow-up rewrite followed by retrieval;
  - deep research with HyDE expansion.
- Invalid classifier, rewrite, and HyDE outputs fail closed in deterministic fake-model tests.
- Ollama provider boundary test confirms structured output translation, deterministic temperature, model attribution, and typed operation preservation.
- Required static verification order passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check application/rag integration/providers/rag tests/unit/application/rag tests/unit/integration/providers/rag --fix`
  - Result: `All checks passed!`.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format application/rag integration/providers/rag tests/unit/application/rag tests/unit/integration/providers/rag`
  - Result: `53 files left unchanged` in the final run.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run mypy . --explicit-package-bases`
  - Result: `Success: no issues found in 988 source files`.
- Focused Step 6 tests passed:
  - Result: `12 passed in 1.59s`.
- Broader RAG regression suite passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/rag tests/unit/integration/providers/rag tests/unit/integration/clients/rag tests/unit/intelligence/research/test_rag_research_node.py tests/unit/telemetry/test_application_rag_telemetry.py tests/integration/rag`
  - Result: `112 passed in 2.54s`.
- Duplication pre-flight completed:
  - Pylint reported only pre-existing duplicate clusters and scored the inspected scope `9.92/10`.
  - JSCPD reported `4` existing exact clones and `96` duplicated lines (`1.01%`) across the inspected RAG scope; no shared helper was introduced for the single-use routing parsers.
- `git diff --check` passed.
- Graphify was updated:
  - `GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .`
  - Result: graph rebuilt successfully with `15481 nodes`, `59394 edges`, and `636 communities`; HTML visualization was skipped because the graph exceeds the configured node limit.

Known issues / deferred work:

- Step 6 deliberately does not modify `RagService`, `RagRetriever`, or the current LangGraph wrapper because those files are churn-heavy and Step 7 owns unified graph composition.
- No live Ollama request was required for Step 6. The provider boundary and all routing behavior were verified with deterministic fakes; live model behavior may be exercised once Step 7 wires the routing service into the graph.

### Step 7 — Unified LangGraph RAG Graph

Status: Completed.

Files changed:

- `application/rag/__init__.py`
- `application/rag/graphs/__init__.py`
- `application/rag/graphs/rag_graph_models.py`
- `application/rag/graphs/rag_graph_state.py`
- `application/rag/graphs/rag_service_graph.py`
- `application/rag/query_routing_service.py`
- `application/rag/rag_service.py`
- `interfaces/cli/services/rag_command_service.py`
- `tests/unit/application/rag/test_rag_service.py`
- `tests/unit/application/rag/test_rag_service_graph.py`
- `graphify-out/GRAPH_REPORT.md`

Summary:

- Replaced the former one-node LangGraph wrapper with the unified internal RAG graph: memory/context, adaptive classification, route selection, optional HyDE, branched retrieval, context fusion/reranking, CRAG evaluation, bounded corrective rewrite, secure generation, Self-RAG reflection, and post-processing safety.
- Kept LangGraph entirely inside `application/rag/graphs/`; no core workflow runtime contracts or files were modified.
- Added typed graph state and immutable CRAG boundary models for context quality, corrective actions, conversation memory loading, context evaluation, and corrective query rewriting.
- Exposed the existing query-routing stages through typed public methods so LangGraph nodes can invoke rewriting, triage, route selection, and HyDE independently without duplicating model parsing logic.
- Made the corrective retrieval loop explicitly bounded by `max_loops`. Exhausting the bound proceeds to the secure generation boundary, which fails closed when no grounded context exists.
- Preserved `RagResult` as the platform-facing output. Final results restore the original request identity and include the adaptive route, model executions, loop count, and graph-stage history as serialized boundary metadata.
- Refactored `RagService` into the persistence and service-telemetry wrapper around a typed RAG pipeline port, then wired the default CLI composition to execute the unified graph before PostgreSQL query/answer persistence.
- Reused the existing `RagRetriever` for its already implemented fusion, PostgreSQL rehydration, parent expansion, deduplication, structured retrieval, and BGE reranking. The graph's fusion/reranking node records that completed retrieval phase rather than duplicating those algorithms.
- Left substantive model-backed CRAG grading, Self-RAG scoring, corrective web fallback, and answer-quality reflection to Step 8. Step 7 uses a deterministic presence-based fail-closed evaluator to establish and verify graph control flow.

Verification:

- Required static verification order passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check . --fix`
  - Result: `All checks passed!`.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format .`
  - Result: `997 files left unchanged`.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run mypy . --explicit-package-bases`
  - Result: `Success: no issues found in 994 source files`.
- Focused graph, service, and routing tests passed:
  - Result: `29 passed, 2 warnings in 7.44s`.
- Broader RAG regression suite passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/rag tests/unit/integration/providers/rag tests/unit/integration/clients/rag tests/unit/interfaces/cli/test_rag_command.py tests/unit/intelligence/research/test_rag_research_node.py tests/unit/telemetry/test_application_rag_telemetry.py tests/integration/rag`
  - Result: `144 passed, 3 warnings in 9.25s`.
- Deterministic graph tests cover:
  - retrieval route;
  - direct route with retrieval bypass and fail-closed generation;
  - deep-research route with HyDE before retrieval;
  - successful corrective rewrite and second retrieval;
  - explicit loop-bound exhaustion;
  - stage exception conversion to a failed `RagResult`;
  - final `RagResult` compatibility and stage metadata.
- `git diff --check` passed.
- Graphify was updated:
  - `GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .`
  - Result: graph rebuilt successfully with `15727 nodes`, `60920 edges`, and `643 communities`; HTML visualization was skipped because the graph exceeds the configured node limit.

Known issues / deferred work:

- Direct-answer routing currently bypasses retrieval but still uses the grounded answer generator, so it returns `no_results` rather than producing an ungrounded answer. This is intentional fail-closed behavior until Step 8 adds explicit quality/safety policy for direct answers.
- The CRAG evaluator, corrective rewriter, and Self-RAG reflection node are typed extension boundaries with deterministic Step 7 behavior. Model-backed grading, discard/rewrite/web-fallback decisions, reflection scoring, and answer revision remain Step 8 work.
- No live PostgreSQL, Qdrant, BGE reranker, Neo4j, or Ollama service was required for Step 7 because graph behavior was verified with deterministic typed fakes and the existing integration boundaries were unchanged.
- `NOTES.md` and `config/settings.py` contained pre-existing user changes and were not modified as part of Step 7.

### Step 8 — CRAG and Self-RAG

Status: Completed.

Files changed:

- `application/rag/__init__.py`
- `application/rag/graphs/__init__.py`
- `application/rag/graphs/rag_graph_models.py`
- `application/rag/graphs/rag_graph_state.py`
- `application/rag/graphs/rag_service_graph.py`
- `application/rag/rag_quality_models.py`
- `application/rag/rag_quality_service.py`
- `application/rag/rag_result.py`
- `application/rag/rag_service.py`
- `config/rag_model_config.py`
- `integration/providers/rag/__init__.py`
- `integration/providers/rag/quality_evaluation_provider.py`
- `integration/providers/rag/ollama_quality_evaluation_provider.py`
- `interfaces/cli/services/rag_command_service.py`
- `tests/unit/application/rag/test_rag_quality_service.py`
- `tests/unit/application/rag/test_rag_result_quality.py`
- `tests/unit/application/rag/test_rag_service.py`
- `tests/unit/application/rag/test_rag_service_graph.py`
- `tests/unit/config/test_rag_model_config.py`
- `tests/unit/integration/providers/rag/test_ollama_quality_evaluation_provider.py`
- `graphify-out/GRAPH_REPORT.md`

Summary:

- Added immutable typed CRAG and Self-RAG domain contracts for context quality, corrective actions, retained context identifiers, reflection scores, answer support, and prompt-injection detection.
- Expanded canonical CRAG outcomes to `correct`, `incorrect`, `ambiguous`, and `missing`, with typed actions for `proceed`, `discard_weak_context`, `rewrite`, `web_fallback`, and `fail_closed`.
- Added `RagQualityService` as the application boundary for model-backed CRAG grading, corrective query rewriting, and Self-RAG reflection. Structured model responses use exact-key, enum, boolean, score-range, non-empty text, and known-context validation and fail closed on malformed output.
- Added a typed async quality-model provider contract and Ollama implementation. Each semantic operation selects its independently configured model, calls the canonical `OllamaClient` through `asyncio.to_thread`, and records provider telemetry with the configured model and RAG request identifier.
- Isolated retrieved evidence and generated answers as untrusted JSON payload data in CRAG/Self-RAG prompts rather than placing source text in system instructions.
- Integrated CRAG decisions into the unified graph. Weak contexts can be deterministically removed before generation, rewrites remain bounded by `max_loops`, and exhausted rewrites, explicit fail-closed decisions, empty retained context, and unavailable web fallback route to a safe renderable grounding-failure result.
- Integrated Self-RAG after secure generation. Unsupported answers or detected injection are replaced with a safe renderable response instead of exposing the rejected draft.
- Extended `RagResult` with strongly typed `grounding_score`, `utility_score`, `injection_detected`, `RagReflectionScores`, and `RagCorrectiveAction` fields, including serialization and deserialization coverage.
- Persisted quality fields and corrective actions in PostgreSQL query-log and answer-log metadata without adding premature relational columns or a schema migration.
- Wired the CLI RAG composition to use the configured CRAG grader, CRAG query-rewrite, and Self-RAG reflection models through one typed `RagQualityService` instance.
- No `core/` files or runtime contracts were modified.

Verification:

- Duplication pre-flight completed before adding the focused quality modules:
  - Pylint reported only pre-existing duplicate clusters and scored the inspected RAG scope `9.94/10`.
  - JSCPD reported `4` existing exact clones and `96` duplicated lines (`0.95%`) across the inspected RAG scope; generated JSCPD reports were removed after inspection.
- Required static verification order passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check . --fix`
  - Result: `All checks passed!`.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format . --check`
  - Result: `1004 files already formatted`.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run mypy . --explicit-package-bases`
  - Result: `Success: no issues found in 1001 source files`.
- Focused RAG, provider, CLI, and configuration regression suite passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/rag tests/unit/integration/providers/rag tests/unit/interfaces/cli/test_rag_command.py tests/unit/config/test_rag_model_config.py`
  - Result: `143 passed, 3 warnings in 8.28s`.
  - Warnings are existing SWIG and `websockets.legacy` deprecation warnings.
- Deterministic tests cover missing context, successful correction and second retrieval, explicit loop bounds, weak-context discard, unavailable web fallback, supported answers, unsupported answers, injection detection, safe renderable grounding failures, typed result round trips, quality-log persistence, operation-specific model selection, and malformed quality output.
- `git diff --check` passed.
- Graphify was updated:
  - `GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .`
  - Result: graph rebuilt successfully with `15862 nodes`, `61732 edges`, and `640 communities`; HTML visualization was skipped because the graph exceeds the configured node limit.

Known issues / deferred work:

- Step 8 defines and records the `web_fallback` corrective action but intentionally does not call an external web provider. Until Step 9 adds the approved request/policy gate and Firecrawl boundary, `web_fallback` fails closed with a safe renderable result.
- No live Ollama request was required for Step 8. Model selection, provider telemetry, strict output parsing, corrective flow, and reflection behavior were verified with deterministic typed fakes.
- Direct-answer routing remains grounded-only and returns `no_results` when no curated context is available; no ungrounded answer path was introduced.

### Step 9 — Firecrawl Web Fallback

Status: Completed.

Files changed:

- `application/rag/graphs/rag_graph_models.py`
- `application/rag/graphs/rag_service_graph.py`
- `application/rag/rag_request.py`
- `application/rag/web_fallback_service.py`
- `config/settings.py`
- `integration/clients/rag/__init__.py`
- `integration/clients/rag/firecrawl_web_client.py`
- `integration/providers/rag/__init__.py`
- `integration/providers/rag/firecrawl_web_retrieval_provider.py`
- `integration/providers/rag/web_retrieval_provider.py`
- `interfaces/cli/commands/rag_command.py`
- `interfaces/cli/services/rag_command_service.py`
- `tests/unit/application/rag/test_rag_contracts.py`
- `tests/unit/application/rag/test_rag_service_graph.py`
- `tests/unit/application/rag/test_web_fallback_service.py`
- `tests/unit/config/test_rag_model_config.py`
- `tests/unit/integration/clients/rag/test_firecrawl_web_client.py`
- `tests/unit/integration/providers/rag/test_firecrawl_web_retrieval_provider.py`
- `tests/unit/interfaces/cli/test_rag_command.py`
- `graphify-out/GRAPH_REPORT.md`

Summary:

- Added a typed async Firecrawl client boundary implemented with the official `firecrawl-py` `AsyncFirecrawl.search` API. The vendor SDK import is lazy so the disabled optional feature does not initialize Firecrawl during ordinary RAG imports.
- Added a typed provider contract and `FirecrawlWebRetrievalProvider` that records canonical provider telemetry, deduplicates URLs, creates deterministic transient context identifiers, and translates vendor results into `RagRetrievedContext` objects.
- Added `RagWebFallbackService` as the application boundary. It enforces `RagRequest.allow_web`, bounds result counts, emits RAG operation telemetry, logs failures, and returns no context on provider failure.
- Added strict `allow_web: bool = False` request serialization and deserialization. Non-boolean serialized values fail validation instead of being truthy-coerced.
- Wired CRAG `web_fallback` decisions into the unified graph only when both request permission and a composed web retriever are present. Disabled, unavailable, or empty fallback retrieval fails closed with the existing safe renderable grounding response.
- Added the CLI opt-in flag `polaris rag ask ... --web`; `--no-web` remains the default.
- Added disabled-by-default Firecrawl settings for enablement, API URL, timeout, and maximum fallback results. Default composition creates the Firecrawl boundary only when `FIRECRAWL_ENABLED=true`.
- Sanitized executable HTML elements and removed detected prompt-injection segments before prompt packaging. All resulting sources and contexts are explicitly marked `transient`, `untrusted`, and `provider=firecrawl`.
- Web content is not sent through curated document ingestion, embedding jobs, Qdrant indexing, or Neo4j projection. RAG answer logs retain source lineage/citations but do not persist raw web context text as canonical corpus.
- Repaired an unreachable return in the graph grounding-failure node found while completing the Step 9 integration.
- No `core/` files or runtime contracts were modified.

Verification:

- Required static verification order passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check . --fix`
  - Result: `All checks passed!`.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format .`
  - Result: `1011 files left unchanged` in the final run.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run mypy . --explicit-package-bases`
  - Result: `Success: no issues found in 1008 source files`.
- RAG, Firecrawl boundary, CLI, configuration, and integration regression suite passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/rag tests/unit/integration/clients/rag tests/unit/integration/providers/rag tests/unit/interfaces/cli/test_rag_command.py tests/unit/config/test_rag_model_config.py tests/integration/rag`
  - Result: `166 passed, 3 warnings in 9.29s`.
  - Warnings are existing SWIG and `websockets.legacy` deprecation warnings.
- Deterministic coverage verifies:
  - official async Firecrawl search arguments and result normalization;
  - default no-web behavior never calls the provider;
  - request permission and CLI flag propagation;
  - CRAG fallback success and empty-result fail-closed behavior;
  - provider failure fail-closed behavior;
  - HTML/script removal and prompt-injection sanitation;
  - transient/untrusted source metadata;
  - disabled-by-default configuration.
- CLI help verification passed and exposes `--web / --no-web` with Firecrawl fallback documentation.
- `git diff --check` passed.
- Duplication pre-flight completed before implementation:
  - Pylint reported only pre-existing duplicate clusters and scored the inspected scope `9.94/10`.
  - JSCPD reported `12` existing exact clones and `199` duplicated lines (`1.60%`); generated reports were removed.
- Graphify was updated:
  - `GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .`
  - Result: graph rebuilt successfully with `15964 nodes`, `62176 edges`, and `663 communities`; HTML visualization was skipped because the graph exceeds the configured node limit.

Known issues / deferred work:

- No live Firecrawl request was run because Step 9 is fully covered with deterministic fake-client/provider tests and no Firecrawl service or API credential was supplied. A future live test requires either a valid `FIRECRAWL_API_KEY` for the hosted API or a running self-hosted Firecrawl endpoint configured through `FIRECRAWL_API_URL`, plus `FIRECRAWL_ENABLED=true`.
- Firecrawl remains corrective fallback only. It does not become a general retrieval branch and is not used unless CRAG requests web fallback and the caller explicitly opts in.

### Step 10 — Neo4j Graph Projection and Graph Retrieval

Status: Completed.

Files changed:

- `application/rag/__init__.py`
- `application/rag/curated_rag_structured_sources.py`
- `application/rag/graph_projection.py`
- `application/rag/rag_operations.py`
- `application/rag/rag_retriever.py`
- `config/settings.py`
- `integration/clients/rag/__init__.py`
- `integration/clients/rag/neo4j_rag_client.py`
- `integration/providers/rag/__init__.py`
- `integration/providers/rag/graph_projection_models.py`
- `integration/providers/rag/graph_projection_provider.py`
- `integration/providers/rag/neo4j_graph_projection_provider.py`
- `interfaces/cli/commands/rag_command.py`
- `interfaces/cli/services/rag_command_service.py`
- `tests/integration/rag/test_neo4j_graph_projection.py`
- `tests/unit/application/rag/test_graph_projection.py`
- `tests/unit/application/rag/test_rag_retriever.py`
- `tests/unit/integration/clients/rag/test_neo4j_rag_client.py`
- `graphify-out/GRAPH_REPORT.md`

Summary:

- Added strongly typed graph node, relationship, projection, search, and health contracts plus a platform-facing async graph provider boundary.
- Added an official async Neo4j client boundary with whitelisted labels and relationship types, read/write routing, configurable database/projection names, connectivity status, projection cleanup, and deterministic graph search.
- Implemented deterministic PostgreSQL-document extraction for workflow runs, reports, agent signals, recommendations, risks, strategies, symbols, macro/technical regimes, news themes, sentiment snapshots, and portfolio snapshots using the master-plan graph design as the bounded starting schema.
- Added document-level `rag_graph_jobs` queueing, processing, terminal status persistence, failure logging, telemetry, and rebuild behavior. Rebuild clears only the configured derived projection, requeues canonical PostgreSQL graph jobs, and recreates Neo4j from those jobs.
- Implemented idempotent node and relationship upserts. Projection name is part of node identity and endpoint matching, preventing test/dev projections from overwriting or deleting another projection with the same deterministic entity identifier.
- Added graph retrieval that searches entity relationships in Neo4j and rehydrates the complete canonical document from PostgreSQL before returning typed `RagRetrievedContext` values.
- Merged graph contexts into the existing lexical, Qdrant, structured, deduplication, and BGE reranking path. Firecrawl remains the later CRAG-only transient fallback and is not indexed or projected.
- Made Neo4j retrieval an optional derived enhancement: an unavailable graph store is logged and observed but does not fail the canonical PostgreSQL/Qdrant retrieval path.
- Wired graph job queueing into successful curated ingestion, implemented operational graph processing and Neo4j rebuild delegation, and composed the Neo4j client/provider/processor/retriever through the existing CLI service boundary.
- Kept integration provider package initialization cycle-safe by importing the application-dependent Firecrawl implementation directly at the CLI composition boundary instead of eagerly exporting it from the provider package initializer.
- No `core/` files or runtime contracts were modified.

Verification:

- Neo4j client unit tests passed and verify whitelisted Cypher construction, projection-scoped MERGE identities, normalized search parameters, and graph-hit translation.
- Deterministic graph tests passed for entity/relationship extraction, stable projection output, job queue idempotency, processing, rebuild from PostgreSQL jobs, graph-result PostgreSQL rehydration, and optional Neo4j failure isolation.
- Guarded live Neo4j integration passed against the running service:
  - idempotent double upsert produced exactly two isolated entities;
  - relationship traversal returned the expected PostgreSQL document identifier and `SPY` related entity;
  - projection cleanup completed successfully.
- A bounded live `firecrawl-py` request used the configured `FIRECRAWL_API_KEY` without exposing it:
  - result: healthy;
  - result count: `1`;
  - returned host: `www.federalreserve.gov`.
- Required static verification order passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check . --fix`
  - Result: `All checks passed!`.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format .`
  - Result: `2 files reformatted, 1017 files left unchanged`.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run mypy . --explicit-package-bases`
  - Result: `Success: no issues found in 1016 source files`.
- Broader RAG, provider, client, CLI, telemetry, research-node, and live integration suite passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/rag tests/unit/integration/providers/rag tests/unit/integration/clients/rag tests/unit/interfaces/cli/test_rag_command.py tests/unit/intelligence/research/test_rag_research_node.py tests/unit/telemetry/test_application_rag_telemetry.py tests/integration/rag`
  - Result: `177 passed, 3 warnings in 9.61s`.
  - Warnings are existing SWIG and `websockets.legacy` deprecation warnings.
- `git diff --check` passed.
- Graphify was updated:
  - `GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .`
  - Result: graph rebuilt successfully with `16156 nodes`, `63312 edges`, and `652 communities`; HTML visualization was skipped because the graph exceeds the configured node limit.

Known issues / deferred work:

- Deterministic extraction intentionally uses curated metadata and does not introduce LLM-based entity extraction or an oversized graph ontology.
- The initial graph search is a bounded relationship-aware term/filter traversal, not a future advanced graph-ranking or community-detection engine.
- Firecrawl remains transient corrective context and is deliberately excluded from PostgreSQL canonical corpus ingestion, Qdrant indexing, and Neo4j projection.

### Step 11 — Security Hardening

Status: Completed.

Files changed:

- `application/rag/__init__.py`
- `application/rag/rag_security.py`
- `application/rag/generation/secure_prompt_builder.py`
- `application/rag/graphs/rag_service_graph.py`
- `integration/providers/rag/firecrawl_web_retrieval_provider.py`
- `tests/unit/application/rag/test_rag_security.py`
- `tests/unit/application/rag/test_rag_service_graph.py`
- `tests/unit/application/rag/test_secure_rag_generation.py`
- `tests/unit/integration/providers/rag/test_firecrawl_web_retrieval_provider.py`
- `graphify-out/GRAPH_REPORT.md`

Summary:

- Added a typed `RagSecurityGuard` and immutable security result contracts for deterministic inspection of direct user input, retrieved context, and generated output.
- Added fail-closed direct prompt-injection detection before the graph invokes memory, classifier, routing, retrieval, or generation components.
- Added canonical context sanitation for every graph retrieval branch. Curated, vector, lexical, structured, graph, and Firecrawl fallback contexts now pass through the same security boundary before CRAG evaluation and generation.
- Preserved safe financial evidence while removing instruction-override segments, executable HTML blocks, system/developer markup blocks, and remaining HTML tags. Contexts that contain no safe evidence after sanitation are discarded.
- Extended secure prompt packaging with defense-in-depth sanitation so callers that use `RagAnswerGenerator` outside the graph cannot package unsanitized retrieved context.
- Refactored the Firecrawl provider to reuse the canonical sanitizer while retaining transient/untrusted provenance and recording detected injection, executable markup, and security signals in context metadata.
- Added deterministic post-generation detection for instruction disclosure, prompt exfiltration, role override, policy bypass, and credential-like disclosure phrases. Suspicious output is replaced with the existing safe grounding-failure response before Self-RAG reflection.
- Preserved retrieved context as isolated untrusted JSON evidence. No retrieved content is mixed into system policy instructions.
- Confirmed that classifier/triage, router, CRAG, query rewrite, and Self-RAG model boundaries continue to require strict structured JSON with exact-key and typed-value validation.
- Added `rag.security.input_guard`, `rag.security.context_sanitization`, `rag.security.output_guard`, and `rag.security.grounding_failure` telemetry operations through `ApplicationRagTelemetry`.
- No `core/` files or runtime contracts were modified.

Verification:

- Repowise pre-flight reported `application/rag/graphs/rag_service_graph.py` as a churn-heavy 91% hotspot with existing complexity in `_post_processing_safety`; security logic was therefore isolated in `rag_security.py` and graph edits were kept to narrow orchestration calls.
- Duplication pre-flight completed before implementation:
  - Pylint reported only existing duplicate clusters and rated the inspected scope `9.93/10`.
  - JSCPD reported `14` existing clones and `215` duplicated lines (`1.78%`); generated reports were removed after inspection.
- Focused security and graph tests passed:
  - Result: `29 passed, 2 warnings in 7.31s`.
- Broader RAG, providers, clients, CLI, research node, telemetry, and integration regression suite passed:
  - Result: `185 passed, 3 warnings in 9.75s`.
  - Warnings are existing SWIG and `websockets.legacy` deprecation warnings.
- Security coverage verifies:
  - direct prompt injection fails closed before routing;
  - safe security-related questions are not falsely blocked;
  - indirect retrieved-context injection is removed while safe evidence is retained;
  - malicious HTML/script content is removed;
  - all retrieval branches are sanitized before CRAG and generation;
  - suspicious generated phrases fail closed before reflection;
  - security and failed-grounding telemetry operations are emitted;
  - secure prompt policy remains separated from untrusted evidence.
- Required static verification order passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check . --fix`
  - Result: `All checks passed!`.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format .`
  - Result: `1021 files left unchanged` in the final run.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run mypy . --explicit-package-bases`
  - Result: `Success: no issues found in 1018 source files`.
- `git diff --check` passed.
- Graphify was updated:
  - `GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .`
  - Result: graph rebuilt successfully with `16206 nodes`, `63542 edges`, and `644 communities`; HTML visualization was skipped because the graph exceeds the configured node limit.

Known issues / deferred work:

- Step 11 provides and tests security telemetry at the application boundary. Step 12 remains responsible for composing comprehensive telemetry across the default RAG pipeline and asserting all V2 stage operations end to end.
- The guard intentionally uses deterministic high-confidence patterns rather than an additional security LLM. This keeps blocking behavior reproducible and avoids turning the security boundary into another prompt-sensitive model call.
- No PostgreSQL, Qdrant, Neo4j, Firecrawl, Ollama, or BGE service was required for Step 11 because the changes are deterministic application security controls with mocked integration boundaries.
- The pre-existing user change in `AGENTS.md` was not modified as part of Step 11.

### Step 12 — Observability and Persistence

Status: Completed.

Files changed:

- `application/rag/graph_projection.py`
- `application/rag/query_routing_service.py`
- `application/rag/rag_operations.py`
- `application/rag/rag_retriever.py`
- `interfaces/cli/services/rag_command_service.py`
- `tests/unit/application/rag/test_graph_projection.py`
- `tests/unit/application/rag/test_query_routing_service.py`
- `tests/unit/application/rag/test_rag_operations.py`
- `tests/unit/application/rag/test_rag_retriever.py`
- `tests/unit/application/rag/test_rag_service.py`
- `graphify-out/GRAPH_REPORT.md`

Summary:

- Composed one shared `ApplicationRagTelemetry` emitter into the default CLI RAG query and operations dependency graphs so telemetry is active for retrieval, generation, quality evaluation, routing, security, Firecrawl fallback, ingestion, embedding jobs, Qdrant lifecycle operations, and Neo4j graph jobs.
- Added explicit ingestion-source selection telemetry for supported and rejected sources without changing the canonical source contracts.
- Added started, completed, and failed stage telemetry for standalone query rewrite, adaptive triage, route selection, and HyDE generation, including strict-output parsing and validation failures.
- Added failure telemetry to the existing retrieval-stage measurements for PostgreSQL candidates, BGE-M3 query embedding, Qdrant search, PostgreSQL vector rehydration, structured retrieval, parent expansion, BGE reranking, and optional Neo4j retrieval.
- Added batch and per-job started/completed/failed telemetry for Neo4j graph projection while preserving persisted graph-job status transitions and graceful graph-retrieval degradation.
- Confirmed existing V2 telemetry remains in place for embedding requeue/rebuild, Qdrant collection lifecycle, hybrid retrieval, CRAG decisions, corrective rewrites, Firecrawl fallback, Self-RAG reflection, answer generation, security guards, and query/answer persistence outcomes.
- Preserved the integration provider boundary and its `record_provider_call` instrumentation; no provider or client call was moved into application or intelligence code.
- Added a persistence regression test proving transient raw Firecrawl/web context text is not stored in PostgreSQL query or answer logs. Only bounded provenance metadata is retained; raw provider payloads do not become canonical RAG source records.
- No `core/` files or runtime contracts were modified.

Verification:

- Focused Step 12 tests passed:
  - Result: `55 passed, 3 warnings in 7.83s`.
- Broader RAG, providers, clients, CLI, research-node, telemetry, and integration regression suite passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/rag tests/unit/integration/providers/rag tests/unit/integration/clients/rag tests/unit/interfaces/cli/test_rag_command.py tests/unit/intelligence/research/test_rag_research_node.py tests/unit/telemetry/test_application_rag_telemetry.py tests/integration/rag`
  - Result: `189 passed, 3 warnings in 10.05s`.
  - Warnings are existing SWIG and `websockets.legacy` deprecation warnings.
- Required static verification order passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check . --fix`
  - Result: `All checks passed!`.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format .`
  - Result: `1021 files left unchanged`.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run mypy . --explicit-package-bases`
  - Result: `Success: no issues found in 1018 source files`.
- `git diff --check` passed.
- Graphify was updated:
  - `GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .`
  - Result: graph rebuilt successfully with `16235 nodes`, `63892 edges`, and `682 communities`; HTML visualization was skipped because the graph exceeds the configured node limit.

Known issues / deferred work:

- Step 12 used deterministic unit and integration-boundary tests; no PostgreSQL, Qdrant, Neo4j, Firecrawl, Ollama, or BGE service was required.
- Step 13 is documentation and final quality-gate work. Its guarded live PostgreSQL, Qdrant, and Neo4j checks require those services to be running; end-to-end model and reranking checks additionally require Ollama and the BGE reranker.

### Step 13 — Documentation and Final Quality Gates

Status: Completed.

Files changed:

- `.docs/platform_rag_pipeline.md`
- `.agent/plans/plan_platform_rag_pipeline_v2.md`

Summary:

- Replaced the stale V1-oriented RAG guide with the implemented V2 architecture and operational model.
- Documented PostgreSQL as the canonical system of record and Qdrant/Neo4j as destructive-rebuild-safe derived projections.
- Documented the six logical RAG layers, independently configurable model settings, twin-engine retrieval, structured and graph retrieval, BGE reranking, CRAG, corrective rewrites, Firecrawl fallback, Self-RAG reflection, and security boundaries.
- Added the complete supported ingestion-source matrix for reports, signals, recommendations, market, macro, news, sentiment, portfolio, and backtest records.
- Documented every current `polaris rag` command: `ask`, `ingest`, `process-embeddings`, `process-graph`, `rebuild`, and `status`, including dry-run and destructive-confirmation behavior.
- Added explicit Qdrant and Neo4j rebuild procedures that recover only from canonical PostgreSQL jobs and records.
- Documented Firecrawl's disabled-by-default, CRAG-only, per-request opt-in behavior and the rule that transient web payloads do not populate PostgreSQL, Qdrant, or Neo4j automatically.
- Documented direct and indirect prompt-injection controls, strict structured model outputs, secure evidence packaging, post-generation inspection, and fail-closed grounding behavior.
- Added local startup, migration, validation, telemetry, runtime integration, and troubleshooting instructions for PostgreSQL, Qdrant, Neo4j, Ollama, BGE-M3, the BGE reranker, and Firecrawl.
- No application, integration, intelligence, runtime, or core code was changed in Step 13.

Verification:

- Confirmed the live container state before integration testing:
  - PostgreSQL: running;
  - Qdrant: running;
  - Neo4j: running;
  - BGE reranker: running and healthy.
- CLI help verification passed for the RAG command group, `rag ask`, and `rag rebuild`; the rendered options match the documented commands and safety flags.
- Deterministic RAG, providers, clients, CLI, runtime-node, security, and telemetry suite passed:
  - Result: `186 passed, 3 warnings in 9.00s`.
- Guarded live RAG infrastructure suite passed against the running Qdrant, Neo4j, and BGE services:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/integration/rag`
  - Result: `3 passed, 2 warnings in 8.51s`.
  - The tests verified isolated Qdrant collection lifecycle, idempotent Neo4j projection/retrieval/cleanup, and live BGE relevance ordering.
- The first PostgreSQL schema check correctly reported that the local database was behind migration head and `polaris rag status` failed because `rag_source_eligibility` did not yet exist.
- Applied the repository's existing migration chain successfully:
  - `POLARIS_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db UV_CACHE_DIR=/tmp/uv-cache timeout 300s uv run alembic upgrade head`
  - Applied revisions through completed-run archive head without errors.
- PostgreSQL migration and live RAG status gates then passed:
  - `uv run alembic check`: `No new upgrade operations detected.`
  - `uv run polaris rag status`: succeeded and reported PostgreSQL as the source of truth with zero current RAG records/jobs.
  - `tests/database/test_migrations.py`: `4 passed, 5 warnings in 13.23s`.
- Required static verification order passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check . --fix`
  - Result: `All checks passed!`.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format .`
  - Result: `1021 files left unchanged`.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run mypy . --explicit-package-bases`
  - Result: `Success: no issues found in 1018 source files`.
- `git diff --check` passed.
- Graphify update completed after documentation changes and reported no code-topology changes.

Known issues / deferred work:

- No live end-to-end answer-generation request was run because the Step 13 final gate requires guarded PostgreSQL/Qdrant/Neo4j infrastructure checks, security tests, telemetry tests, and static validation; model behavior is already covered through deterministic provider-boundary tests. Ollama must be running with every configured `RAG_*_MODEL` pulled before a manual live `polaris rag ask` request.
- The existing SWIG, `websockets.legacy`, and Alembic `path_separator` deprecation warnings remain unchanged and did not cause test failures.
- Pre-existing working-tree changes in `AGENTS.md`, `NOTES.md`, Step 11/12 implementation files, and the LLM Guard analysis were preserved.
