  # Polaris DeepEval LLM Evaluation Integration Plan

  ## Summary

  Adopt DeepEval as the canonical Polaris LLM evaluation engine for RAG, intelligence workflows, reports, recommendations, and future MCP/agent behavior.

  DeepEval will execute evaluations. Polaris will persist canonical evaluation records in PostgreSQL. Langfuse will receive projected scores, reasons, datasets, and trace-linked evaluation metadata.

  Target architecture:

  Polaris RAG / intelligence output
  → canonical PostgreSQL records
  → evaluation case builder
  → DeepEval evaluation runner
  → PostgreSQL evaluation records
  → Langfuse score / dataset / trace projection

  DeepEval must not become a parallel telemetry system or source of truth.

  ## Core Decisions

  1. DeepEval is the canonical LLM evaluation engine
      - Use DeepEval for LLM/RAG quality metrics, CI eval gates, regression tests, and post-run evaluation jobs.

  2. PostgreSQL remains canonical
      - Persist evaluation cases, runs, metric results, thresholds, reasons, and status in Polaris PostgreSQL.

  3. Langfuse receives projections
      - Project DeepEval scores and reasons into Langfuse traces/datasets for AI observability and review.

  4. No direct DeepEval calls from business logic
      - RAG services, intelligence agents, workflow nodes, and CLI code must not import DeepEval directly.
      - DeepEval access belongs behind a Polaris evaluation provider/adapter.

  5. No implicit OpenAI defaults
      - Polaris must require explicit judge model configuration.
      - DeepEval telemetry should default to opt-out unless explicitly approved.

  6. Evaluation is normally asynchronous
      - Normal workflow execution should not block on DeepEval.
      - CI gates, QA workflows, and explicit strict-evaluation commands may block on evaluation results.

  ## Key Implementation Changes

  ### 1. Add evaluation configuration

  Add settings for DeepEval and judge-model configuration:

  POLARIS_DEEPEVAL_ENABLED=true
  POLARIS_DEEPEVAL_JUDGE_PROVIDER
  POLARIS_DEEPEVAL_JUDGE_MODEL
  POLARIS_DEEPEVAL_STRICT_MODE=false
  POLARIS_DEEPEVAL_TELEMETRY_OPT_OUT=true
  POLARIS_DEEPEVAL_DEFAULT_THRESHOLD=0.7
  POLARIS_DEEPEVAL_MAX_CONCURRENCY
  POLARIS_DEEPEVAL_TIMEOUT_SECONDS

  Rules:

  - Production evaluation commands must fail if judge provider/model is missing.
  - Unit tests use fake evaluation providers.
  - Live DeepEval tests require explicit service/model configuration.

  ### 2. Add canonical evaluation domain models

  Create typed internal contracts for evaluation:

  EvaluationCase
  EvaluationRun
  EvaluationMetricResult
  EvaluationScore
  EvaluationThreshold
  EvaluationDatasetReference
  EvaluationTargetType
  EvaluationStatus

  Core target types:

  rag_answer
  rag_retrieval
  rag_generation
  morning_report
  strategy_synthesis
  recommendation_explanation
  mcp_tool_response
  agent_task

  Each evaluation case should carry:

  - stable case ID
  - source record IDs
  - workflow execution ID where applicable
  - Langfuse trace/observation ID where applicable
  - input query/task
  - actual output
  - expected output or rubric
  - retrieval context when applicable
  - citation/context IDs
  - tags
  - created timestamp

  ### 3. Add PostgreSQL evaluation persistence

  Add first-class persistence models and repositories for:

  evaluation_datasets
  evaluation_cases
  evaluation_runs
  evaluation_metric_results
  evaluation_artifacts

  Minimum canonical fields:

  - dataset ID/name/version
  - case ID
  - run ID
  - target type
  - source record references
  - metric name
  - score
  - threshold
  - passed
  - reason
  - evaluator model/provider
  - duration
  - status
  - error message/details
  - Langfuse projection status
  - created/updated timestamps

  Do not store evaluation concepts as opaque metadata if they are canonical fields.

  ### 4. Add DeepEval provider boundary

  Add an integration provider such as:

  integration/providers/llm_evaluation/
      evaluation_provider.py
      deepeval_evaluation_provider.py

  The application layer should call a typed provider protocol, not DeepEval directly.

  Provider responsibilities:

  - translate Polaris evaluation cases into DeepEval test cases
  - select configured DeepEval metrics
  - execute metrics
  - return typed Polaris metric results
  - normalize DeepEval reasons/errors
  - enforce timeouts and concurrency limits

  ### 5. Add evaluation application services

  Add services under an application-owned evaluation package:

  application/evaluations/
      evaluation_case_builder.py
      evaluation_dataset_service.py
      evaluation_run_service.py
      evaluation_result_service.py
      evaluation_langfuse_projection_service.py

  Service responsibilities:

  - build cases from canonical PostgreSQL records
  - run evaluations through the provider
  - persist results
  - project scores to Langfuse
  - expose status and reporting APIs
  - support CI and offline batch runs

  ### 6. Define RAG evaluation metrics

  Use DeepEval metrics for RAG quality:

  Faithfulness
  Answer Relevancy
  Contextual Relevancy
  Contextual Precision
  Contextual Recall
  Hallucination

  Add Polaris custom metrics using G-Eval or DAG-style rubrics for:

  citation_support
  financial_answer_quality
  risk_explanation_quality
  unsupported_claim_penalty
  refusal_correctness
  prompt_injection_resistance

  Initial thresholds:

  faithfulness >= 0.80
  answer_relevancy >= 0.75
  contextual_relevancy >= 0.70
  contextual_precision >= 0.70
  contextual_recall >= 0.70
  citation_support >= 0.80

  Thresholds should be persisted and versioned, not hardcoded inside tests only.

  ### 7. Define intelligence evaluation metrics

  Add DeepEval/custom metrics for:

  strategy_synthesis_quality
  recommendation_rationale_quality
  report_completeness
  risk_assessment_quality
  portfolio_context_alignment
  reasoning_consistency
  unsupported_financial_claims

  These should evaluate structured Polaris outputs, not arbitrary legacy payloads.

  ### 8. Integrate with Langfuse

  After each evaluation run:

  DeepEval result
  → Polaris evaluation record
  → Langfuse score projection

  Langfuse projection should include:

  - metric name
  - score
  - threshold
  - pass/fail
  - reason
  - evaluator model
  - dataset/case ID
  - Polaris run ID
  - related trace/observation ID

  Rules:

  - Langfuse projection failure must not delete or invalidate PostgreSQL evaluation records.
  - Projection retries must be idempotent.
  - Langfuse remains observability/projection, not canonical eval storage.

  ### 9. Add evaluation datasets

  Create canonical evaluation datasets from Polaris records:

  golden_rag_questions
  rag_citation_support
  rag_security_prompt_injection
  morning_report_quality
  strategy_synthesis_quality
  recommendation_explanations
  mcp_tool_responses
  agent_task_completion

  Dataset records should support:

  - versioning
  - tags
  - source lineage
  - active/inactive status
  - threshold profile
  - expected output/rubric
  - deterministic fixture linkage where available

  ### 10. Add CLI commands

  Add focused commands:

  polaris eval status
  polaris eval datasets list
  polaris eval run --dataset <name>
  polaris eval run-rag --case <case-id>
  polaris eval run-latest-rag
  polaris eval results --run <run-id>

  Commands should resolve services through Dishka request scopes and must not call DeepEval directly.

  ### 11. Add CI evaluation suite

  Add a separate eval test suite that can run in CI:

  tests/evaluation/

  Recommended groups:

  quick smoke evals
  RAG regression evals
  prompt regression evals
  strategy synthesis evals
  security evals

  CI behavior:

  - normal unit tests do not require live judge models
  - eval tests require explicit environment configuration
  - missing eval configuration should skip with clear reason unless running an eval-required CI job
  - release gates may require selected eval datasets to pass

  ### 12. Add async evaluation jobs

  Use the existing queue/worker architecture where available.

  Job types:

  evaluate_rag_result
  evaluate_strategy_output
  evaluate_report
  project_eval_scores_to_langfuse
  retry_failed_eval_projection

  Normal production flow:

  workflow completes
  → output persisted
  → curated records projected
  → evaluation jobs enqueued
  → DeepEval runs asynchronously
  → results persisted
  → Langfuse scores projected

  ### 13. Add observability for evaluation

  Record canonical telemetry for:

  - evaluation run started/completed/failed
  - metric execution latency
  - judge-model failures
  - threshold failures
  - dataset load failures
  - Langfuse projection failures
  - retry counts
  - skipped cases

  Expose metrics such as:

  evaluation_runs_total
  evaluation_metric_failures_total
  evaluation_metric_duration_seconds
  evaluation_cases_evaluated_total
  evaluation_langfuse_projection_failures_total

  ### 14. Add documentation

  Create or update docs for:

  docs/llm_evaluation.md
  docs/platform_rag_pipeline.md
  docs/testing_guide.md
  docs/langfuse_ai_observability.md

  Document:

  - DeepEval’s role
  - Langfuse relationship
  - canonical ownership model
  - required env vars
  - local eval workflow
  - CI eval workflow
  - dataset creation
  - threshold policy
  - live service requirements
  - privacy/redaction rules

  ## Test Plan

  - settings validation
  - case builder validation
  - threshold evaluation
  - fake provider execution
  - DeepEval result mapping
  - Langfuse score projection mapping
  - persistence serializer/model tests
  - redaction and capture-policy tests

  ### Integration tests

  - persist evaluation dataset/case/run/result
  - build RAG evaluation case from persisted RAG result
  - run fake evaluation provider end-to-end
  - project fake metric results to fake Langfuse sink
  - retry failed projection idempotently
  - CLI resolves evaluation services through DI

  ### Live DeepEval tests

  Require configured judge model:

  - run one RAG faithfulness evaluation
  - run one answer relevancy evaluation
  - run one custom Polaris financial-quality rubric
  - verify results persist to PostgreSQL

  ### Live Langfuse tests

  Require Langfuse service:

  - project evaluation score to Langfuse
  - confirm trace/case/run correlation fields
  - confirm redaction policy is applied

  ### Regression gates

  - existing RAG tests continue to pass
  - existing Langfuse plan remains valid
  - no direct DeepEval imports outside provider boundary
  - no evaluation data is stored only in Langfuse
  - no secrets or raw credentials appear in tests/docs

  ## Assumptions and Defaults

  - DeepEval is required for Polaris LLM evaluation workflows, but not for every synchronous workflow execution.
  - Langfuse is required for AI-observability projection.
  - PostgreSQL is the canonical evaluation record store.
  - DeepEval judge models must be explicitly configured.
  - DeepEval telemetry defaults to opt-out.
  - Evaluation results may fail quality gates without failing the original workflow unless the run is explicitly in strict evaluation mode.
  - Confident AI platform is not adopted in this plan; only the open-source DeepEval framework is integrated.

