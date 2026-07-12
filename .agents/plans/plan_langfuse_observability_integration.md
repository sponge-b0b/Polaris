  # Polaris Langfuse AI Observability Integration Plan

  ## Summary

  Integrate Langfuse as a required AI-observability projection for Polaris RAG and intelligence workflows while preserving Polaris’s canonical telemetry stack.

  Langfuse will complement—not replace—Polaris observability:

  Polaris canonical telemetry, traces, metrics, logs, PostgreSQL records
          ↓
  Required AI-observability projection boundary
          ↓
  Langfuse traces, generations, prompts, datasets, scores, evals

  Canonical Polaris systems remain authoritative:

  - PostgreSQL remains the durable system of record.
  - OpenTelemetry + Jaeger remain infrastructure/runtime tracing.
  - Prometheus + Grafana remain operational metrics/dashboards.
  - Langfuse becomes the required AI-engineering observability surface for LLM/RAG behavior.

  This plan is based on Langfuse’s current documented design for LLM observability, tracing, prompt management, datasets, evaluations, and OpenTelemetry integration. Relevant references:
  https://langfuse.com/docs
  https://langfuse.com/docs/observability/data-model
  https://langfuse.com/integrations/native/opentelemetry
  https://langfuse.com/docs/evaluation/experiments/datasets
  https://langfuse.com/self-hosting

  ## Core Architecture Decisions

  1. Langfuse is required for AI observability
      - Production AI-capable deployments must configure Langfuse.
      - Missing Langfuse configuration should fail AI-observability bootstrap validation, not silently degrade into no-op behavior.
      - Unit tests may use fake/in-memory sinks; production runtime must use a real Langfuse projection path.

  2. Polaris telemetry remains canonical
      - Do not replace existing logs, metrics, OpenTelemetry traces, Jaeger, Prometheus, Grafana, or PostgreSQL telemetry persistence.
      - Langfuse is a specialized AI projection, not the canonical telemetry store.

  3. OpenTelemetry-first integration
      - Prefer Langfuse’s OpenTelemetry-compatible ingestion path for trace/span/generation projection.
      - Use Langfuse SDK features only where OpenTelemetry alone cannot cleanly express Langfuse-specific concepts such as prompt links, scores, datasets, or evaluation runs.

  4. Single Polaris-owned AI observability boundary
      - Do not call Langfuse directly from RAG services, intelligence agents, providers, workflow nodes, or CLI code.
      - Add a Polaris-owned AI observability abstraction that maps typed Polaris AI events to Langfuse.

  5. Self-hosted-first production posture
      - Default recommendation is self-hosted Langfuse because Polaris handles portfolio, recommendation, strategy, and potentially customer-sensitive data.
      - Langfuse Cloud may be supported only after explicit data-governance approval.

  6. Redaction and capture controls are mandatory
      - Required Langfuse projection does not mean unrestricted prompt/response capture.
      - Prompt, response, retrieved context, portfolio, and user-input capture must pass through explicit redaction and capture policy.
      - Secrets, credentials, raw authenticated URLs, broker identifiers, and unapproved PII must never be exported.

  ## Key Implementation Changes

  ### 1. Add Langfuse deployment and configuration

  Introduce required Langfuse configuration under Polaris settings:

  POLARIS_LANGFUSE_HOST
  POLARIS_LANGFUSE_PUBLIC_KEY
  POLARIS_LANGFUSE_SECRET_KEY
  POLARIS_LANGFUSE_ENVIRONMENT
  POLARIS_LANGFUSE_RELEASE
  POLARIS_LANGFUSE_SAMPLE_RATE
  POLARIS_LANGFUSE_CAPTURE_PROMPTS
  POLARIS_LANGFUSE_CAPTURE_RESPONSES
  POLARIS_LANGFUSE_CAPTURE_CONTEXTS
  POLARIS_LANGFUSE_CAPTURE_USER_INPUT
  POLARIS_LANGFUSE_REDACTION_MODE

  Required behavior:

  - AI-capable production bootstrap validates host and credentials.
  - Local/test can inject fake sinks.
  - Documentation should prefer self-hosted Langfuse deployment.
  - Secrets must be environment-only and never committed.

  ### 2. Create canonical AI observability contracts

  Add typed internal contracts for AI observability projection.

  Recommended models:

  AiObservation
  AiObservationType
  AiGenerationObservation
  AiRetrievalObservation
  AiRerankingObservation
  AiEvaluationObservation
  AiPromptVersionReference
  AiObservabilityCapturePolicy
  AiObservabilityExportResult

  These contracts should represent Polaris concepts first, then map outward to Langfuse.

  DeepEval readiness is part of this contract design. The initial Langfuse
  contracts must anticipate the later DeepEval integration so evaluation
  results can be projected without adding a second Langfuse path or reshaping
  the core AI-observability model. Include first-class fields for:

  - AiEvaluationObservation records.
  - AiObservabilityExportResult status and idempotency details.
  - AiPromptVersionReference for generation and evaluation provenance.
  - dataset, case, and run identifiers.
  - score projection fields, including metric name, score, threshold, pass/fail,
    reason, and evaluator model/provider.
  - trace and observation correlation IDs linking Polaris execution, Langfuse
    observations, and future DeepEval evaluation records.

  These fields prevent rework when DeepEval becomes the canonical LLM
  evaluation engine and begins projecting persisted evaluation scores and
  reasons into Langfuse.

  Primary observation categories:

  - rag.query
  - rag.routing
  - rag.retrieval.vector
  - rag.retrieval.graph
  - rag.retrieval.fusion
  - rag.reranking
  - rag.crag
  - rag.self_rag
  - rag.generation
  - rag.security
  - rag.answer_quality
  - intelligence.agent_reasoning
  - intelligence.strategy_synthesis
  - intelligence.report_generation
  - intelligence.recommendation_explanation

  ### 3. Add Langfuse projection sink

  Implement a Polaris-owned projection boundary:

  ApplicationRagTelemetry / IntelligenceTelemetry
          ↓
  AiObservabilityProjector
          ↓
  LangfuseAiObservabilitySink

  Rules:

  - The sink owns Langfuse-specific mapping.
  - Application code emits typed AI observations only.
  - The sink maps Polaris trace IDs, execution IDs, workflow names, node names, model names, prompt versions, and evaluation scores into Langfuse fields.
  - Langfuse export failures are visible through Polaris telemetry and retry handling.

  ### 4. Add durable export/retry handling

  Because Langfuse is required, projection should not be best-effort-only.

  Add a durable projection path:

  AI observation emitted
  → sanitize/redact
  → persist export job or reuse approved telemetry persistence boundary
  → export to Langfuse
  → mark exported or failed
  → retry failed exports

  Recommended behavior:

  - Missing configuration: bootstrap failure for AI-capable production deployments.
  - Transient Langfuse outage: workflow can complete, but export jobs remain failed/pending and visible.
  - Repeated export failure: emit Polaris telemetry, metrics, and logs.
  - Projection retry must not duplicate Langfuse observations; use stable idempotency keys.

  ### 5. Instrument RAG pipeline stages

  Instrument the full RAG execution path through the new AI observability boundary:

  RagService.run()
  → query routing
  → HyDE / rewrite where used
  → vector retrieval
  → graph retrieval
  → fusion
  → parent expansion
  → reranking
  → CRAG evaluation
  → Self-RAG reflection
  → secure generation
  → answer quality/security evaluation

  For each stage capture:

  - trace correlation
  - stage name
  - model/provider name
  - latency
  - token/cost metadata where available
  - input/output shape
  - sanitized prompt/response if policy permits
  - selected context IDs
  - retrieval scores
  - reranking scores
  - citations
  - quality decisions
  - failure/degradation status

  Do not export raw retrieved documents or full portfolio data unless policy explicitly allows it.

  ### 6. Instrument intelligence workflows

  Extend AI observability to intelligence workflows after RAG is covered.

  Initial target areas:

  - strategy synthesis
  - structured-hypothesis generation/evaluation
  - recommendation explanation
  - report-generation LLM calls
  - risk/reviewer agents if LLM-backed
  - future customer/internal AI agent workflows

  Each intelligence observation should include:

  - workflow name
  - execution ID
  - node name
  - agent/component name
  - prompt version
  - model name
  - sanitized inputs
  - generated reasoning summary or response
  - confidence/evaluation scores where available
  - source record IDs and citation IDs where relevant

  ### 7. Add prompt management strategy

  Use Langfuse prompt management deliberately, without creating split-brain prompt ownership.

  Recommended long-term policy:

  Polaris owns production prompt governance.
  Langfuse supports prompt authoring, experimentation, comparison, and observability.
  Production workflows reference pinned prompt versions.
  Prompt promotion requires an explicit Polaris-side approval/sync step.

  Implementation requirements:

  - Add typed PromptVersionReference.
  - Record prompt name/version/hash on every AI generation observation.
  - Add a promotion workflow for moving evaluated Langfuse prompts into Polaris-approved production configuration.
  - Prevent runtime use of unpinned mutable prompt names in production.
  - Keep source-controlled fallback prompts for deterministic tests and disaster recovery.

  ### 8. Add datasets and evaluation workflows

  Use Langfuse datasets/evals for AI quality engineering.

  Create dataset categories:

  - golden RAG questions
  - expected citation tests
  - hallucination and unsupported-claim tests
  - strategy explanation regression cases
  - morning-report QA cases
  - security/prompt-injection cases
  - retrieval recall and reranking quality cases

  Evaluation outputs should include:

  - answer correctness
  - citation support
  - retrieval relevance
  - groundedness
  - refusal correctness
  - prompt-injection resistance
  - strategy rationale quality
  - report completeness
  - latency/cost regressions

  Polaris should continue to own canonical test fixtures and curated records. Langfuse datasets are AI-evaluation projections and experiment surfaces.

  ### 9. Add operational visibility

  Expose Langfuse projection health through existing Polaris observability.

  Add metrics/logs/traces for:

  - observations created
  - observations exported
  - export failures
  - retry count
  - export latency
  - redaction failures
  - dropped fields by policy
  - prompt-version mismatches
  - dataset/eval run status

  Add CLI/status visibility where appropriate:

  polaris rag status
  polaris observability ai-status

  The exact CLI command can be finalized during implementation, but the capability should report whether Langfuse projection is configured, reachable, exporting, retrying, or degraded.

  ### 10. Add security, redaction, and retention policy

  Define explicit AI-observability data policy.

  Required controls:

  - redact secrets and credentials
  - redact broker/account identifiers
  - bound prompt/response/context payload sizes
  - optionally hash or omit user identifiers
  - sanitize retrieved context before export
  - separate metadata from sensitive content
  - configurable capture policy by environment
  - documented Langfuse retention expectations
  - self-hosted deployment guidance
  - Cloud-use warning and approval requirement

  Default production posture:

  Langfuse projection required.
  Sensitive raw payload capture restricted.
  Sanitized metadata and trace structure always exported.
  Prompt/response/context body export controlled by policy.

  ## Implementation Sequence

  ### Phase 1 — Architecture and configuration foundation

  - Add Langfuse settings and bootstrap validation.
  - Add AI observability config tests.
  - Document required production configuration.
  - Add fake test sink for unit/integration tests.

  ### Phase 2 — Canonical AI observability contracts

  - Add typed AI observation models.
  - Include DeepEval-ready evaluation contracts from the start: AiEvaluationObservation, AiObservabilityExportResult, AiPromptVersionReference, dataset/case/run identifiers, score projection fields, and trace/observation correlation IDs.
  - Add capture/redaction policy models.
  - Add idempotency key generation.
  - Add mapping tests for RAG, intelligence, and future evaluation event types.

  ### Phase 3 — Langfuse sink and export path

  - Add Langfuse sink implementation.
  - Add OpenTelemetry-compatible mapping first.
  - Add SDK-specific mapping only for prompts, scores, datasets, or generation metadata where necessary.
  - Add durable retry/export status if existing telemetry persistence cannot safely represent projection state.

  ### Phase 4 — RAG pipeline instrumentation

  - Instrument RAG service orchestration.
  - Instrument routing, retrieval, reranking, CRAG, Self-RAG, generation, and quality/security checks.
  - Ensure each RAG stage emits once at the canonical owner.
  - Add focused tests verifying no duplicate observations.

  ### Phase 5 — Intelligence workflow instrumentation

  - Instrument strategy synthesis and structured-hypothesis workflows.
  - Instrument LLM-backed report/recommendation explanation paths.
  - Ensure workflow node outputs remain canonical evidence and Langfuse receives only AI-observability projections.

  ### Phase 6 — Prompt management integration

  - Add prompt version references to AI generation observations.
  - Add prompt sync/promotion policy.
  - Add production guard against unpinned mutable prompts.
  - Add documentation for prompt lifecycle.

  ### Phase 7 — Dataset and evaluation integration

  - Add dataset export/build services for curated RAG and intelligence evaluation cases.
  - Add eval-run projection into Langfuse.
  - Add quality score mapping.
  - Add regression datasets for RAG, citations, report QA, strategy rationale, and prompt-injection resistance.

  ### Phase 8 — Operations, retention, and documentation
  - Add metrics, logs, traces, and dashboard guidance.
  - Document local self-host setup.
  - Document production security posture.
  - Document retention and redaction responsibilities.
  - Update testing guide with Langfuse-required test categories.

  ## Test Plan

  ### Unit tests

  - Langfuse settings validation.
  - Redaction and capture policy behavior.
  - AI observation model validation, including DeepEval-ready evaluation, dataset, case, run, score, and correlation fields.
  - Langfuse mapping from Polaris observations.
  - Idempotency key generation.
  - Prompt version reference validation.
  - Dataset/eval score mapping.

  ### Integration tests

  - Fake Langfuse sink receives expected RAG observations.
  - RAG query emits one observation per canonical stage.
  - Intelligence workflow emits expected generation/evaluation observations.
  - Export retry records failures without losing observations.
  - Bootstrap fails when production AI observability requires Langfuse but config is missing.

  ### Live-service tests

  Require Langfuse service running:

  - export a RAG trace to Langfuse
  - export a generation observation
  - export scores/evals
  - confirm trace correlation with Polaris trace/execution IDs
  - confirm redaction policy prevents sensitive payload export

  ### Regression checks

  - Existing OpenTelemetry/Jaeger tests continue to pass.
  - Prometheus/Grafana metrics remain unchanged except for added AI-observability metrics.
  - PostgreSQL telemetry remains canonical.
  - RAG and intelligence workflow outputs do not depend on Langfuse as a source of truth.
  - No direct Langfuse imports appear outside the approved integration boundary.

  ## Assumptions and Defaults

  - Langfuse is required for production AI-observability projection.
  - Self-hosted Langfuse is the default recommended deployment.
  - Langfuse Cloud requires explicit governance approval before customer or portfolio data is exported.
  - Polaris remains the canonical owner of workflow evidence, telemetry records, curated records, prompts approved for production, and business outputs.
  - Langfuse receives AI-observability projections, prompt/eval metadata, traces, generations, datasets, and scores.
  - Prompt/response/context body capture is policy-controlled and redacted by default.
  - Export failures are visible and retryable but should not corrupt or replace valid Polaris workflow results.
  