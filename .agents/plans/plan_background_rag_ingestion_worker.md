  # Platform Queue Worker and Background Processing Plan

  ## Summary

  Implement a platform-native async worker daemon that automatically processes PostgreSQL-backed platform queues without creating a parallel runtime, RAG stack, or scheduler framework.

  Recommended v1 architecture:

  polaris worker
  → Dishka application/request scopes
  → canonical application operation services
  → PostgreSQL-backed queues
  → Qdrant / Neo4j projections as derived outputs

  The worker should run as a separate operational process, not inside RuntimeEngine, workflow execution, MCP, or CLI command handlers for normal user workflows.

  ## Architectural Decisions

  - Use PostgreSQL as the queue system of record for v1.
  - Do not introduce Celery, Redis, APScheduler, or a second worker framework yet.
  - Add a long-running async daemon command, plus a single-cycle mode:
      - polaris worker run
      - polaris worker run --once

  - The worker processes queues through existing canonical services:
      - workflow-output projection jobs
      - incremental RAG ingestion
      - RAG embedding jobs
      - RAG graph projection jobs

  - Each worker cycle opens clean Dishka request scopes instead of reusing stale long-lived request objects.
  - The worker must be safe for multiple instances through PostgreSQL row claiming / locking.
  - Projection stores remain rebuildable outputs; worker failure must never corrupt canonical PostgreSQL records.

  ## Implementation Steps

  ### Step 1 — Define worker scope and queue catalog

  Create typed worker contracts for:

  - enabled queues
  - batch sizes
  - poll interval
  - idle sleep interval
  - max cycles / once mode
  - stale job recovery window
  - shutdown timeout

  Initial queue catalog:

  workflow_output_projection
  rag_incremental_ingestion
  rag_embedding_projection
  rag_graph_projection

  Add result models such as:

  PlatformWorkerRunRequest
  PlatformWorkerCycleResult
  PlatformWorkerQueueResult
  PlatformWorkerRunResult

  Success criteria:

  - worker requests/results are immutable typed dataclasses
  - no dict[str, Any] internal worker contract
  - no runtime or workflow contract changes

  ———

  ### Step 2 — Make RAG embedding jobs claim-safe

  Refactor embedding queue processing so workers do not simply list queued jobs and race each other.

  Add repository methods equivalent to the existing workflow-output projection claim pattern:

  claim_next_embedding_job(...)
  recover_stale_embedding_jobs(...)

  Use PostgreSQL row locking:

  FOR UPDATE SKIP LOCKED

  Required behavior:

  - claim only queued retryable jobs
  - mark claimed jobs as processing
  - increment attempts at claim time
  - recover stale processing jobs back to retryable or failed according to retry policy
  - never reprocess completed jobs unless an explicit rebuild/requeue operation asks for it

  Success criteria:

  - two workers cannot claim the same embedding job
  - stale jobs can be recovered deterministically
  - existing single-command embedding processing still works

  ———

  ### Step 3 — Make RAG graph jobs claim-safe

  Apply the same queue-claim pattern to graph projection jobs.

  Add repository methods such as:

  claim_next_graph_job(...)
  recover_stale_graph_jobs(...)

  Required behavior:

  - claim graph jobs atomically
  - process only claimed jobs
  - preserve existing Neo4j projection behavior
  - avoid duplicate graph processing when multiple workers are running

  Success criteria:

  - graph projection processing is multi-worker safe
  - existing polaris rag process-graph --execute remains supported
  - failed graph jobs retain useful error details

  ———

  ### Step 4 — Refactor queue processors around claimed jobs

  Update:

  - embedding job processor
  - graph projection processor

  So each processor supports:

  process_next_job()
  process_queued_jobs(batch_size=...)

  Where process_queued_jobs() repeatedly claims one job at a time.

  Required behavior:

  - no broad list-then-process race
  - terminal and retryable failure handling stays typed
  - telemetry records claimed, completed, retryable failed, terminal failed, and skipped counts

  Success criteria:

  - focused unit tests pass
  - existing RAG CLI process commands still work
  - no duplicate queue lifecycle emissions

  ———

  ### Step 5 — Add workflow-output projection worker adapter

  Create a worker adapter over the existing workflow-output projection operations.

  The worker should:

  - recover stale running projection jobs
  - claim/project pending or retryable projection jobs
  - reconcile missing projection jobs for completed runs on a configurable cadence
  - return typed queue results

  Use existing projection services rather than reimplementing projection logic.

  Success criteria:

  - completed workflow runs can be projected automatically
  - missing projection jobs can be discovered without manual CLI intervention
  - existing projection operation behavior remains canonical

  ———

  ### Step 6 — Add incremental RAG ingestion worker adapter

  After the incremental ingestion layer is implemented, add a worker adapter that calls the canonical RAG ingestion operation service.

  The worker should:

  - refresh/discover eligible curated records
  - ingest only new or changed records by default
  - queue embedding jobs only for new/changed chunks
  - queue graph jobs only for new/changed documents
  - support configured source groups

  Default source groups:

  reports
  agent-signals
  recommendations
  market
  macro
  news
  sentiment
  portfolio
  backtests
  strategy

  Success criteria:

  - morning report curated records are picked up automatically
  - unchanged records are skipped
  - ingestion result reports new/changed/unchanged/failed counts

  ———

  ### Step 7 — Implement the platform worker service

  Create a canonical application service, for example:

  PlatformQueueWorkerService

  Cycle order:

  1. recover stale jobs
  2. reconcile workflow-output projection jobs
  3. process workflow-output projection jobs
  4. run incremental RAG ingestion
  5. process embedding jobs
  6. process graph jobs
  7. return typed cycle result

  Continuous mode:

  while not stopped:
      run one cycle
      sleep poll_interval if work was done
      sleep idle_sleep_interval if no work was done

  Success criteria:

  - run_once() is deterministic and testable
  - long-running loop exits cleanly
  - one queue failure does not prevent other enabled queues from being attempted unless configured as fail-fast

  ———

  ### Step 8 — Add graceful shutdown

  At the CLI boundary, handle:

  SIGINT
  SIGTERM

  Behavior:

  - stop accepting new cycles
  - allow current claimed job to finish where possible
  - respect shutdown timeout
  - log whether shutdown was graceful or forced

  Do not add signal handling to the core runtime.

  Success criteria:

  - Ctrl+C exits cleanly
  - worker does not abandon request scopes
  - running jobs are either completed or recoverable as stale jobs later

  ———

  ### Step 9 — Add CLI commands

  Add a new command group:

  polaris worker run

  Recommended options:

  polaris worker run --once
  polaris worker run --queue rag-embeddings
  polaris worker run --queue rag-graph
  polaris worker run --queue workflow-projection
  polaris worker run --queue rag-ingestion
  polaris worker run --batch-size 25
  polaris worker run --poll-interval 5
  polaris worker run --idle-sleep 30
  polaris worker run --max-cycles 10

  Also add:

  polaris worker status

  Status should summarize queue depth and stale/failed counts.

  Success criteria:

  - CLI is async-native
  - CLI uses Dishka request scopes
  - no queue logic is implemented directly in command functions

  ———

  ### Step 10 — Add settings and environment defaults

  Add typed settings for worker configuration.

  Recommended defaults:

  POLARIS_WORKER_BATCH_SIZE=25
  POLARIS_WORKER_POLL_INTERVAL_SECONDS=5
  POLARIS_WORKER_IDLE_SLEEP_SECONDS=30
  POLARIS_WORKER_STALE_JOB_AFTER_SECONDS=900
  POLARIS_WORKER_SHUTDOWN_TIMEOUT_SECONDS=30
  POLARIS_WORKER_ENABLED_QUEUES=workflow-projection,rag-ingestion,rag-embeddings,rag-graph

  Do not store credentials or service URLs in worker-specific docs/tests except through redacted examples.

  Success criteria:

  - CLI flags override settings
  - settings are validated
  - invalid intervals/batch sizes fail fast

  ———

  ### Step 11 — Add observability

  Emit structured logs, metrics, and traces for:

  - worker start/stop
  - cycle start/complete/failure
  - queue depth
  - claimed jobs
  - completed jobs
  - retryable failures
  - terminal failures
  - stale recovery
  - idle cycles
  - dependency degradation

  Telemetry rule:

  Worker emits worker lifecycle telemetry.
  Queue processors emit queue/job telemetry.
  Providers emit provider telemetry.

  Success criteria:

  - no duplicate lifecycle events
  - exception logs include tracebacks
  - Jaeger/Prometheus visibility exists for worker cycles and queue processing

  ———

  ### Step 12 — Add tests

  Required tests:

  - typed worker config validation
  - single-cycle worker processes enabled queues in expected order
  - disabled queues are skipped
  - idle cycle sleeps only in continuous mode
  - graceful shutdown stops after current cycle
  - embedding job claim prevents duplicate processing
  - graph job claim prevents duplicate processing
  - stale jobs are recovered
  - failed queue does not block unrelated queues unless fail-fast is enabled
  - CLI once mode invokes worker service correctly

  Integration tests should be gated and only run when services are available:

  PostgreSQL required:
  - queue claiming
  - stale recovery
  - worker once-cycle persistence

  Qdrant required:
  - embedding projection live integration

  Neo4j required:
  - graph projection live integration

  BGE reranker/embedding service required:
  - live embedding provider path

  ## Public Interface Additions

  New CLI:

  polaris worker run
  polaris worker run --once
  polaris worker status

  New application-level service:

  PlatformQueueWorkerService

  New typed contracts:

  PlatformWorkerRunRequest
  PlatformWorkerRunResult
  PlatformWorkerCycleResult
  PlatformWorkerQueueResult

  New repository capabilities:

  claim_next_embedding_job(...)
  recover_stale_embedding_jobs(...)
  claim_next_graph_job(...)
  recover_stale_graph_jobs(...)

  ## Assumptions

  - The incremental RAG ingestion layer is implemented before the automatic worker depends on it.
  - PostgreSQL remains the only durable queue in v1.
  - The worker is an operational daemon process, not part of workflow execution.
  - Running live projection work requires PostgreSQL, Qdrant, Neo4j, and embedding services to be available.
  - Docker/systemd deployment can wrap polaris worker run; Polaris does not need a separate scheduler framework in v1.
  