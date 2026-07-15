  # Polaris Instructor + DSPy Integration Plan

  ## Summary

  Adopt Instructor first as Polaris’s runtime structured-output enforcement layer, then adopt DSPy as a controlled prompt/program optimization layer.

  This follows the Polaris-aligned path:

  Instructor → structured runtime LLM outputs
  DeepEval → quality scoring
  Langfuse → AI observability
  DSPy → offline prompt/program optimization
  PostgreSQL → durable prompt/eval/artifact authority

  Rationale:

  - Instructor is schema-first, Pydantic-based, supports validation/retries, and works across providers including local Ollama-style providers, which fits Polaris’s typed-contract architecture. Sources: Instructor structured
    outputs (https://github.com/567-labs/instructor), provider/Ollama/retry support (https://github.com/567-labs/instructor).

  - DSPy is designed for modular AI programs with signatures, modules, and optimizers against metrics, which fits Polaris golden datasets and DeepEval-driven improvement loops. Sources: DSPy GitHub
    (https://github.com/stanfordnlp/dspy), DSPy docs (https://dspy.ai/).

  ## Implementation Plan

  ### [x] Step 1 — Add dependencies and configuration

  Add dependencies:

  uv add instructor
  uv add dspy

  Add settings:

  - POLARIS_STRUCTURED_OUTPUT_PROVIDER
  - POLARIS_STRUCTURED_OUTPUT_MODEL
  - POLARIS_STRUCTURED_OUTPUT_MAX_RETRIES
  - POLARIS_STRUCTURED_OUTPUT_TIMEOUT_SECONDS
  - POLARIS_DSPY_ENABLED
  - POLARIS_DSPY_OPTIMIZATION_MODEL
  - POLARIS_DSPY_MAX_TRAINSET_CASES
  - POLARIS_DSPY_ARTIFACT_RETENTION_DAYS

  Default choices:

  - Instructor enabled for selected generation paths once wired.
  - DSPy disabled for production runtime execution.
  - DSPy available only through explicit evaluation/optimization commands.

  Verification:

  - settings load from .env
  - no secrets committed
  - config validation errors are explicit

  ———

  ### [x] Step 2 — Create a canonical structured-output provider boundary

  Add a Polaris-owned provider abstraction, likely under:

  integration/providers/llm_structured_output/

  Introduce typed contracts:

  StructuredLlmRequest
  StructuredLlmResult
  StructuredLlmProvider
  StructuredOutputSchemaRef
  StructuredOutputRetryPolicy

  Responsibilities:

  - own Instructor integration
  - call configured model/provider
  - validate response schema
  - apply bounded retries
  - emit integration telemetry
  - emit Langfuse AI observations
  - return Polaris-owned typed results

  Do not expose Instructor objects outside this boundary.

  Verification:

  - unit tests with fake provider
  - validation failure retries are counted
  - retry exhaustion returns a typed failure
  - telemetry includes model, provider, schema name, retry count, latency, and status

  ———

  ### [x] Step 3 — Implement Instructor-backed provider

  Create:

  integration/providers/llm_structured_output/instructor_structured_output_provider.py

  Behavior:

  - builds an Instructor client from settings
  - supports local/Ollama-compatible models first
  - supports future OpenAI-compatible models without changing application code
  - accepts a Pydantic response model at the provider boundary
  - maps Instructor output into Polaris typed result objects
  - never persists raw provider payloads directly

  Failure handling:

  - validation failure → retry up to configured limit
  - provider failure → typed provider error
  - timeout → typed timeout error
  - all failures logged with tracebacks at the canonical provider boundary

  Verification:

  - mocked Instructor client tests
  - malformed output retry test
  - timeout test
  - successful structured output test

  ———

  ### [x] Step 4 — Convert RAG answer generation to structured output first

  Update the RAG answer generation path so RagAnswerGenerator still owns the use case, but its provider returns structured content.

  Add a typed RAG generation schema such as:

  RagStructuredAnswer
  RagStructuredCitation
  RagStructuredAnswerQuality

  Minimum fields:

  - answer_text
  - citations
  - confidence_score
  - grounding_summary
  - limitations
  - refusal_reason

  Then map the structured result back into the existing RagResult.

  Important rule:

  Instructor enforces structure.
  Polaris still owns the canonical RagResult contract.

  Verification:

  - RAG answer with citations
  - no-context response still works
  - malformed citations fail validation
  - retrieved context IDs must match generated citation IDs
  - full answer text is preserved and not truncated
  - Langfuse captures prompt/reference/response according to redaction policy

  ———

  ### [x] Step 5 — Add DeepEval regression coverage for structured RAG output

  Extend existing golden dataset evaluation coverage to confirm:

  - RAG answer quality
  - citation validity
  - grounding
  - refusal behavior
  - prompt-injection resistance
  - schema conformance

  Evaluation results remain persisted through the existing DeepEval/PostgreSQL/Langfuse path.

  Verification:

  - selected golden RAG dataset passes
  - failing schema/citation cases produce useful metric reasons
  - no stale/detached cases are evaluated unless explicitly selected

  ———

  ### [x] Step 6 — Extend structured output to intelligence workflows

  After RAG is stable, add Instructor-backed structured outputs to:

  1. strategy synthesis
  2. recommendation explanations
  3. morning report section generation
  4. MCP/customer-agent response payloads

  Each workflow must define its own typed schema and map that schema into existing Polaris domain/result objects.

  Do not introduce generic legacy payloads.

  Verification:

  - strategy synthesis still produces canonical structured-hypothesis outputs
  - recommendation explanations remain typed and attributable
  - morning report rendering remains human-readable
  - MCP responses are schema-valid and externally safe

  ———

  ### [x] Step 7 — Add durable prompt/program artifact records

  Add PostgreSQL-backed records for approved AI prompt/program artifacts.

  This likely requires core database changes and therefore needs explicit core-change authorization during execution.

  Canonical fields:

  - artifact_id
  - artifact_type
  - artifact_name
  - artifact_version
  - target_component
  - model_name
  - provider_name
  - prompt_reference
  - prompt_hash
  - source
  - evaluation_dataset_id
  - evaluation_run_id
  - deepeval_score_summary
  - langfuse_trace_id
  - approval_status
  - approved_by
  - approved_at
  - created_at

  Artifact types:

  source_controlled_prompt
  langfuse_prompt
  dspy_program
  dspy_compiled_prompt

  Verification:

  - Alembic migration upgrades cleanly
  - model matches DDL
  - repository create/read/list/approve/deactivate tests pass
  - no raw secrets or full authenticated URLs are stored

  ———

  ### Step 8 — Create DSPy optimization workbench

  Add a controlled application service, for example:

  application/ai_optimization/

  Introduce:

  AiOptimizationRequest
  AiOptimizationResult
  DspyOptimizationProvider

  Behavior:

  - loads selected golden dataset cases from PostgreSQL
  - builds DSPy signatures/modules for one target at a time
  - scores candidate outputs with DeepEval
  - records traces and scores in Langfuse
  - persists the selected optimized artifact in PostgreSQL
  - never modifies runtime behavior automatically

  Initial targets:

  1. rag_answer_generation
  2. rag_query_rewrite
  3. strategy_synthesis
  4. recommendation_explanation

  Verification:

  - optimization can run against a tiny deterministic fixture dataset
  - optimized artifact is persisted
  - DeepEval results are linked
  - Langfuse trace/run IDs are linked
  - production runtime does not consume the artifact until approved

  ———

  ### [x] Step 9 — Add CLI commands for optimization and promotion

  Add CLI commands under the existing polaris interface.

  Recommended commands:

  polaris ai optimize --target rag_answer_generation --dataset golden-rag-answer
  polaris ai artifacts list
  polaris ai artifacts approve <artifact-id>
  polaris ai artifacts activate <artifact-id>
  polaris ai artifacts deactivate <artifact-id>

  Rules:

  - optimization is explicit/manual
  - activation requires an approved artifact
  - production requires pinned artifact references
  - no mutable latest prompt references in production

  Verification:

  - CLI reports success/failure clearly
  - invalid artifact activation is denied
  - activated artifact is discoverable by runtime services
  - audit metadata is persisted

  ———

  ### [x] Step 10 — Wire approved artifacts into runtime generation

  Update selected generation services so they resolve an approved prompt/program artifact before generation.

  Runtime rules:

  - if an approved artifact exists for the target, use it
  - if none exists, use source-controlled static prompt
  - do not run DSPy optimization during normal workflow execution
  - record artifact ID and prompt version in Langfuse observations
  - record artifact ID in RAG/evaluation metadata where appropriate

  Verification:

  - runtime path works with source-controlled prompt fallback
  - runtime path works with approved artifact
  - generated observations include prompt/artifact reference
  - no direct DSPy optimizer runs occur in production workflow execution

  ———

  ### [x] Step 11 — Documentation and architecture guardrails

  Update documentation to clearly state:

  - Instructor is the runtime structured-output adapter.
  - DSPy is the offline optimization workbench.
  - DeepEval remains the canonical evaluation engine.
  - Langfuse remains the AI-observability and prompt/dataset/run surface.
  - PostgreSQL remains the system of record.
  - DSPy must not replace Polaris runtime, RAG services, workflow orchestration, or DeepEval.

  docs/ai_structured_outputs.md
  docs/ai_prompt_optimization.md
  docs/llm_evaluation.md
  docs/langfuse_ai_observability.md
  docs/platform_rag_pipeline.md

  Verification:

  - docs match implemented command names/settings
  - architecture ownership is unambiguous
  - no docs contain secrets or live credentials

  ## Test Plan

  Run focused tests after each implementation step:

  uv run ruff check .
  uv run ruff format .
  uv run mypy . --explicit-package-bases
  uv run pytest tests/unit/integration/providers/llm_structured_output
  uv run pytest tests/unit/application/rag
  uv run pytest tests/unit/application/evaluations
  uv run pytest tests/unit/application/observability

  For database steps:

  uv run alembic upgrade head
  uv run pytest tests/database

  For live validation, notify before requiring services:

  - PostgreSQL for persistence and evaluation records
  - Ollama for local Instructor/DSPy model calls
  - Langfuse for AI-observability projection
  - optional Qdrant/Neo4j only if testing full RAG retrieval behavior

  Suggested live checks:

  polaris rag ask "..." --format console
  polaris eval run --dataset golden-rag-answer --slice small
  polaris ai optimize --target rag_answer_generation --dataset golden-rag-answer --limit 5

  ## Assumptions and Defaults

  - Instructor is adopted as a required runtime structured-output capability for selected LLM generation paths.
  - DSPy is adopted as a required optimization capability, but not as a production runtime orchestrator.
  - RAG answer generation is the first Instructor integration target.
  - DSPy optimization starts only after structured RAG output and evaluation gates are stable.
  - PostgreSQL stores approved prompt/program artifacts.
  - Langfuse stores traces, prompt references, datasets, and run correlations.
  - DeepEval remains the scoring authority.
  - No new parallel runtime, RAG stack, or agent framework is introduced.

## Step Results

### Step 1 — Add dependencies and configuration

- Added `instructor>=1.15.4` and `dspy>=3.2.1` through `uv add instructor dspy`; verified both packages import successfully.
- Added canonical structured-output settings for Instructor and disabled-by-default DSPy optimization settings in `config/settings.py`.
- Added `.env.example` entries for the new `POLARIS_STRUCTURED_OUTPUT_*` and `POLARIS_DSPY_*` variables without committing secrets.
- Added focused unit coverage in `tests/unit/config/test_ai_structured_output_settings.py` for defaults, Polaris-prefixed environment loading, provider validation, non-empty model validation, and numeric bounds.
- Verification passed: `uv run pytest -q tests/unit/config/test_ai_structured_output_settings.py tests/unit/config/test_deepeval_evaluation_settings.py tests/unit/config/test_langfuse_observability_settings.py`.
- Verification passed: `uv run mypy config/settings.py tests/unit/config/test_ai_structured_output_settings.py --explicit-package-bases`.

### Step 2 — Create a canonical structured-output provider boundary

- Added the canonical structured-output provider package under `integration/providers/llm_structured_output/`.
- Introduced Polaris-owned typed contracts: `StructuredLlmRequest`, `StructuredLlmResult`, `StructuredOutputSchemaRef`, `StructuredOutputRetryPolicy`, `StructuredOutputStatus`, and the `StructuredLlmProvider` protocol.
- Added `StructuredLlmProviderExecutor` to own bounded retry behavior, Pydantic schema validation, typed success/failure results, timeout handling, and provider telemetry payload enrichment.
- Added fake-provider unit tests covering protocol conformance, successful schema validation, validation retry counting, retry exhaustion typed failures, timeout typed failures, required-field validation, and telemetry fields for provider/model/schema/status/retry counts.
- Verification passed: `uv run pytest -q tests/unit/integration/providers/llm_structured_output/test_structured_output_provider.py`.
- Verification passed: `uv run mypy integration/providers/llm_structured_output tests/unit/integration/providers/llm_structured_output --explicit-package-bases`.
- Verification passed: scoped Ruff check/format for the new provider package and tests.
- Updated Graphify after Python changes.


### Step 3 — Implement Instructor-backed provider

- Added `InstructorStructuredOutputProvider` and `InstructorStructuredOutputProviderConfig` under `integration/providers/llm_structured_output/`.
- Added a minimal `InstructorChatCompletionClient` protocol plus a native Instructor adapter so Instructor objects remain contained inside the provider boundary.
- Implemented settings-based Instructor client construction with Ollama-first model naming (`ollama/<model>`) and future provider-prefixed model support.
- Routed Instructor calls through the canonical `StructuredLlmProviderExecutor`; Instructor's internal retry loop is kept bounded with `max_retries=1` so Polaris owns retry accounting and typed result mapping.
- Strengthened canonical failure mapping so validation exhaustion, provider exceptions, and timeouts return typed `StructuredLlmResult` failures and log tracebacks at the provider boundary.
- Added mocked Instructor unit coverage for successful structured output, malformed-output retry, retry exhaustion, timeout handling, provider errors, settings-based client construction, and provider-prefixed model helpers.
- Verification passed: `uv run pytest -q tests/unit/integration/providers/llm_structured_output`.
- Verification passed: scoped Ruff check/format for `integration/providers/llm_structured_output` and `tests/unit/integration/providers/llm_structured_output`.
- Verification passed: `uv run mypy integration/providers/llm_structured_output tests/unit/integration/providers/llm_structured_output --explicit-package-bases`.
- Updated Graphify after Python changes.

### Step 4 — Convert RAG answer generation to structured output first

- Added `RagStructuredAnswer`, `RagStructuredCitation`, and `RagStructuredAnswerQuality` as the typed schema for Instructor-enforced RAG answer generation.
- Added `StructuredRagAnswerGenerationProvider` as the adapter from the canonical structured-output provider boundary back into the existing `RagAnswerGenerationResult` contract.
- Rewired RAG DI so `RagAnswerGenerator` still owns the secure generation use case while the default answer provider uses `InstructorStructuredOutputProvider` through the structured RAG adapter.
- Preserved the existing no-context behavior in `RagAnswerGenerator`; the provider is not called when no retrieved context exists.
- Added focused tests for full answer preservation, citation metadata mapping, malformed citation schema validation, rejection of generated citation IDs that are not present in retrieved context, structured provider failure mapping, and existing secure/no-context behavior.
- Verification passed: `uv run pytest -q tests/unit/integration/providers/rag/test_structured_answer_generation_provider.py tests/unit/application/rag/test_secure_rag_generation.py`.
- Verification passed: `uv run pytest -q tests/unit/core/bootstrap/test_rag_di_composition.py`.
- Verification passed: `uv run pytest -q tests/unit/integration/providers/rag/test_structured_answer_generation_provider.py tests/unit/application/rag/test_secure_rag_generation.py tests/unit/core/bootstrap/test_rag_di_composition.py`.
- Verification passed: `uv run pytest -q tests/unit/application/rag/test_rag_service_graph.py tests/unit/application/rag/test_rag_service.py`.
- Verification passed: scoped Ruff check/format for the new schema, structured RAG provider, DI wiring, and tests.
- Verification passed: `uv run mypy application/rag/contracts/rag_structured_answer.py integration/providers/rag/structured_answer_generation_provider.py integration/providers/rag/di.py application/rag/di.py tests/unit/integration/providers/rag/test_structured_answer_generation_provider.py --explicit-package-bases`.
- Updated Graphify after Python changes.


### Step 5 — Add DeepEval regression coverage for structured RAG output

- Added deterministic structured RAG evaluation regression coverage in `tests/evaluation/test_structured_rag_output_evals.py`.
- Verified active RAG fixtures can be represented as `RagStructuredAnswer` instances without truncating answer text and with generated citation IDs constrained to fixture citation-context IDs.
- Verified malformed structured citation payloads fail schema validation with useful `claim_summary` error details.
- Verified the selected golden RAG dataset runs through `EvaluationRunService` with the full canonical RAG metric policy, persists dataset/case/run/metric records through the existing evaluation persistence boundary, and requests Langfuse score projection through the existing projection boundary.
- Verified detached stale cases are not evaluated unless explicitly supplied in the evaluation request.
- Confirmed canonical RAG evaluation metrics cover answer quality, citation support, grounding, refusal correctness, unsupported-claim penalties, and prompt-injection resistance.
- Note: structured-output schema conformance is intentionally verified deterministically with Pydantic; DeepEval remains the semantic evaluator for quality, grounding, citation support, refusal, and prompt-injection behavior.
- Verification passed: `uv run ruff check tests/evaluation/test_structured_rag_output_evals.py --fix`.
- Verification passed: `uv run ruff format tests/evaluation/test_structured_rag_output_evals.py`.
- Verification passed: `uv run pytest -q tests/evaluation/test_structured_rag_output_evals.py tests/evaluation/test_rag_regression_evals.py tests/evaluation/test_security_evals.py` (`10 passed`).
- Verification passed: `uv run mypy tests/evaluation/test_structured_rag_output_evals.py --explicit-package-bases`.
- Updated Graphify after Python changes with `uv run graphify update .`.


### Step 6 — Extend structured output to intelligence workflows

- Added `application/structured_outputs/` with strict Pydantic Instructor target schemas for intelligence workflow output:
  - `StructuredStrategySynthesisOutput` and `StructuredStrategyHypothesisEvaluation` map into the canonical `StrategySynthesisDecision` and `StrategyHypothesisEvaluation` domain contracts.
  - `StructuredRecommendationExplanation` maps into the canonical `RecommendationRationaleRecord` while preserving attribution source IDs and limitations as persistence-boundary metadata.
  - `StructuredMorningReportSection` maps into the existing human-facing `ReportSection` model without introducing generic payloads.
- Added `mcp_server/contracts/structured_outputs.py` with `StructuredMcpCustomerAgentResponse`, a strict external-safe response schema that maps into the existing `RagAskResponse` MCP boundary model.
- Added focused unit tests proving schema validity, extra-field rejection, domain/result-object mapping, recommendation attribution, morning-report section mapping, and MCP refusal safety validation.
- Kept the implementation surgical by adding typed Instructor-compatible schemas and mappers rather than refactoring high-risk strategy synthesis or morning-report assembler internals in this step.
- Verification passed: `uv run ruff check application/structured_outputs mcp_server/contracts/structured_outputs.py tests/unit/application/structured_outputs tests/unit/mcp_server/contracts/test_structured_outputs.py --fix`.
- Verification passed: `uv run ruff format application/structured_outputs mcp_server/contracts/structured_outputs.py tests/unit/application/structured_outputs tests/unit/mcp_server/contracts/test_structured_outputs.py`.
- Verification passed: `uv run pytest -q tests/unit/application/structured_outputs/test_intelligence_workflow_structured_outputs.py tests/unit/mcp_server/contracts/test_structured_outputs.py tests/unit/integration/providers/llm_structured_output tests/unit/integration/providers/rag/test_structured_answer_generation_provider.py` (`25 passed`).
- Verification passed: `uv run mypy application/structured_outputs mcp_server/contracts/structured_outputs.py tests/unit/application/structured_outputs tests/unit/mcp_server/contracts/test_structured_outputs.py --explicit-package-bases`.
- Updated Graphify after Python changes with `uv run graphify update .`.

### Step 7 — Add durable prompt/program artifact records

- Added the first-class `ai_prompt_program_artifacts` PostgreSQL model and Alembic migration for durable prompt/program artifacts without overloading evaluation artifacts or metadata-only records.
- Added typed persistence contracts under `core/storage/persistence/ai_artifacts/` for `AiPromptProgramArtifactRecord`, artifact types, approval lifecycle statuses, and repository operations.
- Added `PostgresAiArtifactPersistenceRepository` with create/upsert, read, list, approve, active lookup, and deactivate behavior.
- Added validation that keeps prompt artifacts reference-based: prompt hashes must be SHA-256 digests, prompt references reject authenticated URLs and multiline raw prompt payloads, score summaries reject secret-like keys and authenticated URLs, and active artifacts must be approved.
- Added focused unit tests for typed-record normalization, approval-state invariants, SHA-256 prompt-hash validation, authenticated URL rejection, secret-material rejection, and artifact ID generation.
- Added a PostgreSQL integration test for repository create/read/list/approve/deactivate behavior; it is gated behind `POLARIS_TEST_DATABASE_URL` like the existing live persistence tests.
- Verification passed: `uv run ruff check core/database/models/ai_artifacts.py core/storage/persistence/ai_artifacts core/storage/persistence/repositories/postgres_ai_artifact_persistence_repository.py tests/unit/core/storage/persistence/ai_artifacts tests/integration/core/storage/persistence/test_postgres_ai_artifact_persistence_repository.py --fix`.
- Verification passed: `uv run ruff format core/database/models/ai_artifacts.py core/storage/persistence/ai_artifacts core/storage/persistence/repositories/postgres_ai_artifact_persistence_repository.py tests/unit/core/storage/persistence/ai_artifacts tests/integration/core/storage/persistence/test_postgres_ai_artifact_persistence_repository.py migrations/versions/20260715_000001_add_ai_prompt_program_artifacts.py`.
- Verification passed: `uv run pytest -q tests/unit/core/storage/persistence/ai_artifacts tests/integration/core/storage/persistence/test_postgres_ai_artifact_persistence_repository.py tests/database/test_migrations.py` (`7 passed, 8 skipped`; live PostgreSQL tests skipped because `POLARIS_TEST_DATABASE_URL` was not set).
- Verification passed: `uv run mypy core/database/models/ai_artifacts.py core/storage/persistence/ai_artifacts core/storage/persistence/repositories/postgres_ai_artifact_persistence_repository.py tests/unit/core/storage/persistence/ai_artifacts tests/integration/core/storage/persistence/test_postgres_ai_artifact_persistence_repository.py --explicit-package-bases`.
- Verification passed: `uv run alembic heads` reported single head `9d1e2f3a4b5c`.
- Updated Graphify after Python changes with `uv run graphify update .`.


### Step 8 — Create DSPy optimization workbench

- Added `application/ai_optimization/` with `AiOptimizationRequest`, `AiOptimizationResult`, `AiOptimizationTarget`, `AiOptimizationStatus`, and `AiOptimizationService` as the controlled application workbench boundary.
- Added `integration/providers/ai_optimization/` with the DSPy provider boundary and `DspyOptimizationProvider`, which builds a deterministic DSPy signature/module-backed candidate artifact without activating or mutating production runtime behavior.
- Wired the workbench flow to load selected persisted evaluation cases, build a candidate DSPy artifact, score candidate outputs through the existing `EvaluationRunService` boundary, preserve DeepEval score summaries, capture Langfuse trace IDs from evaluation score projection results, and persist the selected artifact as a non-active draft through the Step 7 AI artifact repository.
- Kept production runtime consumption intentionally out of scope: persisted artifacts remain `draft` and `active=False` until a later explicit approval/activation step.
- Added focused unit tests for deterministic DSPy artifact construction and service-level artifact persistence handoff, including DeepEval evaluation-run linkage, Langfuse trace linkage, draft status, and the failed-evaluation no-persist path.
- Verification passed: `uv run ruff check . --fix`.
- Verification passed: `uv run ruff format .`.
- Verification passed: `uv run mypy . --explicit-package-bases`.
- Verification passed: `uv run pytest -q tests/unit/application/ai_optimization/test_ai_optimization_service.py tests/unit/integration/providers/ai_optimization/test_dspy_optimization_provider.py` (`3 passed`; DSPy emitted upstream deprecation warnings only).
- Updated Graphify after Python changes with `uv run graphify update .`.

### Step 9 — Add CLI commands for optimization and promotion

- Added `interfaces/cli/commands/ai_command.py` and registered the new `polaris ai` command group in the existing Typer application.
- Added `interfaces/cli/services/ai_command_service.py` as the CLI-facing boundary for explicit/manual DSPy optimization and AI artifact lifecycle operations.
- Implemented the requested commands: `polaris ai optimize`, `polaris ai artifacts list`, `polaris ai artifacts approve`, `polaris ai artifacts activate`, and `polaris ai artifacts deactivate`.
- Wired the CLI service through the canonical Dishka request scope so optimization uses `AiOptimizationService`, `EvaluationRunService`, and the PostgreSQL-backed AI artifact repository without a parallel persistence path.
- Corrected approval semantics so approval does not automatically activate an artifact; activation is now explicit and denied unless the artifact is approved.
- Implemented activation behavior that deactivates any currently active artifact for the same target/type before upserting the newly active approved artifact, making the active artifact discoverable by runtime services through `get_active_artifact`.
- Added focused unit coverage for optimize request construction, canonical dataset-name resolution, artifact listing filters, approval without activation, invalid activation denial, active-peer deactivation, command rendering, and CLI success/failure reporting.
- Updated the PostgreSQL repository integration test expectation so `approve_artifact()` records approval audit metadata but leaves `active=False`; explicit activation remains a separate repository upsert path.
- No live services were required for this step; the live PostgreSQL AI artifact repository test remains gated behind `POLARIS_TEST_DATABASE_URL`.
- Verification passed: `uv run pytest -q tests/unit/interfaces/cli/test_ai_command_service.py tests/unit/interfaces/cli/test_ai_command.py tests/unit/application/ai_optimization/test_ai_optimization_service.py tests/unit/integration/providers/ai_optimization/test_dspy_optimization_provider.py` (`13 passed`; DSPy emitted upstream deprecation warnings only).
- Verification passed: `uv run pytest -q tests/unit/core/bootstrap/test_rag_di_composition.py tests/unit/core/storage/persistence/ai_artifacts/test_ai_artifact_persistence_models.py` (`8 passed`).
- Verification passed: `uv run mypy interfaces/cli/commands/ai_command.py interfaces/cli/services/ai_command_service.py core/storage/rag_di.py core/storage/persistence/repositories/postgres_ai_artifact_persistence_repository.py tests/unit/interfaces/cli/test_ai_command_service.py tests/unit/interfaces/cli/test_ai_command.py --explicit-package-bases`.
- Verification passed: `uv run mypy . --explicit-package-bases`.
- Verification passed: `uv run ruff check . --fix` and `uv run ruff format .`.
- Updated Graphify after Python changes with `uv run graphify update .`.

### Step 10 — Wire approved artifacts into runtime generation

- Added `application.ai_optimization.runtime_artifacts` with `ResolvedAiPromptArtifact`, `AiPromptArtifactResolver`, and `ActiveAiPromptArtifactResolver` so runtime generation can resolve active approved prompt/program artifacts through the existing PostgreSQL artifact repository boundary.
- Wired `RagAnswerGenerator` to resolve the active approved `dspy_compiled_prompt` artifact for `rag_answer_generation` before provider generation, while preserving source-controlled prompt metadata as the fallback when no active artifact exists.
- Propagated resolved artifact metadata into the provider request, final `RagResult` metadata, telemetry stage attributes, and RAG AI-observability/Langfuse generation observations.
- Updated RAG DI so the answer generator receives the artifact resolver through the canonical Dishka request scope; no DSPy optimizer is imported or executed in the production generation path.
- Added focused tests for source-controlled fallback behavior, approved artifact metadata propagation, and Langfuse observation artifact references.
- No live services were required for this step.
- Verification passed: `uv run pytest -q tests/unit/application/rag/test_secure_rag_generation.py tests/unit/application/rag/test_rag_service_graph.py tests/unit/core/bootstrap/test_rag_di_composition.py` (`27 passed`).
- Verification passed: `uv run mypy application/ai_optimization application/rag/generation/answer_generator.py application/rag/observability/rag_ai_observability.py application/rag/di.py tests/unit/application/rag/test_secure_rag_generation.py tests/unit/application/rag/test_rag_service_graph.py --explicit-package-bases`.
- Verification passed: scoped Ruff check/format for the touched runtime artifact, RAG generation/observability/DI, and test files.
- Updated Graphify after Python changes with `uv run graphify update .`.

### Step 11 — Documentation and architecture guardrails

- Created `docs/ai_structured_outputs.md` documenting Instructor as the runtime structured-output adapter, the RAG structured generation flow, implemented `POLARIS_STRUCTURED_OUTPUT_*` settings, and guardrails that keep Instructor behind the provider boundary.
- Created `docs/ai_prompt_optimization.md` documenting DSPy as the offline optimization workbench, implemented `polaris ai optimize` and `polaris ai artifacts ...` commands, implemented `POLARIS_DSPY_*` settings, explicit approval/activation semantics, and the PostgreSQL-backed artifact lifecycle.
- Updated `docs/llm_evaluation.md` to clarify that DeepEval remains the canonical semantic evaluation engine while Instructor handles schema validity and DSPy supplies candidate prompt/program artifacts.
- Updated `docs/langfuse_ai_observability.md` to document Instructor/DSPy/DeepEval trace, dataset, score, and artifact correlations while keeping Langfuse a projection rather than an artifact or evaluation source of truth.
- Updated `docs/platform_rag_pipeline.md` with structured generation and prompt artifact governance for the `rag_answer_generation` runtime path.
- No live services were required for this documentation-only step.
- Verification passed: reviewed implemented command names and settings against `interfaces/cli/commands/ai_command.py` and `config/settings.py`.
- Verification passed: searched the updated documentation and plan for authenticated connection strings or committed secret values; only placeholder secret examples were present.