## Step Results

### Step 1 — Add evaluation configuration

Status: Completed.

Changes:

- Added canonical DeepEval evaluation settings to `config/settings.py` with Polaris-prefixed environment aliases.
- Added `validate_deepeval_evaluation()` so strict evaluation commands can require `POLARIS_DEEPEVAL_ENABLED`, `POLARIS_DEEPEVAL_JUDGE_PROVIDER`, and `POLARIS_DEEPEVAL_JUDGE_MODEL` without leaking configured values in errors.
- Added safe defaults: enabled evaluation integration, non-strict execution, DeepEval telemetry opt-out, default threshold `0.7`, max concurrency `4`, and timeout `60` seconds.
- Added `.env.example` entries for the canonical DeepEval settings.
- Added focused unit coverage for defaults, Polaris-prefixed environment loading, strict validation, disabled-required validation, numeric bounds, and non-leaking errors.

Verification:

- `uv run ruff check config/settings.py tests/unit/config/test_deepeval_evaluation_settings.py --fix`
- `uv run ruff format config/settings.py tests/unit/config/test_deepeval_evaluation_settings.py`
- `uv run mypy config/settings.py tests/unit/config/test_deepeval_evaluation_settings.py --explicit-package-bases`
- `uv run pytest -q tests/unit/config/test_deepeval_evaluation_settings.py`

