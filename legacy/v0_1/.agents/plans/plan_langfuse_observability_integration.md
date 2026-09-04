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

  7. A real Langfuse SDK-backed exporter is required
      - The Polaris-owned projection boundary is necessary but not sufficient for a complete integration.
      - Production must use the official `langfuse` Python package behind a narrow adapter that implements the existing `LangfuseExportClient` protocol.
      - RAG, intelligence, workflow, CLI, and core code must not import the Langfuse SDK directly.
      - The only approved direct Langfuse SDK import location is the application observability transport adapter and its tests.
      - The adapter must support durable queued exports, idempotency, trace/observation correlation, flush/shutdown behavior, and sanitized payload projection.

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

  ### 3B. Add concrete Langfuse SDK transport and production wiring

  The current projection boundary must be completed with a real Langfuse SDK-backed exporter.

  Required correction:

  - Add the official dependency with `uv add langfuse`.
  - Implement a concrete SDK adapter, for example `LangfuseSdkExportClient`, that satisfies the existing `LangfuseExportClient` protocol.
  - Keep the SDK isolated to the application observability transport boundary; no RAG, intelligence, workflow, CLI, provider, repository, or core module may import the SDK.
  - Wire production DI/bootstrap so configured AI-capable deployments use the durable queue plus SDK exporter, while tests can still inject fake or recording clients.
  - Map queued `LangfusePayload` records into Langfuse traces, observations/generations/spans, scores, prompt references, dataset/case/run identifiers, tags, release, environment, and metadata according to the approved capture policy.
  - Ensure export completion returns external Langfuse trace and observation IDs when available and persists them back to PostgreSQL.
  - Add explicit flush/shutdown behavior so queued SDK events are delivered before process exit where supported by the SDK.
  - Add dependency/version notes to documentation and keep secrets environment-only.

  This step is required before claiming the Langfuse integration is complete. The earlier protocol-based sink and durable queue are foundation work, not the final live Langfuse integration.

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

  ### Phase 3B — Required SDK-backed Langfuse transport correction

  - Run `uv add langfuse` and commit the dependency/lockfile update.
  - Implement the concrete `LangfuseSdkExportClient` behind the existing `LangfuseExportClient` protocol.
  - Wire the SDK client into the durable export worker path through DI/bootstrap without exposing SDK imports outside the application observability boundary.
  - Add fake-client unit tests, SDK-adapter mapping tests, bootstrap wiring tests, and an optional live Langfuse smoke test that is skipped unless Langfuse credentials/host are configured.
  - Update documentation to state that the integration is complete only when the SDK-backed exporter is configured and the export worker can flush queued observations to Langfuse.

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
  - Langfuse SDK adapter payload mapping using fake/mocked SDK clients.
  - Production DI/bootstrap selection of the SDK-backed exporter when Langfuse is configured.
  - Redaction and capture policy behavior.
  - AI observation model validation, including DeepEval-ready evaluation, dataset, case, run, score, and correlation fields.
  - Langfuse mapping from Polaris observations.
  - Idempotency key generation.
  - Prompt version reference validation.
  - Dataset/eval score mapping.

  ### Integration tests

  - Fake Langfuse sink receives expected RAG observations.
  - Durable export worker drains queued observations through the SDK-backed client.
  - SDK export success persists external Langfuse trace and observation IDs.
  - SDK export failure leaves retryable durable jobs and emits non-fatal Polaris telemetry.
  - RAG query emits one observation per canonical stage.
  - Intelligence workflow emits expected generation/evaluation observations.
  - Export retry records failures without losing observations.
  - Bootstrap fails when production AI observability requires Langfuse but config is missing.

  ### Live-service tests

  Require Langfuse service running:

  - validate the official `langfuse` SDK client can connect with configured host and credentials
  - export a RAG trace to Langfuse through the durable queue and SDK-backed exporter
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
  - `pyproject.toml` includes the official `langfuse` dependency before any live Langfuse integration is considered complete.

  ## Assumptions and Defaults

  - Langfuse is required for production AI-observability projection.
  - Self-hosted Langfuse is the default recommended deployment.
  - Langfuse Cloud requires explicit governance approval before customer or portfolio data is exported.
  - Polaris remains the canonical owner of workflow evidence, telemetry records, curated records, prompts approved for production, and business outputs.
  - Langfuse receives AI-observability projections, prompt/eval metadata, traces, generations, datasets, and scores.
  - Prompt/response/context body capture is policy-controlled and redacted by default.
  - Export failures are visible and retryable but should not corrupt or replace valid Polaris workflow results.
  - The official `langfuse` Python package is required for production export; protocol-only or fake-client implementations are not complete production integration.

## Required Plan Correction — SDK-backed exporter before continuing

The first five implementation steps established the Polaris-owned AI-observability contracts, mapping boundary, durable export queue, and RAG instrumentation. That work intentionally avoided direct SDK imports in RAG and core code. However, the plan must explicitly complete the live Langfuse integration by adding the official `langfuse` dependency and implementing a concrete SDK-backed exporter.

Next executable step:

