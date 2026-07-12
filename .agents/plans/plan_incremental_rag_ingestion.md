  # Incremental RAG Ingestion Layer Plan

  ## Summary

  Add an incremental RAG ingestion layer that lets Polaris ingest only new or changed curated PostgreSQL records into the RAG corpus, without adding the future async worker/scheduler yet.

  The new lifecycle will be:

  curated PostgreSQL record
  → RAG eligibility refresh/marking
  → incremental ingestion planner
  → RAG document/chunk upsert only when new or changed
  → embedding jobs queued only for new/changed chunks
  → graph jobs queued only for new/changed documents
  → manual embed/graph commands process queued jobs

  The morning report workflow will still finish independently. RAG ingestion remains manually invoked for now, but the manual command becomes incremental and safe to rerun.

  ## Key Implementation Changes

  ### 1. Add first-class ingestion state

  Create a typed ingestion-state model and PostgreSQL table, for example:

  rag_source_ingestion_state

  Canonical fields:

  - state_id
  - source_table
  - source_id
  - source_type
  - document_id
  - content_hash
  - target_store
  - embedding_model
  - graph_store
  - graph_model
  - status
  - last_ingested_at
  - last_changed_at
  - last_error
  - created_at
  - updated_at

  Add a unique constraint over:

  source_table, source_id, source_type, target_store, embedding_model, graph_store, graph_model

  Purpose:

  - distinguish new, changed, unchanged, and failed RAG ingestion candidates
  - avoid stuffing ingestion state into metadata
  - provide an operational audit trail for incremental ingestion

  ### 2. Add repository and typed contracts

  Extend the RAG persistence boundary with typed state methods:

  get_source_ingestion_state(...)
  upsert_source_ingestion_state(...)
  list_source_ingestion_state(...)

  Add immutable typed records/results such as:

  RagSourceIngestionStateRecord
  RagIncrementalIngestionDecision
  RagIncrementalIngestionPlan

  Decision statuses:

  new
  changed
  unchanged
  failed

  ### 3. Add RAG eligibility refresh for curated records

  Add a source-discovery/eligibility-refresh service that scans canonical curated PostgreSQL records by source group:

  reports
  agent-signals
  recommendations
  market
  macro
  news
  sentiment
  portfolio
  backtests

  For each candidate:

  1. build a RagEligibilitySourceCandidate
  2. evaluate default RAG eligibility
  3. upsert rag_source_eligibility
  4. return eligible records for ingestion

  This ensures newly projected morning report records can be discovered by RAG ingestion without requiring manual eligibility rows.

  ### 4. Add incremental ingestion planning

  Refactor RagIngestionOperationsService so ingestion is:

  discover/refresh eligibility
  → load curated source
  → build RAG bundle without jobs
  → compare bundle document content_hash to ingestion state/existing document
  → skip unchanged unless forced
  → persist new/changed document and chunks
  → queue only necessary embedding and graph jobs
  → update ingestion state

  Default behavior:

  incremental=True
  force_reingest=False

  Add request flags:

  force_reingest: bool = False
  include_unchanged: bool = False

  CLI flags:

  polaris rag ingest --source portfolio
  polaris rag ingest --source portfolio --dry-run
  polaris rag ingest --source portfolio --force-reingest
  polaris rag ingest --source portfolio --include-unchanged

  ### 5. Queue embedding jobs only for new/changed chunks

  Change the current job-building behavior so unchanged chunks do not get requeued.

  Rules:

  - New document: queue jobs for all chunks.
  - Changed document: queue jobs only for chunks whose content_hash changed or do not exist.
  - Unchanged document: queue no embedding jobs.
  - Force reingest: queue jobs for all current chunks.

  This prevents rerunning ingestion from resetting completed embedding jobs back to queued.

  ### 6. Queue graph jobs only for new/changed documents

  Update the graph queue boundary to be content-hash aware.

  Rules:

  - New document: queue graph job.
  - Changed document: queue graph job.
  - Unchanged document: do not queue graph job.
  - Force reingest: queue graph job.

  The graph job metadata should include the document content_hash, but the canonical state remains in the new ingestion-state table.

  ### 7. Preserve manual processing commands

  Do not add a scheduler or background worker in this plan.

  Manual operations remain:

  polaris rag ingest --source <source>
  polaris rag embed
  polaris rag graph --execute
  polaris rag rebuild --projection qdrant
  polaris rag rebuild --projection neo4j

  rag ingest becomes safe to run repeatedly because unchanged records are skipped by default.

  ### 8. Improve CLI output and status

  Update polaris rag ingest output to show:

  eligible records
  selected records
  new records
  changed records
  unchanged skipped
  documents persisted
  chunks persisted
  embedding jobs queued
  graph jobs queued
  Update polaris rag status to include ingestion-state counts:

  new / changed / unchanged / failed / last ingested

  ### 9. Add tests

  Add focused tests for:

  - ingestion state record validation and serialization
  - Alembic/model DDL coverage for rag_source_ingestion_state
  - repository upsert/list/get behavior
  - eligibility refresh discovering newly projected morning report records
  - unchanged records skipped by default
  - changed records reingested
  - embedding jobs queued only for changed chunks
  - graph jobs queued only for changed documents
  - --force-reingest bypassing unchanged skip
  - dry-run reporting without writes
  - repeated rag ingest idempotence

  Add one integration-style test for:

  project morning-report-like curated records
  → refresh eligibility
  → run rag ingest once
  → run rag ingest again
  → second run skips unchanged records

  ## Suggested Step Order

  1. Add ingestion-state typed models and database model.
  2. Add Alembic migration and model tests.
  3. Extend RAG repository protocol and PostgreSQL implementation.
  4. Add repository unit tests.
  5. Add incremental decision/planner types.
  6. Refactor bundle building so jobs can be added after content-hash comparison.
  7. Add changed-chunk detection and selective embedding job queueing.
  8. Make graph queueing content-hash aware.
  9. Add curated-source eligibility refresh service.
  10. Wire eligibility refresh into RagIngestionOperationsService.
  11. Add force_reingest / include_unchanged request fields and CLI flags.
  12. Update CLI renderers/status output.
  13. Add end-to-end unit coverage for new/changed/unchanged ingestion.
  14. Add focused PostgreSQL integration coverage if Postgres is running.
  15. Update .docs/platform_rag_pipeline.md with the incremental ingestion lifecycle.

  ## Assumptions

  - This plan does not add an async worker, scheduler, daemon, or automatic background processor.
  - PostgreSQL remains authoritative; Qdrant and Neo4j remain rebuildable projections.
  - Existing destructive rebuild commands remain the recovery path for stale external projection cleanup.
  - The default ingestion behavior should become incremental and idempotent.
  - Force reingestion remains available for backfills, rebuild validation, and operational recovery.
  