Result: all focused checks passed.

### Step 2 — Add canonical evaluation domain models

Status: Completed.

Changes:

- Added `domain.evaluation` as the canonical typed domain package for LLM-evaluation contracts.
- Added immutable evaluation target, status, dataset reference, threshold, score, case, run, and metric-result models.
- Kept serialization explicit through `to_dict()` methods for persistence, telemetry, and transport boundaries.
- Added validation for stable identifiers, non-empty text fields, score ranges, threshold/metric consistency, timestamps, evaluator identity, and required expected output or rubric.
- Added focused domain tests for canonical identifiers, context/citation references, pass/fail threshold semantics, serialization, immutability, and invalid score handling.

Verification:

- `uv run ruff check domain/evaluation tests/unit/domain/test_evaluation_models.py --fix`
- `uv run ruff format domain/evaluation tests/unit/domain/test_evaluation_models.py`
- `uv run mypy domain/evaluation tests/unit/domain/test_evaluation_models.py --explicit-package-bases`
- `uv run pytest -q tests/unit/domain/test_evaluation_models.py`

Result: all focused checks passed.


### Step 3 — Add PostgreSQL evaluation persistence

Status: Completed.

Changes:

- Added first-class SQLAlchemy evaluation persistence models for `evaluation_datasets`, `evaluation_cases`, `evaluation_runs`, `evaluation_metric_results`, and `evaluation_artifacts`.
- Added the Alembic migration `20260714_000001_add_evaluation_persistence.py` with the new evaluation tables, canonical columns, constraints, indexes, and foreign-key relationships.
- Added typed persistence-boundary records and repository contracts under `core.storage.persistence.evaluation`.
- Added `PostgresEvaluationPersistenceRepository` for typed PostgreSQL upserts, reads, metric-result listing, artifact listing, and bundle persistence.
- Registered the evaluation models and repository in the existing database and repository package exports.
- Added focused tests for database model coverage, persistence record validation, domain-to-persistence conversion, and metadata registration.

Verification:

- `uv run ruff check core/database/models/evaluation.py core/database/models/__init__.py core/storage/persistence/evaluation core/storage/persistence/repositories/postgres_evaluation_persistence_repository.py core/storage/persistence/repositories/__init__.py tests/unit/core/database/test_evaluation_persistence_models.py tests/unit/core/database/test_evaluation_persistence_records.py migrations/versions/20260714_000001_add_evaluation_persistence.py --fix`
- `uv run ruff format core/database/models/evaluation.py core/database/models/__init__.py core/storage/persistence/evaluation core/storage/persistence/repositories/postgres_evaluation_persistence_repository.py core/storage/persistence/repositories/__init__.py tests/unit/core/database/test_evaluation_persistence_models.py tests/unit/core/database/test_evaluation_persistence_records.py migrations/versions/20260714_000001_add_evaluation_persistence.py`
- `uv run mypy core/database/models/evaluation.py core/database/models/__init__.py core/storage/persistence/evaluation core/storage/persistence/repositories/postgres_evaluation_persistence_repository.py core/storage/persistence/repositories/__init__.py tests/unit/core/database/test_alembic_foundation.py tests/unit/core/database/test_evaluation_persistence_models.py tests/unit/core/database/test_evaluation_persistence_records.py --explicit-package-bases`
- `uv run pytest -q tests/unit/core/database/test_alembic_foundation.py tests/unit/core/database/test_evaluation_persistence_models.py tests/unit/core/database/test_evaluation_persistence_records.py`
- `uv run alembic heads`
- `uv run python - <<'PY' ...` metadata/import smoke check confirmed all five evaluation tables are registered in `Base.metadata` and the repository export imports successfully.
- `uv run ruff check config/settings.py domain/evaluation core/database/models/evaluation.py core/database/models/__init__.py core/storage/persistence/evaluation core/storage/persistence/repositories/postgres_evaluation_persistence_repository.py core/storage/persistence/repositories/__init__.py tests/unit/config/test_deepeval_evaluation_settings.py tests/unit/domain/test_evaluation_models.py tests/unit/core/database/test_alembic_foundation.py tests/unit/core/database/test_evaluation_persistence_models.py tests/unit/core/database/test_evaluation_persistence_records.py migrations/versions/20260714_000001_add_evaluation_persistence.py`
- `uv run mypy config/settings.py domain/evaluation core/database/models/evaluation.py core/database/models/__init__.py core/storage/persistence/evaluation core/storage/persistence/repositories/postgres_evaluation_persistence_repository.py core/storage/persistence/repositories/__init__.py tests/unit/config/test_deepeval_evaluation_settings.py tests/unit/domain/test_evaluation_models.py tests/unit/core/database/test_alembic_foundation.py tests/unit/core/database/test_evaluation_persistence_models.py tests/unit/core/database/test_evaluation_persistence_records.py --explicit-package-bases`
- `uv run pytest -q tests/unit/config/test_deepeval_evaluation_settings.py tests/unit/domain/test_evaluation_models.py tests/unit/core/database/test_alembic_foundation.py tests/unit/core/database/test_evaluation_persistence_models.py tests/unit/core/database/test_evaluation_persistence_records.py`
- `timeout 120s uv run graphify update .`