- [x] **Step 5B — Add official Langfuse SDK exporter and production wiring**
  - Run `uv add langfuse`.
  - Implement the SDK-backed `LangfuseExportClient` adapter inside the application observability boundary.
  - Wire the adapter into the durable export worker path through DI/bootstrap.
  - Add unit, integration, and optional live-service tests proving queued observations export to Langfuse and persist external IDs.
  - Update documentation to distinguish the completed live SDK integration from fake/test sinks and protocol-only foundations.

After Step 5B is complete, resume the original plan with Phase 5 intelligence workflow instrumentation.

## Plan Numbering Reconciliation

The plan contains two overlapping labels: the numbered **Key Implementation Changes** steps (1-10) and the older **Implementation Sequence** phase labels (Phase 1-8). Going forward, execution follows the numbered Key Implementation Changes as the source of truth. Phase labels are retained only as historical grouping notes.

Current reconciled status:

| Numbered step | Canonical meaning | Reconciled status |
| --- | --- | --- |
| Step 1 | Langfuse deployment and configuration | Completed |
| Step 2 | Canonical AI observability contracts | Completed |
| Step 3 | Langfuse projection sink | Completed |
| Step 3B / Step 5B | Required official SDK-backed exporter correction | Completed |
| Step 4 | Durable export/retry handling | Completed |
| Step 5 | RAG pipeline instrumentation | Completed |
| Step 6 | Intelligence workflow instrumentation | Completed |
| Step 7 | Prompt management strategy | Completed |
| Step 8 | Datasets and evaluation workflows | Completed out of order; previously recorded as “Step 7 — Phase 7” |
| Step 9 | Operational visibility | Completed |
| Step 10 | Security, redaction, and retention policy | Completed |

The previous Step Results entries named “Step 7 — Phase 7” and “Step 8 — Phase 8” are preserved as historical records. Future execution and result headings must use the numbered Key Implementation Changes. Step 10 is now completed; the Langfuse AI-observability integration plan is complete pending any separate live-service smoke test you explicitly request.

## Step Results

### Step 1 — Phase 1: Architecture and configuration foundation

Completed.

Changes made:

- Added Langfuse AI-observability settings to `config/settings.py` with Polaris-prefixed environment variable aliases:
  - `POLARIS_LANGFUSE_HOST`
  - `POLARIS_LANGFUSE_PUBLIC_KEY`
  - `POLARIS_LANGFUSE_SECRET_KEY`
  - `POLARIS_LANGFUSE_ENVIRONMENT`
  - `POLARIS_LANGFUSE_RELEASE`
  - `POLARIS_LANGFUSE_SAMPLE_RATE`
  - `POLARIS_LANGFUSE_CAPTURE_PROMPTS`
  - `POLARIS_LANGFUSE_CAPTURE_RESPONSES`
  - `POLARIS_LANGFUSE_CAPTURE_CONTEXTS`
  - `POLARIS_LANGFUSE_CAPTURE_USER_INPUT`
  - `POLARIS_LANGFUSE_REDACTION_MODE`
- Added safe default capture posture:
  - prompt capture disabled
  - response capture disabled
  - retrieved-context capture disabled
  - user-input capture disabled
  - redaction mode defaults to `strict`
- Added `Settings.validate_langfuse_observability()` for bootstrap validation without leaking configured secret values in errors.
- Added validation for HTTP(S) Langfuse host URLs, redaction mode, and sample-rate bounds.
- Added `tests.helpers.fake_langfuse.FakeLangfuseAiObservabilitySink` for unit/integration tests that should not require a live Langfuse service.
- Added `docs/langfuse_ai_observability.md` documenting required configuration, bootstrap validation, capture policy posture, and test support.
- Added focused unit coverage in `tests/unit/config/test_langfuse_observability_settings.py`.

Verification:

- `uv run ruff format config/settings.py tests/helpers/fake_langfuse.py tests/unit/config/test_langfuse_observability_settings.py`
- `uv run ruff check config/settings.py tests/helpers/fake_langfuse.py tests/unit/config/test_langfuse_observability_settings.py --fix`
- `uv run mypy config/settings.py tests/helpers/fake_langfuse.py tests/unit/config/test_langfuse_observability_settings.py --explicit-package-bases`
- `uv run pytest -q tests/unit/config/test_langfuse_observability_settings.py`
- `uv run pytest -q tests/unit/config`
- `uv run graphify update .`

Notes:

- Repowise flagged `config/settings.py` as high-coupling, so Step 1 kept changes limited to additive settings and validation plus focused tests.
- No live Langfuse service was required for this step.

### Step 2 — Phase 2: Canonical AI observability contracts

Completed.

Changes made:

- Added `application/observability/ai_observability_contracts.py` as the application-layer contract surface for Polaris AI observability projection.
- Added `application/observability/__init__.py` exports for the new typed contracts.
- Added canonical observation categories and families for:
  - RAG query, routing, vector retrieval, graph retrieval, fusion, parent expansion, reranking, CRAG, Self-RAG, generation, security, and answer-quality stages.
  - Intelligence agent reasoning, strategy synthesis, report generation, and recommendation explanation stages.
- Added DeepEval-ready typed contracts up front:
  - `AiEvaluationObservation`
  - `AiEvaluationScore` / `AiScoreProjection`
  - `AiPromptVersionReference`
  - `AiObservabilityCorrelationIds`
  - `AiObservabilityExportResult`
