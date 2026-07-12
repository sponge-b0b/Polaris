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
  