Result: all focused checks passed; Alembic reports `8c0d1e2f3a4b` as the single head, and Graphify completed successfully with the existing SQL parser optional-dependency warning.

### Step 4 — Add DeepEval provider boundary

Status: Completed.

Changes:

- Added `integration.providers.llm_evaluation` as the canonical provider boundary for LLM-evaluation engines.
- Added typed provider contracts: `EvaluationMetricSpec`, `EvaluationProviderRequest`, `EvaluationProviderResult`, and `EvaluationProvider`.
- Added `DeepEvalEvaluationProvider` with an injected `DeepEvalMetricAdapter` seam so application services can depend on Polaris contracts and unit tests can avoid live judge-model calls.
- Added supported DeepEval metric names for `faithfulness`, `answer_relevancy`, `contextual_relevancy`, `contextual_precision`, `contextual_recall`, and `hallucination`.
- Added native DeepEval translation from `EvaluationCase` to `LLMTestCase`, metric construction, reason normalization, threshold/default-threshold handling, timeout enforcement, concurrency limiting, and provider telemetry wrapping.
- Normalized per-metric failures and timeouts into typed `EvaluationMetricResult` records with `EvaluationStatus.ERRORED` rather than leaking DeepEval exceptions into application-layer contracts.
- Added focused provider-boundary tests for contract validation, pass/fail scoring, default thresholds, error normalization, timeout behavior, concurrency limits, and explicit judge configuration.

Verification:

- `uv run ruff check integration/providers/llm_evaluation tests/unit/integration/providers/llm_evaluation --fix`
- `uv run ruff format integration/providers/llm_evaluation tests/unit/integration/providers/llm_evaluation`
- `uv run mypy integration/providers/llm_evaluation tests/unit/integration/providers/llm_evaluation --explicit-package-bases`
- `uv run pytest -q tests/unit/integration/providers/llm_evaluation`
- `uv run ruff check integration/providers/llm_evaluation tests/unit/integration/providers/llm_evaluation tests/unit/config/test_deepeval_evaluation_settings.py tests/unit/domain/test_evaluation_models.py --fix`
- `uv run ruff format integration/providers/llm_evaluation tests/unit/integration/providers/llm_evaluation tests/unit/config/test_deepeval_evaluation_settings.py tests/unit/domain/test_evaluation_models.py`
- `uv run mypy integration/providers/llm_evaluation tests/unit/integration/providers/llm_evaluation --explicit-package-bases`
- `uv run pytest -q tests/unit/config/test_deepeval_evaluation_settings.py tests/unit/domain/test_evaluation_models.py tests/unit/integration/providers/llm_evaluation`
- `timeout 120s uv run graphify update .`

Result: all focused checks passed; the provider boundary is ready for Step 5 application services without requiring application code to import DeepEval directly.

### Step 5 — Add evaluation application services

Status: Completed.

Changes:

- Added `application.evaluations` as the application-owned service package for canonical LLM-evaluation workflows.
- Added typed service contracts for case-building, dataset registration, evaluation-run execution, result retrieval, and Langfuse score projection.
- Added `EvaluationCaseBuilder` to construct canonical `EvaluationCase` objects from typed Polaris source data while preserving dataset, source-record, workflow, retrieval-context, citation, and Langfuse correlation fields.
- Added `EvaluationDatasetService` for registering and loading versioned evaluation dataset records through the canonical PostgreSQL repository contract.
- Added `EvaluationRunService` to persist datasets/cases/running runs, execute provider-backed evaluations, persist completed or errored runs, and persist normalized metric results without importing DeepEval in the application layer.
- Added `EvaluationResultService` to expose persisted run, metric-result, artifact, case, and dataset read APIs.
- Added `EvaluationLangfuseProjectionService` to convert persisted evaluation metric results into typed `AiEvaluationObservation` score projections for Langfuse while preserving PostgreSQL as the canonical evaluation store and treating projection failures as non-destructive.
- Added focused unit tests for case construction, dataset registration, run/result persistence, provider-failure normalization, result retrieval, and Langfuse projection success/failure behavior.

Verification:

- `uv run ruff check application/evaluations tests/unit/application/evaluations --fix`
- `uv run ruff format application/evaluations tests/unit/application/evaluations`
- `uv run mypy application/evaluations tests/unit/application/evaluations --explicit-package-bases`
- `uv run pytest -q tests/unit/application/evaluations`
- `uv run pytest -q tests/unit/config/test_deepeval_evaluation_settings.py tests/unit/domain/test_evaluation_models.py tests/unit/core/database/test_evaluation_persistence_models.py tests/unit/core/database/test_evaluation_persistence_records.py tests/unit/integration/providers/llm_evaluation tests/unit/application/evaluations`
- `timeout 120s uv run graphify update .`

Result: all focused checks passed; application services now provide the typed Polaris boundary needed for Step 6 RAG evaluation metric definitions without allowing business logic to import DeepEval directly.

### Step 6 — Define RAG evaluation metrics

Status: Completed.

Changes:

- Added `application.evaluations.rag_evaluation_metrics` as the canonical versioned RAG evaluation metric profile.
- Defined the initial built-in DeepEval metric set: `faithfulness`, `answer_relevancy`, `contextual_relevancy`, `contextual_precision`, `contextual_recall`, and `hallucination`.
- Defined Polaris custom G-Eval rubric metrics: `citation_support`, `financial_answer_quality`, `risk_explanation_quality`, `unsupported_claim_penalty`, `refusal_correctness`, and `prompt_injection_resistance`.
- Added threshold-versioning through `RAG_EVALUATION_THRESHOLD_PROFILE_VERSION` and `rag_threshold_profile()` so RAG quality policy is serializable and persistence-ready instead of being test-only constants.
- Extended `EvaluationMetricSpec` with typed custom metric rubric fields: `criteria` and `evaluation_steps`.
- Extended the DeepEval provider to build custom G-Eval metrics from Polaris metric specs while preserving the existing provider boundary.
- Normalized the native DeepEval `hallucination` metric into Polaris higher-is-better score semantics by inverting both the DeepEval execution threshold and returned raw score.
- Added focused unit coverage for required metric definitions, threshold policy, persistence-ready profile serialization, custom rubric validation, metric spec validation, and hallucination score normalization.

Verification:

- `uv run ruff check application/evaluations integration/providers/llm_evaluation tests/unit/application/evaluations tests/unit/integration/providers/llm_evaluation --fix`
- `uv run ruff format application/evaluations integration/providers/llm_evaluation tests/unit/application/evaluations tests/unit/integration/providers/llm_evaluation`
- `uv run mypy application/evaluations integration/providers/llm_evaluation tests/unit/application/evaluations tests/unit/integration/providers/llm_evaluation --explicit-package-bases`
- `uv run pytest -q tests/unit/application/evaluations tests/unit/integration/providers/llm_evaluation`
- `uv run pytest -q tests/unit/config/test_deepeval_evaluation_settings.py tests/unit/domain/test_evaluation_models.py tests/unit/core/database/test_evaluation_persistence_models.py tests/unit/core/database/test_evaluation_persistence_records.py tests/unit/integration/providers/llm_evaluation tests/unit/application/evaluations`
- `uv run graphify update .`

Result: all focused checks passed; RAG evaluation now has versioned metric definitions, thresholds, custom G-Eval rubrics, and provider support for executing those metrics through the canonical DeepEval boundary.

### Step 7 — Define intelligence evaluation metrics

Status: Completed.

Changes:

- Added versioned intelligence-evaluation threshold policy through `INTELLIGENCE_EVALUATION_THRESHOLD_PROFILE_VERSION` and `intelligence_threshold_profile()`.
- Added canonical structured-output intelligence metric definitions for `strategy_synthesis_quality`, `recommendation_rationale_quality`, `report_completeness`, `risk_assessment_quality`, `portfolio_context_alignment`, `reasoning_consistency`, and `unsupported_financial_claims`.
- Defined all intelligence metrics as Polaris custom G-Eval rubric metrics so they evaluate structured Polaris outputs rather than arbitrary legacy payloads.
- Added `intelligence_evaluation_metric_specs()` with optional target-type filtering for `strategy_synthesis`, `recommendation_explanation`, `morning_report`, and related intelligence target types.
- Exported the new intelligence metric profile APIs from `application.evaluations`.
- Added focused unit coverage for required metric names, GEval rubric enforcement, non-RAG target binding, target-specific metric filtering, threshold/version preservation, and persistence-ready profile serialization.

Verification:

- `uv run ruff check application/evaluations tests/unit/application/evaluations --fix`
- `uv run ruff format application/evaluations tests/unit/application/evaluations`
- `uv run mypy application/evaluations tests/unit/application/evaluations --explicit-package-bases`
- `uv run pytest -q tests/unit/application/evaluations`
- `uv run pytest -q tests/unit/config/test_deepeval_evaluation_settings.py tests/unit/domain/test_evaluation_models.py tests/unit/core/database/test_evaluation_persistence_models.py tests/unit/core/database/test_evaluation_persistence_records.py tests/unit/integration/providers/llm_evaluation tests/unit/application/evaluations`
- `uv run graphify update .`

Result: all focused checks passed; intelligence workflows now have versioned, typed DeepEval/G-Eval metric definitions ready for dataset wiring and run execution in later steps.

### Step 8 — Integrate with Langfuse

Status: Completed.

Changes:

- Wired `EvaluationRunService` to require a score-projection boundary and call it after canonical PostgreSQL evaluation records are persisted.
- Extended `EvaluationRunServiceResult` with an optional `langfuse_projection_result` so callers can inspect projection outcomes without making Langfuse canonical storage.
- Preserved PostgreSQL as the source of truth: projection errors are logged with tracebacks and converted into failed projection summaries without invalidating persisted evaluation runs or metric records.
- Kept Langfuse projection idempotent by relying on stable `AiEvaluationObservation.idempotency_key()` values derived from canonical run, case, observation, and score fields.
- Strengthened Langfuse projection coverage for required score fields: metric name, score, threshold, pass/fail result, reason, evaluator model/provider, dataset/case/run IDs, and related trace/observation IDs.
- Added focused tests for post-persistence projection, non-destructive projection failure handling, full score/correlation mapping, and stable retry idempotency keys.

Verification:

- `uv run ruff check application/evaluations tests/unit/application/evaluations --fix`
- `uv run ruff format application/evaluations tests/unit/application/evaluations`
- `uv run mypy application/evaluations tests/unit/application/evaluations --explicit-package-bases`
- `uv run pytest -q tests/unit/application/evaluations`
- `uv run pytest -q tests/unit/config/test_deepeval_evaluation_settings.py tests/unit/domain/test_evaluation_models.py tests/unit/core/database/test_evaluation_persistence_models.py tests/unit/core/database/test_evaluation_persistence_records.py tests/unit/integration/providers/llm_evaluation tests/unit/application/evaluations`
- `uv run graphify update .`

Result: all focused checks passed; DeepEval evaluation runs now persist canonical PostgreSQL records first and then project typed, retry-safe score observations into the Langfuse AI-observability boundary.

### Step 9 — Add evaluation datasets

Status: Completed.

Changes:

- Added `application.evaluations.evaluation_datasets` as the canonical application-owned dataset catalog for Polaris LLM evaluation workflows.
- Defined the required versioned dataset set: `golden_rag_questions`, `rag_citation_support`, `rag_security_prompt_injection`, `morning_report_quality`, `strategy_synthesis_quality`, `recommendation_explanations`, `mcp_tool_responses`, and `agent_task_completion`.
- Added `EvaluationDatasetDefinition` and helper APIs for listing, filtering, resolving, and converting canonical dataset definitions into `EvaluationDatasetRegistrationRequest` objects.
- Promoted dataset source lineage and deterministic fixture linkage into first-class PostgreSQL-backed evaluation dataset fields rather than storing them as generic metadata.
- Preserved case-level `source_record_ids` as a separate canonical field for concrete evaluation cases, avoiding conflation between dataset provenance and individual source records.
- Extended dataset registration, persistence records, SQLAlchemy models, repository mapping, and the evaluation migration to include dataset `source_lineage` and `deterministic_fixture_uri`.
- Added focused unit coverage for canonical dataset coverage, versioning, tags, target-type filtering, source lineage, fixture URI preservation, dataset registration, and persistence schema/record fields.

Verification:

- `uv run ruff check application/evaluations core/database/models/evaluation.py core/storage/persistence/evaluation core/storage/persistence/repositories/postgres_evaluation_persistence_repository.py tests/unit/application/evaluations tests/unit/core/database/test_evaluation_persistence_models.py tests/unit/core/database/test_evaluation_persistence_records.py migrations/versions/20260714_000001_add_evaluation_persistence.py --fix`
- `uv run ruff format application/evaluations core/database/models/evaluation.py core/storage/persistence/evaluation core/storage/persistence/repositories/postgres_evaluation_persistence_repository.py tests/unit/application/evaluations tests/unit/core/database/test_evaluation_persistence_models.py tests/unit/core/database/test_evaluation_persistence_records.py migrations/versions/20260714_000001_add_evaluation_persistence.py`
- `uv run mypy application/evaluations core/database/models/evaluation.py core/storage/persistence/evaluation core/storage/persistence/repositories/postgres_evaluation_persistence_repository.py tests/unit/application/evaluations tests/unit/core/database/test_evaluation_persistence_models.py tests/unit/core/database/test_evaluation_persistence_records.py --explicit-package-bases`
- `uv run pytest -q tests/unit/application/evaluations tests/unit/core/database/test_evaluation_persistence_models.py tests/unit/core/database/test_evaluation_persistence_records.py`
- `uv run pytest -q tests/unit/config/test_deepeval_evaluation_settings.py tests/unit/domain/test_evaluation_models.py tests/unit/core/database/test_evaluation_persistence_models.py tests/unit/core/database/test_evaluation_persistence_records.py tests/unit/integration/providers/llm_evaluation tests/unit/application/evaluations`
- `uv run pytest -q tests/unit/core/database/test_alembic_foundation.py`
- `uv run graphify update .`

Result: all focused checks passed; Polaris now has a canonical versioned evaluation dataset catalog with first-class provenance and deterministic fixture references ready for Step 10 dataset seeding/registration workflows.

### Step 10 — Add CLI commands

Status: Completed.

Changes:

- Added `polaris eval` as the canonical CLI command group for LLM evaluation operations.
- Added focused subcommands:
  - `polaris eval status`
  - `polaris eval datasets list`
  - `polaris eval run --dataset <name>`
  - `polaris eval run-rag --case <case-id>`
  - `polaris eval run-latest-rag`
  - `polaris eval results --run <run-id>`
- Added `EvaluationCommandService` as the CLI-facing application boundary so commands resolve canonical evaluation services through Dishka request scopes and never call DeepEval directly.
- Added request-scoped DI for evaluation services, the DeepEval provider boundary, Langfuse score projection, and the PostgreSQL evaluation repository.
- Moved the evaluation persistence service contract to `core.storage.persistence.evaluation` and added first-class repository read methods for persisted cases by dataset and target type.
- Added evaluation result-service list methods used by the CLI for dataset and latest-case selection.
- Added professional human-readable renderers for evaluation status, datasets, run summaries, and persisted results.
- Added focused CLI, command-service, application-service, and CLI help coverage.