- Added first-class dataset, case, run, trace, span, workflow, execution, node, observation, and parent-observation correlation identifiers.
- Added score projection fields for metric name, score, threshold, pass/fail/warn/unknown result, reason, evaluator model, and evaluator provider.
- Added capture/redaction policy model with strict, metadata-only, and permissive modes; safe defaults keep prompt, response, context, and user-input capture disabled.
- Added stable idempotency key generation for observations and evaluation observations.
- Added focused unit tests in `tests/unit/application/observability/test_ai_observability_contracts.py` covering:
  - RAG and intelligence observation type mapping.
  - safe capture policy defaults.
  - stable generation idempotency keys.
  - retrieval and reranking stage payload shape fields.
  - DeepEval-ready evaluation identifiers and score projection fields.
  - export result correlation fields.
  - invalid score/count/metadata validation.

Verification:

- `uv run ruff format application/observability tests/unit/application/observability`
- `uv run ruff check application/observability tests/unit/application/observability --fix`
- `uv run mypy application/observability tests/unit/application/observability --explicit-package-bases`
- `uv run pytest -q tests/unit/application/observability/test_ai_observability_contracts.py`
- `uv run ruff check . --fix`
- `uv run ruff format .`
- `uv run mypy . --explicit-package-bases`
- `uv run pytest -q tests/unit/application/observability tests/unit/config/test_langfuse_observability_settings.py`
- `uv run pytest -q tests/unit/application/rag/test_rag_service.py tests/unit/application/rag/test_rag_service_graph.py tests/unit/application/rag/test_rag_retriever.py`
- `uv run graphify update .`

Notes:

- No `core/` changes were required for this step.
- No live Langfuse service was required for this step.
- The contracts are Polaris-owned and Langfuse-agnostic; Langfuse-specific mapping remains deferred to the projection sink step.

### Step 3 — Phase 3: Langfuse sink and export path

Completed.

Changes made:

- Added `application/observability/langfuse_projection.py` as the Polaris-owned Langfuse projection boundary.
- Added `LangfuseObservationMapper` to map typed Polaris AI observations into sanitized Langfuse-boundary payloads.
- Added OpenTelemetry-compatible trace/span correlation fields in the Langfuse payload while preserving Polaris workflow, execution, runtime, node, dataset, case, run, observation, and parent-observation identifiers.
- Added `LangfuseExportClient` as a transport protocol so application code does not depend directly on a Langfuse SDK or live service.
- Added `LangfuseAiObservabilitySink` to export typed observations through the configured client and convert responses into `AiObservabilityExportResult` records.
- Added `AiObservabilityProjector` as the application boundary that future RAG and intelligence instrumentation will call instead of calling Langfuse directly.
- Added defensive exception logging with tracebacks for Langfuse export failures while returning a typed failed export result instead of breaking valid domain execution.
- Added policy-controlled prompt, response, and evaluation-reason capture:
  - strict and metadata-only policies omit body text.
  - permissive policy captures bounded text only when the relevant capture flag is enabled.
- Added generation, retrieval, reranking, and DeepEval-ready evaluation score mapping.
- Exported the new projection classes from `application/observability/__init__.py`.
- Added focused tests in `tests/unit/application/observability/test_langfuse_projection.py` covering:
  - redacted generation payload mapping.
  - OpenTelemetry and Polaris correlation mapping.
  - bounded permissive prompt/response capture.
  - retrieval, reranking, and evaluation payload fields.
  - export response correlation mapping.
  - non-fatal export failure handling.
  - projector-to-sink delegation.

Verification:

- `uv run ruff check application/observability tests/unit/application/observability --fix`
- `uv run ruff format application/observability tests/unit/application/observability`
- `uv run mypy application/observability tests/unit/application/observability --explicit-package-bases`
- `uv run pytest -q tests/unit/application/observability tests/unit/config/test_langfuse_observability_settings.py`
- `uv run ruff check . --fix`
- `uv run ruff format .`
- `uv run mypy . --explicit-package-bases`
- `uv run graphify update .`

Notes:

- No `core/` changes were required for this step.
- No live Langfuse service was required for this step; the sink is transport-protocol based and testable with fake clients.
- Durable PostgreSQL export/retry persistence was not added in this step because the current telemetry persistence boundary should not be stretched into an AI-observability projection queue without a dedicated design. The step adds typed export status and non-fatal failure handling; durable retry ownership remains a later explicit persistence/projection step.

### Step 4 — Phase 4: Durable export queue and retry repository

Completed.

Changes made:

- Added a dedicated PostgreSQL-backed durable export queue for Langfuse AI-observability projections instead of stretching the generic telemetry persistence path.
- Added `core/database/models/ai_observability.py` with `AiObservabilityExportJobModel` and first-class fields for:
  - idempotency key
  - observation type/name/family/status
  - retry lifecycle status and attempt counters
  - Langfuse payload JSONB
  - trace/span, workflow, execution, runtime, node, observation, parent-observation, dataset, case, and run correlation IDs
  - external Langfuse trace and observation IDs
  - retry timing, lifecycle timestamps, and last error
- Added Alembic migration `20260712_000001_add_ai_observability_export_jobs.py` for the `ai_observability_export_jobs` table, constraints, and indexes.
- Added typed durable persistence contracts under `core/storage/persistence/ai_observability/`:
  - `AiObservabilityExportJobRecord`
  - `AiObservabilityExportJobClaim`
  - `AiObservabilityExportJobStatus`
  - `AiObservabilityExportJobRepository`
- Added `PostgresAiObservabilityExportJobRepository` with atomic claim, retry, exported, failed, skipped, list, and stale-running recovery operations.
- Added application-level durable export services in `application/observability/ai_observability_export_service.py`:
  - `AiObservabilityExportQueueService`
  - `DurableLangfuseAiObservabilitySink`
  - `AiObservabilityExportWorker`
  - `AiObservabilityExportBatchResult`
- Kept the Langfuse export path application-owned and transport-protocol based; no Langfuse SDK or live Langfuse service is required by the durable queue/repository contracts.
- Export failures are now durable, retryable, trace-correlated, and non-fatal to valid Polaris workflow/domain execution.
- Added focused unit coverage for the database model, typed export records, queue service, durable sink, worker success path, worker failure/retry path, and batch draining.

Verification:

- `uv run ruff check application/observability core/database/models/ai_observability.py core/storage/persistence/ai_observability core/storage/persistence/repositories/postgres_ai_observability_export_job_repository.py tests/unit/application/observability/test_ai_observability_export_service.py tests/unit/core/database/test_ai_observability_export_models.py tests/unit/core/storage/persistence/test_ai_observability_export_records.py migrations/versions/20260712_000001_add_ai_observability_export_jobs.py --fix`
- `uv run ruff format application/observability core/database/models/ai_observability.py core/storage/persistence/ai_observability core/storage/persistence/repositories/postgres_ai_observability_export_job_repository.py tests/unit/application/observability/test_ai_observability_export_service.py tests/unit/core/database/test_ai_observability_export_models.py tests/unit/core/storage/persistence/test_ai_observability_export_records.py migrations/versions/20260712_000001_add_ai_observability_export_jobs.py`
- `uv run mypy application/observability core/storage/persistence/ai_observability core/storage/persistence/repositories/postgres_ai_observability_export_job_repository.py core/database/models/ai_observability.py tests/unit/application/observability/test_ai_observability_export_service.py tests/unit/core/database/test_ai_observability_export_models.py tests/unit/core/storage/persistence/test_ai_observability_export_records.py --explicit-package-bases`
- `uv run pytest -q tests/unit/application/observability tests/unit/core/database/test_ai_observability_export_models.py tests/unit/core/storage/persistence/test_ai_observability_export_records.py tests/unit/config/test_langfuse_observability_settings.py`
- `uv run ruff check . --fix`
- `uv run ruff format .`
- `uv run mypy . --explicit-package-bases`
- `uv run alembic heads`
- `uv run graphify update .`

Notes:

- `core/` changes were required and were authorized for this step.
- No live Langfuse service was required.
- No live PostgreSQL migration test was run in this step; `uv run alembic heads` confirmed a single migration head. A live PostgreSQL upgrade/check can be run before the next persistence-wiring step if you want database DDL verification now.

### Step 5 — Phase 4: RAG pipeline AI-observability instrumentation

Completed.

Changes made:

- Added `application/rag/observability/` as the RAG-owned AI-observability instrumentation boundary.
- Added `RagAiObservabilityRecorder` and `RagAiObservabilityProjectorPort` so RAG code can emit typed AI observations without importing Langfuse SDKs or calling Langfuse directly.
- Kept AI-observability export non-fatal to valid RAG domain execution; projection failures are logged with tracebacks and do not change RAG results.
- Instrumented `RagService.run()` with a sanitized `rag.query` observation for the full request lifecycle.
- Instrumented `RagServiceGraph` stages for:
  - input security guard
  - memory/context rewrite
  - adaptive classifier
  - route selection
  - HyDE generation
  - context security sanitization
  - CRAG evaluation
  - corrective query rewrite
  - secure generation
  - output security guard
  - Self-RAG reflection or skipped reflection
  - answer quality
- Instrumented `RagRetriever` stages for:
  - lexical candidate listing
  - BM25 lexical scoring
  - query embedding
  - vector search
  - vector rehydration, including degraded missing-chunk cases
  - parent expansion
  - structured retrieval
  - graph retrieval, including failure-as-empty degradation visibility
  - retrieval deduplication/fusion
  - reranking
- Captured only bounded metadata and shapes by default: stage name, observation type, status, model/provider where available, latency, context IDs, scores, counts, route, top-k, selected route, quality decisions, security flags, and error presence.
- Intentionally did not export raw retrieved document text, full prompts, full responses, portfolio data, or unbounded web/context payloads from these stage observations.
- Added `tests/helpers/recording_ai_observability.py` as a reusable fake projector for unit tests.
- Added focused unit coverage for service, graph, and retriever AI-observability projections and redaction expectations.

Verification:

- `uv run ruff check application/rag/rag_service.py application/rag/graphs/rag_service_graph.py application/rag/retrieval/rag_retriever.py application/rag/observability/rag_ai_observability.py application/rag/observability/__init__.py tests/helpers/recording_ai_observability.py tests/unit/application/rag/test_rag_service.py tests/unit/application/rag/test_rag_service_graph.py tests/unit/application/rag/test_rag_retriever.py --fix`
- `uv run ruff format application/rag/rag_service.py application/rag/graphs/rag_service_graph.py application/rag/retrieval/rag_retriever.py application/rag/observability/rag_ai_observability.py application/rag/observability/__init__.py tests/helpers/recording_ai_observability.py tests/unit/application/rag/test_rag_service.py tests/unit/application/rag/test_rag_service_graph.py tests/unit/application/rag/test_rag_retriever.py`
- `uv run mypy application/rag/rag_service.py application/rag/graphs/rag_service_graph.py application/rag/retrieval/rag_retriever.py application/rag/observability/rag_ai_observability.py tests/unit/application/rag/test_rag_service.py tests/unit/application/rag/test_rag_service_graph.py tests/unit/application/rag/test_rag_retriever.py --explicit-package-bases`
- `uv run pytest -q tests/unit/application/rag/test_rag_service.py tests/unit/application/rag/test_rag_service_graph.py tests/unit/application/rag/test_rag_retriever.py tests/unit/application/observability/test_ai_observability_contracts.py`
- `uv run graphify update .`
- `uv run ruff check . --fix`
- `uv run ruff format .`
- `uv run mypy . --explicit-package-bases`
- `uv run pytest -q tests/unit/application/rag/test_rag_service.py tests/unit/application/rag/test_rag_service_graph.py tests/unit/application/rag/test_rag_retriever.py tests/unit/application/observability/test_ai_observability_contracts.py`

Notes:

- No live Langfuse, PostgreSQL, Qdrant, Neo4j, or BGE reranker service was required for this step.
- Repowise risk checks identified `application/rag/rag_service.py`, `application/rag/retrieval/rag_retriever.py`, and `application/rag/graphs/rag_service_graph.py` as high-churn/high-risk files, so this step stayed surgical and avoided unrelated RAG refactoring.
- Production DI wiring to the durable Langfuse export queue remains deferred to a later wiring/bootstrap step; this step added the canonical instrumentation boundary and optional projector injection points.

### Plan correction after Step 5 — SDK-backed Langfuse exporter required

Updated the plan to explicitly require a complete live Langfuse integration before continuing beyond RAG instrumentation.

Correction added:

- Add the official `langfuse` Python dependency with `uv add langfuse`.
- Implement a concrete SDK-backed `LangfuseExportClient` adapter in the application observability boundary.
- Wire production DI/bootstrap to use the durable queue plus SDK exporter.
- Verify queued observations can export to Langfuse and persist external trace/observation IDs.
- Keep RAG, intelligence, workflow, CLI, provider, repository, and core code free of direct Langfuse SDK imports.

Next step to execute: **Step 5B — Add official Langfuse SDK exporter and production wiring**.



### Step 5B — Add official Langfuse SDK exporter and production wiring

Completed.

Changes made:

- Added the official `langfuse` Python dependency with `uv add langfuse`.
- Added `application/observability/langfuse_sdk_exporter.py` as the only approved production SDK import boundary.
- Implemented `LangfuseSdkExportClient` using the official Langfuse SDK low-level ingestion API with deterministic trace, observation/generation, and score event IDs derived from Polaris idempotency keys.
- Added request-scoped `ApplicationObservabilityDIProvider` to compose capture policy, mapper, durable queue service, projector, SDK export client, and export worker.
- Wired the RAG async DI stack so RAG service, graph, and retriever observations flow into the durable PostgreSQL export queue through `AiObservabilityProjector`.
- Exposed `AiObservabilityExportJobRepository` through the RAG persistence DI provider for queued Langfuse export jobs.
- Updated `docs/langfuse_ai_observability.md` to document the completed SDK-backed durable export architecture, capture policy, and DeepEval-ready score/correlation fields.
- Added focused SDK adapter tests for generation exports, evaluation score projection, SDK flush/shutdown delegation, DI capture policy construction, and SDK import isolation.

Verification:

- `uv run ruff check application/observability application/rag/di.py core/storage/rag_di.py core/bootstrap/di_providers.py tests/unit/application/observability/test_langfuse_sdk_exporter.py --fix`
- `uv run ruff format application/observability application/rag/di.py core/storage/rag_di.py core/bootstrap/di_providers.py tests/unit/application/observability/test_langfuse_sdk_exporter.py`
- `uv run mypy application/observability application/rag/di.py core/storage/rag_di.py core/bootstrap/di_providers.py tests/unit/application/observability/test_langfuse_sdk_exporter.py --explicit-package-bases`
- `uv run pytest -q tests/unit/application/observability tests/unit/config/test_langfuse_observability_settings.py`
- `uv run graphify update .`

Notes:

- No live Langfuse service was confirmed for this step, so no live Langfuse export test was run.
- The durable queue path can enqueue AI observations without requiring Langfuse credentials during RAG execution; the export worker validates and requires Langfuse configuration when it is resolved.
- Repowise marked `application/rag/di.py` and `core/bootstrap/di_providers.py` as churn-heavy, so DI changes were kept narrow and limited to canonical observability wiring.
- Next step: resume the original plan with Phase 5 intelligence workflow instrumentation.