Verification:

- `uv run ruff check . --fix`
- `uv run ruff format .`
- `uv run mypy . --explicit-package-bases`
- `uv run pytest -q tests/unit/interfaces/cli/test_evaluation_command_service.py tests/unit/interfaces/cli/test_evaluation_command.py tests/unit/interfaces/cli/test_cli.py tests/unit/application/evaluations/test_evaluation_services.py`
- `POLARIS_POSTGRES_PASSWORD=<redacted> uv run polaris eval --help`
- `uv run graphify update .`

Result: all focused checks passed; Polaris now exposes canonical DeepEval-backed evaluation workflows through the CLI while preserving the service → provider → client boundary and PostgreSQL as the durable source of truth.

### Step 11 — Add CI evaluation suite

Status: Completed.

Changes:

- Added `tests/evaluation/` as the dedicated Polaris CI evaluation suite with marker-based grouping for smoke, RAG regression, prompt regression, strategy synthesis, security, and live DeepEval tests.
- Added evaluation-suite fixtures and helper contracts for loading deterministic JSONL cases, building canonical `EvaluationCase` objects, running evaluation-service smoke tests with an in-memory repository, and avoiding live judge-model requirements in normal CI.
- Added deterministic fixture files for canonical datasets: golden RAG questions, citation support, prompt-injection security, morning report quality, strategy synthesis quality, recommendation explanations, MCP tool responses, and agent task completion.
- Added CI smoke coverage that runs the canonical `EvaluationRunService` through a deterministic provider, repository, and projection boundary without importing or calling live DeepEval judge models.
- Added RAG regression, prompt regression, strategy synthesis, and security tests that verify dataset definitions, fixture linkage, target types, threshold profiles, metric catalogs, rubric fields, and prompt-injection safety coverage.
- Added a live DeepEval smoke test that is skipped by default and requires explicit `POLARIS_RUN_LIVE_EVALS=true` plus `POLARIS_DEEPEVAL_ENABLED`, `POLARIS_DEEPEVAL_JUDGE_PROVIDER`, and `POLARIS_DEEPEVAL_JUDGE_MODEL`; if `POLARIS_EVAL_REQUIRED=true`, missing live config fails clearly instead of silently skipping.
- Documented the evaluation suite, marker groups, default CI behavior, live judge-model opt-in, and release-gate usage in `tests/evaluation/README.md`.

Verification:

- `uv run ruff check tests/evaluation --fix`
- `uv run ruff format tests/evaluation`
- `uv run pytest -q tests/evaluation -m "not live_deepeval"`
- `uv run mypy tests/evaluation --explicit-package-bases`
- `uv run pytest -q tests/evaluation`
- `uv run pytest -q tests/evaluation -m live_deepeval`
- `uv run ruff check tests/evaluation`
- `uv run ruff format tests/evaluation --check`
- `timeout 120s uv run graphify update .`

Result: all focused checks passed. The non-live CI evaluation suite reports `10 passed, 1 deselected`; the full suite reports `10 passed, 1 skipped`; and the live DeepEval marker reports `1 skipped, 10 deselected` with the expected explicit configuration message.

### Step 12 — Add async evaluation jobs

Status: Completed.

Changes:

- Added `application.evaluations.evaluation_jobs` as the canonical application-level async job contract and processor for DeepEval evaluation and Langfuse score-projection work.
- Added typed job contracts: `EvaluationJobType`, `EvaluationJobStatus`, `EvaluationJobRequest`, `EvaluationJobResult`, and `EvaluationJobBatchResult`.
- Supported the required job types: `evaluate_rag_result`, `evaluate_strategy_output`, `evaluate_report`, `project_eval_scores_to_langfuse`, and `retry_failed_eval_projection`.
- Kept job execution queue-agnostic and compatible with the existing worker pattern: durable queues, schedulers, CLI commands, and future MCP boundaries can submit typed job requests without creating a second evaluation runtime.
- Added `EvaluationJobProcessor` to load persisted evaluation cases/runs through `EvaluationResultService`, run evaluations through `EvaluationRunService`, and project persisted scores through the existing Langfuse score-projection boundary.
- Added target-specific metric selection so RAG jobs use RAG metric policy, strategy jobs use structured strategy metrics, and report jobs use morning-report metrics.
- Added validation that evaluation jobs require a case plus evaluator identity, projection jobs require a run, and mismatched job/case target types fail deterministically instead of silently evaluating the wrong output type.
- Registered the job processor in the request-scoped evaluation DI provider and exported the job contracts from `application.evaluations`.
- Added focused unit coverage for RAG evaluation jobs, strategy-output evaluation jobs, report evaluation jobs, persisted score projection, failed-projection retry routing, request validation, and target mismatch failure handling.

Verification:

- `uv run ruff check application/evaluations/evaluation_jobs.py application/evaluations/di.py application/evaluations/__init__.py tests/unit/application/evaluations/test_evaluation_jobs.py --fix`
- `uv run ruff format application/evaluations/evaluation_jobs.py application/evaluations/di.py application/evaluations/__init__.py tests/unit/application/evaluations/test_evaluation_jobs.py`
- `uv run pytest -q tests/unit/application/evaluations/test_evaluation_jobs.py`
- `uv run mypy application/evaluations tests/unit/application/evaluations/test_evaluation_jobs.py --explicit-package-bases`
- `uv run pytest -q tests/unit/application/evaluations tests/evaluation -m "not live_deepeval"`
- `uv run ruff check application/evaluations tests/unit/application/evaluations tests/evaluation --fix`
- `uv run ruff format application/evaluations tests/unit/application/evaluations tests/evaluation --check`
- `uv run mypy application/evaluations tests/unit/application/evaluations tests/evaluation --explicit-package-bases`
- `timeout 120s uv run graphify update .`

Result: all focused checks passed. The async evaluation job layer now provides the required production-flow handoff point: persisted workflow/curated outputs can produce canonical evaluation cases, enqueue typed evaluation jobs, run DeepEval asynchronously through the provider boundary, persist results in PostgreSQL, and project scores to Langfuse through the existing durable AI-observability path.

### Step 13 — Add observability for evaluation

Status: Completed.

Changes:

- Added `EvaluationTelemetry` as the canonical application-level observability boundary for DeepEval evaluation workflows.
- Recorded evaluation lifecycle events for run started, completed, and failed states without adding a parallel telemetry stack.
- Added evaluation metrics for run volume, run duration, evaluated case count, metric execution latency, metric execution failures, threshold failures, judge-model failures, dataset load failures, Langfuse projection failures, retry counts, and skipped cases.
- Wired evaluation telemetry into `EvaluationRunService` so evaluation runs, provider failures, metric results, threshold failures, and Langfuse projection failures are observable from the canonical service boundary.
- Wired evaluation telemetry into `EvaluationJobProcessor` so async evaluation jobs record retry counts, skipped projection cases, and dataset load failures.
- Registered `EvaluationTelemetry` in the evaluation DI provider using the existing `ObservabilityManager`.
- Added focused unit coverage for evaluation telemetry event and metric emission.
- Added service-level coverage proving `EvaluationRunService` emits evaluation lifecycle events and metrics through the injected telemetry boundary.

Verification:

- `uv run ruff check application/evaluations/evaluation_telemetry.py application/evaluations/evaluation_run_service.py application/evaluations/evaluation_jobs.py application/evaluations/di.py application/evaluations/__init__.py tests/unit/application/evaluations/test_evaluation_telemetry.py --fix`
- `uv run ruff format application/evaluations/evaluation_telemetry.py application/evaluations/evaluation_run_service.py application/evaluations/evaluation_jobs.py application/evaluations/di.py application/evaluations/__init__.py tests/unit/application/evaluations/test_evaluation_telemetry.py`
- `uv run pytest -q tests/unit/application/evaluations/test_evaluation_telemetry.py tests/unit/application/evaluations/test_evaluation_services.py tests/unit/application/evaluations/test_evaluation_jobs.py`
- `uv run pytest -q tests/unit/application/evaluations/test_evaluation_services.py tests/unit/application/evaluations/test_evaluation_telemetry.py`
- `uv run mypy application/evaluations tests/unit/application/evaluations/test_evaluation_telemetry.py tests/unit/application/evaluations/test_evaluation_services.py tests/unit/application/evaluations/test_evaluation_jobs.py --explicit-package-bases`
- `uv run pytest -q tests/unit/application/evaluations tests/evaluation -m "not live_deepeval"`
- `uv run ruff check application/evaluations tests/unit/application/evaluations tests/evaluation --fix`
- `uv run ruff format application/evaluations tests/unit/application/evaluations tests/evaluation --check`
- `uv run mypy application/evaluations tests/unit/application/evaluations tests/evaluation --explicit-package-bases`
- `timeout 120s uv run mypy . --explicit-package-bases`
- `uv run ruff check . --fix`
- `uv run ruff format . --check`
- `timeout 120s uv run graphify update .`

Result: all focused checks passed. DeepEval evaluation runs and async evaluation jobs now emit canonical events and metrics at the application evaluation boundary while keeping telemetry failures non-fatal to persisted evaluation results.

### Step 14 — Add documentation

Status: Completed.

Changes:

- Added `docs/llm_evaluation.md` as the canonical DeepEval/Polaris LLM evaluation architecture guide.
- Documented DeepEval's role as the canonical LLM evaluation engine, with PostgreSQL as the system of record and Langfuse as the AI-observability score projection.
- Documented the evaluation architecture flow, ownership model, supported target types, dataset catalog, metric catalog, threshold policy, local CLI workflow, async job workflow, CI workflow, live service requirements, and privacy/redaction rules.
- Updated `docs/langfuse_ai_observability.md` to describe the completed DeepEval relationship, durable PostgreSQL-first evaluation records, score projection boundary, and rule that evaluator code must not call Langfuse directly.
- Updated `docs/platform_rag_pipeline.md` with the RAG evaluation and quality-gate flow, including RAG target types, metric families, threshold rationale, and Langfuse projection relationship.
- Updated `docs/testing_guide.md` with DeepEval/evaluation test commands, live-test requirements, Docker/service matrix entries, and DeepEval environment variables.
- Checked the new and updated docs for obvious credential leakage; only redacted placeholders were present.

Verification:

- `git diff --check`
- `uv run pytest -q tests/evaluation -m "not live_deepeval"`

Result: documentation now describes the completed Polaris DeepEval evaluation architecture and its relationship to Langfuse, RAG, CI, local workflows, thresholds, live services, and privacy boundaries. The focused non-live evaluation suite passed with `10 passed, 1 deselected`.