### Step 6 — Phase 5: Intelligence workflow instrumentation

Completed.

Changes made:

- Added `intelligence/observability/` as the intelligence-owned AI-observability instrumentation boundary.
- Added a non-fatal typed recorder so intelligence components can project sanitized AI observations without importing Langfuse SDKs or treating Langfuse as a source of truth.
- Instrumented LLM-backed analyst reasoning paths in:
  - `FundamentalAgent`
  - `TechnicalAgent`
  - `NewsAgent`
  - `SentimentAgent`
- Instrumented `StrategySynthesisAgent` structured-hypothesis synthesis on both normal and degraded fallback paths.
- Captured only bounded observation metadata and shapes by default, including correlation IDs, workflow/runtime IDs, model/provider names when available, status, latency, counts, confidence, selected perspective, and degradation flags.
- Kept `RuntimeNodeOutput`, `RuntimeContext`, and completed-run persistence as canonical workflow evidence; Langfuse receives only AI-observability projections.
- Verified there is no separate LLM-backed report-generation boundary in current source; report rendering currently consumes existing workflow outputs rather than calling an LLM directly.

Verification:

- `uv run ruff check intelligence/observability intelligence/analysts/fundamental/fundamental_agent.py intelligence/analysts/technical/technical_agent.py intelligence/research/news/news_agent.py intelligence/research/sentiment/sentiment_agent.py intelligence/strategy/synthesis/strategy_synthesis_agent.py tests/unit/intelligence/observability/test_intelligence_ai_observability.py tests/unit/intelligence/analysts/technical/test_technical_agent.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py --fix`
- `uv run ruff format intelligence/observability intelligence/analysts/fundamental/fundamental_agent.py intelligence/analysts/technical/technical_agent.py intelligence/research/news/news_agent.py intelligence/research/sentiment/sentiment_agent.py intelligence/strategy/synthesis/strategy_synthesis_agent.py tests/unit/intelligence/observability/test_intelligence_ai_observability.py tests/unit/intelligence/analysts/technical/test_technical_agent.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py`
- `uv run mypy intelligence/observability intelligence/analysts/fundamental/fundamental_agent.py intelligence/analysts/technical/technical_agent.py intelligence/research/news/news_agent.py intelligence/research/sentiment/sentiment_agent.py intelligence/strategy/synthesis/strategy_synthesis_agent.py tests/unit/intelligence/observability/test_intelligence_ai_observability.py tests/unit/intelligence/analysts/technical/test_technical_agent.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py --explicit-package-bases`
- `uv run pytest -q tests/unit/intelligence/observability/test_intelligence_ai_observability.py tests/unit/intelligence/analysts/technical/test_technical_agent.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py tests/unit/intelligence/research/test_news_sentiment_output_contracts.py tests/unit/intelligence/analysts/fundamental/test_fundamental_agent.py`
- `uv run graphify update .`

Notes:

- No live Langfuse, PostgreSQL, Qdrant, Neo4j, or BGE reranker service was required for this step.
- Repowise identified several touched intelligence files as churn-heavy, so this step stayed additive and surgical.
- Production injection remains optional through constructor dependencies; canonical DI/export wiring added in Step 5B is reusable for any later workflow/bootstrap wiring step.


### Step 7 — Phase 7: Dataset and evaluation integration

Completed.

Changes made:

- Added `application/observability/ai_evaluation_datasets.py` for typed Polaris AI-evaluation dataset contracts.
- Added canonical regression dataset categories for:
  - RAG answer quality
  - RAG citation groundedness
  - report QA
  - strategy rationale
  - prompt-injection resistance
- Added `AiEvaluationDatasetBuildService` to build the default Polaris regression dataset and project case scores into `AiEvaluationObservation` records.
- Added canonical quality-score mapping from numeric scores to `PASS`, `WARN`, and `FAIL` results while preserving DeepEval-ready evaluator metadata.
- Extended the SDK-backed Langfuse exporter with `export_dataset()` using the official `langfuse` SDK dataset APIs:
  - `create_dataset()`
  - `create_dataset_item()`
- Kept dataset definitions and evaluation observations as Polaris-owned typed contracts; Langfuse receives dataset/evaluation projections only.
- Exported the new dataset contracts through `application.observability`.
- Added focused tests for dataset construction, score mapping, evaluation observation projection, and SDK dataset export behavior.

Verification:

- `uv run ruff check application/observability tests/unit/application/observability/test_ai_evaluation_datasets.py tests/unit/application/observability/test_langfuse_sdk_exporter.py --fix`
- `uv run ruff format application/observability tests/unit/application/observability/test_ai_evaluation_datasets.py tests/unit/application/observability/test_langfuse_sdk_exporter.py`
- `uv run mypy application/observability tests/unit/application/observability/test_ai_evaluation_datasets.py tests/unit/application/observability/test_langfuse_sdk_exporter.py --explicit-package-bases`
- `uv run pytest -q tests/unit/application/observability/test_ai_evaluation_datasets.py tests/unit/application/observability/test_ai_observability_contracts.py tests/unit/application/observability/test_langfuse_projection.py tests/unit/application/observability/test_langfuse_sdk_exporter.py tests/unit/application/observability/test_ai_observability_export_service.py`
- `uv run graphify update .`

Notes:

- No live Langfuse service was required for this step; SDK behavior is verified with a recording fake client.
- DeepEval itself is still deferred to the separate DeepEval integration plan. This step provides the Langfuse-side dataset, case, run, score, and correlation contracts needed to avoid rework when DeepEval is integrated.

### Step 8 — Phase 8: Operations, retention, and documentation

Completed.

Changes made:

- Expanded `docs/langfuse_ai_observability.md` with operational guidance for the completed Langfuse AI-observability projection.
- Documented local self-host setup expectations without adding a repo-owned Langfuse Docker service.
- Documented Polaris-owned operational signals and dashboard guidance for:
  - durable export queue status and backlog health;
  - export attempts, retries, latency, and failure rate;
  - observation volume by family/type/status;
  - capture policy, redaction posture, dataset scores, and evaluation trends.
- Documented logging requirements for exporter failures, retry visibility, traceback capture, and secret-safe context.
- Documented trace/correlation requirements for Polaris trace IDs, workflow/runtime IDs, dataset/case/run IDs, and external Langfuse IDs.
- Documented production security posture:
  - PostgreSQL remains authoritative;
  - Langfuse remains a sanitized projection;
  - the official SDK remains isolated to `application.observability.langfuse_sdk_exporter`;
  - workflow, RAG, intelligence, and recommendation behavior must not depend on reading from Langfuse.
- Documented retention and redaction responsibilities, including projection cleanup, strict redaction defaults, dataset sensitivity rules, and evaluation-reason sensitivity rules.
- Documented dataset/evaluation operations now supported by the Langfuse side of the integration.
- Updated `docs/testing_guide.md` with Langfuse AI-observability test categories, optional live-service requirements, Docker service matrix notes, and environment variable guidance.

Verification:

- `uv run pytest -q tests/unit/application/observability tests/unit/config/test_langfuse_observability_settings.py`

Notes:

- No live Langfuse service was required or started for this step.
- No Python source changed in this step, so Graphify update was not required.
- The repository currently documents Langfuse as an external/self-hosted service, not a service defined by the Polaris Docker Compose file.


### Step 7 — Prompt management strategy

Completed.

Changes made:

- Added `application/observability/ai_prompt_management.py` with canonical prompt governance contracts:
  - `AiPromptGovernancePolicy`
  - `AiPromptGovernanceError`
  - `AiPromptPromotionRequest`
  - `AiPromptPromotionDecision`
  - `AiPromptPromotionPolicy`
  - deterministic static prompt hash/reference helpers
- Wired prompt governance into `LangfuseObservationMapper` and DI so production exports reject generation observations without prompt references and reject mutable prompt versions such as `latest`, `draft`, `dev`, or `mutable`.
- Added prompt hash/source support to intelligence AI generation observations and updated LLM-backed intelligence agents to emit source-controlled prompt fingerprints.
- Added prompt provenance to RAG routing model executions and RAG generation metadata so routing, HyDE, and secure-generation observations carry prompt name/version/hash/source references.
- Kept Langfuse as the prompt authoring/experimentation surface while Polaris remains the production prompt-governance authority.
- Updated Langfuse AI-observability documentation with the prompt lifecycle, production governance rules, promotion policy, source-controlled fallback expectations, and DeepEval-ready prompt provenance.
- Added focused tests for prompt references, production prompt governance, prompt promotion decisions, RAG prompt projection, and intelligence prompt fingerprints.

Verification:

- `uv run ruff check application/observability application/rag/routing application/rag/observability application/rag/generation intelligence/observability intelligence/analysts/fundamental/fundamental_agent.py intelligence/analysts/technical/technical_agent.py intelligence/research/news/news_agent.py intelligence/research/sentiment/sentiment_agent.py tests/unit/application/observability tests/unit/application/rag/test_rag_service_graph.py tests/unit/intelligence/observability/test_intelligence_ai_observability.py tests/unit/intelligence/analysts/technical/test_technical_agent.py --fix`
- `uv run ruff format application/observability application/rag/routing application/rag/observability application/rag/generation intelligence/observability intelligence/analysts/fundamental/fundamental_agent.py intelligence/analysts/technical/technical_agent.py intelligence/research/news/news_agent.py intelligence/research/sentiment/sentiment_agent.py tests/unit/application/observability tests/unit/application/rag/test_rag_service_graph.py tests/unit/intelligence/observability/test_intelligence_ai_observability.py tests/unit/intelligence/analysts/technical/test_technical_agent.py`
- `uv run mypy application/observability application/rag/routing application/rag/observability application/rag/generation intelligence/observability intelligence/analysts/fundamental/fundamental_agent.py intelligence/analysts/technical/technical_agent.py intelligence/research/news/news_agent.py intelligence/research/sentiment/sentiment_agent.py tests/unit/application/observability tests/unit/application/rag/test_rag_service_graph.py tests/unit/intelligence/observability/test_intelligence_ai_observability.py tests/unit/intelligence/analysts/technical/test_technical_agent.py --explicit-package-bases`
- `uv run pytest -q tests/unit/application/observability tests/unit/application/rag/test_rag_service_graph.py tests/unit/intelligence/observability/test_intelligence_ai_observability.py tests/unit/intelligence/analysts/technical/test_technical_agent.py`
- `uv run graphify update .`

Notes:

- No live Langfuse, PostgreSQL, Qdrant, Neo4j, or BGE reranker service was required for this step.
- Repowise reported the RAG routing service as churn-heavy, so prompt metadata changes there were kept additive and limited to typed provenance on existing model execution records.
- Step 8 dataset/evaluation work was already completed earlier under the historical “Step 7 — Phase 7” result. The next unreconciled operational stage is Step 9 unless you want to handle remaining Step 10 hardening first.

### Step 9 — Operational visibility

Completed.

Changes made:

- Added `AiObservabilityOperationalStatusService` to report AI-observability projection health from canonical PostgreSQL queue state plus Langfuse configuration validation.
- Added typed queue aggregation through `AiObservabilityExportQueueStatus`, including status counts, backlog count, retry pressure, exhausted failures, latest failure/export timestamps, and oldest retryable availability.
- Added PostgreSQL repository support for export queue status aggregation without making Langfuse the source of truth.
- Added export queue and worker operational telemetry for queued observations, export attempts, successes, failures, retries, export duration, and delivery latency.
- Added `polaris observability ai-status` with console and JSON rendering through the canonical Dishka request scope.
- Updated Langfuse AI-observability documentation with the operational status command, health-state meanings, and metric inventory.
- Added focused unit coverage for operational status derivation, queue status validation, export metrics, CLI rendering, and CLI command registration.

Verification:

- `uv run ruff check . --fix`
- `uv run ruff format .`
- `uv run mypy . --explicit-package-bases`
- `POLARIS_POSTGRES_PASSWORD=<placeholder> uv run pytest -q tests/unit/application/observability tests/unit/interfaces/cli/test_observability_command_service.py tests/unit/interfaces/cli/test_cli.py tests/unit/core/storage/persistence/test_ai_observability_export_records.py tests/unit/core/database/test_ai_observability_export_models.py` — 68 passed, 1 warning
- `POLARIS_POSTGRES_PASSWORD=<placeholder> uv run polaris observability --help`
- `POLARIS_POSTGRES_PASSWORD=<placeholder> uv run polaris observability ai-status --help`
- `uv run graphify update .`

Notes:

- No live Langfuse service was required for this step.
- The status service intentionally treats PostgreSQL as the authoritative export queue and reports Langfuse configuration/reachability as projection health only.
- Focused verification used a non-secret placeholder PostgreSQL password environment value to satisfy import-time database settings without committing or printing real credentials.


### Step 10 — Security, redaction, and retention policy

Completed.

Changes made:

- Added `application/observability/ai_observability_security.py` as the canonical Langfuse export redaction boundary.
- Redacted secret-like metadata keys, bearer tokens, credential assignments, and authenticated URL credentials before payloads enter the durable Langfuse export queue.
- Hashed account, broker, customer, client, and user identifier metadata fields instead of exporting raw identifiers.
- Added bounded capture policy fields for prompt/response/context body size, metadata value size, and terminal export-job retention days.
- Added explicit Langfuse Cloud governance validation through `POLARIS_LANGFUSE_ALLOW_CLOUD_HOST`; `cloud.langfuse.com` is rejected unless explicitly approved through configuration.
- Propagated capture-policy limits and retention settings through application observability DI.
- Added redaction accounting to exported payloads so operators can see dropped, redacted, and truncated field paths without seeing sensitive content.
- Added `AiObservabilityRetentionService` and PostgreSQL repository support for deleting old terminal `exported`/`skipped` Langfuse export jobs while retaining failed, pending, and running jobs for operator action.
- Documented security posture, self-hosted-first guidance, Langfuse Cloud approval requirement, redaction behavior, retention enforcement, and the new retention metric in `docs/langfuse_ai_observability.md`.
- Added focused tests for redaction behavior, cloud approval validation, capture/retention settings, and retention cleanup behavior.

Verification:

- `uv run ruff check . --fix`
- `uv run ruff format .`
- `uv run mypy . --explicit-package-bases`
- `POLARIS_POSTGRES_PASSWORD=<placeholder> uv run pytest -q tests/unit/application/observability tests/unit/config/test_langfuse_observability_settings.py tests/unit/core/storage/persistence/test_ai_observability_export_records.py tests/unit/core/database/test_ai_observability_export_models.py tests/unit/interfaces/cli/test_observability_command_service.py tests/unit/interfaces/cli/test_cli.py` — 79 passed, 1 dependency deprecation warning
- `uv run graphify update .`

Notes:

- No live Langfuse, PostgreSQL, Qdrant, Neo4j, BGE reranker, Prometheus, Jaeger, or Grafana service was required for this step.
- The focused pytest command used a non-secret placeholder PostgreSQL password environment value only to satisfy import-time settings validation.
- Repowise retrieval was degraded/stale for the new Langfuse files, so implementation was verified directly against current source and tests